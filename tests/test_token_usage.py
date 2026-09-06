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
    bucket holds. Runs under an explicit zone via tzset; the process zone is restored after each test —
    by a cleanup registered BEFORE the zone changes, so a setUp that fails after it (a temp dir that
    cannot be made) still puts the zone back instead of leaking New York into every later test."""
    def setUp(self):
        if not hasattr(time, "tzset"):
            self.skipTest("tzset is POSIX-only")
        self.addCleanup(self._restore_tz, os.environ.get("TZ"))
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
        jd.STATE, jd.discover = self.saved_state, self.saved_discover
        km.PRICE_CONFIG, km._refresh_remote_prices = self.saved_cfg, self.saved_refresh
        km._auth_key_present, km._claude_account = self.saved_auth
        self.td.cleanup()

    @staticmethod
    def _restore_tz(saved):
        if saved is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = saved
        time.tzset()

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
        # the spring-forward gap: no instant formats to 02, so the key starts where the gap ends (03:00 EDT),
        # the same whichever offset the library's previous call left it on
        for isdst in (0, 1, 0):
            time.mktime((2026, 3, 8, 1, 0, 0, 0, 0, isdst))
            self.assertEqual(km._bucket_start("2026-03-08T02"), calendar.timegm((2026, 3, 8, 7, 0, 0)), "primed isdst=%d" % isdst)
        self.assertIsNone(km._bucket_start("not-a-key"))
        with self.assertRaises(ValueError):
            km._bucket_start("2026-02-31T05")                                   # well-formed, names no date: loud, never None
        os.environ["TZ"] = "UTC"
        time.tzset()
        self.assertEqual(km._bucket_start("2026-07-01T12"), calendar.timegm((2026, 7, 1, 12, 0, 0)),
                         "a zone without DST: one offset in play, one reading")

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

    # ── the hour keys are the buckets that intersect the window, walked, not sampled once an hour ──────
    # `now - i*3600` cannot see a bucket shorter than its stride. Lord Howe Island springs forward by 30
    # minutes (02:00 +10:30 -> 02:30 +11 on 2026-10-04), so the T02 bucket is the half hour 02:30-02:59
    # and the samples stepped from T03 straight to T01 over it: its turns were in no ledger figure while
    # t0 (the oldest bucket's first instant) put their transcript and judge rows in the period.
    LH_SPRING_T02 = calendar.timegm((2026, 10, 3, 15, 30, 0))              # 02:30 +11: the T02 bucket's first (and only) half hour

    @staticmethod
    def _recorder_keys(t0, now):
        """The keys the recorder gives turns in [t0, now] — one sample a minute, finer than any bucket."""
        return {time.strftime("%Y-%m-%dT%H", time.localtime(t)) for t in range(int(t0), int(now) + 1, 60)}

    def _every_bucket_in_the_window_once(self, now, window):
        """The keys are exactly the buckets that intersect [now - window, now], newest first, each once,
        consecutive (each is the bucket ending where the newer one starts), and t0 is the oldest's start."""
        kind, keys, t0 = km._analytics_edges(now, window)
        self.assertEqual(kind, "hours")
        self.assertEqual(len(keys), len(set(keys)), "each bucket once: %r" % keys)
        self.assertEqual(keys[0], time.strftime("%Y-%m-%dT%H", time.localtime(now)))
        self.assertEqual(keys[-1], time.strftime("%Y-%m-%dT%H", time.localtime(now - window)), "the oldest bucket holds now - window")
        self.assertEqual(t0, km._bucket_start(keys[-1]))
        for newer, older in zip(keys, keys[1:]):
            self.assertEqual(older, time.strftime("%Y-%m-%dT%H", time.localtime(km._bucket_start(newer) - 1)),
                             "%s is the bucket ending where %s starts" % (older, newer))
        self.assertEqual(set(keys), self._recorder_keys(t0, now), "every key the recorder would write in the period, and no other")
        # the walker's own run starts are _bucket_start's answer for every key — the modal's t0 rule, bucket by
        # bucket (a contiguous bucket is one run, so its run start is its first instant)
        self.assertEqual([(k, s) for k, s, _off0, _off1 in km._hour_buckets_back(now, window)], [(k, km._bucket_start(k)) for k in keys])
        return keys, t0

    def _ledger_rows_and_judges_agree(self, now, window):
        """End to end: one ledger turn, one transcript row and one judge call in EVERY bucket the recorder
        would key in the period (placed a minute into each bucket, independent of the edges under test),
        plus one of each just before the period. The modal's three figures must count the same turns."""
        keys, t0 = self._every_bucket_in_the_window_once(now, window)
        hours = {k: {"usd": 1.0, "turns": 1, "tokIn": 10} for k in keys}
        before = time.strftime("%Y-%m-%dT%H", time.localtime(t0 - 1))
        hours[before] = {"usd": 50.0, "turns": 1, "tokIn": 999}
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": hours, "days": {}}))
        rows = [km._bucket_start(k) + 60 for k in keys] + [t0 - 60]
        p1 = pathlib.Path(self.td.name) / ("s-%d-%d.jsonl" % (now, window))   # its own path per case: the row cache keys on path + mtime
        p1.write_text("".join(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(t), model="claude-opus-4-8") + "\n" for t in rows))
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        (jd.STATE / "judge-usage.jsonl").write_text("".join(
            json.dumps({"t": t, "judge": "captioner", "tier": "index", "in": 10, "out": 4, "cost": 1.0, "ms": 5}) + "\n" for t in rows))
        km._ANALYTICS_MEMO.clear()
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        a = km._token_analytics(now, window)
        led = a["sessions"]["ledger"]
        self.assertEqual(a["from"], t0)
        self.assertNotIn("since", led, "the ledger predates the period")
        self.assertEqual((led["usd"], led["turns"]), (float(len(keys)), len(keys)), "one turn per bucket in the period; the bucket before it is out")
        self.assertEqual(a["sessions"]["in"], 1000 * len(keys), "one transcript row per ledger turn")
        self.assertEqual((a["judges"]["total"]["calls"], a["judges"]["total"]["cost"]), (len(keys), float(len(keys))), "one judge call per ledger turn")
        # the rail's own window for the same span sums the same buckets — the modal's figure IS the rail cell's
        rail = km._spend_windows(now=now)
        self.assertEqual(rail["hour" if window == 3600 else "day"]["turns"], led["turns"], "the rail and the modal agree")
        return keys

    def test_a_thirty_minute_spring_forward_keeps_the_half_hour_bucket_in_the_24h_window(self):
        """12:10 +11 on 2026-10-04, 24h: 26 buckets back to 11:00 +10:30 the day before — the half-hour T02
        among them. Sampled once an hour the T02 key never came up (25 keys), so its turn was in no ledger
        figure while its transcript row and judge call, after t0, were: 25 turns against 26 rows."""
        os.environ["TZ"] = "Australia/Lord_Howe"
        time.tzset()
        now = calendar.timegm((2026, 10, 4, 1, 10, 0))                      # 12:10 +11 Oct 4
        keys = self._ledger_rows_and_judges_agree(now, 86400)
        self.assertEqual((len(keys), keys[-1]), (26, "2026-10-03T11"))
        self.assertIn("2026-10-04T02", keys, "the half-hour bucket is one key like any other")
        self.assertEqual(km._bucket_start("2026-10-04T02"), self.LH_SPRING_T02)
        self.assertEqual(km._bucket_start("2026-10-04T03"), self.LH_SPRING_T02 + 1800, "T03 starts half an hour after T02: the bucket is 30 minutes long")

    def test_a_thirty_minute_spring_forward_keeps_the_half_hour_bucket_in_the_1h_window(self):
        """03:15 +11 on 2026-10-04, 1h: now - 3600 is 01:45 +10:30, so the period is T03, T02, T01 — three
        buckets in 105 minutes. The samples were 03:15 and 01:45: T03 and T01, and the T02 turn dropped."""
        os.environ["TZ"] = "Australia/Lord_Howe"
        time.tzset()
        now = calendar.timegm((2026, 10, 3, 16, 15, 0))                     # 03:15 +11 Oct 4
        keys = self._ledger_rows_and_judges_agree(now, 3600)
        self.assertEqual(keys, ["2026-10-04T03", "2026-10-04T02", "2026-10-04T01"])
        self.assertEqual(km._analytics_edges(now, 3600)[2], calendar.timegm((2026, 10, 3, 14, 30, 0)), "t0: 01:00 +10:30")

    def test_walking_the_buckets_changes_nothing_where_every_shift_is_a_whole_hour(self):
        """Controls: a whole-hour shift never makes a bucket shorter than the old stride, so the walked keys
        are the sampled keys — the fall-back day's two-hour bucket once, the spring-forward gap no key — and
        a zone without DST gives n + 1 keys an hour apart. Same end-to-end agreement in each."""
        for tz, label, now, window, want in (
                ("America/New_York", "24h at 03:30 EST Nov 1: 25 clock hours, 24 keys", calendar.timegm((2026, 11, 1, 8, 30, 0)), 86400, (24, "2026-10-31T04")),
                ("America/New_York", "1h at 03:30 EDT Mar 8: T02 is a gap, not a bucket", calendar.timegm((2026, 3, 8, 7, 30, 0)), 3600, (2, "2026-03-08T01")),
                ("America/New_York", "1h at 02:30 EST Nov 1: the oldest bucket spans both 01:00 hours", calendar.timegm((2026, 11, 1, 7, 30, 0)), 3600, (2, "2026-11-01T01")),
                ("UTC", "24h in a zone without DST", calendar.timegm((2026, 11, 1, 8, 30, 0)), 86400, (25, "2026-10-31T08")),
                ("UTC", "1h in a zone without DST", calendar.timegm((2026, 11, 1, 8, 30, 0)), 3600, (2, "2026-11-01T07"))):
            with self.subTest(label):
                os.environ["TZ"] = tz
                time.tzset()
                keys = self._ledger_rows_and_judges_agree(now, window)
                self.assertEqual((len(keys), keys[-1]), want)

    # ── the Chatham Islands (+12:45): the clock changes at 02:45 / 03:45, so a change splits an hour ──────
    # Spring-forward (2026-09-27, 02:45 +12:45 -> 03:45 +13:45, at 14:00Z Sep 26): T02 is 02:00-02:44 (45
    # minutes) and T03 is 03:45-03:59 (15 minutes) — no 03:00 exists, so T03's start is the change itself.
    # Fall-back (2026-04-05, 03:45 +13:45 -> 02:45 +12:45, at 14:00Z Apr 4) replays 02:45-03:44: T02's
    # instants are 02:00-02:59 daylight AND 02:45-02:59 standard, with T03's first run between — one key,
    # two runs, and the whole-bucket sum holds turns from both.
    CH_CHANGE_SPRING = calendar.timegm((2026, 9, 26, 14, 0, 0))
    CH_CHANGE_FALL = calendar.timegm((2026, 4, 4, 14, 0, 0))

    def test_a_quarter_hour_bucket_after_a_mid_hour_spring_forward_is_in_every_window(self):
        """The bucket the old stride could least see: 15 minutes long, and its first instant is the change
        itself (03:45), which no reading of 03:00 names — the mktime-based _bucket_start (until 2026-09-06)
        returned a normalized instant in another bucket for it. Every figure counts its turn now, and the day
        after the change reads as 25 plain buckets."""
        os.environ["TZ"] = "Pacific/Chatham"
        time.tzset()
        self.assertEqual(km._bucket_start("2026-09-27T03"), self.CH_CHANGE_SPRING, "T03 starts at the change, 03:45")
        self.assertEqual(km._bucket_start("2026-09-27T02"), self.CH_CHANGE_SPRING - 45 * 60, "T02 starts at 02:00 and lasts 45 minutes")
        for label, now, window, want in (("1h at 04:05 +13:45", self.CH_CHANGE_SPRING + 20 * 60, 3600, (3, "2026-09-27T02")),
                                         ("24h at 04:05 +13:45", self.CH_CHANGE_SPRING + 20 * 60, 86400, (26, "2026-09-26T03")),
                                         ("24h a day later", self.CH_CHANGE_SPRING + 86400 + 20 * 60, 86400, (25, "2026-09-27T04"))):
            with self.subTest(label):
                keys = self._ledger_rows_and_judges_agree(now, window)
                self.assertEqual((len(keys), keys[-1]), want)
                if window == 3600:
                    self.assertEqual(keys, ["2026-09-27T04", "2026-09-27T03", "2026-09-27T02"], "three buckets in 65 minutes")

    def test_a_key_split_by_a_mid_hour_fall_back_reaches_back_to_its_first_run(self):
        """04:15 standard on the fall-back day, 1h: the walk meets T04 and T03's second run (03:00-03:59
        standard) — but the T03 bucket also holds 03:00-03:44 daylight, before the replay, and T02's holds
        02:45-02:59 standard between the two. The ledger's per-key sums hold every one of those turns, so
        the period starts at the earliest first instant among its keys (02:00 daylight) and takes in every
        key with an instant since: T04, T03, T02 — five turns, five rows, five judge calls, and the rail's
        `1 hour` sums the same three buckets. So this `1h` view spans 3h15m (04:15 standard back to 02:00
        daylight, which is 12:15Z to 15:30Z), and the modal says so through `from`."""
        os.environ["TZ"] = "Pacific/Chatham"
        time.tzset()
        ch = self.CH_CHANGE_FALL
        first_t02, first_t03 = ch - 105 * 60, ch - 45 * 60             # 02:00 and 03:00 daylight
        self.assertEqual((km._bucket_start("2026-04-05T02"), km._bucket_start("2026-04-05T03")), (first_t02, first_t03))
        now = ch + 90 * 60                                              # 04:15 standard
        self.assertEqual(km._hour_buckets_back(now, 3600), [("2026-04-05T04", ch + 75 * 60, 45900, 45900), ("2026-04-05T03", ch + 15 * 60, 45900, 45900)],
                         "the walk alone: T04, then T03's second run — its start is not the key's first instant; both start and end at +12:45")
        self.assertEqual(now - km._analytics_edges(now, 3600)[2], 195 * 60, "the 1h view spans 3h15m here")
        kind, keys, t0 = km._analytics_edges(now, 3600)
        self.assertEqual((kind, keys, t0), ("hours", ["2026-04-05T04", "2026-04-05T03", "2026-04-05T02"], first_t02))
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            "2026-04-05T01": {"usd": 50.0, "turns": 1}, "2026-04-05T02": {"usd": 2.0, "turns": 2},
            "2026-04-05T03": {"usd": 2.0, "turns": 2}, "2026-04-05T04": {"usd": 1.0, "turns": 1}}, "days": {}}))
        rows = [first_t02 + 900, first_t03 + 900, ch + 300, ch + 45 * 60, ch + 80 * 60]   # 02:15 dl, 03:15 dl, 02:50 std, 03:30 std, 04:05 std
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text("".join(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(t), model="claude-opus-4-8") + "\n"
                              for t in rows + [first_t02 - 900]))           # 01:45 daylight: out
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        (jd.STATE / "judge-usage.jsonl").write_text("".join(
            json.dumps({"t": t, "judge": "captioner", "tier": "index", "in": 10, "out": 4, "cost": 1.0, "ms": 5}) + "\n"
            for t in rows + [first_t02 - 900]))
        a = km._token_analytics(now, 3600)
        self.assertEqual(a["from"], first_t02)
        self.assertEqual((a["sessions"]["ledger"]["usd"], a["sessions"]["ledger"]["turns"]), (5.0, 5), "T02 (both runs), T03 (both runs), T04; T01 is out")
        self.assertEqual(a["sessions"]["in"], 5000, "one row per ledger turn — the daylight rows included")
        self.assertEqual(a["judges"]["total"]["calls"], 5)
        self.assertEqual(km._spend_windows(now=now)["hour"]["turns"], 5, "the rail's `1 hour` sums the same three buckets")

    def test_the_hover_series_adds_buckets_that_share_an_epoch_hour(self):
        """Chatham's spring-forward: T03 starts at 14:00Z and T04 at 14:15Z — one epoch hour, two buckets.
        A dense $/hour array has one slot for that hour, so the two buckets' dollars add there rather than
        the later key overwriting the earlier."""
        os.environ["TZ"] = "Pacific/Chatham"
        time.tzset()
        now = self.CH_CHANGE_SPRING + 20 * 60
        h0 = int(now // 3600) - (km._SERIES_HOURS - 1)
        i14 = int(self.CH_CHANGE_SPRING // 3600) - h0
        self.assertEqual((km._series_index("2026-09-27T02", h0), km._series_index("2026-09-27T03", h0), km._series_index("2026-09-27T04", h0)),
                         (i14 - 1, i14, i14))
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {"2026-09-27T02": {"usd": 4.0}, "2026-09-27T03": {"usd": 1.0},
                                                                   "2026-09-27T04": {"usd": 2.0}}, "days": {}}))
        ss = km._spend_series(now=now)
        self.assertEqual((ss["usd"][i14 - 1], ss["usd"][i14]), (4.0, 3.0))

    def test_the_hover_series_slots_the_repeated_hour_at_its_first_instant_whatever_mktime_did_last(self):
        """_series_index placed a key by mktime(strptime(key)) with isdst=-1, and for the fall-back day's T01
        glibc answers with the offset of its PREVIOUS call — so the bucket landed in one of two adjacent slots
        depending on unrelated conversions, and the hover's bar moved between builds with no turn behind it.
        The slot is the bucket's first instant now (the modal's rule); prime the library each way."""
        h0 = int(calendar.timegm((2026, 11, 1, 8, 30, 0)) // 3600) - (km._SERIES_HOURS - 1)
        first_slot = int(self.FIRST_0100 // 3600) - h0
        for isdst in (0, 1, 0, 1):
            time.mktime((2026, 11, 1, 1, 0, 0, 0, 0, isdst))                   # the library's last resolution
            with self.subTest(isdst=isdst):
                self.assertEqual(km._series_index("2026-11-01T01", h0), first_slot, "the daylight 01:00's slot")
                self.assertEqual(km._series_index("2026-11-01T02", h0), first_slot + 2, "02:00 EST: the slot after the standard 01:00's")
                self.assertEqual(km._series_index("2026-11-01T00", h0), first_slot - 1)
        self.assertIsNone(km._series_index("2026-11-01", h0), "a date key is not an hour key")
        self.assertIsNone(km._series_index(None, h0))
        self.assertIsNone(km._series_index("nonsense", h0))
        # the series itself: the bucket's dollars sit in the first 01:00's slot, the second stays an honest zero
        now = calendar.timegm((2026, 11, 1, 8, 30, 0))
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {"2026-11-01T01": {"usd": 2.0, "turns": 2}}, "days": {}}))
        for isdst in (1, 0):
            time.mktime((2026, 11, 1, 1, 0, 0, 0, 0, isdst))
            ss = km._spend_series(now=now)
            self.assertEqual((ss["h0"], ss["usd"][first_slot], ss["usd"][first_slot + 1]), (h0, 2.0, 0.0), "isdst primed %d" % isdst)

    # ── Antarctica/Troll (+00/+02): the longest fall-back tzdata still schedules, 03:00 +02 -> 01:00 +00 ──
    # (Antarctica/Casey's three-hour shifts ended in 2023 and Vostok's seven-hour one was 1994; see the
    # Antarctic-station test below for those).
    # 2026-10-25 at 01:00Z. The replay crosses the 02:00 boundary, so T01 and T02 each own two runs, and the
    # runs INTERLEAVE: T01 daylight [23:00Z, 00:00Z), T02 daylight [00:00Z, 01:00Z), T01 standard [01:00Z,
    # 02:00Z), T02 standard [02:00Z, 03:00Z). T02's standard run starts exactly one hour after the change.
    TR_CHANGE = calendar.timegm((2026, 10, 25, 1, 0, 0))

    def test_a_two_hour_fall_back_names_each_buckets_first_instant_whatever_mktime_did_last(self):
        """_bucket_start compared the offset at a run's start with the offset one hour earlier, and T02's
        standard run starts one hour after the change, where the new offset already applies: the arms never
        ran, and the key followed glibc's previous call — 00:00Z or 02:00Z, two hover slots apart. Round 6
        widened that check to two hours as "the longest replay in tzdata", which it is not (Casey's is three
        hours, Vostok's was seven), and the arms could not have told Casey's two standard-time offsets apart
        anyway. The start is now read off the key's own wall time at every offset in force around it, with
        no library hint at all (the Antarctic-station test below). Every fall-back this file names, under
        alternating primings."""
        x = self.TR_CHANGE
        cases = (("Antarctica/Troll", (2026, 10, 25, 2), {"2026-10-25T00": x - 3 * 3600, "2026-10-25T01": x - 2 * 3600,
                                                          "2026-10-25T02": x - 3600, "2026-10-25T03": x + 2 * 3600,
                                                          "2026-10-25": x - 3 * 3600}),
                 ("Pacific/Chatham", (2026, 4, 5, 3), {"2026-04-05T02": self.CH_CHANGE_FALL - 105 * 60, "2026-04-05T03": self.CH_CHANGE_FALL - 45 * 60,
                                                       "2026-04-05T04": self.CH_CHANGE_FALL + 75 * 60}),
                 ("America/New_York", (2026, 11, 1, 1), {"2026-11-01T01": self.FIRST_0100, "2026-11-01T02": self.SECOND_0100 + 3600}),
                 ("Australia/Lord_Howe", (2026, 4, 5, 1), {"2026-04-05T01": calendar.timegm((2026, 4, 4, 14, 0, 0)),
                                                           "2026-04-05T02": calendar.timegm((2026, 4, 4, 15, 30, 0))}))
        for zone, reading, want in cases:
            os.environ["TZ"] = zone
            time.tzset()
            for isdst in (0, 1, 0, 1):
                time.mktime(reading + (0, 0, 0, 0, isdst))                   # the library's last resolution
                for key, first in want.items():
                    with self.subTest(zone=zone, key=key, isdst=isdst):
                        self.assertEqual(km._bucket_start(key), first)
        os.environ["TZ"] = "Antarctica/Troll"
        time.tzset()
        h0 = int((x + 3 * 3600) // 3600) - (km._SERIES_HOURS - 1)
        slots = set()
        for isdst in (0, 1, 0, 1):
            time.mktime((2026, 10, 25, 2, 0, 0, 0, 0, isdst))
            slots.add(km._series_index("2026-10-25T02", h0))
        self.assertEqual(slots, {int((x - 3600) // 3600) - h0}, "the hover slot of T02 is its daylight hour's, in every state")

    def test_a_two_hour_fall_back_interleaves_two_keys_and_the_window_reaches_both_buckets_first_instants(self):
        """1h at 01:30 standard (01:30Z): the walk is T01's standard run, then T02's daylight run — each key
        once, and T02's run IS its key's first — the shape the old fast path took for contiguous buckets, with
        t0 at 00:00Z. But the T01 bucket also holds the daylight hour [23:00Z, 00:00Z), and the ledger sums
        it whole: an hour of session dollars with no rows against it. The gate is a fall-back at a run
        boundary now (T01's standard run starts at the change), so the period reaches back to 23:00Z: five
        turns in the two buckets, five rows, five judge calls, and the rail's `1 hour` sums the same two."""
        os.environ["TZ"] = "Antarctica/Troll"
        time.tzset()
        x = self.TR_CHANGE
        now = x + 30 * 60
        self.assertEqual([(k, s) for k, s, _off0, _off1 in km._hour_buckets_back(now, 3600)], [("2026-10-25T01", x), ("2026-10-25T02", x - 3600)],
                         "the walk alone: T01's standard run, then T02's daylight run, which is T02's first")
        for isdst in (0, 1):
            time.mktime((2026, 10, 25, 2, 0, 0, 0, 0, isdst))
            with self.subTest(isdst=isdst):
                self.assertEqual(km._analytics_edges(now, 3600), ("hours", ["2026-10-25T01", "2026-10-25T02"], x - 2 * 3600))
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            "2026-10-25T00": {"usd": 50.0, "turns": 1}, "2026-10-25T01": {"usd": 2.0, "turns": 2},
            "2026-10-25T02": {"usd": 3.0, "turns": 3}}, "days": {}}))
        rows = [x - 2 * 3600 + 900, x - 3600 + 900, x - 3600 + 1800, x - 3600 + 2700, x + 900]   # 01:15 dl, 02:15 dl, 02:30 dl, 02:45 dl, 01:15 std
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text("".join(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(t), model="claude-opus-4-8") + "\n"
                              for t in rows + [x - 2 * 3600 - 900]))         # 00:45 daylight: out
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        (jd.STATE / "judge-usage.jsonl").write_text("".join(
            json.dumps({"t": t, "judge": "captioner", "tier": "index", "in": 10, "out": 4, "cost": 1.0, "ms": 5}) + "\n"
            for t in rows + [x - 2 * 3600 - 900]))
        a = km._token_analytics(now, 3600)
        self.assertEqual(a["from"], x - 2 * 3600)
        self.assertEqual((a["sessions"]["ledger"]["usd"], a["sessions"]["ledger"]["turns"]), (5.0, 5), "T01 (both runs) and T02 (its daylight run so far); T00 is out")
        self.assertEqual(a["sessions"]["in"], 5000, "one row per ledger turn — the daylight rows included")
        self.assertEqual(a["judges"]["total"]["calls"], 5)
        self.assertEqual(km._spend_windows(now=now)["hour"]["turns"], 5, "the rail's `1 hour` sums the same two buckets")

    def _closure_rule_holds(self, now, window):
        """The rule _hour_window states, as an oracle: t0 is the earliest first instant among the keys, the keys
        are exactly the buckets the recorder would write in [t0, now] (each once), t0 <= now - window, and the
        rail's prefix of one long walk gives the same answer as the standalone walk."""
        kind, keys, t0 = km._analytics_edges(now, window)
        self.assertEqual(kind, "hours")
        self.assertEqual(len(keys), len(set(keys)), "each key once: %r" % keys)
        self.assertLessEqual(t0, now - window)
        self.assertEqual(t0, min(km._bucket_start(k) for k in keys), "t0 is the earliest first instant among the keys")
        self.assertEqual(set(keys), self._recorder_keys(t0, now), "every key the recorder would write in [t0, now], no other")
        self.assertEqual(km._hour_window(now, window, km._hour_buckets_back(now, 7 * 86400), {}), (keys, t0), "the rail's prefix agrees")

    def test_every_window_across_the_two_hour_fall_back_holds_the_closure_rule(self):
        """Every quarter hour from two hours before the change to four after, for 1h, 5h and 24h, priming the
        library the other way before each: the closure rule holds, wherever the window's edges fall against
        the four interleaved runs. A week on, the 7d view holds it too."""
        os.environ["TZ"] = "Antarctica/Troll"
        time.tzset()
        x = self.TR_CHANGE
        isdst = 0
        for now in range(x - 2 * 3600, x + 4 * 3600 + 1, 900):
            for window in (3600, 5 * 3600, 86400):
                isdst ^= 1
                time.mktime((2026, 10, 25, 2, 0, 0, 0, 0, isdst))
                with self.subTest(now=time.strftime("%H:%M %Z", time.localtime(now)), window=window):
                    self._closure_rule_holds(now, window)
        self._closure_rule_holds(x + 7 * 86400 + 1800, 7 * 86400)
        # the same sweep in the zone this file's other split-key tests use, and in one with no split at all
        os.environ["TZ"] = "Pacific/Chatham"
        time.tzset()
        for now in range(self.CH_CHANGE_FALL - 3600, self.CH_CHANGE_FALL + 3 * 3600 + 1, 900):
            for window in (3600, 5 * 3600):
                with self.subTest(zone="Chatham", now=time.strftime("%H:%M %Z", time.localtime(now)), window=window):
                    self._closure_rule_holds(now, window)
        os.environ["TZ"] = "America/New_York"
        time.tzset()
        for now in range(self.FIRST_0100 - 3600, self.SECOND_0100 + 3 * 3600 + 1, 900):
            with self.subTest(zone="New York", now=time.strftime("%H:%M %Z", time.localtime(now))):
                self._closure_rule_holds(now, 3600)

    def test_a_date_the_zone_skipped_starts_the_period_where_the_gap_ends(self):
        """Samoa skipped 2011-12-30 (24:00 -10 on the 29th became 00:00 +14 on the 31st). No instant formats to
        that date, glibc has no daylight reading for it, and mktime(isdst=1) raises — through the one except
        that also wrapped _bucket_start's fallback, so the 30d view on 2012-01-29 handed _token_analytics t0
        None. The library's own normalized reading is no answer either: it follows the previous call, and
        named the start of Dec 29 in one state (a day of rows the ledger's keys do not cover). The bucket
        starts where the gap ends now, in every state, and the period's rows are cut there."""
        os.environ["TZ"] = "Pacific/Apia"
        time.tzset()
        change = calendar.timegm((2011, 12, 30, 10, 0, 0))                 # 00:00 +14 on Dec 31
        for isdst in (0, 1, 0):
            time.mktime((2011, 12, 28, 12, 0, 0, 0, 0, isdst))
            with self.subTest(isdst=isdst):
                self.assertEqual(km._bucket_start("2011-12-30"), change, "the skipped date starts where the gap ends")
                self.assertEqual(km._bucket_start("2011-12-30T12"), change, "an hour inside it too")
                self.assertEqual(km._bucket_start("2011-12-31"), change, "which is Dec 31's first instant")
        now = calendar.timegm((2012, 1, 28, 22, 0, 0))                     # noon +14 on Jan 29: the 30d view's oldest date is the skipped one
        self.assertEqual(km._analytics_edges(now, 30 * 86400)[1:], ([(datetime(2012, 1, 29).date() - timedelta(days=i)).isoformat() for i in range(31)], change))
        (jd.STATE / "spend.json").write_text(json.dumps({"days": {
            "2011-12-29": {"usd": 50.0, "turns": 1}, "2011-12-31": {"usd": 1.0, "turns": 1}, "2012-01-29": {"usd": 1.0, "turns": 1}}, "hours": {}}))
        rows = [change + 1800, now - 3600]                                  # 00:30 +14 Dec 31; 11:00 Jan 29
        p1 = pathlib.Path(self.td.name) / "s1.jsonl"
        p1.write_text("".join(_asst({"input_tokens": 1000, "output_tokens": 0}, iso(t), model="claude-opus-4-8") + "\n"
                              for t in rows + [change - 1800]))              # 23:30 -10 Dec 29: out
        jd.discover = lambda now, window=None, forks=True: [("fs1", p1, "a1", "s1")]
        a = km._token_analytics(now, 30 * 86400)
        self.assertEqual((a["from"], a["fromDate"], a["buckets"]), (change, "2011-12-30", "days"))
        self.assertEqual((a["sessions"]["ledger"]["usd"], a["sessions"]["ledger"]["turns"]), (2.0, 2))
        self.assertEqual(a["sessions"]["in"], 2000, "the Dec 29 row is out: the period starts where the gap ends, not a day before")
        os.environ["TZ"] = "Pacific/Kwajalein"
        time.tzset()
        self.assertEqual(km._bucket_start("1993-08-21"), calendar.timegm((1993, 8, 21, 12, 0, 0)),
                         "Kwajalein's skipped date, where the STANDARD arm is the one that raises")

    def test_a_ledger_whose_oldest_bucket_nothing_places_still_gives_the_period_its_sum(self):
        """spend.json's oldest hour key is a well-formed key no instant names (a Feb 31: a hand edit, never the
        recorder's), and it sorts inside the window, so _spend_ledger_window asks its first instant for the
        estimate's cut — and _bucket_start raises, by design. The window keeps its sum and names the key as
        `since`, drops `sinceT` (no cut, so no estimate for the part before the ledger), and the analytics
        build finishes; the error center gets one row naming the key and the file, and a second build adds
        none. Until this, the raise went through _token_analytics to the /analytics handler's catch-all."""
        now = calendar.timegm((2026, 3, 4, 12, 0, 0))                                  # 07:00 EST; the 7d window reaches back to Feb 25
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            "2026-02-31T05": {"usd": 9.0, "turns": 1}, "2026-03-03T10": {"usd": 2.0, "turns": 2}}, "days": {}}))
        jd.discover = lambda now, window=None, forks=True: []
        km._SDK_BOOT_PROBLEMS.clear()
        km._LEDGER_UNPLACED.clear()
        self.addCleanup(km._SDK_BOOT_PROBLEMS.clear)
        self.addCleanup(km._LEDGER_UNPLACED.clear)
        with self.assertRaises(ValueError):
            km._bucket_start("2026-02-31T05")                                          # the rule still raises for callers that want it
        led = km._spend_ledger_window(now, 7 * 86400)
        self.assertEqual((led["usd"], led["turns"], led["since"]), (2.0, 2, "2026-02-31T05"))
        self.assertNotIn("sinceT", led)
        rows = [r["text"] for r in km._sdk_problem_rows() if "2026-02-31T05" in r["text"]]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn(str(jd.STATE / "spend.json"), rows[0])
        self.assertIn("estimate", rows[0])
        a = km._token_analytics(now, 7 * 86400)
        self.assertEqual(a["sessions"]["ledger"]["usd"], 2.0)
        self.assertNotIn("estBefore", a["sessions"]["ledger"])
        km._ANALYTICS_MEMO.clear()
        km._token_analytics(now, 7 * 86400)
        self.assertEqual(len([r for r in km._sdk_problem_rows() if "2026-02-31T05" in r["text"]]), 1, "once per key, not once per build")

    def test_the_closure_computes_a_keys_first_instant_once_per_build_and_only_where_a_window_widens(self):
        """Cost, both ways. Where a window widens, the rail's five windows share one memo, so a key's first
        instant is computed once per build, only for the windows that widen, and only for the keys of the
        replay stretch — the ones the change can have split; a key whose run starts at or past the stretch's
        end is not asked (the fall-back week on Chatham once cost 510 calls for 170 keys, 2.2 ms per build;
        round 6 brought that to 168, one per key of the 7d window, on every build of the week after the
        change, none of which widened; round 7 to one per key of the window in the hours it widens, which for
        the 7d window a week after the change is 170 keys and 8-9 ms per rail build against 1.5). Where no
        split key reaches a window's start — a whole-hour fall-back sets the clock back inside a run (New
        York, London), a 30-minute one too (Lord Howe), a spring-forward splits nothing, a zone without DST
        changes nothing, and any zone once its replay is behind every window's start — the gate reads the
        offsets the walk carried and computes no first instant at all."""
        calls = []
        real = km._bucket_start
        km._bucket_start = lambda k: calls.append(k) or real(k)
        self.addCleanup(setattr, km, "_bucket_start", real)
        for zone, label, now, widened, asked in (("Pacific/Chatham", "the fall-back day, 04:15 standard", self.CH_CHANGE_FALL + 90 * 60,
                                                  {"2026-04-05T04", "2026-04-05T03", "2026-04-05T02"}, {"2026-04-05T03", "2026-04-05T02"}),
                                                 ("Antarctica/Troll", "the fall-back day, 01:30 standard", self.TR_CHANGE + 1800,
                                                  {"2026-10-25T01", "2026-10-25T02"}, {"2026-10-25T01", "2026-10-25T02"})):
            os.environ["TZ"] = zone
            time.tzset()
            self.assertEqual(set(km._hour_window(now, 3600)[0]), widened, "the 1h window widens to these keys")
            for build in (lambda: km._spend_windows(now=now), lambda: km._analytics_edges(now, 3600)):
                del calls[:]
                build()
                with self.subTest(zone=zone, label=label):
                    self.assertEqual(len(calls), len(set(calls)), "no key computed twice: %r" % calls)
                    self.assertEqual(set(calls), asked, "one call per key of the replay stretch, none for the others (Chatham's T04 starts where the stretch ends)")
            del calls[:]
            km._analytics_edges(now, 7 * 86400)
            self.assertEqual(calls, [], "%s: the 7d window's start is a week before the replay; nothing to widen, nothing computed" % zone)
        # a week on, the rail's 7d window and the modal's 7d edges have their start inside the stretch (for two,
        # five and three hours), and the series' 192-hour span a day after that: the closure asks the stretch's
        # keys, two or three, and none of the other 167-190 keys of the span
        for zone, x, stretch in (("Pacific/Chatham", self.CH_CHANGE_FALL, {"2026-04-05T02", "2026-04-05T03"}),
                                 ("Antarctica/Casey", calendar.timegm((2023, 3, 8, 16, 0, 0)), {"2023-03-09T00", "2023-03-09T01", "2023-03-09T02"}),
                                 ("Antarctica/Troll", self.TR_CHANGE, {"2026-10-25T01", "2026-10-25T02"})):
            os.environ["TZ"] = zone
            time.tzset()
            now = x + 7 * 86400 + 1800
            for build in (lambda: km._spend_windows(now=now), lambda: km._analytics_edges(now, 7 * 86400)):
                del calls[:]
                build()
                with self.subTest(zone=zone, label="7d, half an hour after its start entered the stretch"):
                    self.assertEqual(len(calls), len(set(calls)), "no key computed twice: %r" % calls)
                    self.assertEqual(set(calls), stretch)
            self.assertEqual(km._hour_window(now, 7 * 86400)[1], min(real(k) for k in stretch), "and t0 is the stretch's first instant")
            now = x + (km._SERIES_HOURS - 1) * 3600 + 1800        # the series' span begins at the change, inside the stretch
            (jd.STATE / "spend.json").write_text(json.dumps({"hours": {time.strftime("%Y-%m-%dT%H", time.localtime(now)): {"usd": 1.0}}, "days": {}}))
            del calls[:]
            km._spend_series(now=now)
            with self.subTest(zone=zone, label="the series' eighth day, its span's start inside the stretch"):
                self.assertEqual(set(calls), stretch)
        for zone, label, now, window in (("Pacific/Chatham", "7d three days after the fall-back", self.CH_CHANGE_FALL + 3 * 86400 + 90 * 60, 7 * 86400),
                                         ("Antarctica/Troll", "24h three days after the fall-back", self.TR_CHANGE + 3 * 86400 + 1800, 86400),
                                         ("America/New_York", "1h at 02:30 EST on the fall-back day", calendar.timegm((2026, 11, 1, 7, 30, 0)), 3600),
                                         ("America/New_York", "24h at 03:30 EST the day after", calendar.timegm((2026, 11, 2, 8, 30, 0)), 86400),
                                         ("America/New_York", "24h after the spring-forward", calendar.timegm((2026, 3, 8, 12, 0, 0)), 86400),
                                         ("Europe/London", "1h at 01:30 GMT on the fall-back day", calendar.timegm((2026, 10, 25, 1, 30, 0)), 3600),
                                         ("Australia/Lord_Howe", "1h at 01:45 standard on the fall-back day", calendar.timegm((2026, 4, 4, 15, 15, 0)), 3600),
                                         ("Australia/Lord_Howe", "24h across the 30-minute fall-back", calendar.timegm((2026, 4, 5, 1, 30, 0)), 86400),
                                         ("UTC", "24h", calendar.timegm((2026, 11, 1, 8, 30, 0)), 86400)):
            os.environ["TZ"] = zone
            time.tzset()
            del calls[:]
            km._analytics_edges(now, window)
            km._spend_windows(now=now)
            with self.subTest(zone=zone, label=label):
                self.assertEqual(calls, [], "the fast path: no first instant computed")

    def test_the_gate_fires_exactly_where_a_window_widens(self):
        """_splitting_fall_back is exact, not a bound: every quarter hour from two hours before a change to nine
        after, for 1h/5h/24h, it fires iff a key of the walked runs has a first instant before the oldest run's
        start. The truth is read from _bucket_start, key by key — never from _hour_window, which runs the
        closure only when the gate says so: read off that, `widened` was False by construction wherever the
        gate stayed quiet, the two sides agreed there whatever the gate had missed, and a gate with only its
        walked-boundary leg passed (until 2026-09-06). So New York, London and Lord Howe — a fall-back inside
        a run — never run the closure (round 6's t0 - 7200 leg ran it for the 45 minutes after their
        changes), and Chatham, Troll and Casey run it only while a window's start lies inside the replay.
        Where it fires it returns the stretch's end, and every key that reaches before t0 has its walked run
        start inside that end — the bound the closure asks no other key past."""
        for zone, x in (("Pacific/Chatham", self.CH_CHANGE_FALL), ("Antarctica/Troll", self.TR_CHANGE), ("Antarctica/Casey", calendar.timegm((2023, 3, 8, 16, 0, 0))),
                        ("America/New_York", self.SECOND_0100), ("Europe/London", calendar.timegm((2026, 10, 25, 1, 0, 0))), ("Australia/Lord_Howe", calendar.timegm((2026, 4, 4, 15, 0, 0)))):
            os.environ["TZ"] = zone
            time.tzset()
            fired_any = False
            for now in range(x - 2 * 3600, x + 9 * 3600 + 1, 900):
                walked = km._hour_buckets_back(now, 7 * 86400)
                for window in (3600, 5 * 3600, 86400):
                    runs = km._runs_through(walked, now - window)
                    t0 = runs[-1][1]
                    starts = {k: km._bucket_start(k) for k, _st, _off0, _off1 in runs}
                    widened = min(starts.values()) < t0
                    reach = km._splitting_fall_back(runs)
                    fired = reach is not None
                    fired_any = fired_any or fired
                    with self.subTest(zone=zone, now=time.strftime("%m-%d %H:%M %Z", time.localtime(now)), window=window):
                        self.assertEqual(fired, widened)
                        if fired:
                            self.assertGreater(reach, t0)
                            self.assertEqual([k for k, st, _off0, _off1 in runs if starts[k] < t0 and st >= reach], [],
                                             "a key that reaches before t0 starts inside the stretch the gate named")
            self.assertEqual(fired_any, zone in ("Pacific/Chatham", "Antarctica/Troll", "Antarctica/Casey"), zone)

    # ── the Antarctic stations: base-offset shifts between two STANDARD times, replaying up to seven hours ──
    # Casey 2023-03-08 16:00Z: +11 -> +08 (03:00 -> 00:00, three hours; eight such since 2010). Davis 2011-10-27
    # 19:00Z: +07 -> +05. Vostok 1994-01-31 17:00Z: +07 -> +00 (seven hours), and 2023-12-17 19:00Z: +07 -> +05.
    # Rothera 1976-12-01 00:00Z: +00 -> -03. Both offsets are standard time, so no isdst hint can pick between
    # the two readings of a replayed wall time: round 6's arms returned the same run twice and the answer
    # followed mktime's previous call, two to three hours and hover slots apart (the round-6 verification).
    @staticmethod
    def _first_instants_by_minute(lo, hi):
        """Brute-force truth: each hour key's first instant over a minute grid (every run starts on a whole minute)."""
        first = {}
        for t in range(lo, hi, 60):
            first.setdefault(time.strftime("%Y-%m-%dT%H", time.localtime(t)), t)
        return first

    def test_a_shift_between_two_standard_times_names_each_buckets_first_instant_in_every_library_state(self):
        """Every key around each change, under alternating primings (an unambiguous mktime on each side of the
        change, the state that moved round 6's answer), equals the brute-force first instant; the replayed
        keys' hover slots are one value each. Two hand-checked anchors: Casey's Mar 9 T00 starts at 00:00 +11
        (13:00Z Mar 8), three hours before its second run; Vostok's Jan 31 T17 at 17:00 +07 (10:00Z), seven
        hours before its second."""
        cases = (("Antarctica/Casey", calendar.timegm((2023, 3, 8, 16, 0, 0))), ("Antarctica/Davis", calendar.timegm((2011, 10, 27, 19, 0, 0))),
                 ("Antarctica/Vostok", calendar.timegm((1994, 1, 31, 17, 0, 0))), ("Antarctica/Vostok", calendar.timegm((2023, 12, 17, 19, 0, 0))),
                 ("Antarctica/Rothera", calendar.timegm((1976, 12, 1, 0, 0, 0))), ("Antarctica/Troll", self.TR_CHANGE), ("Pacific/Chatham", self.CH_CHANGE_FALL),
                 ("Australia/Lord_Howe", calendar.timegm((2026, 4, 4, 15, 0, 0))), ("America/New_York", self.SECOND_0100))
        for zone, x in cases:
            os.environ["TZ"] = zone
            time.tzset()
            a, b = time.localtime(x - 1).tm_gmtoff, time.localtime(x).tm_gmtoff
            self.assertGreater(a, b, "%s: a fall-back at %s" % (zone, x))
            first = self._first_instants_by_minute(x - 12 * 3600, x + 12 * 3600)
            after = {time.strftime("%Y-%m-%dT%H", time.localtime(t)) for t in range(x, x + (a - b) + 3600, 60)}
            replayed = sorted(k for k in first if first[k] < x and k in after)
            self.assertTrue(replayed, zone)
            h0 = int((x + 3 * 3600) // 3600) - (km._SERIES_HOURS - 1)
            slots = {k: set() for k in replayed}
            for i in range(4):
                time.mktime(time.localtime(x - 86400 + (i % 2) * 2 * 86400)[:6] + (0, 0, -1))   # prime: a reading on one side, then the other
                for k in sorted(k for k in first if first[k] >= x - 11 * 3600):
                    with self.subTest(zone=zone, key=k, priming=i % 2):
                        self.assertEqual(km._bucket_start(k), first[k])
                for k in replayed:
                    slots[k].add(km._series_index(k, h0))
            for k in replayed:
                self.assertEqual(slots[k], {int(first[k] // 3600) - h0}, "%s %s: one hover slot in every state" % (zone, k))
        os.environ["TZ"] = "Antarctica/Casey"
        time.tzset()
        self.assertEqual(km._bucket_start("2023-03-09T00"), calendar.timegm((2023, 3, 8, 13, 0, 0)))
        self.assertEqual(km._bucket_start("2023-03-09"), calendar.timegm((2023, 3, 8, 13, 0, 0)), "the date starts at its first midnight too")
        os.environ["TZ"] = "Antarctica/Vostok"
        time.tzset()
        self.assertEqual(km._bucket_start("1994-01-31T17"), calendar.timegm((1994, 1, 31, 10, 0, 0)))
        self.assertEqual(km._bucket_start("1994-02-01T00"), calendar.timegm((1994, 2, 1, 0, 0, 0)), "Feb 1 T00 exists once: at +07 its 00:00 was the change itself")

    def test_a_three_hour_replay_widens_the_window_to_the_buckets_first_run(self):
        """Casey, 1h at 01:30 +08 on 2023-03-09 (17:30Z Mar 8): the walk is T01's second run then T00's second
        run (16:00Z), but both buckets also hold their +11 hours (T00 from 13:00Z), so the period reaches
        back to 13:00Z — four and a half hours for a `1h` view — and takes in T02, whose +11 hour lies
        between T00's two runs. The closure rule holds at every quarter hour across the change. Round 6 cut
        t0 at 16:00Z or 15:00Z by the library's state."""
        os.environ["TZ"] = "Antarctica/Casey"
        time.tzset()
        x = calendar.timegm((2023, 3, 8, 16, 0, 0))
        now = x + 90 * 60
        self.assertEqual([(k, s) for k, s, _off0, _off1 in km._hour_buckets_back(now, 3600)], [("2023-03-09T01", x + 3600), ("2023-03-09T00", x)])
        for i in range(2):
            time.mktime(time.localtime(x - 86400 + i * 2 * 86400)[:6] + (0, 0, -1))
            with self.subTest(priming=i):
                self.assertEqual(km._analytics_edges(now, 3600), ("hours", ["2023-03-09T01", "2023-03-09T00", "2023-03-09T02"], x - 3 * 3600))
        for now in range(x - 2 * 3600, x + 5 * 3600 + 1, 900):
            for window in (3600, 5 * 3600, 86400):
                with self.subTest(now=time.strftime("%H:%M %Z", time.localtime(now)), window=window):
                    self._closure_rule_holds(now, window)

    def test_the_hover_series_places_every_key_by_the_rule_from_one_walk(self):
        """_spend_series takes the slots of the keys in its span from one walk (_first_instants) — the rule
        (_series_index) key by key is a _bucket_start each, 30-55 µs, 192 times on every usage build —
        and the two agree key for key: across the Chatham, Troll and Casey replays (split keys, where the walk
        alone would place a key by its LATER run unless the gate sends it to the rule), on the New York
        fall-back day, and for a ledger whose keys predate the span or sort after now. In a zone with no
        change in the span the walk decides every key of the span and the rule is asked only for the one
        past now."""
        calls = []
        real = km._bucket_start
        km._bucket_start = lambda k: calls.append(k) or real(k)
        self.addCleanup(setattr, km, "_bucket_start", real)
        for zone, now in (("Pacific/Chatham", self.CH_CHANGE_FALL + 90 * 60), ("Pacific/Chatham", self.CH_CHANGE_FALL + 3 * 86400),
                          ("Antarctica/Troll", self.TR_CHANGE + 1800), ("Antarctica/Troll", self.TR_CHANGE + 7 * 86400 + 1800),
                          ("Antarctica/Casey", calendar.timegm((2023, 3, 8, 18, 0, 0))), ("America/New_York", self.SECOND_0100 + 1800),
                          ("UTC", self.SECOND_0100)):
            os.environ["TZ"] = zone
            time.tzset()
            h0 = int(now // 3600) - (km._SERIES_HOURS - 1)
            keys = sorted({time.strftime("%Y-%m-%dT%H", time.localtime(t)) for t in range(now - 200 * 3600, now + 1, 900)})   # every bucket of 200 hours: some before the span
            future = time.strftime("%Y-%m-%dT%H", time.localtime(now + 3600))
            ledger = {k: {"usd": 1.0 + i * 0.01, "turns": 1} for i, k in enumerate(keys + [future])}
            (jd.STATE / "spend.json").write_text(json.dumps({"hours": ledger, "days": {}}))
            want = [0.0] * km._SERIES_HOURS
            for k, e in ledger.items():
                i = km._series_index(k, h0)
                if i is not None and 0 <= i < km._SERIES_HOURS:
                    want[i] = round(want[i] + e["usd"], 4)
            del calls[:]
            with self.subTest(zone=zone, now=time.strftime("%m-%d %H:%M %Z", time.localtime(now))):
                self.assertEqual(km._spend_series(now=now), {"h0": h0, "usd": want})
                if zone == "UTC":
                    self.assertEqual(calls, [future], "the walk placed every key of the span and every key before it; the rule ran for the key past now only")


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
