#!/usr/bin/env python3
"""The set_emoji MCP tool (the user 2026-09-06): a session puts one emoji before its own name on its tab
through the kernel's POST /emoji — the same validator and store write the tab menu and `romp emoji`
use — so a session can mark itself (a moon for an unattended overnight run) and the person watching
sees it on every dashboard. Synthetic only — placeholder ids, hostname-free."""
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()      # hermetic; constants resolve under here at import
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = SourceFileLoader("romp_postal_emoji", os.path.join(BIN, "romp-postal-service")).load_module()

SID = "3e3e3e3e-0e0e-4e4e-8e8e-e0e0e0e0e0e3"   # private synthetic sid
MOON = "\U0001F319"


class SetEmojiTool(unittest.TestCase):
    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.reply = {"ok": True, "emoji": MOON}
        pm._kernel_post = lambda path, body, timeout=2: (self.posts.append((path, body)), self.reply)[1]
        pm._self_identity = lambda: (SID, "web")     # the one resolver every tool call reads (2026-09-06)
        pm._heartbeat = lambda *a, **k: None

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved

    def test_the_tool_is_offered_with_a_required_emoji_argument(self):
        tools = {t["name"]: t for t in pm.MCP_TOOLS}
        self.assertIn("set_emoji", tools)
        self.assertEqual(tools["set_emoji"]["inputSchema"]["required"], ["emoji"])
        self.assertIn("set_emoji", [t["name"] for t in pm._tools_offered()],
                      "offered regardless of the user-todos switch")
        desc = tools["set_emoji"]["description"]
        self.assertIn("one emoji", desc.lower())
        self.assertIn("clears", desc, "the documented clear is empty text")

    def test_set_posts_the_sessions_own_sid_to_the_kernel(self):
        text, is_err = pm._mcp_call("set_emoji", {"emoji": MOON})
        self.assertFalse(is_err)
        self.assertEqual(self.posts, [("/emoji", {"target": SID, "emoji": MOON})])
        self.assertIn(MOON, text)

    def test_empty_clears(self):
        self.reply = {"ok": True, "emoji": ""}
        text, is_err = pm._mcp_call("set_emoji", {"emoji": ""})
        self.assertFalse(is_err)
        self.assertEqual(self.posts, [("/emoji", {"target": SID, "emoji": ""})])
        self.assertIn("Cleared", text)

    def test_a_missing_argument_changes_nothing(self):
        # the set_working lesson: a malformed call must never read as a clear
        text, is_err = pm._mcp_call("set_emoji", {})
        self.assertTrue(is_err)
        self.assertEqual(self.posts, [])
        self.assertIn("nothing was changed", text)
        text, is_err = pm._mcp_call("set_emoji", {"emoji": None})
        self.assertTrue(is_err)
        self.assertEqual(self.posts, [])

    def test_the_kernels_refusal_reaches_the_agent_verbatim(self):
        self.reply = {"ok": False, "error": "one emoji only"}
        text, is_err = pm._mcp_call("set_emoji", {"emoji": MOON + MOON})
        self.assertTrue(is_err)
        self.assertIn("one emoji only", text)
        self.assertIn("Nothing was changed", text)

    def test_an_unreachable_kernel_is_an_honest_error(self):
        self.reply = None
        text, is_err = pm._mcp_call("set_emoji", {"emoji": MOON})
        self.assertTrue(is_err)
        self.assertIn("not changed", text)

    def test_outside_a_session_it_refuses(self):
        pm._self_identity = lambda: ("", "web")     # no session id resolved
        text, is_err = pm._mcp_call("set_emoji", {"emoji": MOON})
        self.assertTrue(is_err)
        self.assertEqual(self.posts, [])

    def test_the_publish_helper_routes_through_the_kernel_emoji_route(self):
        src = open(os.path.join(BIN, "romp-postal-service")).read()
        self.assertIn('_kernel_post("/emoji"', src)
        self.assertIn("_publish_emoji(mid, emoji)", src)


if __name__ == "__main__":
    unittest.main()
