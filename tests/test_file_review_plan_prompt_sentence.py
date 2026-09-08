#!/usr/bin/env python3
"""The plan's From the session's side bullet, decision 35 and the session prompt say the same thing about
where a file's path goes.

A review finding on the todo-file follow-on (plans/file-review.md, 2026-09-07). The follow-on moved the link
between a user todo and its file from a path in the detail's free text to `add_user_todo`'s `file` argument:
`claude/romp-session-prompt.md` tells sessions to give the absolute path as the `file` argument (the detail
may still describe it), `tests/test_session_prompt.py` pins that wording, and decision 35 was amended to say
so with a pointer to Getting into it. The Getting into it bullet the pointer lands on, the one place the plan
spells out the prompt's sentence, was left as approved: the path in the detail. A reader following the
decision learned the mechanism the prompt no longer teaches.

The fix amended the bullet in place with a dated note recording the departure, the way decision 35 was. This
module holds the three to one another: the bullet and the prompt share the sentence's load-bearing phrases
(the tool, the `file` argument, the detail's remaining role, what comes back, the fallback); the bullet no
longer states the detail as the mechanism and records that it once did; decision 35 names the `file` argument
and points at a bullet that agrees; the follow-on note says the prompt passes it; and the Tests section names
this module, so the record the next implementer reads knows the pin exists. Every premise is read from the
files, so whichever side moves first, the failure names the other. Synthetic: the repo's own text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

BULLET_LEAD = "- From the session's side:"
NOTE_LEAD = "The todo-file follow-on (2026-09-07):"
THIS_MODULE = "tests/test_file_review_plan_prompt_sentence.py"

# The phrases the prompt's sentence is made of. The bullet quotes the sentence, so each must appear on both
# sides; a rewording of either side that drops one fails here, naming the side.
SHARED_PHRASES = (
    "flag it with `add_user_todo` if you have that tool",
    "absolute path as its `file` argument",
    "in the detail, which can still describe it",
    "my comments come back to you as a message with instructions",
    "ask for the look in your reply and name the file",
)
# The approved wording, which made the detail the mechanism. Neither side may say it any more.
DETAIL_AS_MECHANISM = "that tool, with the file's absolute path in the detail"


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _section(md, heading):
    """The body under the heading line that starts with `heading` (the line may carry more, as the Decisions
    heading does), up to the next heading of any level, uncollapsed."""
    m = re.search(r"(?m)^%s[^\n]*\n" % re.escape(heading), md)
    assert m, "heading %r not found in the plan" % heading
    body = md[m.end():]
    end = re.search(r"\n#{1,4} ", body)
    return body[: end.start()] if end else body


def _bullet(section, lead):
    """The markdown bullet that starts with `lead`, joined across its wrapped lines and collapsed."""
    for b in re.split(r"\n(?=- )", section):
        if b.startswith(lead):
            return _flat(b)
    raise AssertionError("no bullet starts with %r" % lead)


def _paragraph(md, lead):
    """The blank-line paragraph that starts with `lead`, collapsed."""
    for p in re.split(r"\n\s*\n", md):
        if p.lstrip().startswith(lead):
            return _flat(p)
    raise AssertionError("no paragraph starts with %r" % lead)


def _decision(md, n):
    """Numbered decision `n` of the Decisions section, joined across its wrapped lines and collapsed."""
    decisions = _section(md, "## Decisions")
    m = re.search(r"(?:^|\n)%d\. .*?(?=\n\d+\. |\n\s*\n|\Z)" % n, decisions, re.S)
    assert m, "decision %d not found" % n
    return _flat(m.group(0))


class PromptSentenceAgreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = _read("plans", "file-review.md")
        cls.prompt = _flat(_read("claude", "romp-session-prompt.md"))
        cls.getting_into_it = _section(cls.plan, "### Getting into it")
        cls.bullet = _bullet(cls.getting_into_it, BULLET_LEAD)

    def test_the_bullet_and_the_prompt_share_the_sentence(self):
        for phrase in SHARED_PHRASES:
            self.assertIn(phrase, self.prompt,
                          "the session prompt no longer says %r; if that is deliberate, the plan's From the "
                          "session's side bullet quotes the sentence and must change with it" % phrase)
            self.assertIn(phrase, self.bullet,
                          "the plan's From the session's side bullet does not say %r, which the session prompt "
                          "does; the bullet is where the plan spells out the sentence, so it says what ships"
                          % phrase)

    def test_neither_side_makes_the_detail_the_mechanism(self):
        # The approved sentence put the path in the detail. The prompt moved it to the `file` argument
        # (commit-level record in the follow-on note); the bullet then said both things at once.
        self.assertNotIn(DETAIL_AS_MECHANISM, self.prompt,
                         "the prompt has gone back to the detail as the mechanism; decision 35 and the bullet "
                         "say the `file` argument")
        self.assertNotIn(DETAIL_AS_MECHANISM, self.bullet,
                         "the plan's bullet still states the approved wording, which puts the path in the "
                         "detail; the prompt says the `file` argument")

    def test_the_bullet_records_the_departure_from_the_approved_text(self):
        # The plan's header says dated build notes record where the code departs from the approved text; a
        # silent rewrite of the bullet would hide that the sentence changed after approval.
        self.assertIn("As approved, the sentence put the path in the detail", self.bullet)
        self.assertIn("todo-file follow-on, 2026-09-07", self.bullet)
        self.assertIn("Decision 35 says the same", self.bullet,
                      "the bullet and the decision point at each other, so a reader of either finds the other")

    def test_decision_35_names_the_file_argument_and_points_at_a_bullet_that_agrees(self):
        decision = _decision(self.plan, 35)
        self.assertIn("`add_user_todo`'s `file` argument", decision)
        self.assertIn("See Getting into it", decision,
                      "decision 35 points the reader to Getting into it for the sentence")
        # The pointer lands on the one Getting into it bullet that describes the prompt's sentence, so that
        # bullet must say what the decision says.
        self.assertIn("`file` argument", self.bullet,
                      "decision 35's pointer lands on a bullet that does not name the `file` argument")

    def test_the_follow_on_note_says_the_prompt_passes_it(self):
        note = _paragraph(self.plan, NOTE_LEAD)
        self.assertIn("the session prompt says to pass it", note)

    def test_the_tests_section_names_this_module(self):
        tests = _flat(_section(self.plan, "## Tests"))
        self.assertIn("`%s`" % THIS_MODULE, tests,
                      "the plan's Tests section is the record of the plan's own tests; name this module there")
        self.assertTrue(os.path.exists(os.path.join(ROOT, THIS_MODULE)))


if __name__ == "__main__":
    unittest.main()
