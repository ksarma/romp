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
- a withdraw of a row the person already answered or dismissed, or one this session already
  withdrew, is a plain non-error answer that says what happened and when (the kernel's
  state / at / owner account, 2026-09-07): the need no longer stands, which is what the caller
  wanted; only an id that is not this session's own, or unknown, is an error (Account);
- the per-install SWITCH (the user 2026-09-03, OFF by default): while the kernel's
  user-todos-enabled.json does not say yes, tools/list omits both tools and a call anyway is
  refused plainly, before any post — read from the file per call, because the bus is its own
  long-lived process and a gear flip must land without a restart (Switch);
- the optional `file` (the todo-file follow-on, 2026-09-07): the file the need is about rides
  the post as `file` when given and is absent otherwise; the kernel resolves and stores it, and
  its `warning` for a path that did not resolve reaches the agent in the reply, never swallowed
  (File). The argument's own description keeps the veil, and so does the warning's lead-in.

The veil on the DESCRIPTIONS (no romp machinery named) is scanned by test_injected_voice.py.
SYNTHETIC fixtures only.
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
pm = load_source("romp_postal_ut", os.path.join(BIN, "romp-postal-service"))

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

    def test_add_offers_an_optional_file_and_the_description_names_it(self):
        # the todo-file follow-on (2026-09-07): the file the need is about, structured — the
        # todo shows it and the person's comments on that file can answer the todo
        t = self._tool("add_user_todo")
        self.assertIn("file", t["inputSchema"]["properties"])
        self.assertNotIn("file", t["inputSchema"]["required"], "optional: most needs are not about a file")
        desc = t["inputSchema"]["properties"]["file"]["description"]
        self.assertIn("absolute path", desc)
        self.assertIn("comments on that file", desc, "says what the argument buys: comments answer the todo")
        self.assertIn("`file`", t["description"], "the tool's own description points at the argument")
        for text in (desc, t["inputSchema"]["properties"]["text"]["description"],
                     t["inputSchema"]["properties"]["detail"]["description"]):
            for word in ("romp", "card", "board", "goal", "nudge", "cleared", "dismissal", "status check",
                         "viewer", "panel", "dashboard", "pane"):
                self.assertNotIn(word, text.lower(), "%r names machinery the agent cannot see" % word)

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

    def test_the_descriptions_name_the_bounds_on_text_and_detail(self):
        # the 2026-09-09 review: neither had a cap, and the webview re-links both on every pane frame and chat push
        t = self._tool("add_user_todo")
        self.assertIn("at most 300 characters", t["description"])
        self.assertIn("at most 4000", t["description"])
        props = t["inputSchema"]["properties"]
        self.assertIn("at most 300 characters", props["text"]["description"])
        self.assertIn("at most 4000 characters", props["detail"]["description"])
        self.assertEqual((pm.TODO_TEXT_MAX, pm.TODO_DETAIL_MAX), (300, 4000))


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

    def test_withdraw_refused_by_a_kernel_without_the_account_is_loud(self):
        # a kernel that predates the state / at / owner account (2026-09-07) answers ok:false alone:
        # the one-size answer it always got, still an error; nothing is invented about the row
        self.canned = {"ok": False, "error": "no open todo with that id"}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-deadbeef"})
        self.assertTrue(err, "a loud, plain answer — never a silent success")
        self.assertIn("Nothing changed", out)
        self.assertNotIn(" at ", out, "no time to report")

    def test_withdraw_with_an_unreachable_kernel_says_it_still_stands(self):
        # None is also what _kernel_post makes of the route's 502 for a remote session whose
        # kernel gave no account (a dead tunnel, an older remote): the row still stands there
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


class File(unittest.TestCase):
    """The optional `file` (the todo-file follow-on, 2026-09-07): the absolute path of the file the
    need is about. The tool passes it to POST /usertodo as `file` and otherwise posts the shape it
    always did; the KERNEL resolves it (a relative path against the session's cwd) and stores the
    absolute path, never refusing a todo for its file, and answers `warning` when the value could
    not be made absolute (never an existence check: kernel _user_todo_file). The tool relays that
    warning in its reply — the todo stands, so no error flag, but the agent hears that the path was
    kept as given and is asked for the absolute one. A kernel that takes `file` echoes it on the
    reply, and the tool reads a reply with neither `file` nor `warning` as an older kernel's
    (test_postal_service_todo_file_skew.py), so the canned replies here carry the echo. PRIVATE
    synthetic sid (the fixture rule)."""

    SID = "5e5e5e5e-1111-4222-8333-944444444444"
    FILE = "/TESTDIR/notes-api/docs/report.md"
    MINTED = {"ok": True, "todoId": "ut-0a1b2c3d", "file": FILE}
    # the kernel's own shape for a relative path from a session whose cwd it does not know
    WARNING = ("the file path docs/report.md did not resolve to an absolute path (it is relative and no working "
               "directory is recorded for this session), so it was kept as given; pass the file's absolute path "
               "so the person can open it from the todo and their comments on it can answer the todo")

    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = dict(self.MINTED)
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (self.SID, "api")
        pm._heartbeat = lambda *a, **k: None
        _switch(True)

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

    def test_the_file_rides_the_post_as_given(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a look at the report",
                                                  "detail": "The figures section is new.",
                                                  "file": "/TESTDIR/notes-api/docs/report.md"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/usertodo", {"id": self.SID, "text": "Need a look at the report",
                                                     "detail": "The figures section is new.",
                                                     "file": "/TESTDIR/notes-api/docs/report.md"})])
        self.assertIn("ut-0a1b2c3d", out)

    def test_a_relative_path_is_passed_through_for_the_kernel_to_resolve(self):
        # the kernel owns resolution (_resolve_open_path against the session's cwd): the tool
        # never guesses at a cwd the bus does not have
        pm._mcp_call("add_user_todo", {"text": "Need a look at the report", "file": "docs/report.md"})
        self.assertEqual(self.posts[-1][1]["file"], "docs/report.md")

    def test_no_file_means_no_file_key_the_shape_the_route_always_took(self):
        pm._mcp_call("add_user_todo", {"text": "Need the staging port"})
        self.assertNotIn("file", self.posts[-1][1])
        pm._mcp_call("add_user_todo", {"text": "Need the staging port", "file": "   "})
        self.assertNotIn("file", self.posts[-1][1], "a blank file is no file")
        pm._mcp_call("add_user_todo", {"text": "Need the staging port", "file": None})
        self.assertNotIn("file", self.posts[-1][1])

    def test_the_kernels_warning_reaches_the_agent_and_the_todo_still_stands(self):
        self.canned = dict(self.MINTED, file="docs/report.md", warning=self.WARNING)   # kept as given, with the reason
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a look at the report",
                                                  "file": "docs/report.md"})
        self.assertFalse(err, "the todo was filed: a warning is not a failure")
        self.assertIn("Noted (id ut-0a1b2c3d)", out, "the filing is confirmed first")
        self.assertIn("withdraw_user_todo", out, "the withdraw contract still rides along")
        self.assertIn("About the file: " + self.WARNING, out, "the kernel's words, relayed whole")
        self.assertTrue(out.index("Noted") < out.index("About the file"), "the confirmation leads")

    def test_a_recorded_file_with_no_warning_means_no_file_sentence(self):
        # the kernel echoed the file it stored and warned of nothing: the reply says nothing about the file
        # (a reply with NEITHER field is an older kernel's, and earns the not-recorded sentence instead —
        # test_postal_service_todo_file_skew.py)
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a look at the report", "file": self.FILE})
        self.assertFalse(err)
        self.assertEqual(self.canned["file"], self.FILE)
        self.assertNotIn("About the file", out)
        self.canned = dict(self.MINTED, warning="")
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a look at the report", "file": self.FILE})
        self.assertNotIn("About the file", out, "an empty warning is no warning")

    def test_the_warning_reply_keeps_the_veil(self):
        # the lead-in is the tool's own words (the kernel's warning is scanned where it is
        # rendered); the same vocabulary rule the descriptions ride
        self.canned = dict(self.MINTED, warning="that path did not resolve on this machine")
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a look at the report", "file": "docs/report.md"})
        for word in ("romp", "card", "board", "goal", "nudge", "cleared", "dismissal", "status check"):
            self.assertNotIn(word, out.lower(), "%r names machinery the agent cannot see" % word)


class Link(unittest.TestCase):
    """The optional `link` (the user 2026-09-08): the http or https address the need is about. The tool
    checks it BEFORE any post (_todo_link_error, the kernel's _user_todo_link twin): a value that is not such
    an address is refused in the tool's own reply and nothing is saved, so the agent files again with an
    address, or puts it in the text, where it links too. A good one rides the post stripped, the kernel
    echoes it as stored, and a reply that echoes none to a body that sent one is an older kernel's, named
    in the reply the way the file's skew is (never swallowed; the todo stands, so no error flag). PRIVATE
    synthetic sid (the fixture rule)."""

    SID = "5f5f5f5f-1111-4222-8333-944444444444"
    LINK = "https://example.invalid/notes-api/pull/398"
    MINTED = {"ok": True, "todoId": "ut-0a1b2c3d", "link": LINK}

    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = dict(self.MINTED)
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (self.SID, "api")
        pm._heartbeat = lambda *a, **k: None
        _switch(True)

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

    def test_the_link_rides_the_post_stripped(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a review of the pull request",
                                                  "link": "  " + self.LINK + " \n"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/usertodo", {"id": self.SID, "text": "Need a review of the pull request",
                                                     "detail": "", "link": self.LINK})])
        self.assertIn("ut-0a1b2c3d", out)
        self.assertNotIn("About the link", out, "echoed as stored: nothing to say about it")

    def test_no_link_means_no_link_key_the_shape_the_route_always_took(self):
        for args in ({"text": "Need the staging port"}, {"text": "Need the staging port", "link": None},
                     {"text": "Need the staging port", "link": "   "}):
            _, err = pm._mcp_call("add_user_todo", args)
            self.assertFalse(err)
            self.assertNotIn("link", self.posts[-1][1])

    def test_a_value_that_is_not_a_web_address_is_refused_before_any_post(self):
        for value in ("ftp://example.invalid/x", "example.invalid/x", "https://", "mailto:someone@example.invalid",
                      "https://example.invalid/a b", ["https://example.invalid/x"], {"href": self.LINK}, 7, True,
                      "https://example.invalid/" + "x" * pm.TODO_LINK_MAX):
            with self.subTest(link=value):
                out, err = pm._mcp_call("add_user_todo", {"text": "Need a review of the pull request", "link": value})
                self.assertTrue(err, "a refusal, not a filing")
                self.assertTrue(out.startswith("Refused: "), out)
                self.assertIn("http or https address", out, "what would have been taken")
                self.assertIn("Nothing was saved", out, "plain about the outcome: the agent must not believe the need was filed")
                self.assertIn("file it again", out, "and the remedy: `link`, or the address in the text")
                self.assertIn("`link`", out)
        self.assertEqual(self.posts, [], "the kernel was never asked")

    def test_the_refusal_names_the_reason(self):
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a review", "link": ["x"]})
        self.assertIn("is not a string", out)
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a review", "link": "https://example.invalid/a b"})
        self.assertIn("whitespace or a control character", out)
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a review", "link": "ftp://example.invalid/x"})
        self.assertIn("must start with http:// or https:// and name a host", out)
        long = "https://example.invalid/" + "x" * pm.TODO_LINK_MAX
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a review", "link": long})
        self.assertIn("longer than %d characters" % pm.TODO_LINK_MAX, out)
        self.assertNotIn(long, out, "shown by its head and its length, never whole")

    def test_a_kernel_that_echoes_no_link_is_named_in_the_reply_and_the_todo_stands(self):
        self.canned = {"ok": True, "todoId": "ut-0a1b2c3d"}      # an older kernel: id/text/detail/file alone
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a review of the pull request", "link": self.LINK})
        self.assertFalse(err, "the todo was filed: the loss of its link is not a failure (a retry files a duplicate)")
        self.assertIn("Noted (id ut-0a1b2c3d)", out, "the filing is confirmed first")
        self.assertIn("About the link: " + self.LINK + " was not recorded", out)
        self.assertIn("older version", out)
        self.assertIn("update and a restart", out, "the remedy for the machine")
        self.assertIn("address in its text", out, "and the remedy for this todo: the text links too")
        self.assertTrue(out.index("Noted") < out.index("About the link"))
        # the file's skew sentence and the link's are independent: both when both were dropped
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a look", "file": "/TESTDIR/notes-api/a.md", "link": self.LINK})
        self.assertIn("About the file:", out)
        self.assertIn("About the link:", out)
        self.assertTrue(out.index("About the file") < out.index("About the link"))

    def test_the_kernels_own_link_warning_is_relayed_and_no_skew_of_the_tools_is_read(self):
        # a hub kernel that forwarded the todo to an older remote says so under `linkWarning` (its own key, apart from
        # the file's `warning`): the tool relays the kernel's words after the filing and adds no sentence of its own
        lw = ("the link %s was not recorded (the kernel on TESTHOST predates a todo's link: update romp there and "
              "restart it); the todo stands there without it" % self.LINK)
        self.canned = {"ok": True, "todoId": "ut-0a1b2c3d", "linkWarning": lw}
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a review of the pull request", "link": self.LINK})
        self.assertFalse(err, "the todo was filed")
        self.assertIn("Noted (id ut-0a1b2c3d)", out)
        self.assertIn("About the link: " + lw, out)
        self.assertNotIn("older version", out, "the kernel's account stands alone")
        self.assertEqual(out.count("About the link"), 1)
        self.assertTrue(out.index("Noted") < out.index("About the link"))
        # a file warning and a link warning from the same reply: each under its own label, the file's first
        self.canned = {"ok": True, "todoId": "ut-0a1b2c3d", "warning": "the file path /TESTDIR/notes-api/a.md was not recorded", "linkWarning": lw}
        out, _ = pm._mcp_call("add_user_todo", {"text": "Need a look", "file": "/TESTDIR/notes-api/a.md", "link": self.LINK})
        self.assertIn("About the file: the file path /TESTDIR/notes-api/a.md was not recorded", out)
        self.assertIn("About the link: " + lw, out)
        self.assertTrue(out.index("About the file") < out.index("About the link"))

    def test_an_over_long_text_or_detail_is_refused_before_any_post(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "N" * (pm.TODO_TEXT_MAX + 1), "link": self.LINK})
        self.assertTrue(err)
        self.assertIn("Too long: the line takes at most %d characters and this one is %d" % (pm.TODO_TEXT_MAX, pm.TODO_TEXT_MAX + 1), out)
        self.assertIn("rest can go in 'detail'", out)
        self.assertIn("Nothing was saved", out)
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a review", "detail": "d" * (pm.TODO_DETAIL_MAX + 1)})
        self.assertTrue(err)
        self.assertIn("Too long: 'detail' takes at most %d characters and this one is %d" % (pm.TODO_DETAIL_MAX, pm.TODO_DETAIL_MAX + 1), out)
        self.assertEqual(self.posts, [], "the kernel was never asked")
        # the whitespace the tool strips does not count: a padded line at the bound is filed
        out, err = pm._mcp_call("add_user_todo", {"text": "  " + "N" * pm.TODO_TEXT_MAX + "  ", "detail": " " + "d" * pm.TODO_DETAIL_MAX})
        self.assertFalse(err, out)
        self.assertEqual(len(self.posts), 1)
        self.assertEqual((len(self.posts[0][1]["text"]), len(self.posts[0][1]["detail"])), (pm.TODO_TEXT_MAX, pm.TODO_DETAIL_MAX))

    def test_the_replies_keep_the_veil(self):
        # the refusal and the skew sentence are the tool's own words (test_injected_voice.py renders them too)
        outs = [pm._mcp_call("add_user_todo", {"text": "Need a review", "link": "ftp://example.invalid/x"})[0]]
        self.canned = {"ok": True, "todoId": "ut-0a1b2c3d"}
        outs.append(pm._mcp_call("add_user_todo", {"text": "Need a review", "link": self.LINK})[0])
        for out in outs:
            for word in ("romp", "card", "board", "goal", "nudge", "cleared", "dismissal", "status check"):
                self.assertNotIn(word, out.lower(), "%r names machinery the agent cannot see" % word)

    def test_the_schema_offers_link_and_the_descriptions_say_addresses_link(self):
        t = next(t for t in pm.MCP_TOOLS if t["name"] == "add_user_todo")
        props = t["inputSchema"]["properties"]
        self.assertEqual(set(props), {"text", "detail", "file", "link"})
        self.assertEqual(props["link"]["type"], "string")
        self.assertEqual(t["inputSchema"]["required"], ["text"], "still optional")
        self.assertIn("http or https address", props["link"]["description"])
        self.assertIn("new tab", props["link"]["description"])
        self.assertIn("refused", props["link"]["description"], "the schema says a bad one is refused, so the agent expects it")
        self.assertIn("http or https address", props["text"]["description"], "a URL in the text links")
        self.assertIn("web address", props["detail"]["description"], "and in the detail")
        self.assertIn("pass its address as `link`", t["description"])


class Account(unittest.TestCase):
    """The kernel's ACCOUNT on an ok:false (state / at / owner, 2026-09-07) picks the answer. Two
    sessions read the one-size "No open note of yours" error as a failure and folded a MET need
    into an error path; now a row the person answered or dismissed, or one this session already
    withdrew, is a plain answer with no error flag, and only a not-yours or unknown id is an error.
    PRIVATE synthetic sid (the fixture rule)."""

    SID = "7c7c7c7c-1111-4222-8333-944444444444"
    AT = 1781200000

    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = {}
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (self.SID, "api")
        pm._heartbeat = lambda *a, **k: None
        _switch(True)

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

    def _withdraw(self, **acct):
        self.canned = dict({"ok": False, "error": "no open todo with that id"}, **acct)
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertEqual(self.posts[-1], ("/usertodo/withdraw", {"id": self.SID, "todoId": "ut-9f2c1a34"}))
        return out, err

    def test_answered_by_the_person_is_plain_with_the_time_and_no_error(self):
        out, err = self._withdraw(state="answered", at=self.AT, owner=True)
        self.assertFalse(err, "the need is met: not the agent's failure")
        self.assertIn("Already closed", out)
        self.assertIn("the person you work for answered 'ut-9f2c1a34'", out)
        self.assertIn(pm._when_words(self.AT), out, "says when")
        self.assertTrue(out.endswith("Nothing to withdraw."), out)

    def test_dismissed_by_the_person_is_plain_with_the_time_and_no_error(self):
        out, err = self._withdraw(state="dismissed", at=self.AT, owner=True)
        self.assertFalse(err)
        self.assertIn("Already closed", out)
        self.assertIn("the person you work for dismissed 'ut-9f2c1a34'", out)
        self.assertIn(pm._when_words(self.AT), out)
        self.assertTrue(out.endswith("Nothing to withdraw."), out)

    def test_already_withdrawn_by_this_session_is_plain_and_no_error(self):
        out, err = self._withdraw(state="withdrawn", at=self.AT, owner=True)
        self.assertFalse(err)
        self.assertIn("Already withdrawn: 'ut-9f2c1a34' was taken back", out)
        self.assertIn(pm._when_words(self.AT), out)
        self.assertTrue(out.endswith("Nothing changed."), out)

    def test_an_unknown_id_is_the_error_it_always_was(self):
        out, err = self._withdraw(state="unknown", at=None, owner=False)
        self.assertTrue(err)
        self.assertEqual(out, "No note 'ut-9f2c1a34' of yours. Nothing changed.")

    def test_the_askers_own_row_in_an_unreadable_shape_is_an_error_that_says_so(self):
        # review round 1 (2026-09-07): the kernel's account for a malformed closing stamp is state
        # unknown with owner True and an error naming the stamp: neither "not yours" nor closed
        why = "malformed closing stamp on ut-9f2c1a34: resolved=True (a stamp is {kind: answered | dismissed | withdrawn, t})"
        out, err = self._withdraw(state="unknown", at=None, owner=True, error=why)
        self.assertTrue(err)
        self.assertIn("Couldn't read the record of 'ut-9f2c1a34'", out)
        self.assertIn(why, out, "relays what the kernel could not read")
        self.assertNotIn("of yours", out)
        self.assertIn("Nothing changed", out)
        self.assertIn("say it directly", out, "the agent's move when the record cannot say")
        for word in ("romp", "card", "board", "goal", "cleared", "dismissal", "nudge", "<!--"):
            self.assertNotIn(word, out.lower(), "%r names machinery the agent cannot see" % word)
        # without any error text from the kernel the sentence still stands on its own
        self.canned = {"ok": False, "state": "unknown", "at": None, "owner": True}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("its closing record is unreadable", out)

    def test_not_the_askers_row_is_an_error_whatever_its_state_says(self):
        # the kernel reports another session's rows as unknown; a kernel that ever described one
        # would still be answered on `owner` first, so no agent hears "the person answered it"
        # about a note that was never its own
        out, err = self._withdraw(state="answered", at=self.AT, owner=False)
        self.assertTrue(err)
        self.assertIn("No note 'ut-9f2c1a34' of yours", out)

    def test_a_closed_row_with_no_time_known_drops_the_time_phrase(self):
        out, err = self._withdraw(state="answered", owner=True)
        self.assertFalse(err)
        self.assertEqual(out, "Already closed: the person you work for answered 'ut-9f2c1a34'. "
                              "Nothing to withdraw.")

    def test_every_plain_answer_still_says_what_happened(self):
        # LOUD, never a silent success: each non-error answer names the id and the outcome
        for state, word in (("answered", "answered"), ("dismissed", "dismissed"), ("withdrawn", "withdrawn")):
            out, err = self._withdraw(state=state, at=self.AT, owner=True)
            self.assertFalse(err)
            self.assertIn("ut-9f2c1a34", out)
            self.assertIn(word, out)
            self.assertTrue(out.startswith("Already"), out)

    def test_ok_true_is_withdrawn_whatever_else_rides_along(self):
        self.canned = {"ok": True, "state": "withdrawn", "at": self.AT, "owner": True}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertFalse(err)
        self.assertIn("Withdrawn", out)


class WhenWords(unittest.TestCase):
    """_when_words: the closing time as a phrase a reader can place (today, yesterday, or a dated
    day), in local time. TZ is pinned to UTC for the run so the expected strings are exact."""

    NOON = 1781179200            # 2026-06-11 12:00:00 UTC

    def setUp(self):
        import time as _t
        self._tz = os.environ.get("TZ")
        os.environ["TZ"] = "UTC"
        _t.tzset()

    def tearDown(self):
        import time as _t
        if self._tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self._tz
        _t.tzset()

    def test_same_day_is_today(self):
        self.assertEqual(pm._when_words(self.NOON - 3600, now=self.NOON), " at 11:00 today")

    def test_the_day_before_is_yesterday(self):
        self.assertEqual(pm._when_words(self.NOON - 86400, now=self.NOON), " at 12:00 yesterday")

    def test_older_carries_the_date(self):
        self.assertEqual(pm._when_words(self.NOON - 3 * 86400, now=self.NOON), " on 2026-06-08 at 12:00")

    def test_a_future_stamp_carries_the_date_too(self):
        # a remote kernel's clock ahead of ours: never "today" for a time that has not come
        self.assertEqual(pm._when_words(self.NOON + 2 * 86400, now=self.NOON), " on 2026-06-13 at 12:00")

    def test_no_time_is_the_empty_phrase(self):
        for t in (None, 0, "", "soon", -5, 10 ** 20):
            self.assertEqual(pm._when_words(t, now=self.NOON), "", repr(t))

    def test_defaults_to_the_clock(self):
        import time as _t
        self.assertTrue(pm._when_words(int(_t.time())).endswith(" today"))


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
