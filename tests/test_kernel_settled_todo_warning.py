#!/usr/bin/env python3
"""Send to session against a settled todo: the warning NAMES the todo (plans/file-review.md,
fileCommentsSend — "the reply warns naming the todo").

The message goes and nothing is stamped either way; what this pins is the warning's text. A person
with two open requests about one file, one of them answered from another dashboard, reads the
warning to decide whether the other still needs an answer, so the two warnings must be tellable
apart: each carries its todo's own short line and how it was cleared (answered, dismissed, or
withdrawn by the agent). An id with no row at all falls back to the id. The todo Reply's strict
path keeps its own fixed text, and the switch-off warning names the switch, never a todo.

Synthetic only: the notes-api demo world, a placeholder sid, temp dirs. The comments-log append is
stubbed at the kernel's own seam (_file_comments_call), so no node process runs here.
"""
import json
import os
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
km = SourceFileLoader("romp_kernel_settled_todo_warning", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
FIRST = "Need a look at the findings report"
SECOND = "Check the latency table in the report"
ONE = [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"', "body": "Which cache? Say which."}]


class _World(unittest.TestCase):
    """A STATE sandbox with user todos ON, one known tmux-owned session (`web`), _send_or_park
    scripted to succeed, and the comments-log append stubbed — tests/test_file_comments.py's
    _SendWorld without the node host script."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.fp = os.path.join(self.tmp, "notes-api", "docs", "report.md")
        os.makedirs(os.path.dirname(self.fp))
        with open(self.fp, "w") as f:
            f.write("# Findings\n\nThe api session cut p95 latency by 40%.\n")
        self.saved_state = jd.STATE
        jd.STATE = Path(self.tmp) / "state"
        jd.STATE.mkdir()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        km._set_file_editing(True)
        self._saved = (km._name_of, km._sdk, km._send_or_park, km._file_comments_call)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append({"sid": sid, "text": text, "user_todo": user_todo})
            return True
        km._send_or_park = fake_send_or_park
        km._file_comments_call = lambda path, verb, args=None, fence=None: ({"ok": True, "verb": verb, "logged": True}, None)
        self.tid = km._add_user_todo(SID, FIRST, self.fp)

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park, km._file_comments_call = self._saved
        km._set_file_editing(False)
        jd.STATE = self.saved_state
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def send(self, todo_id):
        return km._file_comments_send_op({"type": "fileCommentsSend", "reqId": 9, "sid": SID, "path": self.fp,
                                          "tracked": True, "comments": ONE, "accepted": 0, "rejected": 0,
                                          "watermark": "1781100000000", "todoId": todo_id})

    def row(self, tid):
        return next(t for t in km._user_todos()[SID] if t["id"] == tid)


class TheSettledWarningNamesTheTodo(_World):
    def test_two_requests_about_one_file_are_told_apart(self):
        # the finding's scenario: two open requests naming the same file; the one the file was opened
        # from was answered from another dashboard before this send
        tid2 = km._add_user_todo(SID, SECOND, self.fp)
        self.assertTrue(km._resolve_user_todo(SID, self.tid, "answered", reply="Looked; the cache is fine."))
        r = self.send(self.tid)
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIs(r["queued"], False)
        self.assertIn("the request “%s” was already answered" % FIRST, r["warning"])
        self.assertTrue(r["warning"].startswith("The message was sent, but "), "did it go? is answered first")
        self.assertTrue(r["warning"].endswith("so nothing was marked."))
        self.assertNotIn(SECOND, r["warning"], "the OTHER request is not the one named")
        self.assertEqual(len(self.injected), 1, "the message went")
        self.assertIsNone(self.injected[0]["user_todo"], "no id rides a send that must not stamp")
        self.assertNotIn("resolved", self.row(tid2), "the other request stays open: this send did not answer it")
        # …and the other one, dismissed, reads differently — the two warnings are not interchangeable
        self.assertTrue(km._resolve_user_todo(SID, tid2, "dismissed"))
        r2 = self.send(tid2)
        self.assertEqual(r2["type"], "fileCommentsSent")
        self.assertIn("the request “%s” was already dismissed" % SECOND, r2["warning"])
        self.assertNotIn(FIRST, r2["warning"])
        self.assertNotEqual(r["warning"], r2["warning"])
        self.assertEqual(len(self.injected), 2)

    def test_a_withdrawn_todo_says_the_agent_withdrew_it(self):
        self.assertTrue(km._resolve_user_todo(SID, self.tid, "withdrawn"))
        r = self.send(self.tid)
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("the request “%s” was already withdrawn by the agent" % FIRST, r["warning"])
        self.assertEqual(len(self.injected), 1)

    def test_an_id_with_no_row_falls_back_to_the_id(self):
        # the store never held this id (a stale client, or a row the resolved-history cap evicted):
        # the line still says WHICH request it meant, and keeps the "already settled" reading the
        # sibling test in tests/test_file_comments.py pins
        r = self.send("ut-deadbeef")
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("(ut-deadbeef)", r["warning"])
        self.assertIn("already settled", r["warning"])
        self.assertIn("no longer listed", r["warning"])
        self.assertNotIn(FIRST, r["warning"], "the open todo is not the one this send named")
        self.assertEqual(len(self.injected), 1)
        self.assertNotIn("resolved", self.row(self.tid), "the real open todo is untouched")

    def test_the_switch_off_warning_names_the_switch_and_no_todo(self):
        km._set_user_todos(False)
        try:
            r = self.send(self.tid)
        finally:
            km._set_user_todos(True)
            km._user_todos_cache.clear()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertEqual(r["warning"], km._SENT_UNSTAMPED_WARN["off"])
        self.assertNotIn(FIRST, r["warning"], "OFF is the switch's story, never a stale-row one")
        self.assertNotIn("resolved", self.row(self.tid))

    def test_an_open_todo_gets_no_warning_and_is_stamped(self):
        r = self.send(self.tid)
        self.assertEqual(r, {"type": "fileCommentsSent", "reqId": 9, "queued": False})
        self.assertEqual(self.row(self.tid)["resolved"]["kind"], "answered")

    def test_the_todo_reply_keeps_its_own_fixed_settled_text(self):
        # the strict path (userTodoAnswer) sends nothing on a settled row and warns with its own text;
        # the naming above is the lenient send's alone
        self.assertTrue(km._resolve_user_todo(SID, self.tid, "answered"))
        sent = []
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": self.tid, "text": "Go with the session cookie."},
                  {"send": lambda s: sent.append(json.loads(s))})
        self.assertEqual(self.injected, [])
        self.assertEqual(sent, [{"type": "warn", "text": km._USER_TODO_SETTLED_WARN}])
        self.assertNotIn(FIRST, km._USER_TODO_SETTLED_WARN)


class ThePhraseReadsTheStore(_World):
    """_settled_todo_phrase on its own: the store row's text and kind, with the two fallbacks."""

    def test_a_stamped_row_gives_its_text_and_kind(self):
        km._resolve_user_todo(SID, self.tid, "answered")
        self.assertEqual(km._settled_todo_phrase(SID, self.tid), "the request “%s” was already answered" % FIRST)

    def test_an_unknown_kind_or_a_blank_text_still_reads(self):
        # a row hand-edited or written by a later kernel: the phrase degrades to the old generic
        # reading rather than a KeyError, and a blank line shows as untitled (the context block's idiom)
        km._resolve_user_todo(SID, self.tid, "answered")
        cur = json.loads((jd.STATE / "user-todos.json").read_text())
        cur[SID][0]["resolved"]["kind"] = "archived"
        cur[SID][0]["text"] = "   "
        (jd.STATE / "user-todos.json").write_text(json.dumps(cur))
        km._user_todos_cache.clear()
        self.assertEqual(km._settled_todo_phrase(SID, self.tid), "the request “(untitled)” was already settled")

    def test_a_missing_row_names_the_id(self):
        self.assertEqual(km._settled_todo_phrase(SID, "ut-deadbeef"),
                         "the request it was meant to answer (ut-deadbeef) was already settled and is no longer listed")
        self.assertEqual(km._settled_todo_phrase("99999999-8888-7777-6666-555555555555", self.tid),
                         "the request it was meant to answer (%s) was already settled and is no longer listed" % self.tid,
                         "another session's row is not this session's")


if __name__ == "__main__":
    unittest.main()
