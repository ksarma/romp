#!/usr/bin/env python3
"""The chat build's per-build fixed costs, memoized on the inputs they read, and the counters that say
where a chat rebuild came from.

Every chat build used to re-derive four things whose inputs had not moved: the live merge's
transcript-side sets (every atom of the parse, per build, for the chat, feed and timeline builds of
one cycle), the sealed postal cards (re-hydrated on every judge pass although a caption is the only
judge-written value a card embeds), the ledger's goal-tree walk (per build, over the same parse and
store), and, in its own commit, the task fold (every turn's atoms, per build). builds.chat in GET /perf
counted rebuilds without saying whether the watched tab or a background one paid, or which input moved.

The tests drive the real code paths: _PerfStats, the real _push over two tabs, _merge_live_atoms with a
recording backend, build_session over a synthetic session in a rebound state root, and _msg_summaries
over stubbed discovery rows. Synthetic fixtures only: private placeholder sids (these tests mint goals,
so never the shared placeholder), invented text, TESTHOST, the notes-api demo world."""
import ast
import collections
import gc
import inspect
import json
import os
import re
import tempfile
import threading
import time
import unittest
from unittest import mock
from datetime import datetime, timezone
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
if __package__:                                  # under pytest tests/ is a package: the one parse_cache module the
    from . import parse_cache as PC              # AST censuses of the process share (one parse of kernel.py between them)
else:                                            # a direct run has tests/ on sys.path already (tests/romp_load.py)
    import parse_cache as PC                     # noqa: E402
KERNEL_PY = os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")
# Hermetic state BEFORE the load: the kernel resolves its state root at import time, and only pytest runs
# conftest's floor (a bare unittest run would otherwise write real state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_chat_memos", os.path.join(BIN, "romp-kernel"))
jd = km.jd                                       # the kernel's own judge module
_REAL_MSG_SUMMARIES = km._msg_summaries          # the real union, for the tests that stub it and the one that must not

# PRIVATE synthetic sids: these tests mint goal stores, and the shared placeholder sid's override journal
# is replayed onto every store minted under it (CLAUDE.md, goal-store fixtures).
SID_A = "66666666-7777-8888-9999-aaaaaaaaaaa1"
SID_B = "66666666-7777-8888-9999-aaaaaaaaaaa2"
PEER = "66666666-7777-8888-9999-aaaaaaaaaaa3"
OTHER_A = "66666666-7777-8888-9999-aaaaaaaaaaa4"   # two sessions the built tab is party to no message with
OTHER_B = "66666666-7777-8888-9999-aaaaaaaaaaa5"
MID = "1788400000.100_1.TESTHOST"


def _clear_memos():
    """Every chat-build memo this module fills, emptied; a name absent on a tree without the memos is skipped."""
    for name in ("_chat_fold", "_ledger_memo", "_task_fold_memo", "_node_anchor_last", "_node_anchor_rev",
                 "_merge_sets_memo"):
        d = getattr(km, name, None)
        if isinstance(d, dict):
            d.clear()


# ── the signature's labels and the chat writer ───────────────────────────────────────────────────
class SigLabels(unittest.TestCase):
    """_chat_build_sig is a flat tuple with one labelled position per component (_CHAT_SIG_LABELS); a rebuild
    is attributed to the components that moved, by position. The row the push hands over is one slot
    either way (None without a row), so every signature has the same shape."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = td.name
        self.tx = Path(self.tmp) / (SID_A + ".jsonl")
        self.tx.write_text('{"type": "user"}\n')
        self.sess = {"sid": SID_A, "path": str(self.tx), "anchor": SID_A}
        self.saved = (km._sdk, km._live_map)
        km._sdk = lambda: None
        km._live_map = lambda: {}

    def tearDown(self):
        km._sdk, km._live_map = self.saved

    def test_a_real_signature_has_one_label_per_position_and_a_row_slot_either_way(self):
        sig = km._chat_build_sig(self.sess)
        self.assertEqual(len(sig), len(km._CHAT_SIG_LABELS))
        row_i = km._CHAT_SIG_LABELS.index("row")
        self.assertEqual(sig[row_i], (None, False), "no row handed over and an empty map: the slot says so")
        self.assertEqual(km._chat_build_sig(self.sess), sig, "stable while nothing moved")
        row = {"state": "idle", "model": "m", "context": 10, "effort": "e", "mode": None, "fast": False,
               "since": int(time.time()) - 5, "subagents": [], "bgTasks": [], "connected": True}   # since: recent, so the faded boolean holds
        sig2 = km._chat_build_sig(self.sess, row)
        self.assertEqual(len(sig2), len(sig))
        self.assertEqual(km._chat_sig_miss(sig, sig2), ("row",), "the row handed over is the row component")
        forked = dict(self.sess, anchor=SID_B)                # a forked lane stats two states files
        sig3 = km._chat_build_sig(forked)
        self.assertEqual(len(sig3), len(sig), "the states component holds both files; the shape never changes")
        self.assertEqual(km._chat_sig_miss(sig, sig3), ("states",))
        self.assertEqual(km._PerfStats.CHAT_MISS, km._CHAT_SIG_LABELS + ("cold", "nosig"))
        self.assertIsNone(km._chat_build_sig({"sid": SID_A, "path": ""}), "no path: no signature")
        self.assertEqual(sig[km._CHAT_SIG_LABELS.index("transcript")], (self.tx.stat().st_mtime, self.tx.stat().st_size))
        self.assertEqual(sig[-3:], ((), (), None), "a tab with no cached build records no dependencies yet")
        gone = dict(self.sess, path=str(Path(self.tmp) / "not-yet.jsonl"))
        sig4 = km._chat_build_sig(gone)
        self.assertIsNone(sig4[0], "a transcript that does not exist yet is a component, so the tab still caches")
        self.assertEqual(len(sig4), len(km._CHAT_SIG_LABELS))

    def test_each_moved_component_is_named(self):
        base = tuple(range(len(km._CHAT_SIG_LABELS)))
        for i, lab in enumerate(km._CHAT_SIG_LABELS):
            new = list(base)
            new[i] = "changed"
            self.assertEqual(km._chat_sig_miss(base, tuple(new)), (lab,), lab)
        self.assertEqual(km._chat_sig_miss(base, base), (), "an equal signature is no miss")
        self.assertEqual(km._chat_sig_miss(None, base), ("cold",), "no cached build")
        self.assertEqual(km._chat_sig_miss(base, None), ("nosig",), "no signature could be taken")
        two = list(base)
        two[km._CHAT_SIG_LABELS.index("transcript")] = "x"
        two[km._CHAT_SIG_LABELS.index("store")] = "y"
        self.assertEqual(km._chat_sig_miss(base, tuple(two)), ("store", "transcript"),
                         "several moved components are each named, sorted")
        self.assertEqual(km._chat_sig_miss(base, base[:-1]), ("cold",), "a signature of another shape is no cached build")

    def test_the_labels_follow_the_appends_in_source_order(self):
        # the two tests above pin the label-to-position mapping at `row` and `states` and over synthetic tuples;
        # this one pins the append order of the rest against the body: one marker per labelled read
        # reg reads through _chat_reg_sig since upstream https://github.com/romp-on/romp/pull/1738: the helper keys the
        # registry content without hostAck and hostLogPos, so a host journal ack no longer busts the tab
        src = inspect.getsource(km._chat_build_sig)
        markers = {"transcript": "sig.append((st.st_mtime, st.st_size))", "states": "sig.append(tuple(states))",
                   "store": "jd._store_identity(sid)[1:]", "hold": "_rewind_hold_get(sid)", "archive": "jd.ARCHDIR",
                   "episodes": "jd.EPIDIR", "reg": "_chat_reg_sig(sid)", "gone": "jd.GONEDIR", "tasks": "_task_store_fp(",
                   "todos": "_user_todo_fp(", "pins": "_pinned_notes_fp(", "cut": "pending_cut(",
                   "live": "Sessions.live_rev(sid, be)", "row": "sig.append((_chat_row_sig(tm), bool(live_map)))", "clock": "_idle_faded(",
                   "backend": "_queue_recallable(", "ops": "_pending_ops.get(sid)", "limit": "_limit_hold(sid, usage=",
                   "retry": "_retry_gate_state(sid)", "bg": "_bg_live_norm(sid, path, live=tm)", "watch": "_watch_awaiting(sid)",
                   "stamp": "_session_stamp_read(sid)", "anchors": "_node_anchor_rev.get(sid, 0)",
                   "downtime": '"downtime", "names", "flags"', "cwd": "_github_repo_of(scwd)", "claudemd": "_claudemd_key(scwd)",
                   "fork": "fork_children()", "note": "_chat_ident(_np)", "needs": "_feed_needs_input_of(sid) is True",
                   "taskout": "_chat_sig_deps(sid, deps)"}
        for lab, needle in markers.items():
            self.assertIn(lab, km._CHAT_SIG_LABELS, lab)
            self.assertIn(needle, src, "%s: the read this table names is not in the body" % lab)
        pos = [src.index(markers[lab]) for lab in km._CHAT_SIG_LABELS if lab in markers]
        self.assertEqual(pos, sorted(pos), "the labels are in the appends' order")
        shared = ("downtime", "names", "flags", "ncards", "colormap", "acct", "cleared", "host")
        i = km._CHAT_SIG_LABELS.index("downtime")
        self.assertEqual(km._CHAT_SIG_LABELS[i:i + len(shared)], shared, "the shared components ride in the loop's order")
        self.assertEqual(km._CHAT_SIG_LABELS[-3:], km._CHAT_SIG_DEPS, "the three dependency components close the tuple")
        self.assertNotIn("_judge_gen[0]", src, "the judge-pass counter is no chat input (the docstring may name its removal)")
        for name in ("_CHAT_SIG_TAIL", "_chat_sig_labels", "_active_chat_sig"):
            self.assertFalse(hasattr(km, name), "%s: an older key's name, gone with it" % name)


class Collector(unittest.TestCase):
    """_PerfStats.build_chat: the chat kind's writer, splitting the watched tab's rebuilds from the
    background tabs' and naming what moved for each background rebuild."""

    def test_build_chat_splits_active_from_background_and_attributes_the_latter(self):
        st = km._PerfStats()
        st.build_chat(True)
        st.build_chat(False, 0.010, active=True)
        st.build_chat(False, 0.020, active=False, miss=("store",))
        st.build_chat(False, 0.030, active=False, miss=("states", "transcript"))
        st.build_chat(False, 0.005, active=False, miss=("cold",))
        st.build_chat_moved()
        c = st.snapshot()["builds"]["chat"]
        self.assertEqual((c["cached"], c["built"], c["active_built"], c["bg_built"], c["moved"]), (1, 4, 1, 3, 1))
        self.assertAlmostEqual(c["ms"], 65.0)
        self.assertEqual({k: v for k, v in c["bg_miss"].items() if v},
                         {"store": 1, "states": 1, "transcript": 1, "cold": 1},
                         "one count per moved component: the two-component miss counts under both")
        self.assertEqual(set(c["bg_miss"]), set(km._PerfStats.CHAT_MISS))
        st.build_chat(False, 0.001, miss=("cold",))
        self.assertEqual(c["bg_miss"]["cold"], 1, "the snapshot is a copy; a later write does not move it")
        s = st.snapshot()["builds"]
        self.assertEqual(set(s["feed"]), {"cached", "built", "ms", "dirty", "memo"},
                         "no split on feed (its dirty is the view-signature bypass; memo is T368's per-session card memo)")
        self.assertEqual(set(s["timeline"]), {"cached", "built", "ms"}, "no split on the other kinds")
        json.dumps(s)
        st.build("chat", False, 0.001)                        # the plain writer still serves the kind, unattributed
        c2 = st.snapshot()["builds"]["chat"]
        self.assertEqual((c2["built"], c2["active_built"] + c2["bg_built"]), (6, 5))

    def test_the_four_memos_report_under_memos(self):
        snap = km._PerfStats().snapshot()["memos"]
        self.assertEqual(set(snap["chatMergeSets"]), {"hit", "miss", "entries", "floorAgeMaxS", "builtAboveFloor"})   # 5b's two counters
        self.assertEqual(set(snap["chatPostal"]), {"gate", "hit", "commit_new"})
        self.assertEqual(set(snap["chatLedger"]), {"hit", "miss", "bypass_live", "bypass_hold", "bypass_empty", "evict", "entries"})
        self.assertEqual(set(snap["chatFoldTasks"]), {"hit", "miss", "entries"})


class MemoBump(unittest.TestCase):
    """The memos' counters are bumped under the chat fold's lock: the pusher, the WS handlers and the
    backends all build, and a bare increment from two threads loses counts."""

    def test_concurrent_bumps_land_exactly(self):
        stats, n, per = {"hit": 0}, 8, 2000
        gate = threading.Barrier(n)

        def run():
            gate.wait()
            for _ in range(per):
                km._chat_memo_bump(stats, "hit")
        threads = [threading.Thread(target=run) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(stats["hit"], n * per)
        km._chat_memo_bump(stats, "new", 3)
        self.assertEqual(stats["new"], 3, "a missing key starts at zero; n adds n")

    def test_the_bump_waits_on_the_fold_caches_lock(self):
        stats, done = {"hit": 0}, threading.Event()
        with km._chat_fold_lock:
            t = threading.Thread(target=lambda: (km._chat_memo_bump(stats, "hit"), done.set()))
            t.start()
            t.join(0.2)
            self.assertEqual(stats["hit"], 0, "held: the bump has not landed")
        done.wait(5)
        self.assertEqual(stats["hit"], 1, "released: it lands")


class MemoCounters(unittest.TestCase):
    """Every write to the four memos' counters goes through _chat_memo_bump (the one helper MemoBump proves
    exact under the fold's lock): a bare increment somewhere else would be the lost update the helper exists
    to prevent."""

    STATS = ("_merge_sets_stats", "_chat_postal_stats", "_ledger_memo_stats", "_task_fold_stats")

    def test_every_increment_goes_through_the_locked_helper(self):
        src = inspect.getsource(km)
        for name in self.STATS:
            bare = [l for l in src.splitlines() if re.search(r"%s\[[^\]]+\]\s*[+-]?=" % name, l)
                    # upstream's floorAgeMaxS gauge (T368's merge-sets memo) is a max() over a reading, not a
                    # count: a lost race there under-reports a gauge by one reading, which is what a gauge is
                    and not re.search(r"\]\s*=\s*max\(", l)]
            self.assertEqual(bare, [], "%s: a write outside _chat_memo_bump" % name)
            self.assertIn("_chat_memo_bump(%s, " % name, src, "%s is bumped through the helper" % name)


# ── the real push over two tabs ──────────────────────────────────────────────────────────────────
class TwoTabAttribution(unittest.TestCase):
    """_push over two tabs, one watched: a rebuild counts under active_built or bg_built, and a background
    rebuild names the component that moved. The sweep at the end of the chat block drops the memos of
    tabs no longer shown (keeping this cycle's comment threads, like the fold prefixes)."""

    STUBS = ("NAMES", "_live_map", "_live_names", "_chat_tab_sessions", "build_session",
             "_cached_feed", "_cached_timeline", "build_timeline", "_fleet_view_sig", "_comments_frame",
             "_retry_parked_creates")

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = td.name
        names = Path(self.tmp) / "names"
        names.mkdir()
        for sid, nm in ((SID_A, "web"), (SID_B, "api")):
            (names / sid).write_text("%s\t/proj/TESTHOST/app\t#1EA1EB\twhite\n" % nm)
        self.tx = {sid: Path(self.tmp) / (sid + ".jsonl") for sid in (SID_A, SID_B)}
        for p in self.tx.values():
            p.write_text('{"type": "user"}\n')                 # exists: _chat_build_sig is a real signature
        self.saved = {nm: getattr(km, nm) for nm in self.STUBS}
        self.saved_state = (jd.STATE, dict(km._built_chat), dict(km._prev_chat_events),
                            dict(km._prev_chat_ledger), list(km._last_tab_order), km._judge_gen[0],
                            [set(km._thread_fold_keep[0]), set(km._thread_fold_keep[1])])
        jd._rebind_state(Path(self.tmp) / "state")
        for d in (jd.STATESDIR, jd.GOALDIR):
            d.mkdir(parents=True, exist_ok=True)
        km.NAMES = names
        self.live = {}
        km._live_map = lambda: dict(self.live)
        km._live_names = lambda tm: {"web": SID_A, "api": SID_B}
        km._chat_tab_sessions = lambda now, live_map: [{"sid": s, "name": n, "path": str(self.tx[s]), "anchor": s}
                                                  for s, n in ((SID_A, "web"), (SID_B, "api"))]
        km.build_session = self._build_session
        km._cached_feed = lambda now, live_map, sig, connect=False: {"working": [], "awaiting": [], "now": now}
        km._cached_timeline = lambda now, live_map, sig, connect=False: {"turns": {}, "judging": [], "messages": [], "now": now}
        km.build_timeline = lambda now, live_map, **kw: {"lanes": [], "now": now}
        km._fleet_view_sig = lambda now, live_map: {"probe": 1}
        km._comments_frame = lambda sid, live_map: None
        km._retry_parked_creates = lambda: None
        km._built_chat.clear(); km._prev_chat_events.clear(); km._prev_chat_ledger.clear()
        self.built = []
        self.chat = {"app": "chat", "alive": True, "sent": {}, "active": SID_A, "send": lambda s: None}
        self.tl = {"app": "timeline", "alive": True, "sent": {}, "send": lambda s: None}

    def tearDown(self):
        for nm, v in self.saved.items():
            setattr(km, nm, v)
        st, bc, pe, pl, lo, jg, keep = self.saved_state
        jd._rebind_state(st)
        km._built_chat.clear(); km._built_chat.update(bc)
        km._prev_chat_events.clear(); km._prev_chat_events.update(pe)
        km._prev_chat_ledger.clear(); km._prev_chat_ledger.update(pl)
        km._last_tab_order[:] = lo
        km._judge_gen[0] = jg
        km._thread_fold_keep[0], km._thread_fold_keep[1] = keep

    def _build_session(self, sid, now, live_map):
        self.built.append(sid)
        return {"type": "session", "id": sid, "name": "x", "events": [{"uuid": "e1", "type": "user"}],
                "ledger": None, "status": {"state": "waiting"}, "color": None}

    @staticmethod
    def _chat():
        return km._PERF_STATS.snapshot()["builds"]["chat"]

    @staticmethod
    def _delta(before, after):
        d = {k: after[k] - before[k] for k in ("cached", "built", "active_built", "bg_built")}
        d["bg_miss"] = {k: v - before["bg_miss"][k] for k, v in after["bg_miss"].items() if v - before["bg_miss"][k]}
        return d

    def test_active_background_and_the_named_cause_of_each_background_rebuild(self):
        c0 = self._chat()
        km._push([self.chat, self.tl])
        c1 = self._chat()
        self.assertEqual(sorted(self.built), sorted([SID_A, SID_B]))
        self.assertEqual(self._delta(c0, c1), {"cached": 0, "built": 2, "active_built": 1, "bg_built": 1,
                                               "bg_miss": {"cold": 1}}, "first cycle: the background tab is cold")
        km._push([self.chat, self.tl])
        c2 = self._chat()
        self.assertEqual(self._delta(c1, c2), {"cached": 2, "built": 0, "active_built": 0, "bg_built": 0, "bg_miss": {}},
                         "nothing moved: both tabs are served on the one key")
        with open(self.tx[SID_B], "a") as f:
            f.write('{"type": "assistant"}\n')
        km._push([self.chat, self.tl])
        c3 = self._chat()
        self.assertEqual(self._delta(c2, c3), {"cached": 1, "built": 1, "active_built": 0, "bg_built": 1,
                                               "bg_miss": {"transcript": 1}},
                         "the background tab's transcript grew; the watched one is served")
        (jd.GOALDIR / (SID_B + ".json")).write_text(json.dumps({"rompUuid": SID_B, "nodes": {}, "status": {}}))
        km._bump_judge_gen_if_changed()                    # the producer's own bump after a pass that moved a store
        km._push([self.chat, self.tl])
        c4 = self._chat()
        self.assertEqual(self._delta(c3, c4)["bg_miss"], {"store": 1},
                         "a judge pass that published this session's store rebuilds its tab under store")
        self.assertEqual(self._delta(c3, c4)["bg_built"], 1)
        km._judge_gen[0] += 1                              # a pass that moved nothing this world reads
        km._push([self.chat, self.tl])
        self.assertEqual(self._delta(c4, self._chat())["built"], 0, "the judge-pass counter alone rebuilds no tab")
        c4 = self._chat()
        with open(jd.STATESDIR / (SID_B + ".jsonl"), "a") as f:
            f.write('{"t": 1, "state": "idle"}\n')
        km._push([self.chat, self.tl])
        c5 = self._chat()
        self.assertEqual(self._delta(c4, c5), {"cached": 1, "built": 1, "active_built": 0, "bg_built": 1,
                                               "bg_miss": {"states": 1}}, "the background tab's states file grew")
        km._push([self.chat, self.tl])
        c6 = self._chat()
        self.assertEqual(self._delta(c5, c6), {"cached": 2, "built": 0, "active_built": 0, "bg_built": 0, "bg_miss": {}},
                         "both are served again once nothing moves")
        with open(self.tx[SID_A], "a") as f:
            f.write('{"type": "assistant"}\n')
        km._push([self.chat, self.tl])
        c7 = self._chat()
        self.assertEqual(self._delta(c6, c7), {"cached": 1, "built": 1, "active_built": 1, "bg_built": 0, "bg_miss": {}},
                         "the watched tab's own transcript grew: it rebuilds, under active_built, unattributed")

    def test_the_sweep_drops_the_merge_sets_of_a_sid_neither_shown_nor_alive(self):
        stray = "66666666-7777-8888-9999-aaaaaaaaaaa9"
        alive = "66666666-7777-8888-9999-aaaaaaaaaaa8"
        self.live = {alive: {"state": "idle"}}
        for sid in (stray, alive, SID_B):
            km._merge_sets_memo[sid] = ({"turns": []}, ())
        try:
            km._push([self.chat, self.tl])
            self.assertNotIn(stray, km._merge_sets_memo, "a sid that is neither a tab nor alive is evicted")
            self.assertIn(SID_B, km._merge_sets_memo, "a shown tab's entry stays")
            self.assertIn(alive, km._merge_sets_memo, "an alive session's entry stays: the feed and timeline merge it")
        finally:
            for sid in (stray, alive, SID_B):
                km._merge_sets_memo.pop(sid, None)

    def test_the_sweep_drops_the_ledger_memo_of_a_tab_no_longer_shown_and_keeps_this_cycles_threads(self):
        stray = "66666666-7777-8888-9999-aaaaaaaaaaa9"
        thread = "66666666-7777-8888-9999-aaaaaaaaaaa7"
        for sid in (stray, thread, SID_B):
            km._ledger_memo[sid] = (("seams", None, 0), {"turns": []}, {"nodes": {}}, [], [])
        km._thread_fold_keep[1].add(thread)                   # a comment thread built this cycle
        evict0 = km._ledger_memo_stats["evict"]
        try:
            km._push([self.chat, self.tl])
            self.assertNotIn(stray, km._ledger_memo, "the ledger memo of a tab no longer shown is evicted")
            self.assertIn(SID_B, km._ledger_memo, "a shown tab's entry stays")
            self.assertIn(thread, km._ledger_memo, "this cycle's thread stays, like its fold prefix")
            self.assertEqual(km._ledger_memo_stats["evict"], evict0 + 1, "one eviction counted")
            self.assertEqual(km._ledger_memo_report()["entries"], len(km._ledger_memo))
        finally:
            for sid in (stray, thread, SID_B):
                km._ledger_memo.pop(sid, None)

    def test_the_sweep_drops_the_task_fold_memo_on_the_same_keep_set(self):
        stray = "66666666-7777-8888-9999-aaaaaaaaaaa9"
        thread = "66666666-7777-8888-9999-aaaaaaaaaaa7"
        for sid in (stray, thread, SID_B):
            km._task_fold_memo[sid] = {}
        km._thread_fold_keep[1].add(thread)
        try:
            km._push([self.chat, self.tl])
            self.assertNotIn(stray, km._task_fold_memo, "the task fold memo of a tab no longer shown is evicted")
            self.assertIn(SID_B, km._task_fold_memo, "a shown tab's entry stays")
            self.assertIn(thread, km._task_fold_memo, "this cycle's thread stays")
            self.assertEqual(km._task_fold_report()["entries"], len(km._task_fold_memo))
        finally:
            for sid in (stray, thread, SID_B):
                km._task_fold_memo.pop(sid, None)


# ── the live merge's transcript-side sets ────────────────────────────────────────────────────────
class MergeSets(unittest.TestCase):
    """_merge_tx_sets: the sets _merge_live_atoms derives from the parsed session, memoized per sid on the
    session object's identity; the same object hits, a fresh parse misses, and the memoized sets are never
    written by a merge or by the backend's prune."""

    T = 1781100000

    def setUp(self):
        self._saved = (km.Sessions.__dict__["backend_for"], dict(km._merge_sets_memo), dict(km._merge_sets_stats))
        km._merge_sets_memo.clear()
        for k in km._merge_sets_stats:
            km._merge_sets_stats[k] = 0
        self.calls, self.live = [], []
        test = self

        class Fake:
            def live_atoms(self, sid):
                return list(test.live)

            def prune_live(self, sid, tx_uuids, tx_user_texts=(), human_floor=0):
                test.calls.append((tx_uuids, tx_user_texts, human_floor))
        km.Sessions.backend_for = staticmethod(lambda sid: Fake())

    def tearDown(self):
        km.Sessions.backend_for = self._saved[0]
        km._merge_sets_memo.clear(); km._merge_sets_memo.update(self._saved[1])
        km._merge_sets_stats.clear(); km._merge_sets_stats.update(self._saved[2])

    @staticmethod
    def _user(text, uid, t, author="human"):
        return {"type": "user", "uuid": uid, "t": t, "author": author,
                "message": {"role": "user", "content": [{"type": "text", "text": text}]}}

    @staticmethod
    def _assistant(uid, t, text=None):
        content = ([{"type": "text", "text": text}] if text is not None
                   else [{"type": "thinking", "thinking": "", "signature": "sig"}])   # a textless twin
        return {"type": "assistant", "uuid": uid, "t": t, "message": {"role": "assistant", "content": content}}

    def _session(self):
        T = self.T
        return {"turns": [
            {"id": "t1", "trigger": "u1", "t": T, "end": T + 10, "ended": True,
             "atoms": [self._user("tighten the notes-api search", "u1", T), self._assistant("a1", T + 10, "Done.")]},
            {"id": "t2", "trigger": "u2", "t": T + 20, "end": T + 30, "ended": True,
             "atoms": [self._user("ok", "u2", T + 20), self._user("ok", "u2b", T + 25),
                       self._assistant("a2", T + 30)]}]}

    def _unmemoized(self, session):
        """The derivation as _merge_live_atoms wrote it before the memo, over the same helpers."""
        tx_uuids = {a.get("uuid") for turn in session["turns"] for a in turn["atoms"] if a.get("uuid")}
        tx_text_uuids = {a.get("uuid") for turn in session["turns"] for a in turn["atoms"]
                         if a.get("uuid") and km._atom_prose_chars(a) > 0}
        tx_texts = {t for turn in session["turns"] for a in turn["atoms"] for t in km._atom_user_texts(a)}
        tx_text_t = {}
        for turn in session["turns"]:
            for a in turn["atoms"]:
                for t in km._atom_user_texts(a):
                    tx_text_t[t] = max(tx_text_t.get(t, 0), float(a.get("t") or 0))
        return (tx_uuids, tx_text_uuids, tx_texts, tx_text_t, km._human_turn_floor(session))

    def test_the_same_object_hits_a_fresh_parse_misses_and_sids_do_not_share(self):
        sess = self._session()
        s1 = km._merge_tx_sets(sess, SID_A)
        self.assertEqual((km._merge_sets_stats["hit"], km._merge_sets_stats["miss"]), (0, 1))
        self.assertIs(km._merge_tx_sets(sess, SID_A), s1, "the same parsed object: served, not derived")
        self.assertEqual((km._merge_sets_stats["hit"], km._merge_sets_stats["miss"]), (1, 1))
        again = self._session()                                     # equal content, a new parse object
        s2 = km._merge_tx_sets(again, SID_A)
        self.assertIsNot(s2, s1)
        self.assertEqual(s2, s1, "a re-parse of the same transcript derives the same sets")
        self.assertEqual(km._merge_sets_stats["miss"], 2)
        km._merge_tx_sets(again, SID_B)                             # another sid, the same object: its own entry
        self.assertEqual(km._merge_sets_stats["miss"], 3)
        self.assertEqual(km._merge_sets_report(), {"hit": 1, "miss": 3, "entries": 2, "floorAgeMaxS": 0, "builtAboveFloor": 0})   # no floor here:
        #                                                                                                        the two 5b counters stay at zero

    def test_the_sets_equal_the_unmemoized_derivation_and_the_three_sets_are_frozen(self):
        sess = self._session()
        got = km._merge_tx_sets(sess, SID_A)
        self.assertEqual(tuple(got), self._unmemoized(sess))
        self.assertEqual(got[0], {"u1", "a1", "u2", "u2b", "a2"})
        self.assertNotIn("a2", got[1], "the textless twin is not a text uuid")
        self.assertEqual(got[3]["ok"], self.T + 25, "a repeated text keeps its newest record time")
        self.assertEqual(got[4], self.T + 25)
        for i in range(3):
            self.assertIsInstance(got[i], frozenset, "set %d is frozen: a write raises instead of corrupting later hits" % i)
        self.assertIsInstance(got[3], dict, "tx_text_t stays a dict: the SDK backend's prune dispatches on isinstance(dict)")

    def test_a_merge_hands_prune_live_the_memoized_sets_and_a_withheld_uuid_makes_a_new_set(self):
        sess = self._session()
        sets = km._merge_tx_sets(sess, SID_A)
        # a live reply streaming under the textless twin's uuid: withheld from the prune, so the text stays
        self.live = [{"type": "assistant", "uuid": "a2", "t": self.T + 30,
                      "message": {"role": "assistant", "content": [{"type": "text", "text": "the explanation"}]}}]
        merged = km._merge_live_atoms(sess, SID_A)
        tx_uuids, tx_text_t, floor = self.calls[-1]
        self.assertEqual(tx_uuids, sets[0] - {"a2"})
        self.assertIsNot(tx_uuids, sets[0])
        self.assertIn("a2", sets[0], "the memoized set is unchanged by the withholding")
        self.assertIs(tx_text_t, sets[3])
        self.assertEqual(floor, sets[4])
        self.assertIn("the explanation", json.dumps(merged["turns"][-1]["atoms"]), "the live text is shown")
        self.assertIs(km._merge_tx_sets(sess, SID_A), sets, "and the entry still serves")
        # a live atom whose disk twin carries text: nothing withheld, the memoized set itself is handed over
        self.live = [{"type": "assistant", "uuid": "a1", "t": self.T + 10,
                      "message": {"role": "assistant", "content": [{"type": "text", "text": "Done."}]}}]
        km._merge_live_atoms(sess, SID_A)
        self.assertIs(self.calls[-1][0], sets[0])
        self.assertEqual(sets, km._merge_tx_sets(sess, SID_A), "prune_live wrote into nothing")
        self.assertEqual(km._merge_sets_stats["miss"], 1)

    def test_no_live_atoms_skips_the_sets(self):
        sess = self._session()
        self.assertIs(km._merge_live_atoms(sess, SID_A), sess)
        self.assertEqual(km._merge_sets_stats, {"hit": 0, "miss": 0, "floorAgeMaxS": 0, "builtAboveFloor": 0})

    def test_the_memo_is_bounded_one_eviction_at_a_time(self):
        sess = self._session()
        for i in range(km._MERGE_SETS_MAX + 3):
            km._merge_tx_sets(sess, "sid-%d" % i)
        self.assertEqual(len(km._merge_sets_memo), km._MERGE_SETS_MAX)
        self.assertNotIn("sid-0", km._merge_sets_memo, "the oldest entry went first")
        self.assertIn("sid-%d" % (km._MERGE_SETS_MAX + 2), km._merge_sets_memo)


# ── the sealed postal cards' values and the caption map ──────────────────────────────────────────
class PostalCardDeps(unittest.TestCase):
    """_postal_card_deps: per sealed card, exactly the values it embeds from outside the transcript."""

    def setUp(self):
        self._names = getattr(km._live_scope, "names", None)
        km._live_scope.names = {PEER: ["api", "/tmp/notes-api", "#abcdef"]}

    def tearDown(self):
        km._live_scope.names = self._names

    def test_each_embedded_value_is_a_component_and_nothing_else_is(self):
        index = {MID: {"id": MID, "from": "api", "fromId": PEER, "toId": SID_A, "body": "b",
                       "kind": "coordinate", "t": 1, "park": False}}
        colour = {"bg": "#abcdef", "fg": "#ffffff"}
        cards = [{"kind": "postal-service", "direction": "in", "peer": "api", "mid": MID, "summary": "cap", "body": "b"},
                 {"kind": "postal-service", "direction": "out", "peer": "api", "mid": MID, "body": "b"},
                 {"kind": "postal-service", "direction": "out", "peer": "tests", "body": "no row joined"},
                 {"kind": "tool", "name": "Bash", "output": "a raw event that did not hydrate"}]
        calls = []

        def caps():
            calls.append(1)
            return {MID: "cap"}
        deps = km._postal_card_deps(cards, index, caps)
        self.assertEqual(deps, ((MID, "cap", "api", colour), (MID, "cap", colour), (None, None, None), None))
        self.assertEqual(len(calls), 1, "the caption map is fetched once, and only because a card carries a mid")
        km._live_scope.names = {PEER: ["api", "/tmp/notes-api", "#000000"]}      # the sender's colour
        self.assertNotEqual(km._postal_card_deps(cards, index, caps), deps)
        km._live_scope.names = {PEER: ["renamed", "/tmp/notes-api", "#abcdef"]}  # the sender's name
        self.assertNotEqual(km._postal_card_deps(cards, index, caps), deps)
        km._live_scope.names = {PEER: ["api", "/tmp/notes-api", "#abcdef"]}
        self.assertNotEqual(km._postal_card_deps(cards, index, lambda: {MID: "other"}), deps, "the caption")
        self.assertEqual(km._postal_card_deps(cards, index, caps), deps, "the same inputs, the same tuple")
        self.assertEqual(km._postal_card_deps([cards[2], cards[3]], index, lambda: self.fail("no mid, no map")),
                         ((None, None, None), None))


# -- the chat signature's postal check: the record's memo and the by-name colour index (2026-10-06) --------------
class _CountingCard(dict):
    """A recorded postal card that counts reads of its kind: _postal_card_deps reads it once per card per walk,
    so the count over a record's cards is the number of walks times the number of cards."""

    def __init__(self, reads, **fields):
        super().__init__(**fields)
        self.reads = reads

    def get(self, key, default=None):
        if key == "kind":
            self.reads[0] += 1
        return super().get(key, default)


_RECORD_KEYS = ("task_outs", "pl_pending", "pl_at", "pl_check", "postal_any", "postal_cards", "at_build")


class PostalSigMemo(unittest.TestCase):
    """The chat signature's postal component (_chat_sig_deps) over a cached build's record: the card values are
    memoized on the record, keyed on the names digest, the postal index and, for a record with a message-id card,
    the caption map, so a cycle whose inputs held does not walk the cards again. Such a record still fetches the
    caption map every cycle; a record with no message-id card never fetches it and is not keyed on it. The record
    is the real one (_chat_build_deps over a payload of cards), the index the real one over a messages log in a
    rebound state root, the caption map a dict the test replaces to model a republication (the union publishes a
    new one on any rescan, whether or not a caption changed) and keeps to model none, never editing one, and each
    cycle opens the pusher's scopes: a new names snapshot and an empty caption slot. Every value is held against an
    evaluation with no memo: the same function over a copy of the record made of its build-time fields, and the
    walk itself over the same cards.

    The memo keys and their dimensions, derived from the code (_names_scope_digest, _name_color_by_name,
    _postal_card_deps_memo and their call sites). Each dimension has a test at the end of this class that changes
    only that dimension and asserts the miss and a tail equal to the unmemoized one:
    - The digest cache (_live_scope.names_digest, one entry per thread): the snapshot object, by identity. The
      thread is not a dimension. The cache is per thread so that two threads' snapshots do not evict each other,
      and a cache shared by every thread with the same identity match gives the same answers.
    - The names digest, which the two keys below share: a digest of [sid, fields] for each entry, in the
      snapshot's order. Its dimensions are each entry's sid, name (parts[0]), working directory (parts[1]), colour
      (parts[2]) and the fields from parts[3] on (the foreground colour and anything after it), and the order of
      the entries. An entry added or removed moves the sids and the values together, so it is not a separate
      dimension.
    - The colour index (_name_color_index, one entry shared by every thread): the names digest. The index reads the
      names, the colours and the order. It never reads the sid, the working directory or the later fields, so a
      key without one of those gives the same answers, and only the index's rebuild shows the difference.
    - The record's entry (deps["postal_memo"]): the names digest, the postal index by identity, the caption map by
      identity for a record with a message-id card, and the record itself, since the entry is stored on it.
      Through the digest the walk reads an incoming card's sender by sid (its name and colour) and an outgoing
      card's recipient by name (the first entry in order carrying it, and its colour); no card reads the working
      directory or the later fields. Whether a record has a message-id card is learned on its first walk and is
      fixed for the record's life.
    A dimension that no reader reads cannot give a stale value, so its pin can go red only on the miss. Such a
    pin says that the key covers the whole entry; a key narrowed to the fields the readers read would turn it red,
    and the narrowing would have to remove it on purpose.

    The cards themselves are outside every key: the walk reads each card's kind, mid, direction and peer, on the rule
    that nothing writes those fields of a card in place once it is built. CardFieldWriters pins that rule over
    kernel/kernel.py's writers, a census of its AST against a list of the writes that build a new dict or write one
    that is never a card, each with a witness that checks its reason."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        saved_state, saved_names, saved_sum = jd.STATE, km.NAMES, km._msg_summaries
        jd._rebind_state(self.root / "state")
        self.log = jd.STATE / "timeline" / "messages.jsonl"
        self.log.parent.mkdir(parents=True)
        km.NAMES = self.root / "names"
        km.NAMES.mkdir()
        km._postal_index_memo[0] = None
        idx = getattr(km, "_name_color_index", None)
        if idx is not None:                      # a tree without the index has no slot (the base, for the red runs)
            idx[0] = None
        self.fetches = [0]
        self.cmap = {}

        def fetch():
            self.fetches[0] += 1
            return self.cmap
        km._msg_summaries = fetch

        def restore():
            jd._rebind_state(saved_state)
            km.NAMES, km._msg_summaries = saved_names, saved_sum
            km._postal_index_memo[0] = None
            km._live_scope.names = None
            km._live_scope.msgsum = None
            km._chat_dep_scope.deps = None
        self.addCleanup(restore)
        self.reads = [0]

    def row(self, **r):
        with open(self.log, "a") as f:
            f.write(json.dumps(r) + "\n")

    def card(self, **fields):
        return _CountingCard(self.reads, kind="postal-service", **fields)

    def record(self, cards):
        """The record a build of these cards leaves (_chat_build_deps), its build-time reads uncounted."""
        km._chat_dep_scope.deps = None
        km._live_scope.msgsum = [km._MSGSUM_UNSET]
        rec = km._chat_build_deps(SID_A, {"events": list(cards)})
        self.reads[0] = 0
        return rec

    def cycle(self, names):
        """A pusher cycle's opening: a new names snapshot (a new dict and new lists, in the given order) and an
        empty caption slot. None opens neither, as on a handler thread outside a push."""
        if names is None:
            km._live_scope.names = None
            km._live_scope.msgsum = None
        else:
            km._live_scope.names = {k: list(v) for k, v in names}
            km._live_scope.msgsum = [km._MSGSUM_UNSET]

    def held(self, rec, why):
        """The memoized tail equals, byte for byte, the tail of a copy of the record with no memo state, and its
        postal component equals the walk itself over the same cards. Both references read a by-name colour by
        the linear scan (_scan_color) while a scope is set, so neither leans on the colour index either."""
        got = km._chat_sig_deps(SID_A, rec)
        by_name = km._name_color_by_name
        km._name_color_by_name = lambda name: (_scan_color(km._live_scope.names, name)
                                               if km._live_scope.names is not None else by_name(name))
        try:
            ref = km._chat_sig_deps(SID_A, {k: rec[k] for k in _RECORD_KEYS})
            idx = km._postal_index()
            walk = (km._chat_postal_rev(SID_A, idx),
                    km._postal_card_deps(rec["postal_cards"], idx, km._msg_summaries_scoped))
        finally:
            km._name_color_by_name = by_name
        self.assertEqual(got, ref, why)
        self.assertEqual(repr(got), repr(ref), why + ": the same bytes")
        self.assertEqual(got[2], walk, why + ": the walk's own value")
        return got

    def test_two_cycles_with_unchanged_inputs_walk_the_cards_once_and_a_names_change_walks_them_again(self):
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        names = [(SID_A, ["web", "/tmp/notes-api", "#1ea1eb"]), (PEER, ["api", "/tmp/notes-api", "#abcdef"])]
        rec = self.record([self.card(direction="in", mid="m1", peer="api"),
                           self.card(direction="out", mid="m2", peer="api"),
                           self.card(direction="out", peer="tests")])
        self.cycle(names)
        first = km._chat_sig_deps(SID_A, rec)
        self.assertEqual(self.reads[0], 3, "the first check walks the three cards once")
        self.cycle(names)
        second = km._chat_sig_deps(SID_A, rec)
        self.assertEqual(self.reads[0], 3, "a second cycle with the same names, index and caption map walks no card")
        self.assertEqual(second, first)
        self.assertEqual(self.fetches[0], 3, "the caption map is still fetched every cycle (and once by the build)")
        self.cycle([names[0], (PEER, ["api", "/tmp/notes-api", "#000000"])])
        third = km._chat_sig_deps(SID_A, rec)
        self.assertEqual(self.reads[0], 6, "a names digest that moved walks the cards again")
        self.assertNotEqual(third, second, "the sender's colour moved")

    def test_the_tail_equals_an_unmemoized_check_in_every_state(self):
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.row(ev="sent", id="m2", from_id=SID_A, to_id=PEER, body="here it is", t=2)
        self.cmap = {"m1": "api: asked for the schema"}
        web = (SID_A, ["web", "/tmp/notes-api", "#1ea1eb"])
        api = (PEER, ["api", "/tmp/notes-api", "#abcdef"])
        cards = [self.card(direction="in", mid="m1", peer="api"), self.card(direction="out", mid="m2", peer="api"),
                 self.card(direction="out", peer="tests")]
        recs = [self.record(cards)]
        seen = []

        def state(names, why):
            before = self.fetches[0]
            self.cycle(names)
            for rec in recs:
                seen.append(self.held(rec, why))
            if names is not None:
                self.assertEqual(self.fetches[0], before + 1, why + ": the caption map is fetched once this cycle")

        state([web, api], "the first check")
        state([web, api], "unchanged, a new snapshot of the same registry")
        state([web, api, (OTHER_A, ["tests", "/tmp/notes-api", "#123456"])], "a name added: the recipient's colour appears")
        tests = (OTHER_A, ["tests", "/tmp/notes-api", "#123456"])
        state([web, (PEER, ["api-v2", "/tmp/notes-api", "#abcdef"]), tests], "the sender renamed")
        state([web, (PEER, ["api-v2", "/tmp/notes-api", "#abcdef"]), (OTHER_A, ["tests", "/tmp/notes-api", "#654321"])],
              "the recipient recoloured")
        tests = (OTHER_A, ["tests", "/tmp/notes-api", "#654321"])
        names = [web, (PEER, ["api-v2", "/tmp/notes-api", "#abcdef"]), tests]
        recs.append(self.record(cards + [self.card(direction="out", mid="m3", peer="tests")]))
        state(names, "a card added (the tab rebuilt)")
        recs.append(self.record(cards[1:]))
        state(names, "a card removed (the tab rebuilt)")
        self.cmap = {"m1": "api: sent the schema"}
        state(names, "a caption changed")
        self.cmap = dict(self.cmap)
        state(names, "the caption map replaced by an equal one")
        self.row(ev="exec", id="m2", t=3)
        state(names, "the log moved: an outcome")
        self.row(ev="sent", id="m1", from_id=OTHER_B, to_id=SID_A, body="the schema?", t=4)
        state(names, "the log moved: the incoming card's row now names another sender")
        twin = (OTHER_B, ["tests", "/tmp/notes-api", "#222222"])
        state([web, tests, twin], "two entries share the recipient's name")
        state([web, twin, tests], "the same entries in the other order: the first one carrying the name answers")
        state([], "an empty registry")
        for sid, parts in (web, api):
            (km.NAMES / sid).write_text("\t".join(parts) + "\n")
        state(None, "no names scope: the registry is read per card")
        state([web, api], "a scope again")
        self.assertGreater(len({repr(t) for t in seen}), 6, "the states moved the tail (the pin compares something)")

    def test_two_unscoped_checks_after_a_rename_each_read_the_registry(self):
        """With no names scope (a thread outside a push) the walk reads the registry per card and nothing
        digests it, so the memo stands aside (_postal_card_deps_memo, `nd is None`): a rename and recolour
        between two unscoped checks reaches the second tail. The messages log and the caption map are the same
        objects at both checks, so the index and the caption map alone would let a stored entry hit."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        rec = self.record([self.card(direction="in", mid="m1", peer="api"), self.card(direction="out", peer="api")])
        for sid, parts in ((SID_A, ["web", "/tmp/notes-api", "#1ea1eb"]), (PEER, ["api", "/tmp/notes-api", "#abcdef"])):
            (km.NAMES / sid).write_text("\t".join(parts) + "\n")
        self.cycle(None)
        first = self.held(rec, "the first unscoped check")
        (km.NAMES / PEER).write_text("api-v2\t/tmp/notes-api\t#000000\n")
        self.cycle(None)
        second = self.held(rec, "a second unscoped check after the sender's rename and recolour")
        self.assertNotEqual(second, first, "the rename moved the tail")
        incoming = second[2][1][0]
        self.assertEqual((incoming[2], incoming[3]["bg"]), ("api-v2", "#000000"),
                         "the incoming card's name and colour are the registry's current ones")

    def test_each_unscoped_check_walks_every_card_and_stores_no_entry(self):
        """The stand-aside itself, with nothing moving: every unscoped check walks the record's cards, counted
        around the memoized check alone, and leaves no entry on the record."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        rec = self.record([self.card(direction="in", mid="m1", peer="api"), self.card(direction="out", peer="api")])
        (km.NAMES / PEER).write_text("api\t/tmp/notes-api\t#abcdef\n")
        for n in (1, 2):
            self.cycle(None)
            before = self.reads[0]
            km._chat_sig_deps(SID_A, rec)
            self.assertEqual(self.reads[0] - before, 2, "unscoped check %d walks both cards" % n)
        self.assertNotIn("postal_memo", rec, "no names digest, no entry")

    # The memos hold the objects they key on (the snapshot in _names_scope_digest's cache, the index and the
    # caption map in the record's entry), never their ids. CPython reuses a freed object's address, and the
    # pusher drops each cycle's snapshot and slot before the next cycle takes new ones, so an id key would hand
    # an entry made for one object to a later one at the same address.
    def test_snapshots_dropped_before_the_next_is_taken_each_get_their_own_tail(self):
        """Two registries that colour both cards differently alternate for 200 cycles, the scope cleared after
        each (the pusher's finally), so a new snapshot can be placed at the address of the one just dropped.
        Every tail equals the unmemoized check."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        rec = self.record([self.card(direction="in", mid="m1", peer="api"), self.card(direction="out", peer="tests")])
        regs = ([(PEER, ["api", "/tmp/notes-api", "#abcdef"]), (OTHER_A, ["tests", "/tmp/notes-api", "#123456"])],
                [(PEER, ["api", "/tmp/notes-api", "#000000"]), (OTHER_A, ["tests", "/tmp/notes-api", "#654321"])])
        tails = set()
        for i in range(200):
            self.cycle(regs[i % 2])
            tails.add(repr(self.held(rec, "cycle %d" % i)))
            self.cycle(None)
        self.assertEqual(len(tails), 2, "the two registries give two tails (the pin compares something)")

    def test_a_caption_map_replaced_twice_between_two_checks_gets_its_own_tail(self):
        """The caption map is replaced twice before each check, with no collection in between: the first
        replacement frees the map the record's entry saw, and the second can be placed at its address. Each
        round's caption is new, and every tail equals the unmemoized check."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: caption 0"}
        rec = self.record([self.card(direction="in", mid="m1", peer="api")])
        names = [(PEER, ["api", "/tmp/notes-api", "#abcdef"])]
        for i in range(200):
            self.cycle(names)
            self.cmap = {"m1": "api: caption %d a" % i}
            self.cmap = {"m1": "api: caption %d b" % i}
            self.held(rec, "round %d" % i)
            self.cycle(None)

    def _log_moves_twice_setup(self):
        names = [(PEER, ["api", "/tmp/notes-api", "#abcdef"]), (OTHER_A, ["tests", "/tmp/notes-api", "#123456"])]
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        rec = self.record([self.card(direction="in", mid="m1", peer="api")])
        return names, rec, (PEER, OTHER_A)

    def test_a_log_that_moves_twice_between_two_checks_gets_its_own_tail_scope_first(self):
        """The index's case, first order: the scope is opened, the log moves (the incoming card's row now names
        the other sender), another reader builds that index, the log moves again (an outcome row), and the
        record is checked against a third index. Whether that index is placed at the address of the one the
        entry saw depends on the allocator's free lists, so an id key goes red here only where the address is
        reused (3.14t in this order; the next test's order covers 3.10 and 3.12).
        test_the_memos_hold_the_objects_they_key_on is the check that holds on every interpreter."""
        names, rec, senders = self._log_moves_twice_setup()
        for i in range(200):
            self.cycle(names)
            self.row(ev="sent", id="m1", from_id=senders[(i + 1) % 2], to_id=SID_A, body="the schema?", t=2 + i)
            km._postal_index()
            self.row(ev="exec", id="m1", t=2 + i)
            self.held(rec, "round %d" % i)
            self.cycle(None)

    def test_a_log_that_moves_twice_between_two_checks_gets_its_own_tail_collected(self):
        """The index's case, second order: check, the scope closed, the log moves, another reader builds that
        index, a collection, the log moves again. An id key goes red in this order only where the address is
        reused (3.10 and 3.12); see the previous test."""
        names, rec, senders = self._log_moves_twice_setup()
        for i in range(200):
            self.cycle(names)
            self.held(rec, "round %d" % i)
            self.cycle(None)
            self.row(ev="sent", id="m1", from_id=senders[(i + 1) % 2], to_id=SID_A, body="the schema?", t=2 + i)
            km._postal_index()
            gc.collect()
            self.row(ev="exec", id="m1", t=2 + i)

    def test_the_memos_hold_the_objects_they_key_on(self):
        """Where the keys are kept, not what a reused key would do: after one check under a scope, the digest
        cache holds the snapshot itself and the record's entry holds the index and the caption map
        themselves. The executed consequences are the tests above: the snapshot's and the caption map's on
        every interpreter, the index's only where the allocator reuses the address."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        rec = self.record([self.card(direction="in", mid="m1", peer="api")])
        self.cycle([(PEER, ["api", "/tmp/notes-api", "#abcdef"])])
        km._chat_sig_deps(SID_A, rec)
        self.assertTrue(any(o is km._live_scope.names for o in getattr(km._live_scope, "names_digest", ())),
                        "the digest cache holds the snapshot itself, so no later snapshot can take its address while"
                        " the digest stands (consequence: test_snapshots_dropped_before_the_next_is_taken_each_get_"
                        "their_own_tail)")
        self.assertTrue(any(o is km._postal_index() for o in rec["postal_memo"]),
                        "the record's entry holds the postal index itself, so no later index can take its address"
                        " while the entry stands (consequence, only where the address is reused: the two"
                        " test_a_log_that_moves_twice_between_two_checks tests)")
        self.assertTrue(any(o is self.cmap for o in rec["postal_memo"]),
                        "the record's entry holds the caption map itself, so no later map can take its address while"
                        " the entry stands (consequence: test_a_caption_map_replaced_twice_between_two_checks_gets_"
                        "its_own_tail)")

    def test_threads_taking_turns_with_different_snapshots_check_one_record_and_each_gets_its_own_answer(self):
        """A connect push on a handler thread takes its own names snapshot while the pusher holds another; both
        can check the same cached record. Here the threads take turns: each is joined before the next starts,
        so they never overlap. Alternating snapshots, each answer equals the unmemoized one for that thread's
        snapshot, so an entry left from one thread's snapshot never answers for the other's. A reader that
        arrives while another thread is building the colour index is NameColorIndex's staged test."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        rec = self.record([self.card(direction="in", mid="m1", peer="api"), self.card(direction="out", peer="api")])
        snaps = ([(PEER, ["api", "/tmp/notes-api", "#abcdef"])], [(PEER, ["api", "/tmp/notes-api", "#000000"])])
        got, errors = [], []

        def check(names):
            try:
                self.cycle(names)
                got.append(self.held(rec, "a thread with its own snapshot"))
            except Exception as e:              # surfaced on the test thread below
                errors.append(e)
            finally:
                km._live_scope.names = km._live_scope.msgsum = None
        for names in (snaps[0], snaps[1], snaps[0], snaps[1]):
            t = threading.Thread(target=check, args=(names,))
            t.start()
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual((got[0], got[1]), (got[2], got[3]))
        self.assertNotEqual(got[0], got[1], "the two snapshots colour the cards differently")

    # -- review round 1: a record with no message-id card, and one pin per dimension of every memo key ------------
    def test_a_record_whose_cards_carry_no_message_id_walks_once_and_never_fetches_the_caption_map(self):
        """A record none of whose postal cards carries a mid: the walk never fetches the caption map, so the
        record's entry holds no map and its key is the names digest and the index alone (_postal_card_deps_memo,
        `hit[3]`). Three scoped cycles over the same registry and the same log, the caption map replaced before
        each, as in a cycle where a discovered session wrote: one walk in total, the first check's, and no caption
        fetch, the build's included. The last state's tail is held against the unmemoized check. Red at the base
        (a walk every cycle), and under a memo that fetches the map on every hit or whose entry always claims a
        mid: either one puts the map in this record's key, so each replaced map makes it miss."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=OTHER_A, body="the schema?", t=1)   # a log: the index holds
        cards = [self.card(direction="out", peer="tests"), self.card(direction="in", peer="api")]
        rec = self.record(cards)
        self.assertEqual([c for c in rec["postal_cards"] if c.get("mid")], [], "precondition: no card carries a mid")
        names = [(PEER, ["api", "/tmp/notes-api", "#abcdef"]), (OTHER_A, ["tests", "/tmp/notes-api", "#123456"])]
        for i in range(3):
            self.cmap = {"m1": "api: caption %d" % i}
            self.cycle(names)
            km._chat_sig_deps(SID_A, rec)
        self.assertEqual((self.reads[0], self.fetches[0]), (len(cards), 0),
                         "(cards read, caption fetches) over three cycles: one walk and no fetch")
        tail = self.held(rec, "the last state")
        self.assertEqual(self.fetches[0], 0, "no check of this record fetches the caption map")
        self.assertEqual(tail[2][1], ((None, None, _bg("#123456")), (None, None, None, None)),
                         "the recipient's colour; an incoming card with no mid embeds nothing")

    API = (PEER, ["api", "/tmp/notes-api", "#abcdef", "#ffffff"])
    TESTS = (OTHER_A, ["tests", "/tmp/notes-api", "#123456", "#ffffff"])

    def keyed(self):
        """The dimension pins' record: an incoming m1 card from PEER and an outgoing card to "tests" with no mid, so
        the walk reads a sender by sid (_name_of, _name_color) and a recipient by name (_name_color_by_name)."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        return self.record([self.card(direction="in", mid="m1", peer="api"), self.card(direction="out", peer="tests")])

    def probe(self, rec, names, why):
        """One scoped cycle over `names` in a snapshot that counts its walks: the memoized check counted alone, then
        held(). Returns the cards that check read, the snapshot's walks during it ("items" for a serialization by
        _names_scope_digest, "values" for a colour index build) and the tail."""
        walks = []
        self.cycle(names)
        km._live_scope.names = _WalkCountingSnap(km._live_scope.names, walks)
        before = self.reads[0]
        km._chat_sig_deps(SID_A, rec)
        read, seen = self.reads[0] - before, list(walks)
        return read, seen, self.held(rec, why)

    @staticmethod
    def values(got):
        """A keyed() probe's card values: the incoming card's (sender name, colour) and the outgoing card's colour."""
        deps = got[2][2][1]
        return deps[0][2:], deps[1][2]

    def missed(self, got, why, index=True):
        """The probe's check missed: the record's two cards were walked once and the new snapshot was serialized
        once, and the colour index was rebuilt once when the names digest moved (`index`), not at all when it held."""
        read, walks, _tail = got
        self.assertEqual(read, 2, why + ": the record's entry missed, so its two cards were walked once")
        self.assertEqual(walks.count("items"), 1, why + ": the new snapshot was serialized once")
        self.assertEqual(walks.count("values"), 1 if index else 0,
                         why + (": the colour index was rebuilt once" if index else ": the colour index held"))

    def test_the_digest_cache_answers_for_the_snapshot_it_holds_and_serializes_a_new_one_once(self):
        """The digest cache's key (_names_scope_digest): the snapshot object, by identity. A further check on the
        snapshot the cache holds serializes nothing and walks no card; a new snapshot on the same thread, the
        sender recoloured, is serialized once and its own digest answers. Red under a cache that answers without
        matching the snapshot: the old digest, so a stale colour."""
        rec = self.keyed()
        first = self.probe(rec, [self.API, self.TESTS], "the first check")
        walks, before = km._live_scope.names.walks, self.reads[0]
        n = len(walks)
        km._chat_sig_deps(SID_A, rec)
        self.assertEqual((walks[n:], self.reads[0] - before), ([], 0),
                         "a further check on the same snapshot: no serialization and no card walked")
        got = self.probe(rec, [(PEER, ["api", "/tmp/notes-api", "#000000", "#ffffff"]), self.TESTS], "a new snapshot")
        self.missed(got, "a new snapshot, the sender recoloured")
        self.assertEqual(self.values(got), (("api", _bg("#000000")), _bg("#123456")))
        self.assertNotEqual(got[2], first[2], "the sender's colour moved the tail")

    def test_an_entry_moved_to_another_session_id_misses_and_the_tail_is_fresh(self):
        """The names digest's sids (round 1, tests-2 and extra5-1): the incoming card's sender entry moved to another
        sid at the same place with the same fields, then two sids swapping their entries and places. Each time the
        sequence of values is the one before and only the sids moved. Red under a digest of the values alone: in
        the record's key, a stale sender name and colour; in the colour index's key, no rebuild (the index never
        reads a sid, so only the miss shows it)."""
        rec = self.keyed()
        first = self.probe(rec, [self.API, self.TESTS], "the first check")
        moved = self.probe(rec, [(OTHER_B, self.API[1]), self.TESTS], "the sender's entry moved to another sid")
        self.missed(moved, "an entry moved to another sid")
        self.assertEqual(self.values(moved), ((None, None), _bg("#123456")), "the row's sender, PEER, has no entry now")
        self.assertNotEqual(moved[2], first[2])
        before = self.probe(rec, [self.API, self.TESTS], "the first registry again")
        swapped = self.probe(rec, [(OTHER_A, self.API[1]), (PEER, self.TESTS[1])], "two sids swap entries and places")
        self.missed(swapped, "two sids swapped")
        self.assertEqual(self.values(swapped), (("tests", _bg("#123456")), _bg("#123456")),
                         "the row's sender, PEER, now holds the other entry")
        self.assertNotEqual(swapped[2], before[2])

    def test_a_renamed_entry_misses_and_the_tail_is_fresh(self):
        """The entries' names (parts[0]): the recipient renamed, so the outgoing card's colour moves through the
        colour index, then the sender renamed, so the incoming card's name moves. Red under a key without the
        names: in the record's key, a stale name or colour; in the colour index's key, a stale colour."""
        rec = self.keyed()
        prev = self.probe(rec, [self.API, self.TESTS], "the first check")
        renamed = (OTHER_A, ["tests-v2", "/tmp/notes-api", "#123456", "#ffffff"])
        for names, why, want in (
                ([self.API, renamed], "the recipient renamed", (("api", _bg("#abcdef")), None)),
                ([(PEER, ["api-v2", "/tmp/notes-api", "#abcdef", "#ffffff"]), renamed], "the sender renamed",
                 (("api-v2", _bg("#abcdef")), None))):
            got = self.probe(rec, names, why)
            self.missed(got, why)
            self.assertEqual(self.values(got), want, why)
            self.assertNotEqual(got[2], prev[2], why + ": the tail moved")
            prev = got

    def test_a_recoloured_entry_misses_and_the_tail_is_fresh(self):
        """The entries' colours (parts[2]): the recipient recoloured, the sender recoloured, and the recipient's
        colour losing its '#', which the colour index and _name_color read as no colour. Red under a key without
        the colours: in the record's key or in the colour index's key, a stale colour."""
        rec = self.keyed()
        prev = self.probe(rec, [self.API, self.TESTS], "the first check")
        api = (PEER, ["api", "/tmp/notes-api", "#000000", "#ffffff"])
        tests = (OTHER_A, ["tests", "/tmp/notes-api", "#654321", "#ffffff"])
        plain = (OTHER_A, ["tests", "/tmp/notes-api", "654321", "#ffffff"])
        for names, why, want in (
                ([self.API, tests], "the recipient recoloured", (("api", _bg("#abcdef")), _bg("#654321"))),
                ([api, tests], "the sender recoloured", (("api", _bg("#000000")), _bg("#654321"))),
                ([api, plain], "the recipient's colour lost its '#'", (("api", _bg("#000000")), None))):
            got = self.probe(rec, names, why)
            self.missed(got, why)
            self.assertEqual(self.values(got), want, why)
            self.assertNotEqual(got[2], prev[2], why + ": the tail moved")
            prev = got

    def test_the_same_entries_in_another_order_miss_and_the_tail_is_fresh(self):
        """The entries' order: two entries carry the recipient's name, and the first in the snapshot's order answers
        its colour. The same entries in the other order. Red under a key over the entries sorted: in the record's
        key or in the colour index's key, the other entry's colour."""
        rec = self.keyed()
        twin = (OTHER_B, ["tests", "/tmp/notes-api", "#222222", "#ffffff"])
        prev = self.probe(rec, [self.API, self.TESTS, twin], "two entries share the recipient's name")
        self.assertEqual(self.values(prev)[1], _bg("#123456"), "the first entry carrying the name answers")
        got = self.probe(rec, [self.API, twin, self.TESTS], "the same entries in the other order")
        self.missed(got, "the order moved")
        self.assertEqual(self.values(got)[1], _bg("#222222"), "the other entry is first now")

    def test_a_moved_working_directory_misses_and_the_tail_holds(self):
        """The entries' working directory (parts[1]), which neither memo's reader reads: the recipient's moved. The
        value cannot go stale, so a key without the working directory is red here only on the miss, in the record's
        key (no walk) or in the colour index's key (no rebuild). This pins that both keys cover the whole entry (the
        class docstring's last paragraph)."""
        rec = self.keyed()
        prev = self.probe(rec, [self.API, self.TESTS], "the first check")
        got = self.probe(rec, [self.API, (OTHER_A, ["tests", "/tmp/notes-web", "#123456", "#ffffff"])],
                         "the recipient's working directory moved")
        self.missed(got, "the working directory moved")
        self.assertEqual(got[2], prev[2], "no reader reads the working directory: the tail is the one before")

    def test_a_moved_later_field_misses_and_the_tail_holds(self):
        """The fields from parts[3] on, which neither memo's reader reads: the recipient's foreground colour moved,
        then a fifth field appended. The value cannot go stale, so a key without these fields is red here only on
        the miss, as for the working directory."""
        rec = self.keyed()
        prev = self.probe(rec, [self.API, self.TESTS], "the first check")
        for fields, why in ((["tests", "/tmp/notes-api", "#123456", "#000000"], "the foreground colour moved"),
                            (["tests", "/tmp/notes-api", "#123456", "#000000", "star"], "a fifth field appended")):
            got = self.probe(rec, [self.API, (OTHER_A, fields)], why)
            self.missed(got, why)
            self.assertEqual(got[2], prev[2], why + ": no reader reads it, so the tail is the one before")

    def test_a_moved_log_misses_with_the_same_names_and_caption_map(self):
        """The postal index, by identity: the log moves twice with the names and the caption map held (a new
        snapshot of the same registry each cycle, the same map object). First m1's row is sent again under another
        sender, so the incoming card's sender moves; then an outcome row lands, which moves no card value (the
        revision beside the memo moves, _chat_postal_rev), and the entry must miss all the same. Red under a key
        without the index: a stale sender."""
        rec = self.keyed()
        names = [self.API, self.TESTS]
        self.probe(rec, names, "the first check")
        held = self.probe(rec, names, "unchanged: a new snapshot of the same registry")
        self.assertEqual(held[:2], (0, ["items"]), "unchanged inputs: no card walked, the snapshot serialized once")
        self.row(ev="sent", id="m1", from_id=OTHER_A, to_id=SID_A, body="the schema?", t=2)
        got = self.probe(rec, names, "m1's row now names another sender")
        self.missed(got, "the log moved", index=False)
        self.assertEqual(self.values(got), (("tests", _bg("#123456")), _bg("#123456")))
        self.row(ev="exec", id="m1", t=3)
        again = self.probe(rec, names, "an outcome row")
        self.missed(again, "the log moved again", index=False)
        self.assertEqual(again[2][2][1], got[2][2][1], "an outcome moves no card value")

    def test_a_replaced_caption_map_misses_with_the_same_names_and_log(self):
        """The caption map, by identity, for a record with a message-id card: the map replaced with the names and the
        log held, first by one with another caption for m1, then by an equal copy, which must miss all the same (the
        key is the object). Red under a key without the map: a stale caption."""
        rec = self.keyed()
        names = [self.API, self.TESTS]
        self.probe(rec, names, "the first check")
        self.cmap = {"m1": "api: sent the schema"}
        got = self.probe(rec, names, "another caption for m1")
        self.missed(got, "the caption map replaced", index=False)
        self.assertEqual(got[2][2][1][0][1], "api: sent the schema")
        self.cmap = dict(self.cmap)
        again = self.probe(rec, names, "the caption map replaced by an equal one")
        self.missed(again, "the caption map replaced by an equal one", index=False)
        self.assertEqual(again[2], got[2])

    def test_two_records_checked_in_one_cycle_each_get_their_own_entry(self):
        """The record (the tab): the entry is stored on the record, and the cards are not in the key. Two tabs'
        records with different cards are checked in one cycle against the same names, index and caption map. Each
        record's first check walks its own cards and each tail equals its own walk, and the next cycle hits both.
        Red under an entry kept in one place for every record: the second record gets the first one's values."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.cmap = {"m1": "api: asked for the schema"}
        recs = (self.record([self.card(direction="in", mid="m1", peer="api"), self.card(direction="out", peer="tests")]),
                self.record([self.card(direction="out", peer="api"), self.card(direction="in", mid="m1", peer="api")]))
        tails = []
        for n in (1, 2):
            self.cycle([self.API, self.TESTS])
            for i, rec in enumerate(recs):
                why = "cycle %d, record %d" % (n, i + 1)
                before = self.reads[0]
                km._chat_sig_deps(SID_A, rec)
                read = self.reads[0] - before
                tails.append(self.held(rec, why))
                self.assertEqual(read, 2 if n == 1 else 0, why + (": its own cards walked once" if n == 1 else ": a hit"))
        self.assertNotEqual(tails[0], tails[1], "the two records' tails differ (the pin compares something)")
        self.assertEqual(tails[:2], tails[2:])


def _bg(colour):
    """A by-name or by-sid colour as the readers answer it."""
    return {"bg": colour, "fg": "#ffffff"}


class _WalkCountingSnap(dict):
    """A names snapshot that records each walk over its entries (values, items, keys, iteration); a lookup by
    key is not a walk."""

    def __init__(self, entries, walks):
        super().__init__(entries)
        self.walks = walks

    def values(self):
        self.walks.append("values")
        return super().values()

    def items(self):
        self.walks.append("items")
        return super().items()

    def keys(self):
        self.walks.append("keys")
        return super().keys()

    def __iter__(self):
        self.walks.append("iter")
        return super().__iter__()


def _scan_color(snap, name):
    """The by-name colour as the linear scan answered it before the index: the first entry in the snapshot's
    order carrying the name and a colour starting with '#'."""
    for parts in dict.values(snap):
        if parts and parts[0] == name and len(parts) > 2 and parts[2].startswith("#"):
            return {"bg": parts[2], "fg": "#ffffff"}
    return None


class _StagedSnap(dict):
    """A names snapshot whose walk over its values runs a hook once, right after the first entry has been handed
    out: the point at which a colour index build has read one entry and not the rest."""

    def __init__(self, entries, hook):
        super().__init__(entries)
        self.hook = hook

    def values(self):
        for i, v in enumerate(dict.values(self)):
            yield v
            if i == 0:
                self.hook()


class NameColorIndex(unittest.TestCase):
    """_name_color_by_name with a names scope answers from an index of name to colour built once per names
    digest, where it scanned the snapshot once per card, and gives the scan's answer in every state."""

    ENTRIES = [("66666666-7777-8888-9999-%012d" % i, ["s%02d" % i, "/tmp/notes-api", "#0000%02d" % i]) for i in range(40)]

    def setUp(self):
        idx = getattr(km, "_name_color_index", None)
        if idx is not None:                      # a tree without the index has no slot: the walk counts decide there
            idx[0] = None
        self.addCleanup(lambda: setattr(km._live_scope, "names", None))

    def test_the_snapshot_is_walked_once_per_digest_not_once_per_card(self):
        walks = []
        km._live_scope.names = _WalkCountingSnap(self.ENTRIES, walks)
        self.assertEqual(km._name_color_by_name("s05"), {"bg": "#000005", "fg": "#ffffff"})
        after_first = len(walks)
        for i in range(40):
            self.assertEqual(km._name_color_by_name("s%02d" % i), {"bg": "#0000%02d" % i, "fg": "#ffffff"})
        self.assertIsNone(km._name_color_by_name("docs"))
        self.assertEqual(len(walks), after_first, "41 more cards walked the snapshot %d more times" % (len(walks) - after_first))
        again = []
        km._live_scope.names = _WalkCountingSnap(self.ENTRIES, again)     # the next cycle: a new snapshot, the same registry
        for i in range(40):
            self.assertEqual(km._name_color_by_name("s%02d" % i), {"bg": "#0000%02d" % i, "fg": "#ffffff"})
        self.assertEqual(again.count("values"), 0, "the same digest reuses the index: no colour walk")
        self.assertLessEqual(len(again), 1, "one walk at most, the digest's")
        moved = []
        entries = list(self.ENTRIES)
        entries[7] = (entries[7][0], ["s07", "/tmp/notes-api", "#abcdef"])
        km._live_scope.names = _WalkCountingSnap(entries, moved)
        self.assertEqual(km._name_color_by_name("s07"), {"bg": "#abcdef", "fg": "#ffffff"}, "a recolour is seen")
        self.assertEqual(km._name_color_by_name("s08"), {"bg": "#000008", "fg": "#ffffff"})
        self.assertEqual(moved.count("values"), 1, "a digest that moved builds the index once")

    def test_the_index_answers_as_the_scan_in_every_state_and_order(self):
        a, b, c, d = ("66666666-7777-8888-9999-%012d" % i for i in range(4))
        shared_plain = (a, ["tests", "/tmp/notes-api", "white"])        # the name with no '#' colour: the scan reads on
        shared_one = (b, ["tests", "/tmp/notes-api", "#111111"])
        shared_two = (c, ["tests", "/tmp/notes-api", "#222222"])
        short = (d, ["docs"])
        names = ("tests", "docs", "api", "", None, 7, "TESTS")
        for entries in ([shared_plain, shared_one, shared_two, short], [shared_two, shared_one, shared_plain, short],
                        [shared_one, shared_two], [shared_two, shared_one], [short], [], [(a, [""])]):
            snap = dict(entries)
            km._live_scope.names = snap
            for name in names:
                self.assertEqual(km._name_color_by_name(name), _scan_color(snap, name),
                                 "%r over %r" % (name, [e[1] for e in entries]))
        km._live_scope.names = dict([shared_one, shared_two])
        first = km._name_color_by_name("tests")
        km._live_scope.names = dict([shared_two, shared_one])           # the same entries, the other order
        self.assertNotEqual(km._name_color_by_name("tests"), first, "the order decides between two entries sharing a name")
        out = km._name_color_by_name("tests")
        out["bg"] = "#ffffff"
        self.assertEqual(km._name_color_by_name("tests"), {"bg": "#222222", "fg": "#ffffff"},
                         "each answer is a new dict: a caller's edit reaches no other card")

    def test_a_reader_on_another_thread_mid_build_never_sees_a_part_filled_index(self):
        """The index is filled first and published after, as one tuple (_name_color_by_name), so a thread that
        asks while another is part way through a build finds no entry for the digest and builds its own, or
        finds a whole index; it never answers from a part-filled one. Staged without timing: the building
        thread's walk over its snapshot, right after the first entry, runs a reader thread to the end. The
        reader holds an equal snapshot (the same entries in the same order, so the same digest) and asks for
        the last entry's name. An index published before it was filled answered that reader None."""
        name = self.ENTRIES[-1][1][0]
        fired, answers, errors, alive = [], [], [], []

        def reader():
            try:
                km._live_scope.names = dict(self.ENTRIES)
                answers.append(km._name_color_by_name(name))
            except Exception as e:              # surfaced on the test thread below
                errors.append(e)
            finally:
                km._live_scope.names = None

        def mid_build():
            fired.append(1)
            t = threading.Thread(target=reader)
            t.start()
            t.join(60)
            alive.append(t.is_alive())
        snap = _StagedSnap(self.ENTRIES, mid_build)
        km._name_color_index[0] = None
        km._live_scope.names = snap
        got = km._name_color_by_name(name)
        want = _scan_color(snap, name)
        self.assertEqual(want, {"bg": "#000039", "fg": "#ffffff"})
        self.assertEqual(fired, [1], "the build walked the snapshot once and the reader ran inside that walk")
        self.assertEqual(alive, [False], "the reader finished inside the walk")
        self.assertEqual(errors, [])
        self.assertEqual(answers, [want], "the reader that arrived mid-build answers as the scan does")
        self.assertEqual(got, want, "the building thread answers as the scan does")

    def test_a_snapshot_with_no_digest_answers_from_its_own_scan_and_stores_no_index(self):
        """The guard on a names digest of None (_name_color_by_name: `d is None` in the rebuild test and in the store). A
        names file whose name is not UTF-8 reaches the snapshot as a surrogate-escaped key (os.fsdecode gives the key
        _names_snapshot files it under), which _names_scope_digest cannot encode, so under a scope the digest is None.
        Such a snapshot is answered from an index built by a scan of that snapshot on every call, and the index is never
        stored: a stored (None, index) would equal the next None digest and answer for a snapshot it was not built from.
        A snapshot with a digest stores its index first; then two snapshots carrying the undecodable entry, the
        recipient renamed between them. Each answers as its own scan, and the slot still holds the first index. Red with
        the guard dropped at both places: the renamed snapshot answers from the index stored for the one before (no
        colour for the new name, the old name's colour for the old one). Red with the store's guard dropped alone: the
        slot holds a None-keyed entry. The rebuild test's `d is None` dropped alone changes no answer and no store:
        while the store's guard stands, no stored key is None, so a None digest never matches one."""
        odd = os.fsdecode(b"66666666-7777-8888-9999-\xff\xfe")
        tests_sid = self.ENTRIES[1][0]
        km._live_scope.names = dict(self.ENTRIES[:3])
        self.assertIsNotNone(km._names_scope_digest(), "precondition: the first snapshot has a digest")
        self.assertEqual(km._name_color_by_name("s01"), _bg("#000001"))
        held = km._name_color_index[0]
        self.assertIsNotNone(held, "the snapshot with a digest stored its index")
        walks = {"before": [], "renamed": []}
        snaps = {label: _WalkCountingSnap([(odd, ["docs", "/tmp/notes-api", "#0f0f0f"]),
                                           (tests_sid, [name, "/tmp/notes-api", "#123456"])], walks[label])
                 for label, name in (("before", "tests"), ("renamed", "tests-v2"))}
        km._live_scope.names = snaps["before"]
        self.assertIsNone(km._names_scope_digest(), "precondition: no digest for a snapshot with an undecodable key")
        self.assertEqual(km._name_color_by_name("tests"), _bg("#123456"), "the recipient's colour, from this snapshot")
        self.assertEqual(km._name_color_by_name("docs"), _bg("#0f0f0f"), "the undecodable entry's own colour")
        km._live_scope.names = snaps["renamed"]
        self.assertIsNone(km._names_scope_digest(), "precondition: the renamed snapshot has no digest either")
        self.assertEqual(km._name_color_by_name("tests-v2"), _bg("#123456"),
                         "after the rename: the new name's colour, from a scan of this snapshot")
        self.assertIsNone(km._name_color_by_name("tests"), "after the rename: the old name answers nothing")
        self.assertEqual((walks["before"].count("values"), walks["renamed"].count("values")), (2, 2),
                         "each call on a snapshot with no digest builds the index from a scan of that snapshot")
        self.assertIs(km._name_color_index[0], held, "no index was stored for a snapshot with no digest")


class ProducerIdentity(unittest.TestCase):
    """The two producers whose objects the chat signature's memos key on by identity, pinned at the producer
    and through the composition. _names_scope_digest caches its digest per names snapshot object, and
    _postal_card_deps_memo keys a record's entry on the caption map object when the record has a message-id card
    (a record with none never fetches the map and is not keyed on it; this class's records carry one), so
    _names_snapshot must return a new dict on every call and _msg_summaries a new union on every change, and
    neither may edit an object it has returned. Every returned object is held across several changes: a producer
    that alternated two buffers would pass a two-call check yet hand a record that skipped a cycle its old object
    back. The union is the real _msg_summaries over stubbed discovery, keys and scans; the snapshot is the real
    _names_snapshot over a temporary registry written as the kernel writes it (_atomic_write)."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        saved_mod = (jd.STATE, km.NAMES, km._msg_summaries, km._sessions, km._msg_sum_key, km._msg_sum_scan_session)
        saved_memos = (dict(km._msg_sum_cache), dict(km._names_entry_memo), km._name_color_index[0],
                       km._postal_index_memo[0])
        saved_scope = (getattr(km._live_scope, "names", None), getattr(km._live_scope, "msgsum", None),
                       getattr(km._chat_dep_scope, "deps", None))

        def restore():
            jd._rebind_state(saved_mod[0])
            km.NAMES, km._msg_summaries, km._sessions, km._msg_sum_key, km._msg_sum_scan_session = saved_mod[1:]
            km._msg_sum_cache.clear()
            km._msg_sum_cache.update(saved_memos[0])
            km._names_entry_memo.clear()
            km._names_entry_memo.update(saved_memos[1])
            km._name_color_index[0], km._postal_index_memo[0] = saved_memos[2:]
            km._live_scope.names, km._live_scope.msgsum = saved_scope[:2]
            km._chat_dep_scope.deps = saved_scope[2]
        self.addCleanup(restore)
        jd._rebind_state(root / "state")
        self.log = jd.STATE / "timeline" / "messages.jsonl"
        self.log.parent.mkdir(parents=True)
        km.NAMES = root / "names"
        km.NAMES.mkdir()
        km._msg_sum_cache.clear()
        km._names_entry_memo.clear()
        km._name_color_index[0] = None
        km._postal_index_memo[0] = None
        km._live_scope.names = km._live_scope.msgsum = None
        km._msg_summaries = _REAL_MSG_SUMMARIES
        self.subs, self.keys = {}, {}           # sid -> its submap, sid -> its key: what a scan and a stat would see
        km._sessions = lambda now: [{"sid": sid, "path": "/nonexistent/" + sid} for sid in self.subs]
        km._msg_sum_key = lambda s: self.keys[s["sid"]]
        km._msg_sum_scan_session = lambda sid, path, now: dict(self.subs[sid])
        self.reads = [0]

    def name(self, sid, *fields):
        km._atomic_write(km.NAMES / sid, "\t".join(fields) + "\n")

    def captions(self, sid, sub):
        """The session's submap moves (a new key, so the union rescans it), or it joins discovery."""
        self.subs[sid] = dict(sub)
        self.keys[sid] = self.keys.get(sid, 0) + 1

    def row(self, **r):
        with open(self.log, "a") as f:
            f.write(json.dumps(r) + "\n")

    def test_names_snapshot_returns_a_new_dict_per_call_and_never_edits_one_it_returned(self):
        held = []

        def take(why):
            snap = km._names_snapshot()
            for old, copy, old_why in held:
                self.assertIsNot(snap, old, "%s: a new dict, not the one returned at %r" % (why, old_why))
                self.assertEqual(old, copy, "%s: the snapshot returned at %r still holds what it held" % (why, old_why))
            held.append((snap, {k: list(v) for k, v in snap.items()}, why))
            return snap
        self.name(PEER, "api", "/tmp/notes-api", "#abcdef")
        self.name(OTHER_A, "tests", "/tmp/notes-api", "#123456")
        self.assertEqual(take("the first call"), {PEER: ["api", "/tmp/notes-api", "#abcdef"],
                                                  OTHER_A: ["tests", "/tmp/notes-api", "#123456"]})
        take("the registry unchanged")
        self.name(OTHER_A, "tests", "/tmp/notes-api", "#654321")
        take("the recipient recoloured")
        self.name(PEER, "api-v2", "/tmp/notes-api", "#abcdef")
        take("the sender renamed")
        (km.NAMES / OTHER_A).unlink()
        self.assertEqual(take("an entry removed"), {PEER: ["api-v2", "/tmp/notes-api", "#abcdef"]})
        take("the registry unchanged again")

    def test_msg_summaries_publishes_a_new_union_per_change_and_never_edits_one_it_published(self):
        held = []

        def publish(why):
            union = km._msg_summaries()
            for old, copy, old_why in held:
                self.assertIsNot(union, old, "%s: a new union, not the one published at %r" % (why, old_why))
                self.assertEqual(old, copy, "%s: the union published at %r still holds what it held" % (why, old_why))
            held.append((union, dict(union), why))
            return union
        self.captions(SID_A, {"m1": "api: asked for the schema"})
        publish("the first call")
        self.captions(SID_A, {"m1": "api: sent the schema"})
        publish("a caption changed")
        self.captions(PEER, {"m2": "web: asked for the tests"})
        publish("a session joined discovery")
        self.captions(SID_A, {"m1": "api: sent the schema and the tests"})
        publish("a caption changed again")
        del self.subs[PEER], self.keys[PEER]
        last = publish("a session left discovery")
        self.assertEqual(last, {"m1": "api: sent the schema and the tests"})
        self.assertIs(km._msg_summaries(), last, "unchanged inputs return the published union itself (the memo's hit)")

    def test_the_real_producers_feed_the_postal_memo_and_every_tail_equals_an_unmemoized_check(self):
        """Pusher-shaped cycles over the real producers: each cycle takes a new snapshot (_names_snapshot) as its
        names scope and opens an empty caption slot, which the real union fills, and drops both after (the
        pusher's finally). Every tail equals, by repr, an unmemoized check (a copy of the record made of its
        build-time fields, the by-name colour read by the linear scan), and the colour index answers as the scan
        in every cycle."""
        self.row(ev="sent", id="m1", from_id=PEER, to_id=SID_A, body="the schema?", t=1)
        self.name(PEER, "api", "/tmp/notes-api", "#abcdef")
        self.name(OTHER_A, "tests", "/tmp/notes-api", "#123456")
        self.captions(SID_A, {"m1": "api: asked for the schema"})
        cards = [_CountingCard(self.reads, kind="postal-service", direction="in", mid="m1", peer="api"),
                 _CountingCard(self.reads, kind="postal-service", direction="out", peer="tests")]
        km._chat_dep_scope.deps = None
        km._live_scope.msgsum = [km._MSGSUM_UNSET]
        rec = km._chat_build_deps(SID_A, {"events": list(cards)})
        km._live_scope.msgsum = None

        def cycle(why):
            km._live_scope.names = km._names_snapshot()
            km._live_scope.msgsum = [km._MSGSUM_UNSET]
            try:
                before = self.reads[0]
                got = km._chat_sig_deps(SID_A, rec)
                walked = self.reads[0] - before
                by_name = km._name_color_by_name
                km._name_color_by_name = lambda name: _scan_color(km._live_scope.names, name)
                try:
                    ref = km._chat_sig_deps(SID_A, {k: rec[k] for k in _RECORD_KEYS})
                finally:
                    km._name_color_by_name = by_name
                self.assertEqual(repr(got), repr(ref), why)
                for nm in ("api", "api-v2", "tests", "docs"):
                    self.assertEqual(km._name_color_by_name(nm), _scan_color(km._live_scope.names, nm),
                                     "%s: the colour of %r" % (why, nm))
                return got, walked
            finally:
                km._live_scope.names = km._live_scope.msgsum = None
        first, walked = cycle("the first check")
        self.assertEqual(walked, 2, "the first check walks both cards")
        seen = [first]
        tail, walked = cycle("nothing moved")
        self.assertEqual((tail, walked), (first, 0), "nothing moved: the memo hits on the real producers' objects")
        self.captions(SID_A, {"m1": "api: sent the schema"})
        seen.append(cycle("a caption changed in the union")[0])
        self.name(OTHER_A, "tests", "/tmp/notes-api", "#654321")
        seen.append(cycle("the recipient recoloured")[0])
        self.name(PEER, "api-v2", "/tmp/notes-api", "#abcdef")
        seen.append(cycle("the sender renamed")[0])
        self.assertEqual(len({repr(t) for t in seen}), 4, "each move moved the tail (the pin compares something)")


# -- the cards' four fields: a rule over the kernel's writers (the closing check of review round 1, 2026-10-07) ----------
CARD_FIELDS = frozenset(("kind", "mid", "direction", "peer"))   # what _postal_card_deps reads from each card
CARD_WRITE_FORMS = frozenset(("assign", "augassign", "for", "with", "del", "update", "setdefault", "pop", "setitem",
                              "delitem", "ior"))
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef, ast.Module)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
_STORE_FORMS = ((ast.Assign, "assign"), (ast.AnnAssign, "assign"), (ast.AugAssign, "augassign"), (ast.For, "for"),
                (ast.AsyncFor, "for"), (ast.comprehension, "for"), (ast.withitem, "with"))
_METHOD_WRITES = {"update": "update", "setdefault": "setdefault", "pop": "pop", "__setitem__": "setitem",
                  "__delitem__": "delitem", "__ior__": "ior"}
_OPERATOR_WRITES = {"setitem": "setitem", "__setitem__": "setitem", "delitem": "delitem", "__delitem__": "delitem",
                    "ior": "ior", "__ior__": "ior"}
_DEPTH = 8                                       # how many steps deep a key is followed (a name to its binding is one)
# The forms the census refuses whatever their key: a writer it does not read as a write, each one syntactic check that
# kernel.py's tree meets nowhere (measured at 0 when the refusals were added, 2026-10-07).
_AS_VALUE = "unrecognised: a writer not called directly"
_BY_GETATTR = "unrecognised: a writer reached by getattr"
_THROUGH_TYPE = "unrecognised: a writer reached through the type"
_INIT = "unrecognised: __init__ other than through super()"
_STARRED = "unrecognised: a * or ** argument to a writer"
CARD_REFUSED_FORMS = frozenset((_AS_VALUE, _BY_GETATTR, _THROUGH_TYPE, _INIT, _STARRED))


def _links(chain):
    """(node, the node's own chain) for each node above a node, innermost first. A chain is (parent, parent's chain), so
    the census's walk keeps each node's ancestors without writing anything on the shared tree."""
    while chain is not None:
        yield chain
        chain = chain[1]


def _store_names(node):
    return [n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)]


def _is_super(expr):
    return isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "super"


def _through_type(expr):
    """type(x) or x.__class__: a writer read off one is the class's, called with the dict as an argument."""
    return ((isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "type")
            or (isinstance(expr, ast.Attribute) and expr.attr == "__class__"))


class _CardWriteReader:
    """The census's reader over one parsed module (CardFieldWriters says what it reads). Read-only over the tree, as
    tests/parse_cache.py requires of every consumer of a shared tree: ancestors travel with each node in the walk, and the
    bindings of each scope it reads are kept in its own table for the life of one read."""

    def __init__(self, tree):
        self.tree = tree
        self.scopes = {}                         # id(scope) -> {name: [(how, expression, its chain)]}
        self.operator_modules, self.operator_names = set(), {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.operator_modules |= {a.asname or a.name for a in node.names if a.name == "operator"}
            elif isinstance(node, ast.ImportFrom) and node.module == "operator":
                for a in node.names:
                    if a.name in _OPERATOR_WRITES:
                        self.operator_names[a.asname or a.name] = _OPERATOR_WRITES[a.name]

    def records(self):
        """(function, target, field, form, the write's node) for each write of a card field, in the walk's order."""
        out, stack = [], [(self.tree, None)]
        while stack:
            node, chain = stack.pop()
            here = (node, chain)
            stack.extend((child, here) for child in ast.iter_child_nodes(node))
            for target, keys, form in self.writes(node, chain):
                fields = sorted(k for k in keys if k in CARD_FIELDS)
                if form.startswith("unrecognised"):      # a write the reader does not model: reported whatever its key
                    fields = fields or ["?"]
                out += [(self.function(chain), ast.unparse(target), f, form, node) for f in fields]
        return out

    def sites(self):
        """(function, target, field, form, line) for each write of a card field, sorted."""
        return sorted(r[:4] + (getattr(r[4], "lineno", 0),) for r in self.records())

    def writes(self, node, chain):
        here = (node, chain)
        called = chain is not None and isinstance(chain[0], ast.Call) and chain[0].func is node
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del)):
            yield node.value, self.values(node.slice, here), self.store_form(node, chain)
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.BitOr):
            yield node.target, self.mapping_keys(node.value, here), "ior"
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            if node.attr == "__init__" and not _is_super(node.value):
                dict_first = called and chain[0].args and isinstance(node.value, ast.Name) and node.value.id == "dict"
                yield (chain[0].args[0] if dict_first else node.value), set(), _INIT
            elif not called and node.attr in _METHOD_WRITES:
                yield node.value, set(), _AS_VALUE
            elif (not called and node.attr in _OPERATOR_WRITES and isinstance(node.value, ast.Name)
                  and node.value.id in self.operator_modules):
                yield node, set(), _AS_VALUE
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in self.operator_names:
            if not called:
                yield node, set(), _AS_VALUE
        elif isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == "getattr" and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value in tuple(_METHOD_WRITES) + ("__init__",)):
                yield node.args[0], set(), _BY_GETATTR
                return
            if isinstance(f, ast.Attribute) and f.attr in _METHOD_WRITES and _through_type(f.value):
                yield f.value, set(), _THROUGH_TYPE
                return
            form, target, args = self.call_form(node)
            if form is None or target is None:
                return
            if any(isinstance(a, ast.Starred) for a in node.args) or any(kw.arg is None for kw in node.keywords):
                yield target, set(), _STARRED
                return
            if form == "update":
                keys = {kw.arg for kw in node.keywords}
                for a in args:
                    keys |= self.mapping_keys(a, here)
            elif form == "ior":
                keys = self.mapping_keys(args[0], here) if args else set()
            else:
                keys = self.values(args[0], here) if args else set()
            yield target, keys, form

    def call_form(self, node):
        """(form, the dict written, the arguments after it) for a direct call of a writer, else Nones."""
        f, args = node.func, node.args
        if (isinstance(f, ast.Attribute) and f.attr in _OPERATOR_WRITES and isinstance(f.value, ast.Name)
                and f.value.id in self.operator_modules):            # operator.__setitem__ too: before the method road
            return _OPERATOR_WRITES[f.attr], (args[0] if args else None), args[1:]
        if isinstance(f, ast.Attribute) and f.attr in _METHOD_WRITES:
            if isinstance(f.value, ast.Name) and f.value.id == "dict":       # dict.update(d, ...): d is the first argument
                return _METHOD_WRITES[f.attr], (args[0] if args else None), args[1:]
            return _METHOD_WRITES[f.attr], f.value, args
        if isinstance(f, ast.Name) and f.id in self.operator_names:
            return self.operator_names[f.id], (args[0] if args else None), args[1:]
        return None, None, ()

    @staticmethod
    def store_form(node, chain):
        if isinstance(node.ctx, ast.Del):
            return "del"
        for up, _up_chain in _links(chain):
            if isinstance(up, (ast.Tuple, ast.List, ast.Starred)):
                continue
            for kind, form in _STORE_FORMS:
                if isinstance(up, kind):
                    return form
            return "unrecognised under %s" % type(up).__name__
        return "unrecognised at the top"

    @staticmethod
    def function(chain):
        names = [getattr(up, "name", "<lambda>") for up, _c in _links(chain)
                 if isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))]
        return ".".join(reversed(names)) or "<module>"

    def values(self, expr, chain, depth=0):
        """The str values the key `expr` can take that the census can name: a constant, either arm of a conditional, a
        name bound in its scope to one (or by a for loop or a comprehension over a literal of them, a name included).
        Anything else adds nothing: the stated limits."""
        if depth > _DEPTH:
            return set()
        here = (expr, chain)
        if isinstance(expr, ast.Constant):
            return {expr.value} if isinstance(expr.value, str) else set()
        if isinstance(expr, ast.IfExp):
            return self.values(expr.body, here, depth + 1) | self.values(expr.orelse, here, depth + 1)
        if isinstance(expr, ast.Name):
            out = set()
            for how, value, where in self.bound(expr.id, chain):
                out |= (self.values if how == "value" else self.elements)(value, where, depth + 1)
            return out
        return set()

    def elements(self, expr, chain, depth=0):
        """What iterating `expr` gives, where the census can name it: a literal tuple, list, set or dict (its keys), a
        set(), frozenset(), tuple(), list() or sorted() of one, a name bound to one."""
        if depth > _DEPTH:
            return set()
        here = (expr, chain)
        if isinstance(expr, (ast.Tuple, ast.List, ast.Set)):
            out = set()
            for e in expr.elts:
                out |= self.values(e, here, depth + 1)
            return out
        if isinstance(expr, ast.Dict):
            return self.mapping_keys(expr, chain, depth + 1)
        if (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and len(expr.args) == 1
                and expr.func.id in ("set", "frozenset", "tuple", "list", "sorted")):
            return self.elements(expr.args[0], here, depth + 1)
        if isinstance(expr, ast.Name):
            out = set()
            for how, value, where in self.bound(expr.id, chain):
                if how == "value":
                    out |= self.elements(value, where, depth + 1)
            return out
        return set()

    def mapping_keys(self, expr, chain, depth=0):
        """The keys a mapping argument writes, where the census can name them: a dict literal (a splatted part
        included), a dict comprehension, a dict() call, a literal list of pairs or a comprehension of pairs, a union of
        these, a name bound to one."""
        if depth > _DEPTH:
            return set()
        here, out = (expr, chain), set()
        if isinstance(expr, ast.Dict):
            for k, v in zip(expr.keys, expr.values):
                out |= self.mapping_keys(v, here, depth + 1) if k is None else self.values(k, here, depth + 1)
        elif isinstance(expr, ast.DictComp):
            out = self.values(expr.key, here, depth + 1)
        elif isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "dict":
            for a in expr.args:
                out |= self.mapping_keys(a, here, depth + 1)
            for kw in expr.keywords:
                out |= {kw.arg} if kw.arg is not None else self.mapping_keys(kw.value, here, depth + 1)
        elif isinstance(expr, (ast.List, ast.Tuple, ast.Set)):
            for e in expr.elts:
                if isinstance(e, (ast.Tuple, ast.List)) and e.elts:
                    out |= self.values(e.elts[0], (e, here), depth + 1)
        elif isinstance(expr, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            if isinstance(expr.elt, (ast.Tuple, ast.List)) and expr.elt.elts:
                out = self.values(expr.elt.elts[0], (expr.elt, here), depth + 1)
        elif isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.BitOr):
            out = self.mapping_keys(expr.left, here, depth + 1) | self.mapping_keys(expr.right, here, depth + 1)
        elif isinstance(expr, ast.Name):
            for how, value, where in self.bound(expr.id, chain):
                if how == "value":
                    out |= self.mapping_keys(value, where, depth + 1)
        return out

    def bound(self, name, chain):
        """(how, expression, its chain) for each binding of `name` the census reads where `chain` sees it: "value" for
        an assignment's value, "iter" for the iterable of a for loop or a comprehension. The innermost comprehension or
        scope that binds the name answers, with every binding it holds (any one the census can read makes a site); a
        class body only for code directly in it; a global or nonlocal declaration adds the outer scopes' bindings."""
        innermost, read = True, []
        for up, up_chain in _links(chain):
            if isinstance(up, _COMPREHENSIONS):
                found = [b[1:] for b in self.comprehension_bindings(up, up_chain) if b[0] == name]
                if found:
                    return read + [b for b in found if b[0] in ("value", "iter")]
                continue
            if not isinstance(up, _SCOPES):
                continue
            if isinstance(up, ast.ClassDef) and not innermost:
                continue
            innermost = False
            entries = self.scope_bindings(up, up_chain).get(name)
            if entries:
                read += [e for e in entries if e[0] in ("value", "iter")]
                if not any(e[0] == "outer" for e in entries):
                    return read
        return read

    @staticmethod
    def comprehension_bindings(comp, comp_chain):
        here, out = (comp, comp_chain), []
        for gen in comp.generators:
            if isinstance(gen.target, ast.Name):
                out.append((gen.target.id, "iter", gen.iter, (gen, here)))
            else:
                out += [(n, "other", None, None) for n in _store_names(gen.target)]
        return out

    def scope_bindings(self, scope, scope_chain):
        """{name: [(how, expression, its chain)]} for every binding whose scope is `scope`, read once per scope."""
        table = self.scopes.get(id(scope))
        if table is None:
            table = self.scopes[id(scope)] = _scope_table(scope, scope_chain)
        return table


def _scope_table(scope, scope_chain):
    """{name: [(how, expression, its chain)]} for every binding whose scope is `scope`: "param", "value" (an
    assignment's value), "iter" (a for loop's iterable), "outer" (a global or nonlocal declaration) or "other"."""
    table = {}

    def add(n, how, value=None, where=None):
        table.setdefault(n, []).append((how, value, where))
    args = getattr(scope, "args", None)
    if args is not None:
        for a in args.posonlyargs + args.args + args.kwonlyargs + [args.vararg, args.kwarg]:
            if a is not None:
                add(a.arg, "param")
    here = (scope, scope_chain)
    body = scope.body if isinstance(scope.body, list) else [scope.body]
    stack = [(child, here) for child in body]
    while stack:
        node, chain = stack.pop()
        at = (node, chain)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            add(node.name, "other")
            continue                         # a scope of its own
        if isinstance(node, ast.Lambda):
            continue                         # a scope of its own; a comprehension is walked: := in one binds here
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.For, ast.AsyncFor)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.iter if isinstance(node, (ast.For, ast.AsyncFor)) else node.value
            for t in targets:
                if isinstance(t, ast.Name) and value is not None:
                    add(t.id, "iter" if isinstance(node, (ast.For, ast.AsyncFor)) else "value", value, at)
                elif not isinstance(t, ast.Name):
                    for n in _store_names(t):
                        add(n, "other")
        elif isinstance(node, ast.NamedExpr):
            add(node.target.id, "value", node.value, at)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            add(node.target.id, "other")
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            for n in _store_names(node.optional_vars):
                add(n, "other")
        elif isinstance(node, ast.ExceptHandler) and node.name:
            add(node.name, "other")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                add((a.asname or a.name).split(".")[0], "other")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            for n in node.names:
                add(n, "outer")
        elif getattr(node, "name", None) and type(node).__name__ in ("MatchAs", "MatchStar"):
            add(node.name, "other")
        elif getattr(node, "rest", None) and type(node).__name__ == "MatchMapping":
            add(node.rest, "other")
        stack.extend((child, at) for child in ast.iter_child_nodes(node))
    return table


def _card_field_writes(tree):
    """The census over `tree`: (function, target, field, form, line) for each in-place write of a card field it reads."""
    return _CardWriteReader(tree).sites()


def _defs_in(scope):
    """The function and class definitions whose nearest enclosing scope is `scope`."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield n
        elif not isinstance(n, (ast.Lambda,) + _COMPREHENSIONS):
            stack.extend(ast.iter_child_nodes(n))


def _definition(tree, qualname):
    """The definition at a dotted name through enclosing functions and classes (the census's `function`), or None."""
    node = tree
    for part in qualname.split("."):
        node = next((d for d in _defs_in(node) if d.name == part), None)
        if node is None:
            return None
    return node


def _own_nodes(func):
    """Every node of a function's body outside the functions, classes and lambdas defined in it."""
    stack = list(func.body)
    while stack:
        n = stack.pop()
        yield n
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(n))


def _parents_of(func):
    parent = {}
    for n in ast.walk(func):
        for c in ast.iter_child_nodes(n):
            parent[id(c)] = n
    return parent


def _nearest_binding(parent, node, name, stop):
    """The nearest binding of `name` that reaches `node`: the nearest statement before it in its block that binds it,
    else an enclosing for loop, with or except clause that binds it, else the same one block out, up to `stop` (a
    function), or None. A statement that binds the name only inside it (in a nested block or a nested function) is
    returned as the binding, and no witness accepts such a statement."""
    cur = node
    while cur is not stop:
        owner = parent.get(id(cur))
        if owner is None:
            return None
        for field in ("body", "orelse", "finalbody"):
            block = getattr(owner, field, None)
            at = next((i for i, s in enumerate(block) if s is cur), None) if isinstance(block, list) else None
            if at is not None:
                for prev in reversed(block[:at]):
                    if name in _store_names(prev):
                        return prev
        if ((isinstance(owner, (ast.For, ast.AsyncFor)) and name in _store_names(owner.target)
             and any(cur is s for s in owner.body + owner.orelse))
                or (isinstance(owner, (ast.With, ast.AsyncWith)) and any(cur is s for s in owner.body) and any(
                    i.optional_vars is not None and name in _store_names(i.optional_vars) for i in owner.items))
                or (isinstance(owner, ast.ExceptHandler) and owner.name == name)):
            return owner
        cur = owner
    return None


def _fresh_dict(expr):
    """A new dict: a literal, a dict comprehension, a dict() call, x.copy(), copy.copy(x) or copy.deepcopy(x)."""
    if isinstance(expr, (ast.Dict, ast.DictComp)):
        return True
    if isinstance(expr, ast.Call):
        f = expr.func
        return ((isinstance(f, ast.Name) and f.id == "dict")
                or (isinstance(f, ast.Attribute) and f.attr == "copy" and not expr.args)
                or (isinstance(f, ast.Attribute) and f.attr in ("copy", "deepcopy") and isinstance(f.value, ast.Name)
                    and f.value.id == "copy"))
    return False


def _new_dict_binding(stmt, name):
    """Whether a statement is `name = <a new dict>`."""
    return (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)
            and stmt.targets[0].id == name and _fresh_dict(stmt.value))


def _binding_text(stmt):
    return ("line %d, %s" % (stmt.lineno, ast.unparse(stmt).split("\n")[0][:80])) if stmt is not None else "none"


def _uses_problems(func, name, ok):
    """A problem for each use of `name` anywhere in the function, nested scopes included, that `ok(use, the node
    holding it, the function's parent map)` does not accept."""
    parent = _parents_of(func)
    return ["line %d: %s used in %s" % (n.lineno, name, ast.unparse(parent[id(n)]).split("\n")[0][:80])
            for n in ast.walk(func) if isinstance(n, ast.Name) and n.id == name and not ok(n, parent[id(n)], parent)]


def _rows_use_ok(n, up, parent):
    """A use of a list of rows that cannot add a row to it: a binding `name = ...` (followed where it is the nearest),
    len() or sorted() of it, a slice or an item read, the iterable of a loop, or a value returned."""
    if isinstance(n.ctx, ast.Store):
        return isinstance(up, ast.Assign) and len(up.targets) == 1 and up.targets[0] is n
    if isinstance(up, ast.Call) and isinstance(up.func, ast.Name) and up.func.id in ("len", "sorted"):
        return any(a is n for a in up.args)
    if isinstance(up, ast.Subscript):
        return up.value is n and isinstance(up.ctx, ast.Load)
    if isinstance(up, (ast.For, ast.AsyncFor, ast.comprehension)):
        return up.iter is n
    if isinstance(up, ast.Tuple):
        up = parent.get(id(up))
    return isinstance(up, ast.Return)


def _dict_use_ok(n, up, parent):
    """A use of a dict of rows that cannot put into it anything but a new dict: its binding `name = {}`, a read (d[k],
    d.get, d.values, d.keys, d.items called), or a store `d[k] = <a new dict>`."""
    if isinstance(n.ctx, ast.Store):
        return (isinstance(up, ast.Assign) and len(up.targets) == 1 and up.targets[0] is n
                and isinstance(up.value, ast.Dict) and not up.value.keys)
    if isinstance(up, ast.Subscript) and up.value is n:
        stmt = parent.get(id(up))
        return isinstance(up.ctx, ast.Load) or (isinstance(up.ctx, ast.Store) and isinstance(stmt, ast.Assign)
                                                and len(stmt.targets) == 1 and stmt.targets[0] is up
                                                and _fresh_dict(stmt.value))
    if isinstance(up, ast.Attribute) and up.value is n and up.attr in ("get", "values", "keys", "items"):
        call = parent.get(id(up))
        return isinstance(call, ast.Call) and call.func is up
    return False


def _rows_problems(func, parent, expr, at, depth=0):
    """Problems with a loop's iterable as a list of new dicts built in the function: a name whose nearest binding
    before `at` is `name = ...`, a slice or a sorted() of one, down to d.values() of a dict bound once as {} and filled
    with new dicts only; each list and the dict used only in ways that add nothing else."""
    if depth > _DEPTH:
        return ["the iterable is followed more than %d steps" % _DEPTH]
    if isinstance(expr, ast.Name):
        prev = _nearest_binding(parent, at, expr.id, func)
        if not (isinstance(prev, ast.Assign) and len(prev.targets) == 1 and isinstance(prev.targets[0], ast.Name)):
            return ["the nearest binding of %s is %s, not `%s = ...`" % (expr.id, _binding_text(prev), expr.id)]
        return _uses_problems(func, expr.id, _rows_use_ok) + _rows_problems(func, parent, prev.value, prev, depth + 1)
    if isinstance(expr, ast.Subscript) and isinstance(expr.slice, ast.Slice):
        return _rows_problems(func, parent, expr.value, at, depth + 1)
    if (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "sorted"
            and len(expr.args) == 1):
        return _rows_problems(func, parent, expr.args[0], at, depth + 1)
    if (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute) and expr.func.attr == "values"
            and isinstance(expr.func.value, ast.Name) and not expr.args and not expr.keywords):
        d = expr.func.value.id
        held = _scope_table(func, None).get(d, [])
        once = len(held) == 1 and held[0][0] == "value" and isinstance(held[0][1], ast.Dict) and not held[0][1].keys
        return ([] if once else ["%s is bound other than once, as {} (%s)" % (d, ", ".join(h[0] for h in held))]) + (
            _uses_problems(func, d, _dict_use_ok))
    return ["the loop runs over %s, which the witness does not follow to the values of a dict of new dicts"
            % ast.unparse(expr)[:80]]


def _copy_witness(func, target, writes):
    """Problems with a row whose target is a new dict made in the function: each write's nearest earlier binding of
    the target is `target = <a new dict>` (a literal, a dict() call or a copy)."""
    parent, problems = _parents_of(func), []
    for n in writes:
        prev = _nearest_binding(parent, n, target, func)
        if not _new_dict_binding(prev, target):
            problems.append("line %d: the nearest earlier binding of %s is %s, not a new dict" % (
                n.lineno, target, _binding_text(prev)))
    return problems


def _loop_witness(func, target, writes):
    """Problems with a row whose target is a loop's row: each write's nearest binding of the target is a for loop
    over a list the function built from the values of a dict it fills with new dicts only (_rows_problems)."""
    parent, problems = _parents_of(func), []
    for n in writes:
        loop = _nearest_binding(parent, n, target, func)
        if not (isinstance(loop, (ast.For, ast.AsyncFor)) and isinstance(loop.target, ast.Name)
                and loop.target.id == target):
            problems.append("line %d: the nearest binding of %s is %s, not a for loop whose target is %s" % (
                n.lineno, target, _binding_text(loop), target))
            continue
        problems += ["line %d: %s" % (n.lineno, p) for p in _rows_problems(func, parent, loop.iter, loop)]
    return problems


def _producer_witness(tree, func, target, writes, producer):
    """Problems with a row whose target a producer function returns: each write's nearest earlier binding of the
    target is `target, ... = producer(...)`, and every return of the producer hands back first a name whose nearest
    binding there is `name = <a new dict>`."""
    parent, problems = _parents_of(func), []
    for n in writes:
        prev = _nearest_binding(parent, n, target, func)
        unpack = (isinstance(prev, ast.Assign) and len(prev.targets) == 1 and isinstance(prev.targets[0], ast.Tuple)
                  and prev.targets[0].elts and isinstance(prev.targets[0].elts[0], ast.Name)
                  and prev.targets[0].elts[0].id == target and isinstance(prev.value, ast.Call)
                  and isinstance(prev.value.func, ast.Name) and prev.value.func.id == producer)
        if not unpack:
            problems.append("line %d: the nearest earlier binding of %s is %s, not `%s, ... = %s(...)`" % (
                n.lineno, target, _binding_text(prev), target, producer))
    fn = _definition(tree, producer)
    rets = [r for r in _own_nodes(fn) if isinstance(r, ast.Return)] if fn is not None else []
    if not rets:
        problems.append("%s is gone, or never returns" % producer)
    fparent = _parents_of(fn) if fn is not None else {}
    for r in rets:
        first = r.value.elts[0] if isinstance(r.value, ast.Tuple) and r.value.elts else None
        name = first.id if isinstance(first, ast.Name) else None
        if not (name and _new_dict_binding(_nearest_binding(fparent, r, name, fn), name)):
            problems.append("line %d: %s returns %s first, not a name bound to a new dict" % (
                r.lineno, producer, ast.unparse(first) if first is not None else "something other than a tuple"))
    return problems


def _module_witness(tree, function, target):
    """Problems with a row whose target is a module's dict: the name is bound once at module level, to a dict literal;
    nothing declares it global; and neither the function nor a scope around it binds the name."""
    held = _scope_table(tree, None).get(target, [])
    problems = [] if (len(held) == 1 and held[0][0] == "value" and isinstance(held[0][1], ast.Dict)) else [
        "%s is bound at module level other than once, to a dict literal (%s)" % (
            target, ", ".join(h[0] for h in held) or "unbound")]
    problems += ["line %d: a global declaration of %s" % (n.lineno, target) for n in ast.walk(tree)
                 if isinstance(n, ast.Global) and target in n.names]
    parts = function.split(".")
    for i in range(1, len(parts) + 1):
        scope = _definition(tree, ".".join(parts[:i]))
        if scope is not None and target in _scope_table(scope, None):
            problems.append("%s binds %s itself" % (".".join(parts[:i]), target))
    return problems


def _fresh_card_witness(tree, function, producers):
    """(calls read, problems) for a listed write into a function's first parameter that relies on every caller handing
    it a card just built: each use of the function is a call whose first argument's nearest earlier binding is a call
    of one of `producers`, the parameter is never rebound, and every return of each producer is a dict literal or
    None."""
    outer_name, _dot, inner_name = function.rpartition(".")
    outer, inner = _definition(tree, outer_name), _definition(tree, function)
    if outer is None or inner is None or not inner.args.args:
        return 0, ["%s is gone, or takes no card" % function]
    param, problems, calls = inner.args.args[0].arg, [], 0
    problems += ["line %d: %s rebinds its card %s" % (n.lineno, inner_name, param) for n in _own_nodes(inner)
                 if isinstance(n, ast.Name) and n.id == param and isinstance(n.ctx, ast.Store)]
    parent = _parents_of(outer)
    for n in ast.walk(outer):
        if not (isinstance(n, ast.Name) and n.id == inner_name):
            continue
        call = parent.get(id(n))
        if not (isinstance(call, ast.Call) and call.func is n and call.args and isinstance(call.args[0], ast.Name)):
            problems.append("line %d: %s used other than as a call on a named card" % (n.lineno, inner_name))
            continue
        calls += 1
        card = call.args[0].id
        prev = _nearest_binding(parent, call, card, outer)
        if not (isinstance(prev, ast.Assign) and len(prev.targets) == 1 and isinstance(prev.value, ast.Call)
                and isinstance(prev.value.func, ast.Name) and prev.value.func.id in producers):
            problems.append("line %d: %s(%s, ...) where %s's nearest earlier binding is %s, not a call of %s" % (
                n.lineno, inner_name, card, card, ("line %d" % prev.lineno) if prev else "none", " or ".join(producers)))
    for p in producers:
        fn = _definition(tree, p)
        rets = [r for r in _own_nodes(fn) if isinstance(r, ast.Return)] if fn is not None else []
        if not any(isinstance(r.value, ast.Dict) for r in rets) or any(
                not (r.value is None or isinstance(r.value, ast.Dict)
                     or (isinstance(r.value, ast.Constant) and r.value.value is None)) for r in rets):
            problems.append("%s: not every return is a dict literal or None (or it is gone)" % p)
    return calls, problems


_WITNESSES = ("copy", "loop", "producer", "module", "fresh")


def _row_witness(tree, records, row):
    """(writes read, problems) for one row of CARD_FIELD_WRITERS: its witness run over every write that `records`,
    the census's records over `tree`, attributes to the row."""
    function, target, field, form, _count, witness, _why = row
    writes = [r[4] for r in records if r[:4] == (function, target, field, form)]
    func, kind = _definition(tree, function), (witness or (None,))[0]
    if kind not in _WITNESSES:
        problems = ["no witness" if kind is None else "no witness named %r" % (kind,)]
    elif func is None:
        problems = ["%s is gone" % function]
    elif kind == "copy":
        problems = _copy_witness(func, target, writes)
    elif kind == "loop":
        problems = _loop_witness(func, target, writes)
    elif kind == "producer":
        problems = _producer_witness(tree, func, target, writes, witness[1])
    elif kind == "module":
        problems = _module_witness(tree, function, target)
    else:
        calls, problems = _fresh_card_witness(tree, function, witness[1])
        if func.args.args and func.args.args[0].arg != target:
            problems.append("%s's card is its parameter %s, not %s" % (function, func.args.args[0].arg, target))
        if not calls:
            problems.append("%s has no caller the witness reads" % function)
    return len(writes), problems


# The legal set: every in-place write of a card field in kernel/kernel.py, derived 2026-10-07 at the census's first
# head (11 sites). Each row: (function, target, field, form, count, witness, why). A row is construction (a NEW dict is
# being built, so no existing card is edited) or a dict that is never a postal card, and every row's witness checks
# that reason by AST, over every write the census attributes to the row:
# - "copy": each write's nearest earlier binding of the target is `target = <a new dict>`.
# - "loop": the target is a for loop's row, over a list the function built from the values of a dict it binds once as
#   {} and fills with new dicts only.
# - "producer": the target is unpacked first from a call of the named function, whose every return hands back first
#   a name bound there to a new dict.
# - "module": the target is a module's dict, bound once at module level as a literal, never declared global, and not
#   bound in the function.
# - "fresh": every caller hands the function a card one of the named producers has just built.
CARD_FIELD_WRITERS = (
    ("_hydrate_postal.enrich_out", "card", "mid", "assign", 1, ("fresh", ("_postal_out_card", "_cli_send_card")),
     "construction: the outgoing card _postal_out_card or _cli_send_card has just returned as a dict literal, joined"
     " to its log row before _hydrate_postal appends it"),
    ("_hydrate_postal", "ev", "mid", "assign", 1, ("copy",),
     "construction, and not a card: `ev = dict(ev)` makes a new dict first, and the event is one whose message ids did"
     " not all resolve (a user event, or a mail reader's tool event), never kind postal-service"),
    ("_handoff_card_fields", "badge", "peer", "update", 1, ("copy",),
     "not a card: the handoffTo badge, a dict literal built above it in the same function"),
    ("_kind_read", "_KIND_CACHE", "kind", "assign", 3, ("module",),
     "not a card: the module's mtime cache of the login's kind word"),
    ("_slice_body", "body", "kind", "update", 2, ("copy",),
     "not a card: the file-slice response body, a dict literal built in the same function"),
    ("_artifacts_items", "it", "kind", "assign", 1, ("loop",),
     "not a card: an artifacts-pane row, a dict literal built in the same function"),
    ("Handler.do_POST", "rec", "kind", "assign", 1, ("copy",),
     "not a card: a stored-login record, a dict literal built a few lines above"),
    ("Handler._ws", "client", "kind", "assign", 1, ("producer", "_new_ws_client"),
     "not a card: the websocket client's registry row, the dict _new_ws_client builds and returns first"),
)


def _in_f(*lines, params="c"):
    return "def f(%s):\n%s" % (params, "".join("    %s\n" % line for line in lines))


_PRODUCER = "def p(e):\n    if e:\n        return None\n    return {'kind': 'postal-service'}\n"


def _handed(*lines, inner=("card['mid'] = 1",), producer=_PRODUCER):
    return producer + "def o(events):\n    def inner(card, ev):\n%s%s" % (
        "".join("        %s\n" % line for line in inner), "".join("    %s\n" % line for line in lines))


def _rows(*middle, bind="d = {}", store="d[x] = {'path': x}", loop="for it in rows:",
          body=("    it['kind'] = 'other'",)):
    """f(xs) on the shape of _artifacts_items: a dict filled with new dicts, its values sorted and sliced into a list,
    a loop writing each row's kind."""
    return _in_f(bind, "for x in xs:", "    cur = d.get(x)", "    if cur is None:", "        " + store,
                 "rows = sorted(d.values(), key=len)", "capped = len(rows) > 5", "rows = rows[:5]", *middle, loop,
                 *body, "return rows, capped", params="xs")


_MAKER = "def mk(a):\n    row = {'a': a}\n    row['q'] = 1\n    return row, 2\n"


def _made(*lines, maker=_MAKER):
    return maker + _in_f(*lines, params="a")


# The witnesses over small sources: (what, source, the row read as (function, target, field, form, witness), holds).
# A case whose `what` starts with "limit:" holds where the reason is false: a known miss (the class docstring).
_W_COPY = ("f", "ev", "mid", "assign", ("copy",))
_W_UPDATE = ("f", "b", "peer", "update", ("copy",))
_W_LOOP = ("f", "it", "kind", "assign", ("loop",))
_W_PRODUCER = ("f", "client", "kind", "assign", ("producer", "mk"))
_W_MODULE = ("f", "CACHE", "kind", "assign", ("module",))
_W_FRESH = ("o.inner", "card", "mid", "assign", ("fresh", ("p",)))
CARD_WITNESS_CASES = (
    ("a dict() copy", _in_f("ev = dict(ev)", "ev['mid'] = 1", params="ev"), _W_COPY, True),
    ("a .copy()", _in_f("ev = ev.copy()", "ev['mid'] = 1", params="ev"), _W_COPY, True),
    ("a copy.copy()", _in_f("ev = copy.copy(ev)", "ev['mid'] = 1", params="ev"), _W_COPY, True),
    ("a splat into a new literal", _in_f("ev = {**ev}", "ev['mid'] = 1", params="ev"), _W_COPY, True),
    ("the copy in an enclosing block", _in_f("ev = dict(ev)", "if ev:", "    ev['mid'] = 1", params="ev"), _W_COPY,
     True),
    ("a copy made inside a loop over the same name", _in_f("for ev in evs:", "    ev = dict(ev)", "    ev['mid'] = 1",
                                                           params="evs"), _W_COPY, True),
    ("an alias, not a copy", _in_f("ev = ev", "ev['mid'] = 1", params="ev"), _W_COPY, False),
    ("no copy: the parameter itself", _in_f("ev['mid'] = 1", params="ev"), _W_COPY, False),
    ("a copy rebound before the write", _in_f("ev = dict(ev)", "ev = g(ev)", "ev['mid'] = 1", params="ev"), _W_COPY,
     False),
    ("a copy shadowed by a loop", _in_f("ev = dict(ev)", "for ev in evs:", "    ev['mid'] = 1", params="ev"), _W_COPY,
     False),
    ("a copy shadowed by a with", _in_f("ev = dict(ev)", "with g() as ev:", "    ev['mid'] = 1", params="ev"), _W_COPY,
     False),
    ("a copy shadowed by an except", _in_f("ev = dict(ev)", "try:", "    pass", "except E as ev:", "    ev['mid'] = 1",
                                           params="ev"), _W_COPY, False),
    ("a copy rebound in a branch before the write", _in_f("ev = dict(ev)", "if ev:", "    ev = g(ev)", "ev['mid'] = 1",
                                                          params="ev"), _W_COPY, False),
    ("an update of a new literal", _in_f("b = {'x': 1}", "b.update({'peer': 'api'})"), _W_UPDATE, True),
    ("update keywords on a dict() copy", _in_f("b = dict(c)", "b.update(peer='api')"), _W_UPDATE, True),
    ("an update of a dict it holds", _in_f("b = c[0]", "b.update(peer='api')"), _W_UPDATE, False),
    ("an update of the parameter", _in_f("b.update(peer='api')", params="b"), _W_UPDATE, False),
    ("an update after a rebinding", _in_f("b = {}", "b = g(c)", "b.update(peer='api')"), _W_UPDATE, False),
    ("limit: a new dict handed to a list, then written", _in_f("b = {'x': 1}", "c.append(b)", "b.update(peer='api')"),
     _W_UPDATE, True),
    ("a loop over the values of a dict of new dicts, through sorted() and a slice", _rows(), _W_LOOP, True),
    ("a loop over a parameter", _in_f("for it in xs:", "    it['kind'] = 'other'", params="xs"), _W_LOOP, False),
    ("a loop over the list and more", _rows(loop="for it in rows + xs:"), _W_LOOP, False),
    ("the row rebound inside the loop", _rows(body=("    it = xs[0]", "    it['kind'] = 'other'")), _W_LOOP, False),
    ("a row bound inside a loop over other rows", _rows(loop="for x in rows:", body=("    it = xs[0]",
                                                                                     "it['kind'] = 'other'")),
     _W_LOOP, False),
    ("a dict that also holds a row it was handed", _rows(store="d[x] = x"), _W_LOOP, False),
    ("a dict bound to one it was handed", _rows(bind="d = xs[0]"), _W_LOOP, False),
    ("a dict bound twice", _rows("d = {}"), _W_LOOP, False),
    ("a dict updated from elsewhere", _rows("d.update(xs[0])"), _W_LOOP, False),
    ("a dict handed to a call", _rows("fill(d)"), _W_LOOP, False),
    ("a list that gains a row before the loop", _rows("rows.append(xs[0])"), _W_LOOP, False),
    ("a list rebound to one it was handed", _rows("rows = xs"), _W_LOOP, False),
    ("a list extended in place", _rows("rows += xs"), _W_LOOP, False),
    ("a row unpacked from a producer whose first return is a new dict",
     _made("client, n = mk(a)", "client['kind'] = 'page'"), _W_PRODUCER, True),
    ("a row rebound after the unpack", _made("client, n = mk(a)", "client = a", "client['kind'] = 'page'"),
     _W_PRODUCER, False),
    ("a row unpacked from another call", _made("client, n = other(a)", "client['kind'] = 'page'"), _W_PRODUCER, False),
    ("the producer's second element", _made("n, client = mk(a)", "client['kind'] = 'page'"), _W_PRODUCER, False),
    ("a producer that returns a dict it was handed", _made("client, n = mk(a)", "client['kind'] = 'page'",
                                                           maker="def mk(a):\n    return a, 2\n"), _W_PRODUCER, False),
    ("a producer whose new dict is rebound before the return", _made(
        "client, n = mk(a)", "client['kind'] = 'page'",
        maker="def mk(a):\n    row = {'a': a}\n    row = a\n    return row, 2\n"), _W_PRODUCER, False),
    ("a producer with one return of a dict it holds", _made(
        "client, n = mk(a)", "client['kind'] = 'page'",
        maker="def mk(a):\n    if a:\n        return a['row'], 1\n    row = {}\n    return row, 2\n"), _W_PRODUCER, False),
    ("a module's dict bound once as a literal", "CACHE = {'kind': ''}\n" + _in_f("CACHE['kind'] = 'x'", params=""),
     _W_MODULE, True),
    ("a function that rebinds it under a global declaration", "CACHE = {'kind': ''}\n" + _in_f(
        "CACHE['kind'] = 'x'", params="") + "def g(c):\n    global CACHE\n    CACHE = c\n", _W_MODULE, False),
    ("the function binds the name itself", "CACHE = {'kind': ''}\n" + _in_f(
        "CACHE = held()", "CACHE['kind'] = 'x'", params=""), _W_MODULE, False),
    ("bound twice at module level", "CACHE = {}\nCACHE = held()\n" + _in_f("CACHE['kind'] = 'x'", params=""),
     _W_MODULE, False),
    ("bound to something other than a dict literal", "CACHE = held()\n" + _in_f("CACHE['kind'] = 'x'", params=""),
     _W_MODULE, False),
    ("a scope around the function binds it", "CACHE = {}\ndef o(c):\n    CACHE = c\n    def f():\n"
                                             "        CACHE['kind'] = 'x'\n",
     ("o.f", "CACHE", "kind", "assign", ("module",)), False),
    ("a card its producer has just built", _handed("for ev in events:", "    card = p(ev)", "    if card:",
                                                   "        inner(card, ev)"), _W_FRESH, True),
    ("a card the caller holds", _handed("for ev in events:", "    inner(ev, ev)"), _W_FRESH, False),
    ("a card rebound after its producer", _handed("for ev in events:", "    card = p(ev)", "    card = ev",
                                                  "    inner(card, ev)"), _W_FRESH, False),
    ("a use other than a call beside a good one", _handed("for ev in events:", "    card = p(ev)", "    inner(card, ev)",
                                                          "keep = inner"), _W_FRESH, False),
    ("the card rebound inside", _handed("for ev in events:", "    card = p(ev)", "    inner(card, ev)",
                                        inner=("card = dict(card)", "card['mid'] = 1")), _W_FRESH, False),
    ("a producer that returns a dict it holds", _handed("for ev in events:", "    card = p(ev)", "    inner(card, ev)",
                                                        producer="def p(e):\n    return e['card']\n"), _W_FRESH, False),
    ("a row with no witness", _in_f("ev = dict(ev)", "ev['mid'] = 1", params="ev"), ("f", "ev", "mid", "assign", None),
     False),
)


def _witness_holds(source, row):
    tree = ast.parse(source)
    function, target, field, form, witness = row
    writes, problems = _row_witness(tree, _CardWriteReader(tree).records(),
                                    (function, target, field, form, None, witness, ""))
    return writes > 0 and not problems


def _chain(names):
    """f(c) writing c[k<names - 1>], where k0 = 'mid' and each next name is bound to the one before: a key that many
    names deep."""
    return _in_f("k0 = 'mid'", *["k%d = k%d" % (i, i - 1) for i in range(1, names)], "c[k%d] = None" % (names - 1))


# The census's form space: (what, source, the sites it must report as (function, target, field, form)). A row whose
# `what` starts with "refused:" is a form the census reports as an unrecognised site whatever its key; one that starts
# with "limit:" is a known miss, a write the census does not read (the class docstring).
CARD_WRITE_FORM_TABLE = (
    ("subscript assignment", _in_f("c['mid'] = None"), [("f", "c", "mid", "assign")]),
    ("an unpacking target", _in_f("c['kind'], n = 'tool', 1"), [("f", "c", "kind", "assign")]),
    ("a starred target", _in_f("a, *c['peer'] = (1, 2)"), [("f", "c", "peer", "assign")]),
    ("an annotated assignment", _in_f("c['peer']: str = 'api'"), [("f", "c", "peer", "assign")]),
    ("a chained assignment", _in_f("c['mid'] = d['mid'] = None", params="c, d"),
     [("f", "c", "mid", "assign"), ("f", "d", "mid", "assign")]),
    ("an augmented assignment", _in_f("c['peer'] += '-v2'"), [("f", "c", "peer", "augassign")]),
    ("del", _in_f("del c['direction']"), [("f", "c", "direction", "del")]),
    ("del of two", _in_f("del c['kind'], c['mid']"), [("f", "c", "kind", "del"), ("f", "c", "mid", "del")]),
    ("a for target", _in_f("for c['mid'] in ('m1',):", "    pass"), [("f", "c", "mid", "for")]),
    ("a comprehension target", _in_f("return [0 for c['mid'] in ('m1',)]"), [("f", "c", "mid", "for")]),
    ("a with target", _in_f("with open('/dev/null') as c['mid']:", "    pass"), [("f", "c", "mid", "with")]),
    ("update, a dict literal", _in_f("c.update({'direction': 'out'})"), [("f", "c", "direction", "update")]),
    ("update, keywords", _in_f("c.update(peer='api')"), [("f", "c", "peer", "update")]),
    ("update, dict()", _in_f("c.update(dict(kind='tool'))"), [("f", "c", "kind", "update")]),
    ("update, pairs", _in_f("c.update([('mid', 'm2')])"), [("f", "c", "mid", "update")]),
    ("update, a literal splatted into a literal", _in_f("c.update({**{'mid': 'm2'}, 'x': 1})"), [("f", "c", "mid", "update")]),
    ("update, a generator of pairs", _in_f("c.update((k, None) for k in ('mid',))"), [("f", "c", "mid", "update")]),
    ("update, a dict comprehension", _in_f("c.update({k: None for k in ('mid', 'peer')})"),
     [("f", "c", "mid", "update"), ("f", "c", "peer", "update")]),
    ("update, a name bound to a literal", _in_f("m = {'peer': 'api'}", "c.update(m)"), [("f", "c", "peer", "update")]),
    ("update, a union of literals", _in_f("c.update({'x': 1} | {'kind': 'tool'})"), [("f", "c", "kind", "update")]),
    ("setdefault", _in_f("c.setdefault('mid', 'm1')"), [("f", "c", "mid", "setdefault")]),
    ("pop", _in_f("c.pop('mid', None)"), [("f", "c", "mid", "pop")]),
    ("|= a literal", _in_f("c |= {'peer': 'api'}"), [("f", "c", "peer", "ior")]),
    ("__setitem__", _in_f("c.__setitem__('kind', 'tool')"), [("f", "c", "kind", "setitem")]),
    ("__delitem__", _in_f("c.__delitem__('peer')"), [("f", "c", "peer", "delitem")]),
    ("__ior__", _in_f("c.__ior__({'peer': 'api'})"), [("f", "c", "peer", "ior")]),
    ("dict.__setitem__", _in_f("dict.__setitem__(c, 'mid', None)"), [("f", "c", "mid", "setitem")]),
    ("dict.update", _in_f("dict.update(c, {'peer': 'api'})"), [("f", "c", "peer", "update")]),
    ("dict.setdefault", _in_f("dict.setdefault(c, 'kind', 'tool')"), [("f", "c", "kind", "setdefault")]),
    ("dict.pop", _in_f("dict.pop(c, 'mid')"), [("f", "c", "mid", "pop")]),
    ("operator.setitem", "import operator\n" + _in_f("operator.setitem(c, 'mid', None)"), [("f", "c", "mid", "setitem")]),
    ("operator.delitem under an alias", "import operator as op\n" + _in_f("op.delitem(c, 'kind')"),
     [("f", "c", "kind", "delitem")]),
    ("operator.__setitem__", "import operator\n" + _in_f("operator.__setitem__(c, 'direction', 'in')"),
     [("f", "c", "direction", "setitem")]),
    ("operator.ior", "import operator\n" + _in_f("operator.ior(c, {'peer': 'api'})"), [("f", "c", "peer", "ior")]),
    ("setitem imported under another name", "from operator import setitem as put\n" + _in_f("put(c, 'direction', 'in')"),
     [("f", "c", "direction", "setitem")]),
    ("a write through an alias of the card", _in_f("a = c", "a['mid'] = None"), [("f", "a", "mid", "assign")]),
    ("a write through an element", _in_f("cards[0]['peer'] = 'api'", params="cards"), [("f", "cards[0]", "peer", "assign")]),
    ("a key from a for loop over a literal", _in_f("for k in ('kind', 'mid'):", "    c[k] = None"),
     [("f", "c", "kind", "assign"), ("f", "c", "mid", "assign")]),
    ("a key from a module constant", "KEY = 'direction'\n" + _in_f("c[KEY] = 'in'"), [("f", "c", "direction", "assign")]),
    ("a key from a loop over a module tuple", "KEYS = ('kind', 'peer')\n" + _in_f("for k in KEYS:", "    c.pop(k)"),
     [("f", "c", "kind", "pop"), ("f", "c", "peer", "pop")]),
    ("a key from a loop over frozenset()", _in_f("for k in frozenset(('kind',)):", "    c[k] = None"),
     [("f", "c", "kind", "assign")]),
    ("a key from a loop over a dict's keys", _in_f("for k in {'mid': 1}:", "    c[k] = None"), [("f", "c", "mid", "assign")]),
    ("a key from an assignment expression", _in_f("if (k := 'mid'):", "    c[k] = None"), [("f", "c", "mid", "assign")]),
    ("a key from an assignment expression in a comprehension", _in_f("[0 for _n in (1,) if (k := 'mid')]", "c[k] = None"),
     [("f", "c", "mid", "assign")]),
    ("a lambda's assignment expression stays in the lambda", "k = 'mid'\n" + _in_f("g = lambda: (k := 'x')", "c[k] = None"),
     [("f", "c", "mid", "assign")]),
    ("a key from a conditional", _in_f("c['mid' if c else 'peer'] = None"),
     [("f", "c", "mid", "assign"), ("f", "c", "peer", "assign")]),
    ("a key from an enclosing function", _in_f("k = 'mid'", "def g():", "    c[k] = None", "return g"),
     [("f.g", "c", "mid", "assign")]),
    ("a key from a comprehension", _in_f("return [c.__setitem__(k, 1) for k in ('mid',)]"), [("f", "c", "mid", "setitem")]),
    ("a key from a global declaration", "X = None\n" + _in_f("global X", "X = 'mid'", "c[X] = 1"),
     [("f", "c", "mid", "assign")]),
    ("a global declaration adds the module's binding", "X = 'mid'\n" + _in_f("global X", "X = g()", "c[X] = 1"),
     [("f", "c", "mid", "assign")]),
    ("a key through a nonlocal declaration", _in_f("k = 'peer'", "def g():", "    nonlocal k", "    c[k] = 1", "return g"),
     [("f.g", "c", "peer", "assign")]),
    ("a key from a class body, in it", "class K:\n    k = 'mid'\n    d = {}\n    d[k] = 1\n", [("K", "d", "mid", "assign")]),
    ("a class body's name, unseen from its method", "k = 'x'\nclass K:\n    k = 'mid'\n    def f(self, c):\n        c[k] = 1\n",
     []),
    ("a comprehension's own binding shadows the outer one", "k = 'mid'\n" + _in_f(
        "return [c.__setitem__(k, 1) for k, _n in ((1, 2),)]"), []),
    ("a parameter shadows a module name", "k = 'mid'\n" + _in_f("c[k] = 1", params="c, k"), []),
    ("an unpacking shadows a module name", "k = 'mid'\n" + _in_f("k, _n = g()", "c[k] = 1"), []),
    ("a with target shadows a module name", "k = 'mid'\n" + _in_f("with g() as k:", "    c[k] = 1"), []),
    ("an import shadows a module name", "k = 'mid'\n" + _in_f("import k", "c[k] = 1"), []),
    ("an except name shadows a module name", "k = 'mid'\n" + _in_f("try:", "    pass", "except E as k:", "    c[k] = 1"),
     []),
    ("an augmented name shadows a module name", "k = 'mid'\n" + _in_f("k += 'x'", "c[k] = 1"), []),
    ("a nested definition shadows a module name", "k = 'mid'\n" + _in_f("def k():", "    pass", "c[k] = 1"), []),
    ("a match capture shadows a module name", "k = 'mid'\n" + _in_f("match c:", "    case {'x': k}:", "        c[k] = 1"), []),
    ("a match star shadows a module name", "k = 'mid'\n" + _in_f("match c:", "    case [*k]:", "        c[k] = 1"), []),
    ("a match rest shadows a module name", "k = 'mid'\n" + _in_f("match c:", "    case {**k}:", "        c[k] = 1"), []),
    ("in a lambda", "f = lambda c: c.update(mid=None)\n", [("<lambda>", "c", "mid", "update")]),
    ("in a method", "class K:\n    def f(self, c):\n        c['kind'] = 'tool'\n", [("K.f", "c", "kind", "assign")]),
    ("at module level", "c = {}\nc['mid'] = 1\n", [("<module>", "c", "mid", "assign")]),
    ("construction: a dict literal", _in_f("return {'kind': 'postal-service', 'mid': c['mid']}"), []),
    ("construction: dict() with keywords", _in_f("return dict(c, mid=None)"), []),
    ("construction: a splat into a new literal", _in_f("return {**c, 'mid': None}"), []),
    ("construction: a union into a new dict", _in_f("return c | {'peer': 'api'}"), []),
    ("construction: a copy", "import copy\n" + _in_f("return copy.copy(c)"), []),
    ("a read", _in_f("return c['mid'], c.get('peer')"), []),
    ("other fields", _in_f("c['summary'] = 'x'", "c.update(receipt={})", "del c['tlId']"), []),
    ("a loop over other names", _in_f("for k in ('email', 'org'):", "    c[k] = None"), []),
    ("a list slice", _in_f("c[1:] = []"), []),
    ("a key followed through _DEPTH names", _chain(_DEPTH), [("f", "c", "mid", "assign")]),
    ("refused: a writer bound to a name, then called", _in_f("upd = c.update", "upd(mid=None)"),
     [("f", "c", "?", _AS_VALUE)]),
    ("refused: a writer passed to map()", _in_f("list(map(c.pop, ('mid',)))"), [("f", "c", "?", _AS_VALUE)]),
    ("refused: a writer wrapped in functools.partial", "import functools\n" + _in_f(
        "functools.partial(c.__setitem__, 'mid')(None)"), [("f", "c", "?", _AS_VALUE)]),
    ("refused: dict.<name> not called directly", _in_f("put = dict.__setitem__", "put(c, 'mid', None)"),
     [("f", "dict", "?", _AS_VALUE)]),
    ("refused: an operator writer not called directly", "import operator\n" + _in_f(
        "put = operator.setitem", "put(c, 'mid', None)"), [("f", "operator.setitem", "?", _AS_VALUE)]),
    ("refused: an operator writer imported by name, not called directly", "from operator import setitem as put\n"
     + _in_f("return put"), [("f", "put", "?", _AS_VALUE)]),
    ("refused: getattr of a writer by a constant name", _in_f("getattr(c, '__setitem__')('mid', None)"),
     [("f", "c", "?", _BY_GETATTR)]),
    ("refused: getattr of __init__", _in_f("getattr(c, '__init__')(mid=None)"), [("f", "c", "?", _BY_GETATTR)]),
    ("refused: a writer reached through type()", _in_f("type(c).__setitem__(c, 'mid', None)"),
     [("f", "type(c)", "?", _THROUGH_TYPE)]),
    ("refused: a writer reached through __class__", _in_f("c.__class__.update(c, mid=None)"),
     [("f", "c.__class__", "?", _THROUGH_TYPE)]),
    ("refused: dict.__init__ over an existing dict", _in_f("dict.__init__(c, mid=None)"), [("f", "c", "?", _INIT)]),
    ("refused: __init__ called again on a dict", _in_f("c.__init__(mid=None)"), [("f", "c", "?", _INIT)]),
    ("refused: a base class's __init__ called by name",
     "class K(dict):\n    def __init__(self):\n        dict.__init__(self, mid=None)\n",
     [("K.__init__", "self", "?", _INIT)]),
    ("an attribute named for a writer, assigned or deleted", _in_f("c.update = None", "del c.pop"), []),
    ("super().__init__ is not refused", "class K(dict):\n    def __init__(self):\n        super().__init__(x=1)\n", []),
    ("refused: a starred argument to a writer", _in_f("c.setdefault(*('mid', None))"), [("f", "c", "?", _STARRED)]),
    ("refused: a starred argument to __setitem__", _in_f("c.__setitem__(*('mid', None))"), [("f", "c", "?", _STARRED)]),
    ("refused: update with a splatted literal", _in_f("c.update(**{'mid': 'm2'})"), [("f", "c", "?", _STARRED)]),
    ("refused: update with a splatted mapping it cannot read", _in_f("c.update(**row)", params="c, row"),
     [("f", "c", "?", _STARRED)]),
    ("limit: a key from a parameter", _in_f("c[k] = None", params="c, k"), []),
    ("limit: a key from a call", _in_f("c[key_of(c)] = None"), []),
    ("limit: a key built by concatenation", _in_f("c['m' + 'id'] = None"), []),
    ("limit: an f-string key", _in_f("c[f'{c}'] = None"), []),
    ("limit: an attribute key", _in_f("c[K.MID] = None"), []),
    ("limit: a key bound by unpacking", _in_f("k, _n = ('mid', 1)", "c[k] = None"), []),
    ("limit: update with a mapping from a parameter", _in_f("c.update(row)", params="c, row"), []),
    ("limit: clear", _in_f("c.clear()"), []),
    ("limit: popitem", _in_f("c.popitem()"), []),
    ("limit: an assignment expression in the key", _in_f("c[(k := 'mid')] = None"), []),
    ("limit: a boolean operator in the key", _in_f("c[None or 'mid'] = None"), []),
    ("limit: a subscript of a literal as the key", _in_f("c[('mid', 'peer')[0]] = None"), []),
    ("limit: a key from a loop over another call", _in_f("for k in reversed(('mid',)):", "    c[k] = None"), []),
    ("limit: a key from a match capture", _in_f("match 'mid':", "    case k:", "        c[k] = None"), []),
    ("limit: a key followed through more names than _DEPTH", _chain(_DEPTH + 1), []),
    ("limit: update with zip()", _in_f("c.update(zip(('mid',), (None,)))"), []),
    ("limit: a method reached by a computed name", _in_f("getattr(c, m)('mid', None)", params="c, m"), []),
    ("limit: operator.methodcaller", "import operator\n" + _in_f("operator.methodcaller('update', mid=None)(c)"), []),
    ("limit: a method read from a type's __dict__", _in_f("dict.__dict__['__setitem__'](c, 'mid', None)"), []),
    ("limit: a method read through object.__getattribute__", _in_f("object.__getattribute__(c, 'update')(mid=None)"),
     []),
)


class CardFieldWriters(unittest.TestCase):
    """The rule the chat signature's postal memo (_postal_card_deps_memo) relies on for the cards it walks: the walk
    reads each recorded card's kind, mid, direction and peer outside every key, so nothing may edit those fields of a
    card in place once it is built. A rule over kernel/kernel.py's writers, pinned by a census of its AST: every
    in-place write of one of the four fields is matched, site by site and with its count, against CARD_FIELD_WRITERS,
    the legal set, where each row is construction (a NEW dict is being built) or a dict that is never a postal card,
    with the function and why. A write that is not on the list, a listed site that is gone, a count that moved, and a
    census that finds no write at all are each red. Every row's reason is checked by its witness (the comment above
    CARD_FIELD_WRITERS names the five) over every write the census attributes to the row, and a row without one is
    red; each witness is held and broken over small sources in CARD_WITNESS_CASES. A witness reads where the target's
    binding comes from, not what happens to the dict between that binding and the write: a new dict handed to a list
    and then written is green (a "limit:" case there).

    What it reads: every subscript in a store or del context, under whichever statement holds it (assignment and
    unpacking, annotated, augmented, for and comprehension targets, with targets, del); a direct call of a writer,
    which is .update, .setdefault, .pop, .__setitem__, .__delitem__ or .__ior__ as the called attribute, the same
    called as dict.<name> with the dict as the first argument, or operator.setitem, delitem or ior or a dunder spelling
    of one, under any import name, called with the dict as the first argument; and |=. It reads these when the key is
    a field it can name: a str constant; a name with a binding in its scope (or, unbound there, an enclosing one, the
    module included) to such a constant, or by a for loop or comprehension over a literal of them or a name for one; a
    conditional of them; the keys of a dict literal, a dict() call, a dict comprehension, a literal or a comprehension
    of pairs, a union of these or a name for one. It follows a key at most _DEPTH steps deep (a name to its binding is
    one step), so a key that needs more is missed. A store under a statement it does not model is reported as an
    unrecognised form, whatever its key, and so is each of these, which kernel.py writes nowhere (each measured at 0
    when the census began refusing it): a writer used other than as the called function of a direct call (bound to a
    name, passed to map(), wrapped in functools.partial); getattr of a writer or of __init__ by a constant name; a
    writer reached through type() or .__class__; __init__ reached on anything but super(); a * or ** argument to a
    writer. The target is not read for what it is: a write through an alias of a card names the alias, and is red like
    any other.

    What it misses, as known examples rather than a closed list (each a "limit:" row of CARD_WRITE_FORM_TABLE, green): a
    key computed from data (a parameter, a call, an attribute, a concatenation, an f-string, an unpacking); a key it
    does not fold (an assignment expression or a boolean operator written in the key itself, a subscript of a literal,
    a loop over a call such as reversed(), a match capture); a key followed through more names than _DEPTH; .update or
    |= of a mapping it cannot read (a parameter, zip()); .clear() and .popitem(), which name no key; a method reached
    by a computed name, through operator.methodcaller, from a type's __dict__ or through object.__getattribute__; a
    write in another module (the cards never leave kernel.py's functions: the population derived for this census,
    2026-10-07)."""

    @classmethod
    def setUpClass(cls):
        cls.tree = PC.source_and_tree(KERNEL_PY, rel="kernel/kernel.py")[1]

    def test_every_in_place_write_of_a_card_field_in_the_kernel_is_on_the_legal_list(self):
        sites = _card_field_writes(self.tree)
        self.assertTrue(sites, "the census found no write of a card field in kernel/kernel.py at all: it read nothing, or"
                               " not the kernel's tree (an empty population is not a pass)")
        found, lines = collections.Counter(), collections.defaultdict(list)
        for site in sites:
            found[site[:4]] += 1
            lines[site[:4]].append(site[4])
        legal = {row[:4]: row[4] for row in CARD_FIELD_WRITERS}
        wrong = ["%s writes %s[%r] (%s): %d in kernel.py (line %s), %d on the list" % (
                     key + (found[key], ", ".join(map(str, lines[key])) or "none", legal.get(key, 0)))
                 for key in sorted(set(found) | set(legal)) if found[key] != legal.get(key, 0)]
        self.assertEqual(wrong, [], (
            "an in-place write of a postal card's kind, mid, direction or peer that CARD_FIELD_WRITERS does not hold."
            " _postal_card_deps_memo reads those fields from each recorded card outside its key, on the rule that"
            " nothing edits a card once it is built, so a write that edits an existing card serves a stale chat"
            " signature: key the memo on the field, or build a new card. A write that builds a NEW dict (a literal, a"
            " dict() call, a copy made before the write) or writes a dict that is never a postal card goes on the list"
            " with its function, why and a witness; a listed site that is gone, or whose count moved, is corrected"
            " there. A site whose field is '?' is a write the census does not read (an unrecognised form, the class"
            " docstring): write it as a direct call or a subscript the census reads."))

    def test_every_listed_rows_reason_holds_by_its_witness(self):
        records = _CardWriteReader(self.tree).records()
        wrong, checked = [], 0
        for row in CARD_FIELD_WRITERS:
            function, target, field, form, count, witness, _why = row
            if witness and witness[0] in _WITNESSES:
                checked += 1
            got = _row_witness(self.tree, records, row)
            if got != (count, []):
                wrong.append("%s writes %s[%r] (%s), listed %d times with witness %r: it read %d, with %s" % (
                    function, target, field, form, count, witness, got[0], got[1] or "no problem"))
        self.assertEqual(wrong, [], (
            "a row of CARD_FIELD_WRITERS whose reason its witness does not find true over every write the census"
            " attributes to it. Each row is construction or a dict that is never a card; a change that hands the listed"
            " name an existing card makes its write an in-place edit of that card: build a new dict, or key the memo on"
            " the field"))
        self.assertEqual(checked, len(CARD_FIELD_WRITERS), "every row of CARD_FIELD_WRITERS carries a witness")

    def test_the_witnesses_read_their_reasons(self):
        outcomes = collections.defaultdict(set)
        for what, source, row, holds in CARD_WITNESS_CASES:
            self.assertEqual(_witness_holds(source, row), holds, "%s (%s):\n%s" % (what, row[4], source))
            outcomes[(row[4] or (None,))[0]].add(holds)
        outcomes.pop(None, None)
        self.assertEqual(dict(outcomes), {kind: {True, False} for kind in _WITNESSES},
                         "each witness has a case that holds and a case that breaks")

    def test_the_census_reads_every_form_in_its_table(self):
        forms = set()
        for what, source, want in CARD_WRITE_FORM_TABLE:
            got = [site[:4] for site in _card_field_writes(ast.parse(source))]
            self.assertEqual(got, sorted(want), "%s:\n%s" % (what, source))
            forms |= {w[3] for w in want}
        self.assertEqual(forms, CARD_WRITE_FORMS | CARD_REFUSED_FORMS,
                         "every form the census reports or refuses has a row in the table")
        for key, field in (("mid", "mid"), ("x", "?")):
            bare = ast.Module(body=[ast.Expr(value=ast.Subscript(value=ast.Name(id="c", ctx=ast.Load()),
                                                                 slice=ast.Constant(value=key), ctx=ast.Store()))],
                              type_ignores=[])
            self.assertEqual([s[:4] for s in _card_field_writes(bare)], [("<module>", "c", field, "unrecognised under Expr")],
                             "a store under a statement the census does not model is reported whatever its key, not skipped")


class MsgSummariesKey(unittest.TestCase):
    """_msg_summaries' per-session submap is keyed on every input its scan reads: the parse's key (the
    transcript's stat, the pending cut, the states file), the captions file and the goal store (the
    store, its override journal, its archive)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved_state = jd.STATE
        jd._rebind_state(Path(self.td.name))
        self.saved = (km._sessions, km._msg_sum_scan_session, dict(km._msg_sum_cache), km._sdk)
        km._msg_sum_cache.clear()
        km._sdk = lambda: None
        self.scanned = []
        km._msg_sum_scan_session = lambda sid, path, now: (self.scanned.append(sid) or {sid + ":m": "cap"})
        self.rows = [{"sid": SID_A, "name": "web", "path": "/x/a", "mtime": 100},
                     {"sid": SID_B, "name": "api", "path": "/x/b", "mtime": 100}]
        km._sessions = lambda now: list(self.rows)
        for d in (jd.CAPDIR, jd.GOALDIR, jd.GOALARCHDIR, jd._overrides_dir(), jd.STATESDIR):
            d.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        km._sessions, km._msg_sum_scan_session = self.saved[:2]
        km._msg_sum_cache.clear(); km._msg_sum_cache.update(self.saved[2])
        km._sdk = self.saved[3]
        jd._rebind_state(self.saved_state)
        self.td.cleanup()

    def _scan(self):
        self.scanned.clear()
        km._msg_summaries()
        return list(self.scanned)

    def test_each_input_change_rescans_that_session_only_and_unchanged_inputs_rescan_nothing(self):
        self.assertEqual(sorted(self._scan()), sorted([SID_A, SID_B]), "the first call scans everything")
        self.assertEqual(self._scan(), [], "unchanged inputs: no rescan")
        (jd.CAPDIR / (SID_A + ".jsonl")).write_text(json.dumps({"id": "seg", "caption": "c"}) + "\n")
        self.assertEqual(self._scan(), [SID_A], "a caption written with no transcript change rescans its session")
        self.assertEqual(self._scan(), [])
        (jd.GOALDIR / (SID_B + ".json")).write_text(json.dumps({"nodes": {}, "status": {}, "seams": [1]}))
        self.assertEqual(self._scan(), [SID_B], "a store publish (its seams) rescans its session")
        with open(jd._overrides_dir() / (SID_B + ".jsonl"), "a") as f:
            f.write('{"op": "reopen"}\n')
        self.assertEqual(self._scan(), [SID_B], "a journaled user gesture rescans its session")
        (jd.GOALARCHDIR / (SID_A + ".json")).write_text("{}")
        self.assertEqual(self._scan(), [SID_A], "an archive write rescans its session")
        self.rows[0] = {**self.rows[0], "mtime": 200}
        self.assertEqual(self._scan(), [SID_A], "the row's mtime still keys when the transcript cannot be stat'd")
        (jd.STATESDIR / (SID_B + ".jsonl")).write_text('{"state": "idle", "t": 1}\n')
        self.assertEqual(self._scan(), [SID_B], "a states row (an idle atom in the parse) rescans its session")
        self.assertEqual(self._scan(), [])
        self.assertEqual(km._msg_summaries(), {SID_A + ":m": "cap", SID_B + ":m": "cap"})

    def test_the_transcripts_size_and_the_pending_cut_key_too(self):
        tx = Path(self.td.name) / "a.jsonl"
        tx.write_text('{"type": "user"}\n')
        self.rows[0] = {**self.rows[0], "path": str(tx)}
        cut = {"value": ""}

        class Fake:
            def pending_cut(self, sid):
                return cut["value"] if sid == SID_A else ""
        km._sdk = lambda: Fake()
        self._scan()
        self.assertEqual(self._scan(), [])
        with open(tx, "a") as f:
            f.write('{"type": "assistant"}\n')                 # the size moves even where the mtime's clock does not
        self.assertEqual(self._scan(), [SID_A], "the transcript's size keys")
        cut["value"] = "uuid-of-the-cut"                     # a pending chat delete changes the parse with no file change
        self.assertEqual(self._scan(), [SID_A], "the backend's pending cut keys")
        self.assertEqual(self._scan(), [])

    def test_the_key_is_taken_before_the_scan(self):
        # a caption appended while the scan runs pairs the OLD key with the new content: one more rescan on
        # the next call, never a stale hit. Proven by writing the caption from inside the scan.
        def scanning(sid, path, now):
            self.scanned.append(sid)
            if sid == SID_A and not (jd.CAPDIR / (SID_A + ".jsonl")).exists():
                (jd.CAPDIR / (SID_A + ".jsonl")).write_text(json.dumps({"id": "seg", "caption": "c"}) + "\n")
            return {sid + ":m": "cap"}
        km._msg_sum_scan_session = scanning
        self._scan()
        self.assertEqual(self._scan(), [SID_A], "the write that landed mid-scan is seen on the next call")
        self.assertEqual(self._scan(), [])


class CycleCaptionSlot(unittest.TestCase):
    """The caption map is fetched once per pusher cycle: _pusher_cycle opens a slot on the cycle's scope,
    the first build that needs the map fills it, later builds of the cycle read it, the timeline's postal
    connectors read the same slot, and the finally closes it. A thread with no cycle scope (a connect
    push) reads the map directly."""

    def setUp(self):
        self.saved = (km._live_map, km._pusher_cycle_jobs, km._msg_summaries, jd.STATE,
                      dict(km._postal_log_cache))
        self.fetched = []
        km._live_map = lambda: {}
        km._msg_summaries = lambda: (self.fetched.append(1) or {MID: "cap"})
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        jd._rebind_state(Path(td.name))                      # the timeline's postal log lives under the state root
        km._postal_log_cache.clear()

    def tearDown(self):
        km._live_map, km._pusher_cycle_jobs, km._msg_summaries, state, log = self.saved
        jd._rebind_state(state)
        km._postal_log_cache.clear(); km._postal_log_cache.update(log)
        km._live_scope.msgsum = None

    def _connectors(self, now):
        return km._postal_messages(now, {SID_A, PEER}, {SID_A: "web", PEER: "api"})

    def test_reads_within_one_cycle_fetch_once_and_the_slot_closes_with_the_cycle(self):
        seen = []

        def jobs(now, live_map, any_client):
            seen.append(getattr(km._live_scope, "msgsum", None))
            first = km._msg_summaries_scoped()
            for _ in range(4):
                self.assertIs(km._msg_summaries_scoped(), first, "the cycle's map, not a fresh fetch")
        km._pusher_cycle_jobs = jobs
        km._pusher_cycle()
        self.assertEqual(len(seen), 1)
        self.assertIsNotNone(seen[0], "the slot was open during the jobs")
        self.assertEqual(len(self.fetched), 1, "one fetch for the whole cycle")
        self.assertIsNone(getattr(km._live_scope, "msgsum", None), "closed with the cycle")
        for _ in range(3):
            km._msg_summaries_scoped()                          # no scope: the direct path
        self.assertEqual(len(self.fetched), 4, "three direct reads fetch three times")

    def test_the_slot_closes_when_the_jobs_raise(self):
        seen = []

        def jobs(now, live_map, any_client):
            seen.append(getattr(km._live_scope, "msgsum", None))
            raise RuntimeError("a job failed")
        km._pusher_cycle_jobs = jobs
        with self.assertRaises(RuntimeError):
            km._pusher_cycle()
        self.assertEqual(len(seen), 1)
        self.assertIsNotNone(seen[0], "the slot was open during the jobs")
        self.assertIsNone(getattr(km._live_scope, "msgsum", None), "closed by the finally")

    def test_the_timelines_postal_connectors_read_the_cycles_map(self):
        now = int(time.time())
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        jd.MESSAGES.write_text(json.dumps({"ev": "sent", "id": MID, "from": "api", "from_id": PEER, "to_id": SID_A,
                                           "body": "the api tests are green now", "kind": "coordinate",
                                           "t": now - 60}) + "\n")
        rows = []

        def jobs(now_, live_map, any_client):
            km._msg_summaries_scoped()                          # a chat build fetched the cycle's map
            rows.append(self._connectors(now))                  # the timeline build's connectors, twice
            rows.append(self._connectors(now))
        km._pusher_cycle_jobs = jobs
        km._pusher_cycle()
        self.assertEqual(len(self.fetched), 1, "the connectors read the cycle's map, not a fresh fetch")
        self.assertEqual([r[0]["summary"] for r in rows], ["cap", "cap"], "each connector carries the caption")
        self._connectors(now)
        self.assertEqual(len(self.fetched), 2, "no scope: the direct path")


# ── build_session over a synthetic session ───────────────────────────────────────────────────────
def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _uline(t, text, uuid, parent=None):
    return {"type": "user", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent, "promptSource": "typed",
            "message": {"role": "user", "content": text}, "cwd": "/tmp/notes-api", "version": "2.1.0", "gitBranch": "main"}


def _aline(t, text, uuid, parent, tool=None, stop="end_turn"):
    content = [{"type": "text", "text": text}]
    if tool:
        content.append({"type": "tool_use", "id": "tu_%s" % uuid, "name": tool, "input": {"command": "uv run pytest -q"}})
    return {"type": "assistant", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "model": "claude-sonnet-4", "content": content, "stop_reason": stop},
            "cwd": "/tmp/notes-api", "version": "2.1.0", "gitBranch": "main"}


def _trline(t, tool_use_id, uuid, parent, content="ok\n"):
    return {"type": "user", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": content}]}}


class World:
    """A synthetic session build_session can build: names/ + projects/<cdir>/<sid>.jsonl under a state root
    the kernel's judge module is rebound to (tests/test_chat_fold.py's Sess, reduced), plus a goal-store
    writer and a postal log. The live tail is the owning backend's (nobody's here: an unowned sid has none)."""

    def __init__(self, sid):
        self.sid = sid
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.cdir = td / "launchdir"
        self.cdir.mkdir()
        proj = td / "projects"
        pdir = proj / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(self.cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (sid + ".jsonl")
        self.tpath.write_text("")
        self.saved_state = jd.STATE
        self.saved = (jd.PROJECTS, km.NAMES, km._live_map, km._GLOBAL_CLAUDE_MD, km._msg_summaries, km._sdk,
                      os.environ.get("CLAUDE_CONFIG_DIR"))
        jd._rebind_state(td)                              # names, goals, captions, archive, states, messages: all under td
        jd.PROJECTS = proj
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        (jd.NAMES / sid).write_text("web\t%s\t#abcdef\n" % str(self.cdir))
        km.NAMES = jd.NAMES
        km._GLOBAL_CLAUDE_MD = td / "no-global-claude.md"
        self.now = int(time.time())                       # discovery keys on the real clock
        self.t = self.now - 3 * 86400
        self.tm = {sid: {"state": "working", "since": self.now - 100, "model": "", "effort": "",
                         "context": None, "compactPct": None, "color": None}}
        km._live_map = lambda: self.tm
        km._msg_summaries = lambda: {}
        km._sdk = lambda: None
        os.environ["CLAUDE_CONFIG_DIR"] = str(td / "claude")   # no real task store is read
        _clear_memos()
        km._parse_cache.clear(); km._PATH_LINK_CACHE.clear(); km._SPACE_PATH_CACHE.clear()
        km._postal_index_memo[0] = None
        if isinstance(jd._discover_cache, dict):
            jd._discover_cache.clear()
        self.n = 0
        self.last = None

    def close(self):
        km._rewind_hold_clear(self.sid)
        (jd.PROJECTS, km.NAMES, km._live_map, km._GLOBAL_CLAUDE_MD, km._msg_summaries, km._sdk, cfg) = self.saved
        if cfg is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = cfg
        jd._rebind_state(self.saved_state)
        _clear_memos()
        km._parse_cache.clear()
        km._postal_index_memo[0] = None
        self.td.cleanup()

    def uid(self):
        self.n += 1
        return "bbbbbbbb-0000-0000-0000-%012d" % self.n

    def tick(self, dt=5):
        self.t += dt
        return self.t

    def turn(self, i):
        """One complete turn: prompt, one Bash round (use + result), a closing reply."""
        u = self.uid()
        recs = [_uline(self.tick(), "step %d: tighten the notes-api search" % i, u, self.last)]
        a = self.uid()
        recs.append(_aline(self.tick(), "Round %d: adjusting `search.py`." % i, a, u, tool="Bash", stop="tool_use"))
        r = self.uid()
        recs.append(_trline(self.tick(), "tu_%s" % a, r, a))
        b = self.uid()
        recs.append(_aline(self.tick(), "Step %d done." % i, b, r))
        self.last = b
        return recs

    def append(self, recs):
        with open(self.tpath, "a") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        os.utime(self.tpath, None)

    def store(self, nodes, seams=None, last=None):
        """Publish goals/<sid>.json by rename, as save_goals does."""
        p = jd.GOALDIR / (self.sid + ".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps({"nodes": nodes, "status": {}, "seams": seams or [], "lastNode": last}))
        os.replace(tmp, p)

    def nodes(self, n, trail=(), parent=None):
        return {"g%d" % i: {"id": "g%d" % i, "text": "goal %d" % i, "t": self.t + i, "mt": self.t + i,
                            "parentId": parent, "trail": list(trail)} for i in range(1, n + 1)}

    def postal_log(self, rows):
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        with open(jd.MESSAGES, "a") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def build(self, scoped=True):
        """build_session under the pusher's names scope (as _pusher_cycle sets it); scoped=False is a
        handler-thread build, which reads the registry per card."""
        if scoped:
            km._live_scope.names = km._names_snapshot()
        try:
            return km.build_session(self.sid, self.now, self.tm)
        finally:
            km._live_scope.names = None


def _dump(m):
    return json.dumps(m, sort_keys=True, default=str)


class PostalGate(unittest.TestCase):
    """The fold gate keys a tab's sealed postal cards on the values they embed (this session's postal revision
    and, per card, its caption and its peer's name and colour), not on the judge generation or the log's
    identity: a judge pass that moved none of them re-hydrates nothing, mail between two other sessions
    re-hydrates nothing, a caption change re-hydrates exactly the sealed cards, and the commit hydrates only
    the raw events new since the seal."""

    def setUp(self):
        self.w = World(SID_A)
        self.caps = {}
        km._msg_summaries = lambda: dict(self.caps)
        self.w.postal_log([{"ev": "sent", "id": MID, "from": "api", "from_id": PEER, "to_id": SID_A,
                            "body": "the api tests are green now", "kind": "coordinate", "t": self.w.t}])
        self.judge_gen = km._judge_gen[0]

    def tearDown(self):
        km._judge_gen[0] = self.judge_gen
        self.w.close()

    def _incoming(self):
        """One sealed incoming card: a delivered peer message, the reply, then a complete turn after it."""
        w = self.w
        u = w.uid()
        w.append([_uline(w.tick(), "<!-- romp-msg-id: %s -->\nthe api tests are green now" % MID, u, w.last)])
        a = w.uid()
        w.append([_aline(w.tick(), "Noted, thanks.", a, u)])
        w.last = a
        w.append(w.turn(2))

    def _spy(self):
        """Every _hydrate_postal call build_session makes from here on, as the event lists it was handed."""
        calls = []
        orig = km._hydrate_postal

        def counting(events, *a, **kw):
            calls.append(list(events))
            return orig(events, *a, **kw)
        km._hydrate_postal = counting
        self.addCleanup(setattr, km, "_hydrate_postal", orig)
        return calls

    @staticmethod
    def _card(m):
        return next(ev for ev in m["events"] if ev.get("kind") == "postal-service")

    @staticmethod
    def _stats():
        # zeros on a tree without the counters, so the behavioural assertions run first
        return dict(getattr(km, "_chat_postal_stats", None) or {"gate": 0, "hit": 0, "commit_new": 0})

    def test_a_judge_pass_that_moved_no_caption_leaves_the_sealed_card_alone(self):
        w = self.w
        self.caps[MID] = "api: tests green"
        w.append(w.turn(0))
        self._incoming()
        m = w.build()
        self.assertEqual(self._card(m)["summary"], "api: tests green")
        w.build()                                                  # warm: the card is sealed in the prefix
        raw = km._chat_fold_get(SID_A)["postal_raw"]
        self.assertEqual(len(raw), 1, "the marker event rides the entry raw")
        calls = self._spy()
        s0 = self._stats()
        km._judge_gen[0] += 1                                      # a judge pass: some store moved
        m2 = w.build()
        self.assertEqual([any(e is raw[0] for e in c) for c in calls], [False],
                         "one hydration, the tail pass: the sealed card was neither re-hydrated by the gate "
                         "nor hydrated again at the commit")
        self.assertEqual(self._card(m2)["summary"], "api: tests green")
        s1 = self._stats()
        self.assertEqual((s1["gate"] - s0["gate"], s1["hit"] - s0["hit"], s1["commit_new"] - s0["commit_new"]), (0, 1, 0))
        # equivalence with a cold build stands
        km._chat_fold.clear()
        self.assertEqual(_dump(w.build()), _dump(m2))

    def test_a_caption_change_re_hydrates_exactly_the_sealed_card_and_refreshes_it(self):
        w = self.w
        self.caps[MID] = "api: tests green (live)"
        w.append(w.turn(0))
        self._incoming()
        w.build()
        w.build()
        entry = km._chat_fold_get(SID_A)
        self.assertEqual(entry["postal_deps"], ((MID, "api: tests green (live)", None, None),),
                         "the entry records the values its card embeds: mid, caption, the sender's name and colour")
        raw = entry["postal_raw"]
        calls = self._spy()
        s0 = self._stats()
        n0 = km._CHAT_FOLD_STATS.get("g:postal", 0)
        self.caps[MID] = "api: tests green"                       # the final caption lands
        m = w.build()
        self.assertEqual(self._card(m)["summary"], "api: tests green")
        self.assertEqual([any(e is raw[0] for e in c) for c in calls][0], True, "the gate re-hydrated the sealed card")
        self.assertEqual(km._chat_postal_stats["gate"] - s0["gate"], 1)
        self.assertGreater(km._CHAT_FOLD_STATS.get("g:postal", 0), n0, "a different card demotes the prefix")
        self.assertEqual(km._chat_fold_get(SID_A)["postal_deps"], ((MID, "api: tests green", None, None),))
        km._chat_fold.clear()
        self.assertEqual(_dump(w.build()), _dump(m), "equal to a cold build")

    def test_a_peers_colour_refreshes_the_sealed_card_and_a_caption_for_another_message_does_not(self):
        w = self.w
        self.caps[MID] = "api: tests green"
        w.append(w.turn(0))
        self._incoming()
        w.build()
        m = w.build()
        self.assertIsNone(self._card(m).get("color"), "the sender has no registry entry yet")
        s0 = self._stats()
        self.caps["1788400000.200_2.TESTHOST"] = "api: something else"
        w.build()
        self.assertEqual((km._chat_postal_stats["gate"] - s0["gate"], km._chat_postal_stats["hit"] - s0["hit"]), (0, 1),
                         "a caption for another message moves nothing this card embeds")
        (jd.NAMES / PEER).write_text("api\t%s\t#123456\n" % str(w.cdir))
        m2 = w.build()
        self.assertEqual(self._card(m2).get("color"), {"bg": "#123456", "fg": "#ffffff"})
        self.assertEqual(km._chat_postal_stats["gate"] - s0["gate"], 1, "the sender's colour is a value the card embeds")
        self.assertEqual(km._chat_fold_get(SID_A)["postal_deps"],
                         ((MID, "api: tests green", "api", {"bg": "#123456", "fg": "#ffffff"}),))

    def test_a_build_outside_the_names_scope_seals_unverified_and_the_next_scoped_build_verifies_once(self):
        # a handler-thread build (a connect push) reads the registry per card, so the values it embeds and
        # the values it would record are two reads: it records None, and the pusher's next build, which reads
        # one snapshot, re-hydrates once and records what it saw
        w = self.w
        self.caps[MID] = "api: tests green"
        w.append(w.turn(0))
        self._incoming()
        w.build(scoped=False)
        w.build(scoped=False)
        self.assertIsNone(km._chat_fold_get(SID_A)["postal_deps"], "sealed unverified")
        s0 = self._stats()
        w.build()
        self.assertEqual((km._chat_postal_stats["gate"] - s0["gate"], km._chat_postal_stats["hit"] - s0["hit"]), (1, 0),
                         "the scoped build re-hydrated once")
        self.assertIsNotNone(km._chat_fold_get(SID_A)["postal_deps"])
        w.build()
        self.assertEqual((km._chat_postal_stats["gate"] - s0["gate"], km._chat_postal_stats["hit"] - s0["hit"]), (1, 1),
                         "and from then on the recorded values verify it")

    def test_builds_within_one_pusher_cycle_read_the_caption_map_once(self):
        # the gate's per-card caption check and the hydrations read the cycle's caption map
        # (_msg_summaries_scoped): one fetch per cycle however many tabs build; a build with no cycle scope
        # (a handler thread) fetches once per build
        w = self.w
        calls = []
        self.caps[MID] = "api: tests green"
        km._msg_summaries = lambda: (calls.append(1) or dict(self.caps))
        w.append(w.turn(0))
        self._incoming()
        w.build()                                                  # the card is sealed
        calls.clear()
        km._live_scope.msgsum = [km._MSGSUM_UNSET]                 # the slot _pusher_cycle opens for one cycle
        try:
            for _ in range(3):
                w.build()
        finally:
            km._live_scope.msgsum = None
        self.assertEqual(len(calls), 1, "three builds in one cycle: one fetch")
        calls.clear()
        for _ in range(3):
            w.build()
        self.assertEqual(len(calls), 3, "no cycle slot: one fetch per build")

    def test_the_commit_hydrates_only_the_raw_events_new_since_the_seal(self):
        w = self.w
        self.caps[MID] = "api: tests green"
        w.append(w.turn(0))
        self._incoming()
        w.build()
        w.build()
        s0 = self._stats()
        calls = self._spy()
        # a second delivery of the same message id, then a turn to seal it behind
        u = w.uid()
        w.append([_uline(w.tick(), "<!-- romp-msg-id: %s -->\nthe api tests are green now" % MID, u, w.last)])
        a = w.uid()
        w.append([_aline(w.tick(), "Seen.", a, u)])
        w.last = a
        w.append(w.turn(4))
        m = w.build()
        self.assertEqual(len([e for e in m["events"] if e.get("kind") == "postal-service"]), 2)
        self.assertEqual(km._chat_postal_stats["commit_new"] - s0["commit_new"], 1,
                         "one raw event was new since the seal, and one was hydrated at the commit")
        raw = km._chat_fold_get(SID_A)["postal_raw"]
        self.assertEqual(len(raw), 2)
        commit_calls = [c for c in calls if c and any(e is raw[1] for e in c) and len(c) == 1]
        self.assertEqual(len(commit_calls), 1, "the commit's hydration carried the new raw event alone")
        km._chat_fold.clear()
        self.assertEqual(_dump(w.build()), _dump(m), "equal to a cold build")

    def test_mail_between_two_other_sessions_verifies_the_sealed_card_without_re_hydrating(self):
        """The gate keys the sealed cards on this session's postal revision (2026-09-18), not the log's
        identity: a row between two other sessions moves the log and nothing the card embeds, so the recorded
        values verify it (a hit); a row addressed to this session re-hydrates once."""
        w = self.w
        self.caps[MID] = "api: tests green"
        w.append(w.turn(0))
        self._incoming()
        w.build()
        w.build()                                                  # the card is sealed and verified
        raw = km._chat_fold_get(SID_A)["postal_raw"]
        s0 = self._stats()
        calls = self._spy()
        w.postal_log([{"ev": "sent", "id": "1788400000.300_3.TESTHOST", "from_id": OTHER_A, "to_id": OTHER_B,
                       "body": "unrelated", "kind": "coordinate", "t": w.t}])
        m = w.build()
        self.assertEqual((km._chat_postal_stats["gate"] - s0["gate"], km._chat_postal_stats["hit"] - s0["hit"]), (0, 1),
                         "mail between two other sessions: the recorded values verify the sealed card")
        self.assertEqual([any(e is raw[0] for e in c) for c in calls], [False],
                         "the tail pass only: the sealed card was not re-hydrated")
        self.assertEqual(self._card(m)["summary"], "api: tests green")
        w.postal_log([{"ev": "sent", "id": "1788400000.400_4.TESTHOST", "from_id": PEER, "to_id": SID_A,
                       "body": "and the docs", "kind": "coordinate", "t": w.t}])
        w.build()
        self.assertEqual((km._chat_postal_stats["gate"] - s0["gate"], km._chat_postal_stats["hit"] - s0["hit"]), (1, 1),
                         "a record addressed to this session re-hydrates the sealed card once")


class PostalSidRevs(unittest.TestCase):
    """_postal_sid_revs: per session, (n, last_mid, outcomes) over the records addressed to or from it, the
    outcomes folded by VALUE per record; the records with no recipient under ""; _postal_sid_revs_of serving
    the memoized index's table by identity; and _chat_postal_rev reading a session's pair (2026-09-18)."""

    @staticmethod
    def _rec(mid, frm, to, t, **outs):
        r = {"id": mid, "from": "api", "fromId": frm, "toId": to, "body": "b", "kind": "coordinate", "t": t, "park": False}
        r.update(outs)
        return r

    def test_each_key_folds_its_records_and_their_outcome_values(self):
        idx = {"m1": self._rec("m1", PEER, SID_A, 1),
               "m2": self._rec("m2", SID_A, PEER, 2),
               "m3": self._rec("m3", OTHER_A, OTHER_B, 3, read=30),
               "m4": self._rec("m4", "", "", 4),
               "m5": self._rec("m5", "", SID_B, 5),             # the bus's own return note: no sender, one recipient
               "m6": self._rec("m6", SID_B, SID_B, 6)}          # self-addressed: counted once
        revs = km._postal_sid_revs(idx)
        self.assertEqual(revs[SID_A], (2, "m2", ()))
        self.assertEqual(revs[PEER], (2, "m2", ()))
        self.assertEqual(revs[OTHER_A], (1, "m3", (("m3", 30, None, None, None, None),)))
        self.assertEqual(revs[OTHER_B], revs[OTHER_A])
        self.assertEqual(revs[""], (1, "m4", ()), "the bucket holds the records with no recipient alone")
        self.assertEqual(revs[SID_B], (2, "m6", ()), "a note with no sender keys its recipient; a self-addressed row counts once")
        self.assertEqual(set(revs), {SID_A, PEER, OTHER_A, OTHER_B, "", SID_B})
        idx["m2"]["read"] = 20                                    # an outcome landing on this session's own message
        r2 = km._postal_sid_revs(idx)
        self.assertEqual(r2[SID_A], (2, "m2", (("m2", 20, None, None, None, None),)))
        self.assertEqual(r2[PEER], r2[SID_A])
        self.assertEqual(r2[OTHER_A], revs[OTHER_A], "a third party's entry is untouched")
        del idx["m2"]["read"]                                     # read then un-read with no build between: the receipt
        self.assertEqual(km._postal_sid_revs(idx), revs)         # is back where it was, and so is the revision
        idx["m2"]["read"] = 25                                    # read again at another time: the card renders the time
        self.assertNotEqual(km._postal_sid_revs(idx)[SID_A], r2[SID_A])
        idx["m1"].update(bounced=11, bouncedWhy="no such mailbox")
        r3 = km._postal_sid_revs(idx)
        self.assertEqual(r3[SID_A][2], (("m1", None, None, 11, None, "no such mailbox"), ("m2", 25, None, None, None, None)),
                         "every outcome and the bounce's why are values, in the log's order")
        idx["m1"]["bouncedWhy"] = "mailbox closed"
        self.assertNotEqual(km._postal_sid_revs(idx)[SID_A], r3[SID_A], "the why is rendered, so it is folded")

    def test_opposite_outcomes_on_two_messages_do_not_net_to_no_change(self):
        idx = {"m10": self._rec("m10", SID_A, PEER, 1, read=10), "m12": self._rec("m12", SID_A, PEER, 2)}
        a = km._postal_sid_revs(idx)[SID_A]
        del idx["m10"]["read"]
        idx["m12"]["read"] = 12                                   # an unexec on one, an exec on the other
        b = km._postal_sid_revs(idx)[SID_A]
        self.assertEqual((a[0], b[0]), (2, 2))
        self.assertNotEqual(a, b, "a count of outcomes would read 1 both times; the values differ")

    def test_the_memoized_index_carries_one_table_per_version_and_a_callers_dict_gets_its_own(self):
        w = World(SID_A)
        try:
            w.postal_log([{"ev": "sent", "id": MID, "from": "api", "from_id": PEER, "to_id": SID_A, "body": "b",
                           "kind": "coordinate", "t": w.t}])
            idx = km._postal_index()
            revs = km._postal_sid_revs_of(idx)
            self.assertIs(revs, km._postal_index_memo[0][3], "the memo entry carries the table")
            self.assertIs(km._postal_sid_revs_of(km._postal_index()), revs, "one table per index version, not per call")
            self.assertEqual(revs, km._postal_sid_revs(idx))
            self.assertEqual(km._chat_postal_rev(SID_A, idx), ((1, MID, ()), None))
            self.assertEqual(km._chat_postal_rev(OTHER_A, idx), (None, None), "a session party to no message: no revision")
            own = dict(idx)
            self.assertIsNot(km._postal_sid_revs_of(own), revs, "a caller's own dict never borrows the memo's table")
            self.assertEqual(km._postal_sid_revs_of(own), revs)
            w.postal_log([{"ev": "exec", "id": MID, "t": w.t + 1}])
            idx2 = km._postal_index()
            self.assertIsNot(idx2, idx, "the log grew: a new index version")
            revs2 = km._postal_sid_revs_of(idx2)
            self.assertIs(revs2, km._postal_index_memo[0][3])
            self.assertEqual(km._chat_postal_rev(SID_A, idx2), ((1, MID, ((MID, w.t + 1, None, None, None, None),)), None))
            self.assertEqual(km._chat_postal_rev(OTHER_A, idx2), (None, None))
        finally:
            w.close()


class LedgerMemo(unittest.TestCase):
    """The goal-tree walk and the live roots, memoized per session on every input of the walk: the parsed
    transcript (by identity, with no live atoms merged), the store (by identity) and its seams,
    cleared.jsonl (its stat, taken before the read) and the warm-anchor table's per-session revision."""

    def setUp(self):
        self.w = World(SID_A)
        self.w.append(self.w.turn(0))
        self.w.append(self.w.turn(1))

    def tearDown(self):
        self.w.close()

    @staticmethod
    def _stats():
        return dict(km._ledger_memo_stats)

    @staticmethod
    def _delta(before):
        now = km._ledger_memo_stats
        return {k: now[k] - before[k] for k in now if now[k] != before[k]}

    def test_unchanged_inputs_hit_and_each_input_change_misses_once(self):
        w = self.w
        s = self._stats()
        self.assertEqual(w.build()["ledger"]["tree"], [])
        self.assertEqual(self._delta(s), {"bypass_empty": 1}, "no store: nothing to walk, nothing to keep")
        w.store(w.nodes(3))
        s = self._stats()
        m = w.build()
        self.assertEqual([r["id"] for r in m["ledger"]["tree"]], ["g3", "g2", "g1"], "freshest first")
        self.assertEqual(self._delta(s), {"miss": 1})
        s = self._stats()
        m2 = w.build()
        self.assertEqual(self._delta(s), {"hit": 1})
        self.assertEqual(_dump(m2["ledger"]), _dump(m["ledger"]))
        km._ledger_memo.clear()
        self.assertEqual(_dump(w.build()["ledger"]), _dump(m["ledger"]), "the served ledger equals a fresh walk")
        # a store publish
        w.store(w.nodes(4))
        s = self._stats()
        self.assertEqual(len(w.build()["ledger"]["tree"]), 4)
        self.assertEqual(self._delta(s), {"miss": 1})
        # a journaled user gesture (the shared store's identity carries its override journal)
        jd._overrides_dir().mkdir(parents=True, exist_ok=True)
        with open(jd._overrides_dir() / (SID_A + ".jsonl"), "a") as f:
            f.write(json.dumps({"op": "resolve", "node": "absent", "t": w.now}) + "\n")
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"miss": 1})
        # a clear
        with open(jd.STATE / "cleared.jsonl", "a") as f:
            f.write(json.dumps({"id": "g1", "t": w.now}) + "\n")
        s = self._stats()
        m = w.build()
        self.assertEqual(self._delta(s), {"miss": 1})
        self.assertTrue(next(r for r in m["ledger"]["tree"] if r["id"] == "g1")["cleared"])
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1})
        # a transcript append: a new parse
        w.append(w.turn(2))
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"miss": 1})
        # a seam change (the seg ids of every turn after it)
        w.store(w.nodes(4), seams=[{"segs": ["no-such-seg"], "t": w.t - 30, "top": "g1", "text": "seam"}])
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"miss": 1})
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1})
        self.assertEqual(km._ledger_memo_report()["entries"], 1)

    def test_a_rewind_hold_and_a_live_merge_bypass(self):
        w = self.w
        w.store(w.nodes(2))
        w.build()
        km._rewind_hold_set(SID_A, w.t + 3, "")
        try:
            s = self._stats()
            self.assertEqual(len(w.build()["ledger"]["tree"]), 2)
            self.assertEqual(self._delta(s), {"bypass_hold": 1})
        finally:
            km._rewind_hold_clear(SID_A)
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1}, "the hold gone, the earlier entry serves")
        # a live atom merged into the last turn: the owning backend's live tail (the SDK backend's input echo
        # shape); the kernel keeps no echo store of its own since the tmux backend's removal (2026-09-11)
        class _LiveTail(km._UnownedBackend):
            def live_atoms(self, sid):
                return [{"type": "user", "uuid": "echo-11111111-2222-3333-4444-555555555555", "session_id": sid,
                         "t": w.now, "parentUuid": None, "author": "human", "_echo_text": "one more thing",
                         "message": {"role": "user", "content": [{"type": "text", "text": "one more thing"}]}}]

            def prune_live(self, sid, tx_uuids, tx_text_t, human_floor):
                pass
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: _LiveTail())):
            s = self._stats()
            w.build()
        self.assertEqual(self._delta(s), {"bypass_live": 1})

    def test_a_warm_anchor_learned_for_this_sessions_node_misses_once_and_another_sessions_does_not(self):
        w = self.w
        w.store(w.nodes(2))
        w.build()
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1})
        km._node_anchor_uuids({"id": "g9", "trail": ["s1"]}, {"s1": "u-1"}, {"s1": "a-1"}, sid=SID_B)
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1}, "another session's revision is not this key")
        km._node_anchor_uuids({"id": "g1", "trail": ["s1"]}, {"s1": "u-1"}, {"s1": "a-1"}, sid=SID_A)
        s = self._stats()
        m = w.build()
        self.assertEqual(self._delta(s), {"miss": 1})
        self.assertEqual(next(r for r in m["ledger"]["tree"] if r["id"] == "g1")["anchorUuid"], "a-1",
                         "the cold node now reads the warm anchor the table holds")
        km._node_anchor_uuids({"id": "g1", "trail": ["s1"]}, {"s1": "u-1"}, {"s1": "a-1"}, sid=SID_A)
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1}, "the same resolve again changes no entry: no bump")
        km._node_anchor_uuids({"id": "g1", "trail": ["s1"]}, {"s1": "u-1"}, {"s1": "a-1"})
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1}, "a resolve with no session names no revision")

    def test_a_resolve_landing_during_the_walk_misses_next_build_never_a_stale_hit(self):
        w = self.w
        w.store(w.nodes(2))
        w.build()
        w.store(w.nodes(3))                                 # the next build walks
        real, fired = km._node_anchor_uuids, []

        def racing(nd, trig, work, sid=None):
            if not fired:                                    # a peer build's resolve lands after this build read the rev
                fired.append(1)
                km._node_anchor_rev[SID_A] = km._node_anchor_rev.get(SID_A, 0) + 1
            return real(nd, trig, work, sid=sid)
        km._node_anchor_uuids = racing
        try:
            s = self._stats()
            w.build()
            self.assertEqual(self._delta(s), {"miss": 1})
        finally:
            km._node_anchor_uuids = real
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"miss": 1}, "the stored revision predates the racing bump: a miss")
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1})

    def test_a_warm_resolve_writes_the_table_entry_before_it_bumps_the_revision(self):
        # A build reads the revision before its walk and stores it. Were the bump to land first, a build
        # reading the revision between the bump and the entry write would store the new revision against a
        # walk over the old entry and serve it next build; so the entry is written first.
        revs_at_write = []

        class Recording(dict):
            def __setitem__(self, k, v):
                revs_at_write.append(km._node_anchor_rev.get(SID_A, 0))
                dict.__setitem__(self, k, v)
        real = km._node_anchor_last
        km._node_anchor_last = Recording()
        self.addCleanup(setattr, km, "_node_anchor_last", real)
        before = km._node_anchor_rev.get(SID_A, 0)
        km._node_anchor_uuids({"id": "g7", "trail": ["s1"]}, {"s1": "u-1"}, {"s1": "a-1"}, sid=SID_A)
        self.assertEqual(revs_at_write, [before], "the entry landed while the revision still read the old value")
        self.assertEqual(km._node_anchor_rev.get(SID_A, 0), before + 1)
        self.assertEqual(km._node_anchor_last["g7"], ("u-1", "a-1"))

    def test_a_store_published_between_the_builds_two_loads_misses_next_build(self):
        # build_session loads the store twice: at the top, for the seams its seg maps are cut with, and at
        # the ledger, for the nodes it walks. A publish landing between the two pairs the old seams' maps
        # with the new store object; the seams in the key make the next build, whose maps come from the new
        # seams, miss instead of serving that tree on the new store's identity.
        w = self.w
        w.store(w.nodes(2))
        w.build()
        real, calls = jd.load_goals_shared_or_fault, []

        def racing(sid):
            calls.append(sid)
            if len(calls) == 2:                                  # between the two loads: a publish with new seams
                w.store(w.nodes(3), seams=[{"segs": ["no-such-seg"], "t": w.t - 30, "top": "g1", "text": "seam"}])
            return real(sid)
        jd.load_goals_shared_or_fault = racing
        try:
            s = self._stats()
            m = w.build()
        finally:
            jd.load_goals_shared_or_fault = real
        self.assertEqual(calls, [SID_A, SID_A], "the seg maps' load, then the ledger's")
        self.assertEqual(self._delta(s), {"miss": 1})
        self.assertEqual(len(m["ledger"]["tree"]), 3, "the walk read the new store's nodes")
        s = self._stats()
        m2 = w.build()
        self.assertEqual(self._delta(s), {"miss": 1}, "the stored walk was cut with the old seams: not this build's key")
        km._ledger_memo.clear()
        self.assertEqual(_dump(w.build()["ledger"]), _dump(m2["ledger"]), "the served ledger equals a fresh walk")
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1})

    def test_a_clear_landing_during_the_walk_misses_next_build(self):
        # cleared.jsonl is stat'd BEFORE it is read: a row appended between the two pairs the old key with
        # the new set, so the next build misses instead of serving a set the file has moved past
        w = self.w
        w.store(w.nodes(2))
        real = km._cleared_ids

        def racing():
            with open(jd.STATE / "cleared.jsonl", "a") as f:
                f.write(json.dumps({"id": "g2", "t": w.now}) + "\n")
            km._cleared_ids = real
            return real()
        km._cleared_ids = racing
        try:
            s = self._stats()
            w.build()
            self.assertEqual(self._delta(s), {"miss": 1})
        finally:
            km._cleared_ids = real
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"miss": 1}, "the key taken before the read predates the row")
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"hit": 1})

    def test_the_ship_slice_caps_the_rows_and_the_walk_resolves_every_anchor(self):
        # the ledger ships the first 80 rows of the full walk (tree[:80]); the walk itself covers every node,
        # so every node's anchor is resolved and warm for the next build, the unshipped rows' included
        w = self.w
        w.build()
        parsed = km._parse(str(w.tpath), SID_A, w.now)
        seg = km._segs_seam(parsed["turns"][0], {})[0]
        w.store(w.nodes(200, trail=[seg["id"]]))
        km._node_anchor_last.clear()
        tree = w.build()["ledger"]["tree"]
        self.assertEqual(len(tree), 80)
        self.assertTrue(all(r["anchorUuid"] for r in tree))
        self.assertEqual(len(km._node_anchor_last), 200, "every node's anchor resolved, the 120 unshipped rows included")
        self.assertEqual(len(km._ledger_memo[SID_A][3]), 200, "the memo keeps the full walk; the slice is taken at the ship")

    def test_a_muted_tab_still_ships_no_tree(self):
        w = self.w
        w.store(w.nodes(3))
        w.build()
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID_A: {"hideFromFeed": True}}))
        s = self._stats()
        m = w.build()
        self.assertEqual((m["ledger"]["tree"], m["ledger"]["recent"], m["ledger"]["current"]), ([], [], None))
        self.assertEqual(self._delta(s), {"hit": 1}, "the mute is applied after the memo, live")
        self.assertEqual(len(km._ledger_memo[SID_A][3]), 3, "the memo keeps the walk for an unmute")


class TaskFold(unittest.TestCase):
    """_fold_tasks' per-turn partials, memoized per sid on each turn's atoms list identity and fingerprint:
    a build over the parse cache's object rescans only the turn the live merge replaced."""

    T = 1781100000

    def setUp(self):
        self._saved = (dict(km._task_fold_memo), dict(km._task_fold_stats), os.environ.get("CLAUDE_CONFIG_DIR"))
        km._task_fold_memo.clear()
        for k in km._task_fold_stats:
            km._task_fold_stats[k] = 0
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        os.environ["CLAUDE_CONFIG_DIR"] = td.name              # no real task store is read

    def tearDown(self):
        km._task_fold_memo.clear(); km._task_fold_memo.update(self._saved[0])
        km._task_fold_stats.clear(); km._task_fold_stats.update(self._saved[1])
        if self._saved[2] is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self._saved[2]

    def _turn(self, i, create=None, update=None, rejected=False):
        T = self.T + 100 * i
        atoms = [{"type": "user", "uuid": "u%d" % i, "t": T, "author": "human",
                  "message": {"role": "user", "content": [{"type": "text", "text": "step %d" % i}]}}]
        content, results = [], []
        if create:
            content.append({"type": "tool_use", "id": "tu_c%d" % i, "name": "TaskCreate",
                            "input": {"subject": create[0], "activeForm": create[1]}})
            results.append({"type": "tool_result", "tool_use_id": "tu_c%d" % i,
                            "content": "InputValidationError: subject is required" if rejected else "Task #%d created" % (i + 1),
                            **({"is_error": True} if rejected else {})})
        if update:
            content.append({"type": "tool_use", "id": "tu_u%d" % i, "name": "TaskUpdate",
                            "input": {"taskId": update[0], "status": update[1]}})
        content.append({"type": "tool_use", "id": "tu_b%d" % i, "name": "Bash", "input": {"command": "uv run pytest -q"}})
        results.append({"type": "tool_result", "tool_use_id": "tu_b%d" % i, "content": "ok"})
        atoms.append({"type": "assistant", "uuid": "a%d" % i, "t": T + 10, "message": {"role": "assistant", "content": content}})
        atoms.append({"type": "user", "uuid": "r%d" % i, "t": T + 20, "message": {"role": "user", "content": results}})
        return {"id": "t%d" % i, "trigger": "u%d" % i, "t": T, "end": T + 20, "ended": True, "atoms": atoms}

    def _session(self):
        return {"turns": [self._turn(0, create=("write the tests", "Writing the tests")),
                          self._turn(1, create=("run the suite", "Running the suite")),
                          self._turn(2, update=("1", "completed"))]}

    EXPECTED = [{"id": "1", "subject": "write the tests", "activeForm": "Writing the tests", "status": "completed"},
                {"id": "2", "subject": "run the suite", "activeForm": "Running the suite", "status": "pending"}]

    def test_identity_hits_a_new_parse_misses_and_a_live_merge_misses_the_last_turn_only(self):
        sess = self._session()
        self.assertEqual(km._fold_tasks(sess), self.EXPECTED, "no sid: the unmemoized fold")
        self.assertEqual(km._task_fold_stats, {"hit": 0, "miss": 3}, "a direct call scans and memoizes nothing")
        self.assertEqual(km._task_fold_report()["entries"], 0)
        got = km._fold_tasks(sess, SID_A)
        self.assertEqual(got, self.EXPECTED)
        self.assertEqual(km._task_fold_stats, {"hit": 0, "miss": 6})
        got2 = km._fold_tasks(sess, SID_A)
        self.assertEqual(got2, self.EXPECTED)
        self.assertIsNot(got2, got, "a fresh list per call")
        self.assertEqual(km._task_fold_stats, {"hit": 3, "miss": 6}, "the same turns: every turn served")
        merged = dict(sess, turns=[dict(t) for t in sess["turns"]])       # _merge_live_atoms' shape
        merged["turns"][-1]["atoms"] = list(merged["turns"][-1]["atoms"]) + [
            {"type": "assistant", "uuid": "live", "t": self.T + 999,
             "message": {"role": "assistant", "content": [{"type": "text", "text": "streaming"}]}}]
        self.assertEqual(km._fold_tasks(merged, SID_A), self.EXPECTED)
        self.assertEqual(km._task_fold_stats, {"hit": 5, "miss": 7}, "a live merge: the last turn scanned, the rest served")
        fresh = json.loads(json.dumps(sess))                              # a re-parse: new atom lists
        self.assertEqual(km._fold_tasks(fresh, SID_A), self.EXPECTED)
        self.assertEqual(km._task_fold_stats, {"hit": 5, "miss": 10})
        self.assertEqual(km._task_fold_report(), {"hit": 5, "miss": 10, "entries": 1})
        self.assertIsNone(km._fold_tasks({"turns": []}, SID_A), "no turns: no checklist")

    def test_a_turn_that_grew_in_place_is_rescanned(self):
        sess = self._session()
        km._fold_tasks(sess, SID_A)
        sess["turns"][1]["atoms"].append({"type": "assistant", "uuid": "a1b", "t": self.T + 150, "message": {
            "role": "assistant", "content": [{"type": "tool_use", "id": "tu_u1b", "name": "TaskUpdate",
                                              "input": {"taskId": "2", "status": "in_progress"}}]}})
        got = km._fold_tasks(sess, SID_A)
        self.assertEqual(got[1]["status"], "in_progress", "the appended update is folded")
        self.assertEqual(km._task_fold_stats, {"hit": 2, "miss": 4}, "the grown turn's fingerprint moved")

    def test_a_rejected_create_and_a_result_in_a_later_turn_fold_as_before(self):
        # the combine runs over every turn's partial in order, so a result that lands in a later turn than its
        # call still names the task, and a rejected create is still no item (the unmemoized rules)
        sess = {"turns": [self._turn(0, create=("write the tests", "Writing the tests")),
                          self._turn(1, create=("a malformed create", None), rejected=True),
                          self._turn(2, update=("1", "in_progress"))]}
        self.assertEqual(km._fold_tasks(sess, SID_A), km._fold_tasks(sess),
                         "memoized and direct folds agree")
        self.assertEqual([t["id"] for t in km._fold_tasks(sess, SID_A)], ["1"], "the rejected create is no item")
        self.assertEqual(km._fold_tasks(sess, SID_A)[0]["status"], "in_progress")

    def test_the_result_is_not_the_memo_and_the_store_reader_leaves_it_unchanged(self):
        sess = self._session()
        got = km._fold_tasks(sess, SID_A)
        before = json.dumps(got)
        self.assertIsNone(km._read_task_store("no-such-fsid-" + SID_A[:8], got), "no store dir: the loud None")
        self.assertEqual(json.dumps(got), before, "the reader alters nothing")
        got[0]["status"] = "cancelled"                                    # a caller altering its copy
        self.assertEqual(km._fold_tasks(sess, SID_A)[0]["status"], "completed", "the memo is untouched")

    def test_build_session_hands_its_sid_to_the_fold(self):
        w = World(SID_A)
        seen = []
        real = km._fold_tasks
        km._fold_tasks = lambda session, sid=None: (seen.append(sid) or None)
        try:
            w.append(w.turn(0))
            w.build()
        finally:
            km._fold_tasks = real
            w.close()
        self.assertEqual(seen, [SID_A], "the memo is keyed on the session the build is for")


if __name__ == "__main__":
    unittest.main()
