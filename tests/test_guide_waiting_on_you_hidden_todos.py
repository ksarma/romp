#!/usr/bin/env python3
"""The guide's Waiting on you section speaks CONTEXT.md's vocabulary (user todo, never request) and
names BOTH reasons a todo can be missing from the pane, in the UI's own words.

Vocabulary. CONTEXT.md's User todo entry lists "request" under _Avoid_, yet this section and its
table-of-contents line called a user todo a request nine times, one sentence away from the gear's
**User todos** label, and the section's first test pinned three of those sentences verbatim, so
aligning the guide meant editing the test too (review finding, 2026-09-06). The section now says
"user todo" on first mention and "todo" after, the plan's own usage (plans/file-review.md, Slice
0). The vocabulary test reads the avoid-words from CONTEXT.md rather than hard-coding them, so a
new avoid-word, or a guide edit that reintroduces one, fails here.

Hiding causes. build_feed skips a session flagged hideFromFeed before it appends the session's
user-todo row (kernel.py build_feed: the `hideFromFeed` continue precedes `_ut_rows.append`), and
hides an ended session's todos until it is revived. Both are pinned on the kernel side already
(test_waiting_pane.py::test_a_muted_session_contributes_no_row; test_user_todos.py's ended and
revived cases). The Slice 0 guide note (plans/file-review.md, "Getting into it") named only the
ended case and told a reader missing a todo to look for an ended session, so a reader whose
session was hidden from the feed found it alive and had no explanation (review finding,
2026-09-06). The paragraph names both causes, with the tab menu's labels and the tab's ⚑ mark, so
a reader can find the hidden session and bring its todos back.

Every UI name the section uses is cross-checked against the UI source, so a renamed menu item,
glyph or gear label fails here and the guide gets updated with it. This file replaces the
section's round-1 test, whose pinned sentences carried the avoided word. Synthetic: no session
data, only the repo's own text.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _section(md, heading):
    """The body of one `### heading` up to the next heading of any level."""
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _toc_entry(md, heading, anchor):
    """The guide's table-of-contents bullet for one section, up to the next bullet or blank line."""
    start = md.index("**[%s](#%s)**" % (heading, anchor))
    m = re.compile(r"\n- |\n\n").search(md, start)
    return md[start:m.start() if m else None]


def _flat(text):
    """Collapse the guide's hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _avoid_words(context_md, term):
    """The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped."""
    m = re.search(r"^\*\*" + re.escape(term) + r"\*\*:\n(.*?)(?=\n\n|\Z)", context_md, re.S | re.M)
    assert m, "CONTEXT.md entry %r not found" % term
    avoid = re.search(r"^_Avoid_:(.*)$", m.group(1), re.M)
    assert avoid, "CONTEXT.md entry %r has no _Avoid_ line" % term
    bare = re.sub(r"\([^)]*\)", "", avoid.group(1))
    return [w.strip() for w in bare.split(",") if w.strip()]


class WaitingOnYouVocabulary(unittest.TestCase):
    """The section and its TOC line use CONTEXT.md's term and none of the words it says to avoid."""

    def setUp(self):
        self.guide = _read("docs", "guide.md")
        self.section = _flat(_section(self.guide, "Waiting on you"))
        self.toc = _flat(_toc_entry(self.guide, "Waiting on you", "waiting-on-you"))
        self.avoid = _avoid_words(_read("CONTEXT.md"), "User todo")

    def test_context_md_still_lists_the_words_this_test_bans(self):
        # The premise, checked against its source: if CONTEXT.md drops "request" from the avoid
        # list, this test's reason to exist goes with it and should be revisited, not left running.
        self.assertIn("request", self.avoid)
        self.assertIn("user task", self.avoid)

    def test_the_section_introduces_the_term_and_the_toc_uses_it(self):
        self.assertIn("One list of every user todo a session has flagged for you", self.section)
        self.assertIn("lists every user todo a session has flagged for you", self.toc)

    def test_neither_the_section_nor_the_toc_uses_an_avoid_word(self):
        # "ask" is avoided as a noun (the feed's `asks` field); as a verb it is ordinary English
        # the guide may need, and a word-boundary regex cannot tell the two apart, so it is the
        # one avoid-word not enforced here. Every other avoid-word is a noun phrase with no such
        # collision, checked in singular and plural.
        for word in self.avoid:
            if word == "ask":
                continue
            pat = r"\b" + re.escape(word) + r"s?\b"
            for where, text in (("section", self.section), ("TOC entry", self.toc)):
                self.assertNotRegex(text, re.compile(pat, re.I),
                                    "the Waiting on you %s says %r; CONTEXT.md avoids it" % (where, word))

    def test_the_gear_label_matches_the_settings_panel(self):
        # The section names the gear's switch by its label; gear.js renders that label.
        self.assertIn("the gear's **User todos** switch", self.section)
        self.assertIn("<b>User todos</b>", _read("ui", "webview", "gear.js"))


class WaitingOnYouHiddenTodos(unittest.TestCase):
    """The section names both hiding causes, with the UI's own labels and glyph."""

    def setUp(self):
        self.guide = _read("docs", "guide.md")
        self.section = _flat(_section(self.guide, "Waiting on you"))
        self.render = _read("ui", "webview", "render.ts")

    def test_the_section_names_both_hiding_causes(self):
        s = self.section
        self.assertIn("A todo you expected can be missing for two reasons.", s)
        self.assertIn("A session that has ended keeps its todos out of the list until you revive it", s)
        self.assertIn("A session you have hidden from the feed (right-click its tab, **Hide from feed**) "
                      "keeps them out too", s)
        self.assertIn("**Show in feed** on the same menu brings them back", s)
        self.assertIn("The file the todo named is still on disk.", s)

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
