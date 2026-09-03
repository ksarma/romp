#!/usr/bin/env python3
"""T235 (the user's spend hover, 2026-09-03): the "1 month" row read LOWER than "1 week" — because
hour/day/week were ROLLING sums while month was CALENDAR month-to-date, three days into September.
A label beside "1 hour / 1 day / 1 week" promises a rolling window, and a superset window can never
read lower. Now `month` is a rolling 30 local days over the days ledger, and the bill-tracking figure
lives under its own honest key, `monthToDate`, which carries the month budget. A ledger younger than
30 days marks the rolling window with its `since` date rather than reading as a silently short window.
Frozen clock, synthetic ledger, local-time bucket keys built the recorder's own way."""
import json
import os
import tempfile
import time
import types
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = SourceFileLoader("romp_kernel_spendwin", os.path.join(BIN, "romp-kernel")).load_module()

# the 3rd of a month, midday local — the exact shape of the user's screenshot
FROZEN = time.mktime((2026, 9, 3, 12, 0, 0, 0, 0, -1))


def _day(n):
    return time.strftime("%Y-%m-%d", time.localtime(FROZEN - n * 86400))


def _hour(n):
    return time.strftime("%Y-%m-%dT%H", time.localtime(FROZEN - n * 3600))


class SpendWindows(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._saved = (km.jd.STATE, km.time)
        km.jd.STATE = Path(self.td.name)
        # freeze the module's clock: time() answers FROZEN; every formatter stays the real one, fed
        # explicit struct_times by the implementation (a bare strftime() would read the wall clock)
        frozen = types.SimpleNamespace(time=lambda: FROZEN, strftime=time.strftime, localtime=time.localtime,
                                       gmtime=time.gmtime, mktime=time.mktime, sleep=time.sleep,
                                       monotonic=time.monotonic, time_ns=time.time_ns)
        km.time = frozen

    def tearDown(self):
        km.jd.STATE, km.time = self._saved
        self.td.cleanup()

    def _ledger(self, days=None, hours=None, budgets=None):
        (km.jd.STATE / "spend.json").write_text(json.dumps({"days": days or {}, "hours": hours or {}}))
        if budgets is not None:
            (km.jd.STATE / "spend-budgets.json").write_text(json.dumps(budgets))

    def _bucket(self, usd, turns=1, tok=10):
        return {"usd": usd, "turns": turns, "tokIn": tok}

    def test_windows_are_monotone_hour_day_week_month(self):
        # 40 days of $24/day (one $1 turn per hour for the last 7 days mirrors the days ledger)
        days = {_day(n): self._bucket(24.0, turns=24, tok=240) for n in range(40)}
        hours = {_hour(n): self._bucket(1.0) for n in range(7 * 24 + 1)}
        self._ledger(days, hours)
        w = km._spend_windows()
        for metric in ("usd", "tok", "turns"):
            chain = [w[k][metric] for k in ("hour", "day", "week", "month")]
            self.assertEqual(chain, sorted(chain), "%s: hour ≤ day ≤ week ≤ month — the invariant the screenshot broke: %r" % (metric, chain))
        self.assertGreater(w["month"]["usd"], w["week"]["usd"], "a rolling month is a strict superset of a week here")

    def test_month_to_date_is_the_calendar_sum_and_carries_the_budget(self):
        days = {_day(n): self._bucket(10.0) for n in range(40)}   # Sep 1,2,3 = 3 buckets in the calendar month
        self._ledger(days, {}, budgets={"month": 150})
        w = km._spend_windows()
        self.assertEqual(w["monthToDate"]["usd"], 30.0, "Sep 1–3 only — what the bill accrues")
        self.assertEqual(w["monthToDate"]["budget"], 150.0, "the bill-cycle budget rides the bill figure")
        self.assertNotIn("budget", w["month"], "…never the rolling window — a cycle cap is not a 30-day cap")

    def test_rolling_month_spans_exactly_the_last_30_local_days_across_a_boundary(self):
        days = {_day(30): self._bucket(100.0), _day(29): self._bucket(1.0), _day(0): self._bucket(1.0),
                _day(31): self._bucket(1000.0)}
        self._ledger(days, {})
        w = km._spend_windows()
        self.assertEqual(w["month"]["usd"], 102.0, "today back through 30 days ago inclusive (31 local dates) — 31 days ago is out")

    def test_a_ledger_younger_than_30_days_marks_its_since_date(self):
        days = {_day(n): self._bucket(1.0) for n in range(5)}
        self._ledger(days, {})
        w = km._spend_windows()
        self.assertEqual(w["month"]["since"], _day(4), "a short ledger says how far back it truly reaches")
        self._ledger({_day(n): self._bucket(1.0) for n in range(35)}, {})
        self.assertNotIn("since", km._spend_windows()["month"], "a full window carries no caveat")

    def test_empty_ledger_stays_honest_zero_everywhere(self):
        self._ledger({}, {})
        w = km._spend_windows()
        self.assertEqual(w["month"], {"usd": 0.0, "tok": 0, "turns": 0})
        self.assertEqual(w["monthToDate"], {"usd": 0.0, "tok": 0, "turns": 0})


if __name__ == "__main__":
    unittest.main()
