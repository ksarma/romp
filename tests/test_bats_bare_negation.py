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
with `! ` and reports one whose next non-blank, non-comment line is not a position whose status bash
reads: the block's closing `}` at column zero (the test's return value), a helper's closing brace (an
indented `}` whose opener at the same indent is `name() {`: the caller's errexit reads the function's
return status), or a `)` (a subshell's or a command substitution's last command, whose status the
parent reads). An indented `}` closing a BRACE GROUP exempts nothing: bash does not exit on a group
whose last command is a negation that failed (the round-7 addendum of fork PR #778, after the
scanner lens found the next-line rule reading a group's brace as a helper's). A heredoc's body is
text and is skipped, from a line carrying `<<WORD`, `<<-WORD`, `<<'WORD'` or `<<"WORD"` to the
line that is WORD (tabs stripped for `<<-`), so a `}` at column zero inside one (a heredoc writing
JSON, say) no longer ends the block early, which at round 7 left 155 body lines in three files
outside the scan, and a text line beginning `! ` inside one is not reported; a heredoc whose
terminator line never comes is not skipped (the rest of the file stays scanned rather than going
blind on one missing line). It does not see `!cmd` written without a space, a `! cmd` sharing a
line with another command, a bare `!` inside setup(), teardown() or a file-scope helper function
(also under errexit), a test whose `@test` line does not end in `{`, or a line inside a quoted
multi-line string (reported as a command). An INDENTED `}` does not end the block: a helper defined
inside a test closes with one, and round 7 of fork PR #778 (tests-1, regression-1) found the
block-end rule `strip() == "}"` ending a 242-line case 31 lines in, at its nested helper's brace, so
211 lines of the case that pinned that round's high were outside this scan; the rule is the
column-zero brace now, which bats' own style puts on every test's last line, and a helper's body
inside a test is scanned like the rest of it. It does report `! cmd || <fallback>`, which errexit
checks through the list's last command; write that as `run` + status too."""
import os
import re
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))

_BARE = re.compile(r"^\s*!\s")
_TEST_OPEN = re.compile(r"^@test\b.*\{\s*$")
_BLANK_OR_COMMENT = re.compile(r"^\s*(#.*)?$")
# a heredoc's introducer: `<<` (not `<<<`, the here-string) with an optional `-`, the delimiter word bare or in either quote
_HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
# a function's opening line, the one closing brace that exempts a bare `!` before it: `name() {`, `function name() {`, `function name {`
_FUNC_OPEN = re.compile(r"^\s*(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*\s*(?:\(\))?\s*\{\s*$")


def _after_heredoc(lines, i):
    """The index of the first line after the heredoc lines[i] opens, when it opens one whose terminator line exists; i + 1 otherwise. A
    comment line opens none; a heredoc with no terminator is not skipped, so a stray `<<WORD` in a string cannot blind the rest of the
    file."""
    if _BLANK_OR_COMMENT.match(lines[i]):
        return i + 1
    m = _HEREDOC.search(lines[i])
    if not m:
        return i + 1
    dash, word = m.group(1), m.group(3)
    for j in range(i + 1, len(lines)):
        if (lines[j].lstrip("\t") if dash else lines[j]) == word:
            return j + 1
    return i + 1


def _read_position(lines, i, j):
    """Whether lines[j], the first command line after the bare `!` at lines[i], puts that `!` where bash reads its status: the test's
    column-zero `}`, a `)` (a subshell's or a command substitution's end), or an indented `}` that closes a FUNCTION (its opener, the
    nearest earlier line at the same indent, is `name() {`). A brace group's `}` is not one: bash does not exit on a compound command
    that returned nonzero because a negated command failed inside it."""
    nxt = lines[j]
    if nxt == "}" or nxt.strip().startswith(")"):
        return True
    if nxt.strip() != "}":
        return False
    indent = nxt[:len(nxt) - len(nxt.lstrip())]
    for k in range(i - 1, -1, -1):
        prev = lines[k]
        if _BLANK_OR_COMMENT.match(prev) or not prev.strip():
            continue
        lead = prev[:len(prev) - len(prev.lstrip())]
        if len(lead) > len(indent) and lead.startswith(indent):
            continue                      # deeper: inside the block the brace closes
        return lead == indent and bool(_FUNC_OPEN.match(prev))
    return False


def mid_test_bare_negations(text):
    """(line number, line) for every bare `!` command inside a @test block that is followed by another
    command, the ones bats cannot see fail. A bare `!` whose next command line is a position whose status
    bash reads (_read_position) is not reported; a heredoc's body is skipped (_after_heredoc)."""
    lines = text.split("\n")
    hits, in_test = [], False
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = _after_heredoc(lines, i)
        if _TEST_OPEN.match(line):
            in_test = True
        elif in_test and line == "}":   # the column-zero brace; an indented one closes a helper or a group inside the test, not the test
            in_test = False
        elif in_test and _BARE.match(line):
            j = nxt
            while j < len(lines) and _BLANK_OR_COMMENT.match(lines[j]):
                j += 1
            if j >= len(lines) or not _read_position(lines, i, j):
                hits.append((i + 1, line.rstrip()))
        i = nxt
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

    # the round-7 addendum of fork PR #778 (the scanner lens): two shapes checked nothing under bats and went unflagged, a brace group's
    # last command (the next-line rule read the group's indented brace as a helper's) and a bare `!` after a heredoc holding a
    # column-zero brace (the brace ended the block; 155 body lines in three files were outside the scan); two more were flagged though
    # bash reads them, heredoc text beginning `! ` and a subshell's or a command substitution's last command

    def test_flags_a_bare_bang_as_the_last_command_of_a_brace_group(self):
        # red before: the group's `    }` passed as a helper's close; bash does not exit on a group whose last command is a failed negation
        text = ('@test "x" {\n    {\n        run true\n        ! grep -q x "$LOG"\n    }\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(4, '        ! grep -q x "$LOG"')])
        # the group closed by a column-zero brace is the same shape one level up: the brace is read as the test's end (documented)

    def test_a_helper_closed_by_an_indented_brace_still_exempts_its_last_line_whatever_its_opener_spelling(self):
        for opener in ('    _h() {', '    function _h() {', '    function _h {'):
            text = ('@test "x" {\n%s\n        run true\n        ! grep -q x "$LOG"\n    }\n    _h\n    true\n}\n' % opener)
            self.assertEqual(mid_test_bare_negations(text), [], opener)

    def test_skips_a_heredoc_body_so_a_column_zero_brace_inside_it_does_not_end_the_block(self):
        # red before: the JSON's `}` ended the block at line 5 and the negation at line 7 was outside the scan
        text = ('@test "x" {\n    cat > "$f" <<\'JSON\'\n{\n  "a": 1\n}\nJSON\n    ! grep -q x "$LOG"\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(7, '    ! grep -q x "$LOG"')])
        for intro, term in (('<<EOF', 'EOF'), ('<<"EOF"', 'EOF'), ('<<-EOF', '\tEOF'), ('<< \'EOF\'', 'EOF')):
            text = ('@test "x" {\n    cat %s\n}\n%s\n    ! grep -q x "$LOG"\n    true\n}\n' % (intro, term))
            self.assertEqual(mid_test_bare_negations(text), [(5, '    ! grep -q x "$LOG"')], intro)

    def test_a_heredoc_text_line_beginning_with_a_bang_is_not_reported(self):
        # red before: the text line was reported as a command (a false flag, on the visible side)
        text = ('@test "x" {\n    cat <<\'EOF\' > "$f"\n! not a command\n! nor this\nEOF\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])

    def test_a_heredoc_with_no_terminator_and_a_here_string_skip_nothing(self):
        # a `<<WORD` whose WORD line never comes (in a string, say) must not blind the rest of the file; `<<<` is a here-string, not a heredoc
        text = ('@test "x" {\n    echo "the marker <<NOPE is text"\n    ! grep -q x "$LOG"\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '    ! grep -q x "$LOG"')])
        text = ('@test "x" {\n    grep -q x <<< "$s"\n    ! grep -q x "$LOG"\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '    ! grep -q x "$LOG"')])

    def test_a_bare_bang_as_a_subshells_or_a_command_substitutions_last_command_is_not_reported(self):
        # red before: both were flagged; bash reads a subshell's status and an assignment takes its substitution's, so both are checked
        text = ('@test "x" {\n    (\n        run true\n        ! grep -q x "$LOG"\n    )\n    true\n'
                '    out="$(\n        ! grep -q x "$LOG"\n    )"\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])
        # and one BEFORE the subshell's last command is still reported
        text = ('@test "x" {\n    (\n        ! grep -q x "$LOG"\n        run true\n    )\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '        ! grep -q x "$LOG"')])


if __name__ == "__main__":
    unittest.main()
