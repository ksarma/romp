#!/usr/bin/env python3
"""Stat-keyed memos for the per-lane readers every timeline build re-read (perf round 4, item C).

Three readers ran per lane per build on unchanged files: `_captions` re-read and re-parsed the
captioner's store (and `_seg_caption` / `_seg_work_caption` then scanned every row per uncaptioned
segment), `_states_awaiting_overlay` re-read the whole states log, and `_thread_reg` re-read and
re-parsed the SDK registry. Each is now memoized on the file's identity, (st_ino, st_mtime_ns,
st_size) taken before the read, or folded append-incrementally through the event model's shared
reader. The rule every memo here follows: it may return only what the unmemoized reader would return
NOW, so each test compares against a private copy of the reader as it stood before the memo, on an
unchanged file, an appended file and a rewritten file.

Synthetic fixtures only: placeholder UUIDs, invented text. The fork seed below mints a goal store, so
the sids are PRIVATE to this module (CLAUDE.md, goal-store fixtures)."""
import inspect
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_capsmemo", os.path.join(BIN, "romp-kernel"))
jd = km.jd
em = km.em

SID = "77777777-8888-9999-aaaa-cccccccccccc"
SID2 = "77777777-8888-9999-aaaa-dddddddddddd"
SID3 = "77777777-8888-9999-aaaa-eeeeeeeeeeee"
PARENT = "77777777-8888-9999-aaaa-ffffffffffff"
T = 1781100000


# ── the readers as they stood before the memos (main at 1e829313), the equality oracles ──
def ref_captions(fsid):
    out = {}
    try:
        for line in (jd.CAPDIR / (fsid + ".jsonl")).read_text(errors="replace").splitlines():
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("id"):
                out[o["id"]] = o
    except OSError:
        pass
    return out


def ref_seg_caption(caps, seg_id):
    hit = caps.get(seg_id + "#p")
    if hit is None:
        want = jd._seg_key(seg_id + "#p")
        hit = next((v for k, v in caps.items() if k.endswith("#p") and jd._seg_key(k) == want), None)
    return (hit or {}).get("caption", "")


def ref_seg_work_caption(caps, seg_id):
    hit = caps.get(seg_id)
    if hit is not None:
        return hit.get("caption", "")
    parts = seg_id.split(":") if seg_id else []
    if len(parts) < 3:
        return ""
    try:
        seg_t = int(parts[-2])
    except ValueError:
        return ""
    want = jd._seg_key(seg_id)
    best = None
    for k, v in caps.items():
        if v.get("grain") != "segment" or jd._seg_key(k) != want:
            continue
        d = abs((v.get("t") or 0) - seg_t)
        if best is None or d < best[0]:
            best = (d, v)
    return best[1].get("caption", "") if best else ""


def ref_overlay(sid):
    p = jd.STATE / "states" / ("%s.jsonl" % sid)
    last = None
    working_after = False
    try:
        with open(p, errors="replace") as f:
            for line in f:
                if '"awaiting"' in line:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(o, dict) and "awaiting" in o:
                        last, working_after = o, False
                elif '"state"' in line and '"working"' in line:
                    working_after = True
    except OSError:
        return None
    if last is not None and last.get("awaiting") and working_after:
        return {"awaiting": False, "why": None}
    return last


def _reset(stats):
    for k in list(stats):
        stats[k] = 0


class _State(unittest.TestCase):
    """A fresh state root per test and every memo emptied, so no test reads another's entries."""

    def setUp(self):
        self.saved_state = jd.STATE
        self.td = tempfile.mkdtemp()
        jd._rebind_state(Path(self.td))
        km._caps_memo.clear(); _reset(km._caps_memo_stats); km._caps_failed.clear()
        km._thread_reg_memo.clear(); _reset(km._thread_reg_stats); km._thread_reg_failed.clear()
        km._states_overlay_cache.clear(); _reset(km._states_overlay_stats); km._states_overlay_failed.clear()

    def tearDown(self):
        jd._rebind_state(self.saved_state)
        shutil.rmtree(self.td, ignore_errors=True)

    # captions
    def cap_path(self, fsid=SID):
        return jd.CAPDIR / (fsid + ".jsonl")

    def write_caps(self, rows, fsid=SID):
        jd.CAPDIR.mkdir(parents=True, exist_ok=True)
        self.cap_path(fsid).write_text("".join(json.dumps(r) + "\n" for r in rows))

    def append_cap(self, row, fsid=SID):
        jd.append_caption(fsid, row["id"], row.get("grain", "segment"), row.get("t", T), row["caption"],
                          live=bool(row.get("live")), natoms=row.get("natoms"))

    # states
    def states_path(self, sid=SID):
        return jd.STATE / "states" / (sid + ".jsonl")

    def write_states(self, rows, sid=SID):
        p = self.states_path(sid)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))

    # sdk registry
    def reg_path(self, tsid=SID):
        return jd.STATE / "sdk" / (tsid + ".json")

    def publish_reg(self, reg, tsid=SID):
        """sdk_backend.write_reg's idiom: a writer-unique temp, then os.replace (a new inode per write)."""
        p = self.reg_path(tsid)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".%d.tmp" % os.getpid())
        tmp.write_text(json.dumps(reg))
        os.replace(tmp, p)


def seg(t, h="cafebabe", sid=SID):
    return "%s:%d:%s" % (sid, t, h)


class CaptionsMemo(_State):
    """`_captions(fsid)` memoized on the store file's identity, taken before the read."""

    ROWS = [{"id": seg(T), "grain": "segment", "t": T, "caption": "wired the feed"},
            {"id": seg(T) + "#p", "grain": "prompt", "t": T, "caption": "the feed wiring"},
            {"id": seg(T + 60, "deadbeef"), "grain": "turn", "t": T + 60, "caption": "a turn rollup"}]

    def test_an_unchanged_file_is_read_once_and_serves_the_same_object(self):
        self.write_caps(self.ROWS)
        a = km._captions(SID)
        b = km._captions(SID)
        self.assertIs(a, b, "a hit hands out the memoized object, indexes included")
        self.assertEqual(dict(a), ref_captions(SID))
        st = km._caps_memo_report()
        self.assertEqual((st["miss"], st["hit"], st["entries"]), (1, 1, 1))

    def test_an_append_is_a_miss_and_the_new_row_is_served(self):
        self.write_caps(self.ROWS)
        a = km._captions(SID)
        self.append_cap({"id": seg(T + 120, "0badf00d"), "grain": "segment", "t": T + 120, "caption": "shipped it"})
        b = km._captions(SID)
        self.assertIsNot(a, b)
        self.assertEqual(dict(b), ref_captions(SID))
        self.assertIn(seg(T + 120, "0badf00d"), b)
        self.assertNotIn(seg(T + 120, "0badf00d"), a, "the served object is never extended in place")
        self.assertEqual(km._caps_memo_report()["miss"], 2)

    def test_a_replace_publish_is_a_miss_even_at_equal_size(self):
        self.write_caps(self.ROWS)
        a = km._captions(SID)
        rows = [dict(r) for r in self.ROWS]
        rows[0]["caption"] = "wired the FEED"                     # same byte length, different content
        tmp = self.cap_path().with_name("x.tmp")
        tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
        st0 = os.stat(self.cap_path())
        os.utime(tmp, ns=(st0.st_atime_ns, st0.st_mtime_ns))     # same mtime_ns and size: only the inode moves
        os.replace(tmp, self.cap_path())
        b = km._captions(SID)
        self.assertEqual(dict(b), ref_captions(SID))
        self.assertEqual(b[seg(T)]["caption"], "wired the FEED")
        self.assertIsNot(a, b)

    def test_an_absent_file_is_empty_and_never_memoized(self):
        self.assertEqual(dict(km._captions(SID)), {})
        self.assertEqual(dict(km._captions(SID)), {})
        st = km._caps_memo_report()
        self.assertEqual(st["entries"], 0, "absent is a state, not an entry")
        self.assertEqual(st["hit"], 0)
        self.write_caps(self.ROWS)
        self.assertEqual(dict(km._captions(SID)), ref_captions(SID), "created after an absent read: read at once")
        self.assertEqual(km._caps_memo_report()["entries"], 1)
        os.unlink(self.cap_path())
        self.assertEqual(dict(km._captions(SID)), {})
        self.assertEqual(km._caps_memo_report()["entries"], 0, "the entry goes with the file")

    def test_a_read_failure_after_a_good_stat_is_not_memoized(self):
        self.write_caps(self.ROWS)
        os.chmod(self.cap_path(), 0)
        try:
            if os.access(self.cap_path(), os.R_OK):
                self.skipTest("this user reads through mode 000 (root)")
            err = io.StringIO()
            with redirect_stderr(err):
                a = km._captions(SID)
                b = km._captions(SID)
            self.assertEqual((dict(a), dict(b)), ({}, {}), "the unmemoized reader answers {} on an unreadable file")
            st = km._caps_memo_report()
            self.assertEqual(st["entries"], 0, "a read that failed after a successful stat is never memoized")
            self.assertEqual(st["fail"], 2)
            self.assertEqual(err.getvalue().count("unreadable"), 1, "one stderr line per failure episode")
        finally:
            os.chmod(self.cap_path(), 0o644)
        self.assertEqual(dict(km._captions(SID)), ref_captions(SID), "readable again: read and memoized")
        self.assertEqual(km._caps_memo_report()["entries"], 1)

    def test_the_fork_seed_publishes_a_new_inode_so_a_memoized_read_of_the_child_is_not_served(self):
        # the round-3 review's hazard: a same-size rewrite in place within one mtime tick keeps all three key
        # components. The fork seed used to write the child's file with Path.write_text (in place); it now
        # publishes through a temp + os.replace, so the inode moves whatever the size and clock do.
        def iso(t):
            from datetime import datetime, timezone
            return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        tpath = os.path.join(self.td, PARENT + ".jsonl")
        Path(tpath).write_text("\n".join(json.dumps(r) for r in [
            {"type": "user", "timestamp": iso(T), "uuid": "u1", "parentUuid": None,
             "message": {"role": "user", "content": "set up the api"}, "promptSource": "typed"},
            {"type": "assistant", "timestamp": iso(T + 10), "uuid": "a1", "parentUuid": "u1",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}], "stop_reason": "end_turn"}},
        ]) + "\n")
        parent_row = {"id": "%s:%d:aaaa" % (PARENT, T), "grain": "segment", "t": T, "caption": "set up the api"}
        self.write_caps([parent_row], fsid=PARENT)
        # the child's file already holds a row of exactly the seeded row's byte length: the seed's
        # os.replace is the only thing that changes the key
        seeded = dict(parent_row, id="%s:%d:aaaa" % (SID2, T))
        stale = dict(seeded, caption="set up the API")
        self.write_caps([stale], fsid=SID2)
        before = km._captions(SID2)
        self.assertEqual(before[seeded["id"]]["caption"], "set up the API")
        st0 = os.stat(self.cap_path(SID2))
        self.assertIsNone(km._seed_fork_stores(PARENT, SID2, tpath, "a1"))
        st1 = os.stat(self.cap_path(SID2))
        self.assertEqual(st0.st_size, st1.st_size, "the fixture holds the size equal on purpose")
        self.assertNotEqual(st0.st_ino, st1.st_ino, "the seed publishes a new inode (temp + os.replace)")
        after = km._captions(SID2)
        self.assertIsNot(after, before)
        self.assertEqual(after[seeded["id"]]["caption"], "set up the api")
        self.assertEqual(dict(after), ref_captions(SID2))

    def test_the_memo_is_bounded_lru_and_the_oldest_used_entry_goes_first(self):
        saved = km._CAPS_MEMO_MAX
        km._CAPS_MEMO_MAX = 2
        try:
            for s in (SID, SID2, SID3):
                self.write_caps([{"id": seg(T, sid=s), "grain": "segment", "t": T, "caption": s[-4:]}], fsid=s)
            km._captions(SID); km._captions(SID2)
            km._captions(SID)                                     # SID is now the most recently used
            km._captions(SID3)                                    # past the cap: SID2, the least recently used, goes
            self.assertEqual(set(km._caps_memo), {SID, SID3})
            self.assertEqual(km._caps_memo_report()["evict"], 1)
            self.assertEqual(km._caps_memo_report()["entries"], 2)
        finally:
            km._CAPS_MEMO_MAX = saved

    def test_forget_releases_the_lanes_outside_the_timeline_set(self):
        for s in (SID, SID2):
            self.write_caps([{"id": seg(T, sid=s), "grain": "segment", "t": T, "caption": "x"}], fsid=s)
            km._captions(s)
        km._caps_forget({SID})
        self.assertEqual(set(km._caps_memo), {SID})
        self.assertEqual(km._caps_memo_report()["evict"], 1)
        km._caps_forget({SID})
        self.assertEqual(km._caps_memo_report()["evict"], 1, "nothing to drop counts nothing")

    def test_a_full_timeline_build_forgets_lanes_that_left_the_timeline(self):
        # build_timeline is where the lane set is known: the forget call rides its full builds. The feed's
        # callers read a subset of the lanes; the postal join reads discover's 48 h window, a superset, and
        # its entries outside the lanes are dropped here and read again only when that transcript changes
        src = inspect.getsource(km.build_timeline)
        self.assertIn("_caps_forget(", src)
        self.assertRegex(src, r"if with_bars and not live_only:\s*\n(\s*#[^\n]*\n)*\s*_caps_forget\(",
                         "full builds only: a skeleton or live-only build reads a subset of the lanes")

    def test_non_object_rows_are_skipped_like_unparseable_ones(self):
        jd.CAPDIR.mkdir(parents=True, exist_ok=True)
        self.cap_path().write_text("[1, 2]\n" + json.dumps(self.ROWS[0]) + "\nnot json\n")
        self.assertEqual(dict(km._captions(SID)), {self.ROWS[0]["id"]: self.ROWS[0]})

    def test_no_kernel_caller_writes_into_a_caps_dict(self):
        # every caller shares the memoized object, so a write anywhere would show on every surface
        src = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()
        for pat in (r"\bcaps\s*\[[^\]]*\]\s*=[^=]", r"\bcaps\.(pop|setdefault|update|clear|popitem)\(", r"\bdel\s+caps\["):
            self.assertIsNone(re.search(pat, src), pat)
        self.assertRegex(src, r"caps = _captions\(sid\)", "the timeline's read binds the name the pins above cover")

    def test_every_captions_writer_appends_or_publishes_by_replace(self):
        # the key's completeness rests on how the file is written: append-only rows (size grows) or a
        # publish through os.replace (a new inode). An in-place rewrite would defeat (ino, mtime_ns, size).
        ksrc = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()
        jsrc = Path(os.path.join(ROOT, "kernel", "judge.py")).read_text()
        self.assertRegex(inspect.getsource(jd.append_caption), r'open\(CAPDIR / \(fsid \+ "\.jsonl"\), "a"\)')
        self.assertNotRegex(ksrc, r'CAPDIR / \([^)]*\)\)\.write_text\(', "no kernel writer rewrites a captions file in place")
        self.assertNotRegex(jsrc, r'CAPDIR / \(fsid \+ "\.jsonl"\)\)\.write_text\(', "no judge writer rewrites a captions file in place")
        self.assertRegex(inspect.getsource(km._seed_fork_stores), r'_atomic_write\(jd\.CAPDIR / \(sid \+ "\.jsonl"\)')
        self.assertIn("os.replace(tmp, path)", inspect.getsource(km._atomic_write))


class CaptionIndexes(_State):
    """`_Caps` carries two lazily built indexes; the indexed lookups equal the scans they replace."""

    def caps_from(self, rows):
        self.write_caps(rows)
        c = km._captions(SID)
        self.assertIsInstance(c, km._Caps)
        return c

    def test_message_caption_index_equals_the_scan_over_drift_and_ties(self):
        rows = [{"id": seg(T) + "#p", "grain": "prompt", "t": T, "caption": "first gist"},
                {"id": seg(T + 5) + "#p", "grain": "prompt", "t": T + 5, "caption": "second gist"},   # same key, drifted t
                {"id": seg(T, "deadbeef") + "#p", "grain": "prompt", "t": T, "caption": "other segment"},
                {"id": seg(T), "grain": "segment", "t": T, "caption": "the work"},
                {"id": "weird#p", "grain": "prompt", "caption": "non-conforming id"}]
        caps = self.caps_from(rows)
        plain = dict(caps)
        for q in (seg(T), seg(T + 5), seg(T - 48), seg(T, "deadbeef"), seg(T, "00000000"), "weird", "", "a:b"):
            self.assertEqual(km._seg_caption(caps, q), ref_seg_caption(plain, q), q)
        self.assertEqual(km._seg_caption(caps, seg(T - 48)), "first gist", "two rows on one key: the first inserted wins, as the scan's next() did")

    def test_work_caption_index_equals_the_scan_over_drift_ties_and_turn_rows(self):
        rows = [{"id": seg(T + 100, "da39a3ee"), "grain": "segment", "t": T + 100, "caption": "first tail"},
                {"id": seg(T + 300, "da39a3ee"), "grain": "segment", "t": T + 300, "caption": "second tail"},
                {"id": seg(T - 48), "grain": "turn", "t": T - 48, "caption": "turn rollup"},          # tests/test_kernel_segdrift.py:155
                {"id": seg(T - 48, "cafebabe") + "#p", "grain": "prompt", "t": T - 48, "caption": "message gist"},
                {"id": seg(T + 900, "aa11bb22"), "grain": "segment", "t": T + 900, "caption": "left"},
                {"id": seg(T + 1100, "aa11bb22"), "grain": "segment", "t": T + 1100, "caption": "right"},
                {"id": seg(T - 48, "feedface"), "grain": "segment", "caption": "no t at all"}]
        caps = self.caps_from(rows)
        plain = dict(caps)
        queries = [seg(T + 111, "da39a3ee"), seg(T + 289, "da39a3ee"), seg(T + 200, "da39a3ee"),   # nearest, and the exact tie
                   seg(T + 1000, "aa11bb22"),                                                          # equidistant: the first inserted
                   seg(T), seg(T - 48), seg(T, "feedface"), seg(T, "00000000"), "weird", "", "a:b", "x:notanint:h"]
        for q in queries:
            self.assertEqual(km._seg_work_caption(caps, q), ref_seg_work_caption(plain, q), q)
        self.assertEqual(km._seg_work_caption(caps, seg(T + 1000, "aa11bb22")), "left", "an equidistant pair resolves to the first row, the scan's strict <")
        self.assertEqual(km._seg_work_caption(caps, seg(T)), "", "a turn row and a prompt row never serve as the bar's caption")

    def test_a_duplicate_id_serves_the_final_row_through_the_index(self):
        # a live caption row and then the final row with the same id: the dict holds the final (last wins),
        # and the indexes are built from the FINAL dict, never while the lines are parsed
        rows = [{"id": seg(T), "grain": "segment", "t": T, "caption": "working…", "live": True, "natoms": 3},
                {"id": seg(T) + "#p", "grain": "prompt", "t": T, "caption": "early gist"},
                {"id": seg(T), "grain": "segment", "t": T, "caption": "landed the fix"},
                {"id": seg(T) + "#p", "grain": "prompt", "t": T, "caption": "final gist"}]
        caps = self.caps_from(rows)
        self.assertEqual(km._seg_work_caption(caps, seg(T - 48)), "landed the fix")
        self.assertEqual(km._seg_caption(caps, seg(T - 48)), "final gist")
        self.assertEqual(len(caps.sidx[jd._seg_key(seg(T))]), 1, "one row per id in the index")
        plain = dict(caps)
        self.assertEqual(km._seg_work_caption(caps, seg(T - 48)), ref_seg_work_caption(plain, seg(T - 48)))
        self.assertEqual(km._seg_caption(caps, seg(T - 48)), ref_seg_caption(plain, seg(T - 48)))

    def test_a_plain_dict_takes_the_scan(self):
        plain = {seg(T) + "#p": {"grain": "prompt", "t": T, "caption": "gist"},
                 seg(T): {"grain": "segment", "t": T, "caption": "work"}}
        self.assertEqual(km._seg_caption(plain, seg(T - 48)), "gist")
        self.assertEqual(km._seg_work_caption(plain, seg(T - 48)), "work")
        self.assertEqual(km._seg_caption({}, seg(T)), "")
        self.assertEqual(km._seg_work_caption({}, seg(T)), "")

    def test_indexes_are_built_lazily_and_once(self):
        caps = self.caps_from([{"id": seg(T) + "#p", "grain": "prompt", "t": T, "caption": "gist"},
                               {"id": seg(T), "grain": "segment", "t": T, "caption": "work"}])
        self.assertIsNone(caps._pidx); self.assertIsNone(caps._sidx)
        self.assertIs(caps.pidx, caps.pidx)
        self.assertIs(caps.sidx, caps.sidx)
        self.assertEqual(caps.pidx, {jd._seg_key(seg(T) + "#p"): caps[seg(T) + "#p"]})
        self.assertEqual(caps.sidx, {jd._seg_key(seg(T)): [caps[seg(T)]]})
        self.assertIs(km._captions(SID), caps, "a hit carries the built indexes with it")


class OverlayFold(_State):
    """`_states_awaiting_overlay` folds the states log through the shared append-incremental reader."""

    def check(self, rows, expect, sid=SID):
        self.write_states(rows, sid)
        got = km._states_awaiting_overlay(sid)
        self.assertEqual(got, ref_overlay(sid), "the fold equals the scan")
        self.assertEqual(got, expect)
        return got

    def test_awaiting_then_idle_stays_awaiting(self):
        self.check([{"t": 100, "awaiting": True, "why": "two jobs"}, {"t": 200, "state": "idle"}],
                   {"t": 100, "awaiting": True, "why": "two jobs"})

    def test_a_later_work_turn_supersedes_a_stale_true(self):
        self.check([{"t": 100, "awaiting": True, "why": "two jobs"}, {"t": 200, "state": "idle"},
                    {"t": 300, "state": "working"}, {"t": 400, "state": "idle"}],
                   {"awaiting": False, "why": None})

    def test_a_work_turn_before_the_overlay_row_does_not_supersede(self):
        self.check([{"t": 100, "state": "working"}, {"t": 200, "awaiting": True, "why": "a build"}, {"t": 300, "state": "waiting"}],
                   {"t": 200, "awaiting": True, "why": "a build"})

    def test_a_row_with_both_keys_is_an_overlay_row(self):
        # awaiting-first, the scan's if/elif order: such a row resets the supersede flag, it never sets it
        self.check([{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "awaiting": True, "state": "working", "why": "y"}],
                   {"t": 200, "awaiting": True, "state": "working", "why": "y"})

    def test_state_rows_with_extra_keys_count_by_their_state(self):
        self.check([{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "picker", "tier": "strict"}],
                   {"t": 100, "awaiting": True, "why": "x"})
        self.check([{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "working", "tier": "loose"}],
                   {"awaiting": False, "why": None}, sid=SID2)

    def test_the_marker_rows_every_other_writer_appends_are_ignored(self):
        rows = [{"t": 100, "awaiting": True, "why": "x", "kind": "task", "count": 2},
                {"t": 110, "retriesGaveUp": 3, "errorKind": "server_error"},
                {"t": 120, "retriesRecovered": 2},
                {"t": 130, "orphanReply": {"uuid": "a9", "text": "working on it"}},
                {"t": 140, "cmdGesture": "/model working"},
                {"t": 150, "machineCut": "restart"},
                {"t": 160, "resumeFork": {"from": SID2, "to": SID3}},
                {"t": 170, "effortApplied": "high"}]
        self.check(rows, rows[0])

    def test_a_trailing_false_row_is_returned_as_is(self):
        self.check([{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "working"}, {"t": 300, "awaiting": False, "why": ""}],
                   {"t": 300, "awaiting": False, "why": ""})

    def test_no_overlay_rows_and_no_file_are_none(self):
        self.assertIsNone(km._states_awaiting_overlay(SID))
        self.assertEqual(km._states_awaiting_overlay(SID), ref_overlay(SID))
        self.check([{"t": 100, "state": "working"}, {"t": 200, "state": "idle"}], None)

    def test_unparseable_lines_are_skipped(self):
        p = self.states_path(); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"t": 100, "awaiting": true, "why": "x"}\nnot json\n{"t": 200, "state": "idle"\n')
        self.assertEqual(km._states_awaiting_overlay(SID), ref_overlay(SID))
        self.assertEqual(km._states_awaiting_overlay(SID)["awaiting"], True)

    def test_an_unparseable_line_carrying_both_substrings_changes_nothing(self):
        # the one stated deviation from the old whole-file scan: that scan set working_after on an UNPARSEABLE
        # line that happened to carry '"state"' and '"working"', without parsing it; the fold sees parsed
        # records only, so the last parsed awaiting row stands. No states writer produces such a line.
        p = self.states_path(); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"t": 100, "awaiting": true, "why": "two jobs"}\n{"t": 200, "state": "working"\n')
        self.assertEqual(km._states_awaiting_overlay(SID), {"t": 100, "awaiting": True, "why": "two jobs"})
        self.assertEqual(ref_overlay(SID), {"awaiting": False, "why": None}, "the old scan's answer, superseded by the torn line")
        self.assertIn("parsed records only", km._states_overlay_step.__doc__)

    def test_a_read_failure_on_a_file_that_exists_is_counted_logged_once_and_not_memoized(self):
        rows = [{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "idle"}]
        self.check(rows, rows[0])
        self.assertEqual(km._states_overlay_report()["entries"], 1)
        # the shared reader serves an UNCHANGED file's records on an identity hit without opening it, so a
        # permission flip alone is not a read attempt: the file grows first, then becomes unreadable
        with open(self.states_path(), "a") as f:
            f.write(json.dumps({"t": 300, "state": "working"}) + "\n")
        os.chmod(self.states_path(), 0)
        try:
            if os.access(self.states_path(), os.R_OK):
                self.skipTest("this user reads through mode 000 (root)")
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertIsNone(km._states_awaiting_overlay(SID), "the old scan answered None on OSError")
                self.assertIsNone(km._states_awaiting_overlay(SID))
            st = km._states_overlay_report()
            self.assertEqual((st["fail"], st["entries"]), (2, 0), "counted per call, memoized never")
            self.assertEqual(err.getvalue().count("unreadable"), 1, "one stderr line per failure episode")
            self.assertEqual(km._states_awaiting_overlay(SID), ref_overlay(SID))
        finally:
            os.chmod(self.states_path(), 0o644)
        self.assertEqual(km._states_awaiting_overlay(SID), {"awaiting": False, "why": None},
                         "readable again: folded from record 0 over the three rows")
        self.assertEqual(km._states_awaiting_overlay(SID), ref_overlay(SID))
        st = km._states_overlay_report()
        self.assertEqual((st["entries"], st["refold"]), (1, 2))
        self.assertNotIn(str(self.states_path()), km._states_overlay_failed, "a good read ends the episode")

    def _counting_step(self):
        real = km._states_overlay_step
        calls = []

        def step(state, o):
            calls.append(o)
            return real(state, o)
        km._states_overlay_step = step
        self.addCleanup(setattr, km, "_states_overlay_step", real)
        return calls

    def test_an_appended_row_folds_without_re_parsing_the_earlier_records(self):
        calls = self._counting_step()
        rows = [{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "idle"}, {"t": 300, "state": "waiting"}]
        self.check(rows, rows[0])
        self.assertEqual(len(calls), 3, "the first fold steps every record")
        del calls[:]
        self.assertEqual(km._states_awaiting_overlay(SID), rows[0])
        self.assertEqual(calls, [], "unchanged: a hit steps nothing")
        with open(self.states_path(), "a") as f:
            f.write(json.dumps({"t": 400, "state": "working"}) + "\n")
        self.assertEqual(km._states_awaiting_overlay(SID), {"awaiting": False, "why": None})
        self.assertEqual(km._states_awaiting_overlay(SID), ref_overlay(SID))
        self.assertEqual(len(calls), 1, "the append folds only the new row")
        st = km._states_overlay_report()
        self.assertEqual((st["refold"], st["hit"], st["append"], st["entries"]), (1, 2, 1, 1),
                         "one first fold, the unchanged read and the post-append oracle read as hits, one append")

    def test_a_truncated_file_refolds_from_the_start(self):
        calls = self._counting_step()
        rows = [{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "working"}, {"t": 300, "state": "idle"}]
        self.check(rows, {"awaiting": False, "why": None})
        del calls[:]
        self.write_states(rows[:1])                              # shrank: the work turn is gone
        self.assertEqual(km._states_awaiting_overlay(SID), rows[0])
        self.assertEqual(km._states_awaiting_overlay(SID), ref_overlay(SID))
        self.assertEqual(len(calls), 1, "re-folded from record 0 over the one record left")
        self.assertEqual(km._states_overlay_report()["refold"], 2)

    def test_a_same_size_rewrite_with_a_new_mtime_refolds(self):
        rows = [{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "waiting"}]
        self.check(rows, rows[0])
        p = self.states_path()
        st0 = os.stat(p)
        rows2 = [{"t": 100, "awaiting": True, "why": "x"}, {"t": 200, "state": "working"}]   # same byte length
        self.write_states(rows2)
        self.assertEqual(os.stat(p).st_size, st0.st_size)
        os.utime(p, ns=(st0.st_atime_ns, st0.st_mtime_ns + 2_000_000_000))
        self.assertEqual(km._states_awaiting_overlay(SID), {"awaiting": False, "why": None})
        self.assertEqual(km._states_awaiting_overlay(SID), ref_overlay(SID))

    def test_forget_releases_entries_for_sessions_outside_the_alive_set(self):
        for s in (SID, SID2):
            self.check([{"t": 100, "awaiting": True, "why": "x"}], {"t": 100, "awaiting": True, "why": "x"}, sid=s)
        self.assertEqual(km._states_overlay_report()["entries"], 2)
        km._states_overlay_forget({SID})
        st = km._states_overlay_report()
        self.assertEqual((st["entries"], st["evict"]), (1, 1))
        self.assertIn(str(self.states_path(SID)), km._states_overlay_cache)

    def test_the_interrupt_tick_forgets_with_the_cycles_alive_set(self):
        src = inspect.getsource(km._interrupt_block_tick)
        self.assertIn("_states_overlay_forget(", src)


class ThreadRegMemo(_State):
    """`_thread_reg(tsid)` memoized on the registry file's identity, taken before the read."""

    REG = {"name": "web", "cwd": "/work/notes-api", "alive": True, "lastSid": SID, "spawnedAt": T}

    def test_two_reads_one_parse_a_copy_each(self):
        self.publish_reg(self.REG)
        a = km._thread_reg(SID)
        b = km._thread_reg(SID)
        self.assertIsNot(a, b, "a hit hands out a shallow copy: a caller's edit never reaches the memo")
        self.assertEqual(a, b)
        self.assertEqual(a, self.REG)
        a["name"] = "mutated by a caller"
        self.assertEqual(km._thread_reg(SID)["name"], "web")
        st = km._thread_reg_report()
        self.assertEqual((st["miss"], st["hit"], st["entries"]), (1, 1, 1))

    def test_a_replace_publish_re_reads_even_at_equal_size(self):
        self.publish_reg(self.REG)
        a = km._thread_reg(SID)
        st0 = os.stat(self.reg_path())
        new = dict(self.REG, name="api")                          # same byte length
        tmp = self.reg_path().with_name("y.tmp")
        tmp.write_text(json.dumps(new))
        os.utime(tmp, ns=(st0.st_atime_ns, st0.st_mtime_ns))
        os.replace(tmp, self.reg_path())
        self.assertEqual(os.stat(self.reg_path()).st_size, st0.st_size)
        b = km._thread_reg(SID)
        self.assertIsNot(a, b)
        self.assertEqual(b["name"], "api")
        self.assertEqual(km._thread_reg_report()["miss"], 2)

    def test_absent_is_empty_and_drops_the_entry(self):
        self.assertEqual(km._thread_reg(SID), {})
        self.assertEqual(km._thread_reg_report()["entries"], 0)
        self.publish_reg(self.REG)
        self.assertEqual(km._thread_reg(SID), self.REG)
        os.unlink(self.reg_path())
        self.assertEqual(km._thread_reg(SID), {})
        self.assertEqual(km._thread_reg_report()["entries"], 0)

    def test_a_parse_or_read_failure_after_a_good_stat_is_not_memoized(self):
        self.reg_path().parent.mkdir(parents=True, exist_ok=True)
        self.reg_path().write_text("{ not a reg")
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(km._thread_reg(SID), {})
            self.assertEqual(km._thread_reg(SID), {})
        st = km._thread_reg_report()
        self.assertEqual((st["entries"], st["fail"]), (0, 2))
        self.assertEqual(err.getvalue().count("unreadable"), 1, "one stderr line per failure episode")
        self.publish_reg(self.REG)
        self.assertEqual(km._thread_reg(SID), self.REG)
        self.assertEqual(km._thread_reg_report()["entries"], 1)
        self.reg_path().write_text("[1, 2]")                       # a non-object document reads as {} and is the file's content
        self.assertEqual(km._thread_reg(SID), {})

    def test_the_memo_is_bounded_lru(self):
        saved = km._THREAD_REG_MEMO_MAX
        km._THREAD_REG_MEMO_MAX = 2
        try:
            for s in (SID, SID2, SID3):
                self.publish_reg(dict(self.REG, name=s[-4:]), tsid=s)
            km._thread_reg(SID); km._thread_reg(SID2); km._thread_reg(SID)
            km._thread_reg(SID3)
            self.assertEqual(set(km._thread_reg_memo), {SID, SID3}, "the least recently used goes, never the whole memo")
            self.assertEqual(km._thread_reg_report()["evict"], 1)
        finally:
            km._THREAD_REG_MEMO_MAX = saved

    def test_the_one_registry_writer_publishes_by_replace(self):
        src = Path(os.path.join(ROOT, "kernel", "sdk_backend.py")).read_text()
        m = re.search(r"def write_reg\(.*?\n(?=\n\n)", src, re.S)
        self.assertIsNotNone(m)
        self.assertIn("os.replace(tmp, p)", m.group(0))
        ksrc = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()
        self.assertNotRegex(ksrc, r'"sdk" / \([^)]*\)\)\.write_text\(', "no kernel writer rewrites a reg in place")

    def test_no_kernel_caller_writes_into_a_memoized_reg(self):
        src = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()
        bodies = re.split(r"\n(?=def |class )", src)
        seen = 0
        for body in bodies:
            if body.startswith("def _thread_reg("):
                continue
            for m in re.finditer(r"^(?:[^\n#]*?)\b(\w+)\s*=\s*\(?_thread_reg\(", body, re.M):
                name = m.group(1)
                seen += 1
                for pat in (r"\b%s\s*\[[^\]]*\]\s*=[^=]" % name, r"\b%s\.(pop|setdefault|update|clear|popitem)\(" % name,
                            r"\bdel\s+%s\[" % name):
                    self.assertIsNone(re.search(pat, body), "%s in %s" % (pat, body.split("\n", 1)[0]))
            for m in re.finditer(r"_thread_reg\([^)]*\)", body):
                tail = body[m.end():m.end() + 12]
                self.assertRegex(tail, r"^(\s*or\s*\{\})?\)?\.get\(|^\s*$|^\s*\n|^\)|^\s*#", "an inline use reads with .get: %r" % tail)
        self.assertGreater(seen, 3, "the pin found the bound callers")


class PerfWiring(_State):
    def test_the_snapshot_carries_the_three_memo_blocks(self):
        memos = km._PERF_STATS.snapshot()["memos"]
        self.assertEqual(set(memos["captions"]), {"hit", "miss", "fail", "evict", "entries"})
        self.assertEqual(set(memos["states_overlay"]), {"hit", "append", "refold", "fail", "evict", "entries"})
        self.assertEqual(set(memos["thread_reg"]), {"hit", "miss", "fail", "evict", "entries"})
        for blk in ("captions", "states_overlay", "thread_reg"):
            for k, v in memos[blk].items():
                self.assertIsInstance(v, int, "%s.%s" % (blk, k))

    def test_the_reference_names_the_three_memos(self):
        doc = Path(os.path.join(ROOT, "docs", "reference.md")).read_text()
        for name in ("`captions`", "`states_overlay`", "`thread_reg`"):
            self.assertIn(name, doc)

    def test_the_bench_empties_the_new_memos_for_its_cold_rows(self):
        src = Path(os.path.join(ROOT, "tools", "perf-bench.py")).read_text()
        for name in ("_caps_memo", "_thread_reg_memo", "_states_overlay_cache"):
            self.assertIn('"%s"' % name, src)


if __name__ == "__main__":
    unittest.main()
