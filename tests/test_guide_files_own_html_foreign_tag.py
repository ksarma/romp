#!/usr/bin/env python3
"""The guide's paragraph on a file's own HTML qualifies decision 52's rule for a tag left open inside an inline `svg` or
`math`, and each clause of the qualification is true of the code.

Decision 52 of plans/file-review.md renders an inline start tag with no end tag in its block as the characters typed
(md-literal-tags.ts, matching by element name), and the guide says so, adding that the characters can be commented on
like any passage. Inside an inline `<svg>` or `<math>` the rule applies by name too, so a child left open there
(`<svg><title>icon</svg>`) is text as well; but that text is the drawing's, which the browser draws without it, or goes
with a `<math>` the sanitizer drops whole (its profile is html and svg, no MathML), so the Rendered view shows nothing
where the tag was typed and a comment on it goes through the Raw view. The decision records the exception (its
characters "drawn nowhere, or go with a dropped `<math>`"); the guide stated the rule without it until the slice's
review, whose finding this module closes: the qualifying sentences stand right after the rule they qualify, and each
clause is cross-checked against what keeps it true (the decision's record, the module's by-name match with no exception
for foreign content, the sanitizer's profile, the html-rules and DOM tests' reading of the example shape, the tooltip
sentence the last clause refers back to). Pinned flattened, so a rewrap survives. Synthetic: only the repo's own text.
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
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(md, lead):
    """The paragraph of `md` that opens with `lead`, flattened."""
    start = md.index(lead)
    end = md.find("\n\n", start)
    return _flat(md[start:] if end < 0 else md[start:end])


def _decision(plan, number):
    """The body of one numbered decision of plans/file-review.md, from its heading to the next decision's, flattened."""
    m = re.search(r"^%d\. \*\*(.*?)(?=^%d\. \*\*)" % (number, number + 1), plan, re.S | re.M)
    assert m, "decision %d not found" % number
    return _flat(m.group(0))


def _code_only(ts):
    """A TypeScript module with its `//` lines and `/* */` blocks removed, so a pin reads the code and not its comments."""
    ts = re.sub(r"/\*.*?\*/", "", ts, flags=re.S)
    return "\n".join(line for line in ts.splitlines() if not line.lstrip().startswith("//"))


# The guide's statement of the rule and of where it stops (the HTML-block passage the second round added, held clause by
# clause by tools/guide-own-html-block-tag.test.mjs and, through the viewer's own lexer, by
# ui/webview/guide-own-html-block-tag.test.ts), then the sentence on the tags that take the rest of the file when they stay
# HTML (the whole review's first round): the qualification follows that sentence directly.
RULE = ("A tag opened in a line of prose and not closed in the same paragraph, heading, list item or table cell (a "
        "placeholder typed mid-sentence as `<table>`, say) is shown as the characters typed, not read as HTML, and can be "
        "commented on like any passage; a tag closed in the same block, a tag that never takes an end tag such as `<br>` or "
        "`<img>`, and a tag written with a slash before its `>` (`<x/>`) are HTML as before. A tag the viewer reads as an "
        "HTML block rather than as prose is HTML as before too: a "
        "tag first on its line, after a list marker or a `>` included, whose name is on CommonMark's HTML-block list "
        "(`<table>`, `<div>`, `<p>` and `<pre>` are on it; `<span>`, `<b>` and an invented name are not), or a tag alone on a "
        "line where a paragraph would begin. The same placeholder typed first on its line is therefore read as HTML: the "
        "browser shows no `<table>`, and a comment on the passage goes through the Raw view. A chat message is not read this "
        "way.")
LOSS = ("A `<title>`, `<script>`, `<style>` or `<iframe>` that stays HTML takes everything after it out of the Rendered view, "
        "up to an end tag of its name, or the end of the file when there is none: a browser reads `<title/>` as `<title>`, so "
        "the tag written with the slash mid-sentence does this, and so does the tag first on its line; a `<textarea>` in "
        "either place shows that stretch as unformatted characters instead: after the tag first on its line the file's own "
        "text, and after the tag written with the slash mid-sentence the HTML the viewer built from the rest of its paragraph "
        "and the blocks after it, tags such as `</p>` and `<h2>` among the characters.")
QUALIFICATION = ("Inside an inline `svg` or `math`, a child tag left open (`<svg><title>icon</svg>`, say) disappears from the "
                 "Rendered view: the same rule makes it text, but the text lands inside the drawing, which the browser draws "
                 "without it, or inside the `math`, which the viewer drops whole, so a comment on it goes through the Raw "
                 "view, which shows it.")
CLOSED = "A child closed with its own end tag, the drawing's `<title>` included, is HTML as before."
TOOLTIP = "the `<title>` of an inline `svg`, the drawing's tooltip, stays"
SHAPE = "Intro <svg><title>icon</svg> beside end\\n"


class TheGuideSaysSo(unittest.TestCase):
    def setUp(self):
        self.paragraph = _paragraph(_read("docs", "guide.md"), "**A file's own HTML.**")

    def test_the_qualification_stands_right_after_the_rule_it_qualifies(self):
        self.assertIn(RULE + " " + LOSS + " " + QUALIFICATION + " " + CLOSED, self.paragraph)

    def test_the_rule_is_stated_once(self):
        self.assertEqual(self.paragraph.count("is shown as the characters typed"), 1)
        self.assertEqual(self.paragraph.count(LOSS), 1)
        self.assertEqual(self.paragraph.count(QUALIFICATION), 1)

    def test_the_closed_clause_refers_back_to_the_tooltip_sentence(self):
        # the last clause says a closed `<title>` keeps the tooltip the earlier sentence promised; that sentence stands before it
        self.assertIn(TOOLTIP, self.paragraph)
        self.assertLess(self.paragraph.index(TOOLTIP), self.paragraph.index(QUALIFICATION))

    def test_no_em_dash_in_the_paragraph(self):
        self.assertNotIn(chr(0x2014), self.paragraph)   # an em dash, spelled by code point so this file carries none


class TheCodeDoesIt(unittest.TestCase):
    """Each clause against what keeps it true, so a rule that starts sparing a drawing's children, a sanitizer that starts
    keeping MathML, or a DOM reading that changes fails here beside the prose."""

    def test_the_decision_records_the_exception_the_guide_qualifies(self):
        d = _decision(_read("plans", "file-review.md"), 52)
        self.assertIn("inside an inline `<svg>` or `<math>` the rule applies by name", d)
        self.assertIn("`<svg><title>icon</svg>`", d)
        self.assertIn("drawn nowhere, or go with a dropped `<math>`", d)

    def test_the_rule_matches_by_name_with_no_exception_for_a_drawing_or_a_formula(self):
        # "the same rule makes it text": the block's inline tags are matched by element name alone (the ASCII-folded name
        # is the key an end tag closes by), with no branch for svg or math
        code = _code_only(_read("ui", "webview", "md-literal-tags.ts"))
        self.assertIn("const name = m[2].toUpperCase();", code)
        self.assertNotRegex(code, re.compile(r"svg|math", re.I), "a foreign-content branch in the rule")
        # a drawing's or a formula's children are non-void, so an unclosed one is converted
        void = re.search(r"VOID_ELEMENTS: ReadonlySet<string> = new Set\(\[(.*?)\]\)", code).group(1)
        for name in ("TITLE", "DESC", "FOREIGNOBJECT", "ANNOTATION-XML", "MTEXT", "SVG", "MATH"):
            self.assertNotIn('"%s"' % name, void)

    def test_the_loss_sentence_names_tags_the_rule_leaves_html_in_both_placements(self):
        # "that stays HTML ... written with the slash ... or first on its line": the rule converts no self-closing tag (the
        # flag read by isSelfClosingTag) and reads no block html token (its walk names the blocks whose inline run it reads and
        # no html case), and none of the five names is void, so the bare spelling mid-sentence is converted and these are not.
        # What the browser then does with them is held by ui/webview/guide-own-html-block-tag.test.ts at the lexer and by the
        # slice's browser legs; this pin is the code's two exclusions.
        code = _code_only(_read("ui", "webview", "md-literal-tags.ts"))
        self.assertIn("!isSelfClosingTag(t.raw)", code)
        walk = code[code.index("export function literalizeUnclosedTags("):code.index("function literalizeRun(")]
        self.assertNotIn('"html"', walk)
        void = re.search(r"VOID_ELEMENTS: ReadonlySet<string> = new Set\(\[(.*?)\]\)", code).group(1)
        for name in ("TITLE", "SCRIPT", "STYLE", "IFRAME", "TEXTAREA"):
            self.assertNotIn('"%s"' % name, void)

    def test_the_viewer_drops_a_math_whole(self):
        # "which the viewer drops whole": the one profile is html and svg; with no MathML profile DOMPurify removes a
        # `<math>` with its content (the MathML elements are in its default FORBID_CONTENTS)
        sanitize = _read("ui", "webview", "md-sanitize.ts")
        self.assertIn("  USE_PROFILES: { html: true, svg: true },", sanitize)
        self.assertNotIn("mathMl", sanitize)
        self.assertNotIn("ADD_TAGS", sanitize)

    def test_the_example_shape_reads_as_text_of_the_drawing_on_both_sides(self):
        # the reader's model and the real DOM agree: `<title>` is text inside the svg, the svg closed by its end tag
        rules = _read("ui", "webview", "anchor-map-html-rules.test.ts")
        self.assertIn('shown("%s"), "Intro <title>icon beside end"' % SHAPE, rules)
        dom = _read("ui", "webview", "anchor-map-html-text-browser.test.ts")
        self.assertIn('src: "%s"' % SHAPE, dom)

    def test_a_closed_svg_title_stays(self):
        # "A child closed with its own end tag, the drawing's `<title>` included, is HTML as before": the DOM leg keeps the
        # shape, and the sanitizer's namespace test keeps an svg's own title
        dom = _read("ui", "webview", "anchor-map-html-text-browser.test.ts")
        self.assertIn('name: "an svg title closed by its own end tag"', dom)
        sanitize = _read("ui", "webview", "md-sanitize.ts")
        self.assertIn("an inline svg's own `<title>` stays", sanitize)


if __name__ == "__main__":
    unittest.main()
