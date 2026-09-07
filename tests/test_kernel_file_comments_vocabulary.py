#!/usr/bin/env python3
"""File comments (plans/file-review.md) — the kernel's file-comments code speaks CONTEXT.md's words.

CONTEXT.md's File comment entry lists "thread" under Avoid: in this codebase a comment thread is a
forked side session anchored to the chat (kernel.py's _comment_thread and the comment-thread section),
so a file comment called a thread reads as a side session. The webview holds file-comments.ts and
file-comments-model.ts to that rule (ui/webview/file-comments.test.ts, "vocabulary and privacy"), and
the guide's Files section is checked against the entry's Avoid list (tests/test_guide_files_comments_log.py);
nothing read the kernel, and the send builder's docstring described the retired zero-comments message as
a pointer at "a thread that does not exist" (the review, 2026-09-06). This module reads kernel/kernel.py
as TEXT — no kernel import, so no state root and no side effects — and holds the FILE COMMENTS section to
the same rule: the only "thread" is the `--thread` CLI flag (the format's word, which plans/file-review.md
keeps), except inside the functions where the word is the stdlib's and means a Python thread.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
KERNEL = os.path.join(REPO, "kernel", "kernel.py")

# The section: its header comment through the last direct-edit log function, up to the git helpers
# that follow it. A moved header or a renamed neighbour fails loudly in setUpClass rather than
# shrinking the scan to nothing.
SECTION_START = "# ---- FILE COMMENTS ("
SECTION_END = "\ndef _git_out("
# The functions whose "thread" is a Python thread (a threading.Thread per frame, the reply on its own
# thread). Listed by name so a new function in the section is scanned by default; a stale name fails.
PYTHON_THREAD = ("_file_comments_call", "_file_comments_reply")
# "thread" as a word, but not the `--thread` flag: the "-" before it is the format's own spelling.
BARE_THREAD = re.compile(r"(?<!-)\bthreads?\b", re.I)
OTHER_AVOID = re.compile(r"\b(suggestion|annotation)s?\b", re.I)


def _blocks(section):
    """{name: text} for the header comment ("header") and each top-level def in the section."""
    out, name, buf = {}, "header", []
    for line in section.split("\n"):
        m = re.match(r"def (\w+)\(", line)
        if m:
            out[name] = "\n".join(buf)
            name, buf = m.group(1), []
        buf.append(line)
    out[name] = "\n".join(buf)
    return out


def _hits(pattern, text):
    return ["%d: %s" % (i + 1, l.strip()) for i, l in enumerate(text.split("\n")) if pattern.search(l)]


class TheFileCommentsSectionSpeaksTheEntrysWords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(KERNEL, encoding="utf-8") as f:
            text = f.read()
        start = text.index(SECTION_START)
        end = text.index(SECTION_END, start)
        cls.section = text[start:end]
        cls.blocks = _blocks(cls.section)

    def test_the_only_thread_is_the_cli_flag(self):
        # the send builder's docstring, the send op, the message's command lines, the header, every helper:
        # `--thread <id>` may appear (the format's flag); "thread" as the noun for a file comment may not
        for name, text in self.blocks.items():
            if name in PYTHON_THREAD:
                continue
            self.assertEqual(_hits(BARE_THREAD, text), [],
                             "%s: a file comment is a file comment, never a thread (CONTEXT.md, File comment); "
                             "a comment thread is a forked side session" % name)
        self.assertIn("--thread <id>", self.blocks["_file_comments_message"], "the flag itself stays")

    def test_the_python_thread_allowlist_names_functions_that_exist_and_use_the_word(self):
        # so the allowlist cannot go stale (a renamed function would otherwise leave a name that excludes
        # nothing) and cannot grow past need (an entry that never says "thread" is a hole, not an exemption)
        for name in PYTHON_THREAD:
            self.assertIn(name, self.blocks, name)
            self.assertTrue(_hits(BARE_THREAD, self.blocks[name]), "%s no longer says thread: drop it from the list" % name)
        self.assertIn("threading.Thread(", self.blocks["_file_comments_reply"])

    def test_no_other_avoid_word_of_the_entry(self):
        # the format's "suggestion" for a change and "annotation" for a comment: the webview guard's pair
        self.assertEqual(_hits(OTHER_AVOID, self.section), [])

    def test_the_section_uses_the_entrys_terms(self):
        # positive side, as the webview guard checks the guide's phrases: CONTEXT.md's own nouns are the ones in use
        for phrase in ("comments log", "direct edit", "Send to session"):
            self.assertIn(phrase, self.section, phrase)


if __name__ == "__main__":
    unittest.main()
