#!/usr/bin/env python3
"""scripts/batch.py: land many PRs as one batch PR with one merge commit.

Member PRs stay ordinary PRs against main. This tool merges their heads, in dependency order, into
a fresh branch `batch/<name>`, the batcher runs the local sweep (scripts/sweep.py) at the batch head,
and one PR to main carries a generated digest. When that PR is merged with a merge commit, GitHub marks every member
merged on its own (a PR is marked merged when its head commits become reachable from its base
branch through another merge: "indirect merges"). No member is ever merged into another PR's
branch, and nothing here squashes or rebases: a squash or rebase of the batch would rewrite the
SHAs, leave every member open, and break retargeting.

Subcommands, in the order a batch goes through them:

  plan       [--labeled] [--only N]... [--name N]
                                      pick the members, order them, predict conflicts, write the plan
                                      (--only N: a single PR lands as a one-member batch)
  assemble   <name> [--without N] [--resolve N] [--repin N|all] [--continue|--abort] [--merge-main]
                                      merge the pinned heads into ../romp-batch-<name> (the branch
                                      is the mutex: refuses if another origin/batch/* exists)
  verify     <name>                   provenance, pinned heads, bases, main contained, ledger check,
                                      the sweep result at the batch head's full sha
  summarize  <name>                   create or update the batch PR body; comment on each member
  pull       <name> N [--reason ..]   rebuild without N (and N's dependents), push, re-summarize
  land       <name> [--auto]          verify again, read the batch head's CI run (green or refused),
                                      then merge the batch PR with a merge commit
  finish     <name>                   confirm members read MERGED, retarget, delete branches, orphans
  bisect     <name> -- <cmd...>       first-parent bisect of the batch chain; names the member

State lives in `<git common dir>/batch/<name>.json` (shared by every worktree of the clone), read only as a
regular file and without waiting (read_state: a FIFO or a symlink there, which a sweep's leg can leave through its
checkout's alternates, stops the command, naming the file). The tool needs git and the GitHub CLI (`gh`, or the
binary named by ROMP_GH); it imports nothing beyond the standard library and its sibling scripts/sweep.py, whose reader
verify uses for the sweep result
(`<state dir>/sweeps/<full sha>.json`, written by `scripts/sweep.py run`). It acts on the clone it
lives in, the directory above its scripts/ directory (or ROMP_BATCH_REPO), never on the shell's cwd, so a
misnamed cwd cannot make it assemble the wrong repository; that directory must hold the clone's .git, and
one that does not (a mistyped ROMP_BATCH_REPO, a .git removed) stops the command, naming it, rather than
being resolved to a repository that encloses it.

Contracts the tests hold this file to (tests/test_batch_tool.py):
  - plan orders dependents after their bases and excludes drafts, `major-feature` and `hold`; a
    `Depends-on` cycle excludes its members (and their dependents), not the plan; plan --only N plans N
    alone (a single PR lands as a one-member batch), refusing a number that is not an open PR;
  - plan excludes a candidate whose pinned head has no passing sweep result of its own (read through the
    reader verify uses, so a member's head owes every leg, the webview legs, pdf-smoke and the served leg
    included, as a batch head does),
    naming the case, and its dependents with it; assemble --repin refuses a re-read head without one; both record
    on the member the pass they read, and the body's members table shows that record, never the author's trailer
    (a member recorded without one reads "not recorded");
  - assemble refuses when any other `batch/*` ref exists on origin;
  - provenance fails on an undeclared commit and passes on a `batch:` commit;
  - every merge on the chain (a member's or origin/main's) equals the clean merge of its parents,
    or carries a recorded resolution and then differs from it only in the resolution's files, which
    cover every path merge-tree calls conflicted and hold no conflict marker (nor does --continue
    ever commit one); a stop lists the files rerere replayed along with the ones still unmerged;
  - a resolution that took one side wholesale says so, in the digest line and above its diff, which
    runs from the clean merge of the parents to the merge;
  - verify fails when a pinned head moved, and when an assembly did not finish; so does finish;
  - verify refuses a missing, stale, unfinished, red, invalid, incomplete or unreadable sweep result
    for the batch head's full sha, one that marks a leg not owed for having no vscode-extension/package.json
    while the head's tree holds one, or the ledger not owed for having no scripts/upstream-ledger.py while the
    head's tree holds that script (plan and --repin refuse the same at a member's head), and a batch head
    that does not contain main as origin has it now (ci.yml does not run on the merge to main, so the tree that
    lands must be the tree the sweep and the batch branch's CI ran on); a result that marks deps, a webview
    leg, pdf-smoke or the served leg not owed for any other reason reads invalid, whatever the diff (every head
    owes the webview legs, pdf-smoke and the served leg), and so does one that marks the ledger not owed for any
    reason but a missing ledger script;
    land re-runs verify and refuses the same. The reader reads the result's whole history (append-only
    runs): a failed run that no later run excused with --flake naming the leg reads red, naming the run and
    its logs, and a result recorded under another leg environment (the allowlist hash) reads invalid; verify
    and the body name each invalid run the history holds, with each leg it failed: invalidity voids a run's
    passes, never its failures, so such a failure needs --flake naming the leg like any other;
  - land reads main on origin before it retargets any member and once more right before the merge call, and
    refuses if it moved since verify, naming any member it had retargeted and how to restore its base; what
    no read can stop, a move between the last read and GitHub's merge (the merge pins the head, not the
    base) or before an --auto merge fires later (--auto is refused until the repository allows auto-merge
    and a rule on main gates a merge; the fork had neither on 2026-09-27), finish reports: it fails loudly,
    after its cleanup, when the merge commit's first parent is not the main verify read, or its second parent
    not the batch head verify read (a commit pushed after verify and merged by the button), naming both shas
    and the sweep at the merge commit that is owed;
  - finish names the batch head's CI run with land's own filtered read (the push run at the landed head, the
    merge commit's second parent), and reports a read that fails after the merge as unread;
  - land requires the batch head's CI run green, read from GitHub at land time before anything changes:
    the newest run of ci.yml from a push to the batch branch at exactly the verified head, whose success counts only
    when every job of ci.yml at the head has a job run in its latest attempt that passed (the coordinator's decision
    18: a success over the label checks alone, or over no job run, is not a green run) (by createdAt,
    then databaseId; a matching row with either, or its attempt, missing or malformed, the zero time
    included, is refused by name, and so is a list as long as land's limit); a missing, pending or red
    run, a failed read, or an answer that is not a JSON list of run records (round 2, extra8-3), is refused by name, and a run at another sha, from another event or on another
    branch does not count. Every other attempt of a push run at that head, the newest run's earlier
    attempts and every attempt of an older push run of the same sha, that did not pass is refused unless
    land's --flake names it (a red is not erased by a GitHub re-run or a second push either; one attempt
    across the runs at the head is excused), and land records the excused attempt in the state for finish;
  - pull N drops N's dependents, unless N already merged into main;
  - every git process this tool starts itself goes through run_git (tests/test_git_call_census.py holds every place this
    file starts a process to a named allowlist, on which run_git is the one that starts git), which names the repository
    the call means, GIT_DIR, GIT_COMMON_DIR and GIT_WORK_TREE set and GIT_CEILING_DIRECTORIES at the directory above the
    work tree (but for find_repo's discovery call, which sets the ceiling alone, at the parent of the directory holding
    .git: repo_root makes it once for the clone, and repo_for before every call made in a batch worktree, each at a
    directory that must itself hold .git and be git's work tree there, never walked up from), so a .git that git does
    not recognize fails the call instead of sending git up to an
    enclosing repository (the 02:43Z ruling, item 1(b)), runs with core.warnAmbiguousRefs off (QUIET_NAMES), so a full
    object id a call resolves as an object reads no ref, and a name opens the names git's rules try up to the first that
    finds a ref and none of the later ones git would open to warn that it is ambiguous (bisect's checkouts, git bisect
    start and its good, bad and skip steps look a commit id up as a ref name under every rule whatever the setting, and
    assemble's merges, which would under merge.log, pass --no-log: QUIET_NAMES' comment), and
    bounds its wait at GIT_BOUND, 600 s (item 1(a)): a git still
    running then (waiting on a FIFO at the
    clone's shallow file, config or HEAD, which a sweep's leg
    can plant through its checkout's alternates, say) is killed with its process group, and the command stops there with
    GitBound, a Fail (exit 1) naming the call, except in finish's read of the landed head's CI run, which, the merge
    having happened, reports any Fail there, GitBound included, as unread after the merge and carries on. The bound is far above the slowest call
    measured (a member's merge, under a second; the comment at GIT_BOUND gives the figures), and larger than
    scripts/sweep.py's because a push runs the pre-push hook, whose scan is not measured, and a fetch can bring new
    commits (one of 70 days of history took up to 59 s: GIT_SETTINGS' comment).
    verify's read of the excuse rule runs its git through scripts/sweep.py, at that script's bound and limits. The two
    processes the tool starts that run git in the clone, scripts/pr-orphans.sh (finish) and the ledger script (verify's
    check,
    assemble's row import), start through run_tool, each with the GIT_DIR, GIT_COMMON_DIR, GIT_WORK_TREE and ceiling of
    the tree it runs in in its environment (the clone for pr-orphans.sh; the batch worktree, or the ledger check's
    temporary worktree, for the ledger script) and GIT_BOUND with the process-group kill, as run_git's calls have (the
    closing check wf_3b100f5e-b38, its item 5); finish reports a pr-orphans.sh killed at the bound as unread, the merge
    having happened, and carries on. Every such git, and every run_tool process, also has a memory limit and an output
    limit, scripts/sweep.py's, read from that module (git_limits; round 1 of PR 959, V1): GIT_MEMORY, 1 GiB, of address
    space (HOOK_MEMORY, 16 GiB, for a push, a commit or a merge, which run the clone's hooks, and a pre-push or pre-commit
    hook can start gitleaks; each comes after a listing of the refs under GIT_MEMORY, _refs_listed; but git merge
    --abort, which runs none of a merge's hooks, runs under GIT_MEMORY with no listing before it: _runs_hooks), so a git
    of this tool's own that reads
    without end (a symlink to /dev/zero at origin/main's loose file, which a sweep's leg can leave through its
    checkout's alternates) fails at the limit and the command stops with GitMemory, naming the call, the limit and the
    files of the repository git reads whole that are not regular files or are oversized when it is raised (the loose
    refs, packed-refs, objects/info/alternates, the shallow file and the files of the refs the call names; round 2 of
    PR 959, ruling C, item 3: _odd_files), and, for a call that lists the refs under a prefix (pick_name's and
    other_remote_batches' for-each-ref of refs/remotes/origin/batch/), that directory, named as one: the loose refs
    under <dir>/ (ruling D, extra4-3: _ref_files); and GIT_OUTPUT_MAX, 64 MiB a stream, past which the
    process is killed with its group and the command stops with GitOutput, naming the call and the stream. Both are
    GitBound Fails, which finish reports after the merge as it reports one at the bound. A git that pr-orphans.sh or the
    ledger script starts has the same memory limit, and GIT_SETTINGS through its environment (round 2 of PR 959,
    ruling B; run_tool's docstring says which gits the scripts run), so it needs what this tool's own calls need and
    starts no gc or maintenance under the limit; but the script reads that git's failure as it reads any other:
    pr-orphans.sh as a merged PR whose content is not on main (or, with no merge commit recorded, unknown), the ledger
    import as a row no commit introduced (dated today), so a failure at the limit there is not named. origin/main and
    the batch branches are named by their full refs (MAIN_REF, batch_ref) wherever a call needs only their commit, and
    finish's check that the local batch branch is still there and bisect's cleanups name it so too (the 22:25Z ruling
    of 2026-10-03 on PR 959, item 1; the cleanups put the branch's tree back with git read-tree and point HEAD at the
    branch with git symbolic-ref, since git checkout stays on a branch only when given its short name), so while the
    ref exists git opens no other name its rev-parse rules try for it (refs/tags/origin/main, <common dir>/batch/<name>
    and the rest); an absent full ref sends git on through the names those rules make of the full name (plan's and
    verify's reads of a deleted base branch, verify's check for the batch branch), but for finish's check, git show-ref
    --verify, which reads only that ref. Two calls still name the batch branch by its short name, both assemble's
    (prepare_worktree): git worktree add -B batch/<name>, which makes the branch and its worktree, and git checkout -B
    batch/<name> MAIN_REF, which resets the branch in a worktree it reuses; git looks the name up by its rules once it
    has set the branch, so each opens <common dir>/batch/<name>, refs/batch/<name> and refs/tags/batch/<name> before
    refs/heads/batch/<name> (SHORT_NAME_RULES), each under the common dir, from the batch worktree too, and git checkout
    -B first looks its start point up as a local branch, refs/heads/refs/remotes/origin/main. Both run under GIT_MEMORY
    (their witness: tests/test_batch_tool.py,
    test_assembles_branch_reset_reads_the_branchs_short_name_and_stops_at_the_memory_limit), and the GitMemory of either
    names each of those files that is not a regular file or is oversized (_ref_files; round 2 of PR 959, ruling D,
    fresh-2: before it no GitMemory named <common dir>/batch/<name>, which is outside refs/). And the listing of the
    remote batch branches (pick_name, other_remote_batches: for-each-ref with %(refname:short)) shortens each
    refs/remotes/origin/batch/<x> it lists to origin/batch/<x> and, to tell whether that short name is ambiguous, opens
    the names git's rules try for it before refs/remotes/ (<common dir>/origin/batch/<x>, refs/origin/batch/<x>,
    refs/tags/origin/batch/<x> and refs/heads/origin/batch/<x>), with core.warnAmbiguousRefs off as every call here
    runs (git 2.43.0, 2026-10-04): a symlink to /dev/zero at any of them stops that call at GIT_MEMORY, and its
    GitMemory names those under refs/ (_odd_files' walk) and not <common dir>/origin/batch/<x> (its witness:
    tests/test_batch_tool.py, test_the_listing_of_the_remote_batch_branches_opens_the_names_of_each_ones_short_name).
    Not bounded: bisect's
    test command, which it
    runs at the tip, at the base and at each step; and gh, with anything it starts: _run holds all of what gh prints,
    with no time, memory or output limit, which this PR leaves out of scope (the 16:04Z ruling on PR 959) since what gh
    prints is GitHub's answer rather than a file a leg can grow, and gh's own git, which reads the clone's config and
    remotes, has none of these limits either. SIGTERM, SIGHUP
    and SIGINT (Ctrl-C) stop the tool (but a SIGHUP or SIGINT the tool was started with ignored, as by nohup or as a
    shell's background job, stays ignored): any process it is waiting on is ended with its process group (a git, a
    run_tool process, gh or bisect's command, each started in a session of its own, so what it started goes too), each
    step of the cleanup runs to its end (_cleanup_steps), the cleanup runs for a stop during any step it undoes
    (bisect's checkout of the base, its detach of HEAD at the tip, its git bisect start and its checkout of each commit
    it tests included), and it exits 128 plus the signal's number
    (Stopped);
  - the body stays under GitHub's 65,536-character cap, the members table never cut and the
    details fitted to the budget (entries table, then resolutions, then the log).
"""
import argparse
import datetime as _dt
import errno
import hashlib
import importlib.util
import json
import os
import re
import resource
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

BODY_CAP = 65_536          # GitHub's PR body limit, in characters
RESOLUTION_LINES = 300     # per conflicted merge, in the "Conflict resolutions" details block
PR_LIST_LIMIT = 200
CI_WORKFLOW = "ci.yml"     # the workflow whose run of the push to the batch branch land requires green,
CI_WORKFLOW_NAME = "CI"    # and its `name:`, which gh reports as a run's workflowName
# The fields land reads of each run gh lists (attempt: the run's latest attempt, whose earlier ones land reads too).
CI_RUN_FIELDS = "databaseId,status,conclusion,headSha,headBranch,event,workflowName,url,createdAt,attempt"
MAIN = "main"
# What the merge-commit remedies say of `scripts/sweep.py run --python <python>` (round 2, extra9-8): the same text as
# scripts/sweep.py's PYTHON_REMEDY, which the reader's missing line prints (tests/test_batch_tool.py holds the two equal).
PYTHON_REMEDY = ("<python>: a Python of the version CI's served step runs, or pass --served-python one as well; "
                 "docs/batching.md, batcher step 3")
REMOTE = "origin"
# origin/main by its full name (round 1 of PR 959, V1), as every git call that needs only its commit names it: a short
# name is tried by git's rev-parse rules as <git dir>/<name>, refs/<name>, refs/tags/<name> and refs/heads/<name> before
# refs/remotes/<name>, and a symlink to /dev/zero at any of those, whatever core.warnAmbiguousRefs says, is read whole.
MAIN_REF = "refs/remotes/%s/%s" % (REMOTE, MAIN)
LABEL_MAJOR = "major-feature"
LABEL_HOLD = "hold"
LABEL_LAND = "land"
LABEL_BATCH = "batch"
NOT_ONLY = "not named by plan --only"
# `docs` is upstream's name for tier 0 (renamed from tests-only on 2026-09-08; upstream's
# scripts/ci/tier_policy.py still reads tests-only as an alias), so a PR labeled either way is tier 0.
# The fork's .github/workflows/pr-tier.yml counts the same labels (plus LABEL_BATCH).
TIERS = ("fix", "tests-only", "docs", "feature", LABEL_MAJOR)
# Paths that put a member under "Read these first" when it touches them.
SENSITIVE_PREFIXES = ("kernel/", ".github/", ".githooks/")
SENSITIVE_FILES = ("install.sh", "uninstall.sh")
LEDGER_SCRIPT = os.path.join("scripts", "upstream-ledger.py")
UPSTREAM_MD = "UPSTREAM.md"

# `Depends-on:` is read from the body's first lines only (docs/batching.md asks for it there), outside
# fenced code blocks, one line per dependency or a `#N, #M` list on one line.
DEPENDS_ON_LINES = 20
_DEPENDS_ON = re.compile(r"^\s*Depends-on:\s*(.*)$", re.IGNORECASE)
_FENCE = re.compile(r"^\s*(```|~~~)")
_PR_TRAILER = re.compile(r"<!--\s*romp-pr:\s*(\{.*?\})\s*-->", re.DOTALL)
_BATCH_TRAILER = re.compile(r"<!--\s*romp-batch:\s*(\{.*?\})\s*-->", re.DOTALL)
# git 2.43.0 writes "is the first bad commit"; 2.55.0, CI's runner's in run 36934414430, "is the first 'bad' commit"
_FIRST_BAD = re.compile(r"^([0-9a-f]{40}) is the first '?bad'? commit", re.MULTILINE)
# A conflict marker line in a file's content. `=======` alone is not one: a Markdown heading underline
# is a legitimate line of exactly that; the `<<<<<<<`, `|||||||` and `>>>>>>>` lines are not.
_CONFLICT_MARKER = re.compile(r"^(?:<{7}|>{7}|\|{7})(?: |$)", re.MULTILINE)


class Fail(Exception):
    """A refusal with a message for the batcher; exit status 1 (2 for usage and mutex refusals)."""

    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


# ── process helpers ──────────────────────────────────────────────────────────

def _run(cmd, cwd=None, check=True, env=None, input_text=None):
    """A process that is not git, run without a bound (gh, which reads the clone's remotes with a git of its own), its
    output read whole, with no memory or output limit either (out of scope: the module docstring's "Not bounded"); every
    git call goes through run_git, and the two processes this tool starts that run git in the clone,
    scripts/pr-orphans.sh and the ledger script, through run_tool. It starts under the stop hold, as run_git's git does
    (the closing check wf_fb19febe-36b, its item 4), and in a session of its own, as run_tool's process does, so any
    exception while it runs ends it with its process group, gh's git included (_held_wait)."""
    _hold_stops()
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, text=True, start_new_session=True,
                             stdin=None if input_text is None else subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except BaseException:
        _release_stops()
        raise
    out, err = _held_wait(p, input_text)
    proc = subprocess.CompletedProcess(cmd, p.returncode, out, err)
    if check and proc.returncode != 0:
        raise Fail("%s failed (%d):\n%s%s" % (" ".join(cmd), proc.returncode, proc.stdout, proc.stderr))
    return proc


def run_command(cmd, cwd):
    """The exit status of `cmd` run in `cwd`, bisect's command: with this tool's stdin, stdout and stderr, and without a
    bound, since a test command can rightly take longer than any git call. It starts under the stop hold, as _run's
    process does (the closing check wf_fb19febe-36b, its item 4), and in a session of its own, so any exception while it
    runs ends it with its process group, what it started included (_held_wait). A session, not only a group: a group of
    its own in this tool's session would be a background job of the terminal there, stopped (SIGTTIN) at its first read
    of it. In a session of its own the terminal is not its controlling terminal: it reads and writes the descriptors it
    inherits without job control, a prompt it opens /dev/tty for fails (run_git's git has no terminal either), and a
    Ctrl-C at the terminal reaches this tool, whose stop then ends the command's group."""
    _hold_stops()
    try:
        p = subprocess.Popen(cmd, cwd=cwd, start_new_session=True)
    except BaseException:
        _release_stops()
        raise
    _held_wait(p)
    return p.returncode


def _held_wait(p, input_text=None):
    """(stdout, stderr) of `p`, a process _run or run_command started in a session of its own, once it ends. Any
    exception while it waits ends it with its process group first (_end_group: SIGTERM to the group, SIGKILL to what is
    left of it GIT_TERM_GRACE seconds later, `p` reaped and its pipes closed unread; its stdin, when it has one, is
    closed too), then propagates: a stop held while `p` started among them, which _release_stops raises here, inside the
    try, and a stop (Ctrl-C among them) that arrives while it runs. The group goes, as run_tool's does, so what `p`
    started goes with it: when `p` was started in this tool's own group and killed alone, as subprocess.run kills its
    child, gh's git or a child of bisect's command waiting on a FIFO ran on after the stop (the focused re-check
    wf_e3f48b16-6ec; the 13:24Z ruling of 2026-10-02 on PR 926, its item 2)."""
    try:
        _release_stops()
        return p.communicate(input_text)
    except BaseException:
        try:
            _end_group(p)
        finally:
            if p.stdin is not None:
                try:
                    p.stdin.close()
                except OSError:
                    pass
        raise


# The 02:43Z ruling, item 1(a): every git process this tool starts has a bounded wait, GIT_BOUND seconds, and starts
# through run_git, the one helper that starts one. A git that has not ended by then is killed with its process group
# (each starts in a session of its own, so it has no terminal to prompt on: a credential prompt fails at once instead of
# waiting; the group gets SIGTERM first, so git removes its own lock files, and SIGKILL GIT_TERM_GRACE seconds later if
# anything of it is left: _end_group) and the call raises GitBound, a Fail naming the call, so plan, assemble, verify, land and finish refuse there
# rather than hang on a file a leg left in the batcher's repository (a FIFO at its config, HEAD, index, info/exclude,
# shallow file or objects/info/alternates), except finish's read of the landed head's CI run, which reports any Fail
# there, GitBound included, as unread after the merge, and carries on.
# The bound is far above the slowest call measured on this project's clone on 2026-10-01: a member's merge in the batch
# worktree 0.74 s, a detached worktree add (the ledger check's) 0.58 s, ls-remote of origin 0.39 to 0.49 s, a fetch with
# nothing new 0.22 s, merge-tree of a batch chain's merges at most 0.12 s, every other read 0.02 s or less. It is larger
# than scripts/sweep.py's GIT_BOUND, whose calls are all local, because this tool's include a push through the clone's
# pre-push hook, which scans the pushed commits, and a fetch that brings new commits: on 2026-10-04 a fetch of 70 days
# of history took 56 to 59 s with GIT_SETTINGS, and a push of that history, with no hook, 13 to 14 s (GIT_SETTINGS'
# comment); the hook's scan is not measured here.
# tests/test_git_call_census.py holds every place this file starts a process to a named allowlist, run_git first.
GIT_BOUND = 600
# The 02:43Z ruling, item 1(b): the variables that tell git where a repository is (git's own list of the repository's
# local variables, less the configuration and replace-ref ones, plus the discovery ones). Each git call drops the inherited ones and
# names the repository it means: GIT_DIR, GIT_COMMON_DIR and GIT_WORK_TREE explicit, GIT_CEILING_DIRECTORIES above it.
GIT_LOCATION_ENV = ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_IMPLICIT_WORK_TREE", "GIT_INDEX_FILE",
                    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX", "GIT_SHALLOW_FILE",
                    "GIT_GRAFT_FILE", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM")


class GitBound(Fail):
    """A git call that did not end within GIT_BOUND seconds, killed with its process group: a refusal naming the call.
    GitMemory and GitOutput, the calls that met the memory and output limits, are GitBounds too, so every place that
    handles one handles them the same way."""


class GitMemory(GitBound):
    """A git call, or a process run_tool started, that failed when an allocation reached the memory limit set on it
    (git_memory): a refusal naming the call, the limit, git's line and the files of the repository git reads whole that
    are not regular files or are oversized when it is raised (_odd_files)."""


class GitOutput(GitBound):
    """A git call, or a process run_tool started, that printed more than GIT_OUTPUT_MAX bytes on its stdout or its stderr,
    killed with its process group: a refusal naming the call, the stream and the limit."""


# What run_git puts before every git call's own arguments: core.warnAmbiguousRefs off, over the clone's own config too.
# With it on (git's default), a git given a name, or a full object id such as a batch head or a member's head, also
# opens each other name git's rev-parse rules give it (<git dir>/<name>, refs/<name>, refs/tags/<name>,
# refs/heads/<name>, refs/remotes/<name> and refs/remotes/<name>/HEAD) to warn that the name is ambiguous, and reads
# what it finds there whole: a symlink to /dev/zero at refs/tags/<head>, which a sweep's leg can leave in the clone
# through its checkout's alternates, made verify's git rev-list --parents -n 1 <head> read without end (round 1 of PR
# 959's spot-check, S4, git 2.43.0, 2026-10-03), and this tool's git had no memory limit then (GIT_SETTINGS' comment), so
# only GIT_BOUND's 600 s or the machine's memory ended it. No call here reads that warning: git prints it on stderr and resolves the name as it
# does with the setting off, by the first rule that finds one. The setting also decides how strictly for-each-ref's
# refname:short shortens a name, which this tool reads for the remote batch branches: it gave the same names with the
# setting on and off, with a branch, a tag or a packed refs/remotes/<name>/HEAD of the same short name present
# (measured the same day); with it off, that shortening still opens each name the rules try for the short name before
# refs/remotes/ (the module docstring names the files and their witness). The setting does not reach every call that
# names a commit by its id: git checkout <sha>, which bisect makes of the base and of each commit it tests, git bisect
# start, and each git bisect good, bad or skip, which looks up the ids of the commits the bisect has marked, look the
# id up as a ref name first under every rule (<git dir>/<sha>, refs/<sha>, refs/tags/<sha>, refs/heads/<sha>,
# refs/remotes/<sha> and refs/remotes/<sha>/HEAD), whatever the setting, and read a symlink to /dev/zero at any of them
# (round 1 of PR 959, V5, git 2.43.0, 2026-10-03; the steps traced on 2026-10-04). git bisect also looks up by every
# rule, whatever the setting, the names it resolves itself: git bisect start, run from HEAD detached at the tip, HEAD
# (refs/HEAD, refs/tags/HEAD, refs/heads/HEAD, refs/remotes/HEAD and refs/remotes/HEAD/HEAD), and each step, given no
# commit, BISECT_HEAD (refs/BISECT_HEAD, refs/tags/BISECT_HEAD and the rest), and a symlink to /dev/zero at any of them
# stops that call at GIT_MEMORY too (traced on 2026-10-04). bisect runs them after your command has run in the batch
# worktree, whose refs are the clone's, and each runs under GIT_MEMORY, so such a read stops bisect there, naming the
# call (GIT_SETTINGS' comment). bisect's cleanups make none of them, but for the git bisect reset after a stop that
# ended git bisect start after it wrote BISECT_START and before BISECT_HEAD, which checks the tip out by its id
# (cmd_bisect's comment). git merge <sha> makes them too when merge.log is set (in the clone's config or the user's, or
# --log in a branch's mergeOptions), to describe the commit in the shortlog it appends, so assemble's merge of a member
# and merge_main's merge pass --no-log and make none (merge_member's comment; round 2 of PR 959, ruling D, fresh-3).
QUIET_NAMES = ("-c", "core.warnAmbiguousRefs=false")

# Round 1 of PR 959, V1 (the 13:21Z ruling: ruling A's class is every unbounded read of something a leg can reach): every
# git run_git starts, and every process run_tool starts, has a memory limit beside GIT_BOUND's time limit, its address
# space (RLIMIT_AS) set by the shell that execs it, and an output limit, scripts/sweep.py's: that module's GIT_MEMORY (1
# GiB), git_memory_limit (the tool's own lower limit passed on instead, and none off Linux, where RLIMIT_AS is not
# enforced), _LIMITED (the shell; one that cannot set the limit starts nothing, LIMIT_FAILED), GIT_OUTPUT_MAX (64 MiB a
# stream, through its _git_streams' selector loop) and _out_of_memory_line (a failure is the limit's only when git died
# with one of git's own lines as its first), read from it once per process (git_limits), so the two scripts keep one
# figure and one reading of each. Before this, batch.py's git had GIT_BOUND alone, and a symlink to /dev/zero a leg left
# at refs/tags/origin/main (a name git tries for origin/main before refs/remotes/origin/main) or at
# refs/remotes/origin/main made its rev-parse, rev-list and fetch read until the machine's memory ran out, at 1.3 to 1.7
# GiB/s (each reached a 3 GiB cap in 1.7 to 2.3 s, the round's evidence). The figures, measured on 2026-10-03 with git
# 2.43.0 on a scratch clone of this project (its objects through alternates: 8 packs, the largest 289 MiB), by bisecting
# to 4 MiB the smallest limit at which each
# call class succeeds: with GIT_SETTINGS, a whole-tree worktree add needed 255 MiB, a member's merge 91 MiB, merge-tree
# and diff-tree 87 MiB, merge-base and rev-list 55 MiB, ls-remote 19 MiB, rev-parse and for-each-ref 11 MiB; without
# them the same calls needed 419, 363, 315, 311, 19 and 11 MiB, since a call that reads an object maps a little more
# than the largest pack it touches (a fetch's figures follow). GIT_SETTINGS are the keys of scripts/sweep.py's
# GIT_NEUTRAL_CONFIG that keep the need flat (its comment has the mechanism), the pack window caps, and
# core.preloadIndex and index.threads off, since each thread git starts for the index reserves a stack and a malloc
# arena, so a checkout's need would vary with the threads it starts; and three keys of batch.py's own, which
# GIT_NEUTRAL_CONFIG does not hold: pack.threads=1, gc.auto=0 and maintenance.auto=false. The sweep needs none of the
# three: none of its git calls fetches, pushes or runs gc (its private clones are made with git init and an alternates
# file), so none runs index-pack or pack-objects (round 3 of PR 959, regression-1). pack.threads=1 (round 2 of PR 959,
# ruling A) holds to one thread index-pack, which a fetch of 100 objects or more runs (git's fetch.unpackLimit), and the
# pack-objects a push runs: git's own count for index-pack is one thread per two CPUs, at most 20 (from 40 CPUs), each
# with a stack, an arena and its own share of the delta base cache, so a fetch's need grew with the machine. A real
# batch's clone holds origin's branches and other refs (the upstream project's, say), and its git fetch --prune origin
# fetches every branch
# on origin, so its need was measured on scratch clones of this project made stale holding origin's branches and the
# clone's other refs as each stood at a cutoff, through this file's fetch, served by a git daemon on the same machine
# (2026-10-04, git 2.43.0, a 60-CPU machine, MALLOC_ARENA_MAX unset, since a shell that inherits it caps the arenas and
# hides that cost; each process's peak address space, its VmPeak,
# which RLIMIT_AS bounds, read from /proc every 2 ms), with the setting: three weeks stale (cutoff 2026-09-13, 85
# branches, 73,197 objects sent), index-pack mapped 460 to 478 MiB in the fetches that passed and the connectivity
# check's rev-list after it 251 MiB, and the whole fetch failed at 400 MiB and, twice, at 448 MiB, and passed twice at
# 480 MiB, twice at 496 MiB and at 512 MiB; six weeks stale (cutoff 2026-08-23, 97,210 objects sent), index-pack mapped
# only 196 MiB, and the rev-list, at 254 MiB, was the larger need. With the limit between the two needs (200, 205, 215,
# 230 and 240 MiB on that clone), the rev-list failed and git fetch exited 1, its first line git's malloc line, its
# inflateInit line or its packfile map line and "did not send all necessary objects" after it, which batch.py reads as a
# plain failure naming the call and quoting those lines, not as GitMemory, since git fetch did not die with the line
# (scripts/sweep.py's OUT_OF_MEMORY comment). So the need depends on the clone and what the fetch brings, not on its
# staleness or its count of objects alone, and a real fetch needs about half of GIT_MEMORY: about two times headroom,
# not the four to five times the figures below for clones holding main alone suggest. What sets the need is the refs
# the clone holds together with the window of history it fetches, not the refspec's breadth alone: on a clone made
# stale to the same three-week cutoff (1,626 refs: origin's 85 branches and a batch branch pushed after the first clone
# was built, each as it stood then, and the upstream refs older than it), a fetch whose refspec named main alone,
# with 45,119 objects to fetch against 55,563 for every branch, failed at 400 and 416 MiB and passed at 448 and 480 MiB,
# as the fetch of every branch failed at 400 MiB and passed
# at 448 and 480 MiB, while a clone holding main alone at that cutoff passed at 320 and 400 MiB fetching every branch
# (73,885 objects) and failed at 256 MiB (2026-10-04, git 2.43.0, MALLOC_ARENA_MAX unset). The refspec can still add
# to it: on a two-week clone holding every branch, the largest git process of a fetch of main alone peaked at 206 MiB
# and of every branch at 304 MiB (the same day). On clones holding main alone, made stale by two weeks (22,516
# objects to fetch) and by 70 days (90,415) and measured the same way, three fetches each: without the setting
# index-pack ran 21 threads and mapped 1542 MiB (two weeks) and 1594 to 1656 MiB (70 days), with it 203 MiB and 125 to
# 128 MiB, and the connectivity check's rev-list after it 198 to 199 MiB and 246 to 248 MiB either way; and the smallest
# limit at which the whole fetch passed, bisected to 4 MiB and checked by three fetches at it and three 8 MiB below, was
# 1424 MiB (two weeks; one of three passed at 1416) and 1500 MiB (70 days; two of three passed at 1492) without the
# setting, so such a fetch failed at GIT_MEMORY then, and 204 and 252 MiB with it (none of three passed 8 MiB below).
# The setting costs time: index-pack took 16 s in place of 11 (two weeks) and 52 to 55 s in place of 12 (70 days), the
# whole fetch 19 s in place of 14 and 56 to 59 s in place of 16, all far inside GIT_BOUND. A push of the same history
# (push_batch's call, to remotes as stale, main alone, with no hook, the same day) ran pack-objects on 61 threads,
# mapping 4569 to 4753 MiB, without the setting, and on one, mapping 274 MiB (two weeks) and 365 MiB (70
# days), with it, which took 1.6 s in place of 1.3 and 6.2 to 6.7 s in place of 5.0 to 5.4, the whole push 13.6 to 14.2
# s in place of 13.4 to 15.4 and 13.1 to 14.0 s in place of 11.8 to 12.6. Last of batch.py's own keys, gc.auto=0 and
# maintenance.auto=false, so no gc or maintenance git starts on its own after a fetch, a merge or a commit runs under
# the limit with a need nobody measured (a repack starts a thread per core) and, failing there, writes the gc.log that
# stops the clone's automatic gc
# until it is removed; your own git calls in the clone still run them. A call that runs the clone's hooks gets
# HOOK_MEMORY instead of GIT_MEMORY (HOOK_CALLS: git push, which runs pre-push; git commit, which runs pre-commit,
# prepare-commit-msg, commit-msg and post-commit; and git merge, which runs pre-merge-commit, prepare-commit-msg,
# commit-msg and post-merge; git merge --abort runs none of those, only post-index-change and reference-transaction, git
# 2.43.0, so it runs under GIT_MEMORY with no listing before it), since a hook can start gitleaks, which reserves its
# address space as it starts: this project's pre-push hook does, and a push through it needed 5323 MiB, with or without
# GIT_SETTINGS, and gitleaks 8.30.1 alone failed to start under a 4 GiB limit and started under 6 GiB (measured on
# 2026-10-03). A pre-commit hook a user sets for every clone (core.hooksPath in the global config) can start it too, and
# until round 2 of PR 959 (ruling C) only a push had the larger limit, so such a hook made assemble --continue's git
# commit fail under GIT_MEMORY, its failure read as a secret found in the staged resolution. HOOK_MEMORY is three times
# gitleaks' need; a gitleaks that reserves more fails to start, and the hook then refuses the call, saying gitleaks
# could not run. No call passes --no-verify, which would skip the user's own scans of what a commit holds. HOOK_MEMORY
# covers the whole call, not the hook alone: a push's own reads run under it, its listing of every loose ref and of
# packed-refs among them, so before each such call batch.py lists the refs under GIT_MEMORY (_refs_listed, ruling C's
# item 2), and a sparse or oversized file planted at a loose ref, or a sparse packed-refs, fails there, at GIT_MEMORY,
# with or without a fetch before it. The residual, stated: a file planted after that listing, or one the call reads and
# the listing does not (objects/info/alternates or the shallow file at a push, a state file in the git dir at a merge or
# a commit, GIT_DIR_STATE_FILES), fails at HOOK_MEMORY, not GIT_MEMORY; its witness is the pin that the listing
# refuses a planted loose ref at GIT_MEMORY on a --no-fetch path (tests/test_batch_tool.py,
# test_a_sparse_loose_ref_planted_before_a_no_fetch_push_path_is_refused_by_the_listing_at_git_memory). Not taken: a
# limit of GIT_MEMORY raised to HOOK_MEMORY for the hook alone by a core.hooksPath wrapper, which would stand in front
# of the clone's own hooks, the user's to change, and would skip their scans without a sound if it missed one. Every
# hook a call under GIT_MEMORY runs has that limit too, among them post-checkout, which git worktree add and git
# checkout run; post-index-change, which git checkout, git read-tree -u, git update-index --refresh, git status (when it
# writes the index) and git worktree add run; and reference-transaction, which git runs for a ref update through a
# transaction (update-ref, checkout -B, worktree add), where git symbolic-ref and checkout's move of HEAD onto a branch
# run none (git 2.43.0, traced on 2026-10-04). git-lfs 3.4.1, which a clone that uses it runs from post-checkout,
# started under a 768 MiB limit and failed under 640 MiB, out of memory, and under 512 MiB, unable to reserve its Go
# runtime's page summary, the same with MALLOC_ARENA_MAX unset and with it at 2 (measured on 2026-10-04). run_tool's
# processes get GIT_MEMORY, and the gits they start GIT_SETTINGS through the environment (round 2 of PR 959, ruling B;
# _tool_env, and run_tool's docstring for which gits the scripts run): the ledger script's check needed 35 MiB on Python
# 3.12 and 103 MiB on free-threaded 3.14 (2026-10-03). With them, pr-orphans.sh's fetch needs what this file's fetch
# needs: the same git fetch --quiet --prune origin, run through run_tool on the three-week clone above, failed at 400
# MiB and passed at GIT_MEMORY (2026-10-04, git 2.43.0, MALLOC_ARENA_MAX unset); and the import's git log -S over
# UPSTREAM.md's history, in a clone of main's whole history (its largest pack 208 MiB), passed at 188 MiB. Without them,
# on the clones holding main alone, pr-orphans.sh needed 1620 and 1544 MiB, more than GIT_MEMORY, so its fetch failed at
# the limit, which the script reports as a failed fetch before it checks what the clone has (index-pack mapped 1656 to
# 1684 MiB on 21 threads, and in one 70-day run the fetch's automatic maintenance started under the limit), and the git
# log -S needed 264 MiB (343 MiB on 2026-10-03 in a clone whose largest pack was 289 MiB, when the figure for
# pr-orphans.sh, 11 MiB, counted no fetch).
GIT_SETTINGS = ("-c", "core.packedGitWindowSize=32m", "-c", "core.packedGitLimit=128m", "-c", "core.preloadIndex=false",
                "-c", "index.threads=false", "-c", "pack.threads=1", "-c", "gc.auto=0", "-c", "maintenance.auto=false")
# The git subcommands that run the clone's hooks, and the address-space limit each gets in GIT_MEMORY's place
# (GIT_SETTINGS' comment): _runs_hooks reads the first word of a call against HOOK_CALLS, git merge --abort excepted,
# which runs none of a merge's hooks.
HOOK_CALLS = ("push", "commit", "merge")
HOOK_MEMORY = 16 << 30


# Round 3 of PR 959, correctness-1: the strategy batch.py's two merges name (MERGE_STRATEGY) and the -c pairs they run
# with after GIT_SETTINGS (merge_settings), so that git merge reads the merge options merge-tree reads. batch.py reads
# merge-tree --write-tree for the paths a merge conflicts on (merge_member and merge_main, through merge_tree_of), and
# verify reads it for the clean merge each merge is checked against; merge-tree runs ort with no -X option, its content
# merges with the histogram diff, and reads no branch's mergeOptions, no pull.twohead and no diff.algorithm. git merge
# reads all three: branch.<the branch HEAD is on>.mergeOptions, as options given before the command line's (an -s on the
# command line adds to the strategies mergeOptions names; it does not replace them), pull.twohead as its strategy when
# none is given, and, from git 2.47 on (its release notes), diff.algorithm for its content merges. With any of them git
# merge can resolve by itself a conflict merge-tree reports: with '-s recursive -Xours' in the batch branch's
# mergeOptions, or pull.twohead=recursive and no mergeOptions at all, git 2.43.0's merge-recursive merged a file
# merge-tree conflicted on and wrote a resolve-undo entry for it, which replayed_paths read as rerere's replay, so a
# merge the clone's pre-merge-commit hook refused was committed with git commit, which does not run that hook; and with
# diff.algorithm=myers, git 2.55.0's merge merged cleanly a file merge-tree conflicted on (measured on 2026-10-04). So
# the two merges empty the batch branch's mergeOptions, name -s ort, the one strategy once mergeOptions is empty, and
# set diff.algorithm to histogram, ort's own: a conflict merge-tree reports is then one git merge leaves, unless rerere
# replays it. The pairs go into run_git's launch after GIT_SETTINGS (its `settings`), not into the call's args, so
# _runs_hooks still reads merge as the call's first word and the merge keeps HOOK_MEMORY and the listing before it; git
# reads the command line's pairs after every other config, the environment's included. The residual, stated: git reads
# the mergeOptions of the branch HEAD is on, and both merges run in the batch worktree, which prepare_worktree puts on
# the batch branch; a batch worktree left on another branch, or detached (git then reads branch.HEAD.mergeOptions),
# merges with that name's options. -s ort needs git 2.33 (batch.py's reads of merge-tree --write-tree need 2.38).
MERGE_STRATEGY = ("-s", "ort")


def merge_settings(name):
    """The -c pairs batch/<name>'s two merges run with after GIT_SETTINGS (MERGE_STRATEGY's comment): the branch's
    mergeOptions emptied and diff.algorithm set to histogram."""
    return ("-c", "branch.%s.mergeOptions=" % branch_of(name), "-c", "diff.algorithm=histogram")


def refuse_equals_in_name(name, planned=False):
    """Refuse a batch name holding '=' (exit 2). The batch's two merges pass `-c branch.batch/<name>.mergeOptions=`
    (merge_settings), and git splits a -c pair at its first '=', so a name holding one could be planned and then not
    merged (the closing check at round 3 of PR 959, cc959-r3-n1). pick_name never makes such a name, so plan calls this
    on a passed --name only, before its fetch (chk-r3e-2), and assemble (pull through it) calls it right after it loads
    a state and before any write, since a state with such a name can still be on disk from a plan that did not refuse
    it; without that, git refused the key with its own "invalid key" after the batch branch and worktree were made (the
    check of that closing check's fix, chk-r3c-1). The message names its caller (chk-r3e-3): plan's --name, or, with
    `planned`, the batch assemble loaded, whose remedy is to plan it again, since assemble and pull take the name as an
    argument and have no --name. A batch that an older batch.py stopped mid-resolution under such a name is finished
    or dropped by hand, since the refusal comes before assemble's --continue and --abort."""
    if "=" in name:
        raise Fail("%s %s holds '=', which a batch name cannot: the batch's merges pass git -c %s.mergeOptions=, "
                   "and git splits a -c pair at its first '=', so it would read the key %s and refuse it; %s"
                   % ("the batch" if planned else "--name", name, "branch." + branch_of(name),
                      "branch." + branch_of(name).split("=")[0],
                      "plan it again under a name without '='" if planned
                      else "pass a name without '=', or no --name for today's date and a letter"), code=2)


# The signals that stop the tool (the closing check wf_3b100f5e-b38, its item 4): each raises Stopped, a BaseException
# as scripts/sweep.py's Stopped is, so the except path of run_git, run_tool, _run and run_command ends the process it
# started, which runs in a session of its own that no signal sent to batch.py or to its terminal's process group
# reaches, with that process's group (_bounded_wait, _held_wait; _run and run_command started gh and bisect's command in
# batch.py's own group and killed that process alone until the 13:24Z ruling of 2026-10-02 on PR 926, its item 2), and
# every finally block runs (the ledger check's temporary worktree is removed); main prints the signal and exits 128 plus
# its number. SIGINT is one of them (the 05:30Z ruling of 2026-10-02 on PR 926, its item 3), as in scripts/sweep.py, so
# Ctrl-C runs the same cleanup as SIGTERM and SIGHUP.
# Before, a Ctrl-C raised Python's KeyboardInterrupt, which _cleanup_steps did not catch, so one that landed inside a
# cleanup step ended the cleanup there. A SIGHUP or SIGINT that batch.py was started with ignored (IGNORE_INHERITED:
# nohup ignores SIGHUP, a non-interactive shell starts a background job with SIGINT ignored) stays ignored, as in
# scripts/sweep.py, since its caller chose not to have the command stopped by it.
# Every process the tool starts is started under the stop hold (the closing check wf_fb19febe-36b, its item 4; the
# census in tests/test_git_call_census.py holds every launch site to it): a stop that arrives while run_git, run_tool,
# _run or run_command starts its process is held until that process is started and the call is inside the try that ends
# it (_hold_stops, _release_stops), and raised there: raised as it arrived, between the start and that try, it ended the
# tool with the process running on, never ended (the verify pass at the wf_3b100f5e-b38 build, its code finding 2: 9 of
# 60 SIGTERMs sent in the first 6 ms of a run_git, at 217 to 579 microseconds, left the git running after batch.py
# exited 143; the closing check wf_fb19febe-36b found the same of gh and bisect's command, which subprocess.run
# started). The git of the excuse rule, which scripts/sweep.py's run_git starts in this process, is held the same way:
# sweep_reader binds that module's hold to this one.
STOP_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
# The stop signals batch.py leaves ignored when its caller started it with them ignored; SIGTERM always stops it.
IGNORE_INHERITED = (signal.SIGHUP, signal.SIGINT)
# Whether a process start is in progress (_hold_stops), and the first stop signal that arrived meanwhile, or None.
_holding = False
_held = None


class Stopped(BaseException):
    """A stop signal (STOP_SIGNALS) reached the tool: any process it was waiting on is killed and its cleanup runs on the
    way out, each step of it to its end (_cleanup_steps)."""

    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum
        # Set when the cleanup the stop ran did not finish (round 3 of PR 959, correctness-2: bisect's cleanups): what
        # failed and the state it left, which main prints in place of its line saying the cleanup ran.
        self.cleanup_failed = None


def _on_stop(signum, _frame):
    # the first stop signal wins: one that arrives during the cleanup it started is ignored, so the cleanup runs to its end
    for s in STOP_SIGNALS:
        signal.signal(s, signal.SIG_IGN)
    _stop(signum)


def _stop(signum):
    """Raise Stopped for `signum`, or, while a process is being started (_hold_stops), hold it for _release_stops; a later
    one held meanwhile is dropped, the first wins."""
    global _held
    if _holding:
        if _held is None:
            _held = signum
        return
    raise Stopped(signum)


def _hold_stops():
    """Hold every stop signal from here until _release_stops: called just before each process this tool starts
    (run_git's git, run_tool's script, _run's gh, run_command's bisect command; tests/test_git_call_census.py's
    unheld_launches finds a start without it), and before the git of scripts/sweep.py's run_git in this process, whose
    hold sweep_reader binds to this one."""
    global _holding
    _holding = True


def _release_stops():
    """End the hold, and raise the stop held during it, if one was: called inside the try that ends the process once it is
    started, so that process is ended as on any other stop (or, when the start failed, on the way out of it)."""
    global _holding, _held
    _holding = False
    held, _held = _held, None
    if held is not None:
        raise Stopped(held)


def _cleanup_steps(*steps):
    """Run each cleanup step (a function of no arguments) to its end, in order, then raise the stop that arrived during
    them, if one did. A stop (SIGTERM, SIGHUP or SIGINT) that lands inside a step (as the step's git starts, say, which
    the stop then ends with its group) raises Stopped there; the step runs again from its start, now with the stop
    signals ignored (_on_stop ignores every one after the first), and so do the steps after it. Before this, such a
    stop ended the cleanup there: bisect left the batch worktree detached at the base or mid-bisect, and the ledger
    check left its temporary worktree registered, while main said the cleanup ran (the verify pass at the closing check
    wf_fb19febe-36b's build, its code finding 4). scripts/sweep.py's _finish runs its cleanup the same way."""
    stopped = []
    for step in steps:
        try:
            step()
        except Stopped as e:
            stopped.append(e)
            step()
    if stopped:
        raise stopped[0]


def install_stop_handlers(replaced):
    """Give SIGCHLD its default action, and make STOP_SIGNALS raise Stopped, leaving a SIGHUP or SIGINT the process was
    started with ignored (IGNORE_INHERITED) as it is; each handler it replaces is recorded in `replaced` ({signal:
    handler}) before it is replaced, and main puts them back when the command ends. An ignored SIGCHLD survives exec,
    and under it the kernel reaps each child as it exits, so a wait finds no exit status to read and subprocess reports
    0 whatever the process returned: started so, batch.py read every failing git, script, gh or bisect command as one
    that passed (the focused re-check wf_e3f48b16-6ec: verify read its git cat-file -e of the ledger script as finding
    it, and the failed git worktree add that followed as done; the 13:24Z ruling of 2026-10-02 on PR 926, its item 3).
    scripts/sweep.py's main sets the same default (install_stop_signals)."""
    replaced[signal.SIGCHLD] = signal.getsignal(signal.SIGCHLD)
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    for s in STOP_SIGNALS:
        current = signal.getsignal(s)
        if s in IGNORE_INHERITED and current == signal.SIG_IGN:
            continue
        replaced[s] = current
        signal.signal(s, _on_stop)


class GitRepo:
    """The repository a git call means, named explicitly (the 02:43Z ruling, item 1(b)): its work tree, git dir and common
    dir, each absolute, and the ceiling above it. A .git git does not recognize (refs/ removed, objects/ a file, HEAD
    removed, .git removed) then fails the call as "not a git repository" instead of sending git up to an enclosing
    repository. The ceiling alone stops that walk at the work tree, for a call made there; the explicit names, beside it,
    keep each call on the repository find_repo found: git reads no .git file again (so one rewritten after repo_root's
    discovery, in a clone that is a linked worktree, does not move a call to another repository: BatchGitBound's
    git-file pin, red when the three are dropped), and a core.worktree in the repository's config moves no call's work
    tree (one present at the discovery, naming another directory than the one holding .git, is refused by find_repo, so
    the work tree named is that directory). They do not keep every read off a commondir file: git 2.43 reads the git
    dir's commondir file when a call reads a ref, whatever GIT_COMMON_DIR says (measured on 2026-10-01), so in a linked
    worktree's git dir that file is read by such a call, and a FIFO there ends it at GIT_BOUND, naming it. git_dir None
    is the discovery call (find_repo), which sets only the ceiling."""

    def __init__(self, work_tree, git_dir, common_dir, ceiling):
        self.work_tree, self.git_dir, self.common_dir, self.ceiling = work_tree, git_dir, common_dir, ceiling


# The repositories repo_root found, by the real path it returned: the batcher's clone, read once per process.
_REPOS = {}


def _git_env(repo, extra=None):
    env = {k: v for k, v in os.environ.items() if k not in GIT_LOCATION_ENV}
    env.update(extra or {})
    env["GIT_CEILING_DIRECTORIES"] = repo.ceiling
    if repo.git_dir is not None:
        env.update(GIT_DIR=repo.git_dir, GIT_COMMON_DIR=repo.common_dir, GIT_WORK_TREE=repo.work_tree)
    return env


def _tool_env(repo):
    """The environment run_tool starts its process in: _git_env's, with GIT_SETTINGS added as git's environment config
    (round 2 of PR 959, ruling B), each setting a GIT_CONFIG_KEY_<n> and GIT_CONFIG_VALUE_<n> pair numbered after the
    GIT_CONFIG_COUNT pairs batch.py inherited, which stay as they were, and GIT_CONFIG_COUNT raised to cover both, so
    every git the process starts reads the inherited pairs and then these, a later pair winning for the same key (git
    2.31 and later read these variables, as scripts/sweep.py's GIT_NEUTRAL_CONFIG does). git reads an empty
    GIT_CONFIG_COUNT as none, and refuses one that is not a number ("bogus count"), as every git batch.py starts would:
    that is a Fail naming it, and nothing is started."""
    env = _git_env(repo)
    inherited = env.get("GIT_CONFIG_COUNT", "")
    m = re.fullmatch(r"\s*\+?([0-9]+)", inherited)
    if inherited and m is None:
        raise Fail("GIT_CONFIG_COUNT in batch.py's environment is %r, which git refuses as a count, so batch.py cannot add "
                   "its git settings after the pairs it counts; unset it or set it to the number of "
                   "GIT_CONFIG_KEY_<n> pairs, and run the command again" % inherited)
    n = int(m.group(1)) if m else 0
    pairs = [GIT_SETTINGS[i + 1].split("=", 1) for i in range(0, len(GIT_SETTINGS), 2)]
    for i, (key, value) in enumerate(pairs, n):
        env["GIT_CONFIG_KEY_%d" % i], env["GIT_CONFIG_VALUE_%d" % i] = key, value
    env["GIT_CONFIG_COUNT"] = str(n + len(pairs))
    return env


def run_git(args, cwd, repo=None, env=None, text=True, settings=()):
    """`git <args>` in `cwd`, in the repository `repo` names (default: repo_for(cwd)), as a CompletedProcess: the one way
    this tool starts git. stdin is closed, `env` is added to the environment, and the process starts in a session of its
    own and has GIT_BOUND seconds to end; one that has not is killed with its process group and reaped, and GitBound is
    raised naming the call. Any other exception while it runs (Stopped, which SIGTERM, SIGHUP and SIGINT raise, among
    them) kills it the same way first. Every call runs with core.warnAmbiguousRefs off (QUIET_NAMES) and GIT_SETTINGS,
    under the memory limit git_memory gives it, set by the shell that execs it, and its output is read through
    _bounded_wait's limit: one that died at the memory limit with one of git's own out-of-memory lines first raises
    GitMemory, one that prints too much GitOutput, and one whose shell could not set the limit, which starts no git, a
    Fail naming LIMIT_FAILED (_limit_met). Other failures at the memory limit are returned as any failure is (git()
    raises one as a Fail naming the call and quoting git), and batch.py's fetch meets two: a connectivity check's
    rev-list that fails at the limit, after which git fetch exits 1 (GIT_SETTINGS' comment), and a thread git cannot
    start there (exit 128, "error: cannot create async thread: Resource temporarily unavailable", the words a limit on
    processes gives too). scripts/sweep.py's OUT_OF_MEMORY comment lists the others that are known. A call that runs
    the clone's hooks, under HOOK_MEMORY, comes after a listing of the refs under GIT_MEMORY (_refs_listed). `settings`
    are -c pairs of the caller's own, which follow GIT_SETTINGS in the launch and come before `args`, so _runs_hooks and
    git_memory still read the subcommand as the first word of `args` (MERGE_STRATEGY's comment)."""
    repo = repo or repo_for(cwd)
    argv = ["git", *args]
    limit = git_memory(args)
    if limit is not None and _runs_hooks(args):
        _refs_listed(args, cwd, repo)
    launch = ["git", *QUIET_NAMES, *GIT_SETTINGS, *settings, *args]
    if limit is not None:
        launch = ["/bin/sh", "-c", git_limits()._LIMITED % (limit >> 10), *launch]
    _hold_stops()
    try:
        p = subprocess.Popen(launch, cwd=cwd, env=_git_env(repo, env), text=text, start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except BaseException:
        _release_stops()
        raise
    what = "git " + " ".join(args)
    out, err = _bounded_wait(p, what, cwd, text)
    _limit_met(p.returncode, err if text else err.decode("utf-8", "replace"), what, cwd, limit, args, repo)
    return subprocess.CompletedProcess(argv, p.returncode, out, err)


def _refs_listed(args, cwd, repo):
    """Every ref of `repo` listed under GIT_MEMORY, with git for-each-ref --format= in `cwd`, before `git <args>`, a
    call that runs the clone's hooks under HOOK_MEMORY (round 2 of PR 959, ruling C, item 2). for-each-ref reads every
    loose ref whole, and packed-refs, as a push reads them to list the local refs, so a sparse or oversized file a leg
    planted at a loose ref, or a sparse packed-refs, meets GIT_MEMORY here, with or without a fetch before it
    (--no-fetch), and the GitMemory names it (_odd_files), where the call itself would read it until HOOK_MEMORY.
    --format= prints an empty line a ref, the least output for the same reads. A bound met here is raised as it was met,
    the call it came before named; the call does not run. Its residual, stated: a file planted after this listing, or
    one the call reads and the listing does not (objects/info/alternates or the shallow file at a push, a state file in
    the git dir at a merge or a commit, of GIT_DIR_STATE_FILES, say, or a loose ref by another road), fails at
    HOOK_MEMORY
    rather than GIT_MEMORY, as do the call's own reads and its hooks' (GIT_SETTINGS' comment; the pin that this listing
    refuses a planted loose ref at GIT_MEMORY on a --no-fetch path is tests/test_batch_tool.py,
    test_a_sparse_loose_ref_planted_before_a_no_fetch_push_path_is_refused_by_the_listing_at_git_memory)."""
    try:
        run_git(["for-each-ref", "--format="], cwd, repo=repo)
    except GitBound as e:
        raise type(e)("batch.py lists the refs under GIT_MEMORY before git %s, which runs the clone's hooks under "
                      "HOOK_MEMORY: %s" % (" ".join(args), e)) from None


def run_tool(cmd, cwd, repo=None):
    """`cmd` in `cwd`, a process that is not git but runs git in the clone (scripts/pr-orphans.sh, the ledger script),
    as a CompletedProcess, started as run_git starts git (the closing check wf_3b100f5e-b38, its item 5): the repository
    `repo` names (default: repo_for(cwd)) explicit in its environment, GIT_DIR, GIT_COMMON_DIR and GIT_WORK_TREE set and
    GIT_CEILING_DIRECTORIES above it, so every git it starts reads that repository and none walks up from its cwd; stdin
    closed; in a session of its own; and GIT_BOUND seconds to end, after which it is killed with its process group, the
    git it is waiting on included, and GitBound is raised naming it. Any other exception while it runs (Stopped among
    them) kills it the same way first. It has run_git's memory and output limits (GIT_MEMORY, every process it starts
    inheriting the address limit, and GIT_OUTPUT_MAX), with GitMemory, GitOutput and the LIMIT_FAILED Fail as run_git
    raises them. The gits it starts get GIT_SETTINGS too, through the environment (_tool_env; round 2 of PR 959, ruling
    B), so they run under GIT_MEMORY with the need run_git's calls have, not one that grows with the largest pack or the
    machine's CPUs, and start no gc or maintenance under that limit: scripts/pr-orphans.sh, unless ROMP_ORPHANS_NO_FETCH
    is set, runs git remote get-url origin and, when the clone has an origin, git fetch --quiet --prune origin, whose
    automatic maintenance was the one that could start a gc there, and then git rev-parse --verify of the main branch,
    the remote-tracking one first, and git merge-base --is-ancestor for each merged PR it reads; the ledger script's
    import runs git log -S over UPSTREAM.md's history to date a row, and its check runs no git. A git the script runs
    with its own -c, or under a GIT_CONFIG_PARAMETERS batch.py inherited, reads that value over these (git reads
    GIT_CONFIG_PARAMETERS after the counted pairs). GIT_SETTINGS' comment gives each one's measured need."""
    repo = repo or repo_for(cwd)
    limit = git_memory()
    launch = cmd if limit is None else ["/bin/sh", "-c", git_limits()._LIMITED % (limit >> 10), *cmd]
    env = _tool_env(repo)
    _hold_stops()
    try:
        p = subprocess.Popen(launch, cwd=cwd, env=env, text=True, start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except BaseException:
        _release_stops()
        raise
    what = " ".join(cmd)
    out, err = _bounded_wait(p, what, cwd, True)
    _limit_met(p.returncode, err, what, cwd, limit, None, repo)
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


# scripts/sweep.py as git_limits loaded it, once per process: the module whose limits run_git and run_tool set.
_LIMITS = None


def git_limits():
    """scripts/sweep.py, loaded once per process through sweep_reader, for the limits run_git and run_tool set and the
    reading of a failure at the memory limit (GIT_SETTINGS' comment names each): one copy of each for both scripts."""
    global _LIMITS
    if _LIMITS is None:
        _LIMITS = sweep_reader()
    return _LIMITS


def _runs_hooks(args):
    """Whether `git <args>` runs the clone's hooks: its first word is one of HOOK_CALLS (push, commit, merge), and it is
    not git merge --abort, which runs none of the hooks a merge runs (git 2.43.0 ran post-index-change and
    reference-transaction alone, as a checkout does), so it runs under GIT_MEMORY with no listing of the refs before it,
    and so do its own whole-file reads, MERGE_AUTOSTASH among them."""
    return bool(args) and args[0] in HOOK_CALLS and tuple(args[:2]) != ("merge", "--abort")


def git_memory(args=None):
    """The address-space limit in bytes run_git sets on `git <args>`, or run_tool on its process (`args` None), or None
    where none is set: scripts/sweep.py's git_memory_limit (GIT_MEMORY, or the tool's own soft or hard RLIMIT_AS where
    either is lower, since a child inherits it and the shell never raises it; None off Linux), but for a call that runs
    the clone's hooks (_runs_hooks: a push, a commit or a merge, but not git merge --abort) HOOK_MEMORY in GIT_MEMORY's
    place (GIT_SETTINGS' comment)."""
    limit, _why = git_limits().git_memory_limit()
    if limit is None or not _runs_hooks(args):
        return limit
    return min([HOOK_MEMORY] + [n for n in resource.getrlimit(resource.RLIMIT_AS) if n != resource.RLIM_INFINITY])


def _bounded_wait(p, what, cwd, text):
    """(stdout, stderr) of `p`, a process run_git or run_tool started in a session of its own, once it ends within
    GIT_BOUND seconds, each stream read through scripts/sweep.py's selector loop (_git_streams, decoded when `text`) up
    to GIT_OUTPUT_MAX bytes; one that has not ended is ended with its process group (_end_group), and GitBound is raised
    naming `what` and `cwd`, and one that printed more is ended the same way, and GitOutput is raised naming the stream.
    Any other exception while it waits ends it the same way first, then propagates: a stop held while `p` started among
    them, which _release_stops raises here, inside the try."""
    limits = git_limits()
    try:
        _release_stops()
        return limits._git_streams(p, None, time.monotonic() + GIT_BOUND, text)
    except BaseException as e:
        _end_group(p)
        if isinstance(e, subprocess.TimeoutExpired):
            raise GitBound("%s in %s did not end within %d s and was killed" % (what, cwd, GIT_BOUND)) from None
        if isinstance(e, limits._PastOutputLimit):
            raise GitOutput("%s in %s printed more than %s on its %s, the most batch.py reads of one call "
                            "(GIT_OUTPUT_MAX), and was killed; remove what made it print so much there and run the "
                            "command again" % (what, cwd, limits.memory_text(limits.GIT_OUTPUT_MAX), e.stream)) from None
        raise


# The state files in a worktree's git dir that a commit, a merge or a bisect reads whole (round 3 of PR 959, extra4-1;
# git 2.43.0, a symlink to /dev/zero at each stopping that call): COMMIT_EDITMSG, which git commit writes and reads
# back; MERGE_MSG, which git merge writes and reads back and git commit reads; MERGE_MODE and SQUASH_MSG, which git
# commit of a merge reads; MERGE_AUTOSTASH, which git merge --abort reads; and BISECT_START, which git bisect reset
# reads. A GitMemory names each of them, in the call's git dir, that is not a regular file or holds at least the call's
# limit (_odd_files), and its remedy lists them all (_limit_met). COMMIT_EDITMSG outlives prepare_worktree's git
# checkout -B, so one planted before an assembly is read by its commit of a rerere replay; MERGE_MODE and SQUASH_MSG are
# removed by that checkout (git 2.43.0 and 2.55.0) and are read only when planted after a stop, by assemble --continue's
# commit. MERGE_HEAD is
# not among them, since continue_after_resolution reads it under GIT_MEMORY, with git rev-parse, before its commit.
GIT_DIR_STATE_FILES = ("COMMIT_EDITMSG", "MERGE_MSG", "MERGE_MODE", "SQUASH_MSG", "MERGE_AUTOSTASH", "BISECT_START")


def _limit_met(returncode, said, what, cwd, limit, args, repo):
    """Raise for a process run_git or run_tool started under the memory `limit` (None: none set) whose shell could not
    set it (exit 125 after LIMIT_FAILED: a Fail, the process never started) or that failed at it (scripts/sweep.py's
    _out_of_memory_line over what it printed on stderr, `said`, with the index of `repo` for a git call: GitMemory
    naming the call, the limit and git's line, the directory of each prefix the call lists the refs under, as a
    directory, "the loose refs under <dir>/" (_ref_files), and the files of `repo` git reads whole that are not regular
    files or are oversized when it is raised, _odd_files); any other exit is the caller's to read. The remedy's list of
    places names the state files in the git dir that a commit, a merge or a bisect reads whole as well, each of
    GIT_DIR_STATE_FILES (its comment says which call reads which), the set _odd_files checks."""
    if limit is None or returncode == 0:
        return
    limits = git_limits()
    said = said.strip()
    if returncode == 125 and limits.LIMIT_FAILED in said:
        raise Fail("%s in %s did not run: %s, so batch.py did not start it without one (%s)"
                   % (what, cwd, limits.LIMIT_FAILED, said))
    index = os.path.join(repo.git_dir, "index") if args is not None and repo.git_dir is not None else None
    line = limits._out_of_memory_line(returncode, said, index)
    if line is None:
        return
    name = "HOOK_MEMORY" if _runs_hooks(args) else "GIT_MEMORY"
    listed = ([p for p in _ref_files(args or [], repo) if p.endswith(os.sep)]
              if repo is not None and repo.common_dir is not None else [])
    odd = _odd_files(args or [], repo, limit)
    if len(odd) > ODD_FILES_SHOWN:
        odd = odd[:ODD_FILES_SHOWN] + ["and %d more" % (len(odd) - ODD_FILES_SHOWN)]
    raise GitMemory("%s in %s reached the %s memory limit (%s) batch.py sets on it and failed (%s); remove what it read "
                    "without end there (a symlink to /dev/zero, an oversized file or a symbolic ref leading to one, where "
                    "git reads a ref, packed-refs, the index, a config file, objects/info/alternates or the shallow "
                    "file, or a state file in the git dir that a commit, a merge or a bisect reads whole, %s or "
                    "%s)%s%s, and run the command again"
                    % (what, cwd, limits.memory_text(limit), name, line, ", ".join(GIT_DIR_STATE_FILES[:-1]),
                       GIT_DIR_STATE_FILES[-1],
                       "; the call reads the loose refs under %s" % ", ".join(listed) if listed else "",
                       "; of the files of the repository git reads whole, these are not regular files or hold more than "
                       "a file of their kind does, now (an lstat each after the call, so one can have changed since): %s"
                       % ", ".join(odd) if odd else ""))


# The most files a GitMemory names (_odd_files); past it the text says how many more there are.
ODD_FILES_SHOWN = 20


def _odd_files(args, repo, limit):
    """The files a GitMemory names (round 2 of PR 959, ruling C, item 3): those of `repo` that git reads whole for a ref
    or an object and that, at an lstat each after the call (no symlink followed, as scripts/sweep.py's main_bound_text
    names those of MAIN_REF's files that are not regular), are not regular files, or hold more than a file of their kind
    does: every loose ref, walked under <common dir>/refs (and, in a linked worktree, under <git dir>/refs, which holds
    that worktree's own refs), and each file of a ref `git <args>` names (_ref_files, less the directories of the
    prefixes a call lists, which the walk covers and _limit_met names as directories), that is over scripts/sweep.py's
    REF_FILE_MAX bytes, the most a loose ref file holds; and <common dir>/packed-refs, objects/info/alternates and
    shallow when at least `limit` bytes, the limit the call ran under, since git reads or maps each whole and a real one
    can hold far more than a loose ref (a clone of this project held one of 168,265 bytes on 2026-10-04); and, the same
    way, each of GIT_DIR_STATE_FILES in the call's git dir, the state files a commit, a merge or a bisect reads whole
    (COMMIT_EDITMSG, MERGE_MSG, MERGE_MODE, SQUASH_MSG, MERGE_AUTOSTASH and BISECT_START: round 3 of PR 959, extra4-1,
    before which a GitMemory from git commit named none of them). Each is named with why: its type, by cannot_read's
    words, or its size; a directory at one of the files git reads whole is named as one (the closing check at round 3
    of PR 959, NEW-2), and one at a loose ref's path is passed over, since the walk reads what it holds. Not named: a
    file of the call's own that git reads by another road (the index, a config file), and a smaller oversized file that
    still took the call past the limit; the remedy's list of places covers them (_limit_met). Before ruling C a
    GitMemory named the batch branch's loose file for a push and MAIN_REF's for a fetch, whatever the call had read."""
    if repo is None or repo.common_dir is None:
        return []
    limits = git_limits()
    odd, seen = [], set()

    def note(path, st, whole):
        """Name `path`, lstat'ed as `st`, when it is not a regular file, or is larger than a loose ref file holds
        (`whole` False) or at least the call's limit (`whole` True)."""
        seen.add(path)
        if not stat.S_ISREG(st.st_mode):
            odd.append("%s (%s)" % (path, limits._not_regular(st.st_mode)))
        elif not whole and st.st_size > limits.REF_FILE_MAX:
            odd.append("%s (%d bytes, more than the %d a loose ref file holds)" % (path, st.st_size, limits.REF_FILE_MAX))
        elif whole and st.st_size >= limit:
            odd.append("%s (%d bytes, at least the %s limit the call ran under, and git reads it whole)"
                       % (path, st.st_size, limits.memory_text(limit)))

    roots = [os.path.join(repo.common_dir, "refs")]
    if repo.git_dir is not None and not same_dir(repo.git_dir, repo.common_dir):
        roots.append(os.path.join(repo.git_dir, "refs"))
    for root in roots:
        stack = [root]
        while stack:
            d = stack.pop()
            try:
                st = os.lstat(d)
                if not stat.S_ISDIR(st.st_mode):
                    note(d, st, False)
                    continue
                entries = sorted(os.scandir(d), key=lambda e: e.name)
            except FileNotFoundError:
                continue
            except OSError as e:
                odd.append("%s (it could not be read: %s)" % (d, e.strerror or e))
                continue
            dirs = []
            for e in entries:
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError as x:
                    odd.append("%s (its lstat failed: %s)" % (e.path, x.strerror or x))
                    continue
                if stat.S_ISDIR(st.st_mode):
                    dirs.append(e.path)
                else:
                    note(e.path, st, False)
            stack.extend(reversed(dirs))
    for path, whole in ([(p, False) for p in _ref_files(args, repo)]
                        + [(os.path.join(repo.common_dir, *f.split("/")), True)
                           for f in ("packed-refs", "objects/info/alternates", "shallow")]
                        + [(os.path.join(repo.git_dir, f), True)
                           for f in (GIT_DIR_STATE_FILES if repo.git_dir is not None else ())]):
        if path in seen or path.endswith(os.sep):
            continue
        try:
            st = os.lstat(path)
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError as e:
            odd.append("%s (its lstat failed: %s)" % (path, e.strerror or e))
            continue
        if whole or not stat.S_ISDIR(st.st_mode):
            note(path, st, whole)
    return odd


# The names git's rev-parse rules try for a short name, in order, up to refs/heads/<name> (ref_rev_parse_rules in git's
# refs.c, git 2.43.0): git worktree add -B <name> and git checkout -B <name> look the name up by them once they have set
# the branch, and open <common dir>/<name>, refs/<name> and refs/tags/<name> before they find refs/heads/<name>, from a
# linked worktree too (traced on 2026-10-04): the files _ref_files names for those calls.
SHORT_NAME_RULES = ("%s", "refs/%s", "refs/tags/%s", "refs/heads/%s")


def _ref_files(args, repo):
    """The loose files, under `repo`'s common dir, of origin/main and of the batch branches that `git <args>` names (a
    full ref, a short batch/<name>, or either in a range, a ^ exclusion or a <rev>:<path>), and of origin/main for a
    fetch from origin, which reads every refs/remotes/origin/ ref it updates: the files of the refs a call names, which
    a GitMemory names when they are not regular files or are oversized (_odd_files). A word that ends in "/" is not a
    ref but a prefix, under which for-each-ref lists the refs (pick_name's and other_remote_batches'
    refs/remotes/origin/batch/): it gives the directory, with its trailing separator, which _odd_files passes over (its
    walk of refs/ reads each loose ref in it) and the GitMemory names as a directory, "the loose refs under <dir>/"
    (_limit_met; round 2 of PR 959, ruling D, extra4-3: before it, the directory was named as if it were a ref's file).
    For git worktree add -B and git checkout -B (prepare_worktree), which look the branch's short name up by git's rules
    once they have set the branch, the files of every name those rules try for it up to refs/heads/<name>
    (SHORT_NAME_RULES), and for git checkout -B also the file of its start point as a local branch,
    refs/heads/<start point>, which checkout looks for first: the files git opens for those calls, each under the
    common dir, as a linked worktree's git opens them too (round 2 of PR 959, ruling D, fresh-2: before it, the
    GitMemory of such a call named the files of the batch branch's and origin/main's full refs, and, from ruling C on,
    the odd files its walk of refs/ found, but never <common dir>/batch/<name>, which is outside refs/)."""
    names = []
    for word in (w for a in args for w in re.split(r"\.\.\.?|[\^:]", a) if w):
        if word == MAIN_REF or word.startswith(("refs/heads/batch/", "refs/remotes/%s/batch/" % REMOTE)):
            names.append(word)
        elif word.startswith("batch/"):
            names.append("refs/heads/" + word)
    if args and args[0] in ("worktree", "checkout") and "-B" in args[:-1]:
        at = args.index("-B")
        names += [rule % args[at + 1] for rule in SHORT_NAME_RULES]
        if args[0] == "checkout" and at + 2 < len(args):
            names.append(SHORT_NAME_RULES[-1] % args[at + 2])
    if args and args[0] == "fetch" and REMOTE in args:
        names.append(MAIN_REF)
    seen = []
    for n in names:
        path = os.path.join(repo.common_dir, *n.split("/"))
        if path not in seen:
            seen.append(path)
    return seen


# How long a process run_git or run_tool ends (at the bound, or on a stop), or one _run or run_command ends (on a stop;
# neither has a bound), has after SIGTERM to its process group before what is left of the group gets SIGKILL. SIGTERM
# comes first because git's own handlers for it remove what the git had made and not finished: its lock files, and a
# worktree it was adding with that worktree's registration. A SIGKILL leaves them: the next git that wants the lock
# fails on it ("index.lock: File exists"; assemble's next run did, after its worktree add was killed at the bound), and
# a registration stays locked ("initializing"), which neither git worktree prune nor git worktree remove --force clears
# (the verify pass at the wf_3b100f5e-b38 build, its code finding 1). Measured on 2026-10-01 (git 2.43.0): a git
# worktree add waiting on a FIFO at info/exclude exited on SIGTERM with its registration and its half-made tree removed;
# under SIGKILL both stayed.
GIT_TERM_GRACE = 10


def _end_group(p):
    """End `p`, started in a session of its own, with its process group: SIGTERM to the group, then wait until the group
    is gone (`p` exited and reaped and no process left in its group), at most GIT_TERM_GRACE seconds, and SIGKILL what
    is left of it then; `p` is reaped and its pipes closed unread (a child still holding one would keep a read
    waiting). Any exception during the wait (a stop that arrives then, say) still gets the SIGKILL and the reap."""
    _signal_group(p.pid, signal.SIGTERM)
    try:
        end = time.monotonic() + GIT_TERM_GRACE
        while _group_left(p) and time.monotonic() < end:
            time.sleep(0.01)
    finally:
        if _group_left(p):
            _signal_group(p.pid, signal.SIGKILL)
        p.wait()
        for f in (p.stdout, p.stderr):
            if f is not None:
                f.close()


def _signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except OSError:
        pass


def _group_left(p):
    """Whether anything of `p`'s process group is left: `p` still running, or, once it has exited and been reaped, any
    other process in its group (one this process adopted that has exited is reaped here, so it does not count)."""
    if p.poll() is None:
        return True
    try:
        while os.waitpid(-p.pid, os.WNOHANG)[0]:
            pass
    except ChildProcessError:
        pass
    try:
        os.killpg(p.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def find_repo(start):
    """The GitRepo of the repository whose work tree is the directory `start`, whose real path must exist and hold a .git
    entry (os.path.lexists, nothing opened): the clone (ROMP_BATCH_REPO, or the directory above the scripts/ directory
    this file is in), a batch worktree, the ledger check's tree. None of them is walked up from, so one that does not
    exist, or whose .git is gone, is a Fail naming it and is never resolved to a repository that encloses it: the clone
    since the closing check wf_3b100f5e-b38, its item 1; a batch worktree and the ledger check's tree were read without
    a walk before it, since the 02:43Z ruling, item 1(b), and a removed batch worktree is pinned (the closing check
    wf_fb19febe-36b, its item 6). git reads it there, `rev-parse --show-toplevel --absolute-git-dir --git-common-dir`
    with GIT_CEILING_DIRECTORIES at its parent, so a .git git does not recognize is a Fail naming the directory and
    never sends git on to an enclosing repository; and the directory is a Fail unless git's work tree
    there is that directory itself (same_dir, by identity), so a core.worktree in the repository's config that names
    another directory is refused here rather than taken as the work tree of every later call."""
    d = os.path.realpath(start)
    if not os.path.lexists(os.path.join(d, ".git")):
        why = ("there is no such directory" if not os.path.lexists(d) else "it is not a directory" if not os.path.isdir(d)
               else "no .git in it")
        raise Fail("%s is not a git working tree: %s" % (start, why))
    p = run_git(["rev-parse", "--path-format=absolute", "--show-toplevel", "--absolute-git-dir", "--git-common-dir"], d,
                repo=GitRepo(d, None, None, os.path.dirname(d)))
    found = p.stdout.splitlines() if p.returncode == 0 else []
    if len(found) != 3:
        raise Fail("%s is not a git working tree that git recognizes (%s)" % (d, (p.stderr or p.stdout).strip()))
    top, git_dir, common = found
    if not same_dir(top, d):
        raise Fail("%s is not the work tree git reads for the .git in it: git's work tree there is %s (a core.worktree in "
                   "the repository's config names it); give the directory that holds .git and is its work tree" % (d, top))
    return GitRepo(top, git_dir, common, os.path.dirname(top))


def same_dir(a, b):
    """Whether the paths `a` and `b` name one directory, compared by identity (os.path.samefile: the same device and
    inode), not by their real paths' text: git prints its work tree as getcwd gives it, which on a case-insensitive
    filesystem is the case on disk, not the case the path was given in, and os.path.realpath does not change a path's
    case (the closing check wf_fb19febe-36b, its item 9). False when either cannot be stat'ed."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def repo_for(cwd):
    """The GitRepo a call in `cwd` means: the batcher's clone as repo_root found it, else find_repo(cwd), read again on
    every call, since this tool adds and removes worktrees as it goes."""
    return _REPOS.get(os.path.realpath(cwd)) or find_repo(cwd)


def git_proc(*args, cwd=None, check=True):
    """run_git's CompletedProcess, and with `check` a Fail naming the call when it exits nonzero."""
    proc = run_git(args, cwd)
    if check and proc.returncode != 0:
        raise Fail("git %s failed (%d):\n%s%s" % (" ".join(args), proc.returncode, proc.stdout, proc.stderr))
    return proc


def git(*args, cwd=None, check=True):
    return git_proc(*args, cwd=cwd, check=check).stdout.strip()


def git_ok(*args, cwd=None):
    """Whether `git <args>` exits 0; False too when `cwd` holds no repository git recognizes. A git that does not end
    within GIT_BOUND still raises GitBound: a call that was killed is not an answer."""
    try:
        repo = repo_for(cwd)
    except GitBound:
        raise
    except Fail:
        return False
    return run_git(args, cwd, repo=repo).returncode == 0


def gh_bin():
    gh = os.environ.get("ROMP_GH") or shutil.which("gh")
    if not gh:
        raise Fail("the GitHub CLI (gh) is not on PATH; install it or set ROMP_GH")
    return gh


def gh(*args, cwd=None, check=True):
    return _run([gh_bin(), *args], cwd=cwd, check=check)


def gh_json(*args, cwd=None):
    out = gh(*args, cwd=cwd).stdout
    try:
        return json.loads(out or "null")
    except json.JSONDecodeError as e:
        raise Fail("gh %s returned something that is not JSON: %s" % (" ".join(args), e))


# ── repository layout ────────────────────────────────────────────────────────

def repo_root():
    """The clone this script acts on: ROMP_BATCH_REPO, else the clone the script file lives in, the directory above its
    scripts/ directory; each must be the directory holding the clone's .git (find_repo: neither is walked up from)."""
    override = os.environ.get("ROMP_BATCH_REPO")
    repo = find_repo(override if override else os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    root = repo.work_tree
    _REPOS[root] = repo
    return root


def common_dir(root):
    return repo_for(root).common_dir


def state_dir(root):
    d = os.path.join(common_dir(root), "batch")
    os.makedirs(d, exist_ok=True)
    return d


def state_path(root, name):
    return os.path.join(state_dir(root), name + ".json")


# How read_state opens a state file: no symlink followed (O_NOFOLLOW), no wait for a FIFO's writer (O_NONBLOCK), and
# no terminal made this process's controlling terminal (O_NOCTTY), as scripts/sweep.py's open_regular opens.
_STATE_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY
# The most bytes read_state reads of a batch state file. The largest real one, measured 2026-10-03 among the 24 plans in
# a working clone's common dir, was 29,946 bytes; 1 MiB is over 35 times it. A leg can leave a sparse file of any size
# there, which costs it nothing on disk, so a larger one is refused naming its size, and is not read.
STATE_MAX = 1 << 20


def read_state(path):
    """The bytes of the batch state file at `path`, or None when nothing is there: os.lstat first, and anything but a
    regular file (a FIFO, a symlink, a directory) is a Fail naming the path and what is there, never opened; then an open
    with _STATE_READ_FLAGS, read only when fstat finds a regular file, so one swapped in after the lstat is refused the
    same way. The state lives in the clone's common dir, which a sweep's leg reaches through its checkout's alternates:
    a FIFO there, opened by name, held verify and assemble without end (the verify pass at PR 926's build head, its code
    finding 1). A regular file is read only when fstat gives it at most STATE_MAX bytes, of which no more are read, and a
    larger one (a sparse file included) is a Fail naming its size and the limit, as the runner's own reads are bounded
    (scripts/sweep.py's read_regular; round 1 of PR 959, ruling A's class). read_small_file reads the same way."""
    return read_small_file(path, STATE_MAX, "the batch state", "move it aside and plan again")


def read_small_file(path, limit, what, remedy):
    """The bytes of the file at `path`, read as read_state's docstring says, with `limit` the most bytes read; a refusal
    is a Fail saying "<what> <path> cannot be read (...); <remedy>"."""
    kinds = {stat.S_IFIFO: "a FIFO", stat.S_IFLNK: "a symlink", stat.S_IFDIR: "a directory", stat.S_IFCHR: "a character device",
             stat.S_IFBLK: "a block device", stat.S_IFSOCK: "a socket"}

    def refuse(mode):
        raise Fail("%s %s cannot be read (%s, not a regular file); %s"
                   % (what, path, kinds.get(stat.S_IFMT(mode), "a file of another type"), remedy))

    def too_large(words):
        raise Fail("%s %s cannot be read (%s); %s" % (what, path, words, remedy))
    try:
        st = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    if not stat.S_ISREG(st.st_mode):
        refuse(st.st_mode)
    try:
        fd = os.open(path, _STATE_READ_FLAGS)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as e:
        if e.errno == errno.ELOOP:
            refuse(stat.S_IFLNK)
        raise
    try:
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode):
            refuse(fst.st_mode)
        if fst.st_size > limit:
            too_large("%d bytes, more than the %d batch.py reads" % (fst.st_size, limit))
        f = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with f:
        data = f.read(limit + 1)
    if len(data) > limit:
        too_large("more than the %d bytes batch.py reads" % limit)
    return data


def load_state(root, name):
    p = state_path(root, name)
    data = read_state(p)
    if data is None:
        raise Fail("no plan named %s (%s); run `scripts/batch.py plan` first" % (name, p))
    return json.loads(data.decode("utf-8"))


def save_state(root, state):
    p = state_path(root, state["name"])
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".batch-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)


def worktree_dir(root, name):
    return os.path.join(os.path.dirname(root), "romp-batch-" + name)


def branch_of(name):
    return "batch/" + name


def batch_ref(name):
    """The batch branch of `name` by its full ref, as the git calls that need only its commit name it (MAIN_REF's
    comment), and as finish's check that the local branch is still there and bisect's cleanups name it (the 22:25Z
    ruling of 2026-10-03 on PR 959, item 1): <common dir>/batch/<name>, a name git tries before refs/heads/batch/<name>,
    is in the directory that holds the batch state. While the ref exists git opens no other name for it; an absent one
    sends a call that resolves it as a name on through the names its rules make of the full name, so finish's check
    reads it with git show-ref --verify, which reads only the ref it is given. assemble's git worktree add -B and git
    checkout -B (prepare_worktree) name the branch by branch_of, the short name, which git looks up by its rules once it
    has set the branch, opening <common dir>/batch/<name>, refs/batch/<name> and refs/tags/batch/<name> before
    refs/heads/batch/<name>, each under the common dir (SHORT_NAME_RULES), and git checkout -B looks its start point,
    MAIN_REF, up as a local branch first, refs/heads/refs/remotes/origin/main; both run under GIT_MEMORY, and the
    GitMemory of either names each of those files that is not a regular file or is oversized (_ref_files; the module
    docstring names their witness);
    branch_of's other uses name the branch in messages, to gh, to git branch -D, which names refs/heads/<its argument>
    itself, and as the remote's branch in a push (git 2.43.0, traced on 2026-10-03)."""
    return "refs/heads/" + branch_of(name)


def remote_ref(branch):
    """origin's `branch` by its full remote-tracking ref (MAIN_REF's comment)."""
    return "refs/remotes/%s/%s" % (REMOTE, branch)


def remote_main():
    return "%s/%s" % (REMOTE, MAIN)


def now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(state, line):
    """The assembly log: one timestamped line per action, shown in the body's details block."""
    state.setdefault("assembly", {}).setdefault("log", []).append("%s %s" % (now(), line))
    print(line)


def fetch(root, no_fetch):
    if not no_fetch:
        git("fetch", "--quiet", "--prune", REMOTE, cwd=root)


def members_by_n(state):
    return {int(k): v for k, v in state["members"].items()}


def short(sha):
    return (sha or "")[:10]


# ── PR data ──────────────────────────────────────────────────────────────────

PR_FIELDS = "number,title,body,labels,baseRefName,headRefName,headRefOid,isDraft,mergeable,url,state"


def label_names(pr):
    return [l["name"] if isinstance(l, dict) else str(l) for l in (pr.get("labels") or [])]


def tier_of(labels):
    tiers = [l for l in labels if l in TIERS]
    return tiers[0] if tiers else None


def parse_trailer(body):
    """The optional `<!-- romp-pr: {...} -->` trailer: (dict|None, error|None)."""
    m = _PR_TRAILER.search(body or "")
    if not m:
        return None, None
    try:
        t = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return None, "trailer is not JSON (%s)" % e
    return (t if isinstance(t, dict) else None), (None if isinstance(t, dict) else "trailer is not an object")


def parse_depends_on(body):
    """The PR numbers a body declares with `Depends-on:` in its first DEPENDS_ON_LINES lines, outside
    fenced code blocks; `#N` tokens, or a bare number list. Sorted, without duplicates."""
    out, fence, seen = set(), None, 0
    for line in (body or "").splitlines():
        f = _FENCE.match(line)
        if f:
            if fence is None:
                fence = f.group(1)
            elif f.group(1) == fence:
                fence = None
            continue
        if fence:
            continue
        seen += 1
        if seen > DEPENDS_ON_LINES:
            break
        m = _DEPENDS_ON.match(line)
        if not m:
            continue
        rest = m.group(1)
        nums = re.findall(r"#(\d+)", rest)
        if not nums and re.fullmatch(r"[\d,\s]+", rest.strip() or "x"):
            nums = re.findall(r"\d+", rest)
        out.update(int(x) for x in nums)
    return sorted(out)


def sensitive_paths(paths):
    hits = []
    for p in paths:
        for pre in SENSITIVE_PREFIXES:
            if p.startswith(pre) and pre not in hits:
                hits.append(pre)
        if p in SENSITIVE_FILES and p not in hits:
            hits.append(p)
    return hits


def ensure_object(root, sha, ref_hint):
    """Make sure a pinned head is in the object store; a plain `fetch origin` brings every branch,
    but a head GitHub reports can be newer than the last fetch."""
    if not git_ok("cat-file", "-e", sha + "^{commit}", cwd=root):
        git("fetch", "--quiet", REMOTE, ref_hint, cwd=root)
        if not git_ok("cat-file", "-e", sha + "^{commit}", cwd=root):
            raise Fail("commit %s (head of %s) is not reachable from origin; was the branch force-pushed?" % (short(sha), ref_hint))


def merged_pr_for_branch(root, branch):
    """(number, head sha at the merge) of the latest MERGED PR whose head was `branch`, or (None,
    None). A PR based on such a branch is the stranded case (2026-09-06: four PRs merged into
    already-merged bases), so it is refused, but by SHA and not by name alone: the fork reuses branch
    names, and a live branch that has moved on from the merged head is not that PR's."""
    rows = gh_json("pr", "list", "--state", "merged", "--head", branch, "--json", "number,headRefOid", "--limit", "5", cwd=root)
    return (rows[0]["number"], rows[0].get("headRefOid")) if rows else (None, None)


def dependency_status(root, d):
    """A declared dependency that is not an open PR: "satisfied" when it merged into main (its content
    is in the base every batch starts from), else why it cannot be satisfied."""
    proc = gh("pr", "view", str(d), "--json", "state,mergeCommit,headRefOid", cwd=root, check=False)
    if proc.returncode != 0:
        return "not a PR"
    try:
        pr = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return "not a PR"
    if pr.get("state") != "MERGED":
        return "%s, not merged" % (pr.get("state") or "unknown").lower()
    merge = (pr.get("mergeCommit") or {}).get("oid")
    for sha in (merge, pr.get("headRefOid")):
        if sha and git_ok("cat-file", "-e", sha + "^{commit}", cwd=root) and is_ancestor(sha, MAIN_REF, root):
            return "satisfied"
    return "merged, but not into %s" % MAIN


# ── plan ─────────────────────────────────────────────────────────────────────

def pick_name(root):
    today = _dt.date.today().isoformat()
    remote_batches = set(git("for-each-ref", "--format=%(refname:short)", "refs/remotes/%s/batch/" % REMOTE, cwd=root).split())
    for letter in "abcdefghijklmnopqrstuvwxyz":
        name = today + letter
        if os.path.exists(state_path(root, name)):
            continue
        if "%s/batch/%s" % (REMOTE, name) in remote_batches:
            continue
        return name
    raise Fail("27 batches in one day; pass --name")


def order_members(cands):
    """Dependencies first, then by number (Kahn's algorithm with a number-ordered frontier). Returns
    (order, stuck): `stuck` are the candidates a dependency cycle keeps out of the order, the cycle's
    own members and everything that depends on them; the caller excludes them with the cycle named
    and plans the rest."""
    import heapq
    indeg = {n: 0 for n in cands}
    dependents = {n: [] for n in cands}
    for n, m in cands.items():
        for d in m["depends_on"]:
            if d in cands:
                indeg[n] += 1
                dependents[d].append(n)
    heap = [n for n, k in indeg.items() if k == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        n = heapq.heappop(heap)
        order.append(n)
        for d in sorted(dependents[n]):
            indeg[d] -= 1
            if indeg[d] == 0:
                heapq.heappush(heap, d)
    return order, sorted(set(cands) - set(order))


def reaches(cands, a, b):
    """Whether a's `Depends-on` chain among the candidates reaches b (a == b: a is in a cycle)."""
    seen, frontier = set(), [d for d in cands[a]["depends_on"] if d in cands]
    while frontier:
        d = frontier.pop()
        if d == b:
            return True
        if d in seen:
            continue
        seen.add(d)
        frontier.extend(x for x in cands[d]["depends_on"] if x in cands)
    return False


def predict_conflicts(root, base_sha, ordered, cands):
    """Read-only merge prediction with `git merge-tree --write-tree` against the accumulating tree.

    Each clean step becomes a dangling commit object (commit-tree; no ref is written, so nothing
    but the object store changes and gc reclaims it) so the next step's merge base is right. A
    conflicting member is recorded with its files and the earlier members whose own diff touches
    those files, and the accumulation continues without it."""
    acc = base_sha
    for n in ordered:
        m = cands[n]
        proc = git_proc("merge-tree", "--write-tree", "--name-only", "--no-messages", acc, m["head"], cwd=root, check=False)
        lines = proc.stdout.splitlines()
        if proc.returncode == 0 and lines:
            tree = lines[0]
            acc = git("commit-tree", tree, "-p", acc, "-p", m["head"], "-m", "batch plan: after #%d" % n, cwd=root)
            m["predicted_conflict"] = None
        elif proc.returncode == 1 and lines:
            files = []
            for l in lines[1:]:
                if not l.strip():
                    break
                files.append(l.strip())
            with_members = [k for k in ordered[:ordered.index(n)]
                            if set(cands[k]["touches"]) & set(files) and cands[k].get("predicted_conflict") is None]
            m["predicted_conflict"] = {"files": files, "with": with_members}
        else:
            m["predicted_conflict"] = {"files": [], "with": [], "error": (proc.stderr or proc.stdout).strip()[:300]}


def cmd_plan(args):
    root = repo_root()
    if args.name:
        refuse_equals_in_name(args.name)
    fetch(root, args.no_fetch)
    base_sha = git("rev-parse", MAIN_REF, cwd=root)
    name = args.name or pick_name(root)
    if os.path.exists(state_path(root, name)) and not args.force:
        old = load_state(root, name)
        if old.get("assembly", {}).get("head"):
            raise Fail("%s is already assembled (pulled: %s); re-planning would forget that. Use a new --name, or --force."
                       % (name, ", ".join("#%d" % n for n in old.get("pulled", [])) or "none"), code=2)
    prs = gh_json("pr", "list", "--state", "open", "--limit", str(PR_LIST_LIMIT), "--json", PR_FIELDS, cwd=root)
    by_n = {pr["number"]: pr for pr in prs}
    only = sorted(set(args.only or []))
    absent = [n for n in only if n not in by_n]
    if absent:
        raise Fail("--only %s: not an open PR" % ", ".join("#%d" % n for n in absent), code=2)

    excluded = {}   # n -> reason
    cands = {}
    for n, pr in sorted(by_n.items()):
        labels = label_names(pr)
        if pr.get("isDraft"):
            excluded[n] = "draft"
        elif LABEL_MAJOR in labels:
            excluded[n] = "labeled %s (discussed first)" % LABEL_MAJOR
        elif LABEL_HOLD in labels:
            excluded[n] = "labeled %s" % LABEL_HOLD
        elif LABEL_BATCH in labels or pr["headRefName"].startswith("batch/"):
            excluded[n] = "a batch PR"
        elif args.labeled and LABEL_LAND not in labels:
            excluded[n] = "not labeled %s (plan --labeled)" % LABEL_LAND
        elif only and n not in only:
            excluded[n] = NOT_ONLY
        else:
            trailer, terr = parse_trailer(pr.get("body"))
            cands[n] = {
                "n": n, "title": pr["title"], "url": pr.get("url"),
                "head": pr["headRefOid"], "head_ref": pr["headRefName"], "base_ref": pr["baseRefName"],
                "labels": labels, "tier": tier_of(labels),
                "depends_on": parse_depends_on(pr.get("body")),
                "trailer": trailer, "trailer_error": terr,
                "mergeable": pr.get("mergeable"),
                "touches": [], "predicted_conflict": None,
            }
    # A base that is another open PR's branch is a dependency on that PR (and if that PR is not a
    # candidate, the fixpoint below takes the dependent out with it, naming why); any other non-main
    # base leaves the PR out (a base belonging to a merged PR is the stranded case and gets the fix
    # in its reason).
    heads = {pr["headRefName"]: n for n, pr in by_n.items()}
    for n, m in list(cands.items()):
        b = m["base_ref"]
        if b == MAIN:
            continue
        if b in heads and heads[b] != n:
            if heads[b] not in m["depends_on"]:
                m["depends_on"].append(heads[b])
                m["depends_on"].sort()
            continue
        merged, merged_head = merged_pr_for_branch(root, b)
        live = git("rev-parse", "--verify", "--quiet", remote_ref(b), cwd=root, check=False) or None
        if merged and (live is None or live == merged_head or is_ancestor(live, base_sha, root)):
            excluded[n] = "base %s belongs to merged PR #%d; run `gh pr edit %d --base %s`" % (b, merged, n, MAIN)
        elif merged:
            excluded[n] = "base %s was merged PR #%d's branch and now holds other commits with no open PR" % (b, merged)
        else:
            excluded[n] = "base %s is neither %s nor a candidate's branch" % (b, MAIN)
        del cands[n]
    # A member owes a passing sweep of its own head before its review and its closing check, so plan reads it
    # through the reader verify uses: a candidate without one is left out with the case named (and its dependents
    # with it, through the fixpoint below).
    sweep = sweep_reader()
    for n, m in list(cands.items()):
        why, m["sweep"] = member_sweep(root, sweep, m)
        if why:
            excluded[n] = "no passing sweep at its head (%s)" % why
            del cands[n]
    # A dependency that is not a candidate takes its dependents out too (failure mode 7), unless it
    # already merged into main: then it is satisfied by the base every batch starts from, and the
    # dependent stays (docs tell authors to leave `Depends-on` in the body; it must not strand them).
    satisfied = {}

    def drop_dependents_of_excluded():
        changed = True
        while changed:
            changed = False
            for n, m in list(cands.items()):
                for d in list(m["depends_on"]):
                    if d in cands:
                        continue
                    if d not in excluded:
                        status = satisfied.get(d) or dependency_status(root, d)
                        satisfied[d] = status
                        if status == "satisfied":
                            m["depends_on"].remove(d)
                            m.setdefault("depends_on_merged", []).append(d)
                            continue
                    why = excluded.get(d) or satisfied.get(d) or "not an open PR"
                    excluded[n] = "depends on #%d (%s)" % (d, why)
                    del cands[n]
                    changed = True
                    break

    drop_dependents_of_excluded()
    for n, m in cands.items():
        ensure_object(root, m["head"], m["head_ref"])
        mb = git("merge-base", base_sha, m["head"], cwd=root)
        m["touches"] = git("diff", "--name-only", mb, m["head"], cwd=root).split()
    ordered, stuck = order_members(cands)
    if stuck:
        # A `Depends-on` cycle (a PR naming itself, two naming each other) is that PR's mistake, not
        # the batch's: its members are excluded with the cycle named, their dependents with them
        # (through the fixpoint above), and the rest is planned.
        cyclic = [n for n in stuck if reaches(cands, n, n)]
        partners = {n: [k for k in cyclic if k != n and reaches(cands, n, k) and reaches(cands, k, n)] for n in cyclic}
        for n in cyclic:
            excluded[n] = ("in a dependency cycle with %s" % ", ".join("#%d" % k for k in partners[n])) if partners[n] \
                else "depends on itself (Depends-on: #%d)" % n
            del cands[n]
        drop_dependents_of_excluded()
        ordered, stuck = order_members(cands)
        if stuck:
            raise Fail("dependency cycle among PRs %s" % ", ".join("#%d" % n for n in stuck))
    predict_conflicts(root, base_sha, ordered, cands)

    state = {
        "name": name, "created": now(), "base": base_sha, "labeled": bool(args.labeled),
        "order": ordered, "members": {str(n): cands[n] for n in ordered},
        "excluded": [{"n": n, "reason": r} for n, r in sorted(excluded.items())],
        "pulled": [], "assembly": {"log": []}, "sweep": None, "verified": None, "pr": None, "commented": {},
    }
    save_state(root, state)

    print("plan %s: base %s (%s), %d member(s), %d excluded" % (name, remote_main(), short(base_sha), len(ordered), len(excluded)))
    for n in ordered:
        m = cands[n]
        flags = []
        if m["depends_on"]:
            flags.append("after " + ", ".join("#%d" % d for d in m["depends_on"]))
        if m["trailer"] is None:
            flags.append("trailer missing" if not m["trailer_error"] else m["trailer_error"])
        if m["tier"] is None:
            flags.append("unlabeled")
        pc = m["predicted_conflict"]
        if pc:
            flags.append("PREDICTED CONFLICT in %s%s" % (", ".join(pc["files"]) or "?",
                                                         (" with " + ", ".join("#%d" % k for k in pc["with"])) if pc["with"] else ""))
        print("  #%d %s @%s [%s]%s" % (n, m["title"], short(m["head"]), m["tier"] or "unlabeled",
                                     ("  " + "; ".join(flags)) if flags else ""))
    others = [row["n"] for row in state["excluded"] if row["reason"] == NOT_ONLY]
    for row in state["excluded"]:
        if row["reason"] != NOT_ONLY:
            print("  excluded #%d: %s" % (row["n"], row["reason"]))
    if others:
        print("  excluded, %s: %s" % (NOT_ONLY, ", ".join("#%d" % n for n in others)))
    missing = [n for n in ordered if cands[n]["trailer"] is None]
    if missing:
        print("message the authors once (trailer missing): %s" % ", ".join("#%d" % n for n in missing))
    print("written: %s" % state_path(root, name))


# ── assemble ─────────────────────────────────────────────────────────────────

def other_remote_batches(root, name):
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/%s/batch/" % REMOTE, cwd=root).split()
    return [r for r in refs if r != "%s/%s" % (REMOTE, branch_of(name))]


def merge_in_progress(wt):
    return os.path.exists(os.path.join(git("rev-parse", "--git-path", "MERGE_HEAD", cwd=wt)))


def prepare_worktree(root, name):
    """A fresh `batch/<name>` at origin/main in ../romp-batch-<name>, reusing the directory when it
    is already this batch's worktree. That directory is the tool's, so resetting it is fine; the
    shared checkout is never touched."""
    wt = worktree_dir(root, name)
    # Both calls below name the branch by its short name, which git looks up by its rules once it has set the branch,
    # opening <common dir>/batch/<name>, refs/batch/<name> and refs/tags/batch/<name> before refs/heads/batch/<name>,
    # and git checkout -B looks MAIN_REF up as a local branch first, refs/heads/<MAIN_REF> (batch_ref's docstring; a
    # GitMemory of either names those files, _ref_files; the module docstring names the witness).
    br = branch_of(name)
    if os.path.isdir(wt) and git_ok("rev-parse", "--is-inside-work-tree", cwd=wt):
        if merge_in_progress(wt):
            git("merge", "--abort", cwd=wt)
        git("checkout", "--quiet", "-B", br, MAIN_REF, cwd=wt)
    else:
        git("worktree", "prune", cwd=root)    # a directory removed by hand leaves a registration that blocks -B
        git("worktree", "add", "--quiet", "-B", br, wt, MAIN_REF, cwd=root)
    # rerere in the repository config: the cache (.git/rr-cache) is shared by every worktree, which
    # is what lets a re-assemble replay a resolution the batcher made once.
    git("config", "rerere.enabled", "true", cwd=wt)
    git("config", "rerere.autoUpdate", "true", cwd=wt)
    return wt


def dependents_of(state, n):
    """Transitive dependents of n among the planned members."""
    members = members_by_n(state)
    out, frontier = set(), {n}
    while frontier:
        nxt = set()
        for k, m in members.items():
            if k not in out and set(m["depends_on"]) & frontier:
                out.add(k)
                nxt.add(k)
        frontier = nxt
    return sorted(out)


def member_rows_added(root, base_sha, head, path=UPSTREAM_MD):
    """The table rows a member ADDS to UPSTREAM.md against its merge base, and whether that is all
    it does to the file. (added_rows, only_rows)."""
    mb = git("merge-base", base_sha, head, cwd=root)
    diff = git_proc("--literal-pathspecs", "diff", "--unified=0", mb, head, "--", path, cwd=root, check=False).stdout
    rows, other = [], False
    for line in diff.splitlines():
        if line.startswith(("+++", "---", "@@", "diff ", "index ")):
            continue
        if line.startswith("+"):
            body = line[1:]
            if body.strip().startswith("|") and body.strip().endswith("|"):
                rows.append(body.strip())
            elif body.strip():
                other = True
        elif line.startswith("-") and line[1:].strip():
            other = True
    return rows, not other


def convert_ledger_rows(root, wt, state, m):
    """The straggler fix inside a member's merge commit: a member that still appends a UPSTREAM.md
    row after the migration conflicts on that file; each added row becomes an entry file through
    `scripts/upstream-ledger.py import --row '<row>'` and the table hunk is dropped by keeping the
    batch side of UPSTREAM.md. Returns the number of rows converted, or None when this conversion
    does not apply (no ledger script in the batch tree, the member changed more than rows, or the
    conversion failed) so the caller treats the conflict like any other.

    The `import --row` interface is the plan's specification of the ledger script (built by a
    sibling branch); the first real batch verifies the two agree."""
    if not os.path.exists(os.path.join(wt, LEDGER_SCRIPT)):
        return None
    rows, only_rows = member_rows_added(root, state["base"], m["head"])
    if not rows or not only_rows:
        return None
    for row in rows:
        proc = run_tool([sys.executable, LEDGER_SCRIPT, "import", "--row", row], wt)
        if proc.returncode != 0:
            log(state, "#%d: import --row failed: %s" % (m["n"], (proc.stderr or proc.stdout).strip()[:300]))
            return None
    git("checkout", "--ours", "--", UPSTREAM_MD, cwd=wt)
    git("add", "--", UPSTREAM_MD, cwd=wt)
    if os.path.isdir(os.path.join(wt, "upstream")):
        git("add", "--", "upstream", cwd=wt)
    return len(rows)


def unmerged_paths(wt):
    return git("diff", "--name-only", "--diff-filter=U", cwd=wt).split()


def staged_paths(wt, paths):
    """Among `paths`, those the index holds at stage 0: staged whole, neither unmerged nor absent. The
    paths are given to git literally, not as pathspecs (`a[1].txt` would also match `a1.txt`), and
    only the entries named in `paths` count."""
    if not paths:
        return []
    wanted, out = set(paths), []
    for entry in git_proc("--literal-pathspecs", "ls-files", "--stage", "-z", "--", *paths, cwd=wt).stdout.split("\0"):
        meta, _, path = entry.partition("\t")
        if path in wanted and meta.split()[2] == "0":
            out.append(path)
    return out


def undone_paths(wt, paths):
    """Among `paths`, those the index's resolve-undo record lists: each path the merge in progress left unmerged in
    the index and that was then resolved there. git commit keeps the record (the paths of a hand resolution that
    assemble --continue committed are still listed after it), and git merge clears it as it starts, so during a merge
    it holds that merge's paths alone (git 2.43.0 and 2.55.0, 2026-10-04; pinned with such a stale record present
    before the merge, tests/test_batch_tool.py, test_merges_read_the_options_merge_tree_reads_and_a_refused_merge_is_not_read_as_a_replay).
    Given to git literally, as staged_paths gives them."""
    if not paths:
        return []
    wanted, out = set(paths), set()
    listed = git_proc("--literal-pathspecs", "ls-files", "--resolve-undo", "-z", "--", *paths, cwd=wt).stdout
    for entry in listed.split("\0"):
        path = entry.partition("\t")[2]
        if path in wanted:
            out.add(path)
    return sorted(out)


def replayed_paths(wt, conflicted, still):
    """The conflicted paths rerere replayed and staged: conflicted, not unmerged, in the index at stage 0, and in the
    index's resolve-undo record (undone_paths), which lists the paths the merge left unmerged and that were resolved
    after it. batch.py's merges read the merge options merge-tree reads (MERGE_STRATEGY's comment), so a path
    merge-tree names conflicted is one git merge leaves unmerged, unless rerere resolves it, staging the recorded
    resolution (rerere.autoUpdate). The stage-0 condition is not implied by the first two: for a distinct-types
    conflict (a file on one side, a symlink on the other) merge-tree names the aside copy after the SHA it was given
    (`notes.txt~<sha>`) while `git merge` names it `notes.txt~HEAD`, so the merge-tree path is conflicted and not
    unmerged and exists nowhere; without the index check a first assembly said rerere had replayed it. The record is a
    second check, for a road by which git merge resolves a conflict merge-tree reports without rerere, which the options
    were the known roads to: before round 3 of PR 959 (correctness-1) git merge read the user's, and an option it reads
    and merge-tree does not (-Xours in branch.<name>.mergeOptions, say) resolved the conflict inside git merge, the file
    staged whole, nothing unmerged and merge-tree still naming it conflicted. ort writes no resolve-undo entry for such
    a resolution, so the record told it from a replay, and a merge the clone's pre-merge-commit hook refused after it
    was refused (round 2's spot-check of PR 959, L3; refused_merge), where before the record a merge so refused was read
    as rerere's replay and committed with git commit, which does not run that hook; merge-recursive wrote an entry for
    each file it merged (git 2.43.0, '-s recursive -Xours' or pull.twohead=recursive), so the record alone did not tell
    them apart, and the options merge-tree reads now do. rerere's own files do not say which paths it replayed: it drops each one it replays from MERGE_RR, git rerere
    status and git rerere remaining print nothing after a whole replay, as after such a refusal, and the empty MERGE_RR
    git commit leaves after a replay is still there at the next merge (git 2.43.0, 2026-10-04)."""
    return undone_paths(wt, staged_paths(wt, sorted(set(conflicted) - set(still))))


def resolution_diff(cwd, merge, paths):
    """The resolution as a diff: from the merge-tree of the merge's parents (conflict markers left in
    the conflicted files) to the merge, over `paths`. That shows the conflict text turning into the
    chosen text; a combined diff (`git show --cc`) omits every hunk equal to one parent, so a side
    taken wholesale rendered as nothing. None when this git cannot compute the merge-tree."""
    ps = parents_of(merge, cwd)
    if len(ps) != 2:
        return None
    mt, _, _ = merge_tree_of(ps[0], ps[1], cwd)
    if mt is None:
        return None
    # --literal-pathspecs: a resolution path with [ * ? in its name is a file name, not a pattern.
    return git_proc("--literal-pathspecs", "diff", "--no-color", mt, merge + "^{tree}", "--", *paths, cwd=cwd, check=False).stdout


def resolution_hunks(cwd, merge, paths):
    out = resolution_diff(cwd, merge, paths)
    return None if out is None else sum(1 for l in out.splitlines() if l.startswith("@@"))


def blob_of(rev, path, cwd):
    return git("rev-parse", "--verify", "--quiet", "%s:%s" % (rev, path), cwd=cwd, check=False) or None


def hunk_lines(cwd, mt, tree, path):
    """One path's resolution as the diff from `mt` (the merge-tree of the parents, markers left in the
    conflicted files) to `tree`, reduced to what identifies the resolution of the hunks: the lines
    the diff removes and adds, in order. Hunk headers and context lines are dropped, since line
    numbers and neighboring lines move when the file changes outside the conflict between
    assemblies; each conflict marker line is cut back to the marker, since its label names a parent
    by SHA and the batch side is a different commit in each assembly. None when the diff has no text
    hunk (a binary file, an unchanged path), where the lines would identify nothing."""
    proc = run_git(["--literal-pathspecs", "diff-tree", "-r", "-p", mt, tree, "--", path], cwd, text=False)
    if proc.returncode != 0:
        return None
    out, in_hunk, after_change = [], False, False
    for line in proc.stdout.split(b"\n"):
        if line.startswith(b"@@"):
            in_hunk, after_change = True, False
        elif line.startswith(b"diff --git"):
            in_hunk = False
        elif not in_hunk:
            continue
        elif line[:1] in (b"-", b"+"):
            body = line[1:]
            if _CONFLICT_MARKER.match(body.decode("utf-8", "replace")):
                line = line[:8]
            out.append(line)
            after_change = True
        elif line.startswith(b"\\"):
            # "\ No newline at end of file" qualifies the line before it: part of the resolution
            # after a change line, part of the surroundings after a context line.
            if after_change:
                out.append(line)
        else:
            after_change = False
    return out or None


def hunk_hash(cwd, mt, tree, path):
    lines = hunk_lines(cwd, mt, tree, path)
    return None if lines is None else hashlib.sha256(b"\n".join(lines)).hexdigest()


def resolution_choices(cwd, merge, paths, label1, label2):
    """Per path, what the resolution chose when it equals one parent's version: {path: phrase}. label1
    names the merge's first parent (the batch), label2 the second (a member, or origin/main). A path
    combined by hand, or one both parents agree on, has no entry."""
    ps = parents_of(merge, cwd)
    if len(ps) != 2:
        return {}
    out = {}
    for p in paths:
        b, b1, b2 = (blob_of(x, p, cwd) for x in (merge, ps[0], ps[1]))
        if b1 == b2:
            continue
        if b == b2:
            out[p] = ("deleted the file, as %s did" % label2) if b2 is None else \
                "took %s's version" % label2 + (", which %s deleted" % label1 if b1 is None else "")
        elif b == b1:
            out[p] = ("kept the file deleted, as %s had it" % label1) if b1 is None else \
                "kept %s's version" % label1 + (", which %s deleted" % label2 if b2 is None else "")
    return out


def marker_paths(tree, paths, cwd):
    """The paths among `paths` whose blob in `tree` (a tree or commit) holds a conflict marker line."""
    out = []
    for p in paths:
        proc = run_git(["cat-file", "-p", "%s:%s" % (tree, p)], cwd, text=False)
        if proc.returncode == 0 and _CONFLICT_MARKER.search(proc.stdout.decode("utf-8", "replace")):
            out.append(p)
    return out


def hold_back(root, state, m, reason, files=None, against=None, with_members=None, notify=True):
    """Record a member held back and, for a conflict, tell its owner once per distinct reason.
    `against` is what the member conflicts with, in the owner's terms: "origin/main", "#101, #102"
    or "the batch". Whether the owner was told is RECORDED (`told`), never assumed: a failed
    `gh pr comment` is logged, printed for a postal message, and retried on the next rebuild."""
    entry = {"n": m["n"], "reason": reason, "files": files or [], "with": with_members or [], "told": None}
    state["assembly"].setdefault("held", []).append(entry)
    log(state, "#%d held back: %s" % (m["n"], reason))
    if files is None:
        return
    text = ("This PR conflicts with %s in %s, so this batch goes ahead without it. "
            "Merge origin/%s%s into yours, push, and comment here; the next batch includes it."
            % (against or "the batch", ", ".join(files), MAIN, " (or that PR's branch)" if with_members else ""))
    told = state.setdefault("held_notified", {})
    if not notify:
        entry["told"], entry["told_why"] = False, "--no-notify"
    elif told.get(str(m["n"])) == text:
        # Once per distinct reason: a rebuild after `pull` meets the same conflict again, and the
        # owner does not need the same comment twice.
        entry["told"], entry["told_why"] = True, "in an earlier assembly"
    else:
        proc = gh("pr", "comment", str(m["n"]), "--body", text, cwd=root, check=False)
        if proc.returncode == 0:
            told[str(m["n"])] = text
            entry["told"] = True
        else:
            err = [l for l in (proc.stderr or proc.stdout).strip().splitlines() if l.strip()]
            entry["told"], entry["told_why"] = False, "comment failed: %s" % (err[-1] if err else "exit %d" % proc.returncode)
            log(state, "#%d: gh pr comment failed (%s); the owner is NOT told, send the postal message below" % (m["n"], entry["told_why"]))
    print("postal (kind: coordinate) to the owner of #%d: %s" % (m["n"], text))


def conflict_attribution(root, state, m, files):
    """What a held-back member conflicts with, in the owner's terms: (text, earlier member numbers).
    A member that conflicts with origin/main by itself is told so (merging main fixes it); otherwise
    the earlier members whose own diff touches the conflicted files are named; failing both, "the
    batch"."""
    _, kind, _ = merge_tree_of(state["base"], m["head"], root)
    if kind == "conflicts":
        return remote_main(), []
    members = members_by_n(state)
    earlier = [e["n"] for e in state["assembly"]["merged"] if set(members[e["n"]]["touches"]) & set(files)]
    return (", ".join("#%d" % k for k in earlier) or "the batch"), earlier


def resolution_blobs(cwd, merge, paths):
    """Per path, the blob the merge holds for it (None where the resolution deleted it), recorded so a
    later rerere replay of the same bytes is recognized as the reviewed resolution."""
    return {p: blob_of(merge, p, cwd) for p in paths}


def resolution_hunk_hashes(cwd, merge, paths):
    """Per path, the identity of the merge's resolution of its hunks (hunk_hash), recorded with the
    blobs so a rerere replay of the same hunk resolution into a file that changed elsewhere since is
    recognized as the reviewed resolution too. None when this git cannot compute the merge-tree."""
    ps = parents_of(merge, cwd)
    mt = merge_tree_of(ps[0], ps[1], cwd)[0] if len(ps) == 2 else None
    if mt is None:
        return None
    return {p: hunk_hash(cwd, mt, merge + "^{tree}", p) for p in paths}


def prior_resolution(state, key, files, wt):
    """The resolution an earlier assembly of this batch recorded under `key` (a member number as a
    string, or "main") that covers `files`, the paths rerere replayed and staged in `wt`: every one of
    them is among the record's files and holds the recorded resolution, so the review carries over.
    A path holds it when the blob staged for it equals the record's, or when the diff from the
    conflicted merge-tree to the index resolves the hunks as the record did (hunk_hash): main, or
    an earlier member, can change the same file outside the conflict between assemblies, and rerere
    then replays the reviewed hunk resolution into a file of different bytes. A replay of a SUBSET of
    a recorded resolution qualifies: main can take one file's change between assemblies and leave
    the others to conflict again. The same hunks resolved to other bytes (rerere's cache is shared
    across batches, and a replayed file can be edited before --continue) do not. A record without
    hunk hashes, written before they were recorded, matches blob for blob; one without blobs, on an
    equal file list only."""
    rec = (state["assembly"].get("previous_resolutions") or {}).get(key)
    if not rec or not files or not set(files) <= set(rec.get("files") or []):
        return None
    blobs = rec.get("blobs")
    if blobs is None:
        return rec if set(files) == set(rec["files"]) else None
    differing = [p for p in files if blob_of("", p, wt) != blobs.get(p)]   # ":path" is the index at stage 0
    if not differing:
        return rec
    hashes = rec.get("hunk_hashes")
    if not hashes or not merge_in_progress(wt):
        return None
    mt, _, _ = merge_tree_of(git("rev-parse", "HEAD", cwd=wt), git("rev-parse", "MERGE_HEAD", cwd=wt), wt)
    index_tree = git("write-tree", cwd=wt, check=False)   # fails while a path is unmerged
    if mt is None or not index_tree:
        return None
    for p in differing:
        h = hunk_hash(wt, mt, index_tree, p)
        if h is None or h != hashes.get(p):
            return None
    return rec


def commit_resolution(wt, files):
    """Commit the staged result of a conflicted merge once no conflict marker is staged and it passes
    the subset rule: the result may differ from the merge git makes of the two parents by itself ONLY
    in the conflicted files (plus upstream/ entries for a row conversion). Anything else staged would
    land inside the merge commit unseen; the refusal names the paths and the tree that holds the
    merge's own content for them. The subset rule is checked first: a stray path is a stray path
    whatever it holds, and the marker refusal's advice (resolve, `git add`) is wrong for one. The
    marker scan then reads the conflicted files and every path that differs from that tree (all of
    them allowed by now): a conflicted file left as merge-tree wrote it does not differ from it. The
    parents are named by SHA, as verify names them, so the two merge-trees are the same object (the
    identifiers label the markers). Returns (sha, paths that differ from the clean merge)."""
    index_tree = git("write-tree", cwd=wt)
    mt, kind, _ = merge_tree_of(git("rev-parse", "HEAD", cwd=wt), git("rev-parse", "MERGE_HEAD", cwd=wt), wt)
    if mt is None:
        raise Fail("this git cannot compare the resolution with the clean merge of its parents (needs git 2.38); the merge is not committed")
    paths = git("diff-tree", "--name-only", "-r", mt, index_tree, cwd=wt).split()
    stray = stray_resolution_paths(files, paths)
    if stray:
        raise Fail("the staged merge also changes %s, outside the conflicted files (%s). A resolution may change only "
                   "the files that conflicted: restore the others to the merge's own content with "
                   "`git restore --source=%s --staged --worktree -- %s`, or move that change into a separate `batch:` "
                   "commit after the merge; then run --continue again."
                   % (", ".join(stray), ", ".join(files), mt, " ".join(stray)))
    marked = marker_paths(index_tree, sorted(set(paths) | set(files)), wt)
    if marked:
        raise Fail("a conflict marker is still staged in %s; resolve it, `git add` the file, then run --continue again" % ", ".join(marked))
    git("commit", "--quiet", "--no-edit", cwd=wt)
    return git("rev-parse", "HEAD", cwd=wt), paths


def base_branch_verdict(root, state, m):
    """What a member's non-main base is, compared by SHA and not by name alone (the fork reuses
    branch names). ("member", k): another member's branch, a dependency the order handles.
    ("merged", k): merged PR #k's branch, deleted or still at the merged head: the stranded case.
    ("reused", k): merged PR #k's branch name, now holding other commits that no member carries.
    ("unknown", None): neither main, nor a member's branch, nor a merged PR's."""
    b = m["base_ref"]
    for k, mm in members_by_n(state).items():
        if k != m["n"] and mm["head_ref"] == b:
            return "member", k
    merged_n, merged_head = merged_pr_for_branch(root, b)
    live = git("rev-parse", "--verify", "--quiet", remote_ref(b), cwd=root, check=False) or None
    if merged_n:
        if live is None or live == merged_head or is_ancestor(live, MAIN_REF, root):
            return "merged", merged_n
        return "reused", merged_n
    return "unknown", None


def refused_merge(wt, still, replayed, what, proc):
    """Abort the merge of `what` that `proc` left in progress in `wt`, and raise a Fail quoting what git printed, when
    it stopped with nothing unmerged (`still`) and nothing rerere replayed (`replayed`, the conflicted paths staged
    whole that the index's resolve-undo record lists: replayed_paths, round 2's spot-check of PR 959, L3, and round 3's
    correctness-1): a hook refused it (a refusal by
    pre-merge-commit, prepare-commit-msg or commit-msg each left MERGE_HEAD with nothing in conflict, git 2.43.0), and
    git's output is the one place the hook's own words are. Before, such a stop was read as a merge rerere had resolved
    whole and committed with git commit, which runs pre-commit, not pre-merge-commit, so a refusal by pre-merge-commit
    was passed over and the log said rerere had replayed a recorded resolution (git commit runs the other two again). On
    a git without merge-tree --write-tree (before 2.38), nothing reads as replayed (merge_tree_of gives no conflicted
    paths), so a replay there cannot be told from a refusal and fails too, loudly, rather than committing a merge a hook
    may have refused. No call passes --no-verify (GIT_SETTINGS' comment)."""
    if still or replayed:
        return
    git("merge", "--abort", cwd=wt)
    raise Fail("git merge of %s stopped with nothing in conflict (a hook refused it?):\n%s%s"
               % (what, proc.stdout, proc.stderr))


def merge_member(root, wt, state, m, resolve_set):
    """One member merge. Returns 'merged', 'contained' (its head was already in the batch, so no
    merge commit of its own), 'held', or 'stopped' (waiting for --continue)."""
    n = m["n"]
    if m["base_ref"] != MAIN:
        what, k = base_branch_verdict(root, state, m)
        if what == "merged":
            hold_back(root, state, m, "base %s belongs to merged PR #%d; retarget it to %s (`gh pr edit %d --base %s`)" % (m["base_ref"], k, MAIN, n, MAIN))
            return "held"
        if what == "reused":
            hold_back(root, state, m, "base %s was merged PR #%d's branch and now holds other commits that no member carries; "
                                      "make its PR a member or retarget #%d to %s" % (m["base_ref"], k, n, MAIN))
            return "held"
        if what == "unknown":
            hold_back(root, state, m, "base %s is neither %s nor a member's branch" % (m["base_ref"], MAIN))
            return "held"
    ensure_object(root, m["head"], m["head_ref"])
    before = git("rev-parse", "HEAD", cwd=wt)
    if is_ancestor(m["head"], before, wt):
        # `git merge` would say "Already up to date" and make no commit; recording HEAD as this
        # member's merge would be a bogus record (verify then fails on the count with no cause).
        members = members_by_n(state)
        by = next(("#%d" % e["n"] for e in state["assembly"]["merged"] if is_ancestor(m["head"], members[e["n"]]["head"], wt)), remote_main())
        state["assembly"].setdefault("contained", []).append({"n": n, "contained_by": by})
        log(state, "#%d is already contained by %s (its head %s is in the batch); no merge of its own%s"
            % (n, by, short(m["head"]), "; add Depends-on or reorder" if by != remote_main() else ""))
        return "contained"
    msg = "Merge #%d: %s" % (n, m["title"])
    # --no-log (round 2 of PR 959, ruling D, fresh-3): with merge.log set, in the clone's config or the user's, or --log
    # in the branch's mergeOptions, git merge appends a shortlog of the merged commits to the message even under -m,
    # and to describe the commit it merges it looks the full id up as a ref name under every rule (<common dir>/<sha>,
    # refs/<sha>, refs/tags/<sha>, refs/heads/<sha>, refs/remotes/<sha> and refs/remotes/<sha>/HEAD), whatever
    # core.warnAmbiguousRefs says, so a symlink to /dev/zero at refs/tags/<member head> stopped the merge (git 2.43.0,
    # traced on 2026-10-04). --no-log, which outranks the config and mergeOptions, drops that shortlog, so the commit's
    # message is the subject alone; batch.py reads only a merge's subject (subject_of), so nothing it relies on
    # changes. merge_main passes it for the same reason.
    proc = run_git(["merge", *MERGE_STRATEGY, "--no-ff", "--no-edit", "--no-log", "-m", msg, m["head"]], wt,
                   env={"GIT_MERGE_AUTOEDIT": "no"}, settings=merge_settings(state["name"]))
    if proc.returncode == 0:
        sha = git("rev-parse", "HEAD", cwd=wt)
        if sha == before or parents_of(sha, wt) != [before, m["head"]]:
            raise Fail("git merge of #%d made no merge commit of %s onto %s:\n%s%s" % (n, short(m["head"]), short(before), proc.stdout, proc.stderr))
        state["assembly"]["merged"].append({"n": n, "merge": sha, "resolved": None})
        log(state, "merged #%d at %s -> %s" % (n, short(m["head"]), short(sha)))
        return "merged"
    if not merge_in_progress(wt):
        raise Fail("git merge of #%d failed without a conflict to resolve:\n%s%s" % (n, proc.stdout, proc.stderr))
    # The files that conflicted are what git would conflict on by itself (merge-tree, plumbing) plus
    # what is unmerged in the index; those of the difference that the index holds at stage 0 are what
    # rerere replayed and staged (replayed_paths says why the index check is needed). A stop lists
    # ALL of them: a replayed file left off the cursor read as a stray change at --continue, and the
    # restore that refusal advised wrote the conflicted tree's markers into it.
    still = unmerged_paths(wt)
    _, _, would = merge_tree_of(before, m["head"], wt)
    conflicted = sorted(set(still) | set(would or []))
    replayed = replayed_paths(wt, conflicted, still)
    refused_merge(wt, still, replayed, "#%d" % n, proc)
    resolved = None
    if not still and merge_in_progress(wt):
        # rerere replayed a recorded resolution and staged the result (rerere.autoUpdate). The review
        # of the earlier assembly's resolution carries over when the replayed files hold that
        # resolution, blob for blob or hunk for hunk (prior_resolution).
        prior = prior_resolution(state, str(n), replayed, wt)
        resolved = {"files": conflicted, "hunks": None, "replayed": True,
                    "how": "rerere replayed the resolution recorded in the earlier assembly" if prior else "rerere replayed a recorded resolution",
                    "review": prior["review"] if prior else None}
    elif UPSTREAM_MD in still:
        rows = convert_ledger_rows(root, wt, state, m)
        if rows is not None:
            still = unmerged_paths(wt)
            if not still:
                how, review = "%d UPSTREAM.md row(s) converted to entries (mechanical)" % rows, "mechanical"
                if replayed:
                    prior = prior_resolution(state, str(n), replayed, wt)
                    how += "; rerere replayed the earlier assembly's resolution in %s" % ", ".join(replayed)
                    review = prior["review"] if prior else None
                resolved = {"files": conflicted, "how": how, "hunks": None, "review": review}
                if replayed:
                    resolved["replayed_files"] = replayed
    if resolved is not None and not unmerged_paths(wt):
        sha, _ = commit_resolution(wt, resolved["files"])
        resolved["hunks"] = resolution_hunks(wt, sha, resolved["files"])
        resolved["choices"] = resolution_choices(wt, sha, resolved["files"], "the batch", "#%d" % n)
        resolved["blobs"] = resolution_blobs(wt, sha, resolved["files"])
        resolved["hunk_hashes"] = resolution_hunk_hashes(wt, sha, resolved["files"])
        state["assembly"]["merged"].append({"n": n, "merge": sha, "resolved": resolved})
        log(state, "merged #%d -> %s with %s" % (n, short(sha), resolved["how"]))
        return "merged"
    files = conflicted
    if n in resolve_set:
        state["assembly"]["cursor"] = {"n": n, "files": files, "replayed": replayed}
        log(state, "#%d stopped for resolution in %s%s; resolve per hunk in %s, `git add` the files, then "
                   "`scripts/batch.py assemble %s --continue [--reviewed '<note>']`"
            % (n, ", ".join(files),
               (" (rerere replayed %s from the earlier assembly and staged it; the review covers the whole resolution)" % ", ".join(replayed)) if replayed else "",
               wt, state["name"]))
        return "stopped"
    git("merge", "--abort", cwd=wt)
    against, earlier = conflict_attribution(root, state, m, files)
    hold_back(root, state, m, "conflicts with %s in %s" % (against, ", ".join(files)),
              files=files, against=against, with_members=earlier, notify=not state["assembly"].get("no_notify"))
    return "held"


def continue_after_resolution(root, wt, state, reviewed):
    """Commit the merge a --resolve (or --merge-main) stop left in the worktree. Returns True when it
    was the merge of origin/main (no members follow it), False for a member."""
    cur = state["assembly"].get("cursor")
    if not cur:
        raise Fail("nothing to continue: no member is stopped for resolution")
    if not merge_in_progress(wt):
        raise Fail("no merge is in progress in %s; run assemble again without --continue" % wt)
    is_main = cur.get("main") is not None
    if is_main:
        expected, label = cur["main"], "the merge of %s" % remote_main()
    else:
        m = members_by_n(state)[cur["n"]]
        expected, label = m["head"], "#%d" % m["n"]
    if git("rev-parse", "MERGE_HEAD", cwd=wt) != expected:
        raise Fail("MERGE_HEAD in %s is not %s's pinned head" % (wt, label))
    still = unmerged_paths(wt)
    if still:
        raise Fail("still unmerged: %s (resolve and `git add` them first)" % ", ".join(still))
    files, replayed = cur["files"], cur.get("replayed") or []
    sha, _ = commit_resolution(wt, files)
    how = "resolved by the batcher, per hunk"
    if replayed:
        how += "; rerere replayed the earlier assembly's resolution in %s" % ", ".join(replayed)
    resolved = {"files": files, "how": how, "hunks": resolution_hunks(wt, sha, files), "review": reviewed,
                "choices": resolution_choices(wt, sha, files, "the batch", remote_main() if is_main else "#%d" % cur["n"]),
                "blobs": resolution_blobs(wt, sha, files), "hunk_hashes": resolution_hunk_hashes(wt, sha, files)}
    if replayed:
        resolved["replayed_files"] = replayed
    if is_main:
        state["assembly"].setdefault("main_merges", []).append({"merge": sha, "main": cur["main"], "resolved": resolved})
        state["assembly"]["head"] = sha
        state["verified"] = None
        state["ci"] = None           # land's CI record belongs to the head it read
    else:
        state["assembly"]["merged"].append({"n": cur["n"], "merge": sha, "resolved": resolved})
    state["assembly"]["cursor"] = None
    log(state, "merged %s -> %s after a hand resolution in %s (%s hunks); review round: %s"
        % (label, short(sha), ", ".join(files), resolved["hunks"], reviewed or "NOT RECORDED"))
    return is_main


def abort_resolution(root, wt, state):
    """Abandon the stopped merge: a member is held back (its owner told); the merge of origin/main is
    just dropped. Returns True when it was the merge of origin/main."""
    cur = state["assembly"].get("cursor")
    if not cur:
        raise Fail("nothing to abort: no member is stopped for resolution")
    if merge_in_progress(wt):
        git("merge", "--abort", cwd=wt)
    state["assembly"]["cursor"] = None
    if cur.get("main") is not None:
        log(state, "the merge of %s (%s) was abandoned; the batch stays at %s" % (remote_main(), short(cur["main"]), short(state["assembly"].get("head"))))
        return True
    m = members_by_n(state)[cur["n"]]
    against, earlier = conflict_attribution(root, state, m, cur["files"])
    hold_back(root, state, m, "conflicts with %s in %s (resolution abandoned)" % (against, ", ".join(cur["files"])),
              files=cur["files"], against=against, with_members=earlier, notify=not state["assembly"].get("no_notify"))
    return False


def merge_main(root, wt, state):
    """Merge origin/main into the assembled batch in its worktree, so a batch that fell behind main
    or into conflict with it catches up without a rebuild (verify allows a merge of main). Clean:
    recorded, and provenance checks it equals the clean merge. Conflict: stops for a hand resolution
    the way --resolve does (main cannot be held back); `--continue --reviewed` commits it under the
    subset rule and the body shows the diff from the clean merge. Returns False when stopped."""
    if not state["assembly"].get("head"):
        raise Fail("nothing assembled yet; run assemble first")
    if not (os.path.isdir(wt) and git_ok("rev-parse", "--is-inside-work-tree", cwd=wt)):
        raise Fail("no batch worktree at %s; run assemble first" % wt)
    main_sha = git("rev-parse", MAIN_REF, cwd=root)
    if is_ancestor(main_sha, "HEAD", wt):
        print("%s (%s) is already in %s" % (remote_main(), short(main_sha), branch_of(state["name"])))
        return True
    msg = "Merge %s into %s" % (remote_main(), branch_of(state["name"]))
    # --no-log, so git looks main's id up as no ref name and appends no shortlog (merge_member's comment)
    proc = run_git(["merge", *MERGE_STRATEGY, "--no-ff", "--no-edit", "--no-log", "-m", msg, main_sha], wt,
                   env={"GIT_MERGE_AUTOEDIT": "no"}, settings=merge_settings(state["name"]))
    resolved = None
    if proc.returncode == 0:
        sha = git("rev-parse", "HEAD", cwd=wt)
    elif not merge_in_progress(wt):
        raise Fail("git merge of %s failed without a conflict to resolve:\n%s%s" % (remote_main(), proc.stdout, proc.stderr))
    else:
        still = unmerged_paths(wt)
        _, _, would = merge_tree_of(git("rev-parse", "HEAD", cwd=wt), main_sha, wt)
        conflicted = sorted(set(still) | set(would or []))
        replayed = replayed_paths(wt, conflicted, still)
        refused_merge(wt, still, replayed, remote_main(), proc)
        if still:
            state["assembly"]["cursor"] = {"n": None, "main": main_sha, "files": conflicted, "replayed": replayed}
            log(state, "the merge of %s stopped for resolution in %s%s; resolve per hunk in %s, `git add` the files, then "
                       "`scripts/batch.py assemble %s --continue [--reviewed '<note>']` (or --abort)"
                % (remote_main(), ", ".join(conflicted),
                   (" (rerere replayed %s from the earlier assembly and staged it; the review covers the whole resolution)" % ", ".join(replayed)) if replayed else "",
                   wt, state["name"]))
            save_state(root, state)
            return False
        prior = prior_resolution(state, "main", replayed, wt)
        resolved = {"files": conflicted, "hunks": None, "replayed": True,
                    "how": "rerere replayed the resolution recorded in the earlier assembly" if prior else "rerere replayed a recorded resolution",
                    "review": prior["review"] if prior else None}
        sha, _ = commit_resolution(wt, conflicted)
        resolved["hunks"] = resolution_hunks(wt, sha, conflicted)
        resolved["choices"] = resolution_choices(wt, sha, conflicted, "the batch", remote_main())
        resolved["blobs"] = resolution_blobs(wt, sha, conflicted)
        resolved["hunk_hashes"] = resolution_hunk_hashes(wt, sha, conflicted)
    state["assembly"].setdefault("main_merges", []).append({"merge": sha, "main": main_sha, "resolved": resolved})
    state["assembly"]["head"] = sha
    state["verified"] = None
    state["ci"] = None
    log(state, "merged %s (%s) into %s -> %s%s" % (remote_main(), short(main_sha), branch_of(state["name"]), short(sha),
                                                   (" with " + resolved["how"]) if resolved else ""))
    save_state(root, state)
    return True


def run_assembly(root, state, resolve_set, resume):
    """Merge the pending members in order; stop at a --resolve member's conflict; hold the rest back."""
    wt = worktree_dir(root, state["name"])
    members = members_by_n(state)
    pending = list(state["assembly"]["pending"])
    satisfied = set(state["assembly"].get("satisfied") or [])
    while pending:
        n = pending[0]
        m = members[n]
        held_ns = {h["n"] for h in state["assembly"].get("held", [])}
        blockers = [d for d in m["depends_on"] if d in held_ns or (d in state["pulled"] and d not in satisfied)]
        if blockers:
            hold_back(root, state, m, "depends on %s (not in this batch)" % ", ".join("#%d" % d for d in blockers))
            pending.pop(0)
            state["assembly"]["pending"] = pending
            continue
        result = merge_member(root, wt, state, m, resolve_set)
        pending.pop(0)
        state["assembly"]["pending"] = pending
        if result == "stopped":
            save_state(root, state)
            return False
        save_state(root, state)
    state["assembly"]["head"] = git("rev-parse", "HEAD", cwd=wt)
    state["assembly"]["pending"] = []
    state["assembly"]["cursor"] = None
    state["verified"] = None
    state["ci"] = None
    log(state, "assembled %s at %s: %d merged, %d already contained, %d held back"
        % (branch_of(state["name"]), short(state["assembly"]["head"]), len(state["assembly"]["merged"]),
           len(state["assembly"].get("contained", [])), len(state["assembly"].get("held", []))))
    save_state(root, state)
    return True


def cmd_assemble(args):
    root = repo_root()
    state = load_state(root, args.name)
    refuse_equals_in_name(state["name"], planned=True)
    fetch(root, args.no_fetch)
    others = other_remote_batches(root, args.name)
    if others:
        raise Fail("another batch is open on %s: %s. One batch at a time; finish it (or delete its branch) first."
                   % (REMOTE, ", ".join(others)), code=2)
    wt = worktree_dir(root, args.name)
    if args.cont or args.abort:
        was_main = continue_after_resolution(root, wt, state, args.reviewed) if args.cont else abort_resolution(root, wt, state)
        save_state(root, state)
        if was_main:
            return
        if not run_assembly(root, state, set(args.resolve or []), resume=True):
            raise Fail("stopped at #%d for a hand resolution (see above)" % state["assembly"]["cursor"]["n"], code=3)
        return
    if os.path.isdir(wt) and git_ok("rev-parse", "--is-inside-work-tree", cwd=wt) and merge_in_progress(wt) \
            and state["assembly"].get("cursor"):
        cur = state["assembly"]["cursor"]
        raise Fail("%s is stopped for resolution in %s; finish with --continue or drop it with --abort"
                   % (merge_label(cur.get("n")), wt))
    if args.merge_main:
        if args.without or args.repin or args.resolve:
            raise Fail("--merge-main merges %s into the assembled batch and takes no other option" % remote_main(), code=2)
        if not merge_main(root, wt, state):
            raise Fail("stopped at the merge of %s for a hand resolution (see above)" % remote_main(), code=3)
        return
    members = members_by_n(state)
    sweep = sweep_reader() if args.repin else None
    for n in args.repin or []:
        targets = list(members) if n == "all" else [int(n)]
        for k in targets:
            if k not in members:
                raise Fail("#%d is not a member of %s" % (k, args.name))
            pr = gh_json("pr", "view", str(k), "--json", "headRefOid,title,body,labels,baseRefName", cwd=root)
            # The re-read head is taken in like plan's: it owes a passing sweep of its own. Refused before anything
            # is re-pinned or rebuilt (nothing is saved until the assembly runs).
            why, record = member_sweep(root, sweep, dict(members[k], head=pr["headRefOid"]))
            if why:
                raise Fail("#%d's head %s has no passing sweep of its own (%s); nothing re-pinned" % (k, short(pr["headRefOid"]), why))
            old = members[k]["head"]
            members[k]["head"] = pr["headRefOid"]
            members[k]["sweep"] = record
            members[k]["title"] = pr["title"]
            members[k]["labels"] = label_names(pr)
            members[k]["tier"] = tier_of(members[k]["labels"])
            members[k]["trailer"], members[k]["trailer_error"] = parse_trailer(pr.get("body"))
            if pr.get("baseRefName") and pr["baseRefName"] != members[k]["base_ref"]:
                log(state, "re-pinned #%d: base %s -> %s" % (k, members[k]["base_ref"], pr["baseRefName"]))
                members[k]["base_ref"] = pr["baseRefName"]
            ensure_object(root, pr["headRefOid"], members[k]["head_ref"])
            mb = git("merge-base", MAIN_REF, pr["headRefOid"], cwd=root)
            members[k]["touches"] = git("diff", "--name-only", mb, pr["headRefOid"], cwd=root).split()
            state["members"][str(k)] = members[k]
            log(state, "re-pinned #%d: %s -> %s" % (k, short(old), short(pr["headRefOid"])))
    for n in args.without or []:
        if n not in members:
            raise Fail("#%d is not a member of %s" % (n, args.name))
        if n not in state["pulled"]:
            state["pulled"].append(n)
    # A pulled member's dependents go with it, unless the member is already in origin/main (it merged
    # alone): then the dependency is satisfied by the new base and the dependents stay.
    dropped, satisfied = [], []
    for n in list(state["pulled"]):
        if is_ancestor(members[n]["head"], MAIN_REF, root):
            satisfied.append(n)
            continue
        for d in dependents_of(state, n):
            if d not in state["pulled"]:
                state["pulled"].append(d)
                dropped.append((d, n))
    state["pulled"].sort()
    prepare_worktree(root, args.name)
    state["base"] = git("rev-parse", MAIN_REF, cwd=root)
    old_log = state["assembly"].get("log", [])
    # Resolutions the earlier assemblies recorded, so a rerere replay of the same conflict keeps its review.
    prev = dict(state["assembly"].get("previous_resolutions") or {})
    for e in state["assembly"].get("merged", []):
        if e.get("resolved"):
            prev[str(e["n"])] = e["resolved"]
    for e in state["assembly"].get("main_merges", []):
        if e.get("resolved"):
            prev["main"] = e["resolved"]
    state["assembly"] = {"log": old_log, "merged": [], "contained": [], "held": [], "main_merges": [], "declared": [],
                         "previous_resolutions": prev, "satisfied": satisfied,
                         "pending": [n for n in state["order"] if n not in state["pulled"]],
                         "cursor": None, "head": None, "no_notify": bool(args.no_notify)}
    log(state, "assembling %s from %s at %s; pulled: %s" % (branch_of(args.name), remote_main(), short(state["base"]),
                                                            ", ".join("#%d" % n for n in state["pulled"]) or "none"))
    for n in satisfied:
        log(state, "#%d is pulled but already in %s; its dependents stay in the batch" % (n, remote_main()))
    for d, n in dropped:
        log(state, "#%d dropped with #%d (depends on it)" % (d, n))
    if not run_assembly(root, state, set(args.resolve or []), resume=False):
        raise Fail("stopped at #%d for a hand resolution (see above)" % state["assembly"]["cursor"]["n"], code=3)


def in_batch(state):
    """The members the batch lands, in plan order: the merged records and the already-contained
    ones (a contained member has no merge commit; its head is reachable through an earlier member's)."""
    order = state["order"]
    recs = list(state["assembly"].get("merged", [])) + list(state["assembly"].get("contained", []))
    return sorted(recs, key=lambda e: order.index(e["n"]) if e["n"] in order else len(order))


# ── verify ───────────────────────────────────────────────────────────────────

def parents_of(sha, cwd):
    return git("rev-list", "--parents", "-n", "1", sha, cwd=cwd).split()[1:]


def subject_of(sha, cwd):
    return git("log", "-n", "1", "--format=%s", sha, cwd=cwd)


def is_ancestor(a, b, cwd):
    return git_ok("merge-base", "--is-ancestor", a, b, cwd=cwd)


def merge_tree_of(p1, p2, cwd):
    """The tree `git merge-tree --write-tree` produces for p1 and p2, and the paths it reports as
    conflicted: (tree, "clean", []) or (tree, "conflicts", paths) with the conflict markers left in
    the conflicted files. (None, "unsupported", None) when this git lacks `merge-tree --write-tree`
    (added in git 2.38). The markers are labeled with the identifiers given, so two callers get the
    same tree for the same merge only when both name the parents the same way: pass SHAs."""
    proc = git_proc("merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", p1, p2, cwd=cwd, check=False)
    fields = proc.stdout.split("\0")
    if proc.returncode in (0, 1) and fields and fields[0].strip():
        if proc.returncode == 0:
            return fields[0].strip(), "clean", []
        paths = []
        for f in fields[1:]:
            if not f:
                break
            paths.append(f)
        return fields[0].strip(), "conflicts", paths
    return None, "unsupported", None


def paths_off_clean_merge(p1, p2, tree, cwd):
    """The paths in `tree` that differ from what git makes of p1 and p2 by itself: the conflicted
    files a resolution had to touch, plus anything else a hand put into the merge. (paths, kind,
    conflicted) with kind "clean" or "conflicts" and the paths merge-tree calls conflicted, or
    (None, "unsupported", None)."""
    mt, kind, conflicted = merge_tree_of(p1, p2, cwd)
    if mt is None:
        return None, kind, None
    return git("diff-tree", "--name-only", "-r", mt, tree, cwd=cwd).split(), kind, conflicted


def stray_resolution_paths(files, paths):
    """The paths a resolution changed that it had no business changing. A resolution may touch its
    conflicted files, and entry files under upstream/ when UPSTREAM.md was among them (a row
    conversion writes entries); every other path is a change the body would never show."""
    allowed = set(files)
    return sorted(p for p in paths
                  if p not in allowed and not (UPSTREAM_MD in allowed and p.startswith("upstream/")))


def merge_label(rec_n):
    return "#%d" % rec_n if rec_n is not None else "the merge of %s" % remote_main()


def check_merge_tree(rec, label, c, p1, p2, root, lines):
    """One first-parent merge against the merge git would make of its parents by itself. Equal: fine.
    Different with a recorded resolution: the differing paths must be the resolution's (the subset
    rule, so a stray staged file cannot ride inside a resolved merge unseen). Different without one:
    an unrecorded resolution or an edit hidden in the merge. When the parents' own merge conflicts,
    every path merge-tree calls conflicted must be covered by the recorded resolution and hold no
    conflict marker in the merge: a conflicted file kept as merge-tree wrote it (markers, or the
    modified side of a modify/delete) does not differ from that tree, so the comparison alone would
    read it as the clean merge. Returns ok."""
    merge_tree = git("rev-parse", c + "^{tree}", cwd=root)
    paths, kind, conflicted = paths_off_clean_merge(p1, p2, merge_tree, root)
    if paths is None:
        lines.append("FAIL provenance: this git cannot check %s's merge tree (needs git 2.38)" % label)
        return False
    resolved = (rec or {}).get("resolved")
    if kind == "conflicts":
        if not resolved:
            lines.append("FAIL provenance: %s merge %s resolved a conflict that is not recorded (in %s)"
                         % (label, short(c), ", ".join(conflicted)))
            return False
        uncovered = [p for p in conflicted if p not in resolved["files"]]
        if uncovered:
            lines.append("FAIL provenance: %s merge %s resolved a conflict in %s that its recorded resolution (%s) does not cover"
                         % (label, short(c), ", ".join(uncovered), ", ".join(resolved["files"])))
            return False
        marked = marker_paths(merge_tree, conflicted, root)
        if marked:
            lines.append("FAIL provenance: %s merge %s carries a conflict marker in %s" % (label, short(c), ", ".join(marked)))
            return False
    if not paths and kind == "clean":
        lines.append("ok   provenance: %s merge %s equals the clean merge of its parents" % (label, short(c)))
        return True
    if resolved:
        stray = stray_resolution_paths(resolved["files"], paths)
        if stray:
            lines.append("FAIL provenance: %s merge %s changes %s outside its recorded resolution (%s)"
                         % (label, short(c), ", ".join(stray), ", ".join(resolved["files"])))
            return False
        lines.append("ok   provenance: %s merge carries a recorded resolution (%s) in %s" % (label, resolved["how"], ", ".join(paths or conflicted)))
        return True
    lines.append("FAIL provenance: %s merge %s differs from the clean merge of its parents (undeclared change in %s)" % (label, short(c), ", ".join(paths)))
    return False


def declared_commit_record(sha, cwd):
    """What the body says about a `batch:` commit: its subject, files and shortstat."""
    stat = [l.strip() for l in git("show", "--shortstat", "--format=", sha, cwd=cwd).splitlines() if l.strip()]
    return {"sha": sha, "subject": subject_of(sha, cwd),
            "files": git("diff-tree", "--no-commit-id", "--name-only", "-r", sha, cwd=cwd).split(),
            "stat": stat[-1] if stat else ""}


def check_provenance(root, state, lines):
    """(a) Every non-merge commit the batch adds is a declared `batch:` commit, and the first-parent
    chain since main is exactly the member merges plus declared commits and merges of origin/main.
    Every merge on the chain, a member's or main's, must equal the clean merge of its parents unless
    it carries a recorded resolution, and then it may differ only in the resolution's files: an edit
    slipped into a merge commit is otherwise invisible to `rev-list --no-merges`. A member recorded
    as already contained must be reachable from the tip."""
    ok = True
    br, bref = branch_of(state["name"]), batch_ref(state["name"])
    merged = state["assembly"].get("merged", [])
    main_merges = {e["merge"]: e for e in state["assembly"].get("main_merges", [])}
    members = members_by_n(state)
    heads = {members[e["n"]]["head"]: e["n"] for e in merged}
    excl = ["^" + MAIN_REF] + ["^" + h for h in heads]
    stray = git("rev-list", bref, *excl, "--no-merges", cwd=root).split()
    undeclared = [s for s in stray if not subject_of(s, root).startswith("batch:")]
    declared = [s for s in stray if subject_of(s, root).startswith("batch:")]
    if undeclared:
        ok = False
        for s in undeclared:
            lines.append("FAIL provenance: undeclared commit %s (%s); commit batch changes with a `batch:` subject" % (short(s), subject_of(s, root)))
    chain = git("rev-list", "--first-parent", "--reverse", "%s..%s" % (MAIN_REF, bref), cwd=root).split()
    member_merges = 0
    for c in chain:
        ps = parents_of(c, root)
        if len(ps) == 1:
            if c not in declared:
                ok = False
                lines.append("FAIL provenance: %s on the first-parent chain is not a `batch:` commit" % short(c))
            continue
        if len(ps) != 2:
            ok = False
            lines.append("FAIL provenance: %s is an octopus merge" % short(c))
            continue
        p1, p2 = ps
        if p2 in heads:
            member_merges += 1
            n = heads[p2]
            rec = next(e for e in merged if e["n"] == n)
            if rec["merge"] != c:
                ok = False
                lines.append("FAIL provenance: #%d's merge on the chain is %s, recorded %s" % (n, short(c), short(rec["merge"])))
            ok = check_merge_tree(rec, "#%d" % n, c, p1, p2, root, lines) and ok
        elif is_ancestor(p2, MAIN_REF, root):
            ok = check_merge_tree(main_merges.get(c), "the %s" % remote_main(), c, p1, p2, root, lines) and ok
        else:
            ok = False
            lines.append("FAIL provenance: %s merges %s, which is neither a member head nor %s" % (short(c), short(p2), remote_main()))
    if member_merges != len(merged):
        ok = False
        lines.append("FAIL provenance: %d member merges on the chain, %d recorded" % (member_merges, len(merged)))
    for e in state["assembly"].get("contained", []):
        if not is_ancestor(members[e["n"]]["head"], bref, root):
            ok = False
            lines.append("FAIL provenance: #%d is recorded as already contained (by %s) but its head %s is not in %s"
                         % (e["n"], e["contained_by"], short(members[e["n"]]["head"]), br))
    state["assembly"]["declared"] = [declared_commit_record(s, root) for s in declared]
    if ok:
        lines.append("ok   provenance: %d member merge(s), %d declared batch: commit(s), nothing else" % (member_merges, len(declared)))
    return ok


def ledger_check_on_branch(root, br):
    """`scripts/upstream-ledger.py check` on the BRANCH's tree (`br`, its full ref), in a temporary detached worktree, so
    the verdict is the branch's and not some directory's (the batch worktree may be gone or dirty).
    None when the branch carries no ledger script (pre-migration); else the completed process."""
    if not git_ok("cat-file", "-e", "%s:%s" % (br, LEDGER_SCRIPT), cwd=root):
        return None
    holder = tempfile.mkdtemp(prefix="romp-batch-ledger-")
    tree = os.path.join(holder, "tree")
    try:
        git("worktree", "add", "--quiet", "--detach", tree, br, cwd=root)
        return run_tool([sys.executable, LEDGER_SCRIPT, "check"], tree)
    finally:
        # -f twice: a registration a killed worktree add left locked is removed too, where one --force refuses it
        _cleanup_steps(lambda: git("worktree", "remove", "-f", "-f", tree, cwd=root, check=False),
                       lambda: shutil.rmtree(holder, ignore_errors=True))


def sweep_reader():
    """scripts/sweep.py, loaded from beside this file: its reader (assess) is the one place the result's
    path, its leg roster and the verdict rule live, so the runner and verify cannot disagree about them."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sweep.py")
    if not os.path.exists(path):
        raise Fail("scripts/sweep.py is missing beside batch.py (%s); verify reads sweep results through it, and every git "
                   "call reads its limits from it (git_limits)" % path)
    spec = importlib.util.spec_from_file_location("romp_batch_sweep_reader", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # The module's run_git starts its git under this tool's stop hold, not its own (the closing check wf_fb19febe-36b, its
    # item 4(b)): this tool's handlers, not the module's, are the ones installed, and they hold a stop only while this
    # module's hold is on, so with the module's own a stop raised inside the git's start and the git ran on. Both names
    # are read at the call, so the module's run_git holds and releases here and raises this tool's Stopped inside the try
    # that ends the git.
    mod._hold_stops, mod._release_stops = _hold_stops, _release_stops
    return mod


def remote_ref_sha(root, ref):
    """The sha of exactly `ref` on origin now, or None. `git ls-remote <remote> <pattern>` matches the
    pattern against the tail of every ref name, so a branch named aaa/refs/heads/main answers
    refs/heads/main too (and sorts first); only the line naming `ref` itself counts."""
    for line in git("ls-remote", REMOTE, ref, cwd=root).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0]
    return None


def main_on_origin(root):
    """main's head on origin now, read with ls-remote (never the tracking ref, which --no-fetch or a
    stale fetch leaves behind); None when origin has no main."""
    return remote_ref_sha(root, "refs/heads/" + MAIN)


def check_contains_main(root, name, head, lines):
    """The batch head must contain main as origin has it NOW. ci.yml does not run on the merge to main: a
    batch lands with a merge commit whose tree is the batch head's only when main is already in the
    head, and that tree is the one the sweep and the batch branch's CI ran on. Returns the main sha it
    compared with when the head contains it, else None."""
    live = main_on_origin(root)
    if not live:
        lines.append("FAIL behind: %s has no %s branch to compare the batch head with" % (REMOTE, MAIN))
        return None
    if is_ancestor(live, head, root):
        lines.append("ok   main: %s at %s is in the batch head" % (remote_main(), short(live)))
        return live
    known = git_ok("cat-file", "-e", live + "^{commit}", cwd=root)
    lines.append("FAIL behind: %s is at %s%s, which the batch head %s does not contain, so the tree that would land is not "
                 "the tree the sweep and CI ran on; `scripts/batch.py assemble %s --merge-main`, then sweep and verify again"
                 % (remote_main(), short(live), "" if known else " (not fetched here)", short(head), name))
    return None


def excuse_contradiction(root, sweep, result, head, subject="the batch head"):
    """Round 1's excuse rule, read against the head's tree: scripts/sweep.py's excuse_contradiction, which its own
    check applies too, so check prints what verify reads. Its git call is sweep.py's, bounded by that script's
    GIT_BOUND, GIT_MEMORY and GIT_OUTPUT_MAX in the repository its find_repo reads at `root`; a refusal there
    (sweep.py's Refused, its GitBound included) is a Fail naming it."""
    try:
        return sweep.excuse_contradiction(root, result, head, subject=subject)
    except sweep.Refused as e:
        raise Fail("the sweep result's excuse rule could not be read: %s" % e)


def sweep_record(sweep, a, head):
    """The pass a reader read (`a`, from assess), as the state records it: verify's state['sweep'] for the batch head
    and each member's 'sweep' for its own head. The head, the result's path and finish, each leg's rc or "not owed",
    the runner's display summaries, the failed runs the history excused with a known flake, and its invalid runs with
    the legs each failed."""
    legs = a["result"]["legs"]
    return {"head": head, "path": a["path"], "verdict": "pass", "finished": a["result"].get("finished"),
            "legs": [[n, legs[n].get("rc") if sweep.is_owed(n, legs[n]) else "not owed"] for n in sweep.LEGS],
            "summary": {n: legs[n]["summary"] for n in sweep.LEGS if sweep.is_owed(n, legs[n]) and legs[n].get("summary")},
            # the result's whole history as the reader read it: each failed run a later run's known flake excused, and
            # each invalid run with the legs it failed, whose failures count (one that failed no leg needs no flake, but
            # it is named)
            "reruns": list(a["result"].get("flake_notes") or []),
            "invalid_runs": list(a["result"].get("invalid_notes") or [])}


def member_sweep(root, sweep, m):
    """A member PR owes a passing sweep of its own head before its review round and before its closing check
    (docs/batching.md), so the steps that take a member in (plan, assemble --repin) read it. Returns (fault, record):
    (None, the pass as sweep_record has it) when the result at the member's pinned head is a pass (every leg owed, the
    webview legs, pdf-smoke and the served leg included, as at a batch head: the reader refuses one of them marked not owed for
    any reason but a missing extension, and the ledger for any reason but a missing ledger script) and any leg it marks
    not owed for a missing vscode-extension/package.json or ledger script is one the head's tree lacks, else (the reader's line naming the case, None). The caller records the pass on the member, and the
    body's members table shows that record (round 1, fresh-3). The result is read from this machine's state dir; one
    recorded on another machine is missing here."""
    subject = "#%d's head" % m["n"]
    a = sweep.assess(m["head"], subject=subject, branch=m["head_ref"])
    if a["case"] != "pass":
        return a["line"], None
    ensure_object(root, m["head"], m["head_ref"])
    fault = excuse_contradiction(root, sweep, a["result"], m["head"], subject=subject)
    return (fault, None) if fault else (None, sweep_record(sweep, a, m["head"]))


def cmd_verify(args, quiet=False):
    root = repo_root()
    state = load_state(root, args.name)
    sweep = sweep_reader()
    # The earlier verdict is cleared first: a verify that dies half-way (a gh error) must not leave
    # a green verification behind for summarize to publish.
    if state.get("verified") or state.get("ci"):
        state["verified"] = None
        state["ci"] = None            # and land's CI record, which belongs to the head a verify read
        save_state(root, state)
    fetch(root, args.no_fetch)
    lines, ok = [], True
    br = branch_of(args.name)
    if not git_ok("rev-parse", "--verify", "--quiet", batch_ref(args.name), cwd=root):
        raise Fail("%s does not exist; run assemble first" % br)
    head = git("rev-parse", batch_ref(args.name), cwd=root)
    if state["assembly"].get("cursor"):
        raise Fail("%s is still stopped for resolution; --continue or --abort first" % merge_label(state["assembly"]["cursor"].get("n")))
    pending = state["assembly"].get("pending") or []
    if pending or not state["assembly"].get("head"):
        raise Fail("assembly incomplete: %s never merged; run assemble again"
                   % (", ".join("#%d" % n for n in pending) or "the last assembly did not finish, so the members"))
    if state["assembly"].get("head") != head:
        # A `batch:` commit the batcher added after assembly moves the tip; provenance below decides
        # whether what moved it is allowed. The recorded head follows the branch.
        lines.append("note head: %s moved from %s to %s since assembly; the chain is checked below"
                     % (br, short(state["assembly"].get("head")), short(head)))
        state["assembly"]["head"] = head
    ok = check_provenance(root, state, lines) and ok
    members = members_by_n(state)
    landing = in_batch(state)
    in_batch_refs = {members[e["n"]]["head_ref"] for e in landing}
    for e in landing:
        m = members[e["n"]]
        pr = gh_json("pr", "view", str(m["n"]), "--json", "headRefOid,state,baseRefName,isDraft", cwd=root)
        if pr["headRefOid"] != m["head"]:
            ok = False
            lines.append("FAIL head moved: #%d pinned %s, now %s (assemble --repin %d, then re-assemble)"
                         % (m["n"], short(m["head"]), short(pr["headRefOid"]), m["n"]))
        else:
            lines.append("ok   head: #%d at %s%s" % (m["n"], short(m["head"]),
                                                    (" (already contained by %s, no merge of its own)" % e["contained_by"]) if e.get("contained_by") else ""))
        if pr.get("state") != "OPEN":
            ok = False
            lines.append("FAIL state: #%d is %s (pull it; the rebuild starts from the current %s, which carries whatever merged alone)"
                         % (m["n"], pr.get("state"), remote_main()))
        if pr.get("baseRefName") != MAIN:
            b = pr.get("baseRefName")
            if b in in_batch_refs:
                lines.append("ok   base: #%d is based on %s, which is in the batch (land retargets it to %s before the merge)" % (m["n"], b, MAIN))
            elif git_ok("rev-parse", "--verify", "--quiet", remote_ref(b), cwd=root) and is_ancestor(remote_ref(b), MAIN_REF, root):
                lines.append("ok   base: #%d is based on %s, already in %s" % (m["n"], b, MAIN))
            else:
                ok = False
                lines.append("FAIL base: #%d is based on %s, which is neither in the batch nor in %s" % (m["n"], b, MAIN))
        state["members"][str(m["n"])] = m
    proc = ledger_check_on_branch(root, batch_ref(args.name))
    if proc is None:
        lines.append("note ledger: %s is not on %s (pre-migration); not checked" % (LEDGER_SCRIPT, br))
        state["ledger"] = "pre-migration"
    elif proc.returncode == 0:
        lines.append("ok   ledger: check clean")
        state["ledger"] = "clean"
    else:
        ok = False
        lines.append("FAIL ledger: %s" % (proc.stdout + proc.stderr).strip()[:500])
        state["ledger"] = "failed"
    main_seen = check_contains_main(root, args.name, head, lines)
    ok = bool(main_seen) and ok
    # The sweep result the runner wrote for this exact sha (scripts/sweep.py), read through its own reader;
    # every case but a pass names itself (missing, stale, unfinished, red, invalid, incomplete, unreadable).
    a = sweep.assess(head, subject="the batch head", branch=br, tree_hint=worktree_dir(root, args.name))
    contradiction = None
    if a["case"] == "pass":
        contradiction = excuse_contradiction(root, sweep, a["result"], head)
    if contradiction:
        ok = False
        state["sweep"] = None
        lines.append("FAIL " + contradiction)
    elif a["case"] == "pass":
        state["sweep"] = sweep_record(sweep, a, head)
        lines.append("ok   " + a["line"])
    else:
        ok = False
        state["sweep"] = None
        lines.append("FAIL " + a["line"])
    state["verified"] = {"head": head, "at": now(), "ok": ok, "lines": lines, "main": main_seen}
    save_state(root, state)
    if not quiet:
        print("\n".join(lines))
        print("verify %s: %s at %s" % (args.name, "OK" if ok else "FAILED", short(head)))
    if not ok:
        raise Fail("verify failed")
    return state


# ── summarize (the body) ─────────────────────────────────────────────────────

def _cell(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def member_sweep_cell(m):
    """The members table's "Sweep at own head" cell: the pass plan (or assemble --repin) read at the member's pinned
    head and recorded on the member (member_sweep), never the author's trailer, whose sweep fields are self-reported
    and may name another sha (round 1, fresh-3); the trailer still gives the Rounds column. A member recorded by a plan
    from before this record existed, or one whose record is for another head, renders "not recorded"."""
    rec = m.get("sweep")
    if not (isinstance(rec, dict) and rec.get("verdict") == "pass" and isinstance(rec.get("legs"), list)):
        return "not recorded"
    if rec.get("head") != m.get("head"):
        return "not recorded (the pass read was at %s, the pinned head is %s)" % (short(rec.get("head")), short(m.get("head")))
    return "pass @%s: %s" % (short(rec["head"]), pass_legs_phrase(rec))


def resolution_reason(resolved):
    """The "Read these first" phrase for a recorded resolution."""
    note = resolved.get("review")
    rev = ("one review round: %s" % note) if note and note != "mechanical" else (
        "mechanical" if note == "mechanical" else "review round NOT recorded")
    if resolved.get("replayed") and note and note != "mechanical":
        rev = "one review round in the earlier assembly, replayed by rerere: %s" % note
    hunks, files, choices = resolved.get("hunks"), resolved["files"], resolved.get("choices") or {}
    # A side taken wholesale is said in words ("took #108's version"); the hunk count alone hid it
    # (and read 0 when the kept file is what merge-tree left, as in a modify/delete).
    parts = [("%s: %s" % (f, choices[f])) if len(files) > 1 else choices[f] for f in files if choices.get(f)]
    if hunks is None and not parts:
        parts.append(resolved["how"])
    elif hunks or not parts:
        parts.append("%d hunk%s" % (hunks, "" if hunks == 1 else "s"))
    return "conflict resolved in %s (%s); %s. [diff from the clean merge below]" % (", ".join(files), "; ".join(parts), rev)


def read_first_reasons(m, resolved, contained_by=None):
    """The computed rule: a member is listed under "Read these first" when its merge needed a
    resolution, when it was already contained by an earlier member (no merge of its own, so a
    missing `Depends-on`), when its tier is `feature` or unlabeled, when it touches kernel/,
    .github/, .githooks/, install.sh or uninstall.sh, or when its trailer is missing. A member PR
    runs no ci.yml of its own (the sweep at the batch head gates it), so there is no CI reason."""
    reasons = []
    if resolved:
        reasons.append(resolution_reason(resolved))
    if contained_by:
        reasons.append("already contained by %s: no merge commit of its own (add `Depends-on` or reorder next time)" % contained_by)
    if m.get("tier") is None:
        reasons.append("unlabeled")
    elif m["tier"] == "feature":
        reasons.append("feature")
    sens = sensitive_paths(m.get("touches") or [])
    if sens:
        reasons.append("touches " + ", ".join(sens))
    if m.get("trailer") is None:
        reasons.append("trailer not stated" if not m.get("trailer_error") else m["trailer_error"])
    return reasons


def sweep_phrase(sw):
    """The first block's words for the sweep verify read: every owed leg with its rc (and the runner's
    display summary), then the legs not owed, then any leg re-run after a known flake, with its first
    failure and the flake, then any invalid run in the result's history, with the legs it failed. A record
    from before the result file (free text passed to verify) is shown as it was written."""
    if not sw:
        return "sweep not recorded"
    if sw.get("verdict") == "pass" and isinstance(sw.get("legs"), list):
        return "sweep pass: " + pass_legs_phrase(sw)
    return sw.get("text") or "sweep not recorded"


def pass_legs_phrase(sw):
    """A recorded pass's legs in words (sweep_record's shape): every owed leg with its rc and the runner's display
    summary, the legs not owed, each failed run a known flake excused, and each invalid run with the legs it failed."""
    summary = sw.get("summary") or {}
    ran = ["%s rc %s%s" % (n, rc, (" (%s)" % summary[n]) if summary.get(n) else "") for n, rc in sw["legs"] if rc != "not owed"]
    skipped = [n for n, rc in sw["legs"] if rc == "not owed"]
    notes = list(sw.get("reruns") or []) + ["an earlier " + t for t in sw.get("invalid_runs") or []]
    return "%s%s%s" % (", ".join(ran), ("; not owed: " + ", ".join(skipped)) if skipped else "",
                       ("; " + "; ".join(notes)) if notes else "")


def land_line(name):
    """The body's first words: how this batch lands, and what `land` checks that the button and `gh pr merge` do not:
    main read again right before the merge (round 1, extra7-4: it states the check, not that the merged tree is
    always the batch head's; a move between that read and GitHub's merge is finish's loud report)."""
    return ("Land with `scripts/batch.py land %s`: it reads main again right before the merge and refuses if the batch "
            "head no longer contains it." % name)


def gather_body_inputs(root, state):
    """Everything the body needs that comes from git: resolution diffs and the ledger entry table.
    A resolution's diff runs from the merge-tree of the parents to the merge and covers EVERY path
    that differs from it (the recorded files and anything else), so what the maintainer reads is the
    whole difference; per path, whose version was taken when one side won outright."""
    br = batch_ref(state["name"])
    members = members_by_n(state)
    resolutions = []
    # The merge shown is the one ON THE BRANCH for that second parent (a merge amended after the
    # record was written is what the maintainer would land), the recorded sha as the fallback.
    on_chain = {}
    if git_ok("rev-parse", "--verify", "--quiet", br, cwd=root):
        for c in git("rev-list", "--first-parent", "%s..%s" % (MAIN_REF, br), cwd=root).split():
            ps = parents_of(c, root)
            if len(ps) == 2:
                on_chain.setdefault(ps[1], c)
    recs = [(e["n"], members[e["n"]]["head"], e) for e in state["assembly"].get("merged", [])] + \
           [(None, e.get("main"), e) for e in state["assembly"].get("main_merges", [])]
    for n, p2, e in recs:
        if not e.get("resolved"):
            continue
        merge = on_chain.get(p2, e["merge"])
        paths = list(e["resolved"]["files"])
        ps = parents_of(merge, root)
        if len(ps) == 2:
            off, _, _ = paths_off_clean_merge(ps[0], ps[1], merge + "^{tree}", root)
            paths = sorted(set(paths) | set(off or []))
        out = resolution_diff(root, merge, paths)
        if out is None:
            out = "(this git cannot compute the clean merge of the parents; needs git 2.38)"
        choices = resolution_choices(root, merge, paths, "the batch", ("#%d" % n) if n is not None else remote_main())
        resolutions.append({"n": n, "merge": merge, "diff": out, "choices": choices})
    entries = []
    if git_ok("rev-parse", "--verify", "--quiet", br, cwd=root):
        mb = git("merge-base", MAIN_REF, br, cwd=root)
        for line in git("diff", "--name-status", mb, br, "--", "upstream/", cwd=root).splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status, path = parts[0][0], parts[-1]
            title, st = "", ""
            if status != "D":
                text = git_proc("show", "%s:%s" % (br, path), cwd=root, check=False).stdout
                hdr = {}
                if text.startswith("---"):
                    for l in text.split("\n")[1:]:
                        if l.strip() == "---":
                            break
                        if ":" in l:
                            k, v = l.split(":", 1)
                            hdr[k.strip()] = v.strip()
                title, st = hdr.get("title", ""), hdr.get("status", "")
            who = [n for n, m in members.items() if path in (m.get("touches") or [])]
            entries.append({"path": path, "title": title, "status": st,
                            "change": {"A": "added", "M": "modified", "D": "deleted"}.get(status, status),
                            "members": who})
    return {"resolutions": resolutions, "entries": entries}


def _largest_fitting(lo, hi, fits):
    """The largest n in [lo, hi] with fits(n), assuming fits is monotone (True below some point);
    lo is assumed to fit."""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def render_body(state, inputs, cap=BODY_CAP):
    """The batch PR body. Pure over its inputs so the cap rule is testable. The members table, the
    first block, "Read these first", "Held back" and the trailer are never cut. When the body would
    exceed the cap the rest is fitted to the budget in priority order, each block keeping as much as
    fits: the ledger entries table (else a count), then the conflict resolutions (up to
    RESOLUTION_LINES per merge; the diff from the clean merge is what the maintainer reads), then the
    assembly log (its newest lines). A body still over the cap with all of that gone is refused with
    the advice to split the batch."""
    name = state["name"]
    members = members_by_n(state)
    merged = state["assembly"].get("merged", [])
    contained = state["assembly"].get("contained", [])
    landing = in_batch(state)
    held = state["assembly"].get("held", [])
    pulled = state.get("pulled", [])
    declared = state["assembly"].get("declared") or []
    main_merges = state["assembly"].get("main_merges") or []
    resolved_by_n = {e["n"]: e.get("resolved") for e in merged}
    contained_by = {e["n"]: e["contained_by"] for e in contained}
    v = state.get("verified") or {}
    sw = state.get("sweep") or {}
    head = state["assembly"].get("head") or ""
    extra = []
    if held:
        extra.append("%d held back" % len(held))
    if pulled:
        extra.append("%d pulled" % len(pulled))
    title = "# Batch %s: %d PR%s%s" % (name, len(landing), "" if len(landing) == 1 else "s", (" (%s)" % ", ".join(extra)) if extra else "")
    if v.get("ok") and v.get("head") == head:
        ledger = {"clean": "ledger check clean", "pre-migration": "ledger: pre-migration, not checked", "failed": "ledger check FAILED"}.get(state.get("ledger"), "ledger: not checked")
        # The main verify saw, named: "contained" is true at verify time only, and a merge by the button or
        # `gh pr merge` after main moved lands a tree no sweep or ci.yml run tested (none runs on main).
        seen = short(v["main"]) if v.get("main") else "its head then"
        # Round 1, extra7-5: that the push run's checks show on the batch PR's head is an expectation the first batch
        # confirms (docs/batching.md, "Checked on the first batch"), so the body says so rather than stating it.
        verified = ("%s Verified at %s: %s; provenance clean; main at %s contained at verify time; %s. CI on this PR: the run "
                    "of the push to %s, expected among the checks on its head (the first batch confirms that). No ci.yml "
                    "run follows the merge to main, so if main has moved past %s, do not merge with the button or `gh pr merge`: the "
                    "batch needs main merged in, a new sweep and verify first."
                    % (land_line(name), short(head), sweep_phrase(sw), seen, ledger, branch_of(name), seen))
    else:
        verified = "%s NOT VERIFIED at %s: run `scripts/batch.py verify %s` (verification is %s)." % (
            land_line(name), short(head), name, "stale" if v else "missing")

    read_first = []
    for e in landing:
        m = members[e["n"]]
        reasons = read_first_reasons(m, resolved_by_n.get(e["n"]), contained_by.get(e["n"]))
        if reasons:
            read_first.append("- #%d %s: %s." % (m["n"], m["head_ref"], "; ".join(reasons).rstrip(".")))
    for e in main_merges:
        if e.get("resolved"):
            read_first.append("- merge of %s (%s): %s." % (remote_main(), short(e["merge"]), resolution_reason(e["resolved"]).rstrip(".")))
    for d in declared:
        read_first.append("- `batch:` commit %s by the batcher: %s; %s%s." % (
            short(d["sha"]), d["subject"], d.get("stat") or "no diffstat",
            ("; touches " + ", ".join(d["files"])) if d.get("files") else ""))
    read_first_block = "\n".join(read_first) if read_first else \
        "- none: every member is labeled, carries a trailer, touches no sensitive path and merged clean; the batch adds no commit of its own."

    rows = ["| # | Title | Tier | Rounds | Sweep at own head | Flags | Ledger |",
            "|---|---|---|---|---|---|---|"]
    entries = inputs.get("entries") or []
    for e in landing:
        m = members[e["n"]]
        t = m.get("trailer") or {}
        flags = []
        if resolved_by_n.get(e["n"]):
            flags.append("resolved")
        if contained_by.get(e["n"]):
            flags.append("contained by %s" % contained_by[e["n"]])
        if m.get("tier") is None:
            flags.append("unlabeled")
        flags += sensitive_paths(m.get("touches") or [])
        if m.get("trailer") is None:
            flags.append("no trailer")
        ledger_n = sum(1 for x in entries if e["n"] in x["members"])
        rows.append("| #%d | %s | %s | %s | %s | %s | %s |" % (
            m["n"], _cell(m["title"]), _cell(m.get("tier") or "unlabeled"),
            _cell(t.get("rounds", "not stated")) if t else "not stated",
            _cell(member_sweep_cell(m)),
            _cell(", ".join(flags) or "-"), ("+%d" % ledger_n) if ledger_n else "-"))
    members_table = "\n".join(rows)

    def entries_table(full):
        if not entries:
            return "(none)"
        if not full:
            return "(%d entries; table omitted to stay under the body cap; see `git diff %s...%s -- upstream/`)" % (len(entries), remote_main(), branch_of(name))
        out = ["| Entry | Title | Status | Change | Member |", "|---|---|---|---|---|"]
        for x in entries:
            out.append("| `%s` | %s | %s | %s | %s |" % (x["path"], _cell(x["title"]), _cell(x["status"]), x["change"],
                                                       ", ".join("#%d" % n for n in x["members"]) or "-"))
        return "\n".join(out)

    held_lines = []
    for h in held:
        if h.get("files"):
            told = h.get("told")
            owner = "owner told" if told else ("owner NOT told (%s)" % h.get("told_why", "comment failed") if told is False else "owner not told")
            held_lines.append("- #%d: %s; %s." % (h["n"], h["reason"].rstrip("."), owner))
        else:
            held_lines.append("- #%d: %s." % (h["n"], h["reason"].rstrip(".")))
    for n in pulled:
        held_lines.append("- #%d: pulled; the PR stays open against %s." % (n, MAIN))
    held_block = "\n".join(held_lines) if held_lines else "- none"

    def resolutions_block(budget_lines):
        parts = []
        for r in inputs.get("resolutions") or []:
            lines = r["diff"].splitlines()
            cut = lines[:min(budget_lines, RESOLUTION_LINES)]
            more = len(lines) - len(cut)
            heading = ("### #%d" % r["n"]) if r.get("n") is not None else "### merge of %s (%s)" % (remote_main(), short(r.get("merge")))
            notes = "".join("- %s: %s\n" % (p, why) for p, why in sorted((r.get("choices") or {}).items()))
            block = ("```diff\n%s\n```%s" % ("\n".join(cut), ("\n(%d more lines)" % more) if more > 0 else "")) if lines \
                else "(no diff: the merge keeps these paths as git left them in the conflicted tree)"
            parts.append("%s\n\n%s%s%s" % (heading, notes, "\n" if notes else "", block))
        return "\n\n".join(parts) if parts else "(none)"

    log_all = state["assembly"].get("log") or []

    def log_block(budget_lines):
        cut = log_all[-budget_lines:] if budget_lines else []
        more = len(log_all) - len(cut)
        return ("(%d earlier lines omitted)\n" % more if more > 0 else "") + "\n".join(cut) if cut else "(omitted)"

    trailer = "<!-- romp-batch: %s -->" % json.dumps({
        "name": name, "base": state.get("base"),
        "members": [{"n": e["n"], "head": members[e["n"]]["head"]} for e in landing]}, separators=(",", ":"))

    def assemble(res_lines, log_lines, full_entries):
        return "\n".join([
            title, verified, "",
            "## Read these first", read_first_block, "",
            "## Members, in merge order", members_table, "",
            "## Upstream entries this batch adds or changes (%d)" % len(entries), entries_table(full_entries), "",
            "## Held back", held_block, "",
            "## To pull a member",
            "Comment `pull #N`. The batch is rebuilt without it; the PR stays open against %s." % MAIN, "",
            "<details><summary>Conflict resolutions</summary>\n\n%s\n\n</details>" % resolutions_block(res_lines),
            "<details><summary>Assembly log</summary>\n\n```\n%s\n```\n\n</details>" % log_block(log_lines),
            trailer, ""])

    res_max = min(RESOLUTION_LINES, max([len(r["diff"].splitlines()) for r in inputs.get("resolutions") or []] or [0]))
    log_max = len(log_all)
    body = assemble(res_max, log_max, True)
    if len(body) <= cap:
        return body
    full_entries = len(assemble(0, 0, True)) <= cap
    if len(assemble(0, 0, full_entries)) > cap:
        raise Fail("the body is %d characters with every detail cut; GitHub caps it at %d. Split the batch (two a day beat one of twenty)."
                   % (len(assemble(0, 0, full_entries)), cap))
    res_lines = _largest_fitting(0, res_max, lambda k: len(assemble(k, 0, full_entries)) <= cap)
    log_lines = _largest_fitting(0, log_max, lambda k: len(assemble(res_lines, k, full_entries)) <= cap)
    body = assemble(res_lines, log_lines, full_entries)
    while len(body) > cap and (res_lines or log_lines):
        # The "(N more lines)" notes make the size not quite monotone; back off a line at a time.
        if log_lines:
            log_lines -= 1
        else:
            res_lines -= 1
        body = assemble(res_lines, log_lines, full_entries)
    if len(body) > cap:
        raise Fail("the body is %d characters with every detail cut; GitHub caps it at %d. Split the batch (two a day beat one of twenty)."
                   % (len(body), cap))
    return body


def find_batch_pr(root, state):
    if state.get("pr") and state["pr"].get("number"):
        return state["pr"]["number"]
    # --state all: after the maintainer clicks merge, the PR is no longer open, and finish must
    # still find it when summarize never recorded it (a PR opened by hand).
    rows = gh_json("pr", "list", "--state", "all", "--head", branch_of(state["name"]), "--json", "number,url", "--limit", "5", cwd=root)
    if rows:
        state["pr"] = {"number": rows[0]["number"], "url": rows[0].get("url")}
        return rows[0]["number"]
    return None


def comment_or_report(root, state, n, text, what):
    """Post a comment on #n and say so when it fails, instead of assuming it landed. Returns ok."""
    proc = gh("pr", "comment", str(n), "--body", text, cwd=root, check=False)
    if proc.returncode == 0:
        return True
    err = [l for l in (proc.stderr or proc.stdout).strip().splitlines() if l.strip()]
    log(state, "#%d: gh pr comment failed (%s) for %s; tell the owner by postal: %s" % (n, err[-1] if err else "exit %d" % proc.returncode, what, text))
    return False


def cmd_summarize(args):
    root = repo_root()
    state = load_state(root, args.name)
    if not state["assembly"].get("head"):
        raise Fail("nothing assembled yet")
    body = render_body(state, gather_body_inputs(root, state))
    if args.print_only:
        print(body)
        return
    b = find_batch_pr(root, state)
    n_members = len(in_batch(state))
    title = "Batch %s: %d PR%s" % (args.name, n_members, "" if n_members == 1 else "s")
    if b:
        _run([gh_bin(), "pr", "edit", str(b), "--title", title, "--body-file", "-"], cwd=root, input_text=body)
        print("updated batch PR #%d" % b)
    else:
        proc = _run([gh_bin(), "pr", "create", "--base", MAIN, "--head", branch_of(args.name), "--title", title,
                     "--label", LABEL_BATCH, "--body-file", "-"], cwd=root, input_text=body)
        url = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        try:
            b = int(url.rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            rows = gh_json("pr", "list", "--state", "open", "--head", branch_of(args.name), "--json", "number,url", "--limit", "5", cwd=root)
            if not rows:
                raise Fail("gh pr create printed no PR URL and the PR is not listed: %r" % url)
            b, url = rows[0]["number"], rows[0].get("url")
        state["pr"] = {"number": b, "url": url}
        print("opened batch PR #%d %s" % (b, url))
    head = state["assembly"]["head"]
    for e in in_batch(state):
        key = str(e["n"])
        if state["commented"].get(key) == head:
            continue
        gh("pr", "comment", key, "--body", "in batch %s at %s" % (args.name, head), cwd=root)
        state["commented"][key] = head
    save_state(root, state)


# ── pull, land, finish, bisect ───────────────────────────────────────────────

def push_batch(root, state, force):
    # the branch by its full ref (MAIN_REF's comment), which pushes it to the same name on origin and sets it as the
    # branch's upstream, as its short name did
    args = ["push", "--quiet", "-u", REMOTE, batch_ref(state["name"])]
    if force:
        args.insert(2, "--force-with-lease")
    git(*args, cwd=root)


def cmd_pull(args):
    root = repo_root()
    state = load_state(root, args.name)
    members = members_by_n(state)
    if args.n not in members:
        raise Fail("#%d is not a member of %s" % (args.n, args.name))
    before = set(state["pulled"])
    ns = argparse.Namespace(name=args.name, without=[args.n], resolve=[], repin=[], cont=False, abort=False,
                            reviewed=None, no_fetch=args.no_fetch, no_notify=args.no_notify, merge_main=False)
    cmd_assemble(ns)
    state = load_state(root, args.name)
    dropped = sorted(set(state["pulled"]) - before - {args.n})
    if args.no_push:
        print("pulled #%d%s; not pushed (--no-push)" % (args.n, (", dropped with it: " + ", ".join("#%d" % d for d in dropped)) if dropped else ""))
        return
    push_batch(root, state, force=True)
    cmd_summarize(argparse.Namespace(name=args.name, print_only=False))
    state = load_state(root, args.name)
    reason = args.reason or "the maintainer asked"
    text = "Pulled from batch %s (%s). This PR stays open against %s and is not in that batch." % (args.name, reason, MAIN)
    if not args.no_notify:
        comment_or_report(root, state, args.n, text, "the pull")
        for d in dropped:
            comment_or_report(root, state, d, "Dropped from batch %s with #%d, which it depends on. It stays open against %s."
                              % (args.name, args.n, MAIN), "the drop")
        save_state(root, state)
    print("pulled #%d%s; pushed and re-summarized" % (args.n, (", dropped with it: " + ", ".join("#%d" % d for d in dropped)) if dropped else ""))


def repo_settings(root):
    return gh_json("repo", "view", "--json", "mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,deleteBranchOnMerge", cwd=root) or {}


def auto_merge_allowed(root):
    """The repository's "Allow auto-merge" setting (REST `allow_auto_merge`; off on the fork at
    writing): GitHub refuses `--auto` on a PR until it is on. True, False, or None when unreadable."""
    proc = gh("api", "repos/{owner}/{repo}", cwd=root, check=False)
    if proc.returncode != 0:
        return None
    try:
        v = json.loads(proc.stdout or "{}").get("allow_auto_merge")
    except (json.JSONDecodeError, AttributeError):
        return None
    return v if isinstance(v, bool) else None


# Ruleset rule types that make a merge wait for something. The rest (non_fast_forward, deletion,
# creation, update, ...) protect the ref and gate no merge, so --auto would merge at once.
GATING_RULE_TYPES = ("required_status_checks", "pull_request", "required_deployments", "merge_queue", "code_scanning")
# The classic branch-protection settings that gate a merge, and how the go-ahead names them.
GATING_PROTECTION = {"required_status_checks": "status checks", "required_pull_request_reviews": "reviews"}


def main_protection(root):
    """What on main gates a merge, as (gating, found). `gating` names it, or is None when nothing
    does: ruleset rules of a type in GATING_RULE_TYPES, read from the rules that apply to the branch
    (`rules/branches/main`, not the repository-wide rulesets list, which counts tag and push rulesets
    too; the endpoint lists the protective rules as well, so the types are read, not counted), or
    classic branch protection with required status checks or required reviews. `found` says what was
    there instead, for the refusal. A rules read that fails, or a protection read that fails with
    anything but a 404 (GitHub's answer for an unprotected branch), raises Fail with gh's error: a
    failed read is not "none". `gh pr merge --auto` is only useful with a gating rule: with nothing
    required, auto-merge merges at once. This detects, it never assumes (scripts/land.sh runs land, so
    the same gate)."""
    proc = gh("api", "repos/{owner}/{repo}/rules/branches/%s" % MAIN, cwd=root, check=False)
    if proc.returncode != 0:
        raise Fail("--auto, and could not read the rules on %s: %s" % (MAIN, (proc.stderr + proc.stdout).strip()))
    try:
        rows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        raise Fail("--auto, and could not read the rules on %s: not JSON (%s)" % (MAIN, e))
    types = [str(r.get("type") or "?") for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    gating = [t for t in types if t in GATING_RULE_TYPES]
    other = [t for t in types if t not in GATING_RULE_TYPES]
    proc = gh("api", "repos/{owner}/{repo}/branches/%s/protection" % MAIN, cwd=root, check=False)
    protected, prot_set, prot_gating = False, [], []
    if proc.returncode == 0:
        try:
            body = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError as e:
            raise Fail("--auto, and could not read %s's branch protection: not JSON (%s)" % (MAIN, e))
        protected = True
        prot_set = sorted(k for k, v in body.items() if v is not None) if isinstance(body, dict) else []
        prot_gating = [k for k in GATING_PROTECTION if k in prot_set]
    elif "HTTP 404" not in proc.stderr + proc.stdout:
        raise Fail("--auto, and could not read %s's branch protection: %s" % (MAIN, (proc.stderr + proc.stdout).strip()))
    if gating or prot_gating:
        parts = []
        if gating:
            parts.append("rules on %s gate a merge (%s)" % (MAIN, ", ".join(gating)))
        if prot_gating:
            parts.append("classic branch protection on %s requires %s" % (MAIN, " and ".join(GATING_PROTECTION[k] for k in prot_gating)))
        return ", and ".join(parts), None
    found = [("ruleset rules %s, which protect the branch and gate no merge" % ", ".join(other)) if other
             else "no rules apply to %s" % MAIN]
    found.append(("branch protection on %s requires no checks and no reviews (set: %s)" % (MAIN, ", ".join(prot_set) or "nothing"))
                 if protected else "it has no classic protection")
    return None, ", and ".join(found)


# A run's createdAt as gh prints it (RFC 3339: a date, T, a time with an optional fraction, then Z or an offset).
_RFC3339 = re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|([+-])(\d{2}):(\d{2}))")
# A creation time before this is a placeholder, not a run's: gh renders a time GitHub did not give as the zero time
# 0001-01-01T00:00:00Z, and the Unix epoch is the other conventional zero; both would sort oldest.
RUN_TIME_FLOOR = _dt.datetime(2000, 1, 1, tzinfo=_dt.timezone.utc)


def run_time(value):
    """(a run's createdAt as an aware datetime, None), or (None, why it is not a time GitHub set): not a string or not
    RFC 3339, RFC 3339 in form but not a real date or time (a February 30th), or before RUN_TIME_FLOOR (the zero time
    among them)."""
    m = _RFC3339.fullmatch(value) if isinstance(value, str) else None
    if m is None:
        return None, "not an RFC 3339 time"
    y, mo, d, h, mi, s, frac, _tz, sign, oh, om = m.groups()
    try:
        off = _dt.timedelta(hours=int(oh), minutes=int(om)) * (-1 if sign == "-" else 1) if sign else _dt.timedelta(0)
        t = _dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s), int((frac or "0")[:6].ljust(6, "0")),
                         tzinfo=_dt.timezone(off))
    except ValueError:
        return None, "RFC 3339 in form but not a real date and time"
    if t < RUN_TIME_FLOOR:
        return None, ("a placeholder before %d (the zero time 0001-01-01T00:00:00Z is one), not a time GitHub set"
                      % RUN_TIME_FLOOR.year)
    return t, None


def run_created(value):
    """A run's createdAt as an aware datetime, or None when it is not a time GitHub set (run_time says why)."""
    return run_time(value)[0]


def run_row_fault(row):
    """Why a matching `gh run list` row cannot be ordered among the others, or None: its databaseId is not a positive
    integer, its createdAt is not a time GitHub set (run_time), or its attempt is not a positive integer. The newest run decides, and a row that cannot be
    placed by time and id would decide by accident, so it is refused rather than guessed at."""
    rid = row.get("databaseId")
    if "databaseId" not in row or rid is None:
        return "no databaseId"
    if type(rid) is not int or rid <= 0:
        return "databaseId %r, not a positive integer" % (rid,)
    created = row.get("createdAt")
    if "createdAt" not in row or created is None:
        return "no createdAt"
    when, why = run_time(created)
    if when is None:
        return "createdAt %r, %s" % (created, why)
    attempt = row.get("attempt")
    if "attempt" not in row or attempt is None:
        return "no attempt"
    if type(attempt) is not int or attempt <= 0:
        return "attempt %r, not a positive integer" % (attempt,)
    return None


def run_attempts(root, run):
    """[(n, record)] for each earlier attempt of `run` (1 to its attempt - 1), read from GitHub now with
    `gh api repos/{owner}/{repo}/actions/runs/<id>/attempts/<n>`. A read that fails, one that is not JSON, or a record
    that is not that run's attempt n (its id and run_attempt) raises Fail: an attempt not read is not one that passed."""
    out = []
    for n in range(1, run["attempt"]):
        what = "attempt %d of the batch head's CI run %s" % (n, run.get("url"))
        proc = gh("api", "repos/{owner}/{repo}/actions/runs/%d/attempts/%d" % (run["databaseId"], n), cwd=root, check=False)
        if proc.returncode != 0:
            raise Fail("could not read %s (gh api): %s; nothing merged" % (what, (proc.stderr + proc.stdout).strip()))
        try:
            rec = json.loads(proc.stdout or "")
        except json.JSONDecodeError as e:
            raise Fail("%s read as something that is not JSON (%s); nothing merged" % (what, e))
        rid, num = (rec.get("id"), rec.get("run_attempt")) if isinstance(rec, dict) else (None, None)
        if not (type(rid) is int and rid == run["databaseId"] and type(num) is int and num == n):
            raise Fail("%s read as another record (id %r, run_attempt %r); nothing merged" % (what, rid, num))
        out.append((n, rec))
    return out


def attempt_passed(rec):
    return rec.get("status") == "completed" and rec.get("conclusion") == "success"


def parse_ci_flakes(values):
    """{(run id, attempt): known-flake entry} from land's --flake RUN/ATTEMPT=TEXT values; a malformed value or one
    naming an attempt twice is a usage refusal."""
    out = {}
    for v in values or []:
        key, sep, text = v.partition("=")
        m = re.fullmatch(r"(\d+)/(\d+)", key.strip())
        if not (sep and m and text.strip()):
            raise Fail("--flake %r: expected RUN/ATTEMPT=TEXT, the run id and the failed attempt as land's refusal names them, "
                       "then the failing test and where it is recorded as a known flake" % v, code=2)
        k = (int(m.group(1)), int(m.group(2)))
        if k in out:
            raise Fail("--flake names run %d attempt %d twice" % k, code=2)
        out[k] = text.strip()
    return out


def ci_attempt_gate(root, run, older, flakes):
    """Round 1, decision 13: a red is not erased by a re-run, locally or on GitHub. Every attempt of a push run at the
    head but the newest run's latest is read: the newest run's earlier attempts (run_attempts), and each older matching
    push run at the same head (`older`, from batch_ci_run: the same sha pushed again, after the branch was deleted and
    pushed back or pushed elsewhere and back), its latest attempt from its row and its earlier ones read like the newest
    run's. One that did not pass (any status or conclusion but completed and success, cancelled included) is refused
    unless land's --flake names it (RUN/ATTEMPT=TEXT), as a --leg re-run needs --flake naming the failed leg. A known
    flake is excused once across every run at the head, as the local sweep's is: two attempts that did not pass are
    refused whatever --flake says. A --flake that names no failed attempt of a run at the head is refused. Returns the
    excused attempts, [{"run", "attempt", "status", "conclusion", "url", "flake"}], which land records in the state and
    finish reports."""
    rid = run["databaseId"]
    failed = [(rid, n, rec, "attempt %d" % n) for n, rec in run_attempts(root, run) if not attempt_passed(rec)]
    for o in older:
        latest = {"status": o.get("status"), "conclusion": o.get("conclusion"), "html_url": o.get("url")}
        for n, rec in run_attempts(root, o) + [(o["attempt"], latest)]:
            if not attempt_passed(rec):
                failed.append((o["databaseId"], n, rec, "an earlier run at this head, %s, attempt %d," % (o.get("url"), n)))
    keys = {(r, n) for r, n, _rec, _what in failed}
    stray = sorted(k for k in flakes if k not in keys)
    if stray:
        raise Fail("--flake names %s, which %s no failed attempt of a run at the batch head (its CI run %s, attempt %d, run "
                   "%d%s); nothing merged" % (", ".join("run %d attempt %d" % k for k in stray), "is" if len(stray) == 1 else "are",
                                              run.get("url"), run["attempt"], rid,
                                              "".join(", and run %d" % o["databaseId"] for o in older)))

    def said(what, rec):
        return "%s concluded %s (%s)" % (what, rec.get("conclusion") or "nothing, status %s" % rec.get("status"),
                                         rec.get("html_url") or run.get("url"))
    if len(failed) > 1:
        raise Fail("the batch head's CI run %s is green on attempt %d, but %s; a known flake is excused once, as the local "
                   "sweep's is, so this head cannot land: fix it and push a new head; nothing merged"
                   % (run.get("url"), run["attempt"], " and ".join(said(what, rec) for _r, _n, rec, what in failed)))
    for r, n, rec, what in failed:
        if (r, n) not in flakes:
            raise Fail("the batch head's CI run %s is green on attempt %d, but %s, and a red is not erased by a re-run: if that "
                       "attempt failed on a known flake, land again with --flake %d/%d='<the failing test, and where it is "
                       "recorded as a known flake>'; otherwise fix it and push a new head; nothing merged"
                       % (run.get("url"), run["attempt"], said(what, rec), r, n))
    return [{"run": r, "attempt": n, "status": rec.get("status"), "conclusion": rec.get("conclusion"),
             "url": rec.get("html_url") or run.get("url"), "flake": flakes[(r, n)]} for r, n, rec, _what in failed]


# The rows land asks gh for. A read that returns this many may have cut the older runs at the head, which the attempt
# gate must read, so it is refused rather than read short.
RUN_LIST_LIMIT = 20
# Round 2, the coordinator's decision 18: a run is read green only when its jobs are ci.yml's. Its conclusion alone reads
# success from a run whose jobs never ran (a skipped job reports success), and a read of the checks on a head (the
# per-PR read this landing gate replaced) reads success from the label checks alone. So the jobs of the run's latest
# attempt are read, and every job of ci.yml at the head must have a job run there that concluded success, told by the
# name GitHub renders for it (ci_jobs).
CI_WORKFLOW_PATH = ".github/workflows/" + CI_WORKFLOW
JOBS_PER_PAGE = 100
_EXPRESSION = re.compile(r"\$\{\{.*?\}\}")


def ci_jobs(root, head, tail):
    """[(job id, the name GitHub renders for it as ci.yml writes it, a regex that matches that rendering)] for every job
    of ci.yml at `head`, read from git with scripts/sweep.py's line reader (workflow_jobs, workflow_job). A job's name
    is its `name:` value, quotes and a trailing comment off, or its id when it has none; each `${{ ... }}` in it matches
    any text, and a job with a strategy: whose name holds none matches with or without the ` (<matrix values>)` GitHub
    appends. Raises Fail (a read that cannot be made is not a green run) when the file cannot be read at the head, holds
    no job, or a name is written in a form this reads no further (a block scalar, an empty value)."""
    sweep = sweep_reader()
    proc = git_proc("show", "%s:%s" % (head, CI_WORKFLOW_PATH), cwd=root, check=False)
    if proc.returncode != 0:
        raise Fail("could not read %s at %s to read which jobs the batch head's CI run must hold (%s)%s"
                   % (CI_WORKFLOW_PATH, short(head), (proc.stderr or proc.stdout).strip(), tail))
    text, where = proc.stdout, "%s at %s" % (CI_WORKFLOW_PATH, short(head))
    out = []
    try:
        for job in sweep.workflow_jobs(text):
            spec = sweep.workflow_job(text, job, where)
            raw = spec["values"].get("name")
            name = job if raw is None else raw
            if raw is not None:
                if name[:1] in "\"'" and name[-1:] == name[:1] and len(name) > 1:
                    name = name[1:-1]
                elif " #" in name:
                    name = name.split(" #", 1)[0].rstrip()
            if not name or name[:1] in "|>":
                raise Fail("%s names its %s job %r, a form this read does not take (a quoted or plain one-line name); the CI "
                           "read tells the run's job runs by name%s" % (where, job, raw, tail))
            parts = _EXPRESSION.split(name)
            pattern = ".*".join(re.escape(x) for x in parts)
            if len(parts) == 1 and "strategy" in spec["keys"]:
                pattern += r"(?: \(.*\))?"
            out.append((job, name, re.compile(pattern)))
    except sweep.Refused as e:
        raise Fail("%s%s" % (e, tail))
    if not out:
        raise Fail("%s holds no job, so no CI run of it tested the batch head%s" % (where, tail))
    return out


def run_jobs(root, run, tail):
    """[{"name", "status", "conclusion"}] of every job of `run`'s latest attempt, read from GitHub now with `gh api
    repos/{owner}/{repo}/actions/runs/<id>/attempts/<attempt>/jobs`. A read that fails, an answer that is not a jobs
    listing, a job that is not a record, or a listing shorter than its total_count (cut) raises Fail: a job not read is
    not one that passed."""
    what = "the jobs of the batch head's CI run %s (attempt %d)" % (run.get("url"), run["attempt"])
    proc = gh("api", "repos/{owner}/{repo}/actions/runs/%d/attempts/%d/jobs?per_page=%d"
              % (run["databaseId"], run["attempt"], JOBS_PER_PAGE), cwd=root, check=False)
    if proc.returncode != 0:
        raise Fail("could not read %s (gh api): %s%s" % (what, (proc.stderr + proc.stdout).strip(), tail))
    try:
        doc = json.loads(proc.stdout or "")
    except json.JSONDecodeError as e:
        raise Fail("%s read as something that is not JSON (%s)%s" % (what, e, tail))
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    total = doc.get("total_count") if isinstance(doc, dict) else None
    if not isinstance(jobs, list) or type(total) is not int or any(not isinstance(j, dict) for j in jobs):
        raise Fail("%s read as something that is not a jobs listing (%s)%s" % (what, json.dumps(doc)[:120], tail))
    if total > len(jobs):
        raise Fail("%s listed %d of %d jobs, so the rest may be cut%s" % (what, len(jobs), total, tail))
    return [{"name": j.get("name"), "status": j.get("status"), "conclusion": j.get("conclusion")} for j in jobs]


def unmet_ci_jobs(expected, jobs):
    """The (job id, name) of each job of ci.yml (ci_jobs) that no job run of `jobs` (run_jobs) matches by name with the
    conclusion success."""
    return [(job, name) for job, name, rx in expected
            if not any(isinstance(j["name"], str) and rx.fullmatch(j["name"]) and j["conclusion"] == "success" for j in jobs)]


def batch_ci_run(root, name, head, tail="; nothing merged"):
    """The batch head's one GitHub run, read from GitHub now: the newest run of ci.yml that a push to
    batch/<name> started at exactly `head`. Returns (case, run, older): case is green (completed, success, and ci.yml's jobs
    passed in it), incomplete (completed, success, but a job of ci.yml has no passing job run there), pending (not
    completed), red (completed with any other conclusion) or missing (no such run; run None); older is every other
    matching run, newest first, which land's attempt gate reads (a red is not erased by pushing the same sha again). gh's
    filters are asked for and then checked on every row (the workflow by its name), so a run of another
    sha, event, branch or workflow never stands in for it. The newest is the latest createdAt, then the highest
    databaseId, whatever order gh lists the rows in; a matching row with no valid databaseId, createdAt (the zero time
    included) or attempt raises Fail naming it (round 1, extra4-4), and so does a list as long as RUN_LIST_LIMIT, which
    may have cut older runs. A run that concluded success is green only when every job of ci.yml at `head` has a job run
    in its latest attempt that concluded success (the coordinator's decision 18: ci_jobs, run_jobs); otherwise the case is
    incomplete, with the run's `jobs` and `jobs_unmet` (the jobs of ci.yml with none) in the run it returns. A read that fails raises Fail with gh's error: a failed read is not a missing run. So does
    an answer that is not a JSON list of run records (round 2, extra8-3): nothing at all, JSON of another type (an error
    object, a string, null), or a list holding a row that is not an object; only an empty list is no run. `tail`
    ends each Fail's text: land's says nothing merged, and finish, which reads the same run after the merge, passes its
    own."""
    br = branch_of(name)
    proc = gh("run", "list", "--workflow", CI_WORKFLOW, "--branch", br, "--event", "push", "--commit", head, "--limit",
              str(RUN_LIST_LIMIT), "--json", CI_RUN_FIELDS, cwd=root, check=False)
    if proc.returncode != 0:
        raise Fail("could not read the batch head's CI run (gh run list): %s%s" % ((proc.stderr + proc.stdout).strip(), tail))
    if not proc.stdout.strip():
        raise Fail("gh run list returned nothing, not a JSON list of runs; a read that returns no run records is not a "
                   "missing run%s" % tail)
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise Fail("gh run list returned something that is not JSON (%s)%s" % (e, tail))
    if not isinstance(rows, list):
        raise Fail("gh run list returned JSON that is not a list of runs (%s: %s); a read that returns no run records is "
                   "not a missing run%s" % (type(rows).__name__, json.dumps(rows)[:120], tail))
    stray = [r for r in rows if not isinstance(r, dict)]
    if stray:
        raise Fail("gh run list returned %d row%s that %s not a run record (%s); a read that returns no run records is "
                   "not a missing run%s" % (len(stray), "" if len(stray) == 1 else "s", "is" if len(stray) == 1 else "are",
                                           json.dumps(stray[0])[:120], tail))
    if len(rows) >= RUN_LIST_LIMIT:
        raise Fail("gh run list returned %d rows, its limit, so older runs at the batch head may be cut, and every run at "
                   "the head is read (a red is not erased by pushing the same sha again)%s" % (len(rows), tail))
    runs = [r for r in rows if r.get("headSha") == head
            and r.get("event") == "push" and r.get("headBranch") == br and r.get("workflowName") == CI_WORKFLOW_NAME]
    if not runs:
        return "missing", None, []
    for r in runs:
        fault = run_row_fault(r)
        if fault:
            raise Fail("the batch head's CI run cannot be chosen: gh run list gave a matching run (%s) with %s; the newest run "
                       "decides, and a row that cannot be ordered by time and id is refused, not guessed at%s"
                       % (r.get("url") or "no url", fault, tail))
    ordered = sorted(runs, key=lambda r: (run_created(r["createdAt"]), r["databaseId"]), reverse=True)
    run, older = ordered[0], ordered[1:]
    if run.get("status") != "completed":
        return "pending", run, older
    if run.get("conclusion") != "success":
        return "red", run, older
    # decision 18: a success is read only over ci.yml's jobs, each with a passing job run in the run's latest attempt
    jobs = run_jobs(root, run, tail)
    unmet = unmet_ci_jobs(ci_jobs(root, head, tail), jobs)
    run = dict(run, jobs=jobs, jobs_unmet=unmet)
    if unmet:
        return "incomplete", run, older
    return "green", run, older


def jobs_text(unmet):
    """ci.yml's jobs a run lacks, for a message: `the python job (Python ${{ ... }})` for each."""
    return ", ".join("the %s job (%s)" % (job, name) if name != job else "the %s job" % job for job, name in unmet)


def run_jobs_text(jobs):
    """A run's job runs, for a message: each name and conclusion, or that it lists none."""
    return ("its job runs: " + "; ".join("%s: %s" % (j["name"], j["conclusion"] or j["status"]) for j in jobs)
            if jobs else "it lists no job run")


def retarget_stacked_members(root, state):
    """A member based on another member's branch is retargeted to main right before the merge.

    GitHub marks a PR merged when its head becomes reachable from ITS BASE. The batch merges into
    main, so a member whose base is a sibling branch would stay open (its base never moves) even
    though its content is in main. Against main, the documented indirect-merge rule applies to it
    like every other member. Done here and not at plan time so the member keeps its stacked diff
    and review until the moment it lands. Returns [(n, old base)] for each member retargeted, so a
    refusal after it can name what it changed on GitHub."""
    members = members_by_n(state)
    landing = in_batch(state)
    in_batch_refs = {members[e["n"]]["head_ref"] for e in landing}
    done = []
    for e in landing:
        m = members[e["n"]]
        if m["base_ref"] != MAIN and m["base_ref"] in in_batch_refs:
            gh("pr", "edit", str(m["n"]), "--base", MAIN, cwd=root)
            log(state, "retargeted #%d from %s to %s before the merge, so the indirect merge marks it" % (m["n"], m["base_ref"], MAIN))
            done.append((m["n"], m["base_ref"]))
            m["base_ref"] = MAIN
            state["members"][str(m["n"])] = m
    save_state(root, state)
    return done


def cmd_land(args):
    root = repo_root()
    flakes = parse_ci_flakes(args.flake)
    state = cmd_verify(argparse.Namespace(name=args.name, no_fetch=args.no_fetch), quiet=False)
    b = find_batch_pr(root, state)
    if not b:
        raise Fail("no open batch PR for %s; run summarize first" % branch_of(args.name))
    settings = repo_settings(root)
    if settings.get("mergeCommitAllowed") is False:
        raise Fail("the repository does not allow merge commits; a batch must land as one (repo settings)")
    for k in ("squashMergeAllowed", "rebaseMergeAllowed"):
        if settings.get(k):
            print("warning: %s is on; a squash or rebase of a batch leaves every member open" % k)
    head = state["verified"]["head"]
    br = branch_of(args.name)
    remote_head = remote_ref_sha(root, "refs/heads/" + br)
    if remote_head != head:
        raise Fail("%s on %s is at %s, verified %s; push the batch first" % (br, REMOTE, short(remote_head) if remote_head else "nothing", short(head)))
    # The one GitHub run per batch, required green as well as the local sweep: ci.yml's run of the push to the batch
    # branch at the verified head, read from GitHub here and now, before anything is changed (--auto does not wait
    # for it either: auto-merge waits only for what a rule on main requires).
    case, run, older = batch_ci_run(root, args.name, head)
    if case == "missing":
        raise Fail("the batch head's CI run is missing: GitHub lists no run of %s from a push to %s at %s; push the batch "
                   "and wait for its run, then land again; nothing merged" % (CI_WORKFLOW, br, head))
    if case == "pending":
        raise Fail("the batch head's CI run is pending (status %s): %s; wait for it to finish, then land again; nothing merged"
                   % (run.get("status"), run.get("url")))
    if case == "red":
        raise Fail("the batch head's CI run is red (conclusion %s): %s; `scripts/batch.py bisect %s -- <failing test>` names "
                   "the member to pull; nothing merged" % (run.get("conclusion"), run.get("url"), args.name))
    if case == "incomplete":
        raise Fail("the batch head's CI run %s concluded success, but %s at the head has %s with no job run that passed "
                   "in it (%s); a success is read only over ci.yml's own jobs, so this run did not test the head: push the "
                   "batch again and wait for its run, then land again; nothing merged"
                   % (run.get("url"), CI_WORKFLOW_PATH, jobs_text(run["jobs_unmet"]), run_jobs_text(run["jobs"])))
    excused = ci_attempt_gate(root, run, older, flakes)
    state["ci"] = {"run": run.get("url"), "id": run["databaseId"], "attempt": run["attempt"], "head": head, "excused": excused}
    save_state(root, state)
    print("ok   CI: the run of the push to %s at %s is green: %s%s" % (
        br, short(head), run.get("url"), "".join("; %sattempt %d concluded %s and is excused as a known flake (%s): %s"
                                                 % ("" if e["run"] == run["databaseId"] else "an earlier run's ", e["attempt"],
                                                    e["conclusion"] or e["status"], e["url"], e["flake"]) for e in excused)))
    cmd = ["pr", "merge", str(b), "--merge", "--match-head-commit", head]
    if args.auto:
        # Both preconditions are read, never assumed (scripts/land.sh runs this land, so it has them too), and
        # before anything is changed: GitHub refuses auto-merge until the repository setting is on,
        # and with nothing required on main --auto merges at once and protects nothing.
        allowed = auto_merge_allowed(root)
        if allowed is not True:
            raise Fail("--auto needs the repository's \"Allow auto-merge\" setting, which is %s (REST allow_auto_merge). "
                       "Turning it on is the maintainer's call: `gh repo edit --enable-auto-merge`. Merge without --auto instead."
                       % ("off" if allowed is False else "unreadable"))
        gating, found = main_protection(root)
        if not gating:
            raise Fail("--auto needs a ruleset or branch protection on %s that gates a merge (read from GitHub: %s); "
                       "with nothing required, auto-merge merges at once and protects nothing. Merge without --auto." % (MAIN, found))
        print("merging with --auto: auto-merge is allowed and %s" % gating)
        cmd.append("--auto")
    # main may have moved since verify read it (a merge by hand). It is read twice more: once here, before anything on
    # GitHub is changed, so a move already made refuses with nothing changed (round 1, correctness-6), and once right
    # before the merge call, so the tree that lands is still the batch head's. GitHub's merge pins the head
    # (--match-head-commit), not the base, so the gap left is the one between that last read and the call; finish
    # reports it loudly when the merge commit's first parent is not the main verify read (pre-round item 4).
    seen = state["verified"].get("main")

    def moved_text(now_sha):
        return "%s moved on %s to %s after verify read %s; nothing merged" % (MAIN, REMOTE, short(now_sha) if now_sha else "nothing",
                                                                          short(seen))
    again = "Run land again: its verify reads the new %s and says whether the batch still contains it" % MAIN
    main_now = main_on_origin(root)
    if main_now != seen:
        raise Fail("%s, and nothing on GitHub was changed. %s" % (moved_text(main_now), again))
    retargeted = retarget_stacked_members(root, state)
    main_now = main_on_origin(root)
    if main_now != seen:
        if not retargeted:
            raise Fail("%s. %s" % (moved_text(main_now), again))
        # The members are based on main on GitHub now; the state takes back their old bases, so the next land
        # retargets them again, whether or not they are restored by hand first.
        members = members_by_n(state)
        for n, old in retargeted:
            members[n]["base_ref"] = old
            state["members"][str(n)] = members[n]
        log(state, "land refused after retargeting %s: %s moved; the state keeps the old base%s"
            % (", ".join("#%d" % n for n, _old in retargeted), MAIN, "" if len(retargeted) == 1 else "s"))
        save_state(root, state)
        raise Fail("%s, but land had already retargeted %s on GitHub: restore %s with %s, or run land again, which retargets "
                   "%s again: its verify reads the new %s and says whether the batch still contains it"
                   % (moved_text(main_now), ", ".join("#%d from %s to %s" % (n, old, MAIN) for n, old in retargeted),
                      "it" if len(retargeted) == 1 else "them", " and ".join("`gh pr edit %d --base %s`" % (n, old) for n, old in retargeted),
                      "it" if len(retargeted) == 1 else "them", MAIN))
    gh(*cmd, cwd=root)
    poll = float(os.environ.get("ROMP_BATCH_POLL", "3"))
    for _ in range(20):
        pr = gh_json("pr", "view", str(b), "--json", "state,mergeCommit", cwd=root)
        if pr.get("state") == "MERGED":
            break
        if args.auto:
            print("auto-merge armed on #%d; run `scripts/batch.py finish %s` once it lands" % (b, args.name))
            save_state(root, state)
            return
        time.sleep(poll)
    else:
        raise Fail("#%d did not read MERGED after the merge call; check it, then run finish" % b)
    state["landed"] = {"pr": b, "merge": (pr.get("mergeCommit") or {}).get("oid"), "at": now()}
    save_state(root, state)
    print("merged batch PR #%d" % b)
    cmd_finish(argparse.Namespace(name=args.name, no_fetch=False, no_notify=args.no_notify, keep_worktree=False))


def cmd_finish(args):
    """After the batch PR merged: confirm each member reads MERGED (and tell the ones that do not),
    retarget still-open dependents, delete member branches and the batch branch, run the orphan
    check, report. Every observation about GitHub's behavior (did it mark the member merged, did
    it delete the branch) is recorded the FIRST time finish sees it, before finish changes anything,
    and kept across re-runs: a run that dies half-way and is run again must not attribute its own
    deletions to GitHub, forget that a member was stacked, or comment on a member twice. A state
    whose last assembly did not finish is refused with the pending members named: its member list is
    not what the merged branch carried (a rebuild that died after an earlier complete assembly had
    been pushed), and acting on it would clean up the wrong set."""
    root = repo_root()
    state = load_state(root, args.name)
    fetch(root, args.no_fetch)
    b = find_batch_pr(root, state)
    if not b:
        raise Fail("no batch PR recorded for %s" % args.name)
    pending = state["assembly"].get("pending") or []
    if state["assembly"].get("cursor") or pending or not state["assembly"].get("head"):
        raise Fail("assembly incomplete: %s never merged in the last assembly, so this state does not say which members "
                   "batch PR #%d carried; finish acts only on a complete assembly. Check the pending member(s) by hand: %s"
                   % (", ".join("#%d" % n for n in pending) or "the last assembly did not finish, so the members", b,
                      "; ".join("`gh pr view %d`" % n for n in pending) or "`gh pr view N`"))
    bpr = gh_json("pr", "view", str(b), "--json", "state,mergeCommit,url", cwd=root)
    if bpr.get("state") != "MERGED":
        raise Fail("batch PR #%d is %s, not MERGED; finish runs after the merge" % (b, bpr.get("state")))
    merge_sha = (bpr.get("mergeCommit") or {}).get("oid")
    if merge_sha and not is_ancestor(merge_sha, MAIN_REF, root):
        raise Fail("batch PR #%d's merge commit %s is not an ancestor of %s; was it squashed or rebased?" % (b, short(merge_sha), remote_main()))
    # Pre-round item 4: the merge commit's first parent must be the main verify read. land reads main once more right
    # before the merge call, but GitHub's merge pins the head, not the base, and the button or `gh pr merge` reads
    # nothing; a first parent that is another commit means main moved before the merge, so the tree on main is not the
    # batch head's tree and no sweep or ci.yml run tested it (none runs on main). Read here and reported loudly at the end,
    # after the cleanup, which does not depend on it.
    merge_parents = parents_of(merge_sha, root) if merge_sha else []
    first_parent = {"merge": merge_sha, "first_parent": (merge_parents or [None])[0],
                    "verified_main": (state.get("verified") or {}).get("main")}
    first_parent["ok"] = bool(first_parent["first_parent"]) and first_parent["first_parent"] == first_parent["verified_main"]
    # The same for the head that landed: the merge commit's second parent must be the batch head verify read. A commit
    # pushed to the batch branch after verify and merged by the button lands a head no sweep read (land pins the head
    # with --match-head-commit; the button and a bare `gh pr merge` do not). Reported with the first parent's check.
    landed = {"merge": merge_sha, "second_parent": merge_parents[1] if len(merge_parents) > 1 else None,
              "verified_head": (state.get("verified") or {}).get("head")}
    landed["ok"] = bool(landed["second_parent"]) and landed["second_parent"] == landed["verified_head"]
    members = members_by_n(state)
    landing = in_batch(state)
    member_refs = {members[e["n"]]["head_ref"] for e in landing} | {branch_of(args.name)}
    prog = state.setdefault("finish_progress", {"members": {}, "branches": {}, "retargeted": []})
    report = {"merged": [], "open": [], "retargeted": [], "deleted": [], "already_gone": [], "observations": []}
    for e in landing:
        m = members[e["n"]]
        key = str(m["n"])
        pr = gh_json("pr", "view", key, "--json", "state,headRefOid,baseRefName,headRefName", cwd=root)
        first = prog["members"].get(key)
        if first is None:
            # Recorded before anything is changed: what GitHub did by itself.
            first = prog["members"][key] = {"state": pr.get("state"), "base": pr.get("baseRefName"), "head": pr.get("headRefOid"), "told": False}
            save_state(root, state)
        was_stacked = first["base"] in member_refs
        if pr.get("state") == "OPEN" and was_stacked and pr.get("baseRefName") != MAIN:
            # The maintainer merged by hand, so land's retarget did not run: a member still based on
            # a sibling branch cannot have been marked merged. Retarget now and look again; whether
            # GitHub marks it merged on the retarget is to verify on the first batch, so the outcome
            # is recorded either way.
            gh("pr", "edit", key, "--base", MAIN, cwd=root)
            pr = gh_json("pr", "view", key, "--json", "state,headRefOid,baseRefName,headRefName", cwd=root)
            first["retargeted_to_main"] = pr.get("state")
            save_state(root, state)
        if first.get("retargeted_to_main"):
            report["observations"].append("#%d was still based on a member branch; retargeted to %s, now %s" % (m["n"], MAIN, pr.get("state")))
        if pr.get("state") == "MERGED":
            report["merged"].append(m["n"])
            continue
        report["open"].append(m["n"])
        moved = pr.get("headRefOid") != m["head"]
        if moved:
            why = "its head moved to %s after the cut at %s, so the batch carried the old head" % (short(pr.get("headRefOid")), short(m["head"]))
            todo = "Merge origin/%s, push, and it goes into the next batch." % MAIN
        elif was_stacked:
            why = "it was based on another PR's branch, and GitHub marks a PR merged only when its base reaches its head"
            todo = "It is retargeted to %s now; its content is already there, so close it if it does not read merged by itself." % MAIN
        else:
            why = "GitHub did not mark it merged although the batch carried its head %s" % short(m["head"])
            todo = "Its content is in %s; close it if it does not read merged by itself." % MAIN
        text = "This PR was in batch %s but is not marked merged: %s. %s" % (args.name, why, todo)
        if not args.no_notify and not first.get("told"):
            if comment_or_report(root, state, m["n"], text, "the still-open notice"):
                first["told"] = True
                save_state(root, state)
        if not moved:
            report["observations"].append("#%d: indirect-merge marking did not fire (head %s is in %s)" % (m["n"], short(m["head"]), MAIN))
    # Retarget still-open PRs based on a member branch or the batch branch BEFORE deleting anything:
    # GitHub retargets dependents itself when it deletes a head branch on merge, but whether that
    # happens for an indirectly merged PR's branch (and after an explicit delete) is to verify on
    # the first batch, so the tool does it explicitly.
    open_prs = gh_json("pr", "list", "--state", "open", "--limit", str(PR_LIST_LIMIT), "--json", "number,baseRefName,headRefName", cwd=root) or []
    for pr in open_prs:
        if pr["baseRefName"] in member_refs:
            gh("pr", "edit", str(pr["number"]), "--base", MAIN, cwd=root)
            if pr["number"] not in prog["retargeted"]:
                prog["retargeted"].append(pr["number"])
                save_state(root, state)
    report["retargeted"] = list(prog["retargeted"])
    remote_branches = set(git("ls-remote", "--heads", REMOTE, cwd=root).replace("refs/heads/", "").split()[1::2])
    for n in report["merged"]:
        ref = members[n]["head_ref"]
        seen = prog["branches"].get(ref)
        if seen is None:
            # Recorded once, before the delete: whether GitHub had already removed the branch.
            seen = prog["branches"][ref] = "present" if ref in remote_branches else "already gone"
            save_state(root, state)
        if seen == "present":
            if ref in remote_branches:
                git("push", "--quiet", REMOTE, "--delete", ref, cwd=root)
                prog["branches"][ref] = "deleted by finish"
                save_state(root, state)
            report["deleted"].append(ref)
        elif seen == "deleted by finish":
            report["deleted"].append(ref)
        else:
            report["already_gone"].append(ref)
    if report["already_gone"]:
        report["observations"].append("GitHub deleted the head branch of indirectly merged PR(s): %s" % ", ".join(report["already_gone"]))
    if report["deleted"]:
        report["observations"].append("finish deleted head branches GitHub left: %s" % ", ".join(report["deleted"]))
    if branch_of(args.name) in remote_branches:
        git("push", "--quiet", REMOTE, "--delete", branch_of(args.name), cwd=root)
    for n in report["retargeted"]:
        pr = gh_json("pr", "view", str(n), "--json", "baseRefName,state", cwd=root)
        if pr.get("baseRefName") != MAIN or pr.get("state") != "OPEN":
            report["observations"].append("#%d after retarget and base deletion: base %s, state %s" % (n, pr.get("baseRefName"), pr.get("state")))
    wt = worktree_dir(root, args.name)
    if not args.keep_worktree and os.path.isdir(wt):
        git("worktree", "remove", "--force", wt, cwd=root)
    # The batch branch by its full ref, read with git show-ref --verify, which reads only refs/heads/batch/<name>,
    # loose or packed, whether it exists or not (the 22:25Z ruling of 2026-10-03 on PR 959, item 1). Its short name
    # sends rev-parse through git's rules, which read <common dir>/batch/<name> (beside the batch state),
    # refs/batch/<name> and refs/tags/batch/<name> before refs/heads/batch/<name>; and rev-parse --verify of the full
    # ref, once the branch is gone (a finish run again after one that died past its git branch -D), walks
    # refs/refs/heads/batch/<name>, refs/tags/refs/heads/batch/<name> and the rest. git branch -D names
    # refs/heads/<its argument> itself, and reads no other name (git 2.43.0, traced on 2026-10-03).
    if git_ok("show-ref", "--verify", "--quiet", batch_ref(args.name), cwd=root) and not args.keep_worktree:
        git("branch", "-D", branch_of(args.name), cwd=root)
    try:
        orphans = run_tool([os.path.join(root, "scripts", "pr-orphans.sh")], root)
        report["orphans"] = {"exit": orphans.returncode, "out": (orphans.stdout + orphans.stderr).strip()}
    except GitBound as e:
        # The merge has happened, so a pr-orphans.sh that did not end within the bound is reported, as the CI read
        # below reports a read that fails, and finish carries on.
        report["orphans"] = {"exit": None, "out": str(e)}
    # ci.yml does not run on the merge to main: the run that tested the batch head's tree is ci.yml's run of the push to
    # the batch branch at the head that landed, read with batch_ci_run, the filtered read land gated on (the push
    # event, batch/<name>, ci.yml by its name, the sha checked on every row), so a manual or scheduled run at the same
    # commit never stands in for it. The merge has happened, so a read that fails is reported as unread, not raised.
    # The head that landed is the merge commit's second parent; verify's head (or the assembly's) only when GitHub
    # reported no merge commit to read it from.
    landed_head = landed["second_parent"] or (state.get("verified") or {}).get("head") or state["assembly"].get("head")
    try:
        ci_case, ci_found, _older = batch_ci_run(root, args.name, landed_head, tail="")
        ci_error = None
    except Fail as e:
        ci_case, ci_found, ci_error = "unread", None, str(e)
    ci_found = ci_found or {}
    report["ci"] = {"case": ci_case, "url": ci_found.get("url"), "status": ci_found.get("status"),
                    "conclusion": ci_found.get("conclusion"), "error": ci_error}
    ci_text = {"green": "green, %s" % ci_found.get("url"),
               "red": "red (conclusion %s), %s" % (ci_found.get("conclusion"), ci_found.get("url")),
               "pending": "pending (status %s), %s" % (ci_found.get("status"), ci_found.get("url")),
               "incomplete": "incomplete: it concluded success, but %s at the head has %s with no job run that passed in it "
                             "(%s), %s" % (CI_WORKFLOW_PATH, jobs_text(ci_found.get("jobs_unmet") or []),
                                           run_jobs_text(ci_found.get("jobs") or []), ci_found.get("url")),
               "missing": "missing: GitHub lists no run of %s from a push to %s at %s" % (CI_WORKFLOW, branch_of(args.name), landed_head),
               "unread": "unread after the merge: %s" % ci_error}[ci_case]
    # land's excused attempts are reported only when they belong to the run finish read (a run's id names its sha too):
    # the state's CI record is land's last, and a land refused after it (main moved), then another push run, leaves
    # another run's there. A new assembly and verify clear it.
    ci_rec = state.get("ci") or {}
    same_run = ci_found.get("databaseId") is not None and ci_rec.get("id") == ci_found.get("databaseId")
    for e in (ci_rec.get("excused") or []) if same_run else []:
        rerun = e.get("run", ci_found.get("databaseId")) == ci_found.get("databaseId")
        report["observations"].append("the batch head's CI run was green %s: attempt %d%s concluded %s (%s) and land "
                                      "excused it as a known flake: %s" % (
                                          "on a re-run" if rerun else "after an earlier run at the same head",
                                          e["attempt"], "" if rerun else " of run %s" % e.get("run"),
                                          e.get("conclusion") or e.get("status"), e.get("url"), e.get("flake")))
    report["first_parent"] = first_parent
    report["landed_head"] = landed
    state["finished"] = {"at": now(), "report": report}
    save_state(root, state)
    print("batch #%d landed, %d member(s) marked merged; no ci.yml run follows the merge to %s; the batch head's CI run: %s"
          % (b, len(report["merged"]), MAIN, ci_text))
    if report["open"]:
        print("STILL OPEN (told on the PR): %s" % ", ".join("#%d" % n for n in report["open"]))
    if report["retargeted"]:
        print("retargeted to %s: %s" % (MAIN, ", ".join("#%d" % n for n in report["retargeted"])))
    for o in report["observations"]:
        print("observed: %s" % o)
    if report["orphans"]["exit"] is None:
        print("pr-orphans.sh: unread: %s" % report["orphans"]["out"])
    elif report["orphans"]["exit"] != 0:
        print("pr-orphans.sh: exit %d\n%s" % (report["orphans"]["exit"], report["orphans"]["out"]))
    else:
        print("pr-orphans.sh: clean")
    if report["merged"]:
        print("postal (kind: coordinate) to the owners of %s: batch %s merged; remove your worktree and local branch (%s); the remote branch is gone."
              % (", ".join("#%d" % n for n in report["merged"]), args.name, ", ".join(members[n]["head_ref"] for n in report["merged"])))
    loud = ([first_parent_report(args.name, b, first_parent)] if not first_parent["ok"] else []) + \
        ([landed_head_report(args.name, b, landed)] if merge_sha and not landed["ok"] else [])
    if loud:
        raise Fail("\n".join(loud))


def landed_head_report(name, b, lh):
    """finish's loud report when the merge commit's second parent is not the batch head verify read: both shas, what it
    means, and the remedy, a sweep at the merge commit (as for the first parent)."""
    merge, second, seen = lh.get("merge"), lh.get("second_parent"), lh.get("verified_head")
    remedy = ("Sweep the merge commit now: `git worktree add --detach ../romp-merge-%s %s`, then `scripts/sweep.py run --tree "
              "../romp-merge-%s --python <python>` (%s; it owes every leg there), and tell the maintainer what it finds."
              % (name, merge, name, PYTHON_REMEDY))
    if not second or not seen:
        return ("HEAD NOT CHECKED: batch PR #%d's merge commit %s has %s, and verify recorded %s, so no one checked that the "
                "head that landed is the one the sweep read. %s" % (b, merge, "second parent %s" % second if second else
                                                                      "no second parent", "head %s" % seen if seen else "no head",
                                                                      remedy))
    return ("HEAD MISMATCH: batch PR #%d's merge commit %s has second parent %s, not %s, the batch head verify read: a commit "
            "reached %s after verify, so the tree on %s is not the tree the sweep read. %s"
            % (b, merge, second, seen, branch_of(name), MAIN, remedy))


def first_parent_report(name, b, fp):
    """finish's loud report when the merge commit's first parent is not the main verify read (pre-round item 4): both
    shas, what it means, and the remedy, a sweep at the merge commit, which owes every leg as any head does."""
    merge, parent, seen = fp.get("merge"), fp.get("first_parent"), fp.get("verified_main")
    remedy = ("Sweep the merge commit now: `git worktree add --detach ../romp-merge-%s %s`, then `scripts/sweep.py run --tree "
              "../romp-merge-%s --python <python>` (%s; it owes every leg there), and tell the maintainer what it finds."
              % (name, merge or "<merge>", name, PYTHON_REMEDY))
    if not merge:
        return ("FIRST PARENT NOT CHECKED: GitHub reports no merge commit for batch PR #%d, so finish cannot say that the tree "
                "on %s is the batch head's (verify read %s at %s). Find the merge commit on %s, then: %s"
                % (b, MAIN, MAIN, seen or "nothing", MAIN, remedy))
    if not seen:
        return ("FIRST PARENT NOT CHECKED: batch PR #%d's merge commit %s has first parent %s, and verify recorded no %s for "
                "batch %s to compare it with, so no one checked that the tree on %s is the batch head's. %s"
                % (b, merge, parent, MAIN, name, MAIN, remedy))
    return ("FIRST PARENT MISMATCH: batch PR #%d's merge commit %s has first parent %s, not %s, the %s verify read: %s moved "
            "before the merge, so the tree on %s is not the batch head's tree, and no sweep or CI run tested it (none runs "
            "on the merge to %s). %s" % (b, merge, parent, seen, MAIN, MAIN, MAIN, MAIN, remedy))


def restore_branch_tree(wt, name, force):
    """Put batch/<name>'s tree in the batch worktree's index and files, as git checkout of the branch does, naming the
    branch by its full ref (batch_ref) and leaving HEAD where it is: with `force`, `git read-tree --reset -u`, which
    discards every change to tracked files, as git checkout --force does; without it, the index refreshed (git checkout
    refreshes it too, so a file only touched is not read as changed) and then `git read-tree -m -u HEAD <branch>`, the
    two-way merge git checkout makes, which keeps each change that is not to a file the two trees hold differently and
    refuses, with git's error raised here, when one is. cmd_bisect's comment on its cleanups gives the measurements."""
    bref = batch_ref(name)
    if force:
        git("read-tree", "--reset", "-u", bref, cwd=wt)
        return
    git("update-index", "-q", "--refresh", cwd=wt, check=False)
    git("read-tree", "-m", "-u", "HEAD", bref, cwd=wt)


def attach_to_branch(wt, name, old):
    """Point the batch worktree's HEAD at batch/<name>, by its full ref, without touching its index or files, with the
    reflog line git checkout writes for the same move from `old`, the commit HEAD was at. git symbolic-ref skips the
    check git checkout makes first, that no other worktree holds the branch, so it is made here (held_elsewhere): a
    worktree that took the branch while bisect's command ran is a Fail naming it, and HEAD stays detached at `old`."""
    held = held_elsewhere(wt, name)
    if held:
        raise Fail("%s is checked out in another worktree at %s; git allows a branch in one worktree at a time, so %s is "
                   "left detached at %s, with the branch's tree. Take the branch off that worktree (git checkout --detach "
                   "there, or end its bisect or rebase), then run `git -C %s symbolic-ref HEAD %s`."
                   % (branch_of(name), held, wt, short(old), wt, batch_ref(name)))
    git("symbolic-ref", "-m", "checkout: moving from %s to %s" % (old, branch_of(name)), "HEAD", batch_ref(name),
        cwd=wt)


# The most bytes held_elsewhere reads of a file in a worktree's git dir (BISECT_START, a rebase's head-name, a linked
# worktree's gitdir): each holds a branch's name, an object id or a path, and a path on Linux is at most 4096 bytes.
GIT_DIR_FILE_MAX = 1 << 16


def held_elsewhere(wt, name):
    """The path of a worktree other than `wt` that holds batch/<name> by the rule git checkout applies before it puts a
    worktree on a branch (one branch, one worktree; is_shared_symref in git 2.43.0's worktree.c), or None: its HEAD
    names refs/heads/batch/<name>, or it is detached with a bisect started from batch/<name> or a rebase of batch/<name>
    in progress (_started_from). The worktrees and their HEADs are read from git worktree list --porcelain; a detached
    one's git dir is the common dir for the main worktree, the first listed, and for a linked one the directory under
    <common dir>/worktrees whose gitdir file names its path (_linked_git_dirs)."""
    bref = batch_ref(name)
    entries = []
    for block in git("worktree", "list", "--porcelain", cwd=wt).split("\n\n"):
        entry = dict(line.partition(" ")[::2] for line in block.splitlines())
        if "worktree" in entry:
            entries.append(entry)
    common = repo_for(wt).common_dir
    linked = None
    for i, entry in enumerate(entries):
        path = entry["worktree"]
        if "bare" in entry or same_dir(path, wt):
            continue
        if entry.get("branch") == bref:
            return path
        if "detached" not in entry:
            continue
        if i:
            linked = _linked_git_dirs(common) if linked is None else linked
            gd = linked.get(path)
        else:
            gd = common
        if gd is not None and _started_from(gd, name):
            return path
    return None


def _git_dir_file(path):
    """The text of a file in a worktree's git dir, or None when nothing is there, read with read_small_file at
    GIT_DIR_FILE_MAX bytes (a FIFO, a symlink or a larger file is a Fail naming it)."""
    data = read_small_file(path, GIT_DIR_FILE_MAX, "the git file", "move it aside and run the command again")
    return None if data is None else data.decode("utf-8", "replace")


def _linked_git_dirs(common):
    """{a linked worktree's path: its git dir} for each directory under <common>/worktrees, the path read from its gitdir
    file as git reads it (trailing whitespace and then a final /.git removed; a relative path taken from that
    directory)."""
    found = {}
    base = os.path.join(common, "worktrees")
    try:
        ids = sorted(os.listdir(base))
    except (FileNotFoundError, NotADirectoryError):
        return found
    for wid in ids:
        gd = os.path.join(base, wid)
        text = _git_dir_file(os.path.join(gd, "gitdir"))
        if text is None:
            continue
        path = text.rstrip()
        path = path[:-len("/.git")] if path.endswith("/.git") else path
        found[path if os.path.isabs(path) else os.path.realpath(os.path.join(gd, path))] = gd
    return found


def _started_from(gd, name):
    """Whether the worktree whose git dir is `gd` has a bisect started from batch/<name> or a rebase of batch/<name> in
    progress, by git's rule (wt_status_check_bisect and wt_status_check_rebase, git 2.43.0): BISECT_LOG there and
    BISECT_START naming the branch; or rebase-apply there, and not an am (no rebase-apply/applying), with
    rebase-apply/head-name naming it; or, with no rebase-apply, rebase-merge there with rebase-merge/head-name naming
    it. A file names the branch when its text, its final newlines removed and then a leading refs/heads/, is
    batch/<name>."""
    def names(rel):
        text = _git_dir_file(os.path.join(gd, rel))
        if text is None:
            return False
        text = text.rstrip("\n")
        return (text[len("refs/heads/"):] if text.startswith("refs/heads/") else text) == branch_of(name)
    if os.path.exists(os.path.join(gd, "BISECT_LOG")) and names("BISECT_START"):
        return True
    if os.path.exists(os.path.join(gd, "rebase-apply")):
        return not os.path.exists(os.path.join(gd, "rebase-apply", "applying")) and names("rebase-apply/head-name")
    return os.path.exists(os.path.join(gd, "rebase-merge")) and names("rebase-merge/head-name")


def cmd_bisect(args):
    """First-parent bisect of the batch chain. The command is run at the tip and at the base FIRST:
    `git bisect` takes "tip bad, base good" on faith, so a command that never fails would name the
    last member and one that fails everywhere the first; both are said instead of a member."""
    root = repo_root()
    state = load_state(root, args.name)
    wt = worktree_dir(root, args.name)
    if not os.path.isdir(wt):
        raise Fail("no batch worktree at %s" % wt)
    if not args.cmd:
        raise Fail("bisect needs a command after --, e.g. `-- pytest tests/test_x.py -q`", code=2)
    br = branch_of(args.name)
    tip = git("rev-parse", batch_ref(args.name), cwd=wt)
    base = git("merge-base", MAIN_REF, tip, cwd=wt)
    if git("rev-parse", "HEAD", cwd=wt) != tip:
        raise Fail("%s is not checked out at %s (HEAD is %s)" % (wt, br, short(git("rev-parse", "HEAD", cwd=wt))))
    held = held_elsewhere(wt, args.name)
    if held:
        raise Fail("%s is checked out in another worktree at %s; git allows a branch in one worktree at a time. Take it off "
                   "that worktree (git checkout --detach there, or end its bisect or rebase), then run bisect again."
                   % (br, held))
    if run_command(args.cmd, wt) == 0:
        raise Fail("the command passes at the batch tip %s; nothing to bisect (does it run the failing test?)" % short(tip))
    # Each setup step is inside the try whose finally undoes it (the 13:24Z ruling of 2026-10-02 on PR 926, its item 1),
    # so a stop that ends the step's git after it has moved HEAD (a post-checkout hook still running, say) still runs
    # the cleanup: outside it, such a stop left the worktree detached at the base, or mid-bisect at the midpoint, while
    # main said the cleanup ran. A checkout's git writes the other commit's files and index before it moves HEAD: a stop
    # between the two (git waiting on a FIFO planted at the worktree's logs/HEAD, which it writes in between) left the
    # worktree on the branch with the base's or the midpoint's tree staged, and the next bisect refused, saying the
    # command passes at the tip (the verify pass at the build of the 13:24Z ruling, its code finding 1). So when the
    # worktree has no changes to tracked files before these steps, each cleanup puts the branch's tree back in the index
    # and the files, forced, and the one after the steps does so before it ends the bisect. A worktree that had changes
    # to tracked files gets the unforced two-way merge, so the cleanup discards none of them. The batch worktree is this
    # tool's own, and these cleanups run whenever bisect ends, stopped or not: with the worktree clean here, the forced
    # restore discards every change the test command made to tracked files at the base and at each commit the bisect
    # tested (kept, the 21:31Z ruling of 2026-10-02 on PR 926, its item (a); docs/batching.md says so). A change the
    # command made in its run at the tip is already in the worktree here, so nothing is forced.
    # The cleanups name the branch by its full ref alone (the 22:25Z ruling of 2026-10-03 on PR 959, item 1). git
    # checkout leaves a worktree on a branch only when given the branch's short name, which it looks up by git's
    # rev-parse rules, and git bisect reset of a bisect started on the branch checks out the short name git bisect start
    # recorded, the same way: both read <common dir>/batch/<name> (beside the batch state), refs/batch/<name> and
    # refs/tags/batch/<name> before refs/heads/batch/<name>, and a leg can leave a symlink to /dev/zero at any of those
    # through its checkout's alternates. So each cleanup puts the branch's tree in the index and the files
    # (restore_branch_tree), the one after the steps then ends the bisect with a plain git bisect reset, which checks
    # nothing out while BISECT_HEAD exists (the bisect runs with --no-checkout, below), and HEAD is pointed at the
    # branch last (attach_to_branch), after the tree is there, so a cleanup whose restore fails, or that is killed
    # between its steps, leaves HEAD detached at the commit it was at rather than on the branch over another commit's
    # tree. Neither cleanup reads a name git's rules make of the branch's short name or of a commit's id (traced with
    # git 2.43.0 on 2026-10-04), except where git bisect start ended before it wrote BISECT_HEAD (the comment at the
    # cleanup after the steps). Before the verify pass at that ruling's build (its F1), the cleanup after the steps
    # ended the bisect with git bisect reset <tip>, which under git 2.43.0 looks the tip's id up by those rules, so a
    # symlink to /dev/zero the command left at refs/tags/<tip> during the steps stopped it: git 2.43.0's git bisect
    # looks a full id up that way whatever core.warnAmbiguousRefs says (QUIET_NAMES turns it off), where git 2.55.0's
    # reads the setting and then looks a full id up as no ref name (the verify pass at round 3's build, its v-2, run
    # under both gits on 2026-10-04). Measured on 2026-10-04 with git 2.43.0 against the cleanups before the ruling
    # (git checkout [--force] batch/<name>, and after the steps a plain git bisect reset of a bisect started on the
    # branch), in 19 cases (14 after the run at the base, 5 after the steps: a clean worktree; changes to tracked files
    # that the move keeps, discards or refuses; a staged change; a deleted file; a file only touched; an untracked file
    # in the way; the checkout of the base refused): the same HEAD, branch, index, files, ORIG_HEAD and bisect state
    # each time, and a move refused in the same cases among them, but for the move refused after the steps, which
    # leaves HEAD detached at the midpoint with the bisect in progress either way,
    # now with BISECT_HEAD among the bisect's files, and which now fails bisect, where git bisect reset's refusal was
    # ignored and bisect exited 0. The last reflog line names the commit HEAD was at when the cleanup began, as git
    # checkout's does when HEAD is detached then and the cleanup moves it. It differs from git checkout's in three of
    # those cases, where git checkout's named the branch: after the run at the base when HEAD never left the branch (git
    # checkout --detach <base> refused, or stopped before it moved HEAD), and after the steps with the restore forced
    # (two cases), where git bisect reset checked the branch out again after git checkout --force had. In the case
    # refused after the steps, the last reflog line is the one batch.py's checkout of the midpoint wrote, which names
    # the tip as the commit HEAD moved from, where bisect's own checkout named the branch. The cleanups' moves run no
    # post-checkout hook (git read-tree, git symbolic-ref and a git bisect reset that checks nothing out run none), and
    # a move an unforced restore refuses is refused in git read-tree's words. One refusal git checkout makes is not git
    # symbolic-ref's: a branch is checked out in one worktree at a time, so git checkout will not put a worktree on a
    # branch another worktree holds. held_elsewhere applies that rule, in git checkout's terms, when bisect starts (a
    # refusal there moves nothing) and again before each move of HEAD to the branch (attach_to_branch), so a worktree
    # that took the branch while the command ran leaves the batch worktree detached, naming it (the verify pass at that
    # ruling's build, its F4).
    # When the run at the base or the steps stopped (a Fail, a stop signal) and the cleanup after them then fails too,
    # the reason they stopped comes first and the cleanup's failure after it (round 3 of PR 959, correctness-2:
    # bisect_unfinished). Before, the cleanup's Fail replaced the reason: a command that crashed at a commit, or a
    # Ctrl-C, under a restore git read-tree refused, printed read-tree's error alone, and a stop exited 1. A command
    # that fails at the base is such a stop: its Fail is raised inside the try, straight after the command runs, so the
    # cleanup after the run at the base reads it as the reason (the verify pass at round 3's build, its v-1). Raised
    # after the finally, as it was before, it was replaced by the cleanup's Fail the same way.
    force = git("status", "--porcelain", "--untracked-files=no", cwd=wt) == ""
    body = None
    try:
        git("checkout", "--quiet", "--detach", base, cwd=wt)
        if run_command(args.cmd, wt) != 0:
            raise Fail("the command fails at the base %s (%s) too; no member made it fail. Check the command and the "
                       "environment before blaming a member" % (short(base), remote_main()))
    except BaseException as e:
        body = e
        raise
    finally:
        try:
            _cleanup_steps(lambda: restore_branch_tree(wt, args.name, force),
                           lambda: attach_to_branch(wt, args.name, git("rev-parse", "HEAD", cwd=wt)))
        except Fail as e:
            if body is None:
                raise
            bisect_unfinished(body, wt, args.name, e, bisected=False)
    # The steps `git bisect run` would take are driven here, with its rules for the command's exit (0 good, 125 skip, any
    # other from 1 to 127 bad, anything else stops the bisect): bisect run runs the command inside git, so the bound on
    # every git call (GIT_BOUND, the 02:43Z ruling, item 1(a)) would bound the command too, and a test command can rightly
    # take longer.
    # Each git step is bounded; the command is not, as the runs at the tip and the base above are not. Each step tests
    # another commit of the chain, so there are at most as many as it has commits, plus one.
    # The bisect runs with --no-checkout (the 22:25Z ruling of 2026-10-03 on PR 959, item 1, and the verify pass at that
    # ruling's build, its F1): git bisect start and each good, bad or skip step move BISECT_HEAD, not HEAD, and batch.py
    # checks out each commit to test itself, with git checkout --detach of BISECT_HEAD's id, which reads the names git's
    # rules make of that id, as bisect's own checkout of it did. HEAD is first detached at the tip, by its id, with git
    # update-ref --no-deref, which looks no name up: git bisect start --no-checkout looks up, by git's rules, the start
    # it records in BISECT_START, which is the branch's short name when it starts on the branch
    # (<common dir>/batch/<name> first) and the tip's id when it starts detached, an id git bisect start looks up anyway
    # as one of the commits it is given; started detached it also looks HEAD up by those rules (refs/HEAD,
    # refs/tags/HEAD and the rest), where started on the branch it looked up the names of refs/heads/batch/<name>
    # (refs/tags/refs/heads/batch/<name> and the rest) (git 2.43.0, measured on 2026-10-04).
    steps = int(git("rev-list", "--first-parent", "--count", "%s..%s" % (base, tip), cwd=wt)) + 1
    bad = body = None
    try:
        git("update-ref", "--no-deref", "-m", "checkout: moving from %s to %s" % (br, tip), "HEAD", tip, cwd=wt)
        proc = git_proc("bisect", "start", "--no-checkout", "--first-parent", tip, base, cwd=wt)
        out = proc.stdout + proc.stderr
        m = _FIRST_BAD.search(out)
        while not m:
            steps -= 1
            if steps < 0:
                raise Fail("bisect took more steps than the chain has commits, at %s" % short(git("rev-parse", "HEAD", cwd=wt)))
            git("checkout", "--quiet", "--detach", git("rev-parse", "--verify", "BISECT_HEAD", cwd=wt), cwd=wt)
            rc = run_command(args.cmd, wt)
            if rc not in range(0, 128):
                raise Fail("bisect stopped at %s: the command exited %d, and git bisect run stops on an exit of 128 or more, or "
                           "a signal" % (short(git("rev-parse", "HEAD", cwd=wt)), rc))
            proc = git_proc("bisect", "skip" if rc == 125 else "good" if rc == 0 else "bad", cwd=wt, check=False)
            out = proc.stdout + proc.stderr
            m = _FIRST_BAD.search(out)
            if not m and proc.returncode != 0:
                raise Fail("bisect did not name a first bad commit:\n%s" % out[-2000:])
        bad = m.group(1)
    except BaseException as e:
        body = e
        raise
    finally:
        # The branch's tree back (forced when the worktree had no changes to tracked files before the steps), the bisect
        # ended, and HEAD pointed at the branch, in that order. A plain git bisect reset checks nothing out while
        # BISECT_HEAD exists, and only ends the bisect; without it (git bisect start ended before it wrote BISECT_HEAD)
        # it checks out what BISECT_START records, the tip by its id, so it runs before HEAD is pointed at the branch.
        # When a step fails after the first bad commit was found, that commit is printed and carried in the Fail raised,
        # so the answer is not lost and the run does not report success over a worktree left off the branch (the verify
        # pass at the 22:25Z ruling's build, its F6 and F1's fifth point); when the steps stopped before it was found,
        # the reason they stopped is carried first (bisect_unfinished).
        try:
            _cleanup_steps(lambda: restore_branch_tree(wt, args.name, force), lambda: git("bisect", "reset", cwd=wt),
                           lambda: attach_to_branch(wt, args.name, git("rev-parse", "HEAD", cwd=wt)))
        except Fail as e:
            if bad is None:
                if body is None:
                    raise
                bisect_unfinished(body, wt, args.name, e, bisected=True)
            print(first_bad_line(state, bad, wt))
            raise Fail("bisect named the first bad commit, %s (printed above), but its cleanup did not finish: %s"
                       % (short(bad), bisect_cleanup_failed(wt, args.name, e))) from None
    print(first_bad_line(state, bad, wt))


def first_bad_line(state, bad, wt):
    """The line bisect prints for the first bad commit `bad`: the member whose merge it is, or the commit's subject."""
    members = members_by_n(state)
    hit = next((e for e in state["assembly"].get("merged", []) if e["merge"] == bad), None)
    if hit:
        return "first bad: #%d %s (merge %s); pull it and say why in the body" % (hit["n"], members[hit["n"]]["title"], short(bad))
    return "first bad: %s (%s), not a member merge" % (short(bad), subject_of(bad, wt))


def bisect_cleanup_failed(wt, name, e, bisected=True):
    """What bisect says after "its cleanup did not finish:" when a cleanup stopped at `e`, a Fail: the error, the state
    the batch worktree is left in, read as it is now (HEAD's commit, on the branch or detached, and whether a bisect is
    in progress), and how to put it back on the branch, named by its full ref; `bisected` False for the cleanup after
    the run at the base, where no bisect was started, so the remedy runs no git bisect reset. What comes before it
    says what came first: the first bad commit, found (cmd_bisect), or why bisect stopped before it found one
    (bisect_unfinished)."""
    bref = batch_ref(name)
    try:
        head = short(git("rev-parse", "HEAD", cwd=wt))
        on = git_proc("symbolic-ref", "-q", "HEAD", cwd=wt, check=False).stdout.strip() == bref
        bisecting = os.path.lexists(os.path.join(repo_for(wt).git_dir, "BISECT_START"))
        left = "%s at %s, with %s" % ("on " + branch_of(name) if on else "detached", head,
                                      "the bisect in progress" if bisecting else "no bisect in progress")
    except Fail as unread:
        left = "in a state batch.py could not read (%s)" % unread
    steps = ["`git -C %s checkout --detach %s`" % (wt, bref)] + (["`git -C %s bisect reset`" % wt] if bisected else [])
    return ("%s\nThe batch worktree %s is left %s. To put it back on %s at the tip, commit or discard any change git "
            "names above, then run %s and `git -C %s symbolic-ref HEAD %s`."
            % (str(e).rstrip(), wt, left, branch_of(name), ", ".join(steps), wt, bref))


def bisect_unfinished(body, wt, name, e, bisected):
    """Raise for bisect when the run at the base (`bisected` False) or the steps stopped on `body`, before a first bad
    commit was found, and the cleanup after them then stopped at `e`, a Fail (round 3 of PR 959, correctness-2): the
    reason first, then the cleanup's error, the state it left and the remedy (bisect_cleanup_failed). A Fail (a command
    that failed at the base; one that exited 128 or more at a step, or was ended by a signal there; a git step that
    failed) is raised again with that text after its own, its exit kept. A stop (Stopped) is raised again carrying the
    text (Stopped.cleanup_failed), so main exits 128 plus the signal's number and says the cleanup did not finish,
    where it says the cleanup ran when it did. Anything else is raised as it is, the text printed before it."""
    unfinished = bisect_cleanup_failed(wt, name, e, bisected)
    if isinstance(body, Stopped):
        body.cleanup_failed = unfinished
        raise body
    if isinstance(body, Fail):
        raise Fail("%s\nThen bisect's cleanup did not finish: %s" % (str(body).rstrip(), unfinished),
                   code=body.code) from None
    print("batch: bisect's cleanup did not finish: %s" % unfinished, file=sys.stderr)
    raise body


# ── entry point ──────────────────────────────────────────────────────────────

HELP_NAME = "the batch's name (`plan` prints it; state lives in <git common dir>/batch/<name>.json)"
HELP_NO_FETCH = "skip `git fetch --prune %s` first (the default fetches so heads and %s are current)" % (REMOTE, MAIN)
HELP_NO_NOTIFY = "post no comment on the member PRs this touches (the postal text is still printed)"


def main(argv=None):
    doc = __doc__.split("\n\n")
    # The epilog is the docstring's explanation, subcommand table and state paragraph; the test
    # contracts that follow them are for a reader of the source.
    ap = argparse.ArgumentParser(prog="scripts/batch.py", description=doc[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n\n".join(p for p in doc[1:] if not p.startswith("Contracts the tests")))
    sub = ap.add_subparsers(dest="subcommand", required=True, metavar="<subcommand>")

    p = sub.add_parser("plan", help="pick and order the members, predict conflicts, write the plan",
                       description="Pick the members: open, non-draft PRs against %s or against another candidate's branch, not labeled "
                                   "`%s` or `%s`, whose head has a passing sweep result of its own (scripts/sweep.py, read from "
                                   "this machine's state dir; a candidate without one is left out with the case named). Order "
                                   "them dependencies first (a base that is another candidate's branch, or "
                                   "`Depends-on: #N` in the body's first lines), then by number; predict conflicts read-only "
                                   "against the accumulating tree; pin every head SHA; write the plan. Nothing is merged."
                                   % (MAIN, LABEL_MAJOR, LABEL_HOLD))
    p.add_argument("--labeled", action="store_true", help="only PRs labeled `%s`" % LABEL_LAND)
    p.add_argument("--only", type=int, action="append", metavar="N",
                   help="only PR N (repeatable): a single PR lands as a one-member batch; a dependency not named is "
                        "not taken in, so its dependent is left out with it")
    p.add_argument("--name", help="batch name (default: today's date plus the first free letter)")
    p.add_argument("--force", action="store_true", help="overwrite a plan that was already assembled")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("assemble", help="merge the pinned heads into ../romp-batch-<name>",
                       description="Merge the pinned heads, in plan order, with `git merge --no-ff` into a fresh `batch/<name>` at "
                                   "%s in the worktree ../romp-batch-<name> (rerere on). Refuses while another `%s/batch/*` "
                                   "exists: the branch is the mutex. A conflicting member is held back and its owner told, "
                                   "unless named by --resolve: then assemble stops with exit 3, you resolve per hunk in the "
                                   "worktree and `git add`, and `--continue --reviewed '<note>'` commits it (only the "
                                   "conflicted files may differ from the clean merge) or `--abort` drops it. Re-running "
                                   "rebuilds the branch from the current %s." % (remote_main(), REMOTE, remote_main()))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--without", type=int, action="append", metavar="N", help="leave N (and its dependents) out")
    p.add_argument("--resolve", type=int, action="append", metavar="N", help="stop at N's conflict for a hand resolution")
    p.add_argument("--repin", action="append", metavar="N|all", help="re-read N's head, title, labels, trailer and base from GitHub before assembling; "
                                                                    "refused when the new head has no passing sweep result of its own")
    p.add_argument("--continue", dest="cont", action="store_true", help="commit the resolved merge and go on")
    p.add_argument("--abort", action="store_true", help="abandon the stopped resolution; hold that member back")
    p.add_argument("--reviewed", metavar="NOTE", help="with --continue: who reviewed the resolution and the verdict")
    p.add_argument("--merge-main", action="store_true",
                   help="merge %s into the assembled batch instead of rebuilding (when %s moved); a conflict stops like --resolve" % (remote_main(), MAIN))
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY + " (held-back PRs)")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_assemble)

    p = sub.add_parser("verify", help="provenance, pinned heads, bases, main contained, ledger, sweep result",
                       description="The gate `land` re-runs. Provenance: every commit the batch adds is a member merge, a `batch:` "
                                   "commit or a merge of %s, and every merge equals the clean merge of its parents unless it "
                                   "carries a recorded resolution (then only the resolution's files may differ). Every member's "
                                   "live head still equals the pinned SHA, is OPEN, and has its base in the batch or in %s. "
                                   "The batch head contains %s as %s has it now (ci.yml does not run on the merge, so the tree that "
                                   "lands must be the tree the sweep and the batch branch's CI ran on); `assemble --merge-main` "
                                   "catches it up. The ledger check runs on the branch's tree. The sweep result that "
                                   "`scripts/sweep.py run` wrote for the batch head's full sha must be a pass; a missing, stale, "
                                   "unfinished, red, invalid, incomplete or unreadable result fails by that name."
                                   % (remote_main(), MAIN, MAIN, REMOTE))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("summarize", help="create or update the batch PR; comment on each member",
                       description="Render the body (first block, Read these first, members table, ledger entries, held back, "
                                   "conflict resolutions, assembly log) and create or edit the batch PR against %s with the "
                                   "`%s` label; comment `in batch <name> at <sha>` on each member once per head." % (MAIN, LABEL_BATCH))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--print-only", action="store_true", help="print the body; touch nothing")
    p.set_defaults(func=cmd_summarize)

    p = sub.add_parser("pull", help="rebuild without N and its dependents, push, re-summarize",
                       description="Take member N out (the maintainer's `pull #N`): rebuild the branch without it and its "
                                   "dependents (unless N already merged into %s, then they stay), force-push with lease, "
                                   "regenerate the body, and comment on N and on each dropped dependent." % MAIN)
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("n", type=int, help="the member PR's number")
    p.add_argument("--reason", metavar="TEXT", help="why, for the comment on N (default: the maintainer asked)")
    p.add_argument("--no-push", action="store_true", help="rebuild only; do not push or re-summarize")
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY)
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("land", help="verify, merge the batch PR with a merge commit, finish",
                       description="On the maintainer's word for this batch: run verify again (pinned heads, main contained, "
                                   "the sweep result at the verified head), read the batch head's CI run from GitHub (the "
                                   "newest run of ci.yml from a push to the batch branch at the verified head; missing, "
                                   "pending or red is refused, --auto or not, and so is a success in which a job of the "
                                   "head's ci.yml has no job run that passed, and any other attempt of a push run at "
                                   "that head that did not pass, the newest run's earlier attempts and every attempt of an "
                                   "older run of the same sha, unless --flake names it), read %s on %s and refuse if it moved since verify, "
                                   "retarget stacked members to %s, read %s once more and refuse if it moved (naming each "
                                   "member it retargeted and how to restore its base), then `gh pr merge --merge "
                                   "--match-head-commit <verified sha>` and finish. The merge pins the head, not the base, so "
                                   "a merge to %s between that last read and GitHub's merge is not stopped: finish then fails "
                                   "loudly, naming the merge commit's first parent and the main verify read. With --auto the "
                                   "merge happens later, when a rule on %s is met, and main is not read again then (--auto "
                                   "is refused until the repository allows auto-merge and a rule gates a merge; the fork had "
                                   "neither on 2026-09-27). scripts/land.sh runs this subcommand. Never squash or rebase: that "
                                   "would leave every member open." % (MAIN, REMOTE, MAIN, MAIN, MAIN, MAIN))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--auto", action="store_true",
                   help="arm auto-merge instead (lands when the required checks pass; needs the repository's \"Allow auto-merge\" "
                        "setting and a rule on %s that gates a merge: a ruleset rule such as required_status_checks or "
                        "pull_request, or classic protection with required checks or reviews)" % MAIN)
    p.add_argument("--flake", action="append", metavar="RUN/ATTEMPT=TEXT",
                   help="an attempt of a push run at the batch head, other than the newest run's latest, that failed on a "
                        "known flake (the run id and attempt number as land's refusal names them, then the failing test and "
                        "where it is recorded as a known flake); without it land refuses a head where such an attempt did not "
                        "pass, an earlier attempt of the newest run or any attempt of an older run of the same sha; one "
                        "attempt across the runs at the head can be excused; repeatable")
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY + " (passed on to finish)")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_land)

    p = sub.add_parser("finish", help="after the merge: member states, retargets, branch deletion, orphans",
                       description="After the batch PR merged (by land, or by hand): confirm each member reads MERGED and "
                                   "comment on any that does not, retarget still-open dependents to %s, delete the member "
                                   "branches and `batch/<name>`, remove the worktree, run scripts/pr-orphans.sh, and report one "
                                   "line naming the batch head's CI run (the push run land gated on, and its case). Then it "
                                   "checks that the merge commit's first parent is the %s verify read, and its second parent "
                                   "the batch head verify read (a commit pushed after verify and merged by the button): no ci.yml "
                                   "run follows the merge to %s, so a batch merged after %s moved, or with a head the sweep did not "
                                   "read, lands a tree nothing tested, and finish cannot undo that; it exits 1 naming both shas "
                                   "and the sweep at the merge commit that is owed. It exits 1 too when it cannot tell: no "
                                   "merge commit reported, or no %s or head recorded by verify. Safe to re-run: what it "
                                   "observed the first time is kept." % (MAIN, MAIN, MAIN, MAIN, MAIN))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY + " (members that did not read merged)")
    p.add_argument("--keep-worktree", action="store_true", help="leave ../romp-batch-<name> and the local batch branch in place")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_finish)

    p = sub.add_parser("bisect", help="first-parent bisect over the batch chain; names the member",
                       description="When the batch's CI is red: run the command at the tip and at the base first (a command that "
                                   "never fails, or fails everywhere, is reported instead of a member), then `git bisect "
                                   "--first-parent` over the member merges, each step taken as `git bisect run` takes it (exit "
                                   "0 good, 125 skip, any other from 1 to 127 bad), and name the member to pull.")
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="-- <command that fails on the bad tree>, run in the batch worktree")
    p.set_defaults(func=cmd_bisect)

    args = ap.parse_args(argv)
    if args.subcommand == "bisect" and args.cmd[:1] == ["--"]:
        args.cmd = args.cmd[1:]
    replaced = {}
    try:
        install_stop_handlers(replaced)
        args.func(args)
    except Fail as e:
        print("batch: %s" % e, file=sys.stderr)
        return e.code
    except Stopped as e:
        # "any": a stop can land between two processes, with none running (the verify pass at the closing check
        # wf_fb19febe-36b's build, the class of its code finding 3, which scripts/sweep.py's check line had too)
        if e.cleanup_failed is not None:
            print("batch: stopped by signal %d; any process it was waiting on was killed, but its cleanup did not "
                  "finish: %s" % (e.signum, e.cleanup_failed), file=sys.stderr)
        else:
            print("batch: stopped by signal %d; any process it was waiting on was killed and its cleanup ran"
                  % e.signum, file=sys.stderr)
        return 128 + e.signum
    finally:
        for s, handler in replaced.items():
            signal.signal(s, handler)
    return 0


if __name__ == "__main__":
    sys.exit(main())
