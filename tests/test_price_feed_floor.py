#!/usr/bin/env python3
"""The suite-wide price-feed floor (tests/conftest.py, 2026-09-20), the runner's half of "no test kernel fetches
the price feed"; the lab kernels' half is tests/test_ship_reship_served.py kernel_env, pinned by LabKernelEnv there.

The cost view's /analytics build (`_token_analytics`, the one refresh=True caller of `_model_prices`) starts a
background GET of the public LiteLLM price list on a third party's host whenever the in-memory price cache is
older than PRICE_TTL, which at import it always is (there is no cache file). Under pytest the feed's switch
(ROMP_PRICE_FEED=off, kernel/kernel.py _price_feed_off, read as the FIRST statement of _refresh_remote_prices)
is off for every test as a DEFENSIVE floor, the model catalog's floor copied (tests/test_model_catalog_floor.py).
It reaches the runner and every child that copies the runner's environment; a lab kernel built from names
(kernel_env's allowlist) never inherits it and sets the switch itself, because the two served labs that open the
view (the settings recut and the widget reorder browser tests) fetched the feed on every run without it
(2026-09-20, review round 2). A test kernel serving the view is one request away from a third party on nobody's
assertion. It STAYS off across a test that pops it: the feed's own tests (tests/test_price_feed_off.py) pop the
variable in setUp to drive the fetch against a recorder, and a module-level pop would otherwise hold for the
rest of a serial run. Synthetic throughout; the kernel is loaded only to prove the refresh is inert under the
floor."""
import io
import os
import tempfile
import threading
import unittest
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
km = load_source("romp_kernel_price_feed_floor", os.path.join(BIN, "romp-kernel"))
# this module builds no backend; the minted root still carries the hosts-off word, as every minted root does
km.jd.STATE.mkdir(parents=True, exist_ok=True)
(km.jd.STATE / "session-hosts").write_text("off")

NOW = 1781100000   # a synthetic clock


class PriceFeedFloor(unittest.TestCase):
    """Ordered on purpose (unittest runs methods by name): the first test pops the switch the way the feed
    suite's setUp does; the second proves the per-test re-assert put it back before the next test ran, and
    that the refresh does nothing under it."""

    def test_1_a_test_may_pop_the_switch(self):
        self.assertEqual(os.environ.get("ROMP_PRICE_FEED"), "off", "conftest's import-time floor")
        os.environ.pop("ROMP_PRICE_FEED", None)

    def test_2_the_floor_is_back_and_the_refresh_is_inert(self):
        self.assertEqual(os.environ.get("ROMP_PRICE_FEED"), "off",
                         "conftest's per-test re-assert must restore the switch a test popped")
        saved_t = km._price_cache["t"]
        self.addCleanup(lambda: km._price_cache.update(t=saved_t))
        km._price_cache["t"] = 0                                   # as stale as a cache gets: a fetch, but for the floor
        calls = []

        def urlopen(url, timeout=None, **kw):
            calls.append(url)
            return io.BytesIO(b"{}")                               # a context manager with a read(), should a fetch start

        err = io.StringIO()
        with mock.patch("urllib.request.urlopen", urlopen), redirect_stderr(err):
            km._refresh_remote_prices(NOW)                         # the cost view's road, the one place a fetch can start
            for t in threading.enumerate():                        # a worker that started anyway must finish before the read
                if t.name == "price-refresh":
                    t.join(5)
        self.assertEqual(calls, [], "under the floor nothing is attempted")
        self.assertEqual(km._price_cache["t"], 0, "and nothing is stamped: the switch is read before the TTL check")
        self.assertEqual(km._price_feed_status(NOW)["reason"], "off", "and the status says why the defaults serve")


if __name__ == "__main__":
    unittest.main()
