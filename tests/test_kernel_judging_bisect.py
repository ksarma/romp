#!/usr/bin/env python3
"""_run_judging answers what the reference scan answered, on upstream's judging band memo (romp-on/romp pull
1798, folded 2026-09-17) as it did on the fork's bisect (round-4 item B, 2026-09-07), and the gloss keeps its bisect and
its NaN guard.

The fork's bisect started the horizon walk at bisect_left over the row times, backed off by a 2 s slack, when the
reader's order fact held (`monotone` on the `_JudgeUsageSnapshot` the reader returned, `hi` the running maximum, one
stderr line at the transition, a full scan otherwise). Upstream's memo covers the same purpose with no ordering
assumption: a cursor over the leading rows each verified to end before the horizon, per-row entry reuse validated on
the gloss by value, keyed on the identity of the reader's live list and shifted by its `pruned` count. The two cannot
coexist (the cursor needs the same list object across builds, and the fork's snapshot copy per read reset it every
build), so the bisect, the snapshot class, the slack and the reader's flag retired at the fold and _judge_usage_rows
returns its live list under the fork's lock. What stands of the fork's change is the gloss's bisect (bisect_right on
the sorted mark times: the newest same-judge mark with t <= end + 1, ties to the last) and its NaN guard (a NaN run
end passes the horizon filter, since NaN < t0 is False, and bisect_right on NaN would answer the newest mark where
the scan's <= matched none).

Two classes pin what holds now. RunJudgingBisect compares the kernel's answer with a private copy of the pre-bisect
function, list for list, in the same order: a mixed file with live runs, the horizon edges, empty and missing files,
growth between calls (the memo's cursor at work), more than the row cap, the gloss rule and its NaN case. SourcePins
pins the shared reader call and the gloss's bisect_right at source. The memo's own contract (entry identity, the
cursor, prunes and rotations, the wire bound, the /perf block) is tests/test_judging_band_memo.py's.

Retired at the fold with twin tests/test_judging_band_memo.py (the catch-up fold's ruling 4, 2026-09-17; a retirement
is never silent), each named: the ReaderOrderFlag class whole (nine cases on the reader's `monotone` flag and `hi`
running maximum: the ordered file, disorder within and past the slack, a non-numeric t, a NaN t or run end named on
stderr, a run end past t + 1, empty and missing files, growth and rewrites, the flag travelling with its snapshot);
RunJudgingBisect.test_a_non_monotone_file_takes_the_full_scan_and_matches (the flag's fallback path; its NaN rows are
test_a_nan_run_end_borrows_no_gloss's claim); test_disorder_within_the_slack_at_the_horizon_is_bisected_exactly (the
slack); test_the_walk_starts_at_the_horizon_when_the_flag_holds (the access-count proof of the horizon start; twin
Cursor.test_rows_before_the_horizon_are_not_read_again); test_a_bare_list_or_an_unflagged_snapshot_walks_from_the_head
(the unflagged walk over `_JudgeUsageSnapshot`, which is gone); _Base._check's `snap.monotone` assertion and its
`expect_monotone` parameter; SourcePins' bisect_left assert and its assert that the gloss comprehension text is gone
(upstream's gloss comment quotes the comprehension it replaced), the case renamed for what it pins; and the
_CountingRow helper the two access-count cases used.
Synthetic rows only (placeholder ids); the fsids here are private to this module."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_jbisect", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID_A = "aaaaaaaa-1111-4111-8111-111111111111"
SID_B = "bbbbbbbb-2222-4222-8222-222222222222"
SID_DEAD = "dddddddd-3333-4333-8333-333333333333"
ALIVE = {SID_A, SID_B}
T0 = 1_781_100_000          # the horizon; rows sit around it


def _reference_run_judging(t0, alive_sids, semantic, rows, runs, now):
    """The pre-bisect _run_judging (main at 1e829313), verbatim except that the rows, the in-flight runs and
    `now` are parameters. Every equivalence test compares the kernel's answer with this one."""
    by = {}
    for mk in semantic:
        by.setdefault((mk["sid"], mk["judge"]), []).append(mk)
    for v in by.values():
        v.sort(key=lambda m: m["t"])
    out = []
    done = set()
    for o in rows:
        sid, judge = o.get("fsid"), o.get("judge")
        judge = km._JUDGE_FAMILY.get(judge, judge)
        if sid not in alive_sids:
            continue
        sent, recv, lt = o.get("sent"), o.get("recv"), o.get("t")
        start = sent if isinstance(sent, (int, float)) else lt
        end = recv if isinstance(recv, (int, float)) else start
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end < t0:
            continue
        if isinstance(sent, (int, float)):
            done.add((sid, judge, sent))
        cands = [m for m in by.get((sid, judge), []) if m["t"] <= end + 1]
        src = cands[-1] if cands else None
        out.append({"judge": judge, "sid": sid, "t": start, "t1": end,
                    "kind": (src or {}).get("kind", "run"), "text": (src or {}).get("text", ""),
                    "ms": int(o.get("ms") or 0), "in": int(o.get("in") or 0), "out": int(o.get("out") or 0),
                    "sent": sent, "recv": recv})
    for run in runs:
        sid, judge, sent = run.get("fsid"), run.get("judge"), run.get("sent")
        judge = km._JUDGE_FAMILY.get(judge, judge)
        if sid not in alive_sids or not isinstance(sent, (int, float)):
            continue
        if sent < t0 or (sid, judge, sent) in done:
            continue
        cands = [m for m in by.get((sid, judge), []) if m["t"] <= now + 1]
        src = cands[-1] if cands else None
        out.append({"judge": judge, "sid": sid, "t": sent, "t1": now,
                    "kind": (src or {}).get("kind", "run"), "text": (src or {}).get("text", ""),
                    "ms": 0, "in": 0, "out": 0, "sent": sent, "recv": None, "open": True})
    if len(out) > km._JUDGING_ROW_CAP:
        out.sort(key=lambda m: m["t"])
        del out[:len(out) - km._JUDGING_ROW_CAP]
    return out


def _row(t, sid=SID_A, judge="captioner", sent="auto", recv="auto", **extra):
    """One usage row the way the writer stamps it: sent < recv <= t + 1, t = int(recv) unless given.
    sent=None / recv=None leave the field out (a pre-recording row)."""
    o = {"t": t, "judge": judge, "fsid": sid, "ms": 700, "in": 40, "out": 9}
    if recv == "auto":
        recv = t + 0.5                                   # .5 and .25 are exact in binary: the
    if sent == "auto":                                   # end + 1 comparisons below are equalities
        sent = (recv if recv is not None else t) - 3.25
    if sent is not None:
        o["sent"] = sent
    if recv is not None:
        o["recv"] = recv
    o.update(extra)
    return o


def _mark(t, sid=SID_A, judge="captioner", text="", kind="segment"):
    return {"judge": judge, "sid": sid, "t": t, "kind": kind, "text": text}


class _FrozenTime:
    """The kernel module's `time` global with time() pinned: _run_judging's `now` for the live-run spans
    must equal the reference's. Scoped to the kernel module, not the process."""
    def __init__(self, real, now):
        self._real, self._now = real, now

    def __getattr__(self, name):
        return getattr(self._real, name)

    def time(self):
        return self._now


class _Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[], pruned=0)
        km._judging_band = None                            # the band memo starts cold; a test's own calls warm it
        self._time = km.time
        km.time = _FrozenTime(km.time, float(T0 + 3600))

    def tearDown(self):
        km.time = self._time
        jd.STATE = self.saved
        jd._active.clear()                               # the in-flight registry is module-level
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[], pruned=0)
        km._judging_band = None
        self.td.cleanup()

    def _write(self, rows, mode="w"):
        with open(jd.STATE / "judge-usage.jsonl", mode) as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def _reference(self, t0, semantic):
        rows = [json.loads(ln) for ln in (jd.STATE / "judge-usage.jsonl").read_text().splitlines() if ln.strip()] \
            if (jd.STATE / "judge-usage.jsonl").exists() else []
        return _reference_run_judging(t0, ALIVE, semantic, rows, jd.active_runs(), km.time.time())

    def _same(self, got, ref):
        """Equal lists in the same order. NaN is unequal to itself, so a span carrying a NaN run end (kept:
        NaN < t0 is False) defeats ==; the JSON text carries NaN literally and compares as text, and the
        readable diff is only produced when the texts differ."""
        if json.dumps(got) != json.dumps(ref):
            self.assertEqual(got, ref)

    def _check(self, t0, semantic):
        """The kernel's answer equals the reference, list for list, in the same order (stderr swallowed: the
        row-cap trim says so once)."""
        with contextlib.redirect_stderr(io.StringIO()):
            got = km._run_judging(t0, ALIVE, semantic)
        self._same(got, self._reference(t0, semantic))
        return got


class RunJudgingBisect(_Base):
    """The kernel's _run_judging answers exactly what the full scan answered, over every shape the horizon
    filter, the memo's cursor and the gloss's bisect can meet."""

    def _mixed_world(self):
        rows = [
            _row(T0 - 40000, judge="planner"),                        # far before the horizon
            _row(T0 - 3, judge="captioner"),                          # t < t0 - 1: ends before t0, dropped
            _row(T0 - 1, recv=T0 - 0.5),                              # t = t0 - 1, ends before t0: dropped
            _row(T0 - 1, recv=float(T0), judge="closer"),             # t = t0 - 1, ends AT t0: kept
            _row(T0, sid=SID_DEAD),                                   # dead session
            _row(T0 + 10, sid=SID_B, judge="gister"),                 # a family alias (gister -> captioner)
            _row(T0 + 20, sid=SID_B, judge="courier"),
            _row(T0 + 30, sent=None, recv=None),                      # a pre-recording point at t
            _row(T0 + 40, sent=T0 + 37.0, recv=None),                 # sent only: end is sent
            _row(T0 + 50, judge="planner", sent=T0 + 48.0, recv=T0 + 50.5),
            _row(T0 + 60, judge="planner", sent=T0 + 58.0, recv=T0 + 60.25),
            _row(T0 + 60, judge="distiller"),                         # tied t across judges
            _row(T0 + 600, sid=SID_B, judge="captioner"),
        ]
        marks = [
            _mark(T0 + 51.5, judge="planner", text="at end+1 exactly: included"),      # end 50.5 → end+1 = 51.5
            _mark(T0 + 52.5, judge="planner", text="at end+2: excluded for that row"),
            _mark(T0 + 61.25, judge="planner", text="tie one"),                         # end 60.25 → end+1 = 61.25
            _mark(T0 + 61.25, judge="planner", text="tie two: the later of the tied marks wins"),
            _mark(T0 - 200, judge="captioner", text="an old caption"),
            _mark(T0 + 29, judge="captioner", text="caption before the point row"),
            _mark(T0 + 5, sid=SID_B, judge="captioner", text="B's caption"),
            _mark(T0 + 7, sid=SID_B, judge="courier", text="B's plant", kind="plant"),
            _mark(T0 + 3500, judge="grouper", text="a mark for a live run, at now - 100"),
            _mark(T0 + 3601, judge="grouper", text="a mark at now + 1: included for the live run"),
            _mark(T0 + 3602, judge="grouper", text="a mark at now + 2: excluded"),
            _mark(T0 + 1, sid=SID_DEAD, judge="planner", text="dead"),
        ]
        return rows, marks

    def test_matches_the_full_scan_over_a_mixed_file_with_live_runs(self):
        rows, marks = self._mixed_world()
        self._write(rows)
        rids = [jd._active_begin("grouper", SID_A, T0 + 3000),          # a live run inside the horizon
                jd._active_begin("planner", SID_A, T0 + 48.0),          # colliding with a done row: deduped
                jd._active_begin("closer", SID_A, T0 - 50),             # a live run older than t0: dropped
                jd._active_begin("planner", SID_DEAD, T0 + 100)]        # dead session
        try:
            got = self._check(T0, marks)
        finally:
            for rid in rids:
                jd._active_end(rid)
        # the shape the equivalence rests on, spelled out
        self.assertEqual([m["sid"] for m in got].count(SID_DEAD), 0)
        by_start = {(m["judge"], m["sent"]): m for m in got}
        self.assertEqual(by_start[("planner", T0 + 48.0)]["text"], "at end+1 exactly: included")
        self.assertEqual(by_start[("planner", T0 + 58.0)]["text"], "tie two: the later of the tied marks wins")
        self.assertEqual(by_start[("captioner", None)]["text"], "caption before the point row")
        self.assertEqual(by_start[("captioner", T0 + 10 + 0.5 - 3.25)]["sid"], SID_B, "gister maps to captioner")
        live = [m for m in got if m.get("open")]
        self.assertEqual([(m["judge"], m["t"], m["text"]) for m in live],
                         [("grouper", T0 + 3000, "a mark at now + 1: included for the live run")])
        self.assertNotIn(("closer", T0 - 50), by_start)
        self.assertNotIn(("captioner", T0 - 3 + 0.5 - 3.25), by_start, "t < t0 - 1 ends before t0: not kept")
        self.assertIn(("closer", T0 - 3.25), by_start, "t = t0 - 1 ending at t0 is kept")

    def test_rows_exactly_at_the_horizon(self):
        # every boundary the horizon filter (end < t0) can meet, for an integer and a fractional t0
        for t0 in (T0, T0 + 0.5):
            with self.subTest(t0=t0):
                km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
                rows = [                                            # in t order, as the writer appends
                    _row(int(t0) - 4, recv=int(t0) - 4 + 0.9998),   # well below the horizon: dropped
                    _row(int(t0) - 3, recv=int(t0) - 3 + 0.9998),   # below the horizon: dropped
                    _row(int(t0) - 2, recv=int(t0) - 2 + 0.9998),   # the writer's measured max recv - t
                    _row(int(t0) - 1, recv=int(t0) - 1 + 0.9998),   # t = int(recv), recv just under t0
                    _row(int(t0) - 1, recv=float(int(t0))),         # t = int(recv), recv == int(t0)
                    _row(int(t0) - 1, sent=None, recv=None),        # a point row at t0 - 1
                    _row(int(t0) - 1, sent=float(int(t0)) - 0.2, recv=None),   # sent only, under t0
                    _row(int(t0), recv=int(t0) + 0.7),              # t = int(recv), t0 in (t, recv]
                    _row(int(t0), sent=None, recv=None),            # a point row at t0
                    _row(int(t0), sent=float(int(t0)), recv=None),             # sent only, at t0
                ]
                self._write(rows)
                got = self._check(t0, [])
                # every row ending before t0 is dropped by both; from there on the filter decides
                self.assertTrue(all(m["t1"] >= t0 for m in got))
                self.assertEqual(len(got), sum(1 for m in self._reference(t0, []) if m["t1"] >= t0))

    def test_an_empty_or_missing_file_answers_the_reference(self):
        rid = jd._active_begin("grouper", SID_A, T0 + 3000)
        try:
            self.assertEqual(self._check(T0, [_mark(T0 + 3000, judge="grouper", text="live")]),
                             [{"judge": "grouper", "sid": SID_A, "t": T0 + 3000, "t1": km.time.time(),
                               "kind": "segment", "text": "live", "ms": 0, "in": 0, "out": 0,
                               "sent": T0 + 3000, "recv": None, "open": True}])
            self._write([])
            self.assertEqual(len(self._check(T0, [])), 1)
        finally:
            jd._active_end(rid)
        self.assertEqual(self._check(T0, []), [])

    def test_a_file_that_grows_between_two_calls(self):
        rows, marks = self._mixed_world()
        self._write(rows[:6])
        first = self._check(T0, marks)
        self._write(rows[6:], mode="a")
        second = self._check(T0, marks)
        self.assertGreater(len(second), len(first), "the appended rows are in the second answer")
        self._write([_row(T0 + 700, sid=SID_B, judge="closer")], mode="a")
        third = self._check(T0, marks)
        self.assertEqual(len(third), len(second) + 1)
        self.assertEqual(third[:len(second)], second, "growth appends; it never reorders what was there")

    def test_more_than_the_row_cap_matches_in_order(self):
        n = km._JUDGING_ROW_CAP + 60
        rows = [_row(T0 + i, judge="captioner" if i % 3 else "planner") for i in range(n)]
        self._write(rows)
        km._JUDGING_TRIMMED.clear()
        got = self._check(T0 - 100, [_mark(T0 + 500, text="mid"), _mark(T0 + n, text="late")])
        self.assertEqual(len(got), km._JUDGING_ROW_CAP)
        self.assertEqual(got[-1]["t"], T0 + n - 1 + 0.5 - 3.25, "the newest survive the trim")

    def test_a_nan_run_end_borrows_no_gloss(self):
        # a NaN recv passes the horizon filter (NaN < t0 is False) and reaches the gloss with end + 1 =
        # NaN. The scan's m["t"] <= NaN was False for every mark, so the span had kind "run" and no text;
        # bisect_right(times, NaN) would return the newest mark. The gloss's guard (the fork's, kept on
        # upstream's memo at the 2026-09-17 fold) answers no mark, matched to the reference
        marks = [_mark(T0 + 1, text="a caption"), _mark(T0 + 9, text="the newest")]
        self._write([_row(T0 + 5), _row(T0 + 6, recv=float("nan"))])
        got = self._check(T0, marks)
        self.assertEqual([(m["text"], m["kind"]) for m in got], [("a caption", "segment"), ("", "run")])
        self.assertNotEqual(got[1]["t1"], got[1]["t1"], "the span carries its NaN end, as before")

    def test_gloss_bisect_answers_the_prefix_scan(self):
        # the gloss rule in isolation: the most recent same-judge mark with t <= end + 1, ties resolved
        # to the LAST of the tied marks in the stable sort (what cands[-1] returned)
        marks = [_mark(T0 + 10, text="third"), _mark(T0 + 10, text="fourth"), _mark(T0 + 5, text="first"),
                 _mark(T0 + 9, text="second"), _mark(T0 + 11, text="too late for row one")]
        self._write([_row(T0 + 9, recv=T0 + 9.0),           # end + 1 = T0 + 10: the tied marks qualify
                     _row(T0 + 8, recv=T0 + 8.5),           # (an inversion: the memo assumes no order, same answer)
                     _row(T0 + 4, recv=T0 + 4.0)])          # end + 1 = T0 + 5: exactly the first mark
        got = self._check(T0, marks)
        self.assertEqual([m["text"] for m in got], ["fourth", "second", "first"])
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self._write([_row(T0 + 4, recv=T0 + 4.0), _row(T0 + 8, recv=T0 + 8.5), _row(T0 + 9, recv=T0 + 9.0),
                     _row(T0 + 20, judge="closer")])        # no closer marks at all: kind "run", empty text
        got = self._check(T0, marks)
        self.assertEqual([(m["text"], m["kind"]) for m in got],
                         [("first", "segment"), ("second", "segment"), ("fourth", "segment"), ("", "run")])


class SourcePins(unittest.TestCase):
    def test_the_shared_reader_and_the_gloss_bisect_stay_at_source(self):
        # the shared incremental reader (never a per-build read of the log) and the gloss's bisect_right. The
        # horizon bisect_left and the assert that no gloss comprehension text remains retired at the fold (the
        # module docstring): the memo's cursor replaced the one, and upstream's gloss comment quotes the other
        import inspect
        src = inspect.getsource(km._run_judging)
        self.assertIn("_judge_usage_rows()", src)
        self.assertIn("bisect_right", src)


if __name__ == "__main__":
    unittest.main()
