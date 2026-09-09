#!/usr/bin/env python3
"""The guide's Files section says where the saved line stands in each layout, and the panel and the sheets agree.

Decision 43 (2026-09-09) put a line in the acknowledgment's position at the panel's foot saying whether the card a save
landed in is above or below when it is out of view (tests/test_guide_files_arrivals.py pins that sentence, and
tests/test_guide_files_save_line.py holds its gestures to the panel). The seen slice's first review round moved the list
layout's line under the panel's header: the list under a narrow column scrolls the whole panel, so its Send section is
below every card, below the very card the line says is below, and a line there was never on screen when it was wanted;
the margin layout's panel clips and its cards track is the one scroller, so the Send section stands at the foot and the
line keeps the acknowledgment's position there. The guide stated the foot for both layouts (the second review round, the
same day); a sentence now follows the save sentences saying the list puts the line under the header. This holds that
sentence to the guide, to the panel that places the line by layout, to the sheets that put the margin layout's Send
section at the foot, and to the panel's own tests of both placements, so a reworded sentence, a line moved in one layout
or a dropped placement test fails here. Synthetic: only the repo's own text.
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


# the claim the qualifier scopes (the exact text is tests/test_guide_files_arrivals.py's), the qualifier, and what follows it
FOOT = ("When the new card lands out of view, a line at the foot of the panel, **Saved · the card is above** (or **below**), "
        "says where it went; click the line to bring the card into view, or leave it: it goes with your next scroll, click, tap, or key.")
LIST = "In the list under a narrow column, the line stands under the panel's header instead."
AFTER = "**Comment on this file** leaves a comment on the file as a whole"
# the section's own name for the layout, given where it first scopes a claim to the panel beside the file
LAYOUT = "in the list under a narrow column, where a long card shows whole."


class TheListSentenceFollowsTheSaveSentences(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))

    def test_the_qualifier_stands_right_after_the_claim_it_scopes(self):
        # the foot is stated, then the list's exception, before the paragraph moves on to the whole-file comment
        self.assertIn(FOOT + " " + LIST + " " + AFTER, self.section)

    def test_the_foot_is_claimed_for_the_saved_line_once(self):
        self.assertEqual(self.section.count("a line at the foot of the panel"), 1)

    def test_the_layout_is_named_the_way_the_section_names_it(self):
        # the reader met "the list under a narrow column" earlier in the section, where the fold is scoped away from the list
        self.assertLess(self.section.index(LAYOUT), self.section.index(LIST))
        self.assertIn("when the column is narrow the panel drops below the file and lists the cards instead", self.section)

    def test_no_panel_vocabulary(self):
        for word in ("savedLineHead", "renderHead", "renderSend", "savedLine", "savedButton", "fc-sec-head", "fc-sec-send",
                     "margin layout", "list layout", "this.margin"):
            self.assertNotIn(word, self.section)


class ThePanelPlacesTheLineByLayout(unittest.TestCase):
    """One button, built once (savedButton); the margin layout appends it in the Send section, the list layout in the head."""

    def setUp(self):
        self.panel = _read("ui", "webview", "file-comments.ts")

    def test_the_margin_layout_keeps_the_acknowledgments_position(self):
        self.assertRegex(self.panel, r"private savedLine\(\): HTMLElement \| null \{\n\s*return this\.margin \? this\.savedButton\(\) : null;")
        self.assertRegex(self.panel, r"const saved = this\.savedLine\(\);[^\n]*\n\s*if \(saved\) box\.appendChild\(saved\);")

    def test_the_list_layout_puts_the_line_under_the_header(self):
        self.assertRegex(self.panel, r"private savedLineHead\(\): HTMLElement \| null \{\n\s*return this\.margin \? null : this\.savedButton\(\);")
        self.assertRegex(self.panel, r"const saved = this\.savedLineHead\(\);\n\s*if \(saved\) head\.appendChild\(saved\);\n\s*return head;")

    def test_one_button_in_either_place(self):
        # the words, the action and the dress are one builder's, so the guide's sentence about the line holds in both layouts
        self.assertEqual(self.panel.count('btn(savedWhereWords(this.savedOut.side), "fcsavedgo", "fc-note fc-sent fc-saved")'), 1)
        self.assertEqual(self.panel.count("this.savedButton()"), 2)

    def test_the_list_is_the_layout_with_the_margin_off(self):
        # the guide's "list under a narrow column" is the panel with `margin` false (layoutOff), the case savedLineHead renders for
        self.assertIn("this.margin = false", self.panel)
        self.assertIn("this.margin = true", self.panel)


class TheSheetsPutTheMarginLayoutsSendSectionAtTheFoot(unittest.TestCase):
    """The margin layout's panel clips and its cards track is the one scroller, so the Send section under the track stands
    at the panel's foot, on screen; the list layout has no such rule, its whole panel scrolls, which is why its line is
    under the header instead. Both sheets carry the block."""

    def setUp(self):
        self.styles = _read("ui", "webview", "styles.css")
        self.feed = _read("ui", "webview", "feed.css")

    def test_the_margin_panel_clips_and_the_track_is_the_scroller(self):
        for css in (self.styles, self.feed):
            self.assertIn(".fc-panel.fc-margin { overflow: hidden; padding: 0; gap: 0; }", css)
            self.assertIn(".fc-margin > .fc-sec-cards { flex: 1 1 0; min-height: 30%; position: relative; overflow: auto; scrollbar-width: none; }", css)
            self.assertIn("Send and the Log at the bottom", css)


class ThePanelTestsHoldBothPlacements(unittest.TestCase):
    """The behavior itself is proven by the panel's suite; the guide's sentence names what it asserts."""

    def test_the_seen_fixes_suite_asserts_the_head_and_the_send_section(self):
        node = _read("ui", "webview", "file-comments-seen-fixes.test.ts")
        self.assertIn('test("the list layout: the line stands under the header, where the composer was, not in the Send section at the scroller\'s foot', node)
        self.assertIn('"under the header"', node)
        self.assertIn('"not at the foot (before: there, below every card)"', node)
        self.assertIn('test("the margin layout keeps the line in the Send section, the acknowledgment\'s position at the panel\'s foot"', node)
        self.assertIn('"in the Send section"', node)


if __name__ == "__main__":
    unittest.main()
