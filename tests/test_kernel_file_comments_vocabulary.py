#!/usr/bin/env python3
"""The kernel's comments-log code speaks CONTEXT.md's vocabulary for the decisions it traces
(plans/file-review.md, Slice 5; the review of 2026-09-06).

The `save` verb carries the decisions taken in the editor — `accepted` and `rejected`, each
{id, oldText, newText} (plans/file-review.md, Slice 5) — and the host writes them into the comments
log. CONTEXT.md lists "ledger" under _Avoid_ for the comments log, and the editor chunk's contract
was renamed to `decisions` for that reason (ui/webview/editor-chunk-decisions.test.ts), but the
kernel's save trace and its file-comments door kept calling the same lists a ledger — nine times
across the docstrings of _save_trace, _file_comments_call and _file_comments_after, and once as a
local — so a reader of a save trace met "the ledger" and "the log" side by side for one set of
decisions, told apart only by the word the glossary bans for one of them. The kernel now says
`decisions`, the plan's word, or names the field (`rejected`).

This file pins it. The avoid-words are read from CONTEXT.md's Comments log entry rather than
hard-coded, so a new avoid-word fails here too; the scan covers the kernel's whole comments-log
region — the trace functions and every _file_comments_* function — and checks that region holds
every such function, so a reordering widens the scan instead of silently shrinking it. The kernel's
OTHER ledgers (the Fleet pane's per-session goal ledgers, the restart-cut ledger) are a different
thing and are outside the region on purpose. Synthetic: only the repo's own text.
"""
import os
import re
import unittest

from tests.test_guide_waiting_on_you_hidden_todos import _avoid_words

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


KERNEL = _read("kernel", "kernel.py")
FIRST, LAST = "_edit_trace_sid", "_file_comments_after"
# every def the comments-log code consists of: the three traces (their bodies, sids and senders) and
# the file-comments door, from the node lookup to what follows a reply
COMMENTS_LOG_DEFS = re.compile(r"^def (_file_comments\w*|_(?:edit|reject|save)_trace(?:_\w+)?)\(", re.M)


def _region():
    """The kernel source from `def FIRST(` to the first column-0 line after `def LAST(` — the
    comments-log code as one contiguous span — with the 1-based line number it starts on."""
    start = KERNEL.index("\ndef %s(" % FIRST) + 1
    last = KERNEL.index("\ndef %s(" % LAST) + 1
    m = re.compile(r"^\S", re.M).search(KERNEL, KERNEL.index("\n", last) + 1)
    end = m.start() if m else len(KERNEL)
    return KERNEL[start:end], KERNEL[:start].count("\n") + 1, start, end


def _func(region, name):
    """One function's source out of the region: its def line to the next top-level line."""
    start = region.index("\ndef %s(" % name) + 1
    m = re.compile(r"^\S", re.M).search(region, region.index("\n", start) + 1)
    return region[start:m.start() if m else len(region)]


class CommentsLogVocabulary(unittest.TestCase):
    """The kernel's comments-log code uses none of the words CONTEXT.md avoids for the comments log."""

    @classmethod
    def setUpClass(cls):
        cls.avoid = _avoid_words(_read("CONTEXT.md"), "Comments log")
        cls.region, cls.first_line, cls.start, cls.end = _region()

    def test_context_md_lists_the_word_under_avoid_for_the_comments_log(self):
        # The premise, checked against its source: if CONTEXT.md drops "ledger" from the avoid list
        # the scan below is no longer the glossary's rule, and this says so before that one passes vacuously.
        self.assertIn("ledger", self.avoid)

    def test_region_holds_every_comments_log_function(self):
        # The scan is a contiguous span; every def the comments-log code consists of must lie inside it,
        # so a function moved past _file_comments_after fails here instead of escaping the scan.
        outside = [m.group(1) for m in COMMENTS_LOG_DEFS.finditer(KERNEL)
                   if not (self.start <= m.start() < self.end)]
        self.assertEqual(outside, [], "comments-log functions outside the scanned region %s..%s; widen FIRST/LAST"
                         % (FIRST, LAST))
        for name in ("_save_trace_body", "_save_trace", "_file_comments_call", "_file_comments_message",
                     "_file_comments_after"):
            self.assertIn("\ndef %s(" % name, self.region)

    def test_comments_log_code_uses_no_avoided_word(self):
        # Single-word entries only: a phrase like "log alone" names a usage, not a token, and the
        # region says "the comments log" where it means the log (CONTEXT.md's own spelling).
        words = [w for w in self.avoid if " " not in w]
        self.assertTrue(words)
        hits = []
        for i, line in enumerate(self.region.split("\n")):
            for word in words:
                if re.search(r"(?i)\b%s\b" % re.escape(word), line):
                    hits.append("kernel/kernel.py:%d says %r (CONTEXT.md, Comments log, Avoid): %s"
                                % (self.first_line + i, word, line.strip()))
        self.assertEqual(hits, [])

    def test_save_path_calls_the_lists_decisions(self):
        # The plan's word, positively: the trace and the after-hook describe the save's `rejected` as
        # decisions, and the local that counts them is spelled the same way.
        for name in ("_save_trace", "_file_comments_call", "_file_comments_after"):
            self.assertRegex(_func(self.region, name), r"\bdecisions\b", name)
        after = _func(self.region, "_file_comments_after")
        self.assertIn('decisions = args.get("rejected")', after)
        self.assertIn("len(decisions) if isinstance(decisions, list) else 0", after)


if __name__ == "__main__":
    unittest.main()
