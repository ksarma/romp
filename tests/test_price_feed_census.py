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

The second half of this module (round 2 of the review, 2026-09-21) runs scripts/network-inventory.py, the census of
every outbound primitive over the runtime trees that SECURITY.md's Network access section and the ledger entry's road
table are derived from. Until this round nothing ran it: its guarantee held only when a person typed the command, its
only gate was an unclassified site (a scan that lost a third of its sites exited 0), its walk was flat, it filed a
shell, node or perl child and every browser fetch as local by spelling, and a second site inside a function that
already had a row folded into that row. The script now exits 1 on a missing root, a file that does not parse, an
unknown import, no sites, an unclassified site, a stale row, a road with no table entry, and any figure that differs
from the committed counts (scripts/network-inventory-expected.json); it walks its roots recursively, classes a program
whose far end its argv does not derive as external-program (never set aside), places a browser fetch by its URL, names
the four classes it cannot see in its --table output, and prints the ledger's table from the sites. The classes below
run it by subprocess with the repository's python: over the tree (clean, against the committed counts), over a copy of
the scanned scope with one mutation at a time (each red the round reproduced or named, now a pin), or with a class's
row-less mutations planted together and read from one run (_SharedRun, whose docstring says why that loses nothing),
over two tiny roots (no sites; a missing root), and --table against the block the ledger entry carries between its two
marker lines. The
script loads no romp code and neither does this module, so no state root is minted here either; the copy lives under
the run's temp root (tests/__init__.py's hook removes it, and tearDownModule does too).

The third round of the review (2026-09-22) found the completeness claim holding for the Python half alone: the shell and
browser scans were closed tool lists with no interpreter arm and no import gate, a program site in the browser or editor
code carried no class whatever its argv, the one npx in the tree was no site, and the Python import gate did not reach
importlib.import_module. The classes from TheShellSideHasAnInterpreterArm on pin the widening by execution over the scope
copy: a shell interpreter text (python3 -c, the heredoc shape, node -e) is a site keyed file plus tool in the
external-program class and needs a row; npx, scp, rsync, sftp and nc are tools; the child_process family is a site only
through its binding (a bare exec( with none is RegExp exec) and is classed by its argv, so the four live program sites
carry the class and leave the local count; net, tls, XMLHttpRequest and sendBeacon are sites; a package the browser and
editor code imports outside KNOWN_JS_IMPORTS fails the run, as does a module named to import_module outside KNOWN_IMPORTS
or one the scan cannot resolve; a socket's sendto and the event loop's connections are sites; the committed counts carry
the program head per Python command site, so a same-count swap of a local tool for curl inside a rowed function is a
COUNTS line naming the key and the head; a socket primitive on a receiver the scan cannot resolve is stated as a named
class and held to the behaviour by a planted call the run does not see; and the git boundary is pinned by two plants (a
row-less git checkout is UNCLASSIFIED with no class tag, a bare git with a runtime subcommand carries it). Each case is
green at the tree and red over a copy of the script with its arm removed (the round's record names the mutation).
"""
import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


# ---- the census script, run from the suite ------------------------------------------------------------------------------

INVENTORY = os.path.join("scripts", "network-inventory.py")
EXPECTED = os.path.join("scripts", "network-inventory-expected.json")
SCOPE_DIRS = ("kernel", "cli", "postal", "bin", "hooks", "ui", "vscode-extension/src")   # the script's declared roots
SCOPE_FILES = ("bootstrap.sh", "install.sh", "vscode-extension/install.sh", "tools/file-comments-host.mjs", INVENTORY, EXPECTED)
LEDGER = os.path.join("upstream", "2026-09-20-price-feed-off.md")
BEGIN, END = "<!-- network-inventory: table begin -->", "<!-- network-inventory: table end -->"
SUMMARY = re.compile(r"^--- (?P<sites>\d+) sites, (?P<roads>\d+) roads \((?P<local_roads>\d+) of them local\), (?P<local_sites>\d+) local sites "
                     r"set aside, (?P<unclassified>\d+) unclassified; (?P<external>\d+) external-program, (?P<runtime>\d+) runtime-program, "
                     r"(?P<computed>\d+) browser-computed-url, (?P<dom>\d+) browser-dom-loads; (?P<files>\d+) files scanned, (?P<skipped>\d+) skipped by kind$", re.M)
FEED_LITERAL = "https://TESTHOST/prices.json"   # a synthetic URL: the bypass the census must catch spells the host as a literal
SITE_LINE = re.compile(r"^\S+:\d+  ")


def inventory(root, *flags):
    """Run <root>/scripts/network-inventory.py over root with the repository's python: (exit code, stdout, stderr)."""
    p = subprocess.run([sys.executable, os.path.join(root, INVENTORY)] + list(flags) + [root], capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


_TREE = {}


def tree_run(*flags):
    """The tree's own run, once per process and shared by the cases: the tree is never mutated."""
    if flags not in _TREE:
        _TREE[flags] = inventory(ROOT, *flags)
    return _TREE[flags]


def summary(out):
    m = SUMMARY.search(out)
    return {k: int(v) for k, v in m.groupdict().items()} if m else None


def unclassified(out):
    """The file:line tokens the UNCLASSIFIED line names, as a set."""
    for ln in out.splitlines():
        if ln.startswith("UNCLASSIFIED "):
            return set(ln.split(": ", 1)[0].split()[1:])
    return set()


def gates(out):
    """The run's output without the site lines: the summary and the gate lines, for a failure message."""
    return "\n".join(ln for ln in out.splitlines() if not SITE_LINE.match(ln))


_COPY = []


def scope_copy():
    """One copy of the scanned scope per process (the declared roots, the named files, the script and its counts), made on
    first use under the run's temp root; every mutation a case makes is restored by that case's cleanup."""
    if not _COPY:
        root = tempfile.mkdtemp(prefix="census-scope-")
        for d in SCOPE_DIRS:
            shutil.copytree(os.path.join(ROOT, d), os.path.join(root, d), symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        for f in SCOPE_FILES:
            os.makedirs(os.path.dirname(os.path.join(root, f)), exist_ok=True)
            if f == EXPECTED and not os.path.isfile(os.path.join(ROOT, f)):
                continue   # a tree without the committed counts: the script's own COUNTS gate reports the absence
            shutil.copy2(os.path.join(ROOT, f), os.path.join(root, f))
        _COPY.append(root)
    return _COPY[0]


def tearDownModule():
    for root in _COPY:
        shutil.rmtree(root, ignore_errors=True)
    del _COPY[:]


def _plant(rel, text, cleanup):
    """Write (or overwrite) rel under the copy and hand `cleanup` the undo (a new file is removed again, its made
    directories with it; an existing one is restored): a case passes its addCleanup, a shared run its undo list."""
    path = os.path.join(scope_copy(), rel)
    existed = os.path.exists(path)
    old = None
    if existed:
        with open(path, encoding="utf-8") as f:
            old = f.read()
    made = []
    d = os.path.dirname(path)
    while not os.path.isdir(d):
        made.append(d)
        d = os.path.dirname(d)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    def restore():
        if existed:
            with open(path, "w", encoding="utf-8") as f:
                f.write(old)
        else:
            os.remove(path)
            for m in made:
                os.rmdir(m)
    cleanup(restore)
    return path


def _append(rel, text, cleanup):
    with open(os.path.join(scope_copy(), rel), encoding="utf-8") as f:
        old = f.read()
    return _plant(rel, old + ("" if old.endswith("\n") else "\n") + text, cleanup)


def _replace(rel, old, new, cleanup):
    with open(os.path.join(scope_copy(), rel), encoding="utf-8") as f:
        text = f.read()
    if text.count(old) != 1:
        raise AssertionError("the mutation's anchor %r occurs %d times in %s, not once" % (old[:60], text.count(old), rel))
    return _plant(rel, text.replace(old, new), cleanup)


def _lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


class _Scope(unittest.TestCase):
    """Mutations over the scope copy, each undone by cleanup, and the assertions the copy's runs share."""

    def plant(self, rel, text):
        """Write (or overwrite) rel under the copy; a new file is removed again, an existing one restored."""
        return _plant(rel, text, self.addCleanup)

    def append(self, rel, text):
        return _append(rel, text, self.addCleanup)

    def replace(self, rel, old, new):
        return _replace(rel, old, new, self.addCleanup)

    def move(self, rel, to):
        root = scope_copy()
        src, dst = os.path.join(root, rel), os.path.join(root, to)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)

        def restore():
            os.rename(dst, src)
            d = os.path.dirname(dst)
            while d != root and not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
        self.addCleanup(restore)

    def lines(self, path):
        return _lines(path)

    def assertRefused(self, rc, out, *needles):
        self.assertNotEqual(rc, 0, "the run must exit non-zero:\n" + gates(out))
        for n in needles:
            self.assertIn(n, out, "the run must name %r:\n%s" % (n, gates(out)))

    def assertClean(self, rc, out):
        self.assertEqual(rc, 0, "the run must exit 0:\n" + gates(out))
        got = summary(out)
        self.assertIsNotNone(got, "the summary line has the committed shape (the totals, the class counts, the files):\n" + gates(out))
        self.assertEqual(got["unclassified"], 0)

    def assertListed(self, out, pattern, msg=""):
        """A site line matching the pattern is in the run's listing (the failure quotes the lines of that file, not the run)."""
        if not re.search(pattern, out, re.M):
            head = pattern.split(":")[0].replace("\\", "")
            self.fail("no listed line matches %r%s\n%s\n%s" % (pattern, (": " + msg) if msg else "", gates(out),
                      "\n".join(ln for ln in out.splitlines() if ln.startswith(head))))


_SHARED = {}   # run name -> (exit code, stdout) of the one run the classes naming it read


class _SharedRun(_Scope):
    """Classes whose row-less mutation cases read ONE run over the scope copy. Every class naming the same RUN plants its
    mutations (`mutate`, recording line numbers in cls.at) on the copy in definition order, the script runs once, and every
    mutation is undone before any case runs, so a case of the class with a mutation of its own still starts from the clean
    copy; the cases read the run as self.rc and self.out. One child process per run instead of one per case: the serial CI
    cell's growth after the third round (2026-09-22) was these runs, at about 3.5 s each on the box, and the cell reached
    its 25-minute wall.

    A run shared this way is exactly as strict as one run per case because of what the shared cases assert: a property
    keyed on a file and a line (a site named UNCLASSIFIED at file:line, the tag on that line's listing, an IMPORT line at
    file:line, a STALE ROW or COUNTS line naming the case's own key, a line NOT listed), never a figure of the whole run.
    The mutations touch different files, or blocks appended in turn to one file with each block's lines recorded as it
    lands, so no block moves another's lines; a second block adds sites at its own lines only, which can fail another
    case's negative (a line it says is no site becoming one) and cannot satisfy its positive. Names two blocks plant in one
    Python file differ, since the scan resolves a module constant by its last assignment. A case that asserts a figure of
    the whole run (a class count, an empty UNCLASSIFIED set, a clean summary equal to the tree's) keeps a run of its own."""

    RUN = None      # the run the class reads; classes naming the same run mutate one copy and read one output
    MEMBERS = {}    # run name -> the classes naming it, in definition order (the order their mutations land)
    at = None       # the line numbers `mutate` recorded, per class

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if cls.RUN:
            _SharedRun.MEMBERS.setdefault(cls.RUN, []).append(cls)

    @classmethod
    def mutate(cls, cleanup):
        """Plant the class's mutations with _plant, _append and _replace, passing `cleanup`, and record lines in cls.at."""
        raise NotImplementedError

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.RUN not in _SHARED:
            undo = []
            try:
                for member in _SharedRun.MEMBERS[cls.RUN]:
                    member.at = {}
                    member.mutate(undo.append)
                rc, out, _ = inventory(scope_copy())
                _SHARED[cls.RUN] = (rc, out)
            finally:
                for f in reversed(undo):
                    f()
        cls.rc, cls.out = _SHARED[cls.RUN]


def _expected():
    with open(os.path.join(ROOT, EXPECTED), encoding="utf-8") as f:
        return json.load(f)


class TheCensusRunsFromTheSuite(_Scope):
    """The instrument is run by the suite (and so by CI's Python job), against counts committed beside it."""

    def test_the_tree_runs_clean_against_the_committed_counts(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, EXPECTED)), "%s exists: the committed counts the run is compared against "
                        "(python3 %s --write-expected on a clean tree writes it)" % (EXPECTED, INVENTORY))
        expected = _expected()
        rc, out, err = tree_run()
        self.assertClean(rc, out)
        got = summary(out)
        self.assertIsNotNone(got, "the summary line has the committed shape")
        for name in ("sites", "roads", "local_roads", "local_sites"):
            self.assertEqual(got[name], expected[name], name)
        self.assertEqual((got["external"], got["runtime"], got["computed"], got["dom"]),
                         tuple(expected["classes"][c] for c in ("external-program", "runtime-program", "browser-computed-url", "browser-dom-loads")))
        self.assertGreater(got["sites"], 200, "a floor: the scan opened the runtime trees")
        self.assertEqual(sum(expected["per_road"].values()) + got["computed"], got["sites"], "every site has a road or is the computed-URL class")
        self.assertEqual(sum(expected["per_key"].values()), got["sites"], "the committed row-key counts sum to the sites")

    def test_the_copy_runs_clean_like_the_tree(self):
        """The control for every mutation case below: the copy alone reads as the tree does."""
        rc, out, _ = inventory(scope_copy())
        self.assertEqual(rc, 0, "the run must exit 0:\n" + gates(out))
        rc2, out2, _ = tree_run()
        line = lambda text: re.sub(r"; \d+ files scanned.*$", "", next(ln for ln in text.splitlines() if ln.startswith("--- ")))
        self.assertEqual(line(out), line(out2), "the copy's summary is the tree's (a copy that reads differently is a broken copy, not a pin)")

    def test_the_committed_counts_are_the_scripts_own_output(self):
        """--write-expected on the clean copy writes what the tree carries: the file has one author, the script."""
        self.plant(EXPECTED, "{}\n")
        rc, out, _ = inventory(scope_copy(), "--write-expected")
        self.assertEqual(rc, 0, gates(out))
        with open(os.path.join(scope_copy(), EXPECTED), encoding="utf-8") as f:
            written = json.load(f)
        self.assertEqual(written, _expected(), "the committed counts are stale: run python3 %s --write-expected and commit the diff" % INVENTORY)

    def test_a_scan_that_loses_a_file_is_refused_naming_the_figure(self):
        """The round's reproduction: kernel/kernel.py one directory down. The flat walk of the earlier script found 165 sites
        where it had found 266 and exited 0; now the moved file is scanned where it sits, so every row keyed on its old path
        is stale, every site under the new path has no row, and the row-key counts differ."""
        self.move("kernel/kernel.py", "kernel/sub/kernel.py")
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "STALE ROW kernel/kernel.py:_refresh_remote_prices.work",
                           "COUNTS per_key kernel/kernel.py:_refresh_remote_prices.work: the committed count is 1, this run found None",
                           "UNCLASSIFIED")
        self.assertTrue(any(t.startswith("kernel/sub/kernel.py:") for t in unclassified(out)), "the moved file's sites are found and named at their new path")

    def test_a_scan_that_loses_sites_is_refused_on_the_total(self):
        """A file gone (emptied, not moved): the total is the loud figure, beside the stale rows."""
        self.plant("kernel/kernel.py", "")
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "STALE ROW kernel/kernel.py:_refresh_remote_prices.work")
        expected = _expected()
        lost = sum(v for k, v in expected["per_key"].items() if k.startswith("kernel/kernel.py:"))
        self.assertGreater(lost, 90, "kernel/kernel.py carries a third of the sites: the figure the round measured")
        self.assertRefused(rc, out, "COUNTS sites: the committed count is %d, this run found %d" % (expected["sites"], expected["sites"] - lost))

    def test_write_expected_is_refused_while_any_other_gate_fails(self):
        self.move("kernel/kernel.py", "kernel/sub/kernel.py")
        path = os.path.join(scope_copy(), EXPECTED)
        before = None
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                before = f.read()
        rc, out, _ = inventory(scope_copy(), "--write-expected")
        self.assertRefused(rc, out, "not written: " + EXPECTED, "STALE ROW")
        after = None
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                after = f.read()
        self.assertEqual(after, before, "the counts file is untouched by a refused write")

    def test_no_sites_and_a_missing_root_are_each_refused_by_name(self):
        for missing in (None, "kernel"):
            tiny = tempfile.mkdtemp(prefix="census-tiny-")
            for d in SCOPE_DIRS:
                if d != missing:
                    os.makedirs(os.path.join(tiny, d))
            os.makedirs(os.path.join(tiny, "scripts"))
            shutil.copy2(os.path.join(ROOT, INVENTORY), os.path.join(tiny, INVENTORY))
            rc, out, _ = inventory(tiny)
            self.assertRefused(rc, out, "NO SITES found", "SCOPE the named file bootstrap.sh is missing", "COUNTS %s is missing" % EXPECTED)
            if missing:
                self.assertIn("SCOPE the declared root kernel/ is missing", gates(out))
            else:
                self.assertNotIn("declared root", gates(out))


class TheWalkIsRecursiveOverTheDeclaredScope(_SharedRun):
    """The declared scope and the walk are held equal by execution: a file below a root and a hook of any kind are opened.
    One run (_SharedRun) carries the five plants: a Python file one directory down, a site appended to the node hook, a new
    shell hook, a Python fixture below the webview root and a program reference in kernel/credentials.py; each case's
    property is a file's own line in UNCLASSIFIED or in a gate line, or a file's absence from them."""

    RUN = "walk"

    @classmethod
    def mutate(cls, cleanup):
        _plant("kernel/sub/extra.py", "import urllib.request\n\ndef _warm():\n    return urllib.request.urlopen(%r, timeout=4)\n" % FEED_LITERAL, cleanup)
        # a node hook (the one in the tree, hooks/romp-track-bash-guard.mjs, is read: a site appended to it is named), a new
        # shell hook with the ordinary ssh spelling, and a Python fixture below the webview root, which is skipped by kind
        _append("hooks/romp-track-bash-guard.mjs", "fetch(%r);\n" % FEED_LITERAL, cleanup)
        _plant("hooks/probe.sh", "#!/usr/bin/env bash\nssh TESTHOST uptime\n", cleanup)
        _plant("ui/webview/anchor-map-fixtures/probe.py", "import urllib.request\nurllib.request.urlopen(%r)\n" % FEED_LITERAL, cleanup)
        _append("kernel/credentials.py", '\n_PROBE_HOST = "tools/probe-host.mjs"\n', cleanup)

    def test_a_site_one_directory_down_is_found(self):
        self.assertRefused(self.rc, self.out, "UNCLASSIFIED")
        self.assertIn("kernel/sub/extra.py:4", unclassified(self.out))

    def test_every_hook_is_scanned_whatever_its_extension_and_a_fixture_of_another_kind_is_not(self):
        out = self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        self.assertIn("hooks/probe.sh:2", named, "ssh <host> <command> in a shell hook is a site")
        self.assertTrue(any(t.startswith("hooks/romp-track-bash-guard.mjs:") for t in named), "the node hook is scanned: %r" % named)
        self.assertFalse(any("anchor-map-fixtures" in t for t in named), "ui/ is read for the browser kinds only")
        self.assertFalse([ln for ln in out.splitlines() if ln.startswith("PARSE")], "the fixture directory's Python is not parsed:\n" + gates(out))

    def test_a_program_the_kernel_runs_from_an_unscanned_directory_is_a_gate(self):
        self.assertRefused(self.rc, self.out, "PROGRAM kernel/credentials.py:", "names 'tools/probe-host.mjs'")


MUTANT_PROGRAMS = '''

def _probe_sh():
    return subprocess.run(["sh", "-c", "true"], check=False)

def _probe_node():
    return subprocess.run(["node", "-e", "1"], check=False)

def _probe_python():
    return subprocess.run([sys.executable, "-m", "pip", "download", "x"], check=False)

def _probe_argv(argv):
    return subprocess.Popen(argv)

def _probe_git_remote():
    return subprocess.run(["git", "remote", "update"], check=False)

def _probe_ps():
    return subprocess.run(["ps", "-o", "pid="], check=False)
'''


class AnExternalProgramIsNeverLocalByDefault(_Scope):
    """A shell, an interpreter, the running python, an argv the code does not spell out and a git subcommand that can fetch
    are not placed by any default rule: each needs a row. A fixed literal of a local tool still is, and the committed row-key
    count catches it as a new key."""

    def test_each_spelling_needs_a_row_and_a_fixed_local_tool_is_a_new_key(self):
        lines = self.lines(self.append("kernel/credentials.py", MUTANT_PROGRAMS))
        at = {name: next(i + 2 for i, ln in enumerate(lines) if ln.startswith("def %s(" % name))
              for name in ("_probe_sh", "_probe_node", "_probe_python", "_probe_argv", "_probe_git_remote", "_probe_ps")}
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        for name in ("_probe_sh", "_probe_node", "_probe_python", "_probe_argv", "_probe_git_remote"):
            self.assertIn("kernel/credentials.py:%d" % at[name], named, "%s is unclassified without a row" % name)
        self.assertNotIn("kernel/credentials.py:%d" % at["_probe_ps"], named, "a fixed literal of a local tool is placed by the default rule")
        self.assertRefused(rc, out, "COUNTS per_key kernel/credentials.py:_probe_ps: the committed count is None, this run found 1")
        for name in ("_probe_sh", "_probe_node", "_probe_python", "_probe_argv"):
            self.assertListed(out, r"kernel/credentials\.py:%d  .*  in %s  -> UNCLASSIFIED \[external-program\]" % (at[name], name),
                             "the site is listed in its class, so the table's count moves with it")

    def test_the_class_members_are_listed_with_their_road_and_not_set_aside(self):
        rc, out, _ = tree_run()
        self.assertEqual(rc, 0, "the run must exit 0:\n" + gates(out))
        self.assertListed(out, r"kernel/judge\.py:\d+  run  sh -c  in _serve_fault  -> local-program \[external-program\]",
                         "a shell on a local road keeps its row and is marked as the class")
        self.assertListed(out, r"kernel/kernel\.py:\d+  run  /bin/sh  in _watch_run  -> predicate-watch \[runtime-program\]")
        self.assertListed(out, r"kernel/credentials\.py:\d+  run  RUNTIME-SUPPLIED\(cmd\) SHELL  in run_helper  -> api-key-helper \[runtime-program\]")
        self.assertClean(rc, out)
        rows = [ln for ln in out.splitlines() if SITE_LINE.match(ln) and "  dom-load  " not in ln]
        local_roads = ("local-bus", "local-manager", "local-kernel", "local-program", "local-git")
        tails = [ln.rsplit("-> ", 1)[1] for ln in rows]
        set_aside = sum(1 for t in tails if t.split(" ")[0] in local_roads and "[" not in t)
        self.assertEqual(summary(out)["local_sites"], set_aside, "the local count excludes every classed site")
        self.assertEqual(summary(out)["external"], sum(1 for t in tails if t.endswith("[external-program]")))
        self.assertEqual(summary(out)["runtime"], sum(1 for t in tails if t.endswith("[runtime-program]")))


class TheBrowserFetchIsClassifiedByItsUrl(_Scope):
    """A fetch under ui/ is local only by its argument: a relative literal or a kernel-URL helper. An absolute literal needs
    a row; a computed argument is the named class, whose committed count moves."""

    def test_an_absolute_literal_needs_a_row_a_helper_is_local_and_a_variable_is_the_class(self):
        n = len(self.lines(self.append("ui/webview/strip.ts", '\nexport function probeFetches(u: string): void {\n  void fetch("https://TESTHOST/x");\n'
                                       '  void fetch(kernelUrl("/probe"));\n  void fetch("/probe");\n  void fetch(u);\n}\n')))
        absolute, helper, relative, computed = n - 4, n - 3, n - 2, n - 1
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        self.assertIn("ui/webview/strip.ts:%d" % absolute, named, "a literal to another host is a road and needs a row")
        for line in (helper, relative, computed):
            self.assertNotIn("ui/webview/strip.ts:%d" % line, named)
        self.assertListed(out, r"ui/webview/strip\.ts:%d  fetch  fetch\(kernelUrl\(\"/probe\"\)\)  in -  -> local-kernel" % helper)
        self.assertListed(out, r"ui/webview/strip\.ts:%d  fetch  fetch\(\"/probe\"\)  in -  -> local-kernel" % relative)
        self.assertListed(out, r"ui/webview/strip\.ts:%d  fetch  fetch\(u\)  in -  -> \(browser-computed-url\)" % computed)
        expected = _expected()
        self.assertRefused(rc, out, "COUNTS classes browser-computed-url: the committed count is %d, this run found %d"
                           % (expected["classes"]["browser-computed-url"], expected["classes"]["browser-computed-url"] + 1),
                           "COUNTS per_key ui/webview/strip.ts:fetch: the committed count is %d, this run found %d"   # the four new lines share the key
                           % (expected["per_key"]["ui/webview/strip.ts:fetch"], expected["per_key"]["ui/webview/strip.ts:fetch"] + 4))

    def test_the_copy_image_handler_reads_a_computed_url_and_is_not_a_browser_figures_site(self):
        """extra8-4 by execution: the lightbox's re-fetch reads the shown img's src (the kernel's own file URL by its binding),
        so it sits in the computed-URL class, not on the browser-figures road and not local by path."""
        rc, out, _ = tree_run()
        self.assertEqual(rc, 0, "the run must exit 0:\n" + gates(out))
        self.assertListed(out, r"ui/webview/preview\.ts:\d+  fetch  fetch\(src\)  in -  -> \(browser-computed-url\)")
        figures = [ln for ln in out.splitlines() if ln.endswith("-> browser-figures")]
        self.assertEqual(sorted(ln.split("  ")[1] for ln in figures), ["Image", "figureHosts"], figures)


class ThePrimitiveListIsKeptHonest(_Scope):
    """NET is a closed list, so the import side is the gate: a module the census does not know fails the run; and the
    primitives the round named beyond the list (a bound socket's connect, asyncio's connections) are sites."""

    def test_an_unknown_import_is_the_loud_line(self):
        n = len(self.lines(self.append("kernel/credentials.py", "\nimport httpx\n")))
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "IMPORT kernel/credentials.py:%d imports httpx" % n)

    def test_a_known_import_is_not(self):
        self.append("kernel/credentials.py", "\nimport json as _probe_json\n")
        rc, out, _ = inventory(scope_copy())
        self.assertFalse([ln for ln in out.splitlines() if ln.startswith("IMPORT")], gates(out))

    def test_a_bound_sockets_connect_and_an_asyncio_connection_are_sites(self):
        n = len(self.lines(self.append("kernel/credentials.py", '\nimport asyncio, socket\n\ndef _probe_sock(addr):\n    s = socket.socket()\n    s.connect(addr)\n\n'
                                       'async def _probe_aio():\n    return await asyncio.open_connection("TESTHOST", 443)\n')))
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        self.assertIn("kernel/credentials.py:%d" % (n - 3), named, "s.connect(addr) on a socket bound in the function")
        self.assertIn("kernel/credentials.py:%d" % n, named, "asyncio.open_connection")


class ASecondSiteInsideARowedFunctionIsRed(_Scope):
    """The table is keyed on file and function; the committed count per key is the guard for a second site inside a rowed
    function, a stale row is its own gate, and the table's road list is held equal to the rows' roads."""

    def test_a_second_urlopen_inside_the_workers_function_is_named_by_its_key(self):
        anchor = "                with urllib.request.urlopen(PRICE_FEED_URL, timeout=4) as r:\n"
        self.replace("kernel/kernel.py", anchor, "                urllib.request.urlopen(%r, timeout=4)\n" % FEED_LITERAL + anchor)
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "COUNTS per_key kernel/kernel.py:_refresh_remote_prices.work: the committed count is 1, this run found 2")
        self.assertFalse(unclassified(out), "the second site takes the row; the count is what names it: %r" % unclassified(out))
        self.assertEqual(len(re.findall(r"kernel/kernel\.py:\d+  urlopen  .*  in _refresh_remote_prices\.work  -> price-feed", out)), 2,
                         "both sites are listed, so the new line is readable")

    def test_a_fetch_of_the_feeds_url_spelled_as_a_literal_in_a_new_function_is_unclassified(self):
        """correctness-3: the module's first half keys on the NAME PRICE_FEED_URL; this run keys on the primitive."""
        n = len(self.lines(self.append("kernel/kernel.py", "\n\ndef _warm_prices():\n    import urllib.request\n    return urllib.request.urlopen(%r, timeout=4)\n" % FEED_LITERAL)))
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "UNCLASSIFIED")
        self.assertIn("kernel/kernel.py:%d" % n, unclassified(out))

    def test_a_row_naming_no_site_is_stale(self):
        self.replace(INVENTORY, '_t("price-feed", K + "_refresh_remote_prices.work")', '_t("price-feed", K + "_refresh_remote_prices.work", K + "_no_such_function")')
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "STALE ROW kernel/kernel.py:_no_such_function names no site")

    def test_the_tables_roads_and_the_rows_roads_are_one_set(self):
        self.replace(INVENTORY, '("price-feed", "price feed (kernel-request)",', '("price-feed-x", "price feed (kernel-request)",')
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "TABLE the road price-feed has sites and no ROADS entry", "TABLE ROADS names price-feed-x, a road with no site")


# The two sentences the docstring, the --table output and SECURITY.md's Network access section share: held here
# by execution beside the planted call the scan does not see, so neither can outlive the behaviour.
RESIDUAL = ("a socket primitive called on a receiver the census cannot resolve (an attribute-held or parameter socket) is not a "
            "site here")
DISCLOSURE = ("The shell and browser sides are matched by a named list with no completeness gate: a tool or a client the lists "
              "do not name is no site and no line; the Python side's gate is module-granular: an import outside the allow-list "
              "fails the run, and a primitive of a known module outside NET and SUB is not a site.")
UNSEEN_LABEL = "a socket primitive on a receiver this scan cannot resolve (not derivable by this scan)"


def _inventory_docstring():
    """The script's module docstring with its line wraps folded to single spaces, so a sentence is matched whole."""
    with open(os.path.join(ROOT, INVENTORY), encoding="utf-8") as f:
        return " ".join((ast.get_docstring(ast.parse(f.read())) or "").split())


def _listed(out, prefix):
    """The site lines of one file in the run's listing."""
    return [ln for ln in out.splitlines() if ln.startswith(prefix) and SITE_LINE.match(ln)]


SERVICE_TEXT = "_probe_fetch() {\n    python3 -c 'import urllib.request, sys; urllib.request.urlopen(sys.argv[1]).read()' %r\n}\n" % FEED_LITERAL
WAKE_TEXT = ("python3 - \"$1\" <<'PY'\nimport sys\nprint(sys.argv[1])\nPY\n"
             "node -e 'fetch(%r)'\n"
             "rsync -a \"$d\" TESTHOST:/srv/x\n"
             "scp \"$f\" TESTHOST:/srv/x\n"
             "sftp TESTHOST\n"
             "nc TESTHOST 443\n"
             "npx --yes some-package\n"
             "[ -e \"$f\" ] && grep -c romp \"$f\"\n"
             "\"$PY\" -c pass\n" % FEED_LITERAL)
WAKE_STARTS = (("heredoc", "python3 - "), ("node", "node -e"), ("rsync", "rsync "), ("scp", "scp "), ("sftp", "sftp "), ("nc", "nc "),
               ("npx", "npx "), ("flags", "[ -e"), ("variable", '"$PY" -c'))
NPX_LINE, NPX_GONE = "npx --yes @vscode/vsce package", "# the package step removed in this copy: vsce package"


class TheShellSideHasAnInterpreterArm(_SharedRun):
    """An interpreter head (python, python3, node, perl, sh, bash) followed by -c or -e, or by a bare `-` (the heredoc
    shape), is a site keyed file plus tool in the external-program class, and needs a row like every member; npx, scp,
    rsync, sftp and nc are tools. Before the round's fix a urllib call inside `python3 -c` in a shell script was no site
    and exit 0 (correctness-1, extra6-1 of the third round). The shared run carries three files: the row-less python3 -c
    text in bin/romp-service, the nine lines in hooks/romp-wake.sh and vscode-extension/install.sh with its npx line
    removed; the rowed text's case reads the whole run's class count and runs alone."""

    RUN = "shell"

    @classmethod
    def mutate(cls, cleanup):
        # bin/romp-service has rows for its curl and its heredoc; a python3 -c text is a new tool and so a new key
        cls.at["service"] = len(_lines(_append("bin/romp-service", SERVICE_TEXT, cleanup))) - 1
        # hooks/romp-wake.sh has a curl row and nothing else: every new tool below is a new key with no row
        lines = _lines(_append("hooks/romp-wake.sh", WAKE_TEXT, cleanup))
        cls.at.update({name: next(i + 1 for i, ln in enumerate(lines) if ln.startswith(start)) for name, start in WAKE_STARTS})
        _replace("vscode-extension/install.sh", NPX_LINE, NPX_GONE, cleanup)

    def test_an_inline_interpreter_text_in_a_rowed_shell_file_needs_its_own_row_and_carries_the_class(self):
        n, out = self.at["service"], self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        self.assertIn("bin/romp-service:%d" % n, unclassified(out), "the python3 -c text is a site with no row")
        self.assertListed(out, r"bin/romp-service:%d  python3 -c  .*  in -  -> UNCLASSIFIED \[external-program\]" % n,
                          "the site is keyed on the interpreter and its flag and classed, so the class count moves with it")

    def test_the_same_text_with_a_row_is_listed_on_its_road_with_the_class(self):
        n = len(self.lines(self.append("bin/romp-service", SERVICE_TEXT))) - 1
        self.replace(INVENTORY, "LOCAL_ROADS = {", '_t("local-program", "bin/romp-service:python3 -c")\nLOCAL_ROADS = {')   # a row planted before the road sets
        rc, out, _ = inventory(scope_copy())   # a run of its own: the empty UNCLASSIFIED set and the class count are the whole run's
        self.assertFalse(unclassified(out), "the row places the site: %r" % unclassified(out))
        self.assertListed(out, r"bin/romp-service:%d  python3 -c  .*  in -  -> local-program \[external-program\]" % n,
                          "a rowed interpreter site keeps its class whatever road the row names")
        expected = _expected()
        self.assertRefused(rc, out, "COUNTS per_key bin/romp-service:python3 -c: the committed count is None, this run found 1",
                           "COUNTS classes external-program: the committed count is %d, this run found %d"
                           % (expected["classes"]["external-program"], expected["classes"]["external-program"] + 1))

    def test_the_heredoc_shape_node_e_and_the_five_tools_are_sites_and_a_variable_head_and_a_bare_flag_are_not(self):
        at, out = self.at, self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        for name in ("heredoc", "node", "rsync", "scp", "sftp", "nc", "npx"):
            self.assertIn("hooks/romp-wake.sh:%d" % at[name], named, "%s is a site with no row" % name)
        self.assertListed(out, r"hooks/romp-wake\.sh:%d  python3 -  .*  -> UNCLASSIFIED \[external-program\]" % at["heredoc"], "the heredoc shape: the head with a bare - argument")
        self.assertListed(out, r"hooks/romp-wake\.sh:%d  node -e  .*  -> UNCLASSIFIED \[external-program\]" % at["node"])
        for name in ("rsync", "scp", "sftp", "nc", "npx"):
            self.assertListed(out, r"hooks/romp-wake\.sh:%d  %s  .*  -> UNCLASSIFIED$" % (at[name], name), "a named tool, not an interpreter: no class tag")
        for name in ("flags", "variable"):
            self.assertNotIn("hooks/romp-wake.sh:%d" % at[name], named)
            self.assertFalse([ln for ln in _listed(out, "hooks/romp-wake.sh:%d  " % at[name])],
                             "%s: the arm keys on an interpreter head, never on -c or -e alone, and a head held in a variable is the stated residual" % name)

    def test_the_trees_interpreter_sites_are_rowed_and_classed_and_the_npx_line_is_rowed_on_install_ext(self):
        rc, out, _ = tree_run()
        self.assertEqual(rc, 0, "the run must exit 0:\n" + gates(out))
        self.assertListed(out, r"bin/romp:\d+  python3 -c  .*  in -  -> local-kernel \[external-program\]")
        self.assertListed(out, r"bin/romp:\d+  python3 -  .*  in -  -> local-kernel \[external-program\]")
        self.assertListed(out, r"hooks/romp-postal-ensure\.sh:\d+  python3 -c  .*  in -  -> local-kernel \[external-program\]")
        self.assertListed(out, r"bin/romp-uninstall:\d+  python3 -  .*  in -  -> local-program \[external-program\]")
        self.assertListed(out, r"vscode-extension/install\.sh:\d+  node -e  .*  in -  -> install-ext \[external-program\]")
        self.assertListed(out, r"vscode-extension/install\.sh:\d+  npx  npx --yes @vscode/vsce package .*  in -  -> install-ext$",
                          "the vsce fetch is rowed on install-ext with no class tag: a named tool")
        expected = _expected()
        self.assertEqual(expected["per_key"]["vscode-extension/install.sh:npx"], 1)
        self.assertGreater(expected["per_key"]["bin/romp:python3 -c"], 50, "bin/romp's inline texts are the bulk of the class")

    def test_the_npx_line_removed_is_a_stale_row(self):
        self.assertRefused(self.rc, self.out, "STALE ROW vscode-extension/install.sh:npx names no site")


EXEC_TEXT = ('\nfunction exec(s: string): string {\n  return s;\n}\nexport function probePrograms(): void {\n  child_process.exec("ls -la", () => {});\n'
             '  require("child_process").execFile("ls", ["-la"]);\n  void exec("not a program");\n  void /x/.exec("not a program either");\n}\n')
SPAWN_TEXT = 'import { spawn } from "child_process";\n\nexport function probe(): void {\n  spawn(process.execPath, ["-e", "1"]);\n}\n'
CONNECTIONS_TEXT = ('\nexport function probeConnections(u: string): void {\n  net.connect(443, "TESTHOST");\n  net.createConnection({ host: "TESTHOST", port: 443 });\n'
                    '  tls.connect(443, "TESTHOST");\n  const x = new XMLHttpRequest();\n  void x;\n  navigator.sendBeacon(u);\n}\n')
IMPORTS_TEXT = ('\nimport * as fs from "node:fs";\nimport { probe } from "./probe-spawn";\nimport {\n  createSocket,\n} from "dgram";\nconst net = require("net");\n'
                'void fs; void probe; void createSocket; void net;\n')
DYNAMIC_TEXT = '\nexport async function probeImports(u: string): Promise<void> {\n  await import(u);\n  await import("./probe-spawn");\n  await import("dgram");\n}\n'


class TheBrowserSideHasTheChildProcessFamilyAndTheConnectionPrimitives(_SharedRun):
    """A child_process call is a site through its binding (`child_process.<fn>(`, `require('child_process').<fn>(`, a
    namespace or a bare name the file binds from the module), never as a bare `exec(`, which RegExp spells the same way;
    net.connect, net.createConnection, tls.connect, XMLHttpRequest and sendBeacon are sites; a package outside
    KNOWN_JS_IMPORTS fails the run (correctness-1, extra6-1 of the third round). The shared run carries four blocks
    appended in turn to ui/webview/strip.ts (the exec shapes, the connections, the imports, the dynamic imports), each
    case's lines read as its block lands, and the new file probe-spawn.ts; none of the blocks binds a child_process name
    into strip.ts, so the first block's bare exec( stays unbound whatever lands after it. The rowed program site's case
    reads the whole run's class count and runs alone."""

    RUN = "browser"

    @classmethod
    def mutate(cls, cleanup):
        n = len(_lines(_append("ui/webview/strip.ts", EXEC_TEXT, cleanup)))
        cls.at.update(qualified=n - 4, inline=n - 3, bare=n - 2, regexp=n - 1)
        _plant("ui/webview/probe-spawn.ts", SPAWN_TEXT, cleanup)
        n = len(_lines(_append("ui/webview/strip.ts", CONNECTIONS_TEXT, cleanup)))
        cls.at.update({"net.connect": n - 6, "net.createConnection": n - 5, "tls.connect": n - 4, "XMLHttpRequest": n - 3, "sendBeacon": n - 1})
        n = len(_lines(_append("ui/webview/strip.ts", IMPORTS_TEXT, cleanup)))
        cls.at.update(import_known=n - 6, import_relative=n - 5, import_dgram=n - 2, import_net=n - 1)
        n = len(_lines(_append("ui/webview/strip.ts", DYNAMIC_TEXT, cleanup)))
        cls.at.update(dynamic_computed=n - 3, dynamic_relative=n - 2, dynamic_package=n - 1)

    def test_a_qualified_exec_is_a_site_in_the_class_and_a_bare_exec_with_no_binding_is_not(self):
        at, out = self.at, self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        self.assertIn("ui/webview/strip.ts:%d" % at["qualified"], named)
        self.assertIn("ui/webview/strip.ts:%d" % at["inline"], named)
        self.assertListed(out, r"ui/webview/strip\.ts:%d  exec  ls -la SHELL  in -  -> UNCLASSIFIED \[external-program\]" % at["qualified"],
                          "exec runs its text through a shell: the class whatever the head")
        self.assertListed(out, r"ui/webview/strip\.ts:%d  execFile  ls  in -  -> UNCLASSIFIED$" % at["inline"], "a literal head that is no interpreter: a site, no class")
        for line in (at["bare"], at["regexp"]):
            self.assertNotIn("ui/webview/strip.ts:%d" % line, named)
            self.assertFalse(_listed(out, "ui/webview/strip.ts:%d  " % line), "a bare exec( with no child_process binding is not a site (RegExp exec)")

    def test_a_bare_name_the_file_binds_from_child_process_is_a_site_classed_by_its_argv(self):
        """The UNCLASSIFIED path for a program site with no row: a new editor-side file spawning the running node."""
        out = self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED", "COUNTS per_key ui/webview/probe-spawn.ts:spawn: the committed count is None, this run found 1")
        self.assertIn("ui/webview/probe-spawn.ts:4", unclassified(out))
        self.assertListed(out, r"ui/webview/probe-spawn\.ts:4  spawn  RUNTIME-SUPPLIED\(process\.execPath\)  in -  -> UNCLASSIFIED \[external-program\]",
                          "an argv the code does not spell out: the class, with the head the by-program breakdown groups on")

    def test_a_non_literal_head_inside_a_rowed_program_site_moves_the_class_count_naming_the_class(self):
        """The class-count path on an existing rowed key: the timeline view's `open` becomes a variable."""
        self.replace("ui/romp-timeline-view.js", "require('child_process').execFile('open', [url]);", "require('child_process').execFile(opener, [url]);")
        rc, out, _ = inventory(scope_copy())   # a run of its own: the class count and the empty UNCLASSIFIED set are the whole run's
        expected = _expected()
        self.assertRefused(rc, out, "COUNTS classes external-program: the committed count is %d, this run found %d"
                           % (expected["classes"]["external-program"], expected["classes"]["external-program"] + 1),
                           "COUNTS local_sites: the committed count is %d, this run found %d" % (expected["local_sites"], expected["local_sites"] - 1))
        self.assertFalse(unclassified(out), "the row still places the site; the class count is what names it")
        self.assertNotIn("COUNTS per_key ui/romp-timeline-view.js:execFile", out, "the key's own count does not move")
        self.assertListed(out, r"ui/romp-timeline-view\.js:\d+  execFile  RUNTIME-SUPPLIED\(opener\)  in -  -> local-program \[external-program\]")

    def test_the_four_live_program_sites_carry_the_class_and_the_literal_open_does_not(self):
        rc, out, _ = tree_run()
        self.assertEqual(rc, 0, "the run must exit 0:\n" + gates(out))
        self.assertListed(out, r"bin/romp-manager:\d+  spawn  RUNTIME-SUPPLIED\(rompServeBin\(\)\)  in -  -> local-manager \[external-program\]")
        self.assertListed(out, r"bin/romp-manager:\d+  spawn  RUNTIME-SUPPLIED\(process\.execPath\)  in -  -> local-manager \[external-program\]")
        self.assertListed(out, r"vscode-extension/src/extension\.ts:\d+  install\.sh  bash  in -  -> install-ext \[external-program\]",
                          "the re-key to the install script's tool stays, and bash is an interpreter")
        self.assertListed(out, r"vscode-extension/src/extension\.ts:\d+  execFile  git  in -  -> local-program \[external-program\]",
                          "git with a subcommand the code does not spell out (the array holds -C and runtime values)")
        self.assertListed(out, r"ui/romp-timeline-view\.js:\d+  execFile  open  in -  -> local-program$", "a literal local tool: rowed, no class")

    def test_the_connection_primitives_are_sites_with_no_class_tag(self):
        out = self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        for tool in ("net.connect", "net.createConnection", "tls.connect", "XMLHttpRequest", "sendBeacon"):
            line = self.at[tool]
            self.assertIn("ui/webview/strip.ts:%d" % line, named, tool)
            self.assertListed(out, r"ui/webview/strip\.ts:%d  %s  .*  in -  -> UNCLASSIFIED$" % (line, re.escape(tool)), "a connection, not a program: no class tag")

    def test_a_package_the_census_does_not_know_is_the_loud_line_and_a_known_or_relative_import_is_not(self):
        at, out = self.at, self.out
        self.assertRefused(self.rc, out, "IMPORT ui/webview/strip.ts:%d imports dgram, a package the census does not know" % at["import_dgram"],
                           "IMPORT ui/webview/strip.ts:%d imports net, a package the census does not know" % at["import_net"])
        for line in (at["import_known"], at["import_relative"]):
            self.assertNotIn("IMPORT ui/webview/strip.ts:%d " % line, out, "a known package and the project's own module pass the gate")

    def test_a_dynamic_import_of_a_computed_module_url_is_the_computed_class_and_a_literal_one_is_an_import(self):
        at, out = self.at, self.out
        self.assertListed(out, r"ui/webview/strip\.ts:%d  import\(\)  import\(u\)  in -  -> \(browser-computed-url\)" % at["dynamic_computed"])
        self.assertFalse(_listed(out, "ui/webview/strip.ts:%d  " % at["dynamic_relative"]) + _listed(out, "ui/webview/strip.ts:%d  " % at["dynamic_package"]),
                         "a literal specifier is an import, not a site")
        self.assertRefused(self.rc, out, "IMPORT ui/webview/strip.ts:%d imports dgram" % at["dynamic_package"])


UNKNOWN_IMPORTS_TEXT = ('\nimport importlib\n_PROBE_MOD = "httpx"\n\ndef _probe_import():\n    importlib.import_module("httpx")\n    importlib.import_module(_PROBE_MOD)\n'
                        '    return __import__("httpx")\n')
KNOWN_IMPORTS_TEXT = ('\nimport importlib\n_PROBE_KNOWN = "json"\n_PROBE_KNOWNS = (("json", "loads"), ("re", "compile"))\n\ndef _probe_known_import(name):\n'
                      '    importlib.import_module("json")\n    importlib.import_module(_PROBE_KNOWN)\n    for mod, attr in _PROBE_KNOWNS:\n        importlib.import_module(mod)\n'
                      '    found = {a: importlib.import_module(m) for m, a in _PROBE_KNOWNS}\n    return found, importlib.import_module(name)\n')


class ThePythonImportGateReachesImportModule(_SharedRun):
    """importlib.import_module and __import__ name a module the way an import statement does: a string literal, a module
    constant, or a loop or comprehension variable over a module constant resolves and goes through KNOWN_IMPORTS; an
    argument the scan cannot resolve is refused as a module named at run time (extra6-2 of the third round). The
    credentials run is shared with the net-list and git-boundary classes below: four blocks appended in turn to
    kernel/credentials.py, this class's two first, under names no other block uses (the scan resolves a module constant by
    its last assignment, so the known-module block's constant is not the unknown-module block's)."""

    RUN = "credentials"

    @classmethod
    def mutate(cls, cleanup):
        n = len(_lines(_append("kernel/credentials.py", UNKNOWN_IMPORTS_TEXT, cleanup)))
        cls.at.update(literal=n - 2, constant=n - 1, dunder=n)
        cls.at["run_time"] = len(_lines(_append("kernel/credentials.py", KNOWN_IMPORTS_TEXT, cleanup)))

    def test_a_literal_or_a_constant_the_census_does_not_know_is_the_loud_line(self):
        self.assertRefused(self.rc, self.out, *("IMPORT kernel/credentials.py:%d imports httpx" % self.at[k] for k in ("literal", "constant", "dunder")))

    def test_a_known_module_by_literal_constant_loop_or_comprehension_passes_and_a_run_time_name_is_refused(self):
        out = self.out
        self.assertRefused(self.rc, out, "IMPORT kernel/credentials.py:%d imports a module named at run time (importlib.import_module(name))" % self.at["run_time"])
        # the run's IMPORT lines, as a set: the case above's three httpx lines and the run-time name, and no other line of the
        # run, this block's literal, constant, loop and comprehension included (the shared run holds the same property the
        # one-IMPORT-line count held over a run of this block alone)
        self.assertEqual(sorted(ln.split()[1] for ln in out.splitlines() if ln.startswith("IMPORT")),
                         sorted("kernel/credentials.py:%d" % self.at[k] for k in ("literal", "constant", "dunder", "run_time")),
                         "the literal, the constant, the loop and the comprehension resolve to known modules:\n" + gates(out))


SENDTO_TEXT = ('\nimport asyncio, socket\n\ndef _probe_udp(addr):\n    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n    s.sendto(b"x", addr)\n\n'
               'async def _probe_loop(addr):\n    loop = asyncio.get_event_loop()\n    await loop.sock_connect(socket.socket(), addr)\n'
               '    await asyncio.get_running_loop().create_connection(lambda: None, "TESTHOST", 443)\n    await loop.create_datagram_endpoint(lambda: None, remote_addr=addr)\n')


class TheNetListNamesSendtoAndTheLoopConnections(_SharedRun):
    """socket.sendto on a socket bound in the function or with a tuple-literal address, and the event loop's sock_connect,
    create_connection and create_datagram_endpoint on a loop bound in the function or on the getter's own call, are sites
    (extra6-2 of the third round; zero sites at this head, so the tree's counts do not move). The block is the third of
    the credentials run (ThePythonImportGateReachesImportModule)."""

    RUN = "credentials"

    @classmethod
    def mutate(cls, cleanup):
        cls.at["n"] = len(_lines(_append("kernel/credentials.py", SENDTO_TEXT, cleanup)))

    def test_sendto_and_the_three_loop_methods_are_sites(self):
        n, out = self.at["n"], self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        self.assertIn("kernel/credentials.py:%d" % (n - 6), named, "sendto on a socket bound in the function")
        self.assertIn("kernel/credentials.py:%d" % (n - 2), named, "sock_connect on a loop bound in the function")
        self.assertIn("kernel/credentials.py:%d" % (n - 1), named, "create_connection on the getter's own call")
        self.assertIn("kernel/credentials.py:%d" % n, named, "create_datagram_endpoint on a bound loop")
        self.assertListed(out, r"kernel/credentials\.py:%d  socket\.sendto  " % (n - 6))
        self.assertListed(out, r"kernel/credentials\.py:%d  loop\.sock_connect  " % (n - 2))


class TheResidualClassIsStatedAndHeld(_Scope):
    """The one class the scan cannot see by construction is named, in the docstring and the table, beside a planted call
    it does not see: a connect and a sendto on a parameter socket and on an attribute-held socket run clean at the
    committed counts, and the sentence that says so is present in both homes (extra6-2 of the third round)."""

    def test_a_socket_primitive_on_a_parameter_or_attribute_receiver_is_not_a_site_and_the_sentence_says_so(self):
        self.append("kernel/credentials.py",
            '\nimport socket\n\ndef _probe_param(sock, addr):\n    sock.connect(addr)\n    sock.sendto(b"x", addr)\n\n'
            'class _ProbeHeld:\n    def __init__(self):\n        self.sock = socket.socket()\n        self.addr = None\n\n    def go(self):\n'
            '        self.sock.connect(self.addr)\n        self.sock.sendto(b"x", self.addr)\n')
        rc, out, _ = inventory(scope_copy())
        self.assertClean(rc, out)
        rc2, out2, _ = tree_run()
        line = lambda text: re.sub(r"; \d+ files scanned.*$", "", next(ln for ln in text.splitlines() if ln.startswith("--- ")))
        self.assertEqual(line(out), line(out2), "the planted calls are not sites: the census does not see them, by construction")
        self.assertIn(RESIDUAL, _inventory_docstring(), "the docstring names the class the scan cannot see")
        rc3, table, err = tree_run("--table")
        self.assertEqual(rc3, 0, err[-1500:])
        self.assertIn(RESIDUAL, table, "the table names the class the scan cannot see")
        self.assertIn("| %s | not counted: " % UNSEEN_LABEL, table, "the class is a row of its own, named and not counted")

    def test_the_disclosure_sentence_stands_in_the_docstring(self):
        self.assertIn(DISCLOSURE, _inventory_docstring(), "the named lists are disclosed as such after the widening")


class TheHeadsFigureNamesASwappedProgram(_Scope):
    """The committed counts carry the program head per Python command site, so a same-count swap of a local tool for a
    network tool inside a rowed function is a COUNTS line naming the key, the primitive and the new head; before the
    round's fix the swap ran clean at the committed counts (extra6-3 of the third round)."""

    def test_systemctl_swapped_for_curl_inside_a_rowed_function_is_named_by_key_primitive_and_head(self):
        self.replace("kernel/sdk_backend.py", 'res = run(["systemctl", "--user", "stop", unit]', 'res = run(["curl", "--user", "stop", unit]')
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "COUNTS heads kernel/sdk_backend.py:SdkBackend._end_cli_tree run via run curl: the committed count is None, this run found 1",
                           "COUNTS heads kernel/sdk_backend.py:SdkBackend._end_cli_tree run via run systemctl: the committed count is 1, this run found None")
        self.assertFalse(unclassified(out), "the row places the site whatever its program; the head figure is what names the swap")
        self.assertNotIn("COUNTS per_key kernel/sdk_backend.py:SdkBackend._end_cli_tree", out, "the key's count is unchanged: the head is the figure that moves")

    def test_the_heads_map_covers_the_python_command_sites_and_nothing_else(self):
        expected = _expected()
        self.assertIn("heads", expected, "the committed counts carry the heads map (row key, primitive, head, per Python command site)")
        heads = expected["heads"]
        self.assertIn("kernel/sdk_backend.py:SdkBackend._end_cli_tree run via run systemctl", heads)
        self.assertIn("kernel/kernel.py:_run_update Popen bash -c", heads)
        self.assertIn("kernel/kernel.py:_spawn_tunnel Popen RUNTIME-SUPPLIED", heads, "an argv the code does not spell out is one head, whatever its expression")
        self.assertFalse([k for k in heads if k.startswith(("bin/", "hooks/", "ui/", "vscode-extension/", "bootstrap.sh", "install.sh"))],
                         "a shell or JavaScript site is a line keyed by tool with no head figure (the stated residual)")
        self.assertFalse([k for k in heads if " urlopen " in k or " Request " in k], "a connection site has no head: the figure is the command sites'")
        command_keys = {k.split(" ", 1)[0] for k in heads}   # a row key carries no space; the head may
        for k in command_keys:
            self.assertIn(k, expected["per_key"], "every heads key is a row key")


GIT_TEXT = '\ndef _probe_checkout():\n    return subprocess.run(["git", "checkout", "main"], check=False)\n\ndef _probe_git(sub):\n    return subprocess.run(["git", sub], check=False)\n'


class TheGitClassBoundaryIsPinned(_SharedRun):
    """The external-program class holds git with a subcommand the code does not spell out, never a spelled one: a
    row-less `git checkout` is UNCLASSIFIED with no class tag (it needs a row; it is not local by default since checkout
    left LOCAL_GIT), and a bare git with a runtime subcommand carries the tag. Pinned by execution because the round's
    record misstated the boundary and nothing executed held it (tests-1, extra8-2 of the third round). The block is the
    fourth of the credentials run (ThePythonImportGateReachesImportModule)."""

    RUN = "credentials"

    @classmethod
    def mutate(cls, cleanup):
        lines = _lines(_append("kernel/credentials.py", GIT_TEXT, cleanup))
        cls.at.update({name: next(i + 2 for i, ln in enumerate(lines) if ln.startswith("def %s(" % name)) for name in ("_probe_checkout", "_probe_git")})

    def test_a_row_less_checkout_is_unclassified_with_no_class_tag_and_a_runtime_subcommand_carries_it(self):
        at, out = self.at, self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        self.assertIn("kernel/credentials.py:%d" % at["_probe_checkout"], named, "a spelled subcommand outside LOCAL_GIT needs a row")
        self.assertIn("kernel/credentials.py:%d" % at["_probe_git"], named)
        self.assertListed(out, r"kernel/credentials\.py:%d  run  git checkout  in _probe_checkout  -> UNCLASSIFIED$" % at["_probe_checkout"],
                          "git checkout is not in the class: no tag")
        self.assertListed(out, r"kernel/credentials\.py:%d  run  git  in _probe_git  -> UNCLASSIFIED \[external-program\]" % at["_probe_git"],
                          "git with a subcommand the code does not spell out is the class")


class TheTableIsTheLedgers(_Scope):
    """--table prints the ledger's table from the sites: one row per road, the local row, one row per class this scan cannot
    see, and the row of the class it cannot see at all (named, not counted); and the ledger entry carries exactly that output
    between its two marker lines, so a hand-written cell cannot survive."""

    def test_the_table_has_a_row_per_road_the_local_row_the_four_classes_and_the_unseen_row(self):
        rc, table, err = tree_run("--table")
        self.assertEqual(rc, 0, err[-1500:])
        expected = _expected()
        lines = table.strip().splitlines()
        self.assertEqual(lines[0], "| road | where | trigger and cadence | what is sent and to where | off switch |")
        self.assertEqual(lines[1], "|---|---|---|---|---|")
        rows = lines[2:]
        self.assertEqual(len(rows), expected["roads"] - expected["local_roads"] + 1 + 4 + 1, "a row per road, the local row, the four counted classes, the unseen row")
        for r in rows:
            self.assertEqual(len(r.split(" | ")), 5, r[:120])
        self.assertTrue(rows[-6].startswith("| local, set aside and counted (local) | %d sites on the %d local roads" % (expected["local_sites"], expected["local_roads"])))
        self.assertTrue(rows[-1].startswith("| %s | not counted: " % UNSEEN_LABEL), "the last row is the class the scan cannot see, named and not counted")
        self.assertIn("| an external program started whose far end its arguments do not show (not derivable by this scan) | %d sites, by program:" % expected["classes"]["external-program"], table)
        self.assertIn("| a browser request whose URL is computed at run time (not derivable by this scan) | %d sites:" % expected["classes"]["browser-computed-url"], table)
        self.assertIn("| the browser DOM's own loads (not derivable by this scan) | %d lines in" % expected["classes"]["browser-dom-loads"], table)
        self.assertIn("| a program supplied at run time (not derivable by this scan) | kernel/credentials.py `run_helper`; kernel/kernel.py `_watch_run` (2 sites) |", table)
        browser = next(r for r in rows if r.startswith("| a viewed file's pictures from the web (browser) |"))
        self.assertIn("| ui/webview/figure-gate.ts (`figureHosts`); ui/webview/preview.ts (`Image`) |", browser, "the where cell is derived from the sites")
        self.assertNotIn("Copy image", browser, "extra8-4: the lightbox re-fetch reads the kernel's own file URL and is not a member")
        for cell in table.splitlines():
            self.assertNotIn(chr(0x2014), cell)
            self.assertNotIn(chr(0x2013), cell)

    def test_the_ledger_carries_the_scripts_table_between_its_markers(self):
        if not os.path.isdir(os.path.join(ROOT, "upstream")):
            self.skipTest("no upstream/ ledger in this tree (the ledger is the fork's)")
        path = os.path.join(ROOT, LEDGER)
        self.assertTrue(os.path.isfile(path), "the ledger entry %s exists" % LEDGER)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(BEGIN in text, "%s carries the marker line %s (run python3 %s --table and paste its output between the two markers)" % (LEDGER, BEGIN, INVENTORY))
        self.assertTrue(END in text, "%s carries the marker line %s" % (LEDGER, END))
        block = text.split(BEGIN, 1)[1].split(END, 1)[0].strip()
        rc, table, err = tree_run("--table")
        self.assertEqual(rc, 0, err[-1500:])
        if block != table.strip():
            diff = "\n".join(list(difflib.unified_diff(block.splitlines(), table.strip().splitlines(), "the ledger's block", "--table", lineterm=""))[:40])
            self.fail("the ledger's table is not the script's output; regenerate the block with python3 %s --table:\n%s" % (INVENTORY, diff))


if __name__ == "__main__":
    unittest.main()
