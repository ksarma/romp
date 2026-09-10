#!/usr/bin/env python3
"""The guide's Files section describes the about follow-on as the panel builds it (plans/file-review.md, "The about
follow-on (2026-09-10)" under Slice 2; decisions 45 and 46).

The user's answers to the decoupling assessment: a comment should say which changes it is about by their own pick, one
list with the filter, and nothing resolves a comment but them, singly or all the answered ones at once; a comment made
inside a change is an ordinary comment. The guide's Track changes paragraph gained the sentences on Comment on this
change, the about option, the tags on both cards and the answered tag; the Send paragraph names the changes a comment
is about among what the message carries; the poll paragraph gained the Resolve answered sentence. Each claim is
checked against the source that makes it true (the panel, the model, the host), so a renamed control, a dropped tag or
a changed rule fails here. The sentences' words follow CONTEXT.md: comment, change, about; never suggestion, bound or
thread. Synthetic: only the repo's own text.
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
    m = re.search(r"^### " + re.escape(heading) + r"\n(.*?)(?=^#{2,3} )", md, re.S | re.M)
    assert m, "section %r not found" % heading
    return m.group(1)


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _paragraph(section, lead):
    start = section.index(lead)
    end = section.find("\n\n", start)
    return _flat(section[start:] if end < 0 else section[start:end])


COMMENT_ON = ("**Comment on this change** on a change's card opens the comment box over the change's text with **about this "
              "change** checked, so the comment names the change and the message tells the session which change it is about; "
              "a deletion, whose text is no longer in the file, takes a comment about the change alone, laid beside its mark.")
OWN_CARD = ("A comment is never shown inside a change's card: every comment is its own card, and the comment and the change "
            "each carry a tag for the other, **about a change** on the comment (hover it to ring the change's marks) and "
            "**N comments** on the change (click it to open the first).")
SELECTION = ("Selecting text inside a change and pressing Comment leaves an ordinary comment on those words, with the same "
             "**about** box checked for the change your selection touches (**about N changes** when it touches several); "
             "uncheck it for a plain comment on the passage.")
ANSWERED = "A comment an older session's edit answered wears **answered by a change** instead."
SEND = ("the comments and replies you wrote since the last send, each with what it refers to, the changes it is about, and "
        "the commands the session needs to answer it.")
RESOLVE = ("Nothing resolves a comment but you: **Resolve** on its card, or **Resolve answered (N)** in the panel's header, "
           "shown once the session has replied to N of your open comments since you last wrote on them (a revision counts as a "
           "reply), which resolves those N after a plain confirm and offers **Reopen all** where the sent acknowledgment stands "
           "until your next scroll, click, tap, or key.")


class TheSentences(unittest.TestCase):
    def setUp(self):
        self.section = _flat(_section(_read("docs", "guide.md"), "Files"))
        self.track = _paragraph(_section(_read("docs", "guide.md"), "Files"), "**Track changes**")
        self.panel = _read("ui", "webview", "file-comments.ts")
        self.model = _read("ui", "webview", "file-comments-model.ts")
        self.host = _read("tools", "file-comments-host.mjs")

    def test_the_track_changes_paragraph_carries_the_about_sentences_in_order(self):
        for s in (COMMENT_ON, OWN_CARD, SELECTION, ANSWERED):
            self.assertIn(s, self.track)
        self.assertLess(self.track.index(COMMENT_ON), self.track.index(OWN_CARD))
        self.assertLess(self.track.index(OWN_CARD), self.track.index(SELECTION))
        self.assertLess(self.track.index(SELECTION), self.track.index(ANSWERED))
        self.assertIn(SEND, self.section)
        self.assertIn(RESOLVE, self.section)

    def test_the_sentences_keep_the_persons_words(self):
        for s in (COMMENT_ON, OWN_CARD, SELECTION, ANSWERED, SEND, RESOLVE):
            self.assertNotRegex(s, r"\b(suggestion|thread|bound to|linked|hosted|romp|card model|sidecar)\b", s)

    def test_comment_on_this_change_is_the_change_cards_button_and_writes_the_ids(self):
        self.assertIn('btn("Comment on this change", "fcchangecomment")', self.panel)
        self.assertIn("startChangeComment(id: string): void {", self.panel)
        self.assertIn('about: { ids: [id], on: true, only: false }', self.panel, "over the change's span, the option checked")
        self.assertIn('about: { ids: [id], on: true, only: true }', self.panel, "a deletion: the change alone")
        self.assertIn("if (c.about && c.about.on) args.changeIds = c.about.ids;", self.panel, "Save carries the ids")
        self.assertIn("export function aboutOptionLabel(n: number): string {", self.model)
        self.assertIn('return n === 1 ? "about this change" : "about " + n + " changes";', self.model)
        self.assertIn("The removed text is not in the file, so the comment is laid at the change's point.", self.panel)
        # the host stores the ids and the message names the change
        self.assertIn("function readChangeIds(args) {", self.host)
        self.assertIn('return parts.length ? "about " + listWords(parts) : null;', self.model, "the message's about clause")

    def test_every_comment_is_its_own_card_with_the_tags_both_ways(self):
        self.assertNotIn("renderHosted", self.panel)
        self.assertNotIn("fc-hosted", self.panel)
        self.assertIn('const cards = filter === "changes" ? [] : this.cards();', self.panel, "every comment's card under All and Comments")
        self.assertIn('el("span", "fc-tag fc-about", aboutTagWords(refs.length, source))', self.panel, "the comment's tag")
        self.assertIn('return n === 1 ? "about a change" : "about " + n + " changes";', self.model)
        self.assertIn('t.addEventListener("pointerenter", () => this.lightChanges(pending, true));', self.panel, "hover rings the marks")
        self.assertIn('m.classList.toggle("fc-lit", on);', self.panel)
        self.assertIn('c.comments + (c.comments === 1 ? " comment" : " comments")', self.panel, "the change card's count")
        self.assertIn('t.dataset.act = "fcaboutfirst";', self.panel)
        self.assertIn("const first = commentsAbout(this.cards(), changeId)[0];", self.panel, "the click shows the first")
        for sheet in ("styles.css", "feed.css"):
            css = _read("ui", "webview", sheet)
            self.assertIn(".fc-ins.fc-lit, .fc-del.fc-lit::before { outline: 2px solid var(--accent);", css, sheet + ": the ring")
            self.assertNotIn(".fc-hosted", css, sheet)

    def test_a_selection_inside_a_change_is_an_ordinary_comment_with_the_option(self):
        self.assertIn("private overlapping(range: SourceRange): string[] {", self.panel)
        self.assertIn("const ids = this.overlapping(res.range);", self.panel)
        self.assertIn("...(ids.length ? { about: { ids, on: true, only: false } } : {})", self.panel, "the option only when a change is under the selection")
        self.assertIn('else if (k === "about") { const c = this.composer; if (c && c.kind === "comment" && c.about) c.about.on = t.checked; return; }', self.panel, "unchecked: a plain comment")

    def test_the_answered_tag_reads_a_legacy_binding(self):
        self.assertIn('if (source === "answered") return n === 1 ? "answered by a change" : "answered by " + n + " changes";', self.model)
        self.assertIn('out.push({ id: String(a), source: "answered" });', self.model, "refIds reads suggestionId as answered")
        self.assertIn("suggestionId is not accepted: a comment names the changes it is about with changeIds", self.host, "and the host never writes one")

    def test_resolve_answered_is_the_persons_and_the_only_bulk_resolve(self):
        self.assertIn("export function answeredComments(", self.model)
        self.assertIn('return "Resolve answered (" + n + ")";', self.model, "the header action's words")
        self.assertIn('return "Resolve the " + plural(n, "comment", "comments") + " the session has answered?";', self.model, "the confirm's one line")
        self.assertIn("resolveAnsweredLabel(answered.length)", self.panel)
        self.assertIn('btn("Reopen all", "fcreopenall"', self.panel)
        self.assertIn("const undo = this.reopenAll !== null && !on(\"fcreopenall\");", self.panel, "the offer ends at the next gesture")
        self.assertNotIn("resolved = true", self.host.replace("resolved: false", ""), "the host resolves nothing on its own: doResolve alone writes resolved")
