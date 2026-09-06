#!/usr/bin/env python3
"""The guide's Waiting on you section names BOTH reasons a request can be missing from the pane, in
the UI's own words.

build_feed skips a session flagged hideFromFeed before it appends the session's user-todo row
(kernel.py build_feed: the `hideFromFeed` continue precedes `_ut_rows.append`), and hides an ended
session's todos until it is revived. Both are pinned on the kernel side already
(test_waiting_pane.py::test_a_muted_session_contributes_no_row; test_user_todos.py's ended and
revived cases). The Slice 0 guide note (plans/file-review.md, "Getting into it") named only the
ended case and told a reader missing a request to look for an ended session, so a reader whose
session was hidden from the feed found it alive and had no explanation (review finding,
2026-09-06). The paragraph now names both causes, with the tab menu's labels and the tab's ⚑
mark, so a reader can find the hidden session and bring its requests back.

This test reads the section and cross-checks every UI name it uses against the UI source, so a
renamed menu item or glyph fails here and the guide gets updated with it. Synthetic: no session
data, only the repo's own text.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _section(md, heading):
    """The body of one `### heading` up to the next heading of any level."""
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _flat(text):
    """Collapse the guide's hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


class WaitingOnYouHiddenRequests(unittest.TestCase):
    def setUp(self):
        self.guide = open(os.path.join(ROOT, "docs", "guide.md")).read()
        self.section = _flat(_section(self.guide, "Waiting on you"))
        self.render = open(os.path.join(ROOT, "ui", "webview", "render.ts")).read()

    def test_the_section_names_both_hiding_causes(self):
        s = self.section
        self.assertIn("A request you expected can be missing for two reasons.", s)
        self.assertIn("A session that has ended keeps its requests out of the list until you revive it", s)
        self.assertIn("A session you have hidden from the feed (right-click its tab, **Hide from feed**) "
                      "keeps them out too", s)
        self.assertIn("**Show in feed** on the same menu brings them back", s)
        self.assertIn("The file the request named is still on disk.", s)

    def test_the_imprecise_live_only_clause_is_gone(self):
        # The finding: "live sessions only" was wrong (a muted live session is excluded too) and
        # "look for an ended session" pointed a reader with a hidden session at the wrong cause.
        self.assertNotIn("live sessions only", self.section)
        self.assertNotIn("look for an ended session", self.section)

    def test_the_menu_labels_match_the_tab_menu(self):
        # The tab's context menu toggles the flag under these two labels (render.ts tab menu).
        self.assertIn('offFeed ? "Show in feed" : "Hide from feed"', self.render)
        self.assertIn("**Hide from feed**", self.section)
        self.assertIn("**Show in feed**", self.section)

    def test_the_glyph_matches_the_tab_mark(self):
        # The designed mute asymmetry: the tab glyph reads build_session's userTodos, which mute
        # does not touch, so a hidden session's tab still shows the mark the guide names.
        self.assertRegex(self.render, r'el\("span", "tab-usertodo"\);\s*\n\s*ut\.textContent = "⚑";')
        self.assertIn("its tab still shows the ⚑ mark", self.section)

    def test_the_revival_pointer_matches_the_picker_and_the_sessions_section(self):
        self.assertIn("(click **+**; closed sessions are listed under **Recent**)", self.section)
        self.assertIn('label("Recent")', self.render)
        # The same words the Sessions section uses for revival, so the two pointers cannot drift apart.
        sessions = _flat(self.guide[self.guide.index("## Sessions, revival, and search"):])
        self.assertIn("Click **+** and the closed ones are listed under **Recent**", sessions)


if __name__ == "__main__":
    unittest.main()
