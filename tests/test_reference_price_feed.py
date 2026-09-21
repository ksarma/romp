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

Text only: the behaviour is pinned in tests/test_price_feed_off.py (the kernel) and
ui/webview/analytics-price-source.test.ts (the view). The doc and the sources are read as files; nothing loads
romp code, so no state root is minted. Every case asserts the doc's text FIRST, so a run over a tree without
the subsection fails at that assertion and never at a slice or a missing symbol.
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
        self.assertQuoted("v.get(kk, base.get(kk, 0))", prices, where,
                          "a rate the row omits reads the base row's, which is the table's for an id it names and empty otherwise")


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
