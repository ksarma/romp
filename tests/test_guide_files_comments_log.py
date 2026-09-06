#!/usr/bin/env python3
"""The guide's Files section describes the Log as holding every kind of entry the comments log takes,
decisions included, in the panel's own terms.

Slice 2 made the host script append an `accept` and a `reject` entry to the comments log (each with the
changes it decided, old and new text), and the panel renders those as "Accepted N changes" /
"Rejected N changes" rows that open to the text. The guide's Log sentence still listed the Slice 1
kinds only: sends, tracking toggles, direct edits (review finding, 2026-09-06). CONTEXT.md's Comments
log entry names decisions as part of the record, and a reader deciding whether to commit
`.trackchanges/` was not told the decisions are part of what git would keep.

The test derives the entry kinds from the host script's `logEntry(kind, ...)` calls rather than
hard-coding them, so a new kind the guide does not name fails here. Every phrase the guide uses is
cross-checked against the panel source that renders the same thing, so a renamed row or a changed
fold fails here too. Synthetic: no session data, only the repo's own text.
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


def _avoid_words(context_md, term):
    """The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    avoid = re.search(r"^_Avoid_:(.*)$", m.group(1), re.M)
    assert avoid, "CONTEXT.md entry %r has no _Avoid_ line" % term
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [w.strip() for w in bare.split(",") if w.strip()]


def _log_kinds(host_mjs):
    """Every `kind` the host script appends to the comments log."""
    return sorted(set(re.findall(r"logEntry\('([\w-]+)'", host_mjs)))


# The guide's words for each kind of entry. A kind with no row here is one the guide does not describe.
GUIDE_PHRASE = {
    "send": "what was sent and when",
    "accept": "the changes you accepted or rejected",
    "reject": "the changes you accepted or rejected",
    "set-tracked": "tracking turned on or off",
    "edit": "your direct edits to the file",
}


class LogSentenceCoversEveryEntryKind(unittest.TestCase):
    """The sentence after 'The **Log** at the foot of the panel' names each kind the host script writes."""

    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.kinds = _log_kinds(_read("tools", "file-comments-host.mjs"))

    def test_the_host_script_writes_the_kinds_this_test_knows(self):
        # The premise, read from its source. A new kind lands here first; add its phrase to GUIDE_PHRASE
        # and to the guide's Log sentence together.
        self.assertEqual(self.kinds, ["accept", "edit", "reject", "send", "set-tracked"])
        for k in self.kinds:
            self.assertIn(k, GUIDE_PHRASE, "the host script writes a %r entry the guide's Log sentence does not name" % k)

    def test_the_log_sentence_names_every_kind(self):
        head = "The **Log** at the foot of the panel is the comments log: "
        self.assertIn(head, self.section)
        sentence = self.section[self.section.index(head):]
        sentence = sentence[:sentence.index(". ") + 1]
        for k in self.kinds:
            self.assertIn(GUIDE_PHRASE[k], sentence, "Log sentence lacks the %r entry" % k)

    def test_the_slice_1_sentence_is_gone(self):
        # The finding: sends, toggles and edits with no decision word between them.
        self.assertNotIn("what was sent and when, tracking turned on or off", self.section)

    def test_the_log_keeps_the_decision_and_is_in_the_folder_git_keeps(self):
        # The reader weighing whether to commit `.trackchanges/` learns from one sentence that the log, decisions
        # listed, is in that folder; the accept sentence's "drops the record" then reads as the card, not the decision.
        self.assertIn("Once a change is decided, its card is gone and the Log keeps the decision", self.section)
        self.assertIn("kept beside the comments in the same folder so git keeps it when the project does. Once a change",
                      self.section)
        self.assertIn("Whether `.trackchanges/` is committed is the project's call; a `.gitignore` line keeps it out.",
                      self.section)


class LogSentenceMatchesThePanel(unittest.TestCase):
    """Each thing the guide says the Log shows is rendered by the panel source it describes."""

    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.model = _read("ui", "webview", "file-comments-model.ts")
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.host = _read("tools", "file-comments-host.mjs")

    def test_the_row_counts_decided_changes(self):
        self.assertIn("the Log keeps the decision: the row gives the count", self.section)
        self.assertRegex(self.model, r'\(k === "accept" \? "Accepted " : "Rejected "\) \+ plural\(n, "change", "changes"\)')

    def test_the_row_opens_to_each_change_s_old_and_new_text(self):
        self.assertIn("clicking it shows the old and new text of each change", self.section)
        # the fold: an accept or reject entry's detail is one diff per change it decided
        self.assertRegex(self.panel, r'if \(\(e\.kind === "accept" \|\| e\.kind === "reject"\) && Array\.isArray\(e\.changes\)')
        self.assertIn('typeof ch.oldText === "string"', self.panel)
        self.assertIn('typeof ch.newText === "string"', self.panel)
        self.assertIn('"Show the changes"', self.panel)
        # ...and the host writes that text into the entry, so the row has it after the sidecar forgets the change
        self.assertIn("logEntry('accept', { changes: changesOf(decided) })", self.host)
        self.assertIn("logEntry('reject', { changes: changesOf(decided) })", self.host)

    def test_the_panel_s_own_empty_state_lists_the_same_kinds(self):
        self.assertIn("Nothing yet: sends, decisions, tracking changes, and direct edits land here.", self.panel)


class LogVocabulary(unittest.TestCase):
    """The section uses CONTEXT.md's term for the log and none of the words it says to avoid."""

    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.context = _read("CONTEXT.md")
        self.avoid = _avoid_words(self.context, "Comments log")

    def test_context_md_names_decisions_as_part_of_the_record(self):
        # The premise: the guide follows CONTEXT.md, which defines the comments log as holding the decisions.
        self.assertIn("what the\nperson accepted or rejected", self.context)
        self.assertIn("history", self.avoid)
        self.assertIn("ledger", self.avoid)

    def test_the_section_uses_the_term(self):
        self.assertIn("is the comments log:", self.section)

    def test_the_section_uses_no_avoid_word(self):
        # "log alone" is CONTEXT.md's gloss, not a word: the section names the panel's **Log** label and
        # then says what it is, which is the point of the entry. The two real words are checked.
        for word in self.avoid:
            if word == "log alone":
                continue
            self.assertNotRegex(self.section, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                "the Files section says %r; CONTEXT.md avoids it" % word)


if __name__ == "__main__":
    unittest.main()
