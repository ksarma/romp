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
tests/*.bats and names each inert site, a second suite test asserts how much the scan read against
bash's own parse, the Scanner tests pin the scanner on synthetic snippets, and the BatsGroundTruth
register runs a corpus of shapes under bats itself and requires the scanner to agree with it.

The checked form is `run <cmd>` followed by `[ "$status" -ne 0 ]` (tests/romp-postal.bats and
tests/git-hermetic.bats write it inline; the `log_lacks` helper that wrapped it left with
tests/romp-manager-tmux-scope.bats when the tmux backend was removed, 2532d6d8 on 2026-09-11), a count for a pipeline (`[ "$(grep -c x "$LOG")" -eq 0 ]`),
or `run ! <cmd>` in a file that declares `bats_require_minimum_version 1.5.0`. `run` overwrites $status and
$output, so an armed negation goes after any `[[ "$output" ... ]]` check that reads the previous run.

Scope: a line scan, not a bash parser. A block opens at a line bats-preprocess rewrites into a test
function (its BATS_TEST_PATTERN: optional leading blanks, `@test`, the name, blanks, `{`, anything
after; the round-8 addendum of fork PR #778 took bats's own pattern over a column-zero `@test ... {`
ending in the brace, which had left an indented opener, one with a trailing comment or a trailing
command, and a one-line test outside both the scan and the coverage pin while bats ran them) and
ends at the `}` line that returns the brace depth to zero, whatever its indentation or trailing
text (a command line ending in `{` opens a level, one beginning with `}` closes one; heredoc bodies,
blank lines and comment lines count for nothing; a one-line test closes on its own line). Inside a
block it reads every line that begins with `! ` and reports one whose next command line is not a
position whose status bash reads. A line that carries a `;` and another command, or a trailing
`&`, after the `!` is reported wherever it sits (the line's last command is not the negation; the
negation runs in the background); one that carries `||` is decided by its fallback: `false`,
`return` or `exit` with no argument or a nonzero one fail the test wherever the line sits (an armed
check, never reported), and any other fallback's status is unknown to this scan and taken as the
list's own 0 (reported wherever the line sits: `! cmd || echo` asserts nothing). The read
positions, each run under bats (the register below): the test's own closing brace (the test's
return value); a function's closing brace, its opener found by brace depth over the command lines
before it (`name() {` in any spelling bash accepts, with or without a trailing comment, or an
Allman `{` under a `name()` line) when the function is CALLED where its status is read (a plain
call, alone on its line or under `&&` or `;`, the caller's errexit reading it; a plain assignment's
`x=$(name)`; `run name` followed by a line reading `$status`), since a helper called under `if`,
`while`, `!`, `||`, a pipe, `&`, `echo $(...)` or not at all has its status discarded; a brace
group's closing brace, an `if`'s `fi` (an `else` or `elif` before that `fi`), a loop's `done` and a
`case`'s `esac` (a `;;` before it) exactly where that close is itself in a read position, so a
compound that is the test's, a helper's or a subshell's last command is read and one followed by
another command, or by `; <command>` on its own line, is not; a subshell's `)` unless what follows
it discards the status; and a command substitution's `)` only under a plain assignment (`out="$(`),
since `echo "$(...)"` discards the status and `local out="$(...)"` returns local's own 0. What
follows a `)`, a `}` or a compound's close decides with redirections read past: `|`, `|&`, `||` and
a trailing `&` discard the status; `&&` hands it to a list whose status is read exactly where the
line is in a read position, unless a `||` or a trailing `&` follows the `&&` (`) && true` as the
test's last command is read, `) && true || echo` is not). A heredoc's body is text and is skipped:
an introducer is a `<<` outside quotes, outside a comment and outside `((...))`, its delimiter any
word bash accepts in any quoting (`EOF`, `'EOF'`, `"EOF"`, `\EOF`, `E\OF`, `"EO"F`, `$'EOF'`,
`EOF-1`), two on one line skipped in order, to the line that is the word (tabs stripped for `<<-`);
a heredoc whose terminator line never comes, or comes after the next `@test` line, is not skipped,
so a skip cannot cross a test and the body is scanned as commands instead. It does not see `!cmd`
written without a space, a `! cmd` on a test's opener line or inside a one-line test, a bare `!`
inside setup(), teardown() or a file-scope helper function (also under errexit), a bare `!` on its
own line inside a multi-line `if` or `while` condition (reported, since the position after it is
`then` or `do`), a line inside a quoted string that began on an earlier line (read as a command, or
as an introducer, or as the test's close when it is a column-zero `}`), or a command line ending in
a literal `{` that opens no group (`printf x {`), which opens a level the block never closes. Each
of those last shapes the coverage pin below makes visible rather than silent.

The coverage pin (round 8, correctness-1: until it existed the CI check asserted nothing about how
much it scanned, so a scan that had lost half a file read as a clean one, and a "blind region 0"
was a number with no pin behind it). Per file, bash's own parse is the derivation, not this
module's rules: every line matching bats-preprocess's test pattern is rewritten into a function
opener as it does, and `bash -n` over prefixes of the file finds each test's extent (an opener
counts when the lines before it parse whole; its close is its own line when the rewritten line
parses whole, a one-line test, else the first `}` line at which the function parses whole) and
checks each heredoc skip taken inside a test (a prefix cut at the introducer must leave bash inside
a here-document, one cut at the terminator must not). The walk's blocks must equal those extents,
no `@test` open may be met while a block is open, and the in-test lines scanned (commands plus
heredoc text) must equal the lines between each test's open and its close. The pin's own cost is
one `bash -n` per test plus one per candidate close and two per in-test heredoc, a few seconds
over the 45 files here (the module's run prints the time); nothing is executed. A `@test` line
inside a heredoc or a string is a test to bats-preprocess too (it rewrites every matching line,
wherever it sits: a fixture written through such a heredoc reaches the disk rewritten and the file
declares one test more than it runs), so the pin's message for such a line says to write it
through printf.

Measured over the 45 tests/*.bats at the round-7 head (938 tests, 14206 in-test lines by bash's
parse), the two roads round 7's ruling left open, both with the helpers of the byte-order-mark case
at file scope: round 6's rule (a block ends at any line stripping to `}`, no heredoc skip) scanned
14019 lines, 187 outside the scan in 10 blocks ended early (tests/install-sh.bats 80,
tests/romp-uninstall.bats 49, tests/install-sh-coexist.bats 35, tests/romp-service.bats 23), 0
reports; round 7's rule scanned all 14206, 0 reports; the round-8 rule scanned all 14206, 0
reports, and the pin held on every file. The fix road was taken on those numbers: the revert would
have reopened 187 lines today and the class for the next nested helper. The round-8 rule then
disagreed with bats on 30 of the 165 shapes an independent lens ran (12 positions bats reads that
it reported: a bare `!` before `fi`, `else`, `done`, `;;` or `esac` when the compound is the test's
last command, `) && true` and `} && true` as the last command, a helper named with a hyphen or
spelled `_h ( ) {`; 18 it missed: a redirection before the operator, `} ; true`, `echo $(...)`
unquoted, `! cmd || fallback` as the last line, a helper called under `if`, `|| true` or never, the
openers above), none live in the repo; this addendum's rule agrees with bats on every shape of the
register below, and the register is the pin on that claim.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))

_BARE = re.compile(r"^\s*!\s")
_BLANK_OR_COMMENT = re.compile(r"^\s*(#.*)?$")
# bats-preprocess's BATS_TEST_PATTERN (bats-core 1.10 and 1.11, /usr/libexec/bats-core/bats-preprocess line 34): the lines it rewrites
# into functions before bash parses the file. group(1) the name, group(2) whatever follows the brace (a comment, a command, a
# one-line body). The walk opens a block on the same lines (round 8 addendum, F4 of the scanner lens)
_TEST_LINE = re.compile(r"^[ \t]*@test[ \t]+(.*[^ \t])[ \t]+\{(.*)$")
# a function's name: any word bash accepts (`my-helper`, `a.b`; round 8 addendum, F8: the letters-and-underscores class refused two
# openers bash runs, and the brace was then read as a group's)
_NAME = r"[^\s$'\"`;&|<>(){}=#]+"
# a function's opening line, the closing brace that exempts a bare `!` before it: `name() {`, `name ( ) {`, `function name() {`,
# `function name {`, each with or without a trailing comment (round 8, tests-2: the opener of the one multi-line helper defined inside
# a test in this repo carries one). `name {` alone is a command with an argument, not a function
_FUNC_OPEN = re.compile(r"^\s*(?:function\s+(?P<n1>%s)\s*(?:\(\s*\))?|(?P<n2>%s)\s*\(\s*\))\s*\{\s*(#.*)?$" % (_NAME, _NAME))
# the line before an Allman-style `{`: `name()` or `function name`, the function's name on its own line
_FUNC_NAME_LINE = re.compile(r"^\s*(?:function\s+(?P<n1>%s)\s*(?:\(\s*\))?|(?P<n2>%s)\s*\(\s*\))\s*$" % (_NAME, _NAME))
# an assignment taking a command substitution's status: `name="$(`, `name=$(`, `arr[k]+="$(`; `local`, `declare`, `export`, `readonly`
# and `typeset` before the name return their own status, 0, so a substitution under them is NOT read (round 8, tests-1's refuter)
_ASSIGN_PREFIX = r"[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?\+?=[\"']?"
_ASSIGN_SUBST = re.compile(r"^\s*" + _ASSIGN_PREFIX + r"\$\($")
# one redirection at the start of a trailer: `> f`, `>>f`, `2>&1`, `&>/dev/null`, `<f`, `>|f`, `<>f`, the target a word or a quoted string
_REDIR = re.compile(r"""^\s*(?:&>>?|[0-9]*(?:>>|>\||>&|<&|<>|>|<))\s*(?:"[^"]*"|'[^']*'|[^\s;&|<>]+)""")
_CLOSE_CANDIDATE = re.compile(r"^\s*\}")
_COMPOUND_CLOSE = re.compile(r"(fi|done|esac)(?![\w-])")
_BRANCH = re.compile(r"(else|elif)(?![\w-])")
# a `{` or `}` standing as its own word in a line's trailing text (the text after a test opener's brace)
_BRACE_WORD = re.compile(r"(?:^|(?<=[\s;]))([{}])(?=[\s;]|$)")


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
    character quotes the word (`<<'EOF'`, `<<"EOF"`, `<<\EOF`, `<<E\OF`, `<<"EO"F`, `<<$'EOF'`, `<<$"EOF"`: the `$` of an ANSI-C or
    locale quoting is part of the quote, not of the word; round 8 addendum, the walk took `$EOF` for the word and would have ended
    the skip at a body line `$EOF` while bash read on to `EOF`); the word ends at an unquoted blank or metacharacter, so `<<EOF-1` is
    the whole token EOF-1 and not a prefix of it."""
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
        elif ch == "$" and j + 1 < n and line[j + 1] in "'\"":
            q = line[j + 1]
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


def _top_level_ops(code):
    """[(operator, index)] for every control operator in the code outside quotes and outside parentheses, in order: `;;`, `;`, `||`,
    `|&`, `|`, `&&`, `&` (a redirection's `&`, as in `2>&1` or `&>f`, is not one)."""
    out, q, depth, i, n = [], None, 0, 0, len(code)
    while i < n:
        ch = code[i]
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
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and ch == ";":
            if code.startswith(";;", i):
                out.append((";;", i))
                i += 1
            else:
                out.append((";", i))
        elif depth == 0 and ch == "|":
            if code.startswith("||", i):
                out.append(("||", i))
                i += 1
            elif code.startswith("|&", i):
                out.append(("|&", i))
                i += 1
            else:
                out.append(("|", i))
        elif depth == 0 and ch == "&":
            if code.startswith("&&", i):
                out.append(("&&", i))
                i += 1
            elif i + 1 < n and code[i + 1] == ">":
                i += 1   # `&>`: a redirection
            elif i > 0 and code[i - 1] in "<>":
                pass   # `>&`, `<&`: a redirection
            else:
                out.append(("&", i))
        i += 1
    return out


def _strip_redirections(rest):
    """The trailer with every leading redirection removed (`) 2>&1 | cat` decides on `| cat`; round 8 addendum, F3: the operator was
    matched at the start of the trailer alone, so a redirection before it hid it)."""
    while True:
        m = _REDIR.match(rest)
        if not m:
            return rest.strip()
        rest = rest[m.end():]


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
            if _TEST_LINE.match(lines[j]):
                return i + 1
            if (lines[j].lstrip("\t") if dash else lines[j]) == word:
                break
            j += 1
        else:
            return i + 1
        j += 1
    return j


def _command_lines_backward(lines, k, heredoc_body, stop=0):
    """The indices of the command lines before k, nearest first, down to stop: heredoc text, blank and comment lines skipped."""
    for m in range(k - 1, stop - 1, -1):
        if m in heredoc_body or _BLANK_OR_COMMENT.match(lines[m]):
            continue
        yield m


def _command_lines_forward(lines, start, end, heredoc_body):
    """The indices of the command lines from start up to end (exclusive), in order: heredoc text, blank and comment lines skipped."""
    for m in range(start, min(end, len(lines))):
        if m in heredoc_body or _BLANK_OR_COMMENT.match(lines[m]):
            continue
        yield m


def _next_command_line(lines, start, heredoc_body):
    """The index of the first command line at or after start, or len(lines)."""
    for m in _command_lines_forward(lines, start, len(lines), heredoc_body):
        return m
    return len(lines)


def _opens(line):
    """How many brace levels the line opens: a test opener's brace plus the brace words in its trailing text (a one-line test opens
    none on balance), else one for a command line ending in `{`."""
    m = _TEST_LINE.match(line)
    if m:
        return max(0, 1 + sum(1 if w == "{" else -1 for w in _BRACE_WORD.findall(_code_part(m.group(2)))))
    return 1 if _code_part(line).endswith("{") else 0


def _brace_opener(lines, j, heredoc_body, block):
    """The index of the line whose `{` the `}` at lines[j] closes, by brace depth over the command lines before it within the block (a
    line ending in `{` or a test opener opens a level, one beginning with `}` closes one; heredoc bodies are text); None when no
    opener is found."""
    depth = 0
    for k in _command_lines_backward(lines, j, heredoc_body, block[0]):
        if _opens(lines[k]):
            if depth == 0:
                return k
            depth -= 1
        if _code_part(lines[k]).lstrip().startswith("}"):
            depth += 1
    return None


def _paren_opener(lines, j, heredoc_body, block):
    """The index of the line whose `(` the `)` at lines[j] closes, by paren depth over the earlier command lines; None when none."""
    depth = 0
    for k in _command_lines_backward(lines, j, heredoc_body, block[0]):
        code = _code_part(lines[k])
        if code.endswith("("):
            if depth == 0:
                return k
            depth -= 1
        if code.lstrip().startswith(")"):
            depth += 1
    return None


def _function_name(lines, k, heredoc_body, block):
    """The name of the FUNCTION whose opener is at lines[k] (`name() {` in any spelling, or an Allman `{` under a `name()` line), or
    None when the line opens a group."""
    m = _FUNC_OPEN.match(lines[k])
    if m:
        return m.group("n1") or m.group("n2")
    if _code_part(lines[k]).strip() == "{":
        for p in _command_lines_backward(lines, k, heredoc_body, block[0]):
            m = _FUNC_NAME_LINE.match(_code_part(lines[p]))
            return (m.group("n1") or m.group("n2")) if m else None
    return None


def _plain_call(lines, idx, name, heredoc_body, block):
    """Whether the command line at idx calls the function `name` where bash reads its status: a plain call as the line's first word
    (after `{` or `(` openers), with no `||`, pipe or trailing `&` on the line (`&&` and `;` leave it read: the list short-circuits
    on it, errexit reads it); a plain assignment's `x=$(name ...)`; or `run name` followed by a command line that reads `$status`."""
    code = _code_part(lines[idx]).strip()
    esc = re.escape(name)
    if re.match(r"^(?:[{(]\s+)*" + esc + r"(?=[\s;]|$)", code):
        ops = _top_level_ops(code)
        if any(op == "||" for op, _ in ops):
            return _fallback_fails(code[[i for op, i in ops if op == "||"][-1] + 2:])
        return not any(op in ("|", "|&") for op, _ in ops) and not (ops and ops[-1][0] == "&" and code.endswith("&"))
    if re.match(r"^" + _ASSIGN_PREFIX + r"\$\(\s*" + esc + r"(?=[\s)])", code):
        return True
    if re.match(r"^run\s+" + esc + r"(?=[\s;]|$)", code):
        nxt = _next_command_line(lines, idx + 1, heredoc_body)
        return nxt < block[1] and "$status" in lines[nxt]
    return False


def _helper_read(lines, k, j, heredoc_body, block):
    """Whether the function opened at lines[k] and closed at lines[j] is called, later in the block, where its status is read (round 8
    addendum, F9: the round-8 rule exempted a helper's last command on the premise of a plain call under errexit; a helper called under
    `if`, as `_h || true`, or never, has that command's status discarded, and bats says so)."""
    name = _function_name(lines, k, heredoc_body, block)
    if name is None:
        return False
    return any(_plain_call(lines, m, name, heredoc_body, block) for m in _command_lines_forward(lines, j + 1, block[1], heredoc_body))


def _matching_close(lines, j, opener, closer, heredoc_body, block):
    """The index of the line closing the compound that lines[j] (an `else`, `elif` or `;;`) belongs to: the first command line after j
    whose code begins a segment with the closer word (`fi` or `esac`) at depth zero, depth counted over segments (the code split at its
    control operators) whose first word is the opener (`if`, `case`) or the closer, so a one-line `if ...; fi` nets to zero. None
    when the block ends first."""
    depth = 0
    for m in _command_lines_forward(lines, j + 1, block[1], heredoc_body):
        code = _code_part(lines[m])
        cuts = [0] + [i + len(op) for op, i in _top_level_ops(code)]
        for seg in (code[a:b] for a, b in zip(cuts, cuts[1:] + [len(code)])):
            words = seg.replace(";", " ").split()
            while words and words[0] in ("then", "do", "else", "!", "{", "(", "time"):
                words.pop(0)
            if not words:
                continue
            if words[0] == opener:
                depth += 1
            elif words[0] == closer:
                if depth == 0:
                    return m
                depth -= 1
    return None


def _trailer(lines, j, rest, heredoc_body, block, brace):
    """What the text after a `)`, a `}` or a compound's close on lines[j] does with its status: False when it discards it (`|`, `|&`,
    a trailing `&`; `||` with a fallback whose status is not known to fail; `&&` followed by such a `||` or by a trailing `&`; for a
    `}` or a compound's close, `; <command>` on the same line, which bats runs on past); True when it is read (`|| false`, `||
    return 1`: the fallback fails the test; an `&&` list whose line is itself in a read position); None when the trailer decides
    nothing (empty, `;`, redirections alone, `; <command>` after a subshell's `)`, which errexit reads) and the closer's own rule
    applies. Redirections before the operator are read past (round 8 addendum, F2, F3, F6)."""
    rest = _strip_redirections(rest)
    if rest in ("", ";"):
        return None
    if rest.startswith("||"):
        return True if _fallback_fails(rest[2:]) else False
    if rest.startswith(("|&", "|")) or rest == "&":
        return False
    if rest.startswith("&&"):
        after = rest[2:]
        ops = _top_level_ops(after)
        ors = [i for op, i in ops if op == "||"]
        if ors:
            return True if _fallback_fails(after[ors[-1] + 2:]) else False
        if ops and ops[-1][0] == "&" and after.rstrip().endswith("&"):
            return False
        return _read_position(lines, j, _next_command_line(lines, j + 1, heredoc_body), heredoc_body, block)
    if rest.startswith(";"):
        return False if brace and rest[1:].strip() else None
    return None


def _read_position(lines, i, j, heredoc_body, block):
    """Whether lines[j], the first command line after the bare `!` at lines[i], puts that `!` where bash reads its status. A `)`: a
    subshell's end, read unless what follows the paren discards it (round 8, tests-1 and correctness-4), or a command substitution's
    end (its opener ends in `$(`, quoted or not; round 8 addendum, F5), read only when the opener is a plain assignment (`out="$(`),
    since `echo "$(...)"` discards it and `local out="$(...)"` returns local's 0. A `}`: what it closes decides, found by brace depth
    over the command lines before it, heredoc bodies skipped (round 8, regression-2): the test's own opener (the test's return value,
    at any indentation; round 8, extra6-1), a function's opener (read where the function is called in a read position, _helper_read;
    a trailing comment on the opener and the Allman `{` under a `name()` line count), or a brace group's, whose status is read
    exactly where the group's own `}` is in a read position, so the question is asked again of the line after it (round 8, extra6-2:
    a group that is the test's, a helper's or a subshell's last command is read; one followed by another command is not). A `fi`, a
    `done` or an `esac`: the compound's close, read exactly where that close is in a read position, asked the same way (round 8
    addendum, F1); an `else` or `elif`, or a `;;`: the compound's close is found forward and the question asked of it. A close
    followed by a status-discarding trailer is not a read position whatever it closes (_trailer)."""
    if j >= len(lines):
        return False
    stripped = _code_part(lines[j]).strip()
    if stripped.startswith(")"):
        rest = stripped[1:]
        if rest[:1] in ('"', "'"):
            rest = rest[1:]
        t = _trailer(lines, j, rest, heredoc_body, block, False)
        if t is not None:
            return t
        k = _paren_opener(lines, j, heredoc_body, block)
        if k is None:
            return True
        opener = _code_part(lines[k])
        if opener.endswith("$("):
            return bool(_ASSIGN_SUBST.match(opener))
        return True
    if stripped.startswith("}"):
        t = _trailer(lines, j, stripped[1:], heredoc_body, block, True)
        if t is not None:
            return t
        k = _brace_opener(lines, j, heredoc_body, block)
        if k is None:
            return False
        if _TEST_LINE.match(lines[k]):
            return True
        if _function_name(lines, k, heredoc_body, block) is not None:
            return _helper_read(lines, k, j, heredoc_body, block)
        return _read_position(lines, j, _next_command_line(lines, j + 1, heredoc_body), heredoc_body, block)
    m = _COMPOUND_CLOSE.match(stripped)
    if m:
        t = _trailer(lines, j, stripped[m.end():], heredoc_body, block, True)
        if t is not None:
            return t
        return _read_position(lines, j, _next_command_line(lines, j + 1, heredoc_body), heredoc_body, block)
    if _BRANCH.match(stripped):
        c = _matching_close(lines, j, "if", "fi", heredoc_body, block)
        return c is not None and _read_position(lines, i, c, heredoc_body, block)
    if stripped.startswith(";;"):
        c = _matching_close(lines, j, "case", "esac", heredoc_body, block)
        return c is not None and _read_position(lines, i, c, heredoc_body, block)
    return False


def _fallback_fails(text):
    """Whether the command after a `||` fails whenever it runs, so the list's status is read wherever the line sits: `false`, or
    `return` or `exit` with no argument (the failing negation's own status) or a nonzero literal one; a `{ ...; }` group by its last
    command. Any other fallback (`true`, `echo`, a function, `return "$rc"`) has a status this scan does not know and is taken as
    discarding, the visible side: `! cmd || echo` asserts nothing, and a fallback that does fail is written as `run` + status."""
    t = text.strip()
    if t.startswith("{"):
        inner = t[1:].strip()
        inner = inner[:-1] if inner.endswith("}") else inner
        segs = [seg for seg in re.split(r";", inner) if seg.strip()]
        t = segs[-1].strip() if segs else ""
    ops = _top_level_ops(t)
    if ops:
        t = t[:ops[0][1]].strip()
    words = t.split()
    if not words:
        return False
    if words[0] == "false":
        return True
    if words[0] in ("return", "exit"):
        return len(words) == 1 or (words[1].isdigit() and int(words[1]) != 0)
    return False


def _negation_line_verdict(line):
    """What the bare `!` line does with the negation's status on its own, before the position after it is asked: "read" when a `||`
    fallback fails whenever it runs (`! cmd || return 1` is an armed check wherever it sits); "discards" when a `||` fallback does
    not (the list returns the fallback's status), when a `;` is followed by another command (the line's last command is not the
    negation) or when a trailing `&` backgrounds it; None otherwise, the position rule deciding (round 8 addendum, F7 and the
    register: `! cmd || echo` and `! cmd &` as the test's last line pass under bats with the negated command succeeding)."""
    code = _code_part(line)
    ops = _top_level_ops(code)
    ors = [i for op, i in ops if op == "||"]
    if ors:
        return "read" if _fallback_fails(code[ors[-1] + 2:]) else "discards"
    for op, idx in ops:
        if op == ";" and code[idx + 1:].strip():
            return "discards"
    if ops and ops[-1][0] == "&" and code.rstrip().endswith("&"):
        return "discards"
    return None


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
    """The walk: a Scan of the text. Inside a block (opened at a line bats-preprocess rewrites into a test function) the block ends at
    the `}` line that returns the brace depth to zero, whatever its indentation or trailing text (a command line ending in `{` opens a
    level, one beginning with `}` closes one; heredoc bodies, blank and comment lines count for nothing; a one-line test closes on its
    own line). A bare `!` is decided when its block closes, with the block's extent known (_read_position reads forward to the
    block's end for a helper's call sites): it is a hit unless its next command line is a position whose status bash reads, and a
    hit whatever follows when its own line discards the status, and no hit when its own line reads it (_negation_line_verdict); a heredoc's body is skipped
    (_after_heredoc). A `@test` open met while a block is open ends that block there (recorded as unclosed) and opens the next."""
    lines = text.split("\n")
    s = Scan()
    in_test, open_idx, depth, pending = False, None, 0, []

    def close_block(c, end):
        s.blocks.append((open_idx, c))
        for bang, j in pending:
            v = _negation_line_verdict(lines[bang])
            if v == "discards" or (v is None and not _read_position(lines, bang, j, s.heredoc_body, (open_idx, end))):
                s.hits.append((bang + 1, lines[bang].rstrip()))

    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = _after_heredoc(lines, i)
        if nxt > i + 1:
            s.heredoc_body.update(range(i + 1, nxt))
        if _TEST_LINE.match(line):
            if in_test:
                s.reopened.append(i)
                close_block(None, i)
            in_test, open_idx, depth, pending = True, i, _opens(line), []
            if depth == 0:
                close_block(i, i + 1)
                in_test = False
        elif in_test and not _BLANK_OR_COMMENT.match(line):
            code = _code_part(line)
            if code.lstrip().startswith("}"):
                depth -= 1
            if depth == 0:
                close_block(i, i)
                in_test = False
            else:
                depth += _opens(line)
                if _BARE.match(line):
                    pending.append((i, _next_command_line(lines, nxt, s.heredoc_body)))
        if in_test and i != open_idx:
            s.command_lines += 1
            s.heredoc_lines += nxt - i - 1
            if nxt > i + 1:
                s.heredoc_skips.append((i, nxt))
        i = nxt
    if in_test:
        close_block(None, len(lines))
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
    """(open index, close index) for every test bash parses, from bash's own parse and not from this module's rules: every line
    matching bats-preprocess's test pattern is rewritten into a function opener the way it does, an opener counts when the lines
    before it parse as a complete script (so one inside a heredoc, a quoted string or another test does not; the lines are read from
    the last point known to parse whole, the previous test's close, which is the same test by induction), and its close is its own
    line when the rewritten line parses whole on its own (a one-line test; round 8 addendum, F4: keyed on the walk's narrower
    opener, the pin had no extent for an indented opener, one with trailing text or a one-line test, and was silent while bats ran
    them), else the first later line beginning with `}` at which the opener and the lines between parse as a complete function.
    None for the close: no such line (the file does not parse under this bash). One `bash -n` per opener plus one per candidate
    close, no execution."""
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


def _in_test_lines(extents):
    return sum(max(0, c - o - 1) for o, c in extents if c is not None)


FIXTURE_LINE_REMEDY = ("bats-preprocess rewrites every line matching its test pattern wherever it sits, a heredoc or a string included, "
                       "so a fixture cannot carry such a line literally (it reaches the disk rewritten and the file declares a test it "
                       "never runs); write it through printf, or begin the line with something other than @test")


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
                            % (name, o + 1, max(0, c - o - 1)))
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
                            "string or another test); %s" % (name, o + 1, FIXTURE_LINE_REMEDY))
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
    expected = _in_test_lines(extents)
    scanned = s.command_lines + s.heredoc_lines
    if scanned != expected:
        problems.append("%s: in-test lines: %d by bash's parse, %d scanned (%d command lines, %d heredoc text lines)"
                        % (name, expected, scanned, s.command_lines, s.heredoc_lines))
    return problems


def coverage_report(name, s, extents):
    return "%s: %d tests, %d in-test lines by bash's parse, %d scanned (%d command lines, %d heredoc text lines)" % (
        name, len(extents), _in_test_lines(extents), s.command_lines + s.heredoc_lines, s.command_lines, s.heredoc_lines)


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
        problems, report, tests, lines_total, scanned_total = [], [], 0, 0, 0
        t0 = time.monotonic()
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".bats"):
                continue
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                lines = f.read().split("\n")
            s, extents = scan("\n".join(lines)), bash_test_extents(lines)
            self.assertTrue(extents or not any(_TEST_LINE.match(l) for l in lines),
                            "%s: @test lines but no extent derived: the file does not parse under bash -n" % name)
            problems += coverage_problems(name, lines, s, extents)
            report.append(coverage_report(name, s, extents))
            tests, lines_total, scanned_total = tests + len(extents), lines_total + _in_test_lines(extents), scanned_total + s.command_lines + s.heredoc_lines
        report.append("%d files: %d tests, %d in-test lines by bash's parse, %d scanned, in %.2f s"
                      % (len(report), tests, lines_total, scanned_total, time.monotonic() - t0))
        print("\n".join(report))
        self.assertEqual(problems, [], "in-test lines outside the bare-negation scan, or file-scope lines inside it:\n"
                         + "\n".join(problems) + "\n\n" + "\n".join(report))


class Scanner(unittest.TestCase):
    """The scanner itself, on synthetic snippets: it flags exactly the form bats cannot see. Every shape below was run under bats
    1.10.0 with the negated command succeeding (round 8 of fork PR #778 and its addendum; the register in BatsGroundTruth runs the
    families under bats in the suite): `ok` means the position asserts nothing and the scanner must report it, `not ok` means bats
    checked it and the scanner must not. `# red before:` names the earlier module's answer."""

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
            "a group under && as the test's last command": '@test "M" {\n    {\n        true\n        %s\n    } && true\n}\n',
        }
        for what, shape in shapes.items():
            self.assertExempt(shape % self.NEG, what)
        # and a group whose status goes elsewhere is reported (bats: ok for each)
        self.assertReported('@test "G" {\n    _h() {\n        {\n            true\n            %s\n        }\n        true\n    }\n    _h\n}\n' % self.NEG)
        self.assertReported('@test "J" {\n    {\n        true\n        %s\n    } || true\n    true\n}\n' % self.NEG)
        # round 8 addendum (F6, F3): a command after the brace on the SAME line is run on past the group (bats: ok), and a redirection
        # before the operator does not hide it; red before: both exempt (the recursion asked the question of the next LINE, and the
        # operator was matched at the start of the trailer alone)
        self.assertReported('@test "N" {\n    {\n        true\n        %s\n    } ; true\n}\n' % self.NEG)
        self.assertReported('@test "O" {\n    {\n        true\n        %s\n    } 2>&1 | cat\n}\n' % self.NEG)
        self.assertReported('@test "P" {\n    {\n        true\n        %s\n    } >/dev/null || true\n}\n' % self.NEG)

    def test_a_subshell_or_a_substitution_is_read_unless_what_follows_the_paren_discards_it(self):
        # round 8 (tests-1, correctness-4): red before, the round-7 rule exempted every `)`. bats: not ok for the read shapes
        sub = '@test "x" {\n    (\n        run true\n        %s\n    )%s\n    true\n}\n'
        for closer in ("", " > /dev/null", ";", " 2>&1", " &>/dev/null", " ; true"):
            self.assertExempt(sub % (self.NEG, closer), repr(closer))
        # bats: ok for the discarding shapes (no pipefail in a bats test; a list hands the status on; `&` backgrounds)
        for closer in (" | cat", " || true", " && echo yes", " &\n    wait"):
            self.assertReported(sub % (self.NEG, closer), repr(closer))
        # round 8 addendum (F3): a redirection before the operator does not hide it (bats: ok; red before: exempt, the operator matched
        # at the start of the trailer alone, where the docstring said `|`, `||` and `&&` after a `)` were caught)
        for closer in (" 2>&1 | cat", " > /dev/null || true", " >/dev/null && true"):
            self.assertReported(sub % (self.NEG, closer), repr(closer))
        # round 8 addendum (F2, the tests-1 refuter's note the builder had left): `) && true` as the test's LAST command is read, the
        # list's status being the test's return (bats: not ok); mid-test it is not; `) && true || echo` is the fallback's 0 (bats: ok)
        # red before: the last shape reported
        last = '@test "x" {\n    (\n        run true\n        %s\n    )%s\n}\n'
        self.assertExempt(last % (self.NEG, " && true"))
        self.assertExempt(last % (self.NEG, " && true && true"))
        self.assertExempt(last % (self.NEG, " && true | cat"), "the pipeline is the && list's right operand; the subshell's failure short-circuits it")
        self.assertReported(sub % (self.NEG, " && true"))
        self.assertReported(last % (self.NEG, " && true || echo fb"))
        # a command substitution: read by a plain assignment, discarded by echo and by `local` (which returns its own 0); round 8
        # addendum (F5): the unquoted `)` of `echo $(` is a substitution's end too, found at its opener (red before: exempt as a
        # subshell's end)
        self.assertExempt('@test "x" {\n    out="$(\n        %s\n    )"\n    true\n}\n' % self.NEG)
        self.assertExempt('@test "x" {\n    out=$(\n        %s\n    )\n    true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    echo "$(\n        %s\n    )"\n    true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    echo $(\n        %s\n    )\n    true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    _h() {\n        local out="$(\n            %s\n        )"\n    }\n    _h\n    true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    _h() {\n        local out=$(\n            %s\n        )\n    }\n    _h\n    true\n}\n' % self.NEG)
        # and one BEFORE the subshell's last command is still reported
        text = ('@test "x" {\n    (\n        ! grep -q x "$LOG"\n        run true\n    )\n    true\n}\n')
        self.assertEqual(mid_test_bare_negations(text), [(3, '        ! grep -q x "$LOG"')])

    def test_a_compound_close_is_read_where_the_compound_is(self):
        # round 8 addendum (F1, the shape the round-7 ruling named for the scanner lens): a bare `!` as the last command of an if, a
        # for, a while, an until or a case body is read when the compound is the test's last command (bats: not ok on every one) and
        # not when a command follows the compound (bats: ok). Red before: `fi`, `else`, `done`, `;;` and `esac` were never read
        # positions, so all eight last-command shapes were reported
        compounds = {
            "if": '    if true; then\n        %s\n    fi',
            "if-else, in the then branch": '    if true; then\n        %s\n    else\n        true\n    fi',
            "if-else, in the else branch": '    if false; then\n        true\n    else\n        %s\n    fi',
            "if-elif": '    if true; then\n        %s\n    elif true; then\n        true\n    fi',
            "nested if": '    if true; then\n        if true; then\n            %s\n        fi\n    fi',
            "a one-line if inside the branch before it": '    if true; then\n        if true; then true; fi\n        %s\n    fi',
            "for": '    for i in 1; do\n        %s\n    done',
            "while": '    n=0\n    while [ "$n" -lt 1 ]; do\n        n=1\n        %s\n    done',
            "until": '    n=0\n    until [ "$n" -ge 1 ]; do\n        n=1\n        %s\n    done',
            "case": '    case a in\n      a)\n        %s\n        ;;\n    esac',
            "case, the pattern line carrying a command": '    case a in\n      a) true\n        %s\n        ;;\n      b) true ;;\n    esac',
            "case without ;;": '    case a in\n      a)\n        %s\n    esac',
        }
        for what, body in compounds.items():
            self.assertExempt('@test "x" {\n%s\n}\n' % (body % self.NEG), what + ", the test's last command")
            self.assertReported('@test "x" {\n%s\n    true\n}\n' % (body % self.NEG), what + ", followed by a command")
        # the compound inside a helper called last, a group that is the test's last command, and a subshell followed by a command
        # (the subshell's failure is errexit's): read, bats not ok
        self.assertExempt('@test "x" {\n    _h() {\n        if true; then\n            %s\n        fi\n    }\n    _h\n}\n' % self.NEG)
        self.assertExempt('@test "x" {\n    {\n        if true; then\n            %s\n        fi\n    }\n}\n' % self.NEG)
        self.assertExempt('@test "x" {\n    (\n        if true; then\n            %s\n        fi\n    )\n    true\n}\n' % self.NEG)
        # what follows the close decides as for a brace: `fi ; true`, `fi || true`, `fi | cat`, `fi 2>&1 | cat` run on (bats: ok);
        # `fi && true`, `fi > /dev/null` and `fi >/dev/null && true` as the last command are read (bats: not ok)
        for trailer in (" ; true", " || true", " | cat", " 2>&1 | cat"):
            self.assertReported('@test "x" {\n    if true; then\n        %s\n    fi%s\n}\n' % (self.NEG, trailer), repr(trailer))
        for trailer in (" && true", " > /dev/null", " >/dev/null && true"):
            self.assertExempt('@test "x" {\n    if true; then\n        %s\n    fi%s\n}\n' % (self.NEG, trailer), repr(trailer))
        self.assertReported('@test "x" {\n    for i in 1; do\n        %s\n    done ; true\n}\n' % self.NEG)
        self.assertReported('@test "x" {\n    case a in\n      a)\n        %s\n        ;;\n    esac ; true\n}\n' % self.NEG)

    def test_a_negation_line_that_discards_its_own_status_is_reported_wherever_it_sits(self):
        # round 8 addendum (F7 and the register): `! cmd || fallback` returns the fallback's status, `! cmd; cmd` ends in the other
        # command, `! cmd &` runs in the background: bats ok for each as the test's LAST line (red before: exempt there, the next
        # command line being the close). `! cmd && cmd` and `! cmd | cmd` as the last line are read (bats: not ok) and mid-test are not
        for tail in (" || echo fb", " && true || echo fb", " | cat || echo fb", "; true", " &\n    wait"):
            text = '@test "x" {\n    true\n    %s%s\n}\n' % (self.NEG, tail)
            self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [3], repr(tail))
        for tail in (" && echo yes", " | cat", ";", "   # a note"):
            self.assertExempt('@test "x" {\n    true\n    %s%s\n}\n' % (self.NEG, tail), repr(tail))
            self.assertReported('@test "x" {\n    %s%s\n    true\n}\n' % (self.NEG, tail), repr(tail))
        # a fallback that fails whenever it runs is an armed check wherever the line sits (bats: not ok mid-test and last); a
        # fallback whose status this scan does not know is taken as discarding, and reported, at both positions
        for tail in (" || false", " || return 1", " || exit 1", " || return", " || { echo no; return 1; }"):
            self.assertExempt('@test "x" {\n    true\n    %s%s\n}\n' % (self.NEG, tail), repr(tail))
            self.assertExempt('@test "x" {\n    %s%s\n    true\n}\n' % (self.NEG, tail), repr(tail))
        for tail in (" || true", " || return 0", ' || return "$rc"', " || fail no", " || { echo no; true; }"):
            self.assertReported('@test "x" {\n    true\n    %s%s\n}\n' % (self.NEG, tail), repr(tail))
            self.assertReported('@test "x" {\n    %s%s\n    true\n}\n' % (self.NEG, tail), repr(tail))
        # a `;` or `||` inside quotes or a substitution on the negation line is not an operator
        self.assertExempt('@test "x" {\n    true\n    ! grep -q "a;b||c" "$LOG"\n}\n')
        self.assertExempt('@test "x" {\n    true\n    ! grep -q "$(echo a; echo b)" "$LOG"\n}\n')

    def test_a_test_closed_by_a_brace_with_leading_or_trailing_whitespace_ends_there_and_reads_its_last_command(self):
        # round 8 (extra6-1, tests-3): bats parses each close and reads the negation (not ok); the round-7 rule reported the armed
        # last command and ran the block on into the next test (red before: [9, 13] for each; 13 alone is right)
        for body, close in (("    ", "  }"), ("    ", "} "), ("    ", "\t}"), ("    ", "    }"), ("  ", "  }"), ("\t", "\t}")):
            text = ('@test "armed last" {\n%srun true\n%s%s\n%s\n\n@test "after it" {\n    %s\n    true\n}\n'
                    % (body, body, self.NEG, close, self.NEG))
            self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [7], repr(close))
            s = scan(text)
            self.assertEqual(s.blocks, [(0, 3), (5, 8)], repr(close))

    def test_a_helpers_opener_may_carry_a_trailing_comment_or_be_spelled_allman_or_carry_any_name_bash_accepts(self):
        # round 8 (tests-2, regression-2's Allman half): bats reads the helper's last command through the caller's errexit (not ok);
        # red before: both reported. Round 8 addendum (F8): a hyphen or a dot in the name and spaced parens are openers bash accepts
        # (bats: not ok); red before: the name class refused them and the brace was read as a group's, then reported
        for opener, call in (('    _h() {   # a note', '_h'), ('    _h()\n    {', '_h'), ('    function _h {', '_h'), ('    function _h() {', '_h'),
                             ('    _h() {', '_h'), ('    my-helper() {', 'my-helper'), ('    _h ( ) {', '_h'), ('    my.helper() {', 'my.helper'),
                             ('    function my-helper ( ) {', 'my-helper')):
            self.assertExempt('@test "x" {\n%s\n        run true\n        %s\n    }\n    %s\n    true\n}\n' % (opener, self.NEG, call), opener)

    def test_a_helpers_last_command_is_read_only_where_the_helper_is_called_in_a_read_position(self):
        # round 8 addendum (F9): the round-8 rule exempted a helper's last-command negation on the premise of a plain call under
        # errexit. bats: ok (asserts nothing) when the helper is called under `if`, as `_h || true`, under `while`, as `! _h`, in
        # `echo $(_h)`, backgrounded, piped, under `run` with no status read, or never; red before: every one exempt
        helper = '@test "x" {\n    _h() {\n        run true\n        %s\n    }\n%s}\n'
        for call in ('    if _h; then true; fi\n    true\n', '    _h || true\n    true\n', '    while _h; do break; done\n    true\n',
                     '    ! _h\n', '    echo $(_h)\n    true\n', '    _h &\n    wait\n', '    _h | cat\n', '    run _h\n    true\n',
                     '    true\n', '    if ! _h; then true; fi\n    true\n'):
            self.assertReported(helper % (self.NEG, call), repr(call))
        # and read (bats: not ok) on a plain call alone, with arguments, as the last command, under `&&`, before `; true`, inside a
        # group, from another helper, in a plain assignment's substitution, and under `run` followed by a status check
        for call in ('    _h\n    true\n', '    _h "$LOG" x\n    true\n', '    _h\n', '    _h && true\n', '    _h; true\n    true\n',
                     '    {\n        _h\n    }\n', '    _g() {\n        _h\n    }\n    _g\n    true\n', '    x=$(_h)\n    true\n',
                     '    x="$(_h)"\n', '    run _h\n    [ "$status" -eq 0 ]\n', '    _h || return 1\n    true\n'):
            self.assertExempt(helper % (self.NEG, call), repr(call))

    def test_a_heredoc_inside_a_nested_helper_does_not_end_the_backward_walk(self):
        # round 8 (regression-2): the helper's opener is found over command lines, heredoc text skipped; bats: not ok. Red before:
        # the walk stopped at the column-zero `PY` and reported the helper's last command
        text = ('@test "x" {\n    _h() {\n        cat > "$f" <<\'PY\'\nimport sys\nPY\n        %s\n    }\n    _h\n    true\n}\n' % self.NEG)
        self.assertExempt(text)
        # round 8 addendum (the mutation lens, row 25): a heredoc body holding unbalanced brace lines is text to the walk; without the
        # skip the depth count reads them and the helper's opener is not found (red under the mutant: reported)
        text = ('@test "x" {\n    _h() {\n        cat > "$f" <<\'EOF\'\n}\n}\nEOF\n        %s\n    }\n    _h\n    true\n}\n' % self.NEG)
        self.assertExempt(text)

    def test_skips_a_heredoc_body_so_a_column_zero_brace_inside_it_does_not_end_the_block(self):
        # the round-7 addendum: the JSON's `}` ended the block at line 5 and the negation at line 7 was outside the scan. Round 8
        # (correctness-5, tests-4): the delimiter is any word bash accepts in any quoting (red before: the backslash and mixed
        # quotings and the hyphen were not introducers, so the brace ended the block and nothing was reported). Round 8 addendum: the
        # `$'EOF'` and `$"EOF"` spellings, whose `$` is part of the quote (red before: the walk looked for a line `$EOF`)
        for intro, term in (('<<EOF', 'EOF'), ('<<"EOF"', 'EOF'), ("<<'EOF'", 'EOF'), ('<<-EOF', '\tEOF'), ("<< 'EOF'", 'EOF'),
                            ('<<\\EOF', 'EOF'), ('<<-\\EOF', '\tEOF'), ('<<E\\OF', 'EOF'), ('<<"EO"F', 'EOF'), ("<<E'OF'", 'EOF'),
                            ("<<'EOF-1'", 'EOF-1'), ('<<EOF-1', 'EOF-1'), ('<<$X', '$X'), ("<<$'EOF'", 'EOF'), ('<<$"EOF"', 'EOF')):
            text = ('@test "x" {\n    cat > "$f" %s\n{\n  "a": 1\n}\n%s\n    %s\n    true\n}\n' % (intro, term, self.NEG))
            self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [7], intro)
        # the `$'EOF'` body may hold a line `$EOF`, which is text to bash and was the walk's terminator before
        text = ("@test \"x\" {\n    cat > \"$f\" <<$'EOF'\n$EOF\n}\nEOF\n    %s\n    true\n}\n" % self.NEG)
        self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [6])
        self.assertEqual(self.coverage(text), [])

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
        # round 8 addendum (the mutation lens, row 29): the shift is observable only with a later line equal to the word after it; a
        # line `2` follows, and is a command, not a terminator (red under the mutant: nothing reported, the lines skipped as text)
        self.assertReported('@test "x" {\n    x=$(( 1 << 2 ))\n    %s\n2\n    true\n}\n' % self.NEG)

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

    def test_the_walk_opens_a_block_on_every_line_bats_preprocess_rewrites(self):
        # round 8 addendum (F4): an indented opener, one with a trailing comment, one with a trailing command and a one-line test are
        # tests to bats (its pattern allows leading blanks and anything after the brace); red before: none opened a block, so the
        # negation under each was outside the scan, and the pin, keyed on the same narrower pattern, had no extent to red on
        for opener in ('  @test "x" {', '@test "x" {   # note', '@test "x" { run true', '\t@test "x" {  # a tab'):
            text = '%s\n    %s\n    true\n}\n' % (opener, self.NEG)
            self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [2], opener)
            self.assertEqual(scan(text).blocks, [(0, 3)], opener)
            self.assertEqual(self.coverage(text), [], opener)
        # a one-line test is a block of no lines, closed on its opener; its body is not scanned (a `! cmd` on the opener line is a
        # stated limit) and the pin counts it as a test of zero in-test lines
        text = '@test "a" {\n    %s\n    true\n}\n@test "b" { true; }\n@test "c" { ! true; }\n@test "d" {\n    true\n    %s\n}\n' % (self.NEG, self.NEG)
        self.assertEqual([ln for ln, _ in mid_test_bare_negations(text)], [2])
        self.assertEqual(scan(text).blocks, [(0, 3), (4, 4), (5, 5), (6, 9)])
        self.assertEqual(bash_test_extents(text.split("\n")), [(0, 3), (4, 4), (5, 5), (6, 9)])
        self.assertEqual(self.coverage(text), [])

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

    def test_the_coverage_pin_reds_a_block_that_never_ends_and_one_that_over_runs(self):
        # round 8 addendum (the mutation lens, rows 3 and 5): the two clauses no case reached. A command line ending in a literal `{`
        # opens a level the block never closes (the documented `printf x {`): the block is (0, None) where bash closes the test at
        # its brace; with a second `}` line after the test's the walk closes there instead, one line past bash
        text = ('@test "x" {\n    printf x {\n    %s\n    true\n}\n' % self.NEG)
        problems = self.coverage(text)
        self.assertEqual(problems, ["x.bats:1: the block never ended where bash ends the test (line 5); it ran to the next @test or the "
                                    "end of the file, scanning file-scope lines as the test's",
                                    "x.bats: in-test lines: 3 by bash's parse, 5 scanned (5 command lines, 0 heredoc text lines)"])
        self.assertEqual(scan(text).blocks, [(0, None)])   # the 5 scanned: the test's 3 lines, its close and the file's last, empty, line
        text = ('@test "x" {\n    printf x {\n    true\n}\n}\n')
        self.assertEqual(self.coverage(text), ["x.bats:1: the block ended at line 5 where bash ends the test at line 4: 1 lines scanned "
                                               "as the test's that are not",
                                               "x.bats: in-test lines: 2 by bash's parse, 3 scanned (3 command lines, 0 heredoc text lines)"])

    def test_the_coverage_pin_reds_a_test_bash_cannot_close(self):
        # round 8 addendum (the mutation lens, row 1): a file that does not parse has no close for bash to find; the pin says so and
        # asserts nothing else about that test
        text = '@test "x" {\n    echo "\n    %s\n    true\n' % self.NEG
        self.assertEqual(bash_test_extents(text.split("\n")), [(0, None)])
        self.assertIn("x.bats:1: bash finds no close for this test (the file does not parse under this bash -n); its extent is unknown "
                      "and nothing about the scan of it can be asserted", self.coverage(text))

    def test_the_coverage_pin_reds_a_skip_bash_does_not_make(self):
        # a `<<PY` inside a string that began on the earlier line is an introducer to this line scan and text to bash: the skip to the
        # later real `PY` reads as covered by the line counts alone, and bash's parse says the introducer line opens no heredoc
        text = ('@test "x" {\n    msg="see the\n<<PY marker"\n    %s\n    python3 - <<PY\nprint(1)\nPY\n    true\n}\n' % self.NEG)
        problems = self.coverage(text)
        self.assertEqual(problems, ["x.bats:3: read as opening a heredoc that bash opens nowhere on this line (a `<<` inside a string "
                                    "that began on an earlier line?): lines 4 to 7 were skipped as text and are commands"])
        self.assertEqual(mid_test_bare_negations(text), [], "the loss the pin names")

    def test_the_coverage_pin_reds_a_skip_ended_before_bash_ends_the_heredoc(self):
        # round 8 addendum (the mutation lens, row 9): no walk shape reaches this clause since the `$'EOF'` fix (both read the exact
        # word line, tabs stripped for `<<-`), so it is pinned on a Scan whose recorded skip ends one line early, the shape the
        # `$'EOF'` walk produced before the fix
        text = ('@test "x" {\n    cat > "$f" <<EOF\n$EOF\n}\nEOF\n    %s\n    true\n}\n' % self.NEG)
        lines = text.split("\n")
        s = scan(text)
        self.assertEqual(s.heredoc_skips, [(1, 5)])
        s.heredoc_skips = [(1, 3)]
        self.assertEqual(coverage_problems("x.bats", lines, s, bash_test_extents(lines)),
                         ["x.bats:2: the heredoc opened here was skipped to line 3, where bash still reads its text (the terminator "
                          "taken is not bash's)"])

    def test_the_coverage_pin_reds_a_fixture_heredoc_holding_a_test_line_and_says_how_to_write_it(self):
        # the bounded skip's cost (round 8, correctness-1): a heredoc writing a bats fixture with a `@test ... {` line is not skipped
        # past that line, so the walk opens a block bash does not see; the pin names the line and the way to write such a fixture.
        # Round 8 addendum (F4, checked under bats 1.10.0): an INDENTED fixture line is no way out, bats-preprocess rewrites it too
        # (the written fixture began `test_inner() { bats_test_begin "inner";` and the file declared 2 tests and ran 1), so the walk
        # opens a block on it as well and the message says to write the line through printf
        text = ('@test "a" {\n    cat > "$f" <<\'EOF\'\n@test "inner" {\n    true\n}\nEOF\n    %s\n    true\n}\n' % self.NEG)
        for fixture in (text, text.replace('\n@test "inner"', '\n  @test "inner"')):
            problems = self.coverage(fixture)
            self.assertIn("x.bats:3: the scan entered a block where bash sees no test start (a @test line inside a heredoc, a quoted "
                          "string or another test); " + FIXTURE_LINE_REMEDY, problems)
            self.assertIn("x.bats:3: a @test open met while a block was open", problems)
        self.assertEqual(self.coverage(text.replace('@test "inner" {', "printf '@test \"inner\" {\\n'")), [], "the printf line: green")

    def test_the_coverage_pin_reads_a_prefix_cut_inside_a_file_scope_heredoc_as_incomplete(self):
        # round 8 addendum (the mutation lens, row 12): `bash -n` exits 0 on a prefix cut inside a heredoc and only warns, so the
        # parse is read off stderr too; on the exit code alone the fixture line inside a file-scope heredoc would count as a test
        # for bash as well as for the walk, and the pin would be silent on both
        text = 'cat <<EOF\n@test "inner" {\nEOF\n\n@test "real" {\n    %s\n    true\n}\n' % self.NEG
        lines = text.split("\n")
        self.assertEqual(bash_test_extents(lines), [(4, 7)])
        self.assertEqual(scan(text).blocks, [(1, None), (4, 7)])
        self.assertEqual(self.coverage(text), ["x.bats:2: the scan entered a block where bash sees no test start (a @test line inside a "
                                               "heredoc, a quoted string or another test); " + FIXTURE_LINE_REMEDY,
                                               "x.bats:5: a @test open met while a block was open",
                                               "x.bats: in-test lines: 2 by bash's parse, 4 scanned (4 command lines, 0 heredoc text lines)"])

    def test_bash_test_extents_reads_the_tests_bash_parses(self):
        # opens inside a heredoc, a string or another test are not tests; a one-line @test is rewritten so the file parses and is
        # an extent of no lines (round 8 addendum); a file that does not parse yields None for the close
        text = ('setup() {\n    cat <<EOF\n@test "not one" {\n}\nEOF\n}\n@test "one" {\n    x="\n@test \\"nor this\\" {\n"\n}\n'
                '@test "two" { true; }\n@test "three" {\n  true\n  }\n')
        lines = text.split("\n")
        self.assertEqual(bash_test_extents(lines), [(6, 10), (11, 11), (12, 14)])
        self.assertEqual(bash_test_extents('@test "x" {\n    echo "\n'.split("\n")), [(0, None)])


def ground_truth_shapes():
    """{name: a synthetic .bats text} whose bare negations are `! true`, the negated command succeeding, so under bats a test passes
    (`ok`) exactly when the negation asserted nothing there. The families of the round-8 scanner lens (subshell closers, command
    substitutions, heredocs, nested helpers and their call sites, test closes, brace groups, positions on the negation's own line,
    compounds, opener forms), each shape mid-test and as the last command where the distinction exists. Every other command in a
    shape succeeds (files are written to /dev/null), so a test's verdict turns on the negation alone; a bare `! _h` calling a helper
    whose last command is `! true` is not in the register, since that negated command fails and its test says nothing."""
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
    for name, opener, closer in (("assign_quoted", 'out="$(', ')"'), ("assign_unquoted", "out=$(", ")"), ("assign_plus", 'out+="$(', ')"'),
                                 ("echo_quoted", 'echo "$(', ')"'), ("echo_unquoted", "echo $(", ")"), ("export", 'export out="$(', ')"'),
                                 ("bracket", '[ -z "$(', ')" ]'), ("assign_then_pipe", 'out="$(', ')" | cat')):
        S["B_%s_mid" % name] = '@test "x" {\n    %s\n        %s\n    %s\n    true\n}\n' % (opener, N, closer)
        S["B_%s_last" % name] = '@test "x" {\n    %s\n        %s\n    %s\n}\n' % (opener, N, closer)
    S["B_local_in_helper"] = '@test "x" {\n    _h() {\n        local out="$(\n            %s\n        )"\n    }\n    _h\n    true\n}\n' % N
    for name, intro, term in (("plain", "<<EOF", "EOF"), ("squote", "<<'EOF'", "EOF"), ("dquote", '<<"EOF"', "EOF"), ("dash", "<<-EOF", "\tEOF"),
                              ("backslash", "<<\\EOF", "EOF"), ("mixed", '<<"EO"F', "EOF"), ("hyphen", "<<'EOF-1'", "EOF-1"), ("dollar", "<<$X", "$X"),
                              ("ansi", "<<$'EOF'", "EOF"), ("dotted", "<<EOF.json", "EOF.json")):
        S["C_heredoc_%s" % name] = '@test "x" {\n    cat > /dev/null %s\n{\n  "a": 1\n}\n%s\n    %s\n    true\n}\n' % (intro, term, N)
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
                               ("spaced_parens", "_h ( ) {", "_h"), ("dot_name", "my.helper() {", "my.helper")):
        S["D_%s" % name] = '@test "x" {\n    %s\n        run true\n        %s\n    }\n    %s\n    true\n}\n' % (opener, N, call)
    S["D_column_zero_body"] = '@test "x" {\n    _h() {\nrun true\n%s\n    }\n    _h\n    true\n}\n' % N
    S["D_mid_negation"] = '@test "x" {\n    _h() {\n        %s\n        run true\n    }\n    _h\n    true\n}\n' % N
    S["D_close_trailing_comment"] = '@test "x" {\n    _h() {\n        %s\n    }   # end\n    _h\n    true\n}\n' % N
    for name, call in (("called_last", "    _h\n"), ("called_mid", "    _h\n    true\n"), ("called_with_args", '    _h /dev/null x\n    true\n'),
                       ("called_in_if", "    if _h; then true; fi\n    true\n"), ("called_or_true", "    _h || true\n    true\n"),
                       ("called_or_return", "    _h || return 1\n    true\n"), ("called_or_false_last", "    _h || false\n"),
                       ("called_or_return_0", "    _h || return 0\n    true\n"), ("never_called", "    true\n"), ("run_no_status", "    run _h\n    true\n"),
                       ("run_status", '    run _h\n    [ "$status" -eq 0 ]\n'), ("and_true_last", "    _h && true\n"), ("semi_true", "    _h; true\n    true\n"),
                       ("subst_echo", "    echo $(_h)\n    true\n"), ("subst_assign_last", "    x=$(_h)\n"), ("subst_assign_quoted_mid", '    x="$(_h)"\n    true\n'),
                       ("if_negated", "    if ! _h; then true; fi\n    true\n"), ("in_group_last", "    {\n        _h\n    }\n"),
                       ("from_other_helper", "    _g() {\n        _h\n    }\n    _g\n    true\n"), ("while_cond", "    while _h; do break; done\n    true\n"),
                       ("bg", "    _h &\n    wait\n"), ("pipe", "    _h | cat\n")):
        S["D_%s" % name] = '@test "x" {\n    _h() {\n        run true\n        %s\n    }\n%s}\n' % (N, call)
    for name, close in (("indent2", "  }"), ("trailing_space", "} "), ("tab", "\t}"), ("indent4", "    }"), ("trailing_comment", "} # end"), ("trailing_tab", "}\t")):
        S["E_close_%s_then_test" % name] = '@test "armed" {\n    run true\n    %s\n%s\n\n@test "after" {\n    %s\n    true\n}\n' % (N, close, N)
        S["E_close_%s_last_in_file" % name] = '@test "armed" {\n    run true\n    %s\n%s\n' % (N, close)
    S["E_close_indented_then_file_helper"] = '@test "armed" {\n    run true\n    %s\n  }\n\nhelper() {\n    %s\n    true\n}\n' % (N, N)
    S["E_close_indented_then_teardown"] = '@test "armed" {\n    run true\n    %s\n  }\n\nteardown() {\n    %s\n    true\n}\n' % (N, N)
    groups = {"bare": "}", "pipe": "} | cat", "and": "} && true", "or": "} || true", "semi": "};", "semi_true": "} ; true", "redir": "} > /dev/null",
              "redir_pipe": "} 2>&1 | cat", "redir_or": "} >/dev/null || true", "redir_and": "} >/dev/null && true", "and_or": "} && true || echo fb"}
    for name, closer in groups.items():
        for pos, tail in (("mid", "\n    true"), ("last", "")):
            S["F_group_%s_%s" % (name, pos)] = '@test "x" {\n    {\n        run true\n        %s\n    %s%s\n}\n' % (N, closer, tail)
    S["F_group_bg_wait_mid"] = '@test "x" {\n    {\n        %s\n    } &\n    wait\n}\n' % N
    S["F_orlist_group_last"] = '@test "x" {\n    false || {\n        true\n        %s\n    }\n}\n' % N
    S["F_group_in_helper_last"] = '@test "x" {\n    _h() {\n        {\n            true\n            %s\n        }\n    }\n    _h\n}\n' % N
    S["F_group_in_helper_mid"] = '@test "x" {\n    _h() {\n        {\n            true\n            %s\n        }\n        true\n    }\n    _h\n}\n' % N
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
                       ("trailing_comment", "   # note"), ("bg", " &\n    wait")):
        S["G_%s_mid" % name] = '@test "x" {\n    %s%s\n    true\n}\n' % (N, tail)
        S["G_%s_last" % name] = '@test "x" {\n    true\n    %s%s\n}\n' % (N, tail)
    S["G_quoted_operators_last"] = '@test "x" {\n    true\n    ! echo "a;b||c" > /dev/null\n}\n'
    S["G_substitution_operators_last"] = '@test "x" {\n    true\n    ! echo "$(echo a; echo b)" > /dev/null\n}\n'
    compounds = {"if": "    if true; then\n        %s\n    fi", "if_else_then": "    if true; then\n        %s\n    else\n        true\n    fi",
                 "if_else_else": "    if false; then\n        true\n    else\n        %s\n    fi", "if_elif": "    if true; then\n        %s\n    elif true; then\n        true\n    fi",
                 "if_nested": "    if true; then\n        if true; then\n            %s\n        fi\n    fi",
                 "if_oneliner_before": "    if true; then\n        if true; then true; fi\n        %s\n    fi",
                 "for": "    for i in 1; do\n        %s\n    done", "while": '    n=0\n    while [ "$n" -lt 1 ]; do\n        n=1\n        %s\n    done',
                 "until": '    n=0\n    until [ "$n" -ge 1 ]; do\n        n=1\n        %s\n    done',
                 "case": "    case a in\n      a)\n        %s\n        ;;\n    esac", "case_pattern_command": "    case a in\n      a) true\n        %s\n        ;;\n      b) true ;;\n    esac",
                 "case_no_dsemi": "    case a in\n      a)\n        %s\n    esac"}
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
    return S


class BatsGroundTruth(unittest.TestCase):
    """The register: every shape of ground_truth_shapes under bats itself, the negated command succeeding, against the scanner (round 8
    addendum of fork PR #778: the round-8 module's Scanner cases pinned the scanner's own verdicts and their agreement with bats rested
    on a bats run kept outside the tree, where an independent lens then found 30 shapes disagreeing). RECORDED holds each shape's bats
    verdicts per test in file order, pasted from bats 1.10.0 (`bats -t` over the shapes, HOME and TMPDIR isolated, stdin /dev/null);
    the scanner must flag exactly the bare negations that sit in a test recorded `ok`, and where bats is on PATH the shapes are run
    again and the verdicts must equal the record (a bats whose semantics differ, or a stale record, reds here). Without bats the
    recorded verdicts stand and the run says so; it never skips."""

    RECORDED = {
        'A_and_and_last': 'not ok',
        'A_and_and_mid': 'ok',
        'A_and_bg_last': 'ok',
        'A_and_bg_mid': 'ok',
        'A_and_last': 'not ok',
        'A_and_mid': 'ok',
        'A_and_or_false_last': 'not ok',
        'A_and_or_false_mid': 'not ok',
        'A_and_or_last': 'ok',
        'A_and_or_mid': 'ok',
        'A_and_pipe_last': 'not ok',
        'A_and_pipe_mid': 'ok',
        'A_bare_last': 'not ok',
        'A_bare_mid': 'not ok',
        'A_bg_last': 'ok',
        'A_bg_mid': 'ok',
        'A_bg_wait_last': 'ok',
        'A_neg_before_last': 'ok',
        'A_or_false_last': 'not ok',
        'A_or_false_mid': 'not ok',
        'A_or_last': 'ok',
        'A_or_mid': 'ok',
        'A_or_return_1_last': 'not ok',
        'A_or_return_1_mid': 'not ok',
        'A_pipe_last': 'ok',
        'A_pipe_mid': 'ok',
        'A_pipe_nospace_last': 'ok',
        'A_pipe_nospace_mid': 'ok',
        'A_pipeamp_last': 'ok',
        'A_pipeamp_mid': 'ok',
        'A_redir2_last': 'not ok',
        'A_redir2_mid': 'not ok',
        'A_redir_and_last': 'not ok',
        'A_redir_and_mid': 'ok',
        'A_redir_last': 'not ok',
        'A_redir_mid': 'not ok',
        'A_redir_or_last': 'ok',
        'A_redir_or_mid': 'ok',
        'A_redir_pipe_last': 'ok',
        'A_redir_pipe_mid': 'ok',
        'A_redirall_last': 'not ok',
        'A_redirall_mid': 'not ok',
        'A_semi_last': 'not ok',
        'A_semi_mid': 'not ok',
        'A_semi_true_last': 'not ok',
        'A_semi_true_mid': 'not ok',
        'B_assign_plus_last': 'not ok',
        'B_assign_plus_mid': 'not ok',
        'B_assign_quoted_last': 'not ok',
        'B_assign_quoted_mid': 'not ok',
        'B_assign_then_pipe_last': 'ok',
        'B_assign_then_pipe_mid': 'ok',
        'B_assign_unquoted_last': 'not ok',
        'B_assign_unquoted_mid': 'not ok',
        'B_bracket_last': 'ok',
        'B_bracket_mid': 'ok',
        'B_echo_quoted_last': 'ok',
        'B_echo_quoted_mid': 'ok',
        'B_echo_unquoted_last': 'ok',
        'B_echo_unquoted_mid': 'ok',
        'B_export_last': 'ok',
        'B_export_mid': 'ok',
        'B_local_in_helper': 'ok',
        'C_apostrophe_then_heredoc': 'ok',
        'C_comment_introducer': 'ok',
        'C_decoy_then_real': 'ok',
        'C_heredoc_ansi': 'ok',
        'C_heredoc_ansi_decoy_body': 'ok',
        'C_heredoc_backslash': 'ok',
        'C_heredoc_dash': 'ok',
        'C_heredoc_decoy_body': 'ok',
        'C_heredoc_dollar': 'ok',
        'C_heredoc_dotted': 'ok',
        'C_heredoc_dquote': 'ok',
        'C_heredoc_hyphen': 'ok',
        'C_heredoc_in_helper_last': 'not ok',
        'C_heredoc_last': 'not ok',
        'C_heredoc_mixed': 'ok',
        'C_heredoc_on_run_line': 'ok',
        'C_heredoc_plain': 'ok',
        'C_heredoc_squote': 'ok',
        'C_herestring': 'ok',
        'C_quoted_introducer_two_tests': 'ok,ok',
        'C_shift': 'ok',
        'C_text_bang_only': 'ok',
        'C_two_introducers': 'ok',
        'D_allman': 'not ok',
        'D_and_true_last': 'not ok',
        'D_bg': 'ok',
        'D_called_in_if': 'ok',
        'D_called_last': 'not ok',
        'D_called_mid': 'not ok',
        'D_called_or_false_last': 'not ok',
        'D_called_or_return': 'not ok',
        'D_called_or_return_0': 'ok',
        'D_called_or_true': 'ok',
        'D_called_with_args': 'not ok',
        'D_close_trailing_comment': 'not ok',
        'D_column_zero_body': 'not ok',
        'D_dot_name': 'not ok',
        'D_from_other_helper': 'not ok',
        'D_function_kw': 'not ok',
        'D_function_kw_parens': 'not ok',
        'D_hyphen_name': 'not ok',
        'D_if_negated': 'ok',
        'D_in_group_last': 'not ok',
        'D_mid_negation': 'ok',
        'D_never_called': 'ok',
        'D_pipe': 'ok',
        'D_run_no_status': 'ok',
        'D_run_status': 'not ok',
        'D_semi_true': 'not ok',
        'D_spaced_parens': 'not ok',
        'D_subst_assign_last': 'not ok',
        'D_subst_assign_quoted_mid': 'not ok',
        'D_subst_echo': 'ok',
        'D_trailing_comment': 'not ok',
        'D_while_cond': 'ok',
        'E_close_indent2_last_in_file': 'not ok',
        'E_close_indent2_then_test': 'not ok,ok',
        'E_close_indent4_last_in_file': 'not ok',
        'E_close_indent4_then_test': 'not ok,ok',
        'E_close_indented_then_file_helper': 'not ok',
        'E_close_indented_then_teardown': 'not ok',
        'E_close_tab_last_in_file': 'not ok',
        'E_close_tab_then_test': 'not ok,ok',
        'E_close_trailing_comment_last_in_file': 'not ok',
        'E_close_trailing_comment_then_test': 'not ok,ok',
        'E_close_trailing_space_last_in_file': 'not ok',
        'E_close_trailing_space_then_test': 'not ok,ok',
        'E_close_trailing_tab_last_in_file': 'not ok',
        'E_close_trailing_tab_then_test': 'not ok,ok',
        'F_group_and_last': 'not ok',
        'F_group_and_mid': 'ok',
        'F_group_and_or_last': 'ok',
        'F_group_and_or_mid': 'ok',
        'F_group_bare_last': 'not ok',
        'F_group_bare_mid': 'ok',
        'F_group_bg_wait_mid': 'ok',
        'F_group_in_helper_last': 'not ok',
        'F_group_in_helper_mid': 'ok',
        'F_group_in_subshell_last': 'not ok',
        'F_group_or_last': 'ok',
        'F_group_or_mid': 'ok',
        'F_group_pipe_last': 'ok',
        'F_group_pipe_mid': 'ok',
        'F_group_redir_and_last': 'not ok',
        'F_group_redir_and_mid': 'ok',
        'F_group_redir_last': 'not ok',
        'F_group_redir_mid': 'ok',
        'F_group_redir_or_last': 'ok',
        'F_group_redir_or_mid': 'ok',
        'F_group_redir_pipe_last': 'ok',
        'F_group_redir_pipe_mid': 'ok',
        'F_group_semi_last': 'not ok',
        'F_group_semi_mid': 'ok',
        'F_group_semi_true_last': 'ok',
        'F_group_semi_true_mid': 'ok',
        'F_nested_group_inner_followed': 'ok',
        'F_nested_group_last': 'not ok',
        'F_orlist_group_last': 'not ok',
        'G_and_or_false_last': 'not ok',
        'G_and_or_false_mid': 'not ok',
        'G_and_or_last': 'ok',
        'G_and_or_mid': 'ok',
        'G_and_then_last': 'not ok',
        'G_and_then_mid': 'ok',
        'G_bg_last': 'ok',
        'G_bg_mid': 'ok',
        'G_first_command': 'ok',
        'G_last_command': 'not ok',
        'G_last_past_comment_blank': 'not ok',
        'G_mid_after_run': 'ok',
        'G_or_fallback_last': 'ok',
        'G_or_fallback_mid': 'ok',
        'G_or_false_last': 'not ok',
        'G_or_false_mid': 'not ok',
        'G_or_group_return_last': 'not ok',
        'G_or_group_return_mid': 'not ok',
        'G_or_return_0_last': 'ok',
        'G_or_return_0_mid': 'ok',
        'G_or_return_1_last': 'not ok',
        'G_or_return_1_mid': 'not ok',
        'G_or_return_bare_last': 'not ok',
        'G_or_return_bare_mid': 'not ok',
        'G_pipe_or_last': 'ok',
        'G_pipe_or_mid': 'ok',
        'G_pipeline_last': 'not ok',
        'G_pipeline_mid': 'ok',
        'G_quoted_operators_last': 'not ok',
        'G_semicolon_command_last': 'ok',
        'G_semicolon_command_mid': 'ok',
        'G_substitution_operators_last': 'not ok',
        'G_tab_indented_mid': 'ok',
        'G_trailing_comment_last': 'not ok',
        'G_trailing_comment_mid': 'ok',
        'G_trailing_semicolon_last': 'not ok',
        'G_trailing_semicolon_mid': 'ok',
        'G_two_tests_second_mid': 'not ok,ok',
        'I_one_liner_between': 'ok,ok,not ok',
        'I_one_liner_negation': 'not ok',
        'I_opener_indented_last': 'not ok',
        'I_opener_indented_mid': 'ok',
        'I_opener_tab_indented_last': 'not ok',
        'I_opener_tab_indented_mid': 'ok',
        'I_opener_trailing_command_last': 'not ok',
        'I_opener_trailing_command_mid': 'ok',
        'I_opener_trailing_comment_last': 'not ok',
        'I_opener_trailing_comment_mid': 'ok',
        'I_opener_trailing_negation': 'ok',
        'T_case_last': 'not ok',
        'T_case_mid': 'ok',
        'T_case_no_dsemi_last': 'not ok',
        'T_case_no_dsemi_mid': 'ok',
        'T_case_pattern_command_last': 'not ok',
        'T_case_pattern_command_mid': 'ok',
        'T_done_semi_true_last': 'ok',
        'T_esac_semi_true_last': 'ok',
        'T_fi_and_or_last': 'ok',
        'T_fi_and_true_last': 'not ok',
        'T_fi_or_true_last': 'ok',
        'T_fi_pipe_last': 'ok',
        'T_fi_redir_and_last': 'not ok',
        'T_fi_redir_last': 'not ok',
        'T_fi_redir_pipe_last': 'ok',
        'T_fi_semi_true_last': 'ok',
        'T_for_last': 'not ok',
        'T_for_mid': 'ok',
        'T_if_elif_last': 'not ok',
        'T_if_elif_mid': 'ok',
        'T_if_else_else_last': 'not ok',
        'T_if_else_else_mid': 'ok',
        'T_if_else_then_last': 'not ok',
        'T_if_else_then_mid': 'ok',
        'T_if_in_group_last': 'not ok',
        'T_if_in_helper_last': 'not ok',
        'T_if_in_subshell_mid': 'not ok',
        'T_if_last': 'not ok',
        'T_if_mid': 'ok',
        'T_if_nested_last': 'not ok',
        'T_if_nested_mid': 'ok',
        'T_if_oneliner_before_last': 'not ok',
        'T_if_oneliner_before_mid': 'ok',
        'T_until_last': 'not ok',
        'T_until_mid': 'ok',
        'T_while_condition_multiline': 'ok',
        'T_while_last': 'not ok',
        'T_while_mid': 'ok',
    }

    def sites(self, text, s):
        return [i for i, l in enumerate(text.split("\n")) if _BARE.match(l) and i not in s.heredoc_body]

    def test_the_scanner_agrees_with_bats_on_every_shape_of_the_register(self):
        shapes = ground_truth_shapes()
        self.assertEqual(sorted(shapes), sorted(self.RECORDED), "the register and the record cover the same shapes")
        disagreements = []
        for name in sorted(shapes):
            text = shapes[name]
            lines = text.split("\n")
            s, extents = scan(text), bash_test_extents(lines)
            verdicts = self.RECORDED[name].split(",")
            self.assertEqual(len(verdicts), len(extents), "%s: %d tests by bash's parse, %d verdicts recorded" % (name, len(extents), len(verdicts)))
            expected = sorted(i + 1 for i in self.sites(text, s)
                              for (o, c), v in zip(extents, verdicts) if c is not None and o < i < c and v == "ok")
            hits = [ln for ln, _ in s.hits]
            if hits != expected:
                disagreements.append("%s: bats %s; sites %s; expected flags %s; scanner flags %s\n%s"
                                     % (name, verdicts, [i + 1 for i in self.sites(text, s)], expected, hits, text))
        self.assertEqual(disagreements, [], "%d shapes where the scanner disagrees with bats:\n\n" % len(disagreements) + "\n".join(disagreements))

    def test_the_record_is_what_bats_says(self):
        shapes = ground_truth_shapes()
        if not shutil.which("bats"):
            print("bats is not on PATH: the recorded verdicts (bats 1.10.0) stand unverified in this run")
            return
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "home"))
            names = sorted(shapes)
            for n, name in enumerate(names):
                # each test renamed to carry the shape's index so the TAP lines map back to it (a @test line inside a heredoc or a
                # string is renamed too, harmlessly: bats-preprocess rewrites it either way)
                k = iter(range(1, 100))
                text = "\n".join(_TEST_LINE.sub(lambda m, n=n: m.group(0).replace(m.group(1), "s%03d_t%d" % (n, next(k)), 1), l)
                                 if _TEST_LINE.match(l) else l for l in shapes[name].split("\n"))
                with open(os.path.join(d, "%03d.bats" % n), "w", encoding="utf-8") as f:
                    f.write(text)
            r = subprocess.run(["bats", "-t", d], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                               env=dict(os.environ, HOME=os.path.join(d, "home"), TMPDIR=d))
        got = {}
        for line in r.stdout.splitlines():
            m = re.match(r"^(ok|not ok) \d+ s(\d{3})_t\d+", line)
            if m:
                got.setdefault(names[int(m.group(2))], []).append(m.group(1))
        got = {name: ",".join(v) for name, v in got.items()}
        self.assertEqual(got, self.RECORDED, "bats on this box against the record:\n" + r.stdout[-4000:] + r.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
