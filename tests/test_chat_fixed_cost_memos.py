#!/usr/bin/env python3
"""The chat builder's fixed-cost memos and its attribution counters (round-4 performance plan, item P3,
2026-09-07). build_session runs about 450 times per two minutes on a loaded kernel and most of those
builds are background rebuilds whose payload comes out byte-identical; the work they repeat is the
per-build fixed cost (the goal-tree walk, the task fold, the live-merge sets, the sealed postal
cards). Each memo here is keyed on every input of the computation it replaces, and each test below
checks the two halves of that claim: an unchanged input set hits, and every single input change
misses. The counters are what the plan reads the memos' value from on the live kernel.

Synthetic fixtures only: private synthetic sids (nothing else mints under them), invented text, the
notes-api demo world, a hermetic state root.
"""
import inspect
import json
import os
import re
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_chatmemos", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# Private synthetic sids (CLAUDE.md, goal-store fixtures): the judge module is shared across the worker's
# test modules and replays each sid's override journal on every load, so nothing else may mint under these.
SID_A = "66666666-7777-8888-9999-aaaaaaaaaaa1"
SID_B = "66666666-7777-8888-9999-aaaaaaaaaaa2"


# ── (f) the attribution counters ─────────────────────────────────────────────────────────────────
class SigLabels(unittest.TestCase):
    """_chat_build_sig is a flat tuple with one position per _CHAT_SIG_LABELS entry (round-4 plan P4), so a
    miss is attributed by position; the labels are pinned against the appends in source order, and a
    real signature has exactly one value per label."""

    def test_the_labels_follow_the_appends_in_source_order(self):
        src = inspect.getsource(km._chat_build_sig)
        markers = {"transcript": "sig.append((st.st_mtime, st.st_size))", "states": "sig.append(tuple(states))",
                   "store": "jd._store_identity(sid)[1:]", "hold": "_rewind_hold_get(sid)", "archive": "jd.ARCHDIR",
                   "episodes": "jd.EPIDIR", "reg": 'jd.STATE / "sdk"', "gone": "jd.GONEDIR", "tasks": "_task_store_fp(",
                   "todos": "_user_todo_fp(", "cut": "pending_cut(", "note": "working_note(", "needs": "_feed_needs_input_of(",
                   "live": "Sessions.live_rev(sid)", "row": '"snapT", "interrupting"', "clock": "_idle_faded(",
                   "backend": "_queue_recallable(", "ops": "_pending_ops.get(sid)", "limit": "_limit_hold(sid)",
                   "retry": "_retry_gate_state(sid)", "bg": "_bg_live_norm(sid, path)", "watch": "_watch_awaiting(sid)",
                   "stamp": "_session_stamp_read(sid)", "anchors": "_node_anchor_rev.get(sid, 0)", "downtime": '"downtime", "names", "flags"',
                   "cwd": "_github_repo_of(scwd)", "claudemd": "_claudemd_key(scwd)", "fork": "fork_children()",
                   "taskout": "_chat_sig_deps(sid, deps)"}
        pos = [src.index(markers[lab]) for lab in km._CHAT_SIG_LABELS if lab in markers]
        self.assertEqual(pos, sorted(pos), "the labels are in the appends' order")
        shared = ("downtime", "names", "flags", "ncards", "colormap", "acct", "cleared", "host")
        i = km._CHAT_SIG_LABELS.index("downtime")
        self.assertEqual(km._CHAT_SIG_LABELS[i:i + len(shared)], shared, "the shared components ride in the loop's order")
        self.assertEqual(km._CHAT_SIG_LABELS[-3:], km._CHAT_SIG_DEPS, "the three dependency components close the tuple")
        self.assertEqual(km._PerfStats.CHAT_MISS, km._CHAT_SIG_LABELS + ("cold", "nosig"))
        self.assertNotIn("_judge_gen[0]", src, "the judge-pass counter is no chat input (the docstring may name its removal)")

    def test_each_single_component_change_is_attributed_to_its_label(self):
        base = tuple(range(len(km._CHAT_SIG_LABELS)))
        for i, lab in enumerate(km._CHAT_SIG_LABELS):
            new = list(base)
            new[i] = "changed"
            self.assertEqual(km._chat_sig_miss(base, tuple(new)), (lab,), lab)
        self.assertEqual(km._chat_sig_miss(base, base), (), "an equal signature is no miss")
        self.assertEqual(km._chat_sig_miss(None, base), ("cold",))
        self.assertEqual(km._chat_sig_miss(base, None), ("nosig",))
        two = list(base)
        two[0], two[2] = "x", "y"
        self.assertEqual(km._chat_sig_miss(base, tuple(two)), ("store", "transcript"),
                         "several moved components are each attributed, sorted")
        self.assertEqual(km._chat_sig_miss(base[:-1], base), ("cold",),
                         "a signature of another shape (an older kernel's entry) is a cold miss, never a crash")

    def test_a_real_signature_has_one_value_per_label_and_holds_between_calls(self):
        tmp = tempfile.mkdtemp()
        tx = Path(tmp) / (SID_A + ".jsonl")
        tx.write_text('{"type": "user"}\n')
        sess = {"sid": SID_A, "path": str(tx), "anchor": SID_A}
        saved = km._sdk
        km._sdk = lambda: None
        try:
            sig = km._chat_build_sig(sess)
            self.assertEqual(len(sig), len(km._CHAT_SIG_LABELS))
            self.assertEqual(km._chat_build_sig(sess), sig, "byte-stable while nothing moved")
            self.assertEqual(sig[km._CHAT_SIG_LABELS.index("transcript")], (tx.stat().st_mtime, tx.stat().st_size))
            self.assertEqual(sig[-3:], ((), (), None), "a tab with no cached build records no dependencies yet")
            self.assertIsNone(km._chat_build_sig({"sid": SID_A, "path": ""}), "no path at all: no signature")
            gone = dict(sess, path=str(Path(tmp) / "not-yet.jsonl"))
            sig2 = km._chat_build_sig(gone)
            self.assertIsNone(sig2[0], "a transcript that does not exist yet is a component, so the tab still caches")
            self.assertEqual(len(sig2), len(km._CHAT_SIG_LABELS))
        finally:
            km._sdk = saved


class Collector(unittest.TestCase):
    def test_build_chat_splits_active_from_background_and_attributes_the_latter(self):
        st = km._PerfStats()
        st.build_chat(True)
        st.build_chat(False, 0.010, active=True)
        st.build_chat(False, 0.020, active=False, miss=("store",))
        st.build_chat(False, 0.030, active=False, miss=("states", "transcript"))
        st.build_chat(False, 0.005, active=False, miss=("cold",))
        c = st.snapshot()["builds"]["chat"]
        self.assertEqual((c["cached"], c["built"], c["active_built"], c["bg_built"]), (1, 4, 1, 3))
        self.assertAlmostEqual(c["ms"], 65.0)
        self.assertEqual({k: v for k, v in c["bg_miss"].items() if v},
                         {"store": 1, "states": 1, "transcript": 1, "cold": 1},
                         "one count per moved component: the two-component miss counts under both")
        self.assertEqual(set(c["bg_miss"]), set(km._PerfStats.CHAT_MISS))
        st.build_chat(False, 0.001, miss=("cold",))
        self.assertEqual(c["bg_miss"]["cold"], 1, "the snapshot is a copy; a later write does not move it")
        s = st.snapshot()["builds"]
        self.assertEqual(set(s["feed"]), {"cached", "built", "ms", "dirty"}, "no split on feed (its dirty is the view-signature bypass)")
        self.assertEqual(set(s["timeline"]), {"cached", "built", "ms"})
        json.dumps(s)
        # the plain writer still serves the chat kind (older call sites and tests), without attribution
        st.build("chat", False, 0.001)
        c2 = st.snapshot()["builds"]["chat"]
        self.assertEqual((c2["built"], c2["active_built"] + c2["bg_built"]), (6, 5))


class TwoTabAttribution(unittest.TestCase):
    """The real _push over two tabs, one watched: each tab is served while its complete signature holds
    (the watched one too — upstream's 2026-09-03 rule, on the one key since round-4 plan P4) and counts
    under active_built or bg_built when it moved, the background tab with the moved component named."""

    STUBS = ("NAMES", "_tmux_sessions", "_live_names", "_tab_list_tmux", "_chat_tab_sessions", "build_session",
             "_cached_feed", "_cached_timeline", "build_timeline", "_fleet_view_sig", "_comments_frame",
             "_retry_parked_creates")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        names = Path(self.tmp) / "names"
        names.mkdir()
        for sid, nm in ((SID_A, "web"), (SID_B, "api")):
            (names / sid).write_text("%s\t/proj/TESTHOST/app\t#1EA1EB\twhite\n" % nm)
        self.tx = {sid: Path(self.tmp) / (sid + ".jsonl") for sid in (SID_A, SID_B)}
        for p in self.tx.values():
            p.write_text('{"type": "user"}\n')                 # exists → _chat_build_sig is a real signature
        self.saved = {nm: getattr(km, nm) for nm in self.STUBS}
        self.saved_state = (km.jd.STATE, dict(km._built_chat), dict(km._prev_chat_events),
                            dict(km._prev_chat_ledger), list(km._last_tab_order), km._judge_gen[0])
        km.NAMES = names
        km.jd.STATE = Path(self.tmp) / "state"
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        km._tmux_sessions = lambda: {}
        km._live_names = lambda tm: {"web": SID_A, "api": SID_B}
        km._tab_list_tmux = lambda tmux: dict(tmux)
        km._chat_tab_sessions = lambda now, tmux: [{"sid": s, "name": n, "path": str(self.tx[s]), "anchor": s}
                                                  for s, n in ((SID_A, "web"), (SID_B, "api"))]
        km.build_session = self._build_session
        km._cached_feed = lambda now, tmux, sig, connect=False: {"working": [], "awaiting": [], "now": now}
        km._cached_timeline = lambda now, tmux, sig, connect=False: {"turns": {}, "judging": [], "messages": [], "now": now}
        km.build_timeline = lambda now, tmux, **kw: {"lanes": [], "now": now}
        km._fleet_view_sig = lambda now, tmux: {"probe": 1}
        km._comments_frame = lambda sid, tmux: None
        km._retry_parked_creates = lambda: None
        km._built_chat.clear(); km._prev_chat_events.clear(); km._prev_chat_ledger.clear()
        self.built = []
        self.chat = {"app": "chat", "alive": True, "sent": {}, "active": SID_A, "send": lambda s: None}
        self.tl = {"app": "timeline", "alive": True, "sent": {}, "send": lambda s: None}

    def tearDown(self):
        for nm, v in self.saved.items():
            setattr(km, nm, v)
        st, bc, pe, pl, lo, jg = self.saved_state
        km.jd.STATE = st
        km._built_chat.clear(); km._built_chat.update(bc)
        km._prev_chat_events.clear(); km._prev_chat_events.update(pe)
        km._prev_chat_ledger.clear(); km._prev_chat_ledger.update(pl)
        km._last_tab_order[:] = lo
        km._judge_gen[0] = jg
        for p in (km.jd.GOALDIR / (SID_B + ".json"), km.jd.STATESDIR / (SID_B + ".jsonl")):
            try:
                p.unlink()
            except OSError:
                pass

    def _build_session(self, sid, now, tmux):
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
                         "nothing moved: both tabs are served (the watched one on its exact key, 2026-09-03 upstream)")
        with open(self.tx[SID_B], "a") as f:
            f.write('{"type": "assistant"}\n')
        km._push([self.chat, self.tl])
        c3 = self._chat()
        self.assertEqual(self._delta(c2, c3), {"cached": 1, "built": 1, "active_built": 0, "bg_built": 1,
                                               "bg_miss": {"transcript": 1}}, "the background tab's transcript grew; the watched one is served")
        km._judge_gen[0] += 1
        km._push([self.chat, self.tl])
        c4 = self._chat()
        self.assertEqual(self._delta(c3, c4), {"cached": 2, "built": 0, "active_built": 0, "bg_built": 0, "bg_miss": {}},
                         "a judge pass ALONE no longer rebuilds any tab (round-4 plan P4): the signature "
                         "names the judge's outputs per session instead of the pass counter")
        km.jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        (km.jd.GOALDIR / (SID_B + ".json")).write_text(json.dumps({"rompUuid": SID_B, "nodes": {}, "status": {}}))
        km._push([self.chat, self.tl])
        c5 = self._chat()
        self.assertEqual(self._delta(c4, c5), {"cached": 1, "built": 1, "active_built": 0, "bg_built": 1,
                                               "bg_miss": {"store": 1}}, "the background tab's goal store was published; the watched tab is served")
        km.jd.STATESDIR.mkdir(parents=True, exist_ok=True)
        with open(km.jd.STATESDIR / (SID_B + ".jsonl"), "a") as f:
            f.write('{"t": 1, "state": "idle"}\n')
        km._push([self.chat, self.tl])
        c6 = self._chat()
        self.assertEqual(self._delta(c5, c6), {"cached": 1, "built": 1, "active_built": 0, "bg_built": 1,
                                               "bg_miss": {"states": 1}}, "the background tab's states file grew")
        km._push([self.chat, self.tl])
        c7 = self._chat()
        self.assertEqual(self._delta(c6, c7), {"cached": 2, "built": 0, "active_built": 0, "bg_built": 0, "bg_miss": {}},
                         "and both are served again once nothing moves")
        with open(self.tx[SID_A], "a") as f:
            f.write('{"type": "assistant"}\n')
        km._push([self.chat, self.tl])
        c8 = self._chat()
        self.assertEqual(self._delta(c7, c8), {"cached": 1, "built": 1, "active_built": 1, "bg_built": 0, "bg_miss": {}},
                         "the watched tab's own transcript grew: it rebuilds, under active_built")

    def test_the_push_loop_attributes_through_the_chat_writer(self):
        src = inspect.getsource(km._push)
        self.assertIn("_PERF_STATS.build_chat(True)", src)
        self.assertIn("_PERF_STATS.build_chat(False, _dt, active=is_active, miss=_miss)", src)
        self.assertIn('_miss = _chat_sig_miss(hit[0] if hit is not None else None, sig)', src,
                      "attributed for every tab, the watched one included (it is keyed too)")
        self.assertNotIn('_PERF_STATS.build("chat"', src, "no unattributed chat record left in the loop")

    def test_the_sweep_drops_the_merge_sets_of_a_sid_neither_shown_nor_alive(self):
        stray = "66666666-7777-8888-9999-aaaaaaaaaaa9"
        km._merge_sets_memo[stray] = ({"turns": []}, ())
        km._merge_sets_memo[SID_B] = ({"turns": []}, ())
        try:
            km._push([self.chat, self.tl])
            self.assertNotIn(stray, km._merge_sets_memo, "a sid that is neither a tab nor alive is evicted")
            self.assertIn(SID_B, km._merge_sets_memo, "a shown tab's entry stays")
        finally:
            km._merge_sets_memo.pop(stray, None)
            km._merge_sets_memo.pop(SID_B, None)

    def test_the_sweep_drops_the_ledger_and_task_fold_memos_of_a_tab_no_longer_shown_and_counts_it(self):
        stray = "66666666-7777-8888-9999-aaaaaaaaaaa9"
        km._ledger_memo[stray] = (("seams", None, 0), {"turns": []}, {"nodes": {}}, [], [])
        km._ledger_memo[SID_B] = (("seams", None, 0), {"turns": []}, {"nodes": {}}, [], [])
        km._task_fold_memo[stray] = {}
        km._task_fold_memo[SID_B] = {}
        evict0 = km._ledger_memo_stats["evict"]
        try:
            km._push([self.chat, self.tl])
            self.assertNotIn(stray, km._ledger_memo, "the ledger memo of a tab no longer shown is evicted")
            self.assertNotIn(stray, km._task_fold_memo, "and its task fold memo")
            self.assertIn(SID_B, km._ledger_memo, "a shown tab's entries stay")
            self.assertIn(SID_B, km._task_fold_memo)
            self.assertEqual(km._ledger_memo_stats["evict"], evict0 + 1, "one eviction counted")
            self.assertEqual(km._ledger_memo_report()["entries"], len(km._ledger_memo))
        finally:
            for d in (km._ledger_memo, km._task_fold_memo):
                d.pop(stray, None)
                d.pop(SID_B, None)


class MemoCounters(unittest.TestCase):
    """The four memos' counters share one lock (_chat_memo_bump, the _chat_fold_count shape): the pusher,
    the WS handlers and the backends all build, and a bare increment from two threads loses counts."""

    STATS = ("_merge_sets_stats", "_chat_postal_stats", "_ledger_memo_stats", "_task_fold_stats")

    def test_every_increment_goes_through_the_locked_helper(self):
        src = inspect.getsource(km)
        for name in self.STATS:
            bare = [l for l in src.splitlines() if re.search(r"%s\[[^\]]+\]\s*[+-]?=" % name, l)]
            self.assertEqual(bare, [], "%s: a write outside _chat_memo_bump" % name)
            self.assertIn("_chat_memo_bump(%s, " % name, src, "%s is bumped through the helper" % name)
        self.assertIn("with _chat_memo_lock:", inspect.getsource(km._chat_memo_bump))

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


# ── (d) the live-merge's transcript-side sets ────────────────────────────────────────────────────
class MergeSets(unittest.TestCase):
    """_merge_tx_sets: the sets _merge_live_atoms derives from the parsed session, memoized per sid on the
    session object's identity; the same object hits, a fresh parse misses, and the memoized sets are never
    written by a merge or by the backend's prune."""

    T = 1781100000

    def setUp(self):
        self._saved = (km.Sessions.__dict__["backend_for"], dict(km._merge_sets_memo), dict(km._merge_sets_stats))
        km._merge_sets_memo.clear()
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
        self.assertEqual(km._merge_sets_report(), {"hit": 1, "miss": 3, "entries": 2})

    def test_the_sets_equal_the_unmemoized_derivation_and_the_three_sets_are_frozen(self):
        sess = self._session()
        got = km._merge_tx_sets(sess, SID_A)
        exp = self._unmemoized(sess)
        self.assertEqual(tuple(got), exp)
        self.assertEqual(got[0], {"u1", "a1", "u2", "u2b", "a2"})
        self.assertNotIn("a2", got[1], "the textless twin is not a text uuid")
        self.assertEqual(got[3]["ok"], self.T + 25, "a repeated text keeps its newest record time")
        self.assertEqual(got[4], self.T + 25)
        for i in range(3):
            self.assertIsInstance(got[i], frozenset, "set %d is frozen: a write raises instead of corrupting later hits" % i)
        self.assertIsInstance(got[3], dict, "tx_text_t stays a dict: sdk_backend.prune_live dispatches on isinstance(dict)")

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
        self.assertEqual(km._merge_sets_stats, {"hit": 0, "miss": 0})

    def test_the_three_builders_merge_the_parse_caches_object(self):
        # identity stands for content only if every caller passes the object _parse caches
        self.assertIn("_merge_live_atoms(parsed, sid, shown_texts=queued)", inspect.getsource(km.build_session))
        self.assertIn('ps = _parse_cached(s["path"])', inspect.getsource(km.build_feed))
        self.assertIn("_merge_live_atoms(ps, fsid)", inspect.getsource(km.build_feed))
        tl = inspect.getsource(km.build_timeline)
        self.assertIn('session = _parse(s["path"], sid, now)', tl)
        self.assertIn("session = _merge_live_atoms(session, sid)", tl)
        self.assertIn("_merge_tx_sets(session, sid)", inspect.getsource(km._merge_live_atoms))


# ── (c) the sealed postal cards' values and the _msg_summaries re-key ────────────────────────────
class PostalCardDeps(unittest.TestCase):
    """_postal_card_deps: per sealed card, exactly the values it embeds from outside the transcript."""

    MID = "1788400000.100_1.TESTHOST"
    PEER = "66666666-7777-8888-9999-aaaaaaaaaaa3"

    def setUp(self):
        self._names = getattr(km._live_scope, "names", None)
        km._live_scope.names = {self.PEER: ["api", "/tmp/notes-api", "#abcdef"]}

    def tearDown(self):
        km._live_scope.names = self._names

    def test_each_embedded_value_is_a_component_and_nothing_else_is(self):
        index = {self.MID: {"id": self.MID, "from": "api", "fromId": self.PEER, "toId": SID_A, "body": "b",
                            "kind": "coordinate", "t": 1, "park": False}}
        colour = {"bg": "#abcdef", "fg": "#ffffff"}
        cards = [{"kind": "postal-service", "direction": "in", "peer": "api", "mid": self.MID, "summary": "cap", "body": "b"},
                 {"kind": "postal-service", "direction": "out", "peer": "api", "mid": self.MID, "body": "b"},
                 {"kind": "postal-service", "direction": "out", "peer": "tests", "body": "no row joined"},
                 {"kind": "tool", "name": "Bash", "output": "a raw event that did not hydrate"}]
        calls = []

        def caps():
            calls.append(1)
            return {self.MID: "cap"}
        deps = km._postal_card_deps(cards, index, caps)
        self.assertEqual(deps, ((self.MID, "cap", "api", colour), (self.MID, "cap", colour), (None, None, None), None))
        self.assertEqual(len(calls), 1, "the caption map is fetched once, and only because a card carries a mid")
        km._live_scope.names = {self.PEER: ["api", "/tmp/notes-api", "#000000"]}      # the sender's colour
        self.assertNotEqual(km._postal_card_deps(cards, index, caps), deps)
        km._live_scope.names = {self.PEER: ["renamed", "/tmp/notes-api", "#abcdef"]}  # the sender's name
        self.assertNotEqual(km._postal_card_deps(cards, index, caps), deps)
        km._live_scope.names = {self.PEER: ["api", "/tmp/notes-api", "#abcdef"]}
        self.assertNotEqual(km._postal_card_deps(cards, index, lambda: {self.MID: "other"}), deps, "the caption")
        self.assertEqual(km._postal_card_deps(cards, index, caps), deps, "the same inputs, the same tuple")
        self.assertEqual(km._postal_card_deps([cards[2], cards[3]], index, lambda: self.fail("no mid, no map")),
                         ((None, None, None), None))


class MsgSummariesKey(unittest.TestCase):
    """_msg_summaries' per-session submap is keyed on every input the scan reads: the transcript's mtime,
    the captions file and the goal store (store, override journal, archive)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved_state = jd.STATE
        jd._rebind_state(Path(self.td.name))
        self.saved = (km._sessions, km._msg_sum_scan_session, dict(km._msg_sum_cache))
        km._msg_sum_cache.clear()
        self.scanned = []
        km._msg_sum_scan_session = lambda sid, path, now: (self.scanned.append(sid) or {sid + ":m": "cap"})
        self.rows = [{"sid": SID_A, "name": "web", "path": "/x/a", "mtime": 100},
                     {"sid": SID_B, "name": "api", "path": "/x/b", "mtime": 100}]
        km._sessions = lambda now: list(self.rows)
        for d in (jd.CAPDIR, jd.GOALDIR, jd.GOALARCHDIR, jd._overrides_dir()):
            d.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        km._sessions, km._msg_sum_scan_session = self.saved[:2]
        km._msg_sum_cache.clear(); km._msg_sum_cache.update(self.saved[2])
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
        self.assertEqual(self._scan(), [SID_A], "the transcript's mtime still keys when the file cannot be stat'd")
        (jd.STATE / "states").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "states" / (SID_B + ".jsonl")).write_text('{"state": "idle", "t": 1}\n')
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
        saved = km._sdk
        km._sdk = lambda: Fake()
        self.addCleanup(setattr, km, "_sdk", saved)
        self._scan()
        self.assertEqual(self._scan(), [])
        with open(tx, "a") as f:
            f.write('{"type": "assistant"}\n')                 # the size moves even where the mtime's clock does not
        self.assertEqual(self._scan(), [SID_A], "the transcript's size keys")
        cut["value"] = "uuid-of-the-cut"                     # a pending chat delete changes the parse with no file change
        self.assertEqual(self._scan(), [SID_A], "the backend's pending cut keys")
        self.assertEqual(self._scan(), [])
        key = km._msg_sum_key(self.rows[0])
        self.assertEqual(len(key), 5, "(transcript, cut, states, captions, store identity)")
        self.assertEqual(key[1], "uuid-of-the-cut")

    def test_the_key_is_taken_before_the_scan_and_names_the_store(self):
        src = inspect.getsource(km._msg_summaries)
        self.assertLess(src.index("key = _msg_sum_key(s)"), src.index('_msg_sum_scan_session(sid, s["path"], now)'))
        self.assertIn("jd._store_identity(sid)[1:]", inspect.getsource(km._msg_sum_key))
        self.assertIn("goal store", km._msg_summaries.__doc__, "the docstring names the store as an input")

    def test_reads_within_one_pusher_cycle_fetch_the_map_once_and_stat_the_files_once(self):
        keyed = []
        real_key = km._msg_sum_key
        km._msg_sum_key = lambda s: (keyed.append(s["sid"]) or real_key(s))
        self.addCleanup(setattr, km, "_msg_sum_key", real_key)
        self.assertIsNone(getattr(km._live_scope, "msgsum", None), "no cycle scope on this thread to begin with")
        km._live_scope.msgsum = [km._MSGSUM_UNSET]               # the slot _pusher_cycle opens
        try:
            first = km._msg_summaries_scoped()
            for _ in range(4):
                self.assertIs(km._msg_summaries_scoped(), first, "the cycle's map, not a fresh fetch")
            self.assertEqual(sorted(keyed), sorted([SID_A, SID_B]), "the key's stats ran once per session, once per cycle")
        finally:
            km._live_scope.msgsum = None
        keyed.clear()
        for _ in range(3):
            km._msg_summaries_scoped()                              # no scope: the direct path, as a handler thread takes it
        self.assertEqual(len(keyed), 6, "three direct reads stat every session three times")

    def test_the_pusher_cycle_opens_and_closes_the_slot_and_the_chat_build_reads_it(self):
        cyc = inspect.getsource(km._pusher_cycle)
        self.assertLess(cyc.index("_live_scope.msgsum = [_MSGSUM_UNSET]"), cyc.index("_pusher_cycle_jobs(now, tmux, any_client)"),
                        "opened inside the try, before the jobs")
        self.assertLess(cyc.index("finally:"), cyc.index("_live_scope.msgsum = None"), "closed in the finally")
        self.assertIn("_msum_slot[0] = _msg_summaries_scoped()", inspect.getsource(km.build_session))
        self.assertIn("captions() if captions is not None else _msg_summaries()", inspect.getsource(km._hydrate_postal),
                      "the hydrations read the build's getter, so they see the cycle's map too")


# ── (a) the ledger memo, (b) the task fold memo ──────────────────────────────────────────────────
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
    """A synthetic session build_session can build: names/ + projects/<cdir>/<sid>.jsonl under a hermetic
    state root the kernel's judge module is rebound to (tests/test_chat_fold.py's Sess, reduced to what the
    ledger tests need), plus a goal-store writer."""

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
        names = td / "names"
        names.mkdir()
        (names / sid).write_text("web\t%s\t#abcdef\n" % str(self.cdir))
        self.saved = (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.GOALARCHDIR, jd.STATE,
                      km.NAMES, km._tmux_sessions, km._GLOBAL_CLAUDE_MD, km._msg_summaries, km._sdk)
        self.now = int(time.time())                       # discovery keys on the real clock
        self.t = self.now - 3 * 86400
        self.tm = {sid: {"state": "working", "since": self.now - 100, "model": "", "effort": "",
                         "context": None, "compactPct": None, "color": None}}
        jd.NAMES, jd.PROJECTS = names, proj
        jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.GOALARCHDIR = td / "captions", td / "archive", td / "goals", td / "goals-archive"
        jd.STATE = td
        km.NAMES = names
        km._GLOBAL_CLAUDE_MD = td / "no-global-claude.md"
        km._tmux_sessions = lambda: self.tm
        km._msg_summaries = lambda: {}
        km._sdk = lambda: None                            # the tmux path: the live tail is the kernel's echo store
        self.reset_memos()
        km._parse_cache.clear(); km._PATH_LINK_CACHE.clear(); km._SPACE_PATH_CACHE.clear()
        km._postal_index_memo[0] = None
        if isinstance(jd._discover_cache, dict):
            jd._discover_cache.clear()
        self.n = 0
        self.last = None

    @staticmethod
    def reset_memos():
        for d in (km._chat_fold, km._ledger_memo, km._task_fold_memo, km._node_anchor_last, km._node_anchor_rev,
                  km._merge_sets_memo, km._tmux_echo):
            d.clear()

    def close(self):
        km._rewind_hold_clear(self.sid)
        (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.GOALARCHDIR, jd.STATE,
         km.NAMES, km._tmux_sessions, km._GLOBAL_CLAUDE_MD, km._msg_summaries, km._sdk) = self.saved
        self.reset_memos()
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

    def build(self):
        km._live_scope.names = km._names_snapshot()       # the pusher's names scope, as _pusher_cycle sets it
        try:
            return km.build_session(self.sid, self.now, self.tm)
        finally:
            km._live_scope.names = None


class LedgerMemo(unittest.TestCase):
    """The goal-tree walk and live roots, memoized per sid on every input of the walk (interim, P3 (a))."""

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
        self.assertEqual(self._delta(s), {"bypass_empty": 1}, "no store: a fresh object per call, and nothing to walk")
        w.store(w.nodes(3))
        s = self._stats()
        m = w.build()
        self.assertEqual([r["id"] for r in m["ledger"]["tree"]], ["g3", "g2", "g1"], "freshest first")
        self.assertEqual(self._delta(s), {"miss": 1})
        s = self._stats()
        m2 = w.build()
        self.assertEqual(self._delta(s), {"hit": 1})
        self.assertIs(m2["ledger"]["tree"][0], m["ledger"]["tree"][0], "the memo's own rows, sliced")
        self.assertEqual(m2["ledger"]["recent"], m["ledger"]["recent"])
        # a store publish
        w.store(w.nodes(4))
        s = self._stats()
        self.assertEqual(len(w.build()["ledger"]["tree"]), 4)
        self.assertEqual(self._delta(s), {"miss": 1})
        # a journaled user gesture (the store's identity carries its override journal)
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
        km._tmux_echo_add(SID_A, "one more thing")           # a live atom merged into the last turn
        s = self._stats()
        w.build()
        self.assertEqual(self._delta(s), {"bypass_live": 1})

    def test_a_warm_anchor_learned_for_this_sids_node_misses_once_and_an_unrelated_sids_does_not(self):
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

    def test_the_orderings_the_memo_rests_on(self):
        src = inspect.getsource(km._node_anchor_uuids)
        self.assertLess(src.index("_node_anchor_last[nid] = (prompt, work)"),
                        src.index("_node_anchor_rev[sid] = _node_anchor_rev.get(sid, 0) + 1"),
                        "the table entry is written before the revision bumps")
        led = inspect.getsource(km.build_session)
        self.assertLess(led.index("_lkey = (_seams_sig, _ck, _node_anchor_rev.get(sid, 0))"), led.index("_twalk(_rid, 0)"),
                        "the revision is read before the walk")
        self.assertLess(led.index("_ck = _chat_cleared_key()"), led.index("_cleared_ids()"),
                        "cleared.jsonl is stat'd before it is read")
        self.assertIn("_node_anchor_uuids(nd, seg_trig, seg_uuid, deps, writes, sid=fsid)", inspect.getsource(km._feed_segs_build),
                      "the feed's resolves bump the same per-sid revision")

    def test_the_walk_caps_the_rows_it_ships_but_resolves_every_nodes_anchor(self):
        w = self.w
        w.build()
        parsed = km._parse(str(w.tpath), SID_A, w.now)
        seg = km._segs_seam(parsed["turns"][0], {})[0]
        w.store(w.nodes(200, trail=[seg["id"]]))
        km._node_anchor_last.clear()
        tree = w.build()["ledger"]["tree"]
        self.assertEqual(len(tree), 80)
        self.assertEqual(len(km._node_anchor_last), 200, "every node's anchor resolved, the 120 unshipped rows included")
        self.assertTrue(all(r["anchorUuid"] for r in tree))
        saved = km._LEDGER_TREE_ROWS
        km._LEDGER_TREE_ROWS = 10 ** 6
        try:
            km._ledger_memo.clear()
            full = w.build()["ledger"]["tree"]
        finally:
            km._LEDGER_TREE_ROWS = saved
        self.assertEqual(len(full), 200)
        self.assertEqual(full[:80], tree, "the capped walk's rows are the full walk's first rows")

    def test_the_cap_inside_a_subtree_ships_the_full_walks_rows_and_resolves_the_unshipped_children(self):
        # 30 roots with two children each: 90 nodes, 3 rows per root, so the 80th row is a first child
        # and the cap falls INSIDE root 27's subtree; the second child ships no row but its anchor resolves
        w = self.w
        w.build()
        parsed = km._parse(str(w.tpath), SID_A, w.now)
        seg = km._segs_seam(parsed["turns"][0], {})[0]
        nodes = {}
        for i in range(1, 31):
            nodes["r%d" % i] = {"id": "r%d" % i, "text": "goal %d" % i, "t": w.t + 10 * i, "mt": w.t + 10 * i,
                                "parentId": None, "trail": [seg["id"]]}
            for j in (1, 2):
                nodes["c%d_%d" % (i, j)] = {"id": "c%d_%d" % (i, j), "text": "step %d of goal %d" % (j, i),
                                            "t": w.t + 10 * i + j, "mt": w.t + 10 * i + j,
                                            "parentId": "r%d" % i, "trail": [seg["id"]]}
        w.store(nodes)
        km._node_anchor_last.clear()
        tree = w.build()["ledger"]["tree"]
        self.assertEqual(len(tree), 80)
        self.assertEqual([r["depth"] for r in tree[:3]], [0, 1, 1], "pre-order: a root, then its children")
        self.assertEqual(tree[-1]["depth"], 1, "the cap fell after a root's first child")
        self.assertIn(tree[-1]["id"], tree[-2]["children"], "that child belongs to the root shipped just before it")
        self.assertEqual(len(km._node_anchor_last), 90, "every node's anchor resolved, the unshipped children included")
        saved = km._LEDGER_TREE_ROWS
        km._LEDGER_TREE_ROWS = 10 ** 6
        try:
            km._ledger_memo.clear()
            full = w.build()["ledger"]["tree"]
        finally:
            km._LEDGER_TREE_ROWS = saved
        self.assertEqual(len(full), 90)
        self.assertEqual(full[:80], tree, "the capped walk's rows are the full walk's first rows, subtree cut included")
        self.assertEqual(full[80]["depth"], 1, "the first unshipped row is the cut subtree's second child")
        self.assertEqual(full[80]["children"], [])

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
    """_fold_tasks' per-turn partials, memoized per sid on each turn's atoms list identity and fingerprint."""

    T = 1781100000

    def setUp(self):
        self._saved = (dict(km._task_fold_memo), dict(km._task_fold_stats), os.environ.get("CLAUDE_CONFIG_DIR"))
        km._task_fold_memo.clear()
        for k in km._task_fold_stats:
            km._task_fold_stats[k] = 0
        self.td = tempfile.mkdtemp()
        os.environ["CLAUDE_CONFIG_DIR"] = self.td              # no real task store is read

    def tearDown(self):
        km._task_fold_memo.clear(); km._task_fold_memo.update(self._saved[0])
        km._task_fold_stats.clear(); km._task_fold_stats.update(self._saved[1])
        if self._saved[2] is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self._saved[2]

    def _turn(self, i, create=None, update=None):
        T = self.T + 100 * i
        atoms = [{"type": "user", "uuid": "u%d" % i, "t": T, "author": "human",
                  "message": {"role": "user", "content": [{"type": "text", "text": "step %d" % i}]}}]
        content, results = [], []
        if create:
            content.append({"type": "tool_use", "id": "tu_c%d" % i, "name": "TaskCreate",
                            "input": {"subject": create[0], "activeForm": create[1]}})
            results.append({"type": "tool_result", "tool_use_id": "tu_c%d" % i, "content": "Task #%d created" % (i + 1)})
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

    def test_the_result_is_not_the_memo_and_the_store_reader_leaves_it_unchanged(self):
        sess = self._session()
        got = km._fold_tasks(sess, SID_A)
        before = json.dumps(got)
        self.assertIsNone(km._read_task_store("no-such-fsid-" + SID_A[:8], got), "no store dir: the loud None")
        self.assertEqual(json.dumps(got), before, "the reader alters nothing")
        got[0]["status"] = "cancelled"                                    # a caller altering its copy
        self.assertEqual(km._fold_tasks(sess, SID_A)[0]["status"], "completed", "the memo is untouched")
        self.assertIn("fold = _fold_tasks(session, sid)", inspect.getsource(km.build_session))


if __name__ == "__main__":
    unittest.main()
