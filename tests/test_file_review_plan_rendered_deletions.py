#!/usr/bin/env python3
"""The plan says one thing about deletions in the Rendered view, and it is what the painter does.

The inline-display follow-on (2026-09-07) made `paintChangesRendered` paint a deletion as the same
zero-width point the Raw view paints, placed through the index map (`paintRenderedPoint`), and rewrote
the plan's surface paragraph, its build note and the not-in-v1 list to say so. Two passages kept the
earlier behaviour in the present tense: the Risks bullet "Rendered markdown versus offsets" said
deletions are panel-only in Rendered, and Slice 2's user-visible line offered Reveal as the only way to
a deletion there, so the governing plan stated both behaviours at once (review finding, 2026-09-07).
No test read the plan, so nothing corrected it.

The premise is read from the painter's source rather than hard-coded: if a deletion stops being painted
in Rendered, the premise test fails first and the passage tests name what must change with it. Every
mention of the older behaviour must sit in a paragraph that dates the follow-on, so a reader knows
which statement is current. Synthetic: the repo's own text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse the plan's hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _section(md, heading):
    """The body of one `### heading` up to the next heading of level two or three."""
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _risk(md, label):
    """One `- **label**` bullet of the Risks list, up to the next bullet or heading."""
    m = re.search(r"^- \*\*" + re.escape(label) + r"\*\*(.*?)(?=^- \*\*|^## |\Z)", md, re.S | re.M)
    assert m, "Risks bullet %r not found" % label
    return m.group(1)


def _paragraphs(md):
    """Blank-line paragraphs, with each list bullet its own paragraph."""
    return [_flat(p) for p in re.split(r"\n\s*\n|\n(?=- )", md) if p.strip()]


class ThePainterPlacesADeletionInRendered(unittest.TestCase):
    """The premise, read from `anchor-map.ts`: a `del` is painted as a point through the index map."""

    def setUp(self):
        self.anchor = _read("ui", "webview", "anchor-map.ts")

    def _has(self, pattern, why):
        # assertTrue over assertRegex: a miss must not print the whole source file
        self.assertTrue(re.search(pattern, self.anchor, re.M), "anchor-map.ts lacks %r: %s" % (pattern, why))

    def test_a_del_goes_through_paint_rendered_point(self):
        self._has(r"^export function paintRenderedPoint\(", "the point painter is gone; the plan's surface paragraph, "
                  "build note, Slice 2 line and Risks bullet all describe it")
        self._has(r'if \(c\.kind === "del"\) \{\s*const p = paintRenderedPoint\(renderedRoot, source, c\.curFrom, "fc-del"',
                  "paintChangesRendered no longer paints a deletion as the point")

    def test_a_deletion_the_map_refuses_is_reported_unpainted(self):
        # the card-only case the plan's Risks bullet keeps: the point painter declines, the id lands in `unpainted`
        self._has(r"\(p \? painted : unpainted\)\.push\(c\.id\)", "a refused deletion must be reported unpainted")


class TheRisksBulletMatchesThePainter(unittest.TestCase):
    """"Rendered markdown versus offsets" states the current mitigation, with the older one dated."""

    def setUp(self):
        self.bullet = _flat(_risk(_read("plans", "file-review.md"), "Rendered markdown versus offsets."))

    def test_a_deletion_is_a_point_through_the_same_map(self):
        self.assertIn("a deletion there is a point placed through the same index map, card-only where the map refuses",
                      self.bullet)

    def test_an_unpainted_change_still_reaches_raw(self):
        self.assertIn("every change and comment has a card, and an unpainted change's Reveal opens Raw", self.bullet)

    def test_the_pre_follow_on_claim_is_not_stated_as_current(self):
        # The finding: "deletions are panel-only there" in a present-tense Mitigation list.
        self.assertNotIn("deletions are panel-only there", self.bullet)
        self.assertIn("(the inline-display follow-on, 2026-09-07; before it every Rendered deletion was panel-only)",
                      self.bullet)


class TheSlice2LineMatchesThePainter(unittest.TestCase):
    """Slice 2's user-visible summary names the Rendered points and keeps Reveal for what cannot be painted."""

    def setUp(self):
        section = _section(_read("plans", "file-review.md"),
                           "Slice 2: the session's changes as accept/reject cards and inline marks")
        self.visible = _flat(section.split("\n\n")[0])
        self.assertTrue(self.visible.startswith("User-visible:"), self.visible[:60])

    def test_deletion_points_in_rendered_are_named(self):
        self.assertIn("inline marks in Raw, highlights and deletion points in Rendered (the points since the "
                      "inline-display follow-on, 2026-09-07), Reveal for a change the Rendered view cannot paint",
                      self.visible)

    def test_reveal_is_no_longer_the_only_way_to_a_rendered_deletion(self):
        self.assertNotIn("Reveal for deletions", self.visible)


class ThePlanAgreesWithItself(unittest.TestCase):
    """The passages that describe Rendered deletions say the same thing, and the older behaviour is dated wherever
    it is recalled."""

    def setUp(self):
        self.md = _read("plans", "file-review.md")
        self.flat = _flat(self.md)

    def test_the_surface_paragraph_and_the_build_note_describe_the_point(self):
        self.assertIn("deletions are struck at their point in both views: the Rendered point is placed through the same "
                      "index map the comment highlights use", self.flat)
        self.assertIn("`paintChangesRendered` now paints a deletion as the same zero-width `span.fc-del` point Raw paints",
                      self.flat)

    def test_the_not_in_v1_list_records_the_follow_on(self):
        self.assertIn("Inline deletions in the Rendered view were on this list until the inline-display follow-on "
                      "(2026-09-07, under Slice 2's build note) built them.", self.flat)

    def test_every_card_only_or_panel_only_mention_dates_the_follow_on(self):
        hits = [p for p in _paragraphs(self.md) if re.search(r"\b(card|panel)-only\b", p)]
        self.assertTrue(hits, "no mention left to check; drop this test with the last one")
        for p in hits:
            self.assertIn("2026-09-07", p, "an undated card-only/panel-only mention reads as current: %s" % p[:160])


if __name__ == "__main__":
    unittest.main()
