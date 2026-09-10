#!/usr/bin/env python3
"""The romp harness prompt (claude/romp-session-prompt.md) is appended to EVERY session's system prompt
(tmux via --append-system-prompt, SDK via the designed system_prompt field). It must keep its EXPLICIT
done/not-done reporting instruction, so a session never reports — and the closer never marks — partial
work as complete (the user 2026-06-26: things were getting marked completed that weren't). These pin the
load-bearing intent so a future "make it lighter" edit can't quietly drop it."""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
PROMPT = os.path.join(os.path.dirname(HERE), "claude", "romp-session-prompt.md")


class SessionPrompt(unittest.TestCase):
    def setUp(self):
        with open(PROMPT) as f:
            self.text = f.read()
        # collapse line wraps so phrase matches survive prose reflow
        self.flat = re.sub(r"\s+", " ", self.text).lower()

    def test_requires_an_explicit_not_done_account(self):
        # not just "say when done" — the NOT-done side must be called out as explicitly as the done side
        self.assertIn("not done", self.flat,
                      "the prompt must require an explicit account of what is NOT done, not only 'done'")

    def test_asks_for_a_bulleted_done_notdone_list(self):
        # the user's ask: a clear, direct, bulleted Done / Not done list when there's a mix
        self.assertRegex(self.flat, r"done\s*/\s*not done",
                         "the prompt must ask for a bulleted Done / Not done list")

    def test_forbids_implying_completion_while_work_remains(self):
        # the anti-false-completion rule that protects against the closer marking partial work complete
        self.assertIn("while pieces remain", self.flat,
                      "the prompt must forbid stating/implying a task is complete while pieces remain")

    def test_preliminary_step_is_not_the_work(self):
        # reading/mapping/planning a refactor is not doing it (the g405 false-completion pattern)
        self.assertIn("preliminary step", self.flat,
                      "the prompt must say a preliminary step (reading/mapping/planning) is not finishing the work")

    def test_file_mentions_carry_a_locating_path(self):
        # A bare basename in a session's prose is an ambiguous (or dead) reference outside that
        # session's own context — the user 2026-08-09, after clicking a `render.js` mention that could
        # not resolve. The prompt asks for working-directory-relative or absolute paths. This is the
        # NUDGE half; the kernel-side link resolver is the mechanism that verifies what actually gets
        # linked — this line just shrinks the ambiguous residue the resolver refuses to guess about.
        self.assertIn("relative to the working", self.flat,
                      "the prompt must ask for paths that locate the file, not bare names")
        self.assertIn("bare name", self.flat,
                      "the prompt must name the failure mode (a bare basename) it steers away from")
    def test_licenses_persisting_through_daunting_work(self):
        # the user 2026-08-11 (after Anthropic's riemann-zeta post, where the operator's whole input was
        # keep-going encouragement): the prompt must license continuing on work that merely LOOKS too big
        # or uncertain — stopping is reserved for decisions that are genuinely the user's to make.
        self.assertIn("talk yourself out of", self.flat,
                      "the prompt must tell the session not to abandon work that merely looks daunting")
        self.assertIn("make progress", self.flat,
                      "the prompt must license taking any visible path to progress without checking in")

    def test_a_look_at_a_file_goes_through_the_tools_file_argument(self):
        # The todo-file follow-on (2026-09-07): a session that wants the user to look at a file
        # passes the file's absolute path as add_user_todo's `file` argument — the structured
        # field the todo shows and the user's comments on that file answer — rather than only
        # naming the path in the detail (the detail may still describe it). The sentence stays in
        # Working style, conditional on the tool (the User todos switch gates it), and speaks as
        # the person: no romp nouns, nothing the agent cannot see.
        working, housekeeping = self.text.split("# Housekeeping", 1)
        flat = re.sub(r"\s+", " ", working).lower()
        self.assertIn("flag it with `add_user_todo` if you have that tool", flat)
        self.assertIn("absolute path as its `file` argument", flat,
                      "the file's absolute path goes in the `file` argument, not only the detail")
        self.assertIn("absolute path in the detail, which can still describe it", flat,
                      "the detail keeps its descriptive role; the path there is no longer the mechanism")
        self.assertIn("my comments", flat, "says what comes back: the person's comments")
        # a look at a web page (the user 2026-09-08): the address goes in the `link` argument the same way, and the
        # fallback names the address too; pinned since the 2026-09-09 review (a drifted argument name would file the
        # todo with its address silently dropped: the schema restricts no extra property)
        self.assertIn("its address as the `link` argument the same way", flat)
        self.assertIn("if you don't have the tool", flat, "the fallback when the switch is off")
        self.assertIn("name the file or the address", flat, "the fallback names the address as well as the file")
        self.assertNotIn("add_user_todo", housekeeping, "Housekeeping explains romp's artifacts only")
        for word in ("romp", "card", "board", "goal", "nudge", "cleared", "dismissal", "status check",
                     "viewer", "panel", "dashboard", "pane", "chip", "todo id", "waiting on you"):
            self.assertNotIn(word, flat, "%r names machinery the agent cannot see" % word)

    def test_asks_sessions_to_commit_the_comments_folder_with_their_work(self):
        # The owner found that his sessions never added `.trackchanges/` to git, so the comments on
        # their files and the record of their tracked changes were not archived with the work
        # (2026-09-10; plans/file-review.md decision 48). One sentence in Working style, in the
        # person's voice, conditional on the project having the folder and not ignoring it: the
        # person's own commits stay theirs, and nothing on the host stages or commits (decision 25).
        # It names the folder and nothing else of the machinery. The vendored skill carries the
        # same rule (vendor/track-changents/patches/0007).
        working, housekeeping = self.text.split("# Housekeeping", 1)
        flat = re.sub(r"\s+", " ", working).lower()
        self.assertIn("when you commit work in a project that has a `.trackchanges/` folder and does not ignore it, "
                      "include that folder in the commit", flat)
        self.assertIn("it holds my comments on your files and the record of your tracked changes", flat,
                      "says why, in the person's voice: their comments, the session's tracked changes")
        self.assertNotIn(".trackchanges", housekeeping, "Housekeeping explains romp's artifacts only")
        for word in ("romp", "card", "board", "goal", "nudge", "sidecar", "comments log", "panel", "dashboard"):
            self.assertNotIn(word, flat, "%r names machinery the agent cannot see" % word)

    def test_housekeeping_note_preexplains_romp_artifacts(self):
        # The ONE place romp is named to a session (the user 2026-07-25): pre-explain the artifacts
        # every session eventually sees — [romp] notices and <!-- romp-* --> comments — so a kernel
        # restart notice reads as explained information, not an unexplained system voice.
        self.assertIn("romp", self.flat,
                      "the housekeeping note must name romp so its artifacts have an anchor")
        self.assertIn("[romp]", self.text, "the note must show the bracketed-notice form")
        self.assertIn("<!-- romp-", self.text, "the note must show the HTML-comment form")
        self.assertIn("ignore", self.flat,
                      "the note must tell the session to ignore the bookkeeping")


if __name__ == "__main__":
    unittest.main()
