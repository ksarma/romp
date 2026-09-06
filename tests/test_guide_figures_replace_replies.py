#!/usr/bin/env python3
"""The guide's Figures paragraph says what a **Re-place** keeps: the comment's words AND its replies.

The paragraph described a re-place as "the comment keeps its words", the current-region title of
the panel's Re-place button (ui/webview/file-comments.ts). Read at the moment it matters, a stale
region comment a session has already answered, that line does not say whether the answer survives:
"its words" can mean the text the person typed alone. No other user-facing string on the Re-place
path names replies either (the stale title says where to draw, the composer note what Cancel does),
so the guide was the one place that could settle it and did not (review finding, 2026-09-06).

The fact is available and the host settles it: `retarget` in tools/file-comments-host.mjs writes
one field, `target` (the rectangle and the hash of the bytes it was drawn on), so the comment's id,
author, time, text, replies and resolved flag all stay by construction. The guide now says so in
the words a reader can act on, directly after the tooltip's phrase so the guide and the control
still agree word for word: the comment keeps its words and its replies, and only the rectangle
changes.

The tooltip's phrase stays as the sentence's head; tests/test_guide_figures_replace.py pins that
the guide carries the control's own words, and this module pins the fact the guide adds after
them. Synthetic: no session data, only the repo's own text.
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


class FiguresSaysWhatReplaceKeeps(unittest.TestCase):
    """The Re-place sentence names the replies, and the host it describes keeps them."""

    def setUp(self):
        guide = _read("docs", "guide.md")
        files = guide[guide.index("### Files"):guide.index("## Automatic nudges")]
        self.figures = _flat(_paragraph(files, "Figures"))
        # The sentence that names the control: from its bold label to the sentence's end.
        m = re.search(r"[^.]*\*\*Re-place\*\*[^.]*\.", self.figures)
        assert m, "the Figures paragraph no longer names **Re-place**"
        self.replace_sentence = m.group(0)

    def test_the_host_s_retarget_writes_only_the_target(self):
        # The premise, checked against its source: the one write a re-place makes is the target, so
        # the guide's "only the rectangle changes" and "keeps ... its replies" are the host's behavior,
        # not a promise the guide makes on its own.
        host = _read("tools", "file-comments-host.mjs")
        self.assertIn("return (s) => { findComment(s, id).target = target; };", host)

    def test_the_re_place_sentence_names_the_replies(self):
        # The finding: nothing a person reads on the Re-place path said whether replies survive.
        self.assertIn("replies", self.replace_sentence)

    def test_the_fact_follows_the_tooltip_s_phrase_word_for_word(self):
        # The control's own words head the clause (the pin in test_guide_figures_replace.py), and the
        # guide adds the fact after them, so a reader who saw the tooltip finds the same words here.
        self.assertIn("the comment keeps its words and its replies, and only the rectangle changes",
                      self.figures)

    def test_the_kept_set_is_stated_once(self):
        # One statement of what a re-place keeps, not the earlier "keeps its words" alone somewhere
        # else in the paragraph, so the paragraph cannot say two different things about it.
        self.assertEqual(self.figures.count("keeps its words"), 1)


if __name__ == "__main__":
    unittest.main()
