#!/usr/bin/env python3
"""The token login page is the screen a signed-out user actually lands on, so it has to be
self-service. After a reinstall (the state dir goes, the next kernel mints a new token) an
existing tab or bookmark silently drops to this page — and read as "the dashboard never
loaded" rather than "you are signed out" (the user 2026-07-27, on a real reinstall).

It must therefore say what happened, and give a command that works from the state the reader
is actually in: a terminal opened BEFORE the install has a stale PATH, so `romp url` alone is
not enough advice — the raw token file has to be there too.

The default view stays short (ui/CLAUDE.md's progressive disclosure): the one sentence, the form
and the `romp url` / `romp` pointer. Why a browser is signed out, and what to do when `romp` is
not found, sit behind <details> folds that open with no script (DefaultViewAndFolds); how the
page renders on a phone-sized screen is checked in a browser by
tests/test_page_key_dashboard_browser.py.

Synthetic only: asserts on the static HTML constant, starts no server.
"""
import os
import re
import unittest
from html.parser import HTMLParser
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_loginpage", os.path.join(BIN, "romp-kernel"))

HTML = km._TOKEN_LOGIN_HTML


class TokenLoginPage(unittest.TestCase):
    def test_explains_that_a_reinstall_signs_you_out(self):
        """The misreading to prevent is "it's broken". Name the cause and say it isn't."""
        low = HTML.lower()
        self.assertIn("reinstall", low)
        self.assertIn("signed out", low)
        self.assertIn("not broken", low)

    def test_says_a_browser_that_lost_its_saved_sign_in_needs_the_token_or_a_fresh_link(self):
        """The page key a sign-in leaves lives in the site's storage, which a browser can lose while its cookie stays
        (cleared site data, a private window, a browser that clears the storage of a site it has not opened for a
        while). The page-key script then sends the reader here, and only the token, a `romp url` link or a window a
        bare `romp` opens signs them in again. The page must name that case, since it is not a reinstall, and name the
        two ways back that need no pasting."""
        flat = " ".join(HTML.split())
        low = flat.lower()
        self.assertIn("lost its saved sign-in", low)
        for case in ("cleared site data", "a private window", "clears a site's storage", "added to the home screen"):
            self.assertIn(case, low)
        self.assertIn("in an app on the home screen, paste the token here", low,
                      "an installed app keeps storage of its own, and pasting the token is the way it signs in")
        self.assertIn("run <code>romp url</code>", flat, "the link that signs a browser in")
        self.assertIn("run <code>romp</code> there to open a signed-in window", flat, "the window a bare romp opens")

    def test_names_the_exact_command_not_just_the_binary(self):
        """`romp` opens the dashboard; `romp url` PRINTS the link. A signed-out reader needs
        the link, and on a headless/remote box `romp` alone has nothing to open."""
        self.assertIn("romp url", HTML)

    def test_covers_the_stale_PATH_case_the_command_alone_does_not(self):
        """A terminal opened before the install cannot run `romp` at all. Without the file
        fallback the advice dead-ends exactly when it is most needed."""
        self.assertIn("serve-token", HTML)
        self.assertIn("PATH", HTML)

    def test_is_self_contained_and_leaks_nothing(self):
        """Every other route is token-gated, so this page is served to an UNAUTHENTICATED
        caller. It must pull in no external asset and must never embed the token itself."""
        self.assertNotIn("/dist/", HTML)
        self.assertNotIn("http://", HTML)
        self.assertNotIn("https://", HTML)
        # No interpolation holes that a token could ever be rendered into.
        self.assertNotIn("%s", HTML)
        self.assertNotIn("{}", HTML)

    def test_posts_nothing_and_keeps_the_token_out_of_history(self):
        """The form redirects client-side to /?token=…; it must not POST anywhere."""
        self.assertNotIn("method=", HTML.lower())
        self.assertIn("location.replace", HTML)   # replace(), so the token is not left in
        #                                           the back-stack of the signed-out page

    def test_encodes_the_pasted_token(self):
        """A pasted token with URL-significant characters must survive the redirect."""
        self.assertIn("encodeURIComponent", HTML)

    def test_renders_as_one_html_document(self):
        self.assertTrue(HTML.lstrip().lower().startswith("<!doctype html>"))
        # Balanced enough to render: the form the reader types into is actually closed.
        self.assertEqual(HTML.count("<form"), 1)
        self.assertEqual(HTML.count("</form>"), 1)
        # No stray backslash-continuations left dangling inside an attribute value.
        self.assertNotIn("\\\n", HTML)

    def test_uses_the_accent_colour_the_repo_standardised_on(self):
        """Accent chrome is --accent #9cd2ff on --accent-fg #0c1a2e."""
        self.assertIn("#9cd2ff", HTML)
        self.assertIn("#0c1a2e", HTML)


class _Folds(HTMLParser):
    """The page's text in two parts: what the default view shows (outside every <details>, each fold's
    <summary> included, since that line shows while the fold is closed) and what a closed fold hides
    (inside a <details>, its summary excluded); with the attribute names of every element inside a
    fold, and the number of script elements, folds and summaries."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = self.in_summary = self.scripts = self.details = self.summaries = 0
        self.shown, self.folded, self.fold_attrs = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts += 1
        if tag == "details":
            self.depth += 1
            self.details += 1
        if self.depth:
            self.fold_attrs.extend(name for name, _ in attrs)
        if tag == "summary" and self.depth:
            self.in_summary += 1
            self.summaries += 1

    def handle_endtag(self, tag):
        if tag == "summary" and self.in_summary:
            self.in_summary -= 1
        if tag == "details" and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        (self.folded if self.depth and not self.in_summary else self.shown).append(data)


class DefaultViewAndFolds(unittest.TestCase):
    """The default view is the one sentence, the form and the pointer to `romp url` and a bare
    `romp`. The list of reasons a browser is signed out sits behind a <details> fold, and so do the
    stale-PATH note and the token file, so the page a signed-out reader lands on stays short
    (ui/CLAUDE.md: glanceable by default, the rest one click away). A fold is the browser's own
    <details>, so it opens with no script."""

    @classmethod
    def setUpClass(cls):
        cls.p = _Folds()
        cls.p.feed(HTML)
        cls.p.close()
        cls.shown = " ".join(" ".join(cls.p.shown).split()).lower()
        cls.folded = " ".join(" ".join(cls.p.folded).split()).lower()

    def test_the_reasons_for_a_sign_out_sit_inside_a_details_fold(self):
        for reason in ("lost its saved sign-in", "cleared site data", "a private window",
                       "clears a site's storage", "added to the home screen", "reinstalled",
                       "token file was replaced", "in an app on the home screen, paste the token here"):
            self.assertIn(reason, self.folded, "the reason is on the page, inside a fold: %r" % reason)
            self.assertNotIn(reason, self.shown, "and not in the default view: %r" % reason)

    def test_the_stale_path_note_and_the_token_file_sit_inside_a_fold(self):
        for text in ("stale path", "cat ~/.local/state/romp/serve-token"):
            self.assertIn(text, self.folded, "inside a fold: %r" % text)
            self.assertNotIn(text, self.shown, "and not in the default view: %r" % text)

    def test_the_default_view_keeps_the_sentence_and_the_pointer(self):
        for text in ("sign in with this dashboard's access token", "you are signed out, not broken",
                     "run romp url on the machine romp runs on", "run romp there to open a signed-in window"):
            self.assertIn(text, self.shown, "the default view says it: %r" % text)

    def test_every_fold_opens_with_no_script(self):
        self.assertGreaterEqual(self.p.details, 1, "the page has a fold")
        self.assertEqual(self.p.summaries, self.p.details, "each fold has the summary line that opens it")
        self.assertEqual(self.p.scripts, 0, "the page has no script element")
        self.assertEqual([a for a in self.p.fold_attrs if a.lower().startswith("on")], [],
                         "no event handler inside a fold: the browser opens a <details> by itself")


if __name__ == "__main__":
    unittest.main()
