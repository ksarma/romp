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
