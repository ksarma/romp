#!/usr/bin/env python3
"""The guide's commenting paragraph promises that a comment on text which occurs more than once stays on
the occurrence you chose (the anchors follow-on, 2026-09-07), and the ADR's Consequences name the two
additive sidecar fields that make it so, `target` and `anchorAt`.

This module pins the prose and proves the promise by behaviour: the real host's `uniqueAnchor` and the
vendored engine's `locateAnchor` run under node on a synthetic text, the way tests/test_file_comments_e2e.py
drives them, and the ADR's field names are read from its sentence and looked up on the store comment type.
It pins no source line. The host and panel lines that keep the promise are pinned once each, in the plan-pin
modules the plan's Tests section names (tools/file-review-plan.test.mjs, tools/file-review-plan-anchors.test.mjs,
tools/file-review-plan-acceptance.test.mjs), and the painter's use of the stored position is driven in
ui/webview/file-comments-anchors.test.ts. An earlier version of this module re-pinned four of those lines
verbatim: a rewrap of one turned three to five tests in unrelated files red while the behaviour suites stayed
green, and a no-op refresh kept every pin green (review, 2026-09-08).

The behaviour tests skip when node is missing. Synthetic: the notes-api demo world and the repo's own text.
"""
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
HOST = os.path.join(ROOT, "tools", "file-comments-host.mjs")
ENGINE = os.path.join(ROOT, "vendor", "track-changents", "engine.js")
NODE = shutil.which("node")

QUOTE = "Ship it."
# Two copies of a passage whose 24 characters either side are the same, and whose wider surroundings are
# not: the engine's default anchor cannot tell the copies apart, one step wider can.
TWICE = ("# Notes\n\n"
         "web: the review of the cache branch is done. Ship it. The deploy waits on nothing else; the web session goes next.\n\n"
         "api: the review of the cache branch is done. Ship it. The deploy waits on nothing else; the api session goes next.\n")
# Two copies with identical surroundings for more than the host's cap on both sides: no width tells them
# apart, and only the stored position can.
_LEAD = "Warm the cache before the deploy. " * 15
_TAIL = " Then watch the p95 line for an hour." * 15
REPEAT = "# Repeats\n\n%s%s%s\n\n%s%s%s\n" % (_LEAD, QUOTE, _TAIL, _LEAD, QUOTE, _TAIL)

# For both copies of `quote` in `text`: the engine's default anchor (what the browser's anchor-map builds),
# the anchor the host stores, where a reader with no position places the stored anchor, and where one with
# the copy's own position places it.
PROBE = (
    "const fs = (await import('fs')).default;"
    " const host = await import(process.argv[1]);"
    " const m = await import(process.argv[2]); const e = m.default || m;"
    " const [text, quote] = JSON.parse(fs.readFileSync(0, 'utf8'));"
    " const first = text.indexOf(quote), second = text.indexOf(quote, first + 1);"
    " const at = [first, second];"
    " const cli = at.map((a) => e.makeAnchor(text, a, a + quote.length));"
    " const stored = at.map((a) => host.uniqueAnchor(text, a, a + quote.length));"
    " const placed = stored.map((u) => e.locateAnchor(text, u.anchor));"
    " const hinted = stored.map((u, i) => e.locateAnchor(text, u.anchor, at[i]));"
    " console.log(JSON.stringify({ first, second, ctx: host.ANCHOR_CTX, cap: host.ANCHOR_CTX_CAP, cli, stored, placed, hinted }));"
)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _probe(text, quote):
    env = dict(os.environ)
    env.pop("TRACKCHANGES_ROOT", None)
    env.pop("ROMP_SID", None)
    r = subprocess.run([NODE, "--input-type=module", "-e", PROBE, "--", Path(HOST).as_uri(), Path(ENGINE).as_uri()],
                       input=json.dumps([text, quote]), capture_output=True, text=True, timeout=30, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class GuideAnchors(unittest.TestCase):
    def test_the_guide_says_a_comment_on_repeated_text_stays_where_it_was_put(self):
        guide = _flat(_read("docs", "guide.md"))
        self.assertIn("a comment on text that occurs more than once stays on the occurrence you chose", guide)

    def test_the_adr_names_both_additive_fields(self):
        adr = _flat(_read("docs", "adr", "0002-file-comments-in-the-track-changents-sidecar.md"))
        self.assertIn("Under that rule the sidecar now carries two additive fields, `target` (a region) and `anchorAt`", adr)
        self.assertIn("the anchors follow-on, 2026-09-07", adr)

    def test_the_fields_the_adr_names_are_optional_fields_of_the_store_comment(self):
        # The names come from the ADR's sentence, not from here: a field the ADR renames or adds is looked up
        # under its new name. "Additive" means optional on the type, whatever line or order the type puts it on.
        adr = _flat(_read("docs", "adr", "0002-file-comments-in-the-track-changents-sidecar.md"))
        m = re.search(r"two additive fields, `(\w+)` \([^)]*\) and `(\w+)` \(", adr)
        self.assertIsNotNone(m, "the ADR's Consequences name the two fields")
        names = m.groups()
        self.assertEqual(sorted(names), ["anchorAt", "target"])
        model = _read("ui", "webview", "file-comments-model.ts")
        typ = re.search(r"export type StoreComment = \{(.*?)\n\};", model, re.S)
        self.assertIsNotNone(typ, "the store comment type")
        for name in names:
            self.assertRegex(typ.group(1), r"\b%s\?\s*:" % re.escape(name),
                             "the ADR names `%s`; the store comment type has no optional field of that name" % name)


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheHostKeepsThePromise(unittest.TestCase):
    """The guide's sentence, on the mechanism the ADR names: the host stores an anchor wide enough to name the
    chosen copy, and where no width can, the stored position picks it."""

    def test_a_passage_tied_at_the_engine_s_context_is_stored_wide_enough_to_name_the_chosen_copy(self):
        r = _probe(TWICE, QUOTE)
        first, second = r["first"], r["second"]
        self.assertGreater(second, first, "the text holds the passage twice")
        # the tie the guide's sentence is about: at the engine's default context the copies share one anchor
        self.assertEqual(r["cli"][0], r["cli"][1])
        self.assertEqual(len(r["cli"][0]["prefix"]), r["ctx"])
        # the host widens until the anchor names one copy, keeping the quote; a reader with no position, the
        # other editors, lands on the copy that was chosen
        for i, at in enumerate((first, second)):
            stored = r["stored"][i]
            self.assertTrue(stored["unique"], "copy %d: the stored anchor is unique" % i)
            self.assertEqual(stored["anchor"]["quote"], QUOTE)
            self.assertGreater(len(stored["anchor"]["prefix"]), r["ctx"], "copy %d: wider than the engine's default" % i)
            self.assertEqual(r["placed"][i]["from"], at, "copy %d: placed on the chosen copy without a position" % i)
        self.assertNotEqual(r["stored"][0]["anchor"], r["stored"][1]["anchor"])

    def test_past_the_cap_the_stored_position_picks_the_copy(self):
        r = _probe(REPEAT, QUOTE)
        first, second = r["first"], r["second"]
        self.assertGreater(second, first, "the text holds the passage twice")
        # no width up to the cap tells the copies apart: the host stops at the cap and says so
        for i in range(2):
            self.assertFalse(r["stored"][i]["unique"])
            self.assertEqual(len(r["stored"][i]["anchor"]["prefix"]), r["cap"])
        self.assertEqual(r["stored"][0]["anchor"], r["stored"][1]["anchor"])
        # without a position the engine takes its earliest tie, the first copy; with the copy's own position, the
        # `anchorAt` the host stores and the painter passes, it stays on the copy that was chosen
        self.assertEqual(r["placed"][1]["from"], first)
        self.assertEqual(r["hinted"][0]["from"], first)
        self.assertEqual(r["hinted"][1]["from"], second)


if __name__ == "__main__":
    unittest.main()
