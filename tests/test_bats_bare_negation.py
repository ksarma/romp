#!/usr/bin/env python3
r"""No bats test may negate a command with a bare `!` unless that is the test's LAST command.

bats runs a test body under `set -e` with an ERR trap, and bash exempts an inverted command from
both, so `! grep -q x "$LOG"` followed by another command checks nothing: the test passes whether
or not the log contains x. As the last command it IS checked, because bats reads the test
function's return status. That is why last-line sites work, and why they stop checking anything
the moment someone appends an assertion after them. PR #383 armed nineteen such sites by hand and
PR #403 one more; within a month three new ones had arrived, one each in tests/romp-headless.bats
(c2a5f844), tests/tmux-status-hook.bats (e0d76b85) and tests/romp.bats (989854c6), each asserting
nothing. This module is the ratchet those hand fixes lacked: the suite test scans every
tests/*.bats and names each inert site, a second suite test asserts how much the scan read, and
the Scanner tests pin the scanner itself on synthetic snippets, each shape run under bats.

The checked form is `run <cmd>` followed by `[ "$status" -ne 0 ]` (tests/romp-postal.bats and
tests/git-hermetic.bats write it inline; the `log_lacks` helper that wrapped it left with
tests/romp-manager-tmux-scope.bats when the tmux backend was removed, 2532d6d8 on 2026-09-11), a count for a pipeline (`[ "$(grep -c x "$LOG")" -eq 0 ]`),
or `run ! <cmd>` in a file that declares `bats_require_minimum_version 1.5.0`. `run` overwrites $status and
$output, so an armed negation goes after any `[[ "$output" ... ]]` check that reads the previous run.

Scope: a line scan, not a bash parser. A block opens at a column-zero `@test ... {` line and ends
at the `}` line that returns the brace depth to zero, whatever its indentation or trailing text (a
command line ending in `{` opens a level, one beginning with `}` closes one; heredoc bodies, blank
lines and comment lines count for nothing). Inside a block it reads every line that begins with
`! ` and reports one whose next command line is not a position whose status bash reads. The read
positions, each run under bats (round 8 of fork PR #778): the test's own closing brace (the test's
return value); a function's closing brace, its opener found by brace depth over the command lines
before it (`name() {` in any spelling, with or without a trailing comment, or an Allman `{` under a
`name()` line: the caller's errexit reads the function's status); a brace group's closing brace
exactly where that brace is itself in a read position, so a group that is the test's, a helper's or
a subshell's last command is read and one followed by another command is not; a subshell's `)`
unless what follows it discards the status (`|`, `|&`, `||`, `&&`, a trailing `&`); and a command
substitution's `)"` only under a plain assignment (`out="$(`), since `echo "$(...)"` discards the
status and `local out="$(...)"` returns local's own 0. A heredoc's body is text and is skipped: an
introducer is a `<<` outside quotes, outside a comment and outside `((...))`, its delimiter any word
bash accepts in any quoting (`EOF`, `'EOF'`, `"EOF"`, `\EOF`, `E\OF`, `"EO"F`, `EOF-1`), two on one line
skipped in order, to the line that is the word (tabs stripped for `<<-`); a heredoc whose terminator
line never comes, or comes after the next `@test` line, is not skipped, so a skip cannot cross a
test and the body is scanned as commands instead. It does not see `!cmd` written without a space,
a `! cmd` sharing a line with another command, a bare `!` inside setup(), teardown() or a
file-scope helper function (also under errexit), a test whose `@test` line is indented or does not
end in `{`, a line inside a quoted string that began on an earlier line (read as a command, or as
an introducer, or as the test's close when it is a column-zero `}`), or a command line ending in a
literal `{` that opens no group (`printf x {`), which opens a level the block never closes. Each of
those last shapes the coverage pin below makes visible rather than silent. It does report
`! cmd || <fallback>`, which errexit checks through the list's last command; write that as `run` +
status too.

The coverage pin (round 8, correctness-1: until it existed the CI check asserted nothing about how
much it scanned, so a scan that had lost half a file read as a clean one, and a "blind region 0"
was a number with no pin behind it). Per file, bash's own parse is the derivation, not this
module's rules: every `@test` line is rewritten into a function opener as bats-preprocess does, and
`bash -n` over prefixes of the file finds each test's extent (an opener counts when the lines
before it parse whole, its close is the first `}` line at which the function parses whole) and
checks each heredoc skip taken inside a test (a prefix cut at the introducer must leave bash inside
a here-document, one cut at the terminator must not). The walk's blocks must equal those extents,
no `@test` open may be met while a block is open, and the in-test lines scanned (commands plus
heredoc text) must equal the lines between each test's open and its close. The pin's own cost is
one `bash -n` per test plus one per candidate close and two per in-test heredoc, about four seconds
over the 45 files here; nothing is executed.

Measured over the 45 tests/*.bats at the round-7 head (938 tests, 14206 in-test lines by bash's
parse), the two roads round 7's ruling left open, both with the helpers of the byte-order-mark case
at file scope: round 6's rule (a block ends at any line stripping to `}`, no heredoc skip) scanned
14019 lines, 187 outside the scan in 10 blocks ended early (tests/install-sh.bats 80,
tests/romp-uninstall.bats 49, tests/install-sh-coexist.bats 35, tests/romp-service.bats 23), 0
reports; round 7's rule scanned all 14206, 0 reports; this rule scans all 14206, 0 reports, and
the pin holds on every file. On 48 synthetic shapes holding 55 bare negations, each run under bats
1.10.0 with the negated command succeeding, round 6's rule reported 14 positions bats checks and
missed 9 it does not, round 7's 19 and 14, this rule 0 and 0. The fix road was taken on those
numbers: the revert would have reopened 187 lines today and the class for the next nested helper.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))

_BARE = re.compile(r"^\s*!\s")
_TEST_OPEN = re.compile(r"^@test\b.*\{\s*$")
_BLANK_OR_COMMENT = re.compile(r"^\s*(#.*)?$")
# a function's opening line, the one closing brace that exempts a bare `!` before it: `name() {`, `function name() {`, `function name {`,
# each with or without a trailing comment (round 8, tests-2: the opener of the one multi-line helper defined inside a test in this
# repo carries one)
_FUNC_OPEN = re.compile(r"^\s*(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*\s*(?:\(\))?\s*\{\s*(#.*)?$")
# the line before an Allman-style `{`: `name()` or `function name`, the function's name on its own line
_FUNC_NAME_LINE = re.compile(r"^\s*(?:function\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:\(\))?|[A-Za-z_][A-Za-z0-9_]*\s*\(\))\s*$")
# an assignment taking a command substitution's status: `name="$(`, `name=$(`, `arr[k]+="$(`; `local`, `declare`, `export`, `readonly`
# and `typeset` before the name return their own status, 0, so a substitution under them is NOT read (round 8, tests-1's refuter)
_ASSIGN_SUBST = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?\+?=[\"']?\$\($")
# what may follow a `)` or a `}` and still leave its status read: nothing, `;`, or redirections; a pipe or a list operator hands the
# status to the next command (`|`, `|&`, `||`, `&&`), and a trailing `&` backgrounds it
_DISCARD = re.compile(r"^(?:\|\|?|\|&|&&)")
# bats-preprocess's BATS_TEST_PATTERN (bats-core 1.10 and 1.11): the lines it rewrites into functions before bash parses the file
_TEST_LINE = re.compile(r"^[ \t]*@test[ \t]+(.*[^ \t])[ \t]+\{(.*)$")
_CLOSE_CANDIDATE = re.compile(r"^\s*\}")


def _code_part(line):
    """The line's code: a trailing comment (a `#` outside quotes, at the start or after a blank) and trailing blanks removed."""
    q, i, n = None, 0, len(line)
    while i < n:
        ch = line[i]
        if q == "'":
            if ch == "'":
                q = None
        elif q == '"':
            if ch == "\\":
                i += 1
            elif ch == '"':
                q = None
        elif ch == "\\":
            i += 1
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def _delimiter_word(line, j):
    r"""(the heredoc delimiter word from line[j:], quoting removed as bash removes it; the index after it). Any quoting of any
    character quotes the word (`<<'EOF'`, `<<"EOF"`, `<<\EOF`, `<<E\OF`, `<<"EO"F`); the word ends at an unquoted blank or
    metacharacter, so `<<EOF-1` is the whole token EOF-1 and not a prefix of it."""
    word, q, n = "", None, len(line)
    while j < n:
        ch = line[j]
        if q == "'":
            if ch == "'":
                q = None
            else:
                word += ch
        elif q == '"':
            if ch == "\\" and j + 1 < n and line[j + 1] in '"\\$`':
                word += line[j + 1]
                j += 1
            elif ch == '"':
                q = None
            else:
                word += ch
        elif ch == "\\" and j + 1 < n:
            word += line[j + 1]
            j += 1
        elif ch in "'\"":
            q = ch
        elif ch in " \t;&|<>()":
            break
        else:
            word += ch
        j += 1
    return word, j


def _introducers(line):
    """[(strips leading tabs, delimiter word)] for every heredoc the line opens, in order: a `<<` (not `<<<`, the here-string)
    outside quotes, outside a comment and outside `((...))` arithmetic (where it is a shift). A `<<` inside a quoted span is text
    (round 8, extra6-3: a test grepping for an introducer skipped every line to the next real terminator), and the search goes on
    past it, so a real heredoc after a quoted decoy on the same line is still skipped."""
    out, q, arith, i, n = [], None, 0, 0, len(line)
    while i < n:
        ch = line[i]
        if q == "'":
            if ch == "'":
                q = None
        elif q == '"':
            if ch == "\\":
                i += 1
            elif ch == '"':
                q = None
        elif ch == "\\":
            i += 1
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        elif line.startswith("((", i):
            arith += 1
            i += 1
        elif arith and line.startswith("))", i):
            arith -= 1
            i += 1
        elif not arith and line.startswith("<<", i) and not line.startswith("<<<", i) and (i == 0 or line[i - 1] != "<"):
            j, dash = i + 2, False
            if j < n and line[j] == "-":
                dash, j = True, j + 1
            while j < n and line[j] in " \t":
                j += 1
            word, j = _delimiter_word(line, j)
            if word:
                out.append((dash, word))
            i = j
            continue
        i += 1
    return out


def _after_heredoc(lines, i):
    """The index of the first line after the heredocs lines[i] opens, when each has its terminator line before the next `@test`
    open; i + 1 otherwise. A blank or comment line opens none. A heredoc whose terminator never comes, or comes after a `@test`
    open, is not skipped (round 8, correctness-1: the search is bounded so a skip cannot cross a test; the body is then scanned as
    commands, which is the visible side). Two heredocs on one line are skipped in order, the second body after the first's
    terminator (round 8, tests-4)."""
    if _BLANK_OR_COMMENT.match(lines[i]):
        return i + 1
    intros = _introducers(lines[i])
    if not intros:
        return i + 1
    j = i + 1
    for dash, word in intros:
        while j < len(lines):
            if _TEST_OPEN.match(lines[j]):
                return i + 1
            if (lines[j].lstrip("\t") if dash else lines[j]) == word:
                break
            j += 1
        else:
            return i + 1
        j += 1
    return j


def _command_lines_backward(lines, k, heredoc_body):
    """The indices of the command lines before k, nearest first: heredoc text, blank and comment lines skipped."""
    for m in range(k - 1, -1, -1):
        if m in heredoc_body or _BLANK_OR_COMMENT.match(lines[m]):
            continue
        yield m


def _brace_opener(lines, j, heredoc_body):
    """The index of the line whose `{` the `}` at lines[j] closes, by brace depth over the command lines before it (a line ending in
    `{` opens a level, one beginning with `}` closes one; heredoc bodies are text); None when no opener is found."""
    depth = 0
    for k in _command_lines_backward(lines, j, heredoc_body):
        code = _code_part(lines[k])
        if code.endswith("{"):
            if depth == 0:
                return k
            depth -= 1
        if code.lstrip().startswith("}"):
            depth += 1
    return None


def _paren_opener(lines, j, heredoc_body):
    """The index of the line whose `(` the `)` at lines[j] closes, by paren depth over the earlier command lines; None when none."""
    depth = 0
    for k in _command_lines_backward(lines, j, heredoc_body):
        code = _code_part(lines[k])
        if code.endswith("("):
            if depth == 0:
                return k
            depth -= 1
        if code.lstrip().startswith(")"):
            depth += 1
    return None


def _is_function_opener(lines, k, heredoc_body):
    """Whether the opener at lines[k] opens a FUNCTION: `name() {` in any spelling, or an Allman `{` under a `name()` line."""
    code = _code_part(lines[k])
    if _FUNC_OPEN.match(lines[k]):
        return True
    if code.strip() == "{":
        for m in _command_lines_backward(lines, k, heredoc_body):
            return bool(_FUNC_NAME_LINE.match(_code_part(lines[m])))
    return False


def _read_position(lines, i, j, heredoc_body):
    """Whether lines[j], the first command line after the bare `!` at lines[i], puts that `!` where bash reads its status. A `)`:
    a subshell's end, read unless what follows the paren discards it (`|`, `|&`, `||`, `&&`, a trailing `&`; round 8, tests-1 and
    correctness-4); a `)"` or `)'`: a command substitution's end, read only when the opener is a plain assignment (`out="$(`), since
    `echo "$(...)"` discards it and `local out="$(...)"` returns local's 0. A `}`: what it closes decides, found by brace depth over
    the command lines before it, heredoc bodies skipped (round 8, regression-2): the test's own opener (the test's return value, at
    any indentation; round 8, extra6-1), a function's opener (the caller's errexit reads the function's status; a trailing comment
    on the opener and the Allman `{` under a `name()` line count), or a brace group's, whose status is read exactly where the
    group's own `}` is in a read position, so the question is asked again of the line after it (round 8, extra6-2: a group that is
    the test's, a helper's or a subshell's last command is read; one followed by another command is not). A `}` or `)` followed by
    a status-discarding operator is not a read position whatever it closes."""
    if j >= len(lines):
        return False
    stripped = _code_part(lines[j]).strip()
    if stripped.startswith(")"):
        rest = stripped[1:]
        quoted = rest[:1] in ('"', "'")
        if quoted:
            rest = rest[1:]
        if _trailer_discards(rest):
            return False
        if not quoted:
            return True
        k = _paren_opener(lines, j, heredoc_body)
        return k is not None and bool(_ASSIGN_SUBST.match(_code_part(lines[k])))
    if stripped.startswith("}"):
        if _trailer_discards(stripped[1:]):
            return False
        k = _brace_opener(lines, j, heredoc_body)
        if k is None:
            return False
        if _TEST_OPEN.match(lines[k]) or _is_function_opener(lines, k, heredoc_body):
            return True
        j2 = j + 1
        while j2 < len(lines) and _BLANK_OR_COMMENT.match(lines[j2]):
            j2 += 1
        return _read_position(lines, j, j2, heredoc_body)
    return False


def _trailer_discards(rest):
    """Whether the text after a `)` or `}` hands its status elsewhere: a pipe or list operator, or a trailing `&`."""
    rest = rest.strip()
    return bool(_DISCARD.match(rest)) or rest == "&" or rest.endswith(" &") or rest.endswith(";&")


class Scan:
    """What one walk over a file read: the hits, and the accounting the coverage pin asserts (round 8 of fork PR #778,
    correctness-1: the CI check said nothing about how much it scanned, so a scan that had lost half a file read as a clean
    one). blocks: (open index, close index or None) per @test block the walk entered, None when the block was still open at the
    next @test open or at EOF; reopened: the @test opens met while a block was open; command_lines: lines inside a block the walk
    read as commands (blanks and comments included); heredoc_lines: lines inside a block it skipped as heredoc text;
    heredoc_body: every line index skipped as heredoc text, in and out of tests; heredoc_skips: (introducer index, index after the
    terminator) for each skip taken inside a block, which the coverage pin verifies against bash's parse."""

    def __init__(self):
        self.hits, self.blocks, self.reopened, self.heredoc_skips = [], [], [], []
        self.command_lines = self.heredoc_lines = 0
        self.heredoc_body = set()


def scan(text):
    """The walk: a Scan of the text. Inside a `@test ... {` block (opened at a column-zero `@test` line ending in `{`) the block ends
    at the `}` line that returns the brace depth to zero, whatever its indentation or trailing text (a command line ending in `{`
    opens a level, one beginning with `}` closes one; heredoc bodies, blank and comment lines count for nothing). A bare `!` whose
    next command line is a position whose status bash reads (_read_position) is not a hit; a heredoc's body is skipped
    (_after_heredoc). A `@test` open met while a block is open ends that block there (recorded as unclosed) and opens the next."""
    lines = text.split("\n")
    s = Scan()
    in_test, open_idx, depth = False, None, 0
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = _after_heredoc(lines, i)
        if nxt > i + 1:
            s.heredoc_body.update(range(i + 1, nxt))
        if _TEST_OPEN.match(line):
            if in_test:
                s.reopened.append(i)
                s.blocks.append((open_idx, None))
            in_test, open_idx, depth = True, i, 1
        elif in_test and not _BLANK_OR_COMMENT.match(line):
            code = _code_part(line)
            if code.lstrip().startswith("}"):
                depth -= 1
            if depth == 0:
                s.blocks.append((open_idx, i))
                in_test = False
            else:
                if code.endswith("{"):
                    depth += 1
                if _BARE.match(line):
                    j = nxt
                    while j < len(lines) and _BLANK_OR_COMMENT.match(lines[j]):
                        j += 1
                    if not _read_position(lines, i, j, s.heredoc_body):
                        s.hits.append((i + 1, line.rstrip()))
        if in_test and i != open_idx:
            s.command_lines += 1
            s.heredoc_lines += nxt - i - 1
            if nxt > i + 1:
                s.heredoc_skips.append((i, nxt))
        i = nxt
    if in_test:
        s.blocks.append((open_idx, None))
    return s


def mid_test_bare_negations(text):
    """(line number, line) for every bare `!` command inside a @test block that is followed by another
    command, the ones bats cannot see fail."""
    return scan(text).hits


def _bash_parses(lines):
    """Whether bash parses these lines as a complete script: `bash -n` exits 0 and reports no here-document cut off by the end of
    the input (a warning, exit 0, so it is read off stderr)."""
    r = subprocess.run(["bash", "-n"], input="\n".join(lines) + "\n", capture_output=True, text=True)
    return r.returncode == 0 and "delimited by end-of-file" not in r.stderr


def _bash_pending_heredoc(lines):
    """Whether bash, parsing these lines, is still inside a here-document at the end of the input (its warning names the case)."""
    r = subprocess.run(["bash", "-n"], input="\n".join(lines) + "\n", capture_output=True, text=True)
    return "delimited by end-of-file" in r.stderr


def _rewritten(lines):
    """The lines with every @test line rewritten into a function opener, as bats-preprocess does before bash parses the file."""
    return [("_t() {" + m.group(2)) if (m := _TEST_LINE.match(l)) else l for l in lines]


def bash_test_extents(lines):
    """(open index, close index or None) for every test bash parses, from bash's own parse and not from this module's rules:
    every @test line is rewritten into a function opener the way bats-preprocess does, an opener counts when the lines before it
    parse as a complete script (so one inside a heredoc, a quoted string or another test does not; the lines are read from the
    last point known to parse whole, the previous test's close, which is the same test by induction), and its close is the first
    later line beginning with `}` at which the opener and the lines between parse as a complete function. None: no such line (the
    file does not parse under this bash). One `bash -n` per opener plus one per candidate close, no execution."""
    rewritten = _rewritten(lines)
    extents, after = [], 0   # after: the first line not yet known to be parsed whole, so the lines before an opener are checked once each
    for o, line in enumerate(lines):
        if o < after or not _TEST_OPEN.match(line):
            continue
        if not _bash_parses(rewritten[after:o]):   # the lines since the last known-complete point do not parse whole: not a top-level opener
            continue
        close = None
        for c in range(o + 1, len(lines)):
            if _CLOSE_CANDIDATE.match(lines[c]) and _bash_parses(rewritten[o:c + 1]):
                close = c
                break
        extents.append((o, close))
        after = (close if close is not None else len(lines)) + 1
    return extents


def coverage_problems(name, lines, s, extents):
    """The coverage pin: every test bash parses is a block the walk entered, each ends where bash ends it, no @test open is met
    while a block is open, every heredoc skipped inside a block is one bash opens on that line and closes where the skip ends, and
    the in-test lines scanned (commands plus heredoc text) equal the lines between each test's open and its close. One problem
    line per disagreement, each naming the file, the line and what was outside the scan."""
    problems = []
    walk = dict(s.blocks)
    bash = dict(extents)
    for o, c in extents:
        if c is None:
            problems.append("%s:%d: bash finds no close for this test (the file does not parse under this bash -n); its extent is "
                            "unknown and nothing about the scan of it can be asserted" % (name, o + 1))
        elif o not in walk:
            problems.append("%s:%d: a test bash parses that the scan never entered: %d in-test lines outside the scan"
                            % (name, o + 1, c - o - 1))
        elif walk[o] is None:
            problems.append("%s:%d: the block never ended where bash ends the test (line %d); it ran to the next @test or the end "
                            "of the file, scanning file-scope lines as the test's" % (name, o + 1, c + 1))
        elif walk[o] < c:
            problems.append("%s:%d: the block ended at line %d where bash ends the test at line %d: %d in-test lines outside the scan"
                            % (name, o + 1, walk[o] + 1, c + 1, c - walk[o]))
        elif walk[o] > c:
            problems.append("%s:%d: the block ended at line %d where bash ends the test at line %d: %d lines scanned as the test's "
                            "that are not" % (name, o + 1, walk[o] + 1, c + 1, walk[o] - c))
    for o, c in s.blocks:
        if o not in bash:
            problems.append("%s:%d: the scan entered a block where bash sees no test start (a @test line inside a heredoc, a quoted "
                            "string or another test); write such a fixture line indented, which bats accepts and this scan does not "
                            "read as a test" % (name, o + 1))
    for r in s.reopened:
        problems.append("%s:%d: a @test open met while a block was open" % (name, r + 1))
    rewritten = _rewritten(lines)
    for i, nxt in s.heredoc_skips:
        o = max((b for b, _ in s.blocks if b < i), default=None)
        if o is None:
            continue
        if not _bash_pending_heredoc(rewritten[o:i + 1]):
            problems.append("%s:%d: read as opening a heredoc that bash opens nowhere on this line (a `<<` inside a string that began "
                            "on an earlier line?): lines %d to %d were skipped as text and are commands" % (name, i + 1, i + 2, nxt))
        elif _bash_pending_heredoc(rewritten[o:nxt]):
            problems.append("%s:%d: the heredoc opened here was skipped to line %d, where bash still reads its text (the terminator "
                            "taken is not bash's)" % (name, i + 1, nxt))
    expected = sum(c - o - 1 for o, c in extents if c is not None)
    scanned = s.command_lines + s.heredoc_lines
    if scanned != expected:
        problems.append("%s: in-test lines: %d by bash's parse, %d scanned (%d command lines, %d heredoc text lines)"
                        % (name, expected, scanned, s.command_lines, s.heredoc_lines))
    return problems


def coverage_report(name, s, extents):
    return "%s: %d tests, %d in-test lines by bash's parse, %d scanned (%d command lines, %d heredoc text lines)" % (
        name, len(extents), sum(c - o - 1 for o, c in extents if c is not None), s.command_lines + s.heredoc_lines,
        s.command_lines, s.heredoc_lines)


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

    def test_the_scan_reaches_every_line_of_every_test_bash_parses(self):
        # the coverage pin (round 8 of fork PR #778, correctness-1): the check above asserted nothing about how much it scanned, so a
        # scan that had lost half a file (a heredoc skip diverted to a later terminator, a block ended early at a brace inside a
        # heredoc or a string, a block that never ended) read exactly like a clean one. Per file, bash's own parse of each test's
        # extent (bash_test_extents) is the derivation; the walk's blocks and line counts must equal it.
        self.assertTrue(shutil.which("bash"), "bash is what bats runs tests under; without it nothing here can be derived")
        problems, report = [], []
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".bats"):
                continue
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                lines = f.read().split("\n")
            s, extents = scan("\n".join(lines)), bash_test_extents(lines)
            self.assertTrue(extents or not any(_TEST_OPEN.match(l) for l in lines),
                            "%s: @test lines but no extent derived: the file does not parse under bash -n" % name)
            problems += coverage_problems(name, lines, s, extents)
            report.append(coverage_report(name, s, extents))
        print("\n".join(report))
        self.assertEqual(problems, [], "in-test lines outside the bare-negation scan, or file-scope lines inside it:\n"
                         + "\n".join(problems) + "\n\n" + "\n".join(report))


class Scanner(unittest.TestCase):
    """The scanner itself, on synthetic snippets: it flags exactly the form bats cannot see. Every shape below was run under bats
    1.10.0 with the negated command succeeding (round 8 of fork PR #778): `ok` means the position asserts nothing and the scanner
    must report it, `not ok` means bats checked it and the scanner must not. `# red before:` names the round-7 module's answer."""

    NEG = '! grep -q x "$LOG"'

    def negation_lines(self, text):
        return [i + 1 for i, l in enumerate(text.split("\n")) if l.lstrip().startswith(self.NEG)]

    def assertReported(self, text, msg=None):
        self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], self.negation_lines(text), msg or text)

    def assertExempt(self, text, msg=None):
        self.assertEqual(mid_test_bare_negations(text), [], msg or text)

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
        # red before the round-7 rule: the scanner returned [] for this file (the helper's `    }` ended the block at line 5)
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
        # a helper's body is scanned like the rest of the test; its last line is its return status, which the caller's errexit
        # reads, so it is exempt under the same next-line rule, and a bare `!` before another command in the body is reported
        text = ('@test "x" {\n    _h() {\n        run true\n        ! grep -q x "$LOG"\n    }\n    _h\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])
        text = ('@test "x" {\n    _h() {\n        ! grep -q x "$LOG"\n        run true\n    }\n    _h\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '        ! grep -q x "$LOG"')])

    def test_the_block_ends_at_its_own_closing_brace_and_a_helper_after_it_is_outside(self):
        # the other half of test_ignores_a_bare_bang_outside_a_test_block: a file-scope helper after a test that holds a nested
        # helper is outside the scan
        text = self.NESTED.replace('    ! grep -q x "$LOG"\n', '') + 'helper() {\n    ! grep -q x "$LOG"\n    true\n}\n'
        self.assertEqual(mid_test_bare_negations(text), [])

    # the round-7 addendum of fork PR #778 (the scanner lens): a brace group's last command followed by another command checked
    # nothing under bats and went unflagged, and heredoc text beginning `! ` was flagged though bash never runs it

    def test_flags_a_bare_bang_as_the_last_command_of_a_brace_group_followed_by_a_command(self):
        # bats: ok (the group's status is discarded when a command follows the group)
        text = ('@test "x" {\n    {\n        run true\n        ! grep -q x "$LOG"\n    }\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(4, '        ! grep -q x "$LOG"')])

    def test_a_brace_group_in_a_read_position_exempts_its_last_command(self):
        # round 8 (extra6-2): whether bash reads a group's last command depends on what follows the GROUP. bats: not ok for each of
        # these, so none is reported; red before: the round-7 rule reported every one (a group's brace exempted nothing)
        shapes = {
            "the test's last command": '@test "D" {\n    {\n        true\n        %s\n    }\n}\n',
            "a helper's last command, the helper called last": '@test "E" {\n    _h() {\n        {\n            true\n            %s\n        }\n    }\n    _h\n}\n',
            "a helper's last command, the helper called mid-test": '@test "E2" {\n    _h() {\n        {\n            true\n            %s\n        }\n    }\n    _h\n    true\n}\n',
            "a subshell's last command": '@test "H" {\n    (\n        {\n            true\n            %s\n        }\n    )\n    true\n}\n',
            "a nested group, the test's last command": '@test "I" {\n    {\n        {\n            true\n            %s\n        }\n    }\n}\n',
            "a group with a redirection, the test's last command": '@test "K" {\n    {\n        true\n        %s\n    } > /dev/null\n}\n',
            "the group of an || list, the test's last command": '@test "L" {\n    false || {\n        true\n        %s\n    }\n}\n',
        }
        for what, shape in shapes.items():
            self.assertExempt(shape % self.NEG, what)
        # and a group whose status goes elsewhere is reported (bats: ok for both)
        self.assertReported('@test "G" {\n    _h() {\n        {\n            true\n            %s\n        }\n        true\n    }\n    _h\n}\n' % self.NEG)
        self.assertReported('@test "J" {\n    {\n        true\n        %s\n    } || true\n    true\n}\n' % self.NEG)

    def test_a_subshell_or_a_substitution_is_read_unless_what_follows_the_paren_discards_it(self):
        # round 8 (tests-1, correctness-4): red before, the round-7 rule exempted every `)`. bats: not ok for the read shapes
        sub = '@test "x" {\n    (\n        run true\n        %s\n    )%s\n    true\n}\n'
        for closer in ("", " > /dev/null", ";", " 2>&1", " &>/dev/null"):
            self.assertExempt(sub % (self.NEG, closer), repr(closer))
        # bats: ok for the discarding shapes (no pipefail in a bats test; a list hands the status on; `&` backgrounds)
        for closer in (" | cat", " || true", " && echo yes", " &\n    wait"):
            self.assertReported(sub % (self.NEG, closer), repr(closer))
        # a command substitution: read by a plain assignment, discarded by echo and by `local` (which returns its own 0)
        self.assertExempt('@test "x" {\n    out="$(\n        %s\n    )"\n    true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    echo "$(\n        %s\n    )"\n    true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    _h() {\n        local out="$(\n            %s\n        )"\n    }\n    _h\n    true\n}\n' % self.NEG)
        # and one BEFORE the subshell's last command is still reported
        text = ('@test "x" {\n    (\n        ! grep -q x "$LOG"\n        run true\n    )\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '        ! grep -q x "$LOG"')])

    def test_a_test_closed_by_a_brace_with_leading_or_trailing_whitespace_ends_there_and_reads_its_last_command(self):
        # round 8 (extra6-1, tests-3): bats parses each close and reads the negation (not ok); the round-7 rule reported the armed
        # last command and ran the block on into the next test (red before: [9, 13] for each; 13 alone is right)
        for body, close in (("    ", "  }"), ("    ", "} "), ("    ", "\t}"), ("    ", "    }"), ("  ", "  }"), ("\t", "\t}")):
            text = ('@test "armed last" {\n%srun true\n%s%s\n%s\n\n@test "after it" {\n    %s\n    true\n}\n'
                    % (body, body, self.NEG, close, self.NEG))
            self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [7], repr(close))
            s = scan(text)
            self.assertEqual(s.blocks, [(0, 3), (5, 8)], repr(close))

    def test_a_helpers_opener_may_carry_a_trailing_comment_or_be_spelled_allman(self):
        # round 8 (tests-2, regression-2's Allman half): bats reads the helper's last command through the caller's errexit (not ok);
        # red before: both reported
        for opener in ('    _h() {   # a note', '    _h()\n    {', '    function _h {', '    function _h() {', '    _h() {'):
            self.assertExempt('@test "x" {\n%s\n        run true\n        %s\n    }\n    _h\n    true\n}\n' % (opener, self.NEG), opener)

    def test_a_heredoc_inside_a_nested_helper_does_not_end_the_backward_walk(self):
        # round 8 (regression-2): the helper's opener is found over command lines, heredoc text skipped; bats: not ok. Red before:
        # the walk stopped at the column-zero `PY` and reported the helper's last command
        text = ('@test "x" {\n    _h() {\n        cat > "$f" <<\'PY\'\nimport sys\nPY\n        %s\n    }\n    _h\n    true\n}\n' % self.NEG)
        self.assertExempt(text)

    def test_skips_a_heredoc_body_so_a_column_zero_brace_inside_it_does_not_end_the_block(self):
        # the round-7 addendum: the JSON's `}` ended the block at line 5 and the negation at line 7 was outside the scan. Round 8
        # (correctness-5, tests-4): the delimiter is any word bash accepts in any quoting (red before: the backslash and mixed
        # quotings and the hyphen were not introducers, so the brace ended the block and nothing was reported)
        for intro, term in (('<<EOF', 'EOF'), ('<<"EOF"', 'EOF'), ("<<'EOF'", 'EOF'), ('<<-EOF', '\tEOF'), ("<< 'EOF'", 'EOF'),
                            ('<<\\EOF', 'EOF'), ('<<-\\EOF', '\tEOF'), ('<<E\\OF', 'EOF'), ('<<"EO"F', 'EOF'), ("<<E'OF'", 'EOF'),
                            ("<<'EOF-1'", 'EOF-1'), ('<<EOF-1', 'EOF-1'), ('<<$X', '$X')):
            text = ('@test "x" {\n    cat > "$f" %s\n{\n  "a": 1\n}\n%s\n    %s\n    true\n}\n' % (intro, term, self.NEG))
            self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [7], intro)

    def test_a_heredoc_text_line_beginning_with_a_bang_is_not_reported(self):
        # the round-7 addendum: the text line was reported as a command (a false flag, on the visible side)
        text = ('@test "x" {\n    cat <<\'EOF\' > "$f"\n! not a command\n! nor this\nEOF\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [])
        # round 8 (tests-4): an unquoted `<<EOF-1` is the whole token, so a body line `EOF` does not end the skip, and two heredocs
        # on one line are skipped in order; red before: the text lines were reported
        self.assertReported('@test "x" {\n    cat > "$f" <<EOF-1\n! text inside\nEOF\n! more text\nEOF-1\n    %s\n    true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    cat <<A <<B > "$f"\n! text of A\nA\n! text of B\nB\n    %s\n    true\n}\n' % self.NEG)

    def test_a_heredoc_with_no_terminator_and_a_here_string_and_a_shift_skip_nothing(self):
        # a `<<WORD` whose WORD line never comes is not skipped; `<<<` is a here-string; `<<` inside `(( ))` is a shift (round 8)
        text = ('@test "x" {\n    cat <<NOPE\n    ! grep -q x "$LOG"\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '    ! grep -q x "$LOG"')])
        text = ('@test "x" {\n    grep -q x <<< "$s"\n    ! grep -q x "$LOG"\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '    ! grep -q x "$LOG"')])
        self.assertReported('@test "x" {\n    x=$(( 1 << 2 ))\n    %s\n    true\n}\n' % self.NEG)

    def test_an_introducer_inside_a_quoted_span_is_text_and_a_real_one_after_it_is_a_heredoc(self):
        # round 8 (extra6-3): red before, the quoted `<<EOF` skipped to the next test's real terminator, dropping this negation and
        # the next test's opener. bats: ok for both tests
        text = ('@test "grep" {\n    run grep -q \'cat > "$f" <<EOF\' "$BATS_TEST_FILENAME"\n    %s\n    true\n}\n\n'
                '@test "real" {\n    cat > "$f" <<EOF\nhello\nEOF\n    %s\n    true\n}\n' % (self.NEG, self.NEG))
        self.assertReported(text)
        self.assertEqual(scan(text).blocks, [(0, 4), (6, 12)])
        # a quote-state machine, not a count: the apostrophe inside "don't" does not quote the heredoc after it (red before as well:
        # the round-7 rule had no quote check at all, so this one it got right and the decoy below it did not)
        self.assertReported('@test "x" {\n    echo "don\'t" ; cat > "$f" <<EOF\n! text\nEOF\n    %s\n    true\n}\n' % self.NEG)
        # the search goes on past a quoted decoy to the real introducer on the same line
        self.assertReported('@test "x" {\n    grep -q \'x <<FAKE\' "$LOG" || cat > "$f" <<EOF\n! text\nEOF\n    %s\n    true\n}\n' % self.NEG)

    def test_a_comment_line_opens_no_heredoc(self):
        # round 8 (tests-5): the guard that makes _after_heredoc's docstring true; without it the comment's `<<PLIST` skips to the
        # real terminator below and the negation between is lost (the mutant returns [])
        self.assertReported('@test "x" {\n    # the fixture below is written with a heredoc <<PLIST\n    %s\n'
                            '    cat > "$f" <<\'PLIST\'\n<plist/>\nPLIST\n    true\n}\n' % self.NEG)

    def test_a_heredoc_skip_cannot_cross_a_test_open(self):
        # round 8 (correctness-1): a `<<WORD` whose terminator comes after the next @test line is not skipped (the body is scanned
        # as commands, the visible side), so a swallow across tests is impossible rather than only reported
        text = ('@test "a" {\n    cat <<WORD\n    %s\n    true\n}\n\n@test "b" {\n    true\n}\nWORD\n' % self.NEG)
        self.assertReported(text)
        self.assertEqual(scan(text).blocks, [(0, 4), (6, 8)])

    # the coverage pin (round 8, correctness-1), on synthetic files: bash's parse against the walk

    def coverage(self, text):
        lines = text.split("\n")
        return coverage_problems("x.bats", lines, scan(text), bash_test_extents(lines))

    def test_the_coverage_pin_is_green_on_a_file_the_scan_reads_whole(self):
        text = (self.NESTED + '\nhelper() {\n    cat <<EOF\n}\nEOF\n}\n\n@test "y" {\n    cat > "$f" <<\'JSON\'\n{\n}\nJSON\n'
                '    _h() {   # note\n        true\n    }\n  }\n')
        self.assertEqual(self.coverage(text), [])
        s = scan(text)
        self.assertEqual((s.blocks, s.command_lines, s.heredoc_lines), ([(0, 8), (16, 24)], 11, 3))

    def test_the_coverage_pin_reds_a_block_ended_early_by_a_brace_inside_a_multi_line_string(self):
        # the documented limit made visible: the scan reads the column-zero `}` inside the string as the test's close; bash does not
        text = ('@test "x" {\n    msg=\'a\n}\nb\'\n    %s\n    true\n}\n' % self.NEG)
        problems = self.coverage(text)
        self.assertEqual(len(problems), 2, problems)
        self.assertIn("x.bats:1: the block ended at line 3 where bash ends the test at line 7: 4 in-test lines outside the scan", problems)
        self.assertIn("x.bats: in-test lines: 5 by bash's parse, 1 scanned (1 command lines, 0 heredoc text lines)", problems)
        self.assertEqual(mid_test_bare_negations(text), [], "the loss the pin names: the negation is outside the block")

    def test_the_coverage_pin_reds_a_skip_bash_does_not_make(self):
        # a `<<PY` inside a string that began on the earlier line is an introducer to this line scan and text to bash: the skip to the
        # later real `PY` reads as covered by the line counts alone, and bash's parse says the introducer line opens no heredoc
        text = ('@test "x" {\n    msg="see the\n<<PY marker"\n    %s\n    python3 - <<PY\nprint(1)\nPY\n    true\n}\n' % self.NEG)
        problems = self.coverage(text)
        self.assertEqual(problems, ["x.bats:3: read as opening a heredoc that bash opens nowhere on this line (a `<<` inside a string "
                                    "that began on an earlier line?): lines 4 to 7 were skipped as text and are commands"])
        self.assertEqual(mid_test_bare_negations(text), [], "the loss the pin names")

    def test_the_coverage_pin_reds_a_fixture_heredoc_holding_a_column_zero_test_line_and_says_how_to_write_it(self):
        # the bounded skip's cost (round 8, correctness-1): a heredoc writing a bats fixture with a column-zero `@test ... {` line
        # is not skipped past that line, so the walk opens a block bash does not see; the pin names the line and the way to write
        # such a fixture (indented, which bats accepts)
        text = ('@test "a" {\n    cat > "$f" <<\'EOF\'\n@test "inner" {\n    true\n}\nEOF\n    %s\n    true\n}\n' % self.NEG)
        problems = self.coverage(text)
        self.assertIn("x.bats:3: the scan entered a block where bash sees no test start (a @test line inside a heredoc, a quoted "
                      "string or another test); write such a fixture line indented, which bats accepts and this scan does not read as a "
                      "test", problems)
        self.assertIn("x.bats:3: a @test open met while a block was open", problems)
        self.assertEqual(self.coverage(text.replace('\n@test "inner"', '\n  @test "inner"')), [], "the indented fixture line: green")

    def test_bash_test_extents_reads_the_tests_bash_parses(self):
        # opens inside a heredoc, a string or another test are not tests; a one-line @test is rewritten so the file parses but is
        # not an extent; a file that does not parse yields None for the close
        text = ('setup() {\n    cat <<EOF\n@test "not one" {\n}\nEOF\n}\n@test "one" {\n    x="\n@test \\"nor this\\" {\n"\n}\n'
                '@test "two" { true; }\n@test "three" {\n  true\n  }\n')
        lines = text.split("\n")
        self.assertEqual(bash_test_extents(lines), [(6, 10), (12, 14)])
        self.assertEqual(bash_test_extents('@test "x" {\n    echo "\n'.split("\n")), [(0, None)])


if __name__ == "__main__":
    unittest.main()
