#!/usr/bin/env python3
"""The two postal tools for user todos (plans/user-todos.md): add_user_todo registers a need with
the person the agent works for (the kernel mints and returns the id); withdraw_user_todo takes it
back. Construction is set_working's exact shape — one MCP_TOOLS schema entry + one _mcp_call
branch each, backed by kernel routes the way _publish_working posts /working.

Pinned here:
- both tools are registered, with the right required fields;
- register posts to /usertodo AS THE CALLING SESSION (postal resolves identity from the CLI
  process env, so a subagent's call files under its parent session — documented, not fixed);
- register echoes the kernel-minted id back to the agent, with the withdraw contract in the
  same breath;
- every failure is LOUD: no session identity, no text, an unreachable kernel, an unknown or
  already-cleared id — never a silent success.

The veil on the DESCRIPTIONS and result texts (no romp machinery named) is scanned by
test_injected_voice.py. SYNTHETIC fixtures only.
"""
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = SourceFileLoader("romp_postal_usertodos", os.path.join(BIN, "romp-postal-service")).load_module()

SID = "11111111-2222-3333-4444-555555555555"


class ToolSurface(unittest.TestCase):
    def _tool(self, name):
        return next((t for t in pm.MCP_TOOLS if t["name"] == name), None)

    def test_both_tools_are_registered(self):
        self.assertIsNotNone(self._tool("add_user_todo"))
        self.assertIsNotNone(self._tool("withdraw_user_todo"))

    def test_add_requires_text_and_offers_optional_detail(self):
        t = self._tool("add_user_todo")
        self.assertEqual(t["inputSchema"]["required"], ["text"])
        self.assertIn("detail", t["inputSchema"]["properties"])

    def test_withdraw_requires_the_id(self):
        t = self._tool("withdraw_user_todo")
        self.assertEqual(t["inputSchema"]["required"], ["id"])

    def test_descriptions_speak_as_the_person_you_work_for(self):
        for name in ("add_user_todo", "withdraw_user_todo"):
            self.assertIn("person you work for", self._tool(name)["description"])

    def test_add_teaches_withdrawal_at_registration_time(self):
        # withdrawal support mechanism #1 (plans/user-todos.md): the agent learns the contract
        # in the same breath it files the need
        self.assertIn("withdraw_user_todo", self._tool("add_user_todo")["description"])


class Dispatch(unittest.TestCase):
    def setUp(self):
        self._saved = (pm._kernel_post, pm.my_id, pm.my_name, pm._heartbeat)
        self.posts = []
        self.canned = {"ok": True, "todoId": "ut-9f2c1a34"}
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body)) or self.canned)
        pm.my_id = lambda: SID                       # the calling SESSION, resolved from the CLI env
        pm.my_name = lambda: "api"
        pm._heartbeat = lambda *a, **k: None

    def tearDown(self):
        pm._kernel_post, pm.my_id, pm.my_name, pm._heartbeat = self._saved

    # ── add_user_todo ──────────────────────────────────────────────────────────────────────────
    def test_register_posts_to_the_kernel_as_the_calling_session(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the auth-scheme decision to wire login",
                                                  "detail": "OAuth vs cookie"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/usertodo", {"id": SID,
                                                     "text": "Need the auth-scheme decision to wire login",
                                                     "detail": "OAuth vs cookie"})])

    def test_register_echoes_the_minted_id_and_the_withdraw_contract(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a test credential"})
        self.assertFalse(err)
        self.assertIn("ut-9f2c1a34", out)
        self.assertIn("withdraw_user_todo", out, "the contract rides the confirmation")

    def test_register_without_detail_posts_an_empty_detail(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertFalse(err)
        self.assertEqual(self.posts[0][1]["detail"], "", "the kernel stores no key for an empty detail")

    def test_register_without_text_is_refused_before_any_post(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "   "})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_register_outside_a_session_is_refused(self):
        pm.my_id = lambda: None                      # no session id resolved
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_register_failure_is_loud_never_a_silent_drop(self):
        # an unsaved need the agent believes is filed is exactly the vanishing this exists to stop
        self.canned = None                                # unreachable kernel / non-2xx
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertIn("NOT", out, "says plainly the person will not see it")

    def test_register_without_a_minted_id_is_loud_too(self):
        # the kernel answered, but with no id (a forward that failed on the far side)
        self.canned = {"ok": False, "todoId": ""}
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertIn("NOT", out)

    # ── withdraw_user_todo ─────────────────────────────────────────────────────────────────────
    def test_withdraw_posts_the_id_pair_and_confirms(self):
        self.canned = {"ok": True}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})])
        self.assertIn("Withdrawn", out)

    def test_withdraw_of_an_unknown_or_cleared_id_is_loud(self):
        self.canned = {"ok": False, "error": "no open todo with that id"}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-deadbeef"})
        self.assertTrue(err, "a loud, plain answer — never a silent success")
        self.assertIn("Nothing changed", out)

    def test_withdraw_with_an_unreachable_kernel_says_it_still_stands(self):
        self.canned = None
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("still stands", out)

    def test_withdraw_without_an_id_is_refused(self):
        out, err = pm._mcp_call("withdraw_user_todo", {})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_withdraw_outside_a_session_is_refused(self):
        pm.my_id = lambda: None                      # no session id resolved
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])


if __name__ == "__main__":
    unittest.main()
