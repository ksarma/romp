#!/usr/bin/env python3
"""Sessions are asked to commit the `.trackchanges/` folder with their work; the host still runs no git
command. The guide, the plan's decision 25, the session prompt and the vendored skill say the same thing.

The owner found that his sessions never added `.trackchanges/` to git, so the comments on their files
and the record of their tracked changes were not archived with the work (2026-09-10; plans/file-review.md
decision 48). Decision 25 stands: romp writes the sidecar and the comments log and does no git operation,
and a `.gitignore` line is the opt-out. The norm is added on the session side, in two places a session
reads (the vendored skill, patch 0007; claude/romp-session-prompt.md, one sentence in the person's
voice), and stated in two places the person reads (the guide's Files section; decision 25's note).

This module holds the four to one another: the two session-facing texts carry the same rule in the
same words (the condition, the folder, the ask); the two person-facing texts say sessions are asked,
that the person's own commits stay theirs, and that nothing on the host stages or commits; and the
guide's opt-out sentence, which tests/test_guide_files_comments_log.py pins, still stands before the
new one. Every premise is read from the files. Synthetic: the repo's own text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

RULE = "when you commit work in a project that has a `.trackchanges/` folder and does not ignore it, include that folder in the commit"
OPT_OUT = "Whether `.trackchanges/` is committed is the project's call; a `.gitignore` line keeps it out."
GUIDE_SENTENCE = ("Sessions are asked to include the folder when they commit their own work, so the comments and the "
                  "changes are kept with it; your commits are yours, and nothing here stages or commits anything.")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _section(md, heading):
    """The body of one `### heading` up to the next heading of any level."""
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _decision(md, n):
    """Numbered decision `n` of the plan's Decisions section, joined across its wrapped lines and collapsed."""
    m = re.search(r"(?m)^## Decisions[^\n]*\n", md)
    assert m, "the Decisions heading"
    decisions = md[m.end():]
    end = re.search(r"\n#{1,4} ", decisions)
    decisions = decisions[: end.start()] if end else decisions
    m = re.search(r"(?:^|\n)%d\. .*?(?=\n\d+\. |\n\s*\n|\Z)" % n, decisions, re.S)
    assert m, "decision %d not found" % n
    return _flat(m.group(0))


class SessionFacingTextsCarryTheRule(unittest.TestCase):
    """The prompt and the skill ask the same thing in the same words; each says why in its own voice."""

    def setUp(self):
        self.prompt = _read("claude", "romp-session-prompt.md")
        self.skill = _flat(_read("vendor", "track-changents", "skill", "SKILL.md"))

    def test_the_prompt_has_the_rule_in_working_style_in_the_persons_voice(self):
        working, housekeeping = self.prompt.split("# Housekeeping", 1)
        flat = _flat(working)
        self.assertIn(RULE, flat.lower())
        self.assertIn("it holds my comments on your files and the record of your tracked changes", flat)
        self.assertNotIn(".trackchanges", housekeeping, "Housekeeping explains romp's artifacts only")

    def test_the_skill_has_the_rule_in_its_notes(self):
        notes = self.skill[self.skill.index("## Notes"):]
        self.assertIn(RULE, notes.lower())
        self.assertIn("it holds the user's comments on your files and the record of your tracked changes", notes)

    def test_neither_names_the_machinery(self):
        working = _flat(self.prompt.split("# Housekeeping", 1)[0]).lower()
        for word in ("sidecar", "comments log", "card", "board", "goal", "romp"):
            self.assertNotIn(word, working, "%r names machinery the agent cannot see" % word)
        # the skill may name its own sidecar elsewhere; the rule's sentence itself does not
        i = self.skill.lower().index(RULE)
        sentence = self.skill[i: self.skill.index(".", i + len(RULE)) + 1]
        for word in ("sidecar", "log", "romp", "card", "board"):
            self.assertNotIn(word, sentence.lower(), "the rule's sentence names %r" % word)


class PersonFacingTextsStateTheNorm(unittest.TestCase):
    """The guide and decision 25 say sessions are asked, the person's commits stay theirs, no host git."""

    def setUp(self):
        self.files = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.plan = _read("plans", "file-review.md")

    def test_the_guide_keeps_the_opt_out_and_adds_the_norm_after_it(self):
        self.assertIn(OPT_OUT + " " + GUIDE_SENTENCE, self.files,
                      "the opt-out sentence stands as pinned, and the norm follows it in one sentence")

    def test_decision_25_stands_and_records_the_norm(self):
        d25 = _decision(self.plan, 25)
        self.assertIn("**Committing is the project's call.**", d25)
        self.assertIn("does no git operation", d25, "the ruling is unchanged")
        self.assertIn("a `.gitignore` line is the opt-out", d25)
        self.assertIn("(2026-09-10: sessions are asked by the skill and the session prompt to include the folder when "
                      "they commit their work", d25)
        self.assertIn("the person's own commits staying theirs", d25)
        self.assertIn("romp still running no git command", d25)
        self.assertIn("decision 48", d25, "points at the record of the owner's finding")


if __name__ == "__main__":
    unittest.main()
