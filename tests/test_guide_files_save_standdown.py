#!/usr/bin/env python3
"""The guide's save sentence names every kind of gesture that stands the save's scroll down; the panel counts exactly those.

The arrivals follow-on (2026-09-09) made the save's scroll to the saved card stand down once the person has moved on, and
"moved on" is any gesture of theirs the panel counts (gesture): a scroll begun by a wheel or a touch move, a pointer press,
a key, each a listener the constructor registers on the body row. The guide's first wording promised the scroll unless you
scrolled on, so a click on a card head or a key pressed during the host round trip left the text where it was while the
guide said the card would come into view (the arrivals review, 2026-09-09). This module reads the events the constructor
counts and requires the sentence to name each one in the reader's words, so a listener added without a word for it, or a
word dropped from the sentence, fails here. The sentence's exact text and its place in the section are pinned by
tests/test_guide_files_arrivals.py. Synthetic: only the repo's own text.
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


def _save_sentence(section):
    m = re.search(r"Saving brings the new card into view[^.]*\.", section)
    assert m, "the save sentence"
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
    "wheel": "scrolled",
    "touchmove": "scrolled",
    "pointerdown": ("clicked", "tapped"),   # a mouse press and a touch are both pointer presses; the guide names each
    "keydown": "pressed a key",
}


class TheSaveSentenceNamesEveryStandDown(unittest.TestCase):
    def setUp(self):
        self.sentence = _save_sentence(_flat(_section(_read("docs", "guide.md"), "Files")))
        self.panel = _read("ui", "webview", "file-comments.ts")

    def test_every_counted_event_has_a_word(self):
        for ev in _gesture_events(self.panel):
            self.assertIn(ev, WORD_FOR_EVENT, "the constructor counts %r as a gesture; the guide's save sentence has no word for it" % ev)

    def test_the_sentence_names_each_kind(self):
        for ev in _gesture_events(self.panel):
            words = WORD_FOR_EVENT[ev]
            for w in (words if isinstance(words, tuple) else (words,)):
                self.assertIn(w, self.sentence, "the save sentence does not say %r (the %s listener)" % (w, ev))
        self.assertIn("unless you scrolled, clicked, tapped, or pressed a key while the save was under way", self.sentence)

    def test_the_save_is_judged_by_the_gesture_count(self):
        # the sentence's "unless" is the count sampled at Save and read when the reply lands, not one event kind
        self.assertIn("const pressed = this.gestures;", self.panel)
        self.assertIn("pressed === this.gestures", self.panel)
        self.assertIn("if (still && !this.cardWhole(key)) { this.scrollCard(key); return; }", self.panel)

    def test_scrolling_alone_is_not_named_as_the_only_stand_down(self):
        self.assertNotIn("unless you scrolled on", self.sentence)


if __name__ == "__main__":
    unittest.main()
