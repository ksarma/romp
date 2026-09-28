#!/usr/bin/env python3
"""The vendored tooling tests run in a CI job of their own, with their own cap (.github/workflows/ci.yml, 2026-09-28).

The step "Vendored tooling and host-script tests (node --test)" ran at the end of the Shell job. At the fork's main 1d591384e
(run 36388144219) the Shell job took 31 min 50 s of its 35-minute cap: Run bats 700 s, then this step 1180 s, where at
ffab236bd (run 36308512751) the step took 67 s. The growth is fork PR #780's tracked-changes bash guard: batch 925 added
27,628 lines under tools/ and vendor/track-changents/, about 25,700 of them #780's. node --test runs files side by side and
a file's tests one after another, and the tests of one file, tools/romp-track-bash-guard.test.mjs, add up to about 1100 s
in that run's log (the slowest single test 222 s). With the step inside the Shell job, a PR that added more than about three
minutes of bats time (the job's margin at 1d591384e was 190 s) ran the job past its cap. Raising the Shell cap was declined,
since it would hide the growth; the step moved to its own job instead.

Pins: the job exists under its name (the step's wording, kept although most of the files it runs are tools/ tests rather
than vendored code), runs on the Shell job's matrix expression (ubuntu-latest always, macOS on a manual run or the weekly
schedule) with fail-fast off and no matrix key but `os` (no include, no exclude, no second axis), so the move lost no cell
and one red cell cancels no other; it carries its per-cell cap, checks out, pins node 22 through setup-node and runs the
step's command; it has no job-level `if:`, `needs:` or continue-on-error, and no step-level `if:` or continue-on-error. The
command runs nowhere else. Every node command in the Shell job's run text and shell: lines is node --test naming only
paths under tests/ (a bare node --test takes node's default glob over the whole tree, tools/ and vendor/ included, and node
running a test file directly runs its tests too), no Shell step sets a working-directory and neither the job nor the
workflow sets a default one, and the Shell job keeps the manager handshake step (T224: that step stays inside a check
upstream's ruleset requires). The rule reads the commands as ci.yml writes them: a script the run text calls, an action a
step uses and a quote inside a word are outside it.

The reader. Source pins, as tests/test_ci_bats_bound.py: the workflow read by line shape, with no YAML library (CI's Python
cells install none). A line reader sees only the shapes it knows, and each audit of this module found one more YAML shape
the reader of the day did not see, so this reader is CLOSED. A job is the block from its key line to the next line that is
not a comment and sits at two spaces or at the top level; comment and blank lines never end a block, wherever they sit
(YAML ignores a comment's indentation). Every other line of the block must be one of these shapes:
  - a job key at four spaces;
  - under strategy:, a key at six spaces, and under its matrix:, a key at eight;
  - under steps:, a step's dash line at six spaces (`- key: value`), and a step field at eight;
  - under a step field `with:` or `env:` that has no value, an entry at ten spaces;
  - under a step field `run: |`, a line deeper than eight spaces: the literal block scalar's text, a `#` line included,
    since YAML reads it as text (the node rule reads it too, on the safe side).
A key is bare or quoted, with or without blanks before its colon, and is compared in lower case. The value on a key's line
is empty, a plain scalar on that one line (no `: ` inside it), a quoted scalar on that one line (a double-quoted one without
a backslash), or, on run: alone, a literal block scalar's indicator. Anything else raises UnknownShape naming every such
line, and every check in the class fails with it: a flow mapping or sequence, a plain scalar continued on the next line, a
folded block scalar (`>`, which joins its lines into one command), a line at one or three spaces, a tab, a tag, and any
anchor, alias or merge key (&name, *name, <<:, by which YAML brings keys into a job from outside it). An unknown shape is a
red to look at, never a silent pass."""
import os
import re
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
WF = os.path.join(os.path.dirname(HERE), ".github", "workflows", "ci.yml")

JOB = "vendored-tooling"
JOB_NAME = "Vendored tooling (node --test, ${{ matrix.os }})"
STEP = "Vendored tooling and host-script tests (node --test)"
CMD = "node --test tools/*.test.mjs vendor/track-changents/hooks/*.test.mjs"
HANDSHAKE = "Manager handshake tests (node --test)"
HANDSHAKE_CMD = "node --test tests/manager-*.test.js"
# The job-level keys that can skip a job or keep its red out of the run's verdict.
SKIPPERS = ("if", "needs", "continue-on-error")

# A key: bare, or quoted in single or double quotes.
KEY = r"(?:[A-Za-z_][A-Za-z0-9_-]*|\"[A-Za-z_][A-Za-z0-9_-]*\"|'[A-Za-z_][A-Za-z0-9_-]*')"
# `key: value` or `key:`, blanks allowed before the colon; the colon is followed by a blank or the line's end.
ENTRY = re.compile(r"(?P<key>%s)[ \t]*:(?:[ \t]+(?P<rest>.*?))?[ \t]*" % KEY)
TOP_KEY = re.compile(r"(?P<key>%s)[ \t]*:(?P<rest>(?:[ \t].*)?)" % KEY)
JOB_KEY = re.compile(r"  (?P<key>%s)[ \t]*:(?P<rest>(?:[ \t].*)?)" % KEY)
# The first character of a plain scalar: not a YAML indicator, or one of `-?:` followed by a character that is not a blank.
PLAIN_START = re.compile(r"[^\s&*!|>'\"%@`\[\]{}#,?:-]|[?:-][^\s,\[\]{}]")
# An anchor or alias at the start of a node, or a merge key: the reason given for an unknown line that holds one.
REF = re.compile(r"(?:^[ \t]*(?:-[ \t]+)*|:[ \t]+|[\[{,][ \t]*)(?:[&*][^\s,\[\]{}]|[\"']?<<[\"']?[ \t]*:)")


class UnknownShape(ValueError):
    """A line of a job the reader cannot classify, a job key written twice, or a job key line that carries a value."""


def workflow(path=WF):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _norm(key):
    """A key as the checks compare it: quotes dropped, lower case (GitHub refuses a key in another case and actionlint
    flags it, so reading `If:` as `if` can only add a red)."""
    return (key[1:-1] if key[:1] in "'\"" else key).lower()


def scalar(rest):
    """(kind, value) of the text after a key's colon, kind one of empty, plain, quoted and block (a literal one, `|`); None
    for any other shape (a flow collection, an anchor, an alias, a tag, a folded block scalar, a double-quoted scalar with a
    backslash, a plain scalar holding `: `)."""
    if rest is None or rest == "" or rest.startswith("#"):
        return ("empty", "")
    m = re.fullmatch(r"'((?:[^']|'')*)'(?:[ \t]+#.*)?", rest)
    if m:
        return ("quoted", m.group(1).replace("''", "'"))
    m = re.fullmatch(r'"([^"\\]*)"(?:[ \t]+#.*)?', rest)
    if m:
        return ("quoted", m.group(1))
    if re.fullmatch(r"\|[+-]?(?:[ \t]+#.*)?", rest):
        return ("block", "")
    if not PLAIN_START.match(rest):
        return None
    value = re.split(r"[ \t]+#", rest, 1)[0].rstrip()
    if re.search(r":(?:[ \t]|$)", value):
        return None
    return ("plain", value)


def _entry(text):
    """(key, value, kind) of a `key: value` text, or None when the key or the value is outside the closed set."""
    m = ENTRY.fullmatch(text)
    if not m:
        return None
    sc = scalar(m.group("rest"))
    return None if sc is None else (_norm(m.group("key")), sc[1], sc[0])


def top_keys(src):
    """The workflow's top-level keys, quotes dropped, in file order."""
    return [_norm(m.group("key")) for m in (TOP_KEY.fullmatch(l) for l in src.split("\n")) if m]


def job_block(key, src):
    """[(line number, line)] of the job under `  <key>:` in the workflow's jobs: section: the lines after the key line up to
    the next line that is not a comment and sits at two spaces or at the top level. Raises LookupError when the job is
    absent, moved or renamed, and UnknownShape when jobs: or the job's key is written twice (YAML keeps the last copy) or
    the key line carries a value."""
    lines = src.split("\n")
    tops = [i for i, l in enumerate(lines) if re.match(r"[^ \t#]", l)]
    jobs = [i for i in tops if TOP_KEY.fullmatch(lines[i]) and _norm(TOP_KEY.fullmatch(lines[i]).group("key")) == "jobs"]
    if not jobs:
        raise LookupError("the workflow has no top-level jobs: key")
    if len(jobs) > 1:
        raise UnknownShape("the workflow's jobs: key is written %d times (lines %s)" % (len(jobs), [i + 1 for i in jobs]))
    end = min([i for i in tops if i > jobs[0]] + [len(lines)])
    hits = [i for i in range(jobs[0] + 1, end) if JOB_KEY.fullmatch(lines[i])
            and _norm(JOB_KEY.fullmatch(lines[i]).group("key")) == key]
    if not hits:
        raise LookupError("ci.yml has no job `%s`" % key)
    if len(hits) > 1:
        raise UnknownShape("the job `%s` is written %d times (lines %s); YAML keeps the last" % (key, len(hits),
                                                                                                [i + 1 for i in hits]))
    rest = JOB_KEY.fullmatch(lines[hits[0]]).group("rest").strip()
    if rest and not rest.startswith("#"):
        raise UnknownShape("line %d: the job `%s` key carries a value, %r" % (hits[0] + 1, key, rest))
    stop = hits[0] + 1
    while stop < end and not re.match(r"(?:  )?[^ \t#]", lines[stop]):
        stop += 1
    return [(i + 1, lines[i]) for i in range(hits[0] + 1, stop)]


def read_job(key, path=WF):
    """The job under `key`, every line classified into the closed set of shapes the module docstring states:
    {keys: [(key, value)] of the job, in file order, wherever they sit (YAML takes a job key after steps: as well as before
    it); strategy: [(key, value)] under strategy:; matrix: [(key, value)] under its matrix:; steps: [{fields: [(key,
    value)], with: [(key, value)], env: [(key, value)], run: [the command's lines]}]}. Raises UnknownShape naming every line
    outside the set, and job_block's errors."""
    job = {"keys": [], "strategy": [], "matrix": [], "steps": []}
    unknown = []
    jk = sk = step = fk = under = None   # job key, strategy key, step, field open for entries, a run scalar's indentation
    for n, line in job_block(key, workflow(path)):
        if not line.strip():
            continue
        ind = len(line) - len(line.lstrip(" "))
        if under is not None:
            if ind > under:
                step["run"].append(line.strip())   # a `#` line here too: YAML reads it as the scalar's text
                continue
            under = None
        if line.lstrip().startswith("#"):
            continue
        body, shape = line[ind:], None
        if ind == 4:
            e = _entry(body)
            if e and e[2] != "block":
                shape, jk, sk, step, fk = "job key", e[0], None, None, None
                job["keys"].append(e[:2])
        elif ind == 6 and jk == "strategy":
            e = _entry(body)
            if e and e[2] != "block":
                shape, sk = "strategy key", e[0]
                job["strategy"].append(e[:2])
        elif ind == 8 and jk == "strategy" and sk == "matrix":
            e = _entry(body)
            if e and e[2] != "block":
                shape = "matrix key"
                job["matrix"].append(e[:2])
        elif jk == "steps" and (ind == 6 and re.match(r"- [^ \t]", body) or ind == 8 and step is not None):
            e = _entry(body[2:] if ind == 6 else body)
            if e and (e[2] != "block" or e[0] == "run"):
                shape = "step field"
                if ind == 6:
                    step = {"fields": [], "with": [], "env": [], "run": []}
                    job["steps"].append(step)
                step["fields"].append(e[:2])
                fk = e[0] if e[2] == "empty" else None
                if e[0] == "run" and e[2] == "block":
                    under = 8
                elif e[0] == "run":
                    step["run"].append(e[1])
        elif ind == 10 and fk in ("with", "env"):
            e = _entry(body)
            if e and e[2] != "block":
                shape = "with or env entry"
                step[fk].append(e[:2])
        if shape is None:
            unknown.append("line %d: %r (%s)" % (n, line, "an anchor, alias or merge key, by which YAML brings keys in "
                                                  "from outside the job" if REF.search(line) else "a shape outside the "
                                                  "closed set the module docstring states"))
    if unknown:
        raise UnknownShape("the job `%s` in %s has lines the reader cannot classify, so no check here can be trusted "
                           "to have read the job whole: %s" % (key, path, "; ".join(unknown)))
    return job


def values(entries, key):
    """The values of every `key` among (key, value) entries, in file order."""
    return [v for k, v in entries if k == key]


def code_lines(text):
    """The lines that are not YAML comments (a line whose first non-blank character is `#`), so a comment that names a
    path is not read as a step that runs it."""
    return [l for l in text.splitlines() if not l.lstrip().startswith("#")]


NODE_WORD = re.compile(r"(?<![\w.-])node(?:js)?(?![\w.-])")
TEST_FLAG = re.compile(r"(?<![\w-])--test(?![\w-])")
OPTION = re.compile(r"--[a-z][a-z0-9-]*(?:=[A-Za-z0-9_.:/+,-]*)?")
# A path under tests/: `tests`, `tests/` or deeper, glob characters allowed, no component starting with a dot (so no `..`).
UNDER_TESTS = re.compile(r"(?:\./)?tests(?:/[A-Za-z0-9_*?+-][A-Za-z0-9_.*?+-]*)*/?")
VENDORED_PATH = re.compile(r"vendor/track-changents|tools/\S*\.test\.mjs")


def node_command_faults(run_lines):
    """The faults of the node commands in a job's run text. Each line splits into commands at `;`, `&` and `|`; a command
    that names node, or holds a --test flag, must be `node` followed by options written `--name` or `--name=value` and at
    least one path under tests/, with --test among the options. So a bare node --test (node's default glob, which takes
    every test file in the tree, tools/ and vendor/ included), node running a test file directly (which runs its tests
    too), a path outside tests/, an option's value written as a separate word, and node behind any other word (bash -c,
    xargs, an absolute path) are faults, the last two on the safe side. A line that names a vendored test path is a fault
    whatever runs it."""
    faults = []
    for line in run_lines:
        if VENDORED_PATH.search(line):
            faults.append("%r names a vendored test path" % line)
        for cmd in re.split(r"[;&|]+", line):
            words = cmd.split()
            if not (NODE_WORD.search(cmd) or TEST_FLAG.search(cmd)):
                continue
            paths = [w for w in words[1:] if not OPTION.fullmatch(w)]
            if words[0] != "node":
                faults.append("%r: node or --test outside a plain `node --test <paths>` command" % cmd.strip())
            elif "--test" not in words:
                faults.append("%r: node without --test; a test file node runs directly runs its tests" % cmd.strip())
            elif not paths:
                faults.append("%r: a bare node --test runs node's default glob over the whole tree, tools/ and vendor/ "
                              "included" % cmd.strip())
            else:
                faults.extend("%r names %r, not a path under tests/" % (cmd.strip(), p) for p in paths
                              if not UNDER_TESTS.fullmatch(p))
    return faults


def node_version(step):
    """The node-version a setup-node step pins, or None when its with: is absent or written twice (YAML keeps the last)."""
    if values(step["fields"], "with") != [""]:
        return None
    return "".join(values(step["with"], "node-version"))


def the_one(test, found, what):
    """The single item of found, failing the test by `what` when there is none or more than one (a key written twice is
    read twice here, and only one of the two copies can be the one in force)."""
    test.assertEqual(len(found), 1, "%s: exactly one, read over the whole job; found %r" % (what, found))
    return found[0]


def read_or_fail(test, key, missing):
    """read_job(key), failing the test with the reader's words when the job is absent or holds a line it cannot classify."""
    try:
        return read_job(key)
    except LookupError as e:
        test.fail("%s: %s" % (e, missing))
    except UnknownShape as e:
        test.fail(str(e))


class VendoredToolingJob(unittest.TestCase):
    def setUp(self):
        self.job = read_or_fail(self, JOB, "the step %r runs in a job of its own, `%s`, with its own cap; at the fork's main "
                                           "1d591384e it ran inside the Shell job, 1180 s of that job's 31 min 50 s under "
                                           "its 35-minute cap" % (STEP, JOB))
        self.keys = self.job["keys"]
        self.assertEqual(the_one(self, values(self.keys, "steps"), "the job's steps: key"), "", "steps: holds a block")
        self.steps = self.job["steps"]

    def test_the_job_is_named_and_runs_on_the_matrix(self):
        self.assertEqual(values(self.keys, "name"), [JOB_NAME], "the job's name, as the checks list shows it")
        self.assertEqual(values(self.keys, "runs-on"), ["${{ matrix.os }}"], "runs-on reads the matrix")

    def test_the_matrix_is_the_shell_jobs_with_fail_fast_off_and_no_cell_added_or_dropped(self):
        self.assertEqual(the_one(self, values(self.keys, "strategy"), "the job's strategy: key"), "")
        self.assertEqual(values(self.job["strategy"], "fail-fast"), ["false"],
                         "fail-fast off, once, as in the Shell job: one red cell must not cancel the other, so on a dispatch "
                         "or the weekly schedule a Linux red leaves the macOS cell running (fail-fast defaults to true)")
        self.assertEqual(the_one(self, values(self.job["strategy"], "matrix"), "the job's matrix: key"), "",
                         "the matrix is a block of its own keys")
        self.assertEqual([k for k, _ in self.job["matrix"]], ["os"],
                         "the matrix's one key is os: no include or exclude and no second axis, so the job runs on exactly "
                         "the Shell job's cells and the move lost no cell (an exclude of macos-latest would drop the macOS "
                         "cell the os line keeps)")
        shell = read_or_fail(self, "shell", "the Shell job is read by its key, `shell`")
        self.assertEqual(the_one(self, values(shell["keys"], "strategy"), "the Shell job's strategy: key"), "")
        self.assertEqual(values(shell["strategy"], "matrix"), [""], "the Shell job's matrix: key, once, a block")
        self.assertEqual([k for k, _ in shell["matrix"]], ["os"], "the Shell job's matrix is its one os line")
        self.assertEqual(values(self.job["matrix"], "os"), values(shell["matrix"], "os"),
                         "the job runs on the Shell job's matrix expression (ubuntu-latest always, macOS on a manual run or "
                         "the weekly schedule), so moving the step lost no cell")

    def test_the_job_carries_its_own_per_cell_cap(self):
        cap = the_one(self, values(self.keys, "timeout-minutes"), "the job's timeout-minutes")
        m = re.fullmatch(r"\$\{\{ matrix\.os == 'macos-latest' && (\d+) \|\| (\d+) \}\}", cap)
        self.assertTrue(m, "the job's timeout-minutes is the per-cell expression (macos-latest && N || M), as the python "
                           "job's is: %r" % cap)
        macos, linux = int(m.group(1)), int(m.group(2))
        self.assertGreaterEqual(linux, 25, "the step took 1180 s (19 min 40 s) on Linux at 1d591384e (run 36388144219); a cap "
                                           "below 25 minutes leaves a slow runner almost no margin")
        self.assertLessEqual(linux, 35, "a cap far above the measured 19 min 40 s would hide the growth that moving the step "
                                        "out of the Shell job was meant to show, and 35 is the Shell job's own cap")
        self.assertGreaterEqual(macos, linux, "the macOS runners are the slower ones")
        self.assertLessEqual(macos, 60, "past an hour a hung macOS cell eats the dispatch (the python job's ceiling)")

    def test_nothing_at_the_job_level_skips_it_or_hides_its_red(self):
        keys = [k for k, _ in self.keys]
        for key in SKIPPERS:
            with self.subTest(key=key):
                self.assertNotIn(key, keys, "a job-level %s: can skip the job or keep its red out of the run's verdict; read "
                                            "over the whole job, since YAML takes a job key after steps: as well as before "
                                            "it (the job's keys: %r)" % (key, keys))
        for s in self.steps:
            fields = [k for k, _ in s["fields"]]
            self.assertNotIn("continue-on-error", fields, "no step of the job may turn its red green: %r" % s)
            self.assertNotIn("if", fields, "no step of the job is conditional: %r" % s)

    def test_the_steps_check_out_pin_node_22_and_run_the_command(self):
        uses = [values(s["fields"], "uses") for s in self.steps]
        self.assertEqual(uses[0], ["actions/checkout@v4"], "the job checks the tree out first: %r" % uses)
        setup = [i for i, u in enumerate(uses) if u == ["actions/setup-node@v4"]]
        self.assertEqual(len(setup), 1, "one setup-node step: %r" % uses)
        self.assertEqual(node_version(self.steps[setup[0]]), "22", "node 22, as the Shell job pins it for the handshake "
                                                                   "step: the step never rides whatever node the image has")
        named = [i for i, s in enumerate(self.steps) if values(s["fields"], "name") == [STEP]]
        self.assertEqual(len(named), 1, "one step named %r" % STEP)
        self.assertEqual(values(self.steps[named[0]]["fields"], "run"), [CMD], "the step's command, once, unchanged by "
                                                                               "the move")
        self.assertLess(setup[0], named[0], "setup-node comes before the step it pins node for")
        shell = read_or_fail(self, "shell", "the Shell job is read by its key, `shell`")
        shell_setup = [s for s in shell["steps"] if values(s["fields"], "uses") == ["actions/setup-node@v4"]]
        self.assertEqual([node_version(s) for s in shell_setup], ["22"], "the Shell job's one setup-node pins node 22 too, "
                                                                        "so the two jobs run the same node")

    def test_the_command_runs_in_this_job_alone(self):
        runs = [l for l in code_lines(workflow()) if CMD in l]
        self.assertEqual(len(runs), 1, "the command runs once in the workflow, in this job, not beside a copy left in the "
                                       "Shell job: %r" % runs)


class ShellJobAfterTheMove(unittest.TestCase):
    def setUp(self):
        self.job = read_or_fail(self, "shell", "the Shell job is read by its key, `shell`")
        self.assertEqual(the_one(self, values(self.job["keys"], "steps"), "the Shell job's steps: key"), "",
                         "steps: holds a block")
        self.steps = self.job["steps"]

    def test_every_node_command_in_the_shell_job_runs_node_test_over_tests_alone(self):
        faults = node_command_faults([l for s in self.steps for l in s["run"] + values(s["fields"], "shell")])
        self.assertEqual(faults, [], "every node command in the Shell job is node --test over paths under tests/: the step "
                                     "over tools/ and vendor/ moved to the `%s` job, since at 1d591384e it took 1180 s of "
                                     "the Shell job's 31 min 50 s under its 35-minute cap, and a PR that added more than "
                                     "about three minutes of bats time ran the job past it" % JOB)

    def test_the_shell_job_sets_no_working_directory(self):
        wd = [values(s["fields"], "working-directory") for s in self.steps if values(s["fields"], "working-directory")]
        self.assertEqual(wd, [], "no Shell step sets a working-directory: the rule on node's paths reads them from the "
                                 "repository root, and a node --test run from tools/ or vendor/ runs the vendored tests")
        self.assertNotIn("defaults", [k for k, _ in self.job["keys"]], "no job-level defaults: (a default "
                                                                        "working-directory for every run step)")
        self.assertNotIn("defaults", top_keys(workflow()), "no workflow-level defaults: (a default working-directory for "
                                                           "every job's run steps, the Shell job's among them)")

    def test_the_shell_job_keeps_the_manager_handshake_step(self):
        named = [s for s in self.steps if values(s["fields"], "name") == [HANDSHAKE]]
        self.assertEqual(len(named), 1, "the Shell job keeps the step %r (T224: it runs inside a check upstream's ruleset "
                                        "requires, so a red handshake blocks the merge)" % HANDSHAKE)
        self.assertEqual(values(named[0]["fields"], "run"), [HANDSHAKE_CMD])

    def test_the_shell_cap_was_not_raised_to_hold_the_step(self):
        cap = the_one(self, values(self.job["keys"], "timeout-minutes"), "the Shell job's timeout-minutes")
        self.assertRegex(cap, r"^\d+$", "the Shell job's timeout-minutes is a plain number")
        self.assertLessEqual(int(cap), 35, "the Shell job's cap stays at 35 minutes: raising it to hold the vendored step "
                                           "would hide the step's growth, which is why the step has its own job")


class ReaderShapes(unittest.TestCase):
    """The reader against synthetic workflows: where a job ends, the key spellings it reads, the shapes it refuses (anchors,
    aliases and merge keys among them), a run block scalar, and the node command rule."""
    BASE = ("name: CI\non:\n  push:\njobs:\n  shell:\n    name: Shell\n    runs-on: x\n    timeout-minutes: 35\n"
            "    strategy:\n      fail-fast: false\n      matrix:\n        os: ${{ matrix.x }}\n    steps:\n"
            "      - uses: actions/setup-node@v4\n        with:\n          node-version: '22'\n"
            "      - name: Install\n        if: runner.os == 'Linux'\n        env:\n          A: \"1\"\n        run: |\n"
            "          set -e\n          # a shell comment\n          echo a && echo b\n"
            "      - name: " + HANDSHAKE + "\n        run: " + HANDSHAKE_CMD + "\n%s"
            "  secrets:\n    runs-on: y\n    needs: [shell]\n")

    def read(self, extra="", key="shell"):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        p = os.path.join(d, "ci.yml")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(self.BASE % extra)
        return read_job(key, p)

    def test_the_base_reads_whole(self):
        job = self.read()
        self.assertEqual([k for k, _ in job["keys"]], ["name", "runs-on", "timeout-minutes", "strategy", "steps"],
                         "the next job's needs: is not read")
        self.assertEqual(job["strategy"], [("fail-fast", "false"), ("matrix", "")])
        self.assertEqual(job["matrix"], [("os", "${{ matrix.x }}")])
        self.assertEqual([s["fields"] for s in job["steps"]],
                         [[("uses", "actions/setup-node@v4"), ("with", "")],
                          [("name", "Install"), ("if", "runner.os == 'Linux'"), ("env", ""), ("run", "")],
                          [("name", HANDSHAKE), ("run", HANDSHAKE_CMD)]])
        self.assertEqual(node_version(job["steps"][0]), "22")
        self.assertEqual(job["steps"][1]["env"], [("a", "1")], "an env entry, its name in lower case as every key")
        self.assertEqual(job["steps"][1]["run"], ["set -e", "# a shell comment", "echo a && echo b"],
                         "a run block's text, a `#` line included")
        self.assertEqual(node_command_faults([l for s in job["steps"] for l in s["run"]]), [])

    def test_a_run_block_ends_at_a_line_not_deeper_than_its_field(self):
        job = self.read("      - name: n\n        run: |\n          # node --test tools\n          echo\n")
        self.assertEqual(job["steps"][-1]["run"], ["# node --test tools", "echo"])
        self.assertEqual(len(node_command_faults(job["steps"][-1]["run"])), 1, "a `#` line in a run block is read")
        job = self.read("      - name: n\n        run: |\n          echo\n      # a comment\n        if: x\n    needs: y\n")
        self.assertEqual(values(job["steps"][-1]["fields"], "if"), ["x"], "a field after the block and a comment")
        self.assertEqual(values(job["keys"], "needs"), ["y"], "a job key after the block")
        with self.assertRaises(UnknownShape):
            self.read("      - name: n\n        run: |\n          echo\n      # a comment\n          echo again\n")
        job = self.read("    If: a\n    'Continue-On-Error': true\n")
        self.assertEqual([k for k, _ in job["keys"]][-2:], ["if", "continue-on-error"], "keys compared in lower case")

    def test_a_comment_at_any_column_ends_no_block(self):
        for col in ("", "  ", "    ", "      "):
            with self.subTest(column=len(col)):
                job = self.read("%s# a comment\n    if: github.event_name == 'schedule'\n" % col)
                self.assertEqual(values(job["keys"], "if"), ["github.event_name == 'schedule'"])
                job = self.read("%s# a comment\n        continue-on-error: true\n" % col)
                self.assertEqual(values(job["steps"][-1]["fields"], "continue-on-error"), ["true"],
                                 "a step field after a comment is the step's")

    def test_keys_bare_quoted_or_spaced_before_the_colon(self):
        job = self.read("    \"if\": a\n    'needs' : b\n    continue-on-error\t: true\n")
        self.assertEqual([k for k, _ in job["keys"]][-3:], ["if", "needs", "continue-on-error"])
        job = self.read("        \"if\": a\n        if : b\n        'continue-on-error': true\n")
        self.assertEqual([k for k, _ in job["steps"][-1]["fields"]], ["name", "run", "if", "if", "continue-on-error"])
        job = self.read("      - \"if\" : a\n        run: echo\n")
        self.assertEqual(job["steps"][-1]["fields"], [("if", "a"), ("run", "echo")], "a dash line's quoted key")

    def test_shapes_outside_the_set_raise(self):
        for label, extra in (("a flow mapping step", "      - {name: x, run: y}\n"),
                             ("a flow sequence value", "    needs: [a]\n"),
                             ("a plain scalar continued", "      - name: n\n        run: node --test\n          tools\n"),
                             ("a folded run block", "      - name: n\n        run: >\n          node --test tests/a.test.js\n"
                                                    "          tools\n"),
                             ("a line at three spaces", "   if: x\n"),
                             ("a line at one space", " if: x\n"),
                             ("a tab", "\tif: x\n"),
                             ("no blank after the colon", "    if:x\n"),
                             ("a block scalar off run:", "        if: |\n          x\n"),
                             ("steps at four spaces", "    - run: x\n"),
                             ("a double-quoted escape", "      - name: n\n        run: \"node --test \\x74ools\"\n"),
                             ("a colon and blank in a plain value", "        name: a: b\n"),
                             ("a tag", "    if: !!str x\n"),
                             ("a nested block under a job key", "    env:\n      A: b\n"),
                             ("an entry under a with that has a value", "        with: x\n          a: b\n")):
            with self.subTest(label):
                with self.assertRaises(UnknownShape) as cm:
                    self.read(extra)
                self.assertIn("closed set", str(cm.exception))

    def test_anchors_aliases_and_merge_keys_raise_by_name(self):
        for extra in ("    <<: *skip\n", "    <<: {if: x}\n", "    \"<<\": {if: x}\n", "    env: &e\n",
                      "      - &a name: x\n", "      - *a\n", "        run: *cmd\n", "        with: &w\n"):
            with self.subTest(extra):
                with self.assertRaises(UnknownShape) as cm:
                    self.read(extra)
                self.assertIn("anchor, alias or merge key", str(cm.exception))

    def test_a_job_absent_or_written_twice(self):
        with self.assertRaises(LookupError):
            self.read(key=JOB)
        with self.assertRaises(UnknownShape):
            self.read("  \"shell\" :\n    runs-on: z\n")
        with self.assertRaises(UnknownShape):
            self.read("  %s: {runs-on: z}\n" % JOB, key=JOB)

    def test_node_command_faults(self):
        for line in (HANDSHAKE_CMD, "node --test tests/other-*.test.js", "node --test tests/a.test.js && echo ok",
                     "node --test --test-reporter=spec ./tests/", "bats --print-output-on-failure tests/*.bats",
                     "npm ci --prefix vscode-extension"):
            self.assertEqual(node_command_faults([line]), [], line)
        for line in ("node --test", "node --test tools", "node --test vendor/", "node --test ./tools/",
                     "node --test tests/../tools/a.test.mjs", "node --test tests/{a,../tools}", "node tools/a.js",
                     "bash -c 'node --test tools'", "/usr/bin/node --test tests/a.test.js", "cat tools/a.test.mjs",
                     "node --test-reporter spec --test tests/a.test.js", "node --test tests/a.test.js \\",
                     "echo ok; node --test", "xargs node --test"):
            self.assertNotEqual(node_command_faults([line]), [], line)

    def test_a_bare_node_test_step_and_a_working_directory_are_read(self):
        job = self.read("      - name: Extra\n        working-directory: tools\n        run: node --test\n")
        self.assertEqual(values(job["steps"][-1]["fields"], "working-directory"), ["tools"])
        self.assertEqual(len(node_command_faults([l for s in job["steps"] for l in s["run"]])), 1)
        job = self.read("      - name: Extra\n        shell: bash -c 'node --test tools; bash {0}'\n        run: echo\n")
        self.assertEqual(len(node_command_faults(values(job["steps"][-1]["fields"], "shell"))), 1, "a shell: line")

    def test_node_version_needs_one_with(self):
        job = self.read("      - uses: actions/setup-node@v4\n        with:\n          node-version: '22'\n        with:\n"
                        "          cache: npm\n")
        self.assertIsNone(node_version(job["steps"][-1]), "a second with: replaces the first in YAML")


if __name__ == "__main__":
    unittest.main()
