#!/usr/bin/env python3
"""docs/reference.md's price feed subsection says which override rows the count counts and how long the fetched
rows live, and both claims are tied to the kernel's code (review round 2, 2026-09-20).

Two sentences of the subsection made claims wider than the code. The override sentence said the line under the
Token usage footnote ends `; 1 row overridden by model-prices.json` "with one row in the file", but
_price_feed_status counts the rows whose merged rates differ from the table under them (the defaults under the
cached feed rows: `if table.get(k) != v`), so a row copied from the defaults, or equal to the feed's row for
that model, is in the file and produces no count; tests/test_price_feed_off.py pins that on purpose (a row equal
to the default is not an override). The cache sentence said the kernel keeps the rows it matched in memory
"until the next restart", but the worker in _refresh_remote_prices assigns `_price_cache["remote"] = out`
whenever a fetch lands, so a landed fetch replaces them with the rows it parsed, even none (a feed whose schema
moved), and only a failed fetch leaves them (stale-while-revalidate). The doc now says both, and these pins hold
the doc's words to the code's shape: a wording change in either reddens here first.

The review of PR 878 (2026-09-21) added a third claim to the same paragraph. The subsection sends a feed-off box to
~/.config/romp/model-prices.json; until that review a row the kernel could not read was silent, and the paragraph said
nothing. The review's first round wrapped the merge's loop in one try, so a bad row voided itself and every row after
it, and documented that; the re-ruling (2026-09-21) found the void's blast radius depended on the row's position and
ruled the row skipped ALONE, every other row applied, the kernel saying so on stderr naming the row's key (once per
kernel life per row, the file fault once on a latch of its own) and the priceFeed block carrying the class as
`overrideFault` and the count of skipped rows as `overrideRowsRejected`, never the file's text or its path, with a
clause on the modal's line from the count. The doc says that; AnUnreadableRowOrFileIsSaid pins the sentence and ties
it to the kernel's fault classes, the count key, the two stderr heads, the two say-once latches and the view's clause,
naming the executed cases in tests/test_price_feed_off.py TheOverrideFileIsSaid. Red over a git archive of 5cbf9e397
(the head before the re-ruling) at the first doc assertion (the paragraph there says the row "voids that row and every
row after it"); green at the tree.

The second round of that review (2026-09-21) moved three of the pinned sentences. The override sentence said the line
ENDS with the count where gear.js puts the skipped-rows clause after it: it now says where the count sits. The row rule
gained the class the round found coerced rather than rejected (a rate present and not a JSON number, a numeric string
included, priced at zero or one per token by `float(x or 0)`): the kernel raises into the per-row path and the doc says
so, with the kernel's row line naming three classes. The stderr sentence was unconditional where both fault lines sit
under `if refresh:`, the cost view's road (the spend ceiling's check and /version merge with refresh=False and write
nothing): the doc conditions it the way the off line's sentence is, says the block carries the class and the count
whether or not the view was opened, and the pin reads the guard by ast. The whole-file clause the view gained this
round (`overrideFault` 'file' in the skipped rows' slot) is quoted the way the row clause is. Red over an archive of that
round's head at the first doc assertion (the old sentences); green at the tree.

Text only, the tests/test_reference_price_feed.py precedent: the doc and the kernel are read as files, nothing
loads romp code, and no state root is minted. A pin keyed on where the code lives says in its message what it
guards and names the executed test that proves the behaviour. Every case asserts the doc's text FIRST, so a run
over a tree without the round's wording fails at that assertion and never at a missing symbol.
"""
import ast
import os
import re
import textwrap
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so a quote that spans a line break in the doc still compares."""
    return re.sub(r"\s+", " ", text).strip()


def _section(doc, heading):
    """The text under `### <heading>` up to the next heading of any level; "" when the heading is absent."""
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{1,3} |\Z)", doc, re.S | re.M)
    return m.group(1) if m else ""


def _pydef(src, name):
    """The text of top-level `def name(...)` up to the next top-level def or class; "" when absent."""
    m = re.search(r"^def " + re.escape(name) + r"\(.*?(?=^(?:def|class) |\Z)", src, re.S | re.M)
    return m.group(0) if m else ""


def _line_of(src, needle):
    """The whole source line that carries `needle` (the first one), and the line after it."""
    lines = src.split("\n")
    for i, line in enumerate(lines):
        if needle in line:
            return line, (lines[i + 1] if i + 1 < len(lines) else "")
    return "", ""


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _fault_classes(src):
    """The string constants assigned to `prices.fault` in `src` (a def's text), through a plain or a tuple assignment
    (`cfg, prices.fault = None, "file"`): the property the doc's classes rest on, keyed on what is assigned and not
    on the assignment's spelling. An empty set when the text does not parse."""
    try:
        tree = ast.parse(textwrap.dedent(src))
    except SyntaxError:
        return set()
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            pairs = (zip(target.elts, node.value.elts) if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple)
                     else [(target, node.value)])
            for t, v in pairs:
                if (isinstance(t, ast.Attribute) and t.attr == "fault" and isinstance(t.value, ast.Name) and t.value.id == "prices"
                        and isinstance(v, ast.Constant) and isinstance(v.value, str)):
                    out.add(v.value)
    return out


REFERENCE = _read("docs", "reference.md")
SECTION = _section(REFERENCE, "The price feed")
KERNEL = _read("kernel", "kernel.py")
DOC = "docs/reference.md (The price feed)"
EXECUTED = "tests/test_price_feed_off.py"

# the override sentence, as the round worded it, and the clause it replaced
COUNTS = "a row that changes or adds a model's rates counts"
NOT_COUNTED = "a row equal to the table's row for that model does not, so the count says what the file changed, not whether it was read"
ONE_COUNTED = ("With one counted row in the file, the line carries `; 1 row overridden by model-prices.json`, whichever table it "
               "names, after the source (and after the unrecognised clause when there is one) and before the skipped-rows clause "
               "when there is one")
OLD_ENDS_COUNT = "the line ends `; 1 row overridden"   # gear.js pushes the skipped-rows clause after the count (round 2)
OLD_CLAUSE = "with one row in the file, the line ends"
# the cache sentence, as the round worded it
LIFETIME = "in memory until the next restart or the next fetch that lands"
REPLACES = "a landed fetch replaces them with the rows it parsed, even when that is none, and a failed fetch leaves them"
# the kernel's shape behind each claim
COUNT_TEST = "if table.get(k) != v"
# the status's one snapshot (review round 2, under _price_feed_lock): the cache reference is taken first, and the table
# the count is read against is the defaults under THAT reference's rows
SNAPSHOT = 'remote = _price_cache["remote"]'
TABLE_UNDER = "table.update({k: dict(v) for k, v in remote.items()})"
ASSIGN = '_price_cache["remote"] = out'
LANDED_NEXT = '_price_feed["fetchedAt"] = now'
FAIL_CLASS = "_price_feed_error_class(e)"
# the unreadable-row sentence (the review of PR 878, re-ruled 2026-09-21), and the kernel's shape behind each clause
SKIPPED = ("A row the kernel cannot read (not an object, a rate that is not a number, or a rate that is not a finite number) is "
           "skipped and every other row applies, wherever in the file the bad row sits")
NOT_A_NUMBER = ("A rate whose key is present is accepted in two forms, a JSON number or a plain decimal number in quotes (`\"0.5\"`, "
                "`\"3e-06\"`: an optional minus, digits, at most one dot with digits after it, an optional exponent, nothing else), and "
                "the quoted form is read as the number it spells. Anything else where a rate belongs (a null, a list, an object, `true`, "
                "`false` or any other string: `\" 0.5\"`, `\"1_0\"`, `\"inf\"`, `\"nan\"`, `\"1e999\"`, `\"+0.5\"`, `\"\"`) makes that row "
                "a skipped row, said like any other, never a rate of zero or one")
OLD_EVERY_STRING = "a string (a numeric one too)"   # round 2 refused every string; round 3 admits the strict decimal form (2026-09-21)
RATE_READ = "row[kk] = _price_rate_value(raw)"   # round 3: the one read of a rate, shared with the feed worker's parse
OLD_TWO_CLASSES = "(not an object, or a rate that is not a finite number)"   # the round-2 predicate names three
OLD_VOIDS = "voids that row and every row after it"   # the first round's consequence, gone from the doc with the re-ruling
WHOLE = "a file it cannot read or parse as a JSON object is ignored whole"
SAID_ONCE = ("The kernel says so on its stderr the first time the cost view prices with the file in that state (the spend "
             "ceiling's check and `/version` price with the same file and write no line): once per kernel life for the file, and "
             "once per kernel life for each skipped row, naming the row's key there and nowhere else")
OLD_UNCONDITIONAL = "The kernel says so once per kernel life on its stderr, for the file"   # written only on the cost view's road
WHETHER_OPENED = "Whether or not the view was opened, the `priceFeed` block carries the class as `overrideFault`"
CLASSED = ("`priceFeed` block carries the class as `overrideFault` (`row` or `file`, else null) and the number of skipped rows "
           "as `overrideRowsRejected`, never the file's text or its path")
VIEW_CLAUSE = "`; 1 row of model-prices.json could not be read and was skipped (the rest of the file applies)`"
FILE_CLAUSE_TEXT = "model-prices.json could not be read as a JSON object and was ignored (none of it applies)"
FILE_CLAUSE = "with the file ignored whole, that last slot carries `; %s` instead" % FILE_CLAUSE_TEXT
FAULT_KEY = '"overrideFault": merged.fault'
COUNT_KEY = '"overrideRowsRejected": merged.rejected'
FAULT_CLASSES = {"row", "file"}   # the two classes the doc names, each assigned to the merged table's `fault`
REJECT_OBJECT = 'raise ValueError("a row that is not an object")'
REJECT_FINITE = 'raise ValueError("a rate that is not a finite number")'
REJECT_NUMBER = 'raise ValueError("a rate that is not a number")'
FILE_SETS_NO_ROWS = 'cfg, prices.fault = None, "file"'   # the file class leaves no row to read, so the two classes are exclusive
FILE_LATCH = '_price_feed_first("overrideFileSaid")'
ROW_LATCH = '_price_feed_first("overrideRowsSaid", k)'
ROW_HEAD = ("price feed: the row %s in model-prices.json could not be read (not an object, a rate that is not a number, or a "
            "rate that is not finite), so that row is skipped and the rest of the file applies")
FILE_HEAD = "price feed: model-prices.json could not be read as a JSON object, so the file is ignored whole"


def _fault_lines(src):
    """The dict `_PRICE_OVERRIDE_FAULT_LINES` evaluates to, read from the module's source through ast (its values are
    implicit concatenations split across source lines, which a text search for the whole line would miss); {} when the
    assignment is absent or does not evaluate."""
    m = re.search(r"^_PRICE_OVERRIDE_FAULT_LINES = \{.*?^\}", src, re.S | re.M)
    if not m:
        return {}
    try:
        node = ast.parse(m.group(0)).body[0]
        return ast.literal_eval(node.value)
    except (SyntaxError, ValueError, IndexError, AttributeError):
        return {}
GEAR_CLAUSE = "' of model-prices.json could not be read and '"
GEAR_FILE_CLAUSE = "'%s'" % FILE_CLAUSE_TEXT
GEAR_FILE_KEY = "pf.overrideFault === 'file'"
GEAR = _read("ui", "webview", "gear.js")
OVERRIDE_CASES = ("tests/test_price_feed_off.py TheOverrideFileIsSaid (a bad row first, in the middle or last is skipped alone with "
                  "the same table, count and line; two bad rows are two lines and a count of 2; each fault class is said once on "
                  "its own latch, in both orders; a non-object row; a non-finite rate; a long key is clipped; a file that is not a "
                  "JSON object is classed file with a count of 0; no file is no fault and a count of 0) and SayOnceLatches (two "
                  "builds meeting a skipped row together name it once)")


class _Pins(unittest.TestCase):
    def assertQuoted(self, needle, haystack, where, msg=""):
        # a bare assertIn would print the whole file on a miss; name the missing text and the file instead
        self.assertTrue(needle in haystack, "%s does not carry %r%s" % (where, needle, (": " + msg) if msg else ""))

    def assertSection(self):
        self.assertTrue(SECTION, "docs/reference.md has no `### The price feed` subsection")

    def assertBefore(self, first, second, haystack, where, msg):
        # both present, then ordered: str.find's -1 on a miss would otherwise order an absent needle first
        a, b = haystack.find(first), haystack.find(second)
        self.assertGreaterEqual(a, 0, "%s does not carry %r" % (where, first))
        self.assertGreaterEqual(b, 0, "%s does not carry %r" % (where, second))
        self.assertLess(a, b, "%s: %s" % (where, msg))


class TheOverrideCountIsOfRowsThatChange(_Pins):
    def test_the_doc_says_which_rows_count_and_the_kernel_counts_the_same_way(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted(COUNTS, flat, DOC)
        self.assertQuoted(NOT_COUNTED, flat, DOC, "the count is of what the file changed, not of the rows it holds")
        self.assertQuoted(ONE_COUNTED, flat, DOC, "the example clause is conditioned on a counted row")
        status = _pydef(KERNEL, "_price_feed_status")
        self.assertTrue(status, "kernel/kernel.py defines _price_feed_status at the top level")
        where = "kernel/kernel.py _price_feed_status"
        self.assertQuoted(COUNT_TEST, status, where,
                          "the count is of rows whose merged rates differ from the table under them, which is what the doc "
                          "says; the behaviour is executed in %s LiveFeed.test_an_override_row_is_counted_in_the_status_and_the_line "
                          "(a row equal to the default is not an override)" % EXECUTED)
        self.assertBefore(SNAPSHOT, TABLE_UNDER, status, where,
                          "the cache reference the table is built from is the snapshot's, taken before the table")
        self.assertBefore(TABLE_UNDER, COUNT_TEST, status, where,
                          "the table the count is taken against is the defaults under the cached feed rows, the table the "
                          "line names, so 'the table's row for that model' in the doc is that table's")
        self.assertQuoted("changed or added", status, where, "the docstring makes the doc's claim in the same words")

    def test_the_clause_that_promised_a_count_for_any_row_is_gone(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertNotIn(OLD_CLAUSE, flat,
                         "%s: 'with one row in the file, the line ends ...' was false for a row equal to the table's row for "
                         "its model (overrides 0, no tail); the example is conditioned on a counted row now" % DOC)
        self.assertNotIn(OLD_ENDS_COUNT, flat, "%s: the count ends the line only when no row is skipped; the doc says where it "
                         "sits (round 2, pinned to gear.js's order in tests/test_reference_price_feed.py)" % DOC)


class TheCachedRowsLiveUntilARestartOrTheNextLandedFetch(_Pins):
    def test_the_doc_says_a_landed_fetch_replaces_the_rows_and_a_failed_one_leaves_them(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted(LIFETIME, flat, DOC)
        self.assertQuoted(REPLACES, flat, DOC, "there is no cache file, and a later fetch that lands can replace the rows before any restart")
        body = _pydef(KERNEL, "_refresh_remote_prices")
        self.assertTrue(body, "kernel/kernel.py defines _refresh_remote_prices at the top level")
        where = "kernel/kernel.py _refresh_remote_prices"
        # a landed fetch replaces the rows with what it parsed, even none: the assignment is unconditional in the
        # worker's landed branch, at the indent of the status write that follows it, with no guard on `out` before it
        assign, after = _line_of(body, ASSIGN)
        self.assertTrue(assign, "%s does not carry %r" % (where, ASSIGN))
        self.assertIn(LANDED_NEXT, after,
                      "%s: the landed branch records fetchedAt on the line after the cache assignment, the pair this pin reads" % where)
        self.assertEqual(_indent(assign), _indent(after),
                         "%s: the cache assignment sits in the landed branch at the same depth as the status write, unguarded, "
                         "so a landed fetch replaces the cached rows with what it parsed, even an empty table (the doc's 'even "
                         "when that is none'); tests/test_price_feed_consistency.py OneSnapshot."
                         "test_a_landing_waits_for_a_read_that_is_inside_the_status drives a populated cache through a "
                         "landed-empty fetch and pins the settled block as defaults/empty; a guard on `out` here is a "
                         "behaviour change the doc, this pin and that assertion must follow" % where)
        before_assign = body[:body.find(ASSIGN)].rstrip().split("\n")[-1].strip()
        self.assertFalse(before_assign.startswith("if ") or before_assign.startswith("elif "),
                         "%s: the line before the cache assignment is %r, a guard; the doc says the landed rows always replace "
                         "the cache" % (where, before_assign))
        # a failed fetch leaves the rows: the worker's except records the reason class and returns before the assignment
        self.assertBefore(FAIL_CLASS, ASSIGN, body, where,
                          "the failure branch comes before the cache assignment")
        fail_at = body.find(FAIL_CLASS)
        ret_at = body.find("return", fail_at)
        self.assertTrue(0 <= ret_at < body.find(ASSIGN),
                        "%s: the failure branch returns before the cache assignment, so a failed fetch leaves the rows in "
                        "memory (the doc's 'a failed fetch leaves them'); executed in %s FailedFetch."
                        "test_a_failed_refresh_after_a_landed_fetch_says_the_cached_rows_still_serve" % (where, EXECUTED))


class AnUnreadableRowOrFileIsSaid(_Pins):
    """The paragraph that sends a feed-off box to the override file says what a row the kernel cannot read does, and
    the kernel classes, counts and says it (the review of PR 878, re-ruled 2026-09-21). Red over the 5cbf9e397 archive at
    the first doc assertion (the paragraph there says the row voids every row after it); green at the tree. Executed
    in %s.""" % OVERRIDE_CASES

    def test_the_doc_says_what_an_unreadable_row_and_file_do_and_the_kernel_classes_counts_and_says_it(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted(SKIPPED, flat, DOC, "one try wraps each row, so the rows around a rejected one are kept, wherever it sits")
        self.assertNotIn(OLD_VOIDS, flat, "%s: the first round's consequence, whose reach depended on the bad row's position" % DOC)
        self.assertNotIn(OLD_TWO_CLASSES, flat, "%s: the predicate names the third class, a rate present and not a number" % DOC)
        self.assertQuoted(NOT_A_NUMBER, flat, DOC, "the predicate as the kernel applies it: present, then a JSON number and never a bool, "
                          "or a plain decimal in quotes (round 3); every other string the skipped row's road")
        self.assertNotIn(OLD_EVERY_STRING, flat, "%s: round 2 refused every string, a regression on the quoted 0.5 (round 3)" % DOC)
        self.assertQuoted(WHOLE, flat, DOC)
        self.assertQuoted(SAID_ONCE, flat, DOC, "one latch per fault class, the row's keyed by row, on the cost view's road")
        self.assertNotIn(OLD_UNCONDITIONAL, flat, "%s: the lines are written under `if refresh:`, the cost view's road; a kernel "
                         "whose Token usage view never prices with the file in that state writes nothing (round 2)" % DOC)
        self.assertQuoted(WHETHER_OPENED, flat, DOC, "the block's class and count come from every merge, opened or not")
        self.assertQuoted(CLASSED, flat, DOC, "a class and a count, since the block rides the auth-exempt /version")
        self.assertQuoted(VIEW_CLAUSE, flat, DOC, "the modal's clause, quoted as the doc quotes the override count's")
        self.assertQuoted(FILE_CLAUSE, flat, DOC, "the whole-file clause, in the same slot, quoted the same way (round 2)")
        status = _pydef(KERNEL, "_price_feed_status")
        self.assertTrue(status, "kernel/kernel.py defines _price_feed_status at the top level")
        self.assertQuoted(FAULT_KEY, status, "kernel/kernel.py _price_feed_status",
                          "the block carries the merged table's own fault class as a literal key; executed in %s" % OVERRIDE_CASES)
        self.assertQuoted(COUNT_KEY, status, "kernel/kernel.py _price_feed_status",
                          "the block carries the merged table's own count of skipped rows as a literal key; executed in %s" % OVERRIDE_CASES)
        prices = _pydef(KERNEL, "_model_prices")
        self.assertTrue(prices, "kernel/kernel.py defines _model_prices at the top level")
        where = "kernel/kernel.py _model_prices"
        self.assertEqual(_fault_classes(prices), FAULT_CLASSES,
                         "%s assigns exactly the two classes the doc names to the merged table's fault: row for a rejected row, "
                         "file for a file that cannot be read or parsed as a JSON object (read by ast, so a tuple assignment "
                         "counts); a third class is a doc change" % where)
        self.assertQuoted(FILE_LATCH, prices, where, "the file fault's own latch: said once per kernel life")
        self.assertQuoted(ROW_LATCH, prices, where, "the row fault's own latch, keyed by the row: each row said once per kernel life")
        self.assertNotIn('_price_feed_first("overrideSaid")', prices,
                         "%s: one latch across both classes let the first fault of either silence the other's first" % where)
        lines = _fault_lines(KERNEL)
        self.assertEqual(set(lines), FAULT_CLASSES, "kernel/kernel.py _PRICE_OVERRIDE_FAULT_LINES carries one line head per fault class")
        self.assertEqual(lines["row"], ROW_HEAD, "the stderr line for a skipped row names the row (the %s) and states the consequence the doc states")
        self.assertEqual(lines["file"], FILE_HEAD, "the stderr line for an unreadable file states the consequence the doc states")
        self.assertQuoted(GEAR_CLAUSE, GEAR, "ui/webview/gear.js raPriceNote", "the clause the doc quotes, keyed on the block's count; "
                          "executed in ui/webview/analytics-price-source-states.test.ts")
        self.assertQuoted(GEAR_FILE_CLAUSE, GEAR, "ui/webview/gear.js raPriceNote", "the whole-file clause the doc quotes, as fixed text")
        self.assertQuoted(GEAR_FILE_KEY, GEAR, "ui/webview/gear.js raPriceNote", "keyed on the block's class alone, never the path")
        self.assertEqual(KERNEL.count(FILE_SETS_NO_ROWS), 2,
                         "kernel/kernel.py _model_prices: the file class is assigned with cfg set to None in the same statement (an "
                         "unreadable file, a file that is not an object), so no row is read and the row class is never assigned "
                         "beside it: the doc's 'one class or the other, never both'; executed in %s" % EXECUTED)

    def test_the_fault_lines_are_written_on_the_cost_views_road_alone_and_the_block_is_from_every_merge(self):
        """The doc conditions the stderr sentence the way the off line's is (round 2): both fault lines sit under `if refresh:`
        in _model_prices, the cost view's road, while _price_feed_status merges with refresh=False and carries the class and
        the count from that merge, so /version says the class whether or not the view was opened. Read by ast: every call of
        _price_feed_line in the def is inside an If whose test is the name `refresh`."""
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted(SAID_ONCE, flat, DOC)
        self.assertQuoted(WHETHER_OPENED, flat, DOC)
        prices = _pydef(KERNEL, "_model_prices")
        self.assertTrue(prices, "kernel/kernel.py defines _model_prices at the top level")
        where = "kernel/kernel.py _model_prices"
        tree = ast.parse(textwrap.dedent(prices))
        def _calls(node):
            return [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_price_feed_line"]
        every = _calls(tree)
        self.assertEqual(len(every), 2, "%s writes two fault lines, the file's and the row's" % where)
        guarded = []
        for n in ast.walk(tree):
            if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == "refresh":
                guarded.extend(_calls(n))
        self.assertEqual(len(guarded), len(every),
                         "%s: %d of %d fault lines sit under `if refresh:`; every one must, since that is the cost view's road (the "
                         "doc's 'the first time the cost view prices with the file in that state') and the spend guard and the status "
                         "pass refresh=False; a line outside the guard is written by every merge" % (where, len(guarded), len(every)))
        status = _pydef(KERNEL, "_price_feed_status")
        self.assertQuoted("_model_prices(now, refresh=False)", status, "kernel/kernel.py _price_feed_status",
                          "the block's class and count come from a merge that writes no line, so /version carries them whether or "
                          "not the view was opened")
        self.assertQuoted(FAULT_KEY, status, "kernel/kernel.py _price_feed_status")
        self.assertQuoted(COUNT_KEY, status, "kernel/kernel.py _price_feed_status")
        self.assertGreaterEqual(KERNEL.count("_model_prices(int(now), refresh=False)"), 2, "the spend ceiling's two roads price with refresh=False (T350)")

    def test_the_consequence_the_doc_states_is_the_codes_one_try_around_each_row(self):
        """The doc's 'skipped and every other row applies' is a try INSIDE the loop whose handler continues: a try around the
        whole loop, the first round's shape, ended the loop at the bad row and lost every row after it. Read by ast, so
        the property is the structure and not a spelling: the loop over the file's rows holds the try, the try's handler
        ends in `continue`, and no try encloses the loop."""
        self.assertSection()
        self.assertQuoted(SKIPPED, _flat(SECTION), DOC)
        prices = _pydef(KERNEL, "_model_prices")
        self.assertTrue(prices, "kernel/kernel.py defines _model_prices at the top level")
        where = "kernel/kernel.py _model_prices"
        self.assertQuoted(REJECT_OBJECT, prices, where, "a row that is not an object is rejected")
        self.assertQuoted(RATE_READ, prices, where, "each rate is read by _price_rate_value inside the row's try (round 3), so its "
                          "two refusals below land in this row's reject path; executed in %s" % OVERRIDE_CASES)
        helper = _pydef(KERNEL, "_price_rate_value")
        self.assertTrue(helper, "kernel/kernel.py defines _price_rate_value at the top level")
        self.assertQuoted(REJECT_NUMBER, helper, "kernel/kernel.py _price_rate_value",
                          "a rate that is present and not a JSON number, nor a string in the strict decimal form, is rejected (rounds 2 and 3)")
        self.assertQuoted(REJECT_FINITE, helper, "kernel/kernel.py _price_rate_value", "a rate that is not a finite number is rejected")
        tree = ast.parse(textwrap.dedent(prices))
        loops = [n for n in ast.walk(tree) if isinstance(n, ast.For) and any(isinstance(b, ast.Try) for b in n.body)]
        self.assertEqual(len(loops), 1, "%s: one loop whose body opens a try, the loop over the file's rows (the loop that writes "
                         "the rows' lines holds none)" % where)
        loop = loops[0]
        tries_in_loop = [n for n in loop.body if isinstance(n, ast.Try)]
        self.assertEqual(len(tries_in_loop), 1, "%s: the loop's body opens one try, around the row" % where)
        handler_bodies = [h.body for h in tries_in_loop[0].handlers]
        self.assertTrue(handler_bodies and all(isinstance(b[-1], ast.Continue) for b in handler_bodies),
                        "%s: the row's handler ends in continue, so the bad row alone is skipped (the doc's 'every other row "
                        "applies'); a raise or a fall-through is the other shape" % where)
        enclosing = [n for n in ast.walk(tree) if isinstance(n, ast.Try) and any(c is loop for c in ast.walk(n))]
        self.assertEqual(enclosing, [], "%s: no try encloses the loop; the first round's one did, and a rejected row ended it "
                         "(the doc's old 'and every row after it')" % where)
        self.assertBefore(RATE_READ, 'prices.fault = "row"', prices, where, "the class is assigned after the loop that skips (the read "
                          "that refuses sits inside the loop; round 3 moved the raises into _price_rate_value)")
        self.assertBefore('prices.fault = "row"', "prices.rejected = len(rejected)", prices, where,
                          "the count beside the class, both on the merged table")


class TheNewProse(_Pins):
    def test_no_em_or_en_dash_and_not_the_banned_word(self):
        self.assertSection()
        self.assertNotIn(chr(0x2014), SECTION, "the price feed subsection")   # em dash
        self.assertNotIn(chr(0x2013), SECTION, "the price feed subsection")   # en dash
        self.assertNotIn("fleet", SECTION.lower(), "the price feed subsection")


if __name__ == "__main__":
    unittest.main()
