#!/usr/bin/env python3
"""The guide's save sentences say a save leaves the text where it is, that a line at the foot of the panel says whether the new
card is above or below, that clicking the line brings the card into view, and that the line goes with your next gesture; the
sentences name every kind of gesture the panel counts, and the panel does each of those.

Decision 43 (2026-09-09): the user prefers no scroll after a save, a scroll being disruptive, and accepts that the person
may then have to look for the card; the line at the panel's foot is the answer to that. Before it, the arrivals follow-on
had the save's scroll stand down once the person had moved on, and this module (then named for the stand-down) held the
guide's sentence to the gestures that stood it down. The same gestures now end the line, so the module keeps its shape:
it reads the events the constructor routes into gesture() and requires the sentences to name each one in the reader's words,
so a listener added without a word for it, or a word dropped from the sentences, fails here. The sentences' exact text and
their place in the section are pinned by tests/test_guide_files_arrivals.py. Synthetic: only the repo's own text.
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


def _save_sentences(section):
    m = re.search(r"Saving leaves the text where it is\. When the new card lands out of view[^.]*\.", section)
    assert m, "the save sentences"
    return m.group(0)


def _gesture_events(panel):
    """The events the constructor routes into gesture(): every `for (const ev of [...]) row.addEventListener(ev, (e) => this.gesture(e)` list."""
    events = set()
    for m in re.finditer(r"for \(const ev of \[([^\]]*)\]\) row\.addEventListener\(ev, \(e\) => this\.gesture\(e\)", panel):
        events.update(re.findall(r'"([a-z]+)"', m.group(1)))
    assert events, "the constructor's gesture listeners"
    return events


# each counted event, and the word the reader knows it by; a listener with no row here fails test_every_counted_event_has_a_word
WORD_FOR_EVENT = {
    "wheel": "scroll",
    "touchmove": "scroll",
    "pointerdown": ("click", "tap"),   # a mouse press and a touch are both pointer presses; the guide names each
    "keydown": "key",
}


class TheSaveSentencesNameEveryGestureThatEndsTheLine(unittest.TestCase):
    def setUp(self):
        self.sentence = _save_sentences(_flat(_section(_read("docs", "guide.md"), "Files")))
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.model = _read("ui", "webview", "file-comments-model.ts")

    def test_every_counted_event_has_a_word(self):
        for ev in _gesture_events(self.panel):
            self.assertIn(ev, WORD_FOR_EVENT, "the constructor counts %r as a gesture; the guide's save sentences have no word for it" % ev)

    def test_the_sentences_name_each_kind(self):
        for ev in _gesture_events(self.panel):
            words = WORD_FOR_EVENT[ev]
            for w in (words if isinstance(words, tuple) else (words,)):
                self.assertIn(w, self.sentence, "the save sentences do not say %r (the %s listener)" % (w, ev))
        self.assertIn("it goes with your next scroll, click, tap, or key", self.sentence)

    def test_the_line_ends_at_a_gesture_and_not_at_a_press_on_itself(self):
        # the sentences' "goes with your next ..." is the gesture handler ending the line, the line's own press excepted (its click is what it is for)
        gesture = self.panel[self.panel.index("gesture(ev?: Event): void {"):self.panel.index("private entryShown(")]
        self.assertIn('const over = this.savedOut !== null && !on("fcsavedgo");', gesture)
        self.assertIn("if (over) this.savedOut = null;", gesture)
        self.assertNotIn("setTimeout", gesture)

    def test_a_save_never_moves_the_text(self):
        land = self.panel[self.panel.index("private landSaved("):self.panel.index("private cardWhere(")]
        for call in ("scrollCard", "scrollBoth", "scrollIntoView", "centerOn", "showLoose", "scrollTop"):
            self.assertNotIn(call, land, "the landing of a save must not scroll (decision 43): %s" % call)
        self.assertIn("if (this.margin) this.focusOn(key);", land, "the card is the focus for the layout all the same")

    def test_the_line_says_above_or_below_in_the_models_words(self):
        self.assertIn('return "Saved · the card is " + side;', self.model)
        self.assertIn("**Saved · the card is above** (or **below**)", self.sentence)
        self.assertIn('private cardWhere(key: string): "above" | "below" | null {', self.panel)

    def test_clicking_the_line_brings_the_card_into_view(self):
        self.assertIn("fcsavedgo: () => { const out = this.savedOut; this.savedOut = null; if (out) this.scrollCard(out.key); this.reflect(); },", self.panel)
        self.assertIn('btn(savedWhereWords(this.savedOut.side), "fcsavedgo", "fc-note fc-sent fc-saved")', self.panel)

    def test_the_scroll_wordings_are_gone(self):
        self.assertNotIn("Saving brings the new card into view", self.sentence)
        self.assertNotIn("unless you scrolled", self.sentence)


if __name__ == "__main__":
    unittest.main()
