#!/usr/bin/env python3
"""The guide's Files section says the Send confirm's third checkbox accepts only the pending changes you have seen, names the
gestures that count as seeing a change, says an unseen change stays pending and the checkbox says how many, and that with
none seen the checkbox is off; the panel does each of those.

The seen follow-on (2026-09-09, decision 41): a Send had accepted eleven changes the user had not looked at. The user keeps
the checkbox and its default but wants no unseen change accepted by a send. The guide's Send paragraph gained the sentence;
each clause is cross-checked against the panel and the model, so a reworded sentence, a renamed control or a dropped rule
fails here. Synthetic: only the repo's own text.
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


SENTENCE = ("When changes are pending, a third checkbox, **accept the pending changes you have seen**, accepts before the send "
            "the pending changes you have looked at, meaning a change whose card or mark was on screen when you scrolled, clicked, "
            "tapped, or pressed a key, so the session's later edits arrive as new changes instead of folding into an old one; a "
            "change you have not seen stays pending, and the checkbox says how many do, or, when you have seen none of them, that "
            "nothing is accepted until you look, and is then off. The message then says how many changes you accepted and rejected.")


class TheSentence(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.model = _read("ui", "webview", "file-comments-model.ts")

    def test_the_sentence_is_in_the_send_paragraph(self):
        self.assertIn(SENTENCE, self.section)
        self.assertNotIn("accepts them all before the send", self.section, "the accept-all wording is gone")
        self.assertNotIn("resolves comments", self.section, "a decision resolves nothing (decision 42), so the guide no longer says it does")

    def test_the_checkbox_words_are_the_models(self):
        self.assertIn('const base = "accept the " + seen + " pending " + (seen === 1 ? "change" : "changes") + " you have seen";', self.model)
        self.assertIn('unseen + " unseen " + (unseen === 1 ? "stays" : "stay") + " pending)"', self.model,
                      "the checkbox says how many unseen changes stay pending")
        self.assertIn('"; nothing is accepted until you look)"', self.model, "with none seen, the words say so")

    def test_the_gestures_are_the_panels_listeners(self):
        # scrolled = a wheel or a touch move; clicked and tapped = a pointer press; pressed a key = keydown
        self.assertIn('for (const ev of ["pointerdown", "keydown"]) row.addEventListener(ev, (e) => this.gesture(e), true);', self.panel)
        self.assertIn('for (const ev of ["wheel", "touchmove"]) row.addEventListener(ev, (e) => this.gesture(e), { capture: true, passive: true });', self.panel)

    def test_an_unseen_change_stays_pending_because_the_send_accepts_the_seen_ones_by_id(self):
        self.assertIn('const acceptIds = this.sendOpts.accept ? this.pendingSplit(s).seen.map((h) => String(h.id)) : [];', self.panel)
        self.assertIn('await this.mutate("accept", { ids: acceptIds }, "send")', self.panel)
        send = self.panel[self.panel.index("async doSend(): Promise<void> {"):self.panel.index("private async sendOnce(")]
        self.assertNotIn('"accept-all"', send, "never an accept-all from the send")

    def test_with_none_seen_the_checkbox_is_off(self):
        self.assertIn("cb.disabled = split.seen.length === 0;", self.panel)
        self.assertIn("cb.checked = split.seen.length > 0 && this.sendOpts.accept;", self.panel)

    def test_no_panel_vocabulary(self):
        for word in ("gesture", "seenKeys", "pendingSplit", "partitionPending", "syncAcceptOption", "accept-all"):
            self.assertNotIn(word, self.section)


if __name__ == "__main__":
    unittest.main()
