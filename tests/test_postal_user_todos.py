#!/usr/bin/env python3
"""The two postal tools for requests from sessions (plans/user-todos.md): add_user_todo files a request
with the person the agent works for (the kernel mints and returns the id); withdraw_user_todo takes it
back. Construction is set_working's shape: one MCP_TOOLS entry and one _mcp_call branch each, backed by
the kernel's routes the way _publish_working posts /working.

Pinned here:
- both tools are registered after set_working, with the right required fields, `blocking` a boolean, and
  descriptions in the veil (no romp vocabulary, "person you work for");
- add posts /usertodo as the calling session with id, text, detail and a boolean blocking, and words the
  outcomes: the minted id, an unreachable kernel, and a kernel that refused (the status's own reason
  relayed);
- withdraw posts /usertodo/withdraw and words ok, the four kinds of ok:false, an unreachable kernel and a
  refusal; a request the person already answered or dismissed, or the session already withdrew, is a
  plain non-error answer with the time;
- the per-install switch, bus side: read from the kernel's file, boolean only, memoized on the file's
  stat, both tools refused before any post while off;
- a connected session learns of a flip: tools/list omits the pair while off, the initialize reply
  declares listChanged, the poll thread sends notifications/tools/list_changed once per flip, and a
  malformed poll interval falls back to the default and is said once.

Synthetic fixtures only: private placeholder uuids, the notes-api demo world.
"""
import ast
import contextlib
import errno
import inspect
import io
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = load_source("romp_postal_usertodos", os.path.join(BIN, "romp-postal-service"))

SID = "5c5c5c5c-1111-4222-8333-944444444401"


def _romp_words():
    """The veil's vocabulary, ROMP_WORDS in tests/test_injected_voice.py, read out of that file as a literal so this
    module follows the list when it grows (a copy here lagged silently)."""
    tree = ast.parse(Path(HERE, "test_injected_voice.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "ROMP_WORDS" for t in node.targets):
            return tuple(word for word, _why in ast.literal_eval(node.value))
    raise AssertionError("ROMP_WORDS not found in tests/test_injected_voice.py")


# the veil's vocabulary (tests/test_injected_voice.py ROMP_WORDS), the words only romp knows
ROMP_WORDS = _romp_words()


def _switch(on):
    """Write the kernel's per-install switch file the way _set_user_todos does (or remove it)."""
    p = pm.USER_TODOS_SWITCH
    pm._user_todos_switch_cache.clear()
    if on is None:
        p.unlink(missing_ok=True)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"enabled": bool(on), "gt": 1}))


class ToolSurface(unittest.TestCase):
    def _tool(self, name):
        return next((t for t in pm.MCP_TOOLS if t["name"] == name), None)

    def test_both_tools_are_registered_after_set_working_and_before_check_sent(self):
        names = [t["name"] for t in pm.MCP_TOOLS]
        self.assertEqual(names[names.index("set_working") + 1:names.index("check_sent")],
                         ["add_user_todo", "withdraw_user_todo"])
        self.assertEqual(pm.USER_TODO_TOOLS, ("add_user_todo", "withdraw_user_todo"))

    def test_add_requires_text_and_offers_detail_and_a_boolean_blocking(self):
        t = self._tool("add_user_todo")
        self.assertEqual(t["inputSchema"]["required"], ["text"])
        props = t["inputSchema"]["properties"]
        self.assertEqual(set(props), {"text", "detail", "blocking"})
        self.assertEqual(props["blocking"]["type"], "boolean")
        self.assertIn("cannot go on without", props["blocking"]["description"])

    def test_withdraw_requires_the_id(self):
        t = self._tool("withdraw_user_todo")
        self.assertEqual(t["inputSchema"]["required"], ["id"])
        self.assertEqual(set(t["inputSchema"]["properties"]), {"id"})

    def test_descriptions_speak_as_the_person_you_work_for_and_say_request(self):
        for name in ("add_user_todo", "withdraw_user_todo"):
            desc = self._tool(name)["description"]
            self.assertIn("person you work for", desc)
            self.assertIn("request", desc)
            for word in ROMP_WORDS:
                self.assertNotIn(word, desc.lower(), (name, word))
            for prop in self._tool(name)["inputSchema"]["properties"].values():
                for word in ROMP_WORDS:
                    self.assertNotIn(word, str(prop.get("description") or "").lower(), (name, word))

    def test_add_teaches_withdrawal_at_registration_time(self):
        self.assertIn("withdraw_user_todo", self._tool("add_user_todo")["description"])


class Dispatch(unittest.TestCase):
    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = {"ok": True, "todoId": "ut-9f2c1a34"}
        pm._kernel_post = lambda path, body, timeout=2: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (SID, "api")
        pm._heartbeat = lambda *a, **k: None
        _switch(True)

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

    def test_register_posts_to_the_kernel_as_the_calling_session_with_a_boolean_blocking(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the auth-scheme decision to wire login",
                                                  "detail": "OAuth vs cookie"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/usertodo", {"id": SID, "text": "Need the auth-scheme decision to wire login",
                                                     "detail": "OAuth vs cookie", "blocking": False})])
        pm._mcp_call("add_user_todo", {"text": "Need the port", "blocking": True})
        self.assertIs(self.posts[-1][1]["blocking"], True)
        pm._mcp_call("add_user_todo", {"text": "Need the port", "blocking": "yes"})
        self.assertEqual(self.posts[-1][1]["blocking"], "yes", "a non-boolean is handed to the kernel, which refuses it")

    def test_register_echoes_the_minted_id_and_the_withdraw_contract(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a test credential"})
        self.assertFalse(err)
        self.assertIn("Noted (id ut-9f2c1a34)", out)
        self.assertIn("withdraw_user_todo", out, "the contract rides the confirmation")
        self.assertIn("request", out)

    def test_register_without_detail_posts_an_empty_detail(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertFalse(err)
        self.assertEqual(self.posts[0][1]["detail"], "")

    def test_register_without_text_is_refused_before_any_post(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "   "})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_register_outside_a_session_is_refused(self):
        pm._self_identity = lambda: (None, None)
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_an_unreachable_kernel_is_loud_never_a_silent_drop(self):
        self.canned = None
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertIn("will NOT see it", out)

    def test_a_refusal_relays_the_kernels_reason_in_one_sentence(self):
        self.canned = {"ok": False, "status": 409,
                       "error": json.dumps({"ok": False, "error": "requests from sessions are turned off on this machine"})}
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertEqual(out, "Not saved: requests from sessions are turned off on this machine.")
        self.canned = {"ok": False, "status": 400, "error": json.dumps({"ok": False, "error": "'blocking' must be true or false, got \"yes\""})}
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port", "blocking": "yes"})
        self.assertTrue(err)
        self.assertIn("'blocking' must be true or false", out)

    def test_an_answer_without_a_minted_id_is_loud_too(self):
        self.canned = {"ok": False, "todoId": ""}
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(err)
        self.assertIn("NOT", out)

    def test_withdraw_posts_the_id_pair_and_confirms(self):
        self.canned = {"ok": True, "state": "withdrawn", "at": 1781200000, "owner": True}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertFalse(err)
        self.assertEqual(self.posts, [("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})])
        self.assertEqual(out, "Withdrawn: ut-9f2c1a34 no longer stands.")

    def test_withdraw_refused_by_a_kernel_without_the_account_is_loud(self):
        self.canned = {"ok": False, "error": "no open request with that id"}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-deadbeef"})
        self.assertTrue(err)
        self.assertIn("Nothing changed", out)
        self.assertNotIn(" at ", out)

    def test_withdraw_with_an_unreachable_kernel_says_it_still_stands(self):
        self.canned = None
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("still stands", out)

    def test_withdraw_refused_with_a_status_relays_the_reason(self):
        self.canned = {"ok": False, "status": 502,
                       "error": json.dumps({"ok": False, "error": "the tunnel to TESTHOST is not answering (re-dialing)"})}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("did not happen", out)
        self.assertIn("not answering", out)

    def test_withdraw_without_an_id_is_refused(self):
        out, err = pm._mcp_call("withdraw_user_todo", {})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])

    def test_withdraw_outside_a_session_is_refused(self):
        pm._self_identity = lambda: (None, None)
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertEqual(self.posts, [])


class Account(unittest.TestCase):
    """The kernel's account on an ok:false (state / at / owner) picks the answer: a request the person
    answered or dismissed, or one this session already withdrew, is a plain answer with no error flag;
    only a not-yours or unknown id, an unreadable record or an unreadable store is an error."""

    SID = "5c5c5c5c-1111-4222-8333-944444444402"
    AT = 1781200000

    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = {}
        pm._kernel_post = lambda path, body, timeout=2: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (self.SID, "api")
        pm._heartbeat = lambda *a, **k: None
        _switch(True)

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

    def _withdraw(self, **acct):
        self.canned = dict({"ok": False, "error": "no open request with that id"}, **acct)
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertEqual(self.posts[-1], ("/usertodo/withdraw", {"id": self.SID, "todoId": "ut-9f2c1a34"}))
        return out, err

    def test_answered_by_the_person_is_plain_with_the_time_and_no_error(self):
        out, err = self._withdraw(state="answered", at=self.AT, owner=True)
        self.assertFalse(err, "the need is met: not the agent's failure")
        self.assertIn("Already closed", out)
        self.assertIn("the person you work for answered ut-9f2c1a34", out)
        self.assertIn(pm._when_words(self.AT), out)
        self.assertTrue(out.endswith("Nothing to withdraw."), out)

    def test_dismissed_by_the_person_is_plain_with_the_time_and_no_error(self):
        out, err = self._withdraw(state="dismissed", at=self.AT, owner=True)
        self.assertFalse(err)
        self.assertIn("the person you work for dismissed ut-9f2c1a34", out)
        self.assertTrue(out.endswith("Nothing to withdraw."), out)

    def test_already_withdrawn_by_this_session_is_plain_and_no_error(self):
        out, err = self._withdraw(state="withdrawn", at=self.AT, owner=True)
        self.assertFalse(err)
        self.assertIn("Already withdrawn: ut-9f2c1a34 was taken back", out)
        self.assertIn(pm._when_words(self.AT), out)
        self.assertTrue(out.endswith("Nothing changed."), out)

    def test_an_unknown_id_is_the_error_it_always_was(self):
        out, err = self._withdraw(state="unknown", at=None, owner=False)
        self.assertTrue(err)
        self.assertEqual(out, "No request ut-9f2c1a34 of yours. Nothing changed.")

    def test_the_askers_own_row_in_an_unreadable_shape_is_an_error_that_says_so(self):
        why = "malformed closing stamp on ut-9f2c1a34: resolved=True (a stamp is {kind: answered | dismissed | withdrawn, t})"
        out, err = self._withdraw(state="unknown", at=None, owner=True, error=why)
        self.assertTrue(err)
        self.assertIn("Couldn't read the record of ut-9f2c1a34", out)
        self.assertIn(why, out)
        self.assertNotIn("of yours", out)
        self.assertIn("Nothing changed", out)
        for word in ROMP_WORDS:
            self.assertNotIn(word, out.lower(), word)
        self.canned = {"ok": False, "state": "unknown", "at": None, "owner": True}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertIn("its closing record is unreadable", out)

    def test_an_unreadable_store_is_an_error_that_names_the_store_never_not_yours(self):
        out, err = self._withdraw(state="unknown", at=None, owner=None,
                                  error="the request store is unreadable (see the kernel log)")
        self.assertTrue(err)
        self.assertNotIn("of yours", out)
        self.assertIn("Nothing changed", out)
        self.assertIn("was not withdrawn", out)

    def test_not_the_askers_row_is_an_error_whatever_its_state_says(self):
        out, err = self._withdraw(state="answered", at=self.AT, owner=False)
        self.assertTrue(err)
        self.assertIn("No request ut-9f2c1a34 of yours", out)

    def test_a_closed_row_with_no_time_known_drops_the_time_phrase(self):
        out, err = self._withdraw(state="answered", owner=True)
        self.assertFalse(err)
        self.assertEqual(out, "Already closed: the person you work for answered ut-9f2c1a34. Nothing to withdraw.")

    def test_every_answer_says_request_and_never_todo_or_note(self):
        for acct in ({"state": "answered", "at": self.AT, "owner": True}, {"state": "dismissed", "at": self.AT, "owner": True},
                     {"state": "withdrawn", "at": self.AT, "owner": True}, {"state": "unknown", "at": None, "owner": False},
                     {"state": "unknown", "at": None, "owner": True}, {"state": "unknown", "at": None, "owner": None}, {}):
            out, _err = self._withdraw(**acct)
            low = out.lower()
            self.assertNotIn("todo", low, out)
            self.assertNotIn("note", low.replace("noted", ""), out)
            self.assertIn("ut-9f2c1a34", out)

    def test_ok_true_is_withdrawn_whatever_else_rides_along(self):
        self.canned = {"ok": True, "state": "withdrawn", "at": self.AT, "owner": True}
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertFalse(err)
        self.assertIn("Withdrawn", out)


class WhenWords(unittest.TestCase):
    """_when_words: the closing time as a phrase a reader can place (today, yesterday, or a dated day), in
    local time. TZ is pinned to UTC for the run so the expected strings are exact."""

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
        self.assertEqual(pm._when_words(self.NOON + 2 * 86400, now=self.NOON), " on 2026-06-13 at 12:00")

    def test_no_time_is_the_empty_phrase(self):
        for t in (None, 0, "", "soon", -5, 10 ** 20):
            self.assertEqual(pm._when_words(t, now=self.NOON), "", repr(t))

    def test_defaults_to_the_clock(self):
        import time as _t
        self.assertTrue(pm._when_words(int(_t.time())).endswith(" today"))


class Switch(unittest.TestCase):
    """The per-install switch, bus side: the kernel writes STATE/user-todos-enabled.json, the bus reads that
    file (never user-todos.json, the store), boolean only, memoized on its stat."""

    def setUp(self):
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        pm._kernel_post = lambda path, body, timeout=2: (self.posts.append((path, body))
                                                         or {"ok": True, "todoId": "ut-9f2c1a34"})
        pm._self_identity = lambda: (SID, "api")
        pm._heartbeat = lambda *a, **k: None
        pm._user_todos_switch_bad.clear()
        _switch(None)

    def tearDown(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        _switch(None)

    def test_the_switch_reads_the_kernels_file_not_the_store(self):
        self.assertEqual(pm.USER_TODOS_SWITCH.name, "user-todos-enabled.json")
        self.assertEqual(pm.USER_TODOS_SWITCH.parent, pm.STATE.parent, "the kernel's STATE dir")

    def test_only_a_literal_true_reads_on(self):
        self.assertFalse(pm._user_todos_on(), "no file: the shipped default")
        _switch(False)
        self.assertFalse(pm._user_todos_on())
        with contextlib.redirect_stderr(io.StringIO()):
            for bad in ("not json", json.dumps(["enabled"]), json.dumps({"enabled": "true"}), json.dumps({"enabled": 1})):
                pm._user_todos_switch_cache.clear()
                pm.USER_TODOS_SWITCH.write_text(bad)
                self.assertFalse(pm._user_todos_on(), bad)
        _switch(True)
        self.assertTrue(pm._user_todos_on())

    def test_the_read_is_memoized_on_the_files_stat(self):
        _switch(True)
        self.assertTrue(pm._user_todos_on())
        reads = []
        real = Path.read_text
        with mock.patch.object(Path, "read_text", lambda p, *a, **k: reads.append(1) or real(p, *a, **k)):
            self.assertTrue(pm._user_todos_on())
            self.assertTrue(pm._user_todos_on())
        self.assertEqual(reads, [], "an unchanged file is never read twice")
        _switch(False)
        self.assertFalse(pm._user_todos_on())

    def test_reading_never_creates_the_file(self):
        pm._user_todos_on()
        self.assertFalse(pm.USER_TODOS_SWITCH.exists())

    def test_a_stat_that_fails_for_another_reason_reads_off_and_is_said_once(self):
        # the kernel reader's rule on the bus side: a present file the bus cannot stat reads OFF and is said once
        # per failure, not on every tools/list and not never
        _switch(True)
        real_stat = Path.stat

        def stat(p, *a, **k):
            if str(p) == str(pm.USER_TODOS_SWITCH):
                raise PermissionError(errno.EACCES, "Permission denied", str(p))
            return real_stat(p, *a, **k)
        err = io.StringIO()
        with mock.patch.object(Path, "stat", stat), contextlib.redirect_stderr(err):
            self.assertFalse(pm._user_todos_on(), "a file the bus cannot stat reads OFF")
            self.assertFalse(pm._user_todos_on())
            self.assertFalse(pm._user_todos_on())
        self.assertEqual(err.getvalue().count("\n"), 1, err.getvalue())
        self.assertIn("stat failed", err.getvalue())
        self.assertIn("reading it as OFF", err.getvalue())
        self.assertTrue(pm._user_todos_on(), "the stat back, the file is read as it is")

    def test_the_tools_list_omits_both_tools_while_off_and_offers_them_while_on(self):
        names_off = {t["name"] for t in pm._tools_offered()}
        self.assertNotIn("add_user_todo", names_off)
        self.assertNotIn("withdraw_user_todo", names_off)
        self.assertEqual(names_off, {t["name"] for t in pm.MCP_TOOLS} - set(pm.USER_TODO_TOOLS))
        _switch(True)
        self.assertEqual(pm._tools_offered(), pm.MCP_TOOLS, "on: the full list, same objects")

    def test_the_stdio_server_answers_tools_list_from_the_gated_list(self):
        src = inspect.getsource(pm.mcp)
        self.assertIn('"tools": _tools_offered()', src)
        self.assertNotIn('"tools": MCP_TOOLS}', src)

    def test_a_call_anyway_is_refused_plainly_before_any_post(self):
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the auth-scheme decision"})
        self.assertTrue(err)
        self.assertEqual(out, pm.USER_TODOS_OFF_ADD)
        self.assertIn("turned off on this machine", out)
        self.assertIn("will NOT see it", out)
        out, err = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(err)
        self.assertEqual(out, pm.USER_TODOS_OFF_WITHDRAW)
        self.assertEqual(self.posts, [], "nothing reached the kernel")

    def test_the_refusal_outranks_the_identity_and_shape_checks(self):
        pm._self_identity = lambda: (None, None)
        self.assertIn("turned off", pm._mcp_call("add_user_todo", {"text": "  "})[0])
        self.assertIn("turned off", pm._mcp_call("withdraw_user_todo", {})[0])
        self.assertEqual(self.posts, [])

    def test_the_refusals_say_request_and_keep_the_veil(self):
        for text in (pm.USER_TODOS_OFF_ADD, pm.USER_TODOS_OFF_WITHDRAW):
            self.assertIn("request", text.lower())
            self.assertNotIn("todo", text.lower())
            for word in ROMP_WORDS + ("gear",):
                self.assertNotIn(word, text.lower(), word)

    def test_on_the_call_goes_through_as_before(self):
        _switch(True)
        out, err = pm._mcp_call("add_user_todo", {"text": "Need the auth-scheme decision"})
        self.assertFalse(err)
        self.assertEqual([p[0] for p in self.posts], ["/usertodo"])


class ListChanged(unittest.TestCase):
    """A flip of the switch reaches a session that is already connected: the stdio server declares
    tools.listChanged, a poll thread stats the switch file and writes notifications/tools/list_changed
    when the listed tools changed. Drives the real shim as a subprocess over its stdio, hermetic. The other
    half, no line when nothing changed, is SwitchWatch's in process (test_a_rewrite_that_keeps_the_value_is_not_a_change):
    over a subprocess it could only be asserted as silence across a wall-clock window."""
    POLL = 0.2

    def setUp(self):
        _switch(None)
        self.tmp = tempfile.mkdtemp()
        seam = os.path.join(self.tmp, "sessions.json")
        with open(seam, "w") as f:
            f.write("[]")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        closed = s.getsockname()[1]          # bound-then-released: nothing answers there
        s.close()
        env = dict(os.environ)
        for k in ("CLAUDE_CODE_SESSION_ID", "ROMP_SID"):
            env.pop(k, None)
        env.update({
            "ROMP_STATE_DIR": str(pm.STATE.parent),   # pm's OWN root, the file _switch() writes
            "ROMP_POSTAL_SWITCH_POLL": str(self.POLL),
            "ROMP_POSTAL_PORT": str(closed),
            "ROMP_KERNEL_PORT": str(closed),
            "ROMP_POSTAL_CLIENT_ONLY": "1",
            "ROMP_POSTAL_PEERS": "0",
            "ROMP_SESSIONS_FILE": seam,
            "ROMP_SERVE_TOKEN": "test-token",
        })
        self.p = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-postal-service"), "mcp"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1, env=env)
        self.lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.p.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def tearDown(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()
            self.p.wait(timeout=10)
        _switch(None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _send(self, obj):
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def _recv(self, timeout):
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            return None
        return json.loads(line) if line else None

    def _init(self):
        self._send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "t", "version": "1"}}})
        res = self._recv(30)
        self.assertIsNotNone(res, "the shim answered initialize")
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return res

    def _tools(self, rid):
        self._send({"jsonrpc": "2.0", "id": rid, "method": "tools/list"})
        for _ in range(4):
            res = self._recv(30)
            self.assertIsNotNone(res, "the shim answered tools/list")
            if res.get("id") == rid:
                return {t["name"] for t in res["result"]["tools"]}
        self.fail("no tools/list reply")

    def _await_list_changed(self):
        note = self._recv(max(15.0, self.POLL * 20))
        self.assertIsNotNone(note, "an unsolicited notifications/tools/list_changed line arrived")
        self.assertEqual(note.get("method"), "notifications/tools/list_changed")
        self.assertNotIn("id", note, "a notification, not a response")
        self.assertEqual(note.get("jsonrpc"), "2.0")

    def test_initialize_declares_list_changed(self):
        res = self._init()
        self.assertEqual(res["id"], 1)
        self.assertIs(res["result"]["capabilities"]["tools"].get("listChanged"), True)

    def test_a_flip_on_reaches_the_connected_session(self):
        self._init()
        self.assertNotIn("add_user_todo", self._tools(2), "off at connect: not listed")
        _switch(True)
        self._await_list_changed()
        names = self._tools(3)
        self.assertIn("add_user_todo", names)
        self.assertIn("withdraw_user_todo", names)

    def test_a_flip_off_reaches_it_too(self):
        _switch(True)
        self._init()
        self.assertIn("add_user_todo", self._tools(2), "on at connect: listed")
        _switch(False)
        self._await_list_changed()
        self.assertNotIn("add_user_todo", self._tools(3))
        _switch(True)
        self._await_list_changed()
        self.assertIn("add_user_todo", self._tools(4))

    def test_the_default_poll_is_a_few_seconds(self):
        self.assertGreaterEqual(pm.SWITCH_POLL, 1.0, "not a busy loop")
        self.assertLessEqual(pm.SWITCH_POLL, 5.0)

    def test_both_stdout_writers_take_the_one_lock(self):
        src = inspect.getsource(pm.mcp)
        self.assertIn("out_lock = threading.Lock()", src)
        self.assertIn("with out_lock:", src)
        self.assertIn('"capabilities": {"tools": {"listChanged": True}}', src)
        self.assertIn('"method": "notifications/tools/list_changed"', src)
        self.assertIn("_switch_poll_loop, args=(", src, "the poll has its own thread")


class SwitchWatch(unittest.TestCase):
    """The change detector behind the poll, in process: one stat per call, the file read only when its
    signature moved, True only when the listed tools changed. The poll interval comes from a guarded read of
    its environment knob: a malformed value falls back to the default and is said once."""

    def setUp(self):
        _switch(None)

    def tearDown(self):
        _switch(None)

    def test_first_call_baselines_and_a_flip_is_one_true(self):
        w = pm._SwitchWatch()
        self.assertFalse(w.flipped(), "nothing moved since construction")
        _switch(True)
        self.assertTrue(w.flipped(), "off to on")
        self.assertFalse(w.flipped(), "already reported")
        _switch(False)
        self.assertTrue(w.flipped(), "on to off")
        self.assertFalse(w.flipped())

    def test_a_rewrite_that_keeps_the_value_is_not_a_change(self):
        _switch(True)
        w = pm._SwitchWatch()
        pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": True, "gt": 424242}))
        pm._user_todos_switch_cache.clear()
        self.assertFalse(w.flipped())
        _switch(None)
        self.assertTrue(w.flipped(), "the file going away reads as OFF, a change from on")
        _switch(False)
        self.assertFalse(w.flipped(), "absent to false: the same listed tools")

    def test_it_stats_and_reads_only_on_a_moved_signature(self):
        w = pm._SwitchWatch()
        reads = []
        saved = pm._user_todos_on
        pm._user_todos_on = lambda: reads.append(1) or False
        try:
            w.flipped(); w.flipped(); w.flipped()
            self.assertEqual(reads, [], "an unchanged file is never read, only stat'ed")
            _switch(False)
            w.flipped()
            self.assertEqual(reads, [1], "one read per moved signature")
        finally:
            pm._user_todos_on = saved

    def test_a_malformed_poll_interval_falls_back_and_is_said_once(self):
        pm._switch_poll_said.clear()
        with mock.patch.dict(os.environ, {"ROMP_POSTAL_SWITCH_POLL": "soon"}):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(pm._switch_poll_seconds(), 2.0)
                self.assertEqual(pm._switch_poll_seconds(), 2.0)
            self.assertEqual(err.getvalue().count("\n"), 1, err.getvalue())
            self.assertIn("ROMP_POSTAL_SWITCH_POLL", err.getvalue())
        with mock.patch.dict(os.environ, {"ROMP_POSTAL_SWITCH_POLL": "0.001"}):
            self.assertEqual(pm._switch_poll_seconds(), 0.05, "floored: never a busy loop")
        with mock.patch.dict(os.environ, {"ROMP_POSTAL_SWITCH_POLL": "4"}):
            self.assertEqual(pm._switch_poll_seconds(), 4.0)
        pm._switch_poll_said.clear()


if __name__ == "__main__":
    unittest.main()
