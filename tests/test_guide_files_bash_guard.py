#!/usr/bin/env python3
"""The guide's Track changes paragraph says a session's write to a tracked file is refused whichever way it
is made, and the shell forms it names are the ones the Bash-side guard reads.

Before this slice the guide implied the tracked-changes loop was complete once tracking was on: a session's
edits came back as changes. A session in auto mode writes files through Bash (cp, tee, a heredoc, sed -i),
which the vendored guard never sees; a dry run saw one copy over a tracked file that way (2026-09-09;
plans/file-review.md decision 47). The guide now says, in one sentence, that a session writing a tracked
file any other way, with its editing tools or a shell command, is refused and pointed at track-edit, so its
edits still come as changes. Each shell form the sentence names is checked against the hook's grammar
(hooks/romp-track-bash-guard.mjs), and the remedy it names against the refusal the hook writes, so a
verb the hook stops reading or a renamed remedy fails here. Synthetic: the repo's own text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

SENTENCE = ("A session that tries to write a tracked file any other way, with its editing tools or a shell command "
            "such as `cp`, `tee`, `sed -i` or a `>` redirection, is refused and pointed at its track-edit command, "
            "so its edits still come to you as changes.")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _section(md, heading):
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


class TrackChangesParagraphNamesTheRefusal(unittest.TestCase):
    def setUp(self):
        self.files = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.hook = _read("hooks", "romp-track-bash-guard.mjs")

    def test_the_sentence_follows_the_figures_sentence(self):
        # after the sentence on figures (a tracked folder may hold them), which is the other thing the guards let by
        self.assertIn("so a tracked folder may hold figures. " + SENTENCE, self.files)

    def test_each_shell_form_named_is_one_the_hook_reads(self):
        for verb in ("cp", "tee"):
            self.assertIn("case '%s'" % verb, self.hook, "the hook reads %s" % verb)
        self.assertIn("case 'sed':", self.hook)
        self.assertIn("function sedTargets(args)", self.hook)
        self.assertRegex(self.hook, r"const WRITE_REDIRECTS = new Set\(\['>'", "the > redirection is a write target")

    def test_the_remedy_named_is_the_one_the_hook_writes(self):
        self.assertIn("Make the change with track-edit", self.hook)
        self.assertIn("node ~/.claude/hooks/track-edit.mjs --file", self.hook)

    def test_the_sentence_speaks_to_the_person_and_names_no_hook(self):
        # the guide describes the behavior, not the mechanism: no hook, guard, matcher or PreToolUse
        for word in ("hook", "PreToolUse", "matcher", "ROMP_SID", "guard"):
            self.assertNotIn(word, SENTENCE)
        self.assertNotIn("\u2014", SENTENCE)


if __name__ == "__main__":
    unittest.main()
