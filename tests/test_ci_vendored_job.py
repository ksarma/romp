#!/usr/bin/env python3
"""The vendored tooling tests run in a CI job of their own, with their own cap (.github/workflows/ci.yml, 2026-09-28).

The step "Vendored tooling and host-script tests (node --test)" ran at the end of the Shell job. At the fork's main 1d591384e
(run 36388144219) the Shell job took 31 min 50 s of its 35-minute cap: Run bats 700 s, then this step 1180 s, where at
ffab236bd (run 36308512751) the step took 67 s. The growth is fork PR #780's tracked-changes bash guard: batch 925 added
27,628 lines under tools/ and vendor/track-changents/, about 25,700 of them #780's. node --test runs files side by side and
a file's tests one after another, and the tests of one file, tools/romp-track-bash-guard.test.mjs, add up to about 1100 s
in that run's log (the slowest single test 222 s). With the step inside the Shell job, a PR that added more than about three
minutes of bats time (the job's margin at 1d591384e was 190 s) ran the job past its cap. Raising the Shell cap was declined,
since it would hide the growth; the step moved to its own job instead. The Shell cap was raised later, for the bats suite's
own growth (Run bats alone took 1850 s on Linux in run 36716348831): main had a flat 35 until fork PR 940 landed on
2026-10-04 with a line per OS, and check 4 holds the line; ci.yml's comment above that line carries the current figure.

THE PIN IS EXACT EQUALITY, read as text: CI's Python cells install no YAML library, as the other tests/test_ci_*.py modules
note. This module first held the job through a closed line reader that enumerated the shapes a line could take and the
fields a step could carry, and each audit found one more way to hide the job's red that the enumeration missed (a step's
shell:, working-directory: or env:, the checkout's with:, a step writing GITHUB_ENV, a job-level or workflow-level env:, a
second setup-node, a Unicode line separator). So nothing here enumerates ways to hide a red: the job is held equal to a
literal, and any change to it is red until the literal changes with it, on purpose. The checks:

1. The whole workflow ends its lines in LF alone: no CR, U+0085, U+2028 or U+2029 anywhere in it, read from its bytes
   (reading in text mode turns a CR into LF before a check could see it). YAML reads each of the four as a line break where
   this module splits at LF alone, so a key after one would sit on a line no check here reads. Every other check reads the
   file through the same refusal, so each of them is red too while one of the four is there.
2. The vendored-tooling job's block, with its comment-only lines removed and nothing else changed (indentation, trailing
   blanks, the blank line before the next job and every value stay as written), EQUALS EXPECTED_JOB: every key, step and
   field, both caps (30 on Linux, 90 on macOS) and the node version. The block runs from the job's key line to the next line
   that starts, after none or two spaces, with a character other than a blank or `#`: the next job's key or a top-level
   key. A line at one space, or one that a tab leads, is a key of neither mapping (YAML refuses both), so it stays inside
   the block, where the literal refuses it. A comment-only line inside a block scalar would be content, since YAML reads it
   as the scalar's text (content() keeps it); this job holds no block scalar, and adding one adds its indicator line, which
   the literal refuses. The same holds for a quoted scalar continued over lines: no line of the literal opens one. The job's
   key is also written once in jobs:, bare, quoted, with blanks before the colon or in any case, since the literal is read
   from one copy and YAML keeps the last; a second copy in those spellings is red here with the reason. A copy written as an
   explicit key (`? vendored-tooling`) or through an escape inside a quoted key is not read here: actionlint refuses both as
   a duplicated job key, and tests/test_ci_sdk_pin.py is red on both.
3. The workflow's top-level keys EQUAL TOP_KEYS, read as the text before the first colon of every top-level line that is
   not blank or a comment. A top-level env: or defaults: reaches every job, this one among them: an env: NODE_OPTIONS can
   make node skip every test, and a defaults: run: working-directory moves where the command runs. The ruling allowed either
   a check that those two keys are absent or an equality; the list is compared, so a quoted or spaced spelling of either, a
   merge key, a second YAML document (`---`) and any key added later are red with no spelling listed here. The on: block
   (its top-level line to the next top-level line, comment-only lines removed) EQUALS ON_LINES too. CI runs on a push to
   a batch branch, by hand and on the schedule, and on nothing else (the workflow's header): a paths or paths-ignore
   filter added to push, or its branch pattern narrowed, starts no run for the batch pushes it filters, and
   scripts/batch.py land then finds no CI run of the batch head and refuses the batch; an added trigger (a pull_request,
   a tags pattern on push, or main back on push) runs the whole matrix where no landing reads it. The value of name and
   the concurrency block stay free (tests/test_ci_workflow_concurrency.py reads concurrency, and its CiTriggers reads the
   triggers and the push filter).
   tests/test_ci_macos_schedule.py still reads the schedule and the dispatch: this equality refuses any change to the block,
   and that module says what the values held must mean (one weekly cron at a quiet hour Pacific, the manual dispatch kept)
   and ties them to every matrix expression's events, so a change made on purpose updates ON_LINES here and must still
   pass that module.
4. The Shell job's cap line EQUALS SHELL_CAP_LINE (60 minutes on macOS, 55 on Linux, in the python job's per-OS form;
   ci.yml's comment above the line sizes each, the slowest finished job of its OS plus 10 minutes rounded up to a multiple
   of 5. Main had a flat 35 until fork PR 940 landed on 2026-10-04 with 60 on macOS and 50 on Linux, the figures its
   branch had held since 2026-10-02, on measured runs, after 55 on macOS, on a projection, and 45 on Linux from
   2026-09-30. Fork PR 926, merging main after 940 landed, set the Linux figure to 55 by the rule): it is the only line at
   four spaces in that job holding
   "timeout", so a second copy, bare, quoted or as an explicit key, is red too (one whose quoted key spells the word through
   an escape is not read here; actionlint and tests/test_ci_sdk_pin.py refuse it). And the Shell job's lines that name
   node as a word or hold --test EQUAL SHELL_NODE_LINES, the manager handshake step's name line and run line. The ruling
   asked that the Shell job hold no node --test step, exactly; this module reads that as no node test there but the manager
   handshake's, whose step stays for T224's reason (it runs inside a check upstream's ruleset requires, so a red handshake
   blocks the merge there). Here too a `#` line inside a block scalar is read as text, so a node command written into a run
   block's heredoc counts. And the Shell job's last two steps, its node setup and the manager handshake step, EQUAL
   SHELL_TAIL, from the job's one setup-node line to its end: with working-directory: tools on the handshake step, node
   --test matches no file, runs no test and exits 0, and a step's shell:, env: (NODE_OPTIONS), with:, if: or
   continue-on-error: hides a red the same way, so the two steps are held whole (what a step before them does is not:
   see "Not held here" below). The node lines are read one line at a time, so among the forms they do not read are a run
   value in a quoted scalar continued over a line that starts with `#` (content() drops that line as a comment, where
   YAML reads it as the scalar's text) and a double-quoted run value that spells node or --test through a backslash
   escape (`\\x6eode -\\x2dtest`, or a word split over an escaped line break); tests/test_ci_sdk_pin.py refuses both
   forms in ci.yml (a quoted scalar continued past its line; a backslash escape in a double-quoted scalar). Nor is
   anything bash assembles from the run text read (a backslash-newline, quotes inside a word, a variable): the lines are
   read as text, and no module reads the shell's result.
5. The macOS cap, 90, is inside the literal (check 2), so it is pinned by equality with everything else.
6. Each moved job's name, the text of its name line before the first expression (`Vendored tooling (node --test, ` here;
   tests/test_ci_served_job.py reads the served-pages job's name up to its runner label, `Served pages (pytest, `, since that
   name has no expression), is held by exactly one content line (comment-only
   lines removed), in any case, across every *.yml and *.yaml file under .github/workflows, each read from its bytes and
   refused on a line break other than LF, as check 1 refuses one in ci.yml. A second job with the same check name, in
   ci.yml or in another workflow file, is red, whether its name is written bare, quoted, or with the runner's label in
   place of the expression (`Vendored tooling (node --test, ubuntu-latest)`, the name GitHub shows): a twin that runs true
   under the name would put a second check of that name beside the real one. That count reads one line's text, so a
   second check over the same files, read the same way, holds every name: line to its whole name (check_name_lines). A
   name: line is one whose `name` key, bare or quoted and in any case, opens the line after its indentation and any of
   the indicators `-` (a list item), `?` (an explicit key) and `:` (an explicit key's value), each followed by a blank,
   so a job written as an explicit key (`? twin`) whose value line opens with `: name:` is read; the key's column is the
   end of those indicators. It is red when its value is empty, is a block indicator (`|` or `>`, with any chomping or
   indentation indicator), holds a backslash, starts with a tag or an anchor (`!` or `&`: the tests after it read the
   value's first character, so a quoted value left open behind one would pass them), is an alias (`*`) or is a quoted
   scalar left open, or when the next line that is not blank is indented past the key (a comment line too, on the safe
   side): each is a name YAML assembles from later lines or from an anchor, or decodes from an escape. A line inside a
   block scalar that looks like a name: line is read too, which only refuses more. Every name: line of the workflow files
   passes the check today, and EachCheckRedsOnItsDefect plants in a second workflow file the three twins the fork PR's
   re-check found green (a name continued over two lines as a plain scalar, a name folded through `>-`, and a name spelled
   through `\\x20`), one plant per refusal and per indicator besides the dash, a name continued after a blank line, and a
   CR inside a name line, which check_name_lines reports itself. Check 6 is CLOSED: it is a pin beyond the ruled list, so
   a name form found after this goes into the list below as one line, with no re-check of this check. Not read here: a
   name key inside a flow mapping (`{name: ...}`); written as an explicit key (`? name`, its value on the next line's
   `:`); through an escape in a quoted key; after a tag or an anchor on the key (`!!str name:`, `&k name:`; one on the
   value is refused above); or as an alias of an anchored `name` (`*k :`).
   tests/test_ci_sdk_pin.py's YAML allowlist refuses all five forms in ci.yml; in the other workflow files no
   tests/test_ci_*.py module refuses them. Nor is a name assembled from pieces by an expression
   (`Vendored ${{ 'tooling' }} ...`).

The equality does not cover these, and they are kept:
  - the job's matrix lines equal the Shell job's: the literal holds this job's lines, and this check ties them to the Shell
    job's, so the job runs on exactly the Shell job's cells and the move lost none;
  - the Shell job's node-version line equals the literal's: the two jobs run the same node, as the job's comment says;
  - the command is on one line of the workflow, this job's: check 4 refuses a copy in the Shell job, and this refuses one in
    any other job, which would run the whole suite a second time under that job's cap. It reads one line at a time, so
    among the copies it does not read are the two forms check 4 names: a run value in a quoted scalar continued over a
    line that starts with `#`, and one that spells the command through a backslash escape in a double-quoted scalar (an
    escaped character, or the command split over an escaped line break); tests/test_ci_sdk_pin.py refuses both forms;
  - the Shell job's working-directory check, dropped when the equality came in, is back in a wider form, SHELL_TAIL (check
    4): the old check caught a working-directory on the handshake step, and SHELL_TAIL holds that step and its node setup
    whole.
Retired, since the equality covers them: the closed line reader and its shape tests, the job-key and step-field checks, the
checkout, setup-node and command checks, the node command rule over the Shell job's run text, the Shell job's job-level
defaults: check (a workflow-level defaults: is check 3's red), and the cap ranges. Not held here:
  - every job-level key of the Shell job but its cap and its matrix, whose lines are tied to this job's above (env,
    defaults, if, continue-on-error, needs and the rest). A
    job-level env: or defaults: there reaches the handshake step too; a defaults: run: working-directory also moves Run
    bats, and outside the root no directory of the tree holds tests/*.bats, so bats fails the job; a job-level env: is red
    today only in tests/test_ci_sdk_pin.py, through its synthetic splices, not by a check made for it;
  - what an earlier Shell step does to the handshake. SHELL_TAIL holds the handshake step and its node setup, and a step
    before them can still change what the handshake runs: one that writes NODE_OPTIONS to GITHUB_ENV (under
    --test-skip-pattern=. node runs none of the tests and exits 0), or one that deletes tests/manager-*.test.js, so node
    --test, handed the unmatched pattern by bash, reports tests 0 and exits 0. Holding the whole Shell block by equality
    was declined: every edit to a bats step would then be red, to catch a change no honest author makes.

EachCheckRedsOnItsDefect runs every check against a synthetic workflow built from the same constants: green as built, and red
on each change it plants, the hiding roads named above among them, so a check that stopped reading would be red there.

The caps in the literal. Linux, 30 minutes: the step took 1180 s (19 min 40 s) at 1d591384e, and 30 is that time and half
again. macOS, 90 minutes: the step has never run on macOS on the fork (it came after Run bats, which was red on every macOS
run there), so the cap starts from the estimate in the job's comment, 70 to 76 minutes: twice the Linux time, since the macOS
cells ran the Python suite about twice as long as the Linux cells, then 18 to 29 percent more for macOS's zsh legs, then half
again. 90 is 14 minutes past 76 because two of the estimate's inputs are weak (the job's comment names them). It is also past
the hour the python job's macOS cap keeps (tests/test_ci_bats_bound.py holds that cap at 60 or less, since past an hour a hung
cell holds the dispatch): the estimate alone is past that hour, so a hung macOS cell of this job holds a dispatch for up to
90 minutes. The first macOS run (a dispatch or the weekly schedule) measures the step; the cap is then re-read from it, and
the literal changes with it."""
import difflib
import os
import re
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
WF_DIR = os.path.join(os.path.dirname(HERE), ".github", "workflows")
WF = os.path.join(WF_DIR, "ci.yml")

JOB = "vendored-tooling"
STEP = "Vendored tooling and host-script tests (node --test)"
CMD = "node --test tools/*.test.mjs vendor/track-changents/hooks/*.test.mjs"

# The vendored-tooling job as ci.yml writes it, comment-only lines removed and nothing else changed, one line per item: the
# key line, the job's keys, its matrix, its three steps, and the blank line before the next job.
EXPECTED_JOB = (
    "  vendored-tooling:",
    "    name: Vendored tooling (node --test, ${{ matrix.os }})",
    "    runs-on: ${{ matrix.os }}",
    "    timeout-minutes: ${{ matrix.os == 'macos-latest' && 90 || 30 }}",
    "    strategy:",
    "      fail-fast: false",
    "      matrix:",
    "        os: ${{ fromJSON((github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && "
    "'[\"ubuntu-latest\",\"macos-latest\"]' || '[\"ubuntu-latest\"]') }}",
    "    steps:",
    "      - uses: actions/checkout@v4",
    "      - uses: actions/setup-node@v4",
    "        with:",
    "          node-version: '22'",
    "      - name: " + STEP,
    "        run: " + CMD,
    "",
)
# The job's name before its first expression: the text check 6 finds on exactly one content line of the workflow files.
NAME_TEXT = "Vendored tooling (node --test, "
# The workflow's top-level keys, in file order: the text before the first colon of each top-level line.
TOP_KEYS = ["name", "on", "concurrency", "jobs"]
# The workflow's on: block as ci.yml writes it, comment-only lines removed (the trailing comments on two lines are content):
# its top-level line to the blank line before the next top-level line.
ON_LINES = (
    "on:",
    "  push:",
    "    branches: ['batch/**']",
    "  workflow_dispatch:   # the manual on-switch for the macOS cells (see above)",
    "  schedule:",
    '    - cron: "0 10 * * 1"   # weekly macOS cells: the scheduled run selects the same matrix a manual dispatch does',
    "",
)
# The Shell job's cap: the only line at four spaces in that job that holds "timeout". One per OS, in the python job's form:
# the slowest measured or projected job plus 10 minutes, rounded up to a multiple of 5 (ci.yml's comment above the line
# carries the measurement: Linux 40 min 43 s in run 37128151383, job 111217616222, the slowest among the finished runs on
# main, the batch branches and the branches of the open and merged PRs, read at 03:32 UTC on 2026-10-04, its Run bats
# step 2365 s, so 55; macOS 48 min 1 s in run 37045964763, job 110967357963, the slowest macOS job among those runs, its
# Run bats step 2856 s, so 60). Fork PR 940, since merged, set this line, at 60 on macOS and 50 on Linux; fork PR 926,
# merging main after 940 landed, set the Linux figure to 55 by the rule.
SHELL_CAP_LINE = "    timeout-minutes: ${{ matrix.os == 'macos-latest' && 60 || 55 }}"
# The Shell job's lines that name node as a word or hold --test: the manager handshake step's name and run lines (T224).
SHELL_NODE_LINES = (
    "      - name: Manager handshake tests (node --test)",
    "        run: node --test tests/manager-*.test.js",
)
# The Shell job's last two steps, comment-only lines removed, from its one setup-node line to the blank line before the next
# job: the node setup and the manager handshake step (T224), every field of both.
SHELL_TAIL = (
    "      - uses: actions/setup-node@v4",
    "        with:",
    "          node-version: '22'",
    "      - name: Manager handshake tests (node --test)",
    "        run: node --test tests/manager-*.test.js",
    "",
)

# Every line break YAML knows other than LF.
FOREIGN_BREAKS = {"\r": "CR", "\x85": "U+0085 (NEXT LINE)", "\u2028": "U+2028 (LINE SEPARATOR)",
                  "\u2029": "U+2029 (PARAGRAPH SEPARATOR)"}
# A top-level line: its first character is not a blank or `#`.
TOP_LINE = re.compile(r"[^ \t#]")
# The line that ends a job's block: after none or two spaces, a character that is not a blank or `#`.
BLOCK_END = re.compile(r"(?:  )?[^ \t#]")
# A key line at two spaces (a job's key): bare or quoted, blanks allowed before the colon.
JOB_KEY_LINE = re.compile(r"  (?P<key>[^ \t#:][^:]*?)[ \t]*:(?:[ \t].*)?")
# A line whose value is a block scalar's indicator (`|` or `>`, with its chomping and indentation indicators), or a line that
# is that indicator alone. Read on the safe side: a plain value ending in ` |` counts too, which only keeps more lines.
BLOCK_SCALAR = re.compile(r"(?:^|[ \t])[|>][1-9+-]{0,2}[ \t]*(?:#.*)?$")
# A name: line: a `name` key, bare or quoted, in any case, at the line's start after its indentation and any of the
# indicators `-` (a list item), `?` (an explicit key) and `:` (an explicit key's value), each followed by a blank; `lead`
# runs to the key's column, `value` is the text after the colon.
NAME_KEY_LINE = re.compile(r"(?P<lead>[ \t]*(?:[-?:][ \t]+)*)(?P<q>[\"']?)name(?P=q)[ \t]*:(?P<value>(?:[ \t].*)?)", re.I)
# node named as a word (not setup-node, node-version or node_modules), and a --test flag.
NODE_WORD = re.compile(r"(?<![\w.-])node(?:js)?(?![\w.-])")
TEST_FLAG = re.compile(r"(?<![\w-])--test(?![\w-])")


class WorkflowShape(ValueError):
    """The workflow cannot be read as this module reads it: a line break other than LF, or a job or key absent or written
    more than once."""


def raw(path=WF):
    """The workflow's text, decoded from its bytes, so a CR reaches the checks (text mode would turn it into LF)."""
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def foreign_breaks(src):
    """[(line number, name)] of every line break other than LF in src, lines counted at LF."""
    return [(n, FOREIGN_BREAKS[ch]) for n, line in enumerate(src.split("\n"), 1) for ch in line if ch in FOREIGN_BREAKS]


def lines(src, who="ci.yml"):
    """src split at LF, refusing a src that holds any other line break (check 1's reason); `who` names the file."""
    found = foreign_breaks(src)
    if found:
        raise WorkflowShape("%s holds line breaks other than LF (%s): YAML reads each as a line break and this module "
                            "splits at LF alone, so no check here can say it read the file whole"
                            % (who, "; ".join("line %d: %s" % f for f in found)))
    return src.split("\n")


def _unquote(key):
    return key[1:-1] if len(key) >= 2 and key[0] == key[-1] and key[0] in "'\"" else key


def top_keys(ls):
    """The text before the first colon of every top-level line (its first character not a blank or `#`), in file order."""
    return [l.split(":", 1)[0] for l in ls if TOP_LINE.match(l)]


def job_block(key, ls):
    """The lines of the job under `  <key>:` in the jobs: section, from its key line to the line before the next line that
    BLOCK_END matches, comment and blank lines included. Raises WorkflowShape when jobs: is not one top-level line, or the
    job's key, compared with its quotes dropped and in lower case, is absent or written more than once."""
    tops = [i for i, l in enumerate(ls) if TOP_LINE.match(l)]
    at = [i for i in tops if ls[i].split(":", 1)[0] == "jobs"]
    if len(at) != 1:
        raise WorkflowShape("ci.yml has %d top-level `jobs` lines (lines %s), where this module reads one"
                            % (len(at), [i + 1 for i in at]))
    end = min([i for i in tops if i > at[0]] + [len(ls)])
    hits = [i for i in range(at[0] + 1, end)
            if JOB_KEY_LINE.fullmatch(ls[i]) and _unquote(JOB_KEY_LINE.fullmatch(ls[i]).group("key")).lower() == key]
    if not hits:
        raise WorkflowShape("ci.yml has no job `%s` under jobs:" % key)
    if len(hits) > 1:
        raise WorkflowShape("the job `%s` is written %d times under jobs: (lines %s); YAML keeps the last copy and this "
                            "module reads one" % (key, len(hits), [i + 1 for i in hits]))
    stop = hits[0] + 1
    while stop < end and not BLOCK_END.match(ls[stop]):
        stop += 1
    return ls[hits[0]:stop]


def content(ls):
    """ls less its comment-only lines (a line whose first character that is not a blank is `#`), except inside a block
    scalar, where YAML reads such a line as the scalar's text and it is kept. Nothing else is changed."""
    out, scalar = [], None   # scalar: the indentation of an open block scalar's indicator line
    for l in ls:
        if scalar is not None:
            if not l.strip(" \t") or len(l) - len(l.lstrip(" ")) > scalar:
                out.append(l)
                continue
            scalar = None
        if l.lstrip(" \t").startswith("#"):
            continue
        out.append(l)
        if BLOCK_SCALAR.search(l):
            scalar = len(l) - len(l.lstrip(" "))
    return out


def _lines_or_fault(src):
    try:
        return lines(src), None
    except WorkflowShape as e:
        return None, [str(e)]


def _block_or_fault(key, src):
    ls, fault = _lines_or_fault(src)
    if fault:
        return None, fault
    try:
        return content(job_block(key, ls)), None
    except WorkflowShape as e:
        return None, [str(e)]


def check_line_breaks(src):
    """Check 1: every line break other than LF, by line."""
    return ["line %d: %s" % f for f in foreign_breaks(src)]


def check_job(src):
    """Check 2: the job's block, comment-only lines removed, against EXPECTED_JOB."""
    block, fault = _block_or_fault(JOB, src)
    if fault:
        return fault
    return [] if block == list(EXPECTED_JOB) else _diff(EXPECTED_JOB, block, "EXPECTED_JOB")


def check_top_keys(src):
    """Check 3: the workflow's top-level keys against TOP_KEYS."""
    ls, fault = _lines_or_fault(src)
    if fault:
        return fault
    keys = top_keys(ls)
    return [] if keys == TOP_KEYS else ["the top-level keys are %r, not %r" % (keys, TOP_KEYS)]


def on_block(ls):
    """The lines of the workflow's on: block, from its one top-level line whose text before the first colon is `on` to the
    line before the next top-level line, comment and blank lines included. Raises WorkflowShape unless there is one."""
    tops = [i for i, l in enumerate(ls) if TOP_LINE.match(l)]
    at = [i for i in tops if ls[i].split(":", 1)[0] == "on"]
    if len(at) != 1:
        raise WorkflowShape("ci.yml has %d top-level `on` lines (lines %s), where this module reads one"
                            % (len(at), [i + 1 for i in at]))
    end = min([i for i in tops if i > at[0]] + [len(ls)])
    return ls[at[0]:end]


def _diff(want, got, name):
    """A failure's text: the unified diff of the constant `name` against what ci.yml has, then the lines to paste."""
    diff = difflib.unified_diff(list(want), got, name, "ci.yml", lineterm="", n=1)
    return ["\n".join(diff), "the lines as ci.yml has them, to paste into %s if the change is meant:\n" % name
            + "\n".join("    %r," % l for l in got)]


def check_on_block(src):
    """Check 3, the triggers: the on: block, comment-only lines removed, against ON_LINES."""
    ls, fault = _lines_or_fault(src)
    if fault:
        return fault
    try:
        block = content(on_block(ls))
    except WorkflowShape as e:
        return [str(e)]
    return [] if block == list(ON_LINES) else _diff(ON_LINES, block, "ON_LINES")


def check_shell_cap(src):
    """Check 4, the cap: the Shell job's lines at four spaces that hold `timeout`, against [SHELL_CAP_LINE]."""
    block, fault = _block_or_fault("shell", src)
    if fault:
        return fault
    caps = [l for l in block if re.match(r"    [^ \t]", l) and "timeout" in l.lower()]
    return [] if caps == [SHELL_CAP_LINE] else ["the Shell job's cap lines are %r, not [%r]" % (caps, SHELL_CAP_LINE)]


def check_shell_node(src):
    """Check 4, node: the Shell job's lines that name node or hold --test, against SHELL_NODE_LINES. One line at a time: a
    run value in a quoted scalar continued over a line that starts with `#`, or one spelling node or --test through a
    backslash escape in a double-quoted scalar, is not read here (tests/test_ci_sdk_pin.py refuses both forms)."""
    block, fault = _block_or_fault("shell", src)
    if fault:
        return fault
    found = [l for l in block if NODE_WORD.search(l) or TEST_FLAG.search(l)]
    return [] if found == list(SHELL_NODE_LINES) else ["the Shell job's lines naming node or --test are %r, not %r"
                                                      % (found, list(SHELL_NODE_LINES))]


def check_shell_tail(src):
    """Check 4, the handshake: the Shell job's block from its one setup-node line to its end, comment-only lines removed,
    against SHELL_TAIL."""
    block, fault = _block_or_fault("shell", src)
    if fault:
        return fault
    at = [i for i, l in enumerate(block) if l == SHELL_TAIL[0]]
    if len(at) != 1:
        return ["the Shell job has %d lines %r, where SHELL_TAIL begins at its one such line" % (len(at), SHELL_TAIL[0])]
    tail = block[at[0]:]
    return [] if tail == list(SHELL_TAIL) else _diff(SHELL_TAIL, tail, "SHELL_TAIL")


def matrix_lines(block, who):
    """The lines under a job's one `      matrix:` line: the blank lines and the lines deeper than six spaces after it."""
    at = [i for i, l in enumerate(block) if l == "      matrix:"]
    if len(at) != 1:
        raise WorkflowShape("%s has %d lines `      matrix:`, where this check reads one" % (who, len(at)))
    out = []
    for l in block[at[0] + 1:]:
        if l.strip(" \t") and not l.startswith("       "):
            break
        out.append(l)
    while out and not out[-1].strip(" \t"):
        out.pop()
    return out


def check_matrix_tie(src):
    """Kept: the job's matrix lines equal the Shell job's."""
    mine, fault = _block_or_fault(JOB, src)
    shell, fault2 = _block_or_fault("shell", src)
    if fault or fault2:
        return (fault or []) + (fault2 or [])
    try:
        a, b = matrix_lines(mine, "the vendored-tooling job"), matrix_lines(shell, "the Shell job")
    except WorkflowShape as e:
        return [str(e)]
    return [] if a == b else ["the vendored-tooling job's matrix lines are %r and the Shell job's %r" % (a, b)]


def check_node_version_tie(src):
    """Kept: the Shell job's node-version lines equal the literal's one node-version line."""
    shell, fault = _block_or_fault("shell", src)
    if fault:
        return fault
    want = [l for l in EXPECTED_JOB if "node-version" in l]
    found = [l for l in shell if "node-version" in l]
    return [] if found == want else ["the Shell job's node-version lines are %r, not %r" % (found, want)]


def check_command_once(src):
    """Kept: the command is on one line of the workflow, comment-only lines aside. One line at a time: a copy in a quoted
    scalar continued over a line that starts with `#`, or spelled through a backslash escape in a double-quoted scalar, is
    not read here (tests/test_ci_sdk_pin.py refuses both forms)."""
    ls, fault = _lines_or_fault(src)
    if fault:
        return fault
    found = [l for l in content(ls) if CMD in l]
    return [] if len(found) == 1 else ["the command is on %d lines: %r" % (len(found), found)]


def workflow_texts(root=WF_DIR):
    """[(path under root, text)] of every file under root, at any depth, whose name ends in .yml or .yaml in any case, each
    decoded from its bytes (so a CR reaches check 6), in path order. GitHub reads the files directly under
    .github/workflows alone; reading deeper only counts more lines."""
    out = []
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for f in sorted(files):
            if f.lower().endswith((".yml", ".yaml")):
                out.append((os.path.relpath(os.path.join(d, f), root), raw(os.path.join(d, f))))
    return out


def check_name_once(name_text, texts):
    """Check 6: the content lines of texts ([(file, text)], comment-only lines removed) that hold name_text in any case;
    no fault when there is exactly one. A file holding a line break other than LF is a fault, as check 1 is for ci.yml."""
    hits, faults = [], []
    for f, text in texts:
        try:
            ls = lines(text, f)
        except WorkflowShape as e:
            faults.append(str(e))
            continue
        hits += ["%s: %s" % (f, l.strip()) for l in content(ls) if name_text.lower() in l.lower()]
    if faults:
        return faults
    return [] if len(hits) == 1 else ["the name %r is held by %d content lines of the workflow files, where it is one job's "
                                      "name line alone: %r" % (name_text, len(hits), hits)]


def name_line_fault(ls, i, m):
    """Why the name: line ls[i] (m, its NAME_KEY_LINE match) does not hold its whole name on that line, or None when it
    does."""
    value, col = m.group("value").strip(" \t"), len(m.group("lead"))
    if not value or value.startswith("#"):
        return "its value is empty, so YAML reads the name from the lines below"
    if "\\" in value:
        return "its value holds a backslash, which a double-quoted scalar decodes as an escape"
    if BLOCK_SCALAR.search(value):
        return "its value is a block scalar's indicator, so YAML reads the name from the lines below"
    if value[0] in "!&":
        return ("its value starts with a tag or an anchor, and the tests after this one read the value's first character, so "
                "a quoted value left open behind one would pass them")
    if value.startswith("*"):
        return "its value is an alias, so the name is written where the anchor is"
    rest = value[1:].replace("''", "") if value[0] == "'" else value[1:]
    if value[0] in "\"'" and value[0] not in rest:
        return "its quoted value is left open, so YAML reads the name on into the lines below"
    nxt = next((j for j in range(i + 1, len(ls)) if ls[j].strip(" \t")), None)
    if nxt is not None and len(ls[nxt]) - len(ls[nxt].lstrip(" \t")) > col:
        return "line %d, the next line that is not blank, is indented past the key, so YAML continues the value there" % (
            nxt + 1)
    return None


def check_name_lines(texts):
    """Check 6, the name lines: every name: line of texts ([(file, text)]) holds its whole name on that line, so the count
    check_name_once makes reads the name whole. A fault for each line that does not, for a file holding a line break
    other than LF, as check 1 is for ci.yml, and for texts that hold no name: line at all, since a check that read none
    would pass on nothing."""
    out, read = [], 0
    for f, text in texts:
        try:
            ls = lines(text, f)
        except WorkflowShape as e:
            out.append(str(e))
            continue
        for i, l in enumerate(ls):
            m = NAME_KEY_LINE.fullmatch(l)
            read += bool(m)
            why = m and name_line_fault(ls, i, m)
            if why:
                out.append("%s line %d, %r: %s" % (f, i + 1, l.strip(" \t"), why))
    if not read and not out:
        out.append("no name: line in the %d workflow texts read, so this check read nothing" % len(texts))
    return out


class VendoredToolingJob(unittest.TestCase):
    def assertNoFaults(self, faults, why):
        if faults:
            self.fail("%s\n%s" % ("\n".join(faults), why))

    def test_1_the_workflow_breaks_its_lines_at_lf_alone(self):
        self.assertNoFaults(check_line_breaks(raw()), (
            "ci.yml holds line breaks other than LF (above, by line). YAML reads each as a line break, and this module "
            "splits the file at LF alone, so a key after one would sit on a line no check here reads. Write the file with LF "
            "line ends and none of these characters: no workflow change needs one, so there is nothing to update here."))

    def test_2_the_job_equals_the_expected_literal(self):
        self.assertNoFaults(check_job(raw()), (
            "The vendored-tooling job in ci.yml, comment-only lines aside, is not EXPECTED_JOB (above: the diff and the job "
            "as ci.yml has it, or the reason the job could not be read). Any field of the job can turn a failing or unrun vendored suite green (a step's shell:, "
            "working-directory: or env:, the checkout's with:, a step writing GITHUB_ENV, a job-level env:, if: or "
            "continue-on-error:, a second setup-node), so the whole job is held. If the change is meant, replace EXPECTED_JOB "
            "in tests/test_ci_vendored_job.py with the lines printed above and say in the commit why the job changed."))

    def test_3_the_workflow_top_level_holds_no_env_or_defaults(self):
        self.assertNoFaults(check_top_keys(raw()), (
            "The workflow's top-level keys changed (above). A top-level env: or defaults: reaches every job, the "
            "vendored-tooling job among them: an env: NODE_OPTIONS can make node skip every test, and a defaults: run: "
            "working-directory moves where the command runs. If the new key is meant and sets nothing a job's steps read, add "
            "it to TOP_KEYS in tests/test_ci_vendored_job.py and say why in the commit."))

    def test_3_the_workflow_triggers_equal_the_expected_literal(self):
        self.assertNoFaults(check_on_block(raw()), (
            "The workflow's on: block, comment-only lines aside, is not ON_LINES (above: the diff and the block as ci.yml has "
            "it, or the reason it could not be read). A paths or paths-ignore filter added to push, or its branch pattern "
            "narrowed, starts no CI run for the batch pushes it filters (scripts/batch.py land then finds no CI run of the "
            "batch head and refuses the batch), and an added trigger runs the whole matrix where no landing reads it, so the "
            "whole block is held. If the change is meant, replace ON_LINES in tests/test_ci_vendored_job.py with the lines "
            "printed above, check that tests/test_ci_macos_schedule.py and tests/test_ci_workflow_concurrency.py still pass, "
            "and say in the commit why the triggers changed."))

    def test_4_the_shell_cap_is_60_on_macos_and_55_on_linux(self):
        self.assertNoFaults(check_shell_cap(raw()), (
            "The Shell job's cap changed (above). It is set per OS from a measurement, the slowest measured or projected "
            "job plus 10 minutes rounded up to a multiple of 5 (ci.yml's comment above the line: Linux 40 min 43 s in run "
            "37128151383, the slowest among the finished runs on main, the batch branches and the branches of the open "
            "and merged PRs, read at 03:32 UTC on 2026-10-04, so 55; macOS 48 min 1 s in run 37045964763, so 60; fork PR "
            "940, since merged, set the line at 60 and 50, and fork PR 926, merging main after it, set the Linux figure "
            "to 55 by the rule). A higher cap hides growth the vendored "
            "tooling move was meant to show, and a lower one cuts a passing cell. If the change is meant, measure the job "
            "again, update SHELL_CAP_LINE in tests/test_ci_vendored_job.py and ci.yml's comment, and say why in the commit."))

    def test_4_the_shell_job_runs_no_node_test_but_the_handshake(self):
        self.assertNoFaults(check_shell_node(raw()), (
            "The Shell job's lines that name node or hold --test changed (above; comment-only lines aside, while a `#` line "
            "inside a block scalar counts, since YAML reads it as text). The vendored tooling tests moved to the "
            "vendored-tooling job (at 1d591384e they took 1180 s of the Shell job's 31 min 50 s under its 35-minute cap), "
            "and the manager handshake step stays in the Shell job for T224's reason. A node --test over tools/ or vendor/ "
            "belongs in the vendored-tooling job. If the handshake step's name or command changed on purpose, update "
            "SHELL_NODE_LINES in tests/test_ci_vendored_job.py and say why in the commit."))

    def test_4_the_shell_jobs_node_setup_and_handshake_step_equal_the_expected_literal(self):
        self.assertNoFaults(check_shell_tail(raw()), (
            "The Shell job's last two steps, its node setup and the manager handshake step, comment-only lines aside, are "
            "not SHELL_TAIL (above: the diff and the lines as ci.yml has them, or the reason they could not be read). A "
            "working-directory: on the handshake step makes node --test match no file, run no test and exit 0, and a step's "
            "shell:, env:, with:, if: or continue-on-error: can hide a red the same way, so both steps are held. If the change "
            "is meant, replace SHELL_TAIL in tests/test_ci_vendored_job.py with the lines printed above and say in the commit "
            "why the steps changed."))

    def test_6_the_jobs_name_is_on_one_line_of_the_workflow_files(self):
        self.assertNoFaults(check_name_once(NAME_TEXT, workflow_texts()), (
            "The vendored-tooling job's name is not held by exactly one content line of the workflow files (above). A second "
            "job of that name, in ci.yml or in another workflow file, puts a second check of that name beside the job's own, "
            "and one that runs true under it reads green. Rename the other job; if the name itself changed on purpose, update "
            "NAME_TEXT and EXPECTED_JOB together."))

    def test_6_every_name_line_of_the_workflow_files_holds_its_whole_name(self):
        self.assertNoFaults(check_name_lines(workflow_texts()), (
            "A name: line of the workflow files does not hold its whole name on that line (above). YAML assembles such a "
            "name from later lines or from an anchor, or decodes it from an escape, and the name checks here and in "
            "tests/test_ci_served_job.py count one line's text, so a second job named that way could put a second check "
            "of a moved job's name beside the real one unseen. Write the name whole on its line, as a plain scalar or a "
            "quoted one with no escape."))

    def test_the_job_runs_on_the_shell_jobs_matrix(self):
        self.assertNoFaults(check_matrix_tie(raw()), (
            "The vendored-tooling job's matrix and the Shell job's differ (above). The job runs on the Shell job's cells "
            "(ubuntu-latest always, macOS on a manual run or the weekly schedule), so moving the step lost none. If the "
            "Shell job's matrix changed on purpose, give the vendored-tooling job the same lines and update EXPECTED_JOB."))

    def test_the_two_jobs_pin_the_same_node(self):
        self.assertNoFaults(check_node_version_tie(raw()), (
            "The Shell job's node-version and the vendored-tooling job's differ (above): the two jobs run the same node, as "
            "the job's comment says. If one changed on purpose, change both, and EXPECTED_JOB with them."))

    def test_the_command_runs_in_this_job_alone(self):
        self.assertNoFaults(check_command_once(raw()), (
            "The vendored tooling command is not on exactly one line of ci.yml (above, comment-only lines aside). It runs "
            "once, in the vendored-tooling job; a copy in another job runs the whole suite a second time under that job's "
            "cap. If a second run is meant, change this check and say why in the commit."))


def check_name_once_in(src):
    """Check 6 over one workflow text, the synthetic workflow's form of it."""
    return check_name_once(NAME_TEXT, [("ci.yml", src)])


def check_name_lines_in(src):
    """Check 6's name lines over one workflow text, the synthetic workflow's form of it."""
    return check_name_lines([("ci.yml", src)])


class EachCheckRedsOnItsDefect(unittest.TestCase):
    """Every check against a synthetic workflow built from the module's constants: green as built, red on each change planted
    into it. The plants include each way round 1 of the fork PR's review found to hide the job's red, a CR, the three Unicode
    line breaks and a legitimate one-field edit, and the roads the round-1 audit found outside the job (the handshake step's
    fields, a trigger filter, a second job of the same name), and a name: line whose name YAML assembles from later lines or
    decodes from an escape."""
    CHECKS = (check_line_breaks, check_job, check_top_keys, check_on_block, check_shell_cap, check_shell_node,
              check_shell_tail, check_matrix_tie, check_node_version_tie, check_command_once, check_name_once_in,
              check_name_lines_in)

    @staticmethod
    def synthetic():
        os_line = [l for l in EXPECTED_JOB if l.startswith("        os: ")]
        version = [l for l in EXPECTED_JOB if "node-version" in l]
        on = list(ON_LINES)
        on[-2:-2] = ["    # a comment inside the on: block"]
        top = ["name: CI", "# a comment"] + on + ["# a comment", "concurrency:", "  group: g", "jobs:"]
        tail = list(SHELL_TAIL)
        tail[3:3] = ["      # a comment before the handshake step"]
        shell = (["  shell:", "    name: Shell (bats)", "    # node --test tools, a comment", "    runs-on: ${{ matrix.os }}",
                  SHELL_CAP_LINE, "    strategy:", "      fail-fast: false", "      matrix:"] + os_line
                 + ["    steps:", "      - name: Run bats", "        timeout-minutes: 5", "        run: |",
                    "          # a shell comment", "          bats tests/*.bats", ""] + tail)
        job = list(EXPECTED_JOB)
        job[1:1] = ["# a comment at the top level's column", "  # a comment at a job key's column", "    # a comment"]
        job[-1:-1] = ["        # a comment deeper than the step"]
        return "\n".join(top + shell + job + ["  # the next job", "  vscode-extension:", "    runs-on: ubuntu-latest", ""])

    def plant(self, src, where, anchor, new):
        """src with the one line `anchor` inside `where` (shell, job, or top: the lines before jobs:) replaced by the lines
        `new`; anchor None appends `new` at the end of the file. Fails unless the anchor is there exactly once."""
        ls = src.split("\n")
        if anchor is None:
            return "\n".join(ls[:-1] + new + ls[-1:])
        lo, hi = {"top": (0, ls.index("jobs:")), "shell": (ls.index("  shell:"), ls.index("  vendored-tooling:")),
                  "job": (ls.index("  vendored-tooling:"), ls.index("  vscode-extension:"))}[where]
        at = [i for i in range(lo, hi) if ls[i] == anchor]
        self.assertEqual(len(at), 1, "the plant's anchor %r is in the %s part once" % (anchor, where))
        return "\n".join(ls[:at[0]] + new + ls[at[0] + 1:])

    def test_the_synthetic_workflow_passes_every_check(self):
        src = self.synthetic()
        for check in self.CHECKS:
            self.assertEqual(check(src), [], check.__name__)
        self.assertIn([l for l in EXPECTED_JOB if "node-version" in l][0], SHELL_TAIL, "the synthetic Shell job's node version "
                      "comes from SHELL_TAIL, and it is the literal's")

    def test_each_plant_reds_its_check(self):
        src = self.synthetic()
        run, name, cap = "        run: " + CMD, "      - name: " + STEP, EXPECTED_JOB[3]
        checkout, key = "      - uses: actions/checkout@v4", "    name: Vendored tooling (node --test, ${{ matrix.os }})"
        bats, os_line = "          bats tests/*.bats", [l for l in EXPECTED_JOB if l.startswith("        os: ")][0]
        plants = (
            (check_job, "the step's shell:", "job", run, [run, "        shell: true {0}"]),
            (check_job, "the step's working-directory:", "job", run, [run, "        working-directory: tools"]),
            (check_job, "the step's env:", "job", run, [run, "        env:", "          NODE_OPTIONS: --test-skip-pattern=."]),
            (check_job, "the checkout's with:", "job", checkout, [checkout, "        with:", "          sparse-checkout: README.md"]),
            (check_job, "a step writing GITHUB_ENV", "job", name,
             ['      - run: echo "NODE_OPTIONS=--test-skip-pattern=." >> "$GITHUB_ENV"', name]),
            (check_job, "a job-level env:", "job", key, [key, "    env:", "      NODE_OPTIONS: --test-skip-pattern=."]),
            (check_job, "a job-level env: from an expression", "job", key, [key, "    env: ${{ fromJSON('{}') }}"]),
            (check_job, "a job-level if: after the steps", "job", run, [run, "    if: false"]),
            (check_job, "a job-level continue-on-error: after a comment", "job", run,
             [run, "    # a comment", "    continue-on-error: true"]),
            (check_job, "a second setup-node", "job", name,
             ["      - uses: actions/setup-node@v5", "        with:", "          node-version: '20'", name]),
            (check_job, "a merge key", "job", key, [key, "    <<: *skip"]),
            (check_job, "a quoted key", "job", key, [key, "    \"if\": false"]),
            (check_job, "a step-level if:", "job", run, [run, "        if: false"]),
            (check_job, "a container:", "job", key, [key, "    container: node:22"]),
            (check_job, "the Linux cap 30 to 31, a legitimate one-field edit", "job", cap, [cap.replace("|| 30", "|| 31")]),
            (check_job, "the macOS cap 90 to 60", "job", cap, [cap.replace("&& 90", "&& 60")]),
            (check_job, "a trailing blank", "job", run, [run + " "]),
            (check_job, "a line at one space", "job", run, [run, " if: false"]),
            (check_job, "a line a tab leads", "job", run, [run, "\tif: false"]),
            (check_job, "a run block scalar holding the command", "job", run,
             ["        run: |", "          # node --test", "          " + CMD]),
            (check_job, "the job's key renamed", "job", "  vendored-tooling:", ["  vendored-tools:"]),
            (check_job, "the job's key written twice", None, None, ["  'Vendored-Tooling' :", "    runs-on: ubuntu-latest"]),
            (check_top_keys, "a workflow env:", "top", "concurrency:",
             ["env:", "  NODE_OPTIONS: --test-skip-pattern=.", "concurrency:"]),
            (check_top_keys, "a workflow defaults:", "top", "concurrency:",
             ["defaults:", "  run:", "    working-directory: tools", "concurrency:"]),
            (check_top_keys, "a quoted workflow env:", "top", "concurrency:", ["\"env\": {NODE_OPTIONS: x}", "concurrency:"]),
            (check_top_keys, "a second YAML document", None, None, ["---", "env:", "  NODE_OPTIONS: x"]),
            (check_on_block, "a paths-ignore filter on push", "top", "  push:",
             ["  push:", "    paths-ignore: [tools/**, vendor/**, hooks/**]"]),
            (check_on_block, "a paths filter on push", "top", "  push:", ["  push:", "    paths: [kernel/**]"]),
            (check_on_block, "a tags filter on push", "top", "  push:", ["  push:", "    tags: ['v*']"]),
            (check_on_block, "the push branch pattern narrowed", "top", "    branches: ['batch/**']", ["    branches: ['batch/x']"]),
            (check_on_block, "a pull_request trigger added", "top", "  push:", ["  pull_request:", "  push:"]),
            (check_on_block, "push replaced by pull_request", "top", "  push:", ["  pull_request:"]),
            (check_on_block, "the push branch filter widened to main", "top", "    branches: ['batch/**']",
             ["    branches: ['batch/**', main]"]),
            (check_top_keys, "a second, quoted on key", "top", "concurrency:", ["\"on\": [workflow_dispatch]", "concurrency:"]),
            (check_shell_cap, "the Shell cap back to the flat 35", "shell", SHELL_CAP_LINE, ["    timeout-minutes: 35"]),
            (check_shell_cap, "the Shell cap a flat 55", "shell", SHELL_CAP_LINE, ["    timeout-minutes: 55"]),
            (check_shell_cap, "the macOS Shell cap 60 to 65", "shell", SHELL_CAP_LINE, [SHELL_CAP_LINE.replace("&& 60", "&& 65")]),
            (check_shell_cap, "the macOS Shell cap 60 to 55", "shell", SHELL_CAP_LINE, [SHELL_CAP_LINE.replace("&& 60", "&& 55")]),
            (check_shell_cap, "the Linux Shell cap 55 to 50", "shell", SHELL_CAP_LINE, [SHELL_CAP_LINE.replace("|| 55", "|| 50")]),
            (check_shell_cap, "the Linux Shell cap 55 to 60", "shell", SHELL_CAP_LINE, [SHELL_CAP_LINE.replace("|| 55", "|| 60")]),
            (check_shell_cap, "the two Shell caps swapped", "shell", SHELL_CAP_LINE,
             ["    timeout-minutes: ${{ matrix.os == 'macos-latest' && 55 || 60 }}"]),
            (check_shell_cap, "the Shell caps keyed on the other OS", "shell", SHELL_CAP_LINE,
             ["    timeout-minutes: ${{ matrix.os == 'ubuntu-latest' && 60 || 55 }}"]),
            (check_shell_cap, "a second Shell cap after the steps", "shell", SHELL_NODE_LINES[1],
             [SHELL_NODE_LINES[1], "    \"timeout-minutes\": 90"]),
            (check_shell_node, "the step put back in the Shell job", "shell", SHELL_NODE_LINES[1],
             [SHELL_NODE_LINES[1], name, run]),
            (check_shell_node, "a bare node --test in the Shell job", "shell", SHELL_NODE_LINES[1],
             [SHELL_NODE_LINES[1], "      - run: node --test"]),
            (check_shell_node, "a node command behind `#` in a run block's heredoc", "shell", bats,
             [bats, "          sed 's/^# //' <<'EOF' | bash", "          # node --test tools", "          EOF"]),
            (check_shell_node, "the handshake step's run line dropped", "shell", SHELL_NODE_LINES[1], []),
            (check_shell_tail, "the handshake step's working-directory: tools", "shell", SHELL_NODE_LINES[1],
             [SHELL_NODE_LINES[1], "        working-directory: tools"]),
            (check_shell_tail, "the handshake step's env: NODE_OPTIONS", "shell", SHELL_NODE_LINES[1],
             ["        env:", "          NODE_OPTIONS: --test-skip-pattern=.", SHELL_NODE_LINES[1]]),
            (check_shell_tail, "the handshake step's shell: true {0}", "shell", SHELL_NODE_LINES[1],
             ["        shell: true {0}", SHELL_NODE_LINES[1]]),
            (check_shell_tail, "the handshake step's continue-on-error: true", "shell", SHELL_NODE_LINES[1],
             [SHELL_NODE_LINES[1], "        continue-on-error: true"]),
            (check_shell_tail, "the handshake step's if: false", "shell", SHELL_NODE_LINES[0],
             [SHELL_NODE_LINES[0], "        if: false"]),
            (check_shell_tail, "a with: on the handshake step", "shell", SHELL_NODE_LINES[1],
             [SHELL_NODE_LINES[1], "        with:", "          x: y"]),
            (check_shell_tail, "a step writing GITHUB_ENV between the node setup and the handshake step", "shell",
             SHELL_NODE_LINES[0], ['      - run: echo "NODE_OPTIONS=--test-skip-pattern=." >> "$GITHUB_ENV"', SHELL_NODE_LINES[0]]),
            (check_shell_tail, "a second setup-node after the handshake step", "shell", SHELL_NODE_LINES[1],
             [SHELL_NODE_LINES[1], "      - uses: actions/setup-node@v4", "        with:", "          node-version: '20'"]),
            (check_shell_tail, "the node setup's with: widened", "shell", "          node-version: '22'",
             ["          node-version: '22'", "          node-version-file: .nvmrc"]),
            (check_matrix_tie, "an include on the Shell job's matrix", "shell", os_line,
             [os_line, "        include:", "          - os: windows-latest"]),
            (check_matrix_tie, "the Shell job's os line changed", "shell", os_line, ["        os: [ubuntu-latest]"]),
            (check_node_version_tie, "the Shell job on node 24", "shell", "          node-version: '22'",
             ["          node-version: '24'"]),
            (check_command_once, "a copy of the command in the last job", None, None, ["    steps:", "      - run: " + CMD]),
        )
        for check, label, where, anchor, new in plants:
            with self.subTest(label):
                out = self.plant(src, where, anchor, new)
                self.assertNotEqual(out, src, "the plant landed")
                self.assertNotEqual(check(out), [], "%s: %s is red" % (label, check.__name__))

    def test_a_second_job_of_the_same_name_reds_check_6(self):
        src = self.synthetic()
        key = "    name: Vendored tooling (node --test, ${{ matrix.os }})"
        twin = ["  twin:", "    runs-on: ubuntu-latest", "    steps:", "      - run: true", ""]
        other = "\n".join(["name: CI", "on: [push, pull_request]", "jobs:", "  vendored-tooling:", key,
                           "    runs-on: ubuntu-latest", "    steps:", "      - run: true", ""])
        self.assertEqual(check_name_once(NAME_TEXT, [("ci.yml", src), ("docs.yml", "name: Docs\non: [push]\n")]), [],
                         "green with the one name line and a second workflow file that does not name the job")
        for label, texts in (
                ("a same-named job placed before the job in ci.yml",
                 [("ci.yml", self.plant(src, "job", "  vendored-tooling:",
                                        twin[:1] + [key] + twin[1:] + ["  vendored-tooling:"]))]),
                ("a same-named job in a second workflow file", [("ci.yml", src), ("twin.yml", other)]),
                ("the same, in a .yaml file", [("ci.yml", src), ("twin.yaml", other)]),
                ("the same, in a .YML file", [("ci.yml", src), ("TWIN.YML", other)]),
                ("a twin whose name is quoted", [("ci.yml", self.plant(src, "job", "  vendored-tooling:", twin[:1]
                                                 + ['    name: "Vendored tooling (node --test, ${{ matrix.os }})"'] + twin[1:]
                                                 + ["  vendored-tooling:"]))]),
                ("a twin named with the runner's label, the name GitHub shows",
                 [("ci.yml", self.plant(src, "job", "  vendored-tooling:", twin[:1]
                                        + ["    name: Vendored tooling (node --test, ubuntu-latest)"] + twin[1:]
                                        + ["  vendored-tooling:"]))]),
                ("a twin named in another case", [("ci.yml", src), ("twin.yml", other.replace("Vendored tooling", "VENDORED TOOLING"))]),
                ("the job's own name changed", [("ci.yml", src.replace(key, "    name: Vendored (node --test, ${{ matrix.os }})"))]),
                ("a second workflow file with a CR in it", [("ci.yml", src), ("docs.yml", "name: Docs\r\non: [push]\n")])):
            with self.subTest(label):
                self.assertNotEqual(check_name_once(NAME_TEXT, texts), [], label)
        self.assertEqual(check_name_once(NAME_TEXT, [("ci.yml", src + "# Vendored tooling (node --test, x): a comment\n")]), [],
                         "a comment-only line naming the job is not a job")
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sub"))
            for name, text in (("ci.yml", src), ("sub/twin.yaml", other), ("notes.txt", other)):
                with open(os.path.join(d, name), "w", encoding="utf-8", newline="") as fh:
                    fh.write(text)
            self.assertEqual([f for f, _ in workflow_texts(d)], ["ci.yml", os.path.join("sub", "twin.yaml")],
                             "workflow_texts reads every .yml and .yaml file at any depth and nothing else")
            self.assertNotEqual(check_name_once(NAME_TEXT, workflow_texts(d)), [], "the twin in a subdirectory is read")

    def test_a_name_yaml_assembles_or_decodes_reds_check_6s_name_lines(self):
        src = self.synthetic()
        docs = ["name: Docs", "on: [push]", "jobs:", "  build:", "    runs-on: ubuntu-latest", "    steps:",
                "      - name: Build", "        run: mkdocs build --strict", ""]

        def with_twin(name_lines, key="  twin:"):
            """docs.yml with a second job, keyed by the line `key`, whose name is written as the lines name_lines."""
            return "\n".join(docs + [key] + name_lines + ["    runs-on: ubuntu-latest", "    steps:",
                                                          '      - run: "true"', ""])

        self.assertEqual(check_name_lines([("ci.yml", src), ("docs.yml", "\n".join(docs))]), [],
                         "green on the synthetic workflow and a second file whose name lines are whole")
        self.assertNotEqual(check_name_lines([]), [], "red when no workflow text is read")
        self.assertNotEqual(check_name_lines([("docs.yml", "on: [push]\njobs: {}\n")]), [], "red when no name: line is read")
        for label, name_lines, *key in (
                ("a pipe inside a plain value", ["    name: a | b"]),
                ("a single-quoted value holding an escaped quote", ["    name: 'it''s whole'"]),
                ("a double-quoted value holding a colon", ['    name: "Twin: whole"']),
                ("a comment line at the key's column after the name", ["    name: whole", "    # a comment"]),
                ("a blank line after the name", ["    name: whole", ""]),
                # the key's column is the end of the lead, so the job's keys at the column after `: ` continue nothing
                ("the job written as an explicit key, its name whole after the value's indicator, its keys at the name's "
                 "column", ["  : name: whole"], "  ? twin")):
            with self.subTest("green: " + label):
                self.assertEqual(check_name_lines([("docs.yml", with_twin(name_lines, *key))]), [], label)
        # The three twins the fork PR's re-check planted in a second workflow file, each left green by check 6's count,
        # then one plant per refusal that no other refusal reds, each red for its own reason, and one plant per indicator
        # the key's lead admits besides the dash, each left unread before the lead admitted it.
        for label, name_lines, reason, *key in (
                ("the re-check's plain scalar continued over two lines",
                 ["    name: Vendored tooling", "      (node --test, ubuntu-latest)"], "is indented past the key"),
                ("the re-check's name folded through >-",
                 ["    name: >-", "      Served pages", "      (pytest, ubuntu-latest)"], "block scalar's indicator"),
                ("the re-check's name spelled through an escape",
                 ['    name: "Vendored\\x20tooling (node --test, ubuntu-latest)"'], "holds a backslash"),
                ("an empty value, the name on the lines below",
                 ["    name:", "      Vendored tooling", "      (node --test, ubuntu-latest)"], "is empty"),
                ("an empty value with a comment and nothing below it", ["    name:   # a comment"], "is empty"),
                ("a block indicator with its indentation and chomping indicators, nothing below it", ["    name: |2-"],
                 "block scalar's indicator"),
                ("an alias", ["    name: *n"], "is an alias"),
                ("a double-quoted value left open, continued at the key's column",
                 ['    name: "Vendored tooling', '    (node --test, ubuntu-latest)"'], "left open"),
                ("a single-quoted value left open after an escaped quote", ["    name: 'it''s", "    open'"], "left open"),
                ("a quoted key", ['    "name": >-', "      Vendored tooling (node --test,", "      ubuntu-latest)"],
                 "block scalar's indicator"),
                ("a key in another case", ["    Name: *n"], "is an alias"),
                ("a step's name continued past its dash's key", ["    steps:", "      - name: Vendored tooling",
                                                                 "          (node --test, ubuntu-latest)"],
                 "is indented past the key"),
                # the continuation read skips blank lines: YAML continues a plain scalar past one
                ("a name continued after a blank line", ["    name: Vendored tooling", "", "      (node --test, ubuntu-latest)"],
                 "line %d, the next line that is not blank, is indented past the key" % (len(docs) + 4)),
                ("a tag before a double-quoted value left open, continued at the key's column",
                 ['    name: !!str "Vendored tooling', '    (node --test, ubuntu-latest)"'], "a tag or an anchor"),
                ("an anchor before a single-quoted value left open, continued at the key's column",
                 ["    name: &n 'Vendored tooling", "    (node --test, ubuntu-latest)'"], "a tag or an anchor"),
                ("the job written as an explicit key, its name after the value's indicator continued on the next line",
                 ["  : name: Vendored tooling", "      (node --test, ubuntu-latest)"], "is indented past the key", "  ? twin"),
                # YAML reads this key as a mapping, not a job's name key; the lead reads it on the safe side
                ("a name key after an explicit key's indicator, folded through >-",
                 ["    ? name: >-", "        Served pages", "        (pytest, ubuntu-latest)"], "block scalar's indicator")):
            with self.subTest(label):
                faults = check_name_lines([("ci.yml", src), ("docs.yml", with_twin(name_lines, *key))])
                self.assertEqual(len(faults), 1, "%s: one fault, %r" % (label, faults))
                self.assertIn("docs.yml line ", faults[0])
                self.assertIn(reason, faults[0], label)
        # check_name_lines refuses a line break other than LF in every file it reads, not only in ci.yml, where check 1
        # reads the file whole: here a CR inside a name line of a second workflow file, where YAML reads the text after the
        # CR as a line of its own, indented past the key, and this module's LF split reads one line.
        with self.subTest("a CR inside a name line of a second workflow file"):
            cr = with_twin(["    name: Vendored tooling\r      (node --test, ubuntu-latest)"])
            self.assertEqual(check_line_breaks(src), [], "check 1 is green on ci.yml, which holds no CR")
            faults = check_name_lines([("ci.yml", src), ("docs.yml", cr)])
            self.assertEqual(len(faults), 1, "one fault, %r" % faults)
            self.assertIn("docs.yml holds line breaks other than LF (line %d: CR)" % (len(docs) + 2), faults[0])

    def test_each_foreign_line_break_reds_every_check(self):
        src = self.synthetic()
        for ch in FOREIGN_BREAKS:
            for label, out in (("in a comment line before a job key",
                                src.replace("    # a comment\n    name: Vendored", "    # a comment%s    if: false\n    name: "
                                            "Vendored" % ch, 1)),
                               ("as a whole line at the top level's column inside the job, before a job key",
                                src.replace("\n        run: %s\n" % CMD, "\n        run: %s\n%s\n    if: false\n" % (CMD, ch), 1)),
                               ("at the end of a top-level line", src.replace("\njobs:\n", "\njobs:%s\n" % ch, 1))):
                with self.subTest(FOREIGN_BREAKS[ch] + ", " + label):
                    self.assertNotEqual(out, src, "the plant landed")
                    for check in self.CHECKS:
                        self.assertNotEqual(check(out), [], check.__name__)
        crlf = src.replace("\n", "\r\n")
        for check in self.CHECKS:
            self.assertNotEqual(check(crlf), [], "CRLF line ends: " + check.__name__)

    def test_the_block_reading(self):
        ls = self.synthetic().split("\n")
        self.assertEqual(content(job_block(JOB, ls)), list(EXPECTED_JOB),
                         "a comment at any column ends no block and is removed; the blank line before the next job stays")
        shell = content(job_block("shell", ls))
        self.assertIn("          # a shell comment", shell, "a `#` line inside a block scalar is its text, kept")
        self.assertNotIn("    # node --test tools, a comment", shell, "a comment-only line outside one is removed")
        self.assertEqual(shell[-1], "", "the Shell block ends at the next job's key line")


if __name__ == "__main__":
    unittest.main()
