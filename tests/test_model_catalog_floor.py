#!/usr/bin/env python3
"""The suite-wide model-catalog floor (tests/conftest.py, 2026-09-02): no test kernel fetches the
Models API. The kernel's lazy `_sdk()` build fires the T222 catalog refresh — an async GET on any
credential the process carries — so under pytest the switch is off for every test as a DEFENSIVE floor
(no test reached the network before it, but only because none carried a credential the fetch could
use; a developer's exported key must not change that), and it STAYS off across a test that pops it
(the catalog suite's own fetch tests do exactly that in setUp/tearDown, and a module-level pop would
otherwise hold for the rest of the run). Synthetic throughout; the kernel is loaded only to prove the
refresh is inert under the floor. CatalogFloor is one self-contained case: it pops the switch, runs conftest's
autouse fixture function itself and asserts the switch is back to off, so it pins the per-test re-assert by
execution in whatever process it runs, a serial run or a pytest-xdist worker (the review of PR 878, round 6: the
two cases it replaces, one popping and the next reading the value back, pinned the re-assert only when both ran in
order in one process). It reads the value inside a test body, where the fixture has already set it, so it pins the
import-time line by nothing; that line, and the fixture's statement, are pinned on conftest's source by
tests/test_price_feed_floor.py TheFloorsAreOnConftestsSource, for this switch beside the price feed's (a review of
PR 878)."""
import importlib.util
import inspect
import os
import sys
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
CONFTEST = os.path.join(HERE, "conftest.py")
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_catalog_floor", os.path.join(BIN, "romp-kernel"))


# The two helpers below are tests/test_price_feed_floor.py's, copied: importing that module would load the kernel a
# second time (its TheFloorsAreOnConftestsSource docstring says the same of its source-pin helpers).
def _conftest():
    """tests/conftest.py as a module: the one pytest already loaded for this run when there is one (found by its file, so
    its import-time statements run once and their floors are not re-minted inside a case), else imported by path under
    a private name (a bare unittest run, where nothing else would load it)."""
    for mod in list(sys.modules.values()):
        if os.path.realpath(getattr(mod, "__file__", None) or "") == os.path.realpath(CONFTEST):
            return mod
    spec = importlib.util.spec_from_file_location("romp_tests_conftest_by_path", CONFTEST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture_function(mod, name):
    """The generator function under pytest's fixture definition `mod.<name>`: pytest 8.4 and later wrap it in a
    FixtureFunctionDefinition that follows the __wrapped__ convention (inspect.unwrap reaches the function); older pytest
    kept the function itself. Verified at pytest 9.1.1. A wrapping this does not know is a failure by name, never a pass."""
    obj = getattr(mod, name)
    fn = inspect.unwrap(obj) if hasattr(obj, "__wrapped__") else obj
    if not inspect.isgeneratorfunction(fn):
        raise AssertionError("tests/conftest.py %s is wrapped in a shape this module cannot unwrap: %r" % (name, type(obj)))
    return fn


class CatalogFloor(unittest.TestCase):
    """The per-test re-assert by execution, in one self-contained case: it pops the switch the way the catalog suite's
    tearDown does, runs conftest's own autouse fixture function (tests/conftest.py _no_model_catalog_fetch, reached
    through the module pytest loaded and unwrapped from pytest's fixture definition), asserts the switch is back to
    off, and then proves the refresh does nothing under it. The class had two cases ordered by name, the first popping
    and the second reading the value back: a pin armed only by the ordering inside one process, since under
    pytest-xdist's load distribution the two can land in different workers, and the second then read a variable
    nobody had popped, which passed whether or not the fixture set it (the review of PR 878, round 6). Running the
    fixture inside the case executes the re-assert in whatever worker the case lands in."""

    def test_the_fixture_puts_a_popped_switch_back_and_the_refresh_is_inert_under_it(self):
        self.assertEqual(os.environ.get("ROMP_MODEL_CATALOG"), "off", "conftest's floor holds as the case begins")
        self.addCleanup(lambda: os.environ.__setitem__("ROMP_MODEL_CATALOG", "off"))   # the floor is never left down, whatever fails
        os.environ.pop("ROMP_MODEL_CATALOG", None)                 # what the catalog suite's tearDown does
        self.assertIsNone(os.environ.get("ROMP_MODEL_CATALOG"), "popped: the fixture, not this case, has to put it back")
        fixture = _fixture_function(_conftest(), "_no_model_catalog_fetch")()   # the fixture's body: its assignment, then its yield
        self.addCleanup(lambda: next(fixture, None))               # run it out, what pytest does at the item's teardown
        next(fixture)
        self.assertEqual(os.environ.get("ROMP_MODEL_CATALOG"), "off",
                         "tests/conftest.py's autouse fixture _no_model_catalog_fetch must set ROMP_MODEL_CATALOG back to off: "
                         "a test that pops the switch to drive its fetch would otherwise leave the floor down for every test "
                         "after it in its worker")
        # Synchronous so a missing floor would show as True (a credential lookup and a stderr line),
        # never as a thread that outlives the assertion.
        self.assertFalse(km._refresh_model_catalog("floor probe", _async=False))
        self.assertFalse(km._catalog_status["inflight"])


if __name__ == "__main__":
    unittest.main()
