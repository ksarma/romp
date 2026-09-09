#!/usr/bin/env python3
"""The two postal tools for pinned notes (the user 2026-09-08): pin_note puts a short note above the
session's own transcript for the person the agent works for (the kernel mints and returns the id, and
answers with the list pinned now); unpin_note takes one down. Construction is add_user_todo's exact
shape: one MCP_TOOLS schema entry + one _mcp_call branch each, backed by the kernel's /pinnote and
/unpinnote routes through _kernel_post.

Pinned here:
- both tools are registered, with the right required fields, and offered whatever the user-todos
  switch says (a pinned note asks nothing of the person; it is not that feature);
- pin posts to /pinnote AS THE CALLING SESSION (postal resolves identity from the CLI process env,
  so a subagent's pin lands on its parent session, as documented);
- pin echoes the kernel-minted id, the unpin contract, and the list pinned now, in the same breath;
- the bounds are checked before the POST (a plain answer naming the bound, never the kernel's 400
  folded into "couldn't pin that"), and the notes a pin evicted are named; the text is cleaned with the
  kernel's own cleaner first (a copy pinned equal by test_pinned_notes.py), so a text of whitespace,
  control characters or escape sequences alone is refused HERE as blank, and a pasted escape sequence
  goes whole; a non-string text or detail is refused, never pinned as its repr;
- every failure is LOUD: no session identity, no text, an unreachable kernel, an id that is unknown or
  another session's, a store that could not be read (named, on a pin as on an unpin, with no "try again"
  a retry cannot honour); never a silent success. A note of this session's
  that was ALREADY taken down (the person unpinned it from the strip) is a plain answer, not an error:
  the state the agent wanted holds (the #325 lesson).

The veil on the DESCRIPTIONS and the result texts (no romp machinery named) is scanned by
test_injected_voice.py. SYNTHETIC fixtures only.
"""
import json
import os
import re
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = load_source("romp_postal_pn", os.path.join(BIN, "romp-postal-service"))

SID = "8f8f8f8f-1111-4222-8333-944444444444"
NOTES = [{"id": "pn-9f2c1a34", "text": "Waiting on CI for the login fix", "createdT": 1781200000},
         {"id": "pn-0badcafe", "text": "Read docs/plan.md before replying", "createdT": 1781200060}]


class ToolSurface(unittest.TestCase):
    def _tool(self, name):
        return next((t for t in pm.MCP_TOOLS if t["name"] == name), None)

    def test_both_tools_are_registered(self):
        self.assertIsNotNone(self._tool("pin_note"))
        self.assertIsNotNone(self._tool("unpin_note"))

    def test_pin_requires_text_and_offers_optional_detail(self):
        t = self._tool("pin_note")
        self.assertEqual(t["inputSchema"]["required"], ["text"])
        self.assertIn("detail", t["inputSchema"]["properties"])

    def test_unpin_requires_the_id(self):
        self.assertEqual(self._tool("unpin_note")["inputSchema"]["required"], ["id"])

    def test_descriptions_speak_as_the_person_you_work_for(self):
        for name in ("pin_note", "unpin_note"):
            self.assertIn("person you work for", self._tool(name)["description"])

    def test_pin_teaches_unpinning_and_the_bounds_at_pin_time(self):
        d = self._tool("pin_note")["description"]
        self.assertIn("unpin_note", d)
        self.assertIn("eight", d)
        self.assertIn("300", d)
        self.assertIn("4000", d)
        props = self._tool("pin_note")["inputSchema"]["properties"]
        self.assertIn("300", props["text"]["description"])
        self.assertIn("4000", props["detail"]["description"])
        self.assertEqual((pm.PIN_TEXT_MAX, pm.PIN_DETAIL_MAX), (300, 4000))

    def test_the_descriptions_name_every_kind_of_link_the_strip_makes(self):
        # docs/reference.md says a file path, a web address or a pull request number in a note links the way it
        # does in a user todo (the strip runs the todo row's linkers); the schema the agent reads says the same
        # (the 2026-09-09 review: the two named different sets)
        props = self._tool("pin_note")["inputSchema"]["properties"]
        self.assertIn("a file path, a web address or a pull-request number in it becomes a link", props["text"]["description"])
        self.assertIn("paths, web addresses and pull-request numbers link the same way", props["detail"]["description"])
        with open(os.path.join(os.path.dirname(HERE), "docs", "reference.md"), encoding="utf-8") as f:
            ref = re.sub(r"\s+", " ", f.read())
        self.assertIn("A file path, a web address or a pull request number in a note links the way it does in a user todo.", ref)

    def test_offered_whatever_the_user_todos_switch_says(self):
        pm.USER_TODOS_SWITCH.unlink(missing_ok=True)          # the switch is OFF by default
        names = [t["name"] for t in pm._tools_offered()]
        self.assertIn("pin_note", names)
        self.assertIn("unpin_note", names)
        self.assertNotIn("add_user_todo", names, "the switch still governs its own pair")


class Dispatch(unittest.TestCase):
    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = {"ok": True, "noteId": "pn-9f2c1a34", "notes": NOTES[:1]}
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (SID, "api")     # the one resolver every tool call reads
        pm._heartbeat = lambda *a, **k: None

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved

    # pin_note
    def test_pin_posts_to_the_kernel_as_the_calling_session(self):
        out, err = pm._mcp_call("pin_note", {"text": "Waiting on CI for the login fix",
                                             "detail": "The api tests flake on the auth step"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/pinnote", {"id": SID, "text": "Waiting on CI for the login fix",
                                                    "detail": "The api tests flake on the auth step"})])

    def test_pin_echoes_the_minted_id_the_unpin_contract_and_the_list(self):
        self.canned = {"ok": True, "noteId": "pn-0badcafe", "notes": NOTES}
        out, err = pm._mcp_call("pin_note", {"text": "Read docs/plan.md before replying"})
        self.assertFalse(err)
        self.assertIn("pn-0badcafe", out)
        self.assertIn("unpin_note", out, "the contract rides the confirmation")
        self.assertIn("Pinned now (2)", out)
        self.assertIn("- pn-9f2c1a34: Waiting on CI for the login fix", out)
        self.assertIn("- pn-0badcafe: Read docs/plan.md before replying", out)

    def test_pin_without_text_is_refused_before_any_post(self):
        for blank in ("   ", "\x1b\x07", "\x01\x02 \x1b[0m", "\x1b[0m\x1b[K", "\x1b]0;a title\x07 \x9b0m \x1b(B"):
            with self.subTest(text=blank):
                out, err = pm._mcp_call("pin_note", {"text": blank})
                self.assertTrue(err)
                self.assertIn("Need 'text'", out, "the plain 'need text' answer, the same as for whitespace")
                self.assertEqual(self.posts, [], "the kernel would refuse it too; it is never asked")

    def test_a_pasted_escape_sequence_is_dropped_whole_before_the_post(self):
        # before this only the ESC byte went and '[0m' reached the kernel as part of the note (review round 2,
        # 2026-09-08); the tool now runs the kernel's own cleaner, so what it posts is what the kernel keeps
        out, err = pm._mcp_call("pin_note", {"text": " \x1b[31mred\x1b[0m alert ", "detail": "\x1b[1mbold\x1b[0m\x00 line"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/pinnote", {"id": SID, "text": "red alert", "detail": "bold line"})])
        self.assertEqual(pm._pinned_note_clean("\x01\x02 \x1b[0m"), "")
        # an OSC hyperlink (ls --hyperlink, ripgrep) goes whole too, its URL with it, so the path reaches the
        # kernel as a path the row's linker can see (review round 3, 2026-09-08)
        self.posts.clear()
        out, err = pm._mcp_call("pin_note", {"text": "see \x1b]8;;https://example.test/a\x07docs/plan.md\x1b]8;;\x07 now"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/pinnote", {"id": SID, "text": "see docs/plan.md now", "detail": ""})])

    def test_a_non_string_text_or_detail_is_refused_before_any_post(self):
        for args, field in (({"text": ["a", "b"]}, "text"), ({"text": 12345}, "text"),
                            ({"text": "fine", "detail": {"k": 1}}, "detail"), ({"text": "fine", "detail": 7}, "detail")):
            with self.subTest(args=args):
                out, err = pm._mcp_call("pin_note", args)
                self.assertTrue(err)
                self.assertIn("'%s'" % field, out)
                self.assertIn("Nothing was pinned", out)
                self.assertEqual(self.posts, [])
        out, err = pm._mcp_call("pin_note", {"text": "fine", "detail": None})
        self.assertFalse(err, "an explicit null detail is no detail")
        self.assertEqual(self.posts[-1][1]["detail"], "")

    def test_an_over_long_pin_is_refused_plainly_before_any_post(self):
        out, err = pm._mcp_call("pin_note", {"text": "x" * 301})
        self.assertTrue(err)
        self.assertIn("300", out)
        self.assertIn("301", out, "says how long it was")
        self.assertIn("Nothing was pinned", out)
        out, err = pm._mcp_call("pin_note", {"text": "fine", "detail": "y" * 4001})
        self.assertTrue(err)
        self.assertIn("4000", out)
        self.assertEqual(self.posts, [])
        out, err = pm._mcp_call("pin_note", {"text": "x" * 300, "detail": "y" * 4000})
        self.assertFalse(err, "the bound itself is allowed")
        self.assertEqual(len(self.posts), 1)

    def test_a_pin_that_evicted_a_note_names_it(self):
        self.canned = {"ok": True, "noteId": "pn-0badcafe", "notes": NOTES,
                       "dropped": [{"id": "pn-00000000", "text": "the first\nnote", "createdT": 1781100000}]}
        out, err = pm._mcp_call("pin_note", {"text": "the ninth"})
        self.assertFalse(err)
        self.assertIn("the oldest came down", out)
        self.assertIn("- pn-00000000: the first note", out, "named, one line")
        self.canned = {"ok": True, "noteId": "pn-0badcafe", "notes": NOTES, "dropped": []}
        out, err = pm._mcp_call("pin_note", {"text": "the second"})
        self.assertNotIn("came down", out, "nothing dropped, nothing said")

    def test_pin_outside_a_session_is_refused(self):
        pm._self_identity = lambda: ("", "api")
        out, err = pm._mcp_call("pin_note", {"text": "Waiting on CI"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_pin_failure_is_loud_never_a_silent_drop(self):
        self.canned = None                                # unreachable kernel / non-2xx (a 502 forward too)
        out, err = pm._mcp_call("pin_note", {"text": "Waiting on CI"})
        self.assertTrue(err)
        self.assertIn("NOT", out, "says plainly the person will not see it")
        self.assertIn("try again", out, "an unreachable kernel may be back shortly")

    def test_a_pin_against_an_unreadable_store_names_the_fault_and_asks_for_no_retry(self):
        # the kernel's account (review round 2, 2026-09-08; before it a 500 the tool read as "try again")
        self.canned = {"ok": False, "state": "unreadable", "notes": [],
                       "error": "the pinned-notes store (x) is not readable; nothing changed"}
        out, err = pm._mcp_call("pin_note", {"text": "Waiting on CI"})
        self.assertTrue(err)
        self.assertIn("Couldn't pin that: the pinned-notes store (x) is not readable", out, "the fault, by name")
        self.assertIn("NOT see it", out)
        self.assertNotIn("try again", out, "a retry does nothing until the file is fixed")
        self.assertNotIn("Pinned", out)

    def test_an_older_kernel_that_sends_no_list_gets_no_invented_account(self):
        self.canned = {"ok": True, "noteId": "pn-9f2c1a34"}
        out, err = pm._mcp_call("pin_note", {"text": "Waiting on CI"})
        self.assertFalse(err)
        self.assertNotIn("Pinned now", out)

    # unpin_note
    def test_unpin_posts_the_id_pair_and_confirms_with_the_rest(self):
        self.canned = {"ok": True, "notes": []}
        out, err = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/unpinnote", {"id": SID, "noteId": "pn-9f2c1a34"})])
        self.assertIn("Unpinned", out)
        self.assertIn("Pinned now: nothing.", out)

    def test_unpin_of_an_unknown_or_foreign_id_is_loud(self):
        self.canned = {"ok": False, "state": "unknown", "error": "no pinned note of yours with that id", "notes": NOTES[:1]}
        out, err = pm._mcp_call("unpin_note", {"id": "pn-deadbeef"})
        self.assertTrue(err, "a loud, plain answer, never a silent success")
        self.assertIn("Nothing changed", out)
        self.assertIn("pn-deadbeef", out)
        self.assertIn("Pinned now (1)", out, "what IS pinned rides the refusal")

    def test_unpin_of_an_already_unpinned_note_is_plain_and_not_an_error(self):
        # the person clicked Unpin on the strip; the session tidies up later. The state it wanted
        # holds, so this is no error to retry or report (the #325 lesson, review round 1 2026-09-08).
        self.canned = {"ok": False, "state": "already", "at": 1781200000, "dropped": False, "error": "already unpinned", "notes": NOTES[1:]}
        out, err = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})
        self.assertFalse(err)
        self.assertIn("Already unpinned", out)
        self.assertIn("taken down", out)
        self.assertIn(" at ", out, "says when")
        self.assertIn("Nothing changed", out)
        self.assertIn("Pinned now (1)", out)
        self.canned = {"ok": False, "state": "already", "at": 1781200000, "dropped": True, "error": "already unpinned", "notes": []}
        out, err = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})
        self.assertFalse(err)
        self.assertIn("made room for a newer pin", out, "a note the bound dropped says so")

    def test_unpin_against_an_unreadable_store_names_the_fault(self):
        self.canned = {"ok": False, "state": "unreadable", "notes": [], "error": "the pinned-notes store (x) is not readable; nothing changed"}
        out, err = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("Couldn't unpin", out)
        self.assertIn("not readable", out)
        self.assertNotIn("Already", out)
        self.assertNotIn("No note", out)

    def test_an_older_kernel_without_the_account_gets_the_one_size_answer(self):
        self.canned = {"ok": False, "error": "no pinned note of yours with that id", "notes": []}
        out, err = pm._mcp_call("unpin_note", {"id": "pn-deadbeef"})
        self.assertTrue(err)
        self.assertIn("already unpinned, or", out)

    def test_unpin_with_an_unreachable_kernel_says_it_is_still_up(self):
        self.canned = None
        out, err = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("still up", out)

    def test_unpin_without_an_id_is_refused(self):
        out, err = pm._mcp_call("unpin_note", {})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_unpin_outside_a_session_is_refused(self):
        pm._self_identity = lambda: ("", "api")
        out, err = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])


class ListWords(unittest.TestCase):
    def test_the_account_lists_one_line_per_note_with_its_id(self):
        self.assertEqual(pm._pinned_notes_words(NOTES),
                         "Pinned now (2):\n- pn-9f2c1a34: Waiting on CI for the login fix\n"
                         "- pn-0badcafe: Read docs/plan.md before replying")
        self.assertEqual(pm._pinned_notes_words([]), "Pinned now: nothing.")
        self.assertEqual(pm._pinned_notes_words(None), "", "no list, no account")

    def test_a_note_with_line_breaks_is_still_one_line_in_the_list(self):
        self.assertEqual(pm._pinned_notes_words([{"id": "pn-9f2c1a34", "text": "line1\nline2\t  tab"}]),
                         "Pinned now (1):\n- pn-9f2c1a34: line1 line2 tab")

    def test_the_dropped_account(self):
        self.assertEqual(pm._pinned_dropped_words([{"id": "pn-00000000", "text": "old"}]),
                         "To stay within eight, the oldest came down:\n- pn-00000000: old")
        self.assertEqual(pm._pinned_dropped_words([]), "")
        self.assertEqual(pm._pinned_dropped_words(None), "")


if __name__ == "__main__":
    unittest.main()
