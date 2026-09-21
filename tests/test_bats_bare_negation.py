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
standing as its own word in a test's text (_bang_at, over _word_ends, bash's word-break rule stated once and read for the `}`
too: a metacharacter, the line's start or a backtick before it, and the word ending after it as bash ends a word, at a
metacharacter or the line's end, a `<` or `>` before `(` and a lone `\` at the line's end excepted, or a backtick, so
`!>/dev/null true`, `!(true)`, `` `! true` ``, a `!` alone on a line and `!\` continued onto ` true` are words and `!=`, `$!`,
`!cmd`, `!<(true)` and `!\` continued onto `true` are none), outside a
comment, a quoted string and a here-document's body, with no grammar of where a pipeline begins. Test bodies are
bash_test_extents, bash's own parse of the file as bats-preprocess rewrites it (an opener line's tail and a one-line test are in the
population): a test's close is the first `}` after its opener that bash reads as the word `}` (_close_words, over the same
_word_ends: the brace ends a word where bash ends one; a brace glued to what precedes it is in the prefix and refused by the
parse itself), by line then column, at which the opener through
that brace parses as a complete function (_closes; _close_col reads the column), whether or not the rest of the brace's line parses
on its own; the text before it is the test's, and whatever follows it, on that line and on the lines after up to the next opener,
is file scope and no test's, a helper or a list on the close line, `    ! true; }; f() { ! false; }`, or one whose body runs on
to later lines, `    ! true; }; f() {` through its `}`. Before fork PR #871's round 2, sixth commit, every `}` was asked, and a
brace glued to a following character, `    true; }x 2>/dev/null || true`, `}# not a comment`, `}}`, one word to bash and no
close, was asked as the prefix through the brace, which the cut ends at, and answered as a close: the test ended there, the
negation on its later lines was no test's text and no candidate, and bats ran the file as written, `ok 1 x`, the negation unseen,
the silent direction (the module said the close is found as bash reads it while asking of braces bash reads as no word). Before
the eighth commit the boundary had two spellings, a regex for the `!` and a rule in _close_words for the `}`, each reading
_METACHARACTERS as the whole rule: `}<(true)`, one word to bash with the process substitution, was a close, the test ended there
and its later negation was no candidate, the silent direction; `!<(true)`, one word too, was a candidate bats reports; and `!\`
continued onto ` true`, `! true` to bash, matched no regex, so the test's negation was no candidate, the silent direction. One
function states the rule now, _word_ends, as bash's read_token_word reads the character after a word, and both readers use it
(_close_words, _bang_at; the run of `!` words a rewrite keeps whole follows a continuation too, _bang_run). Before
the fourth commit, the last brace after a `;` or `&` was read as
the close and a one-liner's text ran to its line's end, so the helper's negation was the test's candidate, decided by running a
test it is no part of: inert while armed, the silent direction; before the fifth commit the close was asked of a line whole, so
where the text after the real `}` opened a construct closing on a later line the close line was skipped, the extent ran to that
construct's close and its lines were the test's text, the same direction, and a close no line pattern named, `(true) }` or
`fi }`, was no close at all, the file refused. bats declares a test by either of two patterns, `@test "name" {` and `name() { # @test` (its BATS_TEST_PATTERN and
BATS_TEST_PATTERN_COMMENT; the second has no `^` and one group, the name, and is matched as bats matches it, by a search), and every
site here that reads an opener reads both (_test_line): before fork PR #871's commit 4 the module opened on the `@test` form alone,
so a test written the other way was run by bats and read by nothing here, and a file of one each was one test to it where bats ran
two. Comment, string and heredoc are bash's call too: the test's text up to the `!`, with ` || ||` appended, goes through
`bash -n` in the C locale (its English wording is what is read), which refuses the `||` token only in command text
(_command_context); a backtick substitution's text is opaque to bash -n, so a `!` inside one is a candidate whatever surrounds it,
and its pipeline ends at the closing backtick. Three exclusions are lexical, by the word before the `!`: `[ !`, `[[ !` and `run !`
(_OPERATOR_OF). A `!` that is another command's argument (`find . ! -name x`) is a candidate, and bats reports it as inert or
undecided: a false report on the visible side, none in the tree today. The one piece of grammar left is the negated pipeline's
extent (negated_pipeline), and bash decides it too: the walker proposes where the text may end, at every `;`, `&&`, `||`, lone
`&` and `)` of the text wherever it stands, at a `#` at the start of a word, and at the line's end, and at each proposal asks
`bash -n` whether the text so far, in a brace group, is a complete command (_pipeline_complete). Where it is, the pipeline ends
there (the closing backtick of the substitution the `!` sits in ends it unasked). Where an operator is not the end, it is inside
something bash reads whole, a quoted string, a `$( )` whatever quotes stand inside it, a `[[ ]]`, a `${ }`, a backtick
substitution, or a compound the `!` negates (`! { true; false; }`, `! if ...; fi`, `! case ... esac`), and the scan goes on past
it to the construct's end. The walker tracks no quote and no parenthesis (since fork PR #871's round 2, third commit: it tracked both to choose
its proposals, and a `$( )` inside double quotes opens a quoting context of its own, so a quote inside one desynchronised it, the
rest of the line read as a string, no operator in it was proposed, and the extent of `! cmd "$(echo "it's")"; true` ran to the
line's end, the `; true` that made the negation inert dropped by the rewrite and the site read as read, the silent direction);
what it reads of bash's lexing is the character after a backslash, that word's, and a blank a backslash escapes at a line's end,
a character of the word and no trailing blank (_text_end: `! true \ ` is complete and `! true \` continues; before round 2's third commit the
walker stripped the blank before asking, and bash read the escaped blank as a continuation). Whether a `#` begins a comment is
bash's call as well (_begins_comment: after a blank, a `|` or a subshell's `)` it does; glued to a `$( )` it is part of the
word). At a comment or at the line's end where bash wants more, the pipeline runs on to the next line: after a `|` or `|&` with
or without a comment after it, after a trailing `\`, inside an open quote, parenthesis, brace group or compound; a here-document
the pipeline introduces is its lines through the terminator, counted by bash (one warning per here-document still pending,
whatever the form: `<<WORD`, `<<-WORD`, the word quoted or not, two on one line, an introducer line ending in a comment or a `|`;
the body of another command's here-document introduced on the line before the `!` comes first and stays), and `$'...'`, like
every quoted string, is text bash refuses to end the pipeline inside. The walker proposes and bash disposes, and the register
below pins every form one shape each. The rewrite keeps every `!` of a run (`! ! true` negates twice, and bash reads a doubled
negation's status), replaces the command after it, and leaves the pipeline's later lines (continuations, here-document bodies
and terminators) empty, the line count kept.

Over the 46 suites at this head (the population is the glob CI's shell job hands bats, `tests/*.bats`, read off
.github/workflows/ci.yml by the reading tests/test_ci_bats_bound.py pins that step with, and a glob naming no file raises rather
than passing an empty corpus as clean: suite_files; BatsSuites lists a file's candidates and judges none; BatsCorpus has bats decide
them): 232 `!` words file-wide, 191 of them `[ !`, 24 inside comments and strings (the word rule takes a `!` next to a backtick, a
`)` or a `>`), 5 at file scope, and 12 candidates in test bodies (bootstrap-sh.bats 184; install-optional-deps.bats 505;
install-sh.bats 329, 400, 411; pr-orphans.bats 125; romp-serve.bats 117, 309, 334, 382; romp-service.bats 683; romp-sessions.bats
84), listed in 7.35 s with the extents (one `bash -n` per `}` word of a test's lines through its close since the sixth commit,
7.02 s there and 7.52 s at the seventh commit, and one per `}` word of the close line for its column; the fifth commit asked
every brace, 8.36 s, and the head before it 6.89 s). bats
reads all 12 (BatsCorpus, under 1.10.0 and 1.11.1): the nine at line start are `not
ok` on their own line under `! true` and `ok` under `! false`; the three condition heads of romp-serve.bats (309, 334 and 382, `if
! _dead "$pid"; then kill ...; return 1; fi`) the reverse, `ok` under `! true` and `not ok` on their own line under `! false`, so
they are read only through the second rewrite; 0 inert, 0 undecided. Each rewrite runs twice (REPEATS) and four candidates are
decided at a time (CORPUS_WORKERS): 166.44 s of runs in 77.96 s on this box under 1.10.0 (74.75 s under 1.11.1), 119.63 s of the
runs the three heads' probe tests, whose slowest side is romp-serve.bats 334 under `! true`, 27.81 s for its two runs, against
which RUN_TIMEOUT stands at 60 s a run. The 5 file-scope `!` words sit in helpers and a setup (bats-state-isolation.bats 125, 126
and 129 twice; romp-postal.bats 47): outside the subject, since a `!` there has no enclosing test to run alone, and so is one in
the text after a test's close, on its close line or on the lines a construct opened there runs on to: a helper defined there, a
list joined to the definition, a case, a group, a subshell, an if, a while or a here-document (I_close_then_* and
I_one_liner_then_arming in the register: no candidate, and the next test, which calls the helper or reads what that text armed,
runs it as written). Two classes
this instrument does not see: that file scope, and a negation inside a string another shell runs (`eval "! true; true"`,
`bash -c "! true; true"`), which is text to the predicate by bash's reading of the test's own text (G_eval_string_mid and
G_bash_c_string_mid, declared in the register). The classes it reports without deciding, by construction, each with the case that
pins it (the register cannot hold them: record_under_bats runs its directory whole, so a shape that never ends would take every
verdict with it and a file bash does not parse loads no test; the pins are BatsRoad's, on synthetic suites down the corpus's own
road, and decide's synthetic runs): a rewrite that does not terminate, a loop whose condition is the negation (`while ! cmd; do
sleep 1; done` never ends under one rewrite), ended at RUN_TIMEOUT and reported undecided, its row's head printed before its runs
so a run an outer bound ends is attributable too (the poll case of the synthetic-suite test); a test whose runs under one rewrite
disagree, a failure nondeterministic for a reason unrelated to the negation, reported undecided with the disagreement named rather
than read from a pair that happened to differ (the alternating case); a test that skips (bats gives no verdict: `skipped`, the TAP
reader's case); two tests of one name in a file, which bats refuses whole (`Error: Duplicate test name(s) in file`, no TAP: the TAP
reader's duplicate case); a file bats could not load, a failure at file scope (`did not load`: `not ok N setup_file failed` under
1.10.0, `bats-gather-tests` under 1.11.1; the TAP reader's unloadable case); a test failing under both rewrites, and one whose
failure is blamed outside the test (the later-failure and read-in-teardown cases); a `not ok` bats prints no frame under (decide's
synthetic no-line case; bats prints one for every failure it traces); and a pipeline or a here-document body running off the end
of the text (Candidates' continuation-past-the-text case, and a test bash cannot close is refused before any candidate of it is
read). Four more roads end undecided with no case at this head, kept as backstops and named so the list above is not read as
exhaustive: more than one test line for the filter (`N tests`) and none (`no such test`), since bats's `-f` is matched here
against the literal name as written, the text this module reads as bats does (measured: `-f` filters on the raw name, a `$HOME`
or a `$( )` in it unexpanded, while `bats -t` prints the expanded description), so the filter finds exactly the test it names or
the file loads none; a run with no test line and no `1..0` plan for any other reason (`no TAP`, the duplicate-name refusal's
outcome, its detail bats's stderr, or `(bats printed nothing; exit N)` when there was none: a bats that ended before its plan, by
a signal or a failure of its own); and a rewritten file bash does not parse (decide's synthetic case), since the walker ends a
pipeline only where bash read the text so far as complete (before the third commit of round 2 an escaped blank at a line's end
reached it: the close blanked). A
negated compound command is not among them since fork PR #871's round 2, second commit: its operators are inside what bash reads whole, so the
extent runs to its close and bats decides it (the group case of the synthetic-suite test, undecided before). None in the tree
today, by the 12 rows.

The register (ground_truth_shapes, BatsGroundTruth) is the gate on the three things the instrument still asserts. Recall: every `!`
character of a shape's tests is a candidate unless NOT_A_NEGATION declares it text or an operator, and a test recorded `ok` with no
candidate holds only declared `!` characters or none (NO_NEGATION); the expected set is every `!` character of the text, derived
from the shapes and the record and not from the predicate's word rule, so a spelling the predicate misses reds it whatever the rule
says. Agreement: with bats on PATH the shapes go through the corpus's own road (record_under_bats: candidates, extent, both
rewrites, one bats run) and the per-test verdicts must equal RECORDED, which holds both rewrites' columns and names the bats
versions it was verified against (RECORDED_WITH: 1.10.0 on this box and 1.11.1, CI's pin); the extent's ends are pinned there one
shape each: its terminators (`; true`, `|| ...`, `&& false`, a lone `&` before `wait %%`, the unmatched `)`, the closing backtick,
a comment holding operators), its continuations (the line continued by `\`, by `|` with and without a comment after it, by `|&`
with one, by a comment line inside it, by an open quote, parenthesis or brace group: G_cont_*), `|&` inside it, the here-documents
it introduces in every form, mid and last (C_negated_heredoc_*, whose bodies are `false`), `$'it\'s'` in it and `$'a\'b'` before a
list operator (G_ansi_quote_*), an operator inside something bash reads whole (a `[[ ]]`, nested quotes, a `${ }`, backticks:
G_op_in_*), one a quote inside a `"$( )"` would hide from a walker tracking quotes, before a `; true` tail (G_hidden_semi_*), an
escaped blank or tab at the line's end and an escaped blank before a `; true` tail (G_escaped_*), a `#` glued to a metacharacter
where bash begins a comment and glued to a `$( )` where it does not (G_glued_*), a
negated compound of every kind followed to its close (G_negated_*), a close sharing its line (I_close_shares_last_line_*), one
introducing a here-document (I_close_introduces_heredoc_*, I_one_liner_heredoc) and one followed on its line by file-scope text
an armed negation stands in, a helper the next test calls or a list arming a variable it reads (I_close_then_*,
I_one_liner_then_arming: a walker reading the last brace as the close rewrites that negation and the next test's recorded verdict
changes), one whose file-scope text opens a construct closing on a later line, a function body, a case, a brace group, a
subshell, an if, a while, a here-document (I_close_then_*_lines: a walker asking the close of a line whole skips the line, runs
the extent to the construct's close, rewrites the negation inside it, and the next test's verdict changes), and a close after a
`)` or a `fi` with no `;` before the brace (I_close_after_*: no close to a line pattern, the file refused), a brace glued to a
following character or continued by a `\` onto the next line's word, no close to bash (I_close_glued_*,
I_close_backslash_newline_word: a walker asking every brace ends the test there, finds no candidate, and records the file as
written under both rewrites), one glued before the real close on the close line and on a one-liner (I_close_glued_before_close,
I_one_liner_glued_before_close: a walker asking every brace of the close line for the column cuts the text at the glued one,
loses the candidate before the close, and records the file as written the same way), with the closes bash does read beside
them, a `\` then an empty line, a comment after the close, and
a parameter expansion's brace before the close (I_close_backslash_newline_then_test, I_close_then_comment,
I_param_brace_then_close), a brace glued to a process substitution, `}<(true)`, `}>(true)`, one word to bash
(I_close_glued_procsub_*: a reader ending a word at every metacharacter reads a close, finds no candidate, and records the file
as written), with a redirection from one after the close beside it (I_close_then_procsub_redirect), and the `!` side of the one
rule: a `!` glued to a process substitution, one word, its `!` declared text (G_procsub_glued_*), one a blank away from it, a
negation (G_procsub_separated_*), a `!` continued by a lone `\` onto ` true`, `! true` to bash (G_bang_backslash_newline_*: a
reader with no continuation finds no candidate and records the file as written), onto `true`, one word, declared
(G_bang_backslash_newline_glued_mid), `! \` onto `true` (G_bang_blank_backslash_newline_*) and `! \` onto `! true`, a doubled
negation whose run the rewrite keeps whole (G_double_negation_continued_*: a run ending at the line's end drops the second `!`
and the doubled negation's record changes), so a split that stops short or runs past one changes a recorded verdict or loses
one. Decision:
decide, asked about every test of the register holding one candidate from the same run's outcomes and blamed lines, reads every
test whose verdicts differ, calls inert every one passing under both and undecided every one failing under both, so its refusal of
a failure blamed outside the candidate's test fires on no deterministic shape (bash blames a `( ! cmd )` subshell's failure on the
line before it, a multi-line one's on the @test line, and a saved `$?` on the `[ ]` reading it, all inside the test; a register
reading verdicts alone was blind to that clause, and to a bats that blamed differently). Without bats those two skip, as the corpus
test does, naming where they run (WHERE_BATS_RUNS): CI's shell job's Linux cell. The job has two cells on a dispatch or the weekly
schedule, ubuntu-latest and macos-latest, and both install a bats (the Linux one 1.11.1 from the release tarball, the macOS one
Homebrew's bats-core); tests/bats-bare-negation-shell-job.bats, a wrapper the job's `bats tests/*.bats` picks up, runs the
register class, the road class (the corpus road's pieces against bats: the TAP reader, the bound on a run, the TERM to the process
running one, a suite decided end to end) and the corpus test under python3 with every BATS_* variable unset (the job's
BATS_TEST_TIMEOUT would otherwise hang a shape's bare `wait` on bats's timeout watcher) and skips every one of them on the macOS
cell, whose bash 3.2.57 (actions/runner-images, images/macos/macos-15-Readme.md; ubuntu-latest ships 5.2.21) refuses the register's
bash-4 syntax, gives no here-document warning under -n, and whose Homebrew bats 1.14.0 the record is not verified against. Every
test of this module that derives from bash skips under such a bash wherever it runs, naming the bash and what it lacks
(bash_shortfall, skip_unless_bash_serves: BASH_4_SYNTAX and the warning; the Python cells run the module on macOS with no bats,
where before round 2's second commit the two recall tests, the extents and the candidates were red, and the two tests that need no bash run
there). The inner bats resolves through a PATH without the outer's libexec directory (_bats_env), since the entry point there
expects the BATS_ROOT the scrub removes and did not load under CI's /usr/local layout. Measured at this head: 531 shapes, 557
tests, in 75.61 s under 1.10.0 and 75.62 s under 1.11.1; under `! true` 317 ok and 240 not ok, under `! false` 540 ok and 17 not
ok (the four condition heads whose branch fails the test, `command _h` and `env _h`, which find no shell function, `run ! true`,
which run itself fails, the doubled negation mid and last and the doubled negation across a line continuation mid and last,
whose inversions cancel, `! true && false` mid and last, the backgrounded negation whose job status `wait %%` reads, mid and
last, the status saved with `rc=$?` and read by `[ ]`, and the brace glued to a `#`, `}# not a comment`, a command found
nowhere, `}#: command not found`, failing under both); decide over the 521 tests holding one candidate: 241 read, 276 inert, 4
undecided (`command _h`, `env _h`, `! true && false` last and `}# not a comment`, failing under both), the 9 holding two (the
doubled and tripled negations, the doubled negation across a line continuation, `if ! _h` and `! _h` mid and last with their
helpers) and the 27 holding none not asked (among them the fourteen `y` tests of I_close_then_*,
I_close_backslash_newline_then_test and I_one_liner_then_arming, which call or read what the file-scope text after a close
defines, or run after it, and the three tests whose one `!` is declared one word with what follows it, G_procsub_glued_* and
G_bang_backslash_newline_glued_mid). The 515 shapes of the head before this commit keep their recorded verdicts under both bats,
and their extents, close columns, candidates and rewrites are byte for byte that head's walker's (measured over every one of
them and the corpus's 24 rewrites: 0 differences; the `!` word rule's matches and the `}` words too, over every line of both; of
the 16 shapes this commit adds, 8 move, the glued process substitutions on both sides, the `!` continued onto ` true` and the
doubled negation across a join, and 8 read the same at both heads, the separated and the declared forms, controls), as each
head of fork PR #871's review kept the one before it (513, 506, 497, 493, 481, 429 and 381 shapes); the 250 shapes of the
earlier register keep their 260 recorded `! true` verdicts and are 260 ok under `! false`; every negation of the register is a
candidate (541, 299 of them in tests recorded ok, 495 at line start), the 139 recorded-inert line-start sites the earlier
register counted and every one off line start among them.

Deleted here, not fixed: the line scanner's frame model (the brace-depth walk, its block ends and the coverage pin over them), its
heredoc classification (introducers, delimiter words, the skip) and its status-read grammar (`_plain_call`, `_helper_read`,
`_read_position`, `_closes_a_condition`, `_trailer`, `_fallback_fails`, the compound closes), with the Scanner cases that pinned
them; the shapes those cases held that the register lacked are register shapes now, verdicts recorded. A new spelling costs one
shape and two bats runs, and can produce only a report a human reads: no silent exemption from a deterministic test. A
nondeterministic one is reported when its runs under a rewrite disagree (REPEATS), and where they happen to agree on both sides it
is read like a deterministic one, a chance repeating narrows and no number of runs closes.
"""
import ast
import collections
import concurrent.futures
import contextlib
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
# bash's metacharacters (man bash, Definitions: blank, tab, `|`, `&`, `;`, `(`, `)`, `<`, `>`, and the newline, a line's end
# here): the characters at which a word may end and after which one may begin. Where a word ENDS is _word_ends, the one statement
# of bash's word-break rule here, read by _close_words for the `}` and by _bang_at for the `!`; this set alone is read where a
# word may BEGIN, the character before a `!` (_bang_at) or before a `#` (negated_pipeline)
_METACHARACTERS = " \t|&;()<>"
_ANY_BANG = re.compile("!")   # every `!` character: the register's expected set (BatsGroundTruth), which owes nothing to the word rule


def _word_ends(lines, i, j):
    r"""Whether a word of lines[i] whose last character stands at column j - 1 ends there to bash: bash's word-break rule, stated
    once and read for the `}` (_close_words) and for the `!` (_bang_at), as read_token_word in bash's parse.y reads the character
    after the word. A metacharacter (_METACHARACTERS) or the line's end ends it, EXCEPT a `<` or a `>` immediately followed by
    `(`, which opens a process substitution and is the word's (read_token_word takes `$(`, `${`, `<(` and `>(` as part of the
    word before its word-break check; `$` is no metacharacter, so its forms glue by the last clause). A lone `\` at the line's end
    is a line continuation, which bash removes with the newline before it reads the word, so the character read is the next
    line's first, or the line after that's where the next line is a lone `\` again, and the word ends where there is no next line
    or the next line is empty. Every other character, a quote, a backtick, a `$`, a `#`, a `\` before a character (an escape, that
    character the word's), a word character, continues the word. bash -n (5.2.21): `f() { true; }` followed by each of ` ; true`,
    a tab, `;`, `&`, `|cat`, `<x`, `>/dev/null`, `<<EOF` with its body, `<<<x`, `>&2`, `&>/dev/null`, `>|/dev/null`, `<&0`,
    `|(true)`, `&(true)`, `;(true)` and nothing: exit 0, the brace the close; followed by `<(true)` or `>(true)`: `unexpected
    end of file`, exit 2, and exit 0 with a later `}` line, the brace glued; followed by `< (true)` or `> (true)`: `syntax error
    near unexpected token `('`, exit 2, the brace the close and the parenthesis refused (and ` <(true)`, a blank first: refused at
    the `<(true)` word, a word after a function's close); by `$(true)`, `${x}`, `$x`, `}`, `# c`, `x`, `'x'`, `"x"`, a backtick,
    `=1` or `\x`: exit 2, glued; by a lone `\` then `<(true)` on the next line: exit 2, glued through the join, and exit 0 with a
    later `}` line; by a lone `\` then ` (true)`: refused at the parenthesis, the brace the close. The same rule on the `!`:
    `f() { !<(true); }` and `f() { !>(true); }` parse, exit 0, one word, a command named `!/dev/fd/N` (`declare -f` keeps
    `!<(true)`), where `f() { ! <(true); }` is that command negated; `f() { !\` then ` true; }` is `! true` to `declare -f`,
    `!\` then `true` is `!true`, one word, and `!\` then `! true` is `!! true`, one word. Before fork PR #871's round 2, eighth
    commit, the boundary had two spellings, a regex for the `!` and a rule in _close_words for the `}`, each reading
    _METACHARACTERS as the whole rule: each read a `<` or `>` before `(` as a word's end (`}<(true)` a close bash does not read,
    the silent direction; `!<(true)` a candidate bats reports), and the regex read no continuation (`!\` then ` true`, `! true` to
    bash, no word and no candidate, the silent direction). The `!` reader adds one allowance on top of this rule, a backtick beside
    the `!` (_bang_at); the `}` reader adds none."""
    rest = lines[i][j:]
    while rest == "\\" and i + 1 < len(lines):   # a continuation: the character after the word is the next line's first
        i, rest = i + 1, lines[i + 1]
    if rest in ("", "\\"):
        return True
    return rest[0] in _METACHARACTERS and not (rest[0] in "<>" and rest[1:2] == "(")


def _bang_at(lines, i, j):
    r"""Whether a `!` standing at column j of lines[i] is its own word to bash: the character before it is a metacharacter
    (_METACHARACTERS), the line's start or a backtick, and the word ends after it (_word_ends), or a backtick follows it. So
    `!>/dev/null true`, `!(true)`, `! ! true`, `` `! true` ``, `` `!` `` and a `!` alone on a line (a pipeline of nothing, status
    1) are words, and `!=`, `$!`, `!cmd`, `!<(true)` and `!>(true)` (one word with the process substitution, a command bash finds
    nowhere) are none; a `!` whose line ends in a lone `\` after it is a word when the next line's first character ends the word
    (`!\` then ` true` is `! true` to bash) and none when it does not (`!\` then `true` is `!true`, `!\` then `! true` is
    `!! true`). The backtick is the one allowance on top of _word_ends, the safe side: a substitution's text begins and ends at
    one and bash -n reads nothing inside one, so `` `!` `` is a negation whose boundary this cannot see, and `` !`true` ``, one
    word to bash, a command named by the substitution, is a candidate bats reports, never a miss. The character before a `!` at
    a line's start is not read across a continuation (`true\` then `! true` is `true! true` to bash, one word): a `!` there is a
    word here, the safe side again, a candidate bats reports. The rule is bash's word boundary and no list of spellings: a `!` it
    takes that is no negation is a candidate bats reports."""
    line = lines[i]
    return (j < len(line) and line[j] == "!" and (j == 0 or line[j - 1] in _METACHARACTERS or line[j - 1] == "`")
            and (line[j + 1:j + 2] == "`" or _word_ends(lines, i, j + 1)))
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
    LANG, LC_MESSAGES or LANGUAGE the environment names (gettext ignores them all for the C locale). The stderr is decoded with
    replacement: a prefix cut inside a conditional command, `[[ "${x}`, has bash name the token it met as the end-of-input byte
    (0xff, no UTF-8), and since fork PR #871's round 2, fifth commit, bash_test_extents cuts a test's text at every `}` before its
    close that bash reads as the word `}` (every `}` until the sixth commit, `[[ "${x}" = y ]]` among them, in the tree; a
    `${x}` followed by a blank inside a `[[ "` still is), so a strict decode raised there; none of the phrases read is touched."""
    r = subprocess.run(["bash", "-n"], input="\n".join(lines) + "\n", capture_output=True, text=True, errors="replace", env=dict(os.environ, LC_ALL="C"))
    return r.returncode, r.stderr


def _bash_parses(lines):
    """Whether bash parses these lines as a complete script: `bash -n` exits 0 and reports no here-document cut off by the end of
    the input (a warning, exit 0, so it is read off stderr)."""
    rc, err = _bash_n(lines)
    return rc == 0 and "delimited by end-of-file" not in err


# what this module reads off the local bash, `bash -n` over a test's text, and the two things a bash must give for that reading to
# hold. The bash-4 syntax register shapes use, one construct each: `|&` (bash 4.0; A_pipeamp_*, G_pipeamp_*, G_cont_pipeamp_*),
# `coproc` (4.0; A_coproc_*) and `;;&` (4.0; T_case_fallthrough_*); candidates() raises on a test whose text it cannot parse, so a
# bash refusing one cannot parse the register or the snippets that use them. And the warning of a here-document the end of the
# input cuts off (`here-document at line N delimited by end-of-file`, exit 0), which _bash_parses reads to refuse a prefix cut
# inside one and _pending_heredocs counts to find where a negated pipeline's here-document ends: a bash without it opens a test
# line inside a file-scope here-document as a test and ends a negated pipeline's here-document at its introducer line, round 1's
# defect, silently. Every test deriving from bash skips under a bash lacking either, whole and loudly, naming the bash and what it
# lacks (skip_unless_bash_serves; fresh-1 of fork PR #871's round 1 gated the register's recall tests, which need no bats and run
# in every Python cell, and round 2's second commit the rest of the module, which the same bash red the same way). The matrix's bashes, from the
# runner images' READMEs (actions/runner-images, images/ubuntu/Ubuntu2404-Readme.md and images/macos/macos-15-Readme.md):
# ubuntu-latest 5.2.21; macos-latest 3.2.57, which refuses all three constructs and prints no such warning (`printf 'cat <<EOF\n' |
# bash -n` is silent, exit 0, under 3.2.57), in the Python cells on a dispatch or the weekly schedule only
BASH_4_SYNTAX = ("true |& cat", "coproc { true; }", "case a in a) true ;;& esac")
_BASH_PROBE = {}   # "shortfall": (the bash's version, what it lacks) or False, once probed (bash_shortfall)


def bash_shortfall():
    """(the local bash's version, what it lacks of what this module reads) when it lacks something, else False: the first construct
    of BASH_4_SYNTAX it refuses, or the here-document warning it does not give under -n; probed once per process."""
    if "shortfall" not in _BASH_PROBE:
        lacks = next(("refuses `%s`, which register shapes use" % text for text in BASH_4_SYNTAX if not _bash_parses([text])), None)
        if lacks is None and not _pending_heredocs(["cat <<EOF"]):
            lacks = "gives no warning of a here-document the end of the input cuts off under -n, which is how a here-document's end is read here"
        version = subprocess.run(["bash", "-c", 'printf %s "$BASH_VERSION"'], capture_output=True, text=True).stdout.strip() if lacks else None
        _BASH_PROBE["shortfall"] = (version, lacks) if lacks else False
    return _BASH_PROBE["shortfall"]


def skip_unless_bash_serves(case):
    """Skips the test case, saying so on stdout too, when the local bash lacks something this module reads (bash_shortfall)."""
    lacking = bash_shortfall()
    if lacking:
        reason = ("NOT RUN: bash %s %s, so nothing here can be derived under it; it runs under CI's Linux cells (bash 5.2.21) and skips "
                  "on macOS (3.2.57)" % lacking)
        print(reason)
        case.skipTest(reason)


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
    r"""(open index, close index) for every test bash parses, from bash's own parse and not from this module's rules: every line
    matching either of bats-preprocess's two test patterns (_test_line) is rewritten into a function opener the way it does, an
    opener counts when the lines before it parse as a complete script (so one inside a heredoc, a quoted string, another test or
    a construct the file-scope text after a close opened and a later line closes does not; the lines are read from the previous
    opener, whose test and the file-scope text after its close through the line before this opener must parse whole, which is
    the lines before it by induction), and its close is the first `}` after the opener that bash reads as the word `}`
    (_close_words, over _word_ends, the one statement of bash's word-break rule here, read for the `!` too: the character after
    the brace a metacharacter or the line's end, a `<` or `>` before `(` excepted, or the next line's first character where a
    lone `\` ends the line after it), by line then column, the opener line's own tail included (a one-line test), at
    which the opener through that brace parses as a complete function (_closes: a here-document the close introduces,
    `{ ! cat <<EOF; }` with its body and terminator after the brace, is read on past the close until bash reads none pending,
    since bash and bats read the test that way; before fork PR #871's round 2, second commit, the pending body left such a test
    with no close), whether or not the rest of the brace's line parses on its own: that rest, and the lines after it up to the
    next opener, bash runs at file scope, and they are no test's (_test_text). The character before the brace needs no rule: it
    is in the prefix bash is asked about, and a brace glued to a preceding word (`x}`, `${x}`, `$(true)}`, the second of `}}`)
    continues that word, so the function stays open and the parse refuses it (`_t() { echo ${x}` and `_t() { { true; }}` are
    each `unexpected end of file` to bash -n). The character after it is not in the prefix, since the cut ends at the brace, so
    it is read here: before fork PR #871's round 2, sixth commit, every `}` was asked, and one glued to a following character,
    `    true; }x 2>/dev/null || true`, `    true; }# not a comment`, `}}`, which is one word to bash and no close (the body runs
    on: `true; }x 2> /dev/null || true; ! false` to `declare -f`), was asked as the prefix through the brace and answered as a
    close, so the test ended there and its later lines, a negation among them, were no test's text and no candidate, while bats
    ran the file as written, `ok 1 x`: the silent direction. Before the fifth commit, the close was asked of a line WHOLE, and of
    lines a pattern named (one beginning with `}`, or holding one after a `;` or `&`): where the text after the real `}` opened a
    construct closing on a later line (`    ! true; }; f() {`, then the helper's body, then its `}`; a case, a group joined by
    `&&`, a subshell, an if, a while) the close line did not parse whole and was skipped, the extent ran to the construct's close,
    or to the next test's where the construct's close was no line the pattern named, and the construct's lines were the test's
    text, its negations the test's candidates, inert by running a test they are no part of while the next test fails once one is
    flipped, the same direction; and a close the pattern did not name, `(true) }`, `fi }`, was no close at all, the file
    refused. None for the close: the file does not parse under this bash (_no_close). One `bash -n` per opener plus one per `}`
    word of the test's lines through its close and one per line of a here-document read past it, no execution; _test_text asks
    one more per `}` word of the close line up to the close for the column (_close_col)."""
    rewritten = _rewritten(lines)
    extents, after, since = [], 0, 0   # after: the first line that may open a test; since: the opener the parse check reads from
    for o, line in enumerate(lines):
        if o < after or not _test_line(line):
            continue
        if not _bash_parses(rewritten[since:o]):   # the previous test and the file-scope text after it do not parse whole through here: not a top-level opener
            continue
        close, end = None, len(lines) - 1
        for c in range(o, len(lines)):
            for col in _close_words(rewritten, c):
                closed, read_to = _closes(rewritten, o, c, col)
                if closed:
                    close, end = c, read_to
                    break
            if close is not None:
                break
        extents.append((o, close))
        after, since = end + 1, o
    return extents


def _close_words(rewritten, c):
    r"""The columns of every `}` of rewritten[c] that bash reads as the word `}`, left to right: the brace ends a word where bash
    ends one (_word_ends, the rule the `!` reader reads too): the character after it a metacharacter or the line's end, a `<` or
    `>` before `(` excepted, or the next line's first character where a lone `\` ends the line after the brace. So a brace
    followed by anything else (`}x`, `}}`, `}#`, `}'x'`, `}$x`, `}=1`, `}\x`, one before a backtick, `` }`true` ``, and
    `}<(true)`, `}>(true)`, one word with the process substitution) is part of a longer word and closes nothing (bash -n:
    `f() { true; }x` and `f() { true; }<(true)` are `unexpected end of file`, and with a later `}` line each parses;
    `f() { true; }(true)`, `f() { true; })` and `f() { true; }< (true)` are refused at the parenthesis, the brace read as the
    close). A `\` alone after the brace at the line's end is a line continuation, which bash removes before it reads the word, so
    the character read is the first of the next line, or of the line after that where the next line is a lone `\` again, and the
    word ends where there is no next line or the next line is empty (bash -n on `f() { true; }\` followed by an empty line, by
    the end of the input, by ` ; true` or by `; true`: exit 0; followed by `x`, by `}`, by `\` then `x`, by `<(true)` or by the
    rewritten opener `_t() {`: `unexpected end of file`, and with a later `}` line the `x` form parses); two backslashes are an
    escaped backslash, a character of the word (`}\\` glues: `unexpected end of file`). The character BEFORE the brace is in the
    prefix _closes hands bash, so it needs no rule here: a brace continuing a preceding word (`x}`, `${x}`, `$(true)}`, the
    second brace of `}}`) leaves the function open and the parse refuses it, and a brace after a `)` (`(true)}`) is the word,
    the `)` a metacharacter, and parses as bash reads it. bash_test_extents and _close_col ask _closes of these braces and no
    other; before fork PR #871's round 2, sixth commit, they asked every `}`, and the cut just past the brace hid the glued
    character from bash; before the eighth commit this read _METACHARACTERS as the whole rule, and `}<(true)` was a close."""
    for m in re.finditer(r"\}", rewritten[c]):
        if _word_ends(rewritten, c, m.end()):
            yield m.start()


def _closes(rewritten, o, c, col=None):
    """(whether the rewritten opener at o through line c, the whole line or, given col, the line cut just past that column, parses
    as a complete function; the last line read): the lines o..c go through `bash -n`, and while bash reports a here-document still
    pending at the end of them (one line c introduces, its body after the brace: `{ ! cat <<EOF; }`, then the body, then `EOF`)
    the next line is appended and bash asked again, so the close is the brace's line and the body is read past it, as bash reads
    the file. A pending here-document another line introduced (a `}` inside its body) reads on to its terminator too, and then
    the function is unclosed, so that line closes nothing. The cut hides the character after the brace from bash, so the
    callers ask this only of a brace bash reads as the word `}` (_close_words); the character before it is in the text, and bash
    refuses a brace glued to a preceding word itself."""
    text, end = rewritten[o:c] + [rewritten[c] if col is None else rewritten[c][:col + 1]], c
    while True:
        rc, err = _bash_n(text)
        pending = err.count("delimited by end-of-file")
        if not pending or end + 1 >= len(rewritten):
            return rc == 0 and not pending, end
        end += 1
        text.append(rewritten[end])


def _close_col(rewritten, o, c):
    r"""The column of the brace that closes the test opened at rewritten[o] on line c, its close line by bash_test_extents: the first
    `}` of the line that bash reads as the word `}` (_close_words), left to right, at which the opener through that brace parses
    as a complete function (_closes, which reads a here-document the line introduces on past the brace). Every brace before it is
    inside the test (a group's close, `{ ! true; } }`; one in a string, `echo "a; }"`; one glued to a following character,
    `}x`, no word to bash: `    true; }x 2>/dev/null || true; ! true; }` closes at column 42, and the negation before that brace
    is the test's candidate, where asking every `}` gave column 10, the text cut there and the candidate lost, a mutation the
    sixth commit's pins did not red and fork PR #871's round 2, seventh commit, pins in Extents and in the register's
    I_close_glued_before_close), and whatever follows it bash runs at file scope: a helper defined after the close
    (`    ! true; }; f() { ! false; }`), a list joined to the function definition (`} && { ...; }`), a one-liner's tail
    (`@test "x" { ! true; } ; ! echo hi`). None when no brace of the line closes the test, which bash_test_extents' close rules
    out. Before fork PR #871's round 2, fourth commit, the column was a close-line pattern's greedy match, the LAST brace after a
    `;` or `&`, and a one-liner's text ran to its line's end, so the text after the real close was the test's, its `!` words the
    test's candidates, and a helper's negation there, armed by the next test that calls the helper, was decided by running the
    test it shares a line with, which it is no part of: inert, while that next test fails once it is armed. The silent direction;
    the tree had no such line (the `[;&]\s*}\s*\S` hits in tests/bats-state-isolation.bats are printf fixture strings)."""
    for col in _close_words(rewritten, c):
        if _closes(rewritten, o, c, col)[0]:
            return col
    return None


def _no_close(lines, o):
    """Why bash_test_extents found no close for the test opened at lines[o], read off bash: the file does not parse under this
    bash -n, the one cause met (a file bash parses closes every top-level function at a `}`, and the first brace bash reads as
    the word `}` (_close_words) at which the opener through it parses is that close, so bash_test_extents finds one; before fork
    PR #871's round 2, fifth commit, a close
    written in a form its line pattern did not name, `(true) }`, was the other cause). The other wording stands for a file bash
    parses, should a bash ever read one that way, and is pinned by calling this directly."""
    if _bash_parses(_rewritten(lines)):
        return "bash parses the file, yet no brace after the opener closes this test to bash -n: a reading not met before, to report"
    return "the file does not parse under this bash -n"


def _test_text(lines, o, c, rewritten=None):
    """(line index, the column the test's text begins at, the column it ends at or None for the line's end) for every line of the
    test bash opens at lines[o] and closes at lines[c]: the opener line from just after its brace (nothing of a comment-form
    opener's, whose brace is followed by the `# @test` comment alone: _tail_start), every line before the close from column 0,
    and the close line up to the brace that closes the test, the first at which the opener through it parses (_close_col, bash's
    call), when a command shares the line with it (`    ! true; }`), or a one-line test's body up to that brace; the `}` and
    whatever follows it bash runs at file scope (a helper defined there, a list joined to the definition, a one-liner's tail), so
    they are not the test's. Raises ValueError when no brace of the close line closes the test, which bash_test_extents' close
    rules out. `rewritten` is the file as _rewritten gives it, passed by a caller that holds it (candidates, once per file, since
    rewriting the whole file once per test made the corpus listing 40 times slower) and computed here otherwise."""
    if rewritten is None:
        rewritten = _rewritten(lines)
    start = _tail_start(_test_line(lines[o]))
    col = _close_col(rewritten, o, c)
    if col is None:
        raise ValueError("line %d: no brace of line %d closes this test, which bash_test_extents read as its close" % (o + 1, c + 1))
    if c == o:   # the opener's columns move when the name is dropped: the brace's column back on the line as written
        yield o, start, col - len(_TEST_OPENER) + start
        return
    yield o, start, None
    for i in range(o + 1, c):
        yield i, 0, None
    if lines[c][:col].strip():
        yield c, 0, col


def _bangs(pattern, lines, o, c, rewritten=None):
    """(line index, column) of every match of the pattern in the test's text (_test_text, handed `rewritten` when given)."""
    for i, start, end in _test_text(lines, o, c, rewritten):
        for m in pattern.finditer(lines[i], start, len(lines[i]) if end is None else end):
            yield i, m.start()


def _test_bangs(lines, o, c, rewritten=None):
    """(line index, column) of every `!` word (_bang_at, over the file as written: a continuation reads the next line) in the
    test's text (_test_text): the predicate's tokens. The register's expected set is every `!` character instead (_ANY_BANG
    through _bangs), so it owes nothing to this rule."""
    for i, start, end in _test_text(lines, o, c, rewritten):
        for j in range(start, len(lines[i]) if end is None else end):
            if _bang_at(lines, i, j):
                yield i, j


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
            raise ValueError("line %d: no close for this test: %s; its text is unknown" % (o + 1, _no_close(lines, o)))
        # the opener's columns move when the name is dropped; a comment-form opener's line holds no text of the test's, so no `!` of it
        # reaches here
        shift = len(_TEST_OPENER) - _tail_start(_test_line(lines[o]))
        for i, j in _test_bangs(lines, o, c, rewritten):
            if _word_before(lines[i], j) in _OPERATOR_OF:
                continue
            context = _command_context(rewritten, o, i, j + shift if i == o else j)
            if context:
                out.append(Candidate(t, i, j, context == "backticks"))
    return out


# the negated pipeline's extent (negated_pipeline): (line index, column) just past its text, trailing blanks excluded (a blank a
# backslash escapes is a character of the word and stays: _text_end), and the lines after the candidate's that the rewrite leaves
# empty: the lines its text ran on to, and the bodies and terminators of the here-documents it introduced; never a line of another
# command's here-document, introduced on the candidate's line before its `!`, whose body comes first among the bodies that follow
# the line and stays
Extent = collections.namedtuple("Extent", "line col blank")


def _pending_heredocs(lines):
    """How many here-documents bash, parsing these lines as a script, is still inside at the end of the input: it warns once per
    pending one (`here-document at line N delimited by end-of-file`), whatever else it reports of the text (an unclosed `$(` or
    `(` before the introducer included)."""
    return _bash_n(lines)[1].count("delimited by end-of-file")


def _pipeline_complete(own):
    """Whether bash reads the negated pipeline's own text (its lines from the `!`, the bodies and terminators of its here-documents
    included) as a complete command: the text wrapped in a brace group goes through `bash -n`, and a pipeline still wanting its
    next stage (a trailing `|` or `|&`, a comment after either or not), a trailing `\\`, an open quote, parenthesis, group or
    compound, an operator inside a quoted string, a `$( )`, a `[[ ]]`, a `${ }` or a backtick substitution, or a pending
    here-document leaves the group unclosed. The one reading of where a pipeline ends: at an operator character the walker found,
    at a comment, at a line's end; the walker proposes every operator character of the text and nothing more."""
    return _bash_parses(["{"] + own + ["}"])


def _text_end(line, stop):
    """The column just past the text of the line before column stop, trailing blanks excluded: a blank the backslash before it
    escapes is a character of the word and stays, so the text bash is asked about is the text bash reads (`! true \\ ` is a
    complete command, `! true \\` continues on the next line; an odd run of backslashes escapes the blank, `\\ `, and an even one
    is escaped backslashes and a blank, `\\\\ `)."""
    cut = len(line[:stop].rstrip())
    if cut < stop and (cut - len(line[:cut].rstrip("\\"))) % 2:
        cut += 1
    return cut


def _heredoc_lines(lines, cand, i, cut):
    """(another command's lines, the negated pipeline's own lines) among the here-document bodies and terminators that follow line
    i, for the here-documents introduced on it up to column cut, in the order bash reads them, introduction order: the ones
    introduced before the candidate's `!` on its line belong to an earlier command of that line and their bodies come first; the
    rest are the pipeline's. Counted by bash (_pending_heredocs) over the candidate's line from column 0 through (i, cut), so a
    `<<` inside a quote, a comment or a body introduces nothing and a here-string (`<<<`) or a shift (`<<` inside `$(( ))`) is
    none, and walked a line at a time until none is pending. ([], []) where the text holds no `<<`, which every introducer has
    (`[n]<<[-]word`, man bash, Here Documents). None when a body runs off the end of the text."""
    text = [lines[cand.line][:cut]] if i == cand.line else [lines[cand.line]] + lines[cand.line + 1:i] + [lines[i][:cut]]
    if "<<" not in "\n".join(text):
        return [], []
    total = pending = _pending_heredocs(["{"] + text)
    if not total:
        return [], []
    head = lines[cand.line][:cand.col]
    before = _pending_heredocs(["{", head]) if i == cand.line and "<<" in head else 0
    others, ours, k = [], [], i + 1
    while pending:
        if k >= len(lines):
            return None
        (others if total - pending < before else ours).append(k)
        pending = _pending_heredocs(["{"] + text + lines[i + 1:k + 1])
        k += 1
    return others, ours


def _begins_comment(own, text):
    """Whether a `#` following `text` (the pipeline's text so far on its line, after its earlier lines, own) begins a comment to
    bash: the text with `#'` appended and with `#"` appended go through `bash -n`, and a `#` that begins a comment hides either
    quote, so bash says the same of both; a `#` that is part of a word (`a#b`, `$#`, one inside a `${ }` or inside a quoted string)
    leaves a quote open, a different one each time. Asked only of a `#` at the start of a word, one
    at column 0 or after a blank or one of bash's metacharacters (`|#`, `)#`, `(#`), since a `#` inside a word never begins a
    comment; a `#` after a `)` begins one when the `)` closed a subshell (`(true)# note`) and not when it closed a `$( )`
    (`$(x)#b`, one word), which is bash's call to make."""
    return _bash_n(["{"] + own + [text + "#'"])[1] == _bash_n(["{"] + own + [text + '#"'])[1]


def negated_pipeline(lines, cand):
    r"""The Extent of the negated pipeline that begins at the candidate's `!`. The walker proposes where the pipeline's text may
    end, and bash decides at every proposal: at every `;`, `&&`, `||`, lone `&` (a redirection's `&>`, `>&` or `<&` is none, and
    the `&` of `|&` is that operator's) and `)` of the text, wherever it stands, the pipeline ends where bash reads the text so
    far as a complete command (_pipeline_complete), and where it does not the character is inside something bash reads whole and
    the scan goes on past it: a quoted string (`"a;b"`), a `$( )` whatever quotes stand inside it (`"$(echo "it's")"`,
    `"$(echo 'a"b')"`: a substitution opens a fresh quoting context), a `[[ ]]` (`! [[ a == b && c == d ]]`), a `${ }`
    (`${x:-a;b}`), a backtick substitution, or a compound the `!` negates (`! { true; false; }`, `! if true; then ...; fi`,
    `! case a in a) ... esac`, followed to its close; before fork PR #871's round 2, second commit, the walker ended the extent at the first such
    operator unasked, so the rewrite split the construct, and the remainder parsing on its own, an inert site read as read). The
    walker tracks no quote and no parenthesis: bash's answer at a proposal inside one is that the text is incomplete, so tracking
    would decide nothing bash does not, and its misreadings hid operators (before round 2's third commit the walker paired the quote inside a
    `"$( )"` with the one outside it, read the rest of the line as a string, proposed no operator in it, and the extent of
    `! cmd "$(echo "it's")"; true` ran to the line's end, so the rewrite dropped the `; true` that made the negation inert and
    the site was read as read, the silent direction). Two things it does read are bash's lexing of single characters: the
    character after a backslash is that word's (`\;` is no operator, `\#` no comment), so the scan skips it; and a blank a
    backslash escapes at a line's end is a character of the word and not a trailing blank (_text_end), so it stays in the text
    bash is asked about (`! true \ ` is complete and `! true \` continues; before round 2's third commit the walker stripped the blank before
    asking, so bash read a continuation and the line after it became the pipeline's, blank in the rewrite: mid-test an inert
    site read as read, last the close blanked and the file unparsed). A `#` at the start of a word begins a comment where bash
    reads one (_begins_comment: after a blank, a `|`, a `)` closing a subshell), and there, and at the line's end, the pipeline
    ends where bash reads the text so far as complete and runs on to the next line where bash wants more: after a `|` or `|&` (a
    comment after either too: bash continues the pipeline past it, and before round 2 the comment ended the extent there, so the
    rewrite split one pipeline into two commands and an armed site read as inert), after a trailing `\`, inside an open quote,
    parenthesis, brace group or compound. A here-document the pipeline introduces is bash's call as well (_heredoc_lines): its
    body and terminator lines are the pipeline's, blank in the rewrite, whatever the form (`<<WORD` or `<<-WORD`, the word quoted
    or not; two on one line, bodies in introduction order; an introducer line ending in a comment or in a `|`, the next stage
    following the terminator), and the body of a here-document another command introduced on the line before the `!` comes
    first and stays. Before round 2 the extent stopped at the introducer line's end, and the rewrite left the body and its
    terminator to run as commands. For a `!` inside a backtick substitution (cand.backticks) the first backtick not escaped by a
    backslash ends it, whatever quotes stand before it, since that is where bash closes the substitution and `bash -n` reads
    nothing inside one. None when the pipeline, or a body, runs off the end of the text: undecided, the safe side."""
    i, j = cand.line, cand.col + 1
    own, keep = [], set()
    while i < len(lines):
        line, n = lines[i], len(lines[i])
        start = cand.col if i == cand.line else 0
        while True:
            stop, kind = n, "end"   # where the pipeline's text may stop on this line, and what stands there
            while j < n:
                ch = line[j]
                if cand.backticks and ch == "`":
                    stop, kind = j, "backtick"
                    break
                if ch == "\\":   # the next character is the word's, whatever it is
                    j += 1
                elif ch == "|" and line.startswith("|&", j):   # one operator, inside the pipeline: its `&` is no lone `&`
                    j += 1
                elif ch in ";)" or line.startswith(("&&", "||"), j) or (ch == "&" and not line.startswith("&>", j) and not (j and line[j - 1] in "<>")):
                    stop, kind = j, "operator"
                    break
                elif ch == "#" and (j == 0 or line[j - 1] in _METACHARACTERS) and _begins_comment(own, line[start:j]):
                    stop, kind = j, "comment"
                    break
                j += 1
            cut = _text_end(line, stop)
            text = line[start:cut]
            bodies = _heredoc_lines(lines, cand, i, cut)
            if bodies is not None:
                others, ours = bodies
                if kind == "backtick" or _pipeline_complete(own + [text] + [lines[k] for k in ours]):
                    keep.update(others)
                    last = max([i] + others + ours)
                    return Extent(i, cut, tuple(k for k in range(cand.line + 1, last + 1) if k not in keep))
            if kind == "operator":   # not the pipeline's end to bash: inside something it reads whole, so the scan goes on past it
                j = stop + (2 if line.startswith(("&&", "||"), stop) else 1)
                continue
            if bodies is None:
                return None
            own.append(text)   # bash wants more: the pipeline runs on to the line after this one and its here-document lines
            keep.update(bodies[0])
            own.extend(lines[k] for k in bodies[1])
            i, j = max([i] + bodies[0] + bodies[1]) + 1, 0
            break
    return None


def negated_pipeline_end(lines, cand):
    """(line index, column) just past the negated pipeline's text (negated_pipeline), None when it runs off the end of the text."""
    ext = negated_pipeline(lines, cand)
    return None if ext is None else (ext.line, ext.col)


def _bang_run(lines, i, j):
    r"""The number of `!` words (_bang_at) in the run beginning at column j of lines[i], blanks between them, and a lone `\` at a
    line's end between them too, which bash removes with the newline so the next line's first word joins the run: 1 for `! true`
    and for `!\` then ` true`, 2 for `! ! true` and for `! \` then `! true` (`! ! true` to bash, its status read: `f() { ! \`
    then `! true; }` returns 0 and with `! false` returns 1), through a second lone `\` line too. Before fork PR #871's round 2,
    eighth commit, the run ended at the line's end, so the rewrite of `! \` then `! true` dropped the second `!`."""
    k = 0
    while _bang_at(lines, i, j):
        k, j = k + 1, j + 1
        while True:   # the blanks after the word, and a lone `\` ending the line, which joins the next line's first word to the run
            while j < len(lines[i]) and lines[i][j] in " \t":
                j += 1
            if lines[i][j:] == "\\" and i + 1 < len(lines):
                i, j = i + 1, 0
            else:
                break
    return k


def rewritten_negation(lines, cand, ext, repl):
    """The lines with the negated pipeline from the candidate's `!` to the extent's end (negated_pipeline) replaced by repl, the
    line count kept: every line of ext.blank (one the pipeline ran on to, a body or terminator line of a here-document it
    introduced) is left empty, a line of another command's here-document among them stays, and what followed the pipeline on its
    last line follows repl. Every `!` of the run at the candidate stays before repl (`! ! true` becomes `! ! false`): bash reads a
    doubled negation's status and exempts a tripled one, so the run is part of what bats is asked about, and the command after it
    is what is replaced. A tail beginning with `#` (a comment glued to the pipeline's last character, `! (true)# note`) gets a
    blank before it, since to bash a `#` begins a comment only at the start of a word and `true#` would be one word."""
    tail = lines[ext.line][ext.col:]
    if tail[:1] == "#" or (ext.line != cand.line and tail and not tail[0].isspace()):
        tail = " " + tail
    out = list(lines)
    out[cand.line] = lines[cand.line][:cand.col] + "! " * (_bang_run(lines, cand.line, cand.col) - 1) + repl + tail
    for k in ext.blank:
        out[k] = ""
    return out


def rewrite(lines, cand, repl):
    """The file's lines with the candidate's negated pipeline rewritten to repl: its extent (negated_pipeline) replaced
    (rewritten_negation), the line count kept. None when the pipeline runs off the end of the text: undecided, the safe side. The
    one road every rewrite takes, the corpus's per-candidate one (BatsCorpus) and the register's (rewritten_shape)."""
    ext = negated_pipeline(lines, cand)
    return None if ext is None else rewritten_negation(lines, cand, ext, repl)


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
    one (bash_test_extents): a fixture line inside a heredoc, a quoted string or another test, or an opener inside a construct
    the file-scope text after a test's close opened and a later line closes (`    ! true; }; if true; then` before it, `fi`
    after the test: bash defines the test's function when the construct runs, and bats runs the test). bats declares a test for
    each and runs a file that is not the one on disk, so the suite test names them (_unopened_problem, FIXTURE_LINE_REMEDY)."""
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
# file it names there, the TAP and stderr text, the wall time, and how many runs it stands for: 1, or the count of a side's
# agreeing runs (_agreed), whose secs is then their total, so a message about one run's time divides or says the count
BatsRun = collections.namedtuple("BatsRun", "outcome line file detail secs runs", defaults=(1,))
_TAP_TEST = re.compile(r"^(ok|not ok) \d+ (.*)$")
_TAP_SKIP = re.compile(r"^ok \d+ .* # skip( |$)")
_TAP_FRAME = re.compile(r"^# \((?:from function `[^']*' )?in (?:test )?file (\S+), line (\d+)")
# the bound on one bats run of the corpus road, in seconds. A rewrite that does not terminate (a loop whose condition is the
# negation, `while ! cmd; do sleep 1; done`, runs forever under `! false`, and `until ! cmd` under `! true`) would otherwise hang
# the oracle with no verdict and no row: under pytest forever, and in CI's shell job to the wrapper test's BATS_TEST_TIMEOUT
# (180 s), which names the wrapper and no candidate and ends python alone (bats's pkill -P reaches a test's direct children),
# leaving the inner bats and the loop running. A run ended at this bound is `timed out`: undecided, reported with its candidate.
# The bound stands well above the slowest legitimate run of the corpus (a romp-serve.bats probe test) and under the corpus's
# whole time, both measured in the module docstring, the one home of those figures, so one run ended at it still ends the corpus
# test inside the wrapper's 180 s
RUN_TIMEOUT = 60
# the bound on the register's one run over every shape: every shape terminates, so a run past it is an error and not a verdict, a
# backstop for a run with no outer bound (pytest)
REGISTER_TIMEOUT = 900


def _end_group(p, grace=5.0):
    """Ends the process group the process p leads (a Popen with start_new_session): TERM to the group, under which bats's EXIT
    traps run and so does a test's teardown (measured, with a CPU free to run it: a teardown's marker file is written under TERM
    and not under KILL; the open observation at BatsRoad's timeout test records the one run where it was not), then KILL to
    whatever of the group is left once the LEADER has exited, or after grace seconds when it has not: the wait between the two
    signals is Popen.wait on the leader, not on the group, so a bats leader that dies of the TERM at once (about 1 ms in the
    observation's measurement) is followed by the KILL within milliseconds, while a test process of the group may still be in
    its exit trap. Returns at once when the group is already gone at either signal."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            return
        try:
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue


# every bats process _run_bats has live, by its Popen, under a lock: a TERM to this process ends them all (_term_ends_live_runs)
_LIVE, _LIVE_LOCK = set(), threading.Lock()
# once a run's output holds what its caller needs (a test's verdict line: _run_bats's `done`), how many seconds a bats that has not
# exited is given before its group is ended and the output read: a test's teardown_file may still be running, and a child the test
# left holding bats's output stream (fd 3) may hold it for as long as it lives
VERDICT_GRACE = 5.0


@contextlib.contextmanager
def _term_ends_live_runs():
    """Within the block, a TERM to this process ends every bats group _run_bats has live (_end_group) and then takes its course, so
    no bats this module started outlives it: the wrapper test's BATS_TEST_TIMEOUT ends a test's direct children, the python running
    the module, and nothing below them. A handler can be set from the main thread only, so on another thread (a corpus worker,
    BatsCorpus) the block does nothing and the main thread's block around the pool covers the workers' runs."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def on_term(signum, frame):
        with _LIVE_LOCK:
            live = list(_LIVE)
        for p in live:
            _end_group(p)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTERM)

    previous = signal.signal(signal.SIGTERM, on_term)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def _read_text(path):
    """The file's text so far, decoded leniently (a child may be mid-write)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _run_bats(args, cwd, env, timeout, done=None):
    """(stdout, stderr, whether the bound ended it with nothing to read, the exit status, seconds) of one bats process, stdin
    /dev/null, its two output streams written to files under a scratch directory, in its own process group and bounded. The wait
    is on the PROCESS (Popen.wait, polled), never on the end of an output pipe: bats hands a test its TAP stream as fd 3, a child
    the test leaves in the background holds it open past the verdict, and a wait for EOF charged that child's lifetime to the run
    and reported it timed out with the complete verdict sitting in the captured output (extra6-1 of fork PR #871's round 1).
    `done`, when given, reads the output so far and says whether it already holds what the caller needs (run_test_alone: the
    test's TAP line, which bats prints after the test and its teardown); a process still running VERDICT_GRACE seconds after
    that, or at the bound, has its group ended (_end_group) and its output read, the flag clear. Past the bound with nothing
    done, the group is ended and the flag is set. A TERM to this process while the run is on ends the group first
    (_term_ends_live_runs, this process's live runs)."""
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as d:
        paths = [os.path.join(d, name) for name in ("out", "err")]
        with open(paths[0], "w", encoding="utf-8") as fo, open(paths[1], "w", encoding="utf-8") as fe:
            p = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=fo, stderr=fe, env=env, start_new_session=True)
        with _LIVE_LOCK:
            _LIVE.add(p)
        try:
            with _term_ends_live_runs():
                ended, seen = False, None
                while True:
                    try:
                        p.wait(timeout=0.1)
                        break
                    except subprocess.TimeoutExpired:
                        pass
                    now = time.monotonic()
                    if seen is not None and now - seen >= VERDICT_GRACE:
                        _end_group(p)
                        break
                    if now - t0 >= timeout:
                        ended = seen is None
                        _end_group(p)
                        break
                    if done is not None and seen is None and done(_read_text(paths[0])):
                        seen = now
        finally:
            with _LIVE_LOCK:
                _LIVE.discard(p)
        out, err = _read_text(paths[0]), _read_text(paths[1])
    return out, err, ended, p.returncode, time.monotonic() - t0


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
    bound ended with no test line out is `timed out` (one whose verdict was out when its group was ended, a background child of
    the test holding bats's fd 3, is read like any other: _run_bats's `done`). The detail carries the TAP after the plan line and
    bats's stderr, for the report."""
    out_text, err_text, ended, status, secs = _run_bats([bats, "-t", "-f", "^%s$" % _ere_literal(name), relpath], tree, _bats_env(scratch), timeout,
                                                        done=lambda text: re.search(r"^(ok|not ok) \d+ ", text, re.M) is not None)
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
    is unrelated to it), a side whose repeated runs disagree (`disagree`, from _agreed: the inference from a differing pair holds
    for a DETERMINISTIC test, and a test failing nondeterministically for a reason unrelated to the negation would otherwise be
    read from noise, its inert negation silently exempted), and a run bats gave no verdict on (a skip, a file that did not load,
    no such test, more than one test line for the filter, no test line and no plan at all (`no TAP`), a `not ok` with no frame
    under it, a run the bound ended, a rewrite bash does not parse). The message says which, so a maintainer can tell a negation bats read as inert from a position this
    instrument could not decide (fork PR #778 round 8, Group C's rule); a run standing for a side's agreeing runs (BatsRun.runs
    above 1, its secs their total) is described as that many runs, each ended at the bound, and never as one run of their total
    time."""
    for (what, _), run in zip(REWRITES, runs):
        if run.outcome == "disagree":
            return "undecided", "under `%s` %s; nothing was decided" % (what, run.detail.splitlines()[0])
        if run.outcome not in ("ok", "not ok"):
            ended = ("the run was ended after %.0f s" % run.secs if run.runs == 1 else
                     "the side's %d runs were each ended at the bound, %.0f s together," % (run.runs, run.secs))
            why = (run.detail if run.outcome == "no run" else
                   "%s with no verdict: a rewrite that does not terminate is one cause, a loop whose condition is this negation "
                   "running forever under one of the two" % ended if run.outcome == "timed out" else
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
# verdict and message (decide), the candidate's line under each rewrite, the run standing for each rewrite's side (_agreed, its
# seconds the side's and its runs their count), and the seconds every run took together
Decision = collections.namedtuple("Decision", "relpath cand test verdict message rewritten runs secs")
# how many times each rewrite of a corpus candidate runs (decide_under_bats). The two outcomes decide reads come from separate bats
# processes, so a differing pair proves a read only when each side's outcome is the test's own and not one run's noise: a side's
# runs must agree for the pair to count, and a side whose runs disagree is undecided and reported (tests-2, regression-2 and
# extra4-3 of fork PR #871's round 1: a test failing nondeterministically for a reason unrelated to its negation was read from a
# differing pair, and the inert negation was silently exempted). No silent exemption from a deterministic test; a nondeterministic
# one is reported, or, when its runs happen to agree on both sides, read like a deterministic one, which repeating narrows and no
# number of runs closes
REPEATS = 2
# how many corpus candidates are decided at a time (BatsCorpus): every run has its own copy of the tree and its own HOME and TMPDIR
# (decide_under_bats, _bats_env), so runs share nothing but the machine. REPEATS doubled the runs per candidate, and the wrapper
# test in CI's shell job holds the whole corpus to its BATS_TEST_TIMEOUT (180 s), which the candidates one after another would
# approach: measured in the module docstring
CORPUS_WORKERS = 4


def _agreed(repl, side):
    """One BatsRun standing for a side's runs (REPEATS of them, under the rewrite repl): the first, its seconds the side's total
    and its runs their count, when every run's outcome, blamed line and file are the first's; else a `disagree` run, undecided to
    decide, whose detail's first line names the nondeterminism and whose later lines carry each run's TAP, for the report."""
    secs = sum(r.secs for r in side)
    if all((r.outcome, r.line, r.file) == (side[0].outcome, side[0].line, side[0].file) for r in side):
        return side[0]._replace(secs=secs, runs=len(side))
    named = "the test's %d runs disagree (%s): its outcome does not turn on this rewrite alone, so no pair holding it is read as " \
            "evidence; a failure nondeterministic for a reason unrelated to this negation is the usual cause" % (len(side), ", then ".join(_shown(r) for r in side))
    return BatsRun("disagree", None, None, "\n".join([named] + ["run %d, %s:\n%s" % (n + 1, _shown(r), r.detail) for n, r in enumerate(side)]), secs, len(side))


def decide_under_bats(root, relpath, lines, extents, cand, scratch, bats="bats", timeout=RUN_TIMEOUT, repeats=REPEATS):
    """One candidate decided by bats: for each rewrite of REWRITES, `repeats` times over, the tree at root is copied whole into a
    fresh directory under scratch (without `.git`, `node_modules` and python caches, none of which a suite reads; the shell job's
    checkout has no node_modules when bats runs), the suite in the copy is replaced by the rewritten file (rewrite), and the
    enclosing test runs alone there (run_test_alone, bounded at timeout seconds); each copy is removed after its run. The runs of
    a side must agree for its outcome to count (_agreed): the two files differ in one word, so a differing pair proves a read
    only when each side's outcome is the test's own, and a side whose runs disagree is undecided, reported as such. A rewritten
    file bash does not parse, or a pipeline running off the text, is decided without a run: undecided."""
    o, _ = extents[cand.test]
    test = _test_name(lines[o])
    runs, shown, secs = [], [], 0.0
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
        side = []
        for r in range(repeats):
            d = os.path.join(scratch, "%s.%d.%d.%d" % (os.path.basename(relpath), cand.line + 1, k, r))
            tree = os.path.join(d, "tree")
            shutil.copytree(root, tree, symlinks=True, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".pytest_cache"))
            with open(os.path.join(tree, relpath), "w", encoding="utf-8") as f:
                f.write("\n".join(new))
            try:
                side.append(run_test_alone(tree, relpath, test, d, bats, timeout))
            finally:
                shutil.rmtree(d, ignore_errors=True)
        secs += sum(r.secs for r in side)
        runs.append(_agreed(repl, side))
    verdict, message = decide(relpath, cand, extents[cand.test], runs)
    return Decision(relpath, cand, test, verdict, message, shown, runs, secs)


def _shown(run):
    """A run's outcome for the table: `ok`, `not ok @<line>`, or why there was no verdict."""
    return "not ok @%s" % run.line if run.outcome == "not ok" else run.outcome


def _row(d):
    """A decision's row in the corpus table, after its head (`<path>:<line> `): the verdict, both outcomes, each side's seconds and
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
                       "with another word, a `name() { # @test` line with a word after `@test` in its comment. A construct the file-scope "
                       "text after a test's close opened is closed before the next test")


def _unopened_problem(name, i):
    """The problem BatsSuites names for line index i of the suite at name, a line bats-preprocess rewrites into a test that bash does
    not open as one (unopened_test_lines), with the four causes met and the remedy: inside a heredoc, a quoted string or another
    test (fixture lines), or inside a construct the file-scope text after a test's close opened and a later line closes (since
    fork PR #871's round 2, fifth commit, which reads that text as file scope; before the sixth the message named three causes)."""
    return ("%s:%d: a line bats-preprocess rewrites into a test that bash does not open as one (inside a heredoc, a quoted string, "
            "another test, or a construct the file-scope text after a test's close opened and a later line closes: `    ! true; }; if "
            "true; then` before the opener and `fi` after the test); %s" % (name, i + 1, FIXTURE_LINE_REMEDY))


class BatsSuites(unittest.TestCase):
    def setUp(self):
        skip_unless_bash_serves(self)

    def test_every_test_of_every_suite_is_closed_by_bash_and_its_candidates_are_listed(self):
        # the population is every suite the shell job's bats glob names (suite_files, read off the workflow; a glob naming no file
        # raises there); per file, bash's own parse (bash_test_extents) is the derivation of each test's text: a test bash cannot
        # close, or a line bats-preprocess rewrites into a test, under either of its patterns, that bash does not open as one (a
        # fixture heredoc holding a `@test` line or a `name() { # @test` line, or an opener inside a construct the file-scope text
        # after a close opened: _unopened_problem), is a problem named here, since the candidates of such a file cannot be
        # derived. The candidates themselves are listed, not judged: bats judges them, where it is installed
        self.assertTrue(shutil.which("bash"), "bash is what bats runs tests under; without it nothing here can be derived")
        files = suite_files()
        problems, report, tests, total = [], [], 0, 0
        t0 = time.monotonic()
        for name in files:
            lines, extents = _read_suite(name)
            for i in unopened_test_lines(lines, extents):
                problems.append(_unopened_problem(name, i))
            for o, c in extents:
                if c is None:
                    problems.append("%s:%d: no close for this test: %s; its text is unknown and no candidate of it can be derived" % (
                        name, o + 1, _no_close(lines, o)))
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

    def setUp(self):
        skip_unless_bash_serves(self)

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
        self.assertEqual(list(_test_text(lines, 0, 3)), [(0, len("first() { # @test"), None), (1, 0, None), (2, 0, None)])
        self.assertEqual(candidates(lines, extents), [Candidate(0, 1, 4, False), Candidate(1, 7, 4, False)])
        self.assertEqual(unopened_test_lines(lines, extents), [22])
        self.assertIsNone(_test_line("x() { # @test fixture"))
        self.assertIsNone(_test_line("x() {# @test"))
        self.assertEqual(_renamed("first() { # @test", "s000_t_t1"), "s000_t_t1() { # @test")
        self.assertEqual(_renamed("function third { # @test", "s000_t_t1"), "function s000_t_t1 { # @test")
        self.assertEqual(_renamed('@test "x" { true; }', "s000_t_t1"), "@test s000_t_t1 { true; }")

    def test_a_close_sharing_a_line_with_the_last_command_closes_the_test_and_that_line_is_the_tests_up_to_the_brace(self):
        # regression-4 of fork PR #871's round 1: the close-line pattern matched a line beginning with `}` only, so `    ! true; }`
        # closed nothing, the test had no close, and the message said the file does not parse under bash -n when bash parses it
        # and bats runs it. A close sharing its line with the test's last command is bash's call (round 1 widened the pattern to
        # a `}` after `;` or `&`; the fifth commit of round 2 dropped the pattern, and every `}` is asked: bash_test_extents), the
        # text before its brace is the test's (its `!` a candidate, one inside a string before the brace included), what follows
        # the brace is not, and a line beginning with `}` is a close whatever follows it. A brace with no `;` or `&` before it,
        # after a subshell's `)`, a `fi`, a `done`, an `esac` or a `]]`, closes the test too, as bash reads it (a reserved word
        # after a compound command's end) and bats runs it; before the fifth commit no pattern named such a line, the test had no
        # close and the message called its close a form not read here. The one cause of no close left is a file bash does not
        # parse, and the message says so; _no_close's other wording is pinned by calling it, since bash_test_extents reaches it on
        # no file bash parses
        lines = ('@test "x" {\n    true\n    ! true; }\n@test "y" {\n    true & }   # note\n@test "z" {\n    true\n}   ; ! true\n'
                 '@test "w" {\n    echo "a; }" ; ! true ; } ; true\n').split("\n")
        extents = bash_test_extents(lines)
        self.assertEqual(extents, [(0, 2), (3, 4), (5, 7), (8, 9)])
        self.assertEqual(list(_test_text(lines, 0, 2)), [(0, 11, None), (1, 0, None), (2, 0, len("    ! true; "))])
        self.assertEqual(list(_test_text(lines, 3, 4)), [(3, 11, None), (4, 0, len("    true & "))])
        self.assertEqual(list(_test_text(lines, 8, 9)), [(8, 11, None), (9, 0, len('    echo "a; }" ; ! true ; '))])
        self.assertEqual(candidates(lines, extents), [Candidate(0, 2, 4, False), Candidate(3, 9, 18, False)])   # the `!` after the third test's brace is file scope
        self.assertEqual(rewritten_shape(lines, extents, "! false")[2], "    ! false; }")
        self.assertEqual(rewritten_shape(lines, extents, "! false")[9], '    echo "a; }" ; ! false ; } ; true')
        for text, close in (('@test "x" {\n    true\n    { true; }; }\n', 2),   # the group's own brace before the `;` is the test's text
                            ('@test "x" {\n    (true) }\n', 1), ('@test "x" {\n    if true; then true; fi }\n', 1),
                            ('@test "x" {\n    for i in 1; do true; done }\n', 1), ('@test "x" {\n    case a in a) true;; esac }\n', 1),
                            ('@test "x" {\n    [[ a ]] }\n', 1)):
            lines = text.split("\n")
            self.assertEqual(bash_test_extents(lines), [(0, close)], text)
            self.assertEqual(list(_test_text(lines, 0, close))[-1], (close, 0, len(lines[close]) - 1), text)   # the text runs to the brace
        lines = '@test "x" {\n    echo "\n}\n'.split("\n")
        self.assertEqual(bash_test_extents(lines), [(0, None)])
        with self.assertRaises(ValueError) as cm:
            candidates(lines, bash_test_extents(lines))
        self.assertIn("the file does not parse under this bash -n", str(cm.exception))
        self.assertIn("no close for this test", str(cm.exception))
        self.assertIn("bash parses the file, yet no brace after the opener closes this test", _no_close(['@test "x" {', '    (true) }'], 0))

    def test_the_close_is_the_first_brace_at_which_the_test_parses_and_what_follows_it_is_file_scope(self):
        # fork PR #871's round 2, fourth commit (the silent direction): the close-line pattern's greedy group took the LAST brace after
        # a `;` or `&` as the close, and a one-liner's text ran to its line's end, so text after the real `}` was the test's: on
        # `    ! true; }; f() { ! false; }` the helper's negation (column 22) was a candidate of test x, decided by running x alone,
        # inert (x passes under both rewrites), while test y, which calls f, is not ok once that negation is armed: an armed site
        # reported inert. Now the close is the first brace at which the opener through it parses as a complete function
        # (_close_col), left to right, so a brace before it (a group's, one in a string) is inside the test and everything after
        # the close is file scope, no test's text: not a candidate, untouched by every rewrite, and outside the subject as every
        # file-scope negation is (the module docstring). The forms: a helper after the close, one with an `|| return 1` tail, a
        # list joined to the definition, a one-liner's tail, and a close line whose first brace closes an inner group
        lines = ['@test "x" {',
                 '    ! true; }; f() { ! false; }',                # 1: the helper's `!` at column 22 is file scope
                 '@test "y" {',
                 '    f',
                 '}',
                 '@test "z" {',
                 '    ! true; }; g() { ! false || return 1; }',   # 6
                 '@test "w" {',
                 '    ! true; } && { ! false && armed=1; }',      # 8: a list joined to the definition
                 '@test "v" { ! true; } ; ! echo hi',             # 9: a one-liner's tail
                 '@test "u" {',
                 '    { ! true; } }']                             # 11: the first brace closes the group, the second the test
        rewritten = _rewritten(lines)
        extents = bash_test_extents(lines)
        self.assertEqual(extents, [(0, 1), (2, 4), (5, 6), (7, 8), (9, 9), (10, 11)])
        self.assertEqual([_close_col(rewritten, o, c) for o, c in extents], [12, 0, 12, 12, len('_t() { ! true; '), 16])
        self.assertEqual(list(_test_text(lines, 0, 1)), [(0, 11, None), (1, 0, len('    ! true; '))])
        self.assertEqual(list(_test_text(lines, 5, 6)), [(5, 11, None), (6, 0, len('    ! true; '))])
        self.assertEqual(list(_test_text(lines, 7, 8)), [(7, 11, None), (8, 0, len('    ! true; '))])
        self.assertEqual(list(_test_text(lines, 9, 9)), [(9, 11, len('@test "v" { ! true; '))])
        self.assertEqual(list(_test_text(lines, 10, 11)), [(10, 11, None), (11, 0, len('    { ! true; } '))])
        self.assertEqual(candidates(lines, extents), [Candidate(0, 1, 4, False), Candidate(2, 6, 4, False), Candidate(3, 8, 4, False),
                                                       Candidate(4, 9, 12, False), Candidate(5, 11, 6, False)])
        for repl in ("! true", "! false"):   # the file-scope text after each close stands as written under both rewrites
            out = rewritten_shape(lines, extents, repl)
            head = "    %s; " % repl
            self.assertEqual([out[1], out[6], out[8], out[9], out[11]],
                             [head + "}; f() { ! false; }", head + "}; g() { ! false || return 1; }", head + "} && { ! false && armed=1; }",
                              '@test "v" { %s; } ; ! echo hi' % repl, "    { %s; } }" % repl])
            self.assertTrue(_bash_parses(_rewritten(out)))
        # no brace of the line closes the test: None, and _test_text refuses rather than guess (bash_test_extents never hands it one)
        self.assertIsNone(_close_col(['_t() {', '    { true; }'], 0, 1))
        with self.assertRaises(ValueError):
            list(_test_text(['@test "x" {', '    { true; }'], 0, 1))
        # fork PR #871's round 2, fifth commit (the same direction): the close was asked of a line WHOLE first, so where the text
        # after the real `}` opened a construct closing on a LATER line the close line did not parse whole and was skipped, and
        # the extent ran to the construct's close (F09: extents [(0, 3), (4, 6)], candidates (0, 1, 4) and (0, 2, 4), the helper's
        # negation decided inert by running x, while y is not ok once it is flipped) or to the next test's where the construct's
        # was no line the pattern named (F08's `esac`, F35's `)`: extents [(0, 6)], y swallowed). Now the close is the first brace
        # anywhere after the opener, by line then column, at which the opener through it parses, whether or not the rest of its
        # line does; that rest and the lines after it up to the next opener are file scope, no test's text, untouched by every
        # rewrite, and the next opener is read after them. The forms, from the grammar of what file-scope text after a close may
        # open: a function body, a case, a brace group, a subshell, an if, a while (F09, F08, F10, F35 and two more of the round's
        # fourth pass) and a here-document (read right before, by the pending body), each closing lines later; x's extent ends on
        # its close line, one candidate per file, the construct's `! false` unseen
        forms = ['@test "x" {\n    ! false; }; f() {\n    ! false\n}\n@test "y" {\n    f\n}',
                 '@test "x" {\n    ! false; }; case x in\n    x) ! false && armed=1 ;;\nesac\n@test "y" {\n    [ "${armed-}" = 1 ]\n}',
                 '@test "x" {\n    ! false; } && {\n    ! false && armed=1\n}\n@test "y" {\n    [ "${armed-}" = 1 ]\n}',
                 '@test "x" {\n    ! false; }; (\n    ! false\n) || armed=1\n@test "y" {\n    [ -z "${armed-}" ]\n}',
                 '@test "x" {\n    ! false; }; if true; then\n    ! false && armed=1\nfi\n@test "y" {\n    [ "${armed-}" = 1 ]\n}',
                 '@test "x" {\n    ! false; }; n=0; while [ "$n" -lt 1 ]; do\n    n=1\n    ! false && armed=1\ndone\n@test "y" {\n    [ "${armed-}" = 1 ]\n}',
                 '@test "x" {\n    ! false; }; read -r armed <<EOF\n! false\nEOF\n@test "y" {\n    [ "$armed" = \'! false\' ]\n}']
        for text in forms:
            lines = text.split("\n")
            y = lines.index('@test "y" {')
            rewritten = _rewritten(lines)
            extents = bash_test_extents(lines)
            self.assertEqual(extents, [(0, 1), (y, y + 2)], text)
            self.assertEqual([_close_col(rewritten, o, c) for o, c in extents], [len('    ! false; '), 0], text)
            self.assertEqual(list(_test_text(lines, 0, 1)), [(0, 11, None), (1, 0, len('    ! false; '))], text)
            self.assertEqual(candidates(lines, extents), [Candidate(0, 1, 4, False)], text)
            for repl in ("! true", "! false"):   # the file-scope text, on the close line and the lines after it, stands as written
                out = rewritten_shape(lines, extents, repl)
                self.assertEqual(out, ['@test "x" {', '    %s; ' % repl + lines[1][len('    ! false; '):]] + lines[2:], text)
                self.assertTrue(_bash_parses(_rewritten(out)), text)
        # a second test opener on the close line: the `@test` pattern is anchored at the line's start, so after a close it is
        # file-scope text (a command named `@test`, to bash as to bats), and the comment pattern matches anywhere, so the WHOLE
        # line is y's opener to bats-preprocess and to _rewritten, x's close with it: x has no close and the file does not parse,
        # as bats does not load it; the module reads both as bats does
        lines = ['@test "x" {', '    ! true; }; @test "y" { true; }']
        self.assertEqual(bash_test_extents(lines), [(0, 1)])
        self.assertEqual(candidates(lines, bash_test_extents(lines)), [Candidate(0, 1, 4, False)])
        self.assertFalse(_bash_parses(_rewritten(lines)), "the `}` after `true;` stands at file scope")
        lines = ['@test "x" {', '    ! true; }; y() { # @test', '    true', '}']
        self.assertEqual(_rewritten(lines)[1], _TEST_OPENER)
        self.assertEqual(bash_test_extents(lines), [(0, None)])
        with self.assertRaises(ValueError) as cm:
            candidates(lines, bash_test_extents(lines))
        self.assertIn("the file does not parse under this bash -n", str(cm.exception))

    def test_a_brace_glued_to_a_following_character_is_no_close_and_the_test_runs_on_as_bash_reads_it(self):
        # fork PR #871's round 2, sixth commit (the fifth's direction): bash_test_extents asked _closes of EVERY `}`, and _closes
        # cuts the line just past the brace, so a brace glued to a following character, one word to bash and no close (`}x`,
        # `}#`, `}}`), was asked as the prefix through the brace and answered as a close. On `@test "x" {` / `    true; }x
        # 2>/dev/null || true` / `    ! false` / `}` the extents were [(0, 1)], _close_col 10 and the candidates [] (this pin's
        # extents assertion, its third: `Lists differ: [(0, 1)] != [(0, 3)]`; its first, the `}` words of the line, reds `Lists
        # differ: [10] != []` under a _close_words yielding every brace), while bash puts the body as `true; }x 2> /dev/null || true;
        # ! false` with the close on line 4 (`declare -f`) and bats runs the file as written, `ok 1 x` under 1.10.0 and 1.11.1:
        # the negation unseen, the silent direction. The same for `}# not a comment` (bats `not ok 1 x`, `}#: command not found`,
        # status 127), for `}}`, for a brace before a quote, a `$` or a backtick, and for a lone `\` after the brace continuing
        # the line onto a word, through one join or two. Now the braces asked are the ones bash reads as the word `}`
        # (_close_words): the character after the brace is a metacharacter, a blank or the line's end (_METACHARACTERS, the class
        # the `!` reader reads; since the eighth commit both read one function, _word_ends, which excepts a `<` or `>` before
        # `(`), or the next line's first character where a lone `\` ends the line after the brace; the
        # character before it is in the prefix, and bash refuses a glued one itself. After: extents to the file's last line, the
        # candidate on the negation's line, _close_col 0, the negation the one line a rewrite touches (the register's
        # I_close_glued_* and I_close_backslash_newline_word record its read, `not ok` under `! true` and `ok` under `! false`)
        # each with the `}` words of its second line: none where the brace is glued on its right, and for `}}` the second brace,
        # followed by a blank, a word to the boundary rule that the parse refuses (the first brace of `}}` is glued on its right)
        glued = [(['@test "x" {', '    true; }x 2>/dev/null || true', '    ! false', '}'], []),
                 (['@test "x" {', '    true; }# not a comment', '    ! false', '}'], []),
                 (['@test "x" {', '    true; }} 2>/dev/null || true', '    ! false', '}'], [11]),
                 (['@test "x" {', "    true; }'x' 2>/dev/null || true", '    ! false', '}'], []),
                 (['@test "x" {', '    true; }$x 2>/dev/null || true', '    ! false', '}'], []),
                 (['@test "x" {', '    true; }`true` 2>/dev/null || true', '    ! false', '}'], []),
                 (['@test "x" {', '    true; }=1 2>/dev/null || true', '    ! false', '}'], []),
                 (['@test "x" {', '    true; }\\', 'x 2>/dev/null || true', '    ! false', '}'], []),         # a continuation onto a word
                 (['@test "x" {', '    true; }\\', '\\', 'x 2>/dev/null || true', '    ! false', '}'], []),   # through two joins
                 (['@test "x" {', '    true; }\\\\ 2>/dev/null || true', '    ! false', '}'], [])]            # an escaped backslash is the word's
        for lines, words in glued:
            rewritten, last = _rewritten(lines), len(lines) - 1
            self.assertEqual(list(_close_words(rewritten, 1)), words, lines[1])
            self.assertNotIn(True, [_closes(rewritten, 0, 1, col)[0] for col in words], lines[1])   # no brace of the line closes the test
            extents = bash_test_extents(lines)
            self.assertEqual(extents, [(0, last)], lines[1])
            self.assertEqual(_close_col(rewritten, 0, last), 0, lines[1])
            self.assertEqual(candidates(lines, extents), [Candidate(0, last - 1, 4, False)], lines[1])
            self.assertTrue(_bash_parses(_rewritten(lines)), lines[1])
            for repl in ("! true", "! false"):
                out = rewritten_shape(lines, extents, repl)
                self.assertEqual(out, lines[:last - 1] + ["    " + repl, "}"], lines[1])
                self.assertTrue(_bash_parses(_rewritten(out)), lines[1])
        # the word `}`: followed by a blank, a tab, each metacharacter or the line's end, and by a comment after a real close, the
        # brace closes x and y opens after it; after a `(` or a `)` the brace is the word too (bash refuses the parenthesis, not
        # the close) and the rest of the line does not parse, so y does not open there, the file-scope problem BatsSuites names
        for after in (" ; true", "\t; true", ";", "&", "|cat", "<x", ">/dev/null", "", " # a comment after the close"):
            lines = ['@test "x" {', '    ! true; }' + after, '@test "y" {', '    ! false', '}']
            rewritten = _rewritten(lines)
            self.assertEqual(list(_close_words(rewritten, 1)), [len("    ! true; ")], after)
            self.assertEqual(bash_test_extents(lines), [(0, 1), (2, 4)], after)
            self.assertEqual(candidates(lines, bash_test_extents(lines)), [Candidate(0, 1, 4, False), Candidate(1, 3, 4, False)], after)
        for after in ("(true)", ")"):
            lines = ['@test "x" {', '    ! true; }' + after, '@test "y" {', '    ! false', '}']
            rewritten = _rewritten(lines)
            self.assertEqual(list(_close_words(rewritten, 1)), [len("    ! true; ")], after)
            self.assertTrue(_closes(rewritten, 0, 1, len("    ! true; "))[0], after)
            self.assertEqual(bash_test_extents(lines), [(0, 1)], after)
            self.assertEqual(unopened_test_lines(lines, bash_test_extents(lines)), [2], after)
        # a lone `\` after the brace at the line's end: the character read is the next line's first, so an empty next line, no
        # next line, or one beginning with a blank or a `;` leaves the brace the word (bash -n: exit 0), and one beginning with a
        # word character, a `}` or the rewritten opener glues (`unexpected end of file`), through a second lone `\` too
        for rest, words in ((["    true; }\\"], [10]), (["    true; }\\", ""], [10]), (["    true; }\\", " ; true"], [10]),
                            (["    true; }\\", "; true"], [10]), (["    true; }\\", "x"], []), (["    true; }\\", "}"], []),
                            (["    true; }\\", "\\", "x"], []), (["    true; }\\", "_t() {"], []), (["    true; }\\\\", ""], [])):
            self.assertEqual(list(_close_words(["_t() {"] + rest, 1)), words, rest)
        lines = ['@test "x" {', '    true; }\\', '', '@test "y" {', '    ! false', '}']
        self.assertEqual(bash_test_extents(lines), [(0, 1), (3, 5)])
        self.assertEqual(candidates(lines, bash_test_extents(lines)), [Candidate(1, 4, 4, False)])
        lines = ['@test "x" {', '    true; }\\', '}']   # joined, `}}`: one word, the test unclosed, and bash does not parse the file
        self.assertEqual(list(_close_words(_rewritten(lines), 2)), [0])
        self.assertEqual(bash_test_extents(lines), [(0, None)])
        self.assertFalse(_bash_parses(_rewritten(lines)))
        # the character before the brace is bash's call through the prefix: a parameter expansion's brace followed by a blank is
        # asked (a `}` word to the boundary rule) and refused, the function still open, and the line's last brace closes; the
        # second brace of `}}` and the brace of `$(true)}` are refused the same way; `(true)}` is the word after a metacharacter
        line = '    echo ${x-} ; true; }'
        rewritten = ['_t() {', line]
        self.assertEqual(list(_close_words(rewritten, 1)), [line.index("}"), line.rindex("}")])
        self.assertEqual([_closes(rewritten, 0, 1, col)[0] for col in _close_words(rewritten, 1)], [False, True])
        rc, err = _bash_n(['_t() {', line[:line.index("}") + 1]])
        self.assertEqual((rc, "unexpected end of file" in err), (2, True), err)
        lines = ['@test "x" {', line, '@test "y" {', '    ! false', '}']
        self.assertEqual(bash_test_extents(lines), [(0, 1), (2, 4)])
        self.assertEqual(_close_col(_rewritten(lines), 0, 1), line.rindex("}"))
        for line, col in (("    { true; }}", 13), ("    echo $(true)}", 16)):
            self.assertEqual(list(_close_words(["_t() {", line], 1)), [col], line)
            self.assertFalse(_closes(["_t() {", line], 0, 1, col)[0], line)
        lines = ['@test "x" {', '    true; }}', '    ! false', '}']   # `}}` a word bash runs, the close on line 4
        self.assertEqual(bash_test_extents(lines), [(0, 3)])
        self.assertEqual(list(_close_words(["_t() {", "    (true)}"], 1)), [10])
        self.assertEqual(bash_test_extents(['@test "x" {', '    (true)}']), [(0, 1)])
        # one boundary: the `!` word and the `}` word read _word_ends (since the eighth commit; one class, two spellings, before
        # it), and the tree's `[[ "${x}" = y ]]` brace, before a quote, is asked of nothing; the `!` keeps the backtick as its
        # one allowance on the safe side (`` !`true` `` is one word to bash, a candidate here, reported by bats), where the `}`
        # before a backtick is glued and no close
        for ch in _METACHARACTERS:
            self.assertTrue(_bang_at(["!" + ch], 0, 0), repr(ch))
            self.assertEqual(list(_close_words(["}" + ch], 0)), [0], repr(ch))
        for ch in "x}#'\"$=":
            self.assertFalse(_bang_at(["!" + ch], 0, 0), repr(ch))
            self.assertNotIn(0, list(_close_words(["}" + ch], 0)), repr(ch))   # the first brace is glued (`}}`'s second is a word, at 1)
        self.assertEqual(list(_close_words(["}\\x"], 0)), [])   # a backslash before a character glues; a lone one at the line's end is the continuation above
        self.assertTrue(_bang_at(["!`"], 0, 0))
        self.assertEqual(list(_close_words(["}`"], 0)), [])
        self.assertEqual(list(_close_words(['    [[ "${x}" = y ]]'], 0)), [])

    def test_a_brace_glued_to_a_following_character_before_the_real_close_on_the_close_line_is_skipped_for_the_column_too(self):
        # fork PR #871's round 2, seventh commit (the sixth's walker verifier): _close_col asks _closes of the close line's `}`
        # words as bash_test_extents does, and no test held it to that: a mutant asking every `}` of the close line for the
        # column (`for col in (mm.start() for mm in re.finditer(r"\}", rewritten[c]))` in _close_col) ran this module green with
        # bats hidden, `29 passed, 11 skipped`, since the pin above reads the column only on close lines that are `}` alone and
        # the register's recall gate reads the same _test_text. Not equivalent: on `@test "x" {` /
        # `    true; }x 2>/dev/null || true; ! true; }` the module gives extents [(0, 1)], _close_col 42, the close line's text
        # (1, 0, 42) and the one candidate Candidate(0, 1, 34, False); the mutant _close_col 10 (the glued brace: the prefix cut
        # just past it, `_t() {` then `    true; }`, parses, exit 0, so the first brace at which the prefix parses is not the
        # close), the text (1, 0, 10) and candidates []: the negation before the real close unseen, while bash reads the body
        # through the glued word (`declare -f`: `true; }x 2> /dev/null || true; ! true`) and bats fails the test as written,
        # `not ok 1 x`, under 1.10.0 and 1.11.1. The same for `    true; }# c; ! true; }` (24 and Candidate(0, 1, 16, False); the
        # mutant 10 and []) and for a one-liner, `@test "x" { true; }x 2>/dev/null || true; ! true; }` (_close_col 45 on the
        # rewritten line, the text (0, 11, 50), Candidate(0, 0, 42, False); the mutant 13, (0, 11, 18) and []). The silent
        # direction; the tree holds no such line (the differential against the sixth commit: 0 candidate differences over the
        # corpus's 858 tests). Here each glue form of the pin above stands before the real close on the close line, with y
        # opening after it, and on a one-liner: the column is the line's last brace, the text runs to it, the candidate is the
        # negation between the glued word and the close, and a rewrite touches that negation alone; the register's
        # I_close_glued_before_close and I_one_liner_glued_before_close record the read, ('not ok', 'ok') under both bats, so the
        # agreement gate reds the mutant where the recall gate cannot (with no candidate both files are the shape as written, and
        # bats says (not ok, not ok))
        for glue in ("x", "#", "}", "'x'", "$x", "`true`", "=1", "\\x", '"x"'):
            line = "    true; }%s 2>/dev/null || true; ! true; }" % glue
            lines = ['@test "x" {', line, '@test "y" {', '    ! false', '}']
            rewritten, close, bang = _rewritten(lines), line.rindex("}"), line.index("!")
            self.assertEqual(list(_close_words(rewritten, 1)), ([11] if glue == "}" else []) + [close], line)   # `}}`: its second brace, before a blank, is a word the parse refuses
            self.assertTrue(_closes(rewritten, 0, 1, 10)[0], line)   # the prefix through the glued brace parses, and the brace is no close
            extents = bash_test_extents(lines)
            self.assertEqual(extents, [(0, 1), (2, 4)], line)
            self.assertEqual(_close_col(rewritten, 0, 1), close, line)
            self.assertEqual(list(_test_text(lines, 0, 1, rewritten)), [(0, 11, None), (1, 0, close)], line)
            self.assertEqual(candidates(lines, extents), [Candidate(0, 1, bang, False), Candidate(1, 3, 4, False)], line)
            for repl in ("! true", "! false"):
                out = rewritten_shape(lines, extents, repl)
                self.assertEqual(out, [lines[0], line[:bang] + repl + line[bang + len("! true"):], lines[2], "    " + repl, "}"], line)
                self.assertTrue(_bash_parses(_rewritten(out)), line)
        lines = ['@test "x" {', '    true; }x 2>/dev/null || true; ! true; }']
        self.assertEqual((_close_col(_rewritten(lines), 0, 1), candidates(lines, [(0, 1)])), (42, [Candidate(0, 1, 34, False)]))
        lines = ['@test "x" {', '    true; }# c; ! true; }']   # the glued word fails (`}#: command not found`); the column and the candidate read the same
        self.assertEqual((_close_col(_rewritten(lines), 0, 1), candidates(lines, [(0, 1)])), (24, [Candidate(0, 1, 16, False)]))
        for line, close, bang in (('@test "x" { true; }x 2>/dev/null || true; ! true; }', 50, 42), ('@test "x" { true; }# c; ! true; }', 32, 24)):
            rewritten = _rewritten([line])
            self.assertTrue(_closes(rewritten, 0, 0, len(_TEST_OPENER) + len(" true; }") - 1)[0], line)   # the glued brace, column 13 of the rewritten line
            self.assertEqual(bash_test_extents([line]), [(0, 0)], line)
            self.assertEqual(_close_col(rewritten, 0, 0), close - len('@test "x" {') + len(_TEST_OPENER), line)   # 45 and 27: the name dropped
            self.assertEqual(list(_test_text([line], 0, 0, rewritten)), [(0, 11, close)], line)
            self.assertEqual(candidates([line], [(0, 0)]), [Candidate(0, 0, bang, False)], line)

    def test_a_brace_glued_to_a_process_substitution_is_no_close_and_one_separated_from_it_by_a_blank_is_the_close(self):
        # fork PR #871's round 2, eighth commit (F1 of the seventh's verifiers: the sixth commit's class again, the silent
        # direction): _close_words read _METACHARACTERS as the whole rule, and `<` and `>` are in it, so a brace glued to a process
        # substitution, `}<(true)`, `}>(true)`, one word to bash (read_token_word takes `<(` and `>(` as the word's before its
        # word-break check; bash -n: `f() { true; }<(true)` is `unexpected end of file`, exit 2, and exit 0 with a later `}`
        # line; `declare -f` puts `}<(true) 2> /dev/null || true;` and `! true` inside the body), was the word `}` here and, the
        # prefix through it parsing, the close. On `@test "x" {` / `    true; }<(true) 2>/dev/null || true` / `    ! true` / `}`
        # / `@test "y" {` / `    true` / `}` the module at the seventh commit gave _close_words(line 1) [10], extents [(0, 1),
        # (4, 6)] and candidates [] (this pin's first assertion: `Lists differ: [10] != []`): both rewrites the file as written,
        # nothing run, nothing reported, while bats runs the negation as x's last command, `not ok 1 x` then `ok 2 y` under
        # 1.10.0 and 1.11.1. Population in tests/*.bats: 0. Now the boundary is one function, _word_ends, read for the `}` and
        # the `!` alike, and a `<` or `>` immediately before `(` continues the word. Both directions: glued, no word, the extent
        # to line 4 and the negation the one candidate (the register's I_close_glued_procsub_*); separated by a blank
        # (`}< (true)`, `}> (true)`: bash -n `syntax error near unexpected token `('`, exit 2, the brace read as the close and
        # the parenthesis refused; `} <(true)`: refused at the `<(true)` word, a word after a function's close), the brace is
        # the word and the prefix through it parses, y unopened since the rest of the line does not parse; a redirection from a
        # process substitution after the close, `} < <(true)`, `} > >(cat)` (exit 0), the brace the word, y opening after it
        # (I_close_then_procsub_redirect); and each other metacharacter before a `(` ends the word (`}|(true)`, `}&(true)`,
        # `};(true)`: exit 0, the brace the close), so the exception is the two characters read_token_word names and no wider
        for glue in ("<(true)", ">(true)"):
            line = "    true; }%s 2>/dev/null || true" % glue
            lines = ['@test "x" {', line, '    ! true', '}', '@test "y" {', '    true', '}']
            rewritten = _rewritten(lines)
            self.assertEqual(list(_close_words(rewritten, 1)), [], line)
            rc, err = _bash_n(["_t() {", "    true; }" + glue])
            self.assertEqual((rc, "unexpected end of file" in err), (2, True), err)
            self.assertEqual(_bash_n(["_t() {", "    true; }" + glue, "}"])[0], 0, glue)
            extents = bash_test_extents(lines)
            self.assertEqual(extents, [(0, 3), (4, 6)], line)
            self.assertEqual(_close_col(rewritten, 0, 3), 0, line)
            self.assertEqual(candidates(lines, extents), [Candidate(0, 2, 4, False)], line)
            for repl in ("! true", "! false"):
                out = rewritten_shape(lines, extents, repl)
                self.assertEqual(out, lines[:2] + ["    " + repl] + lines[3:], line)
                self.assertTrue(_bash_parses(_rewritten(out)), line)
        for after, refused in (("< (true)", "`('"), ("> (true)", "`('"), (" <(true)", "`<(true)'")):
            lines = ['@test "x" {', '    ! true; }' + after, '@test "y" {', '    ! false', '}']
            rewritten = _rewritten(lines)
            self.assertEqual(list(_close_words(rewritten, 1)), [len("    ! true; ")], after)
            self.assertTrue(_closes(rewritten, 0, 1, len("    ! true; "))[0], after)
            rc, err = _bash_n(rewritten[:2])
            self.assertEqual((rc, "syntax error near unexpected token " + refused in err), (2, True), err)
            self.assertEqual(bash_test_extents(lines), [(0, 1)], after)
            self.assertEqual(unopened_test_lines(lines, bash_test_extents(lines)), [2], after)
        for after in (" < <(true)", " > >(cat)", "|(true)", "&(true)", ";(true)"):
            lines = ['@test "x" {', '    ! true; }' + after, '@test "y" {', '    ! false', '}']
            rewritten = _rewritten(lines)
            self.assertEqual(list(_close_words(rewritten, 1)), [len("    ! true; ")], after)
            self.assertEqual(_bash_n(rewritten[:2])[0], 0, after)
            self.assertEqual(bash_test_extents(lines), [(0, 1), (2, 4)], after)
            self.assertEqual(candidates(lines, bash_test_extents(lines)), [Candidate(0, 1, 4, False), Candidate(1, 3, 4, False)], after)
        # through a continuation: a lone `\` after the brace, then `<(true)` first on the next line, glues (bash -n: exit 2, and
        # exit 0 with a later `}` line); then ` (true)`, a blank first, leaves the brace the word (refused at the parenthesis)
        lines = ['@test "x" {', '    true; }\\', '<(true) 2>/dev/null || true', '    ! true', '}']
        self.assertEqual(list(_close_words(_rewritten(lines), 1)), [])
        self.assertEqual(_bash_n(["_t() {", "    true; }\\", "<(true)"])[0], 2)
        self.assertEqual(_bash_n(["_t() {", "    true; }\\", "<(true)", "}"])[0], 0)
        self.assertEqual(bash_test_extents(lines), [(0, 4)])
        self.assertEqual(candidates(lines, bash_test_extents(lines)), [Candidate(0, 3, 4, False)])
        self.assertEqual(list(_close_words(["_t() {", "    true; }\\", " (true)"], 1)), [10])
        rc, err = _bash_n(["_t() {", "    true; }\\", " (true)"])
        self.assertEqual((rc, "syntax error near unexpected token `('" in err), (2, True), err)
        # one rule for both words: each metacharacter ends the word, a `<` or `>` before `(` does not, and the backtick beside
        # the `!` is the one allowance on top of it
        for ch in _METACHARACTERS:
            self.assertTrue(_word_ends(["}" + ch], 0, 1), repr(ch))
            self.assertEqual(_word_ends(["}" + ch + "("], 0, 1), ch not in "<>", repr(ch))
            self.assertEqual(_bang_at(["!" + ch + "("], 0, 0), ch not in "<>", repr(ch))
            self.assertEqual(list(_close_words(["}" + ch + "("], 0)), [] if ch in "<>" else [0], repr(ch))
        self.assertFalse(_word_ends(["}`("], 0, 1))
        self.assertTrue(_bang_at(["!`("], 0, 0))

    def test_a_test_line_inside_a_construct_the_text_after_a_close_opened_is_not_opened_and_the_problem_names_that_cause(self):
        # fork PR #871's round 2, sixth commit (docs): since the fifth commit the text after a close is file scope through the
        # next opener, so an opener inside a construct that text opened (`    ! false; }; if true; then`, the opener, the test,
        # `fi`) is not opened here, a fourth cause beside a heredoc, a quoted string and another test, reported through the same
        # problems list while bats runs y; the problem line named three causes. It names four now, with the example and the remedy
        lines = ['@test "x" {', '    ! false; }; if true; then', '@test "y" {', '    ! false', '}', 'fi']
        extents = bash_test_extents(lines)
        self.assertEqual(extents, [(0, 1)])
        self.assertEqual(unopened_test_lines(lines, extents), [2])
        self.assertEqual(candidates(lines, extents), [Candidate(0, 1, 4, False)])
        problem = _unopened_problem("tests/one.bats", 2)
        self.assertTrue(problem.startswith("tests/one.bats:3: a line bats-preprocess rewrites into a test that bash does not open as one"), problem)
        for cause in ("inside a heredoc", "a quoted string", "another test", "a construct the file-scope text after a test's close opened and a later line closes"):
            self.assertIn(cause, problem)
        self.assertIn("`    ! true; }; if true; then` before the opener and `fi` after the test", problem)
        self.assertIn("is closed before the next test", problem)
        self.assertTrue(problem.endswith(FIXTURE_LINE_REMEDY))

    def test_a_close_sharing_a_line_with_a_here_document_introducer_closes_the_test_and_the_body_is_the_pipelines(self):
        # fork PR #871's round 2, second commit (the walker verifier): `@test "x" { ! cat <<EOF; }` with its body and terminator after the brace,
        # and `    ! cat > /dev/null <<EOF; }` inside a multi-line test, are tests bats runs, and the close line's pending body
        # left them with no close (the opener through the brace does not parse whole), so candidates raised; where a later `}`
        # closed a following test, the first test swallowed the file instead. The body is read on past the close now (_closes),
        # the close stays the brace's line, the next opener is read after the body, the `!` before the introducer is a candidate,
        # and its extent blanks the body and terminator; a `}` inside another here-document's body still closes nothing
        lines = ['@test "x" { ! cat > /dev/null <<EOF; }', 'false', 'EOF', '@test "y" {', '    true', '    ! cat > /dev/null <<EOF; }', 'false', 'EOF',
                 '@test "z" {', '    cat <<EOF', '}', 'EOF', '    ! true', '}']
        extents = bash_test_extents(lines)
        self.assertEqual(extents, [(0, 0), (3, 5), (8, 13)])
        found = candidates(lines, extents)
        self.assertEqual(found, [Candidate(0, 0, 12, False), Candidate(1, 5, 4, False), Candidate(2, 12, 4, False)])
        self.assertEqual(negated_pipeline(lines, found[0]), Extent(0, len('@test "x" { ! cat > /dev/null <<EOF'), (1, 2)))
        self.assertEqual(negated_pipeline(lines, found[1]), Extent(5, len('    ! cat > /dev/null <<EOF'), (6, 7)))
        self.assertEqual(rewritten_shape(lines, extents, "! true"),
                         ['@test "x" { ! true; }', '', '', '@test "y" {', '    true', '    ! true; }', '', '', '@test "z" {', '    cat <<EOF', '}', 'EOF',
                          '    ! true', '}'])
        self.assertTrue(_bash_parses(_rewritten(rewritten_shape(lines, extents, "! false"))))
        self.assertEqual(bash_test_extents(lines[:2]), [(0, None)], "a body running off the text closes nothing")

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

    def setUp(self):
        skip_unless_bash_serves(self)

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

    def test_a_negation_glued_to_a_process_substitution_is_one_word_and_separated_from_it_by_a_blank_a_negation(self):
        # fork PR #871's round 2, eighth commit (F1 of the seventh's verifiers, the `!` side of the same rule, the safe side): the
        # word rule was a regex over _METACHARACTERS, so `!<(true)` and `!>(true)`, one word to bash (read_token_word takes `<(`
        # and `>(` as the word's; bash -n: `f() { !<(true); }` exit 0; `declare -f` keeps `!<(true) 2> /dev/null || true`, a
        # command named `!/dev/fd/N`, found nowhere), were `!` words here and candidates bats reported, never a miss: at the
        # seventh commit `candidates` gave [Candidate(0, 1, 4, False)] for the glued line (this pin's first assertion). Now
        # _bang_at reads _word_ends, the rule _close_words reads for the `}`: glued, no word and no candidate (the register's
        # G_procsub_glued_*, their `!` declared text, so a reader taking it reds the declaration as stale); separated by a blank,
        # `! <(true)`, the negation of that command (bash -n `f() { ! <(true); }`: exit 0; `!< (true)`: `syntax error near
        # unexpected token `('`, exit 2, the `!` a word and the parenthesis refused), a candidate whose rewrite touches its line
        # alone (G_procsub_separated_*)
        for glued in ("!<(true) 2>/dev/null || true", "!>(true) 2>/dev/null || true"):
            lines = ['@test "x" {', "    " + glued, "    true", "}"]
            extents = bash_test_extents(lines)
            self.assertEqual(candidates(lines, extents), [], glued)
            self.assertFalse(_bang_at(lines, 1, 4), glued)
            self.assertEqual(_bash_n(["f() { %s; }" % glued])[0], 0, glued)
            self.assertEqual(list(_bangs(_ANY_BANG, lines, 0, 3)), [(1, 4)], glued)   # the register's expected set holds it: the shape declares it
        for text in ("! <(true) 2>/dev/null", "! >(true) 2>/dev/null"):
            lines = ['@test "x" {', "    true", "    " + text, "}"]
            extents = bash_test_extents(lines)
            self.assertEqual(candidates(lines, extents), [Candidate(0, 2, 4, False)], text)
            self.assertEqual(_bash_n(["f() { %s; }" % text])[0], 0, text)
            for repl in ("! true", "! false"):
                self.assertEqual(rewritten_shape(lines, extents, repl), lines[:2] + ["    " + repl, "}"], text)
        rc, err = _bash_n(["f() { !< (true); }"])
        self.assertEqual((rc, "syntax error near unexpected token `('" in err), (2, True), err)
        self.assertTrue(_bang_at(["!< (true)"], 0, 0))

    def test_a_negation_continued_by_a_lone_backslash_is_the_word_the_next_line_makes_it_and_a_run_follows_the_join(self):
        # fork PR #871's round 2, eighth commit (F2 of the seventh's verifiers, the shared boundary's other clause, the silent
        # direction): the word rule was a regex with no line-continuation reading, so `    !\` then ` true`, which bash joins to
        # `! true` (`declare -f`: `! true`; `f() { !\` then ` true; }` returns 1), matched nothing, the test had no candidate,
        # nothing ran and nothing was reported (at the seventh commit `candidates` gave [] here, this pin's first assertion),
        # while bats reads the negation, `not ok 1 x` under 1.10.0 and 1.11.1 as the test's last command. The sibling forms
        # agreed with bash already: `    ! \` then `true` a candidate (0, 1, 4), read, and `    !\` then `true`, `!true` to bash,
        # one word, no candidate. Now _bang_at reads _word_ends, whose continuation clause _close_words read for the `}` since
        # the sixth commit: a lone `\` at the line's end is removed with the newline and the character read is the next line's
        # first, through a second lone `\` line. The character BEFORE a `!` is not read across a join: `!\` then `! true` is
        # `!! true` to bash, one word, and the second `!`, at its line's start, is a word here, the safe side (its rewrite fails
        # under both, reported). And the run of `!` words the rewrite keeps whole follows the join (_bang_run): `    ! \` then
        # `    ! true` is `! ! true` to bash (returns 0; with `! false`, 1), two words, where a run ending at the line's end
        # wrote `! true` for it and dropped a negation (the register's G_double_negation_continued_*)
        lines = ['@test "x" {', "    true", "    !\\", " true", "}"]
        extents = bash_test_extents(lines)
        self.assertEqual(candidates(lines, extents), [Candidate(0, 2, 4, False)])
        self.assertTrue(_bang_at(lines, 2, 4))
        self.assertEqual(negated_pipeline(lines, Candidate(0, 2, 4, False)), Extent(3, 5, (3,)))
        for repl in ("! true", "! false"):
            self.assertEqual(rewritten_shape(lines, extents, repl), ['@test "x" {', "    true", "    " + repl, "", "}"])
        for second, cands in (("true", []), ("<(true)", []), ("! true", [Candidate(0, 2, 0, False)]), (" true", [Candidate(0, 1, 4, False)]),
                              ("\ttrue", [Candidate(0, 1, 4, False)]), (";true", [Candidate(0, 1, 4, False)]), ("", [Candidate(0, 1, 4, False)])):
            lines = ['@test "x" {', "    !\\", second, "    true", "}"]
            self.assertEqual(candidates(lines, bash_test_extents(lines)), cands, repr(second))
        for rest, k in ((["    !\\", " true"], 1), (["    ! \\", "true"], 1), (["    ! \\", "    ! true"], 2), (["    ! \\", "\\", "! true"], 2),
                        (["    ! ! true"], 2), (["    ! \\ ", "! true"], 1), (["    ! \\", "! \\", "! true"], 3), (["    !\\", "! true"], 0)):
            self.assertEqual(_bang_run(rest, 0, 4), k, rest)
        lines = ['@test "x" {', "    true", "    ! \\", "    ! true", "}"]
        extents = bash_test_extents(lines)
        self.assertEqual(candidates(lines, extents), [Candidate(0, 2, 4, False), Candidate(0, 3, 4, False)])
        for repl in ("! true", "! false"):
            self.assertEqual(rewritten_shape(lines, extents, repl), ['@test "x" {', "    true", "    ! " + repl, "", "}"])
        self.assertEqual(rewrite(lines, Candidate(0, 3, 4, False), "! false"), ['@test "x" {', "    true", "    ! \\", "    ! false", "}"])

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

    def test_the_extent_covers_a_here_document_the_pipeline_introduces_a_continued_pipeline_and_an_ansi_c_quote(self):
        # the extent walker's round-2 forms, on the text: the pipeline's own here-document lines are blank in the rewrite and
        # another command's are kept (negated_pipeline's Extent.blank), a comment after `|` or `|&` continues the pipeline, a group
        # opened on the line runs on to its close, and `$'it\\'s'` is one word
        lines = ['@test "x" {',
                 '    ! cat > /dev/null <<EOF; true',       # 1: the tail follows the introducer; the body and terminator are the pipeline's
                 '    body',
                 'EOF',
                 '    cat > /dev/null <<A; ! cat <<B |',    # 4: A is another command\'s and comes first; B\'s and the next stage are the pipeline\'s
                 '    kept',
                 'A',
                 '    body',
                 'B',
                 '        cat > /dev/null',
                 '    ! true | # note',                     # 10: bash continues the pipeline past the comment
                 '        cat',
                 '    ! true |& # note',                    # 12
                 '        cat',
                 '    ! {',                                 # 14: a group opened on the line
                 '        true',
                 '    }',
                 "    ! echo $'it\\'s' > /dev/null",          # 17: ANSI-C quoting, the escaped quote inside
                 '    ! grep -q x <<< "$s"',                # 18: a here-string introduces no body
                 '    true',
                 '}']
        extents = bash_test_extents(lines)
        found = {c.line: c for c in candidates(lines, extents)}
        self.assertEqual(sorted(found), [1, 4, 10, 12, 14, 17, 18])
        self.assertEqual(negated_pipeline(lines, found[1]), Extent(1, len('    ! cat > /dev/null <<EOF'), (2, 3)))
        self.assertEqual(negated_pipeline(lines, found[4]), Extent(9, len('        cat > /dev/null'), (7, 8, 9)))
        self.assertEqual(negated_pipeline(lines, found[10]), Extent(11, len('        cat'), (11,)))
        self.assertEqual(negated_pipeline(lines, found[12]), Extent(13, len('        cat'), (13,)))
        self.assertEqual(negated_pipeline(lines, found[14]), Extent(16, len('    }'), (15, 16)))
        self.assertEqual(negated_pipeline(lines, found[17]), Extent(17, len("    ! echo $'it\\'s' > /dev/null"), ()))
        self.assertEqual(negated_pipeline(lines, found[18]), Extent(18, len('    ! grep -q x <<< "$s"'), ()))
        self.assertEqual(rewritten_shape(lines, extents, "! true"),
                         ['@test "x" {', '    ! true; true', '', '', '    cat > /dev/null <<A; ! true', '    kept', 'A', '', '', '',
                          '    ! true', '', '    ! true', '', '    ! true', '', '', '    ! true', '    ! true', '    true', '}'])
        self.assertTrue(_bash_parses(_rewritten(rewritten_shape(lines, extents, "! false"))))

    def test_an_operator_inside_a_construct_bash_reads_whole_does_not_end_the_pipeline_and_a_glued_comment_is_bashs_call(self):
        # fork PR #871's round 2, second commit (the walker verifier): the walker ended the extent at a `;`, `&&`, `||` or `)` its own tracking
        # found without asking bash, so an operator inside a `[[ ]]`, a `${ }`, a backtick substitution or a `$( )` whose nested
        # quotes the tracker paired otherwise split the construct (`! [[ a == a && b == b ]]` mid became `! true && b == b ]]`, and
        # the remainder parsing on its own, an inert site read as read), and a negated compound ended at its first operator (the
        # rewritten file did not parse: undecided). Every proposed stop is bash's call now (_pipeline_complete), and so is whether
        # a `#` glued to a metacharacter begins a comment (_begins_comment: after `|` and after a subshell's `)` it does, after a
        # `$( )` it is part of the word); since the third commit the walker tracks no quote and no parenthesis at all, and every operator
        # character is proposed. The forms, one each: the two `[[ ]]` operators, a `&&` and a `;` inside nested quotes,
        # inside a `${ }` and inside backticks, a comment glued to `|`, to a subshell's `)` and to `(`, a word glued to `$( )`, a
        # negated group, `if`, `case`, `for`, `while`, `until`, arithmetic and subshell compound, and the ANSI-C quote before a
        # list operator (fresh-2's arm, which G_ansi_quote_* did not arm: with the arm removed the second commit tracker read `b' || false`
        # as a string and the extent ran to the line's end, where bash reads the whole line as complete; since the third commit the `;` and
        # the `||` inside and after an ANSI-C quote are proposed like any other and bash refuses the one inside)
        lines = ['@test "x" {',
                 '    ! [[ a == a && b == b ]]',                         # 1
                 '    ! [[ a == a || b == b ]]',                         # 2
                 '    ! echo "$(printf "%s && %s" a b)" > /dev/null',    # 3
                 '    ! echo "$(echo "a;b")" > /dev/null',               # 4
                 '    ! echo ${x:-a&&b} > /dev/null',                    # 5
                 '    ! echo ${x:-a;b} > /dev/null',                     # 6
                 '    ! echo `echo a; echo b` > /dev/null',              # 7
                 '    ! true |# a && false',                             # 8: a comment glued to `|`; the pipeline continues past it
                 '        cat',
                 '    ! (true)# a && false',                             # 10: a comment glued to a subshell's `)`
                 '    ! echo $(true)#b || false',                        # 11: no comment: `$(true)#b` is one word
                 '    ! (# a && false',                                  # 12: a comment glued to `(`
                 '        true)',
                 '    ! { false; true; }',                               # 14: a negated group, its `;` operators inside
                 '    ! if true; then',                                  # 15: a negated compound over three lines
                 '        true',
                 '    fi',
                 '    ! case a in a) true;; esac',                       # 18: the `)` and `;;` inside
                 '    ! for i in 1; do true; done',                      # 19
                 '    ! while false; do true; done',                     # 20
                 '    ! until true; do false; done',                     # 21
                 '    ! (( 1 && 1 ))',                                   # 22
                 '    ! (true; true)',                                   # 23
                 "    ! echo $'a\\'b' || false",                          # 24: the ANSI-C quote, then a list operator
                 '}']
        extents = bash_test_extents(lines)
        found = {c.line: c for c in candidates(lines, extents)}
        self.assertEqual(sorted(found), [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 14, 15, 18, 19, 20, 21, 22, 23, 24])
        whole = {i: Extent(i, len(lines[i]), ()) for i in (1, 2, 3, 4, 5, 6, 7, 14, 18, 19, 20, 21, 22, 23)}
        whole.update({8: Extent(9, len('        cat'), (9,)), 10: Extent(10, len('    ! (true)'), ()), 11: Extent(11, len('    ! echo $(true)#b'), ()),
                      12: Extent(13, len('        true)'), (13,)), 15: Extent(17, len('    fi'), (16, 17)), 24: Extent(24, len("    ! echo $'a\\'b'"), ())})
        for i, cand in sorted(found.items()):
            self.assertEqual(negated_pipeline(lines, cand), whole[i], lines[i])
        rewritten = rewritten_shape(lines, extents, "! true")
        self.assertEqual(rewritten, ['@test "x" {'] + ['    ! true'] * 7 + ['    ! true', '', '    ! true # a && false', '    ! true || false', '    ! true', '',
                                                        '    ! true', '    ! true', '', '', '    ! true', '    ! true', '    ! true', '    ! true',
                                                        '    ! true', '    ! true', '    ! true || false', '}'])
        self.assertTrue(_bash_parses(_rewritten(rewritten)))
        self.assertTrue(_bash_parses(_rewritten(rewritten_shape(lines, extents, "! false"))))
        # bash's comment rule, asked of the text: a `#` after a blank or a metacharacter begins a comment unless it is inside a word
        self.assertTrue(_begins_comment([], "! true "))
        self.assertTrue(_begins_comment([], "! true |"))
        self.assertTrue(_begins_comment([], "! (true)"))
        self.assertTrue(_begins_comment(["! true |"], ""))
        self.assertFalse(_begins_comment([], "! echo $(true)"))
        self.assertFalse(_begins_comment([], "! echo ${x:-a "))
        self.assertFalse(_begins_comment([], '! echo "$(echo "a '))

    def test_a_quote_inside_a_substitution_hides_no_operator_and_an_escaped_blank_at_a_lines_end_is_no_continuation(self):
        # fork PR #871's round 2, third commit (the second commit's two verifiers). The walker tracked quotes and parentheses to find the operators it
        # proposed, and a `$( )` inside double quotes opens a quoting context of its own, so a quote inside one desynchronised the
        # tracker: the rest of the line read as a string, no operator in it was proposed, and the extent ran to the line's end,
        # where bash reads the whole line as complete; the rewrite dropped the tail that discarded the status (`; true`,
        # `|| true`) and an inert site was read as read, the silent direction (the runs verifier: `! grep -q x "$(echo "it's")" ;
        # true` last, verdict read, runs `['not ok @2', 'ok']`, where the tail-keeping rewrites run ok, ok). And the walker
        # stripped a line's trailing blanks before asking bash, so `! true \ `, an escaped blank and a complete command to bash,
        # was asked as `! true \`, a continuation, and the line after it became the pipeline's, blank in the rewrite: mid-test the
        # command after it deleted and the negation made last (inert read as read), last the close blanked and the file unparsed
        # (the walker verifier). Now every operator character is proposed, whatever surrounds it, and bash refuses one inside a
        # quote or a substitution (_pipeline_complete); and an escaped blank stays in the text bash is asked about (_text_end).
        # The forms: a `'` inside nested double quotes inside a `"$( )"` and a `"` inside single quotes inside one, before
        # `; true`, and the first before `|| true`; an escaped blank, an escaped tab and an escaped blank ending an argument at the
        # line's end; an escaped blank before a `;`; an escaped backslash before a trailing blank (an even run: the blank is no
        # character of the word and is excluded); and a trailing `\` alone, which still continues
        lines = ['@test "x" {',
                 '    ! echo "$(echo "it\'s")" > /dev/null; true',       # 1
                 '    ! echo "$(echo \'a"b\')" > /dev/null; true',       # 2
                 '    ! echo "$(echo "don\'t")" > /dev/null || true',    # 3
                 '    ! true \\ ',                                       # 4: an escaped blank at the line's end
                 '    ! true \\\t',                                      # 5: an escaped tab
                 '    ! true a\\ ',                                      # 6: the escaped blank ends an argument
                 '    ! true \\ ; true',                                 # 7: an escaped blank before an operator
                 '    ! true \\\\ ',                                     # 8: an escaped backslash, then a trailing blank
                 '    ! true \\',                                        # 9: a continuation
                 '        x',
                 '    true',
                 '}']
        extents = bash_test_extents(lines)
        found = {c.line: c for c in candidates(lines, extents)}
        self.assertEqual(sorted(found), [1, 2, 3, 4, 5, 6, 7, 8, 9])
        ends = {1: Extent(1, len('    ! echo "$(echo "it\'s")" > /dev/null'), ()), 2: Extent(2, len('    ! echo "$(echo \'a"b\')" > /dev/null'), ()),
                3: Extent(3, len('    ! echo "$(echo "don\'t")" > /dev/null'), ()), 4: Extent(4, len('    ! true \\ '), ()), 5: Extent(5, len('    ! true \\\t'), ()),
                6: Extent(6, len('    ! true a\\ '), ()), 7: Extent(7, len('    ! true \\ '), ()), 8: Extent(8, len('    ! true \\\\'), ()), 9: Extent(10, len('        x'), (10,))}
        for i, cand in sorted(found.items()):
            self.assertEqual(negated_pipeline(lines, cand), ends[i], lines[i])
        self.assertEqual(rewritten_shape(lines, extents, "! true"),
                         ['@test "x" {', '    ! true; true', '    ! true; true', '    ! true || true', '    ! true', '    ! true', '    ! true', '    ! true; true',
                          '    ! true ', '    ! true', '', '    true', '}'])
        self.assertTrue(_bash_parses(_rewritten(rewritten_shape(lines, extents, "! false"))))
        # _text_end on its own: an escaped blank stays; an unescaped one, one after an even run of backslashes and a second one
        # after the escaped one do not
        self.assertEqual([_text_end(t, len(t)) for t in ("! true ", "! true \\ ", "! true \\\\ ", "! true \\\\\\ ", "! true \\  ")],
                         [len("! true"), len("! true \\ "), len("! true \\\\"), len("! true \\\\\\ "), len("! true \\ ")])

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


def negated_heredoc_shapes(body, kept="kept", command="true", other="cat > /dev/null"):
    """{name: a synthetic .bats text} for a negated pipeline (`! cat > /dev/null <<WORD`, its negated command succeeding) that
    introduces a here-document whose body is the `body` line, in every form the grammar gives (man bash, Here Documents:
    `[n]<<[-]word`, the word quoted or not; Redirections: several on one line take effect in order, so their bodies follow in
    introduction order) and in the positions that matter to the extent, each mid-test and last: `<<WORD` unquoted, `<<-WORD` with
    the body and the terminator tab-indented, the word in single quotes, in double quotes and with a backslash, a file descriptor
    before the operator, two here-documents introduced on one line, one introduced in a pipeline segment whose next segment
    follows the terminator, an introducer line ending in a comment, an introducer followed by `; true` on its line, another
    command's here-document introduced on the line before the `!` (its body, the `kept` line, comes first and stays) and one
    introduced on the line after the pipeline's end (its body comes after and stays, though the empty lines standing where the
    pipeline's body was now precede it, under both rewrites alike; a test whose other command reads that body's content, a
    comparison against it, fails under both rewrites, and its negation reports undecided whatever it is: a false report on the
    visible side, none in the tree today), and a here-string (`<<<`, one line, no
    body: the line after it, `command`, is a command that runs). The body is data to cat, so it runs only if a rewrite leaves it
    outside the here-document: in the register `false`, which fails a test recorded ok (before fork PR #871's round 2 the extent
    ended at the introducer line, and the rewrite left the body and terminator to run as commands); in the road's marker pins a
    touch of a file under the test's directory, absent after the run, and the here-string's `command` the same touch, present.
    `other` is the other command of the two-command lines, `cat > /dev/null` in the register and a cat into a file in the pins,
    which then holds the `kept` body."""
    N = "! cat > /dev/null"
    S = {}
    forms = {"plain": ("%s <<EOF\n%s\nEOF" % (N, body), ""),
             "dash": ("%s <<-EOF\n\t%s\n\tEOF" % (N, body), ""),
             "squote": ("%s <<'EOF'\n%s\nEOF" % (N, body), ""),
             "dquote": ('%s <<"EOF"\n%s\nEOF' % (N, body), ""),
             "backslash": ("%s <<\\EOF\n%s\nEOF" % (N, body), ""),
             "fd": ("! cat 0<<EOF > /dev/null\n%s\nEOF" % body, ""),
             "two": ("%s <<A <<B\n%s\nA\n%s\nB" % (N, body, body), ""),
             "segment": ("! cat <<EOF |\n%s\nEOF\n        cat > /dev/null" % body, ""),
             "comment": ("%s <<EOF   # a note\n%s\nEOF" % (N, body), ""),
             "semi_tail": ("%s <<EOF; true\n%s\nEOF" % (N, body), ""),
             "others_first": ("%s <<A; %s <<B\n%s\nA\n%s\nB" % (other, N, kept, body), ""),
             "others_after": ("%s <<A; %s <<C\n%s\nA\n%s\nC" % (N, other, body, kept), ""),
             "herestring": ('! grep -q x <<< "$s"\n    %s' % command, "")}
    for name, (text, _) in forms.items():
        S["C_negated_heredoc_%s_mid" % name] = '@test "x" {\n    %s\n    true\n}\n' % text
        S["C_negated_heredoc_%s_last" % name] = '@test "x" {\n    true\n    %s\n}\n' % text
    return S


def ground_truth_shapes():
    """{name: a synthetic .bats text} whose negations are `! true`, the negated command succeeding, so under bats a test passes
    (`ok`) exactly when the negation asserted nothing there. The families of the round-8 scanner lens (subshell closers, command
    substitutions, heredocs, nested helpers and their call sites, test closes, brace groups, positions on the negation's own line,
    compounds, opener forms under both declaration patterns, `name() { # @test` among them) and the ones the round-8 findings of
    fork PR #778 and their refuters named (condition heads, lists,
    inline subshells and substitutions, process substitutions, backticks, paren-bodied helpers, `coproc`, `;;&`, continued lines,
    call sites through `eval`, an assignment prefix, `time --`, `command` and `env`), each shape mid-test and as the last command
    where the distinction exists. Every other command in a shape succeeds (files are written to /dev/null), so a test's verdict
    turns on the negation alone. A bare `! _h` calling a helper whose last command is `! true` (D_bang_called_last and _mid) holds
    two negations whose inversions compose: as written the helper fails and `! _h` succeeds, so the test passes and the verdict as
    written is uninformative under a one-column reading (`ok`, as for an inert site). The register held it out on the premise that
    the composition could not be measured, which the oracle refutes: the register's whole-file rewrite replaces both negations
    and records a last negation's pair (`not ok` under `! true`, `ok` under `! false`), and the per-candidate road decides each
    of the two read (BatsRoad's synthetic suite: the helper's `! true` through the `! false` column, `ok` as written and `not ok`
    with the helper's negated command failing, blamed on the helper's line; the call site through both columns). The register is
    the recall gate of the candidate predicate (every `!` of a
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
    # a here-document the NEGATED pipeline introduces, in every form (negated_heredoc_shapes): its body, `false`, is data as written
    # and a command that fails the test if a rewrite leaves it outside the here-document (regression-1, extra5-1 and tests-3 of fork
    # PR #871's round 1: the extent ended at the introducer line and the body and terminator ran as commands)
    S.update(negated_heredoc_shapes("false"))
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
    # a helper whose last command is `! true`, called by a bare `! _h` (correctness-4 of fork PR #871's round 1: the one site fork
    # PR #778's deleted Scanner case covered and mis-classified, in no shape until now): two candidates, the composition recorded
    S["D_bang_called_last"] = '@test "x" {\n    _h() {\n        run true\n        %s\n    }\n    ! _h\n}\n' % N
    S["D_bang_called_mid"] = '@test "x" {\n    _h() {\n        run true\n        %s\n    }\n    ! _h\n    true\n}\n' % N
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
    # the pipeline running on to the next line where bash continues it, each with the armed (last) position that must read as
    # read and never inert: after a `|` or `|&` followed by a comment (extra4-2 of fork PR #871's round 1: the comment ended the
    # extent, the rewrite split the pipeline in two, and the armed site read as inert), a comment line inside the continuation,
    # a trailing `\\` before the next stage, an open quote, an open parenthesis, an open brace group; and `|&` inside a pipeline
    for name, tail in (("pipe_comment", " | # note\n        cat"), ("pipeamp_comment", " |& # note\n        cat"),
                       ("comment_line", " |\n        # note\n        cat"), ("backslash_pipe", " \\\n        | cat"),
                       ("open_quote", ' | grep -q "a\n        b"'), ("open_paren", " | (\n        cat\n    )"),
                       ("open_group", " | {\n        cat\n    }")):
        S["G_cont_%s_mid" % name] = '@test "x" {\n    %s%s\n    true\n}\n' % (N, tail)
        S["G_cont_%s_last" % name] = '@test "x" {\n    true\n    %s%s\n}\n' % (N, tail)
    S["G_pipeamp_mid"] = '@test "x" {\n    %s |& cat\n    true\n}\n' % N
    S["G_pipeamp_last"] = '@test "x" {\n    true\n    %s |& cat\n}\n' % N
    # ANSI-C quoting in the negated command: `$'it\\'s'` holds an escaped quote (fresh-2 of round 1: read as a plain single quote,
    # the tracker ran off the text and the register raised on the shape)
    S["G_ansi_quote_mid"] = "@test \"x\" {\n    ! echo $'it\\'s' > /dev/null\n    true\n}\n"
    S["G_ansi_quote_last"] = "@test \"x\" {\n    true\n    ! echo $'it\\'s' > /dev/null\n}\n"
    # an operator inside something bash reads whole, which the walker proposes as the pipeline's end and bash refuses (fork PR #871's
    # round 2, second commit: the walker stopped there unasked, the rewrite split the construct and the remainder ran on its own, an inert
    # site read as read), one form each, mid and last: the two `[[ ]]` operators; a `&&` and a `;` inside quotes nested in a
    # `$( )` inside quotes (the second commit tracker paired the inner quote with the outer and exposed them), inside a `${ }` and inside
    # backticks; a
    # `#` glued to `|` and to a subshell's `)`, where bash begins a comment, glued to `(`, and glued to a `$( )`, where it is part
    # of the word (`$(true)#b || false`: an extent ending at the `#` would drop the `|| false` and its verdict); a negated compound
    # (man bash, Compound Commands: a group, `if`, `case`, `for`, `while`, `until`, `(( ))`, a subshell with a `;` inside), on one
    # line and over several, followed to its close; and the ANSI-C quote before a list operator, which armed the second commit tracker's
    # `$'` arm (with the arm removed that tracker read `b' || false` as a string and the extent ran to the line's end, where bash
    # reads the whole line as complete, so G_ansi_quote_* alone did not pin it; since the third commit there is no arm: the `||` is proposed
    # and bash ends the pipeline there)
    for name, text in (("op_in_dbracket_and", "! [[ a == a && b == b ]]"), ("op_in_dbracket_or", "! [[ a == a || b == b ]]"),
                       ("op_in_nested_quotes_and", '! echo "$(printf "%s && %s" a b)" > /dev/null'), ("op_in_nested_quotes_semi", '! echo "$(echo "a;b")" > /dev/null'),
                       ("op_in_param_and", "! echo ${x:-a&&b} > /dev/null"), ("op_in_param_semi", "! echo ${x:-a;b} > /dev/null"),
                       ("op_in_backticks_and", "! echo `true && echo b` > /dev/null"), ("op_in_backticks_semi", "! echo `echo a; echo b` > /dev/null"),
                       ("glued_comment_pipe", "! true |# a && false\n        cat"), ("glued_comment_subshell", "! (true)# a && false"),
                       ("glued_comment_open_paren", "! (# a && false\n        true)"), ("glued_word_subst", "! echo $(true)#b || false"),
                       ("negated_group", "! { false; true; }"), ("negated_group_lines", "! {\n        false\n        true\n    }"),
                       ("negated_if", "! if true; then true; fi"), ("negated_if_lines", "! if true; then\n        true\n    fi"),
                       ("negated_case", "! case a in a) true;; esac"), ("negated_case_lines", "! case a in\n      a) true ;;\n    esac"),
                       ("negated_for", "! for i in 1; do true; done"), ("negated_while", "! while false; do true; done"),
                       ("negated_until", "! until true; do false; done"), ("negated_arith", "! (( 1 && 1 ))"), ("negated_subshell_semi", "! (true; true)"),
                       ("ansi_quote_or_false", "! echo $'a\\'b' || false")):
        S["G_%s_mid" % name] = '@test "x" {\n    %s\n    true\n}\n' % text
        S["G_%s_last" % name] = '@test "x" {\n    true\n    %s\n}\n' % text
    # fork PR #871's round 2, third commit (the second commit's two verifiers): the walker tracks no quote and no parenthesis, since every operator
    # character is proposed and bash refuses one inside a quote or a substitution (a `$( )` inside double quotes opens a quoting
    # context of its own, and the tracker, pairing the quote inside it with the one outside, read the rest of the line as a string
    # and proposed no operator in it, so the extent ran to the line's end and the rewrite dropped the `; true` that made the
    # negation inert: an inert site read as read, the silent direction, which G_op_in_nested_quotes_* did not pin, holding the
    # other direction, an operator the desync exposed and bash refused); and a blank a backslash escapes at a line's end is a
    # character of the word and no trailing blank, so `! true \ ` is complete to bash and no continuation (the walker stripped the
    # blank before asking, bash read `! true \`, and the line after it became the pipeline's and blank in the rewrite: mid-test
    # the command after it deleted and the negation made last, an inert site read as read; last the close blanked). One shape
    # each, mid and last: a `'` inside nested double quotes inside a `"$( )"` and a `"` inside single quotes inside one, each
    # before a `; true` tail, which makes the last position inert too, so the recorded pair is (ok, ok) and a walker dropping the
    # tail records (not ok, ok) there; an escaped blank, an escaped tab and an escaped blank ending an argument at the line's end,
    # whose last position is read, (not ok, ok), and an escaped blank before a `; true` tail, (ok, ok) in both positions
    for name, text in (("hidden_semi_squote_in_subst", '! echo "$(echo "it\'s")" > /dev/null; true'),
                       ("hidden_semi_dquote_in_subst", '! echo "$(echo \'a"b\')" > /dev/null; true'),
                       ("escaped_blank_end", "! true \\ "), ("escaped_tab_end", "! true \\\t"), ("escaped_blank_arg_end", "! true a\\ "),
                       ("escaped_blank_semi_true", "! true \\ ; true")):
        S["G_%s_mid" % name] = '@test "x" {\n    %s\n    true\n}\n' % text
        S["G_%s_last" % name] = '@test "x" {\n    true\n    %s\n}\n' % text
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
    # the same rule on the `!` (fork PR #871's round 2, eighth commit): a `!` glued to a process substitution is one word with it,
    # `!<(true)`, `!>(true)`, a command bash finds nowhere (`2>/dev/null || true` swallows that; its `!` is declared text, and a
    # reader taking it as a word reds the declaration as stale), and separated from it by a blank it negates that command, a
    # candidate; a `!` continued by a lone `\` onto the next line is the word the next line's first character makes it: ` true`
    # joins to `! true`, a negation (a reader with no continuation found no candidate and recorded the file as written, (not ok,
    # not ok) where the record says (not ok, ok) in the last position), `true` to `!true`, one word (declared), and `! \` onto
    # `true` was read already; a doubled negation across the join, `! \` then `! true`, is `! ! true` to bash, whose run the
    # rewrite keeps whole (_bang_run: a run ending at the line's end wrote `! true` for it, and the doubled negation's record,
    # (ok, not ok), came back (not ok, ok))
    S["G_procsub_glued_in_mid"] = '@test "x" {\n    !<(true) 2>/dev/null || true\n    true\n}\n'
    S["G_procsub_glued_out_mid"] = '@test "x" {\n    !>(true) 2>/dev/null || true\n    true\n}\n'
    S["G_procsub_separated_in_mid"] = '@test "x" {\n    ! <(true) 2>/dev/null\n    true\n}\n'
    S["G_procsub_separated_in_last"] = '@test "x" {\n    true\n    ! <(true) 2>/dev/null\n}\n'
    S["G_procsub_separated_out_mid"] = '@test "x" {\n    ! >(true) 2>/dev/null\n    true\n}\n'
    S["G_procsub_separated_out_last"] = '@test "x" {\n    true\n    ! >(true) 2>/dev/null\n}\n'
    S["G_bang_backslash_newline_mid"] = '@test "x" {\n    !\\\n true\n    true\n}\n'
    S["G_bang_backslash_newline_last"] = '@test "x" {\n    true\n    !\\\n true\n}\n'
    S["G_bang_backslash_newline_glued_mid"] = '@test "x" {\n    !\\\ntrue 2>/dev/null || true\n    true\n}\n'
    S["G_bang_blank_backslash_newline_mid"] = '@test "x" {\n    ! \\\ntrue\n    true\n}\n'
    S["G_bang_blank_backslash_newline_last"] = '@test "x" {\n    true\n    ! \\\ntrue\n}\n'
    S["G_double_negation_continued_mid"] = '@test "x" {\n    ! \\\n    %s\n    true\n}\n' % N
    S["G_double_negation_continued_last"] = '@test "x" {\n    true\n    ! \\\n    %s\n}\n' % N
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
    # a test whose closing brace shares a line with its last command (regression-4 of fork PR #871's round 1: no close was found,
    # and the message blamed bash -n for a file bash parses and bats runs)
    S["I_close_shares_last_line_last"] = '@test "x" {\n    true\n    %s; }\n' % N
    S["I_close_shares_last_line_mid"] = '@test "x" {\n    %s\n    true; }\n' % N
    # a test whose closing brace shares its line with a here-document introducer, the body and terminator after the brace (fork PR
    # #871's round 2, second commit: the pending body left the test with no close, and where a later `}` closed a following test the first
    # swallowed the file); the body, `false`, is data unless a rewrite leaves it outside the here-document
    S["I_close_introduces_heredoc_last"] = '@test "x" {\n    true\n    ! cat > /dev/null <<EOF; }\nfalse\nEOF\n'
    S["I_close_introduces_heredoc_mid"] = '@test "x" {\n    ! cat > /dev/null <<EOF; true; }\nfalse\nEOF\n'
    S["I_one_liner_heredoc"] = '@test "x" { ! cat > /dev/null <<EOF; }\nfalse\nEOF\n'
    S["I_close_introduces_heredoc_then_test"] = '@test "a" {\n    true\n    ! cat > /dev/null <<EOF; }\nfalse\nEOF\n@test "b" {\n    ! true\n    true\n}\n'
    S["I_one_liner_between"] = '@test "a" {\n    %s\n    true\n}\n@test "b" { true; }\n@test "c" {\n    true\n    %s\n}\n' % (N, N)
    S["I_one_liner_negation"] = '@test "x" { ! true; }\n'
    S["I_one_liner_subshell"] = '@test "x" { ( ! true ); }\n'
    S["I_opener_trailing_negation"] = '@test "x" { ! true\n    true\n}\n'
    # a close followed on its line by file-scope text an armed negation stands in (fork PR #871's round 2, fourth commit, the silent
    # direction): a helper the next test calls, one with an `|| return 1` tail, a list joined to the function definition whose
    # group arms a variable the next test reads, and a one-liner followed by a list arming it (not by a helper: bats's own test
    # pattern takes the name greedily up to the LAST ` {` of the line, so `@test "x" { ! true; }; f() { ...; }` is one test with a
    # brace in its name and the file does not load). The helper's or list's `! false` is file scope, no test's, and stays as
    # written in both files (a rewrite touches a test's text alone), so y is recorded ok under both; a walker reading the close
    # as the last brace of the line took that negation as x's candidate and rewrote it, and y read (not ok, ok) there
    S["I_close_then_helper"] = '@test "x" {\n    %s; }; f() { ! false; }\n@test "y" {\n    f\n}\n' % N
    S["I_close_then_helper_or_return"] = '@test "x" {\n    %s; }; f() { ! false || return 1; }\n@test "y" {\n    f\n}\n' % N
    S["I_close_then_group_arming"] = '@test "x" {\n    %s; } && { ! false && armed=1; }\n@test "y" {\n    [ "${armed-}" = 1 ]\n}\n' % N
    S["I_one_liner_then_arming"] = '@test "x" { %s; }; ! false && armed=1\n@test "y" {\n    [ "${armed-}" = 1 ]\n}\n' % N
    # a close followed on its line by file-scope text that opens a construct closing on a LATER line (fork PR #871's round 2, fifth
    # commit, the fourth's direction again): a function body the next test calls, a case, a brace group joined to the definition
    # by `&&`, an if and a while each arming a variable the next test reads, a subshell whose failure would arm one the next test
    # reads as unset, and a here-document a file-scope `read` takes a line of for the next test to compare. The construct's
    # `! false` is file scope, no test's, and stays as written in both files, so y is recorded ok under both; a walker asking the
    # close of a line whole skipped x's close line (the open construct left it unparsed), ran x's extent to the construct's close,
    # or to y's where that close was no line its pattern named, and took the construct's negation as x's candidate: inert by
    # running x, while y is not ok once that negation is flipped. The here-document form was read right before the fifth commit
    # (the pending body is read past the brace) and pins the form beside the others
    S["I_close_then_function_lines"] = '@test "x" {\n    %s; }; f() {\n    ! false\n}\n@test "y" {\n    f\n}\n' % N
    S["I_close_then_case_lines"] = '@test "x" {\n    %s; }; case x in\n    x) ! false && armed=1 ;;\nesac\n@test "y" {\n    [ "${armed-}" = 1 ]\n}\n' % N
    S["I_close_then_group_lines"] = '@test "x" {\n    %s; } && {\n    ! false && armed=1\n}\n@test "y" {\n    [ "${armed-}" = 1 ]\n}\n' % N
    S["I_close_then_subshell_lines"] = '@test "x" {\n    %s; }; (\n    ! false\n) || armed=1\n@test "y" {\n    [ -z "${armed-}" ]\n}\n' % N
    S["I_close_then_if_lines"] = '@test "x" {\n    %s; }; if true; then\n    ! false && armed=1\nfi\n@test "y" {\n    [ "${armed-}" = 1 ]\n}\n' % N
    S["I_close_then_while_lines"] = '@test "x" {\n    %s; }; n=0; while [ "$n" -lt 1 ]; do\n    n=1\n    ! false && armed=1\ndone\n@test "y" {\n    [ "${armed-}" = 1 ]\n}\n' % N
    S["I_close_then_heredoc_lines"] = '@test "x" {\n    %s; }; read -r armed <<EOF\n! false\nEOF\n@test "y" {\n    [ "$armed" = \'! false\' ]\n}\n' % N
    # a close with no `;` or `&` before the brace, after a subshell's `)` and after `fi`, which bash reads as a close (the reserved
    # word follows a compound command's end) and bats runs; before the fifth commit no line pattern named such a line, the test
    # had no close and candidates() refused the file
    S["I_close_after_subshell_paren"] = '@test "x" {\n    ( %s ) }\n' % N
    S["I_close_after_fi"] = '@test "x" {\n    if true; then %s; fi }\n' % N
    # a brace glued to a following character on a test's line (fork PR #871's round 2, sixth commit, the fifth's direction): `}x`,
    # `}#` and `}}` are one word to bash, a command it runs inside the test (`}x` and `}}` are found on no PATH and `2>/dev/null ||
    # true` swallows that; `}#` fails, a `#` glued to a word begins no comment, and bats fails x under both rewrites, blamed on
    # its line, so decide reports it undecided), and a lone `\` ending the line after the brace joins it with the next line's
    # word; the negation after it is the test's last command, read. A walker asking every brace ended x at the glued one and found
    # no candidate, so both files were the shape as written and bats said (not ok, not ok) where the record says (not ok, ok).
    # Beside them, braces bash reads as the word `}` and the module must not refuse: a `\` after the close followed by an empty
    # line and a comment after the close, y opening after each; and a parameter expansion's brace before the close, followed by a
    # blank, asked and refused by the parse, the line's last brace the close
    S["I_close_glued_word"] = '@test "x" {\n    true; }x 2>/dev/null || true\n    %s\n}\n' % N
    S["I_close_glued_hash"] = '@test "x" {\n    true; }# not a comment\n    %s\n}\n' % N
    S["I_close_glued_brace"] = '@test "x" {\n    true; }} 2>/dev/null || true\n    %s\n}\n' % N
    S["I_close_backslash_newline_word"] = '@test "x" {\n    true; }\\\nx 2>/dev/null || true\n    %s\n}\n' % N
    S["I_close_backslash_newline_then_test"] = '@test "x" {\n    %s; }\\\n\n@test "y" {\n    true\n}\n' % N
    S["I_close_then_comment"] = '@test "x" {\n    %s; } # a comment after the close\n@test "y" {\n    true\n}\n' % N
    S["I_param_brace_then_close"] = '@test "x" {\n    echo ${x-} > /dev/null; %s; }\n' % N
    # a brace glued to a following character BEFORE the real close on the close line, and on a one-liner (fork PR #871's round 2,
    # seventh commit, the sixth's walker verifier): the close column is the line's last brace, and the negation between the glued
    # word and the close is the test's last command, read. A walker asking every brace of the close line for the column
    # (_close_col) cut the text at the glued one, found no candidate, and recorded the shape as written under both rewrites,
    # (not ok, not ok) where the record says (not ok, ok); the recall gate reads the same text and could not see that, this record can
    S["I_close_glued_before_close"] = '@test "x" {\n    true; }x 2>/dev/null || true; %s; }\n' % N
    S["I_one_liner_glued_before_close"] = '@test "x" { true; }x 2>/dev/null || true; %s; }\n' % N
    # a brace glued to a process substitution, `}<(true)`, `}>(true)`, one word to bash with it (fork PR #871's round 2, eighth
    # commit, F1 of the seventh's verifiers, the sixth commit's class: bash's read_token_word takes `<(` and `>(` as the word's
    # before its word-break check, and a reader ending the word at every metacharacter, the `<` and `>` among them, read a close
    # bash does not read, found no candidate, and recorded the file as written under both rewrites, (not ok, not ok) where the
    # record says (not ok, ok)); and a redirection from a process substitution after the close, `} < <(true)`, the brace the
    # word, y opening after it
    S["I_close_glued_procsub_in"] = '@test "x" {\n    true; }<(true) 2>/dev/null || true\n    %s\n}\n' % N
    S["I_close_glued_procsub_out"] = '@test "x" {\n    true; }>(true) 2>/dev/null || true\n    %s\n}\n' % N
    S["I_close_then_procsub_redirect"] = '@test "x" {\n    %s; } < <(true)\n@test "y" {\n    true\n}\n' % N
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
    G_procsub_glued_in_mid={2: "one word with the process substitution, `!<(true)`, a command bash finds nowhere"},
    G_procsub_glued_out_mid={2: "one word with the process substitution, `!>(true)`, a command bash finds nowhere"},
    G_bang_backslash_newline_glued_mid={2: "one word with the next line's first word after the continuation, `!true`, a command bash finds nowhere"},
    I_close_then_heredoc_lines={6: "text in a string, the next test's comparison against the line a file-scope read took"},
    X_test_bracket_mid={2: "the operator of `[`"},
    X_test_dbracket_mid={2: "the operator of `[[`"},
    X_run_negation_mid={4: "run's own inverted status, checked by run"},
)
# the tests of the register that hold no `!` at all, by shape and 1-based test ordinal: a test recorded `ok` with no candidate must
# be one of these, or hold only declared `!` words, for the gate to pass it
NO_NEGATION = {"I_one_liner_between": (2,), "E_setup_before_test": (1,), "I_close_then_helper": (2,), "I_close_then_helper_or_return": (2,),
               "I_close_then_group_arming": (2,), "I_one_liner_then_arming": (2,), "I_close_then_function_lines": (2,), "I_close_then_case_lines": (2,),
               "I_close_then_group_lines": (2,), "I_close_then_subshell_lines": (2,), "I_close_then_if_lines": (2,), "I_close_then_while_lines": (2,),
               "I_close_backslash_newline_then_test": (2,), "I_close_then_comment": (2,), "I_close_then_procsub_redirect": (2,)}


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
        version_out, version_err, version_ended, _, _ = _run_bats([bats, "--version"], None, env, RUN_TIMEOUT)   # bounded, stdin /dev/null, like every bats run here
        if version_ended or not version_out.split():
            raise RuntimeError("`bats --version` %s: %s" % ("did not finish in %d s" % RUN_TIMEOUT if version_ended else "printed no version",
                                                             (version_out + version_err).strip()[-500:] or "(nothing)"))
        version = version_out.strip()
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


def _differing_shapes(got, want):
    """One line per shape whose verdicts under a rewrite differ between what bats said (got) and the record (want), each named
    with both: the agreement gate's message (BatsGroundTruth), which unittest's dict diff elided for a record of hundreds of
    shapes (extra7-1 of fork PR #871's round 1: the gate red naming the bats version and not one shape that changed)."""
    return ["  %s: recorded %r, bats said %r" % (name, want.get(name), got.get(name)) for name in sorted(set(got) | set(want)) if got.get(name) != want.get(name)]


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
    run (WHERE_BATS_RUNS: CI's shell job's Linux cell; both of its cells install a bats and the wrapper skips on macOS), since a run
    that verified nothing must not read like one that verified every shape. Under a bash that lacks what this module reads (the
    bash-4 syntax some shapes use, `|&`, `coproc` and `;;&`, or the here-document warning under -n: BASH_4_SYNTAX, bash_shortfall)
    all four skip too, naming that bash (fresh-1 of fork PR #871's round 1: the recall tests need no bats and run in every Python
    cell, macOS's bash 3.2.57 among them, where candidates() would raise); the two tests of this class that need no bash run
    everywhere."""

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
        'C_negated_heredoc_backslash_last': ('not ok', 'ok'),
        'C_negated_heredoc_backslash_mid': ('ok', 'ok'),
        'C_negated_heredoc_comment_last': ('not ok', 'ok'),
        'C_negated_heredoc_comment_mid': ('ok', 'ok'),
        'C_negated_heredoc_dash_last': ('not ok', 'ok'),
        'C_negated_heredoc_dash_mid': ('ok', 'ok'),
        'C_negated_heredoc_dquote_last': ('not ok', 'ok'),
        'C_negated_heredoc_dquote_mid': ('ok', 'ok'),
        'C_negated_heredoc_fd_last': ('not ok', 'ok'),
        'C_negated_heredoc_fd_mid': ('ok', 'ok'),
        'C_negated_heredoc_herestring_last': ('ok', 'ok'),
        'C_negated_heredoc_herestring_mid': ('ok', 'ok'),
        'C_negated_heredoc_others_after_last': ('ok', 'ok'),
        'C_negated_heredoc_others_after_mid': ('ok', 'ok'),
        'C_negated_heredoc_others_first_last': ('not ok', 'ok'),
        'C_negated_heredoc_others_first_mid': ('ok', 'ok'),
        'C_negated_heredoc_plain_last': ('not ok', 'ok'),
        'C_negated_heredoc_plain_mid': ('ok', 'ok'),
        'C_negated_heredoc_segment_last': ('not ok', 'ok'),
        'C_negated_heredoc_segment_mid': ('ok', 'ok'),
        'C_negated_heredoc_semi_tail_last': ('ok', 'ok'),
        'C_negated_heredoc_semi_tail_mid': ('ok', 'ok'),
        'C_negated_heredoc_squote_last': ('not ok', 'ok'),
        'C_negated_heredoc_squote_mid': ('ok', 'ok'),
        'C_negated_heredoc_two_last': ('not ok', 'ok'),
        'C_negated_heredoc_two_mid': ('ok', 'ok'),
        'C_quoted_introducer_two_tests': ('ok,ok', 'ok,ok'),
        'C_shift': ('ok', 'ok'),
        'C_text_bang_only': ('ok', 'ok'),
        'C_two_introducers': ('ok', 'ok'),
        'D_allman': ('not ok', 'ok'),
        'D_and_true_last': ('not ok', 'ok'),
        'D_bang_called_last': ('not ok', 'ok'),
        'D_bang_called_mid': ('ok', 'ok'),
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
        'G_ansi_quote_last': ('not ok', 'ok'),
        'G_ansi_quote_mid': ('ok', 'ok'),
        'G_ansi_quote_or_false_last': ('not ok', 'ok'),
        'G_ansi_quote_or_false_mid': ('not ok', 'ok'),
        'G_backtick_glued_mid': ('ok', 'ok'),
        'G_backtick_lone_bang_mid': ('ok', 'ok'),
        'G_bang_backslash_newline_glued_mid': ('ok', 'ok'),
        'G_bang_backslash_newline_last': ('not ok', 'ok'),
        'G_bang_backslash_newline_mid': ('ok', 'ok'),
        'G_bang_blank_backslash_newline_last': ('not ok', 'ok'),
        'G_bang_blank_backslash_newline_mid': ('ok', 'ok'),
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
        'G_cont_backslash_pipe_last': ('not ok', 'ok'),
        'G_cont_backslash_pipe_mid': ('ok', 'ok'),
        'G_cont_comment_line_last': ('not ok', 'ok'),
        'G_cont_comment_line_mid': ('ok', 'ok'),
        'G_cont_open_group_last': ('not ok', 'ok'),
        'G_cont_open_group_mid': ('ok', 'ok'),
        'G_cont_open_paren_last': ('not ok', 'ok'),
        'G_cont_open_paren_mid': ('ok', 'ok'),
        'G_cont_open_quote_last': ('not ok', 'ok'),
        'G_cont_open_quote_mid': ('ok', 'ok'),
        'G_cont_pipe_comment_last': ('not ok', 'ok'),
        'G_cont_pipe_comment_mid': ('ok', 'ok'),
        'G_cont_pipeamp_comment_last': ('not ok', 'ok'),
        'G_cont_pipeamp_comment_mid': ('ok', 'ok'),
        'G_continued_args_last': ('not ok', 'ok'),
        'G_continued_args_mid': ('ok', 'ok'),
        'G_continued_or_false_last': ('not ok', 'ok'),
        'G_continued_or_false_mid': ('not ok', 'ok'),
        'G_continued_or_true_last': ('ok', 'ok'),
        'G_continued_or_true_mid': ('ok', 'ok'),
        'G_continued_pipe_last': ('not ok', 'ok'),
        'G_continued_pipe_mid': ('ok', 'ok'),
        'G_double_negation_continued_last': ('ok', 'not ok'),
        'G_double_negation_continued_mid': ('ok', 'not ok'),
        'G_double_negation_last': ('ok', 'not ok'),
        'G_double_negation_mid': ('ok', 'not ok'),
        'G_escaped_blank_arg_end_last': ('not ok', 'ok'),
        'G_escaped_blank_arg_end_mid': ('ok', 'ok'),
        'G_escaped_blank_end_last': ('not ok', 'ok'),
        'G_escaped_blank_end_mid': ('ok', 'ok'),
        'G_escaped_blank_semi_true_last': ('ok', 'ok'),
        'G_escaped_blank_semi_true_mid': ('ok', 'ok'),
        'G_escaped_tab_end_last': ('not ok', 'ok'),
        'G_escaped_tab_end_mid': ('ok', 'ok'),
        'G_eval_string_mid': ('ok', 'ok'),
        'G_first_command': ('ok', 'ok'),
        'G_glued_comment_open_paren_last': ('not ok', 'ok'),
        'G_glued_comment_open_paren_mid': ('ok', 'ok'),
        'G_glued_comment_pipe_last': ('not ok', 'ok'),
        'G_glued_comment_pipe_mid': ('ok', 'ok'),
        'G_glued_comment_subshell_last': ('not ok', 'ok'),
        'G_glued_comment_subshell_mid': ('ok', 'ok'),
        'G_glued_word_subst_last': ('not ok', 'ok'),
        'G_glued_word_subst_mid': ('not ok', 'ok'),
        'G_hidden_semi_dquote_in_subst_last': ('ok', 'ok'),
        'G_hidden_semi_dquote_in_subst_mid': ('ok', 'ok'),
        'G_hidden_semi_squote_in_subst_last': ('ok', 'ok'),
        'G_hidden_semi_squote_in_subst_mid': ('ok', 'ok'),
        'G_last_command': ('not ok', 'ok'),
        'G_last_past_comment_blank': ('not ok', 'ok'),
        'G_lone_bang_last': ('not ok', 'ok'),
        'G_lone_bang_mid': ('ok', 'ok'),
        'G_lone_bang_semicolon_mid': ('ok', 'ok'),
        'G_mid_after_run': ('ok', 'ok'),
        'G_negated_arith_last': ('not ok', 'ok'),
        'G_negated_arith_mid': ('ok', 'ok'),
        'G_negated_case_last': ('not ok', 'ok'),
        'G_negated_case_lines_last': ('not ok', 'ok'),
        'G_negated_case_lines_mid': ('ok', 'ok'),
        'G_negated_case_mid': ('ok', 'ok'),
        'G_negated_for_last': ('not ok', 'ok'),
        'G_negated_for_mid': ('ok', 'ok'),
        'G_negated_group_last': ('not ok', 'ok'),
        'G_negated_group_lines_last': ('not ok', 'ok'),
        'G_negated_group_lines_mid': ('ok', 'ok'),
        'G_negated_group_mid': ('ok', 'ok'),
        'G_negated_if_last': ('not ok', 'ok'),
        'G_negated_if_lines_last': ('not ok', 'ok'),
        'G_negated_if_lines_mid': ('ok', 'ok'),
        'G_negated_if_mid': ('ok', 'ok'),
        'G_negated_subshell_semi_last': ('not ok', 'ok'),
        'G_negated_subshell_semi_mid': ('ok', 'ok'),
        'G_negated_until_last': ('not ok', 'ok'),
        'G_negated_until_mid': ('ok', 'ok'),
        'G_negated_while_last': ('not ok', 'ok'),
        'G_negated_while_mid': ('ok', 'ok'),
        'G_op_in_backticks_and_last': ('not ok', 'ok'),
        'G_op_in_backticks_and_mid': ('ok', 'ok'),
        'G_op_in_backticks_semi_last': ('not ok', 'ok'),
        'G_op_in_backticks_semi_mid': ('ok', 'ok'),
        'G_op_in_dbracket_and_last': ('not ok', 'ok'),
        'G_op_in_dbracket_and_mid': ('ok', 'ok'),
        'G_op_in_dbracket_or_last': ('not ok', 'ok'),
        'G_op_in_dbracket_or_mid': ('ok', 'ok'),
        'G_op_in_nested_quotes_and_last': ('not ok', 'ok'),
        'G_op_in_nested_quotes_and_mid': ('ok', 'ok'),
        'G_op_in_nested_quotes_semi_last': ('not ok', 'ok'),
        'G_op_in_nested_quotes_semi_mid': ('ok', 'ok'),
        'G_op_in_param_and_last': ('not ok', 'ok'),
        'G_op_in_param_and_mid': ('ok', 'ok'),
        'G_op_in_param_semi_last': ('not ok', 'ok'),
        'G_op_in_param_semi_mid': ('ok', 'ok'),
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
        'G_pipeamp_last': ('not ok', 'ok'),
        'G_pipeamp_mid': ('ok', 'ok'),
        'G_pipeline_last': ('not ok', 'ok'),
        'G_pipeline_mid': ('ok', 'ok'),
        'G_procsub_glued_in_mid': ('ok', 'ok'),
        'G_procsub_glued_out_mid': ('ok', 'ok'),
        'G_procsub_separated_in_last': ('not ok', 'ok'),
        'G_procsub_separated_in_mid': ('ok', 'ok'),
        'G_procsub_separated_out_last': ('not ok', 'ok'),
        'G_procsub_separated_out_mid': ('ok', 'ok'),
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
        'I_close_after_fi': ('not ok', 'ok'),
        'I_close_after_subshell_paren': ('not ok', 'ok'),
        'I_close_backslash_newline_then_test': ('not ok,ok', 'ok,ok'),
        'I_close_backslash_newline_word': ('not ok', 'ok'),
        'I_close_glued_before_close': ('not ok', 'ok'),
        'I_close_glued_brace': ('not ok', 'ok'),
        'I_close_glued_hash': ('not ok', 'not ok'),
        'I_close_glued_procsub_in': ('not ok', 'ok'),
        'I_close_glued_procsub_out': ('not ok', 'ok'),
        'I_close_glued_word': ('not ok', 'ok'),
        'I_close_introduces_heredoc_last': ('not ok', 'ok'),
        'I_close_introduces_heredoc_mid': ('ok', 'ok'),
        'I_close_introduces_heredoc_then_test': ('not ok,ok', 'ok,ok'),
        'I_close_shares_last_line_last': ('not ok', 'ok'),
        'I_close_shares_last_line_mid': ('ok', 'ok'),
        'I_close_then_case_lines': ('not ok,ok', 'ok,ok'),
        'I_close_then_comment': ('not ok,ok', 'ok,ok'),
        'I_close_then_function_lines': ('not ok,ok', 'ok,ok'),
        'I_close_then_group_arming': ('not ok,ok', 'ok,ok'),
        'I_close_then_group_lines': ('not ok,ok', 'ok,ok'),
        'I_close_then_helper': ('not ok,ok', 'ok,ok'),
        'I_close_then_helper_or_return': ('not ok,ok', 'ok,ok'),
        'I_close_then_heredoc_lines': ('not ok,ok', 'ok,ok'),
        'I_close_then_if_lines': ('not ok,ok', 'ok,ok'),
        'I_close_then_procsub_redirect': ('not ok,ok', 'ok,ok'),
        'I_close_then_subshell_lines': ('not ok,ok', 'ok,ok'),
        'I_close_then_while_lines': ('not ok,ok', 'ok,ok'),
        'I_comment_form_and_at_test': ('ok,not ok', 'ok,ok'),
        'I_comment_form_function_keyword_mid': ('ok', 'ok'),
        'I_comment_form_indented_mid': ('ok', 'ok'),
        'I_comment_form_last': ('not ok', 'ok'),
        'I_comment_form_mid': ('ok', 'ok'),
        'I_comment_form_no_parens_mid': ('ok', 'ok'),
        'I_one_liner_between': ('ok,ok,not ok', 'ok,ok,ok'),
        'I_one_liner_glued_before_close': ('not ok', 'ok'),
        'I_one_liner_heredoc': ('not ok', 'ok'),
        'I_one_liner_negation': ('not ok', 'ok'),
        'I_one_liner_subshell': ('not ok', 'ok'),
        'I_one_liner_then_arming': ('not ok,ok', 'ok,ok'),
        'I_opener_indented_last': ('not ok', 'ok'),
        'I_opener_indented_mid': ('ok', 'ok'),
        'I_opener_tab_indented_last': ('not ok', 'ok'),
        'I_opener_tab_indented_mid': ('ok', 'ok'),
        'I_opener_trailing_command_last': ('not ok', 'ok'),
        'I_opener_trailing_command_mid': ('ok', 'ok'),
        'I_opener_trailing_comment_last': ('not ok', 'ok'),
        'I_opener_trailing_comment_mid': ('ok', 'ok'),
        'I_opener_trailing_negation': ('ok', 'ok'),
        'I_param_brace_then_close': ('not ok', 'ok'),
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
        skip_unless_bash_serves(self)
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
        skip_unless_bash_serves(self)
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

    def test_the_agreement_message_names_every_shape_that_differs_with_both_verdicts(self):
        # extra7-1 of fork PR #871's round 1: the gate red with the differing shapes elided by unittest's truncated dict diff, so
        # the message named the bats version and not one shape. Every differing shape is listed, recorded and observed, a shape
        # missing from either side included, and an agreeing one is not
        got = {"A_x": "ok,ok", "B_y": "not ok", "C_z": "ok"}
        want = {"A_x": "ok,ok", "B_y": "ok", "D_w": "ok"}
        self.assertEqual(_differing_shapes(got, want), ["  B_y: recorded 'ok', bats said 'not ok'", "  C_z: recorded None, bats said 'ok'",
                                                        "  D_w: recorded 'ok', bats said None"])
        self.assertEqual(_differing_shapes(got, dict(got)), [])

    def test_under_a_bash_lacking_what_the_module_reads_every_test_deriving_from_bash_skips_naming_that_bash(self):
        # fresh-1 of fork PR #871's round 1: the two recall tests run in every Python cell, parsing every shape with the local bash,
        # and macOS's bash 3.2.57 refuses `|&`, `coproc` and `;;&`, so candidates() would raise there; round 2's second commit (the verifiers, with a
        # bash 3.2.57 built from the GNU tarball): the same bash gives no here-document warning under -n, on which the extents and
        # the here-document extent rest, so the Extents and Candidates tests red there too, and this pin's own closing assertion
        # that the local bash refuses nothing FAILED under that bash, where the ruling asked for a gate. Simulated with two bashes
        # on PATH, each reporting 3.2.57 as its version: one refusing the three constructs under -n, one giving no here-document
        # warning; under either, the probe names the version and what is lacking, each register test and each test of the
        # classes deriving from bash skips, loudly, saying where they run, and the two tests here that need no bash do not. The
        # real bash's probe is restored after; whatever it says stands, since under a bash that lacks something the skips above
        # are the gate at work, not a failure of this pin
        refusing = ("#!/bin/bash\n"
                    'if [ "$1" = -c ]; then printf %s "3.2.57(1)-release"; exit 0; fi\n'
                    'input=$(cat)\n'
                    "if printf '%s' \"$input\" | grep -qE '\\|&|coproc|;;&'; then echo 'bash: line 1: syntax error near unexpected token' >&2; exit 2; fi\n"
                    "printf '%s\\n' \"$input\" | exec /bin/bash \"$@\"\n")
        unwarning = ("#!/bin/bash\n"
                     'if [ "$1" = -c ]; then printf %s "3.2.57(2)-release"; exit 0; fi\n'
                     '/bin/bash "$@" 2> "$0.err"; rc=$?\n'
                     "grep -v 'delimited by end-of-file' \"$0.err\" >&2\n"
                     "exit $rc\n")
        deriving = [Extents("test_bash_test_extents_reads_the_tests_bash_parses"), Candidates("test_candidates_refuses_a_test_bash_cannot_close"),
                    BatsSuites("test_every_test_of_every_suite_is_closed_by_bash_and_its_candidates_are_listed"),
                    BatsRoad("test_run_test_alone_reads_what_bats_says_of_a_frame_a_skip_an_unloadable_file_and_a_missing_name")]
        for text, expected in ((refusing, ("3.2.57(1)-release", "refuses `true |& cat`, which register shapes use")),
                               (unwarning, ("3.2.57(2)-release", "gives no warning of a here-document the end of the input cuts off under -n, "
                                                                  "which is how a here-document's end is read here"))):
            with tempfile.TemporaryDirectory() as d:
                shim = os.path.join(d, "bash")
                with open(shim, "w", encoding="utf-8") as f:
                    f.write(text)
                os.chmod(shim, 0o755)
                with unittest.mock.patch.dict(_BASH_PROBE, clear=True), \
                        unittest.mock.patch.dict(os.environ, {"PATH": d + os.pathsep + os.environ.get("PATH", "")}):
                    self.assertEqual(bash_shortfall(), expected)
                    self.assertTrue(_bash_parses(["true | cat"]), "the shim refuses more than the bash-4 syntax: this pins nothing")
                    for test in (self.test_every_negation_of_the_register_is_a_candidate_unless_declared_an_operator_or_text,
                                 self.test_an_ok_test_without_a_candidate_holds_only_declared_bangs_or_none_and_every_declaration_holds,
                                 self.test_the_record_is_what_bats_says_under_both_rewrites,
                                 self.test_decide_reads_every_test_of_the_register_whose_verdicts_differ_and_refuses_none,
                                 BatsCorpus("test_every_candidate_of_every_suite_is_read_by_bats").test_every_candidate_of_every_suite_is_read_by_bats,
                                 *(case.setUp for case in deriving)):
                        with self.assertRaises(unittest.SkipTest) as cm:
                            test()
                        self.assertIn("NOT RUN: bash %s %s" % expected, str(cm.exception))
                        self.assertIn("CI's Linux cells", str(cm.exception))
                    self.test_the_agreement_message_names_every_shape_that_differs_with_both_verdicts()
                    Population("test_a_dead_glob_beside_a_live_one_raises_naming_the_dead_one").setUp()

    def test_without_bats_the_agreement_half_skips_and_names_where_it_runs(self):
        # regression-1 of fork PR #778: absent bats is a skip that names CI's shell job and the versions the record stands on, never
        # a pass that verified nothing. The bash probe is held at "nothing lacking" for the test, since under a bash that lacks
        # something the bash gate fires first and this message is never reached (round 2's second commit: under bash 3.2.57 this test failed on the
        # gate's message, which has its own pin above)
        with unittest.mock.patch.dict(_BASH_PROBE, {"shortfall": False}), unittest.mock.patch("shutil.which", return_value=None):
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
        skip_unless_bash_serves(self)
        if not shutil.which("bats"):
            self.skipTest("bats is not on PATH: the record (bats %s) stands unverified here; %s" % (" and ".join(self.RECORDED_WITH), WHERE_BATS_RUNS))

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
            want = {name: v[col] for name, v in self.RECORDED.items()}
            differing = _differing_shapes(got, want)
            self.assertEqual(got, want, "%s on this box against the record under the %s rewrite%s: %d shape(s) differ:\n%s\n%s" % (
                version, what, "" if recorded_with else " (a version the record was not verified against: %s)" % ", ".join(self.RECORDED_WITH),
                len(differing), "\n".join(differing), output[-6000:]))


# where the bats-backed tests run, for the skip messages: the shell job has two cells on a dispatch or the weekly schedule and one
# (ubuntu-latest) otherwise (.github/workflows/ci.yml), both install a bats, and the wrapper skips every test of the module on
# macOS, so the Linux cell is the one that verifies the record and decides the tree (extra4-5 and extra7-2 of fork PR #871's
# round 1: the messages called the job "the one cell that installs bats")
WHERE_BATS_RUNS = ("CI's shell job, whose Linux cell is where this runs: the job's two cells both install a bats (ubuntu-latest 1.11.1 from "
                   "the release tarball, macos-latest Homebrew's bats-core), and the wrapper, tests/bats-bare-negation-shell-job.bats, skips "
                   "every test of this module on macOS, whose bash is 3.2.57 and whose bats the record is not verified against")
CORPUS_SKIP = "bats is not on PATH: the corpus's candidates stand undecided here; " + WHERE_BATS_RUNS


class BatsCorpus(unittest.TestCase):
    """bats over the tree: every candidate of every suite (suite_files, bash_test_extents, candidates) is decided by bats itself,
    its negated pipeline rewritten to `! true` and to `! false` (rewrite) and the enclosing test run alone under each in a scratch
    copy of the tree (decide_under_bats, run_test_alone, every run bounded at RUN_TIMEOUT). Three verdicts (decide): read, the
    test's outcome turns on the negation, no report; inert, the test passes under both, the negation asserts nothing, a defect;
    undecided, both fail, the failure is blamed outside the candidate's test, bats gave no verdict (a run the bound ended among
    them), or the rewritten file does not parse. Each candidate's row is printed as it is decided, its head before its runs, so a
    run an outer bound ends (the wrapper test's BATS_TEST_TIMEOUT) leaves its candidate named in this test's output; an inert or
    undecided one's report in full (the message naming which, the line as written and under each rewrite, both outcomes, the
    blamed line, what bats said) follows the table, and the test fails on it. CORPUS_WORKERS candidates are decided at a time, each
    run in its own copy of the tree. Where bats is absent this skips, naming where it runs (WHERE_BATS_RUNS: CI's shell job's Linux
    cell, through tests/bats-bare-negation-shell-job.bats)."""

    SKIP = CORPUS_SKIP

    def test_every_candidate_of_every_suite_is_read_by_bats(self):
        skip_unless_bash_serves(self)
        if not shutil.which("bats"):
            self.skipTest(self.SKIP)
        root, files = ROOT, suite_files()
        decisions, t0 = [], time.monotonic()
        work = [(relpath, lines, extents, cand) for relpath in files for lines, extents in [_read_suite(relpath)] for cand in candidates(lines, extents)]

        def one(item):
            relpath, lines, extents, cand = item
            print("%s:%d started" % (relpath, cand.line + 1), flush=True)   # the head before the runs: a run an outer bound ends is attributable
            return decide_under_bats(root, relpath, lines, extents, cand, scratch)

        # CORPUS_WORKERS candidates at a time, each run in its own copy of the tree; the TERM handler on this thread ends every
        # worker's live bats (_term_ends_live_runs), which a worker cannot install for itself
        with tempfile.TemporaryDirectory() as scratch, _term_ends_live_runs(), concurrent.futures.ThreadPoolExecutor(CORPUS_WORKERS) as pool:
            for d in pool.map(one, work):
                decisions.append(d)
                print("%s:%d %s" % (d.relpath, d.cand.line + 1, _row(d)), flush=True)
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
        # the bash probe held at "nothing lacking", as in the register's without-bats pin: the bash gate fires first under a bash
        # that lacks something, and this is the message of the other gate
        with unittest.mock.patch.dict(_BASH_PROBE, {"shortfall": False}), unittest.mock.patch("shutil.which", return_value=None):
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
                           ([ok, BatsRun("no TAP", None, None, "Error: Duplicate test name(s) in file", 0.0)], "the outcome was `no TAP`"),
                           ([BatsRun("did not load", None, None, "", 0.0), bad(10)], "the outcome was `did not load`"),
                           ([ok, BatsRun("timed out", None, None, "1..1", 61.2)], "under `! false` bats gave no verdict on the test: the run was ended after 61 s with no verdict"),
                           ([ok, _agreed("! false", [BatsRun("timed out", None, None, "1..1", 61.2), BatsRun("timed out", None, None, "1..1", 60.8)])],
                            "under `! false` bats gave no verdict on the test: the side's 2 runs were each ended at the bound, 122 s together, with no verdict"),
                           ([BatsRun("no run", None, None, "the rewritten file does not parse under bash -n: x", 0.0), ok], "does not parse under bash -n"),
                           ([BatsRun("no run", None, None, "the negated pipeline runs off the end of the text", 0.0), ok], "runs off the end"),
                           ([_agreed("! true", [ok, bad(10)]), ok], "under `! true` the test's 2 runs disagree (ok, then not ok @10): its outcome does not turn on this rewrite alone")):
            verdict, message = decide("tests/x.bats", cand, extent, runs)
            self.assertEqual(verdict, "undecided", message)
            self.assertIn(said, message)
            self.assertNotIn("asserts nothing", message)
        # a side's runs stand as one when they agree in outcome, blamed line and file, its seconds summed and its runs counted (a
        # message about the run's time then says the count and the total, never the total as one run's: the walker verifier of fork
        # PR #871's round 2, second commit, read `ended after 6 s` off a 3 s bound); a differing outcome or a failure blamed elsewhere is `disagree`,
        # and its detail carries every run's TAP for the report
        self.assertEqual(_agreed("! true", [bad(10)._replace(secs=1.5), bad(10)._replace(secs=2.0)]), bad(10)._replace(secs=3.5, runs=2))
        self.assertEqual(_agreed("! false", [ok, ok]).outcome, "ok")
        for side in ([ok, bad(10)], [bad(10), bad(11)], [bad(10), bad(10, "tests/other.bats")]):
            run = _agreed("! true", side)
            self.assertEqual((run.outcome, run.line, run.file), ("disagree", None, None))
            self.assertIn("run 1, %s:" % _shown(side[0]), run.detail)
            self.assertIn("run 2, %s:" % _shown(side[1]), run.detail)


class Invocations(unittest.TestCase):
    def test_every_bats_invocation_goes_through_run_bats(self):
        # extra7-3 of fork PR #871's round 1: the register's `bats --version` was the one bats run outside _run_bats, so it carried
        # no bound and no stdin redirection, and one unbounded invocation is how the original hang got in. Derived from the
        # module's syntax tree: every subprocess call outside _run_bats names its program as a string literal, and that program is
        # bash or pgrep, or is sys.executable; a call whose program is a variable, `bats` among them, or the literal `bats`, is
        # refused wherever it stands but inside _run_bats
        with open(__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        calls, outside = [], []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for inner in ast.walk(node):
                    if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and isinstance(inner.func.value, ast.Name)
                            and inner.func.value.id == "subprocess"):
                        calls.append((node.name, inner))
        for func, call in calls:
            if func == "_run_bats":
                continue
            args = call.args[0] if call.args else None
            program = args.elts[0] if isinstance(args, ast.List) and args.elts else None
            if isinstance(program, ast.Constant) and program.value in ("bash", "pgrep"):
                outside.append((func, program.value))
            elif isinstance(program, ast.Attribute) and isinstance(program.value, ast.Name) and (program.value.id, program.attr) == ("sys", "executable"):
                outside.append((func, "sys.executable"))
            else:
                self.fail("%s calls subprocess.%s with a program that is not a bash, pgrep or sys.executable literal (line %d): a bats run "
                          "belongs in _run_bats, bounded, stdin /dev/null, in its own group" % (func, call.func.attr, call.lineno))
        self.assertEqual(sum(1 for func, _ in calls if func == "_run_bats"), 1, "one Popen in _run_bats")
        self.assertGreaterEqual(len(outside), 3, "the census found fewer subprocess calls than the module makes: %s" % outside)
        print("%d subprocess calls outside _run_bats, programs %s" % (len(outside), sorted({p for _, p in outside})))


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

    def setUp(self):
        skip_unless_bash_serves(self)

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
        # no test for is `no such test`, a file holding two tests of one name is refused by bats whole (`Error: Duplicate test
        # name(s) in file`, no plan line: `no TAP`, with bats's words in the detail; the other test of that file runs), and a name
        # holding ERE metacharacters and a `$` is matched literally, as written
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tree", "tests"))
            with open(os.path.join(d, "tree", "tests", "probe.bats"), "w", encoding="utf-8") as f:
                f.write('@test "helper (x) $HOME" {\n    _h() {\n        run true\n        ! true\n    }\n    _h\n    true\n}\n'
                        '@test "line start" {\n    true\n    ! true\n}\n@test "skipped one" {\n    skip "no reason"\n}\n@test "ok one" {\n    ! true\n    true\n}\n')
            with open(os.path.join(d, "tree", "tests", "bad.bats"), "w", encoding="utf-8") as f:
                f.write('@test "bad" {\n    echo "\n}\n')
            with open(os.path.join(d, "tree", "tests", "dup.bats"), "w", encoding="utf-8") as f:
                f.write('@test "dup" {\n    ! true\n}\n@test "dup" {\n    true\n}\n@test "other" {\n    true\n}\n')
            tree = os.path.join(d, "tree")
            run = run_test_alone(tree, "tests/dup.bats", "dup", d)
            self.assertEqual(run.outcome, "no TAP", run.detail)
            self.assertIn("Duplicate test name", run.detail)
            self.assertEqual(run_test_alone(tree, "tests/dup.bats", "other", d).outcome, "ok")
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

    # OPEN OBSERVATION (fork PR #871, round 1, 2026-09-20): the test below went red ONCE on its teardown-marker assertion under the
    # wrapper (tests/bats-bare-negation-shell-job.bats, an outer bats 1.10.0 with BATS_TEST_TIMEOUT=180, the configuration that
    # gates landing) on the box the record was taken on, and did not reproduce in 31 further observations there (load not
    # recorded). The round's refuter then reproduced the same red 4 of 4 times with the process pinned to one busy CPU
    # (`taskset -c <cpu>`, 3 runs inside a systemd scope and 1 plain), 2 of 4 on two CPUs shared with three busy processes, and 0
    # of 3 on two idle CPUs, and read the mechanism as bats's own shutdown: the bats leader dies of the TERM within about 1 ms, so
    # _end_group's wait returns at once and the KILL follows about 3 ms after the TERM, while the teardown's marker appears 0.9 to
    # 2.4 ms after the TERM; and with the KILL removed and one CPU the marker still never appeared, bats-exec-file reporting its
    # run directory gone (`bats.<pid>.out: No such file or directory`: the leader's EXIT cleanup removes BATS_RUN_TMPDIR while the
    # test process is still in its exit trap). The reviewer ruled it carried here as an observation, not closed and given no
    # label: the marker assertion stands as written, _end_group's claim that a teardown runs under TERM holds under the condition
    # it was measured in (a CPU to run it), and the next red has this first sighting to compare against
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
        # process of the run is left. Two legs: the run on the main thread, whose _run_bats installs the handler for itself, and
        # the run on a worker thread under the main thread's _term_ends_live_runs block, the corpus's composition (BatsCorpus:
        # CORPUS_WORKERS candidates at a time), where the worker cannot install a handler and the main thread's ends its group
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        head = "import sys; sys.path.insert(0, %r)\nfrom tests.test_bats_bare_negation import run_test_alone, _term_ends_live_runs\n" % os.path.dirname(HERE)
        for leg in ("direct", "worker"):
            with tempfile.TemporaryDirectory() as d:
                tree = self.hanging_suite(d)
                call = "run_test_alone(%r, 'tests/hang.bats', 'poll', %r, timeout=60)" % (tree, d)
                code = head + ("print(%s.outcome)" % call if leg == "direct" else
                               "import concurrent.futures\nwith _term_ends_live_runs(), concurrent.futures.ThreadPoolExecutor(1) as pool:\n"
                               "    print(pool.submit(lambda: %s).result().outcome)" % call)
                p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    self.assertTrue(_within(30, lambda: _processes_of(d, ignore=(p.pid,))), "%s: the inner bats did not come up within 30 s" % leg)
                    p.send_signal(signal.SIGTERM)
                    out, err = p.communicate(timeout=30)
                finally:
                    if p.poll() is None:
                        p.kill()
                        p.communicate()
                self.assertEqual(p.returncode, -signal.SIGTERM, (leg, out, err))
                self.assertTrue(_within(10, lambda: not _processes_of(d)), "%s: processes of the run outlived the python that started it: %s" % (leg, _processes_of(d)))

    def test_a_here_document_the_negated_pipeline_introduces_never_runs_as_commands_under_a_rewrite(self):
        # regression-1, extra5-1 and tests-3 of fork PR #871's round 1: the extent ended at the introducer line, so the rewrite left
        # the body and its terminator in the file, where bats ran them as commands. Every form of negated_heredoc_shapes, its body
        # a touch of a marker under this test's directory: after the road decides each, no marker exists (the body was data under
        # both rewrites), the here-string's next line, a command, did run (its marker exists), another command's here-document
        # introduced on the same line reached that command (the kept file holds its body), and each verdict is the register's
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            tree = os.path.join(d, "tree")
            os.makedirs(os.path.join(tree, "tests"))
            name = '$(basename "$BATS_TEST_FILENAME" .bats)'
            shapes = negated_heredoc_shapes('touch "%s/marker-%s"' % (d, name), kept="kept line", command='touch "%s/ran-%s"' % (d, name),
                                            other='cat > "%s/kept-%s"' % (d, name))
            verdicts, expected = {}, {}
            for shape, text in sorted(shapes.items()):
                relpath = "tests/%s.bats" % shape
                with open(os.path.join(tree, relpath), "w", encoding="utf-8") as f:
                    f.write(text)
                lines = text.split("\n")
                extents = bash_test_extents(lines)
                found = candidates(lines, extents)
                self.assertEqual(len(found), 1, shape)
                verdicts[shape] = decide_under_bats(tree, relpath, lines, extents, found[0], d, timeout=20, repeats=1).verdict
                expected[shape] = "inert" if BatsGroundTruth.RECORDED[shape] == ("ok", "ok") else "read"
            made = sorted(n for n in os.listdir(d) if n.startswith(("marker-", "ran-", "kept-")))
            kept = {n: open(os.path.join(d, n), encoding="utf-8").read() for n in made if n.startswith("kept-")}
        self.assertEqual(verdicts, expected)
        self.assertEqual([n for n in made if n.startswith("marker-")], [], "a here-document body ran as a command under a rewrite")
        self.assertEqual([n for n in made if n.startswith("ran-")], ["ran-C_negated_heredoc_herestring_last", "ran-C_negated_heredoc_herestring_mid"])
        # another command's body before the pipeline's is untouched; one after it gains the empty lines that stand where the
        # pipeline's body and terminator were (the line count is kept, and those lines now precede the other body), the same two
        # lines under both rewrites, so the pair is still a differential of one word and any effect of them is symmetric
        self.assertEqual(kept, {"kept-C_negated_heredoc_others_first_%s" % pos: "kept line\n" for pos in ("last", "mid")} |
                         {"kept-C_negated_heredoc_others_after_%s" % pos: "\n\nkept line\n" for pos in ("last", "mid")})

    def test_a_child_of_the_test_holding_bats_output_open_does_not_time_out_a_run_whose_verdict_is_out(self):
        # extra6-1 of fork PR #871's round 1: the bound waited for EOF on bats's output pipes, and a test leaving `sleep 30 &` with
        # bats's fd 3 open was charged the sleep's lifetime and reported timed out with its verdict in the captured output. The
        # wait is on the process now, and a verdict already out is read VERDICT_GRACE seconds later: the run comes back `not ok`
        # on its line well inside the bound, and nothing of its group is left
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            tree = os.path.join(d, "tree")
            os.makedirs(os.path.join(tree, "tests"))
            with open(os.path.join(tree, "tests", "bg.bats"), "w", encoding="utf-8") as f:
                f.write('@test "bg" {\n    sleep 30 &\n    true\n    ! true\n}\n')
            t0 = time.monotonic()
            run = run_test_alone(tree, "tests/bg.bats", "bg", d, timeout=15)
            took = time.monotonic() - t0
            self.assertEqual((run.outcome, run.line, run.file), ("not ok", 4, "tests/bg.bats"), run.detail)
            self.assertLess(took, 15, "the run was charged the background child's lifetime")
            self.assertGreaterEqual(run.secs, VERDICT_GRACE)
            self.assertEqual(_processes_of(d), [], "processes of the ended run remain")

    def test_a_test_whose_runs_disagree_under_a_rewrite_is_undecided_and_never_read(self):
        # tests-2, regression-2 and extra4-3 of fork PR #871's round 1: decide read any differing pair, and a test failing
        # nondeterministically for a reason unrelated to its negation was read from noise, its inert negation silently exempted.
        # A test failing on every other run (a counter it keeps under this test's directory) around an inert `! true`: its runs
        # under the first rewrite disagree, the candidate is undecided, and the message names the disagreement
        if not shutil.which("bats"):
            self.skipTest(CORPUS_SKIP)
        with tempfile.TemporaryDirectory() as d:
            tree, counter = os.path.join(d, "tree"), os.path.join(d, "counter")
            os.makedirs(os.path.join(tree, "tests"))
            text = ('@test "alternating" {\n    n=$(cat "%s" 2>/dev/null || echo 0)\n    echo $((n + 1)) > "%s"\n    ! true\n'
                    '    [ $((n %% 2)) -eq 0 ]\n}\n' % (counter, counter))
            with open(os.path.join(tree, "tests", "flaky.bats"), "w", encoding="utf-8") as f:
                f.write(text)
            lines = text.split("\n")
            extents = bash_test_extents(lines)
            found = candidates(lines, extents)
            self.assertEqual([c.line + 1 for c in found], [4])
            decision = decide_under_bats(tree, "tests/flaky.bats", lines, extents, found[0], d, timeout=20)
            with open(counter, encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "%d" % (2 * REPEATS), "the test did not run REPEATS times per rewrite")
        self.assertEqual(decision.verdict, "undecided", decision.message)
        self.assertEqual([r.outcome for r in decision.runs], ["disagree", "disagree"])
        self.assertIn("under `! true` the test's 2 runs disagree (ok, then not ok @5): its outcome does not turn on this rewrite alone, so no "
                      "pair holding it is read as evidence; a failure nondeterministic for a reason unrelated to this negation is the usual "
                      "cause; nothing was decided", decision.message)
        self.assertIn("UNDECIDED", report(decision))

    def test_decide_under_bats_on_a_synthetic_suite_reads_a_last_negation_a_head_and_a_subshell_and_reports_the_rest(self):
        # the per-candidate road end to end on a tree of one suite: a mid-test `! true` is inert (ok under both) and its report
        # carries the message, the rewritten lines and both outcomes; a last `! true` is read (not ok on its line under `! true`);
        # a condition head whose branch returns 1 is read the other way round (not ok on its line under `! false`); a mid-test
        # negation followed by a failing command is undecided, both rewrites failing on the later line; a `( ! true )` subshell on
        # its own line is read, its failure blamed on the line before it (F1 of the commit-3 review: undecided before); a status
        # saved with `SAVED_RC=$?` and read by the teardown is undecided, the failure blamed outside the test, and the message says
        # so; a poll loop whose condition is the negation is undecided, its `! false` run ended at the bound (3 s here), and the
        # message says so (F2); a test declared `comment_form() { # @test` goes down the same road, its name matched by bats's `-f`
        # (tests-1: no such test before, when the module opened on the `@test` form alone); a helper ending in `! true` called by a
        # bare `! _h` is two candidates, each read (correctness-4 of round 1: the oracle's answer at the site fork PR #778's Scanner
        # mis-classified, recorded here); a negated brace group whose line holds `;` operators is followed to its close, since bash
        # reads none of them as the pipeline's end, and decided like any other (inert here; before fork PR #871's round 2, second commit, the extent
        # ended at the first `;`, the rewritten file did not parse, and the candidate was undecided)
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
                'comment_form() { # @test\n    ! true\n    true\n}\n'
                '@test "bang helper" {\n    _h() {\n        run true\n        ! true\n    }\n    ! _h\n}\n'
                '@test "group" {\n    ! { true; false; }\n    true\n}\n')
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tree", "tests"))
            with open(os.path.join(d, "tree", "tests", "one.bats"), "w", encoding="utf-8") as f:
                f.write(text)
            lines = text.split("\n")
            extents = bash_test_extents(lines)
            found = candidates(lines, extents)
            self.assertEqual([c.line + 1 for c in found], [2, 7, 10, 14, 19, 23, 28, 34, 40, 42, 45])
            decisions = [decide_under_bats(os.path.join(d, "tree"), "tests/one.bats", lines, extents, c, d, timeout=3) for c in found]
        self.assertEqual([(x.test, x.verdict) for x in decisions],
                         [("mid", "inert"), ("last", "read"), ("head", "read"), ("later failure", "undecided"), ("subshell", "read"),
                          ("read in teardown", "undecided"), ("poll", "undecided"), ("comment_form", "inert"), ("bang helper", "read"),
                          ("bang helper", "read"), ("group", "inert")])
        self.assertEqual([(r.outcome, r.line) for r in decisions[8].runs], [("ok", None), ("not ok", 40)])   # bats blames the helper's line, the last it ran
        self.assertEqual([(r.outcome, r.line) for r in decisions[9].runs], [("not ok", 42), ("ok", None)])
        self.assertEqual([s.strip() for s in decisions[10].rewritten], ["! true", "! false"])   # the whole group replaced
        self.assertEqual([(r.outcome, r.line) for r in decisions[10].runs], [("ok", None), ("ok", None)])
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
        self.assertTrue(3 * REPEATS <= decisions[6].runs[1].secs < 15 * REPEATS, decisions[6].runs[1].secs)   # the side's runs, summed
        self.assertIn("under `! false` bats gave no verdict on the test: the side's %d runs were each ended at the bound, %.0f s together, with no verdict"
                      % (REPEATS, decisions[6].runs[1].secs), decisions[6].message)   # the count and the total, not the total as one run's
        self.assertEqual(decisions[6].runs[1].runs, REPEATS)
        self.assertIn("under `! false`: while ! false; do sleep 0.1; done  ->  timed out", report(decisions[6]))
        text = report(decisions[0])
        self.assertIn("tests/one.bats:2 in test 'mid': INERT: the test passes with the negated command succeeding and with it failing", text)
        self.assertIn("under `! true`: ! true  ->  ok", text)
        self.assertIn("under `! false`: ! false  ->  ok", text)
        self.assertIn("bats under `! false` said:", text)


if __name__ == "__main__":
    unittest.main()
