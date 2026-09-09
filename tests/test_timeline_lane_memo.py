#!/usr/bin/env python3
"""The timeline's two lane memos: the DEAD-LANE memo (2026-09-08, upstream) and the fork's per-lane segment memo.

Both exist in the kernel since the 2026-09-09 fold, split by liveness (the fork's timeline owner's ruling on
#1131): a DEAD lane with a readable store is the dead-lane memo's (stat-keyed on every file it reads plus the
host's suspensions, the parse dropped once cached), and a dead MISS is derived by _lane_segments directly, so the
fork's _lane_memo (object-identity keyed on the parse, the FrozenStore and the _Caps object) is LIVE-ONLY: its
counters read the live lanes alone, and the dead lanes' outcomes ride the same /perf block as dead_serve,
dead_miss and dead_failed_serve. A dead lane whose PARSE failed is cached as the empty lane it drew (a dead
transcript has no writer; the key's ctime component re-attempts it on a chmod); a seams or marks complaint is
not. Upstream's cases come first (DeadLaneMemo, HorizonFilterIsExact, EntryEncodeMemo, its sid DEAD_SID); the
fork's follow under LaneMemoBase, whose fixtures build LIVE lanes, with the dead cases under DeadLanes.

--- the dead-lane memo ---
The full timeline build ran every pusher cycle (the fleet signature's 5 s bucket turns over faster than a 6 s
cycle) and re-parsed every lane's transcript and goals each time, dead lanes included. Now a dead lane's
parse-derived parts (bars, compactions, the work end, its judging marks) are served from a memo keyed on
every file they read, its parse is dropped from _parse_cache once cached (the resident-memory lever), and the
served frame is byte-identical to a rebuilt one: the judging marks are derived once at horizon zero, stamped
with the value the horizon test compares, and filtered per build on exactly that. The bars encoder reuses the
strings of entry objects it already encoded.

Synthetic transcript, states and captions under a temp root; a placeholder sid; the lane is dead because the
liveness snapshot is empty.

--- the per-lane segment memo ---
A lane's SEGMENT part (its bars, seg_ends, last_t, compaction markers and judging marks) is derived by
_lane_segments and held per lane by _lane_memo while every input is the previous build's: the _parse
object, the FrozenStore from load_goals_shared and the _Caps object from _captions (by identity), live,
the branch clip, tuple(_downtime) and the archive file's identity. The rule: a hit returns exactly what
the uncached loop returns NOW. So each input named in _lanes_memo's comment has a test here that changes
only that input and observes a miss with the new content, the clock-dependent pieces (the horizon and
the caption cap) are shown to apply on a hit, and the badge row is shown to stay per build. The
derivation's split (_derive_judging_marks + _judging_assemble) is compared against a private copy of
_derive_judging as it stood before the split.

Synthetic fixtures only: placeholder UUIDs, invented prompts. This module mints goal stores, so its
sids are PRIVATE to it (CLAUDE.md, goal-store fixtures); the state root is a fresh temp dir per test
and is removed with its override journal in tearDown.
"""

import ast
import inspect
import io
import json
import os
import shutil
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_TMUX_AVAILABLE"] = "1"          # an empty tmux map means zero live sessions, not "no tmux here"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
em = load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_lanememo", os.path.join(BIN, "romp-kernel"))
km._limit_hold = lambda sid: None

DEAD_SID = "11111111-2222-3333-4444-555555555555"
NOW = 1_800_000_000
T0 = NOW - 3600


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _rec(kind, t, uuid, parent, text):
    if kind == "user":
        return {"type": "user", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent, "promptSource": "typed",
                "message": {"role": "user", "content": text}}
    return {"type": "assistant", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}}


class DeadLaneMemo(unittest.TestCase):
    def setUp(self):
        km._downtime[:] = []
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        cdir = td / "launchdir"; cdir.mkdir()
        proj = td / "projects"
        pdir = proj / km.jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        self.recs = [_rec("user", T0, "u1", None, "run the long benchmark"),
                     _rec("assistant", T0 + 10, "a1", "u1", "Launched it.")]
        self.tpath = pdir / (DEAD_SID + ".jsonl")
        self._write(self.recs)
        names = td / "names"; names.mkdir()
        (names / DEAD_SID).write_text("testsess\t%s\t#abcdef\n" % str(cdir))
        self.saved = (km.jd.NAMES, km.jd.PROJECTS, km.jd.GOALDIR, km.jd.CAPDIR, km.jd.STATE, km.NAMES, km._tmux_sessions)
        km.jd.NAMES, km.jd.PROJECTS, km.jd.GOALDIR, km.jd.CAPDIR = names, proj, td / "goals", td / "captions"
        km.jd.STATE = td
        km.NAMES = names
        km._tmux_sessions = lambda: {}                 # NOBODY is live: the lane is a dead one within the window
        (td / "states").mkdir(); (td / "captions").mkdir(); (td / "goals").mkdir()
        (td / "goals" / (DEAD_SID + ".json")).write_text(json.dumps({"nodes": {}, "status": {}}))   # the judging marks need a store
        self.caps = td / "captions" / (DEAD_SID + ".jsonl")
        km._parse_cache.pop(str(self.tpath), None)
        km._dead_lane_memo.clear()
        km._delta_entry_memo.clear()

    def tearDown(self):
        (km.jd.NAMES, km.jd.PROJECTS, km.jd.GOALDIR, km.jd.CAPDIR, km.jd.STATE, km.NAMES, km._tmux_sessions) = self.saved
        km._dead_lane_memo.clear()
        self.td.cleanup()

    def _write(self, recs):
        self.tpath.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        os.utime(self.tpath, (NOW - 30, NOW - 30))    # recently touched: a lane within the 12 h window

    def _build(self, now=NOW):
        return km.build_timeline(now, {}, with_bars=True)

    def _lane(self, tl):
        return next(s for s in tl["sessions"] if s["id"] == DEAD_SID)

    def test_the_second_build_serves_the_lane_without_a_parse_and_drops_the_parse(self):
        parses = []
        real = km._parse
        km._parse = lambda path, sid, now: (parses.append(path), real(path, sid, now))[1]
        try:
            tl1 = self._build()
            self.assertEqual(parses, [str(self.tpath)], "the first build parses the dead lane once")
            self.assertNotIn(str(self.tpath), km._parse_cache, "and drops the parse once the lane is cached")
            self.assertIn(DEAD_SID, km._dead_lane_memo)
            tl2 = self._build()
            self.assertEqual(len(parses), 1, "the second build serves the lane: no parse")
            self.assertEqual(tl1["turns"][DEAD_SID], tl2["turns"][DEAD_SID])
            self.assertEqual(self._lane(tl1), self._lane(tl2), "a served lane is the rebuilt lane, byte for byte")
            self.assertEqual([m for m in tl1["judging"] if m["sid"] == DEAD_SID], [m for m in tl2["judging"] if m["sid"] == DEAD_SID])
            self.assertFalse(any("_h" in m for m in tl2["judging"]), "the horizon stamp never reaches the wire")
        finally:
            km._parse = real

    def test_a_moved_transcript_re_derives_the_lane(self):
        self._build()
        recs = self.recs + [_rec("user", T0 + 600, "u2", "a1", "and the cap?"),
                            _rec("assistant", T0 + 610, "a2", "u2", "Two minutes.")]
        self._write(recs)
        os.utime(self.tpath, (NOW - 20, NOW - 20))
        tl = self._build()
        self.assertEqual(len(tl["turns"][DEAD_SID]), 2, "the new turn is drawn")
        self.assertEqual(km._dead_lane_memo[DEAD_SID][1]["bars"], tl["turns"][DEAD_SID])

    def test_the_memo_keeps_stamped_marks_and_the_wire_never_sees_the_stamp(self):
        cap_t = NOW - km.TL_HORIZON + 30
        self.caps.write_text(json.dumps({"id": "u1", "t": cap_t, "caption": "launched the benchmark",
                                         "grain": "segment"}) + "\n")
        tl = self._build(NOW)
        marks = km._dead_lane_memo[DEAD_SID][1]["marks"]
        self.assertEqual([(m["judge"], m["_h"]) for m in marks], [("captioner", cap_t)], "derived once, stamped")
        self.assertFalse(any("_h" in m for m in tl["judging"]), "the stamp never reaches the wire")

    def test_every_keyed_input_re_derives_the_lane_when_it_moves(self):
        """The key is every file the parse-derived parts read, not the transcript alone (the review of the
        first batch found a key pinned on one component): touching each one changes the memo's key and the
        lane is derived again."""
        td = Path(self.td.name)
        self._build()
        key0 = km._dead_lane_memo[DEAD_SID][0]
        inputs = [td / "states" / (DEAD_SID + ".jsonl"), td / "goals" / (DEAD_SID + ".json"),
                  td / "overrides" / (DEAD_SID + ".jsonl"), td / "captions" / (DEAD_SID + ".jsonl"),
                  td / "archive" / (DEAD_SID + ".json"), td / "session-flags.json"]
        seen = {key0}
        for i, p in enumerate(inputs):
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.name == DEAD_SID + ".json" and p.parent.name == "goals":
                p.write_text(json.dumps({"nodes": {}, "status": {}, "touched": i}))
            elif p.suffix == ".json":
                p.write_text(json.dumps({"touched": i}))
            else:
                p.write_text("")
            os.utime(p, (NOW - 10 + i, NOW - 10 + i))
            self._build()
            key = km._dead_lane_memo[DEAD_SID][0]
            self.assertNotIn(key, seen, "%s moved but the key did not" % p.name)
            seen.add(key)
        self._build()
        self.assertEqual(km._dead_lane_memo[DEAD_SID][0], key, "nothing moved: the key stands")

    def test_a_lane_whose_goals_store_cannot_be_read_is_never_cached(self):
        """A goals FAULT is a store that cannot be read (an OSError; malformed bytes are healed by the loader):
        the lane renders without goal-derived data, complains, and is derived again on every build rather
        than served from a memo that would silence the fault."""
        store = Path(self.td.name) / "goals" / (DEAD_SID + ".json")
        store.chmod(0)
        try:
            self._build()
            self.assertNotIn(DEAD_SID, km._dead_lane_memo, "a faulted store stays loud on every build, never served stale")
        finally:
            store.chmod(0o600)
        self._build()
        self.assertIn(DEAD_SID, km._dead_lane_memo, "readable again: cached like any other dead lane")

    def test_a_live_lane_is_not_memoized(self):
        km._tmux_sessions = lambda: {DEAD_SID: {"state": "waiting", "since": NOW - 100, "model": "", "effort": "",
                                           "context": None, "compactPct": None, "color": None, "mode": ""}}
        km.build_timeline(NOW, km._tmux_sessions(), with_bars=True)
        self.assertNotIn(DEAD_SID, km._dead_lane_memo)


class HorizonFilterIsExact(unittest.TestCase):
    """The cached marks filtered on their stamped compare value are the marks a fresh derivation at that
    horizon would append, mark for mark: the diary and distiller marks are compared on their EVIDENCE time
    but emitted at the segment's work END, so a filter on the emitted time would admit a mark the fresh
    derivation drops (evidence before the horizon, work end after it). Pure functions, synthetic inputs."""

    def _inputs(self):
        h = 1_700_000_000
        caps = {"c%d" % i: {"id": "c%d" % i, "t": h - 100 + i * 50, "caption": "cap %d" % i, "grain": "segment"} for i in range(6)}
        goals = {"nodes": {
            "g1": {"t": h - 40, "mt": h + 10, "text": "old mint, done after the horizon",
                   "log": [{"src": "closer", "kind": "done", "ev_t": h - 5, "why": "evidence just before the horizon"}]},
            "g2": {"t": h + 20, "mt": h + 30, "text": "new mint", "distilledMt": h - 20, "briefedMt": h + 40},
        }}
        seg_ends = {h - 5: h + 300, h - 20: h + 400}      # completion marks land at the work END, after the horizon
        return h, caps, goals, seg_ends

    def test_filtered_stamped_marks_equal_a_fresh_derivation(self):
        h, caps, goals, seg_ends = self._inputs()
        for t0 in (h - 1000, h - 10, h, h + 15, h + 35, h + 1000):
            fresh = []
            km._derive_judging("s", caps, goals, t0, fresh, seg_ends)
            stamped = []
            km._derive_judging("s", caps, goals, 0, stamped, seg_ends, stamp=True)
            self.assertEqual(km._dead_lane_marks(stamped, t0), fresh, "horizon %+d" % (t0 - h))
        fresh = []
        km._derive_judging("s", caps, goals, h, fresh, seg_ends)
        self.assertFalse(any(m["judge"] == "closer" for m in fresh), "evidence before the horizon: dropped")
        self.assertTrue(any(m["judge"] == "distiller" and m["kind"] == "brief" for m in fresh))

    def test_the_stamp_is_private(self):
        h, caps, goals, seg_ends = self._inputs()
        stamped = []
        km._derive_judging("s", caps, goals, 0, stamped, seg_ends, stamp=True)
        self.assertTrue(stamped and all("_h" in m for m in stamped))
        self.assertFalse(any("_h" in m for m in km._dead_lane_marks(stamped, 0)))


class EntryEncodeMemo(unittest.TestCase):
    def test_an_entry_object_seen_last_split_is_not_encoded_again(self):
        km._delta_entry_memo.clear()
        sep = km._DELTA_SEP
        b1, b2 = {"id": "b1", "start": 1, "end": 2}, {"id": "b2", "start": 3, "end": 4}
        ents1, _ = km._delta_split("dictlist:id", {"S": [b1, b2]}, memo_key=("bars", "turns"))
        b3 = {"id": "b3", "start": 5, "end": 6}
        ents2, _ = km._delta_split("dictlist:id", {"S": [b1, b3]}, memo_key=("bars", "turns"))
        self.assertIs(ents2["S" + sep + "b1"][1], ents1["S" + sep + "b1"][1], "the same object: the same string, not re-encoded")
        self.assertEqual(json.loads(ents2["S" + sep + "b3"][1]), b3)
        self.assertNotIn(id(b2), km._delta_entry_memo[("bars", "turns")], "the memo is rebuilt from THIS split: no growth")
        b1b = dict(b1)                                   # equal content, a NEW object: encoded afresh (identity, never equality)
        ents3, _ = km._delta_split("dictlist:id", {"S": [b1b]}, memo_key=("bars", "turns"))
        self.assertEqual(ents3["S" + sep + "b1"][1], ents1["S" + sep + "b1"][1])
        self.assertIsNot(ents3["S" + sep + "b1"][1], ents1["S" + sep + "b1"][1])

    def test_the_wire_fill_hands_the_collection_key_down(self):
        import inspect
        self.assertIn("_delta_split(kind, value, memo_key=(ftype, name))", inspect.getsource(km._delta_parts))


SID = "44444444-5555-6666-7777-888888888801"      # private synthetic sids: this module mints goal stores
SID2 = "44444444-5555-6666-7777-888888888802"
PARENT = "44444444-5555-6666-7777-888888888803"
CHILD = "44444444-5555-6666-7777-888888888804"
SID3 = "44444444-5555-6666-7777-888888888805"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uline(t, text, uuid, parent=None):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "promptSource": "typed", "message": {"role": "user", "content": text}}


def aline(t, text, uuid, parent=None):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}],
                        "stop_reason": "end_turn"}}


def tmux_row(state="waiting", since=None):
    return {"state": state, "since": since, "model": "", "effort": "", "context": None,
            "compactPct": None, "color": None, "mode": ""}


def _reset(stats):
    for k in list(stats):
        stats[k] = 0


def move_ctime(path):
    """Move a file's ctime and nothing else: flip its mode until the stat's ctime differs (the clock's
    coarse tick can hand two chmods one timestamp). mtime, size and inode stand."""
    before = os.stat(path)
    deadline = time.monotonic() + 5
    while True:
        mode = before.st_mode & 0o777
        os.chmod(path, 0o600 if mode != 0o600 else 0o644)
        after = os.stat(path)
        if after.st_ctime_ns != before.st_ctime_ns:
            return after
        if time.monotonic() > deadline:
            raise AssertionError("ctime did not move under chmod")
        time.sleep(0.005)


# ── _derive_judging as it stood before the split (perf4-readers at 3781e0f8), the equality oracle ──
def ref_derive_judging(sid, caps, goals, t0, out, seg_ends=None):
    endt = (lambda tt: seg_ends.get(tt, tt)) if seg_ends else (lambda tt: tt)
    caps_in = sorted((c for c in caps.values() if c.get("t") and c["t"] >= t0), key=lambda c: c["t"])
    for c in caps_in[-km.JUDGE_CAP_LIMIT:]:
        out.append({"judge": "captioner", "sid": sid, "t": c["t"],
                    "kind": c.get("grain", "segment"), "text": c.get("caption", "")})
    for n in goals.get("nodes", {}).values():
        t = n.get("t")
        if not t:
            continue
        text = n.get("text", "")
        mt = n.get("mt") or t
        go = n.get("groupOp")
        if isinstance(go, dict) and (go.get("t") or 0) >= t0:
            out.append({"judge": "grouper", "sid": sid, "t": go["t"],
                        "kind": go.get("kind") or "group", "text": text})
        if n.get("origin"):
            if t >= t0:
                out.append({"judge": "courier", "sid": sid, "t": t, "kind": "plant", "text": text})
        elif n.get("umbrella"):
            if mt >= t0:
                out.append({"judge": "grouper", "sid": sid, "t": mt, "kind": "group", "text": text})
        elif t >= t0:
            out.append({"judge": "planner", "sid": sid, "t": t,
                        "kind": ("mint" if not n.get("parentId") else "sub"), "text": text})
        for _e in (n.get("log") or []):
            if _e.get("synth") or (_e.get("ev_t") or 0) < t0:
                continue
            if _e.get("src") in ("planner", "closer") and _e.get("kind") in ("done", "block"):
                out.append({"judge": _e["src"] if _e["src"] == "planner" else "closer", "sid": sid,
                            "t": endt(_e["ev_t"]),
                            "kind": ("done" if _e["src"] == "planner" else "close") if _e["kind"] == "done" else "block",
                            "text": _e.get("why") or text})
        if n.get("distilledMt") and n["distilledMt"] >= t0:
            out.append({"judge": "distiller", "sid": sid, "t": endt(n["distilledMt"]), "kind": "distill",
                        "text": n.get("summary") or text})
        if n.get("briefedMt") and n["briefedMt"] >= t0:
            out.append({"judge": "distiller", "sid": sid, "t": endt(n["briefedMt"]), "kind": "brief",
                        "text": n.get("blockSummary") or text})
    try:
        arch = json.loads((jd.STATE / "archive" / (sid + ".json")).read_text(errors="replace"))
        if arch.get("t") and arch["t"] >= t0:
            out.append({"judge": "archiver", "sid": sid, "t": arch["t"], "kind": "index",
                        "text": arch.get("headline", "")})
    except (OSError, ValueError):
        pass


class LaneMemoBase(unittest.TestCase):
    """A fresh state root per test, the memos emptied, one live lane SID with one finished turn."""

    def setUp(self):
        self._saved_state, self._saved_proj = jd.STATE, jd.PROJECTS
        self._td = tempfile.mkdtemp()
        jd._rebind_state(Path(self._td))
        jd.PROJECTS = Path(self._td) / "projects"
        jd._discover_cache.clear(); jd._PARSE_CACHE.clear(); jd._CHAIN_MEMO.clear()
        km._parse_cache.clear(); km._dismissed_lanes.clear(); km._BARS_COMPLAINED.clear()
        km._caps_memo.clear(); km._lanes_memo.clear(); _reset(km._lanes_stats)
        km._dead_lane_memo.clear()                   # upstream's dead-lane memo (2026-09-08): served first for a dead lane
        km._downtime[:] = []
        self.now = int(time.time())
        self.t0 = self.now - 600
        self.cdir = str(Path(self._td) / "work")
        self.proj = jd._proj_dir(self.cdir)
        self.proj.mkdir(parents=True, exist_ok=True)
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        self._saved = {nm: getattr(km, nm) for nm in (
            "_sdk", "_run_judging", "TL_HORIZON", "JUDGE_CAP_LIMIT", "_LANES_MEMO_MAX", "_lane_segments",
            "_segs_seam", "_derive_judging_marks", "_judging_assemble", "_captions", "_parse", "_merge_live_atoms")}
        self._saved_backend = km.Sessions.backend_for
        self._saved_file_key = jd._file_key
        km._sdk = lambda: None
        # the band carries THIS build's artifact marks, so the tests read what _judging_assemble emitted
        km._run_judging = lambda t0, alive, semantic: [dict(m) for m in semantic]
        self.recs = [uline(self.t0, "make the retry loop back off", "u1"),
                     aline(self.t0 + 20, "Added exponential backoff.", "a1", "u1")]
        self.add_lane(SID, "web", self.recs)

    def tearDown(self):
        for nm, v in self._saved.items():
            setattr(km, nm, v)
        km.Sessions.backend_for = self._saved_backend
        jd._file_key = self._saved_file_key
        jd._SHARED_OFF[0] = False
        km._lanes_memo.clear(); km._dead_lane_memo.clear()
        jd._rebind_state(self._saved_state)
        jd.PROJECTS = self._saved_proj
        shutil.rmtree(self._td, ignore_errors=True)

    # fixtures
    def tpath(self, sid=SID):
        return self.proj / (sid + ".jsonl")

    def add_lane(self, sid, name, recs):
        (jd.NAMES / sid).write_text("%s\t%s" % (name, self.cdir))
        self.tpath(sid).write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        jd._discover_cache.clear()

    def append_records(self, recs, sid=SID):
        with self.tpath(sid).open("a") as f:
            f.write("".join(json.dumps(r) + "\n" for r in recs))

    def seg_id(self, sid=SID):
        session = em.parse_session(str(self.tpath(sid)), rompuuid=sid, candidate_files=[str(self.tpath(sid))], now=self.now)
        return em.segments(session["turns"][0])[0]["id"]

    def mint_store(self, sid=SID, text="Back off the retries", t=None):
        """The wiring test's idiom: a store with one minted top, published by save_goals (a FrozenStore
        from load_goals_shared afterwards)."""
        s = jd.load_goals(sid)
        jd.apply_plan(s, "s1", t or self.t0, [{"do": "mint", "why": "x", "text": text}], [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(sid, s)
        return s

    def write_archive(self, t, headline, sid=SID):
        jd.ARCHDIR.mkdir(parents=True, exist_ok=True)
        (jd.ARCHDIR / (sid + ".json")).write_text(json.dumps({"t": t, "headline": headline}))

    def tmux(self, *sids):
        return {s: tmux_row(since=self.now - 100) for s in sids}

    def build(self, tmux=None, with_bars=True, live_only=False, now=None):
        return km.build_timeline(now if now is not None else self.now,
                                 self.tmux(SID) if tmux is None else tmux, with_bars=with_bars, live_only=live_only)

    def stats(self):
        return km._lanes_memo_report()

    def outcomes(self):
        st = self.stats()
        return {k: st[k] for k in ("hit", "miss", "live_tail", "complain_skip", "unshared_skip")}

    def dead(self):
        """The dead lanes' counters of the same block (build_timeline's, since the fold made this memo live-only)."""
        st = self.stats()
        return {k: st[k] for k in ("dead_serve", "dead_miss", "dead_failed_serve")}

    def parse_cache_holds(self, sid=SID):
        return any(p.endswith("/" + sid + ".jsonl") for p in km._parse_cache)

    def lane(self, tl, sid=SID):
        return next(l for l in tl["sessions"] if l["id"] == sid)

    def marks(self, tl, sid=SID, judge=None):
        return [m for m in tl["judging"] if m["sid"] == sid and (judge is None or m["judge"] == judge)]

    def spy_segments(self):
        calls = []
        real = self._saved["_lane_segments"]

        def spy(*a, **k):
            calls.append(a[0])
            return real(*a, **k)
        km._lane_segments = spy
        return calls


class HitsAndEquality(LaneMemoBase):
    def test_an_unchanged_lane_is_served_and_equals_the_uncached_loop(self):
        jd.append_caption(SID, self.seg_id(), "segment", self.t0, "Added backoff")
        self.mint_store()
        self.write_archive(self.now - 50, "retry loop")
        calls = self.spy_segments()
        tl1 = self.build()
        self.assertEqual(calls, [SID], "the first build derives the lane")
        tl2 = self.build()
        self.assertEqual(calls, [SID], "the second build derives nothing: a dict lookup served the lane")
        self.assertEqual(self.outcomes(), {"hit": 1, "miss": 1, "live_tail": 0, "complain_skip": 0, "unshared_skip": 0})
        self.assertIs(tl2["turns"][SID], tl1["turns"][SID], "the same bars list object rides into turns[sid]")
        # what the memo served is what the uncached loop returns NOW, on the same objects
        session = km._parse(str(self.tpath()), SID, self.now)
        goals = jd.load_goals_shared(SID)
        caps = km._captions(SID)
        bars, seg_ends, last_t, compactions, cap_marks, other_marks, nsegs, complained = km._lane_segments(
            SID, session, goals, caps, True, None)
        self.assertEqual(json.dumps(tl2["turns"][SID]), json.dumps(bars))
        self.assertEqual(json.dumps(tl2["sessions"]), json.dumps(tl1["sessions"]), "the badge row, per build, agrees")
        self.assertEqual(json.dumps(tl2["judging"]), json.dumps(tl1["judging"]))
        want = []
        km._derive_judging(SID, caps, goals, self.now - km.TL_HORIZON, want, seg_ends)
        self.assertEqual(json.dumps(tl2["judging"]), json.dumps(want), "the marks on a hit are the derivation's")
        self.assertEqual({m["judge"] for m in tl2["judging"]}, {"captioner", "planner", "archiver"})
        self.assertEqual(self.lane(tl2)["since"], self.now - 100, "a live lane's since is tmux's")
        st = self.stats()
        self.assertEqual((st["segs_hit"], st["segs_miss"], st["entries"]), (nsegs, nsegs, 1))
        self.assertEqual(nsegs, 1)

    def test_a_hit_lane_still_runs_the_parse_the_merge_and_the_captions_read(self):
        counts = {"parse": 0, "merge": 0, "caps": 0}
        real_parse, real_merge, real_caps = (self._saved["_parse"], self._saved["_merge_live_atoms"], self._saved["_captions"])
        km._parse = lambda *a, **k: (counts.__setitem__("parse", counts["parse"] + 1), real_parse(*a, **k))[1]
        km._merge_live_atoms = lambda *a, **k: (counts.__setitem__("merge", counts["merge"] + 1), real_merge(*a, **k))[1]
        km._captions = lambda *a, **k: (counts.__setitem__("caps", counts["caps"] + 1), real_caps(*a, **k))[1]
        self.build(); self.build()
        self.assertEqual(self.outcomes()["hit"], 1)
        self.assertEqual(counts, {"parse": 2, "merge": 2, "caps": 2},
                         "the chip needs the merged parse and prune_live must keep running: a hit skips only the loop")

    def test_prune_live_runs_on_a_hit_build(self):
        pruned = []
        # a live atom the transcript already holds (uuid a1, with its text): the merge prunes and returns
        # the parse object itself, so the lane hits, and the backend's prune ran on both builds
        twin = {"type": "assistant", "uuid": "a1", "t": self.t0 + 20, "session_id": SID, "fsid": None,
                "parentUuid": "u1", "message": {"role": "assistant", "stop_reason": "end_turn",
                                                "content": [{"type": "text", "text": "Added exponential backoff."}]}}

        class FakeBE:
            def live_atoms(self, sid):
                return [dict(twin)]

            def prune_live(self, sid, *a, **k):
                pruned.append(sid)
        km.Sessions.backend_for = lambda sid: FakeBE()
        self.build(); self.build()
        self.assertEqual(self.outcomes()["hit"], 1)
        self.assertEqual(pruned, [SID, SID], "prune_live ran on the hit build as on the miss")

    def test_the_held_bars_survive_the_postal_join_unchanged(self):
        tl = self.build()
        before = json.dumps(tl["turns"][SID])
        km._bind_message_execs([{"id": "m1", "toId": SID, "from": "api", "sent": self.t0 - 5, "pending": True}], tl["turns"])
        self.assertEqual(json.dumps(tl["turns"][SID]), before, "_bind_message_execs writes to the messages only")
        tl2 = self.build()
        self.assertIs(tl2["turns"][SID], tl["turns"][SID])
        self.assertEqual(json.dumps(tl2["turns"][SID]), before)


class EveryInputBusts(LaneMemoBase):
    """One test per input in _lanes_memo's comment: change only that input, observe a miss and the new content."""

    def test_a_transcript_append_moves_the_parse_object(self):
        tl1 = self.build()
        self.append_records([uline(self.t0 + 100, "and cap the delay", "u2", "a1"),
                             aline(self.t0 + 120, "Capped at two minutes.", "a2", "u2")])
        tl2 = self.build()
        self.assertEqual(self.outcomes()["miss"], 2)
        self.assertEqual(len(tl1["turns"][SID]), 1)
        self.assertEqual(len(tl2["turns"][SID]), 2, "the appended turn is a second bar")
        self.assertEqual(self.stats()["entries"], 1, "the new entry replaced the old")

    def test_a_states_write_moves_the_parse_object(self):
        # the states log is folded into the parse (idle atoms), and it is in _parse's key
        self.build()
        (jd.STATE / "states").mkdir(exist_ok=True)
        (jd.STATE / "states" / (SID + ".jsonl")).write_text(json.dumps({"t": self.t0 + 30, "state": "waiting"}) + "\n")
        self.build()
        self.assertEqual(self.outcomes()["miss"], 2)

    def test_a_store_publish_is_a_new_frozen_store(self):
        self.mint_store(text="First goal")
        tl1 = self.build()
        self.assertEqual([m["text"] for m in self.marks(tl1, judge="planner")], ["First goal"])
        s = jd.load_goals(SID)
        jd.apply_plan(s, "s2", self.t0 + 100, [{"do": "mint", "why": "x", "text": "Second goal"}], [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        tl2 = self.build()
        self.assertEqual(self.outcomes()["miss"], 2)
        self.assertEqual(sorted(m["text"] for m in self.marks(tl2, judge="planner")), ["First goal", "Second goal"])

    def test_a_journal_append_is_a_new_store_version(self):
        s = self.mint_store()
        nid = next(iter(s["nodes"]))
        self.build()
        jd.append_block(SID, nid, "nudge", "no answer to the status ask", self.now)
        self.build()
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 2, "live_tail": 0, "complain_skip": 0, "unshared_skip": 0})

    def test_a_captions_append_is_a_new_caps_object(self):
        seg = self.seg_id()
        jd.append_caption(SID, seg, "segment", self.t0, "first summary")
        tl1 = self.build()
        self.assertEqual(tl1["turns"][SID][0]["summary"], "first summary")
        jd.append_caption(SID, seg, "segment", self.t0, "second summary")
        tl2 = self.build()
        self.assertEqual(self.outcomes()["miss"], 2)
        self.assertEqual(tl2["turns"][SID][0]["summary"], "second summary")
        self.assertEqual([m["text"] for m in self.marks(tl2, judge="captioner")], ["second summary"])

    def test_a_caption_landing_between_the_read_and_the_build_misses_next_time(self):
        # THE HOLE the refuted form had: a stat of the captions file taken inside the derivation follows
        # _captions' read, so a row appended between the two is memoized under the NEW key and the stale
        # summary is served until another input moves. Keyed on the caps OBJECT (whose stat precedes its
        # read) the next build's fresh object misses and shows the row.
        seg = self.seg_id()
        jd.append_caption(SID, seg, "segment", self.t0, "first summary")
        real = self._saved["_captions"]
        leaked = []

        def leaky(fsid):
            caps = real(fsid)
            if not leaked:
                leaked.append(1)
                jd.append_caption(fsid, seg, "segment", self.t0, "landed after the read")
            return caps
        km._captions = leaky
        tl1 = self.build()
        self.assertEqual(tl1["turns"][SID][0]["summary"], "first summary", "the build read the file before the row landed")
        tl2 = self.build()
        self.assertEqual(self.outcomes()["miss"], 2, "a new caps object: the lane misses")
        self.assertEqual(tl2["turns"][SID][0]["summary"], "landed after the read")
        self.assertEqual([m["text"] for m in self.marks(tl2, judge="captioner")], ["landed after the read"])

    def test_an_archive_rewrite_moves_the_archive_key(self):
        self.write_archive(self.now - 50, "retry loop")
        tl1 = self.build()
        self.assertEqual([m["text"] for m in self.marks(tl1, judge="archiver")], ["retry loop"])
        self.write_archive(self.now - 40, "retry loop with a two minute cap")
        tl2 = self.build()
        self.assertEqual(self.outcomes()["miss"], 2)
        self.assertEqual([(m["t"], m["text"]) for m in self.marks(tl2, judge="archiver")],
                         [(self.now - 40, "retry loop with a two minute cap")])

    def test_an_archive_appearing_after_a_build_misses(self):
        tl1 = self.build()
        self.assertEqual(self.marks(tl1, judge="archiver"), [])
        self.write_archive(self.now - 50, "retry loop")
        tl2 = self.build()
        self.assertEqual(self.outcomes()["miss"], 2)
        self.assertEqual(len(self.marks(tl2, judge="archiver")), 1)

    def test_a_host_suspension_moves_the_downtime_tuple(self):
        self.build()
        km._downtime.append((self.now - 20000, self.now - 19000))        # a sleep outside every segment: same bars,
        self.build()                                                     # a different key
        self.assertEqual(self.outcomes()["miss"], 2)
        km._downtime[:] = [(self.now - 20000, self.now - 19000)]         # a rebind of the same content: the same key
        self.build()
        self.assertEqual(self.outcomes()["hit"], 1)
        km._downtime[:] = [(self.now - 20000, self.now - 18000)]         # the suite's slice-assign pattern moves it
        self.build()
        self.assertEqual(self.outcomes()["miss"], 3)
        self.assertEqual(self.stats()["entries"], 1)

    def test_a_suspension_inside_the_segment_splits_the_bar_on_the_next_build(self):
        self.build()
        km._downtime[:] = [(self.t0 + 5, self.t0 + 10)]
        tl = self.build()
        self.assertEqual(self.outcomes()["miss"], 2)
        self.assertEqual(len(tl["turns"][SID]), 2, "the bar is cut at the nap, on the very next build")

    def test_liveness_is_in_the_key(self):
        self.build(tmux=self.tmux(SID))
        tl = self.build(tmux={})                                         # the process ended: a dead lane (12 h window)
        self.assertFalse(self.lane(tl)["live"])
        # Re-aimed at the 2026-09-09 fold (the fork's timeline owner's ruling on upstream's #1131): this memo is
        # LIVE-ONLY, so the dead build never consults it and the live entry cannot serve the dead lane (before the
        # fold the key's `live` component made that build a second miss here). The dead lane is derived once by
        # _lane_segments directly (dead_miss) and handed to the dead-lane memo, whose populate drops the entry this
        # memo held from the lane's live days (it keys on the parse object the dead-lane memo lets go of).
        self.assertEqual(self.outcomes()["miss"], 1, "one miss, the live build's: a dead lane is not this memo's")
        self.assertEqual(self.dead(), {"dead_serve": 0, "dead_miss": 1, "dead_failed_serve": 0})
        self.assertIn(SID, km._dead_lane_memo, "the dead build handed the lane to the dead-lane memo")
        self.assertNotIn(SID, km._lanes_memo, "and this memo dropped the entry from the lane's live days, so the parse can go")
        served = km._VIEW_STATS.get("laneServe", 0)
        self.build(tmux={})
        self.assertEqual(km._VIEW_STATS.get("laneServe", 0), served + 1, "the third build is a dead-lane serve")
        self.assertEqual(self.dead()["dead_serve"], 1)
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 1, "live_tail": 0, "complain_skip": 0, "unshared_skip": 0},
                         "a dead lane is served without this memo")

    def test_an_open_turn_reads_open_only_on_a_live_lane(self):
        self.append_records([uline(self.t0 + 100, "keep going", "u2", "a1"),
                             {"type": "assistant", "timestamp": iso(self.t0 + 110), "uuid": "a2", "parentUuid": "u2",
                              "message": {"role": "assistant", "stop_reason": None,
                                          "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}}])
        tl_live = self.build(tmux=self.tmux(SID))
        tl_dead = self.build(tmux={})
        self.assertEqual(self.outcomes()["miss"], 1, "the live build's; the dead build is derived outside this memo")
        self.assertEqual(self.dead()["dead_miss"], 1)
        self.assertEqual([b["open"] for b in tl_live["turns"][SID]][-1], True)
        self.assertEqual([b["open"] for b in tl_dead["turns"][SID]][-1], False)

    def fork_fixture(self):
        """A parent lane and a child forked from it at fork_t: the child's transcript carries the parent's
        history verbatim, and the backend reports the fork. Returns fork_t."""
        fork_t = self.now - 300
        shared = [uline(self.now - 600, "how should the retry loop back off?", "u1"),
                  aline(self.now - 580, "Use exponential backoff.", "a1", "u1")]
        own = [uline(fork_t + 60, "and inside the fork?", "u9", "a1"),
               aline(fork_t + 80, "Cap the delay at two minutes.", "a9", "u9")]
        self.add_lane(PARENT, "parent", shared)
        self.add_lane(CHILD, "child", shared + own)
        kids = {PARENT: [{"sid": CHILD, "name": "child", "cut": "a1", "t": fork_t}]}

        class FakeBe:
            def fork_children(self):
                return kids

            def owns(self, sid):
                return False

            def pending_cut(self, sid):
                return ""

            def __getattr__(self, name):
                return lambda *a, **k: None
        km._sdk = lambda: FakeBe()
        return fork_t

    def test_a_parent_lane_leaving_the_build_moves_the_branch_clip(self):
        # The ORIGINAL aim, dead lanes, restored at the 2026-09-09 fold by the fork's timeline owner's ruling: a
        # dead lane is the dead-lane memo's, whose key carries the branch clip (fromId, t, cut), so the parent
        # leaving the build moves the child's key, the child is derived again without the clip and its bars
        # show the pre-fork segments. The memo counters are the dead lanes' (this memo never sees a dead lane).
        fork_t = self.fork_fixture()
        tl1 = self.build(tmux={})
        self.assertTrue(all(b["start"] > fork_t for b in tl1["turns"][CHILD]), "clipped while the parent is a lane")
        key1 = km._dead_lane_memo[CHILD][0]
        self.build(tmux={})
        (jd.NAMES / PARENT).unlink()                                     # the parent leaves the build: no name, no row
        jd._discover_cache.clear()
        tl3 = self.build(tmux={})
        self.assertNotIn(PARENT, {l["id"] for l in tl3["sessions"]})
        self.assertTrue(any(b["start"] < fork_t for b in tl3["turns"][CHILD]), "the whole story, the parent gone")
        self.assertNotEqual(km._dead_lane_memo[CHILD][0], key1, "the child's key moved with its clip")
        self.assertEqual(self.dead(), {"dead_serve": 4, "dead_miss": 4, "dead_failed_serve": 0},
                         "three dead misses, three serves, then the child's clip moved (one more miss) beside SID's serve")
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 0, "live_tail": 0, "complain_skip": 0, "unshared_skip": 0},
                         "dead lanes never touch this memo")
        self.assertEqual(self.stats()["entries"], 0)

    def test_a_parent_lane_leaving_the_build_moves_a_live_childs_branch_clip(self):
        # The same story on LIVE lanes, this memo's domain since the fold: the clip is in its key
        fork_t = self.fork_fixture()
        tl1 = self.build(tmux=self.tmux(SID, PARENT, CHILD))
        self.assertTrue(all(b["start"] > fork_t for b in tl1["turns"][CHILD]), "clipped while the parent is a lane")
        self.assertEqual(self.outcomes()["miss"], 3)
        self.build(tmux=self.tmux(SID, PARENT, CHILD))
        self.assertEqual(self.outcomes()["hit"], 3)
        (jd.NAMES / PARENT).unlink()                                     # the parent leaves the build: no name, no row
        jd._discover_cache.clear()
        tl3 = self.build(tmux=self.tmux(SID, CHILD))
        self.assertEqual(self.outcomes()["miss"], 4, "the child's clip moved: one more miss")
        self.assertEqual(self.outcomes()["hit"], 4, "SID's lane still hits")
        self.assertTrue(any(b["start"] < fork_t for b in tl3["turns"][CHILD]), "the whole story, the parent gone")
        self.assertEqual(self.stats()["evict"], 1, "the parent's entry left with its lane")
        self.assertEqual(self.stats()["entries"], 2)

    def test_the_badge_row_is_per_build_on_a_hit(self):
        tl1 = self.build()
        self.assertFalse(self.lane(tl1)["postalServiceOff"])
        km._set_session_flag(SID, "postalServiceOff", True)
        tl2 = self.build()
        self.assertEqual(self.outcomes()["hit"], 1, "a flag is a badge-row input, not a segment input")
        self.assertTrue(self.lane(tl2)["postalServiceOff"], "and the row carries it at once")


class DeadLanes(LaneMemoBase):
    """The fork's timeline owner's ruling at the 2026-09-09 fold: a dead lane bypasses this memo (its segment
    part is derived by _lane_segments directly and cached in the dead-lane memo), a failed dead parse is cached
    as an empty lane under a key that carries ctime, and the host's suspensions are in the dead-lane key."""

    def dead_build(self):
        return self.build(tmux={})                                       # nobody live: SID is a dead lane in the window

    def test_a_dead_miss_leaves_this_memo_and_the_parse_cache_empty_and_is_not_a_miss_here(self):
        tl = self.dead_build()
        self.assertEqual(len(tl["turns"][SID]), 1, "derived: the bar is drawn")
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 0, "live_tail": 0, "complain_skip": 0, "unshared_skip": 0},
                         "a dead lane is derived outside this memo: no miss, no store-then-pop")
        self.assertEqual(self.dead(), {"dead_serve": 0, "dead_miss": 1, "dead_failed_serve": 0})
        self.assertEqual(self.stats()["entries"], 0)
        self.assertNotIn(SID, km._lanes_memo)
        self.assertFalse(self.parse_cache_holds(), "the parse went with the populate (the resident-memory lever)")
        self.assertIn(SID, km._dead_lane_memo)
        self.assertEqual((self.stats()["segs_hit"], self.stats()["segs_miss"]), (0, 0), "the segment counters are the live lanes' too")
        tl2 = self.dead_build()
        self.assertEqual(self.dead(), {"dead_serve": 1, "dead_miss": 1, "dead_failed_serve": 0})
        self.assertEqual(tl2["turns"][SID], tl["turns"][SID])

    def test_a_failed_dead_parse_is_parsed_once_served_empty_and_re_attempted_when_the_stat_moves(self):
        parses, mode = [], ["fail"]
        real = self._saved["_parse"]

        def parse(path, sid, now):
            parses.append(path)
            if mode[0] == "fail":
                raise OSError("unreadable")
            return real(path, sid, now)
        km._parse = parse
        err = io.StringIO()
        with redirect_stderr(err):
            tl1 = self.dead_build()
            tl2 = self.dead_build()
        self.assertEqual(len(parses), 1, "parsed once: a dead transcript has no writer, so the failed parse is cached")
        self.assertEqual(tl1["turns"][SID], [])
        self.assertEqual(tl2["turns"][SID], [], "served as the empty lane it drew")
        self.assertEqual(self.lane(tl2), self.lane(tl1))
        self.assertTrue(km._dead_lane_memo[SID][1]["failed"], "the entry says its parse failed")
        self.assertEqual(self.dead(), {"dead_serve": 0, "dead_miss": 1, "dead_failed_serve": 1})
        self.assertEqual(err.getvalue().count("parse failed"), 1, "_bars_complain said so once")
        self.assertEqual(self.outcomes()["complain_skip"], 0, "not this memo's outcome: a dead lane")
        # a chmod moves the transcript's ctime alone (mtime and size stand): the key moves and the parse is
        # attempted again, and a readable file draws its bar
        mode[0] = "ok"
        move_ctime(self.tpath())
        with redirect_stderr(err):
            tl3 = self.dead_build()
        self.assertEqual(len(parses), 2, "re-attempted once the stat moved")
        self.assertEqual(len(tl3["turns"][SID]), 1, "readable again: the bar is drawn")
        self.assertFalse(km._dead_lane_memo[SID][1]["failed"])
        self.assertEqual(self.dead(), {"dead_serve": 0, "dead_miss": 2, "dead_failed_serve": 1})
        with redirect_stderr(err):
            self.dead_build()
        self.assertEqual(len(parses), 2)
        self.assertEqual(self.dead()["dead_serve"], 1)

    def test_a_chmod_alone_moves_the_stat_key(self):
        p = str(self.tpath())
        k0 = km._stat_key(p)
        move_ctime(p)
        k1 = km._stat_key(p)
        self.assertNotEqual(k0, k1, "ctime is in the key: a chmod or a rename moves it")
        self.assertEqual(k0[:3], k1[:3], "mtime, size and inode stood")
        self.assertIsNone(km._stat_key(p + ".absent"))

    def test_a_seams_or_marks_complaint_on_a_dead_lane_is_derived_every_build_not_cached(self):
        # the narrowing of upstream's cache-a-failure rule to the PARSE stage: a complaint the lane says every
        # build (seams, judging marks) is never served from the dead-lane memo
        km._segs_seam = lambda turn, store: (_ for _ in ()).throw(ValueError("malformed seam"))
        with redirect_stderr(io.StringIO()):
            tl = self.dead_build(); self.dead_build()
        self.assertNotIn(SID, km._dead_lane_memo, "a seams complaint is not cached")
        self.assertEqual(len(tl["turns"][SID]), 1, "the seams fell back to em.segments; the bar still draws")
        self.assertEqual(self.dead(), {"dead_serve": 0, "dead_miss": 2, "dead_failed_serve": 0})
        km._segs_seam = self._saved["_segs_seam"]
        km._derive_judging_marks = lambda *a, **k: (_ for _ in ()).throw(KeyError("t"))
        with redirect_stderr(io.StringIO()):
            tl = self.dead_build(); self.dead_build()
        self.assertNotIn(SID, km._dead_lane_memo, "a marks complaint is not cached")
        self.assertEqual(tl["judging"], [], "this lane lost its marks; the frame shipped")
        self.assertEqual(self.dead()["dead_miss"], 4)
        self.assertEqual(self.outcomes()["complain_skip"], 0, "dead lanes are not this memo's")

    def test_a_host_suspension_re_derives_a_cached_dead_lane(self):
        # without tuple(_downtime) in the dead-lane key a suspension recorded after the lane was cached left its
        # un-excised bar served until a keyed file moved, and a dead transcript never moves
        self.dead_build()
        key0 = km._dead_lane_memo[SID][0]
        km._downtime[:] = [(self.t0 + 5, self.t0 + 10)]                  # a nap inside the segment
        tl = self.dead_build()
        self.assertEqual(len(tl["turns"][SID]), 2, "the bar is cut at the nap on the very next build")
        self.assertNotEqual(km._dead_lane_memo[SID][0], key0, "the suspensions are in the key")
        self.assertEqual(self.dead(), {"dead_serve": 0, "dead_miss": 2, "dead_failed_serve": 0})
        km._downtime.append((self.now - 20000, self.now - 19000))        # a sleep outside every segment: same bars,
        tl3 = self.dead_build()                                          # a different key
        self.assertEqual(self.dead()["dead_miss"], 3)
        self.assertEqual(json.dumps(tl3["turns"][SID]), json.dumps(tl["turns"][SID]))
        km._downtime[:] = [(self.t0 + 5, self.t0 + 10), (self.now - 20000, self.now - 19000)]   # the same content, rebound
        self.dead_build()
        self.assertEqual(self.dead(), {"dead_serve": 1, "dead_miss": 3, "dead_failed_serve": 0}, "the same suspensions: served")

    def test_a_dead_lane_with_a_faulted_store_is_derived_every_build(self):
        # upstream's rule stands beside the fork's routing: no store, no cache, and the derivation is a dead miss
        real = jd.load_goals_shared_or_fault
        jd.load_goals_shared_or_fault = lambda sid: (None, OSError("store unreadable"))
        try:
            with redirect_stderr(io.StringIO()):
                tl = self.dead_build(); self.dead_build()
        finally:
            jd.load_goals_shared_or_fault = real
        self.assertNotIn(SID, km._dead_lane_memo)
        self.assertEqual(len(tl["turns"][SID]), 1, "drawn without goal-derived data")
        self.assertEqual(self.dead(), {"dead_serve": 0, "dead_miss": 2, "dead_failed_serve": 0})


class NotHeld(LaneMemoBase):
    def test_a_live_tail_is_derived_and_not_held(self):
        fresh = {"type": "assistant", "uuid": "live-1", "t": self.t0 + 40, "session_id": SID, "fsid": None,
                 "parentUuid": "a1", "message": {"role": "assistant", "stop_reason": None,
                                                 "content": [{"type": "text", "text": "Streaming a reply."}]}}

        class FakeBE:
            def live_atoms(self, sid):
                return [dict(fresh)]

            def prune_live(self, *a, **k):
                pass
        km.Sessions.backend_for = lambda sid: FakeBE()
        tl1 = self.build()
        tl2 = self.build()
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 0, "live_tail": 2, "complain_skip": 0, "unshared_skip": 0})
        self.assertEqual(self.stats()["entries"], 0, "a merged tail is a new object every build: nothing to hold")
        self.assertEqual(tl1["turns"][SID][0]["end"], self.t0 + 40, "the live atom extends the bar")
        self.assertIsNot(tl2["turns"][SID], tl1["turns"][SID])

    def test_a_private_store_with_content_is_not_held(self):
        self.mint_store()
        jd._SHARED_OFF[0] = True                                          # the cache is off: load_goals' private store
        try:
            tl = self.build(); self.build()
            self.assertEqual(self.outcomes(), {"hit": 0, "miss": 0, "live_tail": 0, "complain_skip": 0, "unshared_skip": 2})
            self.assertEqual(self.stats()["entries"], 0)
            self.assertEqual(len(self.marks(tl, judge="planner")), 1, "derived all the same")
        finally:
            jd._SHARED_OFF[0] = False

    def test_a_lane_without_a_store_hits_under_the_empty_rule(self):
        self.assertFalse((jd.GOALDIR / (SID + ".json")).exists())
        self.build(); self.build()
        self.assertEqual(self.outcomes()["hit"], 1, "no seams, no nodes: the store's identity does not matter")
        self.mint_store()
        self.build()
        self.assertEqual(self.outcomes()["miss"], 2, "a published store is a new input")

    def test_a_lane_without_captions_hits_under_the_empty_rule(self):
        self.assertFalse((jd.CAPDIR / (SID + ".jsonl")).exists())
        self.build(); self.build()
        self.assertEqual(self.outcomes()["hit"], 1)
        self.assertEqual(self.stats()["entries"], 1)

    def test_a_complaining_seams_stage_is_not_held(self):
        km._segs_seam = lambda turn, store: (_ for _ in ()).throw(ValueError("malformed seam"))
        err = io.StringIO()
        with redirect_stderr(err):
            tl = self.build(); self.build()
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 0, "live_tail": 0, "complain_skip": 2, "unshared_skip": 0})
        self.assertEqual(self.stats()["entries"], 0)
        self.assertEqual(len(tl["turns"][SID]), 1, "the seams fell back to em.segments; the bar still draws")
        self.assertIn("seams failed", err.getvalue())

    def test_a_complaining_marks_stage_is_not_held(self):
        km._derive_judging_marks = lambda *a, **k: (_ for _ in ()).throw(KeyError("t"))
        err = io.StringIO()
        with redirect_stderr(err):
            tl = self.build(); self.build()
        self.assertEqual(self.outcomes()["complain_skip"], 2)
        self.assertEqual(self.stats()["entries"], 0)
        self.assertEqual(len(tl["turns"][SID]), 1)
        self.assertEqual(tl["judging"], [], "this lane lost its marks; the frame shipped")
        self.assertIn("judging-marks failed", err.getvalue())

    def test_a_caption_row_with_a_string_time_costs_the_marks_not_the_frame(self):
        # The horizon comparisons run at assembly, outside the lane's guard; a time they cannot compare
        # must fail the marks stage at derivation (not memoized, the lane says so) instead of raising out
        # of build_timeline on every build (review 2026-09-07: _push's cycle-level except would then drop
        # the feed and bars slots every cycle until the data changed).
        seg = self.seg_id()
        jd.CAPDIR.mkdir(parents=True, exist_ok=True)
        (jd.CAPDIR / (SID + ".jsonl")).write_text(
            json.dumps({"id": seg, "grain": "segment", "t": "not a number", "caption": "typed time"}) + "\n")
        err = io.StringIO()
        with redirect_stderr(err):
            tl1 = self.build()
            tl2 = self.build()
        for tl in (tl1, tl2):
            self.assertEqual(len(tl["turns"][SID]), 1, "the lane is drawn")
            self.assertEqual(tl["turns"][SID][0]["summary"], "typed time", "the caption itself still serves the bar")
            self.assertEqual(tl["judging"], [], "the lane is mark-less")
        self.assertEqual(self.outcomes()["complain_skip"], 2, "not memoized: the miss and the following build both derive")
        self.assertEqual(self.stats()["entries"], 0)
        self.assertIn("judging-marks failed", err.getvalue())

    def test_an_archive_with_a_string_time_costs_the_marks_not_the_frame(self):
        jd.ARCHDIR.mkdir(parents=True, exist_ok=True)
        (jd.ARCHDIR / (SID + ".json")).write_text(json.dumps({"t": "soon", "headline": "h"}))
        err = io.StringIO()
        with redirect_stderr(err):
            tl1 = self.build()
            tl2 = self.build()
        for tl in (tl1, tl2):
            self.assertEqual(len(tl["turns"][SID]), 1)
            self.assertEqual(tl["judging"], [])
        self.assertEqual(self.outcomes()["complain_skip"], 2)
        self.assertIn("judging-marks failed", err.getvalue())

    def test_the_assembly_is_guarded_per_lane_at_its_call_site(self):
        km._judging_assemble = lambda *a, **k: (_ for _ in ()).throw(TypeError("unorderable"))
        try:
            err = io.StringIO()
            with redirect_stderr(err):
                tl = self.build()
            self.assertEqual(len(tl["turns"][SID]), 1, "the frame ships with the lane's bars")
            self.assertEqual(tl["judging"], [])
            self.assertIn("judging-marks failed", err.getvalue())
        finally:
            km._judging_assemble = self._saved["_judging_assemble"]

    def test_a_failed_parse_is_not_held(self):
        km._parse = lambda path, sid, now: (_ for _ in ()).throw(OSError("unreadable"))
        err = io.StringIO()
        with redirect_stderr(err):
            tl = self.build(); self.build()
        self.assertEqual(self.outcomes()["complain_skip"], 2)
        self.assertEqual(self.stats()["entries"], 0)
        self.assertEqual(tl["turns"][SID], [])
        self.assertIn("parse failed", err.getvalue())

    def test_a_failed_archive_stat_stores_nothing(self):
        real = self._saved_file_key
        arch = str(jd.STATE / "archive" / (SID + ".json"))
        jd._file_key = lambda p: object() if p == arch else real(p)
        self.build(); self.build()
        self.assertEqual(self.outcomes()["miss"], 2, "a sentinel matches nothing")
        self.assertEqual(self.stats()["entries"], 0, "and nothing is stored under it")

    def test_the_skeleton_build_bypasses_the_memo(self):
        self.build(with_bars=False)
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 0, "live_tail": 0, "complain_skip": 0, "unshared_skip": 0})
        self.assertEqual(self.stats()["entries"], 0)
        self.build(with_bars=True)
        self.assertEqual(self.outcomes()["miss"], 1)
        self.build(with_bars=False)
        self.assertEqual(self.outcomes(), {"hit": 0, "miss": 1, "live_tail": 0, "complain_skip": 0, "unshared_skip": 0})
        self.assertEqual(self.stats()["entries"], 1, "a skeleton neither reads nor evicts")


class ClockAtAssembly(LaneMemoBase):
    def test_a_caption_row_without_a_time_is_dropped_on_a_hit_as_on_a_miss(self):
        seg = self.seg_id()
        jd.CAPDIR.mkdir(parents=True, exist_ok=True)
        (jd.CAPDIR / (SID + ".jsonl")).write_text(
            json.dumps({"id": seg + "#p", "grain": "prompt", "caption": "no time on this row"}) + "\n"
            + json.dumps({"id": seg, "grain": "segment", "t": self.t0, "caption": "timed"}) + "\n")
        tl1 = self.build()
        tl2 = self.build()
        self.assertEqual(self.outcomes()["hit"], 1)
        for tl in (tl1, tl2):
            self.assertEqual([m["text"] for m in self.marks(tl, judge="captioner")], ["timed"])
            self.assertEqual(tl["turns"][SID][0]["msgCaption"], "no time on this row", "the caption itself still serves")

    def test_the_horizon_applies_per_build_on_a_hit(self):
        jd.append_caption(SID, self.seg_id(), "segment", self.now - 3000, "an older caption")
        tl1 = self.build()
        self.assertEqual(len(self.marks(tl1, judge="captioner")), 1)
        km.TL_HORIZON = 1000                                              # the horizon moves past the mark
        tl2 = self.build()
        self.assertEqual(self.outcomes()["hit"], 1, "no re-derivation: the horizon is applied at assembly")
        self.assertEqual(self.marks(tl2, judge="captioner"), [])

    def test_the_caption_cap_applies_per_build_on_a_hit(self):
        seg = self.seg_id()
        for i in range(3):
            jd.append_caption(SID, seg + ("" if i == 0 else "#p%d" % i), "segment", self.t0 + i, "caption %d" % i)
        tl1 = self.build()
        self.assertEqual(len(self.marks(tl1, judge="captioner")), 3)
        km.JUDGE_CAP_LIMIT = 1
        tl2 = self.build()
        self.assertEqual(self.outcomes()["hit"], 1)
        self.assertEqual([m["text"] for m in self.marks(tl2, judge="captioner")], ["caption 2"], "the newest survives the cap")

    def test_the_derivation_reads_no_clock(self):
        for fn in (km._lane_segments, km._derive_judging_marks):
            tree = ast.parse(inspect.getsource(fn))                      # identifiers, not prose: comments say "now" too
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            self.assertFalse(names & {"now", "time", "TL_HORIZON", "JUDGE_CAP_LIMIT"}, "%s: %r" % (fn.__name__, names))
        src = inspect.getsource(km._judging_assemble)
        self.assertIn("JUDGE_CAP_LIMIT", src, "the cap is read at assembly")
        src = inspect.getsource(km.build_timeline)
        self.assertIn("_judging_assemble(cap_marks, other_marks, now - TL_HORIZON, semantic)", src)
        self.assertIn("_lanes_forget(set(id2name))", src)
        self.assertRegex(src, r"if with_bars and not live_only:\s*\n(\s*#[^\n]*\n)*\s*_caps_forget\([^\n]*\n\s*_lanes_forget\(",
                         "eviction rides the full build beside the captions memo's")


class Eviction(LaneMemoBase):
    def test_entries_leave_with_their_lanes_and_a_live_only_build_evicts_nothing(self):
        self.add_lane(SID2, "api", self.recs)
        self.build(tmux=self.tmux(SID, SID2))
        self.assertEqual(self.stats()["entries"], 2)
        self.build(tmux=self.tmux(SID), live_only=True)                  # SID2 is not in a live-only build
        self.assertEqual(self.stats()["entries"], 2, "a live-only build reads a subset of the lanes and must not evict")
        self.assertEqual(self.stats()["evict"], 0)
        (jd.NAMES / SID2).unlink()
        jd._discover_cache.clear()
        self.build(tmux=self.tmux(SID))
        self.assertEqual(self.stats()["entries"], 1)
        self.assertEqual(self.stats()["evict"], 1)
        self.assertEqual(set(km._lanes_memo), {SID})

    def test_the_memo_is_bounded_least_recently_served_first(self):
        self.add_lane(SID2, "api", self.recs)
        km._LANES_MEMO_MAX = 2
        self.build(tmux=self.tmux(SID, SID2))                            # SID, then SID2, held
        self.assertEqual(set(km._lanes_memo), {SID, SID2})
        self.build(tmux=self.tmux(SID), live_only=True)                  # SID served: now the most recently served
        self.assertEqual(self.outcomes()["hit"], 1)
        self.add_lane(SID3, "tests", self.recs)                          # a third lane (added now: a fresh transcript
        self.build(tmux=self.tmux(SID3), live_only=True)                 # would be a dead lane of the first build)
        self.assertEqual(set(km._lanes_memo), {SID, SID3}, "SID2, the least recently served, went; the served SID stayed")
        self.assertEqual(self.stats()["evict"], 1)
        self.assertEqual(self.stats()["entries"], 2)

    def test_an_entry_whose_parse_left_the_cache_is_dropped_when_its_lane_cannot_hold(self):
        self.build()
        self.assertEqual(self.stats()["entries"], 1)
        self.append_records([uline(self.t0 + 100, "and cap the delay", "u2", "a1")])   # a new parse object
        km._parse = lambda path, sid, now: (_ for _ in ()).throw(OSError("unreadable"))   # and the parse fails
        with redirect_stderr(io.StringIO()):
            self.build()
        self.assertEqual(self.stats()["entries"], 0, "the old entry held a parse the cache no longer serves")


class DerivationSplit(unittest.TestCase):
    """_derive_judging_marks + _judging_assemble emit what _derive_judging emitted in one pass."""

    def setUp(self):
        self._saved_state = jd.STATE
        self._td = tempfile.mkdtemp()
        jd._rebind_state(Path(self._td))
        self.now = 1781100000
        self.sid = SID

    def tearDown(self):
        jd._rebind_state(self._saved_state)
        shutil.rmtree(self._td, ignore_errors=True)

    def fixture(self, timeless=False):
        now = self.now
        caps = {"c%d" % i: {"id": "c%d" % i, "grain": "segment" if i % 2 else "turn", "t": now - 9000 + i * 100,
                            "caption": "c%d" % i} for i in range(km.JUDGE_CAP_LIMIT + 10)}
        caps["tie"] = {"id": "tie", "grain": "segment", "t": now - 9000 + 100, "caption": "tie"}   # equal t: stable order
        caps["none"] = {"id": "none", "grain": "segment", "caption": "no t"}
        nodes = {
            "g1": {"id": "g1", "parentId": None, "t": now - 8000, "mt": now - 7000, "text": "Top",
                   "log": [{"src": "planner", "kind": "done", "ev_t": now - 7000, "why": "shipped"},
                           {"src": "closer", "kind": "done", "ev_t": now - 6500},
                           {"src": "closer", "kind": "block", "ev_t": now - 6000, "why": "waiting"},
                           {"src": "planner", "kind": "done", "ev_t": now - 5000, "synth": True},
                           {"src": "user", "kind": "done", "ev_t": now - 4000}],
                   "distilledMt": now - 7000, "summary": "the takeaway", "briefedMt": now - 6000, "blockSummary": "the brief"},
            "g2": {"id": "g2", "parentId": "g1", "t": now - 7500, "text": "Step"},
            "g3": {"id": "g3", "parentId": None, "t": now - 3000, "text": "Planted", "origin": {"peer": "x"}},
            "g4": {"id": "g4", "parentId": None, "t": now - 2000, "mt": now - 1500, "text": "Umbrella", "umbrella": True},
            "g5": {"id": "g5", "parentId": None, "t": now - 1000, "text": "Merged", "groupOp": {"t": now - 900, "kind": "merge"}},
            "g6": {"id": "g6", "parentId": None, "text": "no t"},
        }
        if timeless:
            nodes["g7"] = {"id": "g7", "parentId": None, "t": now - 500, "text": "timeless op", "groupOp": {"kind": "retitle"},
                           "log": [{"src": "planner", "kind": "done"}]}
        jd.ARCHDIR.mkdir(parents=True, exist_ok=True)
        (jd.ARCHDIR / (self.sid + ".json")).write_text(json.dumps({"t": now - 300, "headline": "h"}))
        seg_ends = {now - 7000: now - 6900, now - 6000: now - 5900}
        return caps, {"nodes": nodes}, seg_ends

    def test_equal_to_the_one_pass_form_at_every_horizon(self):
        caps, goals, seg_ends = self.fixture()
        for t0 in (0, self.now - 100000, self.now - 6500, self.now - 6000, self.now - 1000, self.now - 250, self.now + 1):
            for se in (seg_ends, None):
                want, got = [], []
                ref_derive_judging(self.sid, caps, goals, t0, want, se)
                km._derive_judging(self.sid, caps, goals, t0, got, se)
                self.assertEqual(json.dumps(got), json.dumps(want), "t0=%r seg_ends=%r" % (t0, se))
                cap_marks, other = km._derive_judging_marks(self.sid, caps, goals, se)
                out = []
                km._judging_assemble(cap_marks, other, t0, out)
                self.assertEqual(json.dumps(out), json.dumps(want))
        self.assertEqual(len([m for m in want if m["judge"] == "captioner"]), 0, "the last horizon dropped every caption")

    def test_a_timeless_group_op_or_diary_row_is_dropped_as_the_one_pass_form_dropped_it(self):
        caps, goals, seg_ends = self.fixture(timeless=True)
        for t0 in (self.now - 100000, self.now - 250):
            want, got = [], []
            ref_derive_judging(self.sid, caps, goals, t0, want, seg_ends)
            km._derive_judging(self.sid, caps, goals, t0, got, seg_ends)
            self.assertEqual(json.dumps(got), json.dumps(want))
            self.assertFalse(any(m["kind"] == "retitle" for m in got))

    def test_the_marks_are_derived_once_and_filtered_per_horizon(self):
        caps, goals, seg_ends = self.fixture()
        cap_marks, other = km._derive_judging_marks(self.sid, caps, goals, seg_ends)
        self.assertEqual(len(cap_marks), km.JUDGE_CAP_LIMIT + 11, "every timed caption, no cap yet")
        self.assertEqual([m["t"] for m in cap_marks], sorted(m["t"] for m in cap_marks))
        fts = [ft for ft, m in other]
        self.assertIn(self.now - 7000, fts, "a completion's filter time is the diary's ev_t")
        done = next(m for ft, m in other if m["judge"] == "planner" and m["kind"] == "done")
        self.assertEqual(done["t"], self.now - 6900, "while its plotted t is the segment's work end")


class PerfWiring(LaneMemoBase):
    def test_the_memo_reports_under_perf_memos_lanes(self):
        self.build(); self.build()
        blk = km._PERF_STATS.snapshot()["memos"]["lanes"]
        self.assertEqual(set(blk), {"hit", "miss", "live_tail", "complain_skip", "unshared_skip", "evict", "entries",
                                    "segs_hit", "segs_miss", "dead_serve", "dead_miss", "dead_failed_serve"})
        self.assertEqual((blk["hit"], blk["miss"], blk["entries"], blk["segs_hit"], blk["segs_miss"]), (1, 1, 1, 1, 1))
        self.assertEqual((blk["dead_serve"], blk["dead_miss"], blk["dead_failed_serve"]), (0, 0, 0), "live lanes only so far")
        self.build(tmux={}); self.build(tmux={})
        blk = km._PERF_STATS.snapshot()["memos"]["lanes"]
        self.assertEqual((blk["dead_serve"], blk["dead_miss"], blk["dead_failed_serve"]), (1, 1, 0), "the dead lanes ride the same block")
        self.assertEqual((blk["hit"], blk["miss"]), (1, 1), "and leave the live counters alone")
        self.assertIn('("lanes", _lanes_memo_report)', inspect.getsource(km._PerfStats.snapshot))


if __name__ == "__main__":
    unittest.main()
