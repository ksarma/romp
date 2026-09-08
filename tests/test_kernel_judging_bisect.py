#!/usr/bin/env python3
"""_run_judging bisects instead of scanning (round-4 item B, 2026-09-07), with output identical to the
full scan it replaces.

Two scans made the function 15% of a timeline build: the gloss comprehension re-filtered every
same-(sid, judge) artifact mark per usage row, and the horizon filter visited every retained row (a
31-day cache) to keep the 48 h it plots. Both lists are sorted by t, so both answers are a prefix
boundary: the gloss is the last mark with t <= end + 1 (bisect_right on the mark times), and the
first row that can pass the horizon filter is the first with t >= t0 - 1 (bisect_left on the row
times), because the writer stamps t after recv, so every row's run end is at most t + 1.

The horizon bisect needs three facts of the row list, and the READER verifies them as rows arrive
instead of the consumer trusting the writer: every row's t is a number, no t is more than S = 2 s
below the largest t before it (the writer's pool threads can land two same-second rows in either
order), and no row's run end (recv, else sent, else t) exceeds t + 1. With the bisect backed off by
S, every row it leaves behind ended before t0. The result is the `monotone` flag on the snapshot
_judge_usage_rows returns; a file that breaks any of the three takes today's full scan exactly, and
the reader says so once on stderr.

Three classes: ReaderOrderFlag pins the flag the reader derives (ordered, within-slack and past-slack
disorder, NaN and non-numeric t, a run end past t + 1, empty and missing files, growth and rewrites,
the flag travelling with its snapshot); RunJudgingBisect pins the kernel's answer against a private
copy of the pre-bisect function on both paths (a mixed file with live runs, the horizon edges,
disorder at the horizon, a non-monotone file, growth between calls, more than the row cap, the
access-count proof that the walk starts at the horizon and that a bare list walks from the head, the
gloss rule and its NaN case); SourcePins pins the shared reader call and the two bisects at source.
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
    """Today's _run_judging (main at 1e829313), verbatim except that the rows, the in-flight runs and
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


class _CountingRow(dict):
    """A row that records every field access in a shared list — the proof of which rows a walk touched."""
    __slots__ = ("box",)

    def __init__(self, box, *a, **k):
        super().__init__(*a, **k)
        self.box = box

    def get(self, k, d=None):
        self.box.append(k)
        return dict.get(self, k, d)

    def __getitem__(self, k):
        self.box.append(k)
        return dict.__getitem__(self, k)


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
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self._time = km.time
        km.time = _FrozenTime(km.time, float(T0 + 3600))

    def tearDown(self):
        km.time = self._time
        jd.STATE = self.saved
        jd._active.clear()                               # the in-flight registry is module-level
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
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

    def _check(self, t0, semantic, expect_monotone=True):
        """The kernel's answer equals the reference, list for list, in the same order; and the reader's
        flag for the file is what the test expects (so each test knows which path it exercised)."""
        with contextlib.redirect_stderr(io.StringIO()):
            got = km._run_judging(t0, ALIVE, semantic)
            snap = km._judge_usage_rows()
        self._same(got, self._reference(t0, semantic))
        self.assertIs(snap.monotone, expect_monotone)
        return got


class ReaderOrderFlag(_Base):
    """The reader keeps the three facts the bisect needs, once per appended row, and hands them out with
    the snapshot they describe."""

    def test_a_time_ordered_file_reads_monotone(self):
        self._write([_row(T0 - 100), _row(T0 - 100, judge="planner"), _row(T0 + 5), _row(T0 + 9)])
        snap = km._judge_usage_rows()
        self.assertIsInstance(snap, list)
        self.assertEqual(len(snap), 4)
        self.assertIs(snap.monotone, True, "ties and increases keep the order fact")
        self.assertIs(km._JUDGE_USAGE_CACHE["monotone"], True)

    def test_disorder_within_the_slack_keeps_the_flag(self):
        # the writer's race: two pool threads finishing in the same second append in either order
        self._write([_row(T0 - 100), _row(T0 - 101), _row(T0 + 5), _row(T0 + 3), _row(T0 + 4)])
        self.assertIs(km._judge_usage_rows().monotone, True, "1 s and 2 s below the running maximum")
        self.assertEqual(km._JUDGE_USAGE_CACHE["hi"], T0 + 5, "the running maximum, not the tail's t")

    def test_disorder_past_the_slack_clears_the_flag_and_says_so_once(self):
        self._write([_row(T0 + 10), _row(T0 + 7)])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            snap = km._judge_usage_rows()
        self.assertIs(snap.monotone, False, "3 s below the running maximum")
        lines = [ln for ln in err.getvalue().splitlines() if "time-order fact" in ln]
        self.assertEqual(len(lines), 1, err.getvalue())
        self.assertIn("row 2 of the log", lines[0])
        self.assertIn("3.0 s below the running maximum", lines[0])
        self._write([_row(T0 + 6), _row(T0 + 20)], mode="a")          # more rows, in and out of order
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIs(km._judge_usage_rows().monotone, False)
        self.assertEqual(err.getvalue(), "", "the line is written at the transition only")
        self._write([_row(T0 + 1)])                                    # a rewrite: a new list, a new fact
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIs(km._judge_usage_rows().monotone, True)
        self.assertEqual(err.getvalue(), "")

    def test_a_row_without_a_numeric_t_clears_the_flag(self):
        for bad in ({"judge": "captioner", "fsid": SID_A, "sent": T0 + 1.0, "recv": T0 + 2.0},
                    {"t": "1781100000", "judge": "captioner", "fsid": SID_A},
                    {"t": None, "judge": "captioner", "fsid": SID_A}):
            km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
            self._write([_row(T0 - 100), bad, _row(T0 + 5)])
            self.assertIs(km._judge_usage_rows().monotone, False, bad)

    def test_a_nan_t_or_a_nan_run_end_clears_the_flag_and_names_it(self):
        # NaN compares False against everything: a NaN t would pass `t < hi - S` and a NaN end would
        # fail `end <= t + 1` only incidentally. Both are named, and the line says which
        for bad, reason in (({"t": float("nan"), "judge": "captioner", "fsid": SID_A,
                              "sent": T0 + 1.0, "recv": T0 + 2.0}, "t is not a number"),
                            (_row(T0 + 5, recv=float("nan")), "run end is not a number"),
                            (_row(T0 + 5, recv=None, sent=float("nan")), "run end is not a number")):
            km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
            self._write([_row(T0 - 100), bad, _row(T0 + 9)])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                snap = km._judge_usage_rows()
            self.assertIs(snap.monotone, False, bad)
            self.assertEqual(len(snap), 3, "the row itself stays in the list")
            self.assertIn("row 2 of the log breaks the time-order fact (%s)" % reason, err.getvalue())

    def test_a_run_end_more_than_one_second_past_t_clears_the_flag(self):
        # the fact that lets the bisect skip rows with t < t0 - 1: their run ended before t0. A row that
        # breaks it (t stamped BEFORE its recv) is exactly the row the bisect would lose, so it costs the
        # file the fast path instead
        self._write([_row(T0 - 100), _row(T0 - 50, recv=T0 - 50 + 1.5)])
        self.assertIs(km._judge_usage_rows().monotone, False)
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self._write([_row(T0 - 100), _row(T0 - 50, recv=T0 - 50 + 1.0)])
        self.assertIs(km._judge_usage_rows().monotone, True, "exactly t + 1 is within the bound")
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self._write([_row(T0 - 100), _row(T0 - 50, recv=None, sent=T0 - 50 + 1.5)])
        self.assertIs(km._judge_usage_rows().monotone, False, "without recv the end is sent")
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self._write([_row(T0 - 100), _row(T0 - 50, recv=None, sent=None)])
        self.assertIs(km._judge_usage_rows().monotone, True, "without either the end is t itself")

    def test_an_empty_or_missing_file_is_monotone(self):
        snap = km._judge_usage_rows()
        self.assertEqual((list(snap), snap.monotone), ([], True), "no file")
        self._write([])
        snap = km._judge_usage_rows()
        self.assertEqual((list(snap), snap.monotone), ([], True), "empty file")

    def test_growth_keeps_the_flag_and_an_inverted_append_clears_it_until_a_rewrite(self):
        self._write([_row(T0 - 100), _row(T0 - 90)])
        self.assertIs(km._judge_usage_rows().monotone, True)
        self._write([_row(T0 - 90), _row(T0 + 7)], mode="a")           # an append in order
        snap = km._judge_usage_rows()
        self.assertEqual((len(snap), snap.monotone), (4, True))
        self._write([_row(T0 + 6)], mode="a")                          # a pool thread's 1 s inversion: kept
        snap = km._judge_usage_rows()
        self.assertEqual((len(snap), snap.monotone), (5, True))
        self._write([_row(T0 + 3)], mode="a")                          # 4 s below the maximum: cleared
        with contextlib.redirect_stderr(io.StringIO()):
            snap = km._judge_usage_rows()
        self.assertEqual((len(snap), snap.monotone), (6, False))
        self._write([_row(T0 + 8)], mode="a")                          # order resumes; the fact does not
        self.assertIs(km._judge_usage_rows().monotone, False,
                      "one break anywhere in the list keeps the full scan for that list")
        self._write([_row(T0 + 1), _row(T0 + 2)])                      # rotated / rewritten: a new list
        snap = km._judge_usage_rows()
        self.assertEqual((len(snap), snap.monotone), (2, True), "a reset re-derives the fact")

    def test_the_flag_describes_the_snapshot_it_came_with(self):
        # the flag and the rows are read under the reader's one lock; a later append that clears the
        # cache's flag does not reach back into an earlier snapshot
        self._write([_row(T0 - 100), _row(T0 - 90)])
        earlier = km._judge_usage_rows()
        self._write([_row(T0 - 95)], mode="a")
        with contextlib.redirect_stderr(io.StringIO()):
            later = km._judge_usage_rows()
        self.assertEqual((earlier.monotone, len(earlier)), (True, 2))
        self.assertEqual((later.monotone, len(later)), (False, 3))


class RunJudgingBisect(_Base):
    """The kernel's _run_judging answers exactly what the full scan answered, on the bisect path and on
    the fallback, over every shape the two bisects can meet."""

    def _mixed_world(self):
        rows = [
            _row(T0 - 40000, judge="planner"),                        # far before the horizon
            _row(T0 - 3, judge="captioner"),                          # t < t0 - 1: the bisect skips it
            _row(T0 - 1, recv=T0 - 0.5),                              # t = t0 - 1, ends before t0: examined, dropped
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
        self.assertNotIn(("captioner", T0 - 3 + 0.5 - 3.25), by_start, "t < t0 - 1 is neither examined nor kept")
        self.assertIn(("closer", T0 - 3.25), by_start, "t = t0 - 1 ending at t0 is kept")

    def test_rows_exactly_at_the_horizon(self):
        # every boundary the bisect at t0 - 1 can meet, for an integer and a fractional t0
        for t0 in (T0, T0 + 0.5):
            with self.subTest(t0=t0):
                km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
                rows = [                                            # in t order, as the writer appends
                    _row(int(t0) - 4, recv=int(t0) - 4 + 0.9998),   # below the bisect point t0 - 3: skipped
                    _row(int(t0) - 3, recv=int(t0) - 3 + 0.9998),   # at the bisect point: examined, dropped
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
                # the row below the bisect point is dropped by both; from there on the filter decides
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

    def test_a_non_monotone_file_takes_the_full_scan_and_matches(self):
        rows, marks = self._mixed_world()
        rows.insert(6, _row(T0 + 5, judge="planner"))                # a late-landing row: t 5 s below the maximum
        rows.append(_row(T0 + 9, sid=SID_B))                         # and again at the tail
        rows.append({"t": float("nan"), "judge": "captioner", "fsid": SID_A,     # a NaN t: the span is
                     "sent": T0 + 700.0, "recv": T0 + 702.0, "ms": 5})           # its sent/recv as before
        rows.append(_row(T0 + 800, sid=SID_B, sent=T0 + 797.0, recv=float("nan")))   # a NaN recv: kept, NaN t1
        self._write(rows)
        got = self._check(T0, marks, expect_monotone=False)
        self.assertIn(("planner", T0 + 5 + 0.5 - 3.25), {(m["judge"], m["sent"]) for m in got},
                      "a late row inside the horizon is kept: the fallback is today's scan")
        tail = [(m["t"], m["t1"] != m["t1"], m["text"]) for m in got[-2:]]
        self.assertEqual(tail, [(T0 + 700.0, False, "caption before the point row"), (T0 + 797.0, True, "")])
        # the file a bisect would get wrong: an in-horizon row at the head, older rows after it.
        # bisect_left on t at t0 - 1 over [T0+5, T0-100, T0-50, T0+6] lands at index 3 and would lose
        # the first row; the flag is clear for this list, so the walk starts at the head
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self._write([_row(T0 + 5), _row(T0 - 100), _row(T0 - 50), _row(T0 + 6)])
        got = self._check(T0, [], expect_monotone=False)
        self.assertEqual([m["t1"] for m in got], [T0 + 5.5, T0 + 6.5], "both in-horizon rows, in file order")

    def test_disorder_within_the_slack_at_the_horizon_is_bisected_exactly(self):
        # rows 2 s out of order straddling the horizon, the flag holding. bisect_left on t at t0 - 3 over
        # [t0-2, t0-4, t0, t0-2, t0+3, t0+1] lands at index 2: the two rows it leaves behind both ended
        # before t0, the late row at index 3 is examined and dropped, the late row at index 5 is kept
        self._write([_row(T0 - 2, recv=T0 - 1.5), _row(T0 - 4, recv=T0 - 3.5), _row(T0, recv=T0 + 0.5),
                     _row(T0 - 2, recv=T0 - 1.5), _row(T0 + 3, recv=T0 + 3.5), _row(T0 + 1, recv=T0 + 1.5)])
        got = self._check(T0, [])
        self.assertEqual([m["t1"] for m in got], [T0 + 0.5, T0 + 3.5, T0 + 1.5], "kept rows, in file order")

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

    def test_the_walk_starts_at_the_horizon_when_the_flag_holds(self):
        # the proof the bisect is what runs: 2000 rows before the horizon are touched a handful of times
        # (the bisect's probes) when the flag holds, and once each when it does not. The reader is
        # replaced with a snapshot of counting rows, the way test_timeline_bars_resilience replaces it.
        box = []
        before = [_CountingRow(box, _row(T0 - 5000 + i)) for i in range(2000)]
        inside = [_row(T0 + i) for i in range(5)]
        saved = (km._judge_usage_rows, jd.active_runs)
        jd.active_runs = lambda: []
        try:
            for flag, bound, cmp in ((True, 64, self.assertLess), (False, 2000, self.assertGreaterEqual)):
                snap = km._JudgeUsageSnapshot(before + inside)
                snap.monotone = flag
                km._judge_usage_rows = lambda: snap
                del box[:]
                got = km._run_judging(T0, ALIVE, [_mark(T0 + 2, text="g")])
                reads = len(box)                          # before the reference walks the same rows
                self.assertEqual(got, _reference_run_judging(T0, ALIVE, [_mark(T0 + 2, text="g")],
                                                             before + inside, [], km.time.time()))
                self.assertEqual(len(got), 5)
                cmp(reads, bound, "flag=%r: %d field reads on the 2000 rows before the horizon" % (flag, reads))
        finally:
            km._judge_usage_rows, jd.active_runs = saved

    def test_a_nan_run_end_borrows_no_gloss(self):
        # a NaN recv passes the horizon filter (NaN < t0 is False) and reaches the gloss with end + 1 =
        # NaN. The scan's m["t"] <= NaN was False for every mark, so the span had kind "run" and no text;
        # bisect_right(times, NaN) would return the newest mark. The NaN end also clears the reader's
        # flag (it is not <= t + 1), so this is the fallback path, matched to the reference
        marks = [_mark(T0 + 1, text="a caption"), _mark(T0 + 9, text="the newest")]
        self._write([_row(T0 + 5), _row(T0 + 6, recv=float("nan"))])
        got = self._check(T0, marks, expect_monotone=False)
        self.assertEqual([(m["text"], m["kind"]) for m in got], [("a caption", "segment"), ("", "run")])
        self.assertNotEqual(got[1]["t1"], got[1]["t1"], "the span carries its NaN end, as before")

    def test_a_bare_list_or_an_unflagged_snapshot_walks_from_the_head(self):
        # the reader's test doubles (test_timeline_bars_resilience hands _run_judging plain lists) and a
        # snapshot whose flag was never assigned carry no order fact, so the walk starts at the head even
        # when the rows are in order and a bisect WOULD have skipped the ones before the horizon
        box = []
        before = [_CountingRow(box, _row(T0 - 5000 + i)) for i in range(300)]
        inside = [_row(T0 + i) for i in range(3)]
        marks = [_mark(T0 + 1, text="g")]
        ref = _reference_run_judging(T0, ALIVE, marks, before + inside, [], km.time.time())
        unflagged = km._JudgeUsageSnapshot(before + inside)          # the slot exists; nothing assigned it
        with self.assertRaises(AttributeError):
            unflagged.monotone
        saved = (km._judge_usage_rows, jd.active_runs)
        jd.active_runs = lambda: []
        try:
            for label, rows in (("plain list", list(before + inside)), ("unflagged snapshot", unflagged)):
                km._judge_usage_rows = lambda rows=rows: rows
                del box[:]
                got = km._run_judging(T0, ALIVE, marks)
                reads = len(box)
                self.assertEqual(got, ref, label)
                self.assertEqual(len(got), 3, label)
                self.assertGreaterEqual(reads, 2 * len(before),
                                        "%s: every row before the horizon was examined (%d field reads)" % (label, reads))
        finally:
            km._judge_usage_rows, jd.active_runs = saved

    def test_gloss_bisect_answers_the_prefix_scan(self):
        # the gloss rule in isolation: the most recent same-judge mark with t <= end + 1, ties resolved
        # to the LAST of the tied marks in the stable sort (what cands[-1] returned)
        marks = [_mark(T0 + 10, text="third"), _mark(T0 + 10, text="fourth"), _mark(T0 + 5, text="first"),
                 _mark(T0 + 9, text="second"), _mark(T0 + 11, text="too late for row one")]
        self._write([_row(T0 + 9, recv=T0 + 9.0),           # end + 1 = T0 + 10: the tied marks qualify
                     _row(T0 + 8, recv=T0 + 8.5),           # (an inversion: the fallback path, same answer)
                     _row(T0 + 4, recv=T0 + 4.0)])          # end + 1 = T0 + 5: exactly the first mark
        got = self._check(T0, marks, expect_monotone=False)
        self.assertEqual([m["text"] for m in got], ["fourth", "second", "first"])
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self._write([_row(T0 + 4, recv=T0 + 4.0), _row(T0 + 8, recv=T0 + 8.5), _row(T0 + 9, recv=T0 + 9.0),
                     _row(T0 + 20, judge="closer")])        # no closer marks at all: kind "run", empty text
        got = self._check(T0, marks)
        self.assertEqual([(m["text"], m["kind"]) for m in got],
                         [("first", "segment"), ("second", "segment"), ("fourth", "segment"), ("", "run")])


class SourcePins(unittest.TestCase):
    def test_no_scan_comprehension_remains_and_the_shared_reader_stays(self):
        import inspect
        src = inspect.getsource(km._run_judging)
        self.assertIn("_judge_usage_rows()", src)
        self.assertNotIn("if m[\"t\"] <=", src, "the gloss comprehension is gone")
        self.assertIn("bisect_right", src)
        self.assertIn("bisect_left", src)


if __name__ == "__main__":
    unittest.main()
