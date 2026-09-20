#!/usr/bin/env python3
"""The price-source block describes the table that priced the dollars beside it, and a landing is seen whole
(review round 2, 2026-09-20).

Round 1 left three ways the block and the figures could part. The /analytics memo served figures priced from the
built-in defaults under a fresh block that read live feed for 15 s after the fetch landed (the block rode outside
the memo, the figures inside it). A fetch that landed DURING a build, between the pricing merge and the sessions
walk, gave the same pairing on the miss road. And _price_feed_status read the cache, the status fields and its
override merge one after another with no lock while the worker wrote them one after another, so a read in between
paired one fetch's source with another's counts, and the modal rendered `live feed for 0 of 6 models` or `the
feed's rows for 6 known models could not be read`, or counted six overrides with no file present. The fixes: the
worker lands under _price_feed_lock and clears the analytics memo when the rows changed (the event); the status
takes one snapshot under the same lock; and the /analytics build checks the table it priced with against that
snapshot and builds once more when it moved. Also here: the TLS hostname-mismatch label, which CPython composes
with the server hostname, reads as a fixed phrase; a landing whose rows for some known models could not be read is
said on stderr, as a landing that left nothing usable is; the stderr tail names the share a partial feed priced,
as the modal does, and the served table by the view's term, built-in.

Hermetic through tests/test_price_feed_off.py's harness (the same private kernel, the recording urlopen, the
synthetic feed body with invented rates, the constant clock): a synthetic transcript of one response prices at
$10.00 from the defaults and $11.00 from the feed's row, so the two tables are told apart by the figure.
"""
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from contextlib import redirect_stderr
from datetime import datetime, timezone
from romp_load import load_source   # noqa: F401  the state preamble below precedes the harness import, which loads the kernel

HERE = os.path.dirname(os.path.realpath(__file__))
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)   # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
sys.path.insert(0, HERE)
import test_price_feed_off as H   # noqa: E402  the harness: PriceFeedCase, the recorder, FEED, NOW, the private kernel

km, jd = H.km, H.jd
NOW, WINDOW, FEED, TTL = H.NOW, H.WINDOW, H.FEED, H.km.PRICE_TTL
SID = "11111111-2222-3333-4444-555555555555"
# every built-in id signed, at invented rates that differ from every default
FULL = {k: {"input_cost_per_token": 7e-6, "output_cost_per_token": 9e-6} for k in km.DEFAULT_MODEL_PRICES}
RENAMED = {"some-other-vendor-model": FEED["some-other-vendor-model"]}   # signs to no built-in id: the cache empties
READER = "price-feed-status-reader"


def _alive():
    return any(t.name == "price-refresh" and t.is_alive() for t in threading.enumerate())


class OneSession(H.PriceFeedCase):
    """A synthetic transcript of one response, 1,000,000 input tokens of claude-fable-5-1: $10.00 at the default
    10e-6, $11.00 at FEED's 11e-6, so a payload's figure says which table priced it."""

    def setUp(self):
        super().setUp()
        p = pathlib.Path(self.td.name) / (SID + ".jsonl")
        ts = datetime.fromtimestamp(NOW - 100, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        p.write_text(json.dumps({"type": "assistant", "timestamp": ts,
                                 "message": {"id": "msg_synthetic_1", "model": "claude-fable-5-1",
                                             "usage": {"input_tokens": 1000000, "output_tokens": 0}}}) + "\n")
        self.session = (SID, p, NOW - 100, "web")
        jd.discover = lambda now, window=None, forks=True: [self.session]


class TheBlockDescribesTheTableThatPricedTheDollars(OneSession):
    def test_a_landing_after_the_first_open_reprices_the_next_click_instead_of_relabelling_the_memo(self):
        """The first open builds while the fetch is in flight (defaults, inflight, $10.00). The fetch lands. The
        click within 15 s used to take the memo road: the memo's $10.00 under a block that read live feed. The
        landing clears the memo, so that click builds again and prices from the row the block names."""
        self.gate = threading.Event()
        self.addCleanup(self.gate.set)
        with redirect_stderr(io.StringIO()):
            r1 = km._token_analytics(NOW, WINDOW)
        self.assertEqual((r1["priceFeed"]["source"], r1["priceFeed"]["reason"]), ("defaults", "inflight"))
        self.assertAlmostEqual(r1["sessions"]["cost"], 10.0, msg="priced from the defaults: the fetch has not landed")
        self.gate.set()
        self._join()
        r2 = km._token_analytics(NOW + 5, WINDOW)
        pf = r2["priceFeed"]
        self.assertEqual((pf["source"], pf["rows"], pf["ageS"]), ("feed", 1, 5))
        self.assertAlmostEqual(r2["sessions"]["cost"], 11.0, msg="the click after the landing prices from the feed row the "
                               "block names, never the memo's defaults-priced figure under a live-feed line")
        self.assertEqual(km._ANALYTICS_MEMO[WINDOW]["t"], NOW + 5, "the landing invalidated the memo: this build is fresh")
        self.assertEqual(len(self.calls), 1, "one fetch: the rebuild inside the TTL starts none")
        r3 = km._token_analytics(NOW + 8, WINDOW)
        self.assertEqual(km._ANALYTICS_MEMO[WINDOW]["t"], NOW + 5, "the memo serves again once its figures and its block agree")
        self.assertAlmostEqual(r3["sessions"]["cost"], 11.0)
        self.assertEqual(r3["priceFeed"]["ageS"], 8, "and the block still rides outside it: the age is live")

    def test_a_landing_during_the_build_prices_the_payload_from_the_table_its_block_names(self):
        """The fetch lands between the pricing merge and the sessions walk (the first open on a box with many
        transcripts: the walk takes seconds, so does the fetch). The payload used to carry the old table's dollars
        under the new table's block, and memoize that pairing. The build finds no block for its figures and prices
        once more from the table now."""
        self.gate = threading.Event()
        self.addCleanup(self.gate.set)
        session, walks = self.session, []

        def discover(now, window=None, forks=True):
            walks.append(dict(km._price_cache["remote"]))   # the table as each walk begins
            self.gate.set()                                  # the fetch lands here: after the merge, before the walk
            self._join()
            return [session]
        jd.discover = discover
        with redirect_stderr(io.StringIO()):
            r = km._token_analytics(NOW, WINDOW)
        pf = r["priceFeed"]
        self.assertEqual((pf["source"], pf["rows"]), ("feed", 1), "the block names the landed table")
        self.assertAlmostEqual(r["sessions"]["cost"], 11.0, msg="and the dollars are priced from it, not from the merge "
                               "taken before it landed")
        self.assertEqual(walks[0], {}, "the first walk began with the fetch not landed")
        self.assertEqual(len(walks), 2, "so the build priced twice: once before the landing, once from the landed table")
        self.assertEqual(walks[1]["claude-fable-5-1"]["in"], 11e-6)
        self.assertAlmostEqual(km._ANALYTICS_MEMO[WINDOW]["resp"]["sessions"]["cost"], 11.0,
                               msg="the memo holds the repriced figures, so the next click within 15 s serves them")
        self.assertEqual(len(self.calls), 1, "one fetch: the rebuild is inside the TTL")

    def test_control_a_build_with_nothing_landing_prices_once(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        walks = []
        session = self.session

        def discover(now, window=None, forks=True):
            walks.append(1)
            return [session]
        jd.discover = discover
        with redirect_stderr(io.StringIO()):
            r = km._token_analytics(NOW, WINDOW)
        self.assertEqual(len(walks), 1, "the table did not move: one walk")
        self.assertEqual((r["priceFeed"]["source"], r["priceFeed"]["reason"]), ("defaults", "off"))
        self.assertAlmostEqual(r["sessions"]["cost"], 10.0)
        self.assertEqual(self.calls, [])


class OneSnapshot(H.PriceFeedCase):
    """_price_feed_status and the worker's landing take one lock: a read sees a landing whole or not at all."""

    def test_a_landing_waits_for_a_read_that_is_inside_the_status(self):
        """Six rows cached; the TTL re-attempt lands nothing usable (the feed renamed its ids) while a reader is
        inside the status's own merge (PRICE_CONFIG.read_text, the open() that releases the GIL). The reader used
        to resume onto the landed counts: source feed from the old cache, rows and matched 0 from the new landing,
        overrides 6 from a merge over a cache the block's rows no longer were. The landing waits."""
        self.body = json.dumps(FULL).encode()
        self._analytics()
        self.assertEqual(len(km._price_cache["remote"]), 6)
        self.body = json.dumps(RENAMED).encode()
        self.gate = threading.Event()
        self.addCleanup(self.gate.set)
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        class Park(type(km.PRICE_CONFIG)):
            def read_text(self, *a, **k):
                if threading.current_thread().name == READER:
                    entered.set()
                    release.wait(5)
                return super().read_text(*a, **k)
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW + TTL)                   # the re-attempt's worker parks inside urlopen
            deadline = time.time() + 5
            while len(self.calls) < 2 and time.time() < deadline:
                time.sleep(0.005)
            self.assertEqual(len(self.calls), 2, "the worker is inside the fetch")
            km.PRICE_CONFIG = Park(str(km.PRICE_CONFIG))            # the harness restores the path
            box = {}
            rt = threading.Thread(target=lambda: box.__setitem__("st", km._price_feed_status(NOW + TTL)), name=READER)
            rt.start()
            self.assertTrue(entered.wait(5), "the reader is inside the status's merge")
            self.gate.set()                                        # the worker returns from the fetch and tries to land
            deadline = time.time() + 1.0
            while time.time() < deadline and _alive() and km._price_cache["remote"]:
                time.sleep(0.01)                                   # a landing that CAN happen happens within microseconds
            rows_while_read = len(km._price_cache["remote"])
            release.set()
            rt.join(5)
            self._join()
        st = box["st"]
        self.assertEqual(rows_while_read, 6, "the landing waited for the read: the cache the reader holds is the cache it counts")
        self.assertEqual((st["source"], st["rows"], st["matched"], st["overrides"], st["fetchedAt"]), ("feed", 6, 6, 0, NOW),
                         "one snapshot: the six rows, their counts, no override, the fetch that landed them")
        settled = km._price_feed_status(NOW + TTL)
        self.assertEqual((settled["source"], settled["reason"], settled["rows"], settled["matched"]), ("defaults", "empty", 0, 0),
                         "and the landing went through once the read was done")
        self.assertEqual(err.getvalue().count("price feed: fetch landed with no usable row (0 signed to a built-in id, none parsed); "), 1)

    def test_a_read_waits_for_a_landing_that_has_published_its_rows_and_not_yet_their_counts(self):
        """The worker parked between its cache publish and its fetchedAt write. A reader started there used to read
        source feed from the new rows with rows 0 and no fetch time from the old fields (`live feed for 0 of 6
        models` in the modal). The reader waits for the landing to finish."""
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        class Hooked(dict):
            def __setitem__(self, k, v):
                if k == "fetchedAt" and threading.current_thread().name == "price-refresh":
                    entered.set()
                    release.wait(5)
                dict.__setitem__(self, k, v)
        real = km._price_feed
        km._price_feed = Hooked(real)
        self.addCleanup(setattr, km, "_price_feed", real)          # the harness then resets the real dict's values
        self.body = json.dumps(FULL).encode()
        with redirect_stderr(io.StringIO()):
            km._refresh_remote_prices(NOW)
            self.assertTrue(entered.wait(5), "the worker reached its fetchedAt write")
            self.assertEqual(len(km._price_cache["remote"]), 6, "the cache is published: the worker is between its writes")
            box = {}
            rt = threading.Thread(target=lambda: box.__setitem__("st", km._price_feed_status(NOW)), name=READER)
            rt.start()
            rt.join(1.0)
            waited = rt.is_alive()
            release.set()
            self._join()
            rt.join(5)
        self.assertTrue(waited, "the read waited for the landing to finish instead of reading between its writes")
        st = box["st"]
        self.assertEqual((st["source"], st["rows"], st["matched"], st["fetchedAt"], st["ageS"], st["lastError"]),
                         ("feed", 6, 6, NOW, 0, None), "the landing, whole")


class TheLabelNeverCarriesTheHost(H.PriceFeedCase):
    """CPython's _ssl composes two verify messages itself, with the server hostname quoted in them (its templates
    `Hostname mismatch, certificate is not valid for '%S'.` and `IP address mismatch, certificate is not valid for
    '%S'.`, verify codes 62 and 64); every other verify message is OpenSSL's table string. Built the way _ssl builds
    the exception (errno, reason, verify_code, verify_message), the real handshake's shape (round 2's refuters drove
    it through the worker against a local server with a certificate for another name)."""

    def _cert_error(self, code, message):
        import ssl
        e = ssl.SSLCertVerificationError(ssl.SSL_ERROR_SSL, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                                         "%s (_ssl.c:1000)" % message)
        e.reason, e.verify_code, e.verify_message = "CERTIFICATE_VERIFY_FAILED", code, message
        return e

    def test_a_hostname_or_ip_address_mismatch_reads_as_a_fixed_phrase_never_the_host(self):
        host = self._cert_error(62, "Hostname mismatch, certificate is not valid for 'TESTHOST'.")
        ip = self._cert_error(64, "IP address mismatch, certificate is not valid for 'TESTHOST'.")
        self.assertEqual(km._price_feed_error_class(urllib.error.URLError(host)),
                         "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED (hostname mismatch)")
        self.assertEqual(km._price_feed_error_class(urllib.error.URLError(ip)),
                         "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED (IP address mismatch)")
        # a verify message this interpreter does not compose today, quoting a name: the token alone, never the name
        later = self._cert_error(999, "Some later check, certificate is not valid for 'TESTHOST'.")
        self.assertEqual(km._price_feed_error_class(urllib.error.URLError(later)),
                         "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED")
        # control: a table string is relayed as before
        signed = self._cert_error(18, "self-signed certificate")
        self.assertEqual(km._price_feed_error_class(urllib.error.URLError(signed)),
                         "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED (self-signed certificate)")
        self.raise_with = urllib.error.URLError(host)              # through the worker: lastError, the line and /version
        err = io.StringIO()
        with redirect_stderr(err):
            km._refresh_remote_prices(NOW)
            self._join()
        want = "URLError: SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED (hostname mismatch)"
        self.assertIn("price feed: fetch failed (%s); " % want, err.getvalue())
        self.assertEqual(km._price_feed_status(NOW)["lastError"], want)
        self.assertEqual(km._version_info()["priceFeed"]["lastError"], want)
        self.assertNotIn("TESTHOST", err.getvalue() + json.dumps(km._version_info()["priceFeed"]), "never the host")


class APartialLandingIsSaid(H.PriceFeedCase):
    """A landing that parsed rows for some built-in ids and could not read the rows for others is said once on
    stderr, as a landing that left nothing usable is; the status told the two apart (`matched` above `rows`) and
    the log said nothing."""

    def test_rows_for_some_known_ids_that_do_not_parse_are_said_once(self):
        self.body = json.dumps({"claude-fable-5-1": FEED["claude-fable-5-1"],
                                "claude-opus-4-8": {"input_cost_per_token": "n/a", "output_cost_per_token": "n/a"}}).encode()
        resp, log = self._analytics()
        self.assertEqual(log.count("price feed: fetch landed with rows for 1 known model unreadable (2 signed to a built-in id, "
                                   "1 parsed); "), 1, log)
        self.assertIn("; the cost view prices tokens from the feed rows in memory for 1 of 6 models, fetched 0 s ago, and the "
                      "built-in defaults for the rest\n", log)
        km._ANALYTICS_MEMO.clear()
        resp, log2 = self._analytics(now=NOW + 1)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["rows"], pf["matched"], pf["known"], pf["lastError"]), ("feed", 1, 2, 6, None))
        self.assertEqual(log2, "", "said once, at the fetch, not per build")
        self.assertNotIn("n/a", log, "never the body")
        self.assertEqual(len(self.calls), 1)

    def test_control_a_landing_whose_signed_rows_all_parse_says_nothing(self):
        resp, log = self._analytics()                              # FEED: one row signed, that one parsed
        self.assertEqual(log, "")
        pf = resp["priceFeed"]
        self.assertEqual((pf["rows"], pf["matched"]), (1, 1))


class TheTailNamesTheShare(H.PriceFeedCase):
    """The stderr tail words the same facts the modal's line words: a feed that priced 1 of 6 models says so and
    that the built-in defaults price the rest, where it used to call the whole table feed-priced."""

    def test_a_partial_table_is_named_with_its_share_after_a_failed_refresh(self):
        self._analytics()                                          # FEED lands: 1 of 6
        km._ANALYTICS_MEMO.clear()
        later = NOW + TTL + 1800
        self.raise_with = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
        resp, log = self._analytics(now=later)
        self.assertIn("; the cost view prices tokens from the feed rows in memory for 1 of 6 models, fetched 6 h ago, and the "
                      "built-in defaults for the rest\n", log)
        pf = resp["priceFeed"]
        self.assertEqual((pf["source"], pf["rows"], pf["known"]), ("feed", 1, 6))
        merged = km._model_prices(later, refresh=False)
        self.assertEqual(sum(1 for k in km.DEFAULT_MODEL_PRICES if merged[k] == km.DEFAULT_MODEL_PRICES[k]), 5,
                         "five of the six price from the defaults, as the tail says")

    def test_a_partial_table_under_off_is_named_with_its_share(self):
        self._analytics()
        os.environ["ROMP_PRICE_FEED"] = "off"
        km._ANALYTICS_MEMO.clear()
        resp, log = self._analytics(now=NOW + 7200)
        self.assertIn(H.OFF_LINE + "; the cost view prices tokens from the feed rows in memory for 1 of 6 models, fetched 2 h ago, "
                      "and the built-in defaults for the rest\n", log)
        self.assertEqual(len(self.calls), 1)

    def test_control_a_full_table_s_tail_is_the_plain_one(self):
        self.body = json.dumps(FULL).encode()
        self._analytics()
        km._ANALYTICS_MEMO.clear()
        self.raise_with = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
        resp, log = self._analytics(now=NOW + TTL + 1800)
        self.assertIn("; the cost view prices tokens from the feed rows in memory, fetched 6 h ago\n", log)
        self.assertNotIn(" for ", log.split("prices tokens from")[1], "six of six: no share to name")

    def test_the_served_table_is_named_by_the_views_term(self):
        os.environ["ROMP_PRICE_FEED"] = "off"
        resp, log = self._analytics()
        self.assertIn(H.OFF_LINE + "; the cost view prices tokens from the built-in defaults\n", log,
                      "one term on every surface: the modal's line says built-in, so does the log")
        self.assertNotIn("baked-in", log)


if __name__ == "__main__":
    unittest.main()
