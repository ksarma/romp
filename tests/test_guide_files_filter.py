#!/usr/bin/env python3
"""The guide's Files section describes the Comments panel's filter and the kind cue as the panel builds them.

The filter follow-on (plans/file-review.md, 2026-09-07): reviewing a document with dozens of routine
changes, the user found the few comments that mattered buried among the change cards, and a comment card
and a change card alike at a glance. The panel header gained All · Comments · Changes under the two toggles,
kept as `commentsFilter` in the shared settings, and every card head a kind cue (Comment / Change / Region)
with a coloured left edge. The guide's Track changes paragraph says the filter exists, what each option
hides, that the choice is kept, that Send to session is not filtered, and what the cue shows.

Every claim the paragraph makes is checked against the source that makes it true (the panel, the model,
the settings store, both sheets), so a renamed option, a dropped state, or a changed default fails here.
The paragraph's own words follow CONTEXT.md: comment and change, never suggestion or thread. Synthetic:
no session data, only the repo's own text.
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


def _flat(text):
    """Collapse the guide's hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(section, lead):
    """The paragraph of the section that opens with `lead`, flattened."""
    start = section.index(lead)
    end = section.find("\n\n", start)
    return _flat(section[start:] if end < 0 else section[start:end])


class TrackChangesParagraphDescribesTheFilter(unittest.TestCase):
    """The Track changes paragraph says the filter exists, what each option hides, and how it is kept."""

    def setUp(self):
        self.paragraph = _paragraph(_section(_read("docs", "guide.md"), "Files"), "**Track changes**")
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.model = _read("ui", "webview", "file-comments-model.ts")
        self.settings = _read("ui", "webview", "settings.ts")

    def test_the_filter_is_named_after_show_changes_inline_with_its_offer_condition(self):
        self.assertIn("Once a file has a comment or a change, **All**, **Comments**, and **Changes** appear under those "
                      "two toggles and choose what the panel lists; Comments and Changes show their counts.", self.paragraph)
        self.assertLess(self.paragraph.index("**Show changes inline**"), self.paragraph.index("**All**, **Comments**, and **Changes**"))
        # the offer condition is the model's filterOffered, and the header reads it
        self.assertIn("export function filterOffered(", self.model)
        self.assertIn("if (filterOffered(s)) {", self.panel)
        # the three labels, the counts on two of them
        self.assertRegex(self.panel, r'\["all", "All", ')
        self.assertRegex(self.panel, r'\["comments", "Comments " \+ n\.comments, ')
        self.assertRegex(self.panel, r'\["changes", "Changes " \+ n\.changes, ')

    def test_each_option_s_sentence_matches_what_the_panel_hides(self):
        self.assertIn("**Comments** lists only the comments, comments about changes among them, and hides the change marks "
                      "in the file;", self.paragraph)
        self.assertIn('if (this.activeFilter() === "comments") return;', self.panel, "Comments: no change mark painted")
        self.assertIn('const cards = filter === "changes" ? [] : this.cards();', self.panel,
                      "Comments and All: every comment's card, the ones about changes too (the about follow-on, 2026-09-10)")
        self.assertIn("**Changes** lists only the changes, each counting the comments about it, and hides the comment "
                      "highlights and the rectangles on figures;", self.paragraph)
        self.assertIn('this.activeFilter() === "changes" ? [] : this.cards()', self.panel, "Changes: no highlight painted")
        self.assertIn('const hideRegions = this.activeFilter() === "changes";', self.panel, "Changes: no rectangle painted")
        self.assertIn('comments: commentsAbout(cards, h.id).length, detached: false,', self.model, "the count of comments about a change is the model's")
        self.assertIn('const t = el("span", "fc-tag fc-count fc-about-count", c.comments + (c.comments === 1 ? " comment" : " comments"));',
                      self.panel, "the change card counts them in a tag")
        self.assertNotIn("renderHosted", self.panel, "no comment is drawn inside a change card")
        self.assertIn("**All** lists both.", self.paragraph)

    def test_the_choice_is_kept_like_the_marks_setting(self):
        self.assertIn("The choice is kept like the marks setting and changes only what is shown:", self.paragraph)
        self.assertRegex(self.settings, re.compile(r"^\s+commentsFilter: CommentsFilter;", re.M), "a field of the shared settings")
        self.assertRegex(self.settings, r'export const DEFAULT_SETTINGS: RompSettings = \{[^\n]*\bcommentsFilter: "all"[,\s}]', '"all" by default')
        self.assertIn("saveSettings({ commentsFilter: f });", self.panel)
        self.assertIn("filter: CommentsFilter = loadSettings().commentsFilter;", self.panel)

    def test_send_is_not_filtered(self):
        self.assertIn("**Send to session** still sends everything unsent.", self.paragraph)
        # the confirm and the count read the status's unsent and sendParts, never the filter
        send = self.panel[self.panel.index("private renderSend("):self.panel.index("private opt(")]
        self.assertNotIn("activeFilter", send)
        self.assertNotIn("this.filter", send)
        self.assertIn("const parts = sendParts(s);", send)
        self.assertIn("const n = s ? unsentCount(s.unsent) : 0;", send)

    def test_the_cue_sentence_matches_the_card_heads_and_the_sheets(self):
        self.assertIn("Every card names its kind, **Comment**, **Change**, or **Region**, before the author's chip, and its "
                      "left edge is colored by kind, the accent for a comment and a muted tone for a change, so the two are "
                      "told apart at a glance.", self.paragraph)
        self.assertIn('el("span", "fc-kind", c.kind === "region" ? "Region" : "Comment")', self.panel)
        self.assertIn('el("span", "fc-kind", "Change")', self.panel)
        for sheet in ("styles.css", "feed.css"):
            css = _read("ui", "webview", sheet)
            self.assertIn('.fc-card[data-cue="comment"]:not(.fc-card-detached) { border-left: 3px solid var(--accent); }', css, sheet)
            self.assertIn('.fc-card[data-cue="change"]:not(.fc-card-detached) { border-left: 3px solid var(--text-muted); }', css, sheet)


class TheParagraphKeepsTheVocabulary(unittest.TestCase):
    """The new sentences say comment and change, never the storage format's words."""

    def test_no_avoid_word(self):
        paragraph = _paragraph(_section(_read("docs", "guide.md"), "Files"), "**Track changes**")
        for word in ("suggestion", "thread", "annotation", "diff", "fleet"):
            self.assertNotRegex(paragraph, re.compile(r"\b" + word + r"s?\b", re.I), word)


class ThePlanCarriesTheNote(unittest.TestCase):
    """The plan's follow-on note stands under Slice 2 and names what the user hit and what was built."""

    def setUp(self):
        self.plan = _read("plans", "file-review.md")

    def test_the_note_stands_beside_the_other_follow_on_notes(self):
        at = self.plan.index("The filter follow-on (2026-09-07):")
        self.assertLess(self.plan.index("The composer follow-on (2026-09-07):"), at)
        self.assertLess(at, self.plan.index("### Slice 3: region comments on images"))

    def test_the_note_says_what_the_user_hit_and_what_was_built(self):
        note = _flat(self.plan[self.plan.index("The filter follow-on (2026-09-07):"):].split("\n\n")[0])
        self.assertIn("dozens of routine changes", note)
        self.assertIn("**All · Comments N · Changes M**", note)
        self.assertIn("`commentsFilter`", note)
        self.assertIn("`cardCounts`", note)
        self.assertIn("Comment, Change, or Region", note)
        self.assertIn("`tests/test_guide_files_filter.py`", note)


if __name__ == "__main__":
    unittest.main()
