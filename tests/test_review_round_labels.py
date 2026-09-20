#!/usr/bin/env python3
"""The review-round labels in the lazy-panes surfaces name rounds the reviewer held (the author's pass 7, 2026-09-20).

Two numberings meet in this branch's comments and test prose. The REVIEWER's rounds on the lazy-panes PR are the
rulings files in the review notes, numbered 1 to REVIEWER_ROUNDS below; the AUTHOR's passes are the builds between
them (1, 2, 3, 4, 4b, 5, 6, 7), each with its own verify. An early convention labelled the author's passes as
"review round N", so a "review round 3" in this branch's added lines is the author's pass 3, which took the
reviewer's round 2; the PR body's convention paragraph glosses those, and the labels numbered 1 to 4 stand under
that gloss. The labels that named what the reviewer never held were reworded in pass 7 (the reviewer's round-5
ruling, correctness-4 and extra7-4: a record crediting a reviewer with the author's work): the author's pass 4b
labelled a review round, the author's verifiers labelled "review round N verify", and the author's passes 5 and 6
labelled review rounds 5 and 6 while citing the reviewer's round-4 findings. Each reads now as the author's pass
with the reviewer's round named where a ruling exists.

This module is the ratchet: over the files the lazy-panes branch touched (FILES; every file the branch added or
changed whose review-round mentions are all its own), no label names a round the reviewer never held. Three
forms are refused: a "review round" numbered above REVIEWER_ROUNDS, a lettered round (the author's pass 4b, however
spelled, is a pass), and a verify labelled as a round (a verify is the author's verifier, never a review
round). A bare "round N" without the word "review" is not read as a label: files this branch touched carry other
work's bare "round 6" (a July design's iteration count, another change's own rounds), so only the "review round"
spelling carries the numeric rule. kernel/kernel.py, ui/webview/render.ts and tests/test_error_center.py are not
in FILES because they carry other work's review rounds 6 and 7; kernel.py is held instead through the `[fork]`
tag every lazy-panes comment there that names a round carries (FORK_TAGGED: the tag's lines alone are read, and
origin/main's own `[fork]` lines name no such round). The branch's untagged kernel.py comments are outside the
ratchet, a residual named here rather than pinned by a count that another change's comment would move.

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
FORK_TAGGED = ["kernel/kernel.py"]   # read through the `[fork]` tag alone
TAG = "[fork]"

# a label: "review round N", "round N", either with an optional letter and an optional "verify" after the number
LABEL = re.compile(r"\b(review )?round[- ]?(\d+)([a-z])?\b(\s+verify)?", re.I)


def offences(text):
    """(line number, the label, why) for every label in `text` that names a round the reviewer never held."""
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        for m in LABEL.finditer(line):
            review, n, letter, verify = m.group(1), int(m.group(2)), m.group(3), m.group(4)
            if letter:
                out.append((i, m.group(0), "a lettered round is an author's pass"))
            elif verify:
                out.append((i, m.group(0), "a verify is the author's verifier, never a review round"))
            elif review and n > REVIEWER_ROUNDS:
                out.append((i, m.group(0), "the reviewer held rounds 1 to %d" % REVIEWER_ROUNDS))
    return out


def labels(text):
    return [m.group(0) for m in LABEL.finditer(text)]


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class ReviewRoundLabels(unittest.TestCase):
    def test_every_listed_file_exists(self):
        missing = [f for f in FILES + FORK_TAGGED if not os.path.isfile(os.path.join(ROOT, f))]
        self.assertEqual(missing, [], "a listed file moved: re-list it (a missing file must not read as clean)")

    def test_no_label_names_a_round_the_reviewer_never_held(self):
        bad, seen = [], 0
        for rel in FILES:
            text = _read(rel)
            seen += len(labels(text))
            bad += ["%s:%d: %r (%s)" % (rel, ln, label, why) for ln, label, why in offences(text)]
        for rel in FORK_TAGGED:
            tagged = "\n".join(l if TAG in l else "" for l in _read(rel).split("\n"))
            seen += len(labels(tagged))
            bad += ["%s:%d: %r (%s; a [fork]-tagged line)" % (rel, ln, label, why) for ln, label, why in offences(tagged)]
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


if __name__ == "__main__":
    unittest.main()
