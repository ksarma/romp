#!/usr/bin/env python3
"""docs/reference.md: a todo whose `file` is a mistyped absolute path is cleared like any other, withdraw included.

The todo-file follow-on (2026-09-07) let a user todo name its file. The reference's account of a MISTYPED
absolute path (stored as typed, its chip opens nothing, no Send offers the todo) first ended "only Reply or
Dismiss clears it", which left out the session's withdraw and so contradicted the clearing rule docs/adr/0001
pins (answer, dismiss, withdraw) and CONTEXT.md's User todo entry (review round 2, 2026-09-07). The kernel's
clearing path never reads a row's `file`: `_resolve_user_todo` stamps by id, `_withdraw_user_todo` accounts by
id, and `_user_todo_file` stores any absolute path as typed with no existence check, so a todo naming a file
that is not there is withdrawn, answered and dismissed exactly as one naming a real file is. Pinned here:

- the paragraph names all three clearing events for that todo, in the words the rest of the paragraph uses
  (Reply and Dismiss are the buttons, withdraw the session's tool), and the "only Reply or Dismiss" clause is
  gone;
- the doc is held to the kernel: a todo filed with a nonexistent absolute path is cleared by
  `_withdraw_user_todo` (ok, state withdrawn, owner) and leaves `_open_user_todos` and
  `_user_todos_naming_file`; the same todo is cleared by an answer stamp and by a dismiss stamp;
- the three events the paragraph names are the three ADR 0001 and CONTEXT.md name, so the reference cannot
  drift from the rule again without a test saying so.

Synthetic throughout: a PRIVATE sid of this module's own (the goal-store fixture rule), a temp state root bound
before the kernel loads, a temp project tree named after the docs' demo domain.
"""
import os
import re
import tempfile
import unittest
from pathlib import Path

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
# Hermetic state BEFORE the loads — the kernel resolves its state root at import time (conftest's floor
# holds under pytest; this keeps a bare unittest run off the real store too).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = load_source("romp_kernel_reference_todo_file_withdraw", os.path.join(BIN, "romp-kernel"))
jd = km.jd

WSID = "9a9a9a9a-1111-4222-8333-944444444444"      # a session with a recorded cwd, private to this module

# The sentence the reference states, with hard wraps collapsed (a rewrap must not fail the pin).
CLEARING = ("its chip opens nothing and no Send offers the todo. It is cleared like any other todo, by your "
            "Reply or Dismiss or by the session's withdraw.")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(md, lead):
    """The blank-line paragraph of `md` that starts with `lead`, collapsed."""
    for p in re.split(r"\n\s*\n", md):
        if p.lstrip().startswith(lead):
            return _flat(p)
    raise AssertionError("no paragraph starts with %r" % lead)


class _Sandbox(unittest.TestCase):
    """A per-test store under a temp state root, the switch on, a temp `notes-api` tree with one real file
    and one path that names nothing, and a recorded cwd for WSID."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name, "state")
        os.makedirs(jd.STATE)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        self.root = os.path.join(self.td.name, "notes-api")
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write("# Findings\n")
        self.typo = os.path.join(self.root, "docs", "reprot.md")
        self.assertFalse(os.path.exists(self.typo), "the scenario needs a path naming nothing")
        self._cwd = km._cwd_of
        km._cwd_of = lambda sid: self.root if sid == WSID else ""

    def tearDown(self):
        km._cwd_of = self._cwd
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()

    def _file_mistyped_todo(self):
        tid = km._add_user_todo(WSID, "Need a look at the findings report", file=self.typo)
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$", "filed all the same")
        self.assertEqual(km._user_todos()[WSID][0]["file"], self.typo, "stored as typed")
        self.assertEqual([t["id"] for t in km._open_user_todos(WSID)], [tid], "open, listed")
        return tid

    def _stamp_of(self, tid):
        row = next(t for t in km._user_todos()[WSID] if t["id"] == tid)
        return (row.get("resolved") or {}).get("kind")


class TheParagraphNamesAllThreeClearingEvents(unittest.TestCase):
    """The reference's mistyped-path sentence names Reply, Dismiss and the session's withdraw, and no longer
    says only the first two clear the todo."""

    def setUp(self):
        self.para = _paragraph(_read("docs", "reference.md"), "**User todos.**")

    def test_the_sentence_as_stated(self):
        self.assertIn("The kernel does not check that the file exists. A mistyped absolute path is stored as typed, "
                      "with no warning; " + CLEARING, self.para)

    def test_the_only_reply_or_dismiss_clause_is_gone(self):
        self.assertNotIn("only Reply or Dismiss", self.para)
        self.assertNotRegex(self.para, r"only (Reply|Dismiss|withdraw)\b.{0,40}clears? it",
                            "no clause may restrict a todo's clearing to fewer than the three events")

    def test_the_three_events_are_the_adr_and_context_three(self):
        # the paragraph's words for the events: the two buttons and the session's tool
        m = re.search(r"It is cleared like any other todo, by your (\w+) or (\w+) or by the session's (\w+)\.",
                      self.para)
        self.assertIsNotNone(m, "the clearing sentence's shape")
        named = {m.group(1).lower(), m.group(2).lower(), m.group(3).lower()}
        self.assertEqual(named, {"reply", "dismiss", "withdraw"})
        adr = _read("docs", "adr", "0001-user-todos-authority-tier.md")
        self.assertIn("cleared by exactly three events: the user answers it, the user dismisses it, or the agent "
                      "withdraws it", _flat(adr))
        self.assertIn("Cleared only by answer, dismiss, or withdraw; never by inference.", _flat(_read("CONTEXT.md")))
        # Reply is the button for the ADR's "answers"; the other two share the ADR's words
        self.assertEqual(named - {"reply"}, {"dismiss", "withdraw"})


class TheKernelClearsAMistypedFileTodoLikeAnyOther(_Sandbox):
    """Each clearing event the sentence names is run against a todo whose `file` names nothing on disk."""

    def test_the_sessions_withdraw_clears_it(self):
        tid = self._file_mistyped_todo()
        self.assertEqual(km._user_todos_naming_file(WSID, os.path.realpath(self.typo)),
                         [{"id": tid, "text": "Need a look at the findings report"}],
                         "before: matched on the spelling stored")
        res = km._withdraw_user_todo(WSID, tid)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["state"], "withdrawn")
        self.assertTrue(res["owner"])
        self.assertIsInstance(res["at"], int)
        self.assertEqual(self._stamp_of(tid), "withdrawn")
        self.assertEqual(km._open_user_todos(WSID), [], "gone from Waiting on you")
        self.assertEqual(km._user_todos_naming_file(WSID, os.path.realpath(self.typo)), [],
                         "and from the comments panel's candidates")
        # the account of a second withdraw is the plain one any todo gets, no error path for the file
        again = km._withdraw_user_todo(WSID, tid)
        self.assertEqual((again["ok"], again["state"], again["owner"]), (False, "withdrawn", True))
        self.assertNotIn("error", again)

    def test_your_reply_clears_it(self):
        tid = self._file_mistyped_todo()
        self.assertTrue(km._resolve_user_todo(WSID, tid, "answered", reply="Use the March numbers"))
        self.assertEqual(self._stamp_of(tid), "answered")
        self.assertEqual(km._open_user_todos(WSID), [])

    def test_your_dismiss_clears_it(self):
        tid = self._file_mistyped_todo()
        self.assertTrue(km._resolve_user_todo(WSID, tid, "dismissed"))
        self.assertEqual(self._stamp_of(tid), "dismissed")
        self.assertEqual(km._open_user_todos(WSID), [])

    def test_the_clearing_path_never_reads_the_file(self):
        # the same three stamps on a todo naming a REAL file: identical accounts, so the sentence's "like any
        # other todo" is the kernel's behaviour, not a reading of it
        real = km._add_user_todo(WSID, "Need a look at the findings report", file=self.fp)
        typo = km._add_user_todo(WSID, "Need a look at the findings report", file=self.typo)
        r1 = km._withdraw_user_todo(WSID, real)
        r2 = km._withdraw_user_todo(WSID, typo)
        self.assertEqual({k: v for k, v in r1.items() if k != "at"}, {k: v for k, v in r2.items() if k != "at"})
        self.assertEqual(r1, {"ok": True, "state": "withdrawn", "at": r1["at"], "owner": True})
        self.assertEqual(km._open_user_todos(WSID), [])
        # and the lifecycle log carries the file as filed on the withdrawn line, mistyped or not
        log = Path(jd.STATE, "user-todos-log.jsonl").read_text().splitlines()
        withdrawn = [l for l in log if '"withdrawn"' in l]
        self.assertEqual(len(withdrawn), 2)
        self.assertTrue(any(self.typo in l for l in withdrawn), "the mistyped path, as typed")
        self.assertTrue(any(self.fp in l for l in withdrawn))


if __name__ == "__main__":
    unittest.main()
