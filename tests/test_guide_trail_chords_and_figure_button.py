#!/usr/bin/env python3
"""The guide's two link-navigation sentences (docs/guide.md, Files, "Links in a file") state their exceptions, and the code has them.

The link-navigation follow-on (plans/markdown-viewer.md, "Follow-on: Link navigation (2026-09-19)") gave the viewer a
trail with Back and Forward, chords, and an "Open the picture" button on the figures of a rendered file. Its review
found two guide sentences false by execution, and this module pins the corrected wording to the lines that make it
true, so a change to either fails here beside the other.

The trail sentence. Inside the dashboard the shell's pane-focus script (kernel.py `_LANDING_FOCUS_JS`, served by
`_landing` alone) wires a capture-phase keydown listener on every pane document as the pane loads and takes Alt+Left
and Alt+Right on a non-editable target as the move between panes (preventDefault, stopPropagation); the viewer's
`onNavKey` (file-view.ts), a later capture-phase listener on the same document, returns on a prevented key. So in the
dashboard the arrow chords move the keyboard between the panes and the trail steps on Cmd+[ and Cmd+] (a Mac; the
shell returns on metaKey) and on the two buttons; on a Files or chat page open in a browser tab of its own, which
carries no shell script, the arrows step it too. The guide says so, in those terms, and this module holds the
sentence to the shell's lines, to `onNavKey`'s stand-downs (a prevented key, a typing target, the editor open) and to
`navChord`'s two chord families (file-trail.ts).

The picture sentence. Round 1 of the review left two pictures without the button: one under `FIGOPEN_MIN_PX` on
either side (a badge, an inline icon; `figureTooSmall`, read by the one decision `decideFigureControl` at the load and
at each change of the body's width), and one inside a link that holds more than the picture (`linkAbove`: the climb of `figureAnchor`
leaves such a link standing over the img, where `linkAround` climbs a link holding the picture alone so its button
lands after the link). A small picture no link holds still opens on a plain click: the figure's click listener reads
the link above the target and never the size. The guide names all three kinds of picture without the button (the
`data:` picture among them) and the number it gives is read off the constant here. The file review of the PR
(2026-09-20) added two clauses, held here too: with the Comments panel open a drag that starts on the button draws no
rectangle (the button takes the press; the loss is recorded, not built against), and inside a link with no address
left, or an anchor that only marks a place, the plain click opens the picture (linkOf reads neither, and the button is
withheld there all the same). The figure sentence is quoted whole here and in the tools pin, and the two copies are
read against each other.

Each guide sentence is pinned flattened, so a rewrap survives. Synthetic: only the repo's own text.
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


def _paragraph(section, lead):
    """The paragraph of the section that opens with `lead`, flattened."""
    start = section.index(lead)
    end = section.find("\n\n", start)
    return _flat(section[start:] if end < 0 else section[start:end])


def _body(source, head, close):
    """The text of `source` from the line holding `head` to the first line that is exactly `close` after it."""
    start = source.index(head)
    end = source.index("\n" + close + "\n", start)
    return source[start:end]


TRAIL = ("each at the place and in the view you left it (while you are not editing the file and no text box holds "
         "the keyboard, Cmd+[ and Cmd+] on a Mac do the same, and so do Alt+Left and Alt+Right on a Files or chat "
         "page open in a browser tab of its own; in the dashboard those two keys move the keyboard between the "
         "panes); a file opened from the chat, from a listing or from the Files pane's **Recent** list starts the "
         "trail over, and closing the viewer ends it.")
# the whole figure sentence, byte for byte the copy tools/markdown-viewer-plan-linknav.test.mjs holds as SECOND (checked below)
PICTURE = ("A picture in a rendered file that comes from a file or a web address has an **Open the picture** but"
                "ton at its top-right corner (top-left for a picture floated to the right), shown while the pointer i"
                "s over the picture or the button holds the keyboard focus, that opens the picture on its own in the "
                "viewer, with Back returning you to the file at that place; a plain click on the picture does the sam"
                "e while the Comments panel is closed (with the panel open, a click offers a comment as before, and a"
                " drag draws a rectangle unless it starts on the button, which takes the press), a Cmd-click (Ctrl on"
                " Windows and Linux) opens the picture in a browser tab, and a picture from the web opens its address"
                " in a new tab, as a link to that site does; a figure waiting behind its host's box gets its button o"
                "nce it has loaded, and three kinds of picture have none: a `data:` picture, whose bytes are written "
                "into the file itself and which does not open; a picture smaller than 48 pixels on either side (a bad"
                "ge, an inline icon), which the button would cover, and which a plain click still opens when no link "
                "holds it; and a picture inside a link that holds more than the picture (a caption beside it), where "
                "a click follows the link (a link with no address left, or an anchor that only marks a place, leaves "
                "the click to the picture, which opens), while a picture that is all its link holds keeps its button "
                "beside the link.")
PICTURE_HEAD = PICTURE[:PICTURE.index("; a plain click")]
PICTURE_NONE = PICTURE[PICTURE.index("a figure waiting behind"):]
# the wording the review found false by execution: the arrow chords with no dashboard exception, and every picture with the button
OLD_TRAIL = "(Alt+Left and Alt+Right, or Cmd+[ and Cmd+] on a Mac, do the same while no text box holds the keyboard)"
OLD_PICTURE = "Every picture in a rendered file"


class GuideSentences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = _read("docs", "guide.md")
        cls.links = _paragraph(_section(cls.guide, "Files"), "**Links in a file.**")
        cls.kernel = _read("kernel", "kernel.py")
        cls.viewer = _read("ui", "webview", "file-view.ts")
        cls.trail = _read("ui", "webview", "file-trail.ts")

    def test_the_trail_sentence_names_the_dashboard_exception_and_the_old_wording_is_gone(self):
        self.assertIn(TRAIL, self.links)
        self.assertNotIn(OLD_TRAIL, _flat(self.guide))
        self.assertEqual(self.links.count("Alt+Left"), 1, "the arrow chords are described once")

    def test_the_picture_sentence_names_the_three_pictures_without_the_button_and_the_old_wording_is_gone(self):
        self.assertIn(PICTURE_HEAD, self.links)
        self.assertIn(PICTURE_NONE, self.links)
        self.assertLess(self.links.index(TRAIL), self.links.index(PICTURE_HEAD), "the trail sentence first, then the picture's")
        self.assertLess(self.links.index(PICTURE_HEAD), self.links.index(PICTURE_NONE))
        self.assertTrue(self.links.endswith(PICTURE_NONE), "the picture sentence closes the paragraph")
        self.assertIn(PICTURE, self.links, "the whole sentence, as the tools pin quotes it")

    def test_the_picture_sentence_here_is_byte_for_byte_the_tools_pins_copy(self):
        """Two pins quote the guide's figure sentence whole: SECOND in tools/markdown-viewer-plan-linknav.test.mjs and PICTURE
        here. A correction that reaches one and not the other leaves a pin holding stale words, so the two are read against
        each other: the JS literal, its escapes undone, is this module's constant."""
        pin = _read("tools", "markdown-viewer-plan-linknav.test.mjs")
        m = re.search(r"^const SECOND = '((?:[^'\\]|\\.)*)';$", pin, re.M)
        assert m, "the tools pin's SECOND literal"
        second = re.sub(r"\\(.)", r"\1", m.group(1))
        self.assertEqual(second, PICTURE)
        m = re.search(r"^const FIRST = '((?:[^'\\]|\\.)*)';$", pin, re.M)
        assert m, "the tools pin's FIRST literal"
        self.assertTrue(re.sub(r"\\(.)", r"\1", m.group(1)).endswith(TRAIL), "the trail sentence pinned here is the tail of the tools pin's FIRST")
        self.assertNotIn(OLD_PICTURE, _flat(self.guide))
        for word in ("—", "fleet"):
            self.assertNotIn(word, self.links)


class TheShellTakesTheArrowsInTheDashboard(GuideSentences):
    """The sentence's dashboard half: the shell's listener, wired first on every pane document, takes Alt+Arrow."""

    def setUp(self):
        m = re.search(r'^_LANDING_FOCUS_JS = """\n(.*?)\n"""', self.kernel, re.S | re.M)
        assert m, "_LANDING_FOCUS_JS"
        self.shell = m.group(1)

    def test_the_shell_takes_alt_arrow_alone_on_a_non_editable_target_and_moves_the_pane_focus(self):
        on_key = _body(self.shell, "function onKey(e){", "}")
        self.assertIn("if(!e.altKey||e.shiftKey||e.ctrlKey||e.metaKey)return;", on_key, "Alt alone: Cmd+[ and Cmd+] pass the shell")
        self.assertIn("var dir={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down'}[e.key];", on_key)
        self.assertIn("if(editable(e.target))return;", on_key, "a text box keeps its own Alt+Arrow")
        self.assertIn("e.preventDefault();e.stopPropagation();moveFocus(dir);", on_key, "prevented, so onNavKey stands down; the pane focus moves")
        self.assertIn("return tag==='textarea'||tag==='input'||tag==='select'||t.isContentEditable;", self.shell)

    def test_the_shell_wires_its_listener_in_the_capture_phase_on_every_pane_document_at_load(self):
        wire = _body(self.shell, "function wire(f){", "Object.keys(PANE).forEach(function(id){var f=document.getElementById(id);if(!f)return;")
        self.assertIn("d.addEventListener('keydown',onKey,true);", wire, "capture, on the pane's document: ahead of a listener a later open adds")
        self.assertIn("f.addEventListener('load',function(){wire(f);});wire(f);});", self.shell, "wired now and on every load of the pane")
        self.assertIn("'f-files':'files-pane'", self.shell, "the Files pane is one of the panes wired")
        self.assertIn("'f-chat':'chat-pane'", self.shell, "and so is a chat pane, whose viewer opens over the chat")
        self.assertIn("document.addEventListener('keydown',onKey,true);", self.shell, "and the shell document itself")

    def test_the_landing_page_alone_serves_the_shell_script_so_a_pane_page_in_its_own_tab_has_no_such_listener(self):
        code_lines = [ln for ln in self.kernel.splitlines() if "_LANDING_FOCUS_JS" in ln and not ln.lstrip().startswith(("#", "//"))]
        self.assertEqual(len(code_lines), 2, code_lines)
        self.assertEqual(code_lines[0], '_LANDING_FOCUS_JS = """', "the definition")
        self.assertEqual(code_lines[1].strip(), '"<script>" + _LANDING_FOCUS_JS + "</script>"', "and its one use")
        start = self.kernel.index("\ndef _landing():\n")
        landing = self.kernel[start:self.kernel.index("\ndef ", start + 1)]
        self.assertIn('"<script>" + _LANDING_FOCUS_JS + "</script>"', landing, "inside _landing, the dashboard page")

    def test_the_viewer_chord_listener_stands_down_on_a_prevented_key_a_typing_target_and_the_open_editor(self):
        nav = _body(self.viewer, "const onNavKey = (e: KeyboardEvent) => {", "  };")
        self.assertIn('if (e.defaultPrevented || !document.getElementById("romp-fileview")) return;', nav, "the shell's prevented key ends it here")
        self.assertIn("const dir = navChord(e, IS_MAC);", nav)
        self.assertIn("if (a && a !== document.body && isTypingTarget(a)) return;", nav, "no text box holds the keyboard")
        self.assertIn("if (editing) return;", nav, "you are not editing the file")
        self.assertIn("e.preventDefault();", nav)
        self.assertIn('document.addEventListener("keydown", onNavKey, true);', self.viewer, "the same document, the same phase, registered at the open: after the shell's")
        self.assertIn("if (a.localName === \"textarea\" || a.localName === \"select\") return true;", self.viewer)

    def test_the_chord_table_has_the_arrows_on_every_platform_and_the_bracket_chords_on_a_mac(self):
        chord = _body(self.trail, "export function navChord(", "}")
        self.assertIn("if (e.altKey && !e.metaKey && !e.ctrlKey && !e.shiftKey) {", chord)
        self.assertIn('if (e.key === "ArrowLeft") return "back";', chord)
        self.assertIn('if (e.key === "ArrowRight") return "forward";', chord)
        self.assertIn("if (mac && e.metaKey && !e.altKey && !e.ctrlKey && !e.shiftKey) {", chord, "Cmd+[ and Cmd+] on a Mac: metaKey, which the shell lets through")
        self.assertIn('if (e.key === "[") return "back";', chord)
        self.assertIn('if (e.key === "]") return "forward";', chord)


class ThreeKindsOfPictureWithoutTheButton(GuideSentences):
    """The sentence's exceptions: the floor, the link holding more, and a `data:` picture with nothing to open."""

    def test_the_floor_the_guide_gives_is_the_constant_and_is_read_on_either_side(self):
        m = re.search(r"\nconst FIGOPEN_MIN_PX = (\d+);\n", self.viewer)
        assert m, "FIGOPEN_MIN_PX"
        g = re.search(r"a picture smaller than (\d+) pixels on either side", self.links)
        assert g, "the guide's number"
        self.assertEqual(int(g.group(1)), int(m.group(1)), "the guide's floor is the code's")
        small = _body(self.viewer, "function figureTooSmall(img: Element): boolean {", "}")
        self.assertIn("return b !== null && (b.w < FIGOPEN_MIN_PX || b.h < FIGOPEN_MIN_PX);", small, "either side under the floor")

    def test_the_builder_refuses_the_three_and_puts_the_button_after_a_link_holding_the_picture_alone(self):
        build = _body(self.viewer, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "}")
        self.assertIn("if (figureTooSmall(img)) return false;", build, "the floor, read from the loaded picture")
        self.assertIn("if (figureTarget(img, filePath) === null) return false;", build, "nothing to open: a data: picture, no source")
        self.assertIn("return linkAbove(anchor) === null;", build, "a link holding more than the picture")
        decide = _body(self.viewer, "function decideFigureControl(img: Element, filePath: string): void {", "}")
        self.assertIn("const anchor = figureAnchor(img);", decide)
        self.assertIn("if (standing) { if (!want) standing.remove(); return; }", decide, "the one place a control is added or removed")
        self.assertLess(build.index("figureTooSmall"), build.index("linkAbove"))
        above = _body(self.viewer, "function linkAbove(anchor: Element): Element | null {", "}")
        self.assertIn("return p ? p.closest('a, [data-act=\"openpath\"]') : null;", above, "any link: to a file, a web address or a section, and a dead one")
        around = _body(self.viewer, "function linkAround(p: Element, a: Element): boolean {", "}")
        self.assertIn('return p.localName === "a" && p.children.length === 1 && p.children[0] === a && (p.textContent || "").trim() === "";', around,
                      "a link holding the picture alone is climbed: the button lands after the link, and the picture keeps it")

    def test_a_plain_click_opens_a_small_picture_no_link_holds_and_follows_a_link_that_holds_it(self):
        start = self.viewer.index("const openFigure = (img: Element, ev: MouseEvent): void => {")
        end = self.viewer.index("\n  });\n", self.viewer.index("const img = bareFigureOf(t, body);", start))
        click = self.viewer[start:end]
        self.assertIn("if (!target) return;", click, "a data: picture does not open: no target")
        self.assertIn("if (!img || linkOf(t)) return;", click, "inside a link the click is the link's")
        self.assertIn('if (img.closest("a[href]")) return;', click, "a web address holding the picture too")
        self.assertIn("openFigure(img, ev);", click)
        self.assertNotIn("figureTooSmall", click, "the click reads no size: a small picture no link holds opens")
        self.assertNotIn("FIGOPEN_MIN_PX", click)

    def test_a_dead_link_or_a_named_target_leaves_the_plain_click_to_the_picture_which_opens(self):
        """The guide's clause: a link with no address left, or an anchor that only marks a place, leaves the click to the
        picture. The figure listener yields to linkOf's links (a path link, a web address the viewer dressed, a section link)
        and to an anchor with an href; a dead anchor (file-view-links.ts DEAD_LINK_CLASS, its href taken off) and a named
        target (`<a id>`, never dressed) are neither, so the plain click reaches openFigure. The control is withheld there
        all the same (linkAbove reads any anchor), which the sentence's "three kinds" count relies on."""
        link_of = _body(self.viewer, "const linkOf = (t: Element | null): HTMLElement | null => {", "  };")
        self.assertIn("t.closest('[data-act=\"openpath\"], a.' + URL_LINK_CLASS + \", a.\" + FRAG_LINK_CLASS)", link_of, "linkOf's selector: the three dressed links")
        self.assertNotIn("DEAD_LINK_CLASS", link_of, "a dead anchor is none of them")
        self.assertNotIn("fv-dead", link_of)
        links = _read("ui", "webview", "file-view-links.ts")
        self.assertIn('export const DEAD_LINK_CLASS = "fv-dead";', links)
        self.assertIn('if (a.hasAttribute("name") || a.hasAttribute("id")) return;', links, "a named target is never dressed, and keeps no href")
        self.assertIn("a picture inside a link that holds more than the picture (a caption beside it), where a click follows the link (a link with no "
                      "address left, or an anchor that only marks a place, leaves the click to the picture, which opens)", self.links)
        above = _body(self.viewer, "function linkAbove(anchor: Element): Element | null {", "}")
        self.assertIn("return p ? p.closest('a, [data-act=\"openpath\"]') : null;", above, "and no button stands inside such an anchor")


if __name__ == "__main__":
    unittest.main()
