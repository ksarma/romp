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


if __name__ == "__main__":
    unittest.main()
