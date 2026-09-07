#!/usr/bin/env python3
"""The usage reading, split (perf round 4 P18, 2026-09-07). Three callers act on the rate-limit half of
_usage() alone: _account_limited (both edges of the limit pause), _retry_resume_at (the API-error card's
countdown) and _limit_hold (the queue's account gate) read `limited` and the windows' resetsAt, which
derive from usage.json's segments, the acct stamp and the clock. spend.json is not an input of theirs,
yet every call parsed the ledger twice (once in _spend_windows, once in _spend_series) — on a host in the
spend arm, for a key that arm never produces. _usage_limits() is that half on its own; _usage() builds on
it and parses the ledger ONCE per call, handing the document to both spend readers as `doc`. There is no
memo: every call reads the files as they are at that moment, and the clock every derived value reads is
the module's (`km.time`), the one the frozen-clock tests govern. Synthetic fixtures only."""
import inspect
import json
import os
import re
import tempfile
import time
import types
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_usplit", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"     # no goals are minted here: the shared placeholder is fine
ACCT = "aaaaaaaaaaaa"
LIMIT_FIELDS = ("limited", "fiveHour", "sevenDay", "fable", "t", "acct")


def _frozen_clock(at):
    """A `time` stand-in whose time() answers `at`; every formatter stays the real one, fed explicit
    struct_times by the implementation (the frozen-clock idiom of tests/test_spend_windows.py)."""
    return types.SimpleNamespace(time=lambda: at, strftime=time.strftime, localtime=time.localtime,
                                 gmtime=time.gmtime, mktime=time.mktime, strptime=time.strptime,
                                 sleep=time.sleep, monotonic=time.monotonic, time_ns=time.time_ns)


class _Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._saved = (jd.STATE, km._claude_account, km._claude_account_label, km._auth_key_present, km.time,
                       km._path_of, km._launch_error, km.Path.read_text)
        jd.STATE = Path(self.td.name)
        km._claude_account_label = lambda: "login@example.test"
        km._path_of = lambda sid, now=None: None       # no transcript: the hold's spend arm reads only the pause flag
        km._launch_error = lambda sid: None            # no backend: the CLI-refused arm is another module's axis
        self.reads = {}
        orig = self._saved[-1]

        def spy(p, *a, **kw):
            self.reads[p.name] = self.reads.get(p.name, 0) + 1
            return orig(p, *a, **kw)
        km.Path.read_text = spy

    def tearDown(self):
        (jd.STATE, km._claude_account, km._claude_account_label, km._auth_key_present, km.time,
         km._path_of, km._launch_error, km.Path.read_text) = self._saved
        self.td.cleanup()

    # ── fixtures ──
    def _windows(self, five=10, seven=10, fable=None, acct=ACCT, t=1785898746, five_reset=None, seven_reset=None):
        fut = int(km.time.time()) + 3600
        o = {"t": t,
             "five_hour": {"pct": five, "resets_at": fut if five_reset is None else five_reset},
             "seven_day": {"pct": seven, "resets_at": fut if seven_reset is None else seven_reset}}
        if fable is not None:
            o["fable"] = {"pct": fable, "resets_at": fut}
        if acct is not None:
            o["acct"] = acct
        (jd.STATE / "usage.json").write_text(json.dumps(o))

    def _ledger(self, keyed=True):
        """A spend ledger with a turn in the current hour (the module clock's) and one three hours back;
        the current-hour bucket carries the keyed split when `keyed`, so the windows arm attaches spend."""
        now = km.time.time()
        h = lambda n: time.strftime("%Y-%m-%dT%H", time.localtime(now - n * 3600))
        day = time.strftime("%Y-%m-%d", time.localtime(now))
        cur = {"usd": 2.5, "turns": 2, "tokIn": 10, "tokOut": 5}
        if keyed:
            cur["key"] = {"usd": 2.0, "turns": 1, "tok": 15}
        (jd.STATE / "spend.json").write_text(json.dumps({
            "hours": {h(0): cur, h(3): {"usd": 1.0, "turns": 1, "tokIn": 4}},
            "days": {day: {"usd": 3.5, "turns": 3, "tokIn": 14, "tokOut": 5}}}))

    def _spend_reads(self):
        return self.reads.get("spend.json", 0)

    def _windows_arm(self, **kw):
        km._claude_account = lambda: ACCT              # the login that produced the windows is signed in
        km._auth_key_present = lambda: True            # ...beside a key, so the keyed spend attaches
        self._windows(**kw)
        self._ledger(keyed=True)

    def _spend_arm(self, marker=False):
        km._claude_account = lambda: ""                # no login: the pure API-key host
        km._auth_key_present = lambda: True
        if marker:                                     # the legacy apiKey marker file, with its own stamp
            (jd.STATE / "usage.json").write_text(json.dumps({"apiKey": True, "t": 1785898746}))
        self._ledger(keyed=False)


class LimitsReadingMatchesTheFullReading(_Base):
    """_usage_limits() is exactly _usage()'s rate-limit half, in both arms."""

    def test_windows_arm_beside_a_key(self):
        self._windows_arm(five=100, seven=40, fable=20)
        u, lim = km._usage(), km._usage_limits()
        self.assertEqual(u["limited"], {"fiveHour": True, "sevenDay": False, "fable": False})
        for k in LIMIT_FIELDS + ("acctLabel",):
            self.assertEqual(lim.get(k), u.get(k), "%s: the limits reading is the full reading's" % k)
        self.assertIn("spend", u, "the full reading attaches the keyed spend beside the bars")
        self.assertNotIn("spend", lim, "the limits reading carries nothing from the ledger")
        self.assertNotIn("spendSeries", lim)

    def test_windows_arm_with_no_window_at_its_cap(self):
        self._windows_arm(five=90, seven=99)
        u, lim = km._usage(), km._usage_limits()
        self.assertIsNone(u["limited"])
        for k in LIMIT_FIELDS:
            self.assertEqual(lim.get(k), u.get(k), k)

    def test_spend_arm_with_no_usage_file(self):
        self._spend_arm()
        u, lim = km._usage(), km._usage_limits()
        self.assertTrue(u.get("apiKey"), "the fixture is the pure API-key host's shape")
        for k in LIMIT_FIELDS:
            self.assertEqual(lim.get(k), u.get(k), k)
        self.assertIsNone(lim.get("limited"))

    def test_spend_arm_on_the_legacy_marker_file(self):
        self._spend_arm(marker=True)
        u, lim = km._usage(), km._usage_limits()
        self.assertTrue(u.get("apiKey"))
        self.assertEqual(u["t"], 1785898746, "the marker file's own stamp rides the spend payload")
        for k in LIMIT_FIELDS:
            self.assertEqual(lim.get(k), u.get(k), k)

    def test_a_stamp_from_a_login_that_is_gone_drops_the_windows_in_both(self):
        self._windows(five=100, seven=100, acct="bbbbbbbbbbbb")
        km._claude_account = lambda: ACCT
        km._auth_key_present = lambda: False
        self.assertIsNone(km._usage(), "another login's fossil draws nothing (test_usage_acct_flip)")
        lim = km._usage_limits()
        self.assertIsNone(lim["limited"], "...and limits nothing: the stamp check is part of the limits half")
        self.assertIsNone(lim["fiveHour"])
        self.assertEqual(km._account_limited(), [])


class NoLedgerParseForThePauseAndHoldCallers(_Base):
    """The three callers read usage.json once per call and spend.json never."""

    def test_in_the_spend_arm(self):
        self._spend_arm()
        km._set_retry_paused(True)                     # so _retry_resume_at reads the report
        self.reads.clear()
        self.assertEqual(km._account_limited(), [])
        self.assertIsNone(km._retry_resume_at())
        self.assertIsNone(km._limit_hold(SID))
        self.assertEqual(self._spend_reads(), 0, "no caller of the limits half parses the ledger: %r" % self.reads)
        self.assertEqual(self.reads.get("usage.json", 0), 3, "each call reads the report once, as it is now")

    def test_in_the_windows_arm_beside_a_key(self):
        fut = int(time.time()) + 1800
        self._windows_arm(five=100, seven=20, five_reset=fut)
        km._set_retry_paused(True, reason="limit")
        self.reads.clear()
        self.assertEqual(km._account_limited(), ["fiveHour"])
        self.assertEqual(km._retry_resume_at(), fut)
        self.assertEqual(km._limit_hold(SID)["resetsAt"], fut)
        self.assertEqual(self._spend_reads(), 0, "the keyed spend is not an input of any of these: %r" % self.reads)

    def test_the_pause_tick_parses_no_ledger(self):
        self._spend_arm()
        self.reads.clear()
        km._auto_pause_on_limit()
        self.assertFalse(km._retry_paused_on())
        self.assertEqual(self._spend_reads(), 0)
        self.assertEqual(self.reads.get("usage.json", 0), 1)

    def test_the_callers_read_the_limits_half_by_name(self):
        for fn in (km._account_limited, km._retry_resume_at, km._limit_hold):
            body = inspect.getsource(fn).split('"""', 2)[2]      # the code after the docstring, which may name _usage() in prose
            self.assertIn("_usage_limits()", body, fn.__name__)
            self.assertNotRegex(body, r"(?<![_a-zA-Z])_usage\(\)", "%s must not take the full reading" % fn.__name__)


class OneLedgerParsePerFullReading(_Base):
    """_usage() parses spend.json once per call (it was twice), and the next call parses it again."""

    def test_spend_arm(self):
        self._spend_arm()
        self.reads.clear()
        u = km._usage()
        self.assertIn("spendSeries", u, "both spend readers ran")
        self.assertEqual(u["spend"]["hour"]["usd"], 2.5)
        self.assertEqual(self._spend_reads(), 1, "one parse feeds both the windows and the series: %r" % self.reads)
        km._usage()
        self.assertEqual(self._spend_reads(), 2, "no memo: the next call reads the ledger as it is then")

    def test_windows_arm_with_keyed_turns(self):
        self._windows_arm(five=30, seven=30)
        self.reads.clear()
        u = km._usage()
        self.assertEqual(u["spend"]["hour"]["usd"], 2.0, "the keyed split")
        self.assertIn("spendSeries", u)
        self.assertEqual(self._spend_reads(), 1, "%r" % self.reads)

    def test_windows_arm_with_a_key_but_no_keyed_turns_still_reads_once(self):
        km._claude_account = lambda: ACCT
        km._auth_key_present = lambda: True
        self._windows(five=30, seven=30)
        self._ledger(keyed=False)
        self.reads.clear()
        u = km._usage()
        self.assertNotIn("spend", u, "a key with no recorded turns attaches nothing")
        self.assertEqual(self._spend_reads(), 1)

    def test_windows_arm_with_no_key_never_reads_the_ledger(self):
        km._claude_account = lambda: ACCT
        km._auth_key_present = lambda: False
        self._windows(five=30, seven=30)
        self._ledger()
        self.reads.clear()
        km._usage()
        self.assertEqual(self._spend_reads(), 0)

    def test_the_next_reading_sees_a_ledger_written_between_calls(self):
        self._spend_arm()
        self.assertEqual(km._usage()["spend"]["hour"]["usd"], 2.5)
        d = json.loads((jd.STATE / "spend.json").read_text())
        for e in d["hours"].values():
            e["usd"] = round(e["usd"] * 2, 4)
        (jd.STATE / "spend.json").write_text(json.dumps(d))     # a same-size-agnostic rewrite; no memo to miss it
        self.assertEqual(km._usage()["spend"]["hour"]["usd"], 5.0, "every call reads the file as it is now")

    def test_an_unreadable_ledger_reads_as_it_did(self):
        # the legacy marker with no ledger at all: zero windows (the honest zero), no series — the two
        # readers' own fallbacks, reached through the one shared document
        km._claude_account = lambda: ""
        km._auth_key_present = lambda: False
        (jd.STATE / "usage.json").write_text(json.dumps({"apiKey": True}))
        u = km._usage()
        self.assertTrue(u.get("apiKey"))
        self.assertEqual(u["spend"]["day"], {"usd": 0.0, "tok": 0, "turns": 0})
        self.assertNotIn("spendSeries", u)
        (jd.STATE / "spend.json").write_text("{not json")
        u = km._usage()
        self.assertEqual(u["spend"]["day"], {"usd": 0.0, "tok": 0, "turns": 0})
        self.assertNotIn("spendSeries", u)

    def test_usage_hands_one_document_to_both_readers(self):
        src = inspect.getsource(km._usage)
        calls = re.findall(r"_spend_(?:windows|series)\([^)]*\)", src)
        self.assertEqual(len(calls), 4, calls)
        for c in calls:
            self.assertIn("doc=", c, "every spend reader in _usage takes the parsed document: %s" % c)


class TheSpendReadersTakeADocument(_Base):
    """`doc=None` keeps today's read; a document passed is read instead of the file, and `now` still
    anchors the windows and the series exactly as before."""

    def setUp(self):
        super().setUp()
        self.frozen = time.mktime((2026, 9, 3, 12, 0, 0, 0, 0, -1))
        km.time = _frozen_clock(self.frozen)

    def test_a_document_is_read_in_place_of_the_file(self):
        self._ledger(keyed=True)
        from_file_w = km._spend_windows()
        from_file_s = km._spend_series(now=self.frozen)
        doc = json.loads((jd.STATE / "spend.json").read_text())
        (jd.STATE / "spend.json").unlink()
        self.reads.clear()
        self.assertEqual(km._spend_windows(doc=doc), from_file_w)
        self.assertEqual(km._spend_windows(keyed_only=True, doc=doc)["hour"]["usd"], 2.0)
        self.assertEqual(km._spend_series(now=self.frozen, doc=doc), from_file_s)
        self.assertEqual(km._spend_series(doc=doc), from_file_s, "the module clock is the default `now`, as before")
        self.assertEqual(self._spend_reads(), 0, "a document passed is not re-read from disk")
        self.assertEqual(from_file_w["hour"]["usd"], 2.5, "the frozen hour's bucket: the windows end at km.time")
        self.assertEqual(from_file_s["usd"][-1], 2.5)
        self.assertEqual(from_file_s["h0"], int(self.frozen // 3600) - (km._SERIES_HOURS - 1))

    def test_no_document_keeps_the_readers_own_read_and_fallbacks(self):
        self.assertEqual(km._spend_windows()["hour"], {"usd": 0.0, "tok": 0, "turns": 0})
        self.assertIsNone(km._spend_series(now=self.frozen))
        self._ledger()
        self.reads.clear()                              # the two failed attempts above counted as reads too
        self.assertEqual(km._spend_windows()["hour"]["usd"], 2.5)
        self.assertEqual(self._spend_reads(), 1, "no document: the reader reads the file itself, once")

    def test_an_empty_document_is_the_readers_no_ledger_fallback(self):
        self.assertEqual(km._spend_windows(doc={})["day"], {"usd": 0.0, "tok": 0, "turns": 0})
        self.assertIsNone(km._spend_series(doc={}))


class DerivedValuesKeepTheirClock(_Base):
    """`limited`, the countdown and the hold read km.time, never the wall clock behind it."""

    def test_limited_follows_the_module_clock(self):
        real = time.time()
        reset = int(real) + 3600                        # ahead on the wall clock...
        km._claude_account = lambda: ACCT
        km._auth_key_present = lambda: False
        km.time = _frozen_clock(real + 7200)            # ...behind on the module clock: the window has rolled
        self._windows(five=100, seven=10, five_reset=reset)
        self.assertIsNone(km._usage_limits()["limited"], "a rolled window is not limited on the clock the module reads")
        self.assertIsNone(km._usage()["limited"])
        self.assertEqual(km._account_limited(), [])
        self.assertIsNone(km._limit_hold(SID))
        km.time = _frozen_clock(real)                   # the same file, read at an instant before the reset
        self.assertEqual(km._usage_limits()["limited"], {"fiveHour": True, "sevenDay": False, "fable": False})
        self.assertEqual(km._account_limited(), ["fiveHour"])
        self.assertEqual(km._limit_hold(SID)["resetsAt"], reset)
        km._set_retry_paused(True, reason="limit")
        self.assertEqual(km._retry_resume_at(), reset)

    def test_the_full_reading_anchors_its_spend_on_the_module_clock(self):
        frozen = time.mktime((2026, 9, 3, 12, 0, 0, 0, 0, -1))
        km.time = _frozen_clock(frozen)
        self._spend_arm()
        u = km._usage()
        self.assertEqual(u["spend"]["hour"]["usd"], 2.5, "the frozen hour's bucket ends the rolling hour")
        self.assertEqual(u["spendSeries"]["h0"], int(frozen // 3600) - (km._SERIES_HOURS - 1))
        self.assertEqual(u["spendSeries"]["usd"][-1], 2.5)
        self.assertEqual(u["spendSeries"]["usd"][-4], 1.0)


if __name__ == "__main__":
    unittest.main()
