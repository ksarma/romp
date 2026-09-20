#!/usr/bin/env python3
"""The review-round labels in the lazy-panes surfaces name rounds the reviewer held (the author's pass 7, 2026-09-20).

Two numberings meet in this branch's comments and test prose. The REVIEWER's rounds on the lazy-panes PR are the
rulings files in the review notes, numbered 1 to REVIEWER_ROUNDS below; the AUTHOR's passes are the builds between
them (1, 2, 3, 4, 4b, 5, 6, 7), each with its own verify. An early convention labelled the author's passes as
"review round N", so a "review round 3" in this branch's added lines is the author's pass 3, which took the
reviewer's round 2; the PR body's convention paragraph glosses those, and the labels numbered 1 to 4 stand under
that gloss. The labels that named what the reviewer never held were reworded in pass 7 (the reviewer's round-5
ruling, correctness-4 and extra7-4: a record crediting a reviewer with the author's work): the author's pass 4b
labelled a review round, the author's verifiers labelled "review round N verify" (eight in test prose by the pass's
build, three in kernel.py's pane-loader comments by the pass's verify fixer), and the author's passes 5 and 6
labelled review rounds 5 and 6 while citing the reviewer's round-4 findings. Each reads now as the author's pass
with the reviewer's round named where a ruling exists.

This module is the ratchet. Three forms are refused: a "review round" numbered above REVIEWER_ROUNDS, a lettered
round (the author's pass 4b, however spelled, is a pass), and a verify labelled as a round (a verify is the author's
verifier, never a review round). A bare "round N" without the word "review" is not read as a label: files this
branch touched carry other work's bare "round 6" (a July design's iteration count, another change's own rounds), so
only the "review round" spelling carries the numeric rule.

FILES, the files the lazy-panes branch added or changed (its diff against the merge base with main) minus the three
named below, are read whole, every label in them. They are not all the branch's own: eleven of them carried labels
this module reads at the merge base (tests/test_pane_shim_return.py 19, tests/test_kernel_mobile.py 16 and
ui/webview/file-view.test.ts 77 among them, other changes' labels), none of a refused form. So the census is green
over them today and reds on a refused form another change writes into a listed file; that change answers it by
naming its author's pass, by raising REVIEWER_ROUNDS when the reviewer did hold that round on THIS PR, or by taking
its file out of FILES with a note here.

kernel/kernel.py, ui/webview/render.ts and tests/test_error_center.py are not in FILES because they carry other
work's review rounds numbered past REVIEWER_ROUNDS (kernel.py: 50 lines naming rounds from six to thirteen at the
pass-7 fixer's head 034c88ef9, every one on main and none in the project's copy). kernel.py is read two ways
(KERNEL). The VERIFY rule reads every line of it: no file on main or in the project writes "round N verify" as a
label (`git grep -il 'round[- ]\?[0-9]\+ verify'` over origin/main and over upstream/main: no file), so the
whole-file read costs no other change anything, and it is the form that slipped the tag-scoped read (the three
pane-loader comments above, found by the pass-7 verify). The NUMERIC and LETTERED rules read the `[fork]`-tagged
lines alone (main's own `[fork]` lines name no such round): other work's numeric labels are the 50 lines above, and
other work writes a lettered review round (a letter after the number) in four files on main, so a whole-file read
of either form would need an allowlist of other work's lines that every fold could move. The residual, stated
rather than pinned: at 034c88ef9, 42 branch-added kernel.py lines name a review round, 11 tagged and 31 not
(derived by git against origin/main; none refused), and a new UNTAGGED numeric or lettered label in kernel.py
passes this census. The pass-7 verify executed that hole with an untagged line naming a sixth review round; the
verify rule closes its own form only.

When the reviewer holds a sixth round on this PR, raise REVIEWER_ROUNDS; a label naming it is then a real round.
When a listed file is renamed, re-list it: a missing file is a red, not a skip.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

REVIEWER_ROUNDS = 5   # the rulings files of the lazy-panes review: rounds 1 to 5 (2026-09-19 to 2026-09-20)

# The files the lazy-panes branch added or changed (its diff against the merge base with main), minus the three named
# in the module docstring; every review-round mention in them is the branch's own.
FILES = [
    "docs/read-side.md",
    "tests/lazy_pane_layout_flip_browser.mjs",
    "tests/pane_hidden_word_browser.js",
    "tests/return_from_background_browser.mjs",
    "tests/test_chat_skeleton_reconnect.py",
    "tests/test_client_diag_allowlist.py",
    "tests/test_federated_dial_terms_served.py",
    "tests/test_files_pane.py",
    "tests/test_files_pane_toggle_served.py",
    "tests/test_kernel_mobile.py",
    "tests/test_kernel_pane_rail.py",
    "tests/test_kernel_webpush.py",
    "tests/test_lazy_pane_layout_flip_served.py",
    "tests/test_notification_tap_resume_browser.py",
    "tests/test_pane_hidden_word_browser.py",
    "tests/test_pane_loader_reconnect.py",
    "tests/test_pane_shim_return.py",
    "tests/test_pane_state_broadcast.py",
    "tests/test_return_from_background_served.py",
    "tests/test_review_round_labels.py",
    "tests/test_settings_page.py",
    "tests/test_shell_reveal_unhide.py",
    "tests/test_waiting_pane.py",
    "ui/webview/chat-split-exec.test.ts",
    "ui/webview/chat-visibility.test.ts",
    "ui/webview/chat-visibility.ts",
    "ui/webview/federation-hidden-hold.test.ts",
    "ui/webview/federation-remote-dial.test.ts",
    "ui/webview/feed-age.test.ts",
    "ui/webview/feed-focus-local-switch.test.ts",
    "ui/webview/feed-followup-move.test.ts",
    "ui/webview/feed-freeze.test.ts",
    "ui/webview/feed-hidden-paint.test.ts",
    "ui/webview/feed-session-filter.test.ts",
    "ui/webview/feed.ts",
    "ui/webview/file-view.test.ts",
    "ui/webview/follow-move-cache-echo.test.ts",
    "ui/webview/notify-click-reveal.test.ts",
    "ui/webview/paint-gate.test.ts",
    "ui/webview/paint-gate.ts",
    "ui/webview/pane-focus.test.ts",
    "ui/webview/render-link-word.test.ts",
    "ui/webview/skeleton-tabs-wiring.test.ts",
    "ui/webview/skeleton-tabs.test.ts",
    "ui/webview/skeleton-tabs.ts",
    "upstream/2026-09-18-lazy-panes-phone-skeleton-dial.md",
    "upstream/2026-09-20-lazy-panes-upstream-line-offers.md",
]
KERNEL = ["kernel/kernel.py"]   # every rule over the `[fork]` tag's lines; the verify rule over every line (the module docstring)
TAG = "[fork]"
FORMS = ("letter", "verify", "number")   # the three refused forms, the rules offences() applies

# a label: "review round N", "round N", either with an optional letter and an optional "verify" after the number
LABEL = re.compile(r"\b(review )?round[- ]?(\d+)([a-z])?\b(\s+verify)?", re.I)


def offences(text, forms=FORMS):
    """(line number, the label, why) for every label in `text` that names a round the reviewer never held, under the
    rules named in `forms` (every rule by default; kernel.py's untagged lines are read under the verify rule alone)."""
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        for m in LABEL.finditer(line):
            review, n, letter, verify = m.group(1), int(m.group(2)), m.group(3), m.group(4)
            if letter and "letter" in forms:
                out.append((i, m.group(0), "a lettered round is an author's pass"))
            elif verify and "verify" in forms:
                out.append((i, m.group(0), "a verify is the author's verifier, never a review round"))
            elif review and n > REVIEWER_ROUNDS and "number" in forms:
                out.append((i, m.group(0), "the reviewer held rounds 1 to %d" % REVIEWER_ROUNDS))
    return out


def labels(text):
    return [m.group(0) for m in LABEL.finditer(text)]


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class ReviewRoundLabels(unittest.TestCase):
    def test_every_listed_file_exists(self):
        missing = [f for f in FILES + KERNEL if not os.path.isfile(os.path.join(ROOT, f))]
        self.assertEqual(missing, [], "a listed file moved: re-list it (a missing file must not read as clean)")

    def test_no_label_names_a_round_the_reviewer_never_held(self):
        bad, seen = [], 0
        for rel in FILES:
            text = _read(rel)
            seen += len(labels(text))
            bad += ["%s:%d: %r (%s)" % (rel, ln, label, why) for ln, label, why in offences(text)]
        for rel in KERNEL:
            lines = _read(rel).split("\n")
            tagged = "\n".join(l if TAG in l else "" for l in lines)       # line numbers kept: a blank stands in for every other line
            untagged = "\n".join("" if TAG in l else l for l in lines)
            seen += len(labels(tagged))
            bad += ["%s:%d: %r (%s; a [fork]-tagged line)" % (rel, ln, label, why) for ln, label, why in offences(tagged)]
            bad += ["%s:%d: %r (%s; an untagged line, which the verify rule reads whole-file)" % (rel, ln, label, why)
                    for ln, label, why in offences(untagged, forms=("verify",))]
        self.assertGreater(seen, 0, "the census read no label at all: the pattern or the file list is broken")
        self.assertEqual(bad, [], "a label names a round the reviewer never held on this PR; write the author's pass (\"pass N, the author's "
                                  "label\") with the reviewer's round named where a ruling exists, or raise REVIEWER_ROUNDS for a round the "
                                  "reviewer did hold:\n" + "\n".join(bad))

    def test_the_form_space(self):
        """The classifier over the label shapes the branch wrote, so the census is known to read them."""
        # the probes are assembled at run time: this module is in FILES and reads itself, so a spelled-out refused form here
        # would be the census's one red
        R, V = "round", "verify"
        red = ["review %s 6" % R, "Review %s 7 (2026-09-21)" % R, "review %s 4b" % R, "%s 4b of the lazy panes" % R, "since %s-4b" % R,
               "review %s 5 %s" % (R, V), "the %s-5 %s" % (R, V), "review %s 4 %s:" % (R, V), "%s 6 %s" % (R, V)]
        green = ["review %s 5" % R, "the reviewer's %s-4 finding" % R, "pass 5, the author's label", "the author's pass-5 %s" % V,
                 "%ss 1 to 5" % R, "a%s 6" % R, "backg%s 6" % R, "%s 6" % R, "(%s 6: a parked request)" % R, "%s-trip" % R,
                 "the %s-3 fixlist's" % R, "REVIEWER_ROUNDS = 5"]
        self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
        self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        self.assertEqual(labels("review %s 5 %s and %s 4b" % (R, V, R)), ["review %s 5 %s" % (R, V), "%s 4b" % R])
        # kernel.py's untagged lines are read under the verify rule alone: it refuses the verify form in either spelling and
        # reads a numeric or lettered label as clean (those two rules are the tag's)
        self.assertTrue(offences("review %s 4 %s:" % (R, V), forms=("verify",)), "the verify rule alone missed a verify label")
        self.assertTrue(offences("%s 6 %s" % (R, V), forms=("verify",)), "the verify rule alone missed a bare-round verify label")
        self.assertEqual(offences("review %s 6" % R, forms=("verify",)), [], "the verify rule read a numeric label")
        self.assertEqual(offences("review %s 4b" % R, forms=("verify",)), [], "the verify rule read a lettered label")


if __name__ == "__main__":
    unittest.main()
