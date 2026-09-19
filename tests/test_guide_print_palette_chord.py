#!/usr/bin/env python3
"""The guide's printing sentence says the print chord also opens the command palette in the dashboard, and the
code says why.

The print follow-on (plans/markdown-viewer.md, "Follow-on: Print (2026-09-19)") put Ctrl+P and Cmd+P in front of
window.print while a file is open, and the guide's first wording presented the key as printing the file, as if the
key had been the browser's own before. On the dashboard it never was: Mod+P has been the command palette's chord
since 2026-08-08 (ui/webview/commands.ts), and the palette's dispatcher (ui/webview/palette-main.ts) hears keydown in
the capture phase on every pane document, where the viewer opens, prevents the key and toggles the palette. It calls
stopPropagation, not stopImmediatePropagation, so the print flow's listener on the same document
(ui/webview/file-print.ts) still runs, and that listener reads neither defaultPrevented nor the palette. One press
therefore runs the print and opens the palette (verified by execution on the served dashboard, 2026-09-19). The
guide now says so in the same sentence, and this module holds the sentence to the code it describes: the chord is
the palette's default, the two listeners meet on the same document in the same phase, neither yields to the other,
and Escape closes the palette. A later change that ends the collision (the print flow yielding to a prevented key,
the palette standing down over an open file, a rebound default) fails here, so the sentence is rewritten with it.
Synthetic: the repo's own text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

SENTENCE = ("**Print** in the file's bar, or **Cmd+P** on a Mac and **Ctrl+P** elsewhere while a file is open, "
            "prints the file alone, black on white, with its pictures loaded, across as many pages as it needs; "
            "in the dashboard that key also opens the command palette, which **Escape** closes.")
REVISIT = " (the guide's printing sentence says the key also opens the palette; if this changed, reword it)"


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(md, label):
    at = md.index(label)
    return _flat(md[at:md.index("\n\n", at)])


class PrintingSentenceNamesThePalette(unittest.TestCase):
    def setUp(self):
        self.guide = _read("docs", "guide.md")
        self.palette_main = _read("ui", "webview", "palette-main.ts")
        self.flow = _read("ui", "webview", "file-print.ts")

    def test_the_sentence_is_in_the_markdown_paragraph(self):
        self.assertIn(SENTENCE, _paragraph(self.guide, "**Opening a markdown document.**"))

    def test_the_key_the_sentence_names_is_the_palettes_default_chord(self):
        commands = _read("ui", "webview", "commands.ts")
        self.assertIn('"palette.toggle": "Mod+P",', commands, "Mod+P toggles the palette out of the box" + REVISIT)
        # Mod is the Command key on a Mac and Control elsewhere, the two spellings the sentence gives
        self.assertRegex(_read("ui", "webview", "keybindings.ts"), r'\(mac \? "Meta" : "Ctrl"\)')
        # and the print flow answers the same key: Control or Command with P, no Shift or Alt
        self.assertIn('return (e.ctrlKey === true || e.metaKey === true) && e.altKey !== true && e.shiftKey !== true '
                      '&& e.repeat !== true && typeof e.key === "string" && e.key.toLowerCase() === "p";', self.flow)

    def test_the_palette_is_the_dashboards_and_hears_every_pane_document_in_the_capture_phase(self):
        # the qualifier "in the dashboard": the dispatcher is the browser dashboard's alone
        self.assertIn("browser dashboard only", self.palette_main)
        # wired on the shell document and on every pane document, where the viewer opens, in the capture phase
        self.assertIn('document.addEventListener("keydown", onKey, true);', self.palette_main)
        self.assertIn('if (f.contentDocument) f.contentDocument.addEventListener("keydown", onKey, true);', self.palette_main)
        # the print flow listens on the same document in the same phase
        self.assertIn('doc.addEventListener("keydown", onKey, true);', self.flow)

    def test_neither_listener_yields_to_the_other(self):
        # the palette prevents the key and stops it from travelling on, but not from the other listeners on its node
        self.assertIn("e.preventDefault(); e.stopPropagation();\n    palette.close();", self.palette_main)
        self.assertNotIn("stopImmediatePropagation", self.palette_main, "the print listener would no longer run" + REVISIT)
        # the print flow does not read a prevented key, and neither module knows the other
        self.assertNotIn("defaultPrevented", self.flow, "the print flow would yield to the palette" + REVISIT)
        self.assertNotRegex(self.flow, r"(?i)palette", "the print flow would know the palette" + REVISIT)
        self.assertNotRegex(self.palette_main, r"(?i)fileview", "the palette would know the viewer" + REVISIT)

    def test_escape_closes_the_palette(self):
        self.assertIn('if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }',
                      _read("ui", "webview", "palette.ts"))

    def test_the_sentence_speaks_plainly(self):
        self.assertNotIn("—", SENTENCE)
        self.assertNotIn("fleet", SENTENCE)
        for word in ("listener", "capture", "dispatcher", "keydown", "Mod+P"):
            self.assertNotIn(word, SENTENCE, "the guide describes what happens, not the mechanism")


if __name__ == "__main__":
    unittest.main()
