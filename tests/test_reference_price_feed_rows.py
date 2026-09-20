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

Text only, the tests/test_reference_price_feed.py precedent: the doc and the kernel are read as files, nothing
loads romp code, and no state root is minted. A pin keyed on where the code lives says in its message what it
guards and names the executed test that proves the behaviour. Every case asserts the doc's text FIRST, so a run
over a tree without the round's wording fails at that assertion and never at a missing symbol.
"""
import os
import re
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


REFERENCE = _read("docs", "reference.md")
SECTION = _section(REFERENCE, "The price feed")
KERNEL = _read("kernel", "kernel.py")
DOC = "docs/reference.md (The price feed)"
EXECUTED = "tests/test_price_feed_off.py"

# the override sentence, as the round worded it, and the clause it replaced
COUNTS = "a row that changes or adds a model's rates counts"
NOT_COUNTED = "a row equal to the table's row for that model does not, so the count says what the file changed, not whether it was read"
ONE_COUNTED = "With one counted row in the file, the line ends `; 1 row overridden by model-prices.json`"
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


class TheNewProse(_Pins):
    def test_no_em_or_en_dash_and_not_the_banned_word(self):
        self.assertSection()
        self.assertNotIn(chr(0x2014), SECTION, "the price feed subsection")   # em dash
        self.assertNotIn(chr(0x2013), SECTION, "the price feed subsection")   # en dash
        self.assertNotIn("fleet", SECTION.lower(), "the price feed subsection")


if __name__ == "__main__":
    unittest.main()
