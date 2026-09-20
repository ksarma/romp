#!/usr/bin/env python3
"""No bats test may negate a command with a bare `!` unless that is the test's LAST command.

bats runs a test body under `set -e` with an ERR trap, and bash exempts an inverted command from
both, so `! grep -q x "$LOG"` followed by another command checks nothing: the test passes whether
or not the log contains x. As the last command it IS checked, because bats reads the test
function's return status. That is why last-line sites work, and why they stop checking anything
the moment someone appends an assertion after them. PR #383 armed nineteen such sites by hand and
PR #403 one more; within a month three new ones had arrived, one each in tests/romp-headless.bats
(c2a5f844), tests/tmux-status-hook.bats (e0d76b85) and tests/romp.bats (989854c6), each asserting
nothing. This module is the ratchet those hand fixes lacked: the suite test scans every
tests/*.bats and names each inert site, and the Scanner tests pin the scanner itself on synthetic
snippets.

The checked form is `run <cmd>` followed by `[ "$status" -ne 0 ]` (tests/romp-postal.bats and
tests/git-hermetic.bats write it inline; the `log_lacks` helper that wrapped it left with
tests/romp-manager-tmux-scope.bats when the tmux backend was removed, 2532d6d8 on 2026-09-11), a count for a pipeline (`[ "$(grep -c x "$LOG")" -eq 0 ]`),
or `run ! <cmd>` in a file that declares `bats_require_minimum_version 1.5.0`. `run` overwrites $status and
$output, so an armed negation goes after any `[[ "$output" ... ]]` check that reads the previous run.

Scope: a line scan, not a bash parser. Inside a `@test ... {` block it reads every line that begins
with `! ` and reports one whose next non-blank, non-comment line is not the block's closing `}`. It
does not see `!cmd` written without a space, a `! cmd` sharing a line with another command, a
bare `!` inside setup(), teardown() or a file-scope helper function (also under errexit), or a test
whose `@test` line does not end in `{`; a `}` at column zero inside a test body (a heredoc writing
JSON, say) ends the block early and hides what follows. An INDENTED `}` does not end the block: a
helper defined inside a test closes with one, and round 7 of fork PR #778 (tests-1, regression-1)
found the block-end rule `strip() == "}"` ending a 242-line case 31 lines in, at its nested helper's
brace, so 211 lines of the case that pinned that round's high were outside this scan; the rule is
the column-zero brace now, which bats' own style puts on every test's last line, and a helper's
body inside a test is scanned like the rest of it. A bare `!` on a helper's last line stays exempt
under the same next-line rule: the caller's errexit reads the function's return status. It does
report `! cmd || <fallback>`, which errexit checks through the list's last command; write that as
`run` + status too."""
import os
import re
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))

_BARE = re.compile(r"^\s*!\s")
_TEST_OPEN = re.compile(r"^@test\b.*\{\s*$")
_BLANK_OR_COMMENT = re.compile(r"^\s*(#.*)?$")


def mid_test_bare_negations(text):
    """(line number, line) for every bare `!` command inside a @test block that is followed by another
    command, the ones bats cannot see fail. A bare `!` whose next command line is the block's closing
    brace is the test's return value and is not reported."""
    lines = text.split("\n")
    hits, in_test = [], False
    for i, line in enumerate(lines):
        if _TEST_OPEN.match(line):
            in_test = True
            continue
        if in_test and line == "}":   # the column-zero brace; an indented one closes a helper inside the test, not the test
            in_test = False
            continue
        if not (in_test and _BARE.match(line)):
            continue
        j = i + 1
        while j < len(lines) and _BLANK_OR_COMMENT.match(lines[j]):
            j += 1
        if j >= len(lines) or lines[j].strip() != "}":
            hits.append((i + 1, line.rstrip()))
    return hits


class BatsSuites(unittest.TestCase):
    def test_no_bats_test_negates_a_command_with_a_bare_bang_before_another_command(self):
        offenders = []
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".bats"):
                continue
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                for ln, line in mid_test_bare_negations(f.read()):
                    offenders.append("%s:%d: %s" % (name, ln, line.strip()))
        self.assertEqual(offenders, [], "a bare `!` that is not the test's last command checks nothing "
                         "under bats; use `run <cmd>` + `[ \"$status\" -ne 0 ]`:\n" + "\n".join(offenders))


class Scanner(unittest.TestCase):
    """The scanner itself, on synthetic snippets: it flags exactly the form bats cannot see."""

    def test_flags_a_bare_bang_followed_by_another_command(self):
        text = ('@test "x" {\n    run true\n    ! grep -q x "$LOG"\n    grep -q y "$LOG"\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '    ! grep -q x "$LOG"')])

    def test_allows_a_bare_bang_as_the_last_command_even_past_comments_and_blanks(self):
        text = ('@test "x" {\n    run true\n    ! grep -q x "$LOG"\n    # a trailing note\n\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])

    def test_ignores_the_checked_forms_and_negations_inside_other_syntax(self):
        text = ('@test "x" {\n    run ! grep -q x "$LOG"\n    run grep -q x "$LOG"\n    [ "$status" -ne 0 ]\n'
                '    [ ! -s "$LOG" ]\n    if ! grep -q x "$LOG"; then true; fi\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])

    def test_ignores_a_bare_bang_outside_a_test_block(self):
        # a helper before the block and one after it: the block's closing `}` must end the scan, or the
        # second helper's negation would be reported as if it were the test's
        text = ('setup() {\n    ! grep -q x "$LOG"\n    true\n}\n@test "x" {\n    true\n}\n'
                'helper() {\n    ! grep -q x "$LOG"\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])

    def test_reports_the_file_the_suite_test_would(self):
        # the suite test reads real files; the same scanner over a written snippet finds the same line
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.bats")
            with open(path, "w", encoding="utf-8") as f:
                f.write('@test "x" {\n    ! grep -q x "$LOG"\n    true\n}\n')
            with open(path, encoding="utf-8") as f:
                self.assertEqual([ln for ln, _ in mid_test_bare_negations(f.read())], [2])

    # round 7 of fork PR #778 (tests-1, regression-1): a helper defined inside the test body closes with an INDENTED brace, which
    # the strip() rule took as the test's end, so everything after the helper was outside the scan
    NESTED = ('@test "x" {\n'
              '    _kept() {\n'
              '        run true\n'
              '        [ "$status" -eq 0 ]\n'
              '    }\n'
              '    _kept\n'
              '    ! grep -q x "$LOG"\n'
              '    true\n'
              '}\n')

    def test_flags_a_bare_bang_after_a_helper_defined_inside_the_test(self):
        # red before the column-zero rule: the scanner returned [] for this file (the helper's `    }` ended the block at line 5)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nested.bats")
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.NESTED)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(mid_test_bare_negations(f.read()), [(7, '    ! grep -q x "$LOG"')])

    def test_allows_a_bare_bang_as_the_last_command_after_a_helper_defined_inside_the_test(self):
        # the test's last command is its return value, helper or no helper before it
        text = self.NESTED.replace('    ! grep -q x "$LOG"\n    true\n', '    true\n    ! grep -q x "$LOG"\n')
        self.assertEqual(mid_test_bare_negations(text), [])

    def test_allows_a_bare_bang_as_the_last_line_of_a_helper_inside_the_test_and_flags_one_before_it(self):
        # a helper's body is scanned like the rest of the test now; its last line is its return status, which the caller's errexit
        # reads, so it is exempt under the same next-line rule, and a bare `!` before another command in the body is reported
        text = ('@test "x" {\n    _h() {\n        run true\n        ! grep -q x "$LOG"\n    }\n    _h\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])
        text = ('@test "x" {\n    _h() {\n        ! grep -q x "$LOG"\n        run true\n    }\n    _h\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '        ! grep -q x "$LOG"')])

    def test_the_block_still_ends_at_the_next_column_zero_brace_and_a_helper_after_it_is_outside(self):
        # the other half of test_ignores_a_bare_bang_outside_a_test_block under the new rule: a file-scope helper after a test that
        # holds a nested helper is outside the scan
        text = self.NESTED.replace('    ! grep -q x "$LOG"\n', '') + 'helper() {\n    ! grep -q x "$LOG"\n    true\n}\n'
        self.assertEqual(mid_test_bare_negations(text), [])


if __name__ == "__main__":
    unittest.main()
