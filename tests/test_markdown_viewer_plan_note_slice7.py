#!/usr/bin/env python3
"""The Slice 7 build note of plans/markdown-viewer.md holds to four rules its review rounds corrected it against.

The note is the record of the branch: its head maps the pre-rebase shas and explains which counts moved between the
cut point and the base, its items count each test file, its tests-by-file list counts every file once, and a
paragraph per review round records what the round fixed and what it corrected. Three rounds found the same classes of
record defect: a round paragraph describing the review by the roles of those who ran it, where this file's other
notes describe a round by its rule, its fixes and its routings (round 2 stripped the words, and its own paragraph
reintroduced one in the plural the check had not matched); a count in the head left at the base's number after a
later round added a case, against the list's; a `git range-diff` command whose right-hand range ended at `HEAD`, a
moving reference that stopped pairing commit for commit at the first review commit; and an item's count of a file's
cases by stage (new in the build, in the review's round 1, in its round 2) one short of the list's for the same file.
This module reads the Slice 7 section and holds each of the four (the review's round 3).

The words held out of the note are the nouns the review's plan uses for its readers and its hands, and the verb forms
of the one who directs a round; "seed" is not among them, since the editor's seed, a seeded comment and the seeded
fuzz use the word in its own sense throughout the note, and neither is "coordinate", the BOM items' word for the
offsets' frame. The counts are held to each other within the note, not to the files, as
tests/test_markdown_viewer_plan_note_counts.py does: a later slice's additions leave an earlier note as written. The
premise test fails first if the note's phrasing changes so that a reader finds nothing. Synthetic: the repo's own text
only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
PLAN = os.path.join("plans", "markdown-viewer.md")
NOTE = "Slice 7"

LIST_LEAD = "Tests, by file ("
LIST_END = "Every case that changes behaviour"
# The words the review's plan uses for those who run a round, in every number, and the verb forms of the one who
# directs it; not "coordinate", the word the BOM items use for the offsets' frame.
PROCESS_WORDS = re.compile(r"\b(finders?|refuters?|fixers?|lens|lenses|coordinators?|coordinating|coordinated|"
                           r"consolidation agents?)\b", re.I)
SHA = r"(?=[0-9a-f]*\d)[0-9a-f]{7,40}"  # a short sha; at least one digit, so a word spelt in a to f is not one
# `git range-diff e6aeb1138..9d0c719a0 462ad3ccf..103a13f32`: two ranges, four ends
RANGE_DIFF = re.compile(r"git range-diff ([^\s`]+)\.\.([^\s`]+) ([^\s`]+)\.\.([^\s`]+)")
# The head's account of a count that moved between the cut point and the base: `file-view-reload.test.ts 23 where
# the cut point had 20`, `file-view-outline.test.ts 15 where it had 14`
HEAD_COUNT = re.compile(r"((?:tests/)?[\w-]+\.(?:test\.ts|py)) (\d+) where (?:the cut point|it) had (\d+)")
# A file counted by stage, in an item (`file-view-seam.test.ts (55, ten new in the build, three in the review's
# round 1 and three in its round 2, below:`) or in the list (`file-view-seam (55, ten new in the build, three in the
# review's round 1, three in its round 2)`); a clause may stand between the round 1 count and the conjunction
STAGES = re.compile(r"((?:tests/)?[\w-]+(?:\.test\.ts|\.py)?) \((\d+), (\w+) new in the build, (\w+) in the review's "
                    r"round 1[^,]*?(?:,| and) (\w+) in its round 2")
# The list's entries: `file-view-reload (23, five scenes extended`, `tests/test_kernel_preview.py (31, two record pins)`
LIST_COUNT = re.compile(r"((?:tools/|tests/)?[\w-]+(?:\.test\.(?:ts|mjs)|\.py)?) \((\d+)(?: legs?)?[,)]")
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse the plan's hard wraps so a reading survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _section(md, name):
    """The `### <name>` section's body, flattened."""
    m = re.search(r"^### %s[^\n]*\n(.*?)(?=^#{2,3} |\Z)" % re.escape(name), md, re.S | re.M)
    assert m, "the plan has no %s section" % name
    return _flat(m.group(1))


def _path(name):
    """The repo path a note's mention names: a bare module name is a node test under ui/webview."""
    if name.startswith(("tools/", "tests/")):
        return name
    if name.endswith(".test.ts"):
        return "ui/webview/" + name
    return "ui/webview/" + name + ".test.ts"


def _number(word):
    return int(word) if word.isdigit() else WORDS[word]


def _split(section):
    """(the text outside the tests-by-file list, the list's entries) of one note."""
    i = section.find(LIST_LEAD)
    assert i >= 0, "the note has no tests-by-file list"
    j = section.find(LIST_END, i)
    assert j > i, "the tests-by-file list has no closing sentence"
    lst = section[i:j]
    head_end = lst.find("): ")
    assert head_end > 0, "the tests-by-file list's opening parenthetical does not close"
    return section[:i] + section[j:], lst[head_end:]


def _list_counts(lst):
    return {_path(m.group(1)): int(m.group(2)) for m in LIST_COUNT.finditer(lst)}


def _stages(text):
    """path -> (count, new in the build, in round 1, in round 2) for each file the text counts by stage."""
    return {_path(m.group(1)): (int(m.group(2)), _number(m.group(3)), _number(m.group(4)), _number(m.group(5)))
            for m in STAGES.finditer(text)}


def _context(text, m, width=40):
    return text[max(0, m.start() - width):m.end() + width]


class TheNoteSaysEnough(unittest.TestCase):
    """The premise: the readers below find what they read, so a green run means the rules held and not that the
    phrasing moved out from under them."""

    def test_the_note_carries_the_sentences_the_module_reads(self):
        section = _section(_read(PLAN), NOTE)
        outside, lst = _split(section)
        self.assertGreaterEqual(len(_list_counts(lst)), 20, "the list names its files with a count each")
        self.assertGreaterEqual(len(RANGE_DIFF.findall(section)), 1, "the head gives a range-diff command to run")
        self.assertGreaterEqual(len(HEAD_COUNT.findall(outside)), 3,
                                "the head explains the counts that moved between the cut point and the base")
        both = set(_stages(outside)) & set(_stages(lst))
        self.assertIn(_path("file-view-seam"), both, "an item and the list both count the seam suite by stage")


class TheNoteHoldsToItsRules(unittest.TestCase):
    """Each rule a review round corrected the note against, read over the whole Slice 7 section."""

    @classmethod
    def setUpClass(cls):
        cls.section = _section(_read(PLAN), NOTE)
        cls.outside, cls.lst = _split(cls.section)
        cls.list_counts = _list_counts(cls.lst)

    def test_no_paragraph_describes_the_review_by_the_roles_of_those_who_ran_it(self):
        hits = ["%r at %r" % (m.group(0), _context(self.section, m)) for m in PROCESS_WORDS.finditer(self.section)]
        self.assertEqual(hits, [], "the note describes a round by its rule, its fixes and its routings:\n" + "\n".join(hits))

    def test_a_count_the_head_gives_beside_the_cut_points_is_the_lists(self):
        wrong = []
        for m in HEAD_COUNT.finditer(self.outside):
            path, on_branch = _path(m.group(1)), int(m.group(2))
            self.assertIn(path, self.list_counts, "the list counts %s" % path)
            if self.list_counts[path] != on_branch:
                wrong.append("%s: the head says %d on the branch, the list %d" % (path, on_branch, self.list_counts[path]))
        self.assertEqual(wrong, [], "\n".join(wrong))

    def test_a_range_diff_command_the_note_gives_names_four_fixed_commits(self):
        for m in RANGE_DIFF.finditer(self.section):
            for end in m.groups():
                self.assertRegex(end, r"^%s$" % SHA,
                                 "%r: a range a reader is told to run ends at a commit, never at HEAD or a branch"
                                 % m.group(0))

    def test_an_items_count_of_a_file_by_stage_is_the_lists(self):
        items, lst = _stages(self.outside), _stages(self.lst)
        wrong = ["%s: an item counts %r by stage, the list %r" % (f, items[f], lst[f])
                 for f in sorted(set(items) & set(lst)) if items[f] != lst[f]]
        self.assertEqual(wrong, [], "\n".join(wrong))


if __name__ == "__main__":
    unittest.main()
