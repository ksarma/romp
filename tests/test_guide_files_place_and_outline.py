#!/usr/bin/env python3
"""The guide's Files and Waiting on you sections say six things Slice 6 of plans/markdown-viewer.md made true, and
the viewer, the Files pane and the todo surfaces do them.

The file takes the keyboard when it opens, so PageDown and Space scroll it with no click first, and a box the person
was typing in keeps the keyboard (item 1: the body's tabIndex and takeKeyboard's gate on the active element); the
Outline button above a rendered file lists the file's headings and a pick scrolls the heading to the top, a closed
fold opened on the way (item 2: the button's label, the pick through the fragment landing); a file reopened from the
Files pane's Recent list opens at the place it was left (item 3: the row hands its stored place back and the pane
writes the place the viewer hands it on leaving); a line or a section written after a path in a todo's text or
detail opens the file there, from the chat's todo card and from the Waiting on you pane alike, and a missing section
is named in the notice bar (item 4: the walks' targetSuffix option, the relay's `at`, the viewer's notice); and a
change on disk while the Comments panel is closed raises a line above the text with a Reload that keeps the place
(item 5: the probe's two events, the bar's words, the button through fetchFile). Each clause is pinned flattened, so
a rewrap survives, and cross-checked against the source that keeps it; the clauses other guide pins read in the same
paragraphs and sections (the chip sentence of tests/test_guide_todo_file_chip.py, the hard-wrapped opening lines of
tests/test_files_pane.py) are re-read here unchanged, so an edit that moves one fails in one place and not two. The
guide's word "outline" also names the sessions pane, so the Outline sentence says "the file's headings" and a pin
holds it to that. Synthetic: only the repo's own text.
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


RECENT = ("When no file is open, the pane lists the files most recently open here; click one to open it again, and "
          "the file opens at the place you left it.")
KEYBOARD = ("The file takes the keyboard when it opens, so PageDown and Space scroll it at once; a box you were typing "
            "in keeps the keyboard.")
DISK = ("When a file changes on disk while you read it with the Comments panel closed, a line above the text says so "
        "the next time you return to the dashboard, and **Reload** reads it again with your place kept.")
OUTLINE = ("The **Outline** button above a rendered file lists the file's headings; pick one and the view scrolls to "
           "put it at the top, opening a closed fold around it.")
TODO_TARGET = ("A line or a section written after a path in a todo's text or detail (`docs/report.md:12`, "
               "`docs/report.md#results`) opens the file there too; a section the file does not have leaves the file "
               "at its top, with a notice naming the section.")
WAITING = ("click it and the file opens in the Files pane, which comes forward if it was closed; a line or a section "
           "written after the path (`docs/report.md:12`, `docs/report.md#results`) opens the file at it.")


class TheGuideSaysSo(unittest.TestCase):
    def setUp(self):
        guide = _read("docs", "guide.md")
        self.files = _section(guide, "Files")
        self.waiting = _flat(_section(guide, "Waiting on you"))
        self.opening = _paragraph(self.files, "The Files pane holds the file viewer")
        self.place = _paragraph(self.files, "**Your place in the file.**")
        self.markdown = _paragraph(self.files, "**How a markdown file reads.**")
        self.links = _paragraph(self.files, "**Links in a file.**")

    def test_a_recent_row_reopens_the_file_at_the_place_it_was_left(self):
        self.assertIn(RECENT, self.opening)

    def test_the_file_takes_the_keyboard_and_a_box_being_typed_in_keeps_it(self):
        self.assertIn(KEYBOARD, self.place)

    def test_a_change_on_disk_raises_a_line_above_the_text_and_reload_keeps_the_place(self):
        self.assertIn(DISK, self.place)
        # the paragraph's rule for where a notice sits comes first; the bar is one of those notices
        self.assertLess(self.place.index("sits above the file's text"), self.place.index(DISK))
        self.assertLess(self.place.index(KEYBOARD), self.place.index(DISK))

    def test_the_outline_button_lists_the_files_headings_and_a_pick_lands_one_at_the_top(self):
        self.assertIn(OUTLINE, self.markdown)
        # "the outline" is also the sessions pane (the guide's "### The outline"): the sentence says whose headings
        self.assertIn("the file's headings", OUTLINE)
        self.assertLess(self.markdown.index(OUTLINE), self.markdown.index("The printed page leaves out"))

    def test_a_todo_target_opens_the_file_there_and_a_missing_section_is_named(self):
        self.assertIn(TODO_TARGET, self.links)
        # after the in-file `:line` rule and its past-the-end sentence, which the clause extends to a todo
        self.assertLess(self.links.index("scrolls the Raw view to that line"), self.links.index(TODO_TARGET))
        self.assertLess(self.links.index("lands on the last line, with a notice saying so."), self.links.index(TODO_TARGET))

    def test_the_waiting_on_you_section_says_the_same_of_its_links(self):
        self.assertIn(WAITING, self.waiting)

    def test_the_clauses_other_pins_read_stand_where_they_were(self):
        # tests/test_guide_todo_file_chip.py's chip sentence, unbroken by the target clause before it
        self.assertIn("Click the chip and the file opens the same way; a **Send to session** from that file can then "
                      "answer the todo (see Files).", self.waiting)
        self.assertLess(self.waiting.index(WAITING), self.waiting.index("Click the chip and the file opens the same way"))
        # tests/test_files_pane.py reads the opening paragraph's folder lines with their hard wraps; the Recent clause
        # sits after them and rewrapped none of them
        raw = _read("docs", "guide.md")
        self.assertIn("The folder under the chat (the session's working directory) opens a\nlisting of that folder by "
                      "the same rule", raw)
        self.assertIn("otherwise over the feed. Pick a file in the listing and\nit opens where the listing is.", raw)
        self.assertLess(raw.index("it opens where the listing is."), raw.index("click one to open it again, and the file"))


class TheViewerDoesIt(unittest.TestCase):
    """Each clause against the source that keeps it, so a body that stops being a Tab stop, a relabelled button, a
    dropped notice or a walk that no longer reads a target fails here beside the prose."""

    def setUp(self):
        self.viewer = _read("ui", "webview", "file-view.ts")

    def test_the_body_is_a_tab_stop_and_takes_the_keyboard_unless_a_box_holds_it(self):
        self.assertIn("\n  body.tabIndex = 0;\n", self.viewer)
        self.assertRegex(self.viewer, re.compile(r"^  const takeKeyboard = \(\): void => \{$", re.M))
        gate = self.viewer[self.viewer.index("const takeKeyboard = (): void => {"):]
        gate = gate[:gate.index("\n  };")]
        # the gate: nothing, the document's body or a control in the viewer's own bar yields; a box being typed in keeps it
        self.assertIn("if (a && a !== document.body && !bar.contains(a)) return;", gate)
        self.assertIn("body.focus({ preventScroll: true });", gate)
        # the open's first landing takes it once; a reload's landing never (keyboardPending is spent)
        self.assertIn("const keyboardOnLanding = (): void => { if (!keyboardPending) return; keyboardPending = false; takeKeyboard(); };",
                      self.viewer)
        for sheet in ("styles.css", "feed.css"):
            css = _read("ui", "webview", sheet)
            self.assertIn("\n.fileview-body:focus { outline: none; }\n", css, sheet)
            self.assertIn("\n.fileview-body:focus-visible { outline: 1px solid var(--accent); outline-offset: -1px; }\n", css, sheet)

    def test_the_outline_button_wears_the_guides_label_and_a_pick_lands_through_the_fragment_landing(self):
        self.assertIn('export const OUTLINE_LABEL = "Outline";', self.viewer)
        self.assertIn("outlineBtn.textContent = OUTLINE_LABEL;", self.viewer)
        self.assertIn('outlineBtn.title = "The file\'s headings";', self.viewer)
        pick = self.viewer[self.viewer.index("const pick = (i: number): void => {"):]
        pick = pick[:pick.index("\n    };")]
        # the landing a `#` link uses: revealFragmentTarget opens a closed fold above the heading, then the scroll
        self.assertIn("scrollToFragment(body, id);", pick)
        self.assertIn("takeKeyboard();", pick, "the keyboard returns to the body, so PageDown reads on from the section")
        self.assertLess(pick.index("scrollToFragment(body, id);"), pick.index("takeKeyboard();"))
        fragment = self.viewer[self.viewer.index("function scrollToFragment("):]
        self.assertIn("revealFragmentTarget(", fragment[:1200])
        for sheet in ("styles.css", "feed.css"):
            self.assertRegex(_read("ui", "webview", sheet), re.compile(r"^\.fileview-outline \{", re.M), sheet)

    def test_a_recent_row_hands_its_place_back_and_the_pane_stores_the_place_the_viewer_hands_it(self):
        files = _read("ui", "webview", "files.ts")
        self.assertIn("openHere(r.path, r.sid, r.identity, null, null, r.place);", files)
        self.assertIn("onLeave: (p, sid, rec) => { recent = placeRecent(recent, p, sid, rec); writeStore(); },", files)
        self.assertIn("if (!openFileView(path, sid, { todoId, at, place })) return;", files)
        recent = _read("ui", "webview", "files-recent.ts")
        self.assertIn("export interface RecentFile { path: string; sid: string | null; identity: RecentIdentity | null; t: number; place: RecentPlace | null }",
                      recent)
        # the viewer's side: a record the host hands back seats on the open's first paint, an `at` open ignoring it
        self.assertIn("export type RememberedPlace = {", self.viewer)
        self.assertRegex(self.viewer, re.compile(r"^export function rememberedPlaceOf\(", re.M))
        self.assertRegex(self.viewer, re.compile(r"^export function placeFromRemembered\(", re.M))

    def test_a_todo_target_rides_the_link_from_both_surfaces_and_a_missing_section_is_named(self):
        links = _read("ui", "webview", "path-links.ts")
        self.assertIn("  targetSuffix?: boolean;", links)
        self.assertIn("export const FRAG_SUFFIX_RE = /^#(?!L\\d)([^\\s#]+)/;", links)
        self.assertRegex(links, re.compile(r"^export function linkTarget\(el: HTMLElement\): LinkTarget \| null \{", re.M))
        render = _read("ui", "webview", "render.ts")
        self.assertIn("function linkTodoLinePaths(node: HTMLElement, sid: string | null): void {\n  linkifyUrls(node);\n"
                      "  linkifyPathTokens(node, sid, undefined, { targetSuffix: true });\n}", render)
        self.assertIn("function linkTodoDetailPaths(node: HTMLElement, sid: string | null): void {\n  linkifyUrls(node);\n"
                      "  linkifyFileUris(node, undefined, undefined, undefined, undefined, sid, true, { targetSuffix: true });\n}", render)
        waiting = _read("ui", "webview", "waiting.ts")
        self.assertIn("function linkTodoPaths(node: HTMLElement, sid: string): void {\n  linkifyUrls(node);", waiting)
        self.assertIn("\n  if (!framed) return;\n  linkifyPathTokens(node, sid, undefined, { targetSuffix: true });\n}", waiting)
        # the shell rebuilds the relay's message field by field, so the target is copied on both branches
        shell = _read("kernel", "kernel.py")
        self.assertEqual(shell.count("at:m.at||null"), 2, "the Files branch and the feed branch forward the target")
        # the viewer's notice for a section the file does not have
        self.assertIn("noteBar('No section named \"' + shown + '\" in this file.');", self.viewer)

    def test_the_disk_bar_is_raised_on_the_readers_return_and_its_reload_keeps_the_place(self):
        self.assertIn('export const CHANGED_ON_DISK = "Changed on disk.";', self.viewer)
        self.assertIn("const bar2 = noteBar(CHANGED_ON_DISK);", self.viewer)
        self.assertIn('re.type = "button"; re.textContent = "Reload";', self.viewer)
        # the two events, the person's return to the dashboard: the window's focus and the document coming back to view
        self.assertIn('window.addEventListener("focus", onWindowFocus);', self.viewer)
        self.assertIn('document.addEventListener("visibilitychange", onVisibility);', self.viewer)
        # the button reloads through fetchFile, the path every reload takes, which is what keeps the reader's place
        click = self.viewer[self.viewer.index('re.title = "Read the file as it is now; your place is kept";'):]
        click = click[:click.index("bar2.appendChild(re);")]
        self.assertIn("fetchFile();", click)
        self.assertIn('re.textContent = "Reloading";', click, "the click is acknowledged before the landing")


if __name__ == "__main__":
    unittest.main()
