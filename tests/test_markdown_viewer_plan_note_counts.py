#!/usr/bin/env python3
"""A build note of plans/markdown-viewer.md gives each test file one count: the number an item's parenthetical
states for a file is the number the note's tests-by-file list states for the same file.

The Slice 5 and Slice 8 notes describe a test file twice: inside the item whose rule the file holds, as
`name.test.ts (N, new: ...)` or `(N legs, new: ...)`, and in item 6's list that opens "Tests, by file", as
`name (N, new)`. The Slice 8 review's round 1 added a case to two files, updated the list's numbers and the items'
case descriptions, and left the items' numbers as they were (14 where the list said 15; 3 legs where the list
said 5), so the record contradicted itself and a reader could not tell which case was unaccounted for (the
review's round 2). This module reads every note that carries such a list and holds the two numbers to each
other, file by file.

The file's own test count is not read here: a note's numbers are the slice's snapshot, and a later slice that
adds a case to a file records the new count in its own note and leaves the earlier note as written (the Slice 5
note counts tools/file-comments-host-anchors.test.mjs at 14, the Slice 8 note at 15, one new). The premise
tests fail first if the notes' phrasing changes so that the reader finds nothing. Synthetic: the repo's own
text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
PLAN = os.path.join("plans", "markdown-viewer.md")

LIST_LEAD = "Tests, by file ("
LIST_END = "Every case that changes behaviour"
# A file named with its extension and a count: `anchor-map-cells.test.ts (15, new`, `styles-fc-hl-code-row-browser.test.ts
# (1 leg, new:`, `tests/test_file_comments_e2e.py (27, two new`, `anchor-map-wrappers.test.ts (38)`.
ITEM_COUNT = re.compile(r"((?:tools/|tests/)?[\w-]+\.(?:test\.(?:ts|mjs)|py)) \((\d+)(?: legs?)?[,)]")
# A list entry: the bare module name for ui/webview, the path for tools/ and tests/: `anchor-map-cells (15, new)`,
# `anchor-map-cells-browser (4 legs, new)`, `tools/file-comments-host-anchors.test.mjs (15, one new)`.
LIST_COUNT = re.compile(r"((?:tools/|tests/)?[\w-]+(?:\.test\.(?:ts|mjs)|\.py)?) \((\d+)(?: legs?)?[,)]")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse the plan's hard wraps so a reading survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _slice_sections(md):
    """Each `### Slice N` section's body, flattened, keyed by its slice name."""
    out = {}
    for m in re.finditer(r"^### (Slice \d+)[^\n]*\n(.*?)(?=^#{2,3} |\Z)", md, re.S | re.M):
        out[m.group(1)] = _flat(m.group(2))
    return out


def _path(name):
    """The repo path a note's mention names: a bare module name is a node test under ui/webview."""
    if name.startswith(("tools/", "tests/")):
        return name
    if name.endswith(".test.ts"):
        return "ui/webview/" + name
    return "ui/webview/" + name + ".test.ts"


def _counts(section):
    """(item counts, list counts) of one note: path -> [count, ...] from the items, path -> [count, ...] from the
    tests-by-file list; None when the note carries no list."""
    i = section.find(LIST_LEAD)
    if i < 0:
        return None
    j = section.find(LIST_END, i)
    assert j > i, "the tests-by-file list has no closing sentence"
    lst, items = section[i:j], section[:i] + section[j:]
    head_end = lst.find("): ")
    assert head_end > 0, "the tests-by-file list's opening parenthetical does not close"
    item_counts, list_counts = {}, {}
    for m in ITEM_COUNT.finditer(items):
        item_counts.setdefault(_path(m.group(1)), []).append(int(m.group(2)))
    for m in LIST_COUNT.finditer(lst[head_end:]):
        list_counts.setdefault(_path(m.group(1)), []).append(int(m.group(2)))
    return item_counts, list_counts


class NotesWithLists(unittest.TestCase):
    """The notes this module reads exist and say enough for the cross-check to mean something."""

    @classmethod
    def setUpClass(cls):
        cls.notes = {k: v for k, v in ((k, _counts(s)) for k, s in _slice_sections(_read(PLAN)).items()) if v}

    def test_the_slice_5_and_slice_8_notes_carry_a_tests_by_file_list(self):
        self.assertIn("Slice 5", self.notes)
        self.assertIn("Slice 8", self.notes)

    def test_each_list_names_at_least_twenty_files_and_the_items_count_at_least_ten_of_them(self):
        for name, (items, lst) in self.notes.items():
            self.assertGreaterEqual(len(lst), 20, "%s: the list reads %r" % (name, sorted(lst)))
            both = sorted(set(items) & set(lst))
            self.assertGreaterEqual(len(both), 10, "%s: the items count %r of the list's files" % (name, both))

    def test_the_slice_8_items_count_the_seven_new_files(self):
        items, lst = self.notes["Slice 8"]
        for f in ("anchor-map-cells", "anchor-map-cells-browser", "anchor-map-code-lines", "anchor-map-code-lines-browser",
                  "file-comments-block-paint", "md-config-math-block-paint-browser", "styles-fc-hl-code-row-browser"):
            self.assertIn(_path(f), items, "item text counts %s" % f)
            self.assertIn(_path(f), lst, "the list counts %s" % f)


class OneCountPerFile(unittest.TestCase):
    """Where a note counts a file in an item and in its list, the numbers agree, and the list names a file once."""

    @classmethod
    def setUpClass(cls):
        cls.notes = {k: v for k, v in ((k, _counts(s)) for k, s in _slice_sections(_read(PLAN)).items()) if v}

    def test_the_list_names_each_file_once(self):
        for name, (_items, lst) in self.notes.items():
            twice = {f: c for f, c in lst.items() if len(c) > 1}
            self.assertEqual(twice, {}, "%s: the tests-by-file list names a file more than once" % name)

    def test_an_items_count_for_a_file_is_the_lists_count(self):
        wrong = []
        for name, (items, lst) in self.notes.items():
            for f in sorted(set(items) & set(lst)):
                bad = [c for c in items[f] if c not in lst[f]]
                if bad:
                    wrong.append("%s: %s is counted %s in an item and %s in the tests-by-file list" % (name, f, bad, lst[f]))
        self.assertEqual(wrong, [], "\n".join(wrong))


if __name__ == "__main__":
    unittest.main()
