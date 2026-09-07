#!/usr/bin/env python3
"""The plan's follow-on note states the boundary rule the painter has, and its Tests section names the suite
that pins it.

The round-2 fix of the inline-display follow-on (plans/file-review.md, 2026-09-07) taught `anchor-map.ts` where
a change's point goes at the edge of a painter's own mark (`insertBeforeNode`, `insertAfterText`) and added
`anchor-map-boundary-points.test.ts`, whose header names the follow-on. The same commit left the plan without
either: the note said only that a substitution's point sits immediately before its tint, and the Tests bullet,
which `tests/test_file_review_plan_inline_display.py` holds to every test file whose header names the
follow-on, did not name the suite, so the branch's own pytest was red and the record the next implementer
reads did not know the rule or its suite existed (review finding, 2026-09-07).

The premise is read from the painter's source: if the boundary helpers go, or the placements stop using them,
the premise tests fail first and the passage tests name what must change with them. The bullet's account of
the suite is held to the suite's own test titles, so a behaviour the bullet credits to the suite is one the
suite has a test for. Synthetic: the repo's own text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

FOLLOW_ON = "inline-display follow-on"
NOTE_LEAD = "The inline-display follow-on (2026-09-07):"
BULLET_LEAD = "- The inline-display follow-on (2026-09-07)"
SUITE = "ui/webview/anchor-map-boundary-points.test.ts"


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
    """The test files a run of prose names in backticks, as `file-review-docs.test.ts` reads them."""
    names = re.findall(r"`([^`\s]+\.(?:test\.ts|py|bats))`", text)
    return [n if "/" in n else "ui/webview/" + n for n in names]


def _header(path, lines=25):
    with open(path, encoding="utf-8") as f:
        return "".join(f.readline() for _ in range(lines))


def _test_titles(ts):
    """The titles of a node:test suite's top-level tests."""
    return re.findall(r'^test\("((?:[^"\\]|\\.)*)"', ts, re.M)


class ThePainterPlacesAPointOutsideItsOwnMarks(unittest.TestCase):
    """The premise, read from `anchor-map.ts`: the marks a point climbs out of are the painters' own, both
    boundary helpers climb, and every placement of a point at a node's edge goes through them."""

    def setUp(self):
        self.anchor = _read("ui", "webview", "anchor-map.ts")

    def _has(self, pattern, why):
        # assertTrue over assertRegex: a miss must not print the whole source file
        self.assertTrue(re.search(pattern, self.anchor, re.M), "anchor-map.ts lacks %r: %s" % (pattern, why))

    def test_the_marks_a_point_climbs_out_of_are_the_three_painters_marks(self):
        m = re.search(r"^const isPaintMark = \(n: DNode\): boolean => (.*);$", self.anchor, re.M)
        self.assertTrue(m, "anchor-map.ts has no isPaintMark; the note names the marks a point sits outside of")
        self.assertEqual(sorted(re.findall(r'hasClass\(n, "([^"]+)"\)', m.group(1))), ["fc-hl", "fc-ins", "fc-presel"],
                         "the note names a change's fc-ins, a comment's fc-hl and the composer's fc-presel")

    def test_insert_after_text_climbs_out_of_a_mark_that_ends_with_the_node_and_passes_earlier_points(self):
        self._has(r"^function insertAfterText\(t: DText, m: DElement\): void \{\s*\n\s*let n: DNode = t;\s*\n"
                  r"\s*while \(n\.parentNode && isPaintMark\(n\.parentNode\) && n\.parentNode\.childNodes\[n\.parentNode\.childNodes\.length - 1\] === n\) n = n\.parentNode;",
                  "a point after the last text of a painter's mark climbs out of the mark")
        self._has(r"while \(i < parent\.childNodes\.length && isPoint\(parent\.childNodes\[i\]\)\) i\+\+;",
                  "points at one offset keep their paint order: a later point goes after the earlier ones")

    def test_insert_before_node_climbs_out_of_a_mark_that_begins_with_the_node(self):
        self._has(r"^function insertBeforeNode\(n: DNode, m: DElement\): void \{\s*\n"
                  r"\s*while \(n\.parentNode && isPaintMark\(n\.parentNode\) && n\.parentNode\.childNodes\[0\] === n\) n = n\.parentNode;",
                  "a point before the first text of a painter's mark climbs out of the mark")

    def test_every_edge_placement_goes_through_the_helpers(self):
        self._has(r"if \(col === cum\) insertBeforeNode\(t, m\);", "Raw: a point at a text node's start")
        self._has(r"insertAfterText\(nodes\[nodes\.length - 1\], m\);", "Raw: a point at the row's end")
        self._has(r"if \(spot\.off <= 0\) insertBeforeNode\(spot\.t, m\);", "Rendered: a point at a text node's start")
        self._has(r"else if \(spot\.off >= spot\.t\.data\.length\) insertAfterText\(spot\.t, m\);", "Rendered: a point at a text node's end")
        self._has(r'insertBeforeNode\(first, makePoint\(first\.ownerDocument, "fc-del",', "Rendered: a substitution's point before its tint")


class TheFollowOnNoteStatesTheBoundaryRule(unittest.TestCase):
    """The note under Slice 2's build record records the rule, its scope, its source and what it replaced."""

    def setUp(self):
        self.note = _paragraph(_read("plans", "file-review.md"), NOTE_LEAD)

    def test_the_note_names_the_rule_the_marks_and_its_source(self):
        self.assertIn("A point at the edge of a painter's own mark (a change's `fc-ins`, a comment's `fc-hl`, the composer's "
                      "`fc-presel`) sits outside the mark", self.note)
        self.assertIn("(`insertBeforeNode` and `insertAfterText` in `anchor-map.ts`)", self.note)

    def test_the_note_gives_the_rule_both_views_and_either_paint_order(self):
        self.assertIn("in both views and whichever change was painted first", self.note)
        self.assertIn("Points at one offset keep their paint order", self.note)

    def test_the_note_records_the_substitution_inside_a_refused_block(self):
        # the suite's fourth placement: the tint the text-match fallback found still gets its point
        self.assertIn("wherever the tint was found: inside a code fence or a table cell too, where the tint came through the "
                      "text-match fallback, so a substitution there is shown while a deletion at the same offset is card-only",
                      self.note)

    def test_the_note_bounds_the_rule_to_the_painters_marks(self):
        self.assertIn("The renderer's own inline elements are not boundaries", self.note)

    def test_the_note_says_what_the_rule_replaced(self):
        self.assertIn("with the insertion painted first, Rendered made the point the mark's last child", self.note)


class TheTestsSectionNamesTheBoundarySuite(unittest.TestCase):
    """The follow-on's Tests bullet names the boundary suite and this module, and what it credits the suite with
    is what the suite's tests are titled for."""

    def setUp(self):
        self.tests = _section(_read("plans", "file-review.md"), "Tests")
        bullets = [b for b in _bullets(self.tests) if b.startswith(BULLET_LEAD)]
        self.assertEqual(len(bullets), 1, "exactly one Tests bullet is the follow-on's")
        self.bullet = bullets[0]
        self.titles = " ".join(_test_titles(_read(*SUITE.split("/"))))

    def test_the_suite_claims_the_follow_on(self):
        # the tree pin in test_file_review_plan_inline_display.py holds the bullet to every claimant; a suite that
        # stopped claiming would slip out of that record unnoticed
        self.assertIn(FOLLOW_ON, _header(os.path.join(ROOT, SUITE)), "%s no longer says it is the follow-on's" % SUITE)

    def test_the_bullet_names_the_suite_and_this_module(self):
        named = _test_files(self.bullet)
        self.assertIn(SUITE, named)
        self.assertIn("tests/test_file_review_plan_boundary_points.py", named)

    def test_the_bullets_account_of_the_suite_is_what_the_suite_tests(self):
        m = re.search(r"`anchor-map-boundary-points\.test\.ts` pins (.*?);\s*`", self.bullet)
        self.assertTrue(m, "the bullet does not say what the boundary suite pins")
        account = m.group(1)
        self.assertIn("in Raw and Rendered under both paint orders", account)
        self.assertTrue(self.titles, "%s has no top-level tests" % SUITE)
        for claim, title_marker in (
                ("right after or right before an insertion", "painted first"),
                ("at a row's end too", "ends its line"),
                ("comment highlight's edge", "comment highlight: a deletion at the highlight's end"),
                ("change mark and a highlight over the same word", "cover the same word"),
                ("two points at one offset keep their paint order", "at one offset keep the order they were painted in"),
                ("code fence or a table cell", "inside a code fence or a table cell"),
                ("reported painted while a deletion at the same offset is card-only", "is reported painted; a deletion at the same offset is card-only")):
            self.assertIn(claim, account, "the bullet no longer credits the suite with %r" % claim)
            self.assertIn(title_marker, self.titles, "the suite has no test titled for %r; fix the bullet's account or the suite" % claim)


if __name__ == "__main__":
    unittest.main()
