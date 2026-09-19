#!/usr/bin/env python3
"""The guide's printing sentence says that in the dashboard the print chord opens the command palette instead of
printing, and the code says why.

The print follow-on (plans/markdown-viewer.md, "Follow-on: Print (2026-09-19)") put Ctrl+P and Cmd+P in front of
window.print while a file is open, and the guide's first wording presented the key as printing the file, as if the
key had been the browser's own before. On the dashboard it never was: Mod+P has been the command palette's chord
since 2026-08-08 (ui/webview/commands.ts), and the palette's dispatcher (ui/webview/palette-main.ts) hears keydown in
the capture phase on every pane document, where the viewer opens, from the frame's load, prevents the key and toggles
the palette. The print flow's listener (ui/webview/file-print.ts) is registered per open on the same document in the
same phase, so it runs after the dispatcher (same target, same phase: registration order), and it stands down on a
key a listener before it already prevented (the first review of the follow-on, 2026-09-19; before that fix one press
ran the print AND opened the palette, and the guide of that day said so). So in the dashboard the key opens the
palette and prints nothing, and the bar's Print button prints; outside the shell (a chat page opened on its own, or
the page the browser legs serve) no dispatcher stands ahead and the chord prints. The guide says so in the same
sentence, and this
module holds the sentence to the code it describes: the chord is the palette's default and resolves to the two keys
the sentence names; the two listeners meet on the same document in the same phase, the palette's first; the flow
yields to the prevented key before it presses, knowing the palette by that bit alone; the palette does not stand
down over an open file; and Escape closes the palette. A later change that moves any of these (the flow no longer
reading defaultPrevented, the palette stopping the key from the flow's listener too, the palette standing down over
an open file, a rebound default) fails here, so the sentence is rewritten with it. ui/webview/file-print-driver-
browser.test.ts (2) executes the stand-down in Chromium; this module is the pin that names the sentence, and
tools/markdown-viewer-plan-print.test.mjs reads the SENTENCE literal below so the two pins hold the guide to one
wording. The pins below read the code with its comments removed, so a statement meets them and a comment that names
the same string never does. Synthetic: the repo's own text only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

SENTENCE = ("**Print** in the file's bar, or **Cmd+P** on a Mac and **Ctrl+P** elsewhere while a file is open, "
            "prints the file alone, black on white, with its pictures loaded, across as many pages as it needs; "
            "in the dashboard that key opens the command palette instead (**Escape** closes it), so print from the "
            "bar there.")
REVISIT = (" (the guide's printing sentence says that in the dashboard the key opens the palette instead of printing;"
           " if this changed, reword it)")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(md, label):
    at = md.index(label)
    return _flat(md[at:md.index("\n\n", at)])


def _code(ts):
    """The source without its comments: a pin met here is met by a statement, never by a comment naming the string."""
    ts = re.sub(r"/\*.*?\*/", "", ts, flags=re.S)
    return re.sub(r"//[^\n]*", "", ts)


def _between(text, start, end):
    """`text` from `start` up to the `end` that follows it; a missing mark raises, which is the failure wanted."""
    a = text.index(start)
    return text[a:text.index(end, a + len(start))]


class PrintingSentenceNamesThePalette(unittest.TestCase):
    def setUp(self):
        self.guide = _read("docs", "guide.md")
        self.palette_main = _read("ui", "webview", "palette-main.ts")
        self.flow = _read("ui", "webview", "file-print.ts")
        # the two keydown handlers, code only
        self.flow_key = _between(_code(self.flow), "const onKey = (e: KeyboardEvent): void => {",
                                 'doc.addEventListener("keydown", onKey, true);')
        self.palette_key = _between(_code(self.palette_main), "function onKey(e: KeyboardEvent): void {", "\n  }")

    def test_the_sentence_is_in_the_markdown_paragraph(self):
        para = _paragraph(self.guide, "**Opening a markdown document.**")
        # "also" claimed the key prints in the dashboard too; the flow stands down there, so it does not
        self.assertNotIn("also opens the command palette", para,
                         "in the dashboard the key opens the palette and prints nothing: the guide must not say 'also'")
        self.assertIn(SENTENCE, para, "docs/guide.md's printing sentence is the one this module holds to the code")

    def test_the_key_the_sentence_names_is_the_palettes_default_chord(self):
        commands = _read("ui", "webview", "commands.ts")
        self.assertIn('"palette.toggle": "Mod+P",', commands, "Mod+P toggles the palette out of the box" + REVISIT)
        # Mod is the Command key on a Mac and Control elsewhere, the two spellings the sentence gives
        self.assertRegex(_code(_read("ui", "webview", "keybindings.ts")), r'\(mac \? "Meta" : "Ctrl"\)')
        # and the print flow's keys are the same: Control or Command with P, no Shift or Alt; a press is those keys and
        # not a key repeat (the flow prevents a held chord's repeats and presses on none of them)
        keys = _between(_code(self.flow), "export function isPrintKeys(e: KeyLike): boolean {", "\n}")
        self.assertIn('return (e.ctrlKey === true || e.metaKey === true) && e.altKey !== true && e.shiftKey !== true '
                      '&& typeof e.key === "string" && e.key.toLowerCase() === "p";', keys)
        chord = _between(_code(self.flow), "export function isPrintChord(e: KeyLike): boolean {", "\n}")
        self.assertIn("return isPrintKeys(e) && e.repeat !== true;", chord)

    def test_the_palette_is_the_dashboards_and_hears_every_pane_document_in_the_capture_phase_first(self):
        # the qualifier "in the dashboard": the dispatcher is the browser dashboard's alone
        self.assertIn("browser dashboard only", self.palette_main)
        code = _code(self.palette_main)
        # wired on the shell document and on every pane document, where the viewer opens, in the capture phase, from
        # the frame's load: ahead of any listener a viewer opened in the pane registers later
        self.assertIn('document.addEventListener("keydown", onKey, true);', code)
        self.assertIn('if (f.contentDocument) f.contentDocument.addEventListener("keydown", onKey, true);', code)
        self.assertIn('f.addEventListener("load", wire);', code)
        for pane in ('"f-chat"', '"f-files"'):
            self.assertIn(pane, code, "the panes the viewer opens in are wired")
        # the print flow listens on the same document in the same phase, registered at the open and removed at the close
        flow = _code(self.flow)
        self.assertIn('doc.addEventListener("keydown", onKey, true);', flow)
        self.assertIn('doc.removeEventListener("keydown", onKey, true);', flow)

    def test_the_flow_stands_down_on_the_key_the_palette_prevented(self):
        # the palette prevents the key and stops it from travelling on, but not from the other listeners on its node,
        # so the flow's listener runs and must read the prevented bit itself
        self.assertIn("e.preventDefault(); e.stopPropagation();", self.palette_key)
        self.assertNotIn("stopImmediatePropagation", self.palette_main,
                         "the print listener would no longer run under the palette" + REVISIT)
        # the flow yields to the prevented key before anything it does with the chord: no preventDefault of its own,
        # no press; so under the palette's claim nothing prints and the bar stays at rest
        stand_down = "if (e.defaultPrevented) return;"
        self.assertIn(stand_down, self.flow_key, "the print flow would print under the palette" + REVISIT)
        at = self.flow_key.index(stand_down)
        for later in ("isPrintKeys(e)", "isPrintChord(e)", "press();"):
            self.assertGreater(self.flow_key.index(later), at, later + " runs only past the stand-down")
        self.assertEqual(self.flow_key.count("press();"), 1, "one press in the handler, after the stand-down")
        # and each knows the other by that bit alone: the flow names no palette in its code, the palette no viewer (a
        # palette standing down over an open file would hand the key back to the flow, and "instead" would be wrong)
        self.assertNotRegex(_code(self.flow), r"(?i)palette", "the print flow would know the palette by name" + REVISIT)
        self.assertNotRegex(self.palette_main, r"(?i)fileview", "the palette would stand down over an open file" + REVISIT)

    def test_escape_closes_the_palette(self):
        self.assertIn('if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }',
                      _read("ui", "webview", "palette.ts"))

    def test_the_sentence_speaks_plainly(self):
        self.assertNotIn(chr(0x2014), SENTENCE)
        self.assertNotIn("fleet", SENTENCE)
        for word in ("listener", "capture", "dispatcher", "keydown", "Mod+P", "defaultPrevented"):
            self.assertNotIn(word, SENTENCE, "the guide describes what happens, not the mechanism")


if __name__ == "__main__":
    unittest.main()
