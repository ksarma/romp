#!/usr/bin/env python3
"""No bats test may negate a command with a bare `!` anywhere but as its LAST command (review round 2,
2026-09-06). bats runs a test under `set -e` with an ERR trap, and bash exempts an inverted command
from both, so `! grep -q x "$LOG"` followed by another line checks nothing: the test passes whether or
not the log contains x. The emoji names-map test asserted `! grep -q 'bg=...'` that way and would have
passed with the very bug it was written against. As the last command it IS checked, because bats reads
the test function's return status — which is why the many last-line sites pass today, and why they stop
checking anything the moment someone appends an assertion. The checked form is `run <cmd>` followed by
`[ "$status" -ne 0 ]`, or a count (`grep -c ... -eq 0`) for a pipeline; bats 1.5+ also has `run !`,
which needs `bats_require_minimum_version 1.5.0` in the file."""
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
    command — the ones bats cannot see fail. A bare `!` whose next command line is the block's closing
    brace is the test's return value and is not reported."""
    lines = text.split("\n")
    hits, in_test = [], False
    for i, line in enumerate(lines):
        if _TEST_OPEN.match(line):
            in_test = True
            continue
        if in_test and line.strip() == "}":
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
        text = ('setup() {\n    ! grep -q x "$LOG"\n    true\n}\n@test "x" {\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])

    def test_reports_the_file_the_suite_test_would(self):
        # the suite test reads real files; the same scanner over a written snippet finds the same line
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.bats")
            with open(path, "w", encoding="utf-8") as f:
                f.write('@test "x" {\n    ! grep -q x "$LOG"\n    true\n}\n')
            with open(path, encoding="utf-8") as f:
                self.assertEqual([ln for ln, _ in mid_test_bare_negations(f.read())], [2])


if __name__ == "__main__":
    unittest.main()
