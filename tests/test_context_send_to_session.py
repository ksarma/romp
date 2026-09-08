#!/usr/bin/env python3
"""CONTEXT.md's Send to session and User todo entries say what the todo-file follow-on (2026-09-07) built.

CONTEXT.md pins the vocabulary the guide, the reference and the plan use (plans/file-review.md reads its
terminology from it), and a dozen tests read it as that source. Its Send to session entry was written when
a send could answer only the user todo the file was opened from. The follow-on made a send answer any open
todo of the session that names the file, however the file was opened: the kernel lists those todos on every
`fileCommentsResult` (_user_todos_naming_file) and the panel offers them (todoChoices). The guide, the
reference, the plan and the code comments moved with it while CONTEXT.md kept the old sentence, and no test
read that sentence, so the drift failed nothing (the review, 2026-09-07). This module holds both entries to
the follow-on and cross-checks each claim against the source that makes it true, reading kernel/kernel.py and
the webview as TEXT (no import, so no state root and no side effects). It also pins what must NOT have moved:
the clearing rule docs/adr/0001 rests on (answer, dismiss, withdraw; never inference) and the Authority tier
entry, since a sentence was added to the User todo entry that carries them. Synthetic: only the repo's text.
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


def _entry(context_md, term):
    """The body of CONTEXT.md's `**term**:` entry (definition lines and the _Avoid_ line), up to the blank line."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    return m.group(1)


def _definition(entry):
    """The entry without its _Avoid_ line: the sentences that define the term."""
    return _flat(re.sub(r"^_Avoid_:.*$", "", entry, flags=re.M))


def _avoid_words(entry):
    """The words the entry lists under _Avoid_, parentheticals dropped."""
    avoid = re.search(r"^_Avoid_:(.*)$", entry, re.M)
    assert avoid, "the entry has no _Avoid_ line"
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [w.strip() for w in bare.split(",") if w.strip()]


def _section(md, heading):
    """The body of one `### heading` of the guide up to the next heading of any level."""
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _paragraph(section, lead):
    """The blank-line paragraph of `section` that starts with `lead`, collapsed."""
    for p in re.split(r"\n\s*\n", section):
        if p.lstrip().startswith(lead):
            return _flat(p)
    raise AssertionError("no paragraph starts with %r" % lead)


class SendToSessionAnswersATodoNamingTheFile(unittest.TestCase):
    """The Send to session entry says a send may answer a todo that names the file, however the file was
    opened, or the todo the file was opened from, one per send; and the code does both."""

    def setUp(self):
        context = _read("CONTEXT.md")
        self.entry = _entry(context, "Send to session")
        self.definition = _definition(self.entry)
        self.todo_avoid = _avoid_words(_entry(context, "User todo"))

    def test_the_entry_names_both_kinds_of_todo_a_send_may_answer(self):
        self.assertIn("it may also answer one of that session's open user todos: a todo that names the file, "
                      "however the file was opened, or the todo the file was opened from.", self.definition)

    def test_the_opened_from_only_sentence_is_gone(self):
        # the pre-follow-on definition: a send could answer only the todo the file was opened from
        self.assertNotIn("answer the user todo the file was opened from", self.definition)

    def test_the_gesture_itself_is_still_defined(self):
        self.assertIn("The one gesture that hands a file's unsent comments, replies, and decisions to the session "
                      "that owns the file, as a single message in the person's voice;", self.definition)
        self.assertEqual(_avoid_words(self.entry), ["send review", "ping", "submit"])

    def test_the_definition_uses_no_user_todo_avoid_word(self):
        # "ask" is skipped as the guide tests skip it (a verb ordinary English may need); the rest are noun phrases
        self.assertIn("request", self.todo_avoid)
        for word in self.todo_avoid:
            if word == "ask":
                continue
            self.assertNotRegex(self.definition, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                "the Send to session entry says %r; the User todo entry avoids it" % word)

    def test_the_kernel_lists_the_open_todos_naming_the_file_on_every_reply(self):
        kernel = _read("kernel", "kernel.py")
        # the helper: the session's OPEN todos, matched on the structured `file` alone
        self.assertIn("def _user_todos_naming_file(sid, real):", kernel)
        body = kernel[kernel.index("def _user_todos_naming_file(sid, real):"):]
        body = body[:body.index("\ndef ", 1)]
        self.assertIn("for t in _open_user_todos(str(sid)):", body)
        self.assertIn('f = str(t.get("file") or "")', body)
        # attached to every successful file-comments reply, with no reference to how the file was opened
        self.assertIn('rep["todos"] = _user_todos_naming_file(msg.get("sid"), p)', kernel)

    def test_the_panel_offers_the_status_todos_and_the_opened_from_todo_and_sends_one(self):
        model = _read("ui", "webview", "file-comments-model.ts")
        panel = _read("ui", "webview", "file-comments.ts")
        self.assertRegex(model, r"todos\?: Array<\{ id: string; text: string \}> \| null;")
        # ctx.todoId is the todo the file was opened from; the status's todos are the ones naming the file
        self.assertIn("todoChoices(this.ctx.todoId, s, (id) => answeredTodos.has(id))", panel)
        self.assertIn("const todoId = this.chosenTodoId(s);", panel)

    def test_the_guide_says_the_same(self):
        send = _paragraph(_section(_read("docs", "guide.md"), "Files"), "**Send to session**")
        self.assertIn("When a todo under Waiting on you names this file, or you opened the file from a todo, a checkbox "
                      "answers that todo with the same send;", send)


class AUserTodoMayNameItsFile(unittest.TestCase):
    """The User todo entry says a todo may name the file it is about, and its clearing rule did not move."""

    def setUp(self):
        context = _read("CONTEXT.md")
        self.entry = _entry(context, "User todo")
        self.definition = _definition(self.entry)
        self.authority = _definition(_entry(context, "Authority tier"))

    def test_the_entry_says_a_todo_may_name_its_file(self):
        self.assertIn("held open while the agent keeps working on whatever else it can. It may name the file it is "
                      "about.", self.definition)

    def test_the_clearing_rule_is_unchanged(self):
        # docs/adr/0001: an authority tier the judges cannot clear; nothing here may let inference clear a todo
        self.assertIn("Cleared only by answer, dismiss, or withdraw; never by inference.", self.definition)
        self.assertIn("user todos are the second (cleared only by answer, dismiss, or withdraw).", self.authority)
        self.assertTrue(_read("docs", "adr", "0001-user-todos-authority-tier.md")
                        .startswith("# User todos are an authority tier the judges cannot clear"))

    def test_the_avoid_list_is_unchanged(self):
        self.assertEqual(_avoid_words(self.entry), ["ask", "request", "user task"])

    def test_the_definition_uses_none_of_its_own_avoid_words(self):
        for word in _avoid_words(self.entry):
            if word == "ask":
                continue
            self.assertNotRegex(self.definition, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                "the User todo entry says %r, which it lists under _Avoid_" % word)

    def test_the_record_carries_the_file(self):
        kernel = _read("kernel", "kernel.py")
        self.assertIn("record may name the FILE it is about (`file`", kernel)
        self.assertIn("def _user_todo_file(value, sid):", kernel)


if __name__ == "__main__":
    unittest.main()
