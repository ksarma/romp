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
import unittest
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
    """_chat_build_sig stays a flat tuple; its labels are derived from the tuple's shape, so the source
    and the label tuple are pinned against each other."""

    def test_the_tail_labels_follow_the_appends_in_source_order(self):
        src = inspect.getsource(km._chat_build_sig)
        self.assertEqual(len(re.findall(r"^\s*sig\.append\(", src, re.M)), len(km._CHAT_SIG_TAIL),
                         "one label per sig.append in _chat_build_sig; a new component needs a new label")
        markers = {"judge_gen": "_judge_gen[0]", "tasks": "_task_store_fp(", "todos": "_user_todo_fp(",
                   "cut": "pending_cut(", "note": "working_note(", "needs": "_feed_needs_input_of("}
        pos = [src.index(markers[lab]) for lab in km._CHAT_SIG_TAIL]
        self.assertEqual(pos, sorted(pos), "the labels are in the appends' order")
        self.assertIn("sig = [st.st_mtime, st.st_size]", src, "the head: the transcript's two values")
        self.assertIn("sig += [ss.st_mtime, ss.st_size]", src, "the middle: two values per states file")

    def test_each_single_component_change_is_attributed_to_its_label(self):
        base = (1.0, 10, 2.0, 20, 7, ("tf",), ("uf",), "", "note", False)      # one states file
        labels = km._chat_sig_labels(base)
        self.assertEqual(labels, ("transcript", "transcript", "states", "states") + km._CHAT_SIG_TAIL)
        for i, lab in enumerate(labels):
            new = list(base)
            new[i] = "changed"
            self.assertEqual(km._chat_sig_miss(base, tuple(new)), (lab,), lab)
        self.assertEqual(km._chat_sig_miss(base, base), (), "an equal signature is no miss")
        self.assertEqual(km._chat_sig_miss(None, base), ("cold",))
        self.assertEqual(km._chat_sig_miss(base, None), ("nosig",))
        two = list(base)
        two[0], two[4] = "x", 8
        self.assertEqual(km._chat_sig_miss(base, tuple(two)), ("judge_gen", "transcript"),
                         "several moved components are each attributed")
        # a second states file appeared (the anchor became known): the lengths differ, so `states` is set
        # and the fixed head and tail are compared from their own ends
        longer = base[:4] + (3.0, 30) + base[4:]
        self.assertEqual(km._chat_sig_labels(longer), ("transcript", "transcript") + ("states",) * 4 + km._CHAT_SIG_TAIL)
        self.assertEqual(km._chat_sig_miss(base, longer), ("states",))
        longer2 = list(longer)
        longer2[-1] = True
        self.assertEqual(km._chat_sig_miss(base, tuple(longer2)), ("needs", "states"))
        self.assertEqual(km._chat_sig_miss(longer, base), ("states",), "and the other way round")


class Collector(unittest.TestCase):
    def test_build_chat_splits_active_from_background_and_attributes_the_latter(self):
        st = km._PerfStats()
        st.build_chat(True)
        st.build_chat(False, 0.010, active=True)
        st.build_chat(False, 0.020, active=False, miss=("judge_gen",))
        st.build_chat(False, 0.030, active=False, miss=("states", "transcript"))
        st.build_chat(False, 0.005, active=False, miss=("cold",))
        c = st.snapshot()["builds"]["chat"]
        self.assertEqual((c["cached"], c["built"], c["active_built"], c["bg_built"]), (1, 4, 1, 3))
        self.assertAlmostEqual(c["ms"], 65.0)
        self.assertEqual({k: v for k, v in c["bg_miss"].items() if v},
                         {"judge_gen": 1, "states": 1, "transcript": 1, "cold": 1},
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
    """The real _push over two tabs, one watched: the watched tab counts under active_built every cycle,
    the background tab under bg_built only when its signature moves, with the moved component named."""

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
        self.assertEqual(self._delta(c1, c2), {"cached": 1, "built": 1, "active_built": 1, "bg_built": 0, "bg_miss": {}},
                         "nothing moved: the background tab is served, the watched one rebuilds")
        with open(self.tx[SID_B], "a") as f:
            f.write('{"type": "assistant"}\n')
        km._push([self.chat, self.tl])
        c3 = self._chat()
        self.assertEqual(self._delta(c2, c3), {"cached": 0, "built": 2, "active_built": 1, "bg_built": 1,
                                               "bg_miss": {"transcript": 1}}, "the background tab's transcript grew")
        km._judge_gen[0] += 1
        km._push([self.chat, self.tl])
        c4 = self._chat()
        self.assertEqual(self._delta(c3, c4), {"cached": 0, "built": 2, "active_built": 1, "bg_built": 1,
                                               "bg_miss": {"judge_gen": 1}}, "a judge pass busts the background tab")

    def test_the_push_loop_attributes_through_the_chat_writer(self):
        src = inspect.getsource(km._push)
        self.assertIn("_PERF_STATS.build_chat(True)", src)
        self.assertIn("_PERF_STATS.build_chat(False, _dt, active=is_active, miss=_miss)", src)
        self.assertIn('_miss = () if is_active else _chat_sig_miss(hit[0] if hit is not None else None, sig)', src)
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
        self.assertEqual(self._scan(), [SID_A], "the transcript's mtime still keys")
        self.assertEqual(self._scan(), [])
        self.assertEqual(km._msg_summaries(), {SID_A + ":m": "cap", SID_B + ":m": "cap"})

    def test_the_key_is_taken_before_the_scan_and_names_the_store(self):
        src = inspect.getsource(km._msg_summaries)
        self.assertLess(src.index("key = _msg_sum_key(s)"), src.index('_msg_sum_scan_session(sid, s["path"], now)'))
        self.assertIn("jd._store_identity(sid)[1:]", inspect.getsource(km._msg_sum_key))
        self.assertIn("goal store", km._msg_summaries.__doc__, "the docstring names the store as an input")


if __name__ == "__main__":
    unittest.main()
