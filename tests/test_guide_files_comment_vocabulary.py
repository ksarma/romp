#!/usr/bin/env python3
"""The guide's Files section calls a file comment a comment, in every sentence of the Comments paragraph.

CONTEXT.md's File comment entry lists "note" under _Avoid_ (2026-09-06). The composer slice rewrote the
Comments paragraph's first sentence to "type the comment (Enter adds a line) and save it with ..." and
left the next sentence's "keeps your note" as it was, so one paragraph named the typed text two ways
(review finding, 2026-09-07). The sentence now says "keeps your comment".

The avoid list is read from CONTEXT.md rather than hard-coded, so a word added there fails here too.
The File comment entry's _Avoid_ line wraps onto a second line, which is why the helper takes the rest
of the entry and not one line. Code spans are set aside: a CLI flag quoted in backticks is the format's
own word, not the guide's. Synthetic: no session data, only the repo's own text.
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


def _prose(text):
    """The text with its code spans removed: a flag name in backticks is not the guide's own word."""
    return re.sub(r"`[^`]*`", "", text)


def _avoid_words(context_md, term):
    """The words CONTEXT.md's `**term**:` entry lists under _Avoid_, across every line the list wraps onto,
    parentheticals dropped."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    avoid = re.search(r"^_Avoid_:(.*)\Z", m.group(1), re.S | re.M)
    assert avoid, "CONTEXT.md entry %r has no _Avoid_ line" % term
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [_flat(w) for w in bare.split(",") if w.strip()]


def _paragraph(section, lead):
    """The paragraph of the section that opens with `lead`, flattened."""
    start = section.index(lead)
    end = section.find("\n\n", start)
    return _flat(section[start:] if end < 0 else section[start:end])


class FileCommentAvoidList(unittest.TestCase):
    """The premise: CONTEXT.md avoids "note" for a file comment, and its list wraps onto two lines."""

    def test_note_is_on_the_list(self):
        words = _avoid_words(_read("CONTEXT.md"), "File comment")
        self.assertIn("note", words)
        self.assertIn("thread", words)
        self.assertIn("annotation", words)
        self.assertIn("review comment", words, "the second line of the wrapped _Avoid_ list was not read")


class FilesSectionUsesTheTerm(unittest.TestCase):
    """The Files section uses none of the words CONTEXT.md's File comment entry says to avoid."""

    def setUp(self):
        self.section = _section(_read("docs", "guide.md"), "Files")
        self.avoid = _avoid_words(_read("CONTEXT.md"), "File comment")

    def test_the_section_is_the_one_that_describes_comments(self):
        self.assertIn("Comments are stored beside the file", _flat(self.section))

    def test_the_section_uses_no_avoid_word(self):
        prose = _prose(self.section)
        for word in self.avoid:
            self.assertNotRegex(prose, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                "the Files section says %r; CONTEXT.md avoids it for a file comment" % word)


class CommentsParagraphNamesTheTypedTextOnce(unittest.TestCase):
    """The Comments paragraph says "comment" for the text you type, in the sentence that saves it and in
    the sentence that keeps it when the Rendered view cannot place the passage."""

    def setUp(self):
        section = _section(_read("docs", "guide.md"), "Files")
        self.paragraph = _paragraph(section, "**Comments and tracked changes.**")

    def test_typing_and_keeping_use_the_same_word(self):
        self.assertIn("type the comment (Enter adds a line)", self.paragraph)
        self.assertIn("the panel says so, keeps your comment, and offers the Raw view with the passage selected",
                      self.paragraph)

    def test_the_half_edit_is_gone(self):
        # The finding: the first sentence said "comment" and the refusal sentence, three lines on, "your note".
        self.assertNotIn("your note", self.paragraph)
        self.assertNotIn("the note", self.paragraph)


if __name__ == "__main__":
    unittest.main()
