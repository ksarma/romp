#!/usr/bin/env python3
"""add_user_todo's `file` when the argument is not a string, and the words the two user-todo tools use
for the todo (the todo-file follow-on's review, 2026-09-07).

The tool's schema says `file` is a string, but nothing between the model and _mcp_call enforces it (the
MCP dispatcher hands `arguments` on raw), so a list or a dict can arrive. The tool used to str() every
value, which turned `["/x/docs/report.md"]` into the text "['/x/docs/report.md']" — a RELATIVE spelling
the kernel then joined onto the session's cwd and stored as an absolute path naming nothing, with no
warning: the chip opened nothing, no Send offered the todo, and the tool's reply was the plain "Noted".
The kernel's own branch for a non-string body value (keep it as given, warn naming the shape;
tests/test_kernel_todo_file_paths.py) was reachable only by a hand-built POST. Now the tool hands a
non-string on AS GIVEN, so that branch answers the tool's only client (NonStringFile at the post, and
WiredToTheKernel through the real /usertodo route). None and a blank string are still no file.

The tools' descriptions, their arguments' descriptions and the add tool's own reply call the object a
todo or a need, never a "request" — the word CONTEXT.md's User todo entry lists under _Avoid_, which the
same follow-on purged from the docs while the strings an agent reads still carried it (Vocabulary).

Named test_*.py like every Python test module (CLAUDE.md, tests/README.md), and held to that name
(UnderTheRatchets): the ratchets over tests/ visit only files that pass `fn.startswith("test_")`, while
pytest's default collection also takes *_test.py, so a module named that way runs and is never scanned.
This one shipped as postal_service_todo_file_test.py and was renamed in the same review.

SYNTHETIC fixtures only: a private placeholder sid, the notes-api demo world under a temp dir.
"""
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — both resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = load_source("romp_postal_todo_file_shape", os.path.join(BIN, "romp-postal-service"))
km = load_source("romp_kernel_postal_todo_file", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# PRIVATE synthetic sid (the goal-store fixture rule, generalized: rows minted under the shared
# placeholder can be reached by another module's fixtures).
PSID = "6a6a6a6a-1111-4222-8333-944444444444"
TEXT = "Need a look at the findings report"


def _avoid_words(context_md, term):
    """The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped — the reader
    the reference and guide tests use, so the tool strings are held to the docs' one list."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    avoid = re.search(r"^_Avoid_:(.*)$", m.group(1), re.M)
    assert avoid, "CONTEXT.md entry %r has no _Avoid_ line" % term
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [w.strip() for w in bare.split(",") if w.strip()]


def _serve_post(path, body, headers):
    """Drive the kernel's REAL do_POST dispatcher over a fake socket, in process (the harness
    tests/test_kernel_todo_file_paths.py drives the route with)."""
    raw = json.dumps(body).encode()
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    hdrs = dict(headers)
    hdrs.setdefault("Content-Length", str(len(raw)))
    h.headers = hdrs
    h.path = path
    h.command = "POST"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO(raw)
    h.close_connection = True
    captured = {}
    h.send_response = lambda code, *a: captured.__setitem__("status", code)
    h.send_header = lambda k, v: None
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_POST()
    return captured.get("status"), h.wfile.getvalue()


class _Stubbed(unittest.TestCase):
    """The postal tool with its kernel post captured: the calling session is PSID, the switch is on."""

    MINTED = {"ok": True, "todoId": "ut-0a1b2c3d"}

    def setUp(self):
        # Every restore is an addCleanup registered before the change it undoes.
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat, pm.USER_TODOS_SWITCH)
        self.addCleanup(self._restore)
        self.posts = []
        self.canned = dict(self.MINTED)
        pm._kernel_post = lambda path, body, timeout=4.0: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (PSID, "api")
        pm._heartbeat = lambda *a, **k: None
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        pm.USER_TODOS_SWITCH = Path(self.td.name, "user-todos-enabled.json")
        pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": True, "gt": 1}))

    def _restore(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat, pm.USER_TODOS_SWITCH = self._saved

    def add(self, file_):
        out, err = pm._mcp_call("add_user_todo", {"text": TEXT, "file": file_})
        return out, err, self.posts[-1][1]


class NonStringFile(_Stubbed):
    def test_a_list_rides_the_post_as_given_never_as_its_text(self):
        given = ["/TESTDIR/notes-api/docs/report.md"]
        out, err, body = self.add(given)
        self.assertFalse(err)
        self.assertEqual(body["file"], given)
        self.assertIsInstance(body["file"], list, "the shape the kernel names: never the text \"['…']\", a "
                                                   "relative spelling it would join onto the cwd")
        self.assertIn("ut-0a1b2c3d", out)

    def test_every_non_string_shape_is_handed_on_for_the_kernel_to_name(self):
        # a value that is not a path is still a value the agent gave: the kernel says what it made of
        # it, so even a falsy one (an empty list, False) is posted — never dropped as if no file
        for given in ({"path": "/TESTDIR/notes-api/docs/report.md"}, 7, 2.5, True, [], {}, 0, False):
            with self.subTest(file=given):
                _, err, body = self.add(given)
                self.assertFalse(err)
                self.assertIn("file", body)
                self.assertEqual(body["file"], given)
                self.assertIs(type(body["file"]), type(given), "as given: not str()'d, not coerced")

    def test_none_and_a_blank_string_are_still_no_file(self):
        for given in (None, "", "   "):
            with self.subTest(file=given):
                _, _, body = self.add(given)
                self.assertNotIn("file", body, "the shape the route always took")
        pm._mcp_call("add_user_todo", {"text": "Need the staging port"})
        self.assertNotIn("file", self.posts[-1][1])

    def test_a_string_is_stripped_as_before(self):
        _, _, body = self.add("  /TESTDIR/notes-api/docs/report.md \n")
        self.assertEqual(body["file"], "/TESTDIR/notes-api/docs/report.md")

    def test_the_kernels_words_for_the_shape_reach_the_agent(self):
        self.canned = dict(self.MINTED, warning="the file value ['a'] is not a path string, so it was kept as given")
        out, err, _ = self.add(["a"])
        self.assertFalse(err, "filed all the same: a warning is not a failure")
        self.assertIn("Noted (id ut-0a1b2c3d)", out)
        self.assertIn("About the file: the file value ['a'] is not a path string", out, "relayed whole")


class WiredToTheKernel(unittest.TestCase):
    """The tool's post handed to the REAL /usertodo route (the kernel's dispatcher, in process): the
    kernel's answer for a non-string `file` reaches the agent through the tool's reply, and the store
    keeps the value as given instead of <cwd>/['…']. PSID has a recorded cwd, the notes-api root, so a
    relative STRING still resolves against it — the control."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.tmp = os.path.realpath(self.td.name)
        self._saved_state = jd.STATE
        self.addCleanup(self._restore_state)
        jd.STATE = Path(self.tmp) / "state"
        jd.STATE.mkdir()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        self.root = os.path.join(self.tmp, "notes-api")
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write("# Findings\n")
        self._saved_km = (km._cwd_of, km._push_all, km._push_soon)
        self.addCleanup(self._restore_km)
        km._cwd_of = lambda sid: self.root if sid == PSID else ""
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: None
        self._saved_pm = (pm._kernel_post, pm._self_identity, pm._heartbeat, pm.USER_TODOS_SWITCH)
        self.addCleanup(self._restore_pm)
        pm._kernel_post = self._post
        pm._self_identity = lambda: (PSID, "api")
        pm._heartbeat = lambda *a, **k: None
        pm.USER_TODOS_SWITCH = jd.STATE / km.USER_TODOS_SWITCH_FILE   # the switch the kernel just turned on
        self.assertTrue(pm._user_todos_on())

    def _restore_state(self):
        jd.STATE = self._saved_state
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()

    def _restore_km(self):
        km._cwd_of, km._push_all, km._push_soon = self._saved_km

    def _restore_pm(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat, pm.USER_TODOS_SWITCH = self._saved_pm

    def _post(self, path, body, timeout=4.0):
        code, out = _serve_post(path, body, {"X-Romp-Token": km.TOKEN})
        return json.loads(out.decode() or "{}") if code and code // 100 == 2 else None

    def add(self, file_):
        out, err = pm._mcp_call("add_user_todo", {"text": TEXT, "file": file_})
        return out, err, km._user_todos()[PSID][-1]

    def naming(self):
        return km._user_todos_naming_file(PSID, os.path.realpath(self.fp))

    def test_a_list_is_kept_as_given_and_the_kernels_warning_is_in_the_reply(self):
        out, err, rec = self.add([self.fp])
        self.assertFalse(err, "filed all the same")
        self.assertIn("Noted (id ", out)
        self.assertIn("About the file:", out, "the kernel's words for a value that is not a path, relayed")
        self.assertEqual(rec["file"], str([self.fp]), "as given")
        self.assertFalse(rec["file"].startswith(self.root + os.sep), "never <cwd>/['…'], absolute and naming nothing")
        self.assertEqual(self.naming(), [], "a value kept as given names no file on disk")

    def test_a_dict_and_a_number_answer_the_same_way(self):
        for given in ({"path": self.fp}, 7):
            with self.subTest(file=given):
                out, err, rec = self.add(given)
                self.assertFalse(err)
                self.assertIn("About the file:", out)
                self.assertEqual(rec["file"], str(given))
                self.assertFalse(os.path.isabs(rec["file"]))

    def test_a_relative_string_still_resolves_against_the_cwd_with_no_warning(self):
        out, err, rec = self.add("docs/report.md")
        self.assertFalse(err)
        self.assertNotIn("About the file", out)
        self.assertEqual(rec["file"], self.fp)
        self.assertEqual(self.naming(), [{"id": rec["id"], "text": TEXT}], "a status on the file lists it")


class Vocabulary(_Stubbed):
    """The strings an agent reads from the two user-todo tools call the object a todo or a need, never
    by a word CONTEXT.md's User todo entry avoids: with "request" in the `file` description the schema
    and the docs disagreed on the object's name, and in a tool reply "the request" reads as the call
    itself. "ask" is skipped as the docs' tests skip it: a verb the prose may need."""

    def setUp(self):
        super().setUp()
        with open(os.path.join(ROOT, "CONTEXT.md"), encoding="utf-8") as f:
            self.avoid = _avoid_words(f.read(), "User todo")
        self.assertIn("request", self.avoid)

    def _assert_no_avoid_word(self, text, where):
        for word in self.avoid:
            if word == "ask":
                continue
            self.assertNotRegex(text, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                "%s says %r; CONTEXT.md avoids it" % (where, word))

    def test_the_tool_descriptions_and_their_arguments(self):
        for name in ("add_user_todo", "withdraw_user_todo"):
            t = next(t for t in pm.MCP_TOOLS if t["name"] == name)
            self._assert_no_avoid_word(t["description"], "%s's description" % name)
            for arg, spec in t["inputSchema"]["properties"].items():
                self._assert_no_avoid_word(spec["description"], "%s's `%s` description" % (name, arg))

    def test_the_file_description_still_says_what_the_argument_buys(self):
        t = next(t for t in pm.MCP_TOOLS if t["name"] == "add_user_todo")
        desc = t["inputSchema"]["properties"]["file"]["description"]
        self.assertIn("absolute path", desc)
        self.assertIn("link", desc, "the person sees the file as a link")
        self.assertIn("comments on that file", desc, "and their comments on it answer the todo")
        self.assertIn("todo", desc, "the object's name, the one the tool's own name carries")

    def test_the_add_tools_reply_around_a_warning(self):
        # the tool's own words; the kernel's warning is scanned where it is rendered (test_injected_voice.py)
        self.canned = dict(self.MINTED, warning="that path did not resolve on this machine")
        out, err, _ = self.add("docs/report.md")
        self.assertFalse(err)
        self._assert_no_avoid_word(out, "the add_user_todo reply")


class UnderTheRatchets(unittest.TestCase):
    """This module is named so the ratchets over tests/ scan it. tests/test_state_isolation_order.py (the
    hermetic-state preamble before the first load) and tests/test_postal_marker_form.py (no bare postal
    marker in a fixture) each visit only the files that pass `fn.startswith("test_") and fn.endswith(".py")`;
    pytest's default collection also takes *_test.py, so a module named that way runs and escapes both.
    This one shipped as postal_service_todo_file_test.py: an edit moving its load_source calls above the
    preamble would have passed the state-isolation ratchet unchanged, and a direct script run of the edited
    module would then have resolved STATE from the real ~/.local/state/romp (the 2026-08-12 incident the
    ratchet exists for). The ratchet's own reader is run over this file here too, so the module reports its
    preamble's order itself, whichever way it is run."""

    SELF = os.path.basename(os.path.realpath(__file__))

    def test_named_so_the_tests_ratchets_visit_it(self):
        self.assertTrue(self.SELF.startswith("test_") and self.SELF.endswith(".py"),
                        "%s: the ratchets over tests/ scan test_*.py only; a *_test.py name runs under pytest "
                        "and escapes them" % self.SELF)

    def test_the_state_isolation_ratchets_reader_sees_the_preamble_before_the_loads(self):
        ratchet = load_source("romp_state_isolation_ratchet", os.path.join(HERE, "test_state_isolation_order.py"))
        first_load, first_set, rsd_handled = ratchet.scan(os.path.realpath(__file__))
        self.assertIsNotNone(first_load, "this module loads romp code; the reader must see the load")
        self.assertIsNotNone(first_set, "the reader must see XDG_STATE_HOME assigned")
        self.assertIsNotNone(rsd_handled, "the reader must see ROMP_STATE_DIR handled")
        self.assertLess(first_set, first_load, "XDG_STATE_HOME is set before the first load")
        self.assertLess(rsd_handled, first_load, "ROMP_STATE_DIR is handled before the first load")
        self.assertNotIn(self.SELF, ratchet.EXEMPT, "no exemption: the preamble is the rule")


if __name__ == "__main__":
    unittest.main()
