#!/usr/bin/env python3
"""The guide's Comments paragraph says three things Slice 5 of plans/markdown-viewer.md made true, and the panel does them.

The Comment button follows a selection made or changed from the keyboard (item 9: the panel hears the document's
selectionchange itself, since the seam's mouseup and touchend never see a keyboard's selection); two comments over the
same text carry one highlight, and a click where they overlap opens both cards with the clicked one in front (item 6:
the nested mark's rule in both sheets, and the click opening every covering card); and going to a comment whose passage
sits inside a closed fold opens the fold first (item 5, landed with Slice 4 as revealMarks and recorded in the guide
here). Each clause is pinned flattened, so a rewrap survives, and cross-checked against the source that keeps it: the
listener's install and removal lines, the covering-cards call in the click handler, the nested rule byte-equal in
styles.css and feed.css, and the reveal run before a scroll to the mark. The clauses the vocabulary and anchors pins
read (tests/test_guide_files_comment_vocabulary.py, tests/test_guide_files_comments_anchors.py) sit in the same
paragraph and are re-read here unchanged, so an edit that moves one fails in one place and not two. Synthetic: only the
repo's own text.
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


KEYBOARD = ("press the **Comment** button that appears next to the selection (it hides when you scroll and appears "
            "again when you select, and it follows a selection you make or change from the keyboard); type the comment "
            "(Enter adds a line)")
OVERLAP = ("Where two comments cover the same text, the text carries one highlight, and a click where they overlap "
           "opens both cards, the one you clicked in front.")
FOLD = ("Going to a comment whose passage sits inside a closed fold (a `<details>` block, a callout written "
        "`[!note]-`) opens the fold first.")
NESTED_RULE = ".fc-hl .fc-hl { background: none; box-shadow: none; }"


class TheGuideSaysSo(unittest.TestCase):
    def setUp(self):
        section = _section(_read("docs", "guide.md"), "Files")
        self.paragraph = _paragraph(section, "**Comments and tracked changes.**")

    def test_the_comment_button_follows_a_keyboard_selection(self):
        self.assertIn(KEYBOARD, self.paragraph)

    def test_overlapping_comments_carry_one_highlight_and_a_click_opens_both_cards(self):
        self.assertIn(OVERLAP, self.paragraph)

    def test_a_passage_inside_a_closed_fold_is_reached_by_opening_the_fold(self):
        self.assertIn(FOLD, self.paragraph)

    def test_the_clauses_other_pins_read_stand_where_they_were(self):
        # the vocabulary pin's two clauses and the anchors pin's sentence, in this paragraph still
        self.assertIn("type the comment (Enter adds a line)", self.paragraph)
        self.assertIn("the panel says so, keeps your comment, and offers the Raw view with the passage selected",
                      self.paragraph)
        self.assertIn("a comment on text that occurs more than once stays on the occurrence you chose. When the file has "
                      "changed around that occurrence, the comment's own record of where it was, which copy it is and the "
                      "heading above it places it again. When none of those can tell which copy the comment meant, its "
                      "highlight is dashed and the card carries a **passage recurs** tag: the copy shown is a guess, and "
                      "the card says so.", self.paragraph)
        # the overlap clause sits after the guess sentence and before Reveal's, the fold clause after Reveal's
        self.assertLess(self.paragraph.index("the copy shown is a guess"), self.paragraph.index(OVERLAP))
        self.assertLess(self.paragraph.index(OVERLAP), self.paragraph.index("**Reveal** finds the passage"))
        self.assertLess(self.paragraph.index("**Reveal** finds the passage"), self.paragraph.index(FOLD))


class ThePanelDoesIt(unittest.TestCase):
    """Each clause against the source that keeps it, so a renamed listener, a dropped rule or a reveal that no longer
    runs fails here beside the prose."""

    def setUp(self):
        self.panel = _read("ui", "webview", "file-comments.ts")

    def test_the_panel_hears_selectionchange_and_lets_go_of_it_at_dispose(self):
        self.assertIn('document.addEventListener("selectionchange", this.onSelectionChange);', self.panel)
        self.assertIn('document.removeEventListener("selectionchange", this.onSelectionChange);', self.panel)
        self.assertRegex(self.panel, re.compile(r"^\s*onSelectionChange = \(\): void => \{", re.M), "the handler is the panel's own")
        # the seam's own path stays the mouse's and the touch's; its comment says where the keyboard's lives
        seam = _read("ui", "webview", "file-view.ts")
        self.assertIn("file-comments.ts onSelectionChange", seam)

    def test_a_click_on_a_mark_opens_every_covering_card_and_the_clicked_one_is_the_focus(self):
        m = re.search(r"^\s*fcopen: \(x, ev\) => \{(.*)\},?\s*$", self.panel, re.M)
        self.assertIsNotNone(m, "the fcopen handler")
        handler = m.group(1)
        self.assertIn("this.openCovering(x);", handler)
        self.assertIn("this.showCard(this.cardKey(x.dataset.id!));", handler)
        self.assertLess(handler.index("this.openCovering(x);"), handler.index("this.showCard("),
                        "the covering cards open first; the clicked one is then shown as the focus")
        self.assertRegex(self.panel, re.compile(r"^\s*private openCovering\(x: HTMLElement\): void \{", re.M), "the helper exists")

    def test_the_nested_mark_wears_no_second_wash_in_either_sheet(self):
        for sheet in ("styles.css", "feed.css"):
            css = _read("ui", "webview", sheet)
            self.assertEqual(css.count("\n" + NESTED_RULE + "\n"), 1, "%s: the nested rule once, on a line of its own" % sheet)

    def test_a_fold_around_the_mark_opens_before_any_scroll_to_it(self):
        self.assertRegex(self.panel, re.compile(r"^\s*private revealMarks\(key: string\): boolean \{", re.M), "the reveal helper")
        self.assertIn('import { revealFragmentTarget } from "./md-sanitize";', self.panel)
        goto = self.panel[self.panel.index("this.revealMarks(key);"):]
        self.assertIn("a fold around the mark opens first", goto[:400])


if __name__ == "__main__":
    unittest.main()
