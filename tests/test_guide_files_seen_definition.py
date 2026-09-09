#!/usr/bin/env python3
"""The guide's definition of a seen change is the panel's: the changes already there when the panel was first opened, and a
later one whose CARD was in view at a gesture. The panel does exactly that, and the guide says neither more nor less.

The seen follow-on's review (2026-09-09): the guide's Send sentence first said a seen change was one "whose card or mark was on
screen" at a gesture, and it said nothing about the panel's first status. The panel reads the card alone (entryShown: the
placed top inside the track's box in the margin layout, the card's box inside the aside's in the list layout; a mark on
screen with its card out of view leaves the change unseen), and it seeds the seen set with every entry of its first status
and of the first status to land while it is open (render, noteArrivals), so a pending change present at the first open is
accepted by the send with no gesture at all. The guide now states both; each clause is cross-checked here against the panel's
code, so a guide that promises the mark path or drops the first-open clause fails, and so does a panel that stops seeding or
starts reading marks without the guide following. Synthetic: only the repo's own text.
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
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _method(src, signature):
    """The body of one method of the panel class: from its signature to the class-level closing brace that follows."""
    start = src.index(signature)
    end = src.index("\n  }\n", start)
    return src[start:end]


SENTENCE = ("When changes are pending, a third checkbox, **accept the pending changes you have seen**, accepts before the send "
            "the pending changes you have looked at: the ones already there when you first opened the panel, and any that arrived "
            "later whose card was in view when you scrolled, clicked, tapped, or pressed a key. That way the session's later edits "
            "arrive as new changes instead of folding into an old one. A change you have not seen stays pending, and the checkbox "
            "says how many do, or, when you have seen none of them, that nothing is accepted until you look, and is then off. "
            "The message then says how many changes you accepted and rejected.")


class TheDefinition(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.panel = _read("ui", "webview", "file-comments.ts")

    def test_the_sentence_is_in_the_send_paragraph(self):
        self.assertIn(SENTENCE, self.section)

    def test_the_guide_does_not_promise_the_mark_path(self):
        # the panel never reads a mark's place for seen (below), so the guide must not say a mark on screen counts
        self.assertNotIn("card or mark", self.section)
        self.assertNotIn("or mark was", self.section)

    def test_the_first_open_clause_is_the_panels_seeding(self):
        # the first render with a status seeds the seen set with every entry of it ...
        self.assertIn("if (this.seenKeys === null && s) this.seenKeys = new Set(statusEntries(s).map((e) => e.key));", self.panel)
        # ... and the first status to land while the panel is open is all seen as well (noteArrivals, seenOpen)
        note = _method(self.panel, "private noteArrivals(s: Status): void {")
        self.assertIn("if (!this.seenOpen) {", note)
        self.assertIn("this.seenOpen = true;", note)
        self.assertIn("for (const e of entries) seen.add(e.key);", note)

    def test_the_card_clause_is_the_panels_entry_shown(self):
        shown = _method(self.panel, "private entryShown(e: Entry): boolean {")
        # the card is what is read: found by its key in the track ...
        self.assertIn(".fc-card[data-id=", shown)
        # ... its placed top against the track's box in the margin layout, its own box against the aside's in the list layout
        self.assertIn("const p = this.placed.get(key);", shown)
        self.assertIn("return p.top >= at && p.top < at + track.clientHeight;", shown)
        self.assertIn("const r = card.getBoundingClientRect(), box = this.root.getBoundingClientRect();", shown)
        # ... and never a mark: no mark lookup, no mark geometry
        for mark_path in ("ownMarks", "markTop", "fc-mark", "dataset.act"):
            self.assertNotIn(mark_path, shown, "entryShown reads the card alone; if it now reads marks, reword the guide's clause")
        # the gesture is what admits an arrival, and only one whose card is shown
        gesture = _method(self.panel, "gesture(ev?: Event): void {")
        self.assertIn("if (!this.entryShown(e)) continue;", gesture)

    def test_the_gestures_are_the_panels_listeners(self):
        # scrolled = a wheel or a touch move; clicked and tapped = a pointer press; pressed a key = keydown
        self.assertIn('for (const ev of ["pointerdown", "keydown"]) row.addEventListener(ev, (e) => this.gesture(e), true);', self.panel)
        self.assertIn('for (const ev of ["wheel", "touchmove"]) row.addEventListener(ev, (e) => this.gesture(e), { capture: true, passive: true });', self.panel)

    def test_no_panel_vocabulary(self):
        for word in ("gesture", "seenKeys", "seenOpen", "entryShown", "noteArrivals", "statusEntries", "first status", "seed"):
            self.assertNotIn(word, self.section)


if __name__ == "__main__":
    unittest.main()
