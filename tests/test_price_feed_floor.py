#!/usr/bin/env python3
"""The suite-wide price-feed floor (tests/conftest.py, 2026-09-20), the runner's half of "no test kernel fetches
the price feed"; the lab kernels' half is tests/test_ship_reship_served.py kernel_env, pinned by LabKernelEnv there.
The runner's floor has two halves of its own, and each has a pin here: the per-test re-assert (conftest's autouse
fixture) by execution, in PriceFeedFloor, and the import-time assignment (conftest's module-level statement, the
half that covers collection and module-import time) on conftest's SOURCE, in TheFloorsAreOnConftestsSource, the
shape tests/test_cli_scope_floor.py uses. An assertion inside a test body cannot tell the two halves apart (the
fixture has already set the value when the body runs), so a review of PR 878 found the import-time line unpinned:
deleting it left the suite green. The source pins cover the model catalog's floor too, the twin two
lines above the feed's in conftest.py, whose tests/test_model_catalog_floor.py has the same in-body reads.

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
import ast
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
CONFTEST = os.path.join(HERE, "conftest.py")
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


# The two network switches conftest floors with the same two statements each: a module-level assignment and an
# autouse fixture that re-asserts it. One helper, parameterised by the variable, pins both halves of both.
FLOORED_OFF = ("ROMP_PRICE_FEED", "ROMP_MODEL_CATALOG")


def _sets_off(stmt, var):
    """Is `stmt` the statement os.environ[var] = "off"? (Set, not setdefault: "off" is the one value either switch
    reads as off, so no outer intent is being overridden.)"""
    if not isinstance(stmt, ast.Assign):
        return False
    if not (isinstance(stmt.value, ast.Constant) and stmt.value.value == "off"):
        return False
    for t in stmt.targets:
        if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute) and t.value.attr == "environ"
                and isinstance(t.slice, ast.Constant) and t.slice.value == var):
            return True
    return False


def _is_autouse_fixture(fn):
    """Is `fn` decorated @pytest.fixture(autouse=True)?"""
    for d in fn.decorator_list:
        if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "fixture"):
            continue
        for kw in d.keywords:
            if kw.arg == "autouse" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False


class TheFloorsAreOnConftestsSource(unittest.TestCase):
    """Pinned on tests/conftest.py's SOURCE, not on the value at run time: by the time a test body reads the
    variable the autouse fixture has set it, whether or not the module-level line exists, so a run-time read is
    blind to the import-time half. Both switches are pinned here under a subTest naming the variable (one helper,
    one class, one module to read; a red says which floor lost which half); tests/test_model_catalog_floor.py
    keeps its execution pins and gains none, since importing this module's helper from there would load the
    kernel a second time. No module-level assertion is placed in this module: a bare unittest or script run does
    not execute conftest, and such an assertion would raise at import instead of failing by name. A pin whose
    defect is a missing test has no red at an archive (conftest carried both statements at every head of PR 878),
    so its evidence is a mutation at this head: each of the four statements deleted in a scratch copy of the tree
    reds its case, and its case alone among these two, naming the variable."""

    def setUp(self):
        with open(CONFTEST) as f:
            self.body = ast.parse(f.read(), filename=CONFTEST).body

    def test_the_import_time_floor_is_a_module_level_statement(self):
        # Top level only: a set inside a function does not run at collection, and collection is when a test
        # module's import-time /analytics build (or its _sdk() build, for the catalog) would reach the network.
        for var in FLOORED_OFF:
            with self.subTest(var=var):
                self.assertTrue(any(_sets_off(stmt, var) for stmt in self.body),
                                'tests/conftest.py must set os.environ["%s"] = "off" at module level: without it a test '
                                "module that builds an /analytics payload (or an SDK client) at import or collection time "
                                "fetches from a third party on the next run, and nothing else in the suite would say so" % var)

    def test_an_autouse_fixture_re_asserts_the_floor_per_test(self):
        fixtures = [fn for fn in self.body if isinstance(fn, ast.FunctionDef) and _is_autouse_fixture(fn)]
        self.assertTrue(fixtures, "tests/conftest.py has no autouse fixtures at all")
        for var in FLOORED_OFF:
            with self.subTest(var=var):
                self.assertTrue(any(any(_sets_off(stmt, var) for stmt in fn.body) for fn in fixtures),
                                'no autouse fixture in tests/conftest.py sets os.environ["%s"] = "off": a test that pops '
                                "the switch to drive its fetch against a recorder would otherwise leave it off the floor for "
                                "every test after it in a serial run" % var)


if __name__ == "__main__":
    unittest.main()
