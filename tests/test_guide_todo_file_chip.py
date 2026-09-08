#!/usr/bin/env python3
"""The guide says what the todo-file follow-on (2026-09-07) built, in CONTEXT.md's vocabulary, and the UI does it.

A user todo can now name its file in its record (`file`), the Waiting-on-you pane shows that file as a chip on the
row and in the Reply box, and a Send to session from the file answers the todo however the file was opened — from
the chip, from a path in the todo's text, from a chat link — with a checkbox for one todo and a row of choices when
several todos name the file. Before the follow-on the guide's Files section said the checkbox appears "when the
file was opened from a request under Waiting on you", which was both the old behaviour and CONTEXT.md's avoided
word for a user todo ("request"; the Waiting on you test reads that list from CONTEXT.md and this one reuses it).

Every claim is cross-checked against the source that makes it true: the pane's chip builder and its sheet for the
chip, the panel's confirm for the checkbox, the radio group and its "none" choice, so a renamed control or a dropped
chip fails here and the guide moves with it. Synthetic: no session data, only the repo's own text.
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
    """The blank-line paragraph of `section` that starts with `lead`, collapsed."""
    for p in re.split(r"\n\s*\n", section):
        if p.lstrip().startswith(lead):
            return _flat(p)
    raise AssertionError("no paragraph starts with %r" % lead)


def _avoid_words(context_md, term):
    """The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    avoid = re.search(r"^_Avoid_:(.*)$", m.group(1), re.M)
    assert avoid, "CONTEXT.md entry %r has no _Avoid_ line" % term
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [w.strip() for w in bare.split(",") if w.strip()]


class WaitingOnYouNamesTheChip(unittest.TestCase):
    """The Waiting on you section describes the chip the pane renders from the todo's `file`."""

    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Waiting on you"))
        self.waiting = _read("ui", "webview", "waiting.ts")
        self.css = _read("ui", "webview", "waiting-pane.css")

    def test_the_section_describes_the_chip_and_where_it_shows(self):
        self.assertIn("A todo that names its file also shows the file's name as a chip on the row and in the Reply "
                      "box, with the full path on hover; the session's own todo card in the chat shows the same chip. "
                      "Click the chip and the file opens the same way; a **Send to session** from that file can then "
                      "answer the todo (see Files).", self.section)

    def test_the_chat_card_builds_the_same_chip_and_the_sheet_dresses_it(self):
        # the sentence's second surface: render.ts's todoFileChip on the card's row and in its Reply modal, and the
        # `.ut-file` pill in styles.css — the chat page loads that sheet alone (render-todo-file-chip-sheet.test.ts
        # measures the pill; here the guide's claim is held to the two sources that make it true)
        render = _read("ui", "webview", "render.ts")
        self.assertIn('chip.classList.add("ut-file");', render)
        self.assertIn('if (t.file) txt.append(" ", todoFileChip(t.file, renderingSid || null));', render)
        self.assertIn('if (todoFile) d.append(" ", todoFileChip(todoFile, sid));', render)
        self.assertIn(".ut-file {", _read("ui", "webview", "styles.css"))

    def test_the_pane_builds_that_chip(self):
        # the basename as the label, the full path as the title, on the row and in the Reply modal
        self.assertRegex(self.waiting, r"function fileChip\(file: string, sid: string\): HTMLElement \{\n"
                                       r"\s*const base = file\.replace\(/\\/\+\$/, \"\"\)\.split\(\"/\"\)\.pop\(\) \|\| file;")
        self.assertIn("chip.title = file;", self.waiting)
        self.assertIn("if (w.todo.file) line.appendChild(fileChip(w.todo.file, w.sid));", self.waiting)
        self.assertIn("const chip = todoFile ? fileChip(todoFile, sid) : null;", self.waiting)
        self.assertIn(".wt-file{", self.css)

    def test_the_chip_opens_the_file_the_way_a_path_does(self):
        # openPathLink's span: the same data-act the linkified paths carry, so the same delegate posts the same viewFile
        self.assertIn('const chip = framed ? openPathLink(base, file, false, sid) : el("span", "");', self.waiting)
        self.assertIn('import { linkifyPathTokens, openPathLink } from "./path-links";', self.waiting)


class SendAnswersTheTodoThatNamedTheFile(unittest.TestCase):
    """The Files section's Send paragraph says a Send answers the todo however the file was opened, with the
    checkbox for one todo and a row of choices for several, in the todo vocabulary."""

    def setUp(self):
        self.files = _section(_read("docs", "guide.md"), "Files")
        self.send = _paragraph(self.files, "**Send to session**")
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.model = _read("ui", "webview", "file-comments-model.ts")
        self.avoid = _avoid_words(_read("CONTEXT.md"), "User todo")

    def test_the_paragraph_says_however_the_file_was_reached_and_names_both_controls(self):
        self.assertIn("When a todo under Waiting on you names this file, or you opened the file from a todo, a checkbox "
                      "answers that todo with the same send; when several todos name the file, a row of choices picks "
                      "the one to answer, or none.", self.send)
        self.assertIn("One send answers one todo; a todo that named several files is answered by the first, and later "
                      "sends no longer offer it.", self.send)

    def test_the_old_opened_from_only_sentence_is_gone(self):
        self.assertNotIn("opened from a request", self.send)
        self.assertNotIn("answers that request", self.send)
        self.assertNotIn("later sends show no checkbox", self.send)

    def test_the_paragraph_uses_no_user_todo_avoid_word(self):
        # "ask" is skipped as the Waiting on you test skips it (a verb the guide may need); the rest are noun phrases
        self.assertIn("request", self.avoid)
        for word in self.avoid:
            if word == "ask":
                continue
            self.assertNotRegex(self.send, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                "the Send paragraph says %r; CONTEXT.md avoids it" % word)

    def test_the_panel_offers_the_checkbox_from_the_status_and_the_row_of_choices(self):
        # the status lists the open todos naming the file; one is the checkbox, several the radio group with "none"
        self.assertRegex(self.model, r"todos\?: Array<\{ id: string; text: string \}> \| null;")
        self.assertIn("todoChoices(this.ctx.todoId, s, (id) => answeredTodos.has(id))", self.panel)
        self.assertIn('cb.type = "checkbox"; cb.checked = this.sendOpts.todo; cb.dataset.opt = "todo";', self.panel)
        self.assertIn('r.type = "radio"; r.name = "fc-todo"; r.value = c.id; r.checked = c.id === pick; r.dataset.opt = "todopick";',
                      self.panel)
        self.assertIn('{ id: "", label: "none", title: null }', self.panel)
        # one send answers one todo: the send names the one chosen, and a stamped one is offered no more
        self.assertIn("const todoId = this.chosenTodoId(s);", self.panel)
        self.assertIn("if (todoId && reply.todoStamped) answeredTodos.add(todoId);", self.panel)


if __name__ == "__main__":
    unittest.main()
