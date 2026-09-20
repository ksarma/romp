#!/usr/bin/env python3
r"""No bats test may negate a command with a bare `!` where bats does not read the negation's status.

bats runs a test body under `set -e` with an ERR trap, and bash exempts an inverted command from both, so `! grep -q x "$LOG"`
followed by another command checks nothing: the test passes whether or not the log contains x. As the test's last command it IS
checked, because bats reads the test function's return status; a helper's last command is checked where the helper is called under
errexit, a condition head where its branch fails the test, and so on through every position bash reads. PR #383 armed nineteen
such sites by hand and PR #403 one more; within a month three new ones had arrived, one each in tests/romp-headless.bats
(c2a5f844), tests/tmux-status-hook.bats (e0d76b85) and tests/romp.bats (989854c6), each asserting nothing.

The checked forms: `run <cmd>` followed by `[ "$status" -ne 0 ]` (tests/romp-postal.bats and tests/git-hermetic.bats write it
inline), a count for a pipeline (`[ "$(grep -c x "$LOG")" -eq 0 ]`), or `run ! <cmd>` in a file that declares
`bats_require_minimum_version 1.5.0`. `run` overwrites $status and $output, so an armed negation goes after any `[[ "$output" ... ]]`
check that reads the previous run.

The design (fork PR #871, after eight review rounds of fork PR #778 on a line scanner that modelled where bash reads a status and
was wrong in a new way each round): bats is the oracle and this module classifies nothing. It finds CANDIDATES, and bats decides
each one by running its test with the negated pipeline rewritten twice, to `! true` and to `! false`: the two files differ in one
word, so a test whose outcome differs under them read the negation's status (`read`: one `ok`, one `not ok` blamed inside the
candidate's own test, on the negation's line, on the line before a `( ! cmd )` subshell, or on the `[ ]` a saved `$?` reaches), one
passing under both asserted nothing, and both failing, a failure blamed outside the test, a run not ending within RUN_TIMEOUT or a
rewritten file bash does not parse is undecided and reported as such. The predicate over-approximates by construction: every `!`
standing as its own word in a test's text (_BANG: bounded by bash's metacharacters, the line's ends or a backtick, so
`!>/dev/null true`, `!(true)`, `` `! true` `` and a `!` alone on a line are words and `!=`, `$!` and `!cmd` are none), outside a
comment, a quoted string and a here-document's body, with no grammar of where a pipeline begins. Test bodies are
bash_test_extents, bash's own parse of the file as bats-preprocess rewrites it (an opener line's tail and a one-line test are in the
population). bats declares a test by either of two patterns, `@test "name" {` and `name() { # @test` (its BATS_TEST_PATTERN and
BATS_TEST_PATTERN_COMMENT; the second has no `^` and one group, the name, and is matched as bats matches it, by a search), and every
site here that reads an opener reads both (_test_line): before fork PR #871's commit 4 the module opened on the `@test` form alone,
so a test written the other way was run by bats and read by nothing here, and a file of one each was one test to it where bats ran
two. Comment, string and heredoc are bash's call too: the test's text up to the `!`, with ` || ||` appended, goes through
`bash -n` in the C locale (its English wording is what is read), which refuses the `||` token only in command text
(_command_context); a backtick substitution's text is opaque to bash -n, so a `!` inside one is a candidate whatever surrounds it,
and its pipeline ends at the closing backtick. Three exclusions are lexical, by the word before the `!`: `[ !`, `[[ !` and `run !`
(_OPERATOR_OF). A `!` that is another command's argument (`find . ! -name x`) is a candidate, and bats reports it as inert or
undecided: a false report on the visible side, none in the tree today. The one piece of grammar left is the negated pipeline's
extent: from the `!` to the line's first top-level `;`, `&&`, `||`, lone `&`, unmatched `)`, the closing backtick of the
substitution the `!` sits in, or comment, `|` and `|&` inside, a trailing `\` or `|` running on to the next line
(negated_pipeline_end), decided on the safe side and pinned by the register below; the rewrite keeps every `!` of a run (`! ! true`
negates twice, and bash reads a doubled negation's status) and replaces the command after it.

Over the 46 suites at this head (the population is the glob CI's shell job hands bats, `tests/*.bats`, read off
.github/workflows/ci.yml by the reading tests/test_ci_bats_bound.py pins that step with, and a glob naming no file raises rather
than passing an empty corpus as clean: suite_files; BatsSuites lists a file's candidates and judges none; BatsCorpus has bats decide
them): 232 `!` words file-wide, 191 of them `[ !`, 24 inside comments and strings (the word rule takes a `!` next to a backtick, a
`)` or a `>`), 5 at file scope, and 12 candidates in test bodies (bootstrap-sh.bats 184; install-optional-deps.bats 505;
install-sh.bats 329, 400, 411; pr-orphans.bats 125; romp-serve.bats 117, 309, 334, 382; romp-service.bats 683; romp-sessions.bats
84), listed in 5.20 s with the extents. bats reads all 12 (BatsCorpus, under 1.10.0 and 1.11.1): the nine at line start are `not
ok` on their own line under `! true` and `ok` under `! false`; the three condition heads of romp-serve.bats (309, 334 and 382, `if
! _dead "$pid"; then kill ...; return 1; fi`) the reverse, `ok` under `! true` and `not ok` on their own line under `! false`, so
they are read only through the second rewrite; 0 inert, 0 undecided, in 92.04 s on this box, 57.35 s of it the three heads' probe
tests, whose slowest single run is 13.00 s (romp-serve.bats 334 under `! true`), against which RUN_TIMEOUT stands at 60 s. The 5
file-scope `!` words sit in helpers and a setup (bats-state-isolation.bats 125, 126 and 129 twice; romp-postal.bats 47): outside
the subject, since a `!` there has no enclosing test to run alone. Two classes this instrument does not see: that file scope, and
a negation inside a string another shell runs (`eval "! true; true"`, `bash -c "! true; true"`), which is text to the predicate by
bash's reading of the test's own text (G_eval_string_mid and G_bash_c_string_mid, declared in the register). One class it reports
without deciding: a loop whose condition is the negation (`while ! cmd; do sleep 1; done`) never ends under one rewrite, so that run is
ended at RUN_TIMEOUT and the candidate reported undecided, its row's head printed before its runs so a run an outer bound ends is
attributable too; none in the tree today, by the 12 rows.

The register (ground_truth_shapes, BatsGroundTruth) is the gate on the three things the instrument still asserts. Recall: every `!`
character of a shape's tests is a candidate unless NOT_A_NEGATION declares it text or an operator, and a test recorded `ok` with no
candidate holds only declared `!` characters or none (NO_NEGATION); the expected set is every `!` character of the text, derived
from the shapes and the record and not from the predicate's word rule, so a spelling the predicate misses reds it whatever the rule
says. Agreement: with bats on PATH the shapes go through the corpus's own road (record_under_bats: candidates, extent, both
rewrites, one bats run) and the per-test verdicts must equal RECORDED, which holds both rewrites' columns and names the bats
versions it was verified against (RECORDED_WITH: 1.10.0 on this box and 1.11.1, CI's pin); the extent's terminators are pinned
there one shape each (`; true`, `|| ...`, `&& false`, a lone `&` before `wait %%`, the unmatched `)`, the closing backtick, a
comment holding operators, the continued line), so a split that runs past one changes a recorded verdict or loses one. Decision:
decide, asked about every test of the register holding one candidate from the same run's outcomes and blamed lines, reads every
test whose verdicts differ, calls inert every one passing under both and undecided every one failing under both, so its refusal of
a failure blamed outside the candidate's test fires on no deterministic shape (bash blames a `( ! cmd )` subshell's failure on the
line before it, a multi-line one's on the @test line, and a saved `$?` on the `[ ]` reading it, all inside the test; a register
reading verdicts alone was blind to that clause, and to a bats that blamed differently). Without bats those two skip, as the corpus
test does, naming CI's shell job, the one cell that installs bats, as where they run: tests/bats-bare-negation-shell-job.bats, a
wrapper the job's `bats tests/*.bats` picks up, runs the register class, the road class (the corpus road's pieces against bats: the
TAP reader, the bound on a run, the TERM to the process running one, a suite decided end to end) and the corpus test under python3
with every BATS_* variable unset (the job's BATS_TEST_TIMEOUT would otherwise hang a shape's bare `wait` on bats's timeout watcher)
and skips on the macOS cell, whose bash 3.2.57 and Homebrew bats 1.14.0 the record is not verified against; the inner bats resolves
through a PATH without the outer's libexec directory (_bats_env), since the entry point there expects the BATS_ROOT the scrub
removes and did not load under CI's /usr/local layout. Measured at this head: 381 shapes, 392 tests; under `! true` 234 ok
and 158 not ok, under `! false` 378 ok and 14 not ok (the four condition heads whose branch fails the test, `command _h` and
`env _h`, which find no shell function, `run ! true`, which run itself fails, the doubled negation mid and last, whose inversions
cancel, `! true && false` mid and last, the backgrounded negation whose job status `wait %%` reads, mid and last, and the status
saved with `rc=$?` and read by `[ ]`); decide over the 377 tests holding one candidate: 161 read, 213 inert, 3 undecided
(`command _h`, `env _h` and `! true && false` last, failing under both), the 5 holding two (the doubled and tripled negations,
`if ! _h` with its helper) and the 10 holding none not asked. The 250 shapes of the earlier register keep their 260 recorded
`! true` verdicts and are 260 ok under `! false`; every negation of the register is a candidate, the 139 recorded-inert line-start
sites the earlier register counted and every one off line start among them.

Deleted here, not fixed: the line scanner's frame model (the brace-depth walk, its block ends and the coverage pin over them), its
heredoc classification (introducers, delimiter words, the skip) and its status-read grammar (`_plain_call`, `_helper_read`,
`_read_position`, `_closes_a_condition`, `_trailer`, `_fallback_fails`, the compound closes), with the Scanner cases that pinned
them; the shapes those cases held that the register lacked are register shapes now, verdicts recorded. A new spelling costs one
shape and two bats runs, and can produce only a report a human reads, never a silent exemption.
"""
import collections
import glob
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock

from tests.test_ci_bats_bound import run_bats_step   # the one reading of the shell job's Run bats step: its pin and this population

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)   # the repository root, which the shell job's bats command and this module's suite paths are relative to

# bats-preprocess's two test patterns (bats-core 1.10.0 and 1.11.1, libexec/bats-core/bats-preprocess lines 34 and 35, the same text
# in both): a line matching either is rewritten into a function before bash parses the file, and is a test. bats matches them with
# `=~`, a search, so a pattern without `^` matches anywhere in the line. Every site here that reads an opener reads both
# (_test_line). BATS_TEST_PATTERN, `^[[:blank:]]*@test[[:blank:]]+(.*[^[:blank:]])[[:blank:]]+\{(.*)\$`: anchored, two groups,
# group(1) the name and group(2) whatever follows the brace (a comment, a command, a one-line body)
_TEST_LINE = re.compile(r"^[ \t]*@test[ \t]+(.*[^ \t])[ \t]+\{(.*)$")
# BATS_TEST_PATTERN_COMMENT, `[[:blank:]]*([^[:blank:]()]+)[[:blank:]]*\(?\)?[[:blank:]]+\{[[:blank:]]+#[[:blank:]]*@test[[:blank:]]*\$`:
# the function form `name() { # @test`, unanchored and with ONE group, the name (no blank or parenthesis in it; the parentheses
# optional, so `name { # @test` is a test too, and `function name { # @test` one named `name`, the leftmost match). Nothing but
# that comment follows the brace, and bats writes an empty body after bats_test_begin for it (`${BASH_REMATCH[2]:-}`). Before
# fork PR #871's commit 4 the module opened on the `@test` form alone: a test written this way was run by bats and read by nothing
# here, and a file of one each was one test to this module where bats ran two
_TEST_LINE_COMMENT = re.compile(r"[ \t]*([^ \t()]+)[ \t]*\(?\)?[ \t]+\{[ \t]+#[ \t]*@test[ \t]*$")
_TEST_OPENER = "_t() {"   # what a test's opener line is rewritten into here: the name dropped, the brace kept, the `@test` form's tail after it
_CLOSE_CANDIDATE = re.compile(r"^\s*\}")
# a `!` standing as its own word: bounded on each side by a blank, one of bash's other metacharacters (`|`, `&`, `;`, `(`, `)`,
# `<`, `>`), the line's start or end, or a backtick (a substitution's text begins and ends at one). So `!>/dev/null true`,
# `!(true)`, `! ! true`, `` `! true` `` and a `!` alone on a line (a pipeline of nothing, status 1) are words; `!=`, `$!` and `!cmd`
# are none. The rule is bash's word boundary, not a list of spellings: a `!` it takes that is no negation is a candidate bats
# reports, never a miss
_BANG = re.compile(r"(?<![^\s|&;()<>`])!(?=[\s|&;()<>`]|$)")
_ANY_BANG = re.compile("!")   # every `!` character: the register's expected set (BatsGroundTruth), which owes nothing to _BANG
# the word before a `!` that makes it an operator of `[` or `[[`, or bats's own inverted `run` (`run ! cmd` fails the test itself
# when cmd succeeds, in a file declaring bats_require_minimum_version 1.5.0), rather than a command's negation
_OPERATOR_OF = ("[", "[[", "run")
# what `bash -n` says of a test's text cut at a `!` with ` || ||` appended when the cut is in command text. Inside a quoted string
# or an arithmetic expansion it reports the unmatched delimiter instead, inside a here-document its end-of-file warning, inside a
# comment only the unclosed function, and inside `[[ ]]` a conditional command's error, none of them this phrase
_COMMAND_TEXT = "syntax error near unexpected token `||'"
# and inside backticks: bash -n reads a backtick substitution's text as opaque, so a `!` there is undecidable and taken as a
# candidate (the safe side; one inside a string inside backticks is a false candidate, which bats then reports as undecided)
_IN_BACKTICKS = "unexpected EOF while looking for matching ``'"

# a `!` word the predicate found in command text of a test: the test's index in bash_test_extents, the line index, the column, and
# whether it sits inside a backtick substitution, whose closing backtick then ends its pipeline (negated_pipeline_end)
Candidate = collections.namedtuple("Candidate", "test line col backticks")


def _bash_n(lines):
    """(exit status, stderr) of `bash -n` over these lines as a script, in the C locale: what is read off its stderr (_COMMAND_TEXT,
    _IN_BACKTICKS, the here-document warning) is bash's English wording, and under LC_ALL=C a localized bash prints that whatever
    LANG, LC_MESSAGES or LANGUAGE the environment names (gettext ignores them all for the C locale)."""
    r = subprocess.run(["bash", "-n"], input="\n".join(lines) + "\n", capture_output=True, text=True, env=dict(os.environ, LC_ALL="C"))
    return r.returncode, r.stderr


def _bash_parses(lines):
    """Whether bash parses these lines as a complete script: `bash -n` exits 0 and reports no here-document cut off by the end of
    the input (a warning, exit 0, so it is read off stderr)."""
    rc, err = _bash_n(lines)
    return rc == 0 and "delimited by end-of-file" not in err


def _bash_pending_heredoc(lines):
    """Whether bash, parsing these lines, is still inside a here-document at the end of the input (its warning names the case)."""
    return "delimited by end-of-file" in _bash_n(lines)[1]


def _test_line(line):
    """The match of whichever of bats-preprocess's two test patterns the line fits (_TEST_LINE, then _TEST_LINE_COMMENT, the order
    bats tries them), None for a line that is no test: bats reads a line as a test when `=~` finds either pattern in it, and `=~`
    is a search, so both are searched here (the `@test` pattern begins with `^`, so its search is a match at the line's start; the
    comment pattern's leftmost match makes `function name { # @test` a test named `name`, which a match at the start would miss).
    group(1) is the name under both, BASH_REMATCH[1] to bats."""
    return _TEST_LINE.search(line) or _TEST_LINE_COMMENT.search(line)


def _opener_tail(m):
    """What follows the opener's brace as the test's text, for a match _test_line made: group(2) under the `@test` pattern (a
    comment, a command, a one-line body); nothing under the comment form, whose one group is the name and after whose brace stands
    only the `# @test` comment, which bats-preprocess drops (it writes `${BASH_REMATCH[2]:-}`, empty there, after bats_test_begin)."""
    return m.group(2) if m.re is _TEST_LINE else ""


def _tail_start(m):
    """The column of the opener line at which the test's text begins, for a match _test_line made: where group(2) starts under the
    `@test` pattern; the line's end under the comment form, whose opener line carries no text of the test's."""
    return m.start(2) if m.re is _TEST_LINE else m.end()


def _renamed(line, name):
    """The test's opener line with its name replaced by `name`, under either pattern (_test_line): the first group's span, the
    quotes of a quoted `@test` name included, so the new name stands unquoted."""
    m = _test_line(line)
    return line[:m.start(1)] + name + line[m.end(1):]


def _rewritten(lines):
    """The lines with every test's opener line, under either pattern (_test_line), rewritten into a function opener as
    bats-preprocess does before bash parses the file: _TEST_OPENER and the `@test` form's tail, _TEST_OPENER alone for the comment
    form (an empty body, as bats writes it; `name { # @test`, no parentheses, is no function to bash until it is rewritten)."""
    return [(_TEST_OPENER + _opener_tail(m)) if (m := _test_line(l)) else l for l in lines]


def bash_test_extents(lines):
    """(open index, close index) for every test bash parses, from bash's own parse and not from this module's rules: every line
    matching either of bats-preprocess's two test patterns (_test_line) is rewritten into a function opener the way it does, an
    opener counts when the lines before it parse as a complete script (so one inside a heredoc, a quoted string or another test
    does not; the lines are read from the last point known to parse whole, the previous test's close, which is the same test by
    induction), and its close is its own line when the rewritten line parses whole on its own (a one-line test), else the first
    later line beginning with `}` at which the opener and the lines between parse as a complete function. None for the close: no
    such line (the file does not parse under this bash). One `bash -n` per opener plus one per candidate close, no execution."""
    rewritten = _rewritten(lines)
    extents, after = [], 0   # after: the first line not yet known to be parsed whole, so the lines before an opener are checked once each
    for o, line in enumerate(lines):
        if o < after or not _test_line(line):
            continue
        if not _bash_parses(rewritten[after:o]):   # the lines since the last known-complete point do not parse whole: not a top-level opener
            continue
        close = None
        if _bash_parses(rewritten[o:o + 1]):
            close = o
        else:
            for c in range(o + 1, len(lines)):
                if _CLOSE_CANDIDATE.match(lines[c]) and _bash_parses(rewritten[o:c + 1]):
                    close = c
                    break
        extents.append((o, close))
        after = (close if close is not None else len(lines)) + 1
    return extents


def _test_text(lines, o, c):
    """(line index, the column the test's text begins at) for every line of the test bash opens at lines[o] and closes at lines[c]:
    the opener line from just after its brace (a one-line test's whole body; nothing of a comment-form opener's, whose brace is
    followed by the `# @test` comment alone: _tail_start), then every line before the close from column 0. The close line is `}`
    and whatever follows it, which bash runs at file scope, so it is not the test's."""
    yield o, _tail_start(_test_line(lines[o]))
    for i in range(o + 1, c):
        yield i, 0


def _bangs(pattern, lines, o, c):
    """(line index, column) of every match of the pattern in the test's text (_test_text)."""
    for i, start in _test_text(lines, o, c):
        for m in pattern.finditer(lines[i], start):
            yield i, m.start()


def _test_bangs(lines, o, c):
    """(line index, column) of every `!` word (_BANG) in the test's text: the predicate's tokens. The register's expected set is
    every `!` character instead (_ANY_BANG through the same _bangs), so it owes nothing to this rule."""
    return _bangs(_BANG, lines, o, c)


def _word_before(line, j):
    """The word before column j of the line, blanks between skipped: "" at the line's start."""
    k = j
    while k > 0 and line[k - 1] in " \t":
        k -= 1
    s = k
    while s > 0 and line[s - 1] not in " \t":
        s -= 1
    return line[s:k]


def _command_context(rewritten, o, i, j):
    """Where column j of rewritten[i] stands to bash, given the test's lines from its rewritten opener rewritten[o]: the text up to
    there with ` || ||` appended goes through `bash -n`, which refuses the `||` token exactly where a command may begin
    (_COMMAND_TEXT) and reads on past it inside a quoted string, a here-document's body, a comment, an arithmetic expansion or a
    `[[ ]]`; inside backticks it reports the open backtick (_IN_BACKTICKS). "command" for command text, "backticks" for command
    text inside a backtick substitution (the candidate's pipeline ends at the closing backtick), None for anything else."""
    err = _bash_n(rewritten[o:i] + [rewritten[i][:j] + " || ||"])[1]
    return "backticks" if _IN_BACKTICKS in err else "command" if _COMMAND_TEXT in err else None


def candidates(lines, extents):
    """Every Candidate of the file, in order: a `!` word in a test's text (_test_bangs) that is not the operator of `[`, `[[` or
    `run` (the word before it, _OPERATOR_OF) and sits in command text by bash's own reading of the test up to it (_command_context):
    outside a comment, a quoted string and a here-document's body, wherever in a command it stands. Nothing here says whether the
    negation's status is read; bats does. Raises ValueError for a test bash cannot close: its text is unknown."""
    rewritten = _rewritten(lines)
    out = []
    for t, (o, c) in enumerate(extents):
        if c is None:
            raise ValueError("line %d: bash finds no close for this test (the file does not parse under bash -n); its text is unknown" % (o + 1))
        # the opener's columns move when the name is dropped; a comment-form opener's line holds no text of the test's, so no `!` of it
        # reaches here
        shift = len(_TEST_OPENER) - _tail_start(_test_line(lines[o]))
        for i, j in _test_bangs(lines, o, c):
            if _word_before(lines[i], j) in _OPERATOR_OF:
                continue
            context = _command_context(rewritten, o, i, j + shift if i == o else j)
            if context:
                out.append(Candidate(t, i, j, context == "backticks"))
    return out


def negated_pipeline_end(lines, cand):
    r"""(line index, column) just past the negated pipeline that begins at the candidate's `!`, trailing blanks excluded: it ends at
    the first `;`, `&&`, `||`, lone `&` (a redirection's `&>`, `>&` or `<&` is none), unmatched `)` or comment outside quotes and
    parentheses, else at its line's end; `|` and `|&` are inside it, and it runs on to the next line while a quote or a parenthesis
    is open or the line ends in `\` or in `|`. For a `!` inside a backtick substitution (cand.backticks) the first backtick not
    escaped by a backslash ends it, whatever quote is open, since that is where bash closes the substitution. None when it runs off
    the end of the text: undecided, the safe side."""
    i, j, q, depth = cand.line, cand.col + 1, None, 0
    while i < len(lines):
        line, n, more = lines[i], len(lines[i]), False
        while j < n:
            ch = line[j]
            if cand.backticks and ch == "`":
                return i, len(line[:j].rstrip())
            if q == "'":
                if ch == "'":
                    q = None
            elif q == '"':
                if ch == "\\":
                    j += 1
                elif ch == '"':
                    q = None
            elif ch == "\\":
                more = j == n - 1
                j += 1
            elif ch in "'\"":
                q = ch
            elif ch == "(":
                depth += 1
            elif ch == ")" and depth:
                depth -= 1
            elif depth == 0 and (ch in ";)" or line.startswith(("&&", "||"), j)
                                 or (ch == "&" and not line.startswith("&>", j) and not (j and line[j - 1] in "<>"))
                                 or (ch == "#" and (j == 0 or line[j - 1] in " \t"))):
                return i, len(line[:j].rstrip())
            elif depth == 0 and ch == "|":
                if line.startswith("|&", j):
                    j += 1
                more = not line[j + 1:].strip()
            j += 1
        if not (more or q or depth):
            return i, len(line.rstrip())
        i, j = i + 1, 0
    return None


def _bang_run(line, j):
    """The number of `!` words (_BANG) in the run beginning at column j of the line, blanks between them: 1 for `! true`, 2 for
    `! ! true`."""
    k = 0
    while j < len(line) and _BANG.match(line, j):
        k, j = k + 1, j + 1
        while j < len(line) and line[j] in " \t":
            j += 1
    return k


def rewritten_negation(lines, cand, end, repl):
    """The lines with the negated pipeline from the candidate's `!` to end (negated_pipeline_end) replaced by repl, the line count
    kept: a continuation line the pipeline ran onto is left empty, and what followed the pipeline on its last line follows repl.
    Every `!` of the run at the candidate stays before repl (`! ! true` becomes `! ! false`): bash reads a doubled negation's
    status and exempts a tripled one, so the run is part of what bats is asked about, and the command after it is what is replaced."""
    ei, ej = end
    tail = lines[ei][ej:]
    if ei != cand.line and tail and not tail[0].isspace():
        tail = " " + tail
    out = list(lines)
    out[cand.line] = lines[cand.line][:cand.col] + "! " * (_bang_run(lines[cand.line], cand.col) - 1) + repl + tail
    for k in range(cand.line + 1, ei + 1):
        out[k] = ""
    return out


def rewrite(lines, cand, repl):
    """The file's lines with the candidate's negated pipeline rewritten to repl: its extent (negated_pipeline_end) replaced
    (rewritten_negation), the line count kept. None when the pipeline runs off the end of the text: undecided, the safe side. The
    one road every rewrite takes, the corpus's per-candidate one (BatsCorpus) and the register's (rewritten_shape)."""
    end = negated_pipeline_end(lines, cand)
    return None if end is None else rewritten_negation(lines, cand, end, repl)


def rewritten_shape(lines, extents, repl):
    """The file with every candidate's negated pipeline rewritten to repl (rewrite), the last first so the earlier ones' positions
    hold (an outer negation's pipeline may hold an inner one); each extent is read on the text as it stands when its turn comes.
    Raises ValueError when a candidate's pipeline runs off the end of the text."""
    out = list(lines)
    for cand in sorted(candidates(lines, extents), reverse=True):
        new = rewrite(out, cand, repl)
        if new is None:
            raise ValueError("line %d: the negated pipeline runs off the end of the text" % (cand.line + 1))
        out = new
    return out


def suite_globs(root=ROOT):
    """The patterns CI's shell job hands bats, read off the Run bats step's command in the workflow under root
    (.github/workflows/ci.yml) by the reading tests/test_ci_bats_bound.py pins that step with (run_bats_step, imported, so the
    two read one text one way): every word of the command after `bats` that is not an option. `tests/*.bats` today. Raises
    LookupError when the step is not found or its command names no suite."""
    _, cmd = run_bats_step(os.path.join(root, ".github", "workflows", "ci.yml"))
    patterns = [w for w in shlex.split(cmd)[1:] if not w.startswith("-")]
    if not patterns:
        raise LookupError("the Run bats step's command names no suite: %r" % cmd)
    return patterns


def suite_files(root=ROOT):
    """The population of suites, as paths relative to root: every file the shell job's bats globs name (suite_globs), each
    expanded under root as the job's shell expands it, sorted, each once. Raises LookupError, naming every pattern that names no
    file, when any one does: the job's bash hands bats an unmatched glob as the literal word and bats reds on it (`bats: cd: other:
    No such file or directory` for a missing directory, `Error: Test file ".../other/*.bats" does not exist` for one holding no
    match, under 1.10.0), so this reds on the same glob; a population derived from a pattern that matches nothing must red, never
    pass as a clean corpus (extra4-1 of fork PR #778's round 8: the suite tests asserted agreement over whatever they enumerated and
    pinned the population nowhere, so an empty corpus printed `0 files` and passed; a hand-kept floor was refused there, since the
    corpus has shrunk legitimately once and a suite added under a widened glob would be missed), and the check is per glob, not
    over their union (round 1 of fork PR #871: the union raised only when every glob was dead, so one glob going empty beside a
    live one narrowed the population silently where the job reds). The one derivation both suite tests read (BatsSuites,
    BatsCorpus); tests/bats-bare-negation-shell-job.bats, the wrapper that runs them in the job, is in it."""
    patterns = suite_globs(root)
    found = {pat: glob.glob(os.path.join(root, pat)) for pat in patterns}
    dead = [pat for pat in patterns if not found[pat]]
    if dead:
        raise LookupError("the shell job's bats glob (%s) names no file under %s: bats reds on the unmatched word, and the population "
                          "would be short its suites" % (" ".join(dead), root))
    return sorted({os.path.relpath(p, root) for paths in found.values() for p in paths})


def _read_suite(relpath, root=ROOT):
    """(lines, extents) of the suite at relpath under root: its text split at newlines and bash's parse of its tests
    (bash_test_extents)."""
    with open(os.path.join(root, relpath), encoding="utf-8") as f:
        lines = f.read().split("\n")
    return lines, bash_test_extents(lines)


def unopened_test_lines(lines, extents):
    """The indices of the lines bats-preprocess rewrites into a test, under either pattern (_test_line), that bash does not open as
    one (bash_test_extents): a fixture line inside a heredoc, a quoted string or another test. bats declares a test for each and
    runs a file that is not the one on disk, so the suite test names them (FIXTURE_LINE_REMEDY)."""
    opened = {o for o, _ in extents}
    return [i for i, line in enumerate(lines) if _test_line(line) and i not in opened]


def _test_name(line):
    """The test's name as bats-preprocess reads it off its opener line, under either pattern (_test_line): the first group with one
    `'` or `"` stripped from each end (it strips one character at each end, whatever the pairing, under both forms), the text as
    written and not as bash expands it, which is what a `-f` filter is matched against. `first` for `first() { # @test`."""
    name = _test_line(line).group(1)
    if name[:1] in "'\"":
        name = name[1:]
    if name[-1:] in "'\"":
        name = name[:-1]
    return name


def _ere_literal(text):
    """The text as an extended regular expression matching it literally: every ERE metacharacter escaped (bats matches `-f` with
    bash's `=~`)."""
    return re.sub(r"[][\\^$.|?*+(){}]", r"\\\g<0>", text)


def _bats_env(scratch):
    """The environment for a bats run of this module's: every BATS_* variable unset (under BATS_TEST_TIMEOUT bats's timeout watcher
    is a background child of the test, and a bare `wait` in a test waits on it: the register's D_bg hung to a 40 s kill with the
    variable set and passed in 0.07 s without; a nested bats must also not read the outer run's BATS_ROOT, BATS_RUN_TMPDIR and the
    rest); every directory on PATH holding bats's libexec entry point dropped from it (an outer bats prepends its libexec
    directory to PATH, and the `bats` there, beside bats-exec-test, is the entry point that expects the BATS_ROOT its bin wrapper
    exported, which the strip above removes; the wrapper's own scrub removes BATS_LIBEXEC with the rest before python starts, so
    the directory is known by what it holds and not by that variable; with it gone `bats` resolves to a wrapper again. Left in
    place, the inner bats ran with BATS_ROOT empty: on this box, whose bats lives under /usr and whose /lib is /usr/lib, that only
    put the frames of an `exit` and of a teardown failure on bats-exec-test's own lines, since the frames bats drops are those under
    $BATS_ROOT/lib and libexec, and under CI's /usr/local prefix the inner bats did not load at all, `//bats-core/validator.bash: No
    such file or directory`, measured with 1.11.1 from a scratch prefix as the outer and the inner bats); HOME and TMPDIR each a
    fresh directory under the scratch one, so a test reads and writes no state of this machine's. A bats started with this
    environment resolves through its PATH (Popen looks the executable up in the environment it is given)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BATS_")}
    if "PATH" in env:
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep) if not os.path.isfile(os.path.join(p, "bats-exec-test")))
    for var, sub in (("HOME", "home"), ("TMPDIR", "tmp")):
        env[var] = os.path.join(scratch, sub)
        os.makedirs(env[var], exist_ok=True)
    return env


# one bats run of a test alone: the outcome (`ok`, `not ok`, or why bats gave no verdict: `skipped`, `did not load`, `no such
# test`, `N tests`, `no TAP`, `timed out`), the 1-based line bats blames for a `not ok` (the innermost frame of its trace) and the
# file it names there, the TAP and stderr text, and the wall time
BatsRun = collections.namedtuple("BatsRun", "outcome line file detail secs")
_TAP_TEST = re.compile(r"^(ok|not ok) \d+ (.*)$")
_TAP_SKIP = re.compile(r"^ok \d+ .* # skip( |$)")
_TAP_FRAME = re.compile(r"^# \((?:from function `[^']*' )?in (?:test )?file (\S+), line (\d+)")
# the bound on one bats run of the corpus road, in seconds. A rewrite that does not terminate (a loop whose condition is the
# negation, `while ! cmd; do sleep 1; done`, runs forever under `! false`, and `until ! cmd` under `! true`) would otherwise hang
# the oracle with no verdict and no row: under pytest forever, and in CI's shell job to the wrapper test's BATS_TEST_TIMEOUT
# (180 s), which names the wrapper and no candidate and ends python alone (bats's pkill -P reaches a test's direct children),
# leaving the inner bats and the loop running. A run ended at this bound is `timed out`: undecided, reported with its candidate.
# The bound stands against the slowest legitimate run of the corpus, a romp-serve.bats probe test (line 334, 12.95 s under
# `! true` on a loaded box), and under the corpus's whole time here (90.67 s), so one run ended at it still ends the corpus
# test inside the wrapper's 180 s on this box
RUN_TIMEOUT = 60
# the bound on the register's one run over every shape: every shape terminates, so a run past it is an error and not a verdict, a
# backstop for a run with no outer bound (pytest)
REGISTER_TIMEOUT = 900


def _end_group(p, grace=5.0):
    """Ends the process group the process p leads (a Popen with start_new_session): TERM to the group, under which bats's EXIT
    traps run and so does a test's teardown (measured: a teardown's marker file is written under TERM and not under KILL), then
    KILL to whatever of it is left after grace seconds."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            return
        try:
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue


def _run_bats(args, cwd, env, timeout):
    """(stdout, stderr, whether the bound ended it, the exit status, seconds) of one bats process, stdin /dev/null, in its own
    process group and bounded: past timeout seconds the group is ended (_end_group) and what bats had written comes back with the
    flag set. A TERM to this process while the run is on (the wrapper test's BATS_TEST_TIMEOUT ends a test's direct children, the
    python running the module, and nothing below them) ends the group first and then takes its course, so no bats this module
    started outlives it; the handler is installed for the run and on the main thread only, the one a handler can be set from."""
    t0 = time.monotonic()
    p = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                         start_new_session=True)

    def on_term(signum, frame):
        _end_group(p)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTERM)

    main = threading.current_thread() is threading.main_thread()
    previous = signal.signal(signal.SIGTERM, on_term) if main else None
    try:
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _end_group(p)
            out, err = p.communicate()
            return out, err, True, p.returncode, time.monotonic() - t0
        return out, err, False, p.returncode, time.monotonic() - t0
    finally:
        if main:
            signal.signal(signal.SIGTERM, previous)


def _frame(out, i):
    """(1-based line, file) the frame line after the TAP line out[i] blames, the innermost of bats's trace, or (None, None)."""
    m = _TAP_FRAME.match(out[i + 1]) if i + 1 < len(out) else None
    return (int(m.group(2)), m.group(1)) if m else (None, None)


def run_test_alone(tree, relpath, name, scratch, bats="bats", timeout=RUN_TIMEOUT):
    """The test named `name` of the suite at relpath, run alone under bats with the tree as cwd (`bats -t -f '^<name>$' <relpath>`,
    the name matched literally: _ere_literal), stdin /dev/null and the environment _bats_env gives, bounded at timeout seconds
    (_run_bats). Read off the TAP: exactly one test line is a verdict, `ok` (a skipped one is not: `skipped`, with bats's reason)
    or `not ok` with the line the first frame of bats's trace blames, the candidate's own or a caller's or a callee's; `not ok N
    setup_file failed` (bats 1.10.0, on stdout) or `not ok N bats-gather-tests` (1.11.1, on stderr) is a file bash could not load
    (`did not load`); no test line is `no such test` (bats printed `1..0`) or `no TAP`; more than one is `N tests`; a run the
    bound ended is `timed out`. The detail carries the TAP after the plan line and bats's stderr, for the report."""
    out_text, err_text, ended, status, secs = _run_bats([bats, "-t", "-f", "^%s$" % _ere_literal(name), relpath], tree, _bats_env(scratch), timeout)
    out = out_text.splitlines()
    detail = "\n".join([l for l in out if not re.match(r"^1\.\.\d+$", l)] + [l for l in err_text.splitlines() if l.strip()])
    if ended:
        return BatsRun("timed out", None, None, detail or "(nothing beyond the plan line)", secs)
    if re.search(r"^not ok \d+ (setup_file failed|bats-gather-tests)", out_text + "\n" + err_text, re.M):   # 1.11.1 prints its line on stderr
        return BatsRun("did not load", None, None, detail, secs)
    tests = [i for i, l in enumerate(out) if _TAP_TEST.match(l)]
    if not tests:
        return BatsRun("no such test" if any(l == "1..0" for l in out) else "no TAP", None, None, detail or "(bats printed nothing; exit %d)" % status, secs)
    if len(tests) > 1:
        return BatsRun("%d tests" % len(tests), None, None, detail, secs)
    i = tests[0]
    if out[i].startswith("ok "):
        return BatsRun("skipped" if _TAP_SKIP.match(out[i]) else "ok", None, None, detail, secs)
    line, file = _frame(out, i)
    return BatsRun("not ok", line, file, detail, secs)


REWRITES = (("! true", "the negated command succeeding"), ("! false", "the negated command failing"))


def decide(relpath, cand, extent, runs):
    """(verdict, message) for a candidate from its two runs (BatsRun under `! true` and under `! false`, in REWRITES' order) and
    its test's extent (bash_test_extents' (open, close) pair). The two rewritten files differ in one word, `true` against `false`,
    so a test whose outcome differs under them read that status somewhere: `read`, no report, when one run is `ok` and the other
    `not ok` with the failure blamed inside the candidate's own test, its file and a line from the test's opener to its close (the
    candidate's own line; the line before a `( ! cmd )` subshell, which bash blames for the compound's failure; the `[ "$rc" -eq 1 ]`
    a status saved with `rc=$?` reaches). `inert` when the test passes under both, the negation asserting nothing, a defect.
    `undecided`, a report too, for everything else: `not ok` under both (the failure does not turn on this negation), a failure
    blamed outside the test (a setup, a teardown, a loaded file, another test: the status may have reached there, or the failure
    is unrelated to it), and a run bats gave no verdict on (a skip, a file that did not load, no such test, a run the bound ended,
    a rewrite bash does not parse). The message says which, so a maintainer can tell a negation bats read as inert from a position
    this instrument could not decide (fork PR #778 round 8, Group C's rule)."""
    for (what, _), run in zip(REWRITES, runs):
        if run.outcome not in ("ok", "not ok"):
            why = (run.detail if run.outcome == "no run" else
                   "the run was ended after %.0f s with no verdict: a rewrite that does not terminate is one cause, a loop whose "
                   "condition is this negation running forever under one of the two" % run.secs if run.outcome == "timed out" else
                   "the outcome was `%s`" % run.outcome)
            return "undecided", "under `%s` bats gave no verdict on the test: %s; nothing was decided" % (what, why)
    if all(run.outcome == "ok" for run in runs):
        return "inert", "the test passes with the negated command succeeding and with it failing: this negation asserts nothing"
    if all(run.outcome == "not ok" for run in runs):
        return "undecided", "the test fails under both rewrites (blamed on line %s and line %s): its failure does not turn on this negation" % (
            runs[0].line, runs[1].line)
    failing = runs[0] if runs[0].outcome == "not ok" else runs[1]
    o, c = extent
    if failing.file != relpath or failing.line is None or not o + 1 <= failing.line <= c + 1:
        return "undecided", ("the outcomes differ under the two rewrites, but the failing one is blamed on %s line %s, outside the candidate's "
                             "test (%s lines %d to %d): either the negation's status reached there or the failure is unrelated to it" % (
                                 failing.file, failing.line, relpath, o + 1, c + 1))
    return "read", "the test's outcome turns on this negation"


# what became of one candidate of the corpus: the suite's path (tests/<name>), the candidate, its enclosing test's name, the
# verdict and message (decide), the candidate's line under each rewrite, the two runs, and the seconds the runs took together
Decision = collections.namedtuple("Decision", "relpath cand test verdict message rewritten runs secs")


def decide_under_bats(root, relpath, lines, extents, cand, scratch, bats="bats", timeout=RUN_TIMEOUT):
    """One candidate decided by bats: for each rewrite of REWRITES the tree at root is copied whole into a fresh directory under
    scratch (without `.git`, `node_modules` and python caches, none of which a suite reads; the shell job's checkout has no
    node_modules when bats runs), the suite in the copy is replaced by the rewritten file (rewrite), and the enclosing test runs
    alone there (run_test_alone, bounded at timeout seconds). A rewritten file bash does not parse, or a pipeline running off the
    text, is decided without a run: undecided. Each copy is removed after its run."""
    o, _ = extents[cand.test]
    test = _test_name(lines[o])
    runs, shown = [], []
    for k, (repl, _) in enumerate(REWRITES):
        new = rewrite(lines, cand, repl)
        if new is None:
            runs.append(BatsRun("no run", None, None, "the negated pipeline runs off the end of the text", 0.0))
            shown.append(lines[cand.line])
            continue
        shown.append(new[cand.line])
        if not _bash_parses(_rewritten(new)):
            runs.append(BatsRun("no run", None, None, "the rewritten file does not parse under bash -n: %s" % _bash_n(_rewritten(new))[1].strip(), 0.0))
            continue
        d = os.path.join(scratch, "%s.%d.%d" % (os.path.basename(relpath), cand.line + 1, k))
        tree = os.path.join(d, "tree")
        shutil.copytree(root, tree, symlinks=True, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".pytest_cache"))
        with open(os.path.join(tree, relpath), "w", encoding="utf-8") as f:
            f.write("\n".join(new))
        try:
            runs.append(run_test_alone(tree, relpath, test, d, bats, timeout))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    verdict, message = decide(relpath, cand, extents[cand.test], runs)
    return Decision(relpath, cand, test, verdict, message, shown, runs, sum(r.secs for r in runs))


def _shown(run):
    """A run's outcome for the table: `ok`, `not ok @<line>`, or why there was no verdict."""
    return "not ok @%s" % run.line if run.outcome == "not ok" else run.outcome


def _row(d):
    """A decision's row in the corpus table, after its head (`<path>:<line> `): the verdict, both outcomes, each run's seconds and
    the candidate's line under `! true`."""
    return "%-9s `! true` %s, `! false` %s  (%.2f + %.2f s)  %s" % (d.verdict, _shown(d.runs[0]), _shown(d.runs[1]), d.runs[0].secs, d.runs[1].secs,
                                                                   d.rewritten[0].strip())


def report(d):
    """A decision's report in full: the verdict and its message, the line as written and under each rewrite with bats's outcome,
    and what bats said under each."""
    head = ["%s:%d in test %r: %s: %s" % (d.relpath, d.cand.line + 1, d.test, d.verdict.upper(), d.message)]
    body = ["    under `%s`: %s  ->  %s" % (repl, shown.strip(), _shown(run)) for (repl, _), shown, run in zip(REWRITES, d.rewritten, d.runs)]
    said = ["    bats under `%s` said:\n%s" % (repl, "\n".join("        " + l for l in run.detail.splitlines()) or "        (nothing)")
            for (repl, _), run in zip(REWRITES, d.runs)]
    return "\n".join(head + body + said)


FIXTURE_LINE_REMEDY = ("bats-preprocess rewrites every line matching its test pattern wherever it sits, a heredoc or a string included, "
                       "so a fixture cannot carry such a line literally (it reaches the disk rewritten and the file declares a test it "
                       "never runs); write it through printf, or spell the line so that neither pattern takes it: a `@test` line begun "
                       "with another word, a `name() { # @test` line with a word after `@test` in its comment")


class BatsSuites(unittest.TestCase):
    def test_every_test_of_every_suite_is_closed_by_bash_and_its_candidates_are_listed(self):
        # the population is every suite the shell job's bats glob names (suite_files, read off the workflow; a glob naming no file
        # raises there); per file, bash's own parse (bash_test_extents) is the derivation of each test's text: a test bash cannot
        # close, or a line bats-preprocess rewrites into a test, under either of its patterns, that bash does not open as one (a
        # fixture heredoc holding a `@test` line or a `name() { # @test` line), is a problem named here, since the candidates of
        # such a file cannot be derived. The candidates themselves are listed, not judged: bats judges them, where it is installed
        self.assertTrue(shutil.which("bash"), "bash is what bats runs tests under; without it nothing here can be derived")
        files = suite_files()
        problems, report, tests, total = [], [], 0, 0
        t0 = time.monotonic()
        for name in files:
            lines, extents = _read_suite(name)
            for i in unopened_test_lines(lines, extents):
                problems.append("%s:%d: a line bats-preprocess rewrites into a test that bash does not open as one (inside a heredoc, "
                                "a quoted string or another test); %s" % (name, i + 1, FIXTURE_LINE_REMEDY))
            for o, c in extents:
                if c is None:
                    problems.append("%s:%d: bash finds no close for this test (the file does not parse under this bash -n); its text is "
                                    "unknown and no candidate of it can be derived" % (name, o + 1))
            if any(c is None for _, c in extents):
                continue
            found = candidates(lines, extents)
            report.append("%s: %d tests, %d candidates%s" % (name, len(extents), len(found), "".join(" :%d" % (c.line + 1) for c in found)))
            tests, total = tests + len(extents), total + len(found)
        report.append("%d files: %d tests, %d candidates, in %.2f s" % (len(files), tests, total, time.monotonic() - t0))
        print("\n".join(report))
        self.assertEqual(problems, [], "tests whose text bash cannot derive:\n" + "\n".join(problems) + "\n\n" + "\n".join(report))


class Population(unittest.TestCase):
    """suite_files on scratch roots: the population is the globs the shell job's Run bats step hands bats, as the workflow under
    the root states it, expanded there; any glob naming no file, or a workflow without the step, raises instead of passing as a
    clean or a narrowed corpus (extra4-1 of fork PR #778's round 8; round 1 of fork PR #871)."""

    WORKFLOW = ("jobs:\n  shell:\n    steps:\n      - name: Run bats\n        env:\n          BATS_TEST_TIMEOUT: \"180\"\n"
                "        run: bats --print-output-on-failure %s\n")

    def root(self, d, globs, files):
        """A scratch root under d: a workflow whose Run bats step hands bats `globs`, and the empty files listed, by relative path."""
        os.makedirs(os.path.join(d, ".github", "workflows"))
        with open(os.path.join(d, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as f:
            f.write(self.WORKFLOW % globs)
        for rel in files:
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            open(os.path.join(d, rel), "w").close()

    def test_the_population_is_what_the_workflow_hands_bats_and_an_empty_one_raises(self):
        with tempfile.TemporaryDirectory() as d:
            self.root(d, "tests/*.bats", ["tests/b.bats", "tests/a.bats", "tests/c.bash", "other/d.bats"])
            self.assertEqual(suite_globs(d), ["tests/*.bats"])
            self.assertEqual(suite_files(d), ["tests/a.bats", "tests/b.bats"])
        with tempfile.TemporaryDirectory() as d:
            self.root(d, "tests/*.bats other/*.bats", ["tests/a.bats", "other/d.bats", "other/e.bats"])
            self.assertEqual(suite_files(d), ["other/d.bats", "other/e.bats", "tests/a.bats"])
        with tempfile.TemporaryDirectory() as d:
            self.root(d, "tests/*.bats", ["tests/a.bash"])
            with self.assertRaises(LookupError) as cm:
                suite_files(d)
            self.assertIn("the shell job's bats glob (tests/*.bats) names no file under", str(cm.exception))
        with tempfile.TemporaryDirectory() as d:
            self.root(d, "tests/*.bats", ["tests/a.bats"])
            with open(os.path.join(d, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as f:
                f.write("jobs:\n  shell:\n    steps:\n      - name: Run the bats suites\n        run: bats tests/*.bats\n")
            with self.assertRaises(LookupError) as cm:
                suite_files(d)
            self.assertIn("the Run bats step moved or was renamed", str(cm.exception))
        # the real root: the population is read off the checked-in workflow, and the wrapper that runs the suite tests in the job
        # is one of the suites
        self.assertEqual(suite_globs(), ["tests/*.bats"])
        self.assertIn("tests/bats-bare-negation-shell-job.bats", suite_files())

    def test_a_dead_glob_beside_a_live_one_raises_naming_the_dead_one(self):
        # the job's bash hands bats an unmatched glob as the literal word and bats reds on it, whether the directory is missing
        # (`bats: cd: other: No such file or directory`) or holds no match (`Error: Test file ".../other/*.bats" does not exist`);
        # the union raised only when every glob was dead, so a dead glob beside a live one narrowed the population silently where
        # the job reds (round 1 of fork PR #871). The dead pattern is named and the live one is not; two dead are both named
        for files in (["tests/a.bats"], ["tests/a.bats", "other/d.bash"]):
            with tempfile.TemporaryDirectory() as d:
                self.root(d, "tests/*.bats other/*.bats", files)
                with self.assertRaises(LookupError) as cm:
                    suite_files(d)
                self.assertIn("the shell job's bats glob (other/*.bats) names no file under", str(cm.exception))
                self.assertNotIn("tests/*.bats", str(cm.exception))
        with tempfile.TemporaryDirectory() as d:
            self.root(d, "tests/*.bats other/*.bats", ["tests/a.bash", "other/d.bash"])
            with self.assertRaises(LookupError) as cm:
                suite_files(d)
            self.assertIn("the shell job's bats glob (tests/*.bats other/*.bats) names no file under", str(cm.exception))


class Extents(unittest.TestCase):
    """bash_test_extents on synthetic files: bash's parse, not this module's rules, decides what a test is and where it ends."""

    def test_bash_test_extents_reads_the_tests_bash_parses(self):
        # opens inside a heredoc, a string or another test are not tests; a one-line @test is rewritten so the file parses and is
        # an extent of no lines; a file that does not parse yields None for the close
        text = ('setup() {\n    cat <<EOF\n@test "not one" {\n}\nEOF\n}\n@test "one" {\n    x="\n@test \\"nor this\\" {\n"\n}\n'
                '@test "two" { true; }\n@test "three" {\n  true\n  }\n')
        lines = text.split("\n")
        self.assertEqual(bash_test_extents(lines), [(6, 10), (11, 11), (12, 14)])
        self.assertEqual(bash_test_extents('@test "x" {\n    echo "\n'.split("\n")), [(0, None)])

    def test_both_declaration_forms_open_a_test_as_bats_runs_both(self):
        # tests-1 of fork PR #778's round 8: bats runs a test declared `name() { # @test` (bats-preprocess's second pattern) as it
        # runs one declared `@test "name" {`, and the module opened on the `@test` form alone, so a file of one each was one test
        # here, [(5, 8)], where bats ran two (`1..2`), the first's body outside every derivation. Both open now, at every site: the
        # extents; the rewrite (an empty body for the comment form, the `# @test` dropped as bats drops it; `fourth { # @test`,
        # no parentheses, is a test to bats and no function to bash until rewritten); the test's text (nothing on a comment-form
        # opener's line); the candidates; the name a `-f` filter is matched against (the leftmost match, `third` under the
        # `function` keyword, which a match at the line's start misses); the rename the register makes; and the guard on a test
        # line bash does not open. A word after `@test` in the comment, or no blank between the brace and the `#`, is no test
        text = ('first() { # @test\n    ! true\n    true\n}\n\n@test "second" {\n    true\n    ! true\n}\n\n'
                'function third { # @test\n    true\n}\n\nfourth { # @test\n    true\n}\n  fifth() {  #  @test\n    true\n}\n'
                '@test "sixth" {\n    cat <<EOF\nfake() { # @test\nEOF\n}\n')
        lines = text.split("\n")
        extents = bash_test_extents(lines)
        self.assertEqual(extents, [(0, 3), (5, 8), (10, 12), (14, 16), (17, 19), (20, 24)])
        self.assertEqual(bash_test_extents(lines[:9]), [(0, 3), (5, 8)])
        self.assertEqual([_rewritten(lines)[o] for o, _ in extents], ["_t() {"] * 6)
        self.assertEqual([_test_name(lines[o]) for o, _ in extents], ["first", "second", "third", "fourth", "fifth", "sixth"])
        self.assertEqual(list(_test_text(lines, 0, 3)), [(0, len("first() { # @test")), (1, 0), (2, 0)])
        self.assertEqual(candidates(lines, extents), [Candidate(0, 1, 4, False), Candidate(1, 7, 4, False)])
        self.assertEqual(unopened_test_lines(lines, extents), [22])
        self.assertIsNone(_test_line("x() { # @test fixture"))
        self.assertIsNone(_test_line("x() {# @test"))
        self.assertEqual(_renamed("first() { # @test", "s000_t_t1"), "s000_t_t1() { # @test")
        self.assertEqual(_renamed("function third { # @test", "s000_t_t1"), "function s000_t_t1 { # @test")
        self.assertEqual(_renamed('@test "x" { true; }', "s000_t_t1"), "@test s000_t_t1 { true; }")

    def test_a_heredoc_whose_terminator_comes_after_the_next_test_leaves_the_file_unparsed(self):
        # the `<<WORD` swallows the test's close and the next test whole; bash finds no close for the first test and no second test
        text = '@test "a" {\n    cat <<WORD\n    ! true\n    true\n}\n\n@test "b" {\n    true\n}\nWORD\n'
        self.assertEqual(bash_test_extents(text.split("\n")), [(0, None)])

    def test_a_prefix_cut_inside_a_file_scope_heredoc_is_read_as_incomplete(self):
        # `bash -n` exits 0 on a prefix cut inside a heredoc and only warns, so the parse is read off stderr too; on the exit code
        # alone the fixture line inside the file-scope heredoc would count as a test
        text = 'cat <<EOF\n@test "inner" {\nEOF\n\n@test "real" {\n    ! true\n    true\n}\n'
        self.assertEqual(bash_test_extents(text.split("\n")), [(4, 7)])


class Candidates(unittest.TestCase):
    """The predicate and the rewrite on synthetic snippets: what the register cannot say (columns, the refusal of an unparsed test,
    the extent's end positions and the None past the text). Whether a candidate's status is read is not asked here."""

    SNIPPET = ('@test "one-liner" { ! true; }\n'
               '@test "opener tail" { ! true\n'
               '    true\n'
               '}\n'
               '@test "x" {\n'
               '    # ! in a comment\n'
               '    echo " ! in a string" \' ! and another\' > /dev/null\n'
               "    cat > /dev/null <<'EOF'\n"
               '! heredoc text\n'
               'EOF\n'
               '    [ ! -s /dev/null ]\n'
               '    [[ ! -s /dev/null ]]\n'
               '    run ! true\n'
               '    x=$(( ! 0 ))\n'
               '    [ "$x" != 0 ]\n'
               '    echo "$!" > /dev/null\n'
               '    if ! true; then true; fi\n'
               '    y=$(! true)\n'
               '    ( ! true )\n'
               '    ! true\n'
               "    z=`echo ' ! in a string in backticks'`\n"
               '}\n')

    # the one-liner's and the opener tail's `!`, then in the third test: a condition head, a substitution, an inline subshell, a
    # line-start negation, and the `!` inside backticks (opaque to bash -n, a candidate whatever quotes surround it, and the one
    # whose pipeline ends at the closing backtick). Not: the comment, the strings, the heredoc text, `[`'s and `[[`'s and `run`'s
    # operators, the arithmetic `!`, `!=` and `$!`
    EXPECTED = [Candidate(0, 0, 20, False), Candidate(1, 1, 22, False), Candidate(2, 16, 7, False), Candidate(2, 17, 8, False),
                Candidate(2, 18, 6, False), Candidate(2, 19, 4, False), Candidate(2, 20, 14, True)]

    def test_a_candidate_is_a_bang_word_in_command_text_of_a_test_and_nothing_else_is(self):
        lines = self.SNIPPET.split("\n")
        extents = bash_test_extents(lines)
        self.assertEqual(extents, [(0, 0), (1, 3), (4, 21)])
        self.assertEqual(candidates(lines, extents), self.EXPECTED)

    def test_bash_is_read_in_the_c_locale_whatever_locale_the_environment_names(self):
        # _bash_n reads bash's English wording (_COMMAND_TEXT, _IN_BACKTICKS, the here-document warning), so it pins the probe's
        # locale to C; under a bash whose catalog translates them it would otherwise find no command text and no test extent
        # anywhere. Simulated with a bash on PATH that translates those phrases unless the locale handed to it is C or POSIX, which
        # is what a localized bash does (gettext ignores LANGUAGE and every LC_* for the C locale)
        with tempfile.TemporaryDirectory() as d:
            shim = os.path.join(d, "bash")
            with open(shim, "w", encoding="utf-8") as f:
                f.write("#!/bin/bash\n"
                        'case "${LC_ALL-${LC_MESSAGES-${LANG-}}}" in C|C.*|POSIX|"") exec /bin/bash "$@" ;; esac\n'
                        '/bin/bash "$@" 2> "$0.err"; rc=$?\n'
                        "sed -e 's/syntax error near unexpected token/Syntaxfehler beim unerwarteten Wort/'"
                        " -e 's/unexpected EOF while looking for matching/Dateiende beim Suchen nach passendem/'"
                        " -e 's/delimited by end-of-file/durch Dateiende begrenzt/' \"$0.err\" >&2\n"
                        "exit $rc\n")
            os.chmod(shim, 0o755)
            env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES")}
            env.update(PATH=d + os.pathsep + env.get("PATH", ""), LANG="de_DE.UTF-8")
            with unittest.mock.patch.dict(os.environ, env, clear=True):
                self.assertIn("Syntaxfehler", subprocess.run(["bash", "-n"], input="|| ||\n", capture_output=True, text=True).stderr,
                              "the shim is not the bash on PATH, or does not translate: this pins nothing")
                lines = self.SNIPPET.split("\n")
                extents = bash_test_extents(lines)
                self.assertEqual(extents, [(0, 0), (1, 3), (4, 21)])
                self.assertEqual(candidates(lines, extents), self.EXPECTED)

    def test_candidates_refuses_a_test_bash_cannot_close(self):
        lines = '@test "x" {\n    echo "\n    ! true\n'.split("\n")
        with self.assertRaises(ValueError):
            candidates(lines, bash_test_extents(lines))

    def test_the_negated_pipeline_ends_at_the_first_top_level_operator_or_comment_and_follows_a_continuation(self):
        lines = ['@test "x" {',
                 '    ! grep -q x "$f" ; true',                      # 1: `;`
                 '    ! grep -q "a;b||c" "$f" && true',              # 2: operators inside quotes are text; `&&` ends it
                 '    ! echo "$(echo a; echo b)" | cat || true   # note',   # 3: the `;` inside the substitution is not top level; `|` inside; `||` ends it
                 '    ! true &',                                     # 4: a lone `&`
                 '    ! true 2>&1 &>/dev/null',                      # 5: a redirection's `&` is none
                 '    ! true \\',                                    # 6: a backslash continuation
                 '        --flag || false',
                 '    ! true |',                                     # 8: a pipe continuation
                 '        cat',
                 '    x=$(! true)',                                  # 10: the unmatched `)`
                 '    ( ! true )',                                   # 11
                 '    ! true   # note',                              # 12: the comment, trailing blanks excluded
                 '    ! echo "a',                                    # 13: a string open at the line's end runs on
                 '    b" > /dev/null',
                 '    echo `! echo "a;b"` > /dev/null',              # 15: the closing backtick of the substitution the `!` sits in
                 '    !',                                            # 16: a `!` alone: a pipeline of nothing
                 '}']
        ends = {1: (1, len('    ! grep -q x "$f"')), 2: (2, len('    ! grep -q "a;b||c" "$f"')), 3: (3, len('    ! echo "$(echo a; echo b)" | cat')),
                4: (4, len('    ! true')), 5: (5, len('    ! true 2>&1 &>/dev/null')), 6: (7, len('        --flag')), 8: (9, len('        cat')),
                10: (10, len('    x=$(! true')), 11: (11, len('    ( ! true')), 12: (12, len('    ! true')), 13: (14, len('    b" > /dev/null')),
                15: (15, len('    echo `! echo "a;b"')), 16: (16, len('    !'))}
        found = candidates(lines, bash_test_extents(lines))
        self.assertEqual(sorted(c.line for c in found), sorted(ends))
        for cand in found:
            self.assertEqual(negated_pipeline_end(lines, cand), ends[cand.line], lines[cand.line])
        self.assertIsNone(negated_pipeline_end(['@test "x" {', '    ! true \\'], Candidate(0, 1, 4, False)), "a continuation past the text is undecided")

    def test_the_rewrite_keeps_the_line_count_and_what_follows_the_pipeline_and_every_bang_of_a_run(self):
        lines = ['@test "x" {', '    ! echo "$(echo a; echo b)" | cat || true   # note', '    ! true \\', '        --flag || false', '    ! true   # note',
                 '    echo `! true` > /dev/null', '    ! ! true || false', '    !	!  ! true', '}']
        extents = bash_test_extents(lines)
        self.assertEqual(rewritten_shape(lines, extents, "! false"),
                         ['@test "x" {', '    ! false || true   # note', '    ! false || false', '', '    ! false   # note',
                          '    echo `! false` > /dev/null', '    ! ! false || false', '    ! ! ! false', '}'])
        self.assertEqual(rewritten_shape(lines, extents, "! true"),
                         ['@test "x" {', '    ! true || true   # note', '    ! true || false', '', '    ! true   # note',
                          '    echo `! true` > /dev/null', '    ! ! true || false', '    ! ! ! true', '}'])


def ground_truth_shapes():
    """{name: a synthetic .bats text} whose negations are `! true`, the negated command succeeding, so under bats a test passes
    (`ok`) exactly when the negation asserted nothing there. The families of the round-8 scanner lens (subshell closers, command
    substitutions, heredocs, nested helpers and their call sites, test closes, brace groups, positions on the negation's own line,
    compounds, opener forms under both declaration patterns, `name() { # @test` among them) and the ones the round-8 findings of
    fork PR #778 and their refuters named (condition heads, lists,
    inline subshells and substitutions, process substitutions, backticks, paren-bodied helpers, `coproc`, `;;&`, continued lines,
    call sites through `eval`, an assignment prefix, `time --`, `command` and `env`), each shape mid-test and as the last command
    where the distinction exists. Every other command in a shape succeeds (files are written to /dev/null), so a test's verdict
    turns on the negation alone; a bare `! _h` calling a helper whose last command is `! true` is not in the register, since that
    negated command fails and its test says nothing. The register is the recall gate of the candidate predicate (every `!` of a
    shape is a candidate or is declared in NOT_A_NEGATION), the pin of the negated pipeline's extent (rewriting a shape's own
    candidates must reproduce its recorded verdicts) and the record of what bats says (BatsGroundTruth.RECORDED)."""
    N = "! true"
    S = {}
    closers = {"bare": ")", "redir": ") > /dev/null", "semi": ");", "redir2": ") 2>&1", "redirall": ") &>/dev/null", "semi_true": ") ; true",
               "pipe": ") | cat", "or": ") || true", "and": ") && true", "pipeamp": ") |& cat", "pipe_nospace": ")|cat", "bg": ") &",
               "redir_pipe": ") 2>&1 | cat", "redir_or": ") > /dev/null || true", "redir_and": ") >/dev/null && true",
               "and_or": ") && true || echo fb", "and_pipe": ") && true | cat", "and_and": ") && true && true", "and_bg": ") && true &",
               "or_false": ") || false", "or_return_1": ") || return 1", "and_or_false": ") && true || false"}
    for name, closer in closers.items():
        for pos, tail in (("mid", "\n    true"), ("last", "")):
            S["A_%s_%s" % (name, pos)] = '@test "x" {\n    (\n        run true\n        %s\n    %s%s\n}\n' % (N, closer, tail)
    S["A_neg_before_last"] = '@test "x" {\n    (\n        %s\n        run true\n    )\n    true\n}\n' % N
    S["A_bg_wait_last"] = '@test "x" {\n    (\n        %s\n    ) &\n    wait\n}\n' % N
    S["A_if_condition_mid"] = '@test "x" {\n    if (\n        run true\n        %s\n    ); then true; fi\n    true\n}\n' % N
    S["A_if_condition_last"] = '@test "x" {\n    if (\n        run true\n        %s\n    ); then true; fi\n}\n' % N
    # a subshell closing an `if`, `while` or `until` condition: `then` or `do` on the paren's line or the next, an else branch, an
    # `&&` or `||` list before the `then`, a two-command condition list, and a subshell nested inside the condition's
    for name, kw, trailer in (("if_then_next_line", "if", "\n    then true; fi"), ("if_else", "if", "; then true; else true; fi"),
                              ("if_and_true", "if", " && true; then true; fi"), ("if_or_false", "if", " || false; then true; fi"),
                              ("while", "while", "; do break; done"), ("while_do_next_line", "while", "\n    do break; done"),
                              ("until", "until", "; do break; done"), ("until_do_next_line", "until", "\n    do break; done")):
        S["A_cond_%s_mid" % name] = '@test "x" {\n    %s (\n        run true\n        %s\n    )%s\n    true\n}\n' % (kw, N, trailer)
        S["A_cond_%s_last" % name] = '@test "x" {\n    %s (\n        run true\n        %s\n    )%s\n}\n' % (kw, N, trailer)
    S["A_cond_two_commands_mid"] = '@test "x" {\n    if true; (\n        %s\n    ); then true; fi\n    true\n}\n' % N
    S["A_cond_nested_subshell_mid"] = '@test "x" {\n    if (\n        (\n            %s\n        )\n    ); then true; fi\n    true\n}\n' % N
    S["A_coproc_group_mid"] = '@test "x" {\n    coproc {\n        %s\n    }\n    wait\n    true\n}\n' % N
    S["A_coproc_named_subshell_mid"] = '@test "x" {\n    coproc CP (\n        %s\n    )\n    wait\n    true\n}\n' % N
    for name, opener, closer in (("assign_quoted", 'out="$(', ')"'), ("assign_unquoted", "out=$(", ")"), ("assign_plus", 'out+="$(', ')"'),
                                 ("echo_quoted", 'echo "$(', ')"'), ("echo_unquoted", "echo $(", ")"), ("export", 'export out="$(', ')"'),
                                 ("bracket", '[ -z "$(', ')" ]'), ("assign_then_pipe", 'out="$(', ')" | cat'),
                                 ("assign_backtick", "out=`", "`"), ("echo_backtick", "echo `", "` > /dev/null"),
                                 ("procsub_in", "cat <(", ") > /dev/null"), ("procsub_out", "echo x > >(\n        cat > /dev/null", ")")):
        S["B_%s_mid" % name] = '@test "x" {\n    %s\n        %s\n    %s\n    true\n}\n' % (opener, N, closer)
        S["B_%s_last" % name] = '@test "x" {\n    %s\n        %s\n    %s\n}\n' % (opener, N, closer)
    S["B_local_in_helper"] = '@test "x" {\n    _h() {\n        local out="$(\n            %s\n        )"\n    }\n    _h\n    true\n}\n' % N
    S["B_local_unquoted_in_helper"] = '@test "x" {\n    _h() {\n        local out=$(\n            %s\n        )\n    }\n    _h\n    true\n}\n' % N
    # a heredoc's delimiter in every quoting bash accepts; the body holds a bare `}` and a `!` text line (NOT_A_NEGATION), so a
    # heredoc the predicate misread as commands would surface as a candidate on a declared text line
    for name, intro, term in (("plain", "<<EOF", "EOF"), ("squote", "<<'EOF'", "EOF"), ("dquote", '<<"EOF"', "EOF"), ("dash", "<<-EOF", "\tEOF"),
                              ("backslash", "<<\\EOF", "EOF"), ("mixed", '<<"EO"F', "EOF"), ("hyphen", "<<'EOF-1'", "EOF-1"), ("dollar", "<<$X", "$X"),
                              ("ansi", "<<$'EOF'", "EOF"), ("dotted", "<<EOF.json", "EOF.json"), ("spaced", "<< 'EOF'", "EOF"),
                              ("dash_backslash", "<<-\\EOF", "\tEOF"), ("inner_backslash", "<<E\\OF", "EOF"), ("inner_squote", "<<E'OF'", "EOF"),
                              ("hyphen_unquoted", "<<EOF-1", "EOF-1"), ("locale", '<<$"EOF"', "EOF")):
        S["C_heredoc_%s" % name] = '@test "x" {\n    cat > /dev/null %s\n}\n! text inside\n%s\n    %s\n    true\n}\n' % (intro, term, N)
    S["C_heredoc_last"] = '@test "x" {\n    cat > /dev/null <<EOF\n}\nEOF\n    true\n    %s\n}\n' % N
    S["C_heredoc_decoy_body"] = '@test "x" {\n    cat > /dev/null <<EOF-1\n! text inside\nEOF\n! more text\nEOF-1\n    %s\n    true\n}\n' % N
    S["C_heredoc_ansi_decoy_body"] = "@test \"x\" {\n    cat > /dev/null <<$'EOF'\n$EOF\n}\nEOF\n    %s\n    true\n}\n" % N
    S["C_two_introducers"] = '@test "x" {\n    cat <<A <<B > /dev/null\n! text of A\nA\n! text of B\nB\n    %s\n    true\n}\n' % N
    S["C_text_bang_only"] = '@test "x" {\n    cat <<\'EOF\' > /dev/null\n! not a command\nEOF\n    true\n}\n'
    S["C_quoted_introducer_two_tests"] = ('@test "grep" {\n    run grep -q \'cat > /dev/null <<EOF\' "$BATS_TEST_FILENAME"\n    %s\n    true\n}\n\n'
                                          '@test "real" {\n    cat > /dev/null <<EOF\nhello\nEOF\n    %s\n    true\n}\n' % (N, N))
    S["C_apostrophe_then_heredoc"] = '@test "x" {\n    echo "don\'t" ; cat > /dev/null <<EOF\n! text\nEOF\n    %s\n    true\n}\n' % N
    S["C_decoy_then_real"] = '@test "x" {\n    grep -q \'x <<FAKE\' /dev/null || cat > /dev/null <<EOF\n! text\nEOF\n    %s\n    true\n}\n' % N
    S["C_comment_introducer"] = '@test "x" {\n    # written with a heredoc <<PLIST\n    %s\n    cat > /dev/null <<\'PLIST\'\n<plist/>\nPLIST\n    true\n}\n' % N
    S["C_herestring"] = '@test "x" {\n    grep -q x <<< "$s" || true\n    %s\n    true\n}\n' % N
    S["C_shift"] = '@test "x" {\n    x=$(( 1 << true ))\n    %s\ntrue\n    true\n}\n' % N   # the word after the shift is a later line, a command
    S["C_heredoc_in_helper_last"] = '@test "x" {\n    _h() {\n        cat > /dev/null <<\'PY\'\n}\n}\nPY\n        %s\n    }\n    _h\n    true\n}\n' % N
    S["C_heredoc_on_run_line"] = '@test "x" {\n    run cat <<EOF\n}\nEOF\n    %s\n    true\n}\n' % N
    for name, opener, call in (("trailing_comment", "_h() {   # note", "_h"), ("allman", "_h()\n    {", "_h"), ("function_kw", "function _h {", "_h"),
                               ("function_kw_parens", "function _h() {", "_h"), ("hyphen_name", "my-helper() {", "my-helper"),
                               ("spaced_parens", "_h ( ) {", "_h"), ("dot_name", "my.helper() {", "my.helper"),
                               ("function_kw_hyphen_spaced", "function my-helper ( ) {", "my-helper")):
        S["D_%s" % name] = '@test "x" {\n    %s\n        run true\n        %s\n    }\n    %s\n    true\n}\n' % (opener, N, call)
    S["D_column_zero_body"] = '@test "x" {\n    _h() {\nrun true\n%s\n    }\n    _h\n    true\n}\n' % N
    S["D_mid_negation"] = '@test "x" {\n    _h() {\n        %s\n        run true\n    }\n    _h\n    true\n}\n' % N
    S["D_close_trailing_comment"] = '@test "x" {\n    _h() {\n        %s\n    }   # end\n    _h\n    true\n}\n' % N
    for name, call in (("called_last", "    _h\n"), ("called_mid", "    _h\n    true\n"), ("called_with_args", '    _h /dev/null x\n    true\n'),
                       ("called_in_if", "    if _h; then true; fi\n    true\n"), ("called_or_true", "    _h || true\n    true\n"),
                       ("called_or_return", "    _h || return 1\n    true\n"), ("called_or_false_last", "    _h || false\n"),
                       ("called_or_return_0", "    _h || return 0\n    true\n"), ("called_under_time", "    time _h\n    true\n"),
                       ("never_called", "    true\n"), ("run_no_status", "    run _h\n    true\n"),
                       ("run_status", '    run _h\n    [ "$status" -eq 0 ]\n'), ("and_true_last", "    _h && true\n"), ("semi_true", "    _h; true\n    true\n"),
                       ("subst_echo", "    echo $(_h)\n    true\n"), ("subst_assign_last", "    x=$(_h)\n"), ("subst_assign_quoted_mid", '    x="$(_h)"\n    true\n'),
                       ("if_negated", "    if ! _h; then true; fi\n    true\n"), ("in_group_last", "    {\n        _h\n    }\n"),
                       ("from_other_helper", "    _g() {\n        _h\n    }\n    _g\n    true\n"), ("while_cond", "    while _h; do break; done\n    true\n"),
                       ("bg", "    _h &\n    wait\n"), ("pipe", "    _h | cat\n"),
                       ("called_under_eval", '    eval "_h"\n    true\n'), ("called_under_eval_or_true", '    eval "_h || true"\n    true\n'),
                       ("called_with_assignment_prefix", "    FOO=bar _h\n    true\n"), ("called_under_time_dashdash", "    time -- _h\n    true\n"),
                       ("called_under_command", "    command _h\n    true\n"), ("called_under_env", "    env _h\n    true\n")):
        S["D_%s" % name] = '@test "x" {\n    _h() {\n        run true\n        %s\n    }\n%s}\n' % (N, call)
    for name, call in (("called_mid", "    _h\n    true\n"), ("never_called", "    true\n"), ("called_in_if", "    if _h; then true; fi\n    true\n")):
        S["D_paren_body_%s" % name] = '@test "x" {\n    _h() (\n        run true\n        %s\n    )\n%s}\n' % (N, call)
    S["D_subshell_in_helper_called_in_if"] = '@test "x" {\n    _h() {\n        (\n            %s\n        )\n    }\n    if _h; then true; fi\n    true\n}\n' % N
    S["D_helper_then_mid_negation"] = '@test "x" {\n    _kept() {\n        run true\n        [ "$status" -eq 0 ]\n    }\n    _kept\n    %s\n    true\n}\n' % N
    S["D_helper_then_last_negation"] = '@test "x" {\n    _kept() {\n        run true\n        [ "$status" -eq 0 ]\n    }\n    _kept\n    true\n    %s\n}\n' % N
    for name, close in (("indent2", "  }"), ("trailing_space", "} "), ("tab", "\t}"), ("indent4", "    }"), ("trailing_comment", "} # end"), ("trailing_tab", "}\t")):
        S["E_close_%s_then_test" % name] = '@test "armed" {\n    run true\n    %s\n%s\n\n@test "after" {\n    %s\n    true\n}\n' % (N, close, N)
        S["E_close_%s_last_in_file" % name] = '@test "armed" {\n    run true\n    %s\n%s\n' % (N, close)
    S["E_close_indented_then_file_helper"] = '@test "armed" {\n    run true\n    %s\n  }\n\nhelper() {\n    %s\n    true\n}\n' % (N, N)
    S["E_close_indented_then_teardown"] = '@test "armed" {\n    run true\n    %s\n  }\n\nteardown() {\n    %s\n    true\n}\n' % (N, N)
    S["E_setup_before_test"] = 'setup() {\n    %s\n    true\n}\n\n@test "x" {\n    true\n}\n' % N
    groups = {"bare": "}", "pipe": "} | cat", "and": "} && true", "or": "} || true", "semi": "};", "semi_true": "} ; true", "redir": "} > /dev/null",
              "redir_pipe": "} 2>&1 | cat", "redir_or": "} >/dev/null || true", "redir_and": "} >/dev/null && true", "and_or": "} && true || echo fb"}
    for name, closer in groups.items():
        for pos, tail in (("mid", "\n    true"), ("last", "")):
            S["F_group_%s_%s" % (name, pos)] = '@test "x" {\n    {\n        run true\n        %s\n    %s%s\n}\n' % (N, closer, tail)
    S["F_group_bg_wait_mid"] = '@test "x" {\n    {\n        %s\n    } &\n    wait\n}\n' % N
    S["F_orlist_group_last"] = '@test "x" {\n    false || {\n        true\n        %s\n    }\n}\n' % N
    S["F_group_in_helper_last"] = '@test "x" {\n    _h() {\n        {\n            true\n            %s\n        }\n    }\n    _h\n}\n' % N
    S["F_group_in_helper_mid"] = '@test "x" {\n    _h() {\n        {\n            true\n            %s\n        }\n        true\n    }\n    _h\n}\n' % N
    S["F_group_in_helper_called_mid"] = '@test "x" {\n    _h() {\n        {\n            true\n            %s\n        }\n    }\n    _h\n    true\n}\n' % N
    S["F_group_in_subshell_last"] = '@test "x" {\n    (\n        {\n            true\n            %s\n        }\n    )\n    true\n}\n' % N
    S["F_nested_group_last"] = '@test "x" {\n    {\n        {\n            true\n            %s\n        }\n    }\n}\n' % N
    S["F_nested_group_inner_followed"] = '@test "x" {\n    {\n        {\n            true\n            %s\n        }\n        true\n    }\n}\n' % N
    S["G_last_command"] = '@test "x" {\n    run true\n    %s\n}\n' % N
    S["G_last_past_comment_blank"] = '@test "x" {\n    run true\n    %s\n    # note\n\n}\n' % N
    S["G_mid_after_run"] = '@test "x" {\n    run true\n    %s\n    true\n}\n' % N
    S["G_first_command"] = '@test "x" {\n    %s\n    true\n}\n' % N
    S["G_two_tests_second_mid"] = '@test "a" {\n    run true\n    %s\n}\n\n@test "b" {\n    %s\n    true\n}\n' % (N, N)
    S["G_tab_indented_mid"] = '@test "x" {\n\t%s\n\ttrue\n}\n' % N
    # the negated pipeline's extent (negated_pipeline_end) is pinned here: for each terminator a tail whose verdict changes when
    # the split runs past it. `; true` and `|| ...`; `&& false`, a list whose status is false when the negation is true, where
    # `&& echo yes` succeeds either way; a lone `&` before `wait %%`, which returns the backgrounded command's own status and not
    # its negation (measured: `! true & wait %%` is ok and `! false & wait %%` is not); a comment holding operators, further down
    for name, tail in (("or_fallback", " || echo fb"), ("or_false", " || false"), ("or_return_1", " || return 1"), ("or_return_bare", " || return"),
                       ("or_return_0", " || return 0"), ("or_group_return", " || { echo no; return 1; }"), ("and_then", " && echo yes"), ("and_or", " && true || echo fb"),
                       ("and_or_false", " && true || false"), ("and_false", " && false"),
                       ("pipeline", " | cat"), ("pipe_or", " | cat || echo fb"), ("semicolon_command", "; true"), ("trailing_semicolon", ";"),
                       ("trailing_comment", "   # note"), ("bg", " &\n    wait"), ("bg_wait_job", " & wait %%"),
                       ("or_true", " || true"), ("or_exit_1", " || exit 1"), ("or_fail", " || fail no"), ("or_group_true", " || { echo no; true; }"),
                       ("continued_args", " \\\n        x"), ("continued_or_false", " \\\n        || false"), ("continued_or_true", " \\\n        || true"),
                       ("continued_pipe", " |\n        cat")):
        S["G_%s_mid" % name] = '@test "x" {\n    %s%s\n    true\n}\n' % (N, tail)
        S["G_%s_last" % name] = '@test "x" {\n    true\n    %s%s\n}\n' % (N, tail)
    S["G_or_return_var_mid"] = '@test "x" {\n    rc=1\n    %s || return "$rc"\n    true\n}\n' % N
    S["G_or_return_var_last"] = '@test "x" {\n    rc=1\n    %s || return "$rc"\n}\n' % N
    S["G_quoted_operators_last"] = '@test "x" {\n    true\n    ! echo "a;b||c" > /dev/null\n}\n'
    S["G_substitution_operators_last"] = '@test "x" {\n    true\n    ! echo "$(echo a; echo b)" > /dev/null\n}\n'
    S["G_comment_bang_mid"] = '@test "x" {\n    # ! a note, not a command\n    true\n}\n'
    S["G_string_bang_mid"] = '@test "x" {\n    echo "a ! here is not a command" > /dev/null\n    true\n}\n'
    # the word rule's boundaries, one shape each: a `!` glued to a redirection or to a subshell's `(`, one alone on a line and one
    # before a `;` (a lone `!` is a pipeline of nothing, status 1), one right after an opening backtick and one alone between two
    S["G_redirect_glued_out_mid"] = '@test "x" {\n    !>/dev/null true\n    true\n}\n'
    S["G_redirect_glued_in_mid"] = '@test "x" {\n    !</dev/null true\n    true\n}\n'
    S["G_paren_glued_mid"] = '@test "x" {\n    !(true)\n    true\n}\n'
    S["G_lone_bang_mid"] = '@test "x" {\n    !\n    true\n}\n'
    S["G_lone_bang_last"] = '@test "x" {\n    true\n    !\n}\n'
    S["G_lone_bang_semicolon_mid"] = '@test "x" {\n    !; true\n    true\n}\n'
    S["G_backtick_glued_mid"] = '@test "x" {\n    echo `%s` > /dev/null\n    true\n}\n' % N
    S["G_backtick_lone_bang_mid"] = '@test "x" {\n    echo `!` > /dev/null\n    true\n}\n'
    # a run of `!` words: bash reads a doubled negation's status (the inversions cancel and errexit applies) and exempts a tripled one
    S["G_double_negation_mid"] = '@test "x" {\n    ! %s\n    true\n}\n' % N
    S["G_double_negation_last"] = '@test "x" {\n    true\n    ! %s\n}\n' % N
    S["G_triple_negation_mid"] = '@test "x" {\n    ! ! %s\n    true\n}\n' % N
    S["G_triple_negation_last"] = '@test "x" {\n    true\n    ! ! %s\n}\n' % N
    # a trailing comment holding operators or an apostrophe: the extent ends at the `#`; a split reading into the comment would
    # rewrite `&& false` onto the command, or run past the end of the text after the `'`
    S["G_comment_operators_mid"] = '@test "x" {\n    %s   # a note && false\n    true\n}\n' % N
    S["G_comment_operators_last"] = '@test "x" {\n    true\n    %s   # a note && false\n}\n' % N
    S["G_comment_apostrophe_mid"] = "@test \"x\" {\n    %s   # don't read this\n    true\n}\n" % N
    S["G_comment_apostrophe_last"] = "@test \"x\" {\n    true\n    %s   # don't read this\n}\n" % N
    # a negation inside a string that eval or bash -c runs: text to the predicate (NOT_A_NEGATION), inert under bats, and the one
    # class inside a test this instrument does not see
    S["G_eval_string_mid"] = '@test "x" {\n    eval "%s; true"\n    true\n}\n' % N
    S["G_bash_c_string_mid"] = '@test "x" {\n    bash -c "%s; true"\n    true\n}\n' % N
    # the negation off the line's start: the earlier register negated at line start in 247 of 250 shapes, where the line scanner
    # looked; the predicate finds a `!` word anywhere in command text, and these pin that. Condition heads (a branch that fails
    # the test and one that does not), lists, after `;` and `&`, inline subshells, groups and substitutions, `time`, a case
    # pattern's own line
    S["H_if_head_then_true_mid"] = '@test "x" {\n    if %s; then true; fi\n    true\n}\n' % N
    S["H_if_head_return_mid"] = '@test "x" {\n    if %s; then return 1; fi\n    true\n}\n' % N
    S["H_if_head_return_last"] = '@test "x" {\n    true\n    if %s; then return 1; fi\n}\n' % N
    S["H_elif_head_return_mid"] = '@test "x" {\n    if false; then true; elif %s; then return 1; fi\n    true\n}\n' % N
    S["H_while_head_return_mid"] = '@test "x" {\n    while %s; do return 1; done\n    true\n}\n' % N
    S["H_until_head_break_mid"] = '@test "x" {\n    until %s; do break; done\n    true\n}\n' % N
    S["H_and_list_mid"] = '@test "x" {\n    true && %s\n    true\n}\n' % N
    S["H_and_list_last"] = '@test "x" {\n    true && %s\n}\n' % N
    S["H_or_list_mid"] = '@test "x" {\n    false || %s\n    true\n}\n' % N
    S["H_or_list_last"] = '@test "x" {\n    false || %s\n}\n' % N
    S["H_after_semicolon_mid"] = '@test "x" {\n    true; %s\n    true\n}\n' % N
    S["H_after_semicolon_last"] = '@test "x" {\n    true; %s\n}\n' % N
    S["H_after_bg_mid"] = '@test "x" {\n    sleep 0 & %s\n    wait\n    true\n}\n' % N
    S["H_inline_subshell_mid"] = '@test "x" {\n    ( %s )\n    true\n}\n' % N
    S["H_inline_subshell_nospace_mid"] = '@test "x" {\n    (%s)\n    true\n}\n' % N
    # read positions whose failing line is not the negation's: bash blames a `( ... )` compound's failure on the line before it (the
    # @test line for a first body line, H_inline_subshell_mid; the test's own line for a one-liner, I_one_liner_subshell) and a
    # status saved with `rc=$?` on the `[ ]` that reads it. decide accepts a failure anywhere inside the candidate's test; the
    # decision test of BatsGroundTruth holds it to that over every shape (fork PR #871, the commit-3 review's F1)
    S["H_inline_subshell_after_command_mid"] = '@test "x" {\n    true\n    ( %s )\n    true\n}\n' % N
    S["H_inline_subshell_last"] = '@test "x" {\n    true\n    ( %s )\n}\n' % N
    S["H_status_read_by_test_mid"] = '@test "x" {\n    %s\n    rc=$?\n    [ "$rc" -eq 1 ]\n    true\n}\n' % N
    S["H_inline_group_mid"] = '@test "x" {\n    { %s; }\n    true\n}\n' % N
    S["H_inline_assign_subst_mid"] = '@test "x" {\n    x=$(%s)\n    true\n}\n' % N
    S["H_inline_echo_subst_mid"] = '@test "x" {\n    echo "$(%s)" > /dev/null\n    true\n}\n' % N
    S["H_time_mid"] = '@test "x" {\n    time %s\n    true\n}\n' % N
    S["H_time_last"] = '@test "x" {\n    true\n    time %s\n}\n' % N
    S["H_time_p_mid"] = '@test "x" {\n    time -p %s\n    true\n}\n' % N
    S["H_case_pattern_line_mid"] = '@test "x" {\n    case a in\n      a) %s ;;\n    esac\n    true\n}\n' % N
    S["H_case_pattern_line_last"] = '@test "x" {\n    case a in\n      a) %s ;;\n    esac\n}\n' % N
    compounds = {"if": "    if true; then\n        %s\n    fi", "if_else_then": "    if true; then\n        %s\n    else\n        true\n    fi",
                 "if_else_else": "    if false; then\n        true\n    else\n        %s\n    fi", "if_elif": "    if true; then\n        %s\n    elif true; then\n        true\n    fi",
                 "if_nested": "    if true; then\n        if true; then\n            %s\n        fi\n    fi",
                 "if_oneliner_before": "    if true; then\n        if true; then true; fi\n        %s\n    fi",
                 "for": "    for i in 1; do\n        %s\n    done", "while": '    n=0\n    while [ "$n" -lt 1 ]; do\n        n=1\n        %s\n    done',
                 "until": '    n=0\n    until [ "$n" -ge 1 ]; do\n        n=1\n        %s\n    done',
                 "case": "    case a in\n      a)\n        %s\n        ;;\n    esac", "case_pattern_command": "    case a in\n      a) true\n        %s\n        ;;\n      b) true ;;\n    esac",
                 "case_no_dsemi": "    case a in\n      a)\n        %s\n    esac",
                 "case_fallthrough": "    case a in\n      a)\n        %s\n        ;;&\n      *)\n        true\n        ;;\n    esac"}
    for name, body in compounds.items():
        S["T_%s_last" % name] = '@test "x" {\n%s\n}\n' % (body % N)
        S["T_%s_mid" % name] = '@test "x" {\n%s\n    true\n}\n' % (body % N)
    S["T_if_in_helper_last"] = '@test "x" {\n    _h() {\n        if true; then\n            %s\n        fi\n    }\n    _h\n}\n' % N
    S["T_if_in_group_last"] = '@test "x" {\n    {\n        if true; then\n            %s\n        fi\n    }\n}\n' % N
    S["T_if_in_subshell_mid"] = '@test "x" {\n    (\n        if true; then\n            %s\n        fi\n    )\n    true\n}\n' % N
    for name, trailer in (("semi_true", " ; true"), ("or_true", " || true"), ("pipe", " | cat"), ("redir_pipe", " 2>&1 | cat"), ("and_true", " && true"),
                          ("redir", " > /dev/null"), ("redir_and", " >/dev/null && true"), ("and_or", " && true || echo fb")):
        S["T_fi_%s_last" % name] = '@test "x" {\n    if true; then\n        %s\n    fi%s\n}\n' % (N, trailer)
    S["T_done_semi_true_last"] = '@test "x" {\n    for i in 1; do\n        %s\n    done ; true\n}\n' % N
    S["T_esac_semi_true_last"] = '@test "x" {\n    case a in\n      a)\n        %s\n        ;;\n    esac ; true\n}\n' % N
    S["T_while_condition_multiline"] = '@test "x" {\n    while\n        %s\n    do\n        break\n    done\n    true\n}\n' % N
    for name, opener in (("trailing_comment", '@test "x" {   # note'), ("indented", '  @test "x" {'), ("trailing_command", '@test "x" { run true'),
                         ("tab_indented", '\t@test "x" {')):
        S["I_opener_%s_mid" % name] = '%s\n    %s\n    true\n}\n' % (opener, N)
        S["I_opener_%s_last" % name] = '%s\n    true\n    %s\n}\n' % (opener, N)
    S["I_one_liner_between"] = '@test "a" {\n    %s\n    true\n}\n@test "b" { true; }\n@test "c" {\n    true\n    %s\n}\n' % (N, N)
    S["I_one_liner_negation"] = '@test "x" { ! true; }\n'
    S["I_one_liner_subshell"] = '@test "x" { ( ! true ); }\n'
    S["I_opener_trailing_negation"] = '@test "x" { ! true\n    true\n}\n'
    # the comment form of a declaration, `name() { # @test` (bats-preprocess's BATS_TEST_PATTERN_COMMENT), which bats runs as it
    # runs a `@test` line: with and without the parentheses (`x { # @test` is no function to bash until rewritten), under the
    # `function` keyword (the name is the word before the brace, the pattern's leftmost match), indented with blanks inside the
    # comment, and beside a `@test` test in one file (two tests to bats and to bash_test_extents; one to this module before fork
    # PR #871's commit 4, when it opened on the `@test` form alone and a test written this way was bats's and no one else's)
    S["I_comment_form_mid"] = 'x() { # @test\n    %s\n    true\n}\n' % N
    S["I_comment_form_last"] = 'x() { # @test\n    true\n    %s\n}\n' % N
    S["I_comment_form_no_parens_mid"] = 'x { # @test\n    %s\n    true\n}\n' % N
    S["I_comment_form_function_keyword_mid"] = 'function x { # @test\n    %s\n    true\n}\n' % N
    S["I_comment_form_indented_mid"] = '  x() {  #  @test\n    %s\n    true\n}\n' % N
    S["I_comment_form_and_at_test"] = 'x() { # @test\n    %s\n    true\n}\n\n@test "y" {\n    true\n    %s\n}\n' % (N, N)
    # the `!` that is an operator of `[`, `[[` or bats's `run`, which the predicate leaves out by the word before it (_OPERATOR_OF)
    S["X_test_bracket_mid"] = '@test "x" {\n    [ ! -s /dev/null ]\n    true\n}\n'
    S["X_test_dbracket_mid"] = '@test "x" {\n    [[ ! -s /dev/null ]]\n    true\n}\n'
    S["X_run_negation_mid"] = 'bats_require_minimum_version 1.5.0\n\n@test "x" {\n    run ! true\n    true\n}\n'
    return S


# the `!` characters of the register that are not a command's negation, by shape and 1-based line, each with what it is: a
# heredoc's text, a comment, a string, or the operator of `[`, `[[` or `run`. The recall gate (BatsGroundTruth) reads every other
# `!` character of a shape's tests as a negation the predicate must find, so a shape's `!` that is text must be declared here to
# be excused, and a declared line must hold a `!` the predicate does not take (a stale declaration reds)
NOT_A_NEGATION = dict(
    {"C_heredoc_%s" % name: {4: "heredoc text"} for name in ("plain", "squote", "dquote", "dash", "backslash", "mixed", "hyphen", "dollar", "ansi", "dotted",
                                                              "spaced", "dash_backslash", "inner_backslash", "inner_squote", "hyphen_unquoted", "locale")},
    C_heredoc_decoy_body={3: "heredoc text", 5: "heredoc text"},
    C_two_introducers={3: "heredoc text", 5: "heredoc text"},
    C_text_bang_only={3: "heredoc text"},
    C_apostrophe_then_heredoc={3: "heredoc text"},
    C_decoy_then_real={3: "heredoc text"},
    G_comment_bang_mid={2: "a comment"},
    G_string_bang_mid={2: "text in a string"},
    G_eval_string_mid={2: "text in a string eval runs"},
    G_bash_c_string_mid={2: "text in a string bash -c runs"},
    X_test_bracket_mid={2: "the operator of `[`"},
    X_test_dbracket_mid={2: "the operator of `[[`"},
    X_run_negation_mid={4: "run's own inverted status, checked by run"},
)
# the tests of the register that hold no `!` at all, by shape and 1-based test ordinal: a test recorded `ok` with no candidate must
# be one of these, or hold only declared `!` words, for the gate to pass it
NO_NEGATION = {"I_one_liner_between": (2,), "E_setup_before_test": (1,)}


def record_under_bats(shapes, bats="bats"):
    """({shape: comma-joined per-test verdicts under the `! true` rewrite}, {the same under `! false`}, {"t": {shape: [BatsRun per
    test]}, "f": {the same}}, bats's TAP output and stderr, the version line): every shape goes through the corpus road, its
    candidates found (candidates) and each one's negated pipeline rewritten (rewritten_shape, over rewrite) to `! true` and to
    `! false`, the two files run under bats in one directory with stdin /dev/null and the environment _bats_env gives (HOME and
    TMPDIR isolated, every BATS_* variable unset). One run over the directory rather than one per test as the corpus makes
    (run_test_alone), bounded at REGISTER_TIMEOUT (every shape terminates, so a run past it is an error, not a verdict), and every
    candidate of a test rewritten at once rather than one at a time: in every test of the register but one the two are the same
    file, since the test holds one negated pipeline (a run of `!` words is one); the one, D_if_negated, holds two, a helper's
    `! true` and the `! _h` that calls it, and its record is the file with both rewritten. Each test is renamed to carry its shape's
    index, the rewrite and its ordinal so the TAP lines map back (_renamed, under either declaration pattern; a test line inside a
    heredoc or a string is renamed too, harmlessly: bats-preprocess rewrites it either way). Each test's run comes back too, its
    outcome with the line bats blames and the file, the shape's own file reported under the shape's name (decide compares the
    frame's file to the suite's path; a shape is one file), so decide can be asked about a shape's test the way the corpus asks it
    about a candidate (BatsGroundTruth)."""
    names = sorted(shapes)
    with tempfile.TemporaryDirectory() as d:
        files = {}
        for n, name in enumerate(names):
            lines = shapes[name].split("\n")
            extents = bash_test_extents(lines)
            for tag, repl in (("t", "! true"), ("f", "! false")):
                k = iter(range(1, 100))
                text = "\n".join(_renamed(l, "s%03d_%s_t%d" % (n, tag, next(k))) if _test_line(l) else l
                                 for l in rewritten_shape(lines, extents, repl))
                path = os.path.join(d, "%03d_%s.bats" % (n, tag))
                files[path] = files[os.path.realpath(path)] = name
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
        env = _bats_env(d)
        version = subprocess.run([bats, "--version"], capture_output=True, text=True, env=env).stdout.strip()
        out_text, err_text, ended, _, _ = _run_bats([bats, "-t", d], None, env, REGISTER_TIMEOUT)
    if ended:
        raise RuntimeError("bats did not finish the register in %d s (REGISTER_TIMEOUT); its TAP ends:\n%s" % (REGISTER_TIMEOUT, out_text[-3000:]))
    got, runs = {"t": {}, "f": {}}, {"t": {}, "f": {}}
    out = out_text.splitlines()
    for i, line in enumerate(out):
        m = re.match(r"^(ok|not ok) \d+ s(\d{3})_([tf])_t\d+", line)
        if m:
            name, tag, verdict = names[int(m.group(2))], m.group(3), m.group(1)
            got[tag].setdefault(name, []).append(verdict)
            ln, fl = _frame(out, i) if verdict == "not ok" else (None, None)
            runs[tag].setdefault(name, []).append(BatsRun(verdict, ln, files.get(fl, fl), "", 0.0))
    return ({name: ",".join(v) for name, v in got["t"].items()}, {name: ",".join(v) for name, v in got["f"].items()}, runs,
            out_text + err_text, version)


class BatsGroundTruth(unittest.TestCase):
    """The register: every shape of ground_truth_shapes under bats itself, the negated command succeeding. RECORDED holds each
    shape's verdicts per test in file order under the two rewrites the corpus road makes of a candidate's negated pipeline, `! true`
    (the shapes as written, the pipeline reduced to the word) and `! false`, pasted from bats; RECORDED_WITH names the bats
    versions the record was verified against. The gate has three parts. Recall: every `!` character of a shape's tests is a
    candidate unless declared an operator or text (NOT_A_NEGATION), and a test recorded `ok` with no candidate holds only declared
    `!` characters or none (NO_NEGATION); the expected set owes nothing to the predicate's word rule, so a spelling it misses reds
    here and a new shape costs one entry. Agreement: with bats on PATH the shapes go through the corpus road (record_under_bats)
    and the verdicts must equal the record, which pins the extent of the negated pipeline (a split that swallows a trailing comment
    or an operator changes a verdict) and the record itself (a bats whose semantics differ, or a stale record, reds). Decision: from
    the same run, decide over every test holding one candidate must read every test whose verdicts differ, call inert every one ok
    under both and undecided every one failing under both, so decide's refusal of a failure blamed outside the candidate's test
    fires on no deterministic shape; the verdicts alone could not see that clause. Without bats the last two SKIP, saying where they
    run: CI's shell job is the one cell that installs bats, and a run that verified nothing must not read like one that verified
    every shape."""

    # the bats versions RECORDED was verified against by the agreement test below with that bats on PATH: 1.10.0, the box the
    # record was taken on, and 1.11.1, CI's pin (.github/workflows/ci.yml installs it from the release tarball), installed from the
    # same tarball into a scratch prefix here. A bats of another version that agrees is fine; one that disagrees reds, and the
    # message says the version was not among these
    RECORDED_WITH = ("1.10.0", "1.11.1")

    RECORDED = {
        'A_and_and_last': ('not ok', 'ok'),
        'A_and_and_mid': ('ok', 'ok'),
        'A_and_bg_last': ('ok', 'ok'),
        'A_and_bg_mid': ('ok', 'ok'),
        'A_and_last': ('not ok', 'ok'),
        'A_and_mid': ('ok', 'ok'),
        'A_and_or_false_last': ('not ok', 'ok'),
        'A_and_or_false_mid': ('not ok', 'ok'),
        'A_and_or_last': ('ok', 'ok'),
        'A_and_or_mid': ('ok', 'ok'),
        'A_and_pipe_last': ('not ok', 'ok'),
        'A_and_pipe_mid': ('ok', 'ok'),
        'A_bare_last': ('not ok', 'ok'),
        'A_bare_mid': ('not ok', 'ok'),
        'A_bg_last': ('ok', 'ok'),
        'A_bg_mid': ('ok', 'ok'),
        'A_bg_wait_last': ('ok', 'ok'),
        'A_cond_if_and_true_last': ('ok', 'ok'),
        'A_cond_if_and_true_mid': ('ok', 'ok'),
        'A_cond_if_else_last': ('ok', 'ok'),
        'A_cond_if_else_mid': ('ok', 'ok'),
        'A_cond_if_or_false_last': ('ok', 'ok'),
        'A_cond_if_or_false_mid': ('ok', 'ok'),
        'A_cond_if_then_next_line_last': ('ok', 'ok'),
        'A_cond_if_then_next_line_mid': ('ok', 'ok'),
        'A_cond_nested_subshell_mid': ('ok', 'ok'),
        'A_cond_two_commands_mid': ('ok', 'ok'),
        'A_cond_until_do_next_line_last': ('ok', 'ok'),
        'A_cond_until_do_next_line_mid': ('ok', 'ok'),
        'A_cond_until_last': ('ok', 'ok'),
        'A_cond_until_mid': ('ok', 'ok'),
        'A_cond_while_do_next_line_last': ('ok', 'ok'),
        'A_cond_while_do_next_line_mid': ('ok', 'ok'),
        'A_cond_while_last': ('ok', 'ok'),
        'A_cond_while_mid': ('ok', 'ok'),
        'A_coproc_group_mid': ('ok', 'ok'),
        'A_coproc_named_subshell_mid': ('ok', 'ok'),
        'A_if_condition_last': ('ok', 'ok'),
        'A_if_condition_mid': ('ok', 'ok'),
        'A_neg_before_last': ('ok', 'ok'),
        'A_or_false_last': ('not ok', 'ok'),
        'A_or_false_mid': ('not ok', 'ok'),
        'A_or_last': ('ok', 'ok'),
        'A_or_mid': ('ok', 'ok'),
        'A_or_return_1_last': ('not ok', 'ok'),
        'A_or_return_1_mid': ('not ok', 'ok'),
        'A_pipe_last': ('ok', 'ok'),
        'A_pipe_mid': ('ok', 'ok'),
        'A_pipe_nospace_last': ('ok', 'ok'),
        'A_pipe_nospace_mid': ('ok', 'ok'),
        'A_pipeamp_last': ('ok', 'ok'),
        'A_pipeamp_mid': ('ok', 'ok'),
        'A_redir2_last': ('not ok', 'ok'),
        'A_redir2_mid': ('not ok', 'ok'),
        'A_redir_and_last': ('not ok', 'ok'),
        'A_redir_and_mid': ('ok', 'ok'),
        'A_redir_last': ('not ok', 'ok'),
        'A_redir_mid': ('not ok', 'ok'),
        'A_redir_or_last': ('ok', 'ok'),
        'A_redir_or_mid': ('ok', 'ok'),
        'A_redir_pipe_last': ('ok', 'ok'),
        'A_redir_pipe_mid': ('ok', 'ok'),
        'A_redirall_last': ('not ok', 'ok'),
        'A_redirall_mid': ('not ok', 'ok'),
        'A_semi_last': ('not ok', 'ok'),
        'A_semi_mid': ('not ok', 'ok'),
        'A_semi_true_last': ('not ok', 'ok'),
        'A_semi_true_mid': ('not ok', 'ok'),
        'B_assign_backtick_last': ('not ok', 'ok'),
        'B_assign_backtick_mid': ('not ok', 'ok'),
        'B_assign_plus_last': ('not ok', 'ok'),
        'B_assign_plus_mid': ('not ok', 'ok'),
        'B_assign_quoted_last': ('not ok', 'ok'),
        'B_assign_quoted_mid': ('not ok', 'ok'),
        'B_assign_then_pipe_last': ('ok', 'ok'),
        'B_assign_then_pipe_mid': ('ok', 'ok'),
        'B_assign_unquoted_last': ('not ok', 'ok'),
        'B_assign_unquoted_mid': ('not ok', 'ok'),
        'B_bracket_last': ('ok', 'ok'),
        'B_bracket_mid': ('ok', 'ok'),
        'B_echo_backtick_last': ('ok', 'ok'),
        'B_echo_backtick_mid': ('ok', 'ok'),
        'B_echo_quoted_last': ('ok', 'ok'),
        'B_echo_quoted_mid': ('ok', 'ok'),
        'B_echo_unquoted_last': ('ok', 'ok'),
        'B_echo_unquoted_mid': ('ok', 'ok'),
        'B_export_last': ('ok', 'ok'),
        'B_export_mid': ('ok', 'ok'),
        'B_local_in_helper': ('ok', 'ok'),
        'B_local_unquoted_in_helper': ('ok', 'ok'),
        'B_procsub_in_last': ('ok', 'ok'),
        'B_procsub_in_mid': ('ok', 'ok'),
        'B_procsub_out_last': ('ok', 'ok'),
        'B_procsub_out_mid': ('ok', 'ok'),
        'C_apostrophe_then_heredoc': ('ok', 'ok'),
        'C_comment_introducer': ('ok', 'ok'),
        'C_decoy_then_real': ('ok', 'ok'),
        'C_heredoc_ansi': ('ok', 'ok'),
        'C_heredoc_ansi_decoy_body': ('ok', 'ok'),
        'C_heredoc_backslash': ('ok', 'ok'),
        'C_heredoc_dash': ('ok', 'ok'),
        'C_heredoc_dash_backslash': ('ok', 'ok'),
        'C_heredoc_decoy_body': ('ok', 'ok'),
        'C_heredoc_dollar': ('ok', 'ok'),
        'C_heredoc_dotted': ('ok', 'ok'),
        'C_heredoc_dquote': ('ok', 'ok'),
        'C_heredoc_hyphen': ('ok', 'ok'),
        'C_heredoc_hyphen_unquoted': ('ok', 'ok'),
        'C_heredoc_in_helper_last': ('not ok', 'ok'),
        'C_heredoc_inner_backslash': ('ok', 'ok'),
        'C_heredoc_inner_squote': ('ok', 'ok'),
        'C_heredoc_last': ('not ok', 'ok'),
        'C_heredoc_locale': ('ok', 'ok'),
        'C_heredoc_mixed': ('ok', 'ok'),
        'C_heredoc_on_run_line': ('ok', 'ok'),
        'C_heredoc_plain': ('ok', 'ok'),
        'C_heredoc_spaced': ('ok', 'ok'),
        'C_heredoc_squote': ('ok', 'ok'),
        'C_herestring': ('ok', 'ok'),
        'C_quoted_introducer_two_tests': ('ok,ok', 'ok,ok'),
        'C_shift': ('ok', 'ok'),
        'C_text_bang_only': ('ok', 'ok'),
        'C_two_introducers': ('ok', 'ok'),
        'D_allman': ('not ok', 'ok'),
        'D_and_true_last': ('not ok', 'ok'),
        'D_bg': ('ok', 'ok'),
        'D_called_in_if': ('ok', 'ok'),
        'D_called_last': ('not ok', 'ok'),
        'D_called_mid': ('not ok', 'ok'),
        'D_called_or_false_last': ('not ok', 'ok'),
        'D_called_or_return': ('not ok', 'ok'),
        'D_called_or_return_0': ('ok', 'ok'),
        'D_called_or_true': ('ok', 'ok'),
        'D_called_under_command': ('not ok', 'not ok'),
        'D_called_under_env': ('not ok', 'not ok'),
        'D_called_under_eval': ('not ok', 'ok'),
        'D_called_under_eval_or_true': ('ok', 'ok'),
        'D_called_under_time': ('not ok', 'ok'),
        'D_called_under_time_dashdash': ('not ok', 'ok'),
        'D_called_with_args': ('not ok', 'ok'),
        'D_called_with_assignment_prefix': ('not ok', 'ok'),
        'D_close_trailing_comment': ('not ok', 'ok'),
        'D_column_zero_body': ('not ok', 'ok'),
        'D_dot_name': ('not ok', 'ok'),
        'D_from_other_helper': ('not ok', 'ok'),
        'D_function_kw': ('not ok', 'ok'),
        'D_function_kw_hyphen_spaced': ('not ok', 'ok'),
        'D_function_kw_parens': ('not ok', 'ok'),
        'D_helper_then_last_negation': ('not ok', 'ok'),
        'D_helper_then_mid_negation': ('ok', 'ok'),
        'D_hyphen_name': ('not ok', 'ok'),
        'D_if_negated': ('ok', 'ok'),
        'D_in_group_last': ('not ok', 'ok'),
        'D_mid_negation': ('ok', 'ok'),
        'D_never_called': ('ok', 'ok'),
        'D_paren_body_called_in_if': ('ok', 'ok'),
        'D_paren_body_called_mid': ('not ok', 'ok'),
        'D_paren_body_never_called': ('ok', 'ok'),
        'D_pipe': ('ok', 'ok'),
        'D_run_no_status': ('ok', 'ok'),
        'D_run_status': ('not ok', 'ok'),
        'D_semi_true': ('not ok', 'ok'),
        'D_spaced_parens': ('not ok', 'ok'),
        'D_subshell_in_helper_called_in_if': ('ok', 'ok'),
        'D_subst_assign_last': ('not ok', 'ok'),
        'D_subst_assign_quoted_mid': ('not ok', 'ok'),
        'D_subst_echo': ('ok', 'ok'),
        'D_trailing_comment': ('not ok', 'ok'),
        'D_while_cond': ('ok', 'ok'),
        'E_close_indent2_last_in_file': ('not ok', 'ok'),
        'E_close_indent2_then_test': ('not ok,ok', 'ok,ok'),
        'E_close_indent4_last_in_file': ('not ok', 'ok'),
        'E_close_indent4_then_test': ('not ok,ok', 'ok,ok'),
        'E_close_indented_then_file_helper': ('not ok', 'ok'),
        'E_close_indented_then_teardown': ('not ok', 'ok'),
        'E_close_tab_last_in_file': ('not ok', 'ok'),
        'E_close_tab_then_test': ('not ok,ok', 'ok,ok'),
        'E_close_trailing_comment_last_in_file': ('not ok', 'ok'),
        'E_close_trailing_comment_then_test': ('not ok,ok', 'ok,ok'),
        'E_close_trailing_space_last_in_file': ('not ok', 'ok'),
        'E_close_trailing_space_then_test': ('not ok,ok', 'ok,ok'),
        'E_close_trailing_tab_last_in_file': ('not ok', 'ok'),
        'E_close_trailing_tab_then_test': ('not ok,ok', 'ok,ok'),
        'E_setup_before_test': ('ok', 'ok'),
        'F_group_and_last': ('not ok', 'ok'),
        'F_group_and_mid': ('ok', 'ok'),
        'F_group_and_or_last': ('ok', 'ok'),
        'F_group_and_or_mid': ('ok', 'ok'),
        'F_group_bare_last': ('not ok', 'ok'),
        'F_group_bare_mid': ('ok', 'ok'),
        'F_group_bg_wait_mid': ('ok', 'ok'),
        'F_group_in_helper_called_mid': ('not ok', 'ok'),
        'F_group_in_helper_last': ('not ok', 'ok'),
        'F_group_in_helper_mid': ('ok', 'ok'),
        'F_group_in_subshell_last': ('not ok', 'ok'),
        'F_group_or_last': ('ok', 'ok'),
        'F_group_or_mid': ('ok', 'ok'),
        'F_group_pipe_last': ('ok', 'ok'),
        'F_group_pipe_mid': ('ok', 'ok'),
        'F_group_redir_and_last': ('not ok', 'ok'),
        'F_group_redir_and_mid': ('ok', 'ok'),
        'F_group_redir_last': ('not ok', 'ok'),
        'F_group_redir_mid': ('ok', 'ok'),
        'F_group_redir_or_last': ('ok', 'ok'),
        'F_group_redir_or_mid': ('ok', 'ok'),
        'F_group_redir_pipe_last': ('ok', 'ok'),
        'F_group_redir_pipe_mid': ('ok', 'ok'),
        'F_group_semi_last': ('not ok', 'ok'),
        'F_group_semi_mid': ('ok', 'ok'),
        'F_group_semi_true_last': ('ok', 'ok'),
        'F_group_semi_true_mid': ('ok', 'ok'),
        'F_nested_group_inner_followed': ('ok', 'ok'),
        'F_nested_group_last': ('not ok', 'ok'),
        'F_orlist_group_last': ('not ok', 'ok'),
        'G_and_false_last': ('not ok', 'not ok'),
        'G_and_false_mid': ('ok', 'not ok'),
        'G_and_or_false_last': ('not ok', 'ok'),
        'G_and_or_false_mid': ('not ok', 'ok'),
        'G_and_or_last': ('ok', 'ok'),
        'G_and_or_mid': ('ok', 'ok'),
        'G_and_then_last': ('not ok', 'ok'),
        'G_and_then_mid': ('ok', 'ok'),
        'G_backtick_glued_mid': ('ok', 'ok'),
        'G_backtick_lone_bang_mid': ('ok', 'ok'),
        'G_bash_c_string_mid': ('ok', 'ok'),
        'G_bg_last': ('ok', 'ok'),
        'G_bg_mid': ('ok', 'ok'),
        'G_bg_wait_job_last': ('ok', 'not ok'),
        'G_bg_wait_job_mid': ('ok', 'not ok'),
        'G_comment_apostrophe_last': ('not ok', 'ok'),
        'G_comment_apostrophe_mid': ('ok', 'ok'),
        'G_comment_bang_mid': ('ok', 'ok'),
        'G_comment_operators_last': ('not ok', 'ok'),
        'G_comment_operators_mid': ('ok', 'ok'),
        'G_continued_args_last': ('not ok', 'ok'),
        'G_continued_args_mid': ('ok', 'ok'),
        'G_continued_or_false_last': ('not ok', 'ok'),
        'G_continued_or_false_mid': ('not ok', 'ok'),
        'G_continued_or_true_last': ('ok', 'ok'),
        'G_continued_or_true_mid': ('ok', 'ok'),
        'G_continued_pipe_last': ('not ok', 'ok'),
        'G_continued_pipe_mid': ('ok', 'ok'),
        'G_double_negation_last': ('ok', 'not ok'),
        'G_double_negation_mid': ('ok', 'not ok'),
        'G_eval_string_mid': ('ok', 'ok'),
        'G_first_command': ('ok', 'ok'),
        'G_last_command': ('not ok', 'ok'),
        'G_last_past_comment_blank': ('not ok', 'ok'),
        'G_lone_bang_last': ('not ok', 'ok'),
        'G_lone_bang_mid': ('ok', 'ok'),
        'G_lone_bang_semicolon_mid': ('ok', 'ok'),
        'G_mid_after_run': ('ok', 'ok'),
        'G_or_exit_1_last': ('not ok', 'ok'),
        'G_or_exit_1_mid': ('not ok', 'ok'),
        'G_or_fail_last': ('not ok', 'ok'),
        'G_or_fail_mid': ('not ok', 'ok'),
        'G_or_fallback_last': ('ok', 'ok'),
        'G_or_fallback_mid': ('ok', 'ok'),
        'G_or_false_last': ('not ok', 'ok'),
        'G_or_false_mid': ('not ok', 'ok'),
        'G_or_group_return_last': ('not ok', 'ok'),
        'G_or_group_return_mid': ('not ok', 'ok'),
        'G_or_group_true_last': ('ok', 'ok'),
        'G_or_group_true_mid': ('ok', 'ok'),
        'G_or_return_0_last': ('ok', 'ok'),
        'G_or_return_0_mid': ('ok', 'ok'),
        'G_or_return_1_last': ('not ok', 'ok'),
        'G_or_return_1_mid': ('not ok', 'ok'),
        'G_or_return_bare_last': ('not ok', 'ok'),
        'G_or_return_bare_mid': ('not ok', 'ok'),
        'G_or_return_var_last': ('not ok', 'ok'),
        'G_or_return_var_mid': ('not ok', 'ok'),
        'G_or_true_last': ('ok', 'ok'),
        'G_or_true_mid': ('ok', 'ok'),
        'G_paren_glued_mid': ('ok', 'ok'),
        'G_pipe_or_last': ('ok', 'ok'),
        'G_pipe_or_mid': ('ok', 'ok'),
        'G_pipeline_last': ('not ok', 'ok'),
        'G_pipeline_mid': ('ok', 'ok'),
        'G_quoted_operators_last': ('not ok', 'ok'),
        'G_redirect_glued_in_mid': ('ok', 'ok'),
        'G_redirect_glued_out_mid': ('ok', 'ok'),
        'G_semicolon_command_last': ('ok', 'ok'),
        'G_semicolon_command_mid': ('ok', 'ok'),
        'G_string_bang_mid': ('ok', 'ok'),
        'G_substitution_operators_last': ('not ok', 'ok'),
        'G_tab_indented_mid': ('ok', 'ok'),
        'G_trailing_comment_last': ('not ok', 'ok'),
        'G_trailing_comment_mid': ('ok', 'ok'),
        'G_trailing_semicolon_last': ('not ok', 'ok'),
        'G_trailing_semicolon_mid': ('ok', 'ok'),
        'G_triple_negation_last': ('not ok', 'ok'),
        'G_triple_negation_mid': ('ok', 'ok'),
        'G_two_tests_second_mid': ('not ok,ok', 'ok,ok'),
        'H_after_bg_mid': ('ok', 'ok'),
        'H_after_semicolon_last': ('not ok', 'ok'),
        'H_after_semicolon_mid': ('ok', 'ok'),
        'H_and_list_last': ('not ok', 'ok'),
        'H_and_list_mid': ('ok', 'ok'),
        'H_case_pattern_line_last': ('not ok', 'ok'),
        'H_case_pattern_line_mid': ('ok', 'ok'),
        'H_elif_head_return_mid': ('ok', 'not ok'),
        'H_if_head_return_last': ('ok', 'not ok'),
        'H_if_head_return_mid': ('ok', 'not ok'),
        'H_if_head_then_true_mid': ('ok', 'ok'),
        'H_inline_assign_subst_mid': ('not ok', 'ok'),
        'H_inline_echo_subst_mid': ('ok', 'ok'),
        'H_inline_group_mid': ('ok', 'ok'),
        'H_inline_subshell_after_command_mid': ('not ok', 'ok'),
        'H_inline_subshell_last': ('not ok', 'ok'),
        'H_inline_subshell_mid': ('not ok', 'ok'),
        'H_inline_subshell_nospace_mid': ('not ok', 'ok'),
        'H_or_list_last': ('not ok', 'ok'),
        'H_or_list_mid': ('ok', 'ok'),
        'H_status_read_by_test_mid': ('ok', 'not ok'),
        'H_time_last': ('not ok', 'ok'),
        'H_time_mid': ('ok', 'ok'),
        'H_time_p_mid': ('ok', 'ok'),
        'H_until_head_break_mid': ('ok', 'ok'),
        'H_while_head_return_mid': ('ok', 'not ok'),
        'I_comment_form_and_at_test': ('ok,not ok', 'ok,ok'),
        'I_comment_form_function_keyword_mid': ('ok', 'ok'),
        'I_comment_form_indented_mid': ('ok', 'ok'),
        'I_comment_form_last': ('not ok', 'ok'),
        'I_comment_form_mid': ('ok', 'ok'),
        'I_comment_form_no_parens_mid': ('ok', 'ok'),
        'I_one_liner_between': ('ok,ok,not ok', 'ok,ok,ok'),
        'I_one_liner_negation': ('not ok', 'ok'),
        'I_one_liner_subshell': ('not ok', 'ok'),
        'I_opener_indented_last': ('not ok', 'ok'),
        'I_opener_indented_mid': ('ok', 'ok'),
        'I_opener_tab_indented_last': ('not ok', 'ok'),
        'I_opener_tab_indented_mid': ('ok', 'ok'),
        'I_opener_trailing_command_last': ('not ok', 'ok'),
        'I_opener_trailing_command_mid': ('ok', 'ok'),
        'I_opener_trailing_comment_last': ('not ok', 'ok'),
        'I_opener_trailing_comment_mid': ('ok', 'ok'),
        'I_opener_trailing_negation': ('ok', 'ok'),
        'T_case_fallthrough_last': ('ok', 'ok'),
        'T_case_fallthrough_mid': ('ok', 'ok'),
        'T_case_last': ('not ok', 'ok'),
        'T_case_mid': ('ok', 'ok'),
        'T_case_no_dsemi_last': ('not ok', 'ok'),
        'T_case_no_dsemi_mid': ('ok', 'ok'),
        'T_case_pattern_command_last': ('not ok', 'ok'),
        'T_case_pattern_command_mid': ('ok', 'ok'),
        'T_done_semi_true_last': ('ok', 'ok'),
        'T_esac_semi_true_last': ('ok', 'ok'),
        'T_fi_and_or_last': ('ok', 'ok'),
        'T_fi_and_true_last': ('not ok', 'ok'),
        'T_fi_or_true_last': ('ok', 'ok'),
        'T_fi_pipe_last': ('ok', 'ok'),
        'T_fi_redir_and_last': ('not ok', 'ok'),
        'T_fi_redir_last': ('not ok', 'ok'),
        'T_fi_redir_pipe_last': ('ok', 'ok'),
        'T_fi_semi_true_last': ('ok', 'ok'),
        'T_for_last': ('not ok', 'ok'),
        'T_for_mid': ('ok', 'ok'),
        'T_if_elif_last': ('not ok', 'ok'),
        'T_if_elif_mid': ('ok', 'ok'),
        'T_if_else_else_last': ('not ok', 'ok'),
        'T_if_else_else_mid': ('ok', 'ok'),
        'T_if_else_then_last': ('not ok', 'ok'),
        'T_if_else_then_mid': ('ok', 'ok'),
        'T_if_in_group_last': ('not ok', 'ok'),
        'T_if_in_helper_last': ('not ok', 'ok'),
        'T_if_in_subshell_mid': ('not ok', 'ok'),
        'T_if_last': ('not ok', 'ok'),
        'T_if_mid': ('ok', 'ok'),
        'T_if_nested_last': ('not ok', 'ok'),
        'T_if_nested_mid': ('ok', 'ok'),
        'T_if_oneliner_before_last': ('not ok', 'ok'),
        'T_if_oneliner_before_mid': ('ok', 'ok'),
        'T_until_last': ('not ok', 'ok'),
        'T_until_mid': ('ok', 'ok'),
        'T_while_condition_multiline': ('ok', 'ok'),
        'T_while_last': ('not ok', 'ok'),
        'T_while_mid': ('ok', 'ok'),
        'X_run_negation_mid': ('not ok', 'not ok'),
        'X_test_bracket_mid': ('ok', 'ok'),
        'X_test_dbracket_mid': ('ok', 'ok'),
    }

    def shape(self, name, shapes):
        """(lines, extents, candidates) of the shape, its test count checked against the record."""
        lines = shapes[name].split("\n")
        extents = bash_test_extents(lines)
        self.assertEqual(len(self.RECORDED[name][0].split(",")), len(extents),
                         "%s: %d tests by bash's parse, %d verdicts recorded" % (name, len(extents), len(self.RECORDED[name][0].split(","))))
        return lines, extents, candidates(lines, extents)

    def test_every_negation_of_the_register_is_a_candidate_unless_declared_an_operator_or_text(self):
        # the recall half, over every test of every shape (the recorded-inert ones, in a test bats passes with the negated command
        # succeeding, are the ones a miss would hide; the read ones are counted too): the expected set is every `!` CHARACTER of the
        # test's text (_ANY_BANG, not the predicate's word rule _BANG), minus the lines NOT_A_NEGATION declares, so it is derived
        # from the shapes and the record and from no rule of this module's, and a `!` the word rule misses is a miss here
        shapes = ground_truth_shapes()
        self.assertEqual(sorted(shapes), sorted(self.RECORDED), "the register and the record cover the same shapes")
        negations, inert, line_start, misses = 0, 0, 0, []
        for name in sorted(shapes):
            lines, extents, found = self.shape(name, shapes)
            cands = {(c.line, c.col) for c in found}
            declared = NOT_A_NEGATION.get(name, {})
            for (o, c), v in zip(extents, self.RECORDED[name][0].split(",")):
                for i, j in _bangs(_ANY_BANG, lines, o, c):
                    if i + 1 in declared:
                        continue
                    negations += 1
                    inert += v == "ok"
                    line_start += lines[i][:j].strip() == ""
                    if (i, j) not in cands:
                        misses.append("%s:%d:%d (%s): %s" % (name, i + 1, j + 1, v, lines[i]))
        self.assertGreater(inert, 0, "no recorded-inert negation in the register: the gate would pin nothing")
        print("%d shapes: %d negations, %d in tests recorded ok, %d at line start; %d missed" % (len(shapes), negations, inert, line_start, len(misses)))
        self.assertEqual(misses, [], "%d negations of the register the predicate does not find:\n" % len(misses) + "\n".join(misses))

    def test_an_ok_test_without_a_candidate_holds_only_declared_bangs_or_none_and_every_declaration_holds(self):
        # the other recall half: a test recorded `ok` with no candidate is either text-only (every `!` in it declared) or holds no
        # `!` and says so in NO_NEGATION; a shape with such a test and neither reds. And the declarations themselves: a declared
        # line holds a `!` the predicate does not take, a NO_NEGATION test is recorded ok and holds no `!`
        shapes = ground_truth_shapes()
        without, problems = 0, []
        for name in sorted(shapes):
            lines, extents, found = self.shape(name, shapes)
            cands = {(c.line, c.col) for c in found}
            declared = NOT_A_NEGATION.get(name, {})
            verdicts = self.RECORDED[name][0].split(",")
            for t, ((o, c), v) in enumerate(zip(extents, verdicts)):
                bangs = list(_bangs(_ANY_BANG, lines, o, c))
                if v != "ok" or any(c_.test == t for c_ in found):
                    continue
                without += 1
                if bangs and any(i + 1 not in declared for i, _ in bangs):
                    problems.append("%s test %d: recorded ok, no candidate, and a `!` not declared in NOT_A_NEGATION" % (name, t + 1))
                if not bangs and t + 1 not in NO_NEGATION.get(name, ()):
                    problems.append("%s test %d: recorded ok, holds no `!`, and is not declared in NO_NEGATION" % (name, t + 1))
            for ln, what in declared.items():
                on_line = [(i, j) for o, c in extents for i, j in _bangs(_ANY_BANG, lines, o, c) if i == ln - 1]
                if not on_line:
                    problems.append("%s:%d: declared %s, but the line holds no `!` inside a test" % (name, ln, what))
                elif all(b in cands for b in on_line):
                    problems.append("%s:%d: declared %s, but the predicate takes every `!` on the line: a stale declaration" % (name, ln, what))
            for t in NO_NEGATION.get(name, ()):
                if not 1 <= t <= len(extents) or verdicts[t - 1] != "ok" or list(_bangs(_ANY_BANG, lines, *extents[t - 1])):
                    problems.append("%s test %d: declared as holding no negation, but is not an ok test without a `!`" % (name, t))
        self.assertGreater(without, 0, "no ok test without a candidate in the register: the declarations pin nothing")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_without_bats_the_agreement_half_skips_and_names_where_it_runs(self):
        # regression-1 of fork PR #778: absent bats is a skip that names CI's shell job and the versions the record stands on, never
        # a pass that verified nothing
        with unittest.mock.patch("shutil.which", return_value=None):
            for test in (self.test_the_record_is_what_bats_says_under_both_rewrites, self.test_decide_reads_every_test_of_the_register_whose_verdicts_differ_and_refuses_none):
                with self.assertRaises(unittest.SkipTest) as cm:
                    test()
                self.assertIn("shell job", str(cm.exception))
                self.assertIn(" and ".join(self.RECORDED_WITH), str(cm.exception))

    _record = None   # the one record_under_bats run of this process and its seconds, read by the agreement and the decision test

    @classmethod
    def record(cls):
        """(record_under_bats's result, the seconds it took), run once per process: the agreement test and the decision test read
        the same run, so the wrapper's register test costs one bats run over the directory."""
        if cls._record is None:
            t0 = time.monotonic()
            cls._record = (record_under_bats(ground_truth_shapes()), time.monotonic() - t0)
        return cls._record

    def skip_without_bats(self):
        if not shutil.which("bats"):
            self.skipTest("bats is not on PATH: the record (bats %s) stands unverified here; CI's shell job, the one cell that installs "
                          "bats, is where this runs" % " and ".join(self.RECORDED_WITH))

    def test_decide_reads_every_test_of_the_register_whose_verdicts_differ_and_refuses_none(self):
        # F1 of fork PR #871's commit-3 review: decide refused a `( ! cmd )` subshell on its own line as undecided, since bash blames
        # the compound's failure on the line before it, and the register could not see that: it read verdicts, never the blamed
        # line. Now decide is asked about every test of the register that holds one candidate (there the whole-file rewrite is the
        # corpus's per-candidate one), from the same run's outcomes and blamed lines: verdicts that differ are read, both ok is
        # inert, both not ok is undecided. The clause refusing a failure blamed outside the candidate's test fires on no shape
        # here; a bats blaming a shape's failure outside its test would show, by name
        self.skip_without_bats()
        shapes = ground_truth_shapes()
        (_, _, runs, output, version), _ = self.record()
        counts, several, none, problems = collections.Counter(), [], [], []
        for name in sorted(shapes):
            lines, extents, found = self.shape(name, shapes)
            for t, extent in enumerate(extents):
                cands = [c for c in found if c.test == t]
                if len(cands) != 1:
                    (several if cands else none).append(name)
                    continue
                pair = [runs[tag].get(name, [])[t] if t < len(runs[tag].get(name, [])) else None for tag in ("t", "f")]
                if None in pair:
                    problems.append("%s test %d: no verdict under one rewrite:\n%s" % (name, t + 1, output[-2000:]))
                    continue
                outcomes = tuple(r.outcome for r in pair)
                expected = "inert" if outcomes == ("ok", "ok") else "undecided" if outcomes == ("not ok", "not ok") else "read"
                verdict, message = decide(name, cands[0], extent, pair)
                counts[verdict] += 1
                if verdict != expected:
                    problems.append("%s test %d: `! true` %s, `! false` %s: decided %s, not %s: %s" % (
                        name, t + 1, _shown(pair[0]), _shown(pair[1]), verdict, expected, message))
        print("%s: decide over %d tests of the register: %d read, %d inert, %d undecided; %d with more than one candidate (%s) and %d with none not asked" % (
            version, sum(counts.values()), counts["read"], counts["inert"], counts["undecided"], len(several), ", ".join(several), len(none)))
        self.assertGreater(counts["read"], 0, "no test of the register decided read: the clause would be held to nothing")
        self.assertEqual(problems, [], "%d tests of the register decide does not read from its verdicts:\n" % len(problems) + "\n".join(problems))

    def test_the_record_is_what_bats_says_under_both_rewrites(self):
        self.skip_without_bats()
        shapes = ground_truth_shapes()
        (got_true, got_false, _, output, version), secs = self.record()
        print("%s: %d shapes, %d tests, in %.2f s" % (version, len(shapes), sum(len(v.split(",")) for v in got_true.values()), secs))
        recorded_with = version.split()[-1] in self.RECORDED_WITH
        for what, got, col in (("! true", got_true, 0), ("! false", got_false, 1)):
            self.assertEqual(got, {name: v[col] for name, v in self.RECORDED.items()},
                             "%s on this box against the record under the %s rewrite%s:\n%s" % (
                                 version, what, "" if recorded_with else " (a version the record was not verified against: %s)" % ", ".join(self.RECORDED_WITH),
                                 output[-6000:]))


CORPUS_SKIP = ("bats is not on PATH: the corpus's candidates stand undecided here; CI's shell job, the one cell that installs bats, is "
               "where this runs (tests/bats-bare-negation-shell-job.bats)")


class BatsCorpus(unittest.TestCase):
    """bats over the tree: every candidate of every suite (suite_files, bash_test_extents, candidates) is decided by bats itself,
    its negated pipeline rewritten to `! true` and to `! false` (rewrite) and the enclosing test run alone under each in a scratch
    copy of the tree (decide_under_bats, run_test_alone, every run bounded at RUN_TIMEOUT). Three verdicts (decide): read, the
    test's outcome turns on the negation, no report; inert, the test passes under both, the negation asserts nothing, a defect;
    undecided, both fail, the failure is blamed outside the candidate's test, bats gave no verdict (a run the bound ended among
    them), or the rewritten file does not parse. Each candidate's row is printed as it is decided, its head before its runs, so a
    run an outer bound ends (the wrapper test's BATS_TEST_TIMEOUT) leaves its candidate named in this test's output; an inert or
    undecided one's report in full (the message naming which, the line as written and under each rewrite, both outcomes, the
    blamed line, what bats said) follows the table, and the test fails on it. Where bats is absent this skips, naming CI's shell
    job: tests/bats-bare-negation-shell-job.bats runs it there, the one cell that installs bats."""

    SKIP = CORPUS_SKIP

    def test_every_candidate_of_every_suite_is_read_by_bats(self):
        if not shutil.which("bats"):
            self.skipTest(self.SKIP)
        root, files = ROOT, suite_files()
        decisions, t0 = [], time.monotonic()
        with tempfile.TemporaryDirectory() as scratch:
            for relpath in files:
                lines, extents = _read_suite(relpath)
                for cand in candidates(lines, extents):
                    print("%s:%d " % (relpath, cand.line + 1), end="", flush=True)   # the head before the runs: a run an outer bound ends is attributable
                    decisions.append(decide_under_bats(root, relpath, lines, extents, cand, scratch))
                    print(_row(decisions[-1]), flush=True)
        counts = collections.Counter(d.verdict for d in decisions)
        print("%d files: %d candidates, %d read, %d inert, %d undecided, in %.2f s" % (
            len(files), len(decisions), counts["read"], counts["inert"], counts["undecided"], time.monotonic() - t0), flush=True)
        reports = [report(d) for d in decisions if d.verdict != "read"]
        if reports:
            print("\n\n".join(reports), flush=True)
        self.assertEqual(reports, [], "%d candidate(s) bats did not read; the reports are above, and here:\n\n" % len(reports) + "\n\n".join(reports))

    def test_the_environment_handed_to_bats_has_no_bats_variable_no_outer_libexec_on_path_and_an_isolated_home_and_tmpdir(self):
        # under an outer bats (the shell job's wrapper) the process holds BATS_TEST_TIMEOUT and the rest; none may reach the inner
        # bats (a shape's bare `wait` hangs on the timeout watcher); a directory holding bats's libexec entry point (a `bats` beside
        # a bats-exec-test: the outer's libexec, first on PATH) is dropped wherever it stands, so the inner `bats` is a wrapper that
        # exports BATS_ROOT and not the entry point that expects it; a PATH without such a directory stands as it is, an absent
        # directory included; HOME and TMPDIR are fresh directories under the scratch one
        with tempfile.TemporaryDirectory() as d:
            libexec, bin_, absent = os.path.join(d, "libexec"), os.path.join(d, "bin"), os.path.join(d, "absent")
            for p, names in ((libexec, ("bats", "bats-exec-test")), (bin_, ("bats",))):
                os.makedirs(p)
                for n in names:
                    open(os.path.join(p, n), "w").close()
            with unittest.mock.patch.dict(os.environ, {"BATS_TEST_TIMEOUT": "180", "BATS_RUN_TMPDIR": d, "KEEP_ME": "1",
                                                       "PATH": os.pathsep.join((libexec, bin_, libexec))}):
                env = _bats_env(d)
            with unittest.mock.patch.dict(os.environ, {"PATH": os.pathsep.join((bin_, absent))}):
                plain = _bats_env(d)
        self.assertEqual([k for k in env if k.startswith("BATS_")], [])
        self.assertEqual(env["KEEP_ME"], "1")
        self.assertEqual(env["PATH"], bin_)
        self.assertEqual(plain["PATH"], os.pathsep.join((bin_, absent)))
        self.assertEqual((env["HOME"], env["TMPDIR"]), (os.path.join(d, "home"), os.path.join(d, "tmp")))

    def test_without_bats_the_corpus_skips_and_names_where_it_runs(self):
        with unittest.mock.patch("shutil.which", return_value=None):
            with self.assertRaises(unittest.SkipTest) as cm:
                self.test_every_candidate_of_every_suite_is_read_by_bats()
        self.assertIn("shell job", str(cm.exception))
        self.assertIn("tests/bats-bare-negation-shell-job.bats", str(cm.exception))

    def test_decide_reads_a_candidate_only_when_one_rewrite_fails_inside_its_test_and_names_the_other_cases(self):
        # the three-way rule on synthetic runs: read needs `ok` under one rewrite and `not ok` under the other, whichever way round
        # (a condition head fails under `! false`), blamed inside the candidate's test: its own line, or another of the test's from
        # the opener to the close (the line before a `( ! cmd )` subshell, the `[ ]` reading a saved status); both `ok` is inert;
        # everything else is undecided, and its message says what was seen, so an inert report and an undecided one cannot be
        # confused: a failure blamed outside the test (a teardown's line, a line of another file, no line), no verdict, a run the
        # bound ended
        ok = BatsRun("ok", None, None, "", 0.0)
        bad = lambda line, file="tests/x.bats": BatsRun("not ok", line, file, "", 0.0)
        cand, extent = Candidate(0, 9, 4, False), (7, 11)   # 1-based line 10 of a test spanning lines 8 to 12
        for runs in ([bad(10), ok], [ok, bad(10)], [bad(9), ok], [bad(8), ok], [ok, bad(12)]):
            self.assertEqual(decide("tests/x.bats", cand, extent, runs)[0], "read", runs)
        inert = decide("tests/x.bats", cand, extent, [ok, ok])
        self.assertEqual(inert[0], "inert")
        self.assertIn("asserts nothing", inert[1])
        for runs, said in (([bad(10), bad(10)], "fails under both rewrites"),
                           ([bad(13), ok], "blamed on tests/x.bats line 13, outside the candidate's test (tests/x.bats lines 8 to 12)"),
                           ([ok, bad(7)], "blamed on tests/x.bats line 7, outside the candidate's test"),
                           ([ok, bad(10, "tests/helper.bash")], "blamed on tests/helper.bash line 10, outside the candidate's test"),
                           ([ok, bad(None)], "blamed on tests/x.bats line None, outside the candidate's test"),
                           ([BatsRun("skipped", None, None, "ok 1 x # skip why", 0.0), ok], "the outcome was `skipped`"),
                           ([ok, BatsRun("no such test", None, None, "", 0.0)], "the outcome was `no such test`"),
                           ([BatsRun("did not load", None, None, "", 0.0), bad(10)], "the outcome was `did not load`"),
                           ([ok, BatsRun("timed out", None, None, "1..1", 61.2)], "under `! false` bats gave no verdict on the test: the run was ended after 61 s with no verdict"),
                           ([BatsRun("no run", None, None, "the rewritten file does not parse under bash -n: x", 0.0), ok], "does not parse under bash -n"),
                           ([BatsRun("no run", None, None, "the negated pipeline runs off the end of the text", 0.0), ok], "runs off the end")):
            verdict, message = decide("tests/x.bats", cand, extent, runs)
            self.assertEqual(verdict, "undecided", message)
            self.assertIn(said, message)
            self.assertNotIn("asserts nothing", message)


def _processes_of(path, ignore=()):
    """The pids of the processes whose command line holds the path (pgrep -f), the ignored ones left out: bats-exec-suite,
    bats-exec-file and bats-exec-test carry the suite's absolute path, so a run of a tree under the path shows here while any of it
    lives."""
    r = subprocess.run(["pgrep", "-f", "--", path], capture_output=True, text=True)
    return [int(p) for p in r.stdout.split() if int(p) not in ignore]


def _within(secs, pred):
    """Whether pred came true within secs seconds, polled every 0.1 s."""
    t0 = time.monotonic()
    while not pred():
        if time.monotonic() - t0 > secs:
            return False
        time.sleep(0.1)
    return True


class BatsRoad(unittest.TestCase):
    """The corpus road's pieces against the bats on PATH, on synthetic suites: the TAP reader (run_test_alone), the bound on a run
    and the TERM to the process running one (_run_bats), a suite decided candidate by candidate (decide_under_bats). Each skips
    without bats, naming the wrapper that runs this class in CI's shell job."""

    # a test polling for a file that never comes: a loop whose condition is a negation runs forever under `! false`, and as written
    # too; the teardown leaves a marker, so whether the group was ended by TERM (bats runs the teardown) or KILL (it does not) shows
    POLL = ('@test "poll" {\n    while ! test -e "$TMPDIR/ready"; do sleep 0.1; done\n}\n'
            'teardown() {\n    echo torn > "$TMPDIR/torn"\n}\n')

    def hanging_suite(self, d):
        """A tree under d holding tests/hang.bats (POLL); returns the tree."""
        tree = os.path.join(d, "tree")
        os.makedirs(os.path.join(tree, "tests"))
        with open(os.path.join(tree, "tests", "hang.bats"), "w", encoding="utf-8") as f:
            f.write(self.POLL)
        return tree

    def test_run_test_alone_reads_what_bats_says_of_a_frame_a_skip_an_unloadable_file_and_a_missing_name(self):
        # the TAP reader against the bats on PATH: a failure inside a helper is blamed on the helper's line (the innermost frame),
        # a skipped test is no verdict, a file bash cannot load is `did not load` under both bats names for it, a name bats runs
        # no test for is `no such test`, and a name holding ERE metacharacters and a `$` is matched literally, as written
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tree", "tests"))
            with open(os.path.join(d, "tree", "tests", "probe.bats"), "w", encoding="utf-8") as f:
                f.write('@test "helper (x) $HOME" {\n    _h() {\n        run true\n        ! true\n    }\n    _h\n    true\n}\n'
                        '@test "line start" {\n    true\n    ! true\n}\n@test "skipped one" {\n    skip "no reason"\n}\n@test "ok one" {\n    ! true\n    true\n}\n')
            with open(os.path.join(d, "tree", "tests", "bad.bats"), "w", encoding="utf-8") as f:
                f.write('@test "bad" {\n    echo "\n}\n')
            tree = os.path.join(d, "tree")
            run = run_test_alone(tree, "tests/probe.bats", "helper (x) $HOME", d)
            self.assertEqual((run.outcome, run.line, run.file), ("not ok", 4, "tests/probe.bats"), run.detail)
            self.assertIn("from function `_h'", run.detail)
            run = run_test_alone(tree, "tests/probe.bats", "line start", d)
            self.assertEqual((run.outcome, run.line, run.file), ("not ok", 11, "tests/probe.bats"), run.detail)
            self.assertEqual(run_test_alone(tree, "tests/probe.bats", "skipped one", d).outcome, "skipped")
            self.assertEqual(run_test_alone(tree, "tests/probe.bats", "ok one", d).outcome, "ok")
            self.assertEqual(run_test_alone(tree, "tests/probe.bats", "no such name", d).outcome, "no such test")
            self.assertEqual(run_test_alone(tree, "tests/bad.bats", "bad", d).outcome, "did not load")
        self.assertEqual(_test_name('@test "a (b) $c" {'), "a (b) $c")
        self.assertEqual(_test_name("@test 'q' {"), "q")
        self.assertEqual(_ere_literal("a (b) $c [d] x.y|z*"), r"a \(b\) \$c \[d\] x\.y\|z\*")

    def test_under_an_outer_bats_path_the_inner_run_still_blames_the_test_file(self):
        # the wrapper's inner run inherits the outer bats's PATH, whose first entry is the outer's libexec directory (bats puts it
        # there), with every BATS_* variable scrubbed: the `bats` there expects the BATS_ROOT its bin wrapper exports, and with
        # BATS_ROOT empty the frames bats drops (under $BATS_ROOT/lib and libexec) are not dropped, so an `exit 1` and a teardown
        # failure were blamed on bats-exec-test's own lines here, and under CI's /usr/local prefix the inner bats did not load at
        # all; this showed only once the register's decision test and the end-to-end teardown case ran under the wrapper. The
        # wrapper's precondition exactly: the libexec directory of the bats on PATH, read off a probe run, put first on PATH and no
        # BATS_* variable set; the exit is blamed on its own line of the test file
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            tree = os.path.join(d, "tree")
            os.makedirs(os.path.join(tree, "tests"))
            with open(os.path.join(tree, "tests", "probe.bats"), "w", encoding="utf-8") as f:
                f.write('@test "libexec" {\n    echo "$BATS_LIBEXEC" > "$HOME/libexec.txt"\n}\n@test "exit" {\n    true\n    ! true || exit 1\n}\n')
            run = run_test_alone(tree, "tests/probe.bats", "libexec", d)
            self.assertEqual(run.outcome, "ok", run.detail)
            with open(os.path.join(d, "home", "libexec.txt"), encoding="utf-8") as f:
                libexec = f.read().strip()
            self.assertTrue(os.path.isfile(os.path.join(libexec, "bats")), libexec)
            with unittest.mock.patch.dict(os.environ, {"PATH": libexec + os.pathsep + os.environ.get("PATH", "")}):
                self.assertEqual([k for k in os.environ if k.startswith("BATS_")], [], "a BATS_* variable is set here: not the wrapper's precondition")
                self.assertEqual(shutil.which("bats"), os.path.join(libexec, "bats"), "PATH does not resolve bats to the libexec entry point: this pins nothing")
                run = run_test_alone(tree, "tests/probe.bats", "exit", d)
            self.assertEqual((run.outcome, run.line, run.file), ("not ok", 6, "tests/probe.bats"), run.detail)

    def test_a_run_past_the_bound_is_timed_out_with_its_teardown_run_and_no_process_of_it_left(self):
        # F2 of fork PR #871's commit-3 review: run_test_alone had no bound, so a rewrite that never terminates hung the oracle,
        # locally forever and in CI to the wrapper's per-test bound, nameless. Bounded at 2 s the poll test comes back `timed out`
        # a few seconds later, its process group ended by TERM first (bats runs the teardown: the marker) and then KILL, nothing of
        # it left; decide makes an undecided verdict of it
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            tree = self.hanging_suite(d)
            t0 = time.monotonic()
            run = run_test_alone(tree, "tests/hang.bats", "poll", d, timeout=2)
            took = time.monotonic() - t0
            self.assertEqual(run.outcome, "timed out", run.detail)
            self.assertGreaterEqual(run.secs, 2)
            self.assertLess(took, 20, "the run was not ended near its bound")
            self.assertEqual(_processes_of(d), [], "processes of the ended run remain")
            self.assertTrue(os.path.exists(os.path.join(d, "tmp", "torn")), "the test's teardown did not run: the group was not ended by TERM first")
        verdict, message = decide("tests/hang.bats", Candidate(0, 1, 10, False), (0, 2), [BatsRun("ok", None, None, "", 0.1), run])
        self.assertEqual(verdict, "undecided")
        self.assertIn("the run was ended after %.0f s with no verdict" % run.secs, message)

    def test_a_term_to_the_process_running_a_rewrite_ends_the_inner_bats_with_it(self):
        # the wrapper test's BATS_TEST_TIMEOUT ends the test's direct children (bats's pkill -P), the python running the module,
        # and nothing below it, so the inner bats and its loop outlived the outer kill (measured in the commit-3 review). A python
        # running run_test_alone on the poll test, bounded at 60 s, is sent TERM once its bats is up: it exits by that TERM, and no
        # process of the run is left
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            tree = self.hanging_suite(d)
            code = ("import sys; sys.path.insert(0, %r)\nfrom tests.test_bats_bare_negation import run_test_alone\n"
                    "print(run_test_alone(%r, 'tests/hang.bats', 'poll', %r, timeout=60).outcome)" % (os.path.dirname(HERE), tree, d))
            p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(_within(30, lambda: _processes_of(d, ignore=(p.pid,))), "the inner bats did not come up within 30 s")
                p.send_signal(signal.SIGTERM)
                out, err = p.communicate(timeout=30)
            finally:
                if p.poll() is None:
                    p.kill()
                    p.communicate()
            self.assertEqual(p.returncode, -signal.SIGTERM, (out, err))
            self.assertTrue(_within(10, lambda: not _processes_of(d)), "processes of the run outlived the python that started it: %s" % _processes_of(d))

    def test_decide_under_bats_on_a_synthetic_suite_reads_a_last_negation_a_head_and_a_subshell_and_reports_the_rest(self):
        # the per-candidate road end to end on a tree of one suite: a mid-test `! true` is inert (ok under both) and its report
        # carries the message, the rewritten lines and both outcomes; a last `! true` is read (not ok on its line under `! true`);
        # a condition head whose branch returns 1 is read the other way round (not ok on its line under `! false`); a mid-test
        # negation followed by a failing command is undecided, both rewrites failing on the later line; a `( ! true )` subshell on
        # its own line is read, its failure blamed on the line before it (F1 of the commit-3 review: undecided before); a status
        # saved with `SAVED_RC=$?` and read by the teardown is undecided, the failure blamed outside the test, and the message says
        # so; a poll loop whose condition is the negation is undecided, its `! false` run ended at the bound (3 s here), and the
        # message says so (F2); a test declared `comment_form() { # @test` goes down the same road, its name matched by bats's `-f`
        # (tests-1: no such test before, when the module opened on the `@test` form alone)
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        text = ('@test "mid" {\n    ! true\n    true\n}\n'
                '@test "last" {\n    true\n    ! true\n}\n'
                '@test "head" {\n    if ! true; then return 1; fi\n    true\n}\n'
                '@test "later failure" {\n    ! true\n    false\n}\n'
                '@test "subshell" {\n    true\n    ( ! true )\n    true\n}\n'
                '@test "read in teardown" {\n    ! true\n    SAVED_RC=$?\n    true\n}\n'
                '@test "poll" {\n    while ! test -e "$TMPDIR/ready"; do sleep 0.1; done\n}\n'
                'teardown() {\n    [ "${SAVED_RC-1}" -eq 1 ]\n}\n'
                'comment_form() { # @test\n    ! true\n    true\n}\n')
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tree", "tests"))
            with open(os.path.join(d, "tree", "tests", "one.bats"), "w", encoding="utf-8") as f:
                f.write(text)
            lines = text.split("\n")
            extents = bash_test_extents(lines)
            found = candidates(lines, extents)
            self.assertEqual([c.line + 1 for c in found], [2, 7, 10, 14, 19, 23, 28, 34])
            decisions = [decide_under_bats(os.path.join(d, "tree"), "tests/one.bats", lines, extents, c, d, timeout=3) for c in found]
        self.assertEqual([(x.test, x.verdict) for x in decisions],
                         [("mid", "inert"), ("last", "read"), ("head", "read"), ("later failure", "undecided"), ("subshell", "read"),
                          ("read in teardown", "undecided"), ("poll", "undecided"), ("comment_form", "inert")])
        self.assertEqual([(r.outcome, r.line) for r in decisions[7].runs], [("ok", None), ("ok", None)])
        self.assertIn("tests/one.bats:34 in test 'comment_form': INERT", report(decisions[7]))
        self.assertEqual([(r.outcome, r.line) for r in decisions[1].runs], [("not ok", 7), ("ok", None)])
        self.assertEqual([(r.outcome, r.line) for r in decisions[2].runs], [("ok", None), ("not ok", 10)])
        self.assertEqual([(r.outcome, r.line) for r in decisions[3].runs], [("not ok", 15), ("not ok", 15)])
        self.assertIn("fails under both rewrites (blamed on line 15 and line 15)", decisions[3].message)
        self.assertEqual([(r.outcome, r.line) for r in decisions[4].runs], [("not ok", 18), ("ok", None)])
        self.assertEqual([(r.outcome, r.line) for r in decisions[5].runs], [("ok", None), ("not ok", 31)])
        self.assertIn("blamed on tests/one.bats line 31, outside the candidate's test (tests/one.bats lines 22 to 26)", decisions[5].message)
        self.assertEqual([r.outcome for r in decisions[6].runs], ["ok", "timed out"])
        self.assertTrue(3 <= decisions[6].runs[1].secs < 15, decisions[6].runs[1].secs)
        self.assertIn("under `! false` bats gave no verdict on the test: the run was ended after", decisions[6].message)
        self.assertIn("under `! false`: while ! false; do sleep 0.1; done  ->  timed out", report(decisions[6]))
        text = report(decisions[0])
        self.assertIn("tests/one.bats:2 in test 'mid': INERT: the test passes with the negated command succeeding and with it failing", text)
        self.assertIn("under `! true`: ! true  ->  ok", text)
        self.assertIn("under `! false`: ! false  ->  ok", text)
        self.assertIn("bats under `! false` said:", text)


if __name__ == "__main__":
    unittest.main()
