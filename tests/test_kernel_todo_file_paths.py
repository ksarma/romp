#!/usr/bin/env python3
"""The paths a user todo's `file` can arrive as, and the file the store then names (the todo-file
follow-on's review, 2026-09-07). Three findings, one rule: the stored `file` is a spelling the OS
opens as the file the agent meant, or it is kept as given WITH a warning — never a silently wrong
absolute path.

- A file:// URI in the `file` argument (a spelling the tool's `text` lists as linkable) used to be
  joined onto the session's cwd as if `file:` were a directory — `<cwd>/file:/…`, absolute, so no
  warning — and the chip opened a path that did not exist while no status ever listed the todo. The
  kernel now converts it the way the client converts a clicked link (fileUriToPath): scheme off,
  percent-decoded, absolute path required; a URI without one, a URL of another scheme, and a body
  value that is not a string are kept as given with a warning naming the reason (FileUriInTheFileArgument).
- A `file` kept as given (a relative path, filed before the session had a recorded cwd) was matched
  by a bare os.path.realpath, which resolves a relative string against the KERNEL PROCESS's cwd: a
  todo listed on an unrelated file under the kernel's own directory. A stored path that is not
  absolute now matches nothing — the filing reply said the comments cannot answer it until the agent
  passes the absolute path, and a Send is a stamp (AKeptAsGivenPathAndTheKernelsCwd).
- os.path.normpath at filing collapsed `link/..` lexically, storing a path to a different file than
  the spelling opens when `link` is a directory symlink; _normpath_keeping_links keeps such a `..` so
  the stored spelling and the OS agree (DotDotAcrossADirectorySymlink).
- The lifecycle log's `lost` line carries the todo's `file` like every other line of a todo that names
  one (TheLostLineCarriesTheFile) — the documented shape, pinned through _reopen_user_todo.
- The fixtures restore through addCleanup, never tearDown: unittest skips tearDown when setUp raises, and
  AKeptAsGivenPathAndTheKernelsCwd asserts in setUp AFTER chdir'ing the process and after _World rebound
  jd.STATE (one object for every module in the worker) and three kernel functions — so the very
  regression it guards against would have left every later test in the xdist worker running inside a
  stale temp tree with the sandbox as its state (ASetUpThatFailsLeaksNothing pins the restores).

SYNTHETIC fixtures only: private placeholder sids, the notes-api demo world under a temp dir.
"""
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
km = load_source("romp_kernel_todo_file_paths", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# PRIVATE synthetic sids (the goal-store fixture rule, generalized: rows minted under the shared
# placeholder can be reached by another module's fixtures). PSID has a recorded cwd, PSID2 none.
PSID = "7e7e7e7e-1111-4222-8333-944444444444"
PSID2 = "7f7f7f7f-1111-4222-8333-944444444444"


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
    PSID's cwd recorded as its root, PSID2 with no recorded cwd, and the routes' pusher stubbed."""

    def setUp(self):
        # Every restore is an addCleanup registered BEFORE the change it undoes (cleanups run when
        # setUp raises; tearDown does not), in the order tearDown kept: kernel functions, STATE and
        # the caches, then the temp tree — and a subclass's chdir back runs before all of these.
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.tmp = os.path.realpath(self.td.name)
        self.saved = jd.STATE
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
        self.cwds = {PSID: self.root}
        self._saved = (km._cwd_of, km._push_all, km._push_soon)
        self.addCleanup(self._restore_kernel)
        km._cwd_of = lambda sid: self.cwds.get(sid, "")
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: None

    def _restore_kernel(self):
        km._cwd_of, km._push_all, km._push_soon = self._saved

    def _restore_state(self):
        jd.STATE = self.saved
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()

    def post(self, body):
        code, out = _serve_post("/usertodo", body, {"X-Romp-Token": km.TOKEN})
        return code, json.loads(out.decode() or "{}")

    def naming(self, sid, path):
        return km._user_todos_naming_file(sid, os.path.realpath(path))


class FileUriInTheFileArgument(_World):
    def test_a_file_uri_becomes_its_path_and_is_stored_absolute(self):
        uri = "file://" + self.fp
        self.assertEqual(km._user_todo_file(uri, PSID), (self.fp, None), "the URI's path, no warning")
        tid = km._add_user_todo(PSID, "Need a look at the findings report", file=uri)
        self.assertEqual(km._user_todos()[PSID][0]["file"], self.fp, "never <cwd>/file:/…")
        self.assertTrue(os.path.exists(km._user_todos()[PSID][0]["file"]))
        self.assertEqual(self.naming(PSID, self.fp), [{"id": tid, "text": "Need a look at the findings report"}],
                         "a status on the file lists the todo filed through the URI")

    def test_the_conversion_does_not_need_a_recorded_cwd(self):
        # before: kept as given with a warning that called the URI "relative"
        self.assertEqual(km._user_todo_file("file://" + self.fp, PSID2), (self.fp, None))

    def test_a_percent_encoded_uri_is_decoded(self):
        spaced = os.path.join(self.root, "docs", "my report.md")
        self.assertEqual(km._user_todo_file("file://" + spaced.replace(" ", "%20"), PSID), (spaced, None))

    def test_the_scheme_is_case_insensitive(self):
        self.assertEqual(km._user_todo_file("FILE://" + self.fp, PSID), (self.fp, None))

    def test_a_uri_without_an_absolute_path_is_kept_as_given_with_a_warning(self):
        for uri in ("file://docs/report.md", "file://TESTHOST/srv/notes-api/docs/report.md"):
            stored, warning = km._user_todo_file(uri, PSID)
            self.assertEqual(stored, uri, "as given — never joined onto the cwd")
            for words in (uri, "did not resolve", "absolute path", "file:///"):
                self.assertIn(words, warning)

    def test_another_url_scheme_is_kept_as_given_with_a_warning(self):
        url = "https://example.invalid/notes-api/docs/report.md"
        stored, warning = km._user_todo_file(url, PSID)
        self.assertEqual(stored, url)
        for words in (url, "did not resolve", "absolute path", "URL"):
            self.assertIn(words, warning)
        km._add_user_todo(PSID, "Need a look at the findings report", file=url)
        self.assertEqual(km._user_todos()[PSID][0]["file"], url, "the store keeps it as given too")
        self.assertEqual(self.naming(PSID, self.fp), [])

    def test_a_windows_drive_spelling_is_not_a_url(self):
        # `C:/x` has no `://`, so it is a relative path here: joined onto the cwd, as before
        self.assertEqual(km._user_todo_file("C:/x.md", PSID), (os.path.join(self.root, "C:", "x.md"), None))

    def test_the_route_stores_the_uris_path_and_answers_no_warning(self):
        code, res = self.post({"id": PSID, "text": "Need a look at the findings report", "file": "file://" + self.fp})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertNotIn("warning", res)
        self.assertEqual(km._user_todos()[PSID][0]["file"], self.fp)

    def test_the_route_warns_for_a_url_and_keeps_it_as_given(self):
        url = "https://example.invalid/report.md"
        code, res = self.post({"id": PSID, "text": "Need a look at the findings report", "file": url})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"], "filed all the same")
        self.assertIn("did not resolve", res["warning"])
        self.assertIn(url, res["warning"])
        self.assertEqual(km._user_todos()[PSID][0]["file"], url)

    def test_a_non_string_file_is_kept_as_its_text_with_a_warning(self):
        stored, warning = km._user_todo_file(["a"], PSID)
        self.assertEqual(stored, "['a']", "as given: never <cwd>/['a']")
        self.assertIn("not a path string", warning)
        code, res = self.post({"id": PSID, "text": "Need a look at the findings report", "file": ["a"]})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertIn("not a path string", res["warning"])
        self.assertEqual(km._user_todos()[PSID][0]["file"], "['a']")

    def test_the_remote_forward_hands_a_non_string_file_on_as_is(self):
        seen = []
        remote = {"host": "TESTHOST", "local_port": 1, "token": "t"}

        def fwd(r, path, body):
            seen.append(body)
            return {"ok": True, "todoId": "ut-9f2c1a34", "warning": "the file value ['a'] is not a path string"}
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), mock.patch.object(km, "_remote_forward", fwd):
            code, res = self.post({"id": PSID, "text": "Need a look at the findings report", "file": ["a"]})
        self.assertEqual(code, 200)
        self.assertEqual(seen[0]["file"], ["a"], "the remote kernel names the shape itself")
        self.assertIn("not a path string", res["warning"])

    def test_the_plain_forms_still_resolve_as_before(self):
        self.assertEqual(km._user_todo_file("docs/report.md", PSID), (self.fp, None))
        self.assertEqual(km._user_todo_file(self.fp, PSID2), (self.fp, None))
        stored, warning = km._user_todo_file("docs/report.md", PSID2)
        self.assertEqual(stored, "docs/report.md")
        self.assertIn("no working directory is recorded", warning)


class AKeptAsGivenPathAndTheKernelsCwd(_World):
    """Two roots holding docs/report.md: `kernelcwd`, which the PROCESS is chdir'd into for the test, and
    the session's own root. PSID2 files with no recorded cwd, so the store keeps `docs/report.md`."""

    def setUp(self):
        super().setUp()
        self.kernelcwd = os.path.join(self.tmp, "kernelcwd")
        os.makedirs(os.path.join(self.kernelcwd, "docs"))
        self.kfile = os.path.join(self.kernelcwd, "docs", "report.md")
        with open(self.kfile, "w") as f:
            f.write("# An unrelated report\n")
        self._cwd = os.getcwd()
        self.addCleanup(os.chdir, self._cwd)         # before the chdir: the asserts below may fail
        os.chdir(self.kernelcwd)
        self.tid = km._add_user_todo(PSID2, "Need a look at the findings report", file="docs/report.md")
        self.assertEqual(km._user_todos()[PSID2][0]["file"], "docs/report.md", "kept as given")

    def test_a_relative_stored_file_never_matches_a_file_under_the_kernels_cwd(self):
        self.assertEqual(self.naming(PSID2, self.kfile), [], "the kernel's own directory is no frame")

    def test_it_matches_nothing_while_the_session_has_no_cwd(self):
        self.assertEqual(self.naming(PSID2, self.fp), [])

    def test_it_matches_nothing_once_the_sessions_cwd_is_known_either(self):
        # the filing reply told the agent the comments cannot answer this one until it passes the
        # absolute path; a Send is a stamp, so the match is made on the path resolved at filing or not
        # at all (the e2e pins the same: a path kept as given names no file on disk)
        self.cwds[PSID2] = self.root                 # the session's cwd is registered later (a promotion)
        real = km._file_comments_path("docs/report.md", PSID2)
        self.assertEqual(real, os.path.realpath(self.fp), "the request side resolves against the session's cwd")
        self.assertEqual(km._user_todos_naming_file(PSID2, real), [])
        self.assertEqual(self.naming(PSID2, self.kfile), [])

    def test_the_same_spelling_filed_with_the_cwd_known_matches(self):
        # the control: what the agent gets by filing once the cwd is recorded (or by passing the absolute path)
        self.cwds[PSID2] = self.root
        t2 = km._add_user_todo(PSID2, "Need a look at the findings report, again", file="docs/report.md")
        self.assertEqual(km._user_todos()[PSID2][1]["file"], self.fp)
        self.assertEqual([t["id"] for t in self.naming(PSID2, self.fp)], [t2])

    def test_an_absolute_stored_file_is_matched_as_before(self):
        t2 = km._add_user_todo(PSID2, "Need a look at the other note", file=self.kfile)
        self.assertEqual([t["id"] for t in self.naming(PSID2, self.kfile)], [t2])


class ASetUpThatFailsLeaksNothing(unittest.TestCase):
    """AKeptAsGivenPathAndTheKernelsCwd asserts in setUp after chdir'ing the PROCESS and after _World
    rebound jd.STATE and the kernel copy's _cwd_of/_push_all/_push_soon. unittest skips tearDown when
    setUp raises, so with the restores in tearDown the regression the class guards against (a relative
    `file` with no recorded cwd resolved against the process cwd) left the xdist worker chdir'd into a
    TemporaryDirectory that was never cleaned, with the sandbox as the process-shared STATE and the
    patches in place, for every later test in the process — five clean failures turned into cascading
    noise (the review, 2026-09-07). Every restore is an addCleanup now. This runs the class against two
    setUp failures — the injected regression (an assertion) and an error out of the filing call — and
    reads what the process is left with. Nested runs: the case's own result object, so the failure
    under test never reaches this run's report."""

    def _snapshot(self):
        return os.getcwd(), jd.STATE, (km._cwd_of, km._push_all, km._push_soon)

    def _run_one(self, name="test_it_matches_nothing_while_the_session_has_no_cwd"):
        case = AKeptAsGivenPathAndTheKernelsCwd(name)
        result = unittest.TestResult()
        case.run(result)
        return case, result

    def _assert_nothing_leaked(self, case, before):
        cwd, state, fns = before
        self.assertEqual(os.getcwd(), cwd, "the process cwd is the worker's again")
        self.assertIs(jd.STATE, state, "the shared STATE is out of the sandbox")
        self.assertEqual((km._cwd_of, km._push_all, km._push_soon), fns, "the kernel copy is unpatched")
        self.assertFalse(os.path.exists(case.tmp), "the sandbox (the process's cwd for the test) is gone")

    def test_the_filing_regression_the_class_guards_against_leaks_nothing(self):
        orig = km._user_todo_file

        def regressed(value, sid):        # a relative path with no recorded cwd: abspath'd, no warning
            stored, warning = orig(value, sid)
            if isinstance(stored, str) and warning and "no working directory" in warning:
                return os.path.abspath(stored), None
            return stored, warning

        before = self._snapshot()
        with mock.patch.object(km, "_user_todo_file", regressed):
            case, result = self._run_one()
        self.assertEqual(len(result.failures), 1, "setUp's own assertion is the failure reported")
        self.assertIn("kept as given", result.failures[0][1])
        self.assertEqual(result.errors, [], "and no cleanup added an error of its own")
        self._assert_nothing_leaked(case, before)

    def test_an_error_out_of_the_filing_call_leaks_nothing(self):
        before = self._snapshot()
        with mock.patch.object(km, "_add_user_todo", side_effect=OSError("no space left on device")):
            case, result = self._run_one()
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.failures, [])
        self._assert_nothing_leaked(case, before)

    def test_the_control_run_passes_and_restores_the_same(self):
        before = self._snapshot()
        case, result = self._run_one()
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        self._assert_nothing_leaked(case, before)


class DotDotAcrossADirectorySymlink(_World):
    """repo/docs-link -> vault/docs; repo/notes/x.md and vault/notes/x.md both exist and differ. The
    spelling `docs-link/../notes/x.md` under repo opens vault/notes/x.md on disk."""

    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.tmp, "repo")
        self.vault = os.path.join(self.tmp, "vault")
        for d in ("repo/notes", "vault/docs", "vault/notes"):
            os.makedirs(os.path.join(self.tmp, d))
        self.repo_x = os.path.join(self.repo, "notes", "x.md")
        self.vault_x = os.path.join(self.vault, "notes", "x.md")
        with open(self.repo_x, "w") as f:
            f.write("REPO\n")
        with open(self.vault_x, "w") as f:
            f.write("VAULT\n")
        os.symlink(os.path.join(self.vault, "docs"), os.path.join(self.repo, "docs-link"))
        self.cwds[PSID] = self.repo
        self.spelling = "docs-link/../notes/x.md"

    def test_a_dotdot_through_a_directory_link_stays_in_the_stored_spelling(self):
        stored, warning = km._user_todo_file(self.spelling, PSID)
        self.assertIsNone(warning)
        self.assertEqual(stored, os.path.join(self.repo, self.spelling), "absolute, the spelling kept")
        self.assertEqual(os.path.realpath(stored), self.vault_x, "and it names the file the spelling opens")
        with open(stored) as f:
            self.assertEqual(f.read(), "VAULT\n")

    def test_a_status_on_the_spelling_lists_the_todo_and_the_other_file_does_not(self):
        tid = km._add_user_todo(PSID, "Need a look at the note", file=self.spelling)
        real = km._file_comments_path(self.spelling, PSID)
        self.assertEqual(real, self.vault_x)
        self.assertEqual([t["id"] for t in km._user_todos_naming_file(PSID, real)], [tid])
        self.assertEqual(self.naming(PSID, self.repo_x), [], "normpath's answer was this file — the wrong one")

    def test_an_absolute_spelling_with_the_same_dotdot_is_kept_too(self):
        stored, _ = km._user_todo_file(os.path.join(self.repo, self.spelling), PSID2)
        self.assertEqual(os.path.realpath(stored), self.vault_x)

    def test_a_dotdot_over_a_real_directory_still_collapses(self):
        self.assertEqual(km._user_todo_file("notes/../notes/x.md", PSID), (self.repo_x, None))
        self.assertEqual(km._user_todo_file("./notes//x.md", PSID), (self.repo_x, None))

    def test_a_linked_cwd_spelling_keeps_the_dotdot(self):
        # the commoner shape: the recorded cwd is itself a symlink spelling and the agent files ../x
        os.makedirs(os.path.join(self.tmp, "data", "proj"))
        os.makedirs(os.path.join(self.tmp, "data", "other"))
        os.makedirs(os.path.join(self.tmp, "home"))
        os.symlink(os.path.join(self.tmp, "data", "proj"), os.path.join(self.tmp, "home", "proj"))
        target = os.path.join(self.tmp, "data", "other", "x.md")
        open(target, "w").close()
        self.cwds[PSID] = os.path.join(self.tmp, "home", "proj")
        stored, warning = km._user_todo_file("../other/x.md", PSID)
        self.assertIsNone(warning)
        self.assertEqual(stored, os.path.join(self.tmp, "home", "proj", "..", "other", "x.md"))
        self.assertEqual(os.path.realpath(stored), target)

    def test_the_helper_agrees_with_normpath_where_no_link_is_crossed(self):
        for p in ("/a/b/../c", "/a/./b//c/", "/../a", "/a/../../b", "/", "/a/b/c/../../d/./e"):
            self.assertEqual(km._normpath_keeping_links(p), os.path.normpath(p), p)

    def test_a_dotdot_above_a_kept_one_is_kept_as_well(self):
        p = os.path.join(self.repo, "docs-link", "..", "..", "notes", "x.md")   # two steps from vault/docs
        self.assertEqual(km._normpath_keeping_links(p), p)
        self.assertEqual(os.path.realpath(p), os.path.join(self.tmp, "notes", "x.md"))


class TheLostLineCarriesTheFile(_World):
    def _lines(self):
        return [json.loads(ln) for ln in (jd.STATE / km.USER_TODOS_LOG_FILE).read_text().splitlines()]

    def test_the_reopen_seam_logs_the_file_on_the_lost_line(self):
        tid = km._add_user_todo(PSID, "Need a look at the findings report", file=self.fp)
        km._resolve_user_todo(PSID, tid, "answered", reply="Re: … — looks good")
        self.assertTrue(km._reopen_user_todo(PSID, tid))
        last = self._lines()[-1]
        self.assertEqual((last["kind"], last["id"], last["file"]), ("lost", tid, self.fp),
                         "every line of a todo that names a file carries it — the lost line included")
        self.assertEqual([r["kind"] for r in self._lines()], ["filed", "answered", "lost"])

    def test_a_file_less_todos_lost_line_has_no_file_key(self):
        tid = km._add_user_todo(PSID, "Need the staging port")
        km._resolve_user_todo(PSID, tid, "answered", reply="Re: … — 8081")
        self.assertTrue(km._reopen_user_todo(PSID, tid))
        last = self._lines()[-1]
        self.assertEqual(last["kind"], "lost")
        self.assertNotIn("file", last, "the documented shape for a file-less todo, nothing else")


if __name__ == "__main__":
    unittest.main()
