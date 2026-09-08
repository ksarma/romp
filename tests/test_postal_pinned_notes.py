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
- every failure is LOUD: no session identity, no text, an unreachable kernel, an id that is unknown,
  already unpinned, or another session's; never a silent success.

The veil on the DESCRIPTIONS and the result texts (no romp machinery named) is scanned by
test_injected_voice.py. SYNTHETIC fixtures only.
"""
import json
import os
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

    def test_pin_teaches_unpinning_and_the_bound_at_pin_time(self):
        d = self._tool("pin_note")["description"]
        self.assertIn("unpin_note", d)
        self.assertIn("eight", d)

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
        out, err = pm._mcp_call("pin_note", {"text": "   "})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

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
        self.canned = {"ok": False, "error": "no pinned note of yours with that id", "notes": NOTES[:1]}
        out, err = pm._mcp_call("unpin_note", {"id": "pn-deadbeef"})
        self.assertTrue(err, "a loud, plain answer, never a silent success")
        self.assertIn("Nothing changed", out)
        self.assertIn("pn-deadbeef", out)
        self.assertIn("Pinned now (1)", out, "what IS pinned rides the refusal")

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


if __name__ == "__main__":
    unittest.main()
