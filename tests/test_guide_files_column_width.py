#!/usr/bin/env python3
"""The guide's Files section says how wide the prose column of a note is, and the sheets do that.

Slice 3 of plans/markdown-viewer.md (decision 4) made the prose of a rendered markdown file a centred
column of 80ch, the root's own inline padding: at least 18px a side, and half of what the body is wider
than 80ch beyond that. The guide's first sentence for it said the column keeps its eighty characters at
every text-size step. It does so only while the pane has room for 80ch plus the two 18px gutters: below
that the padding sits at its floor, the column is the pane less 36px, and each step up fits fewer
characters on a line (a 900px pane caps the column at 864px, 79 characters, at the first step up; a
380px pane holds 36 at 100 percent). The sentence now says both cases. Each clause is cross-checked
against the declaration that does it, byte-equal in both sheets, and against the size ladder the "step
up" refers to, so a changed floor or a dropped ladder fails here too. Synthetic: only the repo's own text.
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


def _rule(css, head):
    """The first rule whose head is `head`, through its closing brace (the parity test's ruleOf)."""
    a = css.index(head)
    return css[a:css.index("}", a) + 1]


SENTENCES = ("The prose of a rendered markdown file is a column of about eighty characters, centred in the "
             "pane. A step up in text size widens the column to keep its eighty characters while the pane has "
             "room for them; in a pane too narrow for that, the column fills the pane, leaving a small gutter "
             "on each side, and each step up fits fewer characters on a line. Code blocks keep the column and "
             "wrap long lines.")

MEASURE = "padding-inline: max(18px, round(down, calc((100% - 80ch) / 2), 1px))"


class TheFilesSectionSaysWhenTheColumnKeepsEightyCharacters(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))

    def test_the_sentences(self):
        self.assertIn(SENTENCES, self.section)

    def test_the_unconditional_claim_is_gone(self):
        # the column keeps eighty characters only while the pane has room for 80ch plus the two gutters
        self.assertNotIn("keeps its eighty characters at every step", self.section)
        self.assertNotIn("at every step", self.section)


class TheSentencesMatchTheSheets(unittest.TestCase):
    """The gutter floor and the 80ch measure are one declaration; the steps are the viewer's size ladder."""

    def setUp(self):
        self.styles = _read("ui", "webview", "styles.css")
        self.feed = _read("ui", "webview", "feed.css")

    def test_the_column_is_the_root_inset_floored_at_a_gutter(self):
        # max(18px, ...) is the "small gutter on each side"; (100% - 80ch) / 2 is the column of eighty characters,
        # centred, in the root's own glyph so a larger text size widens it; the floor is why a narrow pane caps it
        for name, css in (("styles.css", self.styles), ("feed.css", self.feed)):
            rule = _rule(css, ".fileview-md {")
            self.assertIn(MEASURE, rule, name)
            self.assertIn("font-size: calc(var(--fs) * 1.15 * var(--fv-scale, 1))", rule, name)

    def test_the_sheets_agree(self):
        self.assertEqual(_rule(self.styles, ".fileview-md {"), _rule(self.feed, ".fileview-md {"))

    def test_the_steps_are_the_size_ladder(self):
        # "a step up" is a step of TEXT_SIZES above the default, the ladder the A+ button walks
        view = _read("ui", "webview", "file-view.ts")
        m = re.search(r"export const TEXT_SIZES: readonly number\[\] = \[([\d, ]+)\];", view)
        self.assertIsNotNone(m)
        sizes = [int(s) for s in m.group(1).split(",")]
        self.assertIn(100, sizes)
        self.assertTrue([s for s in sizes if s > 100], "the ladder has steps above 100 percent")


class TheSizeSentencePromisesNoKnobTheExtensionLacks(unittest.TestCase):
    """The prose is 1.15 times `--fs`, and `--fs` is `var(--vscode-chat-font-size, 13px)`: 13px unless a source
    defines the variable. VS Code hands a webview `vscode-font-*`, `vscode-editor-font-*` and its colour and size
    registries, no chat key, and the extension defines none of its own (its one font coupling is a body zoom from
    editor.fontSize). So the guide may say the 15-for-13 ratio, and not that a note follows a VS Code chat font
    size: review round 2 of Slice 3 found that promise in the guide with nothing behind it (2026-09-08). A source
    that starts setting the variable fails the premise test below, the cue to revisit the sentence and this pin."""

    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))

    def test_the_premise_nothing_in_the_extension_sets_the_variable(self):
        src = os.path.join(ROOT, "vscode-extension", "src")
        sources = [os.path.join(d, n) for d, _, names in os.walk(src) for n in names
                   if n.endswith(".ts") and not n.endswith(".test.ts")]
        self.assertTrue(sources)
        for path in sources:
            with open(path, encoding="utf-8") as f:
                self.assertNotIn("--vscode-chat-font-size", f.read(), path)

    def test_the_ratio_stays_and_the_promise_is_gone(self):
        self.assertIn("(15 pixels where the chat is 13)", self.section)
        self.assertNotIn("chat font size you set in VS Code", self.section)
        self.assertNotIn("follows the chat font size", self.section)


if __name__ == "__main__":
    unittest.main()
