#!/usr/bin/env python3
"""The guide's Files section says a line under the panel's header counts what the session added since you last looked, and
that a save leaves the text where it is, a line at the foot of the panel saying whether the new card is above or below; the
panel does both.

The arrivals follow-on (2026-09-09): the user sent comments, the session answered with eleven changes and seven replies while
they kept commenting, and nothing in the panel said so until the next Send accepted the changes by default; and a reply they
saved pulled the text back to its card after they had scrolled on. The panel now keeps the set of entries the person has seen,
names the rest in a line under the header with a dot on each card until a gesture finds it on screen, and never scrolls on a
save (decision 43, the same day: at first the scroll stood down once the person had moved on; the user then preferred no
scroll at all, and a line at the panel's foot says where the card is). The guide's Files section gained a sentence for the
first and two for the second; each clause is cross-checked against the panel, the model and the sheets, so a reworded
sentence, a renamed control or a dropped rule fails here. Synthetic: only the repo's own text.
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


BEFORE_NOTICE = "a file the session rewrote is shown as it is now."
NOTICE = ("A line under the panel's header counts the changes, comments, and replies the session added since you last looked, "
          "and each of their cards wears a dot until you scroll or click with it in view; click the line to open the first of them.")
BEFORE_SAVE = "on a phone or a tablet the button is the way, and the line under the box says so."
SAVE = ("Saving leaves the text where it is. When the new card lands out of view, a line at the foot of the panel, "
        "**Saved · the card is above** (or **below**), says where it went; click the line to bring the card into view, or leave it: "
        "it goes with your next scroll, click, tap, or key, except Tab or a modifier key pressed on its own, so you can reach it "
        "from the keyboard.")


class TheTwoSentences(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))

    def test_the_notice_sentence_follows_the_poll_sentence(self):
        self.assertIn(BEFORE_NOTICE + " " + NOTICE, self.section)

    def test_the_save_sentences_follow_the_composer_sentence(self):
        self.assertIn(BEFORE_SAVE + " " + SAVE, self.section)

    def test_no_panel_vocabulary(self):
        # the guide speaks in the reader's terms: no gesture, seen set, entry key or attribute name
        for word in ("gesture", "seenKeys", "data-new", "fcarrivals", "entryShown", "cardWhere", "savedOut", "landSaved", "fcsavedgo"):
            self.assertNotIn(word, self.section)

    def test_the_save_pin_agrees_with_the_save_line_module(self):
        # tests/test_guide_files_save_line.py requires words of the same sentences and forbids others; the exact text pinned
        # here must satisfy both, or the two modules contradict and no guide wording is green (the arrivals review round 1
        # rewrote the sentence and this pin alone, 2026-09-09)
        sibling = _read("tests", "test_guide_files_save_line.py")
        required = re.findall(r'self\.assertIn\("([^"]+)", self\.sentence\)', sibling)
        forbidden = re.findall(r'self\.assertNotIn\("([^"]+)", self\.sentence\)', sibling)
        self.assertTrue(required and forbidden, "the save-line module's literal pins on the save sentences")
        for phrase in required:
            self.assertIn(phrase, SAVE)
        for phrase in forbidden:
            self.assertNotIn(phrase, SAVE)


class TheSentencesMatchThePanel(unittest.TestCase):
    """Each clause names something the panel, the model and the sheets do."""

    def setUp(self):
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.model = _read("ui", "webview", "file-comments-model.ts")
        self.styles = _read("ui", "webview", "styles.css")
        self.feed = _read("ui", "webview", "feed.css")

    def test_a_line_under_the_header_counts_what_arrived(self):
        self.assertIn("if (this.arrivals.size) head.appendChild(this.arrivalLine());", self.panel)
        self.assertIn('" since you last looked"', self.model)
        # the counts by kind: changes, comments, replies
        self.assertIn('plural(counts.change, "change", "changes")', self.model)
        self.assertIn('plural(counts.comment, "comment", "comments")', self.model)
        self.assertIn('plural(counts.reply, "reply", "replies")', self.model)

    def test_each_card_wears_a_dot_until_a_gesture_finds_it_in_view(self):
        self.assertIn('card.dataset.new = "1"', self.panel)
        self.assertIn("for (const [k, e] of Array.from(this.arrivals)) {\n        if (!this.entryShown(e)) continue;", self.panel)
        for css in (self.styles, self.feed):
            self.assertIn(".fc-card[data-new] > .fc-card-head::before", css)
            self.assertIn(".fc-arrivals::before", css)
        # a gesture, never a timer: the events the constructor listens for, and no timer in the gesture's body
        self.assertIn('for (const ev of ["pointerdown", "keydown"]) row.addEventListener(ev, (e) => this.gesture(e), true);', self.panel)
        self.assertIn('for (const ev of ["wheel", "touchmove"]) row.addEventListener(ev, (e) => this.gesture(e), { capture: true, passive: true });', self.panel)
        body = self.panel[self.panel.index("gesture(ev?: Event): void {"):self.panel.index("private entryShown(")]
        self.assertNotIn("setTimeout", body)

    def test_click_the_line_to_open_the_first_of_them(self):
        self.assertIn("fcarrivals: () => this.goToArrival(),", self.panel)
        self.assertIn("this.showCard(first);", self.panel)

    def test_saving_leaves_the_text_and_the_line_says_where_the_card_is(self):
        land = self.panel[self.panel.index("private landSaved("):self.panel.index("private cardWhere(")]
        for call in ("scrollCard", "scrollBoth", "scrollIntoView", "centerOn", "showLoose", "scrollTop"):
            self.assertNotIn(call, land, "a save never scrolls (decision 43): %s" % call)
        self.assertIn("const lined = r !== null && this.landSaved(c, had, r, note);", self.panel)
        self.assertIn('return "Saved · the card is " + side;', self.model)
        self.assertIn("fcsavedgo: () => { const out = this.savedOut; this.savedOut = null; if (out) this.scrollCard(out.key); this.reflect(); },", self.panel)


if __name__ == "__main__":
    unittest.main()
