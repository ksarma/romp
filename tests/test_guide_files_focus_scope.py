#!/usr/bin/env python3
"""The guide's Files section scopes the focus placement and the fold to the panel beside the file, and the panel agrees.

The focus follow-on's sentence (tests/test_guide_files_focus.py) says the card you click sits level with its passage and
that a long card folds to a few lines with Show more. Both hold only in the margin layout: the sheets cap a part under the
`fc-margin` class alone, and the pass that finds the cut parts and shows the Show more row returns before that step when
the row has folded to a column, so the list under a narrow column (a phone, a dashboard pane under the fold width) shows a
long card whole and no button. The guide used to state the fold unconditionally, right after the clause about the narrow
column; a sentence now follows it saying the list does neither. This holds that sentence to the guide, to the sheets and
the panel that do the scoping, and to the panel's own tests of the list layout, so a reworded sentence, a cap that escapes
the margin class or a dropped list-layout test fails here. Synthetic: only the repo's own text.
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


FOLD = ("The card you click sits level with its passage whatever stands above it, and a long card folds to a few "
        "lines with **Show more** at its foot.")
SCOPE = "Neither happens in the list under a narrow column, where a long card shows whole."


class TheScopeFollowsTheFoldSentence(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))

    def test_the_scope_sentence_follows_the_fold_sentence(self):
        # the qualifier stands right after the two claims it scopes, before the paragraph moves on to selecting a passage
        self.assertIn(FOLD + " " + SCOPE + " Select a passage", self.section)

    def test_the_fold_is_not_promised_elsewhere_unscoped(self):
        # the guide's only Show more is the one the scope sentence follows
        self.assertEqual(self.section.count("**Show more**"), 1)

    def test_no_panel_vocabulary(self):
        for word in ("fc-margin", "clipCards", "layoutOff", "marginMode", "container query"):
            self.assertNotIn(word, self.section)


class TheSheetsCapOnlyBesideTheFile(unittest.TestCase):
    """Every rule that caps a card part is under the margin class, in both sheets."""

    def setUp(self):
        self.styles = _read("ui", "webview", "styles.css")
        self.feed = _read("ui", "webview", "feed.css")

    def test_every_cap_is_scoped_to_the_margin_layout(self):
        for css in (self.styles, self.feed):
            caps = [ln for ln in css.splitlines() if ".fc-clip" in ln and "max-height" in ln]
            self.assertEqual(len(caps), 1, caps)
            self.assertTrue(caps[0].startswith(".fc-margin .fc-card:not(.fc-more) .fc-clip {"), caps[0])

    def test_the_sheet_says_the_list_shows_every_part_whole(self):
        for css in (self.styles, self.feed):
            self.assertIn("The list layout shows every part whole, and the row stays hidden there.", css)


class ThePanelSkipsTheFoldInTheList(unittest.TestCase):
    """The pass leaves the list layout before it reads the cut parts, and the Show more row renders hidden."""

    def setUp(self):
        self.panel = _read("ui", "webview", "file-comments.ts")

    def test_the_pass_returns_before_the_clip_step_when_the_row_has_folded(self):
        # placeCards: the list layout returns (dropping the margin class) before clipCards, the only step that shows the row
        self.assertEqual(self.panel.count("this.clipCards("), 1)
        # the list branch: a block since the review (it clears the focus a click in the list wrote), ending in the return
        ret = self.panel.index("    if (!margin) {\n")
        end = self.panel.index("      if (flipped) { this.layoutOff(); if (!fromRender) this.render(); }\n      return;\n    }\n", ret)
        clip = self.panel.index("this.clipCards(kids());")
        self.assertLess(end, clip)
        self.assertIn('this.root?.classList.remove("fc-margin");', self.panel)

    def test_the_show_more_row_renders_hidden(self):
        # clipRow: hidden as rendered; only the margin pass un-hides it
        self.assertRegex(self.panel, r"row\.hidden = true;\n\s*return row;")

    def test_the_panel_tests_hold_the_list_layout(self):
        # the behavior itself is proven by the panel's suites; the guide's sentence names what they assert
        node = _read("ui", "webview", "file-comments-focus.test.ts")
        browser = _read("ui", "webview", "file-comments-focus-browser.test.ts")
        self.assertIn('test("the list layout clips nothing:', node)
        self.assertIn('"no Show more in the list"', node)
        self.assertIn('"no cap in the list"', browser)
        self.assertIn('"no Show more in the list"', browser)


if __name__ == "__main__":
    unittest.main()
