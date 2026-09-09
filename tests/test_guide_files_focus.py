#!/usr/bin/env python3
"""The guide's Files section says the card you click sits level with its passage and that long cards fold, and the panel does both.

The focus follow-on (2026-09-08): a tall change card above a comment used to push the comment's card a viewport below its
highlight, and the click on the highlight scrolled the highlight to the body's top edge with the card still out of sight.
The panel now anchors the layout on the card the person last acted on (level with its mark, the cards above moved up by the
least that clears it) and folds a long card part to eight lines with Show more at the card's foot. The guide's Files
paragraph gained one sentence saying both; each clause is cross-checked against the panel, the layout rule and the sheets
that do it, so a renamed class, a dropped rule or a reworded sentence fails here. Synthetic: only the repo's own text.
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


BEFORE = ("when the column is narrow the panel drops below the file and lists the cards instead.")
SENTENCE = ("The card you click sits level with its passage whatever stands above it, and a long card folds to a few "
            "lines with **Show more** at its foot.")


class TheFilesSentence(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))

    def test_the_sentence_follows_the_layout_sentence(self):
        self.assertIn(BEFORE + " " + SENTENCE, self.section)

    def test_no_panel_vocabulary(self):
        # the guide speaks in the reader's terms: no track, pass, focus key or clip
        self.assertNotIn("focusCard", self.section)
        self.assertNotIn("fc-clip", self.section)


class TheSentenceMatchesThePanel(unittest.TestCase):
    """Each clause names something the panel source, the layout rule and the sheets do."""

    def setUp(self):
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.layout = _read("ui", "webview", "card-layout.ts")
        self.styles = _read("ui", "webview", "styles.css")
        self.feed = _read("ui", "webview", "feed.css")

    def test_the_card_you_click_sits_level_whatever_stands_above_it(self):
        # the focus: set by a mark's click before the render whose pass lays the card, and given to the pure rule
        self.assertIn("this.focusCard = key;                               // the focus: the render's pass lays the card level with its mark", self.panel)
        self.assertIn("const out = layoutCards(items, CARD_GAP, this.focusCard);", self.panel)
        # the rule: the focused card at its mark, the cards above moved up only as far as the card under each needs
        self.assertIn("const focusTop = Math.max(fit.desired as number, gap);", self.layout)
        self.assertIn("const top = Math.min(tops.get(it) as number, ceiling - it.height);", self.layout)
        self.assertIn("put(fit, focusTop);", self.layout)

    def test_a_long_card_folds_to_a_few_lines_with_show_more(self):
        self.assertIn('btn(open ? "Show less" : "Show more", "fcclip")', self.panel)
        self.assertIn("if (over) { part.dataset.clipped = \"1\"; cut = true; } else delete part.dataset.clipped;", self.panel)
        for css in (self.styles, self.feed):
            self.assertIn(".fc-margin .fc-card:not(.fc-more) .fc-clip { max-height: 8lh; overflow: hidden; }", css)

    def test_the_sheets_agree(self):
        a = self.styles.index("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)")
        b = self.styles.index("/* ── end file comments panel ── */")
        block = self.styles[a:b]
        self.assertIn(block, self.feed)
        self.assertIn(".fc-clip-row[hidden] { display: none; }", block)


if __name__ == "__main__":
    unittest.main()
