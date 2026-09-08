#!/usr/bin/env python3
"""add_user_todo against a kernel that predates a todo's file: the reply says the file was not recorded
(the review, 2026-09-08).

The pre-follow-on /usertodo route reads id/text/detail alone and answers {ok, todoId} — the whole reply,
see `git show ad26f1a7:kernel/kernel.py` — while the route that takes `file` echoes it as the record
keeps it, or names in `warning` why it was kept as given (_user_todo_file answers one or the other for
every value the tool posts; None and a blank never leave the tool). The tool read only `warning`, so an
older kernel's answer to a post carrying `file` produced the plain "Noted … will see it": the todo stood
without its file, no chip, no Send offering it, and the agent had no reason to put the path anywhere
else. The window is real on a self-hosting install: the kernel keeps the code it started with until its
restart, while every new or revived session spawns this tool from the checkout. The kernel's own forward
to a remote already reads a reply with neither field as the older route and warns; a session's tool
posts to its own host's kernel, which that branch never sees, so the tool makes the same inference.

Now (AnOlderKernel): a post carrying `file` whose reply has neither `file` nor `warning` earns a sentence
behind the same "About the file:" lead-in the relayed warning uses — the path as posted, that it was not
recorded, why (the session manager on this machine is an older version), and the remedy — with no error
flag: the todo is filed and stands, and an error reads as "not saved", whose retry files a duplicate.
Unchanged (ANewerKernel, WiredToTheKernel): a reply echoing `file` with no warning stays silent about the
file; a warning is relayed alone, never doubled with a skew sentence; a post with no file reads nothing
into plain success. TheInference pins the two facts the reading rests on, on this checkout's kernel: the
tool posts `file` for every value but None and a blank, and _user_todo_file stores or warns for each.

Named test_*.py so the ratchets over tests/ visit it (the state-isolation preamble runs before the first
load). SYNTHETIC fixtures only: a private placeholder sid, the notes-api demo world under a temp dir.
"""
import ast
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
pm = load_source("romp_postal_todo_file_skew", os.path.join(BIN, "romp-postal-service"))
km = load_source("romp_kernel_postal_todo_file_skew", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# PRIVATE synthetic sid (the goal-store fixture rule, generalized: rows minted under the shared
# placeholder can be reached by another module's fixtures).
PSID = "7b7b7b7b-1111-4222-8333-944444444444"
TEXT = "Need a look at the findings report"
PATH = "/TESTDIR/notes-api/docs/report.md"
OLDER = {"ok": True, "todoId": "ut-0a1b2c3d"}          # the pre-follow-on route's whole answer
NEWER = dict(OLDER, file=PATH)                         # the route that takes the file echoes it
LEAD = "About the file:"


def _romp_words():
    """ROMP_WORDS as tests/test_injected_voice.py declares it, read from that file's source: the one
    list the veil is held to, without importing a module whose preamble loads the kernel again."""
    tree = ast.parse(open(os.path.join(HERE, "test_injected_voice.py"), encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ROMP_WORDS" for t in node.targets):
            return [word for word, _why in ast.literal_eval(node.value)]
    raise AssertionError("ROMP_WORDS not found in test_injected_voice.py")


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
    """The postal tool with its kernel post captured and its reply canned: the calling session is PSID,
    the switch is on. `canned` is what the kernel answers; the default is the older route's shape."""

    def setUp(self):
        # Every restore is an addCleanup registered before the change it undoes.
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat, pm.USER_TODOS_SWITCH)
        self.addCleanup(self._restore)
        self.posts = []
        self.canned = dict(OLDER)
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


class AnOlderKernel(_Stubbed):
    def test_the_reply_says_the_file_was_not_recorded_and_the_todo_stands(self):
        out, err, body = self.add(PATH)
        self.assertEqual(body["file"], PATH, "the tool posted the file")
        self.assertFalse(err, "the todo is filed and stands: a lost file is not a failure, and an error "
                              "reads as unsaved, whose retry files a duplicate")
        self.assertIn("Noted (id ut-0a1b2c3d)", out, "the filing is confirmed first")
        self.assertIn("withdraw_user_todo", out, "the withdraw contract still rides along")
        self.assertIn("%s %s was not recorded" % (LEAD, PATH), out, "the same lead-in the relayed warning "
                                                                    "uses, then the path as posted")
        self.assertLess(out.index("Noted"), out.index(LEAD), "the confirmation leads")

    def test_the_sentence_says_why_and_what_to_do(self):
        out, _, _ = self.add(PATH)
        self.assertIn("session manager on this machine", out, "the kernel, in the tool's own veiled noun")
        self.assertIn("older version", out, "the cause: version skew, not the path")
        self.assertIn("update and a restart", out, "the operator's remedy")
        self.assertIn("without a link to the file", out, "what the person sees")
        self.assertIn("withdraw this todo and file it again with the path in its text or detail", out,
                      "the agent's remedy: a path in the text or the detail is a link either way")

    def test_a_relative_spelling_is_named_as_posted(self):
        out, _, body = self.add("docs/report.md")
        self.assertEqual(body["file"], "docs/report.md")
        self.assertIn("%s docs/report.md was not recorded" % LEAD, out, "the tool never resolved it, so it "
                                                                        "names what it posted")

    def test_a_non_string_file_is_named_by_its_text(self):
        # a list rides the post as given (test_postal_service_todo_file.py); the sentence can only
        # name its text, the way the kernel's own warning for the shape does
        out, err, body = self.add([PATH])
        self.assertFalse(err)
        self.assertEqual(body["file"], [PATH])
        self.assertIn("%s %s was not recorded" % (LEAD, str([PATH])), out)

    def test_an_empty_warning_with_no_file_echo_is_still_the_older_route(self):
        # an empty warning is no warning (the File tests); with no `file` echoed either, nothing says
        # the file was kept, so the sentence stands
        self.canned = dict(OLDER, warning="")
        out, err, _ = self.add(PATH)
        self.assertFalse(err)
        self.assertIn("%s %s was not recorded" % (LEAD, PATH), out)

    def test_the_sentence_is_one_and_only_about_the_file(self):
        out, _, _ = self.add(PATH)
        self.assertEqual(out.count(LEAD), 1)
        self.assertNotIn("Couldn't save", out, "the todo was saved; only the file was lost")


class ANewerKernel(_Stubbed):
    """The route that takes the file: recorded means silent, a warning is relayed alone."""

    def test_a_recorded_file_earns_no_file_sentence(self):
        self.canned = dict(NEWER)
        out, err, _ = self.add(PATH)
        self.assertFalse(err)
        self.assertNotIn(LEAD, out, "the file is in the record: nothing to say about it")
        self.assertNotIn("not recorded", out)

    def test_a_recorded_file_with_an_empty_warning_is_silent_too(self):
        self.canned = dict(NEWER, warning="")
        out, _, _ = self.add(PATH)
        self.assertNotIn(LEAD, out, "an empty warning is no warning, and the file was kept")

    def test_a_recorded_relative_spelling_echoed_absolute_is_silent(self):
        # the kernel resolved docs/report.md against the session's cwd and echoes the absolute path
        self.canned = dict(OLDER, file=PATH)
        out, _, body = self.add("docs/report.md")
        self.assertEqual(body["file"], "docs/report.md")
        self.assertNotIn(LEAD, out)

    def test_the_kernels_warning_is_relayed_alone_and_no_skew_is_read(self):
        # a kept-as-given value: the route echoes the value AND warns
        warn = "the file path docs/report.md did not resolve to an absolute path (it is relative and no working directory is recorded for this session), so it was kept as given"
        self.canned = dict(OLDER, file="docs/report.md", warning=warn)
        out, err, _ = self.add("docs/report.md")
        self.assertFalse(err)
        self.assertIn(LEAD + " " + warn, out, "the kernel's words, relayed whole")
        self.assertEqual(out.count(LEAD), 1, "one sentence about the file, never a second")
        self.assertNotIn("not recorded", out)

    def test_a_warning_without_a_file_echo_is_relayed_alone_too(self):
        # whatever else a warning rides with, it is the kernel's account of the file and outranks
        # the tool's inference from the missing echo
        self.canned = dict(OLDER, warning="that path did not resolve on this machine")
        out, _, _ = self.add(PATH)
        self.assertIn(LEAD + " that path did not resolve on this machine", out)
        self.assertEqual(out.count(LEAD), 1)
        self.assertNotIn("not recorded", out)

    def test_no_file_posted_reads_no_skew_into_plain_success(self):
        for args in ({"text": TEXT}, {"text": TEXT, "file": ""}, {"text": TEXT, "file": "   "},
                     {"text": TEXT, "file": None}):
            with self.subTest(args=args):
                out, err = pm._mcp_call("add_user_todo", args)
                self.assertFalse(err)
                self.assertNotIn("file", self.posts[-1][1], "nothing posted, so nothing to be recorded")
                self.assertNotIn(LEAD, out)
                self.assertNotIn("not recorded", out)

    def test_an_unsaved_todo_is_still_the_loud_failure_never_the_file_sentence(self):
        # no id minted: the file sentence would describe a todo that does not exist
        for canned in (None, {"ok": False, "error": "id and text required"}, {"ok": True}):
            with self.subTest(canned=canned):
                self.canned = canned
                out, err = pm._mcp_call("add_user_todo", {"text": TEXT, "file": PATH})
                self.assertTrue(err)
                self.assertIn("will NOT see it", out)
                self.assertNotIn(LEAD, out)


class TheSentenceKeepsTheVeil(_Stubbed):
    """The tool's own words about the lost file are read by the agent like its descriptions: no
    tracking-system nouns (test_injected_voice.py's list), no word CONTEXT.md's User todo entry avoids,
    and the kernel is "the session manager", the noun set_emoji's reply already uses for it."""

    def setUp(self):
        super().setUp()
        self.out, _, _ = self.add(PATH)
        self.assertIn("not recorded", self.out, "the branch under test rendered")

    def test_no_tracking_system_nouns(self):
        words = _romp_words()
        self.assertIn("romp", words, "the list was read")
        for word in words:
            with self.subTest(word=word):
                self.assertNotIn(word, self.out.lower(), "%r names machinery the agent cannot see" % word)

    def test_no_word_the_docs_avoid_for_a_todo(self):
        with open(os.path.join(ROOT, "CONTEXT.md"), encoding="utf-8") as f:
            avoid = _avoid_words(f.read(), "User todo")
        self.assertIn("request", avoid)
        for word in avoid:
            if word == "ask":                  # a verb the prose may need, skipped as the docs' tests skip it
                continue
            with self.subTest(word=word):
                self.assertNotRegex(self.out, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                    "the reply says %r; CONTEXT.md avoids it" % word)

    def test_the_kernel_is_the_session_manager(self):
        self.assertIn("session manager", self.out)
        self.assertNotIn("kernel", self.out.lower(), "a noun the agent has no meaning for")
        # the precedent, rendered: set_emoji's reply for a kernel it could not reach
        saved = pm._publish_emoji
        self.addCleanup(setattr, pm, "_publish_emoji", saved)
        pm._publish_emoji = lambda mid, emoji: None
        unreachable, err = pm._mcp_call("set_emoji", {"emoji": "\u2705"})
        self.assertTrue(err)
        self.assertIn("session manager", unreachable, "the noun the tool already uses for the kernel")


class TheInference(unittest.TestCase):
    """The two facts the tool's reading of "neither field" rests on, pinned on this checkout's kernel:
    every value the tool posts as `file` earns a stored path or a warning from _user_todo_file (so the
    route that takes the file always echoes one of them), and the tool posts nothing for the values the
    helper answers (None, None) to."""

    VALUES = ("/TESTDIR/notes-api/docs/report.md", "docs/report.md", "~/notes/report.md", "./report.md",
              "file:///TESTDIR/notes-api/docs/report.md", "file:/TESTDIR/report.md", "file://TESTHOST/report.md",
              "https://example.invalid/report.md", "docs/re\x00port.md", "report.md",
              ["/TESTDIR/notes-api/docs/report.md"], {"path": "/TESTDIR/report.md"}, 7, 2.5, True, [], {}, 0, False)

    def setUp(self):
        self._saved = km._cwd_of
        self.addCleanup(self._restore)

    def _restore(self):
        km._cwd_of = self._saved

    def test_every_posted_value_earns_a_file_or_a_warning_with_or_without_a_cwd(self):
        for cwd in ("/TESTDIR/notes-api", ""):
            km._cwd_of = lambda sid, _cwd=cwd: _cwd if sid == PSID else ""
            for value in self.VALUES:
                with self.subTest(cwd=cwd, file=value):
                    stored, warning = km._user_todo_file(value, PSID)
                    self.assertTrue(stored or warning, "a value the tool posts is stored or warned about, "
                                                       "never (None, None): that pair is the older route's mark")

    def test_the_values_the_helper_answers_nothing_to_are_the_ones_the_tool_never_posts(self):
        for value in (None, "", "   ", "\n"):
            with self.subTest(file=value):
                self.assertEqual(km._user_todo_file(value, PSID), (None, None))


class WiredToTheKernel(unittest.TestCase):
    """The tool's post handed to the REAL /usertodo route of this checkout (the kernel's dispatcher, in
    process): the file is recorded and the reply says nothing about it; a kept-as-given value earns the
    kernel's one warning and no skew sentence on top. PSID has a recorded cwd, the notes-api root."""

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
        self.replies = []
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
        res = json.loads(out.decode() or "{}") if code and code // 100 == 2 else None
        self.replies.append(res)
        return res

    def add(self, file_):
        out, err = pm._mcp_call("add_user_todo", {"text": TEXT, "file": file_})
        return out, err, km._user_todos()[PSID][-1]

    def test_an_absolute_path_is_recorded_and_the_reply_is_silent_about_it(self):
        out, err, rec = self.add(self.fp)
        self.assertFalse(err)
        self.assertEqual(rec["file"], self.fp)
        self.assertEqual(self.replies[-1]["file"], self.fp, "this checkout's route echoes the record's file")
        self.assertNotIn(LEAD, out)

    def test_a_relative_path_resolves_against_the_cwd_and_is_silent(self):
        out, _, rec = self.add("docs/report.md")
        self.assertEqual(rec["file"], self.fp)
        self.assertNotIn(LEAD, out)

    def test_a_url_is_kept_as_given_with_the_kernels_one_warning_and_no_skew(self):
        out, err, rec = self.add("https://example.invalid/report.md")
        self.assertFalse(err)
        self.assertEqual(rec["file"], "https://example.invalid/report.md")
        self.assertIn(LEAD + " the file path https://example.invalid/report.md did not resolve", out)
        self.assertEqual(out.count(LEAD), 1)
        self.assertNotIn("not recorded", out)

    def test_a_non_string_is_kept_as_given_with_the_kernels_one_warning_and_no_skew(self):
        out, err, rec = self.add([self.fp])
        self.assertFalse(err)
        self.assertEqual(rec["file"], str([self.fp]))
        self.assertIn(LEAD + " the file value", out)
        self.assertEqual(out.count(LEAD), 1)
        self.assertNotIn("not recorded", out)

    def test_the_older_routes_reply_shape_through_the_same_wire_earns_the_sentence(self):
        # the control for the class: the same wire, the reply cut down to what the pre-follow-on route
        # answered (id/text/detail read, {ok, todoId} back), and the sentence appears — so the silence
        # above is this checkout's echo, not the tool ignoring the wire
        real = self._post

        def older(path, body, timeout=4.0):
            res = real(path, body, timeout)
            return {"ok": res["ok"], "todoId": res["todoId"]} if isinstance(res, dict) else res
        pm._kernel_post = older
        out, err, rec = self.add(self.fp)
        self.assertFalse(err)
        self.assertIn("%s %s was not recorded" % (LEAD, self.fp), out)
        self.assertEqual(rec["file"], self.fp, "this checkout's store did keep it: the cut-down reply stands in "
                                               "for the older route's answer alone")


if __name__ == "__main__":
    unittest.main()
