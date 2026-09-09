#!/usr/bin/env python3
"""File comments (plans/file-review.md) — the note the Send confirm's text box adds to a send (the user's
ruling, 2026-09-09).

The Send confirm used to show a preview of the message a send would carry; the user ruled the preview a
system message not worth showing and asked for a text box in its place, for anything they want to add in
their own words. The note travels in the fileCommentsSend request as `note` (optional text). The builder
places it as the first paragraph after the header line, unlabeled, in both shapes of the message: before
the comments, or before the accepted/rejected line. A note with no comments and no decisions still sends,
as the header, the note and the closing ask; the line saying nothing needs a reply is emitted only when
there is no note. The op trims the note, refuses one that is not text, refuses one longer than
_SEND_NOTE_MAX before anything else is asked or sent, neutralizes it like a comment body, and records it
on the log's send entry as `note` when it is non-empty. The webview's builder (ui/webview/file-comments-
model.ts, buildSendMessage) ports the text byte for byte and its parity test runs the kernel's builder, so
the two change together. The note's own refusals come after the consent gate (plans/file-review.md,
Security posture: every disk-writing verb checks the consent before any content check), so with dashboard
file editing off a note the op would refuse on its own account is refused as `editing-off` instead.

Synthetic only: the notes-api demo world, a placeholder sid, invented note text, temp dirs
(tests/test_kernel_file_comments_decisions_send.py's hermetic pattern).
"""
import json
import os
import re
import shutil
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
BIN = os.path.join(REPO, "bin")
HOST = os.path.join(REPO, "tools", "file-comments-host.mjs")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load — the kernel resolves its state root at import time, and only pytest
# runs conftest's floor (a bare unittest run would otherwise write REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_filecomments_note", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")
REPORT = "/TESTDIR/notes-api/docs/report.md"
ONE = [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"', "body": "Which cache? Say which."}]
NOTE = "Keep the measured numbers, and add the date of the run above the table."
HEADER = "[obsidian-diff] I went over %s.\n\n" % REPORT
ASK_AGAIN = ("When you have made more changes, ask me for another look the same way you asked for this one,\n"
             "naming the file.\n")
ASK_AGAIN_ADDRESSED = ("When you have addressed these, ask me for another look the same way you asked for this one,\n"
                       "naming the file.\n")
# The same marker probe tests/test_file_comments.py's marker tests use for a comment body: both comment
# openers, the bare goal-id form (its colon becomes a semicolon), a non-romp comment that stays
MARKED = ("see <!--romp-msg-id: 4--> and romp-goal-id: 3\n\n"
          "also <!--  romp-note: x --> and romp-goal-id : 5, but <!-- not ours --> stays")
NEUTRAL = ("see <!- -romp-msg-id: 4--> and romp-goal-id; 3\n\n"
           "also <!- -  romp-note: x --> and romp-goal-id ; 5, but <!-- not ours --> stays")


def message(comments=None, accepted=0, rejected=0, note="", path=REPORT, tracked=True, is_text=True):
    return km._file_comments_message(path, comments or [], accepted, rejected, tracked, is_text, note=note)


class TheNoteInTheMessage(unittest.TestCase):
    """The builder, byte for byte: the shared spec with the webview's builder, in every shape a note can ride."""

    def test_a_note_alone_is_the_header_the_note_and_the_closing_ask(self):
        self.assertEqual(message(note=NOTE), HEADER + NOTE + "\n\n" + ASK_AGAIN)

    def test_a_note_with_decisions_goes_before_the_decisions_line(self):
        self.assertEqual(message(accepted=3, rejected=1, note=NOTE),
                         HEADER + NOTE + "\n\n" + "I accepted 3 of your changes and rejected 1.\n\n" + ASK_AGAIN)

    def test_a_note_with_comments_goes_before_the_comments(self):
        self.assertEqual(message(ONE, note=NOTE),
                         "[obsidian-diff] I left 1 comment on %s.\n"
                         "\n"
                         "%s\n"
                         "\n"
                         "Comment 1781100000000-0 (on \"shipping the cache in v1.2\"):\n"
                         "Which cache? Say which.\n"
                         "\n"
                         "To respond:\n"
                         "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file %s --thread <id> --note \"<your reply>\"\n"
                         "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file %s --old \"<exact text>\" --new \"<replacement>\"\n"
                         "\n" % (REPORT, NOTE, REPORT, REPORT) + ASK_AGAIN_ADDRESSED)

    def test_a_note_with_comments_and_decisions_keeps_the_decisions_line_where_it_was(self):
        body = message(ONE, accepted=2, rejected=0, note=NOTE)
        self.assertTrue(body.startswith("[obsidian-diff] I left 1 comment on %s.\n\n%s\n\nComment 1781100000000-0 "
                                        % (REPORT, NOTE)), body)
        self.assertIn("Which cache? Say which.\n\nI accepted 2 of your changes and rejected 0.\n\nTo respond:\n", body)
        self.assertEqual(body.count(NOTE), 1)

    def test_the_line_saying_nothing_needs_a_reply_goes_only_without_a_note(self):
        self.assertIn("No comments this time, so nothing needs a reply.\n", message(accepted=3))
        self.assertIn("No comments this time, so nothing needs a reply.\n", message())
        for body in (message(note=NOTE), message(accepted=3, note=NOTE), message(ONE, note=NOTE)):
            self.assertNotIn("No comments this time", body)
            self.assertNotIn("nothing needs a reply", body)

    def test_without_a_note_every_shape_is_what_it_was(self):
        # the keyword is optional and empty by default, so callers that never learned of it get the same text;
        # None and "" are both no note
        for comments, accepted, rejected in (([], 3, 0), ([], 0, 0), (ONE, 0, 0), (ONE, 4, 1)):
            for absent in ("", None):
                self.assertEqual(km._file_comments_message(REPORT, comments, accepted, rejected, True, True, note=absent),
                                 km._file_comments_message(REPORT, comments, accepted, rejected, True, True),
                                 (comments, accepted, rejected, absent))
        self.assertEqual(message(accepted=3),
                         HEADER + "I accepted 3 of your changes and rejected 0.\n\nNo comments this time, so nothing needs a reply.\n"
                         + ASK_AGAIN)

    def test_the_note_is_marker_neutralized_and_otherwise_verbatim(self):
        # the op trims; the builder does not, so the two builders agree on every input — a note with
        # surrounding whitespace or inner line breaks is emitted as given, only the markers broken
        body = message(note=MARKED)
        self.assertEqual(body, HEADER + NEUTRAL + "\n\n" + ASK_AGAIN)
        self.assertEqual(re.findall(r"<!--\s*romp-", body), [], "no live marker")
        self.assertNotIn("romp-goal-id:", body)
        self.assertEqual(message(note="  two words \n"), HEADER + "  two words \n\n\n" + ASK_AGAIN)
        self.assertEqual(message(note="one\n\ntwo"), HEADER + "one\n\ntwo\n\n" + ASK_AGAIN)

    def test_the_note_only_shape_has_no_comment_list_and_no_file_kind_branch(self):
        bodies = {(t, x): message(note=NOTE, tracked=t, is_text=x) for t in (True, False) for x in (True, False)}
        self.assertEqual(len(set(bodies.values())), 1, "nothing to revise or reply to, so no second bullet")
        for absent in ("I left", "--thread", "To respond", "I accepted", "addressed these", "Comment "):
            self.assertNotIn(absent, bodies[(True, True)], absent)
        self.assertNotIn("<!--", bodies[(True, True)], "no marker tail: this is the person's own message")

    def test_the_bound_is_the_contracts(self):
        self.assertEqual(km._SEND_NOTE_MAX, 4000)


# The stub host script (tests/test_file_comments.py's): records the request it read from stdin and
# answers as configured. ESM (.mjs) like the real script.
_STUB = """import fs from 'node:fs';
const CFG = %s;
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { raw += d; });
process.stdin.on('end', () => {
  let request = null;
  try { request = JSON.parse(raw); } catch (e) { request = { parseError: String(e), raw }; }
  fs.writeFileSync(CFG.seen, JSON.stringify({ request, argv: process.argv.slice(2) }));
  process.stdout.write(JSON.stringify(CFG.reply));
  process.exit(0);
});
"""


class _SendWorld(unittest.TestCase):
    """The send op's world: a notes-api tree with a .trackchanges/ at its root, the consent on, a STATE
    sandbox with user todos ON, a known session (`web`) owned by the tmux backend, _send_or_park scripted,
    and the kernel pointed at a stub host under the temp dir (tests/test_file_comments.py's _SendWorld)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "notes-api")
        os.makedirs(os.path.join(self.root, ".trackchanges"))
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write("# Findings\n\nThe api session cut p95 latency by 40%.\n")
        self.seen_path = os.path.join(self.tmp, "seen.json")
        self.stub_path = os.path.join(self.tmp, "stub-host.mjs")
        with open(self.stub_path, "w") as f:
            f.write(_STUB % json.dumps({"seen": self.seen_path,
                                        "reply": {"ok": True, "verb": "log-send", "logged": True}}))
        self._saved = (km._FILE_COMMENTS_HOST, km._name_of, km._sdk, km._send_or_park, jd.STATE)
        km._FILE_COMMENTS_HOST = Path(self.stub_path)
        jd.STATE = Path(self.tmp) / "state"
        jd.STATE.mkdir()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        km._set_file_editing(True)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append({"sid": sid, "text": text, "echo": echo, "user_todo": user_todo})
            return True
        km._send_or_park = fake_send_or_park
        self.tid = km._add_user_todo(SID, "Need a look at the findings report", self.fp)

    def tearDown(self):
        km._set_file_editing(False)
        km._FILE_COMMENTS_HOST, km._name_of, km._sdk, km._send_or_park, jd.STATE = self._saved
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def send(self, **kw):
        """A send with nothing unsent but the note, unless the call says otherwise."""
        msg = {"type": "fileCommentsSend", "reqId": 9, "sid": SID, "path": self.fp, "tracked": True,
               "comments": [], "accepted": 0, "rejected": 0, "watermark": None, "todoId": self.tid}
        msg.update(kw)
        return km._file_comments_send_op(msg)

    def logged(self):
        """The log-send request the stub host saw, or None when no request reached it."""
        try:
            with open(self.seen_path) as f:
                return json.load(f)["request"]
        except OSError:
            return None


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheNoteInTheSend(_SendWorld):
    def test_a_note_alone_sends_the_note_only_shape_answers_the_todo_and_is_logged(self):
        r = self.send(note=NOTE)
        self.assertEqual(r, {"type": "fileCommentsSent", "reqId": 9, "queued": False})
        self.assertEqual(len(self.injected), 1)
        text = self.injected[0]["text"]
        self.assertEqual(text, "[obsidian-diff] I went over %s.\n\n%s\n\n" % (self.fp, NOTE) + ASK_AGAIN)
        self.assertEqual(text, km._file_comments_message(self.fp, [], 0, 0, True, True, note=NOTE))
        self.assertEqual(self.injected[0]["user_todo"], self.tid)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        req = self.logged()
        self.assertEqual(req["verb"], "log-send")
        args = req["args"]
        self.assertEqual(args["note"], NOTE)
        self.assertEqual((args["sid"], args["sessionName"], args["comments"], args["accepted"], args["rejected"],
                          args["queued"], args["watermark"]), (SID, "web", [], 0, 0, False, None))

    def test_the_note_is_trimmed_and_its_inner_line_breaks_kept(self):
        r = self.send(note="  \n\tFirst point.\n\nSecond point.  \n\n")
        self.assertEqual(r["type"], "fileCommentsSent", r)
        self.assertEqual(self.injected[0]["text"],
                         "[obsidian-diff] I went over %s.\n\nFirst point.\n\nSecond point.\n\n" % self.fp + ASK_AGAIN)
        self.assertEqual(self.logged()["args"]["note"], "First point.\n\nSecond point.")

    def test_a_note_rides_a_send_with_comments_and_with_decisions(self):
        self.send(comments=ONE, watermark=1781100000000, note=NOTE)
        text = self.injected[-1]["text"]
        self.assertEqual(text, km._file_comments_message(self.fp, ONE, 0, 0, True, True, note=NOTE))
        self.assertTrue(text.startswith("[obsidian-diff] I left 1 comment on %s.\n\n%s\n\nComment " % (self.fp, NOTE)))
        self.assertEqual(self.logged()["args"]["note"], NOTE)
        self.assertEqual(self.logged()["args"]["comments"], ONE)
        self.send(accepted=2, rejected=1, note=NOTE, todoId=None)
        text = self.injected[-1]["text"]
        self.assertEqual(text, "[obsidian-diff] I went over %s.\n\n%s\n\nI accepted 2 of your changes and rejected 1.\n\n"
                         % (self.fp, NOTE) + ASK_AGAIN)
        self.assertEqual((self.logged()["args"]["note"], self.logged()["args"]["accepted"]), (NOTE, 2))

    def test_no_note_key_in_the_log_entry_when_nothing_was_typed(self):
        # absent, null, empty, and whitespace only: the message is the no-note text and the entry keeps the
        # shape every earlier entry has
        for kw in ({}, {"note": None}, {"note": ""}, {"note": "  \n\t "}):
            self.injected.clear()
            r = self.send(accepted=3, **kw)
            self.assertEqual(r["type"], "fileCommentsSent", (kw, r))
            self.assertEqual(self.injected[0]["text"], km._file_comments_message(self.fp, [], 3, 0, True, True), kw)
            self.assertIn("No comments this time, so nothing needs a reply.", self.injected[0]["text"])
            self.assertNotIn("note", self.logged()["args"], kw)

    def test_a_whitespace_only_note_with_nothing_else_is_still_nothing_to_send(self):
        r = self.send(note="  \n\n ")
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("no unsent comments or decisions", r["error"])
        self.assertEqual(self.injected, [])
        self.assertIsNone(self.logged())
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSendFailed", "no note at all: the refusal that was there before")

    def test_a_note_past_the_bound_is_refused_before_anything_goes_and_one_at_the_bound_sends(self):
        # the refusal first, while the todo is still open: nothing is sent, logged or stamped
        over = "x" * (km._SEND_NOTE_MAX + 1)
        r = self.send(note=over)
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertEqual(r["error"], "nothing was sent: the note is 4001 characters and a send carries at most 4000; "
                                     "shorten it")
        self.assertNotIn("code", r)
        self.assertEqual(self.injected, [], "nothing reached the session")
        self.assertIsNone(self.logged(), "no log-send request reached the host")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the todo stays open")
        # then exactly the bound: sent, logged whole, and the todo answered
        at = "x" * km._SEND_NOTE_MAX
        r = self.send(note=at)
        self.assertEqual(r["type"], "fileCommentsSent", r)
        self.assertEqual(len(self.injected), 1)
        self.assertIn("\n\n" + at + "\n\n", self.injected[0]["text"])
        self.assertEqual(self.logged()["args"]["note"], at)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_the_bound_is_measured_after_the_trim_and_checked_before_the_other_gates(self):
        # surrounding whitespace does not count against the bound
        r = self.send(note="   " + "x" * km._SEND_NOTE_MAX + "\n\n")
        self.assertEqual(r["type"], "fileCommentsSent", r)
        self.injected.clear()
        # too long beside comments and a decision, and beside a watermark the op would refuse: the note's
        # refusal comes first, so the person hears about the words they typed, not about the request's fields
        over = "x" * (km._SEND_NOTE_MAX + 1)
        r = self.send(comments=ONE, accepted=1, watermark=-5, note=over)
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("the note is 4001 characters", r["error"])
        self.assertNotIn("watermark", r["error"])
        self.assertEqual(self.injected, [])

    def test_a_note_that_is_not_text_is_refused(self):
        for bad in (5, 4.5, True, ["a note"], {"text": "a note"}):
            self.injected.clear()
            r = self.send(comments=ONE, watermark=1781100000000, note=bad)
            self.assertEqual(r["type"], "fileCommentsSendFailed", bad)
            self.assertEqual(r["error"], "nothing was sent: the note was not text", bad)
            self.assertEqual(self.injected, [], bad)
            self.assertIsNone(self.logged(), bad)

    def test_markers_in_the_note_are_neutralized_in_the_message_and_in_the_log(self):
        r = self.send(note=MARKED)
        self.assertEqual(r["type"], "fileCommentsSent", r)
        text = self.injected[0]["text"]
        self.assertEqual(text, "[obsidian-diff] I went over %s.\n\n%s\n\n" % (self.fp, NEUTRAL) + ASK_AGAIN)
        self.assertEqual(re.findall(r"<!--\s*romp-", text), [], "no live marker reaches the session")
        self.assertNotIn("romp-goal-id:", text)
        logged = self.logged()["args"]["note"]
        self.assertEqual(logged, NEUTRAL)
        self.assertEqual(re.findall(r"<!--\s*romp-", logged), [], "no live marker reaches the log")
        self.assertIn("<!-- not ours --> stays", logged, "a non-romp comment is left alone")

    def test_the_refusal_texts_speak_to_the_person(self):
        # the two new refusals name what to do in plain words and carry no vocabulary a person never typed
        texts = [self.send(note="x" * (km._SEND_NOTE_MAX + 1))["error"], self.send(note=7)["error"]]
        for t in texts:
            self.assertTrue(t.startswith("nothing was sent: "), t)
            for word in ("card", "board", "goal", "column", "nudge", "romp"):
                self.assertNotIn(word, t.lower(), (word, t))


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheNoteStandsBehindTheConsent(_SendWorld):
    """The consent gate is checked before the note is looked at. With dashboard file editing off, a note the
    op would otherwise refuse on its own account (past the bound, or not text) is refused as `editing-off`
    instead: the reply carries the phrase the viewer's regex matches, so the panel can offer the consent and
    retry, and the person hears about the consent, not about their words. The other consent-off pins
    (tests/test_kernel_file_comments_gates.py, tests/test_file_comments.py) send no note, so a note check
    hoisted above the gate, say to answer the client faster, would pass them all; this class holds the order
    the Security posture states (plans/file-review.md: checked before any content check)."""

    def test_a_note_past_the_bound_is_refused_as_editing_off_while_the_consent_is_off(self):
        km._set_file_editing(False)
        r = self.send(note="x" * (km._SEND_NOTE_MAX + 1))
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertEqual(r["code"], "editing-off")
        self.assertIn("file editing is off", r["error"], "the phrase the viewer's regex matches")
        self.assertIn("nothing was sent", r["error"])
        self.assertNotIn("characters", r["error"], "the bound is not what the person hears about")
        self.assertEqual(self.injected, [], "nothing reached the session")
        self.assertIsNone(self.logged(), "no host call without consent")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the todo stays open")

    def test_a_note_that_is_not_text_is_refused_as_editing_off_while_the_consent_is_off(self):
        km._set_file_editing(False)
        for bad in (7, True, ["a note"], {"text": "a note"}):
            r = self.send(comments=ONE, watermark=1781100000000, note=bad)
            self.assertEqual(r["type"], "fileCommentsSendFailed", bad)
            self.assertEqual(r["code"], "editing-off", bad)
            self.assertIn("file editing is off", r["error"], bad)
            self.assertNotIn("not text", r["error"], bad)
        self.assertEqual(self.injected, [])
        self.assertIsNone(self.logged())

    def test_a_good_note_alone_is_refused_as_editing_off_too(self):
        # the note-only shape stands down the nothing-to-send gate, never the consent
        km._set_file_editing(False)
        r = self.send(note=NOTE)
        self.assertEqual((r["type"], r["code"]), ("fileCommentsSendFailed", "editing-off"))
        self.assertNotIn("no unsent comments", r["error"])
        self.assertEqual(self.injected, [])
        self.assertIsNone(self.logged())

    def test_with_consent_restored_the_note_refusals_and_the_send_come_back(self):
        km._set_file_editing(False)
        self.assertEqual(self.send(note="x" * (km._SEND_NOTE_MAX + 1))["code"], "editing-off")
        km._set_file_editing(True)
        r = self.send(note="x" * (km._SEND_NOTE_MAX + 1))
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("the note is 4001 characters", r["error"], "the note's own refusal, once the consent is on")
        self.assertNotIn("code", r)
        r = self.send(note=7)
        self.assertEqual(r["error"], "nothing was sent: the note was not text")
        self.assertNotIn("code", r)
        self.assertEqual(self.injected, [], "the refusals sent nothing")
        r = self.send(note=NOTE)
        self.assertEqual(r, {"type": "fileCommentsSent", "reqId": 9, "queued": False})
        self.assertEqual(len(self.injected), 1, "exactly one message, from the send that was allowed")
        self.assertEqual(self.logged()["args"]["note"], NOTE)


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheNoteWithTheRealHost(_SendWorld):
    """The host script's log-send verb copies the send entry's fields by name, so `note` reaches the comments
    log only because the verb names it: a note-only send through the REAL host lands as a `send` entry
    carrying the note, and a send without one keeps the entry shape every earlier entry has."""

    def setUp(self):
        super().setUp()
        km._FILE_COMMENTS_HOST = Path(HOST)

    def log_lines(self):
        p = os.path.join(self.root, ".trackchanges", "docs%2Freport.md.comments-log.jsonl")
        if not os.path.exists(p):
            return []
        with open(p) as f:
            return [json.loads(l) for l in f.read().splitlines() if l.strip()]

    def test_the_note_lands_in_the_send_entry_and_only_when_there_is_one(self):
        r = self.send(note=MARKED)
        self.assertEqual(r["type"], "fileCommentsSent", r)
        self.assertNotIn("logWarning", r)
        entries = self.log_lines()
        self.assertEqual([e["kind"] for e in entries], ["send"])
        self.assertEqual((entries[0]["sid"], entries[0]["sessionName"], entries[0]["note"], entries[0]["comments"],
                          entries[0]["accepted"], entries[0]["rejected"], entries[0]["queued"], entries[0]["watermark"]),
                         (SID, "web", NEUTRAL, [], 0, 0, False, None))
        r = self.send(accepted=1, todoId=None)
        self.assertEqual(r["type"], "fileCommentsSent", r)
        entries = self.log_lines()
        self.assertEqual([e["kind"] for e in entries], ["send", "send"])
        self.assertNotIn("note", entries[1])
        self.assertEqual(len(self.injected), 2)


if __name__ == "__main__":
    unittest.main()
