#!/usr/bin/env python3
"""ROMP_PRICE_FEED=off (the user 2026-09-20): the cost view's price feed has an off switch, and the view SAYS
where its prices come from.

_refresh_remote_prices fetches a third party's price table when the analytics view opens with a cache older
than six hours; it had no off switch and no visibility: a failed or refused fetch left the built-in defaults
reading as though live. The switch copies the model catalog's (spelling and shape, `_refresh_model_catalog`)
and sits as the FIRST statement of the one function a fetch can start in, before the TTL check and the stamp,
so the spend guard's road, `_model_prices(refresh=False)` (T350), stays unable to start a fetch with the
switch off, on or unset. Under off the cache in process memory keeps serving with its age said, else the
defaults; never a silent early return: one stderr line per kernel life at the first refused attempt, and the
status rides the /analytics payload (`priceFeed`) and /version beside modelCatalog, computed by ONE function
(_price_feed_status). A failed fetch is said once per failed fetch, by reason class, never the response body.
The review of PR 878 added: a switch value that is set and not off leaves the feed on (the catalog's rule) and is
SAID, once per kernel life on stderr naming the value, and as the boolean `unrecognised` in the block (OffSwitch);
every say-once latch is a test-and-set under _price_feed_lock with the line written outside it (SayOnceLatches); a
feed row or an override row whose rate is not a finite number is rejected at the parse (LiveFeed); an override file
the kernel cannot read is classed in the block (`overrideFault`) and said once (TheOverrideFileIsSaid); and what a
row that omits a rate inherits is pinned (APartialOverrideRow). The review's re-ruling (2026-09-21) changed two of
those: a row the kernel cannot read is skipped ALONE, wherever it sits, counted in the block (`overrideRowsRejected`)
and named once per kernel life on stderr by its key, and the override file's two fault classes latch separately
(TheOverrideFileIsSaid, SayOnceLatches). Round 2 of the review (2026-09-21) added: an override rate that is PRESENT and
not a JSON number (null, a string, a list, an object, a bool) is a rejected row like the other two classes, never a rate
coerced to 0.0 or 1.0 (TheOverrideFileIsSaid); the TTL check and its stamp take _price_feed_lock with the attempt's
fields, so two builds arriving together start ONE request, and the in-flight mark is a per-flight token that only its
own flight clears (OneFlightPerWindow); the stderr tail's age has a day arm (LiveFeed); and the status dict's keys are
the harness's reset keys, with the dead `rows` field gone (TheFeedDictIsWhatTheHarnessResets). Round 3 (2026-09-21)
re-ruled the string: a rate in quotes that is a plain decimal whole ("0.5", "3e-06") is read as that number, on the file's
road and the feed's, through _price_rate_value, the one read both parses share, and any other string (" 0.5", "1_0", "inf",
"nan", "1e999", "+0.5", "") is rejected as round 2 had it, never coerced by the bare float() that read those (the accept
and reject cases in TheOverrideFileIsSaid and LiveFeed; the two arms in one landing in tests/test_price_feed_consistency.py
APartialLandingIsSaid). The live feed sends numbers (the helper's docstring carries the count and the fetch time), so on
the feed's road the string arm is belt and braces; on the file's road it restores the quoted "0.5" both earlier heads read.

Hermetic: urllib.request.urlopen is replaced by a recorder (the worker imports urllib inside `work`, so the
module attribute is what it calls) that answers the feed's url alone and refuses any other request with a canned
URLError (PriceFeedCase's docstring says why), the feed body is a synthetic LiteLLM shape with invented rates, the
clock is a constant, and the kernel is loaded under a private name so its cache and status are this module's own.
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
import urllib.request
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
# a LiteLLM-shaped body with INVENTED rates: one row that signs to a built-in id, one that never can
FEED = {
    "claude-fable-5-1": {"input_cost_per_token": 11e-6, "output_cost_per_token": 55e-6,
                         "cache_creation_input_token_cost": 13.75e-6, "cache_read_input_token_cost": 1.1e-6},
    "some-other-vendor-model": {"input_cost_per_token": 1e-6, "output_cost_per_token": 2e-6},
}
OFF_LINE = "price feed: off (ROMP_PRICE_FEED=off)"
FAIL_LINE = "price feed: fetch failed ("
FEED_RESET = {"fetchedAt": None, "attemptedAt": None, "lastError": None, "matched": 0, "inflight": 0, "flights": 0,
              "offSaid": False, "unrecognisedSaid": False, "overrideFileSaid": False, "overrideRowsSaid": frozenset()}
#   the kernel's literal has exactly these keys (TheFeedDictIsWhatTheHarnessResets); `inflight` is the flight's token, 0 when none
UNRECOGNISED_LINE = "price feed: ROMP_PRICE_FEED is set to "   # the head of the said-but-on line, up to the value's repr
SERVED_DEFAULTS = "the cost view prices tokens from the built-in defaults"   # the lines' tail with nothing cached and no override
FOREIGN_REFUSED = "the price feed harness refuses requests that are not the feed: "   # the recorder's URLError reason, then the url
# the override file's two fault lines: the row's takes the row's key by repr (the kernel clips it to 40 characters)
ROW_LINE = ("price feed: the row %s in model-prices.json could not be read (not an object, a rate that is not a number, or a "
            "rate that is not finite), so that row is skipped and the rest of the file applies")
FILE_LINE = "price feed: model-prices.json could not be read as a JSON object, so the file is ignored whole"


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
    restores).

    THE RECORDER COUNTS THE FEED ALONE (2026-09-21). The patch on urllib.request.urlopen is process-wide, so any thread
    in the process that dials urlopen inside a case's window reaches this recorder, and the postal service's peer
    dialer is such a thread: three other test modules start one per synthetic peer and never mark the peer down, so
    the dialers outlive their modules and dial again whenever their backoff returns. Recorded and answered with feed
    bytes, which parse as JSON, a dialer reads a healthy exchange and dials again at once, hundreds of requests per
    second for as long as the window stays open: CI's serial CPython 3.12 cell on 2026-09-21 found 677 of its requests
    in self.calls inside SayOnceLatches' 0.5 s park, the one wide window in the two modules that share this harness.
    So _urlopen compares the request's url (a str, or a Request's full_url) to km.PRICE_FEED_URL: the feed's request
    is recorded and answered as before, and any other request is not recorded and is refused with a URLError whose
    reason is FOREIGN_REFUSED and the url, a failed dial the dialer backs off from. Nothing of the real urlopen is
    kept for delegation, so a foreign caller inside a test never reaches the network and never sees the feed's bytes,
    and `self.calls` is the feed's count and nothing else's. The pin is TheRecorderCountsTheFeedAlone. km.PRICE_FEED_URL
    there is the product's own constant read at call time, not a copy of its text: _refresh_remote_prices's worker passes
    that same name to urlopen as a plain str (no Request object, no composition of a host and a path anywhere in the
    product), so the recorder compares against exactly what the product sends, and a change to the constant moves the
    recorder with it. A literal here would, after such a change, refuse every feed request as foreign and record
    nothing while every count assertion still read 0 or 1 as if the feed were the subject; keep the constant.

    THE RULE FOR READING A LANDING OR A FAILURE (the review of PR 878, whose round found three cases breaking it): any
    assertion about a landing or a failure reads it after the join, from km._price_feed_status(now) or from a second
    build inside the TTL (_settled), never from the payload of the build that started the fetch. _analytics returns
    that payload, built while the worker ran and joined only afterwards, so its block is whichever whole picture the
    build's status read found, the landing or the flight; under the GIL the worker landed inside its first slice and
    the build's block was the landing's, and free-threaded CPython runs the two at once and reads the flight. A case
    that still asserts that payload's block pins it as one whole picture, the landing or the flight, never a landed
    table with no rows."""

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
        (jd.STATE / "session-hosts").write_text("off")   # the hermetic-root rule: a minted root pins per-session hosts off
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
        target = str(getattr(url, "full_url", url))                # a str, or a Request
        if target != km.PRICE_FEED_URL:                            # the feed alone: the class docstring's paragraph
            raise urllib.error.URLError(FOREIGN_REFUSED + target)
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
        joined AFTER the build returned; returns (payload, stderr text). The payload's block is the one the build's
        own status read found, the fetch it started in flight or landed: read a landing or a failure from _settled
        or from km._price_feed_status after this returns, never from this payload (the class docstring's rule)."""
        err = io.StringIO()
        with redirect_stderr(err):
            resp = km._token_analytics(now, WINDOW)
            self._join()
        return resp, err.getvalue()

    def _settled(self, now=NOW):
        """The block once the fetch the last build started has landed or failed: the worker joined, then a second
        build at `now` (inside the TTL, so it starts no fetch; the same `now` as the first build keeps a pinned
        ageS), its payload's block. Where the members of the review's item C read the landing out of the payload
        of the build that started the fetch, they read it from here or from km._price_feed_status."""
        self._join()
        resp, _ = self._analytics(now=now)
        return resp["priceFeed"]


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
        self.assertNotIn("some-other-vendor-model", km._price_cache["remote"], "a row that signs to no built-in id is dropped")
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
        self.assertIn(SERVED_DEFAULTS, log, "it says what is served instead, in the view's word for the table (defaults, not table)")
        self.assertEqual(self.calls, [], "and none of the three attempts left the process")
        self.assertEqual(km._price_cache["t"], 0)

    def test_the_spelling_is_the_catalogs_stripped_and_case_folded(self):
        """Only off, whitespace and case ignored, turns the feed off; every other value leaves it on, and since the review
        of PR 878 a value that is set and not off is also SAID: the block's `unrecognised` is True for it, False for off
        in any spelling, for empty and for unset. At the head the review reviewed the key was absent (`.get` reads None)."""
        os.environ["ROMP_PRICE_FEED"] = " Off "
        resp, _ = self._analytics()
        self.assertEqual(self.calls, [], "the catalog's spelling: whitespace stripped, case folded")
        self.assertIs(resp["priceFeed"].get("unrecognised"), False, "off in any case or padding is off, never a value to say")
        for value in ("false", "0", "no", "on", ""):
            with self.subTest(value=value):
                os.environ["ROMP_PRICE_FEED"] = value
                km._ANALYTICS_MEMO.clear()
                km._price_cache.update(t=0, remote={})
                resp, _ = self._analytics()
                self.assertIs(resp["priceFeed"].get("unrecognised"), bool(value),
                              "set and not off is said as unrecognised; empty reads as unset (the switch reads it per call)")
        self.assertEqual(len(self.calls), 5, "any value but off leaves the feed on (the catalog's rule)")
        os.environ.pop("ROMP_PRICE_FEED", None)
        self.assertIs(km._price_feed_status(NOW).get("unrecognised"), False, "unset: nothing to say")

    def test_a_value_that_is_not_off_leaves_the_feed_on_and_is_said_once_naming_the_value(self):
        """The switch fails OPEN for any value but off, by the catalog's rule; the review of PR 878 found that such a
        value was byte for byte an unset one on every surface (stderr, /version, /analytics, the modal). Now the first
        attempt that reads it writes one line naming the variable, the value (repr) and that only off turns the feed
        off; the block and /version carry `unrecognised` True with the feed's own state unchanged; the line is written
        once per kernel life whatever later values are read; and the value itself never reaches the block or /version,
        which is auth-exempt. Red at the reviewed head at the line count and the key (None there)."""
        os.environ["ROMP_PRICE_FEED"] = "of"
        resp, log = self._analytics()
        self.assertEqual(self.calls, [km.PRICE_FEED_URL], "only off turns the feed off: the fetch went out")
        head = UNRECOGNISED_LINE + "'of', which is not off, so the feed stays on; the cost view prices tokens from "
        self.assertEqual(log.count(head), 1, "one line at the first attempt that read the value, naming what it read:\n" + log)
        pf = self._settled()
        self.assertIs(pf.get("unrecognised"), True, "the block says the switch is set to a value that is not off")
        self.assertEqual((pf["off"], pf["source"], pf["reason"], pf["rows"]), (False, "feed", None, 1),
                         "and the feed's own state is what it is: on, landed")
        self.assertIs(km._version_info()["priceFeed"].get("unrecognised"), True, "/version says so too")
        os.environ["ROMP_PRICE_FEED"] = "enabled-please"          # another value at the next TTL attempt: on, and not said again
        km._ANALYTICS_MEMO.clear()
        resp, log2 = self._analytics(now=NOW + km.PRICE_TTL)
        self.assertEqual(len(self.calls), 2, "the second would-be fetch went out too")
        self.assertNotIn(UNRECOGNISED_LINE, log2, "said once per kernel life, whatever the value:\n" + log2)
        pf2 = self._settled(NOW + km.PRICE_TTL)
        self.assertIs(pf2.get("unrecognised"), True)
        self.assertNotIn("enabled-please", json.dumps(pf2) + json.dumps(km._version_info()["priceFeed"]),
                         "the boolean, never the value: the block rides the auth-exempt /version")

    def test_a_trailing_comment_is_a_value_that_is_not_off_and_the_line_shows_it_by_repr(self):
        """The shape systemd preserves from `ROMP_PRICE_FEED=off # comment` in service.env: not off, so the feed stays
        on, and the line's repr shows the padding, the case and the trailing text that made it so."""
        os.environ["ROMP_PRICE_FEED"] = " Off # comment "
        resp, log = self._analytics()
        self.assertEqual(self.calls, [km.PRICE_FEED_URL], "a trailing comment is a value that is not off: the fetch went out")
        self.assertIn(UNRECOGNISED_LINE + "' Off # comment ', which is not off, so the feed stays on; ", log, log)
        self.assertIs(self._settled().get("unrecognised"), True)

    def test_a_long_value_is_clipped_in_the_line(self):
        """The repr is clipped to 40 characters: enough to see what was typed, never a page of environment on stderr."""
        os.environ["ROMP_PRICE_FEED"] = "x" * 60
        resp, log = self._analytics()
        self.assertIn(UNRECOGNISED_LINE + "'" + "x" * 36 + "..., which is not off, so the feed stays on; ", log, log)
        self.assertNotIn("x" * 40, log, "clipped")

    def test_off_in_any_case_or_padding_is_off_and_never_read_as_unrecognised(self):
        """The off arm is the first statement and the said-but-on arm follows it, so a refused attempt never reads as
        unrecognised and writes no such line."""
        for value in ("off", " OFF ", "Off\t"):
            with self.subTest(value=value):
                os.environ["ROMP_PRICE_FEED"] = value
                km._ANALYTICS_MEMO.clear()
                resp, log = self._analytics()
                self.assertEqual(self.calls, [])
                self.assertNotIn(UNRECOGNISED_LINE, log)
                self.assertEqual((resp["priceFeed"]["off"], resp["priceFeed"].get("unrecognised")), (True, False))

    def test_the_switch_docstring_names_the_update_checks_switch_by_its_real_name(self):
        """The sentence a reader checks the precedent against: the docstring that justifies the spelling cited
        `_update_check_off`, a symbol bound nowhere; the function is _update_checks_off. It states the rule (only off,
        stripped and case-folded, turns the feed off; any other value leaves it on and is said) and names the catalog as
        the spelling copied, and it never quotes the guarded expression, which the source pin above counts once."""
        doc = km._price_feed_off.__doc__
        self.assertIn("_update_checks_off", doc, "the update check's switch, by its real name")
        self.assertNotIn("_update_check_off", doc, "the dead name is gone")
        self.assertTrue(hasattr(km, "_update_checks_off"), "and the name resolves")
        self.assertIn("_refresh_model_catalog", doc, "the catalog, the spelling this switch copies")
        self.assertIn("every other value leaves it on", doc, "the rule, stated")

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
        # the said-but-on arm sits after the off arm (a refused attempt never reads as unrecognised) and before the TTL
        # check (the first attempt, which always fetches, is the one that says it): the review of PR 878's contract
        self.assertIsInstance(body[1], ast.If)
        self.assertEqual(ast.unparse(body[1].test), "_price_feed_unrecognised()", "second: the value that is not off, said")
        # third: the gate, ONE transition under the lock (the TTL check, its stamp and the attempt's fields; round 2 of the
        # review found the check and the stamp one statement above the lock, and two builds arriving together both passed)
        self.assertIsInstance(body[2], ast.With, "third: the with block over the lock that holds the TTL check")
        self.assertEqual([ast.unparse(i.context_expr) for i in body[2].items], ["_price_feed_lock"])
        self.assertIsInstance(body[2].body[0], ast.If, "the TTL check is the lock block's first statement")
        self.assertIn("PRICE_TTL", ast.unparse(body[2].body[0].test), "the TTL check")
        self.assertIsInstance(body[2].body[0].body[0], ast.Return, "a fresh cache returns inside the lock: nothing stamped")


class SayOnceLatches(PriceFeedCase):
    """Each say-once latch (`offSaid`; the unrecognised value's `unrecognisedSaid`; the override file's `overrideFileSaid`
    and, per row key, `overrideRowsSaid`) is a test-and-set under _price_feed_lock, and the line is written outside the
    lock. Before the review of PR 878 the off latch was a check
    then a set with no lock (the comment said a lone fact needs none: true of a store, not of a read followed by a
    write), and two cost-view builds arriving together, request-handler threads, both wrote the line. Staged
    deterministically with a one-shot capture-then-park gate rather than a barrier (a barrier that times out raises
    inside the read and writes no line, a false pass): the first reader captures the latch's value, then parks until
    the second has read it too, or for half a second when the lock keeps the second out; the second reader releases
    it. Without the lock both capture False and both write; with it the first holds the lock while parked, the second
    reads True after it, and one line is written."""

    def _race(self, key, value, marker, target=None):
        """Two threads run `target` (km._refresh_remote_prices by default) at NOW under ROMP_PRICE_FEED=`value`, the read
        of `_price_feed[key]` gated as the class docstring says; returns (the count of `marker` in stderr, the log)."""
        first_read, second_read = threading.Event(), threading.Event()
        prefix = "price-feed-latch-"

        class Parked(dict):
            def __getitem__(self, k):
                v = dict.__getitem__(self, k)                      # captured BEFORE parking: the check's own value
                if k == key and threading.current_thread().name.startswith(prefix):
                    if not first_read.is_set():
                        first_read.set()
                        second_read.wait(0.5)                      # the second read, or the lock keeping it out
                    else:
                        second_read.set()
                return v
        real = km._price_feed
        km._price_feed = Parked(real)
        self.addCleanup(setattr, km, "_price_feed", real)          # the harness then resets the real dict's values
        os.environ["ROMP_PRICE_FEED"] = value
        threads = [threading.Thread(target=target or km._refresh_remote_prices, args=(NOW,), name=prefix + str(i))
                   for i in (1, 2)]
        err = io.StringIO()
        with redirect_stderr(err):
            for t in threads:
                t.start()
            for t in threads:
                t.join(5)
            self._join()
        self.assertFalse(any(t.is_alive() for t in threads), "both attempts finished")
        self.assertTrue(first_read.is_set(), "the gate saw the first read of the latch")
        return err.getvalue().count(marker), err.getvalue()

    def test_two_attempts_under_off_arriving_together_write_the_off_line_once(self):
        count, log = self._race("offSaid", "off", OFF_LINE)
        self.assertEqual(count, 1, "one off line per kernel life, whatever arrives together:\n" + log)
        self.assertEqual(self.calls, [])

    def test_two_attempts_reading_a_value_that_is_not_off_write_its_line_once(self):
        """The contract's second latch, the same shape. At the reviewed head this arm did not exist, so the latch was
        never read (the gate assertion fails first) and no line was written: the subject is the new arm, and the
        lock's own proof for this latch is the mutation run (the test-and-set moved outside the lock in a scratch
        copy reads 2 here, on both interpreters)."""
        count, log = self._race("unrecognisedSaid", "maybe", UNRECOGNISED_LINE)
        self.assertEqual(count, 1, "one line per kernel life for a value that is not off:\n" + log)
        self.assertIn("'maybe'", log)

    def test_two_builds_meeting_a_skipped_row_together_name_it_once(self):
        """The row latch (`overrideRowsSaid`, a frozenset of the row keys named, replaced under the lock) has the same
        shape on the cost view's road: two merges arriving together (km._model_prices at NOW, refresh on, the switch off
        so no fetch starts) name the row once. At the 5cbf9e397 archive the latch was one boolean, `overrideSaid`, and
        this key is never read: the gate assertion fails first. The lock's proof is the mutation run (the test-and-set
        moved outside the lock in a scratch copy reads 2 here)."""
        km.PRICE_CONFIG.write_text(json.dumps({"note": "my rates"}))
        count, log = self._race("overrideRowsSaid", "off", ROW_LINE % "'note'", target=km._model_prices)
        self.assertEqual(count, 1, "one line per kernel life per row, whatever arrives together:\n" + log)
        self.assertEqual(km._price_feed["overrideRowsSaid"], frozenset({"note"}), "the latch holds the row's key")


class _PerCallGate:
    """What the recorder parks on when a case needs each fetch on its OWN event: the n-th caller of wait parks on the
    n-th event (a caller beyond `n` on the last), and `entered[i]` says the i-th caller is inside the fetch. The
    harness's `self.gate` is any object with wait(timeout)."""

    def __init__(self, n):
        self.events = [threading.Event() for _ in range(n)]
        self.entered = [threading.Event() for _ in range(n)]
        self._n, self._lock = 0, threading.Lock()

    def wait(self, timeout):
        with self._lock:
            i = min(self._n, len(self.events) - 1)
            self._n += 1
        self.entered[i].set()
        return self.events[i].wait(timeout)

    def release_all(self):
        for e in self.events:
            e.set()


class OneFlightPerWindow(PriceFeedCase):
    """The TTL check (the read of `_price_cache["t"]`) and its stamp are a read-modify-write, and since round 2 of the
    review of PR 878 they take _price_feed_lock with the attempt's fields (attemptedAt and the flight token) as ONE
    transition, so exactly one caller per TTL window proceeds. Before it the check stood one statement above the
    lock: two cost-view builds arriving together both read the stale stamp, both stamped and each started a worker,
    two requests to the feed's host and two fetch lines inside one window, against the bound _refresh_remote_prices's
    docstring states. Staged the way SayOnceLatches stages a latch, on the read of "t" instead: the first of two
    attempt threads captures the stamp's value and parks; the park ends on an EVENT, the second thread's read of "t"
    (both passed the check: the shape before the fix) or the second thread's ask for the lock the first holds (the
    fixed shape, where the second cannot reach the read until the first is done), never a wall-clock second alone,
    and the wait's return is asserted, so a park that ran out is a failure and not a pass. SayOnceLatches's not-off
    race does not see the gate: its first thread holds the lock through the latch park, so the second blocks before
    the check. The second pin is the token: the in-flight mark was a shared boolean the worker's finally cleared for
    every flight, outside the lock, so the first of two flights to end cleared the mark of one still in the air; the
    mark is the flight's own token now, cleared under the lock only while it is still that flight's."""

    PREFIX = "price-feed-gate-"

    def test_two_builds_arriving_together_start_one_request_and_write_one_line(self):
        """Red over the 84b27dd39 archive (the check-then-stamp predates the PR; no lock and no fetch line exist there, so
        the request count is the assertion that reds: 2 where 1 is expected) and over 3ddaf64d8 (2 requests, 2 lines);
        green at the tree on CPython 3.12 and free-threaded 3.14. The lock shim installs only where the kernel has the
        lock, so at the base the second read is the one release edge, the edge that fires there and at the head anyway."""
        self.raise_with = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))   # each fetch fails and says so
        first_read, release, ended, asks = threading.Event(), threading.Event(), [], []
        prefix = self.PREFIX

        class Parked(dict):
            def __getitem__(self, k):
                v = dict.__getitem__(self, k)                      # captured BEFORE parking: the check's own value
                if k == "t" and threading.current_thread().name.startswith(prefix):
                    if not first_read.is_set():
                        first_read.set()
                        ended.append(release.wait(5))              # the second read, or the second ask for the lock
                    else:
                        release.set()
                return v
        real_cache = km._price_cache
        km._price_cache = Parked(real_cache)
        self.addCleanup(setattr, km, "_price_cache", real_cache)   # LIFO: restored before the harness refills the real dict
        real_lock = getattr(km, "_price_feed_lock", None)          # absent at the base archive: the second read is the one edge

        class Shim:
            def __enter__(self):
                if threading.current_thread().name.startswith(prefix):
                    asks.append(1)
                    if len(asks) >= 2:
                        release.set()                              # the second attempt asks for the lock the first holds
                return real_lock.__enter__()

            def __exit__(self, *exc):
                return real_lock.__exit__(*exc)
        if real_lock is not None:
            km._price_feed_lock = Shim()
            self.addCleanup(setattr, km, "_price_feed_lock", real_lock)
        threads = [threading.Thread(target=km._refresh_remote_prices, args=(NOW,), name=prefix + str(i)) for i in (1, 2)]
        err = io.StringIO()
        with redirect_stderr(err):
            for t in threads:
                t.start()
            for t in threads:
                t.join(5)
            self._join()
        log = err.getvalue()
        self.assertFalse(any(t.is_alive() for t in threads), "both attempts finished")
        self.assertTrue(first_read.is_set(), "the gate saw the first read of the stamp")
        self.assertEqual(ended, [True],
                         "the park ended on its event (the second read, or the second ask for the lock), not by running out")
        self.assertEqual(len(self.calls), 1,
                         "two builds arriving together at a stale cache start ONE request; %d left" % len(self.calls))
        self.assertEqual(log.count(FAIL_LINE), 1, "and one fetch line inside the window:\n" + log)
        self.assertEqual(km._price_cache["t"], NOW, "stamped once, at the attempt")
        st = km._price_feed_status(NOW)
        self.assertEqual((st["reason"], st["attemptedAt"]), ("failed", NOW), "the one flight failed and said so")

    def test_the_first_flight_to_end_leaves_a_later_flights_mark_standing(self):
        """Two flights one TTL apart, both parked inside the fetch; the first is released and lands while the second is
        still in the air. The mark then still says a flight is in the air (the second's token), and clears when the
        second ends. Red over the 3ddaf64d8 archive at the first mark assertion (the finally cleared a shared boolean
        for both). The field is the subject: on every surface a landed or failed result outranks a fetch in flight
        (the reason chain in _price_feed_status), so the mark's truth shows there only for a kernel with no result yet."""
        gates = _PerCallGate(2)
        self.gate = gates                                          # the recorder parks each fetch on its own event
        self.addCleanup(gates.release_all)
        before = set(threading.enumerate())
        with redirect_stderr(io.StringIO()):
            km._refresh_remote_prices(NOW)                         # flight 1
            first = [t for t in threading.enumerate() if t not in before and t.name == "price-refresh"]
            self.assertEqual(len(first), 1, "flight 1 started one worker")
            self.assertTrue(gates.entered[0].wait(5), "flight 1 is inside the fetch")
            km._refresh_remote_prices(NOW + km.PRICE_TTL)          # flight 2: the TTL passed, a new attempt
            second = [t for t in threading.enumerate() if t not in before and t.name == "price-refresh" and t not in first]
            self.assertEqual(len(second), 1, "flight 2 started one worker")
            self.assertTrue(gates.entered[1].wait(5), "flight 2 is inside the fetch")
            self.assertEqual(len(self.calls), 2)
            gates.events[0].set()                                  # flight 1 lands while flight 2 is still in the air
            first[0].join(5)
            self.assertFalse(first[0].is_alive(), "flight 1 ended")
            mark_while_second_flies = km._price_feed["inflight"]
            gates.events[1].set()
            second[0].join(5)
            self._join()
        self.assertTrue(mark_while_second_flies, "flight 1 ended while flight 2 was in the air: the mark still says so (the "
                        "second flight's token), not the cleared value flight 1's end used to leave for both")
        self.assertFalse(km._price_feed["inflight"], "flight 2 ended: the mark is clear")
        st = km._price_feed_status(NOW + km.PRICE_TTL)
        self.assertEqual((st["source"], st["rows"], st["fetchedAt"]), ("feed", 1, NOW + km.PRICE_TTL),
                         "both landed; the later one is the table")


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
                self.assertEqual(prices["claude-fable-5-1"]["in"], 10e-6, "the built-in table is what it merged")

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
        self.assertIn(SERVED_DEFAULTS, log, "and what is served instead")
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

    def test_a_tls_or_resolver_failure_is_labelled_from_its_own_table_never_the_system_errno(self):
        """ssl.SSLError and socket.gaierror carry LIBRARY codes in errno (SSL_ERROR_SSL is 1, EAI_NONAME is -2);
        labelled through os.strerror they read as EPERM's "Operation not permitted" and "Unknown error -2", a false
        diagnosis in the two ways a fetch to a public host fails most (a TLS-intercepting proxy or a stale CA bundle;
        a box offline). The label comes from the code's own table instead: OpenSSL's reason token and the verify code's
        table string (the verify message is never read), the EAI_ constant's name and libc's text. Genuine exceptions wherever one can be raised without traffic (a
        handshake fed EOF through in-memory BIOs; a resolver call that forbids a lookup, AI_NUMERICHOST); the
        certificate failure is built the way CPython's _ssl builds it (errno, reason, verify_code and verify_message)."""
        import socket
        import ssl
        ctx = ssl.create_default_context()                        # a real handshake failure with no socket: the client
        c_in, c_out = ssl.MemoryBIO(), ssl.MemoryBIO()             # hello goes out and EOF comes back
        client = ctx.wrap_bio(c_in, c_out, server_side=False, server_hostname="TESTHOST")
        try:
            client.do_handshake()
        except ssl.SSLWantReadError:
            pass
        c_in.write_eof()
        with self.assertRaises(ssl.SSLError) as cm:
            client.do_handshake()
        eof = cm.exception
        self.assertEqual(eof.errno, ssl.SSL_ERROR_EOF, "the library's code, which os.strerror would read as ENOEXEC")
        label = km._price_feed_error_class(urllib.error.URLError(eof))
        self.assertEqual(label, "URLError: %s: %s" % (type(eof).__name__, eof.reason), label)
        self.assertNotIn(os.strerror(eof.errno), label, "never the system errno's text for a library code")
        cert = ssl.SSLCertVerificationError(ssl.SSL_ERROR_SSL, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify "
                                            "failed: self-signed certificate (_ssl.c:1000)")
        cert.reason, cert.verify_code, cert.verify_message = "CERTIFICATE_VERIFY_FAILED", 18, "self-signed certificate"
        label = km._price_feed_error_class(urllib.error.URLError(cert))
        self.assertEqual(label, "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED (self-signed certificate)")
        self.assertNotIn("Operation not permitted", label)
        self.assertNotIn("_ssl.c", label, "the token and the verify text, never the message")
        with self.assertRaises(socket.gaierror) as cm:             # a real resolver failure with no lookup
            socket.getaddrinfo("TESTHOST.invalid", 443, flags=socket.AI_NUMERICHOST)
        gai = cm.exception
        self.assertEqual(gai.errno, socket.EAI_NONAME)
        label = km._price_feed_error_class(urllib.error.URLError(gai))
        self.assertEqual(label, "URLError: gaierror: EAI_NONAME (%s)" % gai.strerror, label)
        self.assertNotIn("Unknown error", label)
        self.assertNotIn("TESTHOST", label, "never the host")
        self.assertEqual(km._price_feed_error_class(urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))),
                         "URLError: ConnectionRefusedError: errno 111 (Connection refused)", "control: a socket errno keeps the system table")
        # Three legs no case reached until the review of PR 878; each pins the behaviour as it stood (green at the
        # reviewed head), proven by mutation (the leg removed or relabelled in a scratch copy reds the assertion).
        # (a) the older resolver family: an h_errno labelled through the resolver's table, by number when no EAI_
        #     constant carries it, with libc's text, never os.strerror's text for the same number (EPERM's)
        herr = socket.herror(1, "Unknown host")
        label = km._price_feed_error_class(urllib.error.URLError(herr))
        self.assertEqual(label, "URLError: herror: resolver error 1 (Unknown host)", label)
        self.assertNotIn("Operation not permitted", label)
        # (b) an SSL error with no reason token (built by hand, as a library boundary can raise it): the code by number,
        #     never EPERM's text for SSL_ERROR_SSL
        bare = ssl.SSLError(ssl.SSL_ERROR_SSL, "[SSL] text")
        label = km._price_feed_error_class(urllib.error.URLError(bare))
        self.assertEqual(label, "URLError: SSLError: ssl error %d" % ssl.SSL_ERROR_SSL, label)
        self.assertNotIn("Operation not permitted", label)
        # (c) an errno beyond the C int os.strerror takes: OverflowError on Linux, and the label keeps the number alone
        #     (the ValueError leg is for a platform whose strerror rejects a code in range; Linux's never does, it
        #     answers `Unknown error N`, so that leg is unreachable here and stays as the other platforms' guard)
        big = OSError(2 ** 40, "beyond the table")
        self.assertEqual(km._price_feed_error_class(urllib.error.URLError(big)), "URLError: OSError: errno %d" % 2 ** 40)
        self.raise_with = urllib.error.URLError(cert)              # through the worker: lastError, the line and /version carry it
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)
            self._join()
        want = "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED (self-signed certificate)"
        self.assertIn("price feed: fetch failed (%s); " % want, err.getvalue())
        self.assertEqual(km._version_info()["priceFeed"]["lastError"], want)

    def test_a_certificate_failure_is_labelled_from_its_verify_code_never_its_verify_message(self):
        """The verify CODE, through the kernel's own copy of OpenSSL 3.0's verify-error table (_price_feed_verify_errors);
        the verify MESSAGE is never read, since CPython composes two of them with the server hostname. Round 2 kept the
        host out by dropping any message holding a quote character, which dropped eight of the table's own strings, the
        ones with a possessive apostrophe (codes 4, 5, 13, 14, 15, 16, 24 and 46), to the bare token. Here: the eight
        read their table string; a code 18 whose message QUOTES a name still reads the table's row (the row that proves
        the message is not read); the two composed codes read the fixed words (controls); a code the table lacks reads
        its number; under a library older than OpenSSL 3 every code reads its number; and one of the eight rides through
        the worker to lastError, the stderr line and /version. Built the way _ssl builds the exception (errno, reason,
        verify_code, verify_message); every message that names a host names TESTHOST, which no label may carry."""
        import ssl

        def cert(code, message):
            e = ssl.SSLCertVerificationError(ssl.SSL_ERROR_SSL, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify "
                                             "failed: %s (_ssl.c:1000)" % message)
            e.reason, e.verify_code, e.verify_message = "CERTIFICATE_VERIFY_FAILED", code, message
            return urllib.error.URLError(e)
        head = "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED"
        eight = {4: "unable to decrypt certificate's signature", 5: "unable to decrypt CRL's signature",
                 13: "format error in certificate's notBefore field", 14: "format error in certificate's notAfter field",
                 15: "format error in CRL's lastUpdate field", 16: "format error in CRL's nextUpdate field",
                 24: "issuer certificate doesn't have a public key", 46: "RFC 3779 resource not subset of parent's resources"}
        for code, text in eight.items():
            with self.subTest(code=code):
                self.assertEqual(km._price_feed_error_class(cert(code, text)), "%s (%s)" % (head, text))
        quoted = km._price_feed_error_class(cert(18, "self-signed certificate, not valid for 'TESTHOST'"))
        self.assertEqual(quoted, head + " (self-signed certificate)", "the code's row, whatever the message says")
        self.assertNotIn("TESTHOST", quoted, "never the host")
        composed = ((62, "Hostname mismatch, certificate is not valid for 'TESTHOST'.", "hostname mismatch"),
                    (64, "IP address mismatch, certificate is not valid for 'TESTHOST'.", "IP address mismatch"))
        for code, message, words in composed:                      # controls: the two messages _ssl composes with the host
            label = km._price_feed_error_class(cert(code, message))
            self.assertEqual(label, "%s (%s)" % (head, words))
            self.assertNotIn("TESTHOST", label, "never the host")
        unknown = km._price_feed_error_class(cert(999, "Some later check, certificate is not valid for 'TESTHOST'."))
        self.assertEqual(unknown, head + " (verify code 999)", "a code the table lacks: its number, never its message")
        self.assertNotIn("TESTHOST", unknown, "never the host")
        with mock.patch.object(ssl, "OPENSSL_VERSION_INFO", (1, 1, 1, 0, 0)):   # a code's meaning belongs to the major version
            self.assertEqual(km._price_feed_error_class(cert(18, "self-signed certificate")), head + " (verify code 18)",
                             "under an older library the table is not read: the code by number")
        self.raise_with = cert(13, eight[13])                       # through the worker: lastError, the line and /version
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)
            self._join()
        want = "%s (%s)" % (head, eight[13])
        self.assertIn("price feed: fetch failed (%s); " % want, err.getvalue())
        self.assertEqual(km._price_feed_status(NOW)["lastError"], want)
        self.assertEqual(km._version_info()["priceFeed"]["lastError"], want)
        self.assertNotIn("TESTHOST", err.getvalue(), "never the host")

    def test_a_worker_that_cannot_start_is_a_said_failure_not_a_stuck_inflight(self):
        """threading.Thread.start raising (a kernel at its thread limit) left attemptedAt and t stamped with inflight
        True and no worker to clear it, so the status read "nothing fetched yet" for the TTL's six hours while the
        exception escaped a function whose docstring says it never raises (into _model_prices and the /analytics
        handler's 500). The start is guarded: the state is said as a failure (lastError, the line), inflight is cleared,
        and the next TTL attempt is a new episode."""
        real_start = threading.Thread.start

        def exhausted(thread):
            if thread.name == "price-refresh":
                raise RuntimeError("can't start new thread")
            return real_start(thread)
        err, raised, prices = io.StringIO(), None, None
        with mock.patch.object(threading.Thread, "start", exhausted), redirect_stderr(err):
            try:
                prices = km._model_prices(NOW)                     # the cost view's road
            except Exception as e:                                 # caught to reach the assertions: the pre-fix shape raised here
                raised = e
        self.assertIsNone(raised, "the refresh never raises: a worker that cannot start is a failed fetch, said")
        self.assertEqual(prices["claude-fable-5-1"]["in"], 10e-6, "the build still served, from the defaults")
        log = err.getvalue()
        self.assertEqual(log.count(FAIL_LINE), 1, log)
        self.assertIn("price feed: fetch failed (RuntimeError), the worker thread did not start; " + SERVED_DEFAULTS, log)
        pf = km._price_feed_status(NOW)
        self.assertEqual((pf["source"], pf["reason"], pf["lastError"], pf["attemptedAt"]), ("defaults", "failed", "RuntimeError", NOW))
        self.assertEqual(self.calls, [], "nothing left the process")
        self.assertEqual(km._price_cache["t"], NOW, "stamped like any failed attempt: no hammering inside the TTL")
        km._refresh_remote_prices(NOW + km.PRICE_TTL)              # the next TTL attempt, with threads available again
        self._join()
        pf = km._price_feed_status(NOW + km.PRICE_TTL)
        self.assertEqual((pf["source"], pf["reason"], pf["lastError"], pf["rows"]), ("feed", None, None, 1), "a new episode, landed")

    def test_a_failed_refresh_after_a_landed_fetch_says_the_cached_rows_still_serve(self):
        """Stale-while-revalidate: a failed refresh leaves the landed rows in the cache, they keep pricing tokens, and
        the status says source feed. The failure line's tail used to say the built-in table served, a fixed phrase that
        was false here; the tail is read from the status now, so the line and the modal's line cannot disagree."""
        self._analytics()                                          # the fetch lands
        self.assertEqual(len(self.calls), 1)
        km._ANALYTICS_MEMO.clear()
        later = NOW + km.PRICE_TTL + 1800                          # six and a half hours on: the refresh is due, the host is down
        self.raise_with = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
        resp, log = self._analytics(now=later)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(log.count(FAIL_LINE), 1, log)
        self.assertIn("; the cost view prices tokens from the feed rows in memory for 1 of 6 models, fetched 6 h ago, and the "
                      "built-in defaults for the rest\n", log, "the tail words the same facts the modal does: the share the feed "
                      "priced, its age, the defaults for the rest (review round 2)")
        self.assertNotIn("from the built-in defaults\n", log, "the line never says the defaults serve the whole table here")
        pf = resp["priceFeed"]
        # the four fields below are the first landing's, which a failing re-attempt cannot change (it writes lastError
        # and the in-flight mark alone), so they hold on either ordering of the worker and the build's status read
        self.assertEqual((pf["source"], pf["rows"], pf["fetchedAt"], pf["ageS"]), ("feed", 1, NOW, km.PRICE_TTL + 1800))
        # the failure is read from the status after the join (the class docstring's rule): the payload above was built
        # while the re-attempt was in flight, and its lastError is None whenever the read came before the failure
        # landed, which free-threaded CPython or a slow worker gives (the review of PR 878: an AttributeError then)
        st = km._price_feed_status(later)
        self.assertIsNotNone(st["lastError"], "the re-attempt failed and its class is recorded")
        self.assertTrue(st["lastError"].startswith("URLError: ConnectionRefusedError"), st["lastError"])
        self.assertEqual(km._model_prices(later, refresh=False)["claude-fable-5-1"]["in"], 11e-6, "the cached row prices tokens, as the line says")


class LiveFeed(PriceFeedCase):
    """The status when the feed is on: not fetched yet at the view's first open, live with its fetch time and
    age on the click after the landing (a fresh build: the landing clears the memo), empty when the feed matches no
    built-in id, and a populated cache
    under off served with its age said."""

    def test_the_first_open_reads_inflight_and_the_click_after_the_landing_reads_live_from_a_fresh_build(self):
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
        self.assertEqual(km._ANALYTICS_MEMO[WINDOW]["t"], NOW + 5, "the landing invalidated the memo (review round 2): the click "
                         "after it builds fresh, so the figures beside the block are priced from the table the block names")
        pf2 = resp2["priceFeed"]
        self.assertEqual((pf2["source"], pf2["reason"], pf2["fetchedAt"], pf2["ageS"], pf2["rows"], pf2["lastError"]),
                         ("feed", None, NOW, 5, 1, None), "the status rides outside the memo, so the click after the fetch shows it")
        self.assertEqual(resp2["sessions"], resp1["sessions"], "no session discovered here, so the fresh build's figures equal the "
                         "first's; tests/test_price_feed_consistency.py prices a session through the two tables")
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
        self.assertEqual(pf.get("matched"), 0, "no row signed to a built-in id: a renamed feed, not a broken parser")
        self.assertEqual(pf.get("known"), len({km._price_sig(k) for k in km.DEFAULT_MODEL_PRICES if km._price_sig(k)}),
                         "the ids a feed row can sign to, the bound `rows` reads against for a partial match")
        self.assertGreaterEqual(pf["known"], pf["rows"])
        self.assertEqual(len(self.calls), 1)

    def test_rows_for_known_ids_that_do_not_parse_read_empty_with_the_matched_count_and_a_line(self):
        """A landed body whose rows for built-in ids carry unparseable rates (a schema move at the feed: rates renamed,
        nested or stringified) leaves the cache bare like a body naming no known id, and both read `empty`. They differ
        in `matched`, the ids the feed's rows signed to, parsed or not, so the view and /version can tell the parser
        broke from the feed renaming its ids; and a fetch that landed and left nothing usable says so once on stderr,
        as a failed one does."""
        self.body = json.dumps({"claude-fable-5-1": {"input_cost_per_token": "n/a", "output_cost_per_token": "n/a"},
                                "claude-opus-4-8": {"pricing": FEED["claude-fable-5-1"]}}).encode()
        resp, log = self._analytics()
        km._ANALYTICS_MEMO.clear()
        resp, log2 = self._analytics(now=NOW + 1)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["reason"], pf["rows"], pf.get("matched"), pf["fetchedAt"], pf["lastError"]),
                         ("defaults", "empty", 0, 2, NOW, None), "two rows signed to built-in ids and neither parsed")
        self.assertEqual(log.count("price feed: fetch landed with no usable row (2 signed to a built-in id, none parsed); "), 1, log)
        self.assertIn(SERVED_DEFAULTS, log)
        self.assertEqual(log2, "", "said once, at the fetch, not per build")
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("n/a", log + json.dumps(pf), "never the body")

    def test_a_rate_that_is_not_a_finite_number_is_a_rejected_row_never_a_cached_one(self):
        """JSON NaN and Infinity, which json.loads accepts, parse to floats: a feed row carrying one was cached as a live
        row, priced a session's cost as NaN, and the /analytics body then held a bare NaN token the browser's JSON
        parser rejects (the modal read `analytics unavailable`) while the status said live feed. The parse requires
        each of the four rates to be finite; a row that is not is rejected into the existing continue, so it counts in
        `matched` and not in `rows`, and the landing is said as one with no usable row. Red at the base of the PR at
        the cache assertion both heads share (the row was cached there)."""
        bodies = {"NaN input": '{"claude-fable-5-1": {"input_cost_per_token": NaN, "output_cost_per_token": 55e-6}}',
                  "Infinity output": '{"claude-fable-5-1": {"input_cost_per_token": 11e-6, "output_cost_per_token": Infinity}}',
                  "-Infinity cache read": '{"claude-fable-5-1": {"input_cost_per_token": 11e-6, "output_cost_per_token": 55e-6, '
                                          '"cache_read_input_token_cost": -Infinity}}'}
        for name, text in bodies.items():
            with self.subTest(rate=name):
                self.body = text.encode()
                km._price_cache.update(t=0, remote={})             # as stale as a cache gets: the next attempt fetches
                err = io.StringIO()
                with redirect_stderr(err):
                    km._refresh_remote_prices(NOW)
                    self._join()
                self.assertNotIn("claude-fable-5-1", km._price_cache["remote"], "a row whose rate is not finite is never cached")
                self.assertEqual(km._model_prices(NOW, refresh=False)["claude-fable-5-1"]["in"], 10e-6, "the default prices it")
                self.assertEqual(err.getvalue().count("price feed: fetch landed with no usable row (1 signed to a built-in id, "
                                                      "none parsed); "), 1, err.getvalue())
                st = km._price_feed_status(NOW)
                self.assertEqual((st["source"], st["reason"], st["rows"], st["matched"]), ("defaults", "empty", 0, 1),
                                 "signed to a built-in id and not parsed: the status tells the two apart")
                self.assertNotIn("NaN", json.dumps(km._version_info()["priceFeed"]) + json.dumps(km._model_prices(NOW, refresh=False)),
                                 "no NaN reaches a table or the block")

    def test_a_feed_row_whose_rates_are_plain_decimals_in_quotes_is_cached_at_those_numbers(self):
        """Round 3: the feed's four rates go through _price_rate_value, the read the override file's rates take, so a quoted
        plain decimal is read as that number and the row is cached and priced as live. A GUARD at this tree: the head's bare
        float() read these too, so it is green over the 2a5fc1dce archive; what moved is the arm's edge (the next case). The
        live feed sends numbers (the helper's docstring has the count), so this arm is belt and braces on this road."""
        self.body = json.dumps({"claude-fable-5-1": {"input_cost_per_token": "11e-6", "output_cost_per_token": "55e-6",
                                                     "cache_creation_input_token_cost": "13.75e-6",
                                                     "cache_read_input_token_cost": "1.1e-6"}}).encode()
        resp, log = self._analytics()
        self.assertEqual(km._price_cache["remote"]["claude-fable-5-1"], {"in": 11e-6, "out": 55e-6, "cache_w": 13.75e-6, "cache_r": 1.1e-6},
                         "each quoted plain decimal is read as the number it spells")
        st = km._price_feed_status(NOW)
        self.assertEqual((st["source"], st["reason"], st["rows"], st["matched"], st["lastError"]), ("feed", None, 1, 1, None), "live, whole")
        self.assertEqual(log, "", "a landing whose rows all parse says nothing")
        self.assertEqual(len(self.calls), 1)

    def test_a_feed_row_whose_quoted_rate_only_a_bare_float_would_read_is_a_rejected_row(self):
        """The edge of round 3's arm on the feed's road: a rate the strict read refuses makes the row unreadable, counted in
        `matched`, never cached, the default pricing that id and the landing said as one with no usable row. Red over the
        2a5fc1dce archive at the cache assertion for the shapes its bare float() read and cached: "1_0" as $10 a token, the
        padded and the plus-signed forms as 11e-6, true as $1 a token and false as $0, and "1_0" in the optional cache key.
        "inf", "nan" and "1e999" were that head's finite check's already, and "", "abc", null, a list and an object raised in
        its float(): guards. Each shape is its own fetch (the cache reset to stale), and each landing is said once."""
        shapes = {"1_0": "1_0", "padded": " 11e-6", "trailing": "11e-6 ", "plus": "+11e-6", "inf": "inf", "nan": "nan",
                  "1e999": "1e999", "empty": "", "text": "abc", "true": True, "false": False, "null": None, "list": [], "object": {}}
        for name, value in shapes.items():
            with self.subTest(rate=name):
                self.body = json.dumps({"claude-fable-5-1": {"input_cost_per_token": value, "output_cost_per_token": 55e-6}}).encode()
                self._refresh_once_and_assert_rejected()
        with self.subTest(rate="1_0 in the optional cache key"):
            self.body = json.dumps({"claude-fable-5-1": {"input_cost_per_token": 11e-6, "output_cost_per_token": 55e-6,
                                                         "cache_read_input_token_cost": "1_0"}}).encode()
            self._refresh_once_and_assert_rejected()

    def _refresh_once_and_assert_rejected(self):
        """One fetch of self.body from a stale cache: the one row it names signs to claude-fable-5-1 and does not parse."""
        km._price_cache.update(t=0, remote={})             # as stale as a cache gets: the next attempt fetches
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)
            self._join()
        self.assertNotIn("claude-fable-5-1", km._price_cache["remote"], "a row whose rate the strict read refuses is never cached")
        self.assertEqual(km._model_prices(NOW, refresh=False)["claude-fable-5-1"]["in"], 10e-6, "the default prices it")
        self.assertEqual(err.getvalue().count("price feed: fetch landed with no usable row (1 signed to a built-in id, "
                                              "none parsed); "), 1, err.getvalue())
        st = km._price_feed_status(NOW)
        self.assertEqual((st["source"], st["reason"], st["rows"], st["matched"]), ("defaults", "empty", 0, 1),
                         "signed to a built-in id and not parsed: the status tells the two apart")

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
        self.assertIn(OFF_LINE + "; the cost view prices tokens from the feed rows in memory for 1 of 6 models, fetched 2 h ago, "
                      "and the built-in defaults for the rest\n", log,
                      "the off line's tail names what serves: the cached row for one of six models with its age and the defaults "
                      "for the rest, not a fixed phrase about the defaults alone")
        self.assertNotIn("from the built-in defaults\n", log, "the line never says the defaults serve the whole table here")

    def test_an_age_of_thirty_days_is_said_in_days(self):
        """The tail's age had three arms (s, min, h) and counted hours without end, so a month-old cache read `fetched
        720 h ago` in the log where the modal's line, through the webview's one age helper, says 30 days ago; the day
        arm at 24 h makes the two agree on the unit. Red over the 3ddaf64d8 archive at the text (720 h there)."""
        self._analytics()                                          # a fetch landed while the feed was on
        os.environ["ROMP_PRICE_FEED"] = "off"
        km._ANALYTICS_MEMO.clear()
        resp, log = self._analytics(now=NOW + 30 * 86400)
        self.assertIn(OFF_LINE + "; the cost view prices tokens from the feed rows in memory for 1 of 6 models, fetched 30 d ago, "
                      "and the built-in defaults for the rest\n", log, log)
        self.assertNotIn(" h ago", log, "past 24 h the unit is days, as the modal's line has it")
        self.assertEqual(resp["priceFeed"]["ageS"], 30 * 86400, "the block carries the seconds; the words are the line's")
        err = io.StringIO()
        with redirect_stderr(err):
            km._price_feed_line(NOW + 86400, "price feed: probe")   # the boundary: 24 h is the first day
            km._price_feed_line(NOW + 86399, "price feed: probe")   # a second short of it is still hours
        self.assertIn("fetched 1 d ago", err.getvalue(), err.getvalue())
        self.assertIn("fetched 23 h ago", err.getvalue(), err.getvalue())

    def test_an_override_row_is_counted_in_the_status_and_the_line(self):
        """The table's third layer: a row in PRICE_CONFIG (~/.config/romp/model-prices.json) wins over the feed and the
        defaults, and the reference tells a person with the feed off to keep a rate current there. A status that knew
        only the feed and the defaults read `defaults, off` while the user's row priced the dollars, so the modal's line
        said the built-in defaults served when they did not. `overrides` counts the ids the file changed or added,
        derived from the merge itself against the defaults under the cached rows, and the lines' tail says so."""
        self.assertEqual(km._price_feed_status(NOW).get("overrides"), 0, "no file: nothing overridden")
        km.PRICE_CONFIG.write_text(json.dumps({
            "claude-fable-5-1": {"in": 99e-6, "out": 99e-6, "cache_w": 99e-6, "cache_r": 99e-6},   # changed
            "claude-opus-4-8": km.DEFAULT_MODEL_PRICES["claude-opus-4-8"]}))                        # equal to the default
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["reason"], pf.get("overrides")), ("defaults", "off", 1),
                         "one row changed the table; a row equal to the default is not an override")
        self.assertEqual(km._model_prices(NOW)["claude-fable-5-1"]["in"], 99e-6, "the row is what prices tokens")
        self.assertIn(OFF_LINE + "; the cost view prices tokens from the built-in defaults, 1 row overridden by model-prices.json\n", log)
        self.assertEqual(km._version_info()["priceFeed"]["overrides"], 1, "/version carries the count too")
        self.assertNotIn(str(km.PRICE_CONFIG.parent), log + json.dumps(pf), "a count, never the path")
        self.assertEqual(self.calls, [])
        os.environ.pop("ROMP_PRICE_FEED", None)                    # beside a landed feed the count is against the cached rows
        km._ANALYTICS_MEMO.clear()
        resp, log = self._analytics(now=NOW + 1)                   # this build starts the case's first fetch (off stamped nothing)
        pf = self._settled(NOW + 1)                                # the landing, read after the join at the same `now`, never
        #                                                            from the payload of the build that started the fetch
        self.assertEqual((pf["source"], pf["rows"], pf["overrides"]), ("feed", 1, 1), "the user's row still differs from the feed's")
        self.assertEqual(km._model_prices(NOW + 1)["claude-fable-5-1"]["in"], 99e-6, "and still wins")
        self.assertEqual(len(self.calls), 1)


class TheOverrideFileIsSaid(PriceFeedCase):
    """The reference sends a feed-off box to ~/.config/romp/model-prices.json. Until the review of PR 878 a row the kernel
    could not read was silent: a non-object row was skipped without a word and a rate that was no number raised out of
    the loop, so the block counted the rows before it and stderr said nothing. The review's first round wrapped the
    whole loop in one try, which voided the bad row and every row after it; the re-ruling (2026-09-21) rejected that
    too, because the blast radius depended on POSITION (the same bad row first voided the whole file and last voided
    nothing), and ruled the shape the unrecognised switch value has: reject the malformed ROW alone, keep every other
    row, and say so loudly, the stderr line naming the row (its key by repr, clipped as that line clips the value) and
    saying the rest of the file applies, the block carrying the FACT and never a key (`overrideFault` "row" and the
    count `overrideRowsRejected`; the block rides the auth-exempt /version), and the modal's line a clause from the
    count (ui/webview/analytics-price-source-states.test.ts). A file that cannot be read or parsed as a JSON object is
    still ignored whole and classed "file". The re-ruling's second delta split the say-once latch by fault class
    (`overrideFileSaid`; `overrideRowsSaid`, keyed by row): one latch across both classes let the first fault of either
    silence the other class's first for the kernel's life. Both facts travel on the merged table (_PriceTable), so the
    block reports the merge it counts overrides from; the lines are written on the cost view's road outside every lock.
    Each case names its red over a git archive of 5cbf9e397 (the head before the re-ruling), where it has one."""

    GOOD_1 = ("claude-fable-5-1", {"in": 12e-6, "out": 60e-6, "cache_w": 15e-6, "cache_r": 1.2e-6})
    GOOD_2 = ("claude-sonnet-5", {"in": 4e-6, "out": 20e-6})
    BAD = ("claude-opus-4-8", {"in": "twelve dollars", "out": 30e-6})   # a rate that is no number

    def _rows(self, position):
        """Two good rows and the bad one at `position` (0 first, 1 middle, 2 last); json.dumps keeps the order."""
        rows = [self.GOOD_1, self.GOOD_2]
        rows.insert(position, self.BAD)
        return json.dumps(dict(rows))

    def _assert_skipped_alone(self, pf, log):
        """The ruling's shape, asserted in the order that names the red: the table first (both good rows apply, the bad one
        alone is the default), then the block's count and class, then the line naming the key with the rest-applies
        consequence and the tail every price feed line carries. Returns the merged table."""
        prices = km._model_prices(NOW, refresh=False)
        self.assertEqual(prices["claude-fable-5-1"]["in"], 12e-6, "a good row applies")
        self.assertEqual(prices["claude-sonnet-5"]["in"], 4e-6, "and so does the other good row, wherever the bad row sits")
        self.assertEqual(prices["claude-opus-4-8"], km.DEFAULT_MODEL_PRICES["claude-opus-4-8"], "the bad row alone is skipped")
        self.assertEqual(pf.get("overrideRowsRejected"), 1, "the block counts the skipped row")
        self.assertEqual((pf.get("overrideFault"), pf["overrides"]), ("row", 2), "the class, and the count of rows in effect")
        self.assertEqual(log.count(ROW_LINE % "'claude-opus-4-8'"), 1, "the line names the row's key and says the rest applies:\n" + log)
        self.assertIn(ROW_LINE % "'claude-opus-4-8'" + "; the cost view prices tokens from the built-in defaults, 2 rows overridden "
                      "by model-prices.json\n", log, "the consequence, then the tail every price feed line carries")
        return prices

    def test_a_bad_row_first_is_skipped_alone_and_both_rows_after_it_apply(self):
        """The red-before subject: over the 5cbf9e397 archive one try wrapped the loop, so a bad row FIRST voided both good
        rows, and the first table assertion reads the default 10e-6 for claude-fable-5-1 where 12e-6 is expected. The table
        is asserted before the count so the red is for the void and not for the key the archive lacks."""
        km.PRICE_CONFIG.write_text(self._rows(0))
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        pf = resp["priceFeed"]
        self._assert_skipped_alone(pf, log)
        self.assertEqual(km._version_info()["priceFeed"]["overrideRowsRejected"], 1, "/version carries the count")
        self.assertEqual(km._version_info()["priceFeed"]["overrideFault"], "row", "and the class")
        self.assertNotIn(str(km.PRICE_CONFIG.parent), log + json.dumps(pf), "a class and a count, never the path")
        self.assertNotIn("twelve dollars", log + json.dumps(pf), "never the file's values")
        self.assertNotIn("claude-opus-4-8", json.dumps(pf), "the key is in the kernel's own log and not in the block")
        km._ANALYTICS_MEMO.clear()
        resp2, log2 = self._analytics(now=NOW + 1)
        self.assertEqual((resp2["priceFeed"]["overrideFault"], resp2["priceFeed"]["overrideRowsRejected"]), ("row", 1),
                         "the block says it on every build")
        self.assertEqual(log2, "", "the row is named once per kernel life, not per build")

    def test_the_same_bad_row_last_or_in_the_middle_yields_the_table_count_and_line_the_first_position_does(self):
        """Position independence, the property the ruling named: the same malformed row last, in the middle or first yields
        the same table (every other row applied), the same count and the same line. The row latch is reset between
        placements so each placement writes its line. Over the 5cbf9e397 archive the LAST placement, run first here, is
        green at the table by accident (the good rows precede the bad one, and the void after it voids nothing) and red at
        the count (the block there has no overrideRowsRejected key: None != 1); the first-position case above carries the
        red for the table. This case is the property pin."""
        os.environ["ROMP_PRICE_FEED"] = "off"
        seen = []
        for position, where in ((2, "last"), (1, "middle"), (0, "first")):
            km.PRICE_CONFIG.write_text(self._rows(position))
            km._ANALYTICS_MEMO.clear()
            km._price_feed["overrideRowsSaid"] = frozenset()      # the say-once latch, reset so this placement's line is written
            resp, log = self._analytics()
            with self.subTest(where):
                prices = self._assert_skipped_alone(resp["priceFeed"], log)
                seen.append((json.dumps(prices, sort_keys=True), resp["priceFeed"]["overrideRowsRejected"], resp["priceFeed"]["overrides"]))
        self.assertEqual(len(seen), 3, "three placements ran")
        self.assertEqual(len(set(seen)), 1, "three placements, one table and one count: %r" % (seen,))

    def test_two_bad_rows_are_each_named_once_and_counted_as_two_and_a_row_that_goes_bad_later_is_named_too(self):
        """The row latch is per ROW KEY, not one boolean for the class: two bad rows in one file are two lines, each named
        once, and a count of 2; a second build says nothing new; a row that goes bad in a later edit (a new key) is named
        when first seen, while the rows already named are not named again, and the count follows the file. Over the
        5cbf9e397 archive the first bad row voids the good row after it: red at the table's first assertion."""
        os.environ["ROMP_PRICE_FEED"] = "off"
        km.PRICE_CONFIG.write_text(json.dumps({"note": "my rates", "claude-fable-5-1": {"in": 12e-6}, "claude-sonnet-5": None}))
        resp, log = self._analytics()
        prices = km._model_prices(NOW, refresh=False)
        self.assertEqual(prices["claude-fable-5-1"]["in"], 12e-6, "the good row between two bad ones applies")
        self.assertEqual(prices["claude-sonnet-5"], km.DEFAULT_MODEL_PRICES["claude-sonnet-5"], "a null row is skipped")
        self.assertNotIn("note", prices)
        self.assertEqual((resp["priceFeed"]["overrideFault"], resp["priceFeed"]["overrideRowsRejected"], resp["priceFeed"]["overrides"]),
                         ("row", 2, 1))
        tail = "; the cost view prices tokens from the built-in defaults, 1 row overridden by model-prices.json\n"
        self.assertEqual((log.count(ROW_LINE % "'note'" + tail), log.count(ROW_LINE % "'claude-sonnet-5'" + tail)), (1, 1),
                         "one line per row, each with the tail that counts the one row in effect:\n" + log)
        self.assertEqual(log.count("2 rows overridden"), 0, "the tail counts the rows in effect, never the rows in the file")
        km._ANALYTICS_MEMO.clear()
        _, log2 = self._analytics(now=NOW + 1)
        self.assertEqual(log2, "", "nothing new to say")
        km.PRICE_CONFIG.write_text(json.dumps({"note": "my rates", "claude-fable-5-1": {"in": 12e-6}, "claude-sonnet-5": None,
                                               "claude-haiku-4-5-20251001": "cheap"}))
        km._ANALYTICS_MEMO.clear()
        resp3, log3 = self._analytics(now=NOW + 2)
        self.assertEqual(resp3["priceFeed"]["overrideRowsRejected"], 3, "the count follows the file")
        self.assertEqual(log3.count("in model-prices.json could not be read"), 1, "one new row, one new line:\n" + log3)
        self.assertEqual(log3.count(ROW_LINE % "'claude-haiku-4-5-20251001'"), 1)
        self.assertEqual(km._price_feed["overrideRowsSaid"], frozenset({"note", "claude-sonnet-5", "claude-haiku-4-5-20251001"}))

    def test_a_long_row_key_is_clipped_in_the_line_as_the_switch_value_is(self):
        """The key by repr through the same 40-character clip the unrecognised line gives the switch's value (37 characters
        and an ellipsis), so a pasted paragraph as a key is one bounded line in the kernel's log."""
        key = "claude-" + "x" * 60
        km.PRICE_CONFIG.write_text(json.dumps({key: "not a row"}))
        os.environ["ROMP_PRICE_FEED"] = "off"
        _, log = self._analytics()
        clipped = repr(key)[:37] + "..."
        self.assertEqual(len(clipped), 40)
        self.assertEqual(log.count(ROW_LINE % clipped), 1, log)
        self.assertNotIn(repr(key), log, "never the whole key")

    def test_each_fault_class_is_said_once_the_file_fault_then_a_row_fault(self):
        """The re-ruling's second delta: one latch per fault class. A file the kernel cannot parse is said; the file is then
        rewritten with one bad row, and that row is said too: two lines, one per class, each build's block carrying its
        own merge's class and count (the block is the fact of the very merge it describes, so it reads "file" with 0 and
        then "row" with 1, never both at once). Over the 5cbf9e397 archive one latch spanned both classes, so the row
        line is never written: red at its count (0 != 1). The file line's text is the same at both heads, so the red is
        the second class's."""
        os.environ["ROMP_PRICE_FEED"] = "off"
        km.PRICE_CONFIG.write_text("{not json")
        resp, log = self._analytics()
        self.assertEqual(resp["priceFeed"]["overrideFault"], "file")
        self.assertEqual(log.count(FILE_LINE), 1, log)
        km.PRICE_CONFIG.write_text(json.dumps({"note": "my rates", "claude-fable-5-1": {"in": 12e-6}}))
        km._ANALYTICS_MEMO.clear()
        resp2, log2 = self._analytics(now=NOW + 1)
        self.assertEqual(log2.count(ROW_LINE % "'note'"), 1, "the second class's first fault is said, on its own latch:\n" + log2)
        self.assertEqual(log2.count(FILE_LINE), 0, "the file line is not said again")
        self.assertEqual((resp["priceFeed"]["overrideRowsRejected"], resp2["priceFeed"]["overrideFault"], resp2["priceFeed"]["overrideRowsRejected"]),
                         (0, "row", 1), "each block carries its own merge's class and count")
        self.assertEqual(km._model_prices(NOW, refresh=False)["claude-fable-5-1"]["in"], 12e-6, "the good row applies")
        self.assertEqual((km._price_feed["overrideFileSaid"], km._price_feed["overrideRowsSaid"]), (True, frozenset({"note"})),
                         "the two latches, one per class, the row's keyed by row")
        km._ANALYTICS_MEMO.clear()
        _, log3 = self._analytics(now=NOW + 2)
        self.assertEqual(log3, "", "both said once")

    def test_each_fault_class_is_said_once_a_row_fault_then_the_file_fault(self):
        """The other order: a bad row is said, then the file is rewritten as a JSON list, and the file class is said too.
        The first check counts a phrase both heads' row lines carry, so over the 5cbf9e397 archive the red is at the
        second class's line count (0 != 1), the file fault silenced by the row fault's latch."""
        os.environ["ROMP_PRICE_FEED"] = "off"
        km.PRICE_CONFIG.write_text(json.dumps({"note": "my rates", "claude-fable-5-1": {"in": 12e-6}}))
        resp, log = self._analytics()
        self.assertEqual(resp["priceFeed"]["overrideFault"], "row")
        self.assertEqual(log.count("in model-prices.json could not be read"), 1, log)
        km.PRICE_CONFIG.write_text("[1, 2]")
        km._ANALYTICS_MEMO.clear()
        resp2, log2 = self._analytics(now=NOW + 1)
        self.assertEqual(log2.count(FILE_LINE), 1, "the file class's first fault is said, on its own latch:\n" + log2)
        self.assertEqual(log2.count("in model-prices.json could not be read"), 0, "the row line is not said again")
        self.assertEqual((resp2["priceFeed"]["overrideFault"], resp2["priceFeed"]["overrideRowsRejected"]), ("file", 0))
        self.assertEqual(log2.count(ROW_LINE % "'note'"), 0)

    def test_a_row_that_is_not_an_object_is_skipped_too(self):
        """A row that is not an object (a comment string, a null): the base skipped it silently with the rows after it
        kept, the round rejected it with every row after it, and now it is skipped alone and said like any other bad row,
        so the documented rule has one shape. Over the 5cbf9e397 archive the row after it is voided: red at the table."""
        km.PRICE_CONFIG.write_text(json.dumps({"claude-fable-5-1": {"in": 12e-6, "out": 60e-6, "cache_w": 15e-6, "cache_r": 1.2e-6},
                                               "note": "my rates", "claude-sonnet-5": {"in": 4e-6, "out": 20e-6}}))
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        prices = km._model_prices(NOW, refresh=False)
        self.assertEqual((prices["claude-fable-5-1"]["in"], prices["claude-sonnet-5"]["in"]), (12e-6, 4e-6), "both object rows apply")
        self.assertNotIn("note", prices)
        self.assertEqual((resp["priceFeed"].get("overrideFault"), resp["priceFeed"].get("overrideRowsRejected")), ("row", 1))
        self.assertEqual(log.count(ROW_LINE % "'note'"), 1, log)
        self.assertNotIn("my rates", log + json.dumps(resp["priceFeed"]), "never the file's values")

    def test_an_override_row_with_a_rate_that_is_not_finite_is_skipped_and_classed(self):
        """The class rule's other parse: JSON NaN in the user's own file (a rate that is not a finite number) is a row the
        kernel cannot read, not a row that prices a session at NaN; the block says which and counts it."""
        km.PRICE_CONFIG.write_text('{"claude-fable-5-1": {"in": NaN, "out": 55e-6, "cache_w": 1e-6, "cache_r": 1e-6}}')
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        pf = resp["priceFeed"]
        self.assertEqual(pf.get("overrideFault"), "row", "a rate that is not a finite number is a row the kernel cannot read")
        self.assertEqual(km._model_prices(NOW, refresh=False)["claude-fable-5-1"]["in"], 10e-6, "the row is skipped: the table's rate stands")
        self.assertEqual((pf["overrides"], pf.get("overrideRowsRejected")), (0, 1))
        self.assertEqual(log.count(ROW_LINE % "'claude-fable-5-1'"), 1, log)

    def _rate_present_and_not_a_number(self, shape):
        """Round 2 of the review: a rate whose key is PRESENT and whose value is not a JSON number (`shape` is the JSON text
        of the value) is a rejected row like a non-object row or a non-finite rate, never a coerced one. Until then
        `float(x or 0)` priced null, an empty string, a list, an object and false at 0.0 per token and true at 1.0 (a dollar
        a token), and a numeric string parsed, while the block read a clean override and stderr said nothing. Asserted in
        the order that names the red over the 84b27dd39 archive, where the coercion is the base's and no block, no fault
        class and no line exist: the merged rate first (0.0, 1.0 or the string's number there, where the table's rate is
        expected), then the block's class and count and the line, through .get so the archive reads None at them."""
        km.PRICE_CONFIG.write_text('{"claude-fable-5-1": {"in": %s}}' % shape)
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        prices = km._model_prices(NOW, refresh=False)
        table = km.DEFAULT_MODEL_PRICES["claude-fable-5-1"]
        self.assertEqual(prices["claude-fable-5-1"]["in"], table["in"],
                         "a rate that is present and not a number is a rejected row: the table's rate stands, never a coerced one")
        self.assertEqual(prices["claude-fable-5-1"], table, "the whole row is the table's")
        pf = resp.get("priceFeed") or {}
        self.assertEqual((pf.get("overrideFault"), pf.get("overrideRowsRejected"), pf.get("overrides")), ("row", 1, 0),
                         "the block classes and counts it like any other unreadable row, and counts no override in effect")
        self.assertEqual(log.count(ROW_LINE % "'claude-fable-5-1'"), 1, "and the row is named once on stderr:\n" + log)

    def test_a_rate_that_is_null_is_a_rejected_row_never_a_zero_rate(self):
        self._rate_present_and_not_a_number("null")

    def test_a_rate_that_is_an_empty_string_is_a_rejected_row_never_a_zero_rate(self):
        self._rate_present_and_not_a_number('""')

    def test_a_rate_that_is_a_list_is_a_rejected_row_never_a_zero_rate(self):
        self._rate_present_and_not_a_number("[]")

    def test_a_rate_that_is_an_object_is_a_rejected_row_never_a_zero_rate(self):
        self._rate_present_and_not_a_number("{}")

    def test_a_rate_that_is_false_is_a_rejected_row_never_a_zero_rate(self):
        self._rate_present_and_not_a_number("false")

    def test_a_rate_that_is_true_is_a_rejected_row_never_a_dollar_a_token(self):
        self._rate_present_and_not_a_number("true")

    def _reset_for_the_next_shape(self):
        """Between two shapes in one case: a fresh memo (the build would serve the last shape's payload) and a fresh row latch
        (the row's key is the same, so its line would be said once for the whole loop). Both keys exist at every head the
        loops below run over except the base archive, where the status dict is absent (guarded as setUp guards it)."""
        km._ANALYTICS_MEMO.clear()
        feed = getattr(km, "_price_feed", None)
        if feed is not None:
            feed["overrideRowsSaid"] = frozenset()

    def test_a_rate_written_as_a_plain_decimal_in_quotes_is_read_as_that_number(self):
        """Round 3 of the review re-ruled the string. "0.5" was accepted at both earlier heads and round 2 refused it outright, a
        regression, so a string that is a plain decimal WHOLE (an optional minus, digits, at most one dot with digits after it,
        an optional exponent, nothing else) is read as that number through _price_rate_value's strict parse, never through the
        bare float() that also read " 0.5" and "1_0" (the next case). The row is an override in effect; nothing is classed,
        counted or said. Red over the 2a5fc1dce archive at the merged rate (the table's 10e-6 there, the row rejected). Over the
        84b27dd39 archive the first assertion passes (the base's float() read the string too) and the case reds off its subject
        at the omitted rates, the base fetching the feed so its table is the feed row's: no evidence there either way."""
        shapes = {'"0.5"': 0.5, '"3e-06"': 3e-06, '"1E5"': 100000.0, '"10"': 10.0, '"-0.5"': -0.5, '"007"': 7.0}
        os.environ["ROMP_PRICE_FEED"] = "off"
        for shape, value in shapes.items():
            with self.subTest(shape=shape):
                self._reset_for_the_next_shape()
                km.PRICE_CONFIG.write_text('{"claude-fable-5-1": {"in": %s}}' % shape)
                resp, log = self._analytics()
                prices = km._model_prices(NOW, refresh=False)
                self.assertEqual(prices["claude-fable-5-1"]["in"], value, "a plain decimal in quotes is read as that number (round 3)")
                self.assertEqual(prices["claude-fable-5-1"]["out"], km.DEFAULT_MODEL_PRICES["claude-fable-5-1"]["out"],
                                 "the rates the row omits are the table's, as for any override row")
                pf = resp.get("priceFeed") or {}
                self.assertEqual((pf.get("overrideFault"), pf.get("overrideRowsRejected"), pf.get("overrides")), (None, 0, 1),
                                 "an override in effect: nothing classed, nothing counted as skipped")
                self.assertEqual(log.count("in model-prices.json could not be read"), 0, "and nothing said:\n" + log)

    def test_a_quoted_rate_that_only_a_bare_float_would_read_is_a_rejected_row(self):
        """The other edge of round 3's predicate, the reason a bare float() was not restored: every string float() reads that is
        not a plain decimal whole is the row road's report. "inf", "-inf" and "nan" (float reads them as such), "1e999" (reads
        as inf), whitespace either side and a trailing newline, an underscore separator ("1_0" reads as 10.0), a leading plus
        (refused by the decision _price_rate_value's docstring states: JSON's grammar has none), a bare dot either side, an
        empty string, text and hex. Guards at this tree against the arm widening, green over the 2a5fc1dce archive (every
        string was refused there); with the strict-form check cut out of _price_rate_value (a mutant that reads every string
        with float()) the seven shapes only that check refuses go red ("1_0", the three padded forms, "+0.5", ".5", "5.") and
        the other seven stay green as the finite check's or float()'s own refusals; red over the 84b27dd39 archive at the merged rate for the twelve shapes `float(x or 0)` read
        (10.0 for "1_0", 0.5 for the padded, newline-tailed, plus-signed and bare-dot forms, 5.0 for "5.", inf, -inf and nan
        cached as rates, inf for "1e999", 0.0 for ""); "abc" and "0x10" red there off their subject, the base fetching the
        feed so its table is the feed row's."""
        shapes = ('"1_0"', '" 0.5"', '"0.5 "', '"0.5\\n"', '"inf"', '"-inf"', '"nan"', '"1e999"', '"+0.5"', '""', '"abc"',
                  '".5"', '"5."', '"0x10"')
        for shape in shapes:
            with self.subTest(shape=shape):
                self._reset_for_the_next_shape()
                self._rate_present_and_not_a_number(shape)

    def test_control_an_absent_rate_key_inherits_the_tables_rate_and_is_no_fault(self):
        """The other side of the predicate: a rate whose KEY is absent takes the table's rate for an id the table names
        (APartialOverrideRow pins the base resolution), the row is an override in effect, and nothing is classed, counted
        or said. A GUARD, green at the tree and no red-before evidence for anything: over the 84b27dd39 archive it reds
        for reasons that are not its subject (the base has no off switch, so the build fetches and the inherited rate is
        the feed row's 1.1e-05, the table's rate there too; and the block's keys are absent)."""
        km.PRICE_CONFIG.write_text(json.dumps({"claude-fable-5-1": {"out": 6e-05}}))
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        prices = km._model_prices(NOW, refresh=False)
        self.assertEqual((prices["claude-fable-5-1"]["in"], prices["claude-fable-5-1"]["out"]), (10e-6, 6e-05),
                         "in inherited from the table, out the row's")
        pf = resp.get("priceFeed") or {}
        self.assertEqual((pf.get("overrideFault"), pf.get("overrideRowsRejected"), pf.get("overrides")), (None, 0, 1))
        self.assertEqual(log.count("in model-prices.json could not be read"), 0, log)

    def test_a_file_that_is_not_a_json_object_is_ignored_whole_and_classed_file(self):
        km.PRICE_CONFIG.write_text("{not json")
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        self.assertEqual(resp["priceFeed"].get("overrideFault"), "file", "exists and cannot be parsed: the file's class")
        self.assertEqual(resp["priceFeed"].get("overrideRowsRejected"), 0, "no row was read, so none was skipped: the count is 0")
        self.assertEqual(km._model_prices(NOW, refresh=False)["claude-fable-5-1"]["in"], 10e-6, "ignored whole")
        self.assertEqual(log.count(FILE_LINE + "; "), 1, log)
        self.assertEqual(km._version_info()["priceFeed"].get("overrideFault"), "file")
        km.PRICE_CONFIG.write_text("[1, 2]")                       # parses, but is not a table of rows: the same class
        km._ANALYTICS_MEMO.clear()
        resp, log2 = self._analytics(now=NOW + 1)
        self.assertEqual(resp["priceFeed"].get("overrideFault"), "file")
        self.assertEqual(log2, "", "said once per kernel life")

    def test_no_file_is_no_fault_and_no_line(self):
        """No file is no fault, no skipped row and nothing said, and both keys are present on every build. At the head before
        the fault class the class key did not exist, and at 5cbf9e397 the count key did not: the red over either archive is
        a key's absence at its presence assertion, the subject being the new API and named as such; the no-fault, zero-count
        and no-line assertions after it are guards that hold at either head."""
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        self.assertIn("overrideFault", resp["priceFeed"], "the key is always present")
        self.assertIn("overrideRowsRejected", resp["priceFeed"], "so is the count")
        self.assertIsNone(resp["priceFeed"]["overrideFault"], "no file: nothing to class")
        self.assertEqual(resp["priceFeed"]["overrideRowsRejected"], 0, "no file: nothing skipped")
        self.assertNotIn("model-prices.json could not", log)
        self.assertEqual(log.count("in model-prices.json"), 0)
        self.assertIsNone(km._version_info()["priceFeed"]["overrideFault"])
        self.assertEqual(km._version_info()["priceFeed"]["overrideRowsRejected"], 0)


class APartialOverrideRow(PriceFeedCase):
    """What a row in ~/.config/romp/model-prices.json that omits a rate inherits, as the reference states it since the
    review of PR 878: the table's rate for an id the table itself names (`base` is that id's row), and zero for any
    other id (a dated id, an added model), because the merge resolves `base` by the exact id and never through
    _price_for's signature or family fallback; the row then exists under its exact id, so _price_for finds it there and
    the fallbacks that would have reached another row never run. A GUARD on behaviour that predates the PR (green at
    its base and at the reviewed head), proven by mutation: `base` resolved through `_price_for(k, prices) or {}` in a
    scratch copy reds the second assertion. The ruling took the prose branch; the base resolution is unchanged."""

    def test_an_omitted_rate_keeps_the_tables_only_for_an_id_the_table_names(self):
        km.PRICE_CONFIG.write_text(json.dumps({"claude-fable-5-1": {"in": 12e-6}, "claude-opus-5": {"in": 6e-6}}))
        prices = km._model_prices(NOW, refresh=False)              # the merge alone: no fetch on either head
        named = prices["claude-fable-5-1"]
        self.assertEqual((named["in"], named["out"], named["cache_w"], named["cache_r"]),
                         (12e-6, 50e-6, 12.5e-6, 0.25e-6), "an id the table names: the omitted rates are that row's")
        other = prices["claude-opus-5"]
        self.assertEqual((other["in"], other["out"], other["cache_w"], other["cache_r"]), (6e-6, 0.0, 0.0, 0.0),
                         "an id the table does not name: the omitted rates are zero, not any opus row's")
        self.assertIs(km._price_for("claude-opus-5", prices), other,
                      "the row is found by its exact id, so the signature and family fallbacks (which would reach claude-opus-4-8's row) never run")
        self.assertEqual(km._price_for("claude-opus-5", prices)["out"], 0.0)


class ReattemptKeepsTheEarlierResult(PriceFeedCase):
    """A landed or failed fetch outranks a fetch in flight (review round 1): the TTL re-attempt's payload says what
    the table is priced from and why, not that a fetch is under way, which after a result would hide it for the
    seconds the new worker runs. "inflight" is exactly the state with no result yet, the view's first open. The two
    re-attempt cases are red over the tree before the reorder; the first-open case is a CONTROL, green there by
    design, pinning the one state the reorder must leave alone, so it is no red-before evidence for anything."""

    def _reattempt(self):
        km._ANALYTICS_MEMO.clear()
        self.gate = threading.Event()                              # the re-attempt's worker parks inside urlopen
        self.addCleanup(self.gate.set)
        t2 = NOW + km.PRICE_TTL
        resp = km._token_analytics(t2, WINDOW)                     # built while the worker is parked
        pf = dict(resp["priceFeed"])
        alive = any(t.name == "price-refresh" and t.is_alive() for t in threading.enumerate())
        self.gate.set()
        self._join()
        return pf, alive, t2

    def test_after_a_failed_fetch_the_reattempt_reads_failed_while_in_flight(self):
        self.raise_with = urllib.error.HTTPError(km.PRICE_FEED_URL, 500, "Internal Server Error", {}, None)
        with redirect_stderr(io.StringIO()):
            km._token_analytics(NOW, WINDOW)
            self._join()
            pf, alive, t2 = self._reattempt()
        self.assertEqual(len(self.calls), 2, "the TTL passed: a second fetch started")
        self.assertTrue(alive, "the payload was built while the re-attempt was in flight")
        self.assertEqual((pf["source"], pf["reason"], pf["lastError"], pf["attemptedAt"]),
                         ("defaults", "failed", "HTTPError: HTTP 500", t2),
                         "a re-attempt in flight keeps the earlier failure as the reason; inflight is for a kernel with no result yet")

    def test_after_a_landed_empty_fetch_the_reattempt_reads_empty_while_in_flight(self):
        self.body = json.dumps({"some-other-vendor-model": FEED["some-other-vendor-model"]}).encode()
        with redirect_stderr(io.StringIO()):
            km._token_analytics(NOW, WINDOW)
            self._join()
            pf, alive, t2 = self._reattempt()
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(alive)
        self.assertEqual((pf["source"], pf["reason"], pf["fetchedAt"], pf["ageS"], pf["rows"]),
                         ("defaults", "empty", NOW, km.PRICE_TTL, 0),
                         "a fetch landed six hours ago and matched nothing: that is the reason, not inflight")

    def test_control_the_first_open_of_a_fresh_kernel_still_reads_inflight(self):
        self.gate = threading.Event()
        self.addCleanup(self.gate.set)
        with redirect_stderr(io.StringIO()):
            resp = km._token_analytics(NOW, WINDOW)
            pf = dict(resp["priceFeed"])
            self.gate.set()
            self._join()
        self.assertEqual((pf["source"], pf["reason"], pf["fetchedAt"], pf["lastError"]), ("defaults", "inflight", None, None),
                         "no result yet and a fetch under way: inflight, before and after the reorder")


class TheBlockCountsTheTable(PriceFeedCase):
    """`known`: how many built-in ids the feed is matched against, beside `rows`, the ids it matched, so the view can
    say a feed that matched some of them prices those and no more (review round 1)."""

    def test_the_block_carries_known_beside_rows_and_a_partial_feed_prices_the_rest_from_the_defaults(self):
        self._analytics()                                          # FEED signs to one of the built-in ids
        km._ANALYTICS_MEMO.clear()
        resp, _ = self._analytics(now=NOW + 1)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["rows"]), ("feed", 1))
        self.assertIn("known", pf, "the block says how many ids the table holds")
        self.assertEqual(pf["known"], len(km.DEFAULT_MODEL_PRICES))
        self.assertLess(pf["rows"], pf["known"], "one of six matched: the view has the share to word")
        prices = km._model_prices(NOW + 1, refresh=False)
        self.assertEqual(prices["claude-fable-5-1"]["in"], 11e-6, "the matched id is priced from the feed")
        self.assertEqual(prices["claude-opus-4-8"]["in"], km.DEFAULT_MODEL_PRICES["claude-opus-4-8"]["in"],
                         "an unmatched id is priced from the defaults under a source that reads feed")
        self.assertEqual(km._version_info()["priceFeed"]["known"], pf["known"], "/version carries it too")

    def test_known_is_the_count_the_worker_matches_against(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        with redirect_stderr(io.StringIO()):
            pf = km._price_feed_status(NOW)
        self.assertIn("known", pf, "the block says how many ids the table holds, under off too")
        self.assertEqual(pf["known"], len(km.DEFAULT_MODEL_PRICES))
        sigs = {km._price_sig(k) for k in km.DEFAULT_MODEL_PRICES if km._price_sig(k)}
        self.assertEqual(len(sigs), pf["known"], "every built-in id has its own signature, so rows can reach known")


class TheRecorderCountsTheFeedAlone(PriceFeedCase):
    """The harness's own pin (its docstring's paragraph on the recorder): a request for anything but the feed, made
    from another thread inside a case's window, is refused with a URLError naming the url and is not counted, and the
    feed's own request in the same case still is. Red over an archive of the head the first review round left, whose
    recorder answered every caller with the feed body and counted it: there the thread gets the body and no URLError,
    and self.calls holds the foreign request."""

    def test_a_request_that_is_not_the_feed_is_refused_and_not_counted(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        self._analytics()                                          # a build under off: the feed itself makes no request
        url = "http://127.0.0.1:1/peer-exchange"                   # a synthetic far end shaped like a bus exchange; port 1 listens nowhere
        got = {}

        def dial():
            req = urllib.request.Request(url, data=b'{"kind": "synthetic"}', headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=1) as r:
                    got["answered"] = r.read()
            except Exception as e:                                  # whatever it raised is the subject
                got["raised"] = e
        t = threading.Thread(target=dial, name="foreign-dialer")
        t.start()
        t.join(5)
        self.assertFalse(t.is_alive(), "the foreign dial returned")
        self.assertIsInstance(got.get("raised"), urllib.error.URLError,
                              "a request that is not the feed is refused with a URLError, never answered: "
                              "the thread got %r and the recorder holds %r" % (got, self.calls))
        self.assertEqual(self.calls, [], "the foreign request is not counted")
        reason = str(got["raised"].reason)
        self.assertTrue(reason.startswith(FOREIGN_REFUSED), reason)   # the harness's refusal, not a real failed dial
        self.assertIn(url, reason, "the refusal names the url")
        os.environ.pop("ROMP_PRICE_FEED", None)
        km._ANALYTICS_MEMO.clear()                                 # the build under off memoized its payload for 15 s
        self._analytics(now=NOW + 1)                               # this build starts the case's first fetch (off stamped nothing)
        self.assertEqual(self.calls, [km.PRICE_FEED_URL], "the feed's own request in the same case still counts")


class TheFeedDictIsWhatTheHarnessResets(unittest.TestCase):
    """The keys of the kernel's `_price_feed` literal are FEED_RESET's keys, and `rows` is not among them: the field was
    written under the lock by every landing and read by nothing (the block's `rows` is len(remote), computed in
    _price_feed_status), while the dict's comment listed it among the fields the block reads (the review of PR 878,
    round 2), and FEED_RESET listed the keys by hand with nothing holding the two sets equal, so a dead field could stay
    and a new one could be missed by the reset. Text only over the kernel's source (an ast read of the module-level
    assignment: frozenset() in the literal is no literal for literal_eval), the shape tests/test_price_feed_census.py
    reads the file in; the live dict is checked beside it. Red over the 3ddaf64d8 archive at the `rows` assertion (the
    literal carries it there); proven by mutation at the tree too: `"rows": 0` put back in the literal in a scratch copy
    reds the same assertion, and a key added to the literal and not to FEED_RESET reds the set comparison."""

    def test_the_literals_keys_are_the_resets_keys_and_rows_is_not_one(self):
        src = pathlib.Path(inspect.getsourcefile(km._refresh_remote_prices)).read_text()
        assigns = [n for n in ast.parse(src).body if isinstance(n, ast.Assign) and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "_price_feed"]
        self.assertEqual(len(assigns), 1, "kernel/kernel.py assigns _price_feed once at module level")
        self.assertIsInstance(assigns[0].value, ast.Dict, "and the value is a dict literal")
        keys = [k.value for k in assigns[0].value.keys if isinstance(k, ast.Constant)]
        self.assertEqual(len(keys), len(assigns[0].value.keys), "every key is a literal")
        self.assertNotIn("rows", keys, "the dead field is gone: the block's rows is the cache's own length, len(remote)")
        self.assertEqual(set(keys), set(FEED_RESET), "the harness resets exactly the fields the kernel keeps")
        self.assertEqual(len(keys), len(set(keys)), "no key twice")
        self.assertEqual(set(km._price_feed), set(FEED_RESET), "the live dict holds the same keys")


if __name__ == "__main__":
    unittest.main()
