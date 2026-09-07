#!/usr/bin/env python3
"""The guide's commenting paragraph promises that a comment on text which occurs more than once stays on
the occurrence you chose (the anchors follow-on, 2026-09-07), and the ADR's Consequences name the two
additive sidecar fields that make it so, `target` and `anchorAt`. Each promise is cross-checked against the
source that keeps it: the host script sets and refreshes the stored position and widens the anchor's
context, and the panel paints with that position as the engine's tie-break. Synthetic: only the repo's
own text.
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
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


class GuideAnchors(unittest.TestCase):
    def test_the_guide_says_a_comment_on_repeated_text_stays_where_it_was_put(self):
        guide = _flat(_read("docs", "guide.md"))
        self.assertIn("a comment on text that occurs more than once stays on the occurrence you chose", guide)

    def test_the_adr_names_both_additive_fields(self):
        adr = _flat(_read("docs", "adr", "0002-file-comments-in-the-track-changents-sidecar.md"))
        self.assertIn("Under that rule the sidecar now carries two additive fields, `target` (a region) and `anchorAt`", adr)
        self.assertIn("the anchors follow-on, 2026-09-07", adr)

    def test_the_host_and_the_panel_keep_the_promise(self):
        host = _read("tools", "file-comments-host.mjs")
        self.assertIn("anchor: uniqueAnchor(text, loc.from, loc.to).anchor,", host)
        self.assertIn("anchorAt: loc.from,", host)
        self.assertRegex(host, r"function stageSidecar\(root, storePath, store, text\) \{\s*\n\s*refreshAnchorAts\(store, text\);")
        self.assertIn("export const ANCHOR_CTX_CAP = 480;", host)
        panel = _read("ui", "webview", "file-comments.ts")
        self.assertRegex(panel, r"locateComment\(src, card\.anchor, card\.anchorAt \?\? undefined\)")
        model = _read("ui", "webview", "file-comments-model.ts")
        self.assertIn("anchor?: Anchor | null; anchorAt?: number;", model)


if __name__ == "__main__":
    unittest.main()
