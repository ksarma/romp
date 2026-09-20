#!/usr/bin/env python3
"""ROMP_PRICE_FEED=off (the user 2026-09-20): the cost view's price feed has an off switch, and the view SAYS
where its prices come from.

_refresh_remote_prices fetches a third party's price table when the analytics view opens with a cache older
than six hours; it had no off switch and no visibility: a failed or refused fetch left the baked-in defaults
reading as though live. The switch copies the model catalog's (spelling and shape, `_refresh_model_catalog`)
and sits as the FIRST statement of the one function a fetch can start in, before the TTL check and the stamp,
so the spend guard's road, `_model_prices(refresh=False)` (T350), stays unable to start a fetch with the
switch off, on or unset. Under off the cache in process memory keeps serving with its age said, else the
defaults; never a silent early return: one stderr line per kernel life at the first refused attempt, and the
status rides the /analytics payload (`priceFeed`) and /version beside modelCatalog, computed by ONE function
(_price_feed_status). A failed fetch is said once per failed fetch, by reason class, never the response body.

Hermetic: urllib.request.urlopen is replaced by a recorder (the worker imports urllib inside `work`, so the
module attribute is what it calls), the feed body is a synthetic LiteLLM shape with invented rates, the clock
is a constant, and the kernel is loaded under a private name so its cache and status are this module's own.
"""
import ast
import inspect
import io
import json
import os
import pathlib
import tempfile
import textwrap
import threading
import unittest
import urllib.error
from contextlib import redirect_stderr
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)   # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_price_feed", os.path.join(BIN, "romp-kernel"))
jd = km.jd
# this module builds no backend; the minted root still carries the hosts-off word, as every minted root does
jd.STATE.mkdir(parents=True, exist_ok=True)
(jd.STATE / "session-hosts").write_text("off")

NOW = 1781100000              # a synthetic clock; every epoch below is relative to it
WINDOW = 86400
BODY_MARKER = "synthetic-feed-body-marker"   # what a fetch's response body carries; must never reach the status
# a LiteLLM-shaped body with INVENTED rates: one row that signs to a baked-in id, one that never can
FEED = {
    "claude-fable-5-1": {"input_cost_per_token": 11e-6, "output_cost_per_token": 55e-6,
                         "cache_creation_input_token_cost": 13.75e-6, "cache_read_input_token_cost": 1.1e-6},
    "some-other-vendor-model": {"input_cost_per_token": 1e-6, "output_cost_per_token": 2e-6},
}
OFF_LINE = "price feed: off (ROMP_PRICE_FEED=off)"
FAIL_LINE = "price feed: fetch failed ("
FEED_RESET = {"fetchedAt": None, "attemptedAt": None, "lastError": None, "rows": 0, "inflight": False, "offSaid": False}


class _Resp:
    """What the recorder's urlopen returns: a context manager whose read() is the fake body."""

    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


class PriceFeedCase(unittest.TestCase):
    """The harness every case shares: a fresh, stale (t=0) cache and a reset status, no user override file, no
    key and no login, no sessions discovered, the analytics memo cleared, the switch absent unless a test sets
    it, and a recording urlopen (`self.calls`) that serves FEED, raises `self.raise_with`, or parks on
    `self.gate` until the test opens it. Every mutation is undone through addCleanup (a failing setUp still
    restores)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        saved_t, saved_remote = km._price_cache["t"], dict(km._price_cache["remote"])
        self.addCleanup(lambda: km._price_cache.update(t=saved_t, remote=saved_remote))
        km._price_cache.update(t=0, remote={})
        # the status dict is absent on a kernel from before the switch (the fix's red-before run over the
        # pre-fix tree); the assertions below are unconditional, only this reset is guarded
        feed = getattr(km, "_price_feed", None)
        if feed is not None:
            saved_feed = dict(feed)
            self.addCleanup(lambda: feed.update(saved_feed))
            feed.update(FEED_RESET)
        saved = (km.PRICE_CONFIG, jd.STATE, jd.discover, km._auth_key_present, km._claude_account)

        def restore():
            km.PRICE_CONFIG, jd.STATE, jd.discover, km._auth_key_present, km._claude_account = saved
        self.addCleanup(restore)
        km.PRICE_CONFIG = pathlib.Path(self.td.name) / "no-prices.json"   # nonexistent: defaults only
        km._auth_key_present, km._claude_account = (lambda: False), (lambda: "")
        jd.STATE = pathlib.Path(self.td.name)
        jd.discover = lambda now, window=None, forks=True: []
        km._ANALYTICS_MEMO.clear()
        self.addCleanup(km._ANALYTICS_MEMO.clear)
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
        saved_env = os.environ.get("ROMP_PRICE_FEED")

        def restore_env():
            if saved_env is None:
                os.environ.pop("ROMP_PRICE_FEED", None)
            else:
                os.environ["ROMP_PRICE_FEED"] = saved_env
        self.addCleanup(restore_env)
        os.environ.pop("ROMP_PRICE_FEED", None)
        self.calls = []
        self.body = json.dumps(FEED).encode()
        self.raise_with = None
        self.gate = None
        patcher = mock.patch("urllib.request.urlopen", self._urlopen)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _urlopen(self, url, timeout=None, **kw):
        self.calls.append(url)
        if self.gate is not None:
            self.gate.wait(5)
        if self.raise_with is not None:
            raise self.raise_with
        return _Resp(self.body)

    def _join(self):
        """Wait for the refresh worker (the daemon thread named price-refresh) so an assertion reads a settled
        cache and a finished stderr line; a worker still alive after 5 s is a failure, not a wait."""
        for t in threading.enumerate():
            if t.name == "price-refresh":
                t.join(5)
                self.assertFalse(t.is_alive(), "the refresh worker must finish")

    def _analytics(self, now=NOW):
        """One build of the /analytics payload on the production road (the only refresh=True caller), the worker
        joined; returns (payload, stderr text)."""
        err = io.StringIO()
        with redirect_stderr(err):
            resp = km._token_analytics(now, WINDOW)
            self._join()
        return resp, err.getvalue()


class OffSwitch(PriceFeedCase):
    """(1) the switch stops the fetch, (2) the payload and /version say defaults because off, (5) one stderr line
    per kernel life, and the switch's spelling."""

    def test_off_an_analytics_build_with_a_stale_cache_makes_no_request(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        self.assertEqual(self.calls, [], "ROMP_PRICE_FEED=off: no request leaves the process")
        self.assertEqual(km._price_cache["t"], 0,
                         "the switch is read before the TTL stamp: off is no attempt at all, not a stamped skip")
        self.assertEqual(km._price_cache["remote"], {})
        self.assertEqual(resp["sessions"]["cost"], 0.0, "the build itself still served")

    def test_control_without_the_switch_the_same_build_fetches_exactly_once(self):
        resp, log = self._analytics()
        self.assertEqual(self.calls, [km.PRICE_FEED_URL], "a stale cache starts exactly one fetch")
        self.assertEqual(km._price_cache["t"], NOW, "stamped at the attempt")
        self.assertEqual(km._price_cache["remote"]["claude-fable-5-1"]["in"], 11e-6, "the fake's row landed")
        self.assertNotIn("some-other-vendor-model", km._price_cache["remote"], "a row that signs to no baked-in id is dropped")
        self.assertEqual(log, "", "a fetch that lands says nothing")

    def test_the_payload_and_version_say_defaults_because_the_feed_is_off(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        self.assertIn("priceFeed", resp, "the cost view's payload says where its prices come from")
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["reason"], pf["off"]), ("defaults", "off", True))
        self.assertEqual((pf["fetchedAt"], pf["ageS"], pf["attemptedAt"], pf["lastError"], pf["rows"]),
                         (None, None, None, None, 0), "nothing was attempted, so nothing is dated or blamed")
        v = km._version_info()
        self.assertIn("priceFeed", v, "/version mirrors the block")
        self.assertIn("modelCatalog", v, "beside the catalog's")
        self.assertEqual(v["priceFeed"], pf, "one function computes both, so they cannot disagree")
        resp2, _ = self._analytics(now=NOW + 5)
        self.assertEqual(km._ANALYTICS_MEMO[WINDOW]["t"], NOW, "the second build took the 15 s memo road")
        self.assertEqual(resp2["priceFeed"], pf, "and carries the status too")
        self.assertNotIn("priceFeed", km._ANALYTICS_MEMO[WINDOW]["resp"], "the memoized payload is never mutated")
        self.assertEqual(self.calls, [])

    def test_the_off_line_is_written_once_per_kernel_life(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)                        # the first refused attempt says so
            km._refresh_remote_prices(NOW + km.PRICE_TTL + 1)     # a second would-be fetch: silent
            km._token_analytics(NOW + 2 * km.PRICE_TTL, WINDOW)   # the view's road: silent too
            self._join()
        log = err.getvalue()
        self.assertEqual(log.count(OFF_LINE), 1, "one line per kernel life, at the first refused attempt:\n" + log)
        self.assertIn("the cost view prices tokens from the baked-in table", log, "it says what is served instead")
        self.assertEqual(self.calls, [], "and none of the three attempts left the process")
        self.assertEqual(km._price_cache["t"], 0)

    def test_the_spelling_is_the_catalogs_stripped_and_case_folded(self):
        os.environ["ROMP_PRICE_FEED"] = " Off "
        self._analytics()
        self.assertEqual(self.calls, [], "the catalog's spelling: whitespace stripped, case folded")
        for value in ("false", "0", ""):
            with self.subTest(value=value):
                os.environ["ROMP_PRICE_FEED"] = value
                km._ANALYTICS_MEMO.clear()
                km._price_cache.update(t=0, remote={})
                self._analytics()
        self.assertEqual(len(self.calls), 3, "any value but off leaves the feed on (the catalog's rule)")

    def test_the_switch_is_the_first_statement_of_the_refresh(self):
        """Nothing precedes the switch: not the TTL check, not the stamp. The one place a fetch can start."""
        fn = ast.parse(textwrap.dedent(inspect.getsource(km._refresh_remote_prices))).body[0]
        body = fn.body
        if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            body = body[1:]                                        # past the docstring
        self.assertIsInstance(body[0], ast.If)
        self.assertEqual(ast.unparse(body[0].test), "_price_feed_off()")
        self.assertEqual(inspect.getsource(km._price_feed_off).count(
            '(os.environ.get("ROMP_PRICE_FEED") or "").strip().lower() == "off"'), 1, "the catalog's spelling, verbatim")


class GuardRoad(PriceFeedCase):
    """(3) T350 both ways: `_model_prices(refresh=False)`, the spend guard's road, starts no fetch and says
    nothing with the switch off, on and unset. A PIN, green before the switch existed (the road predates it and
    never enters `_refresh_remote_prices`); the existing tests/test_spend_guard.py pin on the guard's own tick
    is left as it is."""

    def test_refresh_false_starts_no_fetch_whatever_the_switch_says(self):
        for value in ("off", "on", None):
            with self.subTest(switch=value):
                if value is None:
                    os.environ.pop("ROMP_PRICE_FEED", None)
                else:
                    os.environ["ROMP_PRICE_FEED"] = value
                km._price_cache.update(t=0, remote={})            # as stale as a cache gets
                err = io.StringIO()
                with redirect_stderr(err):
                    prices = km._model_prices(NOW, refresh=False)
                    self._join()
                self.assertEqual(self.calls, [], "the guard's road never starts a fetch")
                self.assertEqual(km._price_cache["t"], 0, "the stamp never moved: the road never entered the refresh")
                self.assertEqual(err.getvalue(), "", "and nothing is said: the guard made no attempt the switch could refuse")
                self.assertEqual(prices["claude-fable-5-1"]["in"], 10e-6, "the baked-in table is what it merged")

    def test_refresh_true_under_off_serves_the_defaults_and_still_starts_nothing(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        err = io.StringIO()
        with redirect_stderr(err):
            prices = km._model_prices(NOW)                        # the cost view's road
            self._join()
        self.assertEqual(self.calls, [])
        self.assertEqual(prices["claude-fable-5-1"]["in"], 10e-6)
        self.assertEqual(err.getvalue().count(OFF_LINE), 1, "the view's road is an attempt, and the first one is said")


class FailedFetch(PriceFeedCase):
    """(4) a fetch that fails is said once per failed fetch, not once per build, and the status names the
    reason class: the exception type, an HTTP status, an errno; never the response body or the URL."""

    def test_a_failed_fetch_is_said_once_and_the_status_names_the_reason_class(self):
        self.raise_with = urllib.error.HTTPError(km.PRICE_FEED_URL, 500, "Internal Server Error", {},
                                                 io.BytesIO(BODY_MARKER.encode()))
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)
            self._join()
        log = err.getvalue()
        self.assertEqual(log.count(FAIL_LINE), 1, "one stderr line for the failed fetch:\n" + log)
        self.assertIn("(HTTPError: HTTP 500)", log, "the reason class: type and status")
        self.assertIn("the cost view prices tokens from the baked-in table", log, "and what is served instead")
        self.assertNotIn(BODY_MARKER, log, "never the response body")
        self.assertNotIn(km.PRICE_FEED_URL, log, "never the URL")
        resp, log2 = self._analytics(now=NOW + 60)                # a build inside the TTL: no new fetch, no new line
        self.assertEqual(log2, "", "the status is read, not re-announced, per build")
        self.assertEqual(len(self.calls), 1)
        self.assertIn("priceFeed", resp)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["reason"], pf["off"]), ("defaults", "failed", False))
        self.assertEqual(pf["lastError"], "HTTPError: HTTP 500")
        self.assertEqual((pf["attemptedAt"], pf["fetchedAt"], pf["ageS"], pf["rows"]), (NOW, None, None, 0))
        self.assertNotIn(BODY_MARKER, json.dumps(pf))
        self.assertEqual(km._version_info()["priceFeed"]["lastError"], "HTTPError: HTTP 500", "/version names it too")

    def test_a_socket_error_names_the_wrapped_type_and_errno(self):
        self.raise_with = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)
            self._join()
        self.assertEqual(err.getvalue().count(FAIL_LINE), 1)
        resp, _ = self._analytics(now=NOW + 1)
        self.assertIn("priceFeed", resp)
        reason = resp["priceFeed"]["lastError"]
        self.assertTrue(reason.startswith("URLError: ConnectionRefusedError: errno 111"), reason)
        self.assertNotIn("://", reason, "no URL")
        self.assertEqual(resp["priceFeed"]["reason"], "failed")

    def test_the_next_fetch_after_the_ttl_is_a_new_episode_and_a_success_clears_the_blame(self):
        self.raise_with = urllib.error.HTTPError(km.PRICE_FEED_URL, 503, "Service Unavailable", {}, None)
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)
            self._join()
            km._refresh_remote_prices(NOW + km.PRICE_TTL - 1)     # inside the TTL: no attempt
            self._join()
            self.raise_with = None
            km._refresh_remote_prices(NOW + km.PRICE_TTL)         # the TTL passed: a new attempt, which lands
            self._join()
        self.assertEqual(err.getvalue().count(FAIL_LINE), 1, "the one failed fetch, once")
        self.assertEqual(len(self.calls), 2)
        resp, _ = self._analytics(now=NOW + km.PRICE_TTL + 30)
        self.assertIn("priceFeed", resp)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["reason"], pf["lastError"], pf["fetchedAt"], pf["ageS"], pf["rows"]),
                         ("feed", None, None, NOW + km.PRICE_TTL, 30, 1), "a landed fetch clears the blame")


class LiveFeed(PriceFeedCase):
    """The status when the feed is on: not fetched yet at the view's first open, live with its fetch time and
    age on the next click (through the memo), empty when the feed matches no baked-in id, and a populated cache
    under off served with its age said."""

    def test_the_first_open_reads_inflight_and_the_next_click_reads_live_through_the_memo(self):
        self.gate = threading.Event()                              # the worker parks inside urlopen
        self.addCleanup(self.gate.set)
        err = io.StringIO()
        with redirect_stderr(err):
            resp1 = km._token_analytics(NOW, WINDOW)
        self.assertIn("priceFeed", resp1)
        pf1 = resp1["priceFeed"]
        self.assertEqual((pf1["source"], pf1["reason"], pf1["attemptedAt"], pf1["fetchedAt"], pf1["off"]),
                         ("defaults", "inflight", NOW, None, False), "built before the fetch it started landed")
        self.gate.set()
        self._join()
        resp2 = km._token_analytics(NOW + 5, WINDOW)
        self.assertEqual(km._ANALYTICS_MEMO[WINDOW]["t"], NOW, "the second build served the memo")
        pf2 = resp2["priceFeed"]
        self.assertEqual((pf2["source"], pf2["reason"], pf2["fetchedAt"], pf2["ageS"], pf2["rows"], pf2["lastError"]),
                         ("feed", None, NOW, 5, 1, None), "the status rides outside the memo, so the click after the fetch shows it")
        self.assertEqual(resp2["sessions"], resp1["sessions"], "the memoized figures are what was served")
        self.assertEqual(err.getvalue(), "")
        v = km._version_info()["priceFeed"]
        self.assertEqual((v["source"], v["fetchedAt"], v["rows"]), ("feed", NOW, 1))

    def test_a_feed_that_matches_no_baked_in_id_reads_empty_never_live(self):
        self.body = json.dumps({"some-other-vendor-model": FEED["some-other-vendor-model"]}).encode()
        self._analytics()
        km._ANALYTICS_MEMO.clear()
        resp, _ = self._analytics(now=NOW + 1)
        self.assertIn("priceFeed", resp)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["reason"], pf["rows"], pf["fetchedAt"], pf["ageS"]),
                         ("defaults", "empty", 0, NOW, 1), "a landed feed that matched nothing is not the live feed")
        self.assertEqual(len(self.calls), 1)

    def test_a_populated_cache_under_off_is_served_with_its_age(self):
        self._analytics()                                          # a fetch landed while the feed was on
        self.assertEqual(len(self.calls), 1)
        os.environ["ROMP_PRICE_FEED"] = "off"
        km._ANALYTICS_MEMO.clear()
        resp, log = self._analytics(now=NOW + 7200)
        self.assertIn("priceFeed", resp)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["off"], pf["reason"], pf["fetchedAt"], pf["ageS"], pf["rows"]),
                         ("feed", True, None, NOW, 7200, 1), "off stops traffic, not data: the cache serves and says its age")
        self.assertEqual(km._model_prices(NOW + 7200)["claude-fable-5-1"]["in"], 11e-6, "the cached row is what prices tokens")
        self.assertEqual(len(self.calls), 1, "and no request left")
        self.assertEqual(log.count(OFF_LINE), 1)


if __name__ == "__main__":
    unittest.main()
