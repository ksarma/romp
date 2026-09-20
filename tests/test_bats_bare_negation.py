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
each one by running its test with the negated pipeline rewritten twice, to `! true` and to `! false`: a read negation fails the
test under exactly one of them, one that passes under both asserted nothing, and both failing, a failure blamed on another line or
a rewritten file bash does not parse is undecided and reported as such. The predicate over-approximates by construction: every `!`
standing as its own word in a test's text (_BANG: bounded by bash's metacharacters, the line's ends or a backtick, so
`!>/dev/null true`, `!(true)`, `` `! true` `` and a `!` alone on a line are words and `!=`, `$!` and `!cmd` are none), outside a
comment, a quoted string and a here-document's body, with no grammar of where a pipeline begins. Test bodies are
bash_test_extents, bash's own parse of the file as bats-preprocess rewrites it (an opener line's tail and a one-line test are in the
population). Comment, string and heredoc are bash's call too: the test's text up to the `!`, with ` || ||` appended, goes through
`bash -n` in the C locale (its English wording is what is read), which refuses the `||` token only in command text
(_command_context); a backtick substitution's text is opaque to bash -n, so a `!` inside one is a candidate whatever surrounds it,
and its pipeline ends at the closing backtick. Three exclusions are lexical, by the word before the `!`: `[ !`, `[[ !` and `run !`
(_OPERATOR_OF). A `!` that is another command's argument (`find . ! -name x`) is a candidate, and bats reports it as inert or
undecided: a false report on the visible side, none in the tree today. The one piece of grammar left is the negated pipeline's
extent: from the `!` to the line's first top-level `;`, `&&`, `||`, lone `&`, unmatched `)`, the closing backtick of the
substitution the `!` sits in, or comment, `|` and `|&` inside, a trailing `\` or `|` running on to the next line
(negated_pipeline_end), decided on the safe side and pinned by the register below; the rewrite keeps every `!` of a run (`! ! true`
negates twice, and bash reads a doubled negation's status) and replaces the command after it.

Over the 45 tests/*.bats at this head (BatsSuites lists a file's candidates and judges none): 229 `!` words file-wide, 191 of them
`[ !` and 21 of them, the ones the word rule takes next to a backtick, a `)` or a `>`, inside comments and strings; 12 candidates in
test bodies (bootstrap-sh.bats 184; install-optional-deps.bats 505; install-sh.bats 329, 400, 411; pr-orphans.bats 125;
romp-serve.bats 117, 309, 334, 382; romp-service.bats 683; romp-sessions.bats 84), in 4.2 s with the extents. Five more `!` words
sit at file scope in helpers and a setup (bats-state-isolation.bats 125, 126 and 129 twice; romp-postal.bats 47): outside the
subject, since a `!` there has no enclosing test to run alone. Two classes this instrument does not see: that file scope, and a
negation inside a string another shell runs (`eval "! true; true"`, `bash -c "! true; true"`), which is text to the predicate by
bash's reading of the test's own text (G_eval_string_mid and G_bash_c_string_mid, declared in the register).

The register (ground_truth_shapes, BatsGroundTruth) is the gate on the two things the instrument still asserts. Recall: every `!`
character of a shape's tests is a candidate unless NOT_A_NEGATION declares it text or an operator, and a test recorded `ok` with no
candidate holds only declared `!` characters or none (NO_NEGATION); the expected set is every `!` character of the text, derived
from the shapes and the record and not from the predicate's word rule, so a spelling the predicate misses reds it whatever the rule
says. Agreement: with bats on PATH the shapes go through the
corpus's own road (record_under_bats: candidates, extent, both rewrites, one bats run) and the per-test verdicts must equal
RECORDED, which holds both rewrites' columns and names the bats versions it was verified against (RECORDED_WITH: 1.10.0 on this
box and 1.11.1, CI's pin); without bats that half skips, naming CI's shell job, the one cell that installs bats, as where it runs.
Measured at this head: 367 shapes, 377 tests; under `! true` 225 ok and 152 not ok, under `! false` 368 ok and 9 not ok (the four
condition heads whose branch fails the test, `command _h` and `env _h`, which find no shell function, `run ! true`, which run
itself fails, and the doubled negation mid and last, whose inversions cancel). The 250 shapes of the earlier register keep their
260 recorded `! true` verdicts and are 260 ok under `! false`; every negation of the register is a candidate, the 139
recorded-inert line-start sites the earlier register counted and every one off line start among them.

Deleted here, not fixed: the line scanner's frame model (the brace-depth walk, its block ends and the coverage pin over them), its
heredoc classification (introducers, delimiter words, the skip) and its status-read grammar (`_plain_call`, `_helper_read`,
`_read_position`, `_closes_a_condition`, `_trailer`, `_fallback_fails`, the compound closes), with the Scanner cases that pinned
them; the shapes those cases held that the register lacked are register shapes now, verdicts recorded. A new spelling costs one
shape and two bats runs, and can produce only a report a human reads, never a silent exemption.
"""
import collections
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.realpath(__file__))

# bats-preprocess's BATS_TEST_PATTERN (bats-core 1.10 and 1.11, /usr/libexec/bats-core/bats-preprocess line 34): the lines it rewrites
# into functions before bash parses the file. group(1) the name, group(2) whatever follows the brace (a comment, a command, a
# one-line body)
_TEST_LINE = re.compile(r"^[ \t]*@test[ \t]+(.*[^ \t])[ \t]+\{(.*)$")
_TEST_OPENER = "_t() {"   # what a @test line is rewritten into here: the name dropped, the brace and its tail kept
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


def _rewritten(lines):
    """The lines with every @test line rewritten into a function opener, as bats-preprocess does before bash parses the file."""
    return [(_TEST_OPENER + m.group(2)) if (m := _TEST_LINE.match(l)) else l for l in lines]


def bash_test_extents(lines):
    """(open index, close index) for every test bash parses, from bash's own parse and not from this module's rules: every line
    matching bats-preprocess's test pattern is rewritten into a function opener the way it does, an opener counts when the lines
    before it parse as a complete script (so one inside a heredoc, a quoted string or another test does not; the lines are read from
    the last point known to parse whole, the previous test's close, which is the same test by induction), and its close is its own
    line when the rewritten line parses whole on its own (a one-line test), else the first later line beginning with `}` at which the
    opener and the lines between parse as a complete function. None for the close: no such line (the file does not parse under this
    bash). One `bash -n` per opener plus one per candidate close, no execution."""
    rewritten = _rewritten(lines)
    extents, after = [], 0   # after: the first line not yet known to be parsed whole, so the lines before an opener are checked once each
    for o, line in enumerate(lines):
        if o < after or not _TEST_LINE.match(line):
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
    the opener line from just after its brace (a one-line test's whole body), then every line before the close from column 0. The
    close line is `}` and whatever follows it, which bash runs at file scope, so it is not the test's."""
    yield o, _TEST_LINE.match(lines[o]).start(2)
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
        shift = len(_TEST_OPENER) - _TEST_LINE.match(lines[o]).start(2)   # the opener's columns move when the name is dropped
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


def rewritten_shape(lines, extents, repl):
    """The file with every candidate's negated pipeline rewritten to repl, the last first so the earlier ones' positions hold (an
    outer negation's pipeline may hold an inner one); each extent is read on the text as it stands when its turn comes. Raises
    ValueError when a candidate's pipeline runs off the end of the text."""
    out = list(lines)
    for cand in sorted(candidates(lines, extents), reverse=True):
        end = negated_pipeline_end(out, cand)
        if end is None:
            raise ValueError("line %d: the negated pipeline runs off the end of the text" % (cand.line + 1))
        out = rewritten_negation(out, cand, end, repl)
    return out


FIXTURE_LINE_REMEDY = ("bats-preprocess rewrites every line matching its test pattern wherever it sits, a heredoc or a string included, "
                       "so a fixture cannot carry such a line literally (it reaches the disk rewritten and the file declares a test it "
                       "never runs); write it through printf, or begin the line with something other than @test")


class BatsSuites(unittest.TestCase):
    def test_every_test_of_every_suite_is_closed_by_bash_and_its_candidates_are_listed(self):
        # the population is every tests/*.bats; per file, bash's own parse (bash_test_extents) is the derivation of each test's text:
        # a test bash cannot close, or a line bats-preprocess rewrites into a test that bash does not open as one (a fixture heredoc
        # holding a `@test` line), is a problem named here, since the candidates of such a file cannot be derived. The candidates
        # themselves are listed, not judged: bats judges them, where it is installed
        self.assertTrue(shutil.which("bash"), "bash is what bats runs tests under; without it nothing here can be derived")
        files = sorted(name for name in os.listdir(HERE) if name.endswith(".bats"))
        self.assertTrue(files, "no tests/*.bats: the population this reads is empty")
        problems, report, tests, total = [], [], 0, 0
        t0 = time.monotonic()
        for name in files:
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                lines = f.read().split("\n")
            extents = bash_test_extents(lines)
            opened = {o for o, _ in extents}
            for i, line in enumerate(lines):
                if _TEST_LINE.match(line) and i not in opened:
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
    compounds, opener forms) and the ones the round-8 findings of fork PR #778 and their refuters named (condition heads, lists,
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
    for name, tail in (("or_fallback", " || echo fb"), ("or_false", " || false"), ("or_return_1", " || return 1"), ("or_return_bare", " || return"),
                       ("or_return_0", " || return 0"), ("or_group_return", " || { echo no; return 1; }"), ("and_then", " && echo yes"), ("and_or", " && true || echo fb"),
                       ("and_or_false", " && true || false"),
                       ("pipeline", " | cat"), ("pipe_or", " | cat || echo fb"), ("semicolon_command", "; true"), ("trailing_semicolon", ";"),
                       ("trailing_comment", "   # note"), ("bg", " &\n    wait"),
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
    S["I_opener_trailing_negation"] = '@test "x" { ! true\n    true\n}\n'
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
    """({shape: comma-joined per-test verdicts under the `! true` rewrite}, {the same under `! false`}, bats's TAP output and
    stderr, the version line): every shape goes through the corpus road, its candidates found (candidates) and each one's negated
    pipeline rewritten (rewritten_shape) to `! true` and to `! false`, the two files run under bats in one directory, HOME and
    TMPDIR isolated, stdin /dev/null and every BATS_* variable unset (under BATS_TEST_TIMEOUT bats's timeout watcher is a
    background child a shape's bare `wait` waits on). Each test is renamed to carry its shape's index, the rewrite and its ordinal
    so the TAP lines map back (a @test line inside a heredoc or a string is renamed too, harmlessly: bats-preprocess rewrites it
    either way)."""
    names = sorted(shapes)
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "home"))
        for n, name in enumerate(names):
            lines = shapes[name].split("\n")
            extents = bash_test_extents(lines)
            for tag, repl in (("t", "! true"), ("f", "! false")):
                k = iter(range(1, 100))
                text = "\n".join(_TEST_LINE.sub(lambda m, n=n, tag=tag: m.group(0).replace(m.group(1), "s%03d_%s_t%d" % (n, tag, next(k)), 1), l)
                                 if _TEST_LINE.match(l) else l for l in rewritten_shape(lines, extents, repl))
                with open(os.path.join(d, "%03d_%s.bats" % (n, tag)), "w", encoding="utf-8") as f:
                    f.write(text)
        env = {k: v for k, v in os.environ.items() if not k.startswith("BATS_")}
        env.update(HOME=os.path.join(d, "home"), TMPDIR=d)
        version = subprocess.run([bats, "--version"], capture_output=True, text=True).stdout.strip()
        r = subprocess.run([bats, "-t", d], capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env)
    got = {"t": {}, "f": {}}
    for line in r.stdout.splitlines():
        m = re.match(r"^(ok|not ok) \d+ s(\d{3})_([tf])_t\d+", line)
        if m:
            got[m.group(3)].setdefault(names[int(m.group(2))], []).append(m.group(1))
    return ({name: ",".join(v) for name, v in got["t"].items()}, {name: ",".join(v) for name, v in got["f"].items()},
            r.stdout + r.stderr, version)


class BatsGroundTruth(unittest.TestCase):
    """The register: every shape of ground_truth_shapes under bats itself, the negated command succeeding. RECORDED holds each
    shape's verdicts per test in file order under the two rewrites the corpus road makes of a candidate's negated pipeline, `! true`
    (the shapes as written, the pipeline reduced to the word) and `! false`, pasted from bats; RECORDED_WITH names the bats
    versions the record was verified against. The gate has two halves. Recall: every `!` character of a shape's tests is a
    candidate unless declared an operator or text (NOT_A_NEGATION), and a test recorded `ok` with no candidate holds only declared
    `!` characters or none (NO_NEGATION); the expected set owes nothing to the predicate's word rule, so a spelling it misses reds
    here and a new shape costs one entry. Agreement: with bats on PATH the
    shapes go through the corpus road (record_under_bats) and the verdicts must equal the record, which pins the extent of the
    negated pipeline (a split that swallows a trailing comment or an operator changes a verdict) and the record itself (a bats whose
    semantics differ, or a stale record, reds). Without bats the agreement half SKIPS, saying where it runs: CI's shell job is the
    one cell that installs bats, and a run that verified nothing must not read like one that verified every shape."""

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
        'H_inline_subshell_mid': ('not ok', 'ok'),
        'H_inline_subshell_nospace_mid': ('not ok', 'ok'),
        'H_or_list_last': ('not ok', 'ok'),
        'H_or_list_mid': ('ok', 'ok'),
        'H_time_last': ('not ok', 'ok'),
        'H_time_mid': ('ok', 'ok'),
        'H_time_p_mid': ('ok', 'ok'),
        'H_until_head_break_mid': ('ok', 'ok'),
        'H_while_head_return_mid': ('ok', 'not ok'),
        'I_one_liner_between': ('ok,ok,not ok', 'ok,ok,ok'),
        'I_one_liner_negation': ('not ok', 'ok'),
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
            with self.assertRaises(unittest.SkipTest) as cm:
                self.test_the_record_is_what_bats_says_under_both_rewrites()
        self.assertIn("shell job", str(cm.exception))
        self.assertIn(" and ".join(self.RECORDED_WITH), str(cm.exception))

    def test_the_record_is_what_bats_says_under_both_rewrites(self):
        if not shutil.which("bats"):
            self.skipTest("bats is not on PATH: the record (bats %s) stands unverified here; CI's shell job, the one cell that installs "
                          "bats, is where this runs" % " and ".join(self.RECORDED_WITH))
        shapes = ground_truth_shapes()
        t0 = time.monotonic()
        got_true, got_false, output, version = record_under_bats(shapes)
        print("%s: %d shapes, %d tests, in %.2f s" % (version, len(shapes), sum(len(v.split(",")) for v in got_true.values()), time.monotonic() - t0))
        recorded_with = version.split()[-1] in self.RECORDED_WITH
        for what, got, col in (("! true", got_true, 0), ("! false", got_false, 1)):
            self.assertEqual(got, {name: v[col] for name, v in self.RECORDED.items()},
                             "%s on this box against the record under the %s rewrite%s:\n%s" % (
                                 version, what, "" if recorded_with else " (a version the record was not verified against: %s)" % ", ".join(self.RECORDED_WITH),
                                 output[-6000:]))


if __name__ == "__main__":
    unittest.main()
