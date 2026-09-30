#!/usr/bin/env python3
"""The secret scan runs on every push whose commit carries its workflow and on every push to an open pull request's
branch, a workflow of its own, as one definition with ci.yml's secrets job (.github/workflows/secret-scan.yml, 2026-09-30).

Since 2026-09-27 ci.yml runs only on a push to a batch branch, by hand and on its weekly schedule. A push the pre-push
hook did not scan (CLAUDE.md, "Credentials", lists the kinds) then waited for the next of those runs, and a commit that
left every branch before one (force-pushed over, or on a deleted branch) was never scanned by CI, though GitHub still
serves it by its sha. secret-scan.yml runs ci.yml's secrets job on every push of a branch or a tag whose commit
carries that file (the PR's narrow landing delta, ruling 1) and on a pull request's opened, synchronize and reopened
events (the ruling of 2026-09-30 12:42Z, item 1): GitHub reads a push's workflows from the commit the push puts on its
ref, and a pull request's from the merge commit it makes of the PR's head and its base, which carries the base's copy,
so a PR's pushes are scanned on a branch cut before the file landed and on a PR from another repository, while a
branch cut before the file with no open PR starts no run until it merges main (the file's header says which pushes start
none). The two copies are held equal here instead of being written once as a reusable workflow that
both call: GitHub renders a called job's check name as "<caller job> / <called job>", and scripts/batch.py land tells
ci.yml's jobs by the names GitHub renders (ci_jobs, the coordinator's decision 18), as does the list of checks
docs/batching.md's maintainer section gives.

The checks, each over the files' text, read with tests/test_ci_vendored_job.py's readers (lines, job_block, content:
comment-only lines dropped, a `#` line inside a block scalar kept, nothing else changed), so the modules read the workflow
files one way. No YAML library is in the test deps.
1. IDENTITY. The job `secrets` of each file, split into its keys at four spaces (job_keys): the two jobs have the same
   keys, and every key but `name` has the same lines, trailing blank lines aside. That holds runs-on, permissions,
   timeout-minutes and steps (every step and field: the pinned version, its checksum, fetch-depth, each step's env,
   timeout and if, both scans' flags), and a key either copy adds (a job-level env:, if:, continue-on-error:,
   concurrency:, strategy:, defaults:) is a key the other lacks. Each of the four keys must be there, so the equality
   cannot hold over two copies that both dropped one. A workflow-level env:, defaults: or permissions: would reach the
   job from outside its block: ci.yml's top-level keys are held by tests/test_ci_vendored_job.py (check 3), and
   secret-scan.yml's here (check 3 below).
2. WHAT THE SCAN NEEDS, in both copies, since the equality alone passes a change made to both: the permissions are
   `contents: read` alone; the checkout step fetches at depth 0, without which the scan reads one commit; the install
   step checks the download against its pinned sha256; and the steps hold one history-scan line (`run: gitleaks git .`)
   whose --log-opts passes git log exactly --all, --diff-merges=first-parent and --text (every branch and tag the
   checkout fetched, a merge's own diff, and a path git would print as binary), on which the texts' coverage claims
   rest (the focused re-check's item 2 after the merge of main: dropping --all from both copies passed every check).
3. TRIGGERS. secret-scan.yml's top-level keys are name, on and jobs, in that order, so no concurrency group (whose cancel
   would drop a push's run when the next push to its branch arrives), and no workflow-level env:, defaults: or
   permissions:. Its on: block is exactly `push:` with no filter, so every push of any branch or tag whose commit
   carries the file starts a run, and `pull_request:` with `types: [opened, synchronize, reopened]` and no other
   filter, so a PR onto any base is scanned when it opens, on each push to its branch and when it reopens (SCAN_ON_LINES;
   a block that lacks either trigger, filters one, or adds another is red, the old push-only block among them). The
   block is held to those exact lines, so a spelling GitHub reads the same way (the types line dropped, since those
   three are its default) is red too, and is made together with SCAN_ON_LINES. Its jobs: holds the one job, and the job
   has no concurrency: key.
4. NAMES. Each copy's name line is its literal, and each name is held by exactly one content line across the workflow
   files (tests/test_ci_vendored_job.py's check_name_once). The names differ on purpose: GitHub matches a required
   status check by job name whatever the workflow, so one name for two jobs would let either meet a rule that names it.
   batch.py land reads the jobs of ci.yml's own run of the batch push (gh run list --workflow ci.yml, then the jobs of
   that run by its id), so the other workflow's job does not count toward a landing under either name.
EachFieldRedsOnItsDefect plants one change at a time into the real files' text, in memory: each field in each copy, a
change made to both copies where check 2 is the one that reads it, and each trigger and name change; each is red naming
what changed.
tests/gitleaks-config.bats runs ci.yml's history-scan line against the real scanner; check 1 makes secret-scan.yml's line
the same line."""
import difflib
import os
import re
import shlex
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the one import from a sibling module, as tests/test_ci_served_job.py does
sys.path.insert(0, ROOT)
from tests.test_ci_vendored_job import (WF_DIR, WorkflowShape, check_name_once, content, job_block, lines,  # noqa: E402
                                        on_block, raw, top_keys, workflow_texts)

CI = os.path.join(WF_DIR, "ci.yml")
SCAN = os.path.join(WF_DIR, "secret-scan.yml")
JOB = "secrets"
# The keys check 1 requires in both copies before it compares them.
HELD = ("runs-on", "permissions", "timeout-minutes", "steps")
PERMISSIONS = ["    permissions:", "      contents: read"]
FETCH_DEPTH = "          fetch-depth: 0"
CHECKSUM = re.compile(r'^          echo "\$\{GITLEAKS_SHA256\}  /tmp/gitleaks\.tar\.gz" \| sha256sum -c -$')
# The history scan's line in the steps, and the git log options its --log-opts must pass, no more and no fewer: --all
# (every branch and tag the checkout fetched, not the pushed ref's history alone), --diff-merges=first-parent (a merge's
# own diff, which `git log -p` omits) and --text (a path whose attributes mark it -diff, which `git log -p` prints as a
# binary line with no hunk). ci.yml's comment on the step gives the reasons; an added option (a --since, a pathspec)
# could narrow what the scan reads.
SCAN_RUN = re.compile(r"^        run: gitleaks git \. (?P<args>.*)$")
LOG_OPTS = ("--all", "--diff-merges=first-parent", "--text")
SCAN_TOP_KEYS = ["name", "on", "jobs"]
# The on: block, comment-only lines dropped: push with no filter, and pull_request with GitHub's three default types
# written out and no branch filter (under pull_request a branch filter selects the base branch).
SCAN_ON_LINES = ["on:", "  push:", "  pull_request:", "    types: [opened, synchronize, reopened]", ""]
CI_NAME = "Secret scan (gitleaks)"
SCAN_NAME = "Secret scan on push (gitleaks)"
# A key line at four spaces, the job's own keys.
KEY_LINE = re.compile(r"    (?P<key>[^ \t#:-][^:]*?)[ \t]*:(?:[ \t].*)?")
# A job's key line under jobs:, at two spaces.
JOB_LINE = re.compile(r"  (?P<key>[^ \t#:][^:]*?)[ \t]*:(?:[ \t].*)?")


def job_keys(src, who):
    """{key: [the key's line and the lines under it, trailing blank lines dropped]} for every key at four spaces of the job
    `secrets` in src, its block read by job_block and content. Raises WorkflowShape for a line at fewer than four spaces
    inside the block, a line at four spaces that is not a key, or a key given twice (YAML keeps the last copy)."""
    block = content(job_block(JOB, lines(src, who)))
    out, cur = {}, None
    for n, line in enumerate(block[1:], 2):
        if not line.strip(" \t"):
            if cur is not None:
                out[cur].append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent < 4:
            raise WorkflowShape("%s: line %d of the %s job's block (%r) is indented fewer than four spaces" % (who, n, JOB, line))
        if indent == 4:
            m = KEY_LINE.fullmatch(line)
            if m is None:
                raise WorkflowShape("%s: line %d of the %s job's block (%r) is at a key's indent and is not a key"
                                    % (who, n, JOB, line))
            cur = m.group("key")
            if cur in out:
                raise WorkflowShape("%s: the %s job gives %s: twice; YAML keeps the last copy" % (who, JOB, cur))
            out[cur] = [line]
            continue
        if cur is None:
            raise WorkflowShape("%s: line %d of the %s job's block (%r) comes before any key" % (who, n, JOB, line))
        out[cur].append(line)
    for key in out:
        while out[key] and not out[key][-1].strip(" \t"):
            out[key].pop()
    return out


def _diff(a, b, what):
    return "%s:\n%s" % (what, "\n".join(difflib.unified_diff(a, b, "ci.yml", "secret-scan.yml", lineterm="", n=1)))


def _both(ci_src, scan_src):
    """(ci.yml's job keys, secret-scan.yml's job keys, faults): the faults name a copy that cannot be read."""
    faults, got = [], []
    for src, who in ((ci_src, "ci.yml"), (scan_src, "secret-scan.yml")):
        try:
            got.append(job_keys(src, who))
        except WorkflowShape as e:
            got.append(None)
            faults.append(str(e))
    return got[0], got[1], faults


def identity_faults(ci_src, scan_src):
    """Check 1: the two copies' keys, and every key's lines but name's."""
    a, b, faults = _both(ci_src, scan_src)
    if faults:
        return faults
    for who, keys in (("ci.yml", a), ("secret-scan.yml", b)):
        faults += ["%s's %s job has no %s: key, which the identity check requires" % (who, JOB, k) for k in HELD if k not in keys]
    only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    if only_a or only_b:
        faults.append("the %s jobs' keys differ: only ci.yml's has %s, only secret-scan.yml's has %s"
                      % (JOB, only_a or "none", only_b or "none"))
    for k in [k for k in a if k in b and k != "name"]:
        if a[k] != b[k]:
            faults.append(_diff(a[k], b[k], "the %s jobs' %s: lines differ" % (JOB, k)))
    return faults


def log_opts_faults(who, steps):
    """The faults of one copy's history-scan line: the steps hold exactly one `run: gitleaks git .` line, its words split
    as a shell splits them, one --log-opts=VALUE word among them (the option written as a word of its own, with its
    value in the next, is refused too, so the one form is read), and VALUE's words are LOG_OPTS, in any order."""
    found = [m for m in (SCAN_RUN.match(l) for l in steps) if m]
    if len(found) != 1:
        return ["%s's %s job's steps hold %d `run: gitleaks git .` lines, not 1, so the history scan's log options cannot be "
                "read" % (who, JOB, len(found))]
    try:
        words = shlex.split(found[0].group("args"))
    except ValueError as e:
        return ["%s's %s job's history-scan line cannot be split into words (%s)" % (who, JOB, e)]
    values = [w[len("--log-opts="):] for w in words if w.startswith("--log-opts=")]
    if len(values) != 1 or "--log-opts" in words:
        return ["%s's %s job's history-scan line gives %d --log-opts=VALUE words%s, not 1" % (
            who, JOB, len(values), " and --log-opts as a word of its own" if "--log-opts" in words else "")]
    try:
        got = shlex.split(values[0])
    except ValueError as e:
        return ["%s's %s job's --log-opts value cannot be split into words (%s)" % (who, JOB, e)]
    if sorted(got) != sorted(LOG_OPTS):
        missing = [o for o in LOG_OPTS if o not in got]
        added = [o for o in got if o not in LOG_OPTS or got.count(o) > 1]
        return ["%s's %s job's history scan passes --log-opts %r, not %r (%s)" % (
            who, JOB, got, list(LOG_OPTS), "; ".join(
                (["lacks " + ", ".join(missing)] if missing else []) + (["adds " + ", ".join(added)] if added else [])))]
    return []


def needs_faults(ci_src, scan_src):
    """Check 2: in each copy, the permissions are contents: read alone, the checkout fetches at depth 0, the install
    step checks the download's sha256, and the history scan passes git log exactly LOG_OPTS (log_opts_faults)."""
    a, b, faults = _both(ci_src, scan_src)
    if faults:
        return faults
    for who, keys in (("ci.yml", a), ("secret-scan.yml", b)):
        if keys.get("permissions") != PERMISSIONS:
            faults.append("%s's %s job's permissions are %r, not %r" % (who, JOB, keys.get("permissions"), PERMISSIONS))
        steps = keys.get("steps") or []
        if FETCH_DEPTH not in steps:
            faults.append("%s's %s job's steps hold no %r line: a default checkout fetches one commit, and the history scan "
                          "then reads that commit alone" % (who, JOB, FETCH_DEPTH.strip()))
        if not any(CHECKSUM.match(l) for l in steps):
            faults.append("%s's %s job's steps hold no line checking the download against GITLEAKS_SHA256 with sha256sum -c"
                          % (who, JOB))
        faults += log_opts_faults(who, steps)
    return faults


def trigger_faults(scan_src):
    """Check 3: secret-scan.yml's top-level keys, its on: block, its one job and that job's lack of a concurrency: key."""
    try:
        ls = lines(scan_src, "secret-scan.yml")
        keys = top_keys(ls)
        on = content(on_block(ls))
        job = job_keys(scan_src, "secret-scan.yml")
    except WorkflowShape as e:
        return [str(e)]
    faults = []
    if keys != SCAN_TOP_KEYS:
        faults.append("secret-scan.yml's top-level keys are %r, not %r" % (keys, SCAN_TOP_KEYS))
    if on != SCAN_ON_LINES:
        faults.append("secret-scan.yml's on: block, comment-only lines aside, is %r, not %r" % (on, SCAN_ON_LINES))
    at = [i for i, l in enumerate(ls) if l.split(":", 1)[0] == "jobs"]
    after = ls[at[0] + 1:] if len(at) == 1 else []
    stop = next((i for i, l in enumerate(after) if l[:1] not in ("", " ", "\t", "#")), len(after))
    jobs = [JOB_LINE.fullmatch(l).group("key") for l in after[:stop] if JOB_LINE.fullmatch(l)]
    if jobs != [JOB]:
        faults.append("secret-scan.yml's jobs are %r, not [%r]" % (jobs, JOB))
    if "concurrency" in job:
        faults.append("secret-scan.yml's %s job has a concurrency: key: a group that cancels drops a push's run when the "
                      "next push to its branch arrives" % JOB)
    return faults


def name_faults(ci_src, scan_src, texts):
    """Check 4: each copy's name line is its literal, and each name is on exactly one content line of the workflow files."""
    a, b, faults = _both(ci_src, scan_src)
    if faults:
        return faults
    for who, keys, name in (("ci.yml", a, CI_NAME), ("secret-scan.yml", b, SCAN_NAME)):
        if keys.get("name") != ["    name: " + name]:
            faults.append("%s's %s job's name lines are %r, not [%r]" % (who, JOB, keys.get("name"), "    name: " + name))
    return faults + check_name_once(CI_NAME, texts) + check_name_once(SCAN_NAME, texts)


class SecretScanIsCiJobOnEveryPush(unittest.TestCase):
    def setUp(self):
        self.ci, self.scan = raw(CI), raw(SCAN)

    def assertNoFaults(self, faults, why):
        if faults:
            self.fail("%s\n%s" % ("\n".join(faults), why))

    def test_1_the_two_copies_of_the_job_are_equal_but_for_the_name(self):
        self.assertNoFaults(identity_faults(self.ci, self.scan), (
            "ci.yml's secrets job and secret-scan.yml's are not the same job (above). They are one definition of the secret "
            "scan, run by ci.yml on a batch push, by hand and on the schedule, and by secret-scan.yml on every push whose "
            "commit carries it and every push to an open pull request's branch; a "
            "change to one copy is made to the other in the same commit, every key but the name."))

    def test_2_both_copies_hold_what_the_scan_needs(self):
        self.assertNoFaults(needs_faults(self.ci, self.scan), (
            "A copy of the secrets job lost something the scan needs (above): read-only contents, a full-history checkout, "
            "the checksum check on the pinned gitleaks download, or the history scan's git log options (--all, "
            "--diff-merges=first-parent, --text)."))

    def test_3_secret_scan_runs_on_every_push_and_every_pull_request_push_and_cancels_no_run(self):
        self.assertNoFaults(trigger_faults(self.scan), (
            "secret-scan.yml's triggers or layout changed (above). It runs on every push of any branch or tag whose commit "
            "carries it, and on a pull request's opened, synchronize and reopened events, with no "
            "filter and no concurrency group, so each run completes; its one job is ci.yml's secrets job, and a "
            "workflow-level env:, defaults: or permissions: would reach that job from outside the block check 1 compares."))

    def test_4_each_copy_keeps_its_own_name(self):
        self.assertNoFaults(name_faults(self.ci, self.scan, workflow_texts()), (
            "The two secrets jobs' names changed, or a name is on more than one content line of the workflow files (above). "
            "GitHub matches a required status check by job name whatever the workflow, so the two jobs keep two names."))


# The history scan's line as both copies hold it, the anchor of the plants on its log options.
SCAN_LINE = ('        run: gitleaks git . --no-banner --redact -v --config .gitleaks.toml '
             '--log-opts="--all --diff-merges=first-parent --text"')


# pull_request's types line as secret-scan.yml holds it, the anchor of the plants on that trigger.
TYPES_LINE = "    types: [opened, synchronize, reopened]"


class EachFieldRedsOnItsDefect(unittest.TestCase):
    """Each check over the real files' text with one change planted in memory, inside the secrets job's block of the file
    named (or in secret-scan.yml's lines before jobs:): green as read, red on each plant, naming what changed."""

    def setUp(self):
        self.ci, self.scan = raw(CI), raw(SCAN)

    @staticmethod
    def plant(src, anchor, new, part="job"):
        """src with the one line `anchor` inside the secrets job's block (part "job") or before jobs: (part "top") replaced
        by the lines `new`. Raises AssertionError unless the anchor is there exactly once."""
        ls = src.split("\n")
        if part == "job":
            lo = ls.index("  %s:" % JOB)
            hi = next((i for i in range(lo + 1, len(ls)) if re.match(r"(?:  )?[^ \t#]", ls[i])), len(ls))
        else:
            lo, hi = 0, ls.index("jobs:")
        at = [i for i in range(lo, hi) if ls[i] == anchor]
        assert len(at) == 1, "the plant's anchor %r is in the %s part %d times, not once" % (anchor, part, len(at))
        return "\n".join(ls[:at[0]] + new + ls[at[0] + 1:])

    def checks(self, ci, scan):
        return {"identity": identity_faults(ci, scan), "needs": needs_faults(ci, scan), "triggers": trigger_faults(scan),
                "names": name_faults(ci, scan, [("ci.yml", ci), ("secret-scan.yml", scan)])}

    def test_the_real_files_pass_every_check(self):
        self.assertEqual(self.checks(self.ci, self.scan), {"identity": [], "needs": [], "triggers": [], "names": []})

    def red(self, ci, scan, check, word):
        got = self.checks(ci, scan)
        self.assertTrue(got[check], "the %s check read the plant green" % check)
        self.assertIn(word, "\n".join(got[check]), "the %s check is red but does not name %r" % (check, word))

    def test_a_field_changed_in_one_copy_is_red(self):
        run_dir = "        run: gitleaks dir . --no-banner --redact -v --config .gitleaks.toml"
        plants = (
            ("steps", "a scan's flag dropped", run_dir, [run_dir.replace(" -v", "")]),
            ("steps", "a step's env value", "          GITLEAKS_VERSION: 8.28.0", ["          GITLEAKS_VERSION: 8.28.1"]),
            ("steps", "a step's env added", "          GITLEAKS_VERSION: 8.28.0",
             ["          GITLEAKS_VERSION: 8.28.0", "          GITLEAKS_CONFIG: other.toml"]),
            ("steps", "a step's if", "        if: ${{ !cancelled() }}", ["        if: ${{ success() }}"]),
            ("steps", "a step's timeout", "        timeout-minutes: 5", ["        timeout-minutes: 6"]),
            ("runs-on", "the runner", "    runs-on: ubuntu-latest", ["    runs-on: ubuntu-22.04"]),
            ("timeout-minutes", "the job's cap", "    timeout-minutes: 10", ["    timeout-minutes: 11"]),
            ("permissions", "a permission's value", "      contents: read", ["      contents: write"]),
            ("permissions", "a permission added", "      contents: read", ["      contents: read", "      actions: read"]),
        )
        for field, what, anchor, new in plants:
            for who in ("ci.yml", "secret-scan.yml"):
                with self.subTest(field=field, what=what, copy=who):
                    ci = self.plant(self.ci, anchor, new) if who == "ci.yml" else self.ci
                    scan = self.plant(self.scan, anchor, new) if who == "secret-scan.yml" else self.scan
                    self.red(ci, scan, "identity", "%s: lines differ" % field)

    def test_a_key_added_to_or_dropped_from_one_copy_is_red(self):
        runs_on = "    runs-on: ubuntu-latest"
        plants = (
            ("a job-level env:", runs_on, [runs_on, "    env:", "      GITLEAKS_CONFIG: other.toml"], "env"),
            ("a job-level if:", runs_on, [runs_on, "    if: false"], "if"),
            ("continue-on-error:", runs_on, [runs_on, "    continue-on-error: true"], "continue-on-error"),
            ("a job-level concurrency:", runs_on, [runs_on, "    concurrency:", "      group: g", "      cancel-in-progress: true"],
             "concurrency"),
            ("permissions dropped", "    permissions:", [], "permissions"),
        )
        for what, anchor, new, key in plants:
            for who in ("ci.yml", "secret-scan.yml"):
                with self.subTest(what=what, copy=who):
                    if key == "permissions":
                        drop = lambda s: self.plant(self.plant(s, "    permissions:", []), "      contents: read", [])  # noqa: E731
                        ci = drop(self.ci) if who == "ci.yml" else self.ci
                        scan = drop(self.scan) if who == "secret-scan.yml" else self.scan
                    else:
                        ci = self.plant(self.ci, anchor, new) if who == "ci.yml" else self.ci
                        scan = self.plant(self.scan, anchor, new) if who == "secret-scan.yml" else self.scan
                    self.red(ci, scan, "identity", "keys differ")
                    self.assertIn(repr(key), "\n".join(self.checks(ci, scan)["identity"]))

    def test_a_held_key_dropped_from_both_copies_is_red(self):
        for key, anchor in (("runs-on", "    runs-on: ubuntu-latest"), ("timeout-minutes", "    timeout-minutes: 10")):
            with self.subTest(key=key):
                self.red(self.plant(self.ci, anchor, []), self.plant(self.scan, anchor, []), "identity",
                         "has no %s: key" % key)

    def test_what_the_scan_needs_changed_in_both_copies_is_red(self):
        """Each plant is made to both copies alike, so the identity check reads it green and check 2 is the one that must
        be red, naming what changed."""
        plants = (
            ("contents: write", "      contents: read", ["      contents: write"], "permissions are"),
            ("fetch-depth 1", FETCH_DEPTH, ["          fetch-depth: 1"], "fetch-depth: 0"),
            ("no checksum check", '          echo "${GITLEAKS_SHA256}  /tmp/gitleaks.tar.gz" | sha256sum -c -', [],
             "sha256sum -c"),
            # the history scan's git log options (the focused re-check's item 2 after the merge of main)
            ("--all dropped", SCAN_LINE, [SCAN_LINE.replace('="--all ', '="')], "lacks --all"),
            ("--diff-merges=first-parent dropped", SCAN_LINE, [SCAN_LINE.replace(" --diff-merges=first-parent", "")],
             "lacks --diff-merges=first-parent"),
            ("--text dropped", SCAN_LINE, [SCAN_LINE.replace(' --text"', '"')], "lacks --text"),
            ("all three dropped", SCAN_LINE, [SCAN_LINE.replace('--all --diff-merges=first-parent --text', '')],
             "lacks --all, --diff-merges=first-parent, --text"),
            ("a narrowing option added", SCAN_LINE, [SCAN_LINE.replace(' --text"', ' --text --since=2026-01-01"')],
             "adds --since=2026-01-01"),
            ("--log-opts dropped", SCAN_LINE, [SCAN_LINE.replace(' --log-opts="--all --diff-merges=first-parent --text"', '')],
             "gives 0 --log-opts=VALUE words"),
            ("--log-opts as a word of its own", SCAN_LINE, [SCAN_LINE.replace('--log-opts=', '--log-opts ')],
             "--log-opts as a word of its own"),
            ("the history scan moved into a block scalar", SCAN_LINE,
             ["        run: |", "          " + SCAN_LINE.split("run: ", 1)[1]], "hold 0 `run: gitleaks git .` lines"),
        )
        for what, anchor, new, word in plants:
            with self.subTest(what=what):
                ci, scan = self.plant(self.ci, anchor, new), self.plant(self.scan, anchor, new)
                self.assertEqual(identity_faults(ci, scan), [], "the plant is made to both copies alike")
                self.red(ci, scan, "needs", word)

    def test_a_trigger_or_layout_change_is_red(self):
        plants = (
            ("a branch filter", "  push:", ["  push:", "    branches: [main]"], "top", "on: block"),
            ("a tags filter", "  push:", ["  push:", "    tags: ['v*']"], "top", "on: block"),
            ("push dropped", "  push:", [], "top", "on: block"),
            ("a pull_request branch filter", TYPES_LINE, [TYPES_LINE, "    branches: [main]"], "top", "on: block"),
            ("a pull_request type dropped", TYPES_LINE, ["    types: [opened, reopened]"], "top", "on: block"),
            ("a pull_request type added", TYPES_LINE, ["    types: [opened, synchronize, reopened, edited]"], "top",
             "on: block"),
            ("pull_request replaced by pull_request_target", "  pull_request:", ["  pull_request_target:"], "top",
             "on: block"),
            ("a third trigger", TYPES_LINE, [TYPES_LINE, "  workflow_dispatch:"], "top", "on: block"),
            ("a concurrency group", "on:", ["concurrency:", "  group: g", "  cancel-in-progress: true", "on:"], "top",
             "top-level keys"),
            ("a workflow env:", "on:", ["env:", "  GITLEAKS_CONFIG: other.toml", "on:"], "top", "top-level keys"),
            ("a workflow permissions:", "on:", ["permissions:", "  contents: write", "on:"], "top", "top-level keys"),
            ("a second job", "  secrets:", ["  other:", "    runs-on: ubuntu-latest", "    steps:", "      - run: true",
                                            "  secrets:"], "job", "jobs are"),
        )
        for what, anchor, new, part, word in plants:
            with self.subTest(what=what):
                self.red(self.ci, self.plant(self.scan, anchor, new, part), "triggers", word)

    def test_the_push_only_triggers_are_red(self):
        """The on: block as it stood before the pull_request trigger (`push:` alone) is red: a PR whose branch lacks the
        file (cut before it landed, or from another repository) would start no run (the 12:42Z ruling's item 1)."""
        scan = self.plant(self.plant(self.scan, "  pull_request:", [], "top"), TYPES_LINE, [], "top")
        self.assertIn("on:\n  push:\n\njobs:", scan, "the plant rebuilds the old push-only block")
        self.red(self.ci, scan, "triggers", "on: block")

    def test_a_concurrency_key_on_both_jobs_is_red(self):
        runs_on = "    runs-on: ubuntu-latest"
        new = [runs_on, "    concurrency:", "      group: g", "      cancel-in-progress: true"]
        ci, scan = self.plant(self.ci, runs_on, new), self.plant(self.scan, runs_on, new)
        self.assertEqual(identity_faults(ci, scan), [], "the plant is made to both copies alike")
        self.red(ci, scan, "triggers", "concurrency: key")

    def test_a_name_change_is_red(self):
        plants = (
            ("secret-scan.yml's job named as ci.yml's", "secret-scan.yml", "    name: " + SCAN_NAME, ["    name: " + CI_NAME],
             "name lines are"),
            ("ci.yml's job renamed", "ci.yml", "    name: " + CI_NAME, ["    name: Secrets"], "name lines are"),
        )
        for what, who, anchor, new, word in plants:
            with self.subTest(what=what):
                ci = self.plant(self.ci, anchor, new) if who == "ci.yml" else self.ci
                scan = self.plant(self.scan, anchor, new) if who == "secret-scan.yml" else self.scan
                self.red(ci, scan, "names", word)
                self.assertEqual(identity_faults(ci, scan), [], "the name is the one key the identity check leaves free")
        for name in (CI_NAME, SCAN_NAME):
            with self.subTest(what="a job of another workflow file named %r" % name):
                other = "name: Other\non:\n  push:\njobs:\n  other:\n    name: %s\n    runs-on: ubuntu-latest\n" % name
                texts = [("ci.yml", self.ci), ("other.yml", other), ("secret-scan.yml", self.scan)]
                self.assertIn("%r is held by 2 content lines" % name, "\n".join(name_faults(self.ci, self.scan, texts)))

    def test_a_key_given_twice_or_a_line_out_of_place_is_refused(self):
        runs_on = "    runs-on: ubuntu-latest"
        for what, new, word in (("runs-on twice", [runs_on, runs_on], "gives runs-on: twice"),
                                ("a line at three spaces", [runs_on, "   x: y"], "fewer than four spaces"),
                                ("a sequence at four spaces", [runs_on, "    - x"], "is not a key")):
            with self.subTest(what=what):
                self.red(self.ci, self.plant(self.scan, runs_on, new), "identity", word)


if __name__ == "__main__":
    unittest.main()
