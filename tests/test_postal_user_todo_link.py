#!/usr/bin/env python3
"""add_user_todo's `link` end to end (the user 2026-09-08, whose todo titles named pull requests by URL): the
tool's check and the kernel's agree, a good address rides the tool's post through the REAL /usertodo route onto
the row and back in the echo, and a bad one is refused by the tool before any post (and by the route, for a
hand-built POST, as a 400 with the same words).

The tool and the kernel are separate processes and cannot share a function, so each holds a copy of the rule
(postal_service.py _todo_link_error, kernel.py _user_todo_link): TheTwoChecksAgree runs both over one list of
addresses and refusals and holds them to one verdict and one wording, so a widening on one side without the
other is caught here.

Named test_*.py like every Python test module (the ratchets over tests/ visit those alone). SYNTHETIC fixtures
only: a private placeholder sid, example.invalid addresses, the notes-api demo world under a temp dir.
"""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: both resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = load_source("romp_postal_todo_link", os.path.join(BIN, "romp-postal-service"))
km = load_source("romp_kernel_postal_todo_link", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# PRIVATE synthetic sid (the goal-store fixture rule, generalized: rows minted under the shared placeholder
# can be reached by another module's fixtures).
PSID = "6b6b6b6b-1111-4222-8333-944444444444"
TEXT = "Need a review of the pull request"
LINK = "https://example.invalid/notes-api/pull/398"

# One list, two checks: (value, accepted). The refusals cover each rule in turn.
CASES = [
    (LINK, True),
    ("http://example.invalid/notes", True),
    ("HTTPS://Example.invalid/X?y=1#z", True),
    ("  " + LINK + "  ", True),
    ("https://exmaple.invalid/typo", True),            # not fetched: a mistyped host is an address
    ("https://example.invalid/" + "x" * 2000, True),   # long, under the bound
    ("ftp://example.invalid/x", False),
    ("example.invalid/x", False),
    ("https://", False),
    ("https:///nohost", False),
    ("mailto:someone@example.invalid", False),
    ("javascript:alert(1)", False),
    ("file:///tmp/notes-api/a.md", False),
    ("https://example.invalid/a b", False),
    ("https://example.invalid/a\tb", False),
    ("https://example.invalid/a\nb", False),
    ("https://example.invalid/a\x00b", False),
    ("https://example.invalid/a\x1bb", False),         # ESC: a C0 control
    ("https://example.invalid/a\x7fb", False),         # DEL
    ("https://example.invalid/\x9bx", False),          # a C1 control, which str.isspace does not read as whitespace (the 2026-09-09 review)
    ("https://example.invalid/a\x85b", False),         # NEL: C1, and whitespace to isspace
    ("https://example.invalid/a\x80b", False),         # the first C1 code point
    # the round-3 review: the C0/C1 gate let every format character through, and a refused Unicode whitespace rode
    # the reason as itself; one predicate now (not printable, or whitespace) refuses and spells all of them
    ("https://example.invalid/a\u200bb", False),       # ZERO WIDTH SPACE: a format character, neither a control nor whitespace to isspace
    ("\ufeffhttps://example.invalid/x", False),        # a leading BYTE ORDER MARK, the paste artifact: not whitespace, so strip() keeps it
    ("https://example.invalid/a\u2028b", False),       # LINE SEPARATOR: whitespace to isspace, and shown unspelled before
    ("https://example.invalid/a\u2060b", False),       # WORD JOINER: a format character
    ("https://example.invalid/a\xa0b", False),         # NO-BREAK SPACE
    ("https://example.invalid/caf\u00e9", True),       # a printable character outside ASCII is an address's own, not refused
    ("https://example.invalid/" + "x" * 2048, False),
    (["https://example.invalid/x"], False),
    ({"href": LINK}, False),
    (7, False),
    (2.5, False),
    (True, False),
]


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


class TheTwoChecksAgree(unittest.TestCase):
    """The tool's _todo_link_error and the kernel's _user_todo_link: one verdict and one wording per value."""

    def test_the_same_verdict_for_every_case(self):
        for value, ok in CASES:
            with self.subTest(link=value):
                perr = pm._todo_link_error(value)
                stored, kerr = km._user_todo_link(value)
                self.assertEqual(perr is None, ok, "the tool")
                self.assertEqual(kerr is None, ok, "the kernel")
                if ok:
                    self.assertEqual(stored, value.strip(), "the kernel stores it stripped, otherwise as typed")
                else:
                    self.assertIsNone(stored)

    def test_the_same_words_for_every_refusal(self):
        for value, ok in CASES:
            if ok:
                continue
            with self.subTest(link=value):
                self.assertEqual(pm._todo_link_error(value), km._user_todo_link(value)[1],
                                 "the agent reads the tool's words and a hand-built POST the kernel's: one wording")

    def test_none_and_blank_are_no_link_on_both_sides(self):
        for value in (None, "", "   ", "\n"):
            self.assertIsNone(pm._todo_link_error(value))
            self.assertEqual(km._user_todo_link(value), (None, None))

    def test_the_bound_and_the_shape_are_the_same_constants(self):
        self.assertEqual(pm.TODO_LINK_MAX, km._TODO_LINK_MAX)
        self.assertEqual(pm._TODO_LINK_RE.pattern, km._TODO_LINK_RE.pattern)
        self.assertEqual(pm._TODO_LINK_RE.flags, km._TODO_LINK_RE.flags)

    def test_every_refused_character_is_spelled_out_on_both_sides(self):
        # a NUL was spelled out and every other control rode the reason as itself, invisible in a reply (the 2026-09-09
        # review); then the format characters and separators past U+00FF, as \uNNNN (the round-3 review), and the ordinary
        # space as \x20, since the one predicate that refuses a character also decides its spelling
        for value, esc in (("https://example.invalid/a\x1bb", "\\x1b"), ("https://example.invalid/a\x7fb", "\\x7f"),
                           ("https://example.invalid/\x9bx", "\\x9b"), ("https://example.invalid/a\x85b", "\\x85"),
                           ("https://example.invalid/a\x00b", "\\0"),
                           ("https://example.invalid/a\u200bb", "\\u200b"), ("\ufeffhttps://example.invalid/x", "\\ufeff"),
                           ("https://example.invalid/a\u2028b", "\\u2028"), ("https://example.invalid/a\u2060b", "\\u2060"),
                           ("https://example.invalid/a\xa0b", "\\xa0"), ("https://example.invalid/a b", "\\x20")):
            with self.subTest(link=value):
                for side, err in (("the tool", pm._todo_link_error(value)), ("the kernel", km._user_todo_link(value)[1])):
                    self.assertIn("whitespace or a control character", err, side)
                    self.assertIn(esc, err, side + ": the character is spelled out")
                    self.assertTrue(err.isprintable(), side + ": no unprintable character rides the reason")

                    self.assertEqual(err.count("example.invalid"), 1, side + ": the address is shown once, spelled")
        # the two spellers agree above U+FFFF too (Python's \UNNNNNNNN), and on a printable character they are not asked
        for side in (pm, km):
            self.assertEqual(side._todo_link_spell("\U000e0001"), "\\U000e0001")
            self.assertFalse(side._todo_link_bad_char("\u00e9"))
            self.assertTrue(side._todo_link_bad_char(" "), "the ordinary space is refused, as before")

    def test_a_long_refused_link_keeps_its_count_suffix_unspelled_and_names_a_character_past_the_cut(self):
        # round 3's spelling pass ran over the shown string AFTER the 80-character cut had appended "... (N characters)",
        # so the suffix's own spaces read \x20 (the round-3 review); the address is spelled, the suffix is not, and a
        # refused character past the cut is named after the count so the reason always names one
        early = "https://example.invalid/" + "x" * 6 + " " + "x" * 70          # 101 characters, the space at 30
        late = "https://example.invalid/" + "x" * 50 + "\u200b" + "x" * 40     # 115 characters, the ZWSP at 74
        for side, check in (("the tool", pm._todo_link_error), ("the kernel", lambda v: km._user_todo_link(v)[1])):
            with self.subTest(side=side, link="early"):
                err = check(early)
                self.assertIn("... (%d characters) holds whitespace" % len(early), err, "the suffix keeps its spaces")
                self.assertNotIn("\\x20(", err, "the suffix is never spelled")
                self.assertEqual(err.count("\\x20"), 1, "the address's own space is spelled once")
                self.assertNotIn("past the cut", err, "nothing hidden past the cut")
            with self.subTest(side=side, link="late"):
                err = check(late)
                self.assertIn("... (%d characters) (past the cut: \\u200b) holds whitespace" % len(late), err,
                              "a refused character past the cut is named after the count")
                self.assertTrue(err.isprintable(), "no unprintable character rides the reason")

    def test_the_text_and_detail_bounds_are_the_same_constants_and_the_pinned_notes(self):
        # the 2026-09-09 review: neither had a cap, and the webview links every open todo's text and detail on every
        # Waiting pane frame and every chat push, so one unbounded string cost every reader
        self.assertEqual((pm.TODO_TEXT_MAX, pm.TODO_DETAIL_MAX), (km.USER_TODO_TEXT_MAX, km.USER_TODO_DETAIL_MAX))
        self.assertEqual((km.USER_TODO_TEXT_MAX, km.USER_TODO_DETAIL_MAX), (km.PINNED_TEXT_MAX, km.PINNED_DETAIL_MAX),
                         "a todo's bounds are a pinned note's")
        self.assertEqual((pm.TODO_TEXT_MAX, pm.TODO_DETAIL_MAX), (300, 4000), "the numbers the tool descriptions and the reference state")


class WiredToTheKernel(unittest.TestCase):
    """The tool's post handed to the REAL /usertodo route (the kernel's dispatcher, in process)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self._saved_state = jd.STATE
        self.addCleanup(self._restore_state)
        jd.STATE = Path(os.path.realpath(self.td.name)) / "state"
        jd.STATE.mkdir()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        self._saved_km = (km._push_all, km._push_soon)
        self.addCleanup(self._restore_km)
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        self.pushed = []
        km._push_soon = lambda: self.pushed.append(True)
        self._saved_pm = (pm._kernel_post, pm._self_identity, pm._heartbeat, pm.USER_TODOS_SWITCH)
        self.addCleanup(self._restore_pm)
        self.posts = []
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
        km._push_all, km._push_soon = self._saved_km

    def _restore_pm(self):
        pm._kernel_post, pm._self_identity, pm._heartbeat, pm.USER_TODOS_SWITCH = self._saved_pm

    def _post(self, path, body, timeout=4.0):
        self.posts.append((path, body))
        code, out = _serve_post(path, body, {"X-Romp-Token": km.TOKEN})
        return json.loads(out.decode() or "{}") if code and code // 100 == 2 else None

    def test_a_good_address_lands_on_the_row_and_comes_back_in_the_echo(self):
        out, err = pm._mcp_call("add_user_todo", {"text": TEXT, "link": "  " + LINK + " "})
        self.assertFalse(err)
        self.assertIn("Noted (id ut-", out)
        self.assertNotIn("About the link", out, "the kernel echoed the link it stored: nothing to say")
        self.assertEqual(self.posts[-1][1]["link"], LINK, "stripped before the post")
        rec = km._user_todos()[PSID][-1]
        self.assertEqual(rec["link"], LINK)
        self.assertEqual(km._open_user_todos(PSID)[0]["link"], LINK, "the rows every surface ships carry it")
        self.assertEqual(len(self.pushed), 1, "the pusher woke once")

    def test_a_bad_address_is_refused_by_the_tool_and_the_kernel_is_never_asked(self):
        out, err = pm._mcp_call("add_user_todo", {"text": TEXT, "link": "ftp://example.invalid/x"})
        self.assertTrue(err)
        self.assertTrue(out.startswith("Refused: the link ftp://example.invalid/x is not an http or https address"), out)
        self.assertEqual(self.posts, [], "no post")
        self.assertEqual(km._user_todos(), {}, "no row")
        self.assertEqual(self.pushed, [])

    def test_a_hand_built_post_with_a_bad_address_is_the_routes_400_in_the_same_words(self):
        code, raw = _serve_post("/usertodo", {"id": PSID, "text": TEXT, "link": "ftp://example.invalid/x"},
                                {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)
        body = json.loads(raw.decode())
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], pm._todo_link_error("ftp://example.invalid/x"))
        self.assertEqual(km._user_todos(), {})
        # and the tool, handed that refusal by a kernel it did not pre-check against (a hypothetical), still
        # answers plainly: _kernel_post files a 4xx as {ok: False, ...}, which the tool reads as "not saved"
        pm._kernel_post = lambda path, body, timeout=4.0: {"ok": False, "status": 400, "error": "the link x is not an http or https address"}
        out, err = pm._mcp_call("add_user_todo", {"text": TEXT})
        self.assertTrue(err)
        self.assertIn("will NOT see it", out)

    def test_an_over_long_text_or_detail_is_refused_by_the_tool_before_any_post_and_by_the_route_as_a_400(self):
        long_text = "N" * (pm.TODO_TEXT_MAX + 1)
        out, err = pm._mcp_call("add_user_todo", {"text": long_text})
        self.assertTrue(err)
        self.assertIn("Too long: the line takes at most %d characters and this one is %d" % (pm.TODO_TEXT_MAX, pm.TODO_TEXT_MAX + 1), out)
        self.assertIn("Nothing was saved", out)
        out, err = pm._mcp_call("add_user_todo", {"text": TEXT, "detail": "d" * (pm.TODO_DETAIL_MAX + 1)})
        self.assertTrue(err)
        self.assertIn("'detail' takes at most %d characters" % pm.TODO_DETAIL_MAX, out)
        self.assertEqual(self.posts, [], "no post")
        self.assertEqual(km._user_todos(), {}, "no row")
        # at the bound: filed
        out, err = pm._mcp_call("add_user_todo", {"text": "N" * pm.TODO_TEXT_MAX, "detail": "d" * pm.TODO_DETAIL_MAX})
        self.assertFalse(err, out)
        self.assertEqual(len(km._user_todos()[PSID]), 1)
        # a hand-built POST past the bound: the route's 400 naming the field and the bound, nothing filed
        for body, key in (({"id": PSID, "text": long_text}, "text"),
                          ({"id": PSID, "text": TEXT, "detail": "d" * (km.USER_TODO_DETAIL_MAX + 1)}, "detail")):
            with self.subTest(field=key):
                code, raw = _serve_post("/usertodo", body, {"X-Romp-Token": km.TOKEN})
                self.assertEqual(code, 400)
                self.assertIn("%s is longer than %d characters" % (key, getattr(km, "USER_TODO_%s_MAX" % key.upper())),
                              json.loads(raw.decode())["error"])
        self.assertEqual(len(km._user_todos()[PSID]), 1, "nothing more filed")
        # a hand-built POST with the detail at the bound inside surrounding whitespace: the route strips before it
        # measures, as the tool does before it posts (the round-3 review: it measured the raw value, so a padded detail
        # the tool would have filed was a 400 for every other client), and the row keeps the detail as measured
        code, raw = _serve_post("/usertodo", {"id": PSID, "text": " " + TEXT + " ", "detail": " \n" + "d" * km.USER_TODO_DETAIL_MAX + "\t "},
                                {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 200, raw)
        rows = km._user_todos()[PSID]
        self.assertEqual(len(rows), 2, "filed, not refused")
        self.assertEqual(rows[-1]["detail"], "d" * km.USER_TODO_DETAIL_MAX, "stored stripped, as the tool's post is")
        self.assertEqual(rows[-1]["text"], TEXT)

    def test_a_link_beside_a_file_rides_both_and_the_text_links_too(self):
        root = os.path.join(self.td.name, "notes-api")
        os.makedirs(root)
        fp = os.path.join(root, "report.md")
        open(fp, "w").close()
        saved = km._cwd_of
        km._cwd_of = lambda sid: root if sid == PSID else ""
        self.addCleanup(lambda: setattr(km, "_cwd_of", saved))
        out, err = pm._mcp_call("add_user_todo", {"text": "Need a look at report.md and " + LINK, "file": "report.md", "link": LINK})
        self.assertFalse(err)
        self.assertNotIn("About the", out)
        rec = km._user_todos()[PSID][-1]
        self.assertEqual((rec["file"], rec["link"]), (fp, LINK))
        self.assertEqual(rec["text"], "Need a look at report.md and " + LINK, "the text is kept as typed: the webview links the address in it")


if __name__ == "__main__":
    unittest.main()
