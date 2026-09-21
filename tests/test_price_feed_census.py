#!/usr/bin/env python3
"""Every place a price fetch can start is counted, and every road to it (the review of PR 878, 2026-09-21).

The claim the off switch rests on is that _refresh_remote_prices is the ONE place a price fetch can start: the switch
(ROMP_PRICE_FEED=off, _price_feed_off) is its first statement, so nothing else in the kernel reaches the feed's host
(docs/reference.md's price feed subsection and the ledger entry say so). Until this module the claim stood in
docstrings alone: a second urlopen of PRICE_FEED_URL in another function, or a second refresh=True caller of
_model_prices (a boot warm-up, a route handler), left every price feed test green. This is the census that keeps it
true, in the repo's classify-or-red shape: every site found is in the table below with its reason, or the test fails
naming the site by file, enclosing function and line and the two ways to resolve it; and a classified site that no
longer exists fails too, so the table cannot go stale.

Counted, by ast over kernel/kernel.py: (1) every call whose arguments (positional or keyword, at any depth) read the
name PRICE_FEED_URL, and every other read of that name, so an alias (`url = PRICE_FEED_URL`) is a site too (the URL is
read once, in the worker's urlopen); (2) every call to _refresh_remote_prices (the one caller is _model_prices); (3)
every call to _model_prices, partitioned by its `refresh` argument: the callers that let the refresh run (no
`refresh` argument, or one that is not the constant False) are the cost view's build alone, and the refresh=False
callers are the guard's road and the status's own merge, which never enter the refresh (T350). The enclosing function
is the path of nested defs and classes (the worker is `_refresh_remote_prices.work`); a call at module level is
`<module>`.

Text only: kernel/kernel.py is read as a file and parsed, nothing loads romp code, so no state root is minted
(tests/test_price_feed_vocabulary.py's shape). tests/test_price_feed_off.py executes the switch at the one site this
module counts (OffSwitch, GuardRoad); tests/test_stage_marks.py's census keys on the worker's inner def name.
"""
import ast
import os
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
KERNEL_PATH = os.path.join("kernel", "kernel.py")

# The table. A site is classified here, with its reason, only once it cannot start an ungated fetch: a fetch that
# starts anywhere but _refresh_remote_prices must check _price_feed_off itself, or route through _model_prices.
URL_SITES = {"_refresh_remote_prices.work": "the worker's urlopen, inside the one function the switch gates"}
REFRESH_CALLERS = {"_model_prices": "the merge's refresh road (refresh=True), the cost view's"}
REFRESH_TRUE_CALLERS = {"_token_analytics": "the /analytics build, the one road that lets a fetch start"}
REFRESH_FALSE_CALLERS = {
    "_spend_window_usd": "the spend guard's window sum on the pusher's path: never a fetch (T350)",
    "_spend_guard_tick": "the spend guard's tick on the pusher's path: never a fetch (T350)",
    "_price_feed_status": "the status's own merge under _price_feed_lock, the count of overrides: never a fetch (T350)",
}
RESOLVE = ("either gate it behind _price_feed_off (the first statement of _refresh_remote_prices is the shape) and add it "
           "to the table in tests/test_price_feed_census.py with its reason, or route it through _model_prices")


def _read_kernel():
    with open(os.path.join(ROOT, KERNEL_PATH), encoding="utf-8") as f:
        return f.read()


class _Census(ast.NodeVisitor):
    """Every call in a module with the path of the function it sits in, and every read of PRICE_FEED_URL."""

    def __init__(self):
        self.path = []
        self.calls = []        # (path, Call)
        self.url_reads = []    # (path, line)

    def _scope(self, node):
        self.path.append(node.name)
        self.generic_visit(node)
        self.path.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _scope

    def visit_Call(self, node):
        self.calls.append((".".join(self.path) or "<module>", node))
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id == "PRICE_FEED_URL" and isinstance(node.ctx, ast.Load):
            self.url_reads.append((".".join(self.path) or "<module>", node.lineno))


def _callee(call):
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


def _reads_url(call):
    exprs = list(call.args) + [k.value for k in call.keywords]
    return any(isinstance(n, ast.Name) and n.id == "PRICE_FEED_URL" for e in exprs for n in ast.walk(e))


def _refresh_is_false(call):
    """True only for the constant False, by keyword or as the second positional; anything else lets the refresh run."""
    for k in call.keywords:
        if k.arg == "refresh":
            return isinstance(k.value, ast.Constant) and k.value.value is False
    if len(call.args) >= 2:
        return isinstance(call.args[1], ast.Constant) and call.args[1].value is False
    return False


def census(src):
    """{"url": {path: [lines]}, "url_reads": {path: [lines]}, "refresh": {...}, "true": {...}, "false": {...}}."""
    c = _Census()
    c.visit(ast.parse(src))
    out = {"url": {}, "url_reads": {}, "refresh": {}, "true": {}, "false": {}}
    for path, line in c.url_reads:
        out["url_reads"].setdefault(path, []).append(line)
    for path, call in c.calls:
        name = _callee(call)
        if _reads_url(call):
            out["url"].setdefault(path, []).append(call.lineno)
        if name == "_refresh_remote_prices":
            out["refresh"].setdefault(path, []).append(call.lineno)
        elif name == "_model_prices":
            out["false" if _refresh_is_false(call) else "true"].setdefault(path, []).append(call.lineno)
    return out


KERNEL = _read_kernel()
CENSUS = census(KERNEL)


class _Pins(unittest.TestCase):
    def assertClassified(self, found, table, what, resolve):
        """Every site found is in the table (else: the site by file, function and line, and how to resolve it), and every
        table entry is found (else: the stale row)."""
        for path in sorted(set(found) - set(table)):
            self.fail("%s:%s %s %s and is not in the classified set: %s" % (
                KERNEL_PATH, ",".join(str(n) for n in found[path]), path, what, resolve))
        for path in sorted(set(table) - set(found)):
            self.fail("the census table names %s, which no longer %s: drop it from the table (a classified site that is "
                      "gone is a stale row, never a pass)" % (path, what))


class TheFeedHasOneFetchSite(_Pins):
    def test_the_census_finds_its_anchors(self):
        """An empty census is a moved anchor (the functions renamed, the constant renamed), never a pass."""
        self.assertTrue(CENSUS["url"], "kernel/kernel.py calls something with PRICE_FEED_URL among its arguments")
        self.assertTrue(CENSUS["refresh"], "kernel/kernel.py calls _refresh_remote_prices")
        self.assertTrue(CENSUS["true"] and CENSUS["false"], "kernel/kernel.py calls _model_prices with and without refresh=False")

    def test_the_url_is_read_at_the_workers_urlopen_alone(self):
        self.assertClassified(CENSUS["url"], URL_SITES, "passes PRICE_FEED_URL to a call", RESOLVE)
        self.assertClassified(CENSUS["url_reads"], URL_SITES, "reads PRICE_FEED_URL",
                              "a read outside the worker's urlopen is a second road to the host, or an alias for one: " + RESOLVE)
        self.assertEqual(sum(len(v) for v in CENSUS["url_reads"].values()), 1,
                         "the constant is read exactly once outside its own assignment: %r" % CENSUS["url_reads"])

    def test_the_refresh_is_entered_from_the_merge_alone(self):
        self.assertClassified(CENSUS["refresh"], REFRESH_CALLERS, "calls _refresh_remote_prices",
                              "a caller besides _model_prices is a road to a fetch that the T350 rule (refresh=False never "
                              "enters the refresh) does not cover: route it through _model_prices, or add it here with its reason")

    def test_the_merge_lets_a_fetch_start_from_the_cost_view_alone(self):
        self.assertClassified(CENSUS["true"], REFRESH_TRUE_CALLERS, "calls _model_prices letting the refresh run",
                              "a second refresh=True caller is a second road to the feed's host (a boot warm-up, a route handler): "
                              "pass refresh=False if it must never fetch, or add it here with its reason and the switch it obeys")
        self.assertClassified(CENSUS["false"], REFRESH_FALSE_CALLERS, "calls _model_prices with refresh=False",
                              "a new refresh=False caller never fetches (T350); add it to the table with its reason")

    def test_the_switch_is_the_first_statement_of_the_one_fetch_site(self):
        """Read as text here so the census and the gate are one module (tests/test_price_feed_off.py executes it)."""
        fn = next(n for n in ast.parse(KERNEL).body if isinstance(n, ast.FunctionDef) and n.name == "_refresh_remote_prices")
        body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) else fn.body
        self.assertIsInstance(body[0], ast.If)
        self.assertEqual(ast.unparse(body[0].test), "_price_feed_off()", "the switch gates the one fetch site before anything else")


class TheCensusIsLive(unittest.TestCase):
    """The extractor on a small module of its own: a second fetch site, a second refresh caller and an alias are found,
    and a classified site that is gone is found missing. The same functions run over the real kernel above."""

    SMALL = '''
PRICE_FEED_URL = "https://TESTHOST/prices.json"

def _refresh_remote_prices(now):
    def work():
        with urllib.request.urlopen(PRICE_FEED_URL, timeout=4) as r:
            return r
    return work

def _model_prices(now=None, refresh=True):
    if refresh:
        _refresh_remote_prices(now)
    return {}

def _spend_window_usd(now):
    return _model_prices(int(now), refresh=False)

def _spend_guard_tick(now):
    return _model_prices(int(now), refresh=False)

def _price_feed_status(now):
    return _model_prices(now, refresh=False)

def _token_analytics(now, window):
    return _model_prices(now)
'''

    def test_the_small_module_matches_the_table(self):
        c = census(self.SMALL)
        self.assertEqual(set(c["url"]), set(URL_SITES))
        self.assertEqual(set(c["refresh"]), set(REFRESH_CALLERS))
        self.assertEqual(set(c["true"]), set(REFRESH_TRUE_CALLERS))
        self.assertEqual(set(c["false"]), set(REFRESH_FALSE_CALLERS))

    def test_a_second_urlopen_of_the_url_is_found(self):
        c = census(self.SMALL + "\ndef _warm_prices():\n    return urllib.request.urlopen(PRICE_FEED_URL, timeout=4)\n")
        self.assertEqual(set(c["url"]) - set(URL_SITES), {"_warm_prices"})
        self.assertEqual(sum(len(v) for v in c["url_reads"].values()), 2)

    def test_an_alias_of_the_url_is_found(self):
        c = census(self.SMALL + "\ndef _warm_prices():\n    url = PRICE_FEED_URL\n    return urllib.request.urlopen(url)\n")
        self.assertEqual(set(c["url"]), set(URL_SITES), "the call reads the alias, not the name")
        self.assertEqual(set(c["url_reads"]) - set(URL_SITES), {"_warm_prices"}, "and the read of the name finds it")

    def test_a_second_refresh_true_caller_is_found(self):
        c = census(self.SMALL + "\ndef _boot_warm(now):\n    return _model_prices(now)\n")
        self.assertEqual(set(c["true"]) - set(REFRESH_TRUE_CALLERS), {"_boot_warm"})
        c = census(self.SMALL + "\ndef _boot_warm(now):\n    return _model_prices(now, refresh=bool(now))\n")
        self.assertIn("_boot_warm", c["true"], "a refresh argument that is not the constant False lets the refresh run")
        c = census(self.SMALL + "\ndef _boot_warm(now):\n    return _model_prices(now, False)\n")
        self.assertIn("_boot_warm", c["false"], "the constant False as the second positional is the guard's road")

    def test_a_second_caller_of_the_refresh_is_found(self):
        c = census(self.SMALL + "\ndef _boot_warm(now):\n    _refresh_remote_prices(now)\n")
        self.assertEqual(set(c["refresh"]) - set(REFRESH_CALLERS), {"_boot_warm"})

    def test_a_classified_site_that_is_gone_is_found_missing(self):
        gone = self.SMALL.replace("def _spend_guard_tick(now):\n    return _model_prices(int(now), refresh=False)\n", "")
        self.assertNotEqual(gone, self.SMALL)
        c = census(gone)
        self.assertEqual(set(REFRESH_FALSE_CALLERS) - set(c["false"]), {"_spend_guard_tick"})
        with self.assertRaises(AssertionError) as cm:
            _Pins("assertClassified").assertClassified(c["false"], REFRESH_FALSE_CALLERS, "calls _model_prices with refresh=False", "")
        self.assertIn("stale row", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
