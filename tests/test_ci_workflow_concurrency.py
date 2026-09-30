#!/usr/bin/env python3
"""When CI runs, and which of its runs cancel which (.github/workflows/ci.yml, 2026-09-08 and 2026-09-27).

Triggers (2026-09-27): the workflow runs on a push to a batch branch (`batch/**`), by hand
(workflow_dispatch) and on its weekly schedule, and on nothing else. A member PR runs no ci.yml of its own:
the local sweep (scripts/sweep.py) recorded at the batch head is the landing gate (scripts/batch.py
verify and land read it), and GitHub's full matrix runs once on the batch branch, whose PR is expected to
show that push run's checks on its head (the first batch confirms it). A merge to main runs none: batch.py
land refuses a batch whose head does not contain main and reads main again right before the merge
(tests/test_batch_tool.py, VerifyBehind), so the merge commit's tree is the batch head's, which the batch
push already tested; a move after that read is finish's loud report (LandAndFinish). The gate is the workflow's `on:` block and not a job-level
`if:`: `pull_request`'s branch filter selects the base branch, so singling out batch PRs there would
need an `if:` on every job, and a skipped job reports success (a required check reads it as passing).
CiTriggers reads the `on:` block and holds it to exactly those three triggers, so an added one (a merge queue, a
review, another workflow's run) fails by name; NoJobLevelGate refuses an `if:` or `continue-on-error:` on any job
ci.yml defines, read from the file.

Concurrency (2026-09-08, extended 2026-09-27): the group was `ci-<event>-<ref>` with cancel-in-progress
for every event, so two merges to main in quick succession cancelled the first merge's run, and a red
main went unseen until a later run happened to fail. Pushes to main are keyed on the commit sha, one
group per merge commit, so every merge gets its own completed run (a queue would not do: a group holds
at most one pending run, so a third merge would replace the second's); main is no longer a push trigger,
and the keying stays so that adding it back cannot bring the failure back. A push to a batch branch is
keyed on the branch and cancels the older run there: a rebuild's new head supersedes the old one. A
dispatch queues rather than cancels, and the event name stays in the key so a dispatch (the macOS gate)
is never cancelled by a push to the same ref (2026-07-27). CiConcurrency evaluates the stanza's two
expressions for each kind of run instead of matching their spelling.

Runners (2026-09-28): a batch push gets Linux alone. CiMatrixRunners evaluates each matrix job's `os:` expression
(python, shell and vendored-tooling) for each kind of run with the same evaluator, joins every `include:` entry's os,
and reads the other jobs' literal `runs-on:` (secrets, vscode-extension and served-pages), so macOS on a batch push by
any of those roads fails by name.

No YAML library is in the test deps, so the blocks are read by indentation, and anything the readers
do not understand fails with "re-anchor" rather than passing."""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
WF = os.path.join(os.path.dirname(HERE), ".github", "workflows", "ci.yml")

JOBS = ("python", "shell", "secrets", "vendored-tooling", "vscode-extension", "served-pages")


def _source():
    with open(WF, encoding="utf-8") as f:
        return f.read()


def _block(src, key):
    """The lines under the top-level `key:` up to the next top-level key, comments and blank lines dropped."""
    m = re.search(r"^%s:[ \t]*(?:#.*)?\n" % re.escape(key), src, re.M)
    if m is None:
        raise LookupError("no top-level %s: block in ci.yml; re-anchor this pin" % key)
    out = []
    for line in src[m.end():].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            break
        out.append(line)
    return out


def _keys_at(lines, indent):
    """[(key, rest of the line, index)] for every `key:` line at exactly `indent` spaces."""
    out = []
    for i, line in enumerate(lines):
        if len(line) - len(line.lstrip(" ")) != indent:
            continue
        m = re.match(r"([A-Za-z_][\w-]*):(.*)$", line.strip())
        if m is None:
            raise LookupError("a line at indent %d that is not a key: %r; re-anchor this pin" % (indent, line))
        out.append((m.group(1), m.group(2), i))
    return out


def _children(lines, index, indent):
    """The lines after lines[index] that are indented deeper than `indent`."""
    out = []
    for line in lines[index + 1:]:
        if len(line) - len(line.lstrip(" ")) <= indent:
            break
        out.append(line)
    return out


def _strip_comment(text):
    return re.sub(r"\s+#.*$", "", text).strip()


def _unquote(word):
    word = word.strip()
    if len(word) >= 2 and word[0] == word[-1] and word[0] in "'\"":
        return word[1:-1]
    return word


def triggers(src=None):
    """{event: [its lines]} for the workflow's `on:` block."""
    lines = _block(src if src is not None else _source(), "on")
    return {k: _children(lines, i, 2) for k, _rest, i in _keys_at(lines, 2)}


def push_filters(src=None):
    """{filter key: [patterns]} under `on: push:`, a flow list (`[a, 'b']`) or a block list (`- a`); None without a
    push trigger."""
    lines = triggers(src).get("push")
    if lines is None:
        return None
    out = {}
    for key, rest, i in _keys_at(lines, 4):
        rest = _strip_comment(rest)
        if rest.startswith("["):
            if not rest.endswith("]"):
                raise LookupError("a flow list that does not close on its line: %r; re-anchor this pin" % rest)
            out[key] = [_unquote(w) for w in rest[1:-1].split(",") if w.strip()]
        elif rest:
            out[key] = [_unquote(rest)]
        else:
            out[key] = [_unquote(_strip_comment(l.strip()[1:])) for l in _children(lines, i, 4) if l.strip().startswith("-")]
    return out


def glob_matches(pattern, ref):
    """GitHub's branch-filter glob for the two wildcards the workflow may use: `*` matches any run of characters
    other than `/`, `**` any run of characters. Any other special character (`?`, `+`, `[`, a leading `!`) is not
    modelled here and raises LookupError."""
    if pattern.startswith("!") or any(c in pattern for c in "?+[]"):
        raise LookupError("the branch pattern %r uses a filter character this pin does not model; re-anchor it" % pattern)
    rx, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            rx, i = rx + ".*", i + 2
        elif pattern[i] == "*":
            rx, i = rx + "[^/]*", i + 1
        else:
            rx, i = rx + re.escape(pattern[i]), i + 1
    return re.fullmatch(rx, ref) is not None


def job_keys(src=None):
    """{job: [its keys at the job's key indent]} for the workflow's jobs."""
    lines = _block(src if src is not None else _source(), "jobs")
    return {job: [k for k, _r, _i in _keys_at(_children(lines, i, 2), 4)] for job, _rest, i in _keys_at(lines, 2)}


class CiTriggers(unittest.TestCase):
    """The workflow runs on pushes to batch branches, by hand, and on the schedule; never on a PR event or a push to main."""

    def setUp(self):
        self.events = triggers()
        self.filters = push_filters()

    def test_the_triggers_are_exactly_batch_pushes_the_dispatch_and_the_schedule(self):
        # round 1, tests-3 and extra6-1: the docstring's "and on nothing else", held as a closed set
        self.assertEqual(sorted(self.events), ["push", "schedule", "workflow_dispatch"],
                         "ci.yml's triggers are %r; an added trigger changes which events run the full matrix (a PR event, "
                         "a review, a merge queue, another workflow's run)" % sorted(self.events))

    def test_no_pull_request_trigger(self):
        # a PR event would run the full matrix on every member push again: the cost the local gate removes
        for event in ("pull_request", "pull_request_target"):
            self.assertNotIn(event, self.events, "ci.yml runs on %s again; member PRs run no ci.yml (the local sweep gates them)" % event)

    def test_push_filters_by_branch_only(self):
        self.assertIsNotNone(self.filters, "no push: trigger in ci.yml; re-anchor this pin")
        self.assertEqual(sorted(self.filters), ["branches"],
                         "push: carries %s; a paths, paths-ignore, branches-ignore or tags filter changes which pushes run CI"
                         % sorted(self.filters))

    def test_push_runs_on_batch_branches_and_nothing_else(self):
        patterns = (self.filters or {}).get("branches") or []

        def match(ref):
            return any(glob_matches(p, ref) for p in patterns)
        for ref in ("batch/2026-09-28a", "batch/2026-10-01b"):
            self.assertTrue(match(ref), "a push to %s must run CI (branches: %r)" % (ref, patterns))
        for ref in ("ci-sdk-install", "quickfix-x", "stack/a", "mainline", "batch", "xbatch/2026-09-28a", "feature/batch/x"):
            self.assertFalse(match(ref), "a push to the member branch %s must not run CI (branches: %r)" % (ref, patterns))
        # A merge to main re-tests the tree the batch push tested (land refuses a batch behind main), so
        # a full run there spends a private repository's minutes on a repeat (2026-09-27).
        self.assertFalse(match("main"), "a push to main runs CI again (branches: %r); the batch push already tested "
                                        "the tree a batch merge lands" % (patterns,))

    def test_the_manual_dispatch_stays(self):
        self.assertIn("workflow_dispatch", self.events, "the manual on-switch (the macOS gate) is gone")

    def test_the_glob_reader_itself(self):
        self.assertTrue(glob_matches("batch/**", "batch/a/b"))
        self.assertTrue(glob_matches("batch/*", "batch/a"))
        self.assertFalse(glob_matches("batch/*", "batch/a/b"))
        self.assertFalse(glob_matches("batch", "batch/a"))
        with self.assertRaises(LookupError):
            glob_matches("batch/[0-9]*", "batch/2")


def job_level_gates(src=None):
    """[(job, key)] for each job-level `if:` or `continue-on-error:` in the workflow, over every job it defines (job_keys),
    not over a list of known jobs."""
    return [(job, key) for job, keys in job_keys(src).items() for key in ("if", "continue-on-error") if key in keys]


class NoJobLevelGate(unittest.TestCase):
    """No job carries an `if:` or a `continue-on-error:` of its own: a skipped job reports success, and
    continue-on-error passes over a failure, so a batch head could read green with a suite that never ran.
    The triggers are the gate (CiTriggers). PR 872's check holds the python job to an allowlist of keys;
    this holds every job ci.yml defines, the python job included, to the two refusals, read from the file
    (job_level_gates): six jobs since this branch's merge of PR 928. A job added later is read by
    job_level_gates as it stands; test_a_gate_on_any_job_is_read, which holds ci.yml's job set equal to JOBS,
    then goes red asking for the new job's name in JOBS. A guard: it passes on the base too."""

    def test_the_six_jobs_exist(self):
        found = job_keys()
        for job in JOBS:
            self.assertIn(job, found, "no job %r in ci.yml; re-anchor this pin" % job)

    def test_no_job_level_if_or_continue_on_error(self):
        for job, key in job_level_gates():
            self.fail("the %s job carries a job-level %s:; a skipped job reports success and continue-on-error passes over "
                      "a failure, so CI could read green without running it" % (job, key))

    def test_a_gate_on_any_job_is_read(self):
        """A job-level if: or continue-on-error: planted on each job ci.yml defines, and on a job added at the end, is
        read. Until this branch's merge of PR 928 the check read a fixed list of four jobs, so on that merge a gate on
        vendored-tooling or served-pages, the two jobs 928 added, passed it."""
        src = _source()
        jobs = list(job_keys(src))
        self.assertEqual(sorted(jobs), sorted(JOBS), "re-anchor: the jobs are %r" % sorted(jobs))
        for job in jobs:
            m = re.search(r"^  %s:[ \t]*(?:#.*)?\n" % re.escape(job), src, re.M)
            self.assertIsNotNone(m, "the %s job's key line; re-anchor this pin" % job)
            for key, value in (("if", "false"), ("continue-on-error", "true")):
                with self.subTest(job=job, key=key):
                    planted = src[:m.end()] + "    %s: %s\n" % (key, value) + src[m.end():]
                    self.assertIn((job, key), job_level_gates(planted))
        added = src.rstrip("\n") + "\n\n  late:\n    if: false\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n"
        self.assertEqual(job_level_gates(added), [("late", "if")])


# ── a small evaluator for the concurrency stanza's ${{ }} expressions ────────────────────────────────────────────────

_TOKEN = re.compile(r"\s*(?:(?P<str>'(?:[^']|'')*')|(?P<op>==|!=|&&|\|\||!|\(|\)|,)|(?P<name>[A-Za-z_][\w.-]*))")


def _tokens(expr):
    out, pos = [], 0
    expr = expr.strip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if m is None or m.end() == pos:
            raise LookupError("a token this evaluator does not read at %r; re-anchor this pin" % expr[pos:])
        pos = m.end()
        if m.group("str") is not None:
            out.append(("str", m.group("str")[1:-1].replace("''", "'")))
        elif m.group("op") is not None:
            out.append(("op", m.group("op")))
        else:
            out.append(("name", m.group("name")))
    return out


def _truthy(v):
    return v not in (None, False, "", 0)


def _text_of(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    return "" if v is None else str(v)


def evaluate(expr, ctx):
    """GitHub's value semantics for the subset the stanza uses: string literals, github.event_name, github.ref and
    github.sha, `==` and `!=` (case-insensitive on strings), `!`, `&&` and `||` (which return an operand, not a
    boolean), parentheses, and startsWith(). Anything else raises LookupError."""
    toks = _tokens(expr)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else (None, None)

    def take(kind=None, value=None):
        t = peek()
        if t == (None, None) or (kind and t[0] != kind) or (value and t[1] != value):
            raise LookupError("unexpected %r in %r; re-anchor this pin" % (t[1], expr))
        pos[0] += 1
        return t

    def primary():
        kind, value = peek()
        if kind == "str":
            take()
            return value
        if kind == "op" and value == "(":
            take()
            v = or_()
            take("op", ")")
            return v
        if kind == "op" and value == "!":
            take()
            return not _truthy(primary())
        if kind == "name":
            take()
            if value in ("true", "false"):
                return value == "true"
            if value == "null":
                return None
            if peek() == ("op", "("):
                if value != "startsWith":
                    raise LookupError("the function %s() is not modelled; re-anchor this pin" % value)
                take()
                a = or_()
                take("op", ",")
                b = or_()
                take("op", ")")
                return _text_of(a).lower().startswith(_text_of(b).lower())
            if value not in ctx:
                raise LookupError("the name %s is not modelled; re-anchor this pin" % value)
            return ctx[value]
        raise LookupError("unexpected %r in %r; re-anchor this pin" % (value, expr))

    def eq():
        left = primary()
        while peek() in (("op", "=="), ("op", "!=")):
            op = take()[1]
            right = primary()
            same = (left.lower() == right.lower()) if isinstance(left, str) and isinstance(right, str) else left == right
            left = same if op == "==" else not same
        return left

    def and_():
        left = eq()
        while peek() == ("op", "&&"):
            take()
            right = eq()
            left = right if _truthy(left) else left
        return left

    def or_():
        left = and_()
        while peek() == ("op", "||"):
            take()
            right = and_()
            left = left if _truthy(left) else right
        return left

    v = or_()
    if pos[0] != len(toks):
        raise LookupError("trailing tokens in %r; re-anchor this pin" % expr)
    return v


def job_lines(src, job):
    """The lines of one job under `jobs:`."""
    lines = _block(src, "jobs")
    for key, _rest, i in _keys_at(lines, 2):
        if key == job:
            return _children(lines, i, 2)
    raise LookupError("no job %r in ci.yml; re-anchor this pin" % job)


def job_value(src, job, key):
    """A job-level key's value (runs-on), or None when the job has no such key."""
    for k, rest, _i in _keys_at(job_lines(src, job), 4):
        if k == key:
            return _strip_comment(rest)
    return None


def matrix_os(src, job):
    """(the job's strategy.matrix os: expression, [each include: entry's os]) as written."""
    jl = job_lines(src, job)
    strat = next((_children(jl, i, 4) for k, _r, i in _keys_at(jl, 4) if k == "strategy"), None)
    mat = next((_children(strat, i, 6) for k, _r, i in _keys_at(strat, 6) if k == "matrix"), None) if strat else None
    if mat is None:
        raise LookupError("the %s job has no strategy.matrix; re-anchor this pin" % job)
    keys = {k: (rest, i) for k, rest, i in _keys_at(mat, 8)}
    if "os" not in keys:
        raise LookupError("the %s job's matrix has no os:; re-anchor this pin" % job)
    includes = []
    if "include" in keys:
        for line in _children(mat, keys["include"][1], 8):
            m = re.match(r"^\s*(?:-\s+)?os:\s*(.*)$", line)
            flow = re.match(r"^\s*-?\s*\{(.*)\}\s*(?:#.*)?$", line)
            if m:
                includes.append(_unquote(_strip_comment(m.group(1))))
            elif flow:
                # a flow-form entry, `- {os: macos-latest, python-version: '3.11'}`: each key: value pair read
                pairs = [part.split(":", 1) for part in flow.group(1).split(",") if part.strip()]
                if any(len(pair) != 2 for pair in pairs):
                    raise LookupError("an include: entry the reader cannot split: %r; re-anchor this pin" % line)
                includes += [_unquote(v) for k, v in pairs if k.strip() == "os"]
            elif re.search(r"\bos\s*:", line):
                raise LookupError("an include: line names os: in a form this reader cannot read: %r; re-anchor this pin" % line)
    return _strip_comment(keys["os"][0]), includes


def os_list(expr, ctx):
    """The runner list an os: expression gives: `${{ fromJSON(<inner>) }}`, the inner expression evaluated and its
    string read as JSON (fromJSON is modelled for this one shape); anything else raises LookupError."""
    m = re.fullmatch(r"\$\{\{\s*fromJSON\((.*)\)\s*\}\}", expr.strip())
    if m is None:
        raise LookupError("the os: expression %r is not ${{ fromJSON(...) }}; re-anchor this pin" % expr)
    value = json.loads(_text_of(evaluate(m.group(1), ctx)))
    if not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
        raise LookupError("the os: expression %r gives %r, not a list of runner labels; re-anchor this pin" % (expr, value))
    return value


def render(template, ctx):
    """A value with embedded ${{ }} expressions, each replaced by its value as text; a value that is one expression
    alone keeps the expression's value, and a bare true or false is that boolean."""
    template = template.strip()
    whole = re.fullmatch(r"\$\{\{(.*)\}\}", template)
    if whole and "${{" not in whole.group(1):
        return evaluate(whole.group(1), ctx)
    if template in ("true", "false"):
        return template == "true"
    return re.sub(r"\$\{\{(.*?)\}\}", lambda m: _text_of(evaluate(m.group(1), ctx)), template)


def concurrency(src=None):
    """(group template, cancel-in-progress template) from the top-level concurrency stanza."""
    lines = _block(src if src is not None else _source(), "concurrency")
    keys = {k: _strip_comment(rest) for k, rest, _i in _keys_at(lines, 2)}
    if "group" not in keys or "cancel-in-progress" not in keys:
        raise LookupError("the concurrency stanza lacks group: or cancel-in-progress:; re-anchor this pin")
    return keys["group"], keys["cancel-in-progress"]


def run(event, ref, sha):
    return {"github.event_name": event, "github.ref": ref, "github.sha": sha}


SHA_A, SHA_B = "a" * 40, "b" * 40
MAIN, BATCH_X, BATCH_Y = "refs/heads/main", "refs/heads/batch/2026-09-28a", "refs/heads/batch/2026-09-28b"


class CiConcurrency(unittest.TestCase):
    """The stanza's two expressions, evaluated for every kind of run the triggers allow."""

    def setUp(self):
        self.group_t, self.cancel_t = concurrency()

    def group(self, *a):
        return render(self.group_t, run(*a))

    def cancels(self, *a):
        return _truthy(render(self.cancel_t, run(*a)))

    def test_pushes_to_main_get_a_group_per_commit_and_never_cancel(self):
        # main is not a push trigger (CiTriggers); the keying is held anyway, so adding main back cannot
        # make one merge's run cancel or replace another's (2026-09-08)
        a, b = self.group("push", MAIN, SHA_A), self.group("push", MAIN, SHA_B)
        self.assertNotEqual(a, b, "two merges to main share the group %r: the second would cancel or replace the first" % a)
        self.assertFalse(self.cancels("push", MAIN, SHA_A), "a push to main cancels an in-flight run: main's CI must never cancel itself")

    def test_a_newer_push_to_a_batch_branch_cancels_the_older_run_there_only(self):
        a, b = self.group("push", BATCH_X, SHA_A), self.group("push", BATCH_X, SHA_B)
        self.assertEqual(a, b, "two heads of one batch branch get the groups %r and %r: the rebuild does not supersede the old run" % (a, b))
        self.assertTrue(self.cancels("push", BATCH_X, SHA_B), "a newer push to a batch branch does not cancel the older run")
        self.assertNotEqual(a, self.group("push", BATCH_Y, SHA_A), "two batch branches share a group")
        self.assertNotEqual(a, self.group("push", MAIN, SHA_A), "a batch push shares main's group")

    def test_a_dispatch_is_keyed_apart_from_pushes_and_queues(self):
        for ref in (MAIN, BATCH_X):
            d = self.group("workflow_dispatch", ref, SHA_A)
            for sha in (SHA_A, SHA_B):
                self.assertNotEqual(d, self.group("push", ref, sha), "a dispatch on %s shares a push's group: the push cancels it" % ref)
            self.assertFalse(self.cancels("workflow_dispatch", ref, SHA_A), "a dispatch on %s cancels a run in flight" % ref)

    def test_the_schedule_never_cancels(self):
        self.assertFalse(self.cancels("schedule", MAIN, SHA_A))
        self.assertNotEqual(self.group("schedule", MAIN, SHA_A), self.group("push", MAIN, SHA_A))

    def test_the_evaluator_itself(self):
        ctx = run("push", MAIN, SHA_A)
        self.assertEqual(evaluate("github.event_name == 'PUSH' && github.sha || github.ref", ctx), SHA_A)
        self.assertEqual(evaluate("github.event_name == 'pull_request' && github.sha || github.ref", ctx), MAIN)
        self.assertIs(evaluate("!(github.event_name == 'push')", ctx), False)
        self.assertIs(evaluate("startsWith(github.ref, 'refs/heads/')", ctx), True)
        self.assertIs(render("true", ctx), True)
        with self.assertRaises(LookupError):
            evaluate("contains(github.ref, 'main')", ctx)
        with self.assertRaises(LookupError):
            evaluate("github.head_ref", ctx)



MATRIX_JOBS = ("python", "shell", "vendored-tooling")          # runs-on: ${{ matrix.os }}
FIXED_JOBS = ("secrets", "vscode-extension", "served-pages")   # runs-on: a literal label


class CiMatrixRunners(unittest.TestCase):
    """Round 1, tests-5: a batch push gets Linux alone. Every job's runners on a push to refs/heads/batch/x: each matrix
    job's (MATRIX_JOBS) evaluated os: list joined with every include: entry's os, and each other job's (FIXED_JOBS)
    literal runs-on. The weekly schedule and a manual dispatch add macOS to every matrix job."""

    def setUp(self):
        self.src = _source()

    def runners(self, event, ref, src=None):
        """{job: its runner labels} for EVERY job ci.yml defines (job_keys), not a list of the known ones: a job whose
        runs-on is `${{ matrix.os }}` gets its matrix's evaluated os: list joined with every include: entry's os, any
        other job its literal runs-on; a runs-on in neither form is a re-anchor."""
        src = self.src if src is None else src
        out = {}
        for job in job_keys(src):
            value = job_value(src, job, "runs-on")
            if value is None:
                raise LookupError("the %s job has no runs-on:; re-anchor this pin" % job)
            if value == "${{ matrix.os }}":
                expr, includes = matrix_os(src, job)
                out[job] = sorted(set(os_list(expr, run(event, ref, SHA_A))) | set(includes))
            elif "${{" in value:
                raise LookupError("the %s job's runs-on %r is neither ${{ matrix.os }} nor a literal; re-anchor this pin" % (job, value))
            else:
                out[job] = [_unquote(value)]
        return out

    def test_a_batch_push_runs_every_job_on_linux_alone(self):
        got = self.runners("push", BATCH_X)
        for job, labels in got.items():
            self.assertEqual(labels, ["ubuntu-latest"], "a batch push runs the %s job on %r; it gets Linux alone (macOS runs "
                                                        "only on the weekly schedule or a manual dispatch)" % (job, labels))
        self.assertEqual(sorted(got), sorted(MATRIX_JOBS + FIXED_JOBS), "re-anchor: the jobs are %r" % sorted(got))
        for job in MATRIX_JOBS:
            self.assertEqual(job_value(self.src, job, "runs-on"), "${{ matrix.os }}", "the %s job runs on its matrix's os" % job)

    def test_the_schedule_and_a_dispatch_add_macos_to_every_matrix_job(self):
        for event in ("schedule", "workflow_dispatch"):
            got = self.runners(event, MAIN)
            for job in MATRIX_JOBS:
                with self.subTest(event=event, job=job):
                    self.assertEqual(got[job], ["macos-latest", "ubuntu-latest"])

    def test_an_added_job_and_a_flow_form_include_are_read(self):
        """The two ways round 1's verify put a job on macOS for a batch push past the pin: an added job with a literal
        runs-on (the job set was then a fixed list of four) and a flow-form include: entry (the include reader read the
        block form only). Both are read now, and an include line that names os: in a form the reader cannot read is a
        re-anchor, not a silent skip."""
        fifth = self.src.rstrip("\n") + "\n\n  late:\n    runs-on: macos-latest\n    steps:\n      - run: true\n"
        self.assertEqual(self.runners("push", BATCH_X, src=fifth)["late"], ["macos-latest"])
        m = re.search(r"^(\s+)include:\s*\n", self.src, re.M)
        self.assertIsNotNone(m, "the python job's matrix has an include:; re-anchor this pin")
        pad = m.group(1) + "  "
        flow = self.src[:m.end()] + "%s- {os: macos-latest, python-version: '3.11'}\n" % pad + self.src[m.end():]
        got = self.runners("push", BATCH_X, src=flow)
        self.assertIn("macos-latest", got["python"], got)
        odd = self.src[:m.end()] + "%s-   os  :  macos-latest\n" % pad + self.src[m.end():]
        with self.assertRaises(LookupError):
            self.runners("push", BATCH_X, src=odd)

    def test_the_readers_themselves(self):
        ctx = run("push", BATCH_X, SHA_A)
        self.assertEqual(os_list("${{ fromJSON(github.event_name == 'push' && '[\"a\"]' || '[\"b\"]') }}", ctx), ["a"])
        with self.assertRaises(LookupError):
            os_list("ubuntu-latest", ctx)
        with self.assertRaises(LookupError):
            job_lines(self.src, "no-such-job")


if __name__ == "__main__":
    unittest.main()
