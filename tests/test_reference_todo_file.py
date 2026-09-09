#!/usr/bin/env python3
"""docs/reference.md's User todos paragraph says what a todo's `file` does, in CONTEXT.md's vocabulary.

The todo-file follow-on (2026-09-07) let a user todo name its file (`add_user_todo`'s `file` argument). Two
review findings on the reference's account of it, both pinned here:

- The kernel's notion of a path that "does not resolve" is narrow: `_user_todo_file` makes the path absolute
  (`~` expanded, a relative path against the session's recorded cwd), normalizes it and stores that spelling.
  It never checks the disk, so a mistyped ABSOLUTE path is stored as typed with no warning (its chip opens
  nothing and no Send from the file it meant offers the todo); only a relative path from a session with no
  recorded cwd is kept as given with a warning the tool's reply relays. The reference used to say a path
  that "does not resolve on the session's machine" earns the warning, an existence claim the kernel does not
  make. The sentences are held to the code by running the same helper the filing runs. What clears the todo
  (Reply, Dismiss, the session's withdraw) is the next sentence's claim, pinned in
  tests/test_reference_todo_file_withdraw.py only.
- CONTEXT.md's **User todo** entry lists "request" under _Avoid_, and the same follow-on purged the word from
  docs/guide.md (tests/test_guide_todo_file_chip.py) while the reference's paragraph, its two MCP rows and
  the File comments paragraph kept saying "request" for the same object. The avoid list is read from
  CONTEXT.md, as the guide test reads it, so a new avoided word is caught here too.

Synthetic throughout: PRIVATE sids of this module's own (the goal-store fixture rule), a temp state root
bound before the kernel loads, a temp project tree named after the docs' demo domain.
"""
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
# Hermetic state BEFORE the loads — the kernel resolves its state root at import time (conftest's floor
# holds under pytest; this keeps a bare unittest run off the real store too).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = load_source("romp_kernel_reference_todo_file", os.path.join(BIN, "romp-kernel"))
jd = km.jd

RSID = "8e8e8e8e-1111-4222-8333-944444444444"      # a session with a recorded cwd
RSID2 = "8f8f8f8f-1111-4222-8333-944444444444"     # a session with no recorded cwd


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(md, lead):
    """The blank-line paragraph of `md` that starts with `lead`, collapsed."""
    for p in re.split(r"\n\s*\n", md):
        if p.lstrip().startswith(lead):
            return _flat(p)
    raise AssertionError("no paragraph starts with %r" % lead)


def _table_row(md, cell):
    """The markdown table row whose first cell starts with `cell`."""
    for line in md.splitlines():
        if line.startswith("| " + cell):
            return line
    raise AssertionError("no table row starts with %r" % cell)


def _avoid_words(context_md, term):
    """The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped (the guide
    test's reader, so the two docs are held to one list)."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    avoid = re.search(r"^_Avoid_:(.*)$", m.group(1), re.M)
    assert avoid, "CONTEXT.md entry %r has no _Avoid_ line" % term
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [w.strip() for w in bare.split(",") if w.strip()]


class _Sandbox(unittest.TestCase):
    """A per-test store under a temp state root, the switch on, a temp `notes-api` tree with one real file,
    and a recorded cwd for RSID only."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name, "state")
        os.makedirs(jd.STATE)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        self.root = os.path.join(self.td.name, "notes-api")
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write("# Findings\n")
        self.typo = os.path.join(self.root, "docs", "reprot.md")
        self._cwd = km._cwd_of
        km._cwd_of = lambda sid: self.root if sid == RSID else ""

    def tearDown(self):
        km._cwd_of = self._cwd
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()


class TheParagraphSaysWhatTheKernelDoes(_Sandbox):
    """Each claim the reference makes about a todo's `file` is checked against the helper the filing runs."""

    def setUp(self):
        super().setUp()
        self.para = _paragraph(_read("docs", "reference.md"), "**User todos.**")

    def test_the_paragraph_states_the_resolution_the_kernel_performs(self):
        self.assertIn("The kernel that holds the session makes the path absolute and stores it: `~` is expanded, a "
                      "relative path is read against the session's working directory like one in the text, and a "
                      "`file://` URI becomes its path.", self.para)
        # The existence claim ends at "no Send offers the todo." The sentence after it, which names the three
        # events that clear the todo (Reply, Dismiss, the session's withdraw), is pinned ONCE, in
        # tests/test_reference_todo_file_withdraw.py against the ADR; round 2 reworded it and this module's
        # copy of the old "only Reply or Dismiss" wording went red, so the clause is not repeated here.
        self.assertIn("The kernel does not check that the file exists. A mistyped absolute path is stored as typed, "
                      "with no warning; its chip opens nothing and no Send offers the todo.", self.para)
        self.assertIn("A value the kernel cannot make into a path on the session's machine is kept as given: the todo "
                      "is still filed, and the tool's reply says why and asks for the absolute path. That happens for a "
                      "relative path from a session whose working directory the kernel does not know, a `file://` URI "
                      "that does not carry an absolute path, a URL of another scheme, and a spelling no path can have "
                      "(a NUL byte in it, or a length past the machine's limit).", self.para)
        self.assertIn("The list a resuming session is handed back shows the path after the text of each todo that "
                      "names one.", self.para)

    def test_the_existence_wording_the_kernel_never_honoured_is_gone(self):
        # the old sentence read as "a path naming nothing on disk is warned about" — the kernel never stats
        self.assertNotIn("does not resolve on the session's machine", self.para)
        self.assertNotIn("the link may not open", self.para)

    def test_a_mistyped_absolute_path_is_stored_as_typed_with_no_warning(self):
        self.assertFalse(os.path.exists(self.typo), "the scenario needs a path naming nothing")
        self.assertEqual(km._user_todo_file(self.typo, RSID), (self.typo, None))
        tid = km._add_user_todo(RSID, "Need a look at the findings report", file=self.typo)
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$", "filed all the same")
        self.assertEqual(km._user_todos()[RSID][0]["file"], self.typo)
        # "no Send offers the todo": a comments status on the file the session meant lists nothing
        self.assertEqual(km._user_todos_naming_file(RSID, os.path.realpath(self.fp)), [])
        self.assertEqual(km._user_todos_naming_file(RSID, os.path.realpath(self.typo)), [{"id": tid, "text": "Need a look at the findings report"}],
                         "matched on the spelling stored, so a Send could only come from a file that is not there")

    def test_a_relative_path_reads_against_the_cwd_and_a_tilde_expands(self):
        self.assertEqual(km._user_todo_file("docs/../docs/report.md", RSID), (self.fp, None), "normalized")
        with mock.patch.dict(os.environ, {"HOME": self.root}):
            self.assertEqual(km._user_todo_file("~/docs/report.md", RSID), (self.fp, None))

    def test_a_file_uri_becomes_its_path(self):
        self.assertEqual(km._user_todo_file("file://" + self.fp, RSID), (self.fp, None))

    def test_a_relative_path_without_a_cwd_earns_the_warning_and_is_still_filed(self):
        stored, warning = km._user_todo_file("docs/report.md", RSID2)
        self.assertEqual(stored, "docs/report.md", "kept as given")
        self.assertIsInstance(warning, str)
        self.assertIn("did not resolve", warning)
        self.assertIn("absolute path", warning, "the reply asks for the absolute path")
        tid = km._add_user_todo(RSID2, "Need a look at the findings report", file="docs/report.md")
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$", "the todo is still filed")
        self.assertEqual(km._user_todos()[RSID2][0]["file"], "docs/report.md")
        # and the same absolute typo for a cwd-less session is NOT warned about: the check is absoluteness
        self.assertEqual(km._user_todo_file(self.typo, RSID2), (self.typo, None))

    def test_a_uri_without_an_absolute_path_and_a_url_are_kept_as_given_with_the_reason(self):
        for value in ("file://docs/report.md", "https://example.invalid/docs/report.md"):
            stored, warning = km._user_todo_file(value, RSID)
            self.assertEqual(stored, value, "kept as given")
            self.assertIsInstance(warning, str)
            self.assertIn("did not resolve", warning)
            self.assertIn("absolute path", warning, "the reply says why and asks for the absolute path")

    def test_a_spelling_no_path_can_have_is_kept_as_given_with_the_reason(self):
        # the paragraph's last two cases (the review, 2026-09-07: the list read as exhaustive and omitted them):
        # a NUL byte, in the value or percent-encoded in a URI, and a spelling past the machine's path limit
        # (test_kernel_todo_file_edges.py holds the mechanics; here the doc's claim is held to the helper)
        nul = os.path.join(self.root, "docs", "rep\x00ort.md")
        for value in (nul, "file://" + os.path.join(self.root, "docs", "rep%00ort.md"),
                      os.path.join(self.root, "docs", "x" * km._PATH_MAX + ".md")):
            stored, warning = km._user_todo_file(value, RSID)
            self.assertEqual(stored, value, "kept as given")
            self.assertIsInstance(warning, str)
            self.assertIn("did not resolve", warning)
            self.assertIn("absolute path", warning, "the reply says why and asks for the absolute path")
        # the absolute spelling the kernel DOES take is untouched by the new clause: still stored, no warning
        self.assertEqual(km._user_todo_file(self.fp, RSID), (self.fp, None))

    def test_the_tools_reply_relays_the_warning(self):
        # "the tool's reply tells the session so": add_user_todo appends the kernel's warning to its Noted line
        postal = _read("postal", "postal_service.py")
        self.assertIn('warning = str(res.get("warning") or "").strip()', postal)
        self.assertIn('out += " About the file: " + warning', postal)

    def test_the_resume_list_shows_the_path_after_the_text(self):
        km._add_user_todo(RSID, "Need a look at the findings report", file=self.fp)
        block = km._user_todo_context_block(RSID)
        self.assertRegex(block, r"- Need a look at the findings report \(ut-[0-9a-f]{8}, opened \d{4}-\d{2}-\d{2}\); file: "
                                + re.escape(self.fp))


class TheParagraphSaysWhatTheKernelDoesForLinks(_Sandbox):
    """`link` (the user 2026-09-08): the reference's account of a URL in the text and of a todo's own `link`,
    each held to the code that does it: the URL pass is the webview's (url-links.ts; pinned at source there and
    run in url-links.test.ts), the `link` check the kernel's `_user_todo_link`."""

    LINK = "https://example.invalid/notes-api/pull/398"

    def setUp(self):
        super().setUp()
        self.para = _paragraph(_read("docs", "reference.md"), "**User todos.**")

    def test_the_paragraph_says_a_url_in_the_text_links_and_what_stays_outside(self):
        self.assertIn("An http or https address in the text or the detail is a link too, shown as typed and opened in a new "
                      "tab; it runs to the next whitespace, quote, angle bracket or backtick, sentence punctuation after it "
                      "stays outside the link, and so does a closing bracket the address itself did not open", self.para)
        self.assertIn("A path-shaped run inside an address is part of the address, never a file link.", self.para)
        # the webview's grammar, the sentence's source: the same characters end a URL, the same trail is trimmed
        urls = _read("ui", "webview", "url-links.ts")
        self.assertIn('const URL_RE = /https?:\\/\\/[^\\s<>"\'`]+/gi;', urls)
        self.assertIn('const URL_TRAIL = ".,;:!?\'\\"";', urls)
        self.assertIn('const PAIRS: Record<string, string> = { ")": "(", "]": "[", "}": "{" };', urls)
        # and both hosts run it before the path walk, which is what makes the last sentence true
        render = _read("ui", "webview", "render.ts")
        self.assertIn("function linkTodoLinePaths(node: HTMLElement, sid: string | null): void {\n  linkifyUrls(node);\n  linkifyPathTokens(node, sid);\n}", render)
        waiting = _read("ui", "webview", "waiting.ts")
        self.assertRegex(waiting, r"function linkTodoPaths\(node: HTMLElement, sid: string\): void \{\n  linkifyUrls\(node\);[^\n]*\n  if \(!framed\) return;\n  linkifyPathTokens\(node, sid\);\n\}")

    def test_the_paragraph_states_the_link_argument_and_what_is_refused(self):
        self.assertIn("A todo can carry a web address of its own as well, through the tool's `link` argument: an http or "
                      "https address, shown as a chip beside the file's on the session's card and in the pane alike, opening "
                      "in a new tab. The chip's label keeps the part that tells two addresses apart: a GitHub `pull/N` or `issues/N` "
                      "address reads `owner/repo#N`, any other address as its host and last two path segments; the whole "
                      "address is on hover.", self.para)
        # the label's source (url-links.ts urlChipLabel; url-links.test.ts executes the forms)
        urls = _read("ui", "webview", "url-links.ts")
        self.assertIn('if (gh) return gh[1] + "/" + gh[2] + "#" + gh[3];', urls)
        self.assertIn('return segs[0] + "/…/" + segs.slice(-2).join("/") + tail;', urls)
        # the bounds on a todo's text and detail (the 2026-09-09 review), stated once and held to both processes
        self.assertIn("A todo's text takes at most 300 characters and its detail 4000, a pinned note's bounds; a longer one "
                      "is refused before anything is filed, and the tool's reply names the bound.", self.para)
        self.assertEqual((km.USER_TODO_TEXT_MAX, km.USER_TODO_DETAIL_MAX), (300, 4000))
        self.assertIn("Only such an address is taken: anything else (another scheme, a bare host, a value with whitespace "
                      "or a character that does not print in it, one past 2048 characters) is refused, the todo is not "
                      "filed, and the tool's reply says why.", self.para)
        self.assertIn("The kernel does not fetch the address, so a mistyped host is stored as typed.", self.para)
        self.assertIn("The handed-back list shows the address after the path.", self.para)
        self.assertEqual(km._TODO_LINK_MAX, 2048, "the number the paragraph states")

    def test_only_such_an_address_is_taken(self):
        self.assertEqual(km._user_todo_link(self.LINK), (self.LINK, None))
        self.assertEqual(km._user_todo_link("http://example.invalid/notes"), ("http://example.invalid/notes", None))
        for value, why in (("ftp://example.invalid/x", "another scheme"), ("example.invalid/x", "a bare host"),
                           ("https://example.invalid/a b", "whitespace"), ("https://example.invalid/a\u200bb", "does not print"),
                           ("https://example.invalid/" + "x" * 2048, "past 2048")):
            with self.subTest(case=why):
                stored, err = km._user_todo_link(value)
                self.assertIsNone(stored)
                self.assertIn("http or https address", err, "the tool's reply says why")
                with self.assertRaises(ValueError):
                    km._add_user_todo(RSID, "Need a review of the pull request", link=value)
        self.assertEqual(km._user_todos(), {}, "the todo is not filed")

    def test_a_mistyped_host_is_stored_as_typed(self):
        typo = "https://exmaple.invalid/notes-api/pull/398"
        self.assertEqual(km._user_todo_link(typo), (typo, None))
        km._add_user_todo(RSID, "Need a review of the pull request", link=typo)
        self.assertEqual(km._user_todos()[RSID][0]["link"], typo)
        self.assertEqual(km._open_user_todos(RSID)[0]["link"], typo, "shown as typed on every surface")

    def test_the_handed_back_list_shows_the_address_after_the_path(self):
        km._add_user_todo(RSID, "Need a look at the findings report", file=self.fp, link=self.LINK)
        block = km._user_todo_context_block(RSID)
        self.assertRegex(block, r"- Need a look at the findings report \(ut-[0-9a-f]{8}, opened \d{4}-\d{2}-\d{2}\); file: "
                                + re.escape(self.fp) + "; link: " + re.escape(self.LINK))

    def test_the_tools_reply_refuses_before_the_post_and_names_a_kernel_that_kept_no_link(self):
        postal = _read("postal", "postal_service.py")
        self.assertIn("lerr = _todo_link_error(link_)", postal)
        self.assertIn('return ("Refused: %s. Nothing was saved', postal)
        self.assertIn('if "link" in body and not res.get("link"):', postal)
        self.assertIn('out += (" About the link: %s was not recorded', postal)


class TheReferenceUsesTheTodoVocabulary(unittest.TestCase):
    """The paragraph, the two MCP rows and the File comments paragraph say "todo", never a word CONTEXT.md's
    **User todo** entry avoids — the rule the guide already holds to."""

    def setUp(self):
        self.ref = _read("docs", "reference.md")
        self.avoid = _avoid_words(_read("CONTEXT.md"), "User todo")
        self.assertIn("request", self.avoid)

    def _assert_no_avoid_word(self, text, where):
        # "ask" is skipped as the guide tests skip it (a verb the prose may need: "asks for the absolute path");
        # the rest are noun phrases for the object itself
        for word in self.avoid:
            if word == "ask":
                continue
            self.assertNotRegex(text, re.compile(r"\b" + re.escape(word) + r"s?\b", re.I),
                                "%s says %r; CONTEXT.md avoids it" % (where, word))

    def test_the_user_todos_paragraph(self):
        para = _paragraph(self.ref, "**User todos.**")
        self._assert_no_avoid_word(para, "the User todos paragraph")
        self.assertIn("Each open todo is listed under *Waiting on you*", para)
        self.assertIn("A todo can also name the file it is about, through the tool's `file` argument.", para)

    def test_the_mcp_rows(self):
        add = _table_row(self.ref, "`add_user_todo(text, detail?, file?, link?)`")
        withdraw = _table_row(self.ref, "`withdraw_user_todo(id)`")
        self._assert_no_avoid_word(add, "the add_user_todo row")
        self._assert_no_avoid_word(withdraw, "the withdraw_user_todo row")
        self.assertIn("`text` is the one-line todo, `detail` optional longer context, `file` the absolute path of the "
                      "file the todo is about, `link` the http or https address it is about (User todos, above)", add)
        self.assertIn("Take back a todo by the id `add_user_todo` returned", withdraw)

    def test_the_file_comments_paragraph(self):
        para = _paragraph(self.ref, "**File comments** (the viewer's Comments panel)")
        self._assert_no_avoid_word(para, "the File comments paragraph")
        self.assertIn("so no todo appears under Waiting on you", para)

    def test_the_guide_and_the_reference_name_the_object_alike(self):
        guide = _read("docs", "guide.md")
        m = re.search(r"^### Waiting on you\n(.*?)(?=^#{2,3} )", guide, re.S | re.M)
        assert m, "the guide's Waiting on you section"
        self.assertIn("todo", _flat(m.group(1)))
        self.assertIn("todo", _paragraph(self.ref, "**User todos.**"))


if __name__ == "__main__":
    unittest.main()
