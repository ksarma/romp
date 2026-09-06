#!/usr/bin/env python3
"""Tests for build_timeline's token-usage split:
  _session_tokens  — per-session transcript token sums (the SESSIONS half)
  _judge_usage     — the judge PIPELINE rollup from judge-usage.jsonl (per-judge / per-tier)
Synthetic data only (placeholder usage numbers, a temp state dir)."""
import calendar
import json
import os
import pathlib
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from importlib.machinery import SourceFileLoader

BIN = os.path.join(os.path.dirname(__file__), "..", "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()

NOW = 1781100000


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _asst(usage, ts=None, model=None, mid=None):
    msg = {"role": "assistant", "content": [], "usage": usage}
    if model is not None:
        msg["model"] = model
    if mid is not None:
        msg["id"] = mid
    o = {"type": "assistant", "message": msg}
    if ts is not None:
        o["timestamp"] = ts
    return json.dumps(o)


class SessionTokens(unittest.TestCase):
    def test_sums_windowed_usage_across_assistant_messages(self):
        t0 = NOW - 3600
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(_asst({"input_tokens": 10, "output_tokens": 5,
                           "cache_creation_input_tokens": 100, "cache_read_input_tokens": 200}, iso(NOW - 100)) + "\n")
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n")  # ignored
            f.write(_asst({"input_tokens": 3, "output_tokens": 7, "cache_read_input_tokens": 50}, iso(NOW - 50)) + "\n")  # missing cache_w
            f.write(_asst({"input_tokens": 999, "output_tokens": 999}, iso(NOW - 99999)) + "\n")  # OUTSIDE the window → dropped
            path = f.name
        try:
            self.assertEqual(km._session_tokens(path, t0),
                             {"in": 13, "out": 12, "cache_w": 100, "cache_r": 250})
        finally:
            os.unlink(path)

    def test_missing_file_returns_zeros(self):
        self.assertEqual(km._session_tokens("/no/such/transcript.jsonl", NOW - 3600),
                         {"in": 0, "out": 0, "cache_w": 0, "cache_r": 0})

    def test_records_sharing_a_message_id_count_once(self):
        """The CLI writes a multi-block response as several assistant records sharing one message.id;
        summing records counted each response 2.3-3.0x. In a MAIN transcript the records repeat one usage
        block (2026-09-05: 2,515 groups, none differing); subagent transcripts differ — see the next
        test. One row per id, the largest output count kept; an id-less record stands alone."""
        u = {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 200}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            with open(p, "w") as f:
                for _ in range(3):
                    f.write(_asst(u, iso(NOW - 100), mid="msg_aaaa") + "\n")         # a 3-block response
                f.write(_asst({"input_tokens": 1, "output_tokens": 1}, iso(NOW - 90)) + "\n")   # no id
                f.write(_asst({"input_tokens": 1, "output_tokens": 1}, iso(NOW - 80)) + "\n")   # no id
                f.write(_asst({"input_tokens": 7, "output_tokens": 2}, iso(NOW - 70), mid="msg_bbbb") + "\n")
                # a split response whose LAST record carries a larger output count (a final tally): the
                # larger figure is the one kept, never both
                f.write(_asst({"input_tokens": 4, "output_tokens": 1}, iso(NOW - 60), mid="msg_cccc") + "\n")
                f.write(_asst({"input_tokens": 4, "output_tokens": 9}, iso(NOW - 59), mid="msg_cccc") + "\n")
            self.assertEqual(km._session_tokens(p, NOW - 3600),
                             {"in": 10 + 2 + 7 + 4, "out": 5 + 2 + 2 + 9, "cache_w": 100, "cache_r": 200})

    def test_subagent_same_id_records_keep_the_final_tally_whatever_their_order(self):
        """A SUBAGENT transcript's same-id records DIFFER: every record but the last carries the
        stream-start snapshot (a few output tokens) and the last the final tally — measured 2026-09-06
        over 30 days of subagent files, 94% of multi-record groups, the last record the maximum in every
        one. The fold keeps the LARGEST output count, in either order, so a first-record fold (about a
        tenth of the subagents' output) or a last-record fold cannot quietly replace it."""
        first = {"input_tokens": 4000, "output_tokens": 3, "cache_read_input_tokens": 50000}    # stream start
        last = {"input_tokens": 4000, "output_tokens": 1950, "cache_read_input_tokens": 50000}  # final tally
        with tempfile.TemporaryDirectory() as d:
            for name, order in (("a.jsonl", (first, first, last)), ("b.jsonl", (last, first, first))):
                pth = os.path.join(d, name)
                with open(pth, "w") as f:
                    for k, u in enumerate(order):
                        f.write(_asst(u, iso(NOW - 100 + k), mid="msg_sub") + "\n")
                self.assertEqual(km._session_tokens(pth, NOW - 3600),
                                 {"in": 4000, "out": 1950, "cache_w": 0, "cache_r": 50000},
                                 name + ": one row, the final tally's output count")

    def test_subagent_transcripts_beside_the_main_one_count_and_refresh_the_cache(self):
        """`<sid>/subagents/agent-<id>.jsonl` holds each spawned agent's conversation; its tokens are the
        session's spend too (the ledger already counts them via modelUsage). The row cache fingerprints
        every contributing file, so a subagent landing later refreshes the sum while the main file rests."""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "11111111-2222-3333-4444-555555555555.jsonl")
            with open(p, "w") as f:
                f.write(_asst({"input_tokens": 10, "output_tokens": 5}, iso(NOW - 100), mid="m1") + "\n")
            sub = pathlib.Path(d) / "11111111-2222-3333-4444-555555555555" / "subagents"
            sub.mkdir(parents=True)
            (sub / "agent-a1.jsonl").write_text(
                _asst({"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 1000},
                      iso(NOW - 90), mid="m2") + "\n"
                + _asst({"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 1000},
                        iso(NOW - 89), mid="m2") + "\n"                       # a split block, deduped too
                + _asst({"input_tokens": 999, "output_tokens": 999}, iso(NOW - 99999), mid="m3") + "\n")  # out of window
            (sub / "notes.txt").write_text("not a transcript\n")
            # a Workflow agent's transcript one level down (Claude Code 2.1.261 writes
            # subagents/workflows/wf_<id>/agent-<id>.jsonl): the walk is recursive, so it counts too
            wf = sub / "workflows" / "wf_1111-2222"
            wf.mkdir(parents=True)
            (wf / "agent-c3.jsonl").write_text(_asst({"input_tokens": 1000, "output_tokens": 500}, iso(NOW - 80), mid="m5") + "\n")
            # …but the walk never leaves the session's own tree: a symlinked directory is not followed
            other = pathlib.Path(d) / "elsewhere"
            other.mkdir()
            (other / "agent-zz.jsonl").write_text(_asst({"input_tokens": 7777, "output_tokens": 7777}, iso(NOW - 70), mid="m6") + "\n")
            os.symlink(other, sub / "linked")
            # …nor is a symlinked FILE: os.walk lists one like any other file (only DIRECTORY links go
            # unfollowed), so before 2026-09-06 the reader opened it wherever it pointed — outside the tree
            os.symlink(other / "agent-zz.jsonl", sub / "agent-link.jsonl")
            self.assertEqual(km._session_tokens(p, NOW - 3600), {"in": 1110, "out": 555, "cache_w": 0, "cache_r": 1000})
            # a second subagent lands; the main transcript's mtime has not moved
            mt = os.path.getmtime(p)
            (sub / "agent-b2.jsonl").write_text(_asst({"input_tokens": 1, "output_tokens": 1}, iso(NOW - 10), mid="m4") + "\n")
            os.utime(p, (mt, mt))
            self.assertEqual(km._session_tokens(p, NOW - 3600)["in"], 1111, "the new subagent file refreshes the rows")
            # a NESTED file growing refreshes them too (its mtime is in the fingerprint like any other)
            with (wf / "agent-c3.jsonl").open("a") as f:
                f.write(_asst({"input_tokens": 1, "output_tokens": 1}, iso(NOW - 5), mid="m7") + "\n")
            os.utime(p, (mt, mt))
            self.assertEqual(km._session_tokens(p, NOW - 3600)["in"], 1112, "a nested file's growth refreshes the rows")
            self.assertEqual(km._subagent_transcripts(p),
                             [str(sub / "agent-a1.jsonl"), str(sub / "agent-b2.jsonl"), str(wf / "agent-c3.jsonl")],
                             "sorted, nested files included, the symlinked directory not walked, the symlinked file skipped")
            self.assertEqual(km._subagent_transcripts(os.path.join(d, "no-such.jsonl")), [])
            self.assertEqual(km._subagent_transcripts(os.path.join(d, "x.txt")), [])

    def test_a_symlinked_subagents_directory_is_not_walked_either(self):
        """os.walk follows its TOP argument even when it is a symlink (followlinks governs the descent, not
        the root), so `<sid>/subagents` itself pointing elsewhere would read another tree wholesale."""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "11111111-2222-3333-4444-555555555555.jsonl")
            with open(p, "w") as f:
                f.write(_asst({"input_tokens": 10, "output_tokens": 5}, iso(NOW - 100), mid="m1") + "\n")
            other = pathlib.Path(d) / "elsewhere"
            other.mkdir()
            (other / "agent-zz.jsonl").write_text(_asst({"input_tokens": 7777, "output_tokens": 7777}, iso(NOW - 70), mid="m6") + "\n")
            sid_dir = pathlib.Path(d) / "11111111-2222-3333-4444-555555555555"
            sid_dir.mkdir()
            os.symlink(other, sid_dir / "subagents")
            self.assertEqual(km._subagent_transcripts(p), [])
            self.assertEqual(km._session_tokens(p, NOW - 3600), {"in": 10, "out": 5, "cache_w": 0, "cache_r": 0})


class JudgeUsageIncrementalCache(unittest.TestCase):
    """_judge_usage_rows (2026-08-13): the append-only, never-rotated judge-usage.jsonl used to be
    re-read and re-parsed IN FULL by both the analytics modal and every timeline build (38.7 MB
    measured) — the term that froze the dashboard as the log grew. Rows now parse once, appends parse
    from the last byte offset, and the cache is keyed on the PATH too (a test repointing jd.STATE must
    never inherit another dir's offset — the overrides-sandbox lesson)."""
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = pathlib.Path(self.td.name)
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])

    def tearDown(self):
        jd.STATE = self.saved
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        self.td.cleanup()

    def _row(self, t, judge="captioner", **kw):
        return json.dumps({"t": t, "judge": judge, "tier": kw.get("tier", "index"),
                           "in": kw.get("i", 10), "out": kw.get("o", 5),
                           "cost": kw.get("cost", 0.01), "ms": 100})

    def test_appends_parse_incrementally_and_rollup_reads_the_cache(self):
        p = jd.STATE / "judge-usage.jsonl"
        p.write_text(self._row(NOW - 1800) + "\n")
        self.assertEqual(len(km._judge_usage_rows()), 1)
        u = km._judge_usage(NOW - 3600)
        self.assertEqual(u["total"]["calls"], 1)
        with p.open("a") as fh:                          # an append parses from the offset, not from zero
            fh.write(self._row(NOW - 600, judge="planner", tier="triage", i=70, o=30) + "\n")
        rows = km._judge_usage_rows()
        self.assertEqual(len(rows), 2)
        u = km._judge_usage(NOW - 3600)
        self.assertEqual(u["total"]["calls"], 2)
        self.assertEqual(u["byJudge"]["planner"]["in"], 70)

    def test_a_mid_append_partial_line_waits_for_its_newline(self):
        p = jd.STATE / "judge-usage.jsonl"
        p.write_text(self._row(NOW - 1800) + "\n")
        self.assertEqual(len(km._judge_usage_rows()), 1)
        with p.open("a") as fh:
            fh.write('{"t": ')                           # the writer is mid-append
        self.assertEqual(len(km._judge_usage_rows()), 1, "the fragment is left for the next read")
        with p.open("a") as fh:
            fh.write(str(NOW - 60) + ', "judge": "closer", "in": 1, "out": 1, "cost": 0, "ms": 1}\n')
        self.assertEqual(len(km._judge_usage_rows()), 2, "…and picked up whole once complete")

    def test_repointing_state_never_inherits_an_offset(self):
        (jd.STATE / "judge-usage.jsonl").write_text(self._row(NOW - 1800) + "\n")
        self.assertEqual(len(km._judge_usage_rows()), 1)
        td2 = tempfile.TemporaryDirectory()
        try:
            jd.STATE = pathlib.Path(td2.name)            # a different state dir (the sandbox trap)
            (jd.STATE / "judge-usage.jsonl").write_text(
                self._row(NOW - 300, judge="grouper") + "\n")
            rows = km._judge_usage_rows()
            self.assertEqual([r["judge"] for r in rows], ["grouper"], "fresh path → fresh parse")
        finally:
            jd.STATE = pathlib.Path(self.td.name)
            td2.cleanup()

    def test_truncation_resets_cleanly(self):
        p = jd.STATE / "judge-usage.jsonl"
        p.write_text(self._row(NOW - 1800) + "\n" + self._row(NOW - 900) + "\n")
        self.assertEqual(len(km._judge_usage_rows()), 2)
        p.write_text(self._row(NOW - 60) + "\n")         # rotated/truncated
        self.assertEqual(len(km._judge_usage_rows()), 1)


class JudgeUsageRollup(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = pathlib.Path(self.td.name)

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()

    def _write(self, rows):
        (jd.STATE / "judge-usage.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def test_empty_when_no_log(self):
        r = km._judge_usage(NOW - 3600)
        self.assertEqual(r["total"]["calls"], 0)
        self.assertEqual(r["byJudge"], {})
        self.assertEqual(r["byTier"], {})

    def test_rolls_up_total_byjudge_bytier_and_windows(self):
        self._write([
            {"t": NOW - 100, "judge": "captioner", "tier": "index", "in": 10, "out": 5, "cost": 0.01, "ms": 800},
            {"t": NOW - 50, "judge": "captioner", "tier": "index", "in": 20, "out": 8, "cost": 0.02, "ms": 900},
            {"t": NOW - 30, "judge": "planner", "tier": "triage", "in": 100, "out": 40, "cost": 0.3, "ms": 2500},
            {"t": NOW - 99999, "judge": "planner", "tier": "triage", "in": 999, "out": 999, "cost": 9.9, "ms": 9999},
        ])
        r = km._judge_usage(NOW - 3600)
        self.assertEqual(r["total"]["calls"], 3, "the out-of-window row is dropped")
        self.assertEqual(r["total"]["in"], 130)
        self.assertEqual(r["total"]["out"], 53)
        self.assertAlmostEqual(r["total"]["cost"], 0.33)
        self.assertEqual(r["byJudge"]["captioner"]["calls"], 2)
        self.assertEqual(r["byJudge"]["captioner"]["in"], 30)
        self.assertEqual(r["byJudge"]["planner"]["in"], 100)
        self.assertEqual(r["byTier"]["index"]["calls"], 2)
        self.assertEqual(r["byTier"]["triage"]["in"], 100)

    def test_garbled_lines_are_skipped(self):
        (jd.STATE / "judge-usage.jsonl").write_text(
            '{"t":%d,"judge":"closer","tier":"triage","in":5,"out":2}\nnot json\n' % NOW)
        r = km._judge_usage(NOW - 3600)
        self.assertEqual(r["total"]["calls"], 1)
        self.assertEqual(r["byJudge"]["closer"]["out"], 2)


class AttachRunUsage(unittest.TestCase):
    """_attach_run_usage greedily matches each judging mark to the judge's nearest real call in
    judge-usage.jsonl (same fsid+judge), so a band block's tooltip can sum members' ms + tokens."""
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = pathlib.Path(self.td.name)

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()

    def test_matches_marks_to_nearest_runs_same_session(self):
        (jd.STATE / "judge-usage.jsonl").write_text("\n".join(json.dumps(r) for r in [
            {"t": NOW - 95, "judge": "captioner", "fsid": "S1", "ms": 800, "in": 10, "out": 5},
            {"t": NOW - 45, "judge": "captioner", "fsid": "S1", "ms": 900, "in": 20, "out": 8},
            {"t": NOW - 40, "judge": "captioner", "fsid": "S2", "ms": 700, "in": 30, "out": 9},
        ]) + "\n")
        judging = [
            {"judge": "captioner", "sid": "S1", "t": NOW - 100, "kind": "segment", "text": "a"},
            {"judge": "captioner", "sid": "S1", "t": NOW - 50, "kind": "turn", "text": "b"},
            {"judge": "planner", "sid": "S1", "t": NOW - 50, "kind": "mint", "text": "c"},
        ]
        km._attach_run_usage(judging, NOW - 3600, {"S1", "S2"})
        self.assertEqual((judging[0]["ms"], judging[0]["in"], judging[0]["out"]), (800, 10, 5))
        self.assertEqual((judging[1]["ms"], judging[1]["in"], judging[1]["out"]), (900, 20, 8), "each run consumed once")
        self.assertEqual((judging[2]["ms"], judging[2]["in"], judging[2]["out"]), (0, 0, 0), "planner mark unmatched → zeros")

    def test_no_log_leaves_zeros(self):
        judging = [{"judge": "captioner", "sid": "S1", "t": NOW, "kind": "segment", "text": "x"}]
        km._attach_run_usage(judging, NOW - 3600, {"S1"})
        self.assertEqual((judging[0]["ms"], judging[0]["in"], judging[0]["out"]), (0, 0, 0))
        self.assertEqual((judging[0]["sent"], judging[0]["recv"]), (None, None), "no log → no API times")

    def test_attaches_literal_api_sent_recv_to_the_matched_mark(self):
        # The literal API call window (the user 2026-06-19): each judge-usage row carries `sent`/`recv`
        # floats (when the prompt went out / the response came back). _attach_run_usage copies them onto the
        # matched mark so the band's hover can show the judge's REAL run interval, distinct from the
        # work-time the mark sits at. An unmatched mark keeps None.
        (jd.STATE / "judge-usage.jsonl").write_text("\n".join(json.dumps(r) for r in [
            {"t": NOW - 44, "judge": "distiller", "fsid": "S1", "ms": 4200, "in": 50, "out": 12,
             "sent": NOW - 48.6, "recv": NOW - 44.4},
        ]) + "\n")
        judging = [{"judge": "distiller", "sid": "S1", "t": NOW - 46, "kind": "distill", "text": "k"},
                   {"judge": "distiller", "sid": "S1", "t": NOW - 900, "kind": "distill", "text": "old"}]
        km._attach_run_usage(judging, NOW - 3600, {"S1"})
        self.assertEqual((judging[0]["sent"], judging[0]["recv"]), (NOW - 48.6, NOW - 44.4),
                         "the matched mark carries the literal API send/response wall-clock")
        self.assertEqual(judging[0]["ms"], 4200)
        self.assertEqual((judging[1]["sent"], judging[1]["recv"]), (None, None), "far-off mark unmatched → None")


class TokenAnalytics(unittest.TestCase):
    """_token_analytics: ONE arbitrary window (the analytics modal's period picker) → the coding
    SESSIONS total vs the judge pipeline broken out per judge AND per tier. discover() supplies the
    session fleet; jd.STATE points at a temp judge-usage.jsonl."""
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved_state, self.saved_discover = jd.STATE, jd.discover
        self.saved_cfg, self.saved_refresh = km.PRICE_CONFIG, km._refresh_remote_prices
        self.saved_auth = (km._auth_key_present, km._claude_account)
        km._auth_key_present, km._claude_account = (lambda: False), (lambda: "")   # no key, no login unless a test says
        jd.STATE = pathlib.Path(self.td.name)
        km.PRICE_CONFIG = pathlib.Path(self.td.name) / "no-prices.json"   # nonexistent → defaults only
        km._refresh_remote_prices = lambda now: None                     # no network in tests
        km._ANALYTICS_MEMO.clear()                                       # the TTL memo must not leak across tests
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])

    def tearDown(self):
        jd.STATE, jd.discover = self.saved_state, self.saved_discover
        km.PRICE_CONFIG, km._refresh_remote_prices = self.saved_cfg, self.saved_refresh
        km._auth_key_present, km._claude_account = self.saved_auth
        self.td.cleanup()

    def test_window_splits_sessions_vs_per_judge_and_tier(self):
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text(_asst({"input_tokens": 100, "output_tokens": 20}, iso(NOW - 1800)) + "\n" +     # in window
                      _asst({"input_tokens": 999, "output_tokens": 999}, iso(NOW - 99999)) + "\n")     # outside → dropped
        p2 = pathlib.Path(self.td.name) / "s2.jsonl"
        p2.write_text(_asst({"input_tokens": 30, "output_tokens": 8}, iso(NOW - 600)) + "\n")
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1"), ("fs2", p2, "a2", "s2")]
        (jd.STATE / "judge-usage.jsonl").write_text("\n".join(json.dumps(r) for r in [
            {"t": NOW - 900, "judge": "captioner", "tier": "index", "in": 10, "out": 4, "cost": 0.01, "ms": 50},
            {"t": NOW - 800, "judge": "archiver", "tier": "index", "in": 6, "out": 2, "cost": 0.01, "ms": 40},
            {"t": NOW - 700, "judge": "planner", "tier": "triage", "in": 70, "out": 30, "cost": 0.2, "ms": 300},
            {"t": NOW - 50000, "judge": "planner", "tier": "triage", "in": 999, "out": 999, "cost": 9, "ms": 9},  # >1h → dropped
        ]) + "\n")
        a = km._token_analytics(NOW, 3600)
        self.assertEqual(a["window"], 3600)
        self.assertEqual((a["sessions"]["in"], a["sessions"]["out"]), (130, 28), "both sessions summed, windowed")
        self.assertEqual(a["judges"]["total"]["in"], 86, "10+6+70; the >1h planner call dropped")
        self.assertEqual(set(a["judges"]["byJudge"]), {"captioner", "archiver", "planner"})
        self.assertEqual(a["judges"]["byJudge"]["planner"]["out"], 30)
        self.assertEqual(a["judges"]["byTier"]["index"]["in"], 16, "captioner+archiver share the index tier")
        self.assertEqual(a["judges"]["byTier"]["triage"]["in"], 70)

    def test_empty_fleet_and_no_log_is_zero_but_shaped(self):
        jd.discover = lambda now, window=None, forks=True: []
        a = km._token_analytics(NOW, 86400)
        self.assertEqual((a["sessions"]["in"], a["sessions"]["out"], a["sessions"]["cost"]), (0, 0, 0.0))
        self.assertEqual(a["judges"]["total"]["calls"], 0)
        self.assertEqual(a["judges"]["byJudge"], {})
        self.assertNotIn("ledger", a["sessions"], "no spend.json → no ledger figure, the estimate stands alone")

    def test_the_ledgers_own_cost_rides_the_sessions_side_where_spend_json_reaches(self):
        """The rail's ledger holds the CLI's own per-turn cost (2026-09-05: the token-price estimate read
        1.55x that over a day). Hour buckets for a window inside the 8-day hour ledger, day buckets
        beyond; a ledger that starts inside the window says `since`."""
        jd.discover = lambda now, window=None, forks=True: []
        # a clock AFTER the per-turn fix (NOW is June 2026, before it): the ledger's `preFix` caveat is
        # exercised on its own below, with one deliberately old bucket
        later = time.mktime((2026, 10, 15, 12, 0, 0, 0, 0, -1))
        hk = lambda n: time.strftime("%Y-%m-%dT%H", time.localtime(later - n * 3600))
        dk = lambda n: (datetime.fromtimestamp(later).date() - timedelta(days=n)).isoformat()
        hours = {hk(0): {"usd": 1.5, "turns": 2, "tokIn": 10, "tokCacheR": 90},
                 hk(1): {"usd": 2.0, "turns": 1, "tokOut": 5},
                 hk(5): {"usd": 100.0, "turns": 9}}                        # outside a 1h window
        days = {dk(0): {"usd": 3.5, "turns": 3, "tokIn": 105},
                dk(20): {"usd": 40.0, "turns": 7, "tokIn": 1000},
                dk(45): {"usd": 999.0, "turns": 1}}                          # outside a 30d window
        (jd.STATE / "spend.json").write_text(json.dumps({"days": days, "hours": hours}))
        a = km._token_analytics(later, 3600)
        self.assertEqual(a["sessions"]["ledger"], {"usd": 3.5, "turns": 3, "tok": 105},
                         "this hour + the previous one, the rail's rolling math")
        self.assertEqual((a["from"], a["buckets"]), (time.mktime((2026, 10, 15, 11, 0, 0, 0, 0, -1)), "hours"),
                         "the payload names the period's real start: the oldest bucket's")
        km._ANALYTICS_MEMO.clear()
        a = km._token_analytics(later, 30 * 86400)
        self.assertEqual(a["sessions"]["ledger"], {"usd": 43.5, "turns": 10, "tok": 1105},
                         "a 30-day window reads the day ledger and leaves the 45-day-old bucket out")
        # a ledger younger than the window names how far back it reaches
        km._ANALYTICS_MEMO.clear()
        (jd.STATE / "spend.json").write_text(json.dumps({"days": {dk(0): days[dk(0)], dk(20): days[dk(20)]}, "hours": hours}))
        self.assertEqual(km._token_analytics(later, 30 * 86400)["sessions"]["ledger"]["since"], dk(20))
        km._ANALYTICS_MEMO.clear()
        self.assertNotIn("since", km._token_analytics(later, 3600)["sessions"]["ledger"],
                         "hour buckets older than the window exist → no caveat")
        # a day recorded before the per-turn fix inside the window flags the sum (kept as recorded)
        km._ANALYTICS_MEMO.clear()
        aug = time.mktime((2026, 8, 20, 12, 0, 0, 0, 0, -1))
        adk = lambda n: (datetime.fromtimestamp(aug).date() - timedelta(days=n)).isoformat()
        (jd.STATE / "spend.json").write_text(json.dumps({"days": {adk(0): {"usd": 1.0, "turns": 1},
                                                                  adk(12): {"usd": 500.0, "turns": 4}}, "hours": {}}))
        led = km._token_analytics(aug, 30 * 86400)["sessions"]["ledger"]
        self.assertEqual((led["usd"], led["preFix"]), (501.0, True), "2026-08-08 is before the fix → flagged, not dropped")
        # an empty ledger is no ledger
        km._ANALYTICS_MEMO.clear()
        (jd.STATE / "spend.json").write_text(json.dumps({"days": {}, "hours": {}}))
        self.assertNotIn("ledger", km._token_analytics(later, 3600)["sessions"])

    def test_every_figure_is_cut_at_the_oldest_buckets_start(self):
        """The ledger sums whole buckets (the rail's rule: `1h` is this hour and the previous one), so the
        judge rows and the transcript rows are cut at the oldest bucket's START, not at now - window —
        otherwise a 1h view opened at :30 divided 60 minutes of judge dollars by 90 minutes of session
        dollars (2026-09-06). `from` in the payload is that start; `buckets` says hours or days."""
        clock = time.mktime((2026, 10, 15, 12, 30, 0, 0, 0, -1))
        start = time.mktime((2026, 10, 15, 11, 0, 0, 0, 0, -1))
        hk = lambda n: time.strftime("%Y-%m-%dT%H", time.localtime(clock - n * 3600))
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {hk(0): {"usd": 1.0, "turns": 1},
                                                                   hk(1): {"usd": 1.0, "turns": 1},
                                                                   hk(2): {"usd": 50.0, "turns": 1}}, "days": {}}))
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text(_asst({"input_tokens": 100, "output_tokens": 10}, iso(start + 120)) + "\n" +    # 11:02 — inside the oldest bucket, before now - 1h
                      _asst({"input_tokens": 1000, "output_tokens": 1}, iso(start - 120)) + "\n" +    # 10:58 — before the period
                      _asst({"input_tokens": 5, "output_tokens": 5}, iso(clock - 60)) + "\n")
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        (jd.STATE / "judge-usage.jsonl").write_text("\n".join(json.dumps(r) for r in [
            {"t": start + 60, "judge": "captioner", "tier": "index", "in": 10, "out": 4, "cost": 1.0, "ms": 50},   # 11:01 counts
            {"t": start - 60, "judge": "captioner", "tier": "index", "in": 10, "out": 4, "cost": 100.0, "ms": 50},  # 10:59 does not
            {"t": clock - 30, "judge": "planner", "tier": "triage", "in": 1, "out": 1, "cost": 1.0, "ms": 5},
        ]) + "\n")
        a = km._token_analytics(clock, 3600)
        self.assertEqual((a["from"], a["buckets"]), (start, "hours"))
        self.assertEqual(a["sessions"]["ledger"]["usd"], 2.0, "the two buckets, whole")
        self.assertEqual((a["sessions"]["in"], a["sessions"]["out"]), (105, 15), "rows from 11:00 on, the 10:58 row out")
        self.assertEqual(a["judges"]["total"]["cost"], 2.0, "judge rows from 11:00 on — the same cut as the ledger and the tokens")
        self.assertNotIn("fromDate", a, "hour edges are instants: the browser renders them in its own clock")
        # a day-bucket period starts at local midnight of the oldest date — and names that DATE as the
        # kernel's own string, because the buckets are the kernel's local dates and a browser west of the
        # kernel rendering the midnight epoch printed the day before (2026-09-06)
        km._ANALYTICS_MEMO.clear()
        a = km._token_analytics(clock, 30 * 86400)
        self.assertEqual((a["from"], a["buckets"]), (time.mktime((2026, 9, 15, 0, 0, 0, 0, 0, -1)), "days"))
        self.assertEqual(a["fromDate"], "2026-09-15")
        self.assertEqual(a["judges"]["total"]["calls"], 3, "every row is inside 31 local dates")

    def test_a_young_ledger_adds_the_estimate_for_the_time_before_it(self):
        """A ledger that began inside the period covers only its own span. The build prices the
        transcripts for [from, the ledger's first bucket) and hands it over as `estBefore`, so the modal
        shows ledger dollars plus a labelled estimate rather than a short ledger figure against a full
        period of judges (2026-09-06). `sinceT` is the first bucket's start; `cost` stays the estimate
        for the whole period, for the hover."""
        clock = time.mktime((2026, 10, 15, 12, 30, 0, 0, 0, -1))
        dk = lambda n: (datetime.fromtimestamp(clock).date() - timedelta(days=n)).isoformat()
        since_t = time.mktime((2026, 10, 14, 0, 0, 0, 0, 0, -1))
        (jd.STATE / "spend.json").write_text(json.dumps({"days": {dk(0): {"usd": 10.0, "turns": 2},
                                                                  dk(1): {"usd": 5.0, "turns": 1}}, "hours": {}}))
        start = time.mktime((2026, 9, 15, 0, 0, 0, 0, 0, -1))
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(start + 3600), model="claude-opus-4-8") + "\n"      # before the ledger
                      + _asst({"input_tokens": 1000, "output_tokens": 0}, iso(since_t + 3600), model="claude-opus-4-8") + "\n"  # inside it
                      + _asst({"input_tokens": 1000, "output_tokens": 0}, iso(start - 3600), model="claude-opus-4-8") + "\n")   # before the period
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        a = km._token_analytics(clock, 30 * 86400)
        led = a["sessions"]["ledger"]
        self.assertEqual((led["usd"], led["since"], led["sinceT"]), (15.0, dk(1), since_t))
        self.assertEqual(led["sinceDate"], dk(1), "day buckets: the ledger's first date as the kernel's own string")
        self.assertAlmostEqual(led["estBefore"], 1000 * 5e-6, places=9, msg="only the row before the ledger's first bucket")
        self.assertAlmostEqual(a["sessions"]["cost"], 2 * 1000 * 5e-6, places=9, msg="the whole-period estimate, for the hover")
        self.assertEqual(a["sessions"]["in"], 2000)
        # a ledger older than the period carries neither `since` nor an estimate to add
        km._ANALYTICS_MEMO.clear()
        (jd.STATE / "spend.json").write_text(json.dumps({"days": {dk(0): {"usd": 10.0, "turns": 2},
                                                                  dk(40): {"usd": 1.0, "turns": 1}}, "hours": {}}))
        led = km._token_analytics(clock, 30 * 86400)["sessions"]["ledger"]
        self.assertEqual(led, {"usd": 10.0, "turns": 2, "tok": 0})

    def test_the_session_dollars_follow_the_rails_keyed_rule(self):
        """The rail's API cell counts key-billed turns only on a host that runs a login beside a key (a
        login turn's computed cost is billed to no one, the user 2026-08-08); with a key alone or no key
        it sums the total. The modal's ledger figure follows the same arms — it used to sum every
        bucket's total on every host while the docs called the two the same figure (2026-09-06) — and
        says `keyed` so the footnote can name what it left out."""
        clock = time.mktime((2026, 10, 15, 12, 30, 0, 0, 0, -1))
        hk = lambda n: time.strftime("%Y-%m-%dT%H", time.localtime(clock - n * 3600))
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            hk(0): {"usd": 40.0, "turns": 4, "tokIn": 400, "key": {"usd": 4.0, "turns": 1, "tok": 100}},   # 3 login turns + 1 key turn
            hk(1): {"usd": 2.0, "turns": 1, "tokIn": 20}}, "days": {}}))                                     # a login-only hour, no split
        jd.discover = lambda now, window=None, forks=True: []
        km._auth_key_present, km._claude_account = (lambda: True), (lambda: "0123456789ab")   # a key beside a login
        self.assertEqual(km._token_analytics(clock, 3600)["sessions"]["ledger"],
                         {"usd": 4.0, "turns": 1, "tok": 100, "keyed": True}, "mixed host: the key turn only")
        km._ANALYTICS_MEMO.clear()
        km._claude_account = lambda: ""                                                       # a key alone
        self.assertEqual(km._token_analytics(clock, 3600)["sessions"]["ledger"],
                         {"usd": 42.0, "turns": 5, "tok": 420}, "key-only host: every turn bills the key, the total")
        km._ANALYTICS_MEMO.clear()
        km._auth_key_present, km._claude_account = (lambda: False), (lambda: "0123456789ab")  # a login alone
        self.assertEqual(km._token_analytics(clock, 3600)["sessions"]["ledger"],
                         {"usd": 42.0, "turns": 5, "tok": 420}, "no key: the CLI's computed total, nothing to split")

    def test_a_key_configured_beside_a_login_but_never_used_keeps_the_total_as_the_rail_does(self):
        """The rail attaches the keyed split only when the keyed windows hold turns (`if any(turns …)`), so
        a mixed host that never used its key shows no spend cell at all. The modal had no such guard: it
        showed a $0.00 Sessions bar with the keyed footnote and 'judges = 0% of session cost' against real
        judge dollars (2026-09-06). Same guard now — the split arms on RECORDED key turns, in the rail's
        own day/week/month windows, not on a key merely being present."""
        clock = time.time()   # _spend_windows reads the wall clock; the buckets are keyed on it too
        hk = lambda n: time.strftime("%Y-%m-%dT%H", time.localtime(clock - n * 3600))
        dk = lambda n: (datetime.fromtimestamp(clock).date() - timedelta(days=n)).isoformat()
        (jd.STATE / "spend.json").write_text(json.dumps({
            "hours": {hk(0): {"usd": 40.0, "turns": 4, "tokIn": 400}, hk(30): {"usd": 3.0, "turns": 1}},   # login turns only
            "days": {dk(0): {"usd": 40.0, "turns": 4, "tokIn": 400}, dk(1): {"usd": 3.0, "turns": 1}}}))
        jd.discover = lambda now, window=None, forks=True: []
        km._auth_key_present, km._claude_account = (lambda: True), (lambda: "0123456789ab")   # a key beside a login…
        led = km._token_analytics(clock, 3600)["sessions"]["ledger"]
        self.assertEqual(led, {"usd": 40.0, "turns": 4, "tok": 400}, "…never used: the total, and no `keyed` flag")
        # one key-billed turn recorded anywhere in the rail's windows arms the split for every period
        km._ANALYTICS_MEMO.clear()
        (jd.STATE / "spend.json").write_text(json.dumps({
            "hours": {hk(0): {"usd": 40.0, "turns": 4, "tokIn": 400}, hk(30): {"usd": 3.0, "turns": 1, "key": {"usd": 3.0, "turns": 1, "tok": 30}}},
            "days": {dk(0): {"usd": 40.0, "turns": 4, "tokIn": 400}, dk(1): {"usd": 3.0, "turns": 1, "key": {"usd": 3.0, "turns": 1, "tok": 30}}}}))
        self.assertEqual(km._token_analytics(clock, 3600)["sessions"]["ledger"],
                         {"usd": 0.0, "turns": 0, "tok": 0, "keyed": True},
                         "the key is in use on this host: this hour's keyed split is an honest zero, as the rail's `1 hour` row is")


class AnalyticsEdgesUnderDst(unittest.TestCase):
    """The autumn fall-back day (2026-09-06): two consecutive clock hours format to one local hour key,
    the recorder folds both into that one bucket, and the modal's per-key sum added it twice where the
    rail's set counted it once. The keys are distinct now, and `_bucket_start` names the bucket's FIRST
    instant explicitly (mktime with isdst=-1 leaves the repeated hour to the C library), so the estimate
    for the time before a ledger born in that hour stops at the first 01:00 and never re-prices what the
    bucket holds. Runs under an explicit zone via tzset; the process zone is restored after each test."""
    def setUp(self):
        if not hasattr(time, "tzset"):
            self.skipTest("tzset is POSIX-only")
        self.saved_tz = os.environ.get("TZ")
        os.environ["TZ"] = "America/New_York"
        time.tzset()
        self.td = tempfile.TemporaryDirectory()
        self.saved_state, self.saved_discover = jd.STATE, jd.discover
        self.saved_cfg, self.saved_refresh = km.PRICE_CONFIG, km._refresh_remote_prices
        self.saved_auth = (km._auth_key_present, km._claude_account)
        km._auth_key_present, km._claude_account = (lambda: False), (lambda: "")
        jd.STATE = pathlib.Path(self.td.name)
        km.PRICE_CONFIG = pathlib.Path(self.td.name) / "no-prices.json"
        km._refresh_remote_prices = lambda now: None
        km._ANALYTICS_MEMO.clear()
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])

    def tearDown(self):
        if self.saved_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self.saved_tz
        time.tzset()
        jd.STATE, jd.discover = self.saved_state, self.saved_discover
        km.PRICE_CONFIG, km._refresh_remote_prices = self.saved_cfg, self.saved_refresh
        km._auth_key_present, km._claude_account = self.saved_auth
        self.td.cleanup()

    # 2026-11-01: EDT -> EST at 02:00 EDT (06:00Z); the two 01:00 hours are 05:00Z (EDT) and 06:00Z (EST)
    FIRST_0100 = calendar.timegm((2026, 11, 1, 5, 0, 0))
    SECOND_0100 = calendar.timegm((2026, 11, 1, 6, 0, 0))

    def test_the_repeated_hour_is_one_key_summed_once_and_the_period_still_covers_every_hour(self):
        now = calendar.timegm((2026, 11, 1, 8, 30, 0))                     # 03:30 EST
        kind, keys, t0 = km._analytics_edges(now, 86400)
        self.assertEqual(kind, "hours")
        self.assertEqual(len(keys), len(set(keys)), "no key twice: %r" % keys)
        self.assertEqual(len(keys), 24, "25 clock hours, 24 local hour keys — the 01 hour names two of them")
        self.assertEqual(keys[0], "2026-11-01T03")
        self.assertEqual(keys[2], "2026-11-01T01")
        self.assertEqual(keys[-1], "2026-10-31T04", "the oldest bucket: 24 clock hours before this one")
        self.assertEqual(t0, calendar.timegm((2026, 10, 31, 8, 0, 0)), "t0 is that bucket's start (04:00 EDT)")
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {"2026-11-01T01": {"usd": 1.0, "turns": 1, "tokIn": 10},
                                                                   "2026-10-30T00": {"usd": 50.0, "turns": 1}},   # older than the window
                                                         "days": {}}))
        self.assertEqual(km._spend_ledger_window(now, 86400), {"usd": 1.0, "turns": 1, "tok": 10},
                         "the bucket that holds both 01:00 hours is added once, as the rail's set adds it")

    def test_bucket_start_is_the_first_instant_the_key_names(self):
        self.assertEqual(km._bucket_start("2026-11-01T01"), self.FIRST_0100, "the daylight 01:00, not the standard one")
        self.assertEqual(km._bucket_start("2026-11-01T02"), calendar.timegm((2026, 11, 1, 7, 0, 0)), "02:00 exists once (EST)")
        self.assertEqual(km._bucket_start("2026-11-01"), calendar.timegm((2026, 11, 1, 4, 0, 0)), "midnight EDT")
        # the spring-forward gap: no instant formats to 02, so the library's normalized answer stands
        self.assertEqual(km._bucket_start("2026-03-08T02"), time.mktime((2026, 3, 8, 2, 0, 0, 0, 0, -1)))
        self.assertIsNone(km._bucket_start("not-a-key"))
        os.environ["TZ"] = "UTC"
        time.tzset()
        self.assertEqual(km._bucket_start("2026-07-01T12"), calendar.timegm((2026, 7, 1, 12, 0, 0)),
                         "a zone without DST: the isdst=1 arm does not round-trip and is ignored")

    def test_a_ledger_born_in_the_repeated_hour_prices_only_the_time_before_its_first_instant(self):
        """The T01 bucket holds the turns of BOTH 01:00 hours. sinceT is the first 01:00, so a row in the
        daylight hour is the ledger's, not the estimate's; a row in the 00 hour is estimated."""
        now = calendar.timegm((2026, 11, 1, 8, 30, 0))                     # 03:30 EST
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            "2026-11-01T01": {"usd": 2.0, "turns": 2}, "2026-11-01T02": {"usd": 1.0, "turns": 1},
            "2026-11-01T03": {"usd": 1.0, "turns": 1}}, "days": {}}))
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(self.FIRST_0100 + 1800), model="claude-opus-4-8") + "\n"     # 01:30 EDT: in the bucket
                      + _asst({"input_tokens": 1000, "output_tokens": 0}, iso(self.SECOND_0100 + 1800), model="claude-opus-4-8") + "\n"  # 01:30 EST: in the bucket
                      + _asst({"input_tokens": 1000, "output_tokens": 0}, iso(self.FIRST_0100 - 1800), model="claude-opus-4-8") + "\n")  # 00:30 EDT: before the ledger
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        led = km._token_analytics(now, 86400)["sessions"]["ledger"]
        self.assertEqual((led["usd"], led["since"], led["sinceT"]), (4.0, "2026-11-01T01", self.FIRST_0100))
        self.assertNotIn("sinceDate", led, "an hour edge is an instant, rendered in the browser's own clock")
        self.assertAlmostEqual(led["estBefore"], 1000 * 5e-6, places=9, msg="the 00:30 row alone; neither 01:30 row is re-priced")

    # ── t0 is the oldest bucket's FIRST instant, in every zone, whatever mktime did last ──────────────
    # The round-3 tests above open the view at 03:30 EST, where the current hour and the oldest key are
    # both unambiguous; there `this_hour - n*3600` and `_bucket_start(keys[-1])` agree. They part when the
    # oldest bucket IS the repeated hour (it spans two clock hours, so hour arithmetic lands on its second
    # 01:00), when midnight repeats (a zone whose fall-back crosses it), and in a 30-minute-shift zone.

    def _edges_start_at_the_oldest_buckets_first_instant(self, now, window):
        """_analytics_edges for (now, window), checked against the rule: t0 is the earliest instant that
        formats to the oldest key — it formats to it, the second before it does not — and for hour
        buckets it lies at or before now - window (the period covers the window asked for)."""
        kind, keys, t0 = km._analytics_edges(now, window)
        fmt = "%Y-%m-%dT%H" if kind == "hours" else "%Y-%m-%d"
        self.assertEqual(t0, km._bucket_start(keys[-1]), "t0 is the oldest bucket's start, per _bucket_start")
        self.assertEqual(time.strftime(fmt, time.localtime(t0)), keys[-1], "t0 lies in the oldest bucket")
        self.assertNotEqual(time.strftime(fmt, time.localtime(t0 - 1)), keys[-1], "and is its FIRST instant")
        if kind == "hours":
            self.assertLessEqual(t0, now - window, "the period covers the whole window asked for")
        return kind, keys, t0

    def test_t0_is_the_first_0100_when_the_oldest_bucket_is_the_repeated_hour(self):
        """1h at 02:30 EST on the fall-back day, 24h the next day, 7d a week on: the oldest key is the T01
        bucket, which holds 01:00 EDT AND 01:00 EST. Its start is the first of them; hour arithmetic from
        the current (unambiguous) hour gave the second, one hour late, whatever mktime did before."""
        for label, now, window in (("1h @ 02:30 EST Nov 1", calendar.timegm((2026, 11, 1, 7, 30, 0)), 3600),
                                   ("24h @ 01:30 EST Nov 2", calendar.timegm((2026, 11, 2, 6, 30, 0)), 86400),
                                   ("7d @ 01:30 EST Nov 8", calendar.timegm((2026, 11, 8, 6, 30, 0)), 7 * 86400)):
            with self.subTest(label):
                kind, keys, t0 = self._edges_start_at_the_oldest_buckets_first_instant(now, window)
                self.assertEqual((kind, keys[-1]), ("hours", "2026-11-01T01"))
                self.assertEqual(t0, self.FIRST_0100, "%s: the daylight 01:00, not the standard one" % label)

    def test_t0_does_not_depend_on_what_the_c_library_resolved_last(self):
        """Inside the repeated hour the current hour itself is ambiguous, and glibc's mktime(isdst=-1)
        answers with whichever offset its previous call resolved — so the old t0 moved with unrelated
        conversions elsewhere in the process (a _bucket_start call in the previous build was enough).
        Prime the library each way before asking; the answer must not move."""
        cases = ((calendar.timegm((2026, 11, 1, 5, 30, 0)), ["2026-11-01T01", "2026-11-01T00"],
                  calendar.timegm((2026, 11, 1, 4, 0, 0))),                    # 01:30 EDT: T01 + T00, from 00:00 EDT
                 (calendar.timegm((2026, 11, 1, 6, 30, 0)), ["2026-11-01T01"],
                  self.FIRST_0100))                                            # 01:30 EST: both 01 hours, one key
        for isdst in (0, 1, 0):
            time.mktime((2026, 11, 1, 1, 0, 0, 0, 0, isdst))                   # the library's last resolution
            for now, want_keys, want_t0 in cases:
                with self.subTest(isdst=isdst, now=time.strftime("%H:%M %Z", time.localtime(now))):
                    kind, keys, t0 = self._edges_start_at_the_oldest_buckets_first_instant(now, 3600)
                    self.assertEqual(keys, want_keys)
                    self.assertEqual(t0, want_t0)

    def test_the_1h_view_after_the_repeated_hour_counts_the_rows_its_ledger_figure_holds(self):
        """02:30 EST Nov 1, 1h: the ledger sums T02 and the whole T01 bucket (both 01:00 hours' turns).
        Cut at the second 01:00, the transcript and judge figures missed the daylight hour: three turns
        of session dollars against two rows of tokens and two judge calls. Every figure now starts at
        the first 01:00, and the 00 hour stays out."""
        now = calendar.timegm((2026, 11, 1, 7, 30, 0))                     # 02:30 EST
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            "2026-11-01T00": {"usd": 50.0, "turns": 1}, "2026-11-01T01": {"usd": 2.0, "turns": 2},
            "2026-11-01T02": {"usd": 1.0, "turns": 1}}, "days": {}}))
        rows = [self.FIRST_0100 + 1800, self.SECOND_0100 + 1800, now - 900]  # 01:30 EDT, 01:30 EST, 02:15 EST
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text("".join(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(t), model="claude-opus-4-8") + "\n"
                              for t in rows + [self.FIRST_0100 - 1800]))     # 00:30 EDT: the hour before the period
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        (jd.STATE / "judge-usage.jsonl").write_text("".join(
            json.dumps({"t": t, "judge": "captioner", "tier": "index", "in": 10, "out": 4, "cost": 1.0, "ms": 5}) + "\n"
            for t in rows) + json.dumps({"t": self.FIRST_0100 - 1800, "judge": "captioner", "tier": "index",
                                         "in": 10, "out": 4, "cost": 100.0, "ms": 5}) + "\n")
        a = km._token_analytics(now, 3600)
        self.assertEqual((a["from"], a["buckets"]), (self.FIRST_0100, "hours"))
        led = a["sessions"]["ledger"]
        self.assertEqual((led["usd"], led["turns"]), (3.0, 3), "T01 whole plus T02; T00 is out")
        self.assertNotIn("since", led, "the ledger predates the period")
        self.assertEqual(a["sessions"]["in"], 3000, "one row per ledger turn: the 01:30 EDT row counts, the 00:30 row does not")
        self.assertEqual((a["judges"]["total"]["calls"], a["judges"]["total"]["cost"]), (3, 3.0), "the same three hours of judges")

    def test_the_24h_view_the_next_day_starts_at_the_fall_back_days_first_0100(self):
        """01:30 EST Nov 2, 24h: 25 keys back to the T01 bucket of Nov 1. The ledger's five turns are
        matched by five transcript rows only if the period starts at 01:00 EDT; at 01:00 EST the 01:30
        EDT row fell out, and the modal compared 24 hours of ledger dollars with 23 hours of tokens."""
        now = calendar.timegm((2026, 11, 2, 6, 30, 0))                     # 01:30 EST Nov 2
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            "2026-10-31T23": {"usd": 50.0, "turns": 1}, "2026-11-01T00": {"usd": 50.0, "turns": 1},
            "2026-11-01T01": {"usd": 2.0, "turns": 2}, "2026-11-01T02": {"usd": 1.0, "turns": 1},
            "2026-11-01T03": {"usd": 1.0, "turns": 1}, "2026-11-02T01": {"usd": 1.0, "turns": 1}}, "days": {}}))
        rows = [self.FIRST_0100 + 1800, self.SECOND_0100 + 1800, self.SECOND_0100 + 5400,
                self.SECOND_0100 + 9000, now - 900]                        # 01:30 EDT, 01:30 / 02:30 / 03:30 EST, 01:15 EST Nov 2
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text("".join(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(t), model="claude-opus-4-8") + "\n"
                              for t in rows + [self.FIRST_0100 - 1800]))     # 00:30 EDT Nov 1: out
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        a = km._token_analytics(now, 86400)
        kind, keys, t0 = km._analytics_edges(now, 86400)
        self.assertEqual((len(keys), keys[-1]), (25, "2026-11-01T01"))
        self.assertEqual((a["from"], t0), (self.FIRST_0100, self.FIRST_0100))
        led = a["sessions"]["ledger"]
        self.assertEqual((led["usd"], led["turns"]), (5.0, 5), "T01 (both hours) through Nov 2 T01; T00 and Oct 31 are out")
        self.assertEqual(a["sessions"]["in"], 5000, "five rows for five ledger turns")

    def test_a_days_period_starts_at_the_first_midnight_where_the_fall_back_repeats_it(self):
        """A zone whose fall-back crosses midnight (Cuba: 01:00 CDT -> 00:00 CST on Nov 1, 2026) has two
        midnights on the oldest date; the day bucket holds both hours, and the period starts at the first.
        mktime(isdst=-1) for that midnight follows the library's previous call, so prime it each way."""
        os.environ["TZ"] = "America/Havana"
        time.tzset()
        first_midnight = calendar.timegm((2026, 11, 1, 4, 0, 0))            # 00:00 CDT
        second_midnight = calendar.timegm((2026, 11, 1, 5, 0, 0))           # 00:00 CST
        self.assertEqual(km._bucket_start("2026-11-01"), first_midnight)
        now = calendar.timegm((2026, 12, 1, 17, 0, 0))                     # noon CST, Dec 1
        for isdst in (0, 1):
            time.mktime((2026, 11, 1, 0, 0, 0, 0, 0, isdst))
            with self.subTest(isdst=isdst):
                kind, keys, t0 = self._edges_start_at_the_oldest_buckets_first_instant(now, 30 * 86400)
                self.assertEqual((kind, len(keys), keys[-1]), ("days", 31, "2026-11-01"))
                self.assertEqual(t0, first_midnight)
        # end to end: the ledger's Nov 1 bucket holds both midnight hours' turns; the rows must match it
        (jd.STATE / "spend.json").write_text(json.dumps({"days": {
            "2026-10-31": {"usd": 50.0, "turns": 1}, "2026-11-01": {"usd": 2.0, "turns": 2},
            "2026-12-01": {"usd": 1.0, "turns": 1}}, "hours": {}}))
        rows = [first_midnight + 1800, second_midnight + 1800, now - 3600]  # 00:30 CDT, 00:30 CST, 11:00 Dec 1
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text("".join(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(t), model="claude-opus-4-8") + "\n"
                              for t in rows + [first_midnight - 1800]))       # 23:30 CDT Oct 31: out
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        a = km._token_analytics(now, 30 * 86400)
        self.assertEqual((a["from"], a["fromDate"], a["buckets"]), (first_midnight, "2026-11-01", "days"))
        self.assertEqual((a["sessions"]["ledger"]["usd"], a["sessions"]["ledger"]["turns"]), (3.0, 3))
        self.assertEqual(a["sessions"]["in"], 3000, "the 00:30 CDT row is in the period, the Oct 31 row is not")

    def test_a_thirty_minute_shift_keeps_t0_on_the_oldest_buckets_first_instant(self):
        """Lord Howe Island shifts by 30 minutes (+10:30 <-> +11), so `now - n*3600` and the bucket
        edges drift apart by half an hour across either transition, and the repeated half hour (01:30 to
        02:00 on the fall-back day) shares the T01 key with the daylight hour before it. Smoke check: the
        rule holds across both transitions and in a plain winter hour."""
        os.environ["TZ"] = "Australia/Lord_Howe"
        time.tzset()
        for label, now, window in (("24h across the October spring-forward", calendar.timegm((2026, 10, 4, 1, 0, 0)), 86400),
                                   ("24h across the April fall-back", calendar.timegm((2026, 4, 5, 1, 30, 0)), 86400),
                                   ("1h after the repeated half hour", calendar.timegm((2026, 4, 4, 15, 45, 0)), 3600),
                                   ("1h in July", calendar.timegm((2026, 7, 1, 1, 45, 0)), 3600)):
            with self.subTest(label):
                kind, keys, t0 = self._edges_start_at_the_oldest_buckets_first_instant(now, window)
                self.assertEqual(kind, "hours")
        self.assertEqual(km._bucket_start("2026-04-05T01"), calendar.timegm((2026, 4, 4, 14, 0, 0)),
                         "01:00 at +11 — the first instant of a bucket that spans 90 minutes")


class CostWeighting(unittest.TestCase):
    """The cost-weighted analytics: SESSIONS priced tokens × _model_prices (defaults < remote feed <
    ~/.config override); JUDGES use claude's exact logged cost. The remote feed is monkeypatched off so
    these never touch the network."""
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved_cfg, self.saved_refresh = km.PRICE_CONFIG, km._refresh_remote_prices
        self.saved_remote = dict(km._price_cache.get("remote", {}))
        self.saved_state, self.saved_discover = jd.STATE, jd.discover
        km.PRICE_CONFIG = pathlib.Path(self.td.name) / "model-prices.json"
        km._refresh_remote_prices = lambda now: None      # no network in tests → defaults/config only
        km._price_cache["remote"] = {}
        jd.STATE = pathlib.Path(self.td.name)
        km._ANALYTICS_MEMO.clear()                        # the TTL memo must not leak across tests
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])

    def tearDown(self):
        km.PRICE_CONFIG, km._refresh_remote_prices = self.saved_cfg, self.saved_refresh
        km._price_cache["remote"] = self.saved_remote
        jd.STATE, jd.discover = self.saved_state, self.saved_discover
        self.td.cleanup()

    def test_price_for_exact_then_family_then_none(self):
        prices = {"claude-opus-4-8": {"in": 1, "out": 2, "cache_w": 3, "cache_r": 4}}
        self.assertEqual(km._price_for("claude-opus-4-8", prices)["out"], 2, "exact id")
        self.assertEqual(km._price_for("claude-opus-4-8-20990101", prices)["out"], 2, "same-family fallback")
        self.assertIsNone(km._price_for("some-other-model", prices), "unknown family → uncounted")

    def test_fable_and_sonnet5_are_priced_not_uncounted(self):
        # Regression: both signed as None AND matched no family, so their tokens costed $0 silently.
        prices = km._model_prices(NOW)
        for mid, rate in (("claude-fable-5", 50e-6), ("claude-sonnet-5", 15e-6)):
            row = km._price_for(mid, prices)
            self.assertIsNotNone(row, mid + " must be priced, not uncounted")
            self.assertEqual(row["out"], rate, mid + " output rate")
        self.assertEqual(km._price_for("claude-fable-5", prices)["in"], 10e-6, "fable input is 2x opus")
        self.assertEqual(km._price_for("claude-opus-4-8", prices)["in"], 5e-6, "opus rate unchanged")

    def test_fable_5_1_has_its_own_row_with_the_quarter_rate_cache_read(self):
        # Before the row existed the family fallback handed Fable 5.1 Fable 5's $1/Mtok cache read — 4x
        # its list rate (Claude Code 2.1.261's catalog: tier_10_50_cache_read_0_25), and the remote feed
        # could never correct it because only exact (family, major, minor) signatures match.
        prices = km._model_prices(NOW)
        row = km._price_for("claude-fable-5-1", prices)
        self.assertEqual((row["in"], row["out"], row["cache_w"], row["cache_r"]), (10e-6, 50e-6, 12.5e-6, 0.25e-6))
        self.assertEqual(km._price_for("claude-fable-5", prices)["cache_r"], 1e-6, "Fable 5 keeps its own rate")
        self.assertEqual(km._price_sig("claude-fable-5-1"), ("fable", "5", "1"), "signs distinctly, so the feed can reach it")
        self.assertEqual(km._price_for("claude-fable-5-1-20261201", prices)["cache_r"], 0.25e-6,
                         "…and a dated id of the same model lands on the fable-5-1 row by signature, not on the first fable row")

    def test_price_sig_signs_single_number_ids_and_ignores_date_suffixes(self):
        self.assertEqual(km._price_sig("claude-opus-4-8"), ("opus", "4", "8"), "X-Y pair still signs")
        self.assertEqual(km._price_sig("claude-haiku-4-5-20251001"), ("haiku", "4", "5"), "date after a minor")
        self.assertEqual(km._price_sig("claude-sonnet-5"), ("sonnet", "5", None), "single-number id")
        self.assertEqual(km._price_sig("claude-fable-5"), ("fable", "5", None), "fable family")
        self.assertEqual(km._price_sig("claude-sonnet-5-20260101"), ("sonnet", "5", None), "date is not a minor")
        self.assertIsNone(km._price_sig("gpt-4o"), "non-Anthropic id")

    def test_remote_feed_can_reach_every_baked_in_model(self):
        # _refresh_remote_prices builds `want` from DEFAULT_MODEL_PRICES; an id that cannot sign is
        # invisible to the feed forever, which is how fable/sonnet-5 would have stayed stale.
        want = {km._price_sig(k): k for k in km.DEFAULT_MODEL_PRICES if km._price_sig(k)}
        self.assertEqual(len(want), len(km.DEFAULT_MODEL_PRICES),
                         "every baked-in model must sign, or the feed can never refresh it")

    def test_config_overrides_default_price(self):
        km.PRICE_CONFIG.write_text(json.dumps(
            {"claude-opus-4-8": {"in": 9e-6, "out": 40e-6, "cache_w": 1e-6, "cache_r": 1e-7}}))
        pr = km._model_prices(NOW)
        self.assertEqual(pr["claude-opus-4-8"]["in"], 9e-6, "config overrides the baked-in default")
        self.assertEqual(pr["claude-sonnet-4-6"]["out"], 15e-6, "an unconfigured model keeps its default")

    def test_session_cost_prices_per_message_model_and_all_token_classes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, dir=self.td.name) as f:
            f.write(_asst({"input_tokens": 1000, "output_tokens": 500,
                           "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 40000},
                          iso(NOW - 100), model="claude-opus-4-8") + "\n")
            f.write(_asst({"input_tokens": 9, "output_tokens": 9}, iso(NOW - 99999),
                          model="claude-opus-4-8") + "\n")     # outside the window → not priced
            path = f.name
        prices = {"claude-opus-4-8": {"in": 5e-6, "out": 25e-6, "cache_w": 6.25e-6, "cache_r": 0.5e-6}}
        cost = km._session_cost(path, NOW - 3600, prices)
        expected = 1000 * 5e-6 + 500 * 25e-6 + 2000 * 6.25e-6 + 40000 * 0.5e-6   # cache reads count too
        self.assertAlmostEqual(cost, expected, places=9)

    def test_analytics_carries_cost_both_sides(self):
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text(_asst({"input_tokens": 1000, "output_tokens": 200, "cache_read_input_tokens": 100000},
                            iso(NOW - 600), model="claude-opus-4-8") + "\n")
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a", "s1")]
        (jd.STATE / "judge-usage.jsonl").write_text(json.dumps(
            {"t": NOW - 500, "judge": "captioner", "tier": "index", "in": 10, "out": 4,
             "cost": 0.0123, "ms": 50}) + "\n")
        a = km._token_analytics(NOW, 3600)
        # sessions: priced from defaults (opus $5/$25/Mtok + $0.5/Mtok cache read)
        exp_sess = 1000 * 5e-6 + 200 * 25e-6 + 100000 * 0.5e-6
        self.assertAlmostEqual(a["sessions"]["cost"], exp_sess, places=9)
        self.assertEqual(a["sessions"]["in"], 1000)
        # judges: the exact logged cost, not a token estimate
        self.assertAlmostEqual(a["judges"]["total"]["cost"], 0.0123, places=9)
        self.assertAlmostEqual(a["judges"]["byJudge"]["captioner"]["cost"], 0.0123, places=9)


if __name__ == "__main__":
    unittest.main()
