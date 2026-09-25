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

The picture sentence. The guide names four kinds of picture without the button once the browser has answered for it: a
picture that failed to load (the file review's round 2: `figureState`, refused by `figureWantsControl` and by
`figureTarget` alike, on one rule since before the file review's round 3, `figureHasPicture`, a target or a button only for a
state with a picture to name, so the button and the plain click agree and nothing opens), a `data:` picture (`figureTarget`
null), one under `FIGOPEN_MIN_PX` on either side (a badge, an inline icon; `figureTooSmall`, read by the one decision
`decideFigureControl` at the load and at each reflow of the figure's own box, `watchFigureBoxes`), and one inside a link
that holds more than the picture (`linkAbove`: the climb of `figureAnchor` leaves such a link standing over the img,
where `linkAround` climbs a link holding the picture alone so its button lands after the link); a picture still on its
way has none until its load, and a click on it before then opens nothing (`figureTarget` null while fetching). A small picture no link holds still opens on a plain click: the figure's click listener reads
the link above the target and never the size. The guide's list of pictures without the button is read against the
refusal arms of `figureWantsControl` (a census pinned here, so an arm added or removed asks for the sentence again; the
file review's round 2 added the failed picture to the code's refusals, and `figureTarget` refuses it too, so the button
and the plain click agree), and the floor's number is read off the constant here. The file review of the PR
(2026-09-20) added two clauses, held here too: with the Comments panel open a drag that starts on the button draws no
rectangle (the button takes the press; the loss is recorded, not built against), and inside a link with no address
left, or an anchor that only marks a place, the plain click opens the picture, and since the file review's round 12
(correctness-1 with ui-1) the button and the picture's tooltip stand there too: the click listener, the title and the
button's exclusion read ONE predicate (figureLinkOf over FIGURE_LINK_SET), and neither anchor is in its set. The figure
sentence is quoted whole here and in the tools pin, and the two copies are read against each other.

The hidden pair. The trail sentence's condition clause (the two arrow buttons appear once there is a file to step back or
forward to; there are none before that) and the browser plan's pointer clause ("the pair hidden until then",
plans/file-browser.md) are two claims about one line of openFileView, `nav.hidden`. Open point 13 of the plan's section
records the revert road (the dimmed pair the contract had) as that line and the pins and legs L2 names; the file review's
round 4 (extra8-3) found the guide's clause and its pin missing from that list, so taking the road would have left the
guide false with nothing catching it. Rather than a longer list, the line and the two clauses are asserted together
here, and the tools pins that quote the two sentences (FIRST, POINTER) are read for the clauses too, so a revert of the
hide fails one test naming the two sentences it makes false.

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
         "trail over, and closing the viewer ends it, as does, in the chat, following a link to a page on the "
         "dashboard's own web address that ends in .md or .markdown: the page opens in the viewer in the file's place "
         "as a web "
         "document rather than a file of the session, and the trail ends there (in the Files pane such a link opens "
         "a tab, as any web address does, and the trail stands).")
# the whole figure sentence, byte for byte the copy tools/markdown-viewer-plan-linknav.test.mjs holds as SECOND (checked below)
PICTURE = ("A picture in a rendered file that comes from a file or a web address has an **Open the picture** but"
                "ton at its top-right corner (the top-left in right-to-left text, and on a picture floated to one sid"
                "e, the top corner away from that side), shown while the pointer is over the picture or the button, w"
                "hile a focus you reached from the keyboard is on the button, under any focus for a picture from the "
                "web, and at all times on a phone or tablet and on a laptop with a touchscreen, that opens the pictur"
                "e on its own in the viewer, with Back returning you to the file at that place (where the button is n"
                "ot shown at all times, a Cmd-click on a local picture's button, a Ctrl-click on Windows and Linux, o"
                "r a press dragged off it leaves the button focused but hidden until you press a key, so Enter then o"
                "pens the picture in the viewer with nothing shown first); a plain click on the picture does the same"
                " while the Comments panel is closed (with the panel open, a click offers a comment as before, and so"
                " does a Cmd-click on the picture on a mouse or trackpad, and a drag draws a rectangle unless it star"
                "ts on the button, which takes the press), a Cmd-click (Ctrl on Windows and Linux) on the picture whi"
                "le the panel is closed, or on the button at any time, opens the picture in a browser tab, and a pict"
                "ure from the web opens its address in a new tab, as a link to that site does, but only while its but"
                "ton, or on a small picture its dashed border, is on the screen with nothing over it: a click, a tap,"
                " Enter or Space while it is off the screen or covered (by the list of headings the **Outline** butto"
                "n opens, or the menu of the text size buttons, say) opens nothing and scrolls it into view, and the "
                "next one opens once it shows (a button partly on the screen counts as shown), and the button and the"
                " picture both show that before the click: the button's tooltip says it opens a new tab at the addres"
                "s's host, its border is dashed and its glyph is an arrow leaving a box, and the picture's own toolti"
                "p shows the address's origin (its scheme, host and port, never its path, query or fragment), on a li"
                "ne after the author's title when there is one; when the address has an @ anywhere after its scheme, "
                "so that it may carry a sign-in, both tooltips say the address is withheld and show none of it, even "
                "for a harmless name such as a@2x.png; a click on a picture in a fold's title line (a `<details>` blo"
                "ck's summary) opens or closes the fold and opens nothing, with or without Cmd, and a picture from th"
                "e web there shows no address in its tooltip, while its button, where it has one, still opens it; a f"
                "igure waiting behind its host's box gets its button once it has loaded, as does one still on its way"
                " (a click on it before then opens nothing), and once the browser has answered for a picture, four ki"
                "nds have none: a picture that failed to load, which opens nothing either; a `data:` picture, whose b"
                "ytes are written into the file itself and which does not open; a picture smaller than 48 pixels on e"
                "ither side (a badge, an inline icon), which the button would cover, and which a plain click still op"
                "ens when neither a link nor a fold's title line holds it (a small picture from the web outside such "
                "a line has the dashed border itself, on a mouse or trackpad while the pointer is over it, and at all"
                " times on a phone or tablet and on a laptop with a touchscreen, since a finger gets no tooltip); and"
                " a picture inside a link that holds more than the picture (a caption beside it), where a click follo"
                "ws the link (a link with no address left, or an anchor that only marks a place, is not a link a clic"
                "k can follow, so a picture inside it keeps its button and its tooltip, and a plain click opens it), "
                "while a picture that is all its link holds keeps its button beside the link.")
PICTURE_HEAD = PICTURE[:PICTURE.index("; a plain click")]
PICTURE_NONE = PICTURE[PICTURE.index("a figure waiting behind"):]
# the guide's condition clause for the Back and Forward pair, the browser plan's matching clause, and the one line of openFileView both claim
HIDDEN_UNTIL = ("Two arrow buttons appear at the left of its title bar once there is a file to step back or forward to (after you "
                "follow a link or open a picture; there are none before that):")
BROWSER_PLAN_HIDDEN = "with Back and Forward glyphs at the left of its bar once a step exists either way (the pair hidden until then)"
HIDE_LINE = "nav.hidden = !trailBackTarget(trailNow) && !trailForwardTarget(trailNow);"
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

    def test_the_picture_sentence_names_the_four_pictures_without_the_button_and_the_old_wording_is_gone(self):
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


class TheHiddenPairIsOneLineWithTwoClaims(GuideSentences):
    """The hide of the Back and Forward pair (`nav.hidden` in openFileView), the guide's condition clause and the browser plan's
    clause, asserted together: a revert of the hide fails here naming the two sentences it makes false, and the tools pins
    that quote those sentences are read for the clauses too (the file review's round 4, extra8-3)."""

    def test_the_hide_line_stands_with_the_guide_clause_and_the_browser_plan_clause_it_makes_true(self):
        # assertTrue, not assertIn: on a revert the failure opens with the two sentences, not with the viewer's whole source as
        # the haystack before them (the author's closing pass after the file review's round 4, attribution-and-gates-9)
        self.assertTrue(HIDE_LINE in self.viewer,
                      "openFileView's hide of the Back and Forward pair is gone. Two sentences claim it and go false with it: the guide's "
                      "(docs/guide.md, Links in a file) %r and the browser plan's (plans/file-browser.md, the navigation-stack pointer) %r; "
                      "a revert of the hide rewrites both, and the tools pins FIRST and POINTER that quote them, beside the pins and legs "
                      "open point 13 lists" % (HIDDEN_UNTIL, BROWSER_PLAN_HIDDEN))
        self.assertIn(HIDDEN_UNTIL, self.links, "the guide's condition clause, which the hide line makes true")
        pointer = _paragraph(_read("plans", "file-browser.md"), "Since 2026-09-19 the viewer keeps a trail of its own")
        self.assertIn(BROWSER_PLAN_HIDDEN, pointer, "the browser plan's clause, which the hide line makes true")
        pin = _read("tools", "markdown-viewer-plan-linknav.test.mjs")
        m = re.search(r"^const FIRST = '((?:[^'\\]|\\.)*)';$", pin, re.M)
        assert m, "the tools pin's FIRST literal"
        self.assertIn(HIDDEN_UNTIL, re.sub(r"\\(.)", r"\1", m.group(1)), "the tools pin quoting the guide's sentence carries the clause")
        m = re.search(r"^const POINTER = '((?:[^'\\]|\\.)*)';$", pin, re.M)
        assert m, "the tools pin's POINTER literal"
        self.assertIn(BROWSER_PLAN_HIDDEN, re.sub(r"\\(.)", r"\1", m.group(1)), "the tools pin quoting the browser plan's sentence carries the clause")
        self.assertIn(HIDE_LINE, pin, "and the tools module pins the hide line itself (L2)")


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


class PicturesWithoutTheButton(GuideSentences):
    """The sentence's exceptions, held to the code: the floor, the link holding more, a `data:` picture with nothing to open, and
    (the file review's round 2) the picture that did not load, which the button and the plain click refuse on one verdict.
    The refusal arms of figureWantsControl are the census the guide's list is read against: an arm added or removed fails here
    until the guide's sentence is revisited, so the count the guide gives can no longer drift from the code unseen."""

    def test_the_target_and_the_button_refuse_on_one_rule_a_picture_to_name_so_the_click_and_the_button_agree(self):
        """The file review's round 2 (regression-3 with extra5-4): figureWantsControl withheld the button on a failed figure while
        figureTarget refused the fetching state alone, so a plain click on a failed local figure opened the missing path in the
        viewer and pushed it onto the trail, and a plain click on a failed remote figure opened a tab at a host whose image
        request had answered 404. Both readers now refuse on ONE rule, read before the candidate: a target or a button only for a
        state with a picture to name (figureHasPicture: loaded, or a stand-in outside a browser), so fetching, failed and any
        state figureState gains later are refused alike (before the file review's round 3 each reader listed the two states it
        refused, a list a new value passes). The clause that a picture which did not load has nothing to open is true by this
        pin and by file-view-figure-state-browser.test.ts's execution."""
        self.assertIn('\ntype FigureState = "standin" | "fetching" | "loaded" | "failed";\n', self.viewer, "the domain: four states")
        rule = _body(self.viewer, "function figureHasPicture(state: FigureState): boolean {", "}")
        self.assertIn('return state === "loaded" || state === "standin";', rule, "the allowance: loaded, or a stand-in; every other value refused")
        # the refused states' literals held absent from every reader of file-view.ts: ONE pin, in
        # ui/webview/file-view-figure-shapes.test.ts, reading the literals as the TypeScript compiler does
        # (ui/webview/source-units.ts); the copy that stood here counted the double-quoted spelling alone and passed a
        # single-quoted comparison (the file review's round 4, regression-2 with extra6-1), so it is not kept as a second reader
        target = _body(self.viewer, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "}")
        self.assertIn("const state = figureState(img);", target)
        self.assertIn("if (!figureHasPicture(state)) return null;", target, "no target for a state without a picture to name")
        self.assertLess(target.index("if (!figureHasPicture(state))"), target.index("const dest = chosenSource(img);"), "the state read before the candidate")
        build = _body(self.viewer, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "}")
        self.assertIn("if (!figureHasPicture(state)) return false;", build, "the button withheld on the same rule")

    def test_the_refusals_of_figure_wants_control_are_these_and_no_more(self):
        """Every `return false` arm of figureWantsControl, named and in order: the gate's placeholder (its figure loads on the
        click), the state (one rule, figureHasPicture: no picture to name, which today is fetching or failed), the floor, the
        target (a `data:` picture, no source), and the last word, any link above. A fifth arm, or one gone, fails here and asks for the guide's sentence to be read again."""
        build = _body(self.viewer, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "}")
        arms = [ln.strip() for ln in build.splitlines() if ln.strip().startswith("if (") and ln.strip().endswith("return false;")]
        self.assertEqual(arms, [
            "if (img.closest('[data-act=\"' + GATE_ACT + '\"]')) return false;",
            "if (!figureHasPicture(state)) return false;",
            "if (figureTooSmall(img)) return false;",
            "if (figureTarget(img, filePath) === null) return false;",
        ], "the refusal arms, as the guide's list of pictures without the button reads them")
        self.assertTrue(build.rstrip().endswith("return linkAbove(anchor) === null;"), "the last word: any link above the picture")
        self.assertEqual(build.count("return false;"), 4, "four refusals and the link's verdict; a change here is a change to the guide's sentence")
        # the guide's count against the census: the state arm's failed half, the target arm (a `data:` picture), the floor arm and
        # the link verdict are the four kinds the guide counts once the browser has answered; the gate arm and the fetching half are
        # its "waiting" clause (the button once loaded; a click before then opens nothing), which figureTarget's refusal makes true
        g = re.search(r"once the browser has answered for a picture, (\w+) kinds have none: a picture that failed to load, which opens nothing either;", self.links)
        assert g, "the guide's count and its first kind"
        self.assertEqual(g.group(1), "four", "failed, data:, under the floor, inside a link holding more: the four the census maps to")
        self.assertIn("as does one still on its way (a click on it before then opens nothing)", self.links, "the waiting clause")
        target = _body(self.viewer, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "}")
        self.assertIn("if (!figureHasPicture(state)) return null;", target, "which figureTarget makes true: no target while fetching, by the same rule")

    def test_the_floor_the_guide_gives_is_the_constant_and_is_read_on_either_side(self):
        m = re.search(r"\nconst FIGOPEN_MIN_PX = (\d+);\n", self.viewer)
        assert m, "FIGOPEN_MIN_PX"
        g = re.search(r"a picture smaller than (\d+) pixels on either side", self.links)
        assert g, "the guide's number"
        self.assertEqual(int(g.group(1)), int(m.group(1)), "the guide's floor is the code's")
        small = _body(self.viewer, "function figureTooSmall(img: Element): boolean {", "}")
        self.assertIn("return b !== null && (b.w < FIGOPEN_MIN_PX || b.h < FIGOPEN_MIN_PX);", small, "either side under the floor")

    def test_the_builder_refuses_the_floor_the_empty_target_and_the_link_and_puts_the_button_after_a_link_holding_the_picture_alone(self):
        build = _body(self.viewer, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "}")
        self.assertIn("if (figureTooSmall(img)) return false;", build, "the floor, read from the loaded picture")
        self.assertIn("if (figureTarget(img, filePath) === null) return false;", build, "nothing to open: a data: picture, no source")
        self.assertIn("return linkAbove(anchor) === null;", build, "a link holding more than the picture")
        decide = _body(self.viewer, "function decideFigureControl(img: Element, filePath: string): void {", "}")
        self.assertIn("const anchor = figureAnchor(img);", decide)
        self.assertIn("if (standing) { if (!want) removeFigureControl(standing); else dressFigureControl(standing, target); return; }", decide, "the one place a control is added or removed, a standing one re-dressed from the target read at the decision (the spelling: a sentence pin)")
        self.assertLess(build.index("figureTooSmall"), build.index("linkAbove"))
        above = _body(self.viewer, "function linkAbove(anchor: Element): Element | null {", "}")
        self.assertIn("return p ? figureLinkOf(p) : null;", above, "a link of the click's own set: to a file, a web address or a section, never a dead one or a named target (the one predicate, figureLinkOf; a sentence pin)")
        around = _body(self.viewer, "function linkAround(p: Element, a: Element): boolean {", "}")
        self.assertIn('return p.localName === "a" && p.children.length === 1 && p.children[0] === a && (p.textContent || "").trim() === "";', around,
                      "a link holding the picture alone is climbed: the button lands after the link, and the picture keeps it")

    def test_a_plain_click_opens_a_small_picture_no_link_holds_and_follows_a_link_that_holds_it(self):
        start = self.viewer.index("const openFigure = (img: Element, ev: MouseEvent): void => {")
        end = self.viewer.index("\n  });\n", self.viewer.index("const img = bareFigureOf(t, body);", start))
        click = self.viewer[start:end]
        self.assertIn("if (!target) return;", click, "a data: picture does not open: no target")
        self.assertIn("if (!img || figureLinkOf(img)) return;", click, "inside a link of the click's own set the click is the link's: the one predicate (an anchor with an href, a URL, section or path link; a sentence pin)")
        self.assertIn("openFigure(img, ev);", click)
        self.assertNotIn("figureTooSmall", click, "the click reads no size: a small picture no link holds opens")
        self.assertNotIn("FIGOPEN_MIN_PX", click)

    def test_a_dead_link_or_a_named_target_leaves_the_plain_click_to_the_picture_which_opens(self):
        """The guide's clause: a link with no address left, or an anchor that only marks a place, leaves the click to the
        picture. The figure listener yields to linkOf's links (a path link, a web address the viewer dressed, a section link)
        and to an anchor with an href, the one set FIGURE_LINK_SET spells; a dead anchor (file-view-links.ts DEAD_LINK_CLASS,
        its href taken off) and a named target (`<a id>`, never dressed unless it still carries the plain `xlink:href` of a
        split svg anchor, which was a link and is dressed dead) are neither, so the plain click reaches openFigure, and the
        control and the picture's tooltip stand there too (linkAbove and dressFigureTitle read the same predicate, figureLinkOf;
        the file review's round 12, correctness-1 with ui-1), which the sentence's carve-out after its "four kinds" says."""
        link_of = _body(self.viewer, "const linkOf = (t: Element | null): HTMLElement | null => {", "  };")
        self.assertIn("t.closest('[data-act=\"openpath\"], a.' + URL_LINK_CLASS + \", a.\" + FRAG_LINK_CLASS)", link_of, "linkOf's selector: the three dressed links")
        self.assertNotIn("DEAD_LINK_CLASS", link_of, "a dead anchor is none of them")
        self.assertNotIn("fv-dead", link_of)
        links = _read("ui", "webview", "file-view-links.ts")
        self.assertIn('export const DEAD_LINK_CLASS = "fv-dead";', links)
        self.assertIn('if ((a.hasAttribute("name") || a.hasAttribute("id")) && !a.hasAttribute("xlink:href")) return;', links,
                      "a named target is never dressed, and keeps no href (the one exception, a target still carrying the plain "
                      "xlink:href the fence pass's re-parse leaves on a split svg anchor, is dressed dead: it was a link)")
        self.assertIn("a picture inside a link that holds more than the picture (a caption beside it), where a click follows the link (a link "
                      "with no address left, or an anchor that only marks a place, is not a link a click can follow, so a picture inside it "
                      "keeps its button and its tooltip, and a plain click opens it), while a picture that is all its link holds keeps its "
                      "button beside the link.", self.links)
        above = _body(self.viewer, "function linkAbove(anchor: Element): Element | null {", "}")
        self.assertIn("return p ? figureLinkOf(p) : null;", above, "the button's exclusion reads the click's own set, so a button stands inside such an anchor, after the picture (a sentence pin)")
        self.assertIn("export const FIGURE_LINK_SET = 'a[href], a.' + URL_LINK_CLASS + ', a.' + FRAG_LINK_CLASS + ', [data-act=\"openpath\"]';", self.viewer, "the set, one selector (a sentence pin)")
        set_line = next(line for line in self.viewer.splitlines() if line.startswith("export const FIGURE_LINK_SET"))
        self.assertNotIn("DEAD_LINK_CLASS", set_line, "a dead anchor is not in it (a property pin on the set's line: it names no dead class)")
        self.assertNotIn("fv-dead", set_line, "nor the class by its literal (a property pin)")


if __name__ == "__main__":
    unittest.main()
