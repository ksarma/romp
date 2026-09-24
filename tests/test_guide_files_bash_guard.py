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
import json
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

SENTENCE = ("A session that tries to write a tracked file any other way, with its editing tools or a shell command "
            "such as `cp`, `tee`, `sed -i` or a `>` redirection, is refused and pointed at its track-edit command, "
            "so its edits still come to you as changes.")
# The sentence after it, since the round-1 review of the non-literal-target rule (2026-09-18): a shell write whose
# target the hook cannot read is refused in a tracking project too, and the guide says so where the rule above is
# stated, in the same voice (the behavior, not the mechanism). Round 5 of that review (2026-09-20) re-pointed it: the
# class the code refuses is a target the guard cannot READ (docs/install.md's wording), not any variable, since the
# hook resolves a name the command sets to a plain string and judges the real path (B2, 2026-09-19); the old sentence
# was pinned here verbatim, a test holding a false user-facing claim in place.
SENTENCE_2 = ("In a project that tracks files, a shell write whose target Romp cannot read (a substitution, a name the "
              "command never sets to a plain string, or a glob it cannot expand) is refused too, and the session is asked "
              "for the literal path.")
# The sentence after those two, since round 7 of fork PR #780's review (the reviewer's regression-2 with extra7-3): round 6 had put
# the hook header's whole residual paragraph into the guide under a heading of its own, the mechanism's words and the review's
# provenance included, against the guide's voice (the behaviour, not the mechanism). The paragraph and its heading left the guide;
# this one sentence, in the same voice, points the reader at docs/install.md, where the full statement stands under the installer's
# section on what it links into ~/.claude/. It stays clear of the two words CONTEXT.md avoids for the comments log.
POINTER = ("What a shell command can still do to a tracked file is set out in full in [Install](install.md), under what "
           "the installer links into `~/.claude/`.")
# the words a user-facing sentence here never carries: the mechanism (the first five) and the review's provenance (the last three)
BARRED = ("hook", "PreToolUse", "matcher", "ROMP_SID", "guard", "round", "commit", "as ruled")


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

    def test_the_non_literal_sentence_follows_it_and_the_hook_refuses_that_way(self):
        # the second sentence sits right after the first, so a reader of the rule finds the refusal it describes
        self.assertIn(SENTENCE + " " + SENTENCE_2, self.files)
        self.assertIn("which is not a literal path", self.hook)
        self.assertIn("Spell the path out", self.hook)

    def test_the_pointer_follows_them_and_install_md_carries_the_statement_it_points_at(self):
        # the pointer sits right after the two sentences, and the section it names in docs/install.md holds the full statement
        self.assertIn(SENTENCE + " " + SENTENCE_2 + " " + POINTER, self.files)
        install = _section(_read("docs", "install.md"), "What the installer links into `~/.claude/`")
        self.assertIn("THE RESIDUAL PROPERTY. The guard refuses a write only when", install)
        self.assertIn("A shape outside these classes that reaches a tracked file is a rule to state, not a residual.", _flat(install))

    def test_the_guide_carries_no_copy_of_the_developer_paragraph(self):
        # round 6's heading and its verbatim paragraph are gone from the whole guide, not moved inside another section
        guide = _read("docs", "guide.md")
        self.assertNotIn("### The write guard on tracked files", guide)
        for text in ("residual property", "THE RESIDUAL PROPERTY", "extract's switch", "RESIDUAL TABLE", "B2 as ruled",
                     "stated since the first commit of this round"):
            self.assertNotIn(text.lower(), guide.lower(), "the guide carries %r" % text)

    def test_each_shell_form_named_is_one_the_hook_reads(self):
        for verb in ("cp", "tee"):
            self.assertIn("case '%s'" % verb, self.hook, "the hook reads %s" % verb)
        self.assertIn("case 'sed':", self.hook)
        self.assertIn("function sedTargets(args)", self.hook)
        self.assertRegex(self.hook, r"const WRITE_REDIRECTS = new Set\(\['>'", "the > redirection is a write target")

    def test_the_remedy_named_is_the_one_the_hook_writes(self):
        self.assertIn("Make the change with track-edit", self.hook)
        self.assertIn("node ~/.claude/hooks/track-edit.mjs --file", self.hook)

    def test_the_class_the_sentence_names_is_the_behaviour(self):
        """The hook as a process on a synthetic project: a name the command sets to a plain string is read and judged by
        the path it resolves to (refused onto a tracked file, allowed onto an untracked one), and a target it cannot
        read (a variable the command never sets) is refused: the class SENTENCE_2 states, run rather than quoted."""
        env = dict(os.environ, ROMP_SID="11111111-2222-3333-4444-555555555555")
        with tempfile.TemporaryDirectory(prefix="romp-guide-bash-guard-") as root:
            proj = os.path.realpath(os.path.join(root, "notes-api"))
            for d in (".trackchanges", "docs", "base"):
                os.makedirs(os.path.join(proj, d))
            with open(os.path.join(proj, ".trackchanges", "config.json"), "w", encoding="utf-8") as f:
                json.dump({"v": 2, "tracked": ["docs/report.md"]}, f)
            for rel, text in (("docs/report.md", "tracked\n"), ("base/report.md", "base\n"), ("docs/other.md", "plain\n")):
                with open(os.path.join(proj, rel), "w", encoding="utf-8") as f:
                    f.write(text)

            def verdict(command):
                payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": proj})
                r = subprocess.run(["node", os.path.join(ROOT, "hooks", "romp-track-bash-guard.mjs")], input=payload,
                                   capture_output=True, text=True, env=env, timeout=60)
                return r.returncode, r.stderr

            rc, why = verdict("x=docs/report.md; cp base/report.md $x")
            self.assertEqual(rc, 2, "a readable name resolving onto the tracked file is refused: %s" % why)
            self.assertIn("Track-changes is ON for", why)
            rc, why = verdict("x=other.md; cp base/report.md docs/$x")
            self.assertEqual(rc, 0, "a readable name resolving onto an untracked file is allowed: %s" % why)
            rc, why = verdict('cp base/report.md "$DST"')
            self.assertEqual(rc, 2, "a target the guard cannot read is refused: %s" % why)
            self.assertIn("which is not a literal path", why)
            self.assertIn("Spell the path out", why)

    def test_the_sentence_speaks_to_the_person_and_names_no_hook(self):
        # the guide describes the behavior, not the mechanism, and not the review that shaped it: no hook, guard, matcher or
        # PreToolUse, and no round, commit or ruling (matched at a word's start, case aside, so "hooks" and "Commits" count too);
        # the pointer is held to the same words, and to the two CONTEXT.md avoids in the Files section
        for sentence in (SENTENCE, SENTENCE_2, POINTER):
            for word in BARRED:
                self.assertNotRegex(sentence, re.compile(r"\b" + re.escape(word), re.I), "%r in %r" % (word, sentence))
            self.assertNotIn("\u2014", sentence)
        for word in ("history", "ledger"):
            self.assertNotRegex(POINTER, re.compile(r"\b" + word, re.I))


if __name__ == "__main__":
    unittest.main()
