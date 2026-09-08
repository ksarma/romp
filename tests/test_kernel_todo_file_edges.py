#!/usr/bin/env python3
"""The edges of a user todo's `file` the round-3 review of the todo-file follow-on found (2026-09-07):
four findings, the same rule as tests/test_kernel_todo_file_paths.py — the stored `file` is a spelling
the OS opens as the file the agent meant, or it is kept as given WITH a warning, never a refusal and
never a silently wrong absolute path.

- A `~name` spelling holding a NUL byte before its first slash RAISED out of _user_todo_file:
  os.path.expanduser hands the user name to pwd.getpwnam, which refuses an embedded NUL with
  ValueError, and the helper's NUL check ran only on the CONVERTED spelling — after the call. POST
  /usertodo answered 500 with a traceback and filed nothing, while the tool told the agent the person
  would NOT see it. The NUL is now checked on the value as given, before any resolution
  (ANulByteInATildeSpelling).
- The warnings' shared tail called the todo "the request" — the word CONTEXT.md's User todo entry lists
  under _Avoid_, purged from the tool's own strings in round 2 — and the postal tool relays the
  kernel's warning verbatim into the agent's reply. Every warning branch is rendered here and held to
  the avoid list (TheWarningsUseNoAvoidWord); the postal test scans the tool's own words around a
  canned warning, so between the two the whole reply is covered.
- `..` after a symlink to a FILE (or a dangling one) was kept in the stored spelling, which the OS
  answers ENOTDIR (ENOENT) for: the chip opened nothing while realpath walked the `..` lexically, so a
  Send from the neighbouring file offered the todo. Only a `..` after a DIRECTORY link is kept now; a
  file link collapses as normpath collapses it (ADotDotAfterAFileSymlink).
- _normpath_keeping_links re-joined the whole prefix on every `..` to probe it for a link, so an
  oversized `file` cost the handler thread quadratic CPU under the GIL (a 180 KB value: 8 s) before
  the todo was written, and the postal bus's 2 s timeout told the agent to retry — a duplicate per
  retry. The probe is skipped once the prefix is PATH_MAX or longer (lstat refuses it anyway, so
  nothing changes but the cost), and a spelling that stays that long after normalizing is kept as
  given with a warning, since no path that long opens on this machine; the comments matcher skips
  such a spelling instead of walking it (AnOverlongFile).

SYNTHETIC fixtures only: private placeholder sids, the notes-api demo world under a temp dir.
"""
import io
import json
import os
import re
import tempfile
import time
import unittest
from unittest import mock
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_todo_file_edges", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# PRIVATE synthetic sids (the goal-store fixture rule, generalized: rows minted under the shared
# placeholder can be reached by another module's fixtures). ESID has a recorded cwd, ESID2 none.
ESID = "8a8a8a8a-1111-4222-8333-944444444444"
ESID2 = "8b8b8b8b-1111-4222-8333-944444444444"
TEXT = "Need a look at the findings report"
TILDE_NULS = ("~\x00/x.md", "~a\x00b/x.md", "~\x00x.md")


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


def _avoid_words(context_md, term):
    """The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    avoid = re.search(r"^_Avoid_:(.*)$", m.group(1), re.M)
    assert avoid, "CONTEXT.md entry %r has no _Avoid_ line" % term
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [w.strip() for w in bare.split(",") if w.strip()]


def _exact_length_path(n):
    """An absolute path of exactly `n` characters, every component within NAME_MAX — the OS's length
    limit is PATH_MAX alone, so what the helper does at the boundary is what this pins."""
    parts, need = [], n - 1                          # the leading slash
    while need > 0:
        k = min(200, need)
        if need - k == 1:                            # never leave a lone separator for the last step
            k -= 1
        parts.append("a" * k)
        need -= k + 1
    p = os.sep + os.sep.join(parts)
    assert len(p) == n, (len(p), n)
    return p


class _World(unittest.TestCase):
    """A STATE sandbox with user todos ON, a notes-api tree (docs/report.md) under a realpath'd temp dir,
    ESID's cwd recorded as its root, ESID2 with no recorded cwd, and the routes' pusher stubbed. Every
    restore is an addCleanup (they run when setUp raises; tearDown does not)."""

    def setUp(self):
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
        self.cwds = {ESID: self.root}
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

    def rows(self, sid):
        return km._user_todos().get(sid) or []

    def naming(self, sid, path):
        return km._user_todos_naming_file(sid, os.path.realpath(path))


class ANulByteInATildeSpelling(_World):
    def test_the_helper_keeps_it_as_given_with_the_nul_warning_instead_of_raising(self):
        # before: ValueError('embedded null byte') out of os.path.expanduser, uncaught
        for raw in TILDE_NULS:
            for sid in (ESID, ESID2):
                with self.subTest(raw=raw, sid=sid[:8]):
                    stored, warning = km._user_todo_file(raw, sid)
                    self.assertEqual(stored, raw, "as given")
                    for words in ("did not resolve", "NUL byte", "kept as given", "absolute path"):
                        self.assertIn(words, warning)
                    self.assertNotIn("\x00", warning, "the byte is spelled out, never embedded")
                    self.assertIn(raw.replace("\x00", "\\0"), warning)

    def test_the_route_files_it_with_the_warning_and_never_answers_500(self):
        code, res = self.post({"id": ESID, "text": TEXT, "file": "~\x00/x.md"})
        self.assertEqual(code, 200, "before: do_POST's catch-all answered 500 with a traceback")
        self.assertTrue(res["ok"], "filed all the same")
        self.assertRegex(res["todoId"], r"^ut-[0-9a-f]{8}$")
        self.assertIn("NUL byte", res["warning"])
        self.assertEqual((res["file"], self.rows(ESID)[0]["file"]), ("~\x00/x.md", "~\x00/x.md"))

    def test_the_check_runs_before_any_resolution_under_every_interpreter(self):
        # pinned rather than assumed: a resolver that raises on a NUL (as 3.12's expanduser does for a
        # `~name` spelling) is never reached with one, whatever the interpreter running the suite does
        def resolve(p, sid=None):
            if "\x00" in p:
                raise ValueError("embedded null byte")
            return self._saved_resolve(p, sid)
        self._saved_resolve = km._resolve_open_path
        with mock.patch.object(km, "_resolve_open_path", resolve):
            for raw in TILDE_NULS + ("/x\x00y/report.md", "docs/re\x00port.md"):
                with self.subTest(raw=raw):
                    stored, warning = km._user_todo_file(raw, ESID)
                    self.assertEqual(stored, raw)
                    self.assertIn("NUL byte", warning)
            self.assertEqual(km._user_todo_file("docs/report.md", ESID), (self.fp, None), "a clean path still resolves")

    def test_the_spellings_the_earlier_pins_cover_answer_as_before(self):
        for raw in ("/x\x00y/report.md", "~/x\x00y.md", "docs/re\x00port.md", "file:///x%00y/report.md"):
            with self.subTest(raw=raw):
                stored, warning = km._user_todo_file(raw, ESID)
                self.assertEqual(stored, raw)
                self.assertIn("NUL byte", warning)


class TheWarningsUseNoAvoidWord(_World):
    """Every warning _user_todo_file can answer, rendered from the real code paths and held to CONTEXT.md's
    User todo _Avoid_ list: the postal tool relays these words verbatim into the agent's reply, after its
    own "Noted (id ut-…)", where "the request" read as the call itself. "ask" is skipped as the docs'
    tests skip it: a verb the prose may need."""

    def setUp(self):
        super().setUp()
        with open(os.path.join(ROOT, "CONTEXT.md"), encoding="utf-8") as f:
            self.avoid = _avoid_words(f.read(), "User todo")
        self.assertIn("request", self.avoid)

    def _warnings(self):
        cases = {
            "a relative path with no recorded cwd": ("docs/report.md", ESID2),
            "a URL": ("https://example.invalid/report.md", ESID),
            "a file URI with a host": ("file://TESTHOST/srv/notes-api/docs/report.md", ESID),
            "a file URI without an absolute path": ("file:docs/report.md", ESID),
            "a NUL byte": ("/x\x00y/report.md", ESID),
            "a NUL byte in a ~name spelling": ("~\x00/x.md", ESID),
            "a non-string value": (["docs/report.md"], ESID),
            "a falsy non-string value": (0, ESID),
            "an overlong path": (_exact_length_path(km._PATH_MAX + 40), ESID),
        }
        out = {}
        for where, (value, sid) in cases.items():
            stored, warning = km._user_todo_file(value, sid)
            self.assertIsInstance(warning, str, where)
            self.assertEqual(stored, value if isinstance(value, str) else str(value), where)
            out[where] = warning
        return out

    def test_no_warning_carries_an_avoided_word(self):
        # before: every branch ended "so it opens from the request and its comments can answer it"
        for where, warning in self._warnings().items():
            for word in self.avoid:
                if word == "ask":
                    continue
                with self.subTest(where=where, word=word):
                    self.assertNotRegex(warning, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                        "the warning for %s says %r; CONTEXT.md avoids it" % (where, word))

    def test_every_warning_still_says_what_the_agent_must_do(self):
        for where, warning in self._warnings().items():
            with self.subTest(where=where):
                self.assertIn("kept as given", warning)
                self.assertIn("absolute path", warning, "what to pass instead")
                self.assertIn("todo", warning, "the object's name, the one the tool's own name carries")
                self.assertRegex(warning, r"comments .* answer", "and what naming the file buys")

    def test_the_kernels_own_account_of_the_matcher_quotes_the_tail(self):
        # _user_todos_naming_file's docstring quotes the filing reply; the quote must be of the text that ships
        doc = km._user_todos_naming_file.__doc__
        self.assertNotIn("its comments can answer it", doc, "the old tail")
        self.assertIn("their comments on it can answer the todo", doc)


class ADotDotAfterAFileSymlink(_World):
    """docs/ holds t.txt and x.md; docs/fl is a symlink to the FILE t.txt, docs/dl a dangling one, and
    docs/dir-link a symlink to a real directory elsewhere. The OS answers ENOTDIR for `fl/../x.md`, so the
    spelling opens nothing; normpath's collapse names the file the agent meant."""

    def setUp(self):
        super().setUp()
        self.docs = os.path.join(self.root, "docs")
        self.t = os.path.join(self.docs, "t.txt")
        self.x = os.path.join(self.docs, "x.md")
        for p, body in ((self.t, "T\n"), (self.x, "X\n")):
            with open(p, "w") as f:
                f.write(body)
        os.symlink(self.t, os.path.join(self.docs, "fl"))
        os.symlink(os.path.join(self.docs, "missing"), os.path.join(self.docs, "dl"))
        self.other = os.path.join(self.tmp, "other")
        os.makedirs(self.other)
        with open(os.path.join(self.tmp, "x.md"), "w") as f:
            f.write("TOP\n")
        os.symlink(self.other, os.path.join(self.docs, "dir-link"))

    def test_a_dotdot_after_a_file_link_collapses_to_the_file_the_spelling_names(self):
        # before: stored '<root>/docs/fl/../x.md' with no warning — a spelling the OS refuses (ENOTDIR)
        for spelling in ("docs/fl/../x.md", os.path.join(self.root, "docs", "fl", "..", "x.md")):
            with self.subTest(spelling=spelling):
                stored, warning = km._user_todo_file(spelling, ESID)
                self.assertIsNone(warning)
                self.assertEqual(stored, self.x, "normpath's answer: the spelling the OS opens")
                self.assertTrue(os.path.isfile(stored))
                with open(stored) as f:
                    self.assertEqual(f.read(), "X\n")

    def test_the_stored_path_opens_and_the_matcher_agrees_with_the_chip(self):
        tid = km._add_user_todo(ESID, "Need a look at the note", file="docs/fl/../x.md")
        self.assertEqual(self.rows(ESID)[0]["file"], self.x)
        self.assertEqual([t["id"] for t in self.naming(ESID, self.x)], [tid], "a status on x.md lists it")
        self.assertEqual(self.naming(ESID, self.t), [], "and the link's target does not")

    def test_a_dangling_link_collapses_too(self):
        stored, warning = km._user_todo_file("docs/dl/../x.md", ESID)
        self.assertEqual((stored, warning), (self.x, None))

    def test_a_dotdot_after_a_directory_link_is_still_kept(self):
        # the control: the case the helper exists for — the OS walks `dir-link/..` through the link's target
        spelling = os.path.join(self.root, "docs", "dir-link", "..", "x.md")
        stored, warning = km._user_todo_file(spelling, ESID)
        self.assertEqual((stored, warning), (spelling, None), "kept: it names <tmp>/x.md on disk, not docs/x.md")
        self.assertEqual(os.path.realpath(stored), os.path.join(self.tmp, "x.md"))
        with open(stored) as f:
            self.assertEqual(f.read(), "TOP\n")

    def test_the_helper_alone_tells_a_file_link_from_a_directory_link(self):
        self.assertEqual(km._normpath_keeping_links(os.path.join(self.docs, "fl", "..", "x.md")), self.x)
        self.assertEqual(km._normpath_keeping_links(os.path.join(self.docs, "dl", "..", "x.md")), self.x)
        kept = os.path.join(self.docs, "dir-link", "..", "x.md")
        self.assertEqual(km._normpath_keeping_links(kept), kept)
        two = os.path.join(self.docs, "dir-link", "..", "..", "x.md")
        self.assertEqual(km._normpath_keeping_links(two), two, "a `..` above a kept one is kept as well")


class AnOverlongFile(_World):
    """PATH_MAX (4096 on Linux, the terminator counted) bounds every path string the OS takes: a spelling
    that long or longer is ENAMETOOLONG to lstat and open alike, so no probe of it can answer and no file
    bears it."""

    def _pathological(self, n):
        """The review's probe: `n` one-letter directories, then n/2 `d/..` pairs — every `..` sits under a
        prefix far past PATH_MAX, and each one used to re-join that prefix for an islink that could only
        answer False."""
        return os.sep + "a/" * n + "d/../" * (n // 2) + "x"

    def test_path_max_is_the_platforms(self):
        self.assertEqual(km._PATH_MAX, os.pathconf(os.sep, "PC_PATH_MAX"))
        self.assertGreaterEqual(km._PATH_MAX, 1024)

    def test_the_helper_probes_no_prefix_the_os_would_refuse(self):
        p = self._pathological(2100)                 # ~9.5 KB; 1050 `..`s, each under a 4202-char prefix
        probes = []
        orig = os.path.islink

        def islink(path):
            probes.append(len(path))
            return orig(path)
        with mock.patch.object(km.os.path, "islink", islink):
            out = km._normpath_keeping_links(p)
        self.assertEqual(out, os.path.normpath(p), "no link is crossed, so normpath's answer")
        self.assertEqual(probes, [], "before: one join of the whole prefix per `..`, 1050 times")
        # and a `..` under a short prefix still asks the disk (the case the helper exists for)
        probes.clear()
        with mock.patch.object(km.os.path, "islink", islink):
            km._normpath_keeping_links(os.path.join(self.root, "docs", "..", "docs", "report.md"))
        self.assertEqual(probes, [len(os.path.join(self.root, "docs"))])

    def test_the_helper_is_linear_in_the_spelling(self):
        # the review's 180 KB value held the handler thread for 8 s; a generous bound still fails that by 4x
        p = self._pathological(45000)
        self.assertGreater(len(p), 180_000)
        t0 = time.monotonic()
        out = km._normpath_keeping_links(p)
        self.assertLess(time.monotonic() - t0, 2.0)
        self.assertEqual(out, os.path.normpath(p))

    def test_a_spelling_that_stays_overlong_is_kept_as_given_with_a_warning(self):
        # before: stored absolute, no warning — a spelling nothing opens and no Send could match
        raw = _exact_length_path(km._PATH_MAX)
        stored, warning = km._user_todo_file(raw, ESID2)
        self.assertEqual(stored, raw, "as given")
        for words in ("did not resolve", "kept as given", "absolute path", str(km._PATH_MAX - 1)):
            self.assertIn(words, warning)
        self.assertLess(len(warning), 600, "the warning names the length; it does not repeat the spelling whole")
        self.assertIn(raw[:60], warning)
        self.assertIn(str(len(raw)), warning)

    def test_the_longest_path_the_os_opens_is_stored_as_before(self):
        p = _exact_length_path(km._PATH_MAX - 1)
        self.assertEqual(km._user_todo_file(p, ESID2), (p, None))
        self.assertEqual(km._user_todo_file(p + "a", ESID2)[0], p + "a")
        self.assertIsNotNone(km._user_todo_file(p + "a", ESID2)[1], "one more character and no path takes it")

    def test_a_spelling_overlong_only_in_its_padding_stores_the_collapsed_path(self):
        padded = os.path.join(self.root, "docs") + "/." * 3000 + "/report.md"
        self.assertGreater(len(padded), km._PATH_MAX)
        self.assertEqual(km._user_todo_file(padded, ESID2), (self.fp, None), "normpath's answer, as for `./notes//x.md`")

    def test_the_route_files_it_with_the_warning_and_the_matcher_never_walks_it(self):
        raw = self._pathological(3000)               # ~13.5 KB as given; 4.5 KB collapsed, still past PATH_MAX
        code, res = self.post({"id": ESID, "text": TEXT, "file": raw})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"], "filed all the same")
        self.assertIn("did not resolve", res["warning"])
        self.assertEqual((res["file"], self.rows(ESID)[0]["file"]), (raw, raw))
        good = km._add_user_todo(ESID, "Need a look at the other note", file=self.fp)
        walked = []
        orig = os.path.realpath

        def realpath(p, *a, **k):
            walked.append(p)
            return orig(p, *a, **k)
        with mock.patch.object(km.os.path, "realpath", realpath):
            self.assertEqual(self.naming(ESID, self.fp), [{"id": good, "text": "Need a look at the other note"}])
            self.assertEqual(km._user_todos_naming_file(ESID, os.path.normpath(raw)), [],
                             "the lexical collapse of a spelling nothing opens matches nothing")
        self.assertNotIn(raw, walked, "realpath's walk — one lstat per component on the growing prefix — is skipped")


if __name__ == "__main__":
    unittest.main()
