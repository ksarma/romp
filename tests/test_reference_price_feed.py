#!/usr/bin/env python3
"""docs/reference.md's price feed subsection and its analytics sentence quote what the code does (2026-09-20).

ROMP_PRICE_FEED=off is the price feed's off switch (kernel/kernel.py _price_feed_off, the first statement of
_refresh_remote_prices, the one place a fetch can start), and the Token usage modal's line under the footnote
(ui/webview/gear.js raPriceNote) says where its prices came from. The reference describes both by quoting the
variable and the line's text, and nothing else ties the doc to the code, so these pins hold it there: the
reference carries the subsection (beside Judge concurrency) and the analytics sentence; the fragments it quotes
are the ones gear.js renders and kernel.py reads; the six-hour, host and override-file claims are the kernel's
constants; the entry's word that the line and the block count the override file's rows in effect is tied to
_price_feed_status counting them from the merge (_model_prices, which applies the file last; review round 2: the
merge's two needles are each asserted present before their order is compared, since str.find returns -1 on a
miss and -1 sorts before any found index) and to the gear.js clause the entry quotes (review round 1,
2026-09-20: a row in the file prices its model whichever table the line names, and the line says so instead of
reading as the table alone); and the new prose carries no em or en dash
and not the word the repo's CLAUDE.md bans. A wording change in gear.js or a moved constant reddens here before
the reference goes stale.

The review of PR 878 (2026-09-21) corrected two claims and added one. The subsection stated the guarantee's
condition as the variable being SET, wider than the code's (only the value off, stripped and case-folded, turns the
feed off; any other value leaves it on and, since that review, is SAID: one stderr line naming the value at the
first attempt that reads it, the boolean `unrecognised` in the priceFeed block, and one clause on the modal's line);
TheSwitchValueRule pins the condition, the other-values clause and the said-so clause, each tied to the kernel's
_price_feed_unrecognised, the status literal's key, the stderr line's head and the gear.js clause. The subsection
said a rate an override row omits keeps the table's, where _model_prices resolves the base by the exact id alone
(`base = prices.get(k, {})`), so an id the table does not name zeroes its omitted rates; ThePartialRowRule pins the
corrected sentence and names the executed guard (tests/test_price_feed_off.py APartialOverrideRow). Both classes
are red over a git archive of the reviewed head d1026b768 at their first doc assertion (the subsection there says
"With the variable set" and "a rate the row omits keeps the table's.") and green at the tree.

The second round of that review (2026-09-21) corrected three more claims. The subsection said the modal's line ENDS with
the unrecognised clause, ends with the override count and ends with the skipped-rows clause, three claims that cannot all
hold: gear.js raPriceNote pushes the clauses in one order (the unrecognised clause, the override count, the skipped rows,
then the whole-file clause, on both sources), so only the last slot ends the line. The doc now says where each clause
sits, and TheLineClausesSitWhereGearJsPutsThem pins the words to that push order by index on both branches (the executed
proof is ui/webview/analytics-price-source-states.test.ts). The override merge no longer coerces a rate that is present
and not a JSON number (`float(x or 0)` priced null, an empty string, a list, an object or false at zero per token and
true at a dollar per token, with the block reading a clean override): such a row is rejected into the per-row path, and
ThePartialRowRule's anchor moved to the merge's new shape (the table's rate only when the KEY is absent). The trigger
sentence, which the reference had right, gained a pin on the TTL compare and the stamp before the thread start, so the
reference and SECURITY.md move together.

Text only: the behaviour is pinned in tests/test_price_feed_off.py (the kernel) and
ui/webview/analytics-price-source.test.ts (the view). The doc and the sources are read as files; nothing loads
romp code, so no state root is minted. Every case asserts the doc's text FIRST, so a run over a tree without
the subsection fails at that assertion and never at a slice or a missing symbol.
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


def _paragraph(doc, opening):
    """The blank-line-delimited paragraph that begins with `opening`; "" when none does."""
    for para in doc.split("\n\n"):
        if para.startswith(opening):
            return para
    return ""


def _pydef(src, name):
    """The text of top-level `def name(...)` up to the next top-level def or class; "" when absent."""
    m = re.search(r"^def " + re.escape(name) + r"\(.*?(?=^(?:def|class) |\Z)", src, re.S | re.M)
    return m.group(0) if m else ""


def _jsdef(src, name):
    """The text of top-level `function name(...) {` up to its closing brace at column 0; "" when absent."""
    m = re.search(r"^function " + re.escape(name) + r"\(.*?^\}", src, re.S | re.M)
    return m.group(0) if m else ""


REFERENCE = _read("docs", "reference.md")
SECTION = _section(REFERENCE, "The price feed")
ANALYTICS = _paragraph(REFERENCE, "The gear's analytics modal")
KERNEL = _read("kernel", "kernel.py")
GEAR = _read("ui", "webview", "gear.js")

VAR = "ROMP_PRICE_FEED"
# gear.js raPriceNote assembles the defaults reading as 'prices: built-in defaults' + '; ' + why
DEFAULTS_HEAD = "prices: built-in defaults"
WHY_OFF = "live feed off (%s=off)" % VAR
OFF_LINE = DEFAULTS_HEAD + "; " + WHY_OFF
# the kernel's one stderr line under the switch, and the constants the doc's claims rest on
OFF_STDERR = "price feed: off (%s=off)" % VAR
TTL_LINE = "PRICE_TTL = 6 * 3600"
FEED_HOST = "raw.githubusercontent.com"
CONFIG_LINE = 'PRICE_CONFIG = Path(os.path.expanduser("~/.config/romp/model-prices.json"))'
ROW_KEYS = ("in", "out", "cache_w", "cache_r")
# _model_prices merges the feed's cached rows over the defaults, then reads the override file, so a row there wins
FEED_MERGE = '_price_cache["remote"]'
FILE_READ = "PRICE_CONFIG.read_text()"
# the analytics paragraph's new sentence, and the anchor it links
SENTENCE_HEAD = "A line under the footnote says where the table's prices came from"
LINK = "[The price feed](#the-price-feed)"
# the switch's value rule (the review of PR 878): the condition, what any other value does, and how that is said
RULE = "Only `off`, whitespace and case ignored, turns the feed off"
OTHER_VALUES = "any other value, `0`, `false` and `no` included, leaves the feed on, and the kernel says so"
SAID_STDERR = "one line on its stderr naming the value the first time it would have fetched"
SAID_SURFACES = "the line under the footnote and `/version`'s `priceFeed` block say the variable is set to a value that is not off"
UNREC_CLAUSE = "ROMP_PRICE_FEED is set to a value that is not off, so the feed stays on (only off turns it off)"
UNREC_KEY = '"unrecognised": unrecognised'
UNREC_STDERR = "price feed: ROMP_PRICE_FEED is set to %s, which is not off, so the feed stays on"
OLD_CONDITION = "With the variable set, the table"
# the override row's omitted rates (the review of PR 878): the table's only for an id the table names, zero otherwise
OMITS_NAMED = "a rate the row omits keeps the table's only for an id the table itself names"
OMITS_OTHER = "for any other id (a dated id, a model the table lacks) the omitted rates are zero, not a related model's"
OMITS_EXACT = "the row is matched by its exact id and inherits nothing"
OLD_OMITS = "and a rate the row omits keeps the table's."
BASE_EXACT = "base = prices.get(k, {})"
PARTIAL_GUARD = "tests/test_price_feed_off.py APartialOverrideRow.test_an_omitted_rate_keeps_the_tables_only_for_an_id_the_table_names"
# the merge's read of a row's rate (the second round of the review of PR 878): the table's rate only when the KEY is
# absent, and a present value accepted only as a JSON number, never coerced
INHERIT = "v[kk] if kk in v else base.get(kk, 0)"
TYPE_CHECK = "isinstance(raw, bool) or not isinstance(raw, (int, float))"
REJECT_NUMBER = 'raise ValueError("a rate that is not a number")'
OLD_INHERIT = "v.get(kk, base.get(kk, 0))"
# where each clause of the modal's line sits (the second round): the words, and gear.js raPriceNote's push order behind them
UNREC_SITS = "after the source and before the override count"
OVR_SITS = "after the source (and after the unrecognised clause when there is one) and before the skipped-rows clause when there is one"
FEED_PUSHES = ("tails.push(unrec)", "tails.push(ovr)", "tails.push(rej)", "tails.push(badFile)")
DEFAULTS_TAILS = ("(unrec ? '; ' + unrec : '')", "(ovr ? '; ' + ovr : '')", "(rej ? '; ' + rej : '')", "(badFile ? '; ' + badFile : '')")
ENDS_CLAUSE = "1 row of model-prices.json could not be read and was skipped (the rest of the file applies)"
# the trigger (the reference's wording, now SECURITY.md's too), and the kernel's compare, stamp and thread start behind it
TRIGGER = "when the modal opens and the last fetch attempt is more than six hours old, or there has been none"
TTL_CHECK = 'if now - _price_cache["t"] < PRICE_TTL:'
TTL_STAMP = '_price_cache["t"] = now'
THREAD_START = "threading.Thread(target=work"


class _Pins(unittest.TestCase):
    def assertQuoted(self, needle, haystack, where, msg=""):
        # a bare assertIn would print the whole file on a miss; name the missing text and the file instead
        self.assertTrue(needle in haystack, "%s does not carry %r%s" % (where, needle, (": " + msg) if msg else ""))

    def assertSection(self):
        self.assertTrue(SECTION, "docs/reference.md has no `### The price feed` subsection")


class TheReferenceCarriesTheSubsection(_Pins):
    DOC = "docs/reference.md (The price feed)"

    def test_the_subsection_sits_beside_the_judge_concurrency_knob(self):
        self.assertSection()
        before, after = REFERENCE.find("### Judge concurrency"), REFERENCE.find("### Fast mode for the judges")
        at = REFERENCE.find("### The price feed")
        self.assertTrue(0 <= before < at < after, "the subsection sits between Judge concurrency and Fast mode for the judges, "
                        "with the other kernel env vars of the Configuration section")
        self.assertEqual(REFERENCE.count("### The price feed"), 1, "one subsection, not a duplicate")

    def test_it_names_the_switch_and_where_the_service_reads_it(self):
        self.assertSection()
        self.assertQuoted("`%s=off`" % VAR, SECTION, self.DOC)
        self.assertQuoted("`service.env`", SECTION, self.DOC, "the service reads its env from service.env, then a restart")
        self.assertQuoted("restart", SECTION, self.DOC)
        self.assertQuoted('os.environ.get("%s")' % VAR, KERNEL, "kernel/kernel.py", "the switch the doc names is the one the kernel reads")

    def test_it_says_what_the_fetch_is_and_the_kernel_agrees(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted("more than six hours old", flat, self.DOC)
        self.assertQuoted(TTL_LINE, KERNEL, "kernel/kernel.py", "six hours is the kernel's TTL")
        self.assertQuoted("`%s`" % FEED_HOST, SECTION, self.DOC, "the host the request goes to")
        self.assertQuoted('PRICE_FEED_URL = "https://%s/' % FEED_HOST, KERNEL, "kernel/kernel.py")
        self.assertQuoted("with no credential", flat, self.DOC)
        self.assertQuoted("in memory until the next restart", flat, self.DOC, "there is no cache file")

    def test_it_quotes_the_modal_line_gear_js_renders(self):
        self.assertSection()
        self.assertQuoted("`%s`" % OFF_LINE, _flat(SECTION), self.DOC, "the reading under the switch, as the modal renders it")
        src = "ui/webview/gear.js"
        self.assertQuoted("'%s'" % DEFAULTS_HEAD, GEAR, src)
        self.assertQuoted("'%s'" % WHY_OFF, GEAR, src)
        self.assertQuoted("'; ' + why", GEAR, src, "the head and the reason are joined by '; ', which the doc's quote carries")

    def test_it_names_version_and_the_kernel_carries_the_block_beside_the_catalog(self):
        self.assertSection()
        for needle in ("`/version`", "`priceFeed`", "`modelCatalog`"):
            self.assertQuoted(needle, SECTION, self.DOC)
        feed, catalog = '"priceFeed": _price_feed_status()', '"modelCatalog": _catalog_public_status()'
        self.assertQuoted(feed, KERNEL, "kernel/kernel.py")
        self.assertQuoted(catalog, KERNEL, "kernel/kernel.py")
        self.assertLess(abs(KERNEL.find(feed) - KERNEL.find(catalog)), 600, "the two keys sit beside each other in _version_info")

    def test_it_says_the_kernel_logs_one_line_naming_the_variable(self):
        self.assertSection()
        self.assertQuoted("logs one line, naming the variable", _flat(SECTION), self.DOC)
        self.assertQuoted(OFF_STDERR, KERNEL, "kernel/kernel.py", "the stderr line names the variable")

    def test_it_says_the_spend_ceiling_check_never_fetches(self):
        self.assertSection()
        self.assertQuoted("The spend ceiling's check never fetches", _flat(SECTION), self.DOC)
        self.assertGreaterEqual(KERNEL.count("_model_prices(int(now), refresh=False)"), 2,
                                "the guard's two roads price with refresh=False (T350)")

    def test_it_documents_the_override_file_the_kernel_reads(self):
        self.assertSection()
        self.assertQuoted("`~/.config/romp/model-prices.json`", SECTION, self.DOC)
        self.assertQuoted(CONFIG_LINE, KERNEL, "kernel/kernel.py")
        for key in ROW_KEYS:
            self.assertQuoted("`%s`" % key, SECTION, self.DOC, "a row's four rates")
        self.assertQuoted('("in", "out", "cache_w", "cache_r")', KERNEL, "kernel/kernel.py", "the keys _model_prices reads from a row")

    def test_it_says_the_line_counts_the_override_rows_and_the_status_counts_them_from_the_merge(self):
        # The line and the priceFeed block come from _price_feed_status. A row in the override file prices its model
        # whichever table the line names (_model_prices applies the file after the defaults and the feed), so the
        # status counts the rows in effect from that merge (`overrides`, through _model_prices with refresh=False,
        # the road that never fetches) and the line ends with the count; the entry says so rather than promising
        # the built-in defaults. Review round 1: the first draft documented the line as blind to the file, which
        # left the visible statement false in the configuration the entry itself recommends. The omitted-rate tie moved to
        # ThePartialRowRule with the corrected words (the review of PR 878), so this case is green over that head's archive
        # and records nothing.
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted("count the rows the file puts in effect", flat, self.DOC)
        self.assertQuoted("`; 1 row overridden by model-prices.json`", flat, self.DOC)
        status, prices = _pydef(KERNEL, "_price_feed_status"), _pydef(KERNEL, "_model_prices")
        self.assertTrue(status and prices, "kernel/kernel.py defines _price_feed_status and _model_prices at the top level")
        self.assertQuoted("_model_prices(now, refresh=False)", status, "kernel/kernel.py _price_feed_status",
                          "the count comes from the merge that prices, never a second parse of the file")
        self.assertQuoted('"overrides": overrides', status, "kernel/kernel.py _price_feed_status", "the block carries the count")
        self.assertQuoted("' row' : ' rows') + ' overridden by model-prices.json'", GEAR, "ui/webview/gear.js",
                          "the clause the doc quotes, on either source")
        # Review round 2: both needles are asserted present before their order is compared. str.find returns -1 on
        # a miss and -1 is less than any found index, so without the first assertQuoted a _model_prices that no
        # longer merged the feed's rows, or merged them under another key, kept this pin green.
        self.assertQuoted(FEED_MERGE, prices, "kernel/kernel.py _model_prices", "the feed's cached rows are merged into the table")
        self.assertQuoted(FILE_READ, prices, "kernel/kernel.py _model_prices")
        self.assertLess(prices.find(FEED_MERGE), prices.find(FILE_READ),
                        "the override is applied after the feed's rows, so a row there replaces the table's")


class TheSwitchValueRule(_Pins):
    """The condition is the code's, not setness (the review of PR 878). Red over the d1026b768 archive at the first
    doc assertion of each case (the subsection there reads "With the variable set" and states no value rule); green
    at the tree. The behaviour is executed in tests/test_price_feed_off.py OffSwitch (the spelling, the said-once
    line naming the value, off in any case or padding never read as unrecognised) and
    ui/webview/analytics-price-source-states.test.ts (the clause on either source)."""
    DOC = "docs/reference.md (The price feed)"

    def test_it_states_that_only_off_turns_the_feed_off_and_the_kernel_reads_it_that_way(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted(RULE, flat, self.DOC, "the condition as the code has it, in the sibling bullets' value-rule voice")
        self.assertQuoted(OTHER_VALUES, flat, self.DOC, "what any other value does, the three a reader would try named")
        self.assertQuoted("Set the variable to `off` where the kernel's service sees it", flat, self.DOC)
        self.assertQuoted("With the variable set to `off`, the table is the built-in defaults", flat, self.DOC)
        self.assertNotIn(OLD_CONDITION, flat,
                         "%s: 'With the variable set' stated the condition as setness, wider than the code's equality "
                         "against off after strip and case-fold" % self.DOC)
        off = _pydef(KERNEL, "_price_feed_off")
        self.assertTrue(off, "kernel/kernel.py defines _price_feed_off at the top level")
        self.assertQuoted('.strip().lower() == "off"', off, "kernel/kernel.py _price_feed_off",
                          "only off, stripped and case-folded, turns the feed off; executed in tests/test_price_feed_off.py "
                          "OffSwitch.test_the_spelling_is_the_catalogs_stripped_and_case_folded")
        unrec = _pydef(KERNEL, "_price_feed_unrecognised")
        self.assertTrue(unrec, "kernel/kernel.py defines _price_feed_unrecognised at the top level: the read that says so")
        self.assertQuoted('v.lower() != "off"', unrec, "kernel/kernel.py _price_feed_unrecognised",
                          "set, non-empty after strip and not off in any case is the value the doc's clause describes")

    def test_it_says_a_value_that_is_not_off_is_said_and_each_surface_carries_it(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted(SAID_STDERR, flat, self.DOC, "the stderr line, at the first attempt that reads the value")
        self.assertQuoted(SAID_SURFACES, flat, self.DOC, "the modal's line and /version")
        self.assertQuoted("`; %s`" % UNREC_CLAUSE, flat, self.DOC, "the clause as the modal renders it, quoted whole")
        self.assertQuoted("the block carries the fact as the boolean `unrecognised`", flat, self.DOC)
        self.assertQuoted("the value itself is in the kernel's log and nowhere else", flat, self.DOC,
                          "/version is auth-exempt and an environment value is arbitrary text")
        self.assertQuoted(UNREC_STDERR, KERNEL, "kernel/kernel.py", "the stderr line's head names the variable and the value; "
                          "executed in tests/test_price_feed_off.py OffSwitch."
                          "test_a_value_that_is_not_off_leaves_the_feed_on_and_is_said_once_naming_the_value")
        status = _pydef(KERNEL, "_price_feed_status")
        self.assertTrue(status, "kernel/kernel.py defines _price_feed_status at the top level")
        self.assertQuoted(UNREC_KEY, status, "kernel/kernel.py _price_feed_status", "the block carries the boolean as a literal key")
        self.assertNotIn("os.environ", status, "kernel/kernel.py _price_feed_status reads the switch through its two boolean "
                         "readers and never puts an environment value in the block")
        src = "ui/webview/gear.js"
        self.assertQuoted("'%s'" % UNREC_CLAUSE, GEAR, src, "the clause the doc quotes, on either source")
        self.assertQuoted("pf.unrecognised === true", GEAR, src, "worded only for the boolean true, so an older kernel's block says nothing")


class ThePartialRowRule(_Pins):
    """An omitted override rate keeps the table's only for an id the table names (the review of PR 878). Red over the
    d1026b768 archive at the first doc assertion (the subsection there says "a rate the row omits keeps the table's."
    for every id); green at the tree. The code is unchanged: the ruling took the prose branch, and the executed guard
    named below pins the base resolution by mutation."""
    DOC = "docs/reference.md (The price feed)"

    def test_it_says_an_omitted_rate_keeps_the_tables_only_for_an_id_the_table_names(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted(OMITS_NAMED, flat, self.DOC)
        self.assertQuoted(OMITS_OTHER, flat, self.DOC, "a partial row for an id the six built-in rows do not name zeroes what it omits")
        self.assertQuoted(OMITS_EXACT, flat, self.DOC, "no inheritance through the signature or family fallback")
        self.assertNotIn(OLD_OMITS, flat, "%s: the unconditional clause overstated the merge" % self.DOC)
        prices = _pydef(KERNEL, "_model_prices")
        self.assertTrue(prices, "kernel/kernel.py defines _model_prices at the top level")
        where = "kernel/kernel.py _model_prices"
        self.assertQuoted(BASE_EXACT, prices, where, "the base is the exact id's row, never _price_for's fallback; executed in %s" % PARTIAL_GUARD)
        self.assertNotIn("_price_for(", prices, "%s resolves the base by the exact id: a fallback here is the contract change the "
                         "doc's sentence, this pin and %s must follow" % (where, PARTIAL_GUARD))
        self.assertQuoted(INHERIT, prices, where,
                          "a rate the row omits (the KEY absent) reads the base row's, which is the table's for an id it names and "
                          "empty otherwise; a present value is read as it is, so the type check below sees it")
        self.assertNotIn(OLD_INHERIT, prices, "%s: `.get(kk, ...)` read a present null as absent, and `or 0` coerced it "
                         "(the second round of the review of PR 878)" % where)

    def test_a_present_rate_that_is_not_a_number_is_a_skipped_row_never_a_coerced_one(self):
        # the second round of the review of PR 878: `float(v.get(kk, base.get(kk, 0)) or 0)` priced a row whose rate was
        # null, "", [], {} or false at zero per token and true at a dollar per token while the block read a clean
        # override; the doc states the predicate that ships, and the kernel raises into the per-row reject path
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted("a rate whose key is present is accepted only as a JSON number, an int or a float and never a bool", flat, self.DOC)
        self.assertQuoted("a null, a string (a numeric one too), a list, an object, `true` or `false` where a rate belongs makes that "
                          "row a skipped row, never a rate of zero or one", flat, self.DOC)
        prices = _pydef(KERNEL, "_model_prices")
        self.assertTrue(prices, "kernel/kernel.py defines _model_prices at the top level")
        where = "kernel/kernel.py _model_prices"
        self.assertQuoted(TYPE_CHECK, prices, where, "a bool first (it is an int to isinstance), then anything not an int or a float")
        self.assertQuoted(REJECT_NUMBER, prices, where, "raised inside the row's try, so the row lands in the reject path that "
                          "already exists; executed in tests/test_price_feed_off.py TheOverrideFileIsSaid (seven shapes and the "
                          "absent-key control)")
        self.assertLess(prices.find(TYPE_CHECK), prices.find(REJECT_NUMBER), "%s: the check, then the raise" % where)
        # by ast, since the docstring names the old expression: no float() of an `or` expression is left in the merge
        coerced = [n for n in ast.walk(ast.parse(textwrap.dedent(prices)))
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "float"
                   and n.args and isinstance(n.args[0], ast.BoolOp)]
        self.assertEqual(coerced, [], "%s: a float() of an `or` expression is the coercion the round removed" % where)


class TheLineClausesSitWhereGearJsPutsThem(_Pins):
    """The subsection says where each clause of the modal's price line sits, and gear.js raPriceNote puts it there (the
    second round of the review of PR 878: three sentences each said the line ENDS with a different clause). Red over an
    archive of that round's head at the first doc assertion of each case (the subsection there says "the line ends" of
    the unrecognised clause and of the override count); green at the tree. The rendered order is executed in
    ui/webview/analytics-price-source-states.test.ts."""
    DOC = "docs/reference.md (The price feed)"

    def test_the_doc_says_where_each_clause_sits_and_only_the_last_slot_ends_the_line(self):
        self.assertSection()
        flat = _flat(SECTION)
        self.assertQuoted("(the line carries `; %s` %s" % (UNREC_CLAUSE, UNREC_SITS), flat, self.DOC,
                          "the unrecognised clause: after the source, before the override count")
        self.assertQuoted("the line carries `; 1 row overridden by model-prices.json`, whichever table it names, %s" % OVR_SITS,
                          flat, self.DOC, "the override count: after the source and the unrecognised clause, before the skipped rows")
        self.assertNotIn("the line ends `; %s`" % UNREC_CLAUSE, flat, "%s: the unrecognised clause ends the line only when no row "
                         "is counted or skipped" % self.DOC)
        self.assertNotIn("the line ends `; 1 row overridden", flat, "%s: the override count ends the line only when no row is "
                         "skipped" % self.DOC)
        ends = re.findall(r"ends `; ([^`]*)`", flat)
        self.assertEqual(ends, [ENDS_CLAUSE], "%s: one clause is said to end the line, the skipped rows', the last slot on both "
                         "branches (the whole-file clause takes that slot instead and is said so, not as a second 'ends')" % self.DOC)
        note = _jsdef(GEAR, "raPriceNote")
        self.assertTrue(note, "ui/webview/gear.js defines raPriceNote at the top level")
        where = "ui/webview/gear.js raPriceNote"
        for seq, branch in ((FEED_PUSHES, "the feed branch's pushes"), (DEFAULTS_TAILS, "the defaults branch's tail")):
            at = [note.find(s) for s in seq]
            for s, i in zip(seq, at):
                self.assertGreaterEqual(i, 0, "%s does not carry %r" % (where, s))
            self.assertEqual(at, sorted(at), "%s: %s run unrecognised, override count, skipped rows, whole file, the order the "
                             "doc's 'after' and 'before' describe: %r" % (where, branch, list(zip(seq, at))))
        self.assertLess(note.find("'prices: live feed'"), note.find(FEED_PUSHES[0]), "%s: the source comes first" % where)
        self.assertLess(note.find("'prices: built-in defaults'"), note.find(DEFAULTS_TAILS[0]), "%s: the source comes first" % where)

    def test_the_trigger_is_the_last_attempt_and_the_kernel_stamps_it_before_the_fetch(self):
        # the reference had this right; pinned so SECURITY.md (tests/test_security_price_feed.py) and this document move
        # together: the compare reads the stamp of the last ATTEMPT, written before the worker thread starts
        self.assertSection()
        self.assertQuoted(TRIGGER, _flat(SECTION), self.DOC)
        refresh = _pydef(KERNEL, "_refresh_remote_prices")
        self.assertTrue(refresh, "kernel/kernel.py defines _refresh_remote_prices at the top level")
        where = "kernel/kernel.py _refresh_remote_prices"
        for needle in (TTL_CHECK, TTL_STAMP, THREAD_START):
            self.assertQuoted(needle, refresh, where)
        self.assertLess(refresh.find(TTL_CHECK), refresh.find(TTL_STAMP), "%s: the check, then the stamp" % where)
        self.assertLess(refresh.find(TTL_STAMP), refresh.find(THREAD_START), "%s: the stamp before the thread start, so a fetch "
                        "that fails or lands nothing has stamped the attempt (the doc's 'last fetch attempt')" % where)
        self.assertQuoted('_price_cache = {"t": 0', KERNEL, "kernel/kernel.py", "no attempt yet reads as a stale one: the first open fetches")


class TheAnalyticsParagraphPointsAtTheLine(_Pins):
    DOC = "docs/reference.md (the analytics modal paragraph)"

    def test_it_says_where_the_table_came_from_and_links_the_switch(self):
        self.assertTrue(ANALYTICS, "docs/reference.md has the analytics modal paragraph")
        flat = _flat(ANALYTICS)
        self.assertQuoted(SENTENCE_HEAD, flat, self.DOC)
        self.assertQuoted("the live price feed, and how long ago it was fetched, or the built-in defaults and why", flat, self.DOC)
        self.assertQuoted(LINK, flat, self.DOC, "how to stop the fetch is one link away")
        self.assertQuoted("'prices: live feed'", GEAR, "ui/webview/gear.js", "the live reading the sentence describes")

    def test_the_link_resolves_to_the_subsection(self):
        self.assertQuoted(LINK, ANALYTICS, self.DOC)
        self.assertSection()   # `### The price feed` is the heading GitHub anchors as #the-price-feed


class TheNewProse(_Pins):
    def test_no_em_or_en_dash_and_not_the_banned_word(self):
        self.assertSection()
        flat = _flat(ANALYTICS)          # the sentence is hard-wrapped in the doc; the dashes survive the flattening
        i = flat.find(SENTENCE_HEAD)
        self.assertGreaterEqual(i, 0, "the analytics paragraph carries the new sentence")
        for text, name in ((SECTION, "the price feed subsection"), (flat[i:], "the analytics paragraph's new sentence")):
            self.assertNotIn(chr(0x2014), text, name)   # em dash
            self.assertNotIn(chr(0x2013), text, name)   # en dash
            self.assertNotIn("fleet", text.lower(), name)


if __name__ == "__main__":
    unittest.main()
