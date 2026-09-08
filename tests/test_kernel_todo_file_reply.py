#!/usr/bin/env python3
"""What POST /usertodo's reply says about a todo's `file`, held to what the record keeps (the todo-file
follow-on's review round 2, 2026-09-07). One rule: the reply describes the resolution the filing made,
not a second one, and a value the kernel cannot make a path is kept as given WITH a warning.

- The route resolved `file` twice: once inside the filing (what the store keeps) and once more for the
  reply's warning, each a fresh read of the session's cwd from the names registry. A cwd that became
  known between the two (a comment thread promoted while its todo was filing) stored the relative
  spelling — matched by no Send, ever — while the reply carried no warning, so the agent was never told
  to pass the absolute path; the reverse order warned falsely. _register_user_todo now returns the id,
  the stored file and the warning from ONE resolution, and the reply echoes `file` as the record keeps
  it (OneResolutionFeedsTheStoreAndTheReply).
- A falsy non-string body value (0, false, [], {}) was dropped before the filing (`fraw or None`) while
  the reply said it was kept as given; it is now kept like any other non-string, as its text
  (AFalsyNonStringFileIsKeptLikeAnyOther).
- A forwarded filing whose remote kernel predates a todo's file answered plain success while the file
  was neither stored there nor warned about; a kernel that takes the field echoes it (or warns), so a
  reply with neither is the older route, and the hub names the skew (TheForwardNamesAnOlderRemote).
- A `file` holding a NUL byte passed as an absolute path with no warning, and os.path.realpath raises
  ValueError on it under 3.12, so the except in _user_todos_naming_file was the only thing keeping every
  comments reply of that session alive — and nothing exercised it. Filing now warns, and the arm is
  pinned (ANulByteInTheFile).
- RFC 8089's no-authority spelling, file:/abs/path, has no `://`, so it slipped past the URI branch and
  the URL check and was joined onto the cwd as `<cwd>/file:/…` — absolute, hence silently wrong, the
  class round 1 fixed for file:// (ASingleSlashFileUri).

SYNTHETIC fixtures only: private placeholder sids, the notes-api demo world under a temp dir, TESTHOST.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_todo_file_reply", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# PRIVATE synthetic sids (the goal-store fixture rule, generalized: rows minted under the shared
# placeholder can be reached by another module's fixtures). RSID has a recorded cwd, RSID2 none.
RSID = "6c6c6c6c-1111-4222-8333-944444444444"
RSID2 = "6d6d6d6d-1111-4222-8333-944444444444"
TEXT = "Need a look at the findings report"
NUL_PATH = "/x\x00y/report.md"


def _serve_post(path, body=None, headers=None):
    """Drive the REAL do_POST dispatcher over a fake socket (the auth-hardening harness)."""
    raw = json.dumps(body).encode() if isinstance(body, (dict, list)) else (body or b"")
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    hdrs = dict(headers or {})
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


class _World(unittest.TestCase):
    """A STATE sandbox with user todos ON, a notes-api tree (docs/report.md) under a realpath'd temp dir,
    RSID's cwd recorded as its root, RSID2 with no recorded cwd, and the routes' pusher stubbed."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = os.path.realpath(self.td.name)
        self.saved = jd.STATE
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
        self.cwds = {RSID: self.root}
        self._saved = (km._cwd_of, km._push_all, km._push_soon)
        km._cwd_of = lambda sid: self.cwds.get(sid, "")
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: None

    def tearDown(self):
        km._cwd_of, km._push_all, km._push_soon = self._saved
        jd.STATE = self.saved
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        self.td.cleanup()

    def post(self, body):
        code, out = _serve_post("/usertodo", body, {"X-Romp-Token": km.TOKEN})
        return code, json.loads(out.decode() or "{}")

    def rows(self, sid):
        return km._user_todos().get(sid) or []

    def naming(self, sid, path):
        return km._user_todos_naming_file(sid, os.path.realpath(path))


class OneResolutionFeedsTheStoreAndTheReply(_World):
    def _cwd_sequence(self, *answers):
        """_cwd_of answering each value once, in order, and the calls counted — the handler thread has no
        names snapshot, so every resolution is a fresh registry read, and a flip between two reads is what
        the double resolution exposed."""
        calls = []

        def cwd(sid):
            calls.append(sid)
            return answers[min(len(calls), len(answers)) - 1]
        km._cwd_of = cwd
        return calls

    def test_a_cwd_that_becomes_known_mid_filing_leaves_the_store_and_the_reply_in_agreement(self):
        # before: stored "docs/report.md" (matched by nothing, ever), reply without a warning
        calls = self._cwd_sequence("", self.root)
        code, res = self.post({"id": RSID2, "text": TEXT, "file": "docs/report.md"})
        self.assertEqual(code, 200)
        self.assertEqual(self.rows(RSID2)[0]["file"], "docs/report.md", "kept as given: no cwd at the resolution")
        self.assertIn("no working directory is recorded", res.get("warning", ""),
                      "and the agent is told to pass the absolute path — the warning the second read lost")
        self.assertEqual(len(calls), 1, "one resolution: the route never re-reads the cwd for the reply")
        self.assertEqual(res["file"], "docs/report.md", "the reply says what the record keeps")

    def test_a_cwd_that_goes_unrecorded_mid_filing_does_not_warn_falsely(self):
        # before: stored absolute, reply with a false "no working directory is recorded" warning
        self._cwd_sequence(self.root, "")
        code, res = self.post({"id": RSID2, "text": TEXT, "file": "docs/report.md"})
        self.assertEqual(code, 200)
        self.assertEqual(self.rows(RSID2)[0]["file"], self.fp)
        self.assertNotIn("warning", res, "the record holds the absolute path: nothing to warn about")
        self.assertEqual(res["file"], self.fp)
        self.assertEqual([t["id"] for t in self.naming(RSID2, self.fp)], [res["todoId"]])

    def test_the_reply_echoes_the_file_as_the_record_keeps_it(self):
        code, res = self.post({"id": RSID, "text": TEXT, "file": "docs/report.md"})
        self.assertEqual((code, res["file"]), (200, self.fp), "resolved against the cwd: the absolute path")
        self.assertNotIn("warning", res)
        code, res = self.post({"id": RSID, "text": "Need a look at the other note", "file": "file://" + self.fp})
        self.assertEqual(res["file"], self.fp, "a URI: its path")
        url = "https://example.invalid/report.md"
        code, res = self.post({"id": RSID, "text": "Need a look at the published copy", "file": url})
        self.assertEqual(res["file"], url, "kept as given, and the reply says so")
        self.assertIn("did not resolve", res["warning"])
        self.assertEqual([r["file"] for r in self.rows(RSID)], [self.fp, self.fp, url])

    def test_a_filing_without_a_file_answers_as_before(self):
        code, res = self.post({"id": RSID, "text": "Need the staging port"})
        self.assertEqual(code, 200)
        self.assertEqual(set(res), {"ok", "todoId"}, "no file, no warning: nothing invented")
        self.assertNotIn("file", self.rows(RSID)[0])

    def test_register_user_todo_returns_the_triple_and_add_user_todo_its_id(self):
        tid, stored, warning = km._register_user_todo(RSID, TEXT, file="docs/report.md")
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$")
        self.assertEqual((stored, warning), (self.fp, None))
        tid2, stored2, warning2 = km._register_user_todo(RSID2, TEXT, "the morning report", file="docs/report.md")
        self.assertEqual(stored2, "docs/report.md")
        self.assertIn("did not resolve", warning2)
        tid3, stored3, warning3 = km._register_user_todo(RSID, "Need the staging port")
        self.assertEqual((stored3, warning3), (None, None))
        self.assertRegex(km._add_user_todo(RSID, TEXT, file=self.fp), r"^ut-[0-9a-f]{8}$", "the id alone, as every in-process filer reads it")
        recs = self.rows(RSID)
        self.assertEqual([r["id"] for r in recs[:2]], [tid, tid3])
        self.assertEqual((recs[0]["file"], recs[1].get("file"), recs[2]["file"]), (self.fp, None, self.fp))
        self.assertEqual(self.rows(RSID2)[0], {"id": tid2, "text": TEXT, "detail": "the morning report",
                                              "createdT": self.rows(RSID2)[0]["createdT"], "file": "docs/report.md"})


class AFalsyNonStringFileIsKeptLikeAnyOther(_World):
    FALSY = (0, False, [], {})

    def test_the_route_stores_the_text_of_a_falsy_non_string_and_the_warning_agrees(self):
        # before: nothing stored, while the reply said the value "was kept as given"
        for value in self.FALSY:
            with self.subTest(value=value):
                km._user_todos_cache.clear()
                (jd.STATE / "user-todos.json").unlink(missing_ok=True)
                code, res = self.post({"id": RSID, "text": TEXT, "file": value})
                self.assertEqual(code, 200)
                self.assertTrue(res["ok"], "filed all the same")
                self.assertIn("not a path string", res["warning"])
                self.assertIn(str(value), res["warning"])
                self.assertEqual(self.rows(RSID)[0]["file"], str(value), "kept as given, as the reply says")
                self.assertEqual(res["file"], str(value))

    def test_a_truthy_non_string_is_kept_the_same_way(self):
        code, res = self.post({"id": RSID, "text": TEXT, "file": ["a"]})
        self.assertEqual((code, res["file"], self.rows(RSID)[0]["file"]), (200, "['a']", "['a']"))
        self.assertIn("not a path string", res["warning"])

    def test_the_forward_hands_a_falsy_non_string_on_as_is(self):
        seen = []
        remote = {"host": "TESTHOST", "local_port": 1, "token": "t"}

        def fwd(r, path, body):
            seen.append(body)
            return {"ok": True, "todoId": "ut-9f2c1a34", "file": "0", "warning": "the file value 0 is not a path string"}
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), mock.patch.object(km, "_remote_forward", fwd):
            code, res = self.post({"id": RSID, "text": TEXT, "file": 0})
        self.assertEqual(code, 200)
        self.assertIn("file", seen[0], "before: dropped by `if fraw:` and nothing said")
        self.assertEqual(seen[0]["file"], 0)
        self.assertNotIsInstance(seen[0]["file"], bool)
        self.assertIn("not a path string", res["warning"])
        self.assertEqual(res["file"], "0")

    def test_a_blank_or_null_file_is_no_file_at_all(self):
        seen = []
        remote = {"host": "TESTHOST", "local_port": 1, "token": "t"}

        def fwd(r, path, body):
            seen.append(body)
            return {"ok": True, "todoId": "ut-9f2c1a35"}
        for value in ("", "   ", None):
            with self.subTest(value=value):
                km._user_todos_cache.clear()
                (jd.STATE / "user-todos.json").unlink(missing_ok=True)
                code, res = self.post({"id": RSID, "text": TEXT, "file": value})
                self.assertEqual(code, 200)
                self.assertEqual(set(res), {"ok", "todoId"})
                self.assertNotIn("file", self.rows(RSID)[0])
                with mock.patch.object(km, "_host_for_sid", lambda s: remote), mock.patch.object(km, "_remote_forward", fwd):
                    code, res = self.post({"id": RSID, "text": TEXT, "file": value})
                self.assertNotIn("file", seen[-1], "nothing to forward")
                self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a35"}, "and no skew is read into a file-less forward")


class TheForwardNamesAnOlderRemote(_World):
    REMOTE = {"host": "TESTHOST", "local_port": 1, "token": "t"}

    def forward(self, reply, body):
        seen = []

        def fwd(r, path, body_):
            seen.append(body_)
            return reply
        err = io.StringIO()
        with mock.patch.object(km, "_host_for_sid", lambda s: self.REMOTE), \
                mock.patch.object(km, "_remote_forward", fwd), contextlib.redirect_stderr(err):
            code, res = self.post(body)
        self.assertEqual(code, 200)
        self.assertEqual(km._user_todos(), {}, "nothing stored here: the remote owns that session's ledger")
        return seen[0], res, err.getvalue()

    def test_a_remote_that_predates_the_field_is_named_in_the_warning(self):
        # the pre-follow-on route reads id/text/detail alone and answers {ok, todoId}
        sent, res, err = self.forward({"ok": True, "todoId": "ut-9f2c1a34"}, {"id": RSID, "text": TEXT, "file": "docs/report.md"})
        self.assertEqual(sent["file"], "docs/report.md")
        self.assertEqual((res["ok"], res["todoId"]), (True, "ut-9f2c1a34"), "the todo stands there")
        self.assertNotIn("file", res, "nothing invented: no kernel stored a file")
        for words in ("docs/report.md", "was not recorded", "kernel on TESTHOST", "predates", "update romp there"):
            self.assertIn(words, res["warning"])
        self.assertIn("TESTHOST", err, "and the operator's stderr names it")

    def test_a_remote_that_took_the_file_echoes_it_and_no_skew_is_read(self):
        sent, res, err = self.forward({"ok": True, "todoId": "ut-9f2c1a34", "file": "/srv/notes-api/docs/report.md"},
                                      {"id": RSID, "text": TEXT, "file": "docs/report.md"})
        self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a34", "file": "/srv/notes-api/docs/report.md"})
        self.assertEqual(err, "")

    def test_a_remote_that_warned_is_relayed_as_before(self):
        warn = "the file path docs/report.md did not resolve to an absolute path"
        sent, res, err = self.forward({"ok": True, "todoId": "ut-9f2c1a34", "file": "docs/report.md", "warning": warn},
                                      {"id": RSID, "text": TEXT, "file": "docs/report.md"})
        self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a34", "file": "docs/report.md", "warning": warn})
        self.assertEqual(err, "")

    def test_a_forward_without_a_file_reads_no_skew_into_plain_success(self):
        sent, res, err = self.forward({"ok": True, "todoId": "ut-9f2c1a35"}, {"id": RSID, "text": "Need the staging port"})
        self.assertNotIn("file", sent)
        self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a35"})
        self.assertEqual(err, "")

    def test_a_forward_that_did_not_land_invents_nothing(self):
        sent, res, err = self.forward(None, {"id": RSID, "text": TEXT, "file": "docs/report.md"})
        self.assertEqual(res, {"ok": False, "todoId": ""}, "the tool says the todo was not saved; no file account is made up")
        self.assertEqual(err, "")


class ANulByteInTheFile(_World):
    def test_the_helper_keeps_it_as_given_with_a_warning_naming_the_byte(self):
        # before: stored absolute with no warning — isabs is a string check, and the islink probes swallow the ValueError
        stored, warning = km._user_todo_file(NUL_PATH, RSID)
        self.assertEqual(stored, NUL_PATH, "as given")
        for words in ("did not resolve", "NUL byte", "kept as given", "absolute path"):
            self.assertIn(words, warning)
        self.assertNotIn("\x00", warning, "the byte is spelled out in the reply's text, never embedded")
        self.assertIn("/x\\0y/report.md", warning)

    def test_a_percent_encoded_nul_in_a_uri_and_a_relative_spelling_are_caught_too(self):
        stored, warning = km._user_todo_file("file:///x%00y/report.md", RSID2)
        self.assertEqual(stored, "file:///x%00y/report.md")
        self.assertIn("NUL byte", warning)
        stored, warning = km._user_todo_file("docs/re\x00port.md", RSID)
        self.assertEqual(stored, "docs/re\x00port.md", "never joined onto the cwd into a path that cannot exist")
        self.assertIn("NUL byte", warning)

    def test_the_route_files_it_with_the_warning(self):
        code, res = self.post({"id": RSID, "text": TEXT, "file": NUL_PATH})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"], "filed all the same")
        self.assertIn("NUL byte", res["warning"])
        self.assertEqual((res["file"], self.rows(RSID)[0]["file"]), (NUL_PATH, NUL_PATH))

    def _realpath_raising_on_nul(self):
        """os.path.realpath as Python 3.12 has it — ValueError('embedded null byte') on a NUL — pinned
        rather than assumed, so the arm is exercised under every interpreter the suite runs on."""
        orig = os.path.realpath

        def rp(p, *a, **k):
            if isinstance(p, str) and "\x00" in p:
                raise ValueError("embedded null byte")
            return orig(p, *a, **k)
        return mock.patch.object(km.os.path, "realpath", rp)

    def test_one_such_todo_fails_no_comments_reply_of_its_session(self):
        # the loop realpaths every open todo of the session on every reply: the except's ValueError arm
        # is what keeps a status on ANY file of the session answering
        nul = km._add_user_todo(RSID, "Need a look at the file with the odd name", file=NUL_PATH)
        good = km._add_user_todo(RSID, TEXT, file=self.fp)
        self.assertEqual(self.rows(RSID)[0]["file"], NUL_PATH, "the store keeps it — the match is where it must not raise")
        with self._realpath_raising_on_nul():
            self.assertEqual(self.naming(RSID, self.fp), [{"id": good, "text": TEXT}])
            self.assertEqual(km._user_todos_naming_file(RSID, "/x/y/report.md"), [], "nothing matches the NUL spelling")
            host = ({"ok": True, "root": self.root, "tracked": False}, None)
            with mock.patch.object(km, "_file_comments_node", lambda: True), \
                    mock.patch.object(km, "_file_comments_call", lambda *a, **k: host):
                rep = km._file_comments_op({"type": "fileComments", "reqId": 7, "sid": RSID, "path": self.fp, "verb": "status"})
        self.assertEqual(rep["type"], "fileCommentsResult", "a status on the other file still answers")
        self.assertEqual(rep["todos"], [{"id": good, "text": TEXT}])
        self.assertNotEqual(nul, good)

    def test_the_arm_is_what_stands_between_the_nul_and_the_panel(self):
        # the control for the test above: the very realpath the loop runs raises on the stored spelling
        km._add_user_todo(RSID, "Need a look at the file with the odd name", file=NUL_PATH)
        with self._realpath_raising_on_nul():
            with self.assertRaises(ValueError):
                km.os.path.realpath(self.rows(RSID)[0]["file"])
            self.assertEqual(self.naming(RSID, self.fp), [])


class ASingleSlashFileUri(_World):
    def test_rfc_8089s_no_authority_spelling_becomes_its_path(self):
        # before: joined onto the cwd as `<cwd>/file:/…` — absolute, so no warning, and a path that is not there
        self.assertEqual(km._user_todo_file("file:" + self.fp, RSID), (self.fp, None))
        self.assertEqual(km._user_todo_file("file:" + self.fp, RSID2), (self.fp, None), "no cwd needed")
        self.assertEqual(km._user_todo_file("FILE:" + self.fp, RSID), (self.fp, None))
        spaced = os.path.join(self.root, "docs", "my report.md")
        self.assertEqual(km._user_todo_file("file:" + spaced.replace(" ", "%20"), RSID), (spaced, None), "percent-decoded")

    def test_a_file_uri_without_an_absolute_path_is_kept_as_given_with_the_warning(self):
        for uri in ("file:docs/report.md", "file:", "file://docs/report.md", "file://TESTHOST/srv/notes-api/docs/report.md"):
            with self.subTest(uri=uri):
                stored, warning = km._user_todo_file(uri, RSID)
                self.assertEqual(stored, uri, "as given — never joined onto the cwd")
                for words in ("did not resolve", "absolute path", "file:///"):
                    self.assertIn(words, warning)

    def test_the_route_stores_the_path_and_a_status_on_the_file_lists_the_todo(self):
        code, res = self.post({"id": RSID, "text": TEXT, "file": "file:" + self.fp})
        self.assertEqual((code, res["file"]), (200, self.fp))
        self.assertNotIn("warning", res)
        self.assertEqual(self.rows(RSID)[0]["file"], self.fp)
        self.assertTrue(os.path.exists(self.rows(RSID)[0]["file"]))
        self.assertEqual(self.naming(RSID, self.fp), [{"id": res["todoId"], "text": TEXT}])

    def test_the_double_slash_form_and_the_drive_spelling_are_as_before(self):
        self.assertEqual(km._user_todo_file("file://" + self.fp, RSID), (self.fp, None))
        # `C:/x` has no `file:` and no `://`, so it is a relative path here: joined onto the cwd, as before
        self.assertEqual(km._user_todo_file("C:/x.md", RSID), (os.path.join(self.root, "C:", "x.md"), None))
        self.assertEqual(km._user_todo_file("filed/report.md", RSID), (os.path.join(self.root, "filed", "report.md"), None),
                         "a directory whose name starts with `file` is not a URI")


if __name__ == "__main__":
    unittest.main()
