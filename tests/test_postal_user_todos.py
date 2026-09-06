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
  already-cleared id — never a silent success;
- the per-install SWITCH (the user 2026-09-03, OFF by default): while the kernel's
  user-todos-enabled.json does not say yes, tools/list omits both tools and a call anyway is
  refused plainly, before any post — read from the file per call, because the bus is its own
  long-lived process and a gear flip must land without a restart (Switch).

The veil on the DESCRIPTIONS (no romp machinery named) is scanned by test_injected_voice.py.
SYNTHETIC fixtures only.
"""
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = SourceFileLoader("romp_postal_ut", os.path.join(BIN, "romp-postal-service")).load_module()

SID = "11111111-2222-3333-4444-555555555555"


def _switch(on):
    """Write the kernel's per-install switch file the way _set_user_todos does (or remove it)."""
    p = pm.USER_TODOS_SWITCH
    if on is None:
        p.unlink(missing_ok=True)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"enabled": bool(on), "gt": 1}))


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
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = {"ok": True, "todoId": "ut-9f2c1a34"}
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (SID, "api")     # the one resolver every tool call reads (2026-09-06)
        pm._heartbeat = lambda *a, **k: None
        _switch(True)                                # the switch is OFF by default (2026-09-03): these pin ON

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

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

    def test_register_without_text_is_refused_before_any_post(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "   "})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_register_outside_a_session_is_refused(self):
        pm._self_identity = lambda: ("", "api")     # no session id resolved
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_register_failure_is_loud_never_a_silent_drop(self):
        # an unsaved need the agent believes is filed is exactly the vanishing this exists to stop
        self.canned = None                                # unreachable kernel / non-2xx
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertIn("NOT", out, "says plainly the person will not see it")

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
        pm._self_identity = lambda: ("", "api")     # no session id resolved
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])


class Switch(unittest.TestCase):
    """The per-install switch, bus side (the user 2026-09-03). The kernel writes
    STATE/user-todos-enabled.json = {"enabled": bool, "gt": ms}; the bus reads THAT file (never
    user-todos.json, which is the todo store) on every tools/list and every call."""

    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body))
                                                           or {"ok": True, "todoId": "ut-9f2c1a34"})
        pm._self_identity = lambda: (SID, "api")     # the one resolver every tool call reads (2026-09-06)
        pm._heartbeat = lambda *a, **k: None
        _switch(None)

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

    def test_the_switch_reads_the_kernels_file_not_the_store(self):
        self.assertEqual(pm.USER_TODOS_SWITCH.name, "user-todos-enabled.json")
        self.assertEqual(pm.USER_TODOS_SWITCH.parent, pm.STATE.parent, "the kernel's STATE dir")
        self.assertNotEqual(pm.USER_TODOS_SWITCH.name, "user-todos.json", "that file is the todo STORE")

    def test_absent_garbled_or_false_all_read_off(self):
        self.assertFalse(pm._user_todos_on(), "no file = the shipped default, OFF")
        _switch(False)
        self.assertFalse(pm._user_todos_on())
        pm.USER_TODOS_SWITCH.write_text("not json")
        self.assertFalse(pm._user_todos_on(), "a garbled file must not turn the feature on")
        pm.USER_TODOS_SWITCH.write_text(json.dumps(["enabled"]))
        self.assertFalse(pm._user_todos_on())
        _switch(True)
        self.assertTrue(pm._user_todos_on())

    def test_the_tools_list_omits_both_tools_while_off_and_offers_them_while_on(self):
        names_off = {t["name"] for t in pm._tools_offered()}
        self.assertNotIn("add_user_todo", names_off)
        self.assertNotIn("withdraw_user_todo", names_off)
        self.assertEqual(names_off, {t["name"] for t in pm.MCP_TOOLS} - set(pm.USER_TODO_TOOLS),
                         "every OTHER tool is still offered")
        _switch(True)
        self.assertEqual(pm._tools_offered(), pm.MCP_TOOLS, "on: the full list, same objects")

    def test_the_list_is_read_per_call_no_restart_needed(self):
        # the bus is a separate long-lived process: a gear flip must land on the next list/call
        self.assertNotIn("add_user_todo", {t["name"] for t in pm._tools_offered()})
        _switch(True)
        self.assertIn("add_user_todo", {t["name"] for t in pm._tools_offered()})
        _switch(False)
        self.assertNotIn("add_user_todo", {t["name"] for t in pm._tools_offered()})

    def test_the_stdio_server_answers_tools_list_from_the_gated_list(self):
        import inspect
        src = inspect.getsource(pm.mcp)
        self.assertIn('"tools": _tools_offered()', src, "tools/list goes through the gate")
        self.assertNotIn('"tools": MCP_TOOLS}', src, "…never the raw constant")

    def test_a_call_anyway_is_refused_plainly_before_any_post(self):
        # a session that connected while the switch was on still holds the tool
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the auth-scheme decision"})
        self.assertTrue(err)
        self.assertIn("turned off on this machine", out)
        self.assertIn("will NOT see it", out, "the agent must not believe the need was filed")
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("turned off on this machine", out)
        self.assertEqual(self.posts, [], "nothing reached the kernel")

    def test_the_refusals_keep_the_veil(self):
        # the same vocabulary rule the descriptions ride (test_injected_voice.py sweeps the live
        # branches; the OFF branches are rendered there too) — pinned here at the source of the text
        for text in (pm.USER_TODOS_OFF_ADD, pm.USER_TODOS_OFF_WITHDRAW):
            for word in ("romp", "card", "board", "goal", "gear", "nudge", "cleared", "dismissal"):
                self.assertNotIn(word, text.lower(), "%r names machinery the agent cannot see" % word)

    def test_on_the_call_goes_through_as_before(self):
        _switch(True)
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the auth-scheme decision"})
        self.assertFalse(err)
        self.assertEqual([p[0] for p in self.posts], ["/usertodo"])


if __name__ == "__main__":
    unittest.main()
