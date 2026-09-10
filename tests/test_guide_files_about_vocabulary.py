#!/usr/bin/env python3
"""The guide's Files section names a comment's relation to a change with "about", in the paragraphs that describe it.

CONTEXT.md's About entry (2026-09-10) lists under _Avoid_ the names the relation is not given: "bound to", "linked to"
(the old binding the session's edit made), "on a change" (a comment is on its passage or its file) and "thread". The
slice that added the entry also wrote "the two are linked by tags" into the Track changes paragraph, so the guide named
the new cross-reference with the verb the entry sets aside for the old binding (review finding, 2026-09-10). The
sentence now says the comment and the change each carry a tag for the other.

The avoid list is read from CONTEXT.md rather than hard-coded, so an entry added there fails here until this module
learns how it shows up in prose: a verb phrase is caught in every inflection and with any preposition ("linked by" as
much as "linked to"), and "on a change" only where it places a comment or a reply, since "on a change's card" and "a
click on a change mark" place a control or a gesture and are the guide's ordinary words. Control names in bold and
CLI flags in backticks are set aside: "Comment on this change" is the button's own name. The guide's other "link"s,
hyperlinks in a rendered file and the tooling `install.sh` links into a home folder, are outside these paragraphs and
are not this relation, which is why the check reads the paragraphs and not the section. Synthetic: only the repo's own
text.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

ABOUT_ENTRY = "About (a comment about a change)"

# How each avoided name shows up in prose. A verb is caught in every inflection and with any preposition; the
# location phrase only where it places a comment or a reply.
AVOID_IN_PROSE = {
    "bound to": r"\b(bound|binds?|binding)\b",
    "linked to": r"\b(links?|linked|linking)\b",
    "on a change": r"\b(comments?|repl(?:y|ies)) on (?:a|an|the|this|that|these|those|its|your|each|every|several|N) "
                   r"(?:pending |accepted |rejected )?changes?\b",
    "thread": r"\bthreads?\b",
}


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
    """The text with its code spans and bold control names removed: a flag in backticks is the format's own word,
    and a control's name in bold is the panel's."""
    return re.sub(r"\*\*[^*]*\*\*", "", re.sub(r"`[^`]*`", "", text))


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
    """The paragraph of the section that opens with `lead`, flattened. The lead is read at a line's start: the Track
    changes paragraph names **Send to session** mid-sentence, and that is not the Send paragraph."""
    m = re.search(r"^" + re.escape(lead), section, re.M)
    assert m, "paragraph %r not found" % lead
    end = section.find("\n\n", m.start())
    return _flat(section[m.start():] if end < 0 else section[m.start():end])


def _about_paragraphs():
    """The Files section's paragraphs that describe a comment's relation to a change: Track changes (the tags, the
    about option), Send to session (the message names the changes a comment is about) and the resolve rule."""
    section = _section(_read("docs", "guide.md"), "Files")
    return {
        "Track changes": _paragraph(section, "**Track changes**"),
        "Send to session": _paragraph(section, "**Send to session**"),
        "Resolve": _paragraph(section, "Nothing resolves a comment but you"),
    }


class AboutAvoidList(unittest.TestCase):
    """The premise: CONTEXT.md's About entry sets the relation's other names aside, and this module knows each."""

    def test_the_relation_names_are_on_the_list(self):
        words = _avoid_words(_read("CONTEXT.md"), ABOUT_ENTRY)
        for w in ("bound to", "linked to", "on a change", "thread"):
            self.assertIn(w, words)

    def test_every_listed_name_has_a_prose_pattern(self):
        for w in _avoid_words(_read("CONTEXT.md"), ABOUT_ENTRY):
            self.assertIn(w, AVOID_IN_PROSE, "CONTEXT.md avoids %r for a comment about a change; say how it shows up in prose" % w)

    def test_the_patterns_catch_the_old_wordings_and_pass_the_guides_own(self):
        # the slice's sentence, the old binding's name, a reply on the change, and the format's word
        for word, wording in (("linked to", "the two are linked by tags"),
                              ("linked to", "a comment linked to a change"),
                              ("bound to", "a comment bound to the change"),
                              ("on a change", "a reply on the change"),
                              ("on a change", "leaves a comment on a change"),
                              ("thread", "the change's thread")):
            self.assertRegex(wording, re.compile(AVOID_IN_PROSE[word], re.I), word)
        # the guide's ordinary words: a control's place, a gesture's place, a comment on its passage
        for wording in ("**Comment on this change** on a change's card opens the comment box",
                        "A click on a change mark or a comment highlight opens its card",
                        "a tap on a change places the caret",
                        "a plain comment on the passage",
                        "**N comments** on the change (click it to open the first)"):
            for pat in AVOID_IN_PROSE.values():
                self.assertNotRegex(_prose(wording), re.compile(pat, re.I), wording)


class TheParagraphsSayAbout(unittest.TestCase):
    """The paragraphs that describe the relation use none of the names CONTEXT.md sets aside."""

    def setUp(self):
        self.paragraphs = _about_paragraphs()
        self.avoid = _avoid_words(_read("CONTEXT.md"), ABOUT_ENTRY)

    def test_the_paragraphs_are_the_ones_that_describe_the_relation(self):
        self.assertIn("**about this change** checked", self.paragraphs["Track changes"])
        self.assertIn("the changes it is about", self.paragraphs["Send to session"])
        self.assertIn("**Resolve answered (N)**", self.paragraphs["Resolve"])

    def test_no_paragraph_uses_an_avoided_name(self):
        for lead, paragraph in self.paragraphs.items():
            prose = _prose(paragraph)
            for word in self.avoid:
                self.assertNotRegex(prose, re.compile(AVOID_IN_PROSE[word], re.I),
                                    "the %s paragraph says %r; CONTEXT.md avoids it for a comment about a change" % (lead, word))


class TheTagsSentence(unittest.TestCase):
    """The Track changes paragraph says the comment and the change each carry a tag for the other, and names the tags."""

    def setUp(self):
        self.paragraph = _about_paragraphs()["Track changes"]

    def test_each_card_carries_a_tag_for_the_other(self):
        self.assertIn("A comment is never shown inside a change's card: every comment is its own card, and the comment and "
                      "the change each carry a tag for the other, **about a change** on the comment (hover it to ring the "
                      "change's marks) and **N comments** on the change (click it to open the first).", self.paragraph)

    def test_the_old_wording_is_gone(self):
        # The finding: the slice's own CONTEXT entry sets "linked to" aside for the old binding, and the same slice wrote
        # "the two are linked by tags" for the new cross-reference.
        self.assertNotIn("linked by tags", self.paragraph)
        self.assertNotIn("cross-linked", self.paragraph)


if __name__ == "__main__":
    unittest.main()
