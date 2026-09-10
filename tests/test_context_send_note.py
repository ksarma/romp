#!/usr/bin/env python3
"""CONTEXT.md defines the note of a send, and the Send to session entry carries it (the arrivals follow-on, 2026-09-09).

The Send confirm's message preview gave way to a box for the person's own words (plans/file-review.md, decision 40).
The panel, the kernel and the comments log all call those words a note: the panel's Log says "Sent 2 comments and a
note", the request and the log's send entry carry `note`, and the kernel refuses "the note is N characters" over the
bound. CONTEXT.md, which pins the vocabulary the guide, the plan and a dozen tests read, said nothing about it: its
File comment entry lists "note" under _Avoid_ (a file comment is never a note), and its Send to session entry still
described a send as the unsent comments, replies and decisions alone. Meanwhile the storage format already uses a
`note` field for a comment's or a reply's BODY (tools/file-comments-host.mjs, requireNote), so the one field name
means two things across the feature's own API. This module pins the entry that settles it: a note belongs to one
send, not to the file; it is the first paragraph after the header, before the comments; a note alone still sends;
the format's `note` on a comment is that comment's body, not this. Each claim is cross-checked against the source
that makes it true, reading kernel/kernel.py, the webview, the host and the guide as TEXT (no import, so no state
root and no side effects). Synthetic: only the repo's text.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

TERM = "Note (of a send)"


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
    return _flat(re.sub(r"^_Avoid_:.*\Z", "", entry, flags=re.M | re.S))


def _avoid_words(entry):
    """The words the entry lists under _Avoid_, across every line the list wraps onto, parentheticals dropped."""
    avoid = re.search(r"^_Avoid_:(.*)\Z", entry, re.S | re.M)
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


class TheNoteEntry(unittest.TestCase):
    """CONTEXT.md's Note (of a send) entry: where it sits, what it says, what it tells the reader apart from."""

    def setUp(self):
        self.context = _read("CONTEXT.md")
        self.entry = _entry(self.context, TERM)
        self.definition = _definition(self.entry)

    def test_the_entry_sits_in_the_file_comments_section_below_the_entries_that_point_at_it(self):
        # the File comment entry's Avoid line says "the Note entry below": it must be below, in the same section
        section_start = self.context.index("### File comments and changes")
        section_end = self.context.index("### Pre-existing attention vocabulary")
        at = self.context.index("**%s**:" % TERM)
        self.assertLess(section_start, at)
        self.assertLess(at, section_end)
        self.assertLess(self.context.index("**File comment**:"), at)
        self.assertLess(self.context.index("**Send to session**:"), at)

    def test_the_definition_places_the_note_in_the_message(self):
        self.assertIn("The person's own words, typed in the Send confirm's box and carried by that one send: the first "
                      "paragraph of the message after its header line, unlabeled, before the comments.", self.definition)

    def test_the_definition_says_a_note_alone_still_sends(self):
        self.assertIn("Optional; a note alone still sends.", self.definition)

    def test_the_definition_tells_a_note_from_a_file_comment(self):
        self.assertIn("It belongs to the send, not to the file: it is not stored beside the file, names no passage, "
                      "takes no reply, and is never a file comment; the comments log's send entry records it.",
                      self.definition)

    def test_the_definition_tells_the_field_from_the_formats_field_and_the_note_from_the_acknowledgment(self):
        self.assertIn("The storage format's `note` field on a comment or a reply is that comment's body, not this.",
                      self.definition)
        self.assertIn("The panel's acknowledgment after a send (Sent to <session> at <time>, or Queued for <session>) "
                      "is not a note either.", self.definition)

    def test_the_avoid_list(self):
        self.assertEqual(_avoid_words(self.entry), ["message", "comment"])

    def test_the_definition_uses_no_word_the_neighbouring_entries_avoid(self):
        # "note" is the term itself; "ask" is skipped as the guide tests skip it (a verb ordinary English may need)
        for term, skip in (("File comment", {"note"}), ("User todo", {"ask"}), ("Comments log", set())):
            for word in _avoid_words(_entry(self.context, term)):
                if word in skip:
                    continue
                self.assertNotRegex(self.definition, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                    "the Note entry says %r; the %s entry avoids it" % (word, term))


class AFileCommentIsStillNeverANote(unittest.TestCase):
    """The File comment entry keeps "note" under _Avoid_ (the premise tests/test_guide_files_comment_vocabulary.py and
    tools/file-review-plan-kind-cue.test.mjs rest on), and its parenthetical sends the reader to the new entry."""

    def setUp(self):
        self.entry = _entry(_read("CONTEXT.md"), "File comment")

    def test_note_stays_on_the_avoid_list_with_its_neighbours(self):
        self.assertEqual(_avoid_words(self.entry), ["thread", "annotation", "note", "review comment"])

    def test_the_parenthetical_points_at_the_note_entry(self):
        self.assertIn("note (a note goes with one send and is never stored beside the file: the Note entry below)",
                      self.entry)


class SendToSessionCarriesTheNote(unittest.TestCase):
    """The Send to session entry says the note goes first and that a note alone sends, with its gesture sentence
    and its todo sentence (tests/test_context_send_to_session.py) unmoved."""

    def setUp(self):
        self.entry = _entry(_read("CONTEXT.md"), "Send to session")
        self.definition = _definition(self.entry)

    def test_the_note_sentence(self):
        self.assertIn("A note the person types in the confirm goes first in that message, after its header line and "
                      "before the comments, and a note with nothing else unsent still sends.", self.definition)

    def test_the_gesture_sentence_still_opens_the_entry(self):
        self.assertTrue(self.definition.startswith("The one gesture that hands a file's unsent comments, replies, and "
                                                   "decisions to the session that owns the file, as a single message "
                                                   "in the person's voice;"), self.definition)
        self.assertEqual(_avoid_words(self.entry), ["send review", "ping", "submit"])


class TheCodeMakesTheEntryTrue(unittest.TestCase):
    """Each claim of the entry against the source that makes it true."""

    def test_the_kernel_builder_places_the_note_after_the_header_before_the_comments(self):
        kernel = _read("kernel", "kernel.py")
        start = kernel.index("def _file_comments_message(path, comments, accepted, rejected, tracked, is_text, note=\"\"):")
        body = kernel[start:]
        body = body[:body.index("\ndef ", 1)]
        self.assertIn('nt = _neutralize_romp_markers(str(note or ""))', body)
        # the comments shape: the header line, then the note, then each comment
        header = body.index('lines = ["[obsidian-diff] I left %d comment%s on %s." % (n, "" if n == 1 else "s", ap), ""]')
        note = body.index("if nt:\n        lines += [nt, \"\"]", header)
        comment = body.index('lines.append("Comment %s (%s):"', note)
        self.assertLess(header, note)
        self.assertLess(note, comment)
        # a note alone still sends: the decisions-only shape carries it too, and the docstring says so
        self.assertIn("A note with no comments and no decisions still makes a message: the\n"
                      "    header, the note and the closing ask.", body)
        first = body.index('lines = ["[obsidian-diff] I went over %s." % ap, ""]')
        self.assertLess(first, body.index("if nt:\n            lines += [nt, \"\"]", first))

    def test_the_kernel_records_the_note_in_the_comments_logs_send_entry(self):
        kernel = _read("kernel", "kernel.py")
        self.assertIn('entry["note"] = _neutralize_romp_markers(note)', kernel)

    def test_the_webview_builder_does_the_same(self):
        model = _read("ui", "webview", "file-comments-model.ts")
        self.assertIn("  note?: string;", model)
        start = model.index("export function buildSendMessage(o: MessageOpts): string {")
        body = model[start:]
        body = body[:body.index("\n}\n", 1)]
        self.assertIn('const nt = neutralizeRompMarkers(o.note || "");', body)
        header = body.index('const lines: string[] = ["[obsidian-diff] I left " + n + " comment"')
        note = body.index('if (nt) lines.push(nt, "");', header)
        comment = body.index('lines.push("Comment " + neutralizeRompMarkers(c.id)', note)
        self.assertLess(header, note)
        self.assertLess(note, comment)
        first = body.index('const lines: string[] = ["[obsidian-diff] I went over " + ap + ".", ""];')
        self.assertLess(first, body.index('if (nt) lines.push(nt, "");', first))

    def test_the_formats_note_field_on_a_comment_is_its_body_and_the_logs_is_the_persons_words(self):
        host = _read("tools", "file-comments-host.mjs")
        # the comment and reply ops read `note` as the body they store beside the file
        self.assertIn("function requireNote(args) {\n  const note = args.note;", host)
        self.assertIn("const note = requireNote(args);", host)
        self.assertIn("const note = requireNote(ctx.args);", host)
        # the send entry of the comments log records the person's words under the same key
        self.assertIn("if (typeof a.note === 'string') fields.note = a.note;", host)

    def test_the_panel_shows_the_logged_note_and_names_the_acknowledgment_as_the_entry_does(self):
        panel = _read("ui", "webview", "file-comments.ts")
        self.assertIn('el("div", "fc-body fc-log-note", e.note as string)', panel)
        self.assertIn('reply.queued ? "Queued for " + who : "Sent to " + who + " at " + clock(Date.now())', panel)

    def test_the_guide_says_the_same_without_the_word(self):
        # the guide's Files section may not say "note" (tests/test_guide_files_comment_vocabulary.py reads the File
        # comment entry's Avoid list), so its Send to session paragraph says the thing instead
        send = _paragraph(_section(_read("docs", "guide.md"), "Files"), "**Send to session**")
        self.assertIn("with a box for anything you want to add in your own words, which go first in the message; "
                      "words alone send too.", send)

    def test_nothing_calls_the_acknowledgment_a_sent_note(self):
        # the entry says the panel's acknowledgment after a send is not a note; the plan, the model, the panel, the sheets and
        # their tests call it the acknowledgment (line), never "the sent note" in prose -- the field `sentNote` is an
        # identifier older than the entry and stays (the review's consolidation, 2026-09-09: the round wrote "the sent
        # note" in seven places across these files; the seen follow-on's rounds wrote it again in both sheets' comments on
        # the saved line and in the prose of four test modules, which this scan then took in)
        for parts in (("plans", "file-review.md"), ("ui", "webview", "file-comments-model.ts"), ("ui", "webview", "file-comments.ts"),
                      ("ui", "webview", "file-comments-send-note.test.ts"), ("ui", "webview", "file-comments-send-resolves.test.ts"),
                      ("docs", "guide.md"), ("ui", "webview", "styles.css"), ("ui", "webview", "feed.css"),
                      ("ui", "webview", "file-comments.test.ts"), ("ui", "webview", "file-comments-arrivals.test.ts"),
                      ("ui", "webview", "file-comments-arrivals-browser.test.ts"), ("ui", "webview", "file-comments-focus-verify-2.test.ts"),
                      ("ui", "webview", "feed-css-saved-line-head-dress.test.ts")):
            text = _read(*parts)
            hit = re.search(r"\bsent[ -]note\b", text, re.I)
            self.assertIsNone(hit, "%s calls the acknowledgment a note: %r"
                              % ("/".join(parts), text[max(0, hit.start() - 60):hit.end() + 40] if hit else None))


if __name__ == "__main__":
    unittest.main()
