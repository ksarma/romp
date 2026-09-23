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

Text only: kernel/kernel.py is read as a file and parsed once per process (tests/parse_cache.py's source_and_tree: the
parse this half, the switch case and the served pass below share, and in a serial cell the thread-stop census's parse of
the same file is the same object); nothing loads romp code. The state root the preamble at the head mints is the state
ratchet's floor for the in-process load of the census script (tests/test_state_isolation_order.py reads every importlib
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
from one run (_SharedRun, whose docstring says why that loses nothing), over two tiny roots (no sites; a missing root),
and --table against the block the ledger entry carries between its two marker lines. The script loads no romp code and
neither does this module; the copy lives under the run's temp root (tests/__init__.py's hook removes it, and
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
numbered on from the third round's record (M19 to M25): TheEchoRuleScansTheLiveRemainder, a shell run member, appends seven
echo-led lines to bin/romp (ECHO_TEXT): the pipe form and the double-quoted substitution form are curl sites, a python3 -c
substitution is an interpreter site on its row and a node -e one is UNCLASSIFIED, while three copies of the tree's printed
remedies (a tool inside quotes) list no site, and the tree's four remedy lines, located by content, have no site line (M19:
the head's one-line skip restored in a scratch copy of the script, none of the four live lines listed).
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
import contextlib
import difflib
import gc
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

# Hermetic state BEFORE the in-process load of the census script (script_module, below): tests/test_state_isolation_order.py
# reads every importlib load in a test module as a load of romp code and asks for this floor above it. The script is
# standard-library code and resolves no state root, and nothing here loads romp code; the floor is the ratchet's price for
# the load, an empty directory under the run's temp root.
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
REFRESH_FALSE_CALLERS = {
    "_spend_window_usd": "the spend guard's window sum on the pusher's path: never a fetch (T350)",
    "_spend_guard_tick": "the spend guard's tick on the pusher's path: never a fetch (T350)",
    "_price_feed_status": "the status's own merge under _price_feed_lock, the count of overrides: never a fetch (T350)",
}
RESOLVE = ("either gate it behind _price_feed_off (the first statement of _refresh_remote_prices is the shape) and add it "
           "to the table in tests/test_price_feed_census.py with its reason, or route it through _model_prices")


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


def census(src, tree=None):
    """{"url": {path: [lines]}, "url_reads": {path: [lines]}, "refresh": {...}, "true": {...}, "false": {...}}; `tree` is the
    source's parsed tree when the caller holds one (the kernel's, from tests/parse_cache.py), else the source is parsed here."""
    c = _Census()
    c.visit(tree if tree is not None else ast.parse(src))
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
        fn = next(n for n in KERNEL_TREE.body if isinstance(n, ast.FunctionDef) and n.name == "_refresh_remote_prices")
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
    `if __name__ == "__main__"` road does not run. The module carries the script's constants (T, ROADS, CLASS_ROWS,
    CLICK_RESIDUAL, EXPECTED) and its functions (main, scan, figures, problems, render_sites, render_table, Scan,
    served_texts, Result, Site), the surface the runs and the served pass call. The fifth round (2026-09-23), on the
    reviewer's cost ruling; a child interpreter ran the file before it."""
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
    sys.exit. One run is one full scan of the root's declared scope, about 2.4 s on 3.10 with the collector off."""
    mod = script_module(root)
    out, err = io.StringIO(), io.StringIO()
    with _collector_off(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mod.main(list(flags) + [root])
    return rc, out.getvalue(), err.getvalue()


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
    other run of this module, over the copy and the tiny roots). Two roads and no other flag."""
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
    property is a file's own line in UNCLASSIFIED or in a gate line, or a file's absence from them. Since the fifth round
    the run also carries the primitive list's two blocks in kernel/credentials.py and the literal-URL function in
    kernel/kernel.py (ThePrimitiveListIsKeptHonest, ASecondSiteInsideARowedFunctionIsRed), each keyed on its own lines."""

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
SERVED_PAGES = ("The pages the kernel serves and its service worker's script, from its own string constants (the dashboard shell, the seven "
                "pane pages, the token login page, the too-large page and /sw.js, with the shim, the timeline boot and the shell scripts they "
                "inline), are read from kernel.py's syntax tree, each route's page function followed to the constants it returns or inlines, "
                "and scanned as browser text keyed kernel/kernel.py plus tool, with the DOM loads counted; a route that serves text/html or "
                "text/javascript from text the extraction cannot read fails the run (SERVED); a file the page reads at run time is covered "
                "by the walk when it is a scanned kind, and a stylesheet is named, not scanned.")
SERVED_REFUSED_SCAN = ("The whole of kernel.py is not scanned as text, since a text scan misreads Python and JS concatenations (a Python "
                       "method spelled like a client, a `from` inside a script split across Python literals).")
SERVED_IMPORT_GATE = ("Over served text the import gate's statement form applies only to a line that starts with import or export (a line led "
                      "by a closing brace is a multi-line import's last line in a module and any block's in a page's script), while a literal "
                      "require() or import() is gated wherever it stands.")
SERVED_KEYED_RESIDUAL = ("The served pages' rows are keyed by tool (kernel/kernel.py plus WebSocket, window.open or clients.openWindow), so a "
                         "second socket or opener in the served text is caught by the count per key when it changes the tool and not when it "
                         "keeps it, as any rowed shell or JavaScript line is (the residual above).")
SERVED_NAMED_CLASS = ("Named and not counted in the served text: a stylesheet's `url()` loads (THEME_CSS's fonts, _LOADER_CSS's face, "
                      "_RDRIFT_CSS's and the dashboard shell's own rules, and the pane stylesheets under ui/webview read at run time), every one "
                      "a `/media` path on the kernel's own origin, and the same-origin navigations no list names (`location.replace` on the token "
                      "login page, `location.reload` in the shim and the shell, `navigator.serviceWorker.register('/sw.js')`, "
                      "`history.replaceState`).")
ROUND_FOUR_SENTENCES = (("the echo rule", ECHO_RULE), ("the served pages", SERVED_PAGES), ("the refused whole-file text scan", SERVED_REFUSED_SCAN),
                        ("the narrowed import gate over served text", SERVED_IMPORT_GATE), ("the keyed-by-tool residual of the served rows", SERVED_KEYED_RESIDUAL),
                        ("the named class the served scan does not count", SERVED_NAMED_CLASS))


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
        self.assertEqual(doc[doc.index(DISCLOSURE) + len(DISCLOSURE):].lstrip()[:len(ECHO_RULE)], ECHO_RULE,
                         "the echo rule is the sentence right after the disclosure sentence: the narrowing of the skip is stated where the closed lists are")


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


# ---- the fourth round of the review (2026-09-23) --------------------------------------------------------------------------
# D1, the echo rule: seven echo-led lines appended to bin/romp in the shared shell run. The first four are live (a pipe outside the
# quotes; a curl substitution inside them; a python3 -c and a node -e substitution), the last three are copies of the tree's
# printed remedies (a tool inside quotes; an escaped quote and an escaped dollar; a substitution whose body names no tool).
ECHO_TEXT = ('echo "$body" | curl -fsSL -d @- https://TESTHOST/collect\n'
             'echo "rate: $(curl -fsSL https://TESTHOST/rate)"\n'
             'echo "$(python3 -c \'import urllib.request; urllib.request.urlopen("https://TESTHOST/x").read()\')"\n'
             'echo "$(node -e \'fetch("https://TESTHOST/x")\')"\n'
             'echo "  curl -fsSL https://TESTHOST/bootstrap.sh | bash"\n'
             'echo "    curl -fsSL <url> | ROMP_DIR=\\"\\$HOME/elsewhere\\" bash" >&2\n'
             'echo "      forward the port:  ssh -N -L $p:127.0.0.1:$p $(hostname -s 2>/dev/null || echo \'<this-host>\')"\n')
ECHO_STARTS = (("pipe", 'echo "$body" |'), ("substitution", 'echo "rate: $('), ("python", 'echo "$(python3 -c'), ("node", 'echo "$(node -e'),
               ("remedy_pipe", 'echo "  curl'), ("remedy_escaped", 'echo "    curl'), ("remedy_ssh", 'echo "      forward'))
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
# E, the served pages: the plants in kernel/kernel.py (each located by content in the copy after every plant has landed)
BOOT_ANCHOR = "function post(m){api.postMessage(m);}\n"
BOOT_PLANTS = ('fetch("https://example.invalid/probe");\n'
               'new WebSocket("wss://example.invalid/");\n'
               'window.open("https://example.invalid/");\n'
               "}else{alert('Pull from '+h+' failed');}\n"
               "import x from 'example-pkg';\n")
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
# The sent cell's clause on an inline svg's paint references (kept by the sanitizer, loading at render, their request able to carry the
# dashboard's address with the serve token in its Referer), one text with SECURITY.md's sentence, which tests/test_security_price_feed.py
# holds to the same words; the claim it replaces, that no token rides, is held absent
CHAT_MEDIA_PAINT = ("an inline svg's paint references (a `fill`, `mask` or `filter` whose `url()` names another host) load at render too, with no "
                    "click, and are the one case where the request can carry the dashboard's address with the serve token in its Referer: the browser does "
                    "not reliably hold them to the page's referrer policy, so the request to that host can carry the page's origin or the full chat URL "
                    "with the serve token (the response is blocked as cross-origin; the request, with that header, has reached the host)")
CHAT_MEDIA_NO_TOKEN_WITHDRAWN = "no serve token, key or login token rides"
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
    are curl sites on bin/romp's row (its committed count moves by two), a python3 -c substitution is an interpreter site on its
    row (by one) and a node -e one is UNCLASSIFIED, while a remedy that names a tool inside its quotes stays no site: three copies
    of the tree's own remedy lines list nothing, and the four originals, located by content, have no site line while the tree runs
    clean. Before the round every such line was skipped whole, so the four live shapes were silent at exit 0. The block is
    appended to bin/romp in the shared shell run (no other member touches that file); its lines are recorded by content."""

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
        self.assertListed(out, r"bin/romp:%d  python3 -c  .*  in -  -> local-kernel \[external-program\]" % at["python"], "an interpreter substitution is a site on its row, classed")
        self.assertIn("bin/romp:%d" % at["node"], unclassified(out), "the node -e substitution has no row: UNCLASSIFIED")
        self.assertListed(out, r"bin/romp:%d  node -e  .*  in -  -> UNCLASSIFIED \[external-program\]" % at["node"])
        expected = _expected()
        self.assertRefused(self.rc, out, "COUNTS per_key bin/romp:curl: the committed count is %d, this run found %d"
                           % (expected["per_key"]["bin/romp:curl"], expected["per_key"]["bin/romp:curl"] + 2),
                           "COUNTS per_key bin/romp:python3 -c: the committed count is %d, this run found %d"
                           % (expected["per_key"]["bin/romp:python3 -c"], expected["per_key"]["bin/romp:python3 -c"] + 1),
                           "COUNTS per_key bin/romp:node -e: the committed count is None, this run found 1")

    def test_a_remedy_that_names_a_tool_inside_its_quotes_is_no_site(self):
        at, out = self.at, self.out
        named = unclassified(out)
        for name in ("remedy_pipe", "remedy_escaped", "remedy_ssh"):
            self.assertNotIn("bin/romp:%d" % at[name], named, name)
            self.assertFalse(_listed(out, "bin/romp:%d  " % at[name]), "%s: the tool stands in the printed text, inside the quotes, and is not live" % name)

    def test_the_trees_four_remedy_lines_have_no_site_line_and_the_run_is_clean(self):
        rc, out, _ = tree_run()
        self.assertClean(rc, out)
        for rel, needle in REMEDY_LINES:
            n = _line_of(os.path.join(ROOT, rel), needle)
            self.assertFalse(_listed(out, "%s:%d  " % (rel, n)), "%s:%d prints a remedy whose pipe or substitution stands inside the quotes: no site" % (rel, n))

    def test_the_head_skip_restored_leaves_the_live_lines_silent(self):
        """M19: the one-line skip the round replaced, restored in a scratch copy of the script, skips the four live shapes whole."""
        lines = self.lines(self.append("bin/romp", ECHO_TEXT))
        at = {name: next(i + 1 for i, ln in enumerate(lines) if ln.startswith(start)) for name, start in ECHO_STARTS}
        self.replace(INVENTORY, ECHO_ARM, ECHO_SKIP)
        rc, out, _ = inventory(scope_copy())
        for name in ("pipe", "substitution", "python", "node"):
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


SERVED_KEY = ("tests/test_price_feed_census.py", "the served pass over the planted kernel.py")   # parse_cache.derived's key
SERVED_PLANT_LINES = (("fetch", 'fetch("https://example.invalid/probe");'), ("alert", "}else{alert('Pull from '+h+' failed');}"),
                      ("import", "import x from 'example-pkg';"), ("settings_def", "def _settings_page():"),
                      ("settings_anchor", SETTINGS_ANCHOR.strip()), ("probe_read", '    return (UI / "probe.html").read_text()'),
                      ("fstring", 'fetch(\'https://example.invalid/f\')'), ("slot", '"<script>fetch(\'%s\')</script>" % p'),
                      ("body_param", 'return self._send(200, body, "text/html")'))   # the plants' lines, located by content once all have landed


def _served_build():
    """The served pass over kernel/kernel.py with TheServedPagesAreScanned's plants applied to its TEXT, in memory and never to
    the copy (the fifth round, 2026-09-23, on the reviewer's cost ruling; a shared run over a planted copy before): the planted
    text parsed once (this build; the clean text's parse is tests/parse_cache.py's), the script's Scan over that tree for the
    routes (and kernel.py's Python sites and PROGRAM lines, which the plants leave as they are), served_texts over those
    routes with the tree's file list (its "a file the walk covers" check), and the pass spliced into the tree's one Result
    (_tree) in place of kernel/kernel.py's own contributions, then the script's figures, problems and render_sites over the
    spliced Result: (the plants' lines by content, (exit code, stdout)) as a run over a copy carrying the same plants prints
    them, so the class's cases read the pass as they read a run. The splice is exact by construction of the script's scan():
    a file contributes sites (Site.file), DOM lines (their rel), stylesheets (their rel), problem lines naming it and its
    entry in served; each of kernel/kernel.py's is replaced by the planted text's, files and skipped are the tree's
    (kernel.py is still a file), and the sites are re-sorted as scan sorts them. Held here: the tree's run served
    kernel/kernel.py alone (a second file with routes would need the splice widened; refused, not assumed) and the script
    has the served pass at all (a script without it, the archive of the reviewed head, is refused by name, so every case
    of the class reds with this message and not with an error). Residual: scan()'s walk-time gate over kernel.py's Python
    imports is not re-run over the planted text (the plants add no Python import; the tree's run gates the real ones)."""
    mod = script_module(ROOT)
    for name in ("Result", "Scan", "served_texts", "Site"):
        if not hasattr(mod, name):
            raise AssertionError("the census script has no served pass (%s is not defined in %s): the pages the kernel serves and its "
                                 "service worker's script are outside the scan" % (name, INVENTORY))
    base = _tree()
    if base.res.served != [KERNEL_PATH]:
        raise AssertionError("the served pass reads one file at this head, %s; the tree's run served %r, and the splice replaces that "
                             "file's contributions alone" % (KERNEL_PATH, base.res.served))
    text = _replace_text(KERNEL, BOOT_ANCHOR, BOOT_ANCHOR + BOOT_PLANTS, KERNEL_PATH)
    text = _replace_text(text, SETTINGS_ANCHOR, SETTINGS_PLANT + SETTINGS_ANCHOR, KERNEL_PATH)
    text = _replace_text(text, CHAT_BRANCH, ROUTE_PLANTS + CHAT_BRANCH, KERNEL_PATH)
    text = _replace_text(text, SEND_ANCHOR, SEND_PLANT + SEND_ANCHOR, KERNEL_PATH)
    text = text + ("" if text.endswith("\n") else "\n") + PROBE_PAGE_DEF   # appended as _append lands a block
    lines = text.splitlines()
    at = {name: _line_in(lines, needle, KERNEL_PATH + " (planted)") for name, needle in SERVED_PLANT_LINES}
    tree = ast.parse(text, filename=KERNEL_PATH)
    res = mod.Result()
    res.files, res.skipped = list(base.res.files), base.res.skipped
    sc = mod.Scan(KERNEL_PATH, res)
    sc.visit(tree)
    mod.served_texts(KERNEL_PATH, tree, sorted(sc.routes, key=lambda r: r[0].lineno), res)
    merged = mod.Result()
    merged.files, merged.skipped = res.files, res.skipped
    merged.sites = [x for x in base.res.sites if x.file != KERNEL_PATH] + res.sites
    merged.dom = [d for d in base.res.dom if d[0] != KERNEL_PATH] + res.dom
    merged.served_files = [f for f in base.res.served_files if f[0] != KERNEL_PATH] + res.served_files
    merged.problems = [p for p in base.res.problems if KERNEL_PATH + ":" not in p] + res.problems
    merged.served = [r for r in base.res.served if r != KERNEL_PATH] + res.served
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
    routes' `_send` calls with a text/html or text/javascript literal are followed through kernel.py's syntax tree to the constants
    they inline, and each piece goes through line_scan keyed kernel/kernel.py plus tool. Planted in kernel/kernel.py's text (the
    served pass, served_pass; a run over a planted copy before the fifth round): a third-party fetch, a second socket and a
    second opener in _TIMELINE_BOOT (the fetch UNCLASSIFIED, the two rowed tools moving their keys' counts: the keyed-by-tool
    residual), a brace-led alert and an import statement there (the narrowed import gate), a sendBeacon in the settings page's
    template (UNCLASSIFIED at the template's own lines), a route serving a file the walk does not scan and a method serving
    text/html from a parameter (each a SERVED line by name), an f-string page (its fetch UNCLASSIFIED: the branch executed) and
    a page whose fetch URL is a Python format slot (the computed class). At the tree the shim's and the shell's sockets, the
    boot's dead opener and the worker's clients.openWindow list on local-kernel, the four fetches whose route literal a caller
    passes list as computed, and the four pane stylesheets are named, not scanned. The pass is the class's alone: its import
    plant would join the credentials run's IMPORT set, which that run's case holds equal to its own lines; the served-pass
    mutation (M21) is a run of its own over the copy, as every script mutation is."""

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


class TheChatMediaRoadIsRowed(_Scope):
    """A rendered message's media on the web dashboard is a road (the fourth round, tests-1): the pipeline's one line on a
    message's pictures before the browser fetches them, `mdImgPostPass(clean)` in md() and in userMd(), is the row's site (two
    lines, keyed ui/webview/render.ts:mdImgPostPass, through a JS entry whose lookbehind keeps the definition in preview.ts out),
    and the table's row states the render as the trigger, the cross-site cookies and no Referer as what is sent (save an inline svg's
    paint references, whose request can carry the dashboard's address with the serve token in its Referer, one text with the
    section's sentence), and no switch.
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
        for phrase in ("with the cross-site cookies that browser sends to that host", "no Referer (every page the kernel serves carries `Referrer-Policy: same-origin`)",
                       CHAT_MEDIA_PAINT):
            self.assertIn(phrase, cells[3], "the sent cell: the host the URL names, the cookies a cross-site subresource carries, no Referer, and the one case "
                          "whose request can carry the dashboard's address with the serve token in its Referer, an inline svg's paint references")
        self.assertNotIn(CHAT_MEDIA_NO_TOKEN_WITHDRAWN, cells[3], "the sent cell no longer claims that no token rides: a paint reference's Referer can carry the serve token")
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
