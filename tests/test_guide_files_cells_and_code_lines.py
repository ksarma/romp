#!/usr/bin/env python3
"""The guide's Comments paragraph says three things Slice 8 of plans/markdown-viewer.md made true, and the viewer does them.

A table cell and a line of a code block can be commented from the Rendered view like any passage (items 1 and 2: the
anchor map positions a table's cells and a code block's lines as it positions prose, walkTable and walkCode in the
block walk, where before the slice both were holes whose selection refused); what cannot be mapped from the Rendered
view is a selection across two cells of a table or one touching a formula (item 3: the one-cell rule's sentence, with
the Raw view offered on the exact span; the formula's sentence from Slice 5), the parenthetical no longer naming a table
or a code block; and a comment on a formula that stands on its own line highlights the whole formula (item 5: the block
class on the `.katex-display` box, painted by the anchor map for the two comment classes and dressed by a rule that is
byte-equal in both sheets). Each clause is pinned flattened, so a rewrap survives, and cross-checked against the source
that keeps it. The clauses the vocabulary, anchors and Slice 5 pins read (tests/test_guide_files_comment_vocabulary.py,
tests/test_guide_files_comments_anchors.py, tests/test_guide_files_keyboard_overlap_fold.py) sit in the same paragraph
and are re-read here unchanged, the refusal's tail clause byte for byte among them, so an edit that moves one fails in
one place and not two. Synthetic: only the repo's own text.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _section(md, heading):
    """The body of one `### heading` up to the next heading of any level."""
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _flat(text):
    """Collapse the guide's hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(section, lead):
    """The paragraph of the section that opens with `lead`, flattened."""
    start = section.index(lead)
    end = section.find("\n\n", start)
    return _flat(section[start:] if end < 0 else section[start:end])


def _header_comment(source):
    """A module's leading `//` comment, flattened, so a sentence pin survives a rewrap of the header."""
    lines = []
    for line in source.splitlines():
        if not line.startswith("//"):
            break
        lines.append(line[2:])
    return _flat(" ".join(lines))


def _rule(css, head):
    """The one rule under `head` (a line of its own) read through its first `}`, as fileview-parity reads a head."""
    starts = [m.start() for m in re.finditer(r"^" + re.escape(head), css, re.M)]
    assert len(starts) == 1, "%d copies of %r" % (len(starts), head)
    return css[starts[0]:css.index("}", starts[0]) + 1]


CELLS_AND_LINES = "A table cell and a line of a code block can be commented from the Rendered view like any passage."
CANNOT_MAP = ("When a passage cannot be mapped from the Rendered view (a selection across two cells of a table, a formula), "
              "the panel says so, keeps your comment, and offers the Raw view with the passage selected.")
TAIL = "the panel says so, keeps your comment, and offers the Raw view with the passage selected"
FORMULA = "A comment on a formula that stands on its own line (a `$$` block) highlights the whole formula."
ONE_CELL = "This selection spans more than one cell of a table; select within one cell, or comment on it from the Raw view."
FORMULA_TOUCHED = "This selection touches a formula; comment on it from the Raw view."
BLOCK_HEAD = ".fileview-md .katex-display.fc-hl-block {"


class TheGuideSaysSo(unittest.TestCase):
    def setUp(self):
        section = _section(_read("docs", "guide.md"), "Files")
        self.paragraph = _paragraph(section, "**Comments and tracked changes.**")

    def test_a_cell_and_a_code_line_comment_from_the_rendered_view(self):
        self.assertIn(CELLS_AND_LINES, self.paragraph)

    def test_what_cannot_be_mapped_is_a_selection_across_cells_or_a_formula(self):
        self.assertIn(CANNOT_MAP, self.paragraph)
        self.assertNotIn("(a table, a code block)", self.paragraph, "the parenthetical before Slice 8")

    def test_a_comment_on_a_display_formula_highlights_the_whole_formula(self):
        self.assertIn(FORMULA, self.paragraph)

    def test_the_clauses_other_pins_read_stand_where_they_were(self):
        # the vocabulary pin's two clauses, the refusal's tail clause byte for byte among them
        self.assertIn("type the comment (Enter adds a line)", self.paragraph)
        self.assertIn(TAIL, self.paragraph)
        self.assertEqual(self.paragraph.count(TAIL), 1)
        # the anchors pin's sentence and the Slice 5 pins' clauses, in this paragraph still
        self.assertIn("a comment on text that occurs more than once stays on the occurrence you chose", self.paragraph)
        self.assertIn("it follows a selection you make or change from the keyboard", self.paragraph)
        self.assertIn("a click where they overlap opens both cards", self.paragraph)
        self.assertIn("opens the fold first", self.paragraph)
        # the order: the whole-file button, what maps, what does not, the formula's highlight, then where comments live
        for clause in (CELLS_AND_LINES, CANNOT_MAP, FORMULA):
            self.assertIn(clause, self.paragraph)
        whole_file = self.paragraph.index("**Comment on this file** leaves a comment on the file as a whole")
        self.assertLess(whole_file, self.paragraph.index(CELLS_AND_LINES))
        self.assertLess(self.paragraph.index(CELLS_AND_LINES), self.paragraph.index(CANNOT_MAP))
        self.assertLess(self.paragraph.index(CANNOT_MAP), self.paragraph.index(FORMULA))
        self.assertLess(self.paragraph.index(FORMULA), self.paragraph.index("Comments are stored beside the file"))


class TheViewerDoesIt(unittest.TestCase):
    """Each clause against the source that keeps it, so a walk that stops positioning cells or lines, a reworded
    refusal, a dropped block rule or a class the two modules no longer agree on fails here beside the prose."""

    def setUp(self):
        self.am = _read("ui", "webview", "anchor-map.ts")

    def test_the_anchor_map_positions_a_tables_cells_and_a_code_blocks_lines(self):
        head = _header_comment(self.am)
        self.assertIn("A table's cells and a code block's lines are positioned as prose is", head)
        self.assertNotIn("Code, tables, HTML, entity-bearing prose, and escaped link labels refuse by design", head,
                         "the boundary sentence before Slice 8")
        self.assertRegex(self.am, re.compile(r"^function walkTable\(tt: Tokens\.Table, tv: View, em: Emitter\): void \{", re.M))
        self.assertRegex(self.am, re.compile(r"^function walkCode\(tt: Tokens\.Code, cv: View, em: Emitter\): void \{", re.M))
        # the block walk hands each token to its walk over the view its raw tiles
        self.assertIn("walkTable(t as Tokens.Table, view.sub(p, p + raw.length), em);", self.am)
        self.assertIn("walkCode(t as Tokens.Code, view.sub(p, p + raw.length), em);", self.am)

    def test_a_selection_across_two_cells_is_refused_with_the_raw_view_offered_on_the_span(self):
        m = re.search(r'refuse\(' + re.escape('"' + ONE_CELL + '"') + r",\s*\{(.*?)\}\s*\);", self.am, re.S)
        self.assertIsNotNone(m, "the one-cell rule's sentence, on a refuse with an offer")
        offer = m.group(1)
        self.assertIn("rawHasQuote: true", offer, "the Raw view is offered on the span, so Save works from Raw")
        self.assertIn("rawRange: { start: s, end: e }", offer)
        self.assertIn("blockStartOffset: s", offer, "the panel's search for the span begins at the span, not at the table")

    def test_a_formula_touched_from_rendered_is_refused_in_the_same_shape(self):
        self.assertIn('const FORMULA_TOUCHED = "%s";' % FORMULA_TOUCHED, self.am)
        # both sentences a person reads keep the guide's shape: what the selection does, then the Raw view
        for sentence in (ONE_CELL, FORMULA_TOUCHED):
            self.assertRegex(sentence, r"^This selection (touches|spans) .*; .*comment on it from the Raw view\.$")

    def test_a_display_formula_takes_the_block_class_the_panel_strips_and_both_sheets_dress(self):
        m = re.search(r'^const BLOCK_PAINT_FOR = new Set\(\[(.*)\]\);$', self.am, re.M)
        self.assertIsNotNone(m, "the classes the block paint serves")
        served = [x.strip().strip('"') for x in m.group(1).split(",")]
        panel = _read("ui", "webview", "file-comments.ts")
        p = re.search(r'^const BLOCK_PAINT_CLASSES = \[(.*)\];$', panel, re.M)
        self.assertIsNotNone(p, "the classes the panel strips")
        stripped = [x.strip().strip('"') for x in p.group(1).split(",")]
        self.assertEqual([c + "-block" for c in served], stripped, "the paint's classes and the panel's are one set")
        self.assertIn("fc-hl-block", stripped)
        self.assertIn("stampBlock", self.am, "the paint stamps the box instead of wrapping it")
        rules = {sheet: _rule(_read("ui", "webview", sheet), BLOCK_HEAD) for sheet in ("styles.css", "feed.css")}
        self.assertEqual(rules["styles.css"], rules["feed.css"], "the block rule byte-equal in both sheets")
        self.assertIn("background:", rules["styles.css"])
        self.assertNotIn("padding", rules["styles.css"], "the box keeps its size: no padding on the block rule")
        self.assertNotRegex(rules["styles.css"], r"#[0-9a-fA-F]{3,8}\b", "tokens, not hex")


if __name__ == "__main__":
    unittest.main()
