#!/usr/bin/env python3
"""The guide's Files section says five things Slice 7 of plans/markdown-viewer.md made true, and the viewer does them.

A markdown file that cannot be shown as rendered Markdown shows its text as written, the way Raw shows it, under a line
that says so and names the error, with Rendered still chosen (item 1: `RENDER_FELL`, renderBody's catch, mode() reading
`renderFell`); a figure that cannot be loaded shows a line where the picture would be, naming the fact, the figure's
path and its alt text (item 2: `FIGURE_FAILED`, the body's capture-phase `error` listener, the label both text walks
skip); an empty file says so in place of its text and Edit still opens it (item 6: `EMPTY_FILE`, the line above the
empty root, the Edit gate unchanged); a file that is not UTF-8 on disk can be read but not edited, and a line above
the text says why (item 5: `LATIN1_NOTICE`, raised at the text landing off the served header); and a file with CR or
CRLF line endings cannot be edited while changes are pending (item 7: `CR_REFUSAL`, trackedRefusal keyed on any CR,
where the guide and the code named CRLF alone). Each sentence is pinned flattened, so a rewrap survives, in its place
among the sentences around it, and cross-checked against the exported constant that keeps its words: the constant's
exact export line, the line that shows it, and the phrases the guide's sentence and the constant share, read off the
source, so a wording change in either fails here beside the other. The clauses other guide pins read in the same
paragraphs (the Outline and changed-on-disk sentences of tests/test_guide_files_place_and_outline.py, the hard-wrapped
lines of tests/test_files_pane.py) are re-read unchanged, so an edit that moves one fails in one place and not two.
The panel's own row for a reload that failed (`BYTES_FAILED`, item 3) has no guide sentence: item 8 of the slice's
brief names five, so its export is held as a record pin alone. Synthetic: only the repo's own text.
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


def _constant(source, name):
    """The value of `export const <name> = "...";` in a TypeScript source, one line, one export."""
    found = re.findall(r'^export const %s = "(.*)";$' % re.escape(name), source, re.M)
    assert len(found) == 1, "%s is exported once as a string: %r" % (name, found)
    return found[0]


# The five sentences, flattened. Each carries words of the constant it describes (SHARED below), so the guide cannot
# say one thing and the viewer another without this module going red.
RENDER_FELL_SAYS = ("When a file cannot be shown as rendered Markdown, its text is shown as written, the way Raw shows "
                    "it, under a line that says so and names the error; **Rendered** stays chosen, and the next reload "
                    "or click of that button tries again.")
FIGURE_SAYS = ("A figure that cannot be loaded, because its file is missing or is not an image, shows a line where the "
               "picture would be: **Image failed to load**, then the figure's path as written in the file, and its alt "
               "text when it has one.")
EMPTY_SAYS = "An empty file says so in place of its text (**This file is empty**), and **Edit** still opens it."
LATIN1_SAYS = ("A file that is not UTF-8 on disk can be read but not edited, and a line above the text says why: a save "
               "would rewrite its bytes as UTF-8.")
CR_SAYS = ("A file with CR or CRLF line endings cannot be edited while changes are pending, because the editor rewrites "
           "its line endings, which would move them; accept or reject them first.")
# The words each guide sentence and its constant share, so the two are read against each other, not only each against
# its own pin.
SHARED = {
    "RENDER_FELL": (RENDER_FELL_SAYS, ("shown as rendered Markdown", "shown as written")),
    "FIGURE_FAILED": (FIGURE_SAYS, ("Image failed to load",)),
    "EMPTY_FILE": (EMPTY_SAYS, ("This file is empty",)),
    "LATIN1_NOTICE": (LATIN1_SAYS, ("not UTF-8 on disk", "a save would rewrite its bytes as UTF-8")),
    "CR_REFUSAL": (CR_SAYS, ("CR or CRLF line endings", "rewrites")),
}
# The constants' exact export lines (the slice's contract C5): a wording change fails here with the text in view.
EXPORTS = {
    "RENDER_FELL": 'export const RENDER_FELL = "This file could not be shown as rendered Markdown, so its text is shown as written";',
    "FIGURE_FAILED": 'export const FIGURE_FAILED = "Image failed to load:";',
    "EMPTY_FILE": 'export const EMPTY_FILE = "This file is empty.";',
    "LATIN1_NOTICE": ('export const LATIN1_NOTICE = "This file is not UTF-8 on disk, so it can be read here but not edited: '
                      'a save would rewrite its bytes as UTF-8.";'),
    "CR_REFUSAL": ('export const CR_REFUSAL = "The editor rewrites this file\'s CR or CRLF line endings as it loads the text, '
                   'and that would move the pending changes.";'),
}
# The neighbouring clauses other pins read, re-read here unchanged.
OUTLINE = ("The **Outline** button above a rendered file lists the file's headings; pick one and the view scrolls to "
           "put it at the top, opening a closed fold around it.")
DISK = ("When a file changes on disk while you read it with the Comments panel closed, a line above the text says so "
        "the next time you return to the dashboard, and **Reload** reads it again with your place kept.")


class TheGuideSaysSo(unittest.TestCase):
    def setUp(self):
        guide = _read("docs", "guide.md")
        self.raw = guide
        self.files = _section(guide, "Files")
        self.markdown = _paragraph(self.files, "**How a markdown file reads.**")
        self.figures = _paragraph(self.files, "**Figures.**")
        self.place = _paragraph(self.files, "**Your place in the file.**")
        self.edit = _paragraph(self.files, "**Edit** works")

    def test_a_render_that_fell_shows_the_text_as_written_under_a_line_and_rendered_stays_chosen(self):
        self.assertIn(RENDER_FELL_SAYS, self.markdown)
        # after the print sentence, which closed the paragraph before this slice; the Outline sentence before both
        self.assertLess(self.markdown.index("The printed page leaves out"), self.markdown.index(RENDER_FELL_SAYS))
        self.assertTrue(self.markdown.endswith(RENDER_FELL_SAYS), "the sentence closes the paragraph")
        self.assertIn("**Rendered**", RENDER_FELL_SAYS, "the button is named as the guide names buttons")

    def test_a_failed_figure_shows_a_line_naming_its_path_where_the_picture_would_be(self):
        self.assertIn(FIGURE_SAYS, self.figures)
        self.assertLess(self.figures.index("comment on the file as a whole instead."), self.figures.index(FIGURE_SAYS))
        self.assertTrue(self.figures.endswith(FIGURE_SAYS), "the sentence closes the paragraph")

    def test_an_empty_file_says_so_in_place_of_its_text_and_edit_still_opens_it(self):
        self.assertIn(EMPTY_SAYS, self.place)
        # after the changed-on-disk sentence, the paragraph's last before this slice; the notices rule stands before both
        self.assertLess(self.place.index("sits above the file's text"), self.place.index(EMPTY_SAYS))
        self.assertLess(self.place.index(DISK), self.place.index(EMPTY_SAYS))
        self.assertTrue(self.place.endswith(EMPTY_SAYS), "the sentence closes the paragraph")

    def test_a_file_that_is_not_utf8_can_be_read_but_not_edited_and_a_line_says_why(self):
        self.assertIn(LATIN1_SAYS, self.edit)
        self.assertLess(self.edit.index(CR_SAYS), self.edit.index(LATIN1_SAYS))
        self.assertTrue(self.edit.endswith(LATIN1_SAYS), "the sentence closes the paragraph")

    def test_the_line_ending_refusal_names_cr_and_crlf(self):
        self.assertIn(CR_SAYS, self.edit)
        # the sentence the slice widened: it named CRLF alone, and a CR-only file's pending changes went into the editor
        self.assertNotIn("A file with CRLF line endings", self.edit)
        self.assertLess(self.edit.index("The session's own track-edit keeps working throughout."), self.edit.index(CR_SAYS))

    def test_the_clauses_other_pins_read_stand_where_they_were(self):
        # tests/test_guide_files_place_and_outline.py's Outline and changed-on-disk sentences, in their paragraphs
        self.assertIn(OUTLINE, self.markdown)
        self.assertLess(self.markdown.index(OUTLINE), self.markdown.index("The printed page leaves out"))
        self.assertIn(DISK, self.place)
        # tests/test_files_pane.py reads the opening paragraph's folder lines with their hard wraps; nothing here touched them
        self.assertIn("The folder under the chat (the session's working directory) opens a\nlisting of that folder by "
                      "the same rule", self.raw)
        self.assertIn("otherwise over the feed. Pick a file in the listing and\nit opens where the listing is.", self.raw)
        # the Edit paragraph's lines before the widened sentence keep their hard wraps byte for byte
        self.assertIn("the panel says when the file changed under you. The session's own track-edit keeps working\n"
                      "throughout. A file with CR or CRLF line endings", self.raw)


class TheViewerDoesIt(unittest.TestCase):
    """Each sentence against the constant that keeps its words and the line that shows it, so a reworded notice, a
    relabelled line or a moved raise fails here beside the prose."""

    def setUp(self):
        self.viewer = _read("ui", "webview", "file-view.ts")

    def test_each_guide_sentence_shares_its_words_with_the_constant_the_viewer_shows(self):
        for name, (sentence, phrases) in SHARED.items():
            self.assertIn(EXPORTS[name], self.viewer, name)
            value = _constant(self.viewer, name)
            for phrase in phrases:
                self.assertIn(phrase, value, "%s carries %r" % (name, phrase))
                self.assertIn(phrase, sentence, "the guide's sentence for %s carries %r" % (name, phrase))

    def test_a_render_that_fell_paints_the_line_over_raw_rows_and_mode_answers_raw(self):
        # the line: the constant, the error's message in parentheses, then the period, the body's first child
        self.assertIn('why.textContent = RENDER_FELL + " (" + msg + ").";', self.viewer)
        # the message through fellMessage (an Error's message with marked's appended report-this sentence cut, else the
        # value's string), the line then the rows, and the record once the fallback stands (the Slice 7 review's round 2)
        self.assertIn("const fell = fellMessage(err);", self.viewer)
        self.assertIn("body.replaceChildren(renderFellLine(fell), codeBlock(text, path, true));", self.viewer)
        self.assertIn("renderFell = fell;", self.viewer)
        self.assertNotIn("renderFell = err instanceof Error", self.viewer, "no catch records the raw message before its fallback swap")
        # mdBlock keeps no fallback of its own: the old catch wrote the source into the box as one paragraph
        self.assertNotIn("box.textContent = text;", self.viewer)
        # "the way Raw shows it": the seam's word for the body follows what was painted, so the panel pairs over the rows
        self.assertIn('mode: () => (isImage || isPdf) && !(svgSource && svgText !== null) ? "media" : isMd && fmt.md === '
                      '"rendered" && renderFell === null ? "rendered" : "raw",', self.viewer)

    def test_a_failed_figure_wears_a_label_the_body_hears_the_error_for_and_both_text_walks_skip(self):
        # the source the label names: the candidate the browser asked for as the author wrote it (failedSource: pictureDest's rule
        # for the img's own src, the srcset candidate in currentSrc otherwise), a data: source cut to its head (shownSource); the
        # Slice 7 review's round 1
        # ...and the words in the source's place when the figure names none (an empty destination; the review's round 2)
        self.assertIn('const src = failedSource(img);', self.viewer)
        self.assertIn('return FIGURE_FAILED + " " + (src ? shownSource(src) : FIGURE_NO_SOURCE) + (alt ? " (" + alt + ")" : "");', self.viewer)
        self.assertIn('const FIGURE_NO_SOURCE = "the source is empty";', self.viewer)
        # the img's error does not bubble: one capture-phase listener on the body per open, its twin removing the label
        self.assertIn('body.addEventListener("error", onError, true);', self.viewer)
        self.assertIn('const FIGERR_MARK = "data-fv-figerr";', self.viewer)
        # "where the picture would be": the label is the note's neighbour, not its text, to the pairing and the place
        self.assertRegex(_read("ui", "webview", "anchor-map.ts"), re.compile(r'^  "fv-figerr",', re.M))
        self.assertIn('const CONTROL_CLASSES = ["code-copy", "katex", "md-fnback", "md-frontmatter-head", "fv-gate", "fv-figerr"];',
                      _read("ui", "webview", "reader-place.ts"))
        for sheet in ("styles.css", "feed.css"):
            self.assertRegex(_read("ui", "webview", sheet), re.compile(r"^\.fileview-md \.fv-figerr \{", re.M), sheet)

    def test_an_empty_file_gets_the_line_above_its_empty_root_in_both_viewers_with_edit_shown(self):
        self.assertIn("why.textContent = EMPTY_FILE;", self.viewer)
        self.assertEqual(self.viewer.count('if (text === "") body.prepend(emptyFileLine());'), 2,
                         "the local viewer's paint and the URL viewer's")
        # "Edit still opens it": the gate reads null, never ""; an empty file's text is "" at the landing
        self.assertIn("editBtn.hidden = editing || text === null || !isText || !mtimeNs;", self.viewer)

    def test_a_latin1_file_raises_the_line_off_the_served_header_before_the_targets_notice(self):
        # the verdict reads the header's VALUE "0" on a text answer, never a negation of isText (an image carries no header)
        self.assertIn('v.notUtf8 = ct.startsWith("text/plain") && r.headers.get("X-Romp-Text-Utf8") === "0";', self.viewer)
        # raised at the text landing before landTarget, so an open's own notice takes the row; a reload's landing has none
        self.assertRegex(self.viewer, re.compile(r"^      if \(notUtf8\) noteBar\(LATIN1_NOTICE\);\n      landTarget\(\);", re.M))
        self.assertEqual(self.viewer.count("noteBar(LATIN1_NOTICE)"), 1, "one raise site")

    def test_the_editor_refuses_pending_changes_over_any_cr(self):
        self.assertIn('if (text !== null && /\\r/.test(text)) return CR_REFUSAL + " " + pending.refusal;', self.viewer)
        self.assertNotIn("CRLF_REFUSAL", self.viewer, "the CRLF-only refusal is gone")

    def test_record_pin_the_panels_row_for_a_reload_that_failed_carries_the_seams_words(self):
        # item 3's row has no guide sentence (the slice's item 8 names five); its words are held here as a record
        panel = _read("ui", "webview", "file-comments.ts")
        self.assertIn('export const BYTES_FAILED = "The file could not be read again";', panel)
        self.assertIn('this.errors.set("bytes", { text: BYTES_FAILED + " (" + words + ")" + BYTES_FAILED_TAIL, reload: true });',
                      panel)


if __name__ == "__main__":
    unittest.main()
