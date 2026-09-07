#!/usr/bin/env python3
"""The guide's Figures paragraph names the region card's **Re-place** control by its label.

A stale region comment's card offers a button labeled "Re-place" (ui/webview/file-comments.ts,
`btn("Re-place", "fcreplace")`), and the stale tag's title tells the person to Re-place it or
resolve it. The paragraph the Files section gained for figures (Slice 3 of plans/file-review.md)
described the gesture as placing the comment again, so a reader who searched the guide for the
button's label found nothing, and the guide's phrase was one the UI never shows (review finding,
2026-09-06). The paragraph now names the control in bold, as the section names **Comment**,
**Comment on this file** and **Reveal**, and describes it in the button's own words: draw the
rectangle again where it belongs now, and the comment keeps its words.

Every label and phrase the paragraph borrows is cross-checked against the panel source, so a
renamed button or a reworded tooltip fails here and the guide gets updated with it. Synthetic: no
session data, only the repo's own text.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _paragraph(md, lead):
    """The body of the guide paragraph whose bold lead-in is `lead`, up to the next blank line."""
    m = re.search(r"^\*\*" + re.escape(lead) + r"\.\*\*(.*?)(?=\n\n|\Z)", md, re.S | re.M)
    assert m, "paragraph %r not found" % lead
    return m.group(1)


def _flat(text):
    """Collapse the guide's hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


class FiguresNamesReplace(unittest.TestCase):
    """The Figures paragraph names the button by its label and describes it as its tooltip does."""

    def setUp(self):
        guide = _read("docs", "guide.md")
        files = guide[guide.index("### Files"):guide.index("## Automatic nudges")]
        self.figures = _flat(_paragraph(files, "Figures"))
        self.panel = _read("ui", "webview", "file-comments.ts")

    def test_the_panel_still_labels_the_control_re_place(self):
        # The premise, checked against its source: the label this test makes the guide carry.
        self.assertIn('btn("Re-place", "fcreplace")', self.panel)
        self.assertIn("Re-place it where it belongs now, or resolve it", self.panel)

    def test_the_paragraph_names_the_label_in_bold(self):
        self.assertIn("**Re-place**", self.figures)

    def test_the_paragraph_describes_the_control_in_the_tooltip_s_words(self):
        # The button's two titles (stale and current) say where to draw and what is kept; the guide
        # says the same, so the words a person reads on the control and in the guide agree.
        self.assertIn("draw the region again where it belongs now", self.panel)
        self.assertIn("the comment keeps its words", self.panel)
        self.assertIn("press **Re-place** and drag the rectangle again where it belongs now; "
                      "the comment keeps its words", self.figures)

    def test_the_unlabelled_phrase_is_gone(self):
        # The finding: "place it again" matched no control the panel shows.
        self.assertNotIn("place it again", self.figures)

    def test_re_place_stands_beside_resolve_as_the_two_ways_out_of_stale(self):
        # The stale tag's title offers exactly these two; the guide offers the same two, in order.
        self.assertIn("shown as stale until you resolve it, or press **Re-place**", self.figures)


if __name__ == "__main__":
    unittest.main()
