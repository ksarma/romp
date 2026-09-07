#!/usr/bin/env python3
"""The plan's follow-on note says what a Rendered point's white-space is, and its Tests section names the
follow-on's tests.

Two review findings on the inline-display follow-on (plans/file-review.md, 2026-09-07). First, the note under
Slice 2's build record ended by saying the point's label takes the block's font and white-space, unqualified.
The round-1 fix added `renderedPointStyles` (`anchor-map.ts`), which puts `white-space: pre-wrap` on a point
whose label has no visible character, so a removed space keeps its width instead of collapsing to a 0px point
under the block's normal white-space; the sentence was left stating the behaviour the code deliberately does
not have. Second, the Tests section, which `ui/webview/file-review-docs.test.ts` holds to the tree (every test
file it names exists), named none of the follow-on's test files, so the record the next implementer reads did
not know they existed, and deleting one left the docs test green.

The white-space premise is read from the painter's source rather than hard-coded: if `renderedPointStyles`
goes, the premise test fails first and the passage test names what must change with it. The Tests pin is held
to the tree, not to a list: every test file whose header says it belongs to the follow-on must be named, so a
tenth suite added later is caught the same way. Synthetic: the repo's own text only.
"""
import glob
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

FOLLOW_ON = "inline-display follow-on"
NOTE_LEAD = "The inline-display follow-on (2026-09-07):"
BULLET_LEAD = "- The inline-display follow-on (2026-09-07)"


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse the plan's hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(md, lead):
    """The blank-line paragraph that starts with `lead`, collapsed."""
    for p in re.split(r"\n\s*\n", md):
        if p.lstrip().startswith(lead):
            return _flat(p)
    raise AssertionError("no paragraph of the plan starts with %r" % lead)


def _section(md, heading):
    """The body of one `## heading` up to the next heading of level two."""
    m = re.search(r"^## " + re.escape(heading) + r"\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _bullets(section):
    """The section's list bullets, each joined across its wrapped lines (the docs test's split)."""
    return [_flat(b) for b in re.split(r"\n(?=- )", section) if b.strip().startswith("- ")]


def _test_files(text):
    """The test files a run of prose names in backticks, as `file-review-docs.test.ts` reads them: a bare
    `*.test.ts` is a webview test, anything else a repo path."""
    names = re.findall(r"`([^`\s]+\.(?:test\.ts|py|bats))`", text)
    return [n if "/" in n else "ui/webview/" + n for n in names]


def _header(path, lines=25):
    with open(path, encoding="utf-8") as f:
        return "".join(f.readline() for _ in range(lines))


class TheRenderedPointCarriesTheRowsWhiteSpace(unittest.TestCase):
    """The premise, read from `anchor-map.ts`: a whitespace-only label gets `white-space: pre-wrap` inline, on both
    Rendered points, and the sheets carry no such rule."""

    def setUp(self):
        self.anchor = _read("ui", "webview", "anchor-map.ts")

    def _has(self, pattern, why):
        # assertTrue over assertRegex: a miss must not print the whole source file
        self.assertTrue(re.search(pattern, self.anchor, re.M), "anchor-map.ts lacks %r: %s" % (pattern, why))

    def test_rendered_point_styles_adds_pre_wrap_to_a_label_with_no_visible_character(self):
        self._has(r"^function renderedPointStyles\(label: string, styles: Record<string, string>\)[^\n]*\{\s*"
                  r'return /\\S/\.test\(label\) \? styles : \{ \.\.\.styles, "white-space": "pre-wrap" \};',
                  "the follow-on note says a label of spaces or tabs alone carries the Raw rows' white-space inline")

    def test_both_rendered_points_take_those_styles(self):
        self._has(r'paintRenderedPoint\(renderedRoot, source, c\.curFrom, "fc-del", data, label, renderedPointStyles\(label,',
                  "a deletion's point must carry renderedPointStyles")
        self._has(r'makePoint\(first\.ownerDocument, "fc-del", data, label, renderedPointStyles\(label, styles\)\)',
                  "a substitution's point must carry renderedPointStyles")

    def test_the_sheets_gained_no_rule(self):
        # the note's first clause: the white-space lives on the point, so no `.fc-del` rule declares it
        for sheet in ("styles.css", "feed.css"):
            rules = re.findall(r"^\s*\.fc-del[^{]*\{[^}]*\}", _read("ui", "webview", sheet), re.M)
            self.assertTrue(rules, "%s has no .fc-del rule" % sheet)
            for r in rules:
                self.assertNotIn("white-space", r, "%s declares white-space on the point; the plan says the sheets gained no rule" % sheet)


class TheFollowOnNoteMatchesThePainter(unittest.TestCase):
    """The note under Slice 2's build record states the narrow white-space rule and no longer the unqualified one."""

    def setUp(self):
        self.note = _paragraph(_read("plans", "file-review.md"), NOTE_LEAD)

    def test_the_white_space_clause_names_the_rule_and_its_source(self):
        self.assertIn("Its white-space is the block's when the label has a visible character", self.note)
        self.assertIn("label of spaces or tabs alone (a removed space beside one that stayed, a substitution of whitespace)", self.note)
        self.assertIn("carries the Raw rows' `white-space: pre-wrap` as an inline style (`renderedPointStyles` in "
                      "`anchor-map.ts`)", self.note)

    def test_the_unqualified_claim_is_gone(self):
        # The finding: "the label takes the block's font and white-space", which for a whitespace-only label is
        # the 0px collapse the round-1 fix removed.
        self.assertNotIn("font and white-space", self.note)

    def test_the_sheets_clause_stands(self):
        self.assertIn("The sheets gained no rule", self.note)


class TheTestsSectionNamesTheFollowOnsTests(unittest.TestCase):
    """One bullet of the Tests section names the follow-on's test files, every named file exists, and every test
    file that says it belongs to the follow-on is named."""

    def setUp(self):
        self.tests = _section(_read("plans", "file-review.md"), "Tests")
        bullets = [b for b in _bullets(self.tests) if b.startswith(BULLET_LEAD)]
        self.assertEqual(len(bullets), 1, "exactly one Tests bullet is the follow-on's")
        self.named = _test_files(bullets[0])

    def test_the_bullet_names_the_suites_the_follow_on_added_or_rewrote(self):
        for rel in ("ui/webview/anchor-map.test.ts",
                    "ui/webview/anchor-map-rendered-points.test.ts",
                    "ui/webview/anchor-map-whitespace-point-browser.test.ts",
                    "ui/webview/file-comments-changes-review.test.ts",
                    "ui/webview/file-comments-inline-toggle.test.ts",
                    "ui/webview/file-comments-inline-review.test.ts",
                    "ui/webview/file-comments-reveal-title.test.ts",
                    "ui/webview/file-comments-rendered-point-browser.test.ts",
                    "tests/test_file_review_plan_rendered_deletions.py",
                    "tests/test_file_review_plan_inline_display.py"):
            self.assertIn(rel, self.named, "the Tests section's follow-on bullet does not name %s" % rel)

    def test_every_named_file_exists(self):
        # the docs test's own check, so a run of this suite alone catches a rename too
        for rel in self.named:
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)),
                            "the Tests section names %s, which does not exist; name the file the tests are in" % rel)

    def test_every_test_file_that_claims_the_follow_on_is_named(self):
        # held to the tree: a suite whose header says it is the follow-on's must be in the section's record
        claimants = []
        for pattern in ("ui/webview/*.test.ts", "tests/test_*.py", "tools/*.test.mjs"):
            for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
                if FOLLOW_ON in _header(path):
                    claimants.append(os.path.relpath(path, ROOT))
        self.assertIn("ui/webview/file-comments-inline-toggle.test.ts", claimants, "the header scan finds nothing; widen it")
        unnamed = [c for c in claimants if c not in _test_files(self.tests)]
        self.assertEqual(unnamed, [], "test files whose header names the follow-on but the Tests section does not: %r" % unnamed)


if __name__ == "__main__":
    unittest.main()
