#!/usr/bin/env python3
"""The price-source vocabulary is one set, pinned from one place (review round 1, 2026-09-20).

kernel/kernel.py _price_feed_status emits the state of the cost view's price table as a `source` ("feed" or
"defaults") and, for the defaults, a `reason` ("off", "failed", "empty", "inflight", "unfetched"); ui/webview/gear.js
raPriceNote words those literals on the Token usage modal's line. Each side pins its own words (tests/
test_price_feed_off.py the kernel's tuples, ui/webview/analytics-price-source.test.ts the view's text), and the view
words an unknown reason as the source alone and an unknown source as no line at all (absent beats a false statement).
So a rename on one side that carries its own pin, the shape an upstream fold takes, left every test green while the
line lost its why or vanished. This module reads both files and holds the two vocabularies to one set: every source
and every reason the kernel can emit is a literal the view tests for, and the view tests for no literal the kernel
cannot emit; every field the view reads from the block is a key the kernel's status dict carries; and every key the
status dict carries is a field the view reads, or one named in VIEW_EXEMPT with the reason the view leaves it unworded
(the review of PR 878, round 2: the key check ran one way, view minus kernel, so `overrideFault` rode the block unread and
a model-prices.json discarded whole rendered the clean line). This module holds no age wording: the fetch age's words
are the shell's one helper's, pinned by execution in ui/webview/analytics-price-source-states.test.ts, and the kernel's
stderr age by tests/test_price_feed_off.py.

Text only: the sources are read as files, nothing loads romp code, so no state root is minted. The kernel side is
read as code (an ast walk over the status function's assignments and its return), never as text: the chain tests
`_price_feed["inflight"]`, a dict key spelled like the reason it sets, and a text read counted it as a reason. The
extraction is proved live on a copy of each side with one word renamed (an extractor that read the docstring, the
dict key or nothing would report the same set either way).
"""
import ast
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _pydef(src, name):
    """The text of top-level `def name(...)` up to the next top-level def or class; "" when absent."""
    m = re.search(r"^def " + re.escape(name) + r"\(.*?(?=^(?:def|class) |\Z)", src, re.S | re.M)
    return m.group(0) if m else ""


def _jsfunc(src, name):
    """The text of top-level `function name(...) {` up to its closing brace at column 0; "" when absent."""
    m = re.search(r"^function " + re.escape(name) + r"\(.*?^\}\n", src, re.S | re.M)
    return m.group(0) if m else ""


KERNEL = _read("kernel", "kernel.py")
GEAR = _read("ui", "webview", "gear.js")
STATUS = _pydef(KERNEL, "_price_feed_status")
NOTE = _jsfunc(GEAR, "raPriceNote")


def _strings(expr):
    """Every string literal an expression can evaluate TO: the branches of a conditional chain, never its tests
    (`"inflight" if _price_feed["inflight"] else ...` yields inflight once, from the branch, not from the key)."""
    if isinstance(expr, ast.IfExp):
        return _strings(expr.body) | _strings(expr.orelse)
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return {expr.value}
    return set()


def _assigned(status, name):
    """The string literals assigned to `name` anywhere in the def, through `name = ...` and `a, name = x, y`."""
    out = set()
    try:
        tree = ast.parse(status)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                out |= _strings(node.value)
            elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                for t, v in zip(target.elts, node.value.elts):
                    if isinstance(t, ast.Name) and t.id == name:
                        out |= _strings(v)
    return out


def kernel_sources(status):
    return _assigned(status, "source")


def kernel_reasons(status):
    return _assigned(status, "reason")


def kernel_keys(status):
    """The keys of the dict literal the def returns."""
    try:
        tree = ast.parse(status)
    except SyntaxError:
        return set()
    return {k.value for node in ast.walk(tree) if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
            for k in node.value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}


def view_sources(note):
    return set(re.findall(r"pf\.source (?:===|!==) '([a-z]+)'", note))


def view_reasons(note):
    return set(re.findall(r"pf\.reason === '([a-z]+)'", note))


def view_keys(note):
    return set(re.findall(r"\bpf\.(\w+)", note))


# The keys of the block the view deliberately leaves unworded, each with its reason. Every other key _price_feed_status
# returns has to be read in raPriceNote as pf.<key>, so a key the kernel adds is worded, or named here with why not, at
# authoring time; an entry the view has since started reading, or the kernel has since dropped, is stale and fails too.
VIEW_EXEMPT = {
    "attemptedAt": "an epoch on the kernel's clock; the view words the attempt through `reason` (inflight), never a raw epoch",
    "fetchedAt": "an epoch; superseded on the view side by `ageS`, the kernel's now minus fetchedAt on one clock",
}


class TheTwoSidesAreFound(unittest.TestCase):
    """The anchors: each extractor finds the code it reads, so an empty set on either side is a moved anchor to
    re-pin here, never a pass."""

    def test_the_kernel_status_and_its_chain_are_read(self):
        self.assertTrue(STATUS, "kernel/kernel.py defines _price_feed_status at the top level")
        self.assertTrue(kernel_sources(STATUS), "the status assigns `source` from string literals")
        self.assertTrue(kernel_reasons(STATUS), "the status assigns `reason` from a conditional chain of literals")
        self.assertIn("source", kernel_keys(STATUS), "the status returns a dict literal with a `source` key")
        self.assertIn("(ROMP_PRICE_FEED=off)", STATUS, "the docstring names the switch in prose, and the walk does not read it:")
        self.assertNotIn("ROMP_PRICE_FEED=off", kernel_reasons(STATUS) | kernel_sources(STATUS))

    def test_the_view_formatter_is_read(self):
        self.assertTrue(NOTE, "ui/webview/gear.js defines raPriceNote at the top level, exported beside initGear")
        self.assertTrue(view_sources(NOTE), "the formatter tests `pf.source` against string literals")
        self.assertTrue(view_reasons(NOTE), "the formatter tests `pf.reason` against string literals")


class TheVocabularyIsOneSet(unittest.TestCase):
    def test_the_sources_the_kernel_emits_are_the_sources_the_view_words(self):
        self.assertEqual(view_sources(NOTE), kernel_sources(STATUS),
                         "a source the kernel emits and the view does not test for renders NO line; one the view tests for and "
                         "the kernel never emits is dead wording. Rename on both sides, or word the new source in raPriceNote")

    def test_the_reasons_the_kernel_emits_are_the_reasons_the_view_words(self):
        self.assertEqual(view_reasons(NOTE), kernel_reasons(STATUS),
                         "a reason the kernel emits and the view does not test for renders the source with no why; one the view "
                         "tests for and the kernel never emits is dead wording. Rename on both sides, or word the new reason")

    def test_every_field_the_view_reads_is_a_key_the_kernel_emits(self):
        missing = view_keys(NOTE) - kernel_keys(STATUS)
        self.assertEqual(missing, set(),
                         "raPriceNote reads %s from the block and _price_feed_status emits no such key: the clause keyed on it can "
                         "never render. Add the key to the status dict, or drop the read" % sorted(missing))

    def test_every_key_the_kernel_emits_is_read_by_the_view_or_exempt_by_name(self):
        """The other direction: a key the kernel emits that the view words nowhere, which the check above cannot see by
        construction (the review of PR 878, round 2: `overrideFault` rode the block unread, and a model-prices.json the
        kernel discarded whole rendered the line a clean file renders). The exemptions are declared with their reasons,
        so a new key is worded in raPriceNote or named in VIEW_EXEMPT at authoring time, never left silent."""
        unread = kernel_keys(STATUS) - view_keys(NOTE)
        unworded = sorted(unread - set(VIEW_EXEMPT))
        self.assertEqual(unworded, [],
                         "_price_feed_status emits %s and raPriceNote reads no such field: the block carries a fact the modal never "
                         "words. Word it in raPriceNote (a pf.<key> read), or add it to VIEW_EXEMPT with the reason the view leaves "
                         "it out" % unworded)
        stale = sorted(set(VIEW_EXEMPT) - unread)
        self.assertEqual(stale, [],
                         "VIEW_EXEMPT names %s, which the view now reads or the kernel no longer emits: drop the stale exemption" % stale)
        for key, reason in VIEW_EXEMPT.items():
            with self.subTest(key=key):
                self.assertTrue(reason.strip(), "an exemption carries its reason")


class TheExtractionIsLive(unittest.TestCase):
    """A pin that read the docstring, or nothing, would report the same set with the code renamed. Rename one word in a
    copy of each side and the pin reads the rename."""

    def test_a_renamed_kernel_reason_is_read(self):
        renamed = STATUS.replace('"inflight" if', '"pending" if')
        self.assertNotEqual(renamed, STATUS, "the chain spells inflight as `\"inflight\" if ...`; re-anchor if it moved")
        self.assertIn('_price_feed["inflight"]', renamed, "the dict key the chain tests still spells inflight, and is not a reason")
        self.assertEqual(kernel_reasons(renamed) ^ kernel_reasons(STATUS), {"inflight", "pending"},
                         "the rename is read from the branch, and the key the chain tests is not counted as the old word")
        self.assertNotEqual(kernel_reasons(renamed), view_reasons(NOTE), "the one-set pin goes red on the rename")

    def test_a_renamed_view_reason_is_read(self):
        renamed = NOTE.replace("pf.reason === 'inflight'", "pf.reason === 'pending'")
        self.assertNotEqual(renamed, NOTE, "the formatter tests `pf.reason === 'inflight'`; re-anchor if it moved")
        self.assertEqual(view_reasons(renamed) ^ view_reasons(NOTE), {"inflight", "pending"})
        self.assertNotEqual(view_reasons(renamed), kernel_reasons(STATUS))

    def test_a_renamed_kernel_source_is_read(self):
        renamed = STATUS.replace('source, reason = "feed", None', 'source, reason = "live", None')
        self.assertNotEqual(renamed, STATUS, "the status assigns `source, reason = \"feed\", None`; re-anchor if it moved")
        self.assertEqual(kernel_sources(renamed) ^ kernel_sources(STATUS), {"feed", "live"})

    def test_a_removed_kernel_key_is_read(self):
        renamed = STATUS.replace('"rows":', '"matched":')
        self.assertNotEqual(renamed, STATUS, "the status returns a `\"rows\":` key; re-anchor if it moved")
        self.assertIn("rows", view_keys(NOTE) - kernel_keys(renamed), "the view reads rows, so the renamed key is a missing one")

    def test_a_kernel_key_the_view_stops_reading_is_read(self):
        self.assertTrue("pf.overrideFault" in NOTE, "the formatter reads `pf.overrideFault`; re-anchor if it moved")
        renamed = NOTE.replace("pf.overrideFault", "pf.overrideKind")
        self.assertEqual(sorted((kernel_keys(STATUS) - view_keys(renamed)) - set(VIEW_EXEMPT)), ["overrideFault"],
                         "a key the view no longer reads is the two-way pin's unworded key, and the exempt keys stay out of it")


if __name__ == "__main__":
    unittest.main()
