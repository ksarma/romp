#!/usr/bin/env python3
"""File comments (plans/file-review.md, Slice 2) — the decisions-only message Send to session hands
the owning session.

Slice 2 made a send with no comments reachable: a manual Accept or Reject (or Accept all) appends a
log entry the unsent derivation counts, the Send button enables on that count, and the send op admits
an empty comment list whenever a decision is pending. The message builder then wore the comments shape
for it: "I left 0 comments on <path>", the two `--thread <id>` command lines with no id to put in
them, and "When you have addressed these" over a list that was not there (the review, 2026-09-06).
This module pins the shape that replaced it — the file, the decisions line, that nothing needs a
reply, the closing ask — and that the comments shape did not move. The webview's preview builder
(ui/webview/file-comments-model.ts, buildSendMessage) ports this text byte for byte and its parity
test runs the kernel's builder, so the two change together.

Synthetic only: the notes-api demo world, a placeholder sid, temp dirs (tests/test_file_comments.py's
hermetic pattern).
"""
import json
import os
import re
import shutil
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load — the kernel resolves its state root at import time, and only pytest
# runs conftest's floor (a bare unittest run would otherwise write REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_filecomments_decisions", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")
REPORT = "/TESTDIR/notes-api/docs/report.md"
ONE = [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"', "body": "Which cache? Say which."}]
ASK_AGAIN = ("When you have made more changes, ask me for another look the same way you asked for this one,\n"
             "naming the file.\n")
# The romp-noun scan is tests/test_injected_voice.py's (ROMP_WORDS, one list): it renders this shape too
# ("file comments message (decisions only)"), so no copy of the list lives here to drift from it.


def decisions_only(path=REPORT, accepted=3, rejected=0, tracked=True, is_text=True):
    return km._file_comments_message(path, [], accepted, rejected, tracked, is_text)


class TheDecisionsOnlyMessage(unittest.TestCase):
    """The text, byte for byte: the shared spec with the webview's preview builder, like TheMessage in
    tests/test_file_comments.py is for the comments shape."""

    def test_accepts_alone_name_the_file_the_decision_and_that_nothing_needs_a_reply(self):
        self.assertEqual(decisions_only(),
                         "[obsidian-diff] I went over %s.\n"
                         "\n"
                         "I accepted 3 of your changes and rejected 0.\n"
                         "\n"
                         "No comments this time, so nothing needs a reply.\n" % REPORT + ASK_AGAIN)

    def test_rejects_alone_and_a_mix_wear_the_same_shape_with_their_own_counts(self):
        self.assertIn("\n\nI accepted 0 of your changes and rejected 3.\n\nNo comments this time",
                      decisions_only(accepted=0, rejected=3))
        self.assertIn("\n\nI accepted 2 of your changes and rejected 1.\n\nNo comments this time",
                      decisions_only(accepted=2, rejected=1))

    def test_it_never_claims_zero_comments_or_aims_a_reply_command_at_a_comment_that_does_not_exist(self):
        # every file kind and tracking state: the shape has no comment to reply into, so the second
        # bullet's three variants never enter it and the body is the same for all four
        bodies = {(t, x): decisions_only(tracked=t, is_text=x) for t in (True, False) for x in (True, False)}
        self.assertEqual(len(set(bodies.values())), 1, "no file-kind branch: nothing to revise or reply to")
        body = bodies[(True, True)]
        for absent in ("I left", "0 comments", "--thread", "<id>", "To respond", "track-reply", "track-edit",
                       "addressed these", "Comment "):
            self.assertNotIn(absent, body, absent)
        self.assertNotIn("<!--", body, "no marker tail: this is the person's own message, like a todo answer")

    def test_the_closing_ask_is_the_one_the_comments_shape_ends_on(self):
        with_comments = km._file_comments_message(REPORT, ONE, 0, 0, True, True)
        tail = "ask me for another look the same way you asked for this one,\nnaming the file.\n"
        self.assertTrue(with_comments.endswith("When you have addressed these, " + tail), with_comments)
        self.assertTrue(decisions_only().endswith("When you have made more changes, " + tail))
        self.assertEqual(km._SEND_ASK_AGAIN, ("ask me for another look the same way you asked for this one,",
                                              "naming the file."), "one constant, so the two lead-ins share a tail")

    def test_the_path_stays_plain_and_is_marker_neutralized(self):
        # no command lines, so no shell word: a path with a space or a quote reads as written
        self.assertTrue(decisions_only("/repo/notes-api/vault/Meeting notes.md").startswith(
            "[obsidian-diff] I went over /repo/notes-api/vault/Meeting notes.md.\n"))
        self.assertTrue(decisions_only("/repo/notes-api/vault/it's here.md").startswith(
            "[obsidian-diff] I went over /repo/notes-api/vault/it's here.md.\n"))
        forged = decisions_only("/TESTDIR/notes-api/<!--romp-injected-->/report.md")
        self.assertIn("I went over /TESTDIR/notes-api/<!- -romp-injected-->/report.md.", forged)
        self.assertEqual(re.findall(r"<!--\s*romp-", forged), [], "a marker-shaped path is no live marker")
        self.assertTrue(decisions_only("").startswith("[obsidian-diff] I went over .\n"), "an empty path, like the comments shape")

    def test_the_comments_shape_did_not_move(self):
        # the same decisions beside ONE comment: the Slice 1 shape, the decisions line where it was
        body = km._file_comments_message(REPORT, ONE, 3, 0, True, True)
        self.assertTrue(body.startswith("[obsidian-diff] I left 1 comment on %s.\n\nComment 1781100000000-0 " % REPORT))
        self.assertIn("Which cache? Say which.\n\nI accepted 3 of your changes and rejected 0.\n\nTo respond:\n", body)
        self.assertIn("track-reply.mjs --file %s --thread <id>" % REPORT, body)
        self.assertIn("track-edit.mjs --file %s --thread <id>" % REPORT, body)
        self.assertTrue(body.endswith("\nWhen you have addressed these, ask me for another look the same way you asked "
                                      "for this one,\nnaming the file.\n"))
        self.assertNotIn("I went over", body)
        self.assertNotIn("nothing needs a reply", body)

    def test_no_comments_and_no_decision_is_still_text_the_op_never_sends(self):
        # the send op refuses this call before building (tests/test_file_comments.py,
        # test_nothing_unsent_is_a_refusal_not_an_empty_message); the builder stays a pure function of
        # its inputs so a caller that forgot the guard gets text, never an exception on the reply thread
        body = decisions_only(accepted=0, rejected=0)
        self.assertTrue(body.startswith("[obsidian-diff] I went over %s.\n\nNo comments this time" % REPORT))
        self.assertNotIn("I accepted", body)
        for a, r in ((None, None), (0, None)):
            self.assertNotIn("I accepted", decisions_only(accepted=a, rejected=r), (a, r))


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


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheDecisionsOnlySend(unittest.TestCase):
    """The send op end to end with an empty comment list: a notes-api tree with a .trackchanges/ at
    its root, the consent on, a STATE sandbox with user todos ON, a known session (`web`) owned by the
    tmux backend, _send_or_park scripted, and the kernel pointed at a stub host under the temp dir —
    tests/test_file_comments.py's _SendWorld."""

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
        msg = {"type": "fileCommentsSend", "reqId": 9, "sid": SID, "path": self.fp, "tracked": True,
               "comments": [], "accepted": 3, "rejected": 0, "watermark": None, "todoId": self.tid}
        msg.update(kw)
        return km._file_comments_send_op(msg)

    def logged(self):
        with open(self.seen_path) as f:
            return json.load(f)["request"]

    def test_accepts_alone_send_the_decisions_shape_answer_the_todo_and_log_the_counts(self):
        r = self.send()
        self.assertEqual(r, {"type": "fileCommentsSent", "reqId": 9, "queued": False})
        self.assertEqual(len(self.injected), 1)
        text = self.injected[0]["text"]
        self.assertEqual(text, km._file_comments_message(self.fp, [], 3, 0, True, True))
        self.assertTrue(text.startswith("[obsidian-diff] I went over %s.\n\nI accepted 3 of your changes and rejected 0.\n"
                                        % self.fp), text)
        self.assertIn("No comments this time, so nothing needs a reply.", text)
        for absent in ("I left", "0 comments", "--thread", "To respond", "addressed these"):
            self.assertNotIn(absent, text, absent)
        self.assertEqual(self.injected[0]["user_todo"], self.tid)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        req = self.logged()
        self.assertEqual(req["verb"], "log-send")
        self.assertEqual((req["args"]["comments"], req["args"]["accepted"], req["args"]["rejected"]), ([], 3, 0))

    def test_rejects_alone_and_an_untracked_or_image_file_wear_the_same_shape(self):
        self.send(accepted=0, rejected=2, tracked=False)
        self.assertIn("\n\nI accepted 0 of your changes and rejected 2.\n\nNo comments this time", self.injected[-1]["text"])
        self.assertNotIn("edit the file normally", self.injected[-1]["text"], "no second bullet: nothing to revise")
        png = os.path.join(self.root, "docs", "latency.png")
        with open(png, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        self.send(path=png, accepted=1, rejected=0)
        text = self.injected[-1]["text"]
        self.assertTrue(text.startswith("[obsidian-diff] I went over %s.\n" % png))
        self.assertNotIn("regenerate the file", text)
        self.assertNotIn("track-edit", text)

    def test_nothing_unsent_is_still_a_refusal(self):
        r = self.send(accepted=0, rejected=0)
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("no unsent comments or decisions", r["error"])
        self.assertEqual(self.injected, [])


if __name__ == "__main__":
    unittest.main()
