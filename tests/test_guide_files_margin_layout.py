#!/usr/bin/env python3
"""The guide's Files section says how the Comments panel lays its cards out, and the panel does that.

The margin-layout follow-on (2026-09-07) placed each card level with the passage it is about, scrolling with
the text, when the panel stands beside the file, and kept the list layout when the column is narrow and the
panel drops below the file. The guide's sentence used to say only where the panel opens; it now says both
layouts. Each clause is cross-checked against the panel source that does it (the margin class the pass
toggles, the fold read off the row's computed flex-direction, the scroll lock), and against the sheets' rules
for the layout, so a renamed class or a dropped rule fails here too. Synthetic: only the repo's own text.
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


SENTENCE = ("The viewer's **Comments** action opens a panel beside the file, where each card sits level with the "
            "passage it is about and scrolls with the text; when the column is narrow the panel drops below the file "
            "and lists the cards instead.")


class TheFilesSentenceSaysBothLayouts(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))

    def test_the_sentence(self):
        self.assertIn(SENTENCE, self.section)

    def test_the_old_sentence_is_gone(self):
        self.assertNotIn("opens a panel beside the file (below it when the column is narrow)", self.section)


class TheSentenceMatchesThePanel(unittest.TestCase):
    """Each clause names something the panel source and the sheets do."""

    def setUp(self):
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.layout = _read("ui", "webview", "card-layout.ts")
        self.styles = _read("ui", "webview", "styles.css")
        self.feed = _read("ui", "webview", "feed.css")

    def test_level_with_the_passage(self):
        # the desired top is the mark's top in the body's content, less the header the track begins under
        self.assertIn("desired: mark === null ? null : mark - bodyRect.top + scroll - offset", self.panel)
        self.assertRegex(self.layout, r"put\(it, Math\.max\(it\.desired as number, floor\)\)")
        for css in (self.styles, self.feed):
            self.assertIn(".fc-margin .fc-cards > * { position: absolute; left: 12px; right: 12px; box-sizing: border-box; }", css)

    def test_scrolls_with_the_text(self):
        self.assertRegex(self.panel, r'body\.addEventListener\("scroll", \(\) => this\.mirrorScroll\("body"\)\);')
        self.assertRegex(self.panel, r'track\.addEventListener\("scroll", \(\) => this\.mirrorScroll\("track"\)\);')
        for css in (self.styles, self.feed):
            self.assertIn("scrollbar-width: none;", css.split(".fc-margin > .fc-sec-cards {")[1].split("}")[0])

    def test_the_narrow_column_lists_the_cards(self):
        # the fold is the sheet's container query; the panel reads its verdict off the row and drops the margin class
        self.assertRegex(self.panel, r'getComputedStyle\(row\)\.flexDirection !== "column"')
        self.assertRegex(self.panel, r'root\.classList\.toggle\("fc-margin", margin\);')
        for css in (self.styles, self.feed):
            self.assertRegex(css, r"@container \(max-width: 680px\) \{\n\s*\.fileview-main \{ flex-direction: column; \}")
            # the card is the container that query resolves against (a query never styles its own container)
            card = css[css.index("\n.fileview {"):]
            self.assertIn("container-type: inline-size;", card[:card.index("}")])

    def test_the_sheets_agree(self):
        a = self.styles.index("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)")
        b = self.styles.index("/* ── end file comments panel ── */")
        block = self.styles[a:b]
        self.assertIn(block, self.feed)
        self.assertIn(".fc-panel.fc-margin {", block)


if __name__ == "__main__":
    unittest.main()
