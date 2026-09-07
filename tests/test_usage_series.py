#!/usr/bin/env python3
"""The usage hover's time series (the user 2026-08-13): window utilization gets a recorded past
(usage-history.json, appended by both usage writers, hourly max-pct with roll-aware overwrites, 192h
bound), spend.json's hour buckets ship as a dense $/hour series, and a pure API-key host — which never
gets a usage.json at all — finally reaches the no-login spend arm instead of reporting {} (the devbox,
whose spend was missing from the fleet sum). SYNTHETIC fixtures only.

Clock discipline: every writer/reader takes an injectable `now`, and these tests FREEZE it (FIXED) —
an import-time "current hour" diverges from a call-time stamp whenever the suite straddles an hour
boundary, which is exactly how the 23:00 UTC CI run failed while local runs passed. Where a path still
reads the real clock (_usage), assertions derive the index from the payload's own h0, never from an
assumed position."""
import json
import os
import pathlib
import tempfile
import time
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_useries", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdkb_useries", os.path.join(BIN, "romp_sdk_backend.py"))
jd = km.jd

FIXED = 1765000000.0                 # frozen mid-hour instant; every key below derives from it


def _h(n=0):
    """Hour key n hours before FIXED, in the stores' own format."""
    return time.strftime("%Y-%m-%dT%H", time.localtime(FIXED - n * 3600))


class UsageHistoryLedger(unittest.TestCase):
    """_record_usage_history: hourly max-pct per window, roll-aware, bounded, atomic."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.b = object.__new__(sb.SdkBackend)
        self.b.state_dir = pathlib.Path(self.td.name)
        self.b._log = lambda *a, **k: None

    def tearDown(self):
        self.td.cleanup()

    def _read(self):
        return json.loads((pathlib.Path(self.td.name) / "usage-history.json").read_text())

    def test_max_pct_per_hour_and_roll_takes_the_fresh_reading(self):
        self.b._record_usage_history({"acct": "a1", "five_hour": {"pct": 30, "resets_at": 100}}, now=FIXED)
        self.b._record_usage_history({"acct": "a1", "five_hour": {"pct": 20, "resets_at": 100}}, now=FIXED)
        ent = self._read()["hours"][_h()]
        self.assertEqual(ent["five_hour"], {"pct": 30, "ra": 100},
                         "within one window the hour keeps its MAX (usage only climbs)")
        self.b._record_usage_history({"acct": "a1", "five_hour": {"pct": 5, "resets_at": 200}}, now=FIXED)
        ent = self._read()["hours"][_h()]
        self.assertEqual(ent["five_hour"], {"pct": 5, "ra": 200},
                         "a ROLL (new resets_at) takes the fresh reading outright")

    def test_windows_accumulate_independently_and_prune_bounds_the_file(self):
        self.b._record_usage_history({"acct": "a1", "seven_day": {"pct": 11, "resets_at": 7},
                                      "fable": {"pct": 3, "resets_at": 9}}, now=FIXED)
        ent = self._read()["hours"][_h()]
        self.assertEqual(ent["seven_day"]["pct"], 11)
        self.assertEqual(ent["fable"]["pct"], 3)
        self.assertNotIn("five_hour", ent, "a window the reading lacks stays absent — never a made-up 0")
        hours = {_h(i): {"acct": "a1", "five_hour": {"pct": 1, "ra": 1}} for i in range(1, 250)}
        (pathlib.Path(self.td.name) / "usage-history.json").write_text(json.dumps({"hours": hours}))
        self.b._record_usage_history({"acct": "a1", "five_hour": {"pct": 50, "resets_at": 1}}, now=FIXED)
        self.assertLessEqual(len(self._read()["hours"]), 192, "8 days of hours, never unbounded")


class SeriesPayloads(unittest.TestCase):
    """_spend_series: dense arrays + base hour; honest gaps. (The winSeries assembler that lived
    beside it is gone — the user 2026-08-14 wanted only the fleet $/h graph; rail-spend.test.ts
    pins the removal. usage-history.json keeps recording — sdk_backend _record_usage_history.)"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = (jd.STATE, km._claude_account)
        jd.STATE = pathlib.Path(self.td.name)
        km._claude_account = lambda: "me"    # pinned: the foreign-skip below must not float on the
        # machine's real login (CI has none, which turns the skip inert)

    def tearDown(self):
        jd.STATE, km._claude_account = self.saved
        self.td.cleanup()

    def test_spend_series_places_hours_and_splits_keyed(self):
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            _h(): {"usd": 2.5, "key": {"usd": 2.0, "turns": 1, "tok": 5}},
            _h(3): {"usd": 1.0},
        }, "days": {}}))
        ss = km._spend_series(now=FIXED)
        self.assertEqual(len(ss["usd"]), 192)
        self.assertEqual(ss["usd"][-1], 2.5)
        self.assertEqual(ss["usd"][-4], 1.0)
        self.assertEqual(ss["usd"][-2], 0.0, "an hour with no turns genuinely spent $0 — money has a true zero")
        self.assertEqual(km._spend_series(keyed_only=True, now=FIXED)["usd"][-1], 2.0)
        self.assertEqual(km._spend_series(keyed_only=True, now=FIXED)["usd"][-4], 0.0,
                         "an hour with no key sub-counter contributes nothing to the keyed series")

    def test_empty_stores_return_none(self):
        self.assertIsNone(km._spend_series(now=FIXED))

    def test_a_bucket_the_rule_cannot_place_is_left_out_and_reported_once(self):
        """A well-formed hour key no instant names in any zone (a Feb 31) — never the recorder's, so a hand
        edit or a file gone bad. _bucket_start raises for it by design (the fail-loudly rule); the strptime
        rule before it skipped such a key silently, and for a few hours on 2026-09-06 _spend_series let the
        raise through: every usage build runs the series, every timeline push runs a usage build, so the push
        tick logged 'push build:' and sent nothing, to every client, on every tick, for as long as the key
        stayed in the file. The series leaves the bucket out
        and says so once, in the error center, naming the key and the file; the other buckets land where
        they did, and the rule still raises for a caller that asks it directly."""
        (jd.STATE / "spend.json").write_text(json.dumps({"hours": {
            _h(): {"usd": 2.5}, _h(3): {"usd": 1.0}, "2099-02-31T05": {"usd": 7.0}}, "days": {}}))
        km._SDK_BOOT_PROBLEMS.clear()
        km._LEDGER_UNPLACED.clear()
        self.addCleanup(km._SDK_BOOT_PROBLEMS.clear)
        self.addCleanup(km._LEDGER_UNPLACED.clear)
        with self.assertRaises(ValueError):
            km._series_index("2099-02-31T05", 0)
        ss = km._spend_series(now=FIXED)
        self.assertEqual((ss["usd"][-1], ss["usd"][-4], round(sum(ss["usd"]), 4)), (2.5, 1.0, 3.5),
                         "the buckets the rule places land in their slots; the one it cannot is nowhere")
        rows = [r["text"] for r in km._sdk_problem_rows() if "2099-02-31T05" in r["text"]]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn(str(jd.STATE / "spend.json"), rows[0])
        self.assertIn("hover graph", rows[0])
        km._spend_series(now=FIXED)
        km._spend_series(keyed_only=True, now=FIXED)
        self.assertEqual(len([r for r in km._sdk_problem_rows() if "2099-02-31T05" in r["text"]]), 1,
                         "once per key, not once per build")


class ApiKeyHostReportsSpend(unittest.TestCase):
    """The devbox fix: no usage.json at all + spend.json present + no login → the no-login spend arm
    answers (spend + spendSeries), never {} (kernel _usage used to bail on the missing file)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = (jd.STATE, km._claude_account)
        jd.STATE = pathlib.Path(self.td.name)
        km._claude_account = lambda: ""      # the devbox shape: NO login — never the dev machine's real one

    def tearDown(self):
        jd.STATE, km._claude_account = self.saved
        self.td.cleanup()

    def test_missing_usage_json_still_reports_key_spend(self):
        # _usage() runs on the REAL clock, so the fixture stamps the real current hour and the
        # assertion asks the payload's own h0 where that hour landed — position-independent.
        hour_key = time.strftime("%Y-%m-%dT%H")
        (jd.STATE / "spend.json").write_text(json.dumps({
            "hours": {hour_key: {"usd": 3.0, "turns": 2, "tok": 10}},
            "days": {time.strftime("%Y-%m-%d"): {"usd": 3.0, "turns": 2, "tok": 10}}}))
        u = km._usage()
        self.assertIsNotNone(u, "a keyed host with recorded spend must never answer {}")
        self.assertTrue(u.get("apiKey"))
        self.assertEqual(u["spend"]["day"]["usd"], 3.0)
        i = km._series_index(hour_key, u["spendSeries"]["h0"])
        self.assertEqual(u["spendSeries"]["usd"][i], 3.0, "…and ships the $/hour series for the hover graph")

    def test_nothing_recorded_still_answers_none(self):
        self.assertIsNone(km._usage(), "a fresh box with neither login nor spend has nothing to show")

    def test_a_bucket_the_rule_cannot_place_does_not_stop_the_usage_build(self):
        # the push path: _usage() -> _spend_series(); a raise here reached the push tick's catch and the
        # timeline stopped for every client (2026-09-06). The build finishes with the bucket left out.
        hour_key = time.strftime("%Y-%m-%dT%H")
        (jd.STATE / "spend.json").write_text(json.dumps({
            "hours": {hour_key: {"usd": 3.0, "turns": 2, "tok": 10}, "2099-02-31T05": {"usd": 7.0, "turns": 1}},
            "days": {time.strftime("%Y-%m-%d"): {"usd": 3.0, "turns": 2, "tok": 10}}}))
        km._LEDGER_UNPLACED.clear()
        self.addCleanup(km._LEDGER_UNPLACED.clear)
        self.addCleanup(km._SDK_BOOT_PROBLEMS.clear)
        u = km._usage()
        self.assertTrue(u.get("apiKey"))
        self.assertEqual(u["spend"]["day"]["usd"], 3.0, "the windows never summed the unplaceable key: it is no walked bucket")
        i = km._series_index(hour_key, u["spendSeries"]["h0"])
        self.assertEqual((u["spendSeries"]["usd"][i], round(sum(u["spendSeries"]["usd"]), 4)), (3.0, 3.0))

    def test_spend_carries_its_own_freshness_stamp(self):
        # the user 2026-08-24: the windows' "updated 9h 38m ago" (usage.json's t — which nothing
        # writes under key auth) sat directly above the spend section and read as the spend's age.
        # The payload now stamps the spend's OWN last-record moment: spend.json's mtime, an event
        # time (the recorder writes per turn result), so the hover can say when the last charge
        # actually landed — and a frozen number visibly ages instead of hiding behind the windows.
        hour_key = time.strftime("%Y-%m-%dT%H")
        p = jd.STATE / "spend.json"
        p.write_text(json.dumps({"hours": {hour_key: {"usd": 1.0, "turns": 1, "tok": 5}},
                                 "days": {time.strftime("%Y-%m-%d"): {"usd": 1.0, "turns": 1, "tok": 5}}}))
        os.utime(p, (1000000000, 1000000000))
        u = km._usage()
        self.assertEqual(u.get("spendAt"), 1000000000, "the stamp is the record file's own mtime")

    def test_view_and_tag_state_never_filters_the_spend_aggregation(self):
        # the user 2026-08-24 asked whether hidden/tagged sessions count toward the spend. They MUST:
        # the series is machine-level API-key billing, recorded per turn result before any view
        # exists, and read straight from spend.json's buckets. This pins that a views blob hiding
        # and tagging everything changes NOTHING about the sums — if a view/tag filter ever leaks
        # into the aggregation, this breaks.
        hour_key = time.strftime("%Y-%m-%dT%H")
        (jd.STATE / "spend.json").write_text(json.dumps({
            "hours": {hour_key: {"usd": 7.5, "turns": 3, "tok": 30}},
            "days": {time.strftime("%Y-%m-%d"): {"usd": 7.5, "turns": 3, "tok": 30}}}))
        before = km._usage()
        (jd.STATE / "timeline-views.json").write_text(json.dumps({
            "active": "g1", "hidden": ["11111111-2222-3333-4444-555555555555"],
            "tags": [{"id": "g1", "name": "workers", "color": "#DD42FF",
                      "members": ["22222222-3333-4444-5555-666666666666"]}]}))
        km._flags_cache.clear()
        after = km._usage()
        self.assertEqual(after["spend"], before["spend"],
                         "hiding/tagging sessions must never change the billed sums")
        self.assertEqual(after["spendSeries"], before["spendSeries"],
                         "…or the $/h series behind the graph")


class RemoteUsageStaleness(unittest.TestCase):
    def test_an_answered_empty_payload_clears_instead_of_freezing(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('r.pop("usage", None)', src,
                      "a host that ANSWERS with nothing to show clears its row — only an unanswered "
                      "poll (blip/rate-gate) keeps the last good reading")


if __name__ == "__main__":
    unittest.main()
