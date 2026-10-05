#!/usr/bin/env python3
"""The tests that read the name of the current branch of the repository they run in, derived from the tree and pinned
(the 22:25Z ruling of 2026-10-03 on PR 959, item 2), so a new one is noticed and judged.

Why it matters: each job's checkout in the local sweep is detached at the swept commit and holds no branch
(scripts/sweep.py, make_checkout), while CI's checkout, in every job of ci.yml, holds the run's branch as a local branch,
which actions/checkout creates at the commit it checks out. A test that reads the current branch's name of its checkout
therefore gets none in the sweep (git rev-parse --abbrev-ref HEAD prints HEAD, git symbolic-ref HEAD fails, git branch
--show-current prints nothing) and the run's branch in CI, and can behave differently in the two; the sweep is the
landing gate for every member PR (docs/batching.md).

The census is a text scan, with the machinery tests/test_origin_main_readers.py uses (tests/ref_reader_census.py, whose
docstring gives the rules: every tracked text file, of a Markdown file its fenced blocks alone, none of the census files;
a hit file classified and pinned line by line). A line is a hit when it carries one of SPELLINGS: --show-current
(git branch's; a prefix of it git accepts, down to --sh, git 2.43.0, 2026-10-03, is read after git branch, as a listing
option, below, since --sh and --show alone are other tools' options too); git rev-parse
--abbrev-ref or --symbolic-full-name, the names rev-parse gives HEAD or any revision (rev-parse takes no prefix of
either); symbolic-ref, read or written (git symbolic-ref [--short] HEAD reads the branch HEAD names); a git status with
--branch, a prefix of it (--b is the shortest), or -b in a cluster of short options; a line git prints with the current
branch's name, or with none, that a reader of git's output parses (On branch, HEAD detached, Not currently on any
branch, porcelain v2's branch.head); name-rev; describe with --all (exact: --al is ambiguous); HEAD's file, read
directly (.git/HEAD; a path joined to "HEAD" by a join, joinpath, Path or resolve call; a "/HEAD" literal; <dir>/HEAD
in a shell or an f-string, the directory a variable, a ${...}, a $(...) or a {...}; --git-path HEAD; the kernel's
_git_head_file);
GitHub's variables for the run's ref (GITHUB_REF, GITHUB_REF_NAME, GITHUB_HEAD_REF, GITHUB_BASE_REF and the rest, and
the workflow expressions github.ref, github.head_ref and github.base_ref); the current branch's upstream or push (@{u},
@{upstream}, @{push}, in any case); a listing that marks the current branch or holds the local branches (git branch with
no other word, or with a listing option or a prefix of one git accepts, %(HEAD), for-each-ref over refs/heads, show-ref
--heads, git worktree list); a decoration (--decorate, exact; %d, %D or %(decorate) in a format given after
--format=, --pretty=, format: or tformat:, quoted or not; log.decorate), which prints HEAD -> <branch> (a format given
as a separate word, git log --format %D, is not git's syntax: git takes a format only joined to its option with =, and
git 2.43.0 refuses that form as an ambiguous revision, 2026-10-04, so it reads nothing and is not a spelling); and a
branch's name put before refs/heads/ or taken off it (refs/heads/ before a composed part, as in
"refs/heads/" + name or head[len("refs/heads/"):]), the step that turns a name a reader got into a ref, or the ref HEAD
names into a name. A run of two or three consecutive lines is a hit too when its joined text carries a spelling made of
more than one word that none of its lines, and no shorter run inside it, carries alone (SPLIT_SPELLINGS: a status with
--branch, a describe --all, a path joined to "HEAD", a listing, each split over lines).

What the scan cannot see: a git subcommand, option or name assembled at run time; a command that uses the current
branch without naming it (a bare git push or git pull, git branch -u or -m with one name, git merge or git rebase with no
argument, git checkout -), which the census does not read as a spelling; gh's own read of the current branch, which a gh
pr command given no number, URL or branch makes (the tests run a fake gh, tests/fixtures/fake_gh.py, and no test has gh
credentials); another CI system's variables; a spelling split over more than three lines; a judged line moved to
another place in its file; code that is not tracked; and a reader the execution check below did not run.

Every hit is classified, by file (CLASSIFIED: the kinds of its hits and why), and pinned by its text (HITS, a JSON file
of each classified file's judged hit lines): READS, a line of a test, or of code a test runs, that reads the current
branch of the checkout the test runs in, its name or the ref HEAD names (READERS names each such line); SYNTHETIC, a
read of a repository the test or the code under test builds, which the entry names; and NOT_A_READ, prose, a message, an
expected text, a write, a command string that is never run, or a name composed for a ref that is not the current
branch. census_problems fails on each finding tests/ref_reader_census.py names, by the rules of
tests/test_origin_main_readers.py's census: an unclassified hit, a changed or added hit line, a judged line gone, a stale
entry, a READERS line no longer read; and the tree-level pin fails on an empty scan.

The classification was confirmed by execution where the text did not settle it. On 2026-10-03, 189 Python modules (those
that name the kernel's or postal's branch readers, a function that calls one, or the update walk; those that build a
session, whose directory's branch the kernel reads; and those that carry a hit) and the bats files that carry a hit (of
pre-push-hook.bats only its first 103 of 703 cases: its hits are writes of HEAD in the repository its setup builds,
which the text settles) ran in a detached checkout of this repository, as a sweep's checkout is, with a git first on
PATH logging each call whose words could read a branch's name (a rerun of the four of them that name the update mode, a
channel or the update probe's gate logged the test each of their calls ran under). Of the 7,042 calls it logged, the
checkout's own were git status --porcelain, git log of a commit, git log -p of HEAD, and the reads READERS lists:
tests/test_sdk_kernel.py's two rev-parse --abbrev-ref HEAD, its own and the kernel's, and the kernel's symbolic-ref -q
--short HEAD under tests/test_main_drift_notice.py. tools/perf-bench.py's reader reads files, not git, so the check
cannot see it, and its text settles it. Nor can the check see a test that puts its own PATH ahead of the logging git, or
calls git by an absolute path.

At this head four lines read the checkout's current branch, and each test that runs one gets the same outcome detached
and on a branch: tests/test_sdk_kernel.py's test_git_branch_derived_from_folder asks git for the checkout's branch and
the kernel for its own reading (_git_branch, whose _tree_branch line is the second reader), and maps git's HEAD, a
detached HEAD's answer, to no branch as the kernel does; tests/test_main_drift_notice.py's update-probe cases run the
kernel's _checkout_branch (the third) with the update mode stubbed to auto, under which the probe's verdict does not
depend on the branch; and tools/perf-bench.py's git_head (the fourth) reads the checkout's HEAD file and follows the
branch it names to the branch's commit (tests/test_perf_bench.py compares that commit with git rev-parse HEAD), where a
detached HEAD holds the commit itself.
"""
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tests import ref_reader_census
from tests.ref_reader_census import CENSUS_FILES, NOT_A_READ, SYNTHETIC, Census, pinned_text, tracked_files

ROOT = Path(__file__).resolve().parent.parent
HERE = "tests/test_branch_name_readers.py"
# {path: [each judged hit line, stripped, as pinned_text gives it, sorted]}: the lines of each CLASSIFIED file judged so
# far, written with json.dump(..., ensure_ascii=True, sort_keys=True, indent=1), so the tree stays ASCII. It holds every
# spelling, so the census reads it no more than it reads this file (CENSUS_FILES).
HITS = "tests/fixtures/branch-name-hits.json"


def _prefixes(option, shortest):
    """A pattern matching `option` (a long option, "--name") or any prefix of it at least as long as `shortest`, the
    shortest prefix git accepts for it."""
    rest = ""
    for ch in reversed(option[len(shortest):]):
        rest = "(?:%s%s)?" % (re.escape(ch), rest)
    return re.escape(shortest) + rest


# The options of git branch that list branches rather than make, move or delete one, each as git 2.43.0 accepts it: a
# long option or a prefix of it down to the shortest git takes (measured 2026-10-03: --sh, --l, --al, --rem, --v, --con,
# --po, --form, --mer and --so), or short options in a cluster (-a, -l, -r, -v).
_LISTING_OPTIONS = "(?:%s|-[alrv]+)" % "|".join(
    [_prefixes(o, s) for o, s in (("--show-current", "--sh"), ("--list", "--l"), ("--all", "--al"),
                                  ("--remotes", "--rem"), ("--verbose", "--v"), ("--contains", "--con"),
                                  ("--no-contains", "--no-con"), ("--points-at", "--po"), ("--format", "--form"),
                                  ("--merged", "--mer"), ("--no-merged", "--no-mer"), ("--sort", "--so"))]
    + ["--column", "--no-column", "--abbrev", "--no-abbrev", "--ignore-case", "--omit-empty"])
# git and its global options (-C <dir>, -c <name>=<value>, --git-dir=<dir> and the like), before its subcommand.
_GIT = r"\bgit(?:\s+-[cC]\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\S+)|\s+--?[\w-]+(?:=\S+)?)*\s+"
# A git branch that lists branches, marking the current one: the subcommand last in its command, or before a listing
# option, spelled as a command line (git, any global options, then branch) or as quoted words of one argument list
# ("git" and then, in the same list, "branch").
_BRANCH_LISTING = (_GIT + r"branch(?=\s*(?:$|[;|&)\"'`]|\s" + _LISTING_OPTIONS + r"(?![\w-])))"
                   r"|[\"']git[\"'][^\]\n]{0,160}?[\"']branch[\"']\s*(?:[\])]|,\s*[\"']" + _LISTING_OPTIONS
                   + r"[\"'=])")
# A git status that prints the branch: with --branch or a prefix of it, or -b in a cluster such as -sb, spelled as a
# command line or as quoted words of an argument list (its long format prints the branch too, which a reader finds by
# the line it parses: the next spelling).
_STATUS_OPTION = r"(?:-[A-Za-z]*b[A-Za-z]*|%s)" % _prefixes("--branch", "--b")
_STATUS_BRANCH = (_GIT + r"status\b[^\n|;&]{0,120}?\s" + _STATUS_OPTION + r"(?![\w-])"
                  r"|[\"']status[\"'][^\]\n]{0,120}?[\"']" + _STATUS_OPTION + r"[\"']")
# The lines git prints that name the current branch, or say there is none, which a reader of git's output parses: git
# status's "On branch <name>", "HEAD detached at", "Not currently on any branch", porcelain v2's "# branch.head", and git
# push's "You are not currently on a branch" (the short format's "## <name>" comes only with -b, the spelling above).
_BRANCH_LINE = r"\bOn branch\b|\bHEAD detached\b|\bcurrently on (?:any|a) branch\b|\bbranch\.head\b"
# (what it is, the pattern): every spelling the census looks for, each matched anywhere in a line.
SPELLINGS = (
    ("branch --show-current", re.compile(r"--show-current(?![\w-])")),
    ("a name rev-parse gives a revision", re.compile(r"--abbrev-ref(?![\w-])|--symbolic-full-name(?![\w-])")),
    ("symbolic-ref", re.compile(r"\bsymbolic-ref\b")),
    ("a status that prints the branch", re.compile(_STATUS_BRANCH)),
    ("a line git prints with the branch's name", re.compile(_BRANCH_LINE)),
    ("name-rev", re.compile(r"\bname-rev\b")),
    ("describe over every ref",
     re.compile(r"\bdescribe\b[^\n]{0,160}?--all(?![\w-])|--all\b[^\n]{0,160}?\bdescribe\b")),
    ("HEAD's file", re.compile(r"\.git/HEAD\b|--git-path[\s\"',]+HEAD\b"
                               r"|\b(?:join(?:path)?|Path|resolve)\([^)\n]{0,160}[\"']HEAD[\"']\s*\)"
                               r"|/\s*[\"']HEAD[\"']|[\"']/HEAD[\"']|(?:\$\{?\w+|[)}])\}?/HEAD\b|\b_git_head_file\b")),
    ("GitHub's ref variables", re.compile(r"\bGITHUB_(?:HEAD_|BASE_)?REF(?:_NAME|_TYPE|_PROTECTED)?\b"
                                          r"|\bgithub\.(?:head_|base_)?ref(?:_name|_type|_protected)?\b")),
    ("the current branch's upstream or push", re.compile(r"@\{(?:u|upstream|push)\}", re.IGNORECASE)),
    ("a listing that marks or holds the local branches",
     re.compile(_BRANCH_LISTING + r"|%\(HEAD\)|for-each-ref[^\n]{0,160}?refs/heads|show-ref[^\n]{0,160}?--heads\b"
                r"|\bworktree\s+list\b|[\"']worktree[\"']\s*,\s*[\"']list[\"']")),
    ("a decoration", re.compile(r"--decorate(?![\w-])|(?:--(?:format|pretty)=|\bt?format:)[^\s\"'`]*%(?:[dD]|\(decorate)"
                                r"|(?:--(?:format|pretty)=|\bt?format:)[\"'][^\"'\n]*%(?:[dD]|\(decorate)"
                                r"|\blog\.decorate\b|\bdecorate\s*=")),
    ("a branch's name put before refs/heads/ or taken off it", re.compile(r"refs/heads/(?=[$%{}\"'`+(\[])")),
)
# Every line a spelling can match holds one of these, so the lines that hold none are not matched against SPELLINGS.
_CANDIDATE = re.compile(r"show-current|abbrev-ref|symbolic|status|On branch|HEAD|_git_head_file|currently on"
                        r"|branch\.head|name-rev|describe"
                        r"|GITHUB_|github\.|@\{|branch|for-each-ref|show-ref|worktree|decorate|%[dD(]|refs/heads/")
# The most consecutive lines split_hits joins to read a spelling written across them.
WINDOW = 3
# The spellings made of more than one word, which a line break can split, as split_hits reads them; a run of lines holds
# a word of one of them (_SPLIT_CANDIDATE), in some line, before it is joined.
SPLIT_SPELLINGS = tuple((what, rx) for what, rx in SPELLINGS
                        if what in ("a status that prints the branch", "describe over every ref", "HEAD's file",
                                    "a listing that marks or holds the local branches"))
_SPLIT_CANDIDATE = re.compile(r"status|describe|HEAD|branch|for-each-ref|show-ref|worktree")

READS = "reads the checkout's current branch"

# The lines that read the current branch of the checkout the test runs in: (path, text the line holds, why). Each one's
# file is in CLASSIFIED too, with READS among its kinds (the module docstring says how each reads the same detached).
READERS = (
    ("tests/test_sdk_kernel.py", '"rev-parse", "--abbrev-ref", "HEAD"]',
     "test_git_branch_derived_from_folder asks git for the romp checkout's own branch (repo, the directory above bin/) "
     "and maps a detached HEAD's answer, HEAD, to no branch, as the kernel's _git_branch does"),
    ("kernel/kernel.py", '"rev-parse", "--abbrev-ref", "HEAD"]',
     "_tree_branch, which _git_branch runs on a session's directory, and tests/test_sdk_kernel.py's "
     "test_git_branch_derived_from_folder on the checkout; it gives '' for a detached HEAD"),
    ("kernel/kernel.py", 'out = subprocess.run(["git", "symbolic-ref", "-q", "--short", "HEAD"],',
     "_checkout_branch, the install's own branch (ROOT), which _main_tracking, the update probe's gate, passes to "
     "_main_channel_verdict; tests/test_main_drift_notice.py's ConvergeWaitsSpareOnlyCuts and DriftWiring cases run "
     "the probe with ROOT the checkout and the update mode stubbed to auto, under which the verdict is true whatever "
     "the branch, so they pass detached and on a branch (the execution check's calls, 2026-10-03)"),
    ("tools/perf-bench.py", 'with open(os.path.join(gitdir, "HEAD")) as f:',
     "git_head reads the checkout's HEAD file and follows the branch it names to the branch's commit; "
     "tests/test_perf_bench.py runs the bench on the checkout (ROOT) and compares that commit with git rev-parse HEAD "
     "there; a detached HEAD holds the commit itself"),
)

# path: (the kinds its hits are, why): every file with a hit; HITS holds the lines judged.
CLASSIFIED = {
    ".github/workflows/ci.yml": ((NOT_A_READ,), "github.ref in the concurrency group, which GitHub evaluates for a run "
                                                "and no test runs; tests/test_ci_workflow_concurrency.py evaluates the "
                                                "expression over values it gives"),
    ".github/workflows/docs.yml": ((NOT_A_READ,), "github.ref in the concurrency group, which GitHub alone evaluates"),
    ".github/workflows/ledger.yml": ((NOT_A_READ,), "github.ref in the concurrency group, which GitHub alone evaluates"),
    "kernel/kernel.py": ((READS, SYNTHETIC, NOT_A_READ),
                         "_tree_branch reads the branch of a session's directory, and _checkout_branch the install's "
                         "own (ROOT), and a test runs each on the checkout (READERS); _local_branch reads ROOT's too, "
                         "and the tests that reach it stub it (the restart tests and "
                         "tests/test_kernel_remote_pull.py), and the execution check saw no call of it in the checkout; "
                         "_file_github_link reads a viewed file's own repository, which the tests build "
                         "(tests/test_file_github.py); the update walk's advance() runs in the install clone the "
                         "tests build (tests/test_kernel_update.py); _git_head_file and its users take HEAD's file "
                         "for its path and its time, and the bare-repository check its presence; the refs/heads/ "
                         "compositions name the peer-update branch (_P2P_REF) and a pushed branch by name; the rest "
                         "are docstrings and comments"),
    "postal/postal_service.py": ((SYNTHETIC,), "_git_branch reads the branch of an agent's directory, which the postal "
                                               "tests set to directories they make; the execution check saw no call "
                                               "of it in the checkout"),
    "scripts/batch.py": ((SYNTHETIC, NOT_A_READ),
                         "bisect's git symbolic-ref writes HEAD in the batch worktree of the clone the tool acts on "
                         "(the tests' Fixture's dev clone), the message of a cleanup that did not finish reads "
                         "that worktree's HEAD, and held_elsewhere lists that clone's worktrees and takes refs/heads/ "
                         "off the head-name a worktree's git dir there holds; the refs/heads/ compositions name the "
                         "batch branch, main and a member's head branch by name, never the current branch, and "
                         "SHORT_NAME_RULES spells git's rev-parse rules, for the files a -B call opens; comments"),
    "scripts/pr-orphans.sh": ((NOT_A_READ,), "refs/heads/$MAIN names main by its name, not the current branch"),
    "scripts/release.sh": ((SYNTHETIC, NOT_A_READ),
                           "`git symbolic-ref -q --short HEAD` reads the branch of the clone above its own scripts/ "
                           "(it cds there); tests/release-sh.bats copies it into a repository its setup builds; "
                           "comments"),
    "scripts/sweep.py": ((SYNTHETIC, NOT_A_READ),
                         "cmd_run's and check's symbolic-ref read the BATCHER's HEAD (the repository --tree names), and "
                         "git_state lists the HEAD files of a leg's checkout; the tests' batchers are repositories they "
                         "build (tests/test_sweep_runner.py: World; tests/test_batch_tool.py: the Fixture's dev clone), "
                         "and every run there names --tree; the refs/heads/ test takes the branch's name off the ref "
                         "HEAD names there; the rest are docstrings and comments"),
    "tests/bootstrap-sh.bats": ((SYNTHETIC,), "rev-parse --abbrev-ref HEAD of the clone bootstrap.sh made in "
                                              "$HOME/romp from the origin setup builds ($ROMP_REPO)"),
    "tests/conftest.py": ((NOT_A_READ,), "GitHub's variable names in the set whose values a report need not hide "
                                         "(_ENV_VALUE_PUBLIC_NAMES); their values are not read as a branch"),
    "tests/fixtures/fake_gh.py": ((SYNTHETIC,), "refs/heads/<name> of the bare origin the batch Fixture builds, named "
                                                "by a PR's head or base branch, never the current branch"),
    "tests/fork-remotes.bats": ((NOT_A_READ,), "symbolic-ref writes HEAD in the repositories its setup builds"),
    "tests/gitleaks-config.bats": ((NOT_A_READ,), "symbolic-ref writes HEAD in the repository each case builds, "
                                                  "synth_repo's among them"),
    "tests/pr-orphans.bats": ((NOT_A_READ,), "symbolic-ref writes HEAD in the repository its setup builds"),
    "tests/pre-push-hook.bats": ((NOT_A_READ,),
                                 "symbolic-ref writes HEAD in the repository setup builds ($REPO); rewind_remote's "
                                 "update-ref of refs/heads/<ref> in its bare remote; the hook's "
                                 "for-each-ref over refs/remotes/ and refs/replace/ in the calls and texts a case "
                                 "expects, beside a refs/heads/ name (split_hits)"),
    "tests/pre-push-identity.bats": ((NOT_A_READ,), "symbolic-ref writes HEAD in the repository setup builds"),
    "tests/pre-push-message.bats": ((NOT_A_READ,), "symbolic-ref writes HEAD in the repository setup builds"),
    "tests/release-sh.bats": ((SYNTHETIC, NOT_A_READ),
                              "rev-parse --abbrev-ref HEAD of the repository setup builds ($REPO) and branch --list of "
                              "its origin; a write of HEAD there; a comment"),
    "tests/test_batch_tool.py": ((SYNTHETIC, NOT_A_READ),
                                 "the Fixture's clones and batch worktrees (Fixture.__init__): their branch, HEAD's "
                                 "file, local branches and worktree lists; git's rev-parse rules naming where the "
                                 "pins plant; comments and the calls the stop pins expect"),
    "tests/test_chat_build_sig_inputs.py": ((SYNTHETIC, NOT_A_READ),
                                            "the calls a stubbed Popen records while the kernel signs a session whose "
                                            "directory the test builds; a docstring"),
    "tests/test_ci_sdk_pin.py": ((NOT_A_READ,), "a workflow text the test parses, github.ref in an if: key"),
    "tests/test_ci_workflow_concurrency.py": ((NOT_A_READ,), "evaluates ci.yml's concurrency expression over github.ref "
                                                             "values it gives; reads no repository"),
    "tests/test_converge_main_branch.py": ((SYNTHETIC, NOT_A_READ), "symbolic-ref --short HEAD of the checkout setUp "
                                                                    "builds (self.checkout); a comment"),
    "tests/test_docs_workflow_pins.py": ((NOT_A_READ,), "an expected text: docs.yml's concurrency group, matched "
                                                        "against the workflow file's text; reads no repository"),
    "tests/test_env_value_redaction.py": ((NOT_A_READ,), "GitHub's variables set to values the test gives, in an "
                                                         "environment it builds, for the redaction of their values"),
    "tests/test_federated_linkdrop_mint.py": ((SYNTHETIC,), "git worktree list of the repository the case builds "
                                                            "(self.root, a mkdtemp)"),
    "tests/test_file_github.py": ((SYNTHETIC, NOT_A_READ), "a stub git that refuses --show-current, run in the "
                                                           "repository each case builds; comments"),
    "tests/test_git_fixture.py": ((SYNTHETIC,), "symbolic-ref --short HEAD of the repository the case inits"),
    "tests/test_git_pointer_file_bytes.py": ((SYNTHETIC, NOT_A_READ),
                                             "the kernel's _git_head_file and _git_branch, and rev-parse --abbrev-ref "
                                             "HEAD, over the repositories and worktrees each case builds; a docstring"),
    "tests/test_github_repo.py": ((SYNTHETIC, NOT_A_READ),
                                  "the forks a stubbed run records while the kernel reads the repositories each case "
                                  "builds, a write of HEAD in a bare one and its HEAD file's time; docstrings"),
    "tests/test_kernel.py": ((NOT_A_READ,), "a setting's label, Show git branch, in a comment and an assertion"),
    "tests/test_kernel_delta_send.py": ((SYNTHETIC, NOT_A_READ), "the HEAD files of the repositories the case builds; "
                                                                 "a docstring"),
    "tests/test_kernel_fork_burn.py": ((SYNTHETIC, NOT_A_READ), "the kernel's _git_head_file over the repositories and "
                                                                "worktrees the cases build; the module docstring"),
    "tests/test_kernel_remote_update.py": ((SYNTHETIC, NOT_A_READ),
                                           "refs/heads/<the peer-update branch> in the repositories the cases build, "
                                           "and in the pushes they expect"),
    "tests/test_sdk_kernel.py": ((READS, NOT_A_READ), "test_git_branch_derived_from_folder (READERS); comments"),
    "tests/test_sweep_runner.py": ((SYNTHETIC, NOT_A_READ),
                                   "the World's repository and the checkouts its runs make (World), and the "
                                   "repositories other cases build: their HEAD files, branches, worktree lists and "
                                   "refs; git's rev-parse rules naming where the pins plant; docstrings, comments and "
                                   "expected texts"),
    "tools/perf-bench.py": ((READS,), "git_head (READERS)"),
    "tools/romp-track-bash-guard-corpus.json": ((NOT_A_READ,),
                                                "command strings the guard judges, in its own scratch project "
                                                "(corpusWorld), never run"),
    "ui/webview/statusline-branch.test.ts": ((NOT_A_READ,), "a setting's label, Show git branch, in a pattern"),
    "ui/webview/tab-groups.test.ts": ((NOT_A_READ,), "a setting's label, Show git branch's, in a comment"),
}

CENSUS = Census(SPELLINGS, _CANDIDATE, SPLIT_SPELLINGS, _SPLIT_CANDIDATE, WINDOW, HITS, READS,
                "the current branch of the checkout the test runs in", "the current branch")


def spelled(line):
    """The SPELLINGS `line` carries, by what each is."""
    return CENSUS.spelled(line)


def census(root=ROOT, rels=None):
    """{path: [(line number, the line stripped)]}: every hit, by file, over the tracked text files at `root` (all but
    CENSUS_FILES)."""
    return CENSUS.census(root, rels)


def split_hits(scanned, each=None):
    """The runs of two up to WINDOW consecutive lines of `scanned` whose joined text carries a spelling of
    SPLIT_SPELLINGS that none of its lines, and no shorter run inside it, carries alone (Census.split_hits)."""
    return CENSUS.split_hits(scanned, each)


def judged(root=ROOT):
    """HITS as {path: [text]}, read from the tree at `root`; a missing or unreadable file is the test's own error."""
    return ref_reader_census.judged(root, HITS)


def census_problems(hits, judged, classified=None, readers=None):
    """Every finding of the census over `hits` against `judged` (HITS, as judged() reads it), `classified` and `readers`
    (default CLASSIFIED and READERS): Census.census_problems."""
    return CENSUS.census_problems(hits, judged, CLASSIFIED if classified is None else classified,
                                  READERS if readers is None else readers)


class Spellings(unittest.TestCase):
    """Each spelling the census looks for is matched on a line that carries it, and a line that carries none is not:
    a census whose patterns cannot see a spelling would pass with that spelling's readers unlisted."""

    CARRIES = (
        ("branch --show-current", 'git branch --show-current'),
        ("a listing that marks or holds the local branches", 'subprocess.run(["git", "branch", "--show-cur"], cwd=co)'),
        ("a listing that marks or holds the local branches", 'git -C "$repo" branch --sh'),
        ("a name rev-parse gives a revision", 'git rev-parse --abbrev-ref HEAD'),
        ("a name rev-parse gives a revision", 'git rev-parse --symbolic-full-name @{-1}'),
        ("symbolic-ref", 'git symbolic-ref --short HEAD'),
        ("symbolic-ref", 'r = git(repo, "symbolic-ref", "-q", "HEAD")'),
        ("a status that prints the branch", 'git status -sb'),
        ("a status that prints the branch", 'git -C "$R" status --porcelain=v2 --branch'),
        ("a status that prints the branch", 'git status --bra'),
        ("a status that prints the branch", 'subprocess.run(["git", "status", "-b", "--porcelain"])'),
        ("a line git prints with the branch's name", 'assert out.startswith("On branch ")'),
        ("a line git prints with the branch's name", 'if "HEAD detached at" in text:'),
        ("a line git prints with the branch's name", '[[ "$output" == *"Not currently on any branch"* ]]'),
        ("a line git prints with the branch's name", 'head = fields["branch.head"]'),
        ("name-rev", 'git name-rev --name-only HEAD'),
        ("describe over every ref", 'git describe --all --exact-match'),
        ("HEAD's file", 'cat .git/HEAD'),
        ("HEAD's file", 'with open(os.path.join(gitdir, "HEAD")) as f:'),
        ("HEAD's file", 'head = (Path(gd) / "HEAD").read_text()'),
        ("HEAD's file", 'read -r line < "$GIT_DIR/HEAD"'),
        ("HEAD's file", 'hp = git("rev-parse", "--git-path", "HEAD")'),
        ("HEAD's file", 'gi = _git_head_file(tree)'),
        ("HEAD's file", 'head = Path(ROOT, ".git", "HEAD").read_text()'),
        ("HEAD's file", 'head = ROOT.joinpath(".git", "HEAD").read_text()'),
        ("HEAD's file", "const head = fs.readFileSync(path.resolve(root, '.git', 'HEAD'), 'utf8');"),
        ("HEAD's file", 'with open(f"{gitdir}/HEAD") as f:'),
        ("HEAD's file", 'with open(gitdir + "/HEAD") as f:'),
        ("HEAD's file", 'cat "$(git rev-parse --git-dir)/HEAD"'),
        ("GitHub's ref variables", 'branch = os.environ.get("GITHUB_HEAD_REF") or os.environ["GITHUB_REF_NAME"]'),
        ("GitHub's ref variables", "if: github.ref == 'refs/heads/main'"),
        ("GitHub's ref variables", 'echo "${{ github.head_ref }}"'),
        ("the current branch's upstream or push", 'git rev-parse @{u}'),
        ("the current branch's upstream or push", 'git log HEAD@{Upstream}..'),
        ("a listing that marks or holds the local branches", 'git branch'),
        ("a listing that marks or holds the local branches", 'git branch -vv'),
        ("a listing that marks or holds the local branches", 'git -C "$R" branch --list "rel-*"'),
        ("a listing that marks or holds the local branches", 'git branch --points-at HEAD'),
        ("a listing that marks or holds the local branches", 'git branch --po HEAD'),
        ("a listing that marks or holds the local branches", 'subprocess.run(["git", "-C", co, "branch"])'),
        ("a listing that marks or holds the local branches", 'subprocess.run(["git", "branch", "--format=%(refname)"])'),
        ("a listing that marks or holds the local branches", 'git for-each-ref --format="%(HEAD) %(refname)"'),
        ("a listing that marks or holds the local branches", 'git for-each-ref refs/heads/'),
        ("a listing that marks or holds the local branches", 'git show-ref --heads'),
        ("a listing that marks or holds the local branches", 'git worktree list --porcelain'),
        ("a listing that marks or holds the local branches", 'git(wt, "worktree", "list")'),
        ("a decoration", 'git log --decorate --oneline -1'),
        ("a decoration", 'git log -1 --format=%D'),
        ("a decoration", "git log -1 --format='%D'"),
        ("a decoration", 'git log -1 --format="%d"'),
        ("a decoration", "git log -1 --pretty='%D'"),
        ("a decoration", "git log -1 --format='%(decorate)'"),
        ("a branch's name put before refs/heads/ or taken off it", 'ref = "refs/heads/" + name'),
        ("a branch's name put before refs/heads/ or taken off it", 'branch = head[len("refs/heads/"):]'),
        ("a branch's name put before refs/heads/ or taken off it", 'git rev-parse --verify "refs/heads/$MAIN"'),
        ("a branch's name put before refs/heads/ or taken off it", 'name="${ref#refs/heads/}"'),
    )
    CARRIES_NONE = (
        'git rev-parse HEAD',
        'git rev-parse --symbolic HEAD',
        'git rev-parse --show-toplevel',
        'git status --porcelain --untracked-files=no',
        'self.assertEqual(r["status"], "ok")',
        '[ "$status" -eq 0 ] && git checkout -q -b rel',
        'git branch topic',
        'git branch -d topic',
        'git branch -D batch/b1',
        'git checkout -b topic',
        'git describe --tags --exact-match',
        'head = "HEAD"',
        'git rev-parse --verify refs/heads/main',
        'os.environ["GITHUB_SHA"]',
        'GITHUB_REF_RE = /pull/',
        'git log -1 --format=%H',
        'git log -1 --format %D',
        'git worktree add --detach wt HEAD',
        'a branch on the board, said in prose',
        "['sudo --sh', 'sudo --sh'], ['numactl --show', 'x']",
    )

    def test_each_spelling_is_seen_and_a_line_with_none_is_not(self):
        for what, line in self.CARRIES:
            with self.subTest(line=line):
                self.assertIn(what, spelled(line), "the census does not see %s in %r" % (what, line))
        for line in self.CARRIES_NONE:
            with self.subTest(line=line):
                self.assertEqual(spelled(line), [], "%r carries no spelling of the current branch" % line)
        self.assertEqual(sorted({what for what, _ in self.CARRIES}), sorted(what for what, _ in SPELLINGS),
                         "every spelling has a line that carries it")

    def test_each_option_prefix_git_takes_is_seen_and_one_letter_less_is_not(self):
        """git 2.43.0 takes a long option of git branch, or of git status, cut to any prefix that names one option
        (measured 2026-10-03 by running each): the census sees each such prefix down to the shortest git takes, and not
        one letter less, which git refuses as ambiguous or unknown."""
        for option, shortest in (("--show-current", "--sh"), ("--list", "--l"), ("--all", "--al"),
                                 ("--remotes", "--rem"), ("--verbose", "--v"), ("--points-at", "--po"),
                                 ("--merged", "--mer"), ("--sort", "--so")):
            for k in range(len(shortest), len(option) + 1):
                with self.subTest(option=option[:k]):
                    self.assertIn("a listing that marks or holds the local branches",
                                  spelled("git branch %s" % option[:k]))
            with self.subTest(option=shortest[:-1]):
                self.assertNotIn("a listing that marks or holds the local branches",
                                 spelled("git branch %s x" % shortest[:-1]))
        for k in range(len("--b"), len("--branch") + 1):
            with self.subTest(option="--branch"[:k]):
                self.assertIn("a status that prints the branch", spelled("git status %s" % "--branch"[:k]))

    # A file whose spellings are each split across lines: an argument list over two lines and over three, a backslash
    # continuation, and a path joined over a line break; and two lines that print a status and a -b, which are not one.
    SPLIT = r"""subprocess.run(["git", "status",
                "-sb"], cwd=co)
subprocess.run(["git",
                "branch",
                "-v"])
git describe \
    --all
head = os.path.join(gitdir,
                    "HEAD")
print("a status")
print("-b is a flag of many tools")
"""

    def test_a_spelling_split_across_lines_is_seen_once_at_its_first_line(self):
        """split_hits joins up to WINDOW consecutive lines and names a run whose joined text carries a spelling that
        none of its lines, and no shorter run inside it, carries alone; the census adds each such run, by its first
        line's number and its lines joined by a space, beside the lines that carry a spelling themselves. Two lines that
        print a status and a -b are not such a run: the status spelling needs git's own words around them."""
        lines = list(enumerate(self.SPLIT.splitlines(), 1))
        self.assertEqual([n for n, line in lines if spelled(line)], [], "premise: no line carries a spelling alone")
        self.assertEqual(split_hits(lines), [
            (1, 'subprocess.run(["git", "status", "-sb"], cwd=co)'),
            (3, 'subprocess.run(["git", "branch", "-v"])'),
            (6, 'git describe \\ --all'),
            (8, 'head = os.path.join(gitdir, "HEAD")'),
        ])
        d = tempfile.mkdtemp(prefix="bnr-split-")
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "split.py"), "w") as f:
            f.write(self.SPLIT)
        self.assertEqual([n for n, _line in census(Path(d), ["tests/split.py"])["tests/split.py"]], [1, 3, 6, 8])

    def test_no_census_reads_the_census_files(self):
        """Each census reads none of the census files, its own and the other's modules and fixtures and the machinery
        they share, whose texts hold every spelling: this census and tests/test_origin_main_readers.py's, each over
        exactly those files, find nothing, though this file carries a spelling of each, and CENSUS_FILES names those
        files. Red when CENSUS_FILES leaves them out (the mutant mB-exclusion)."""
        from tests import test_origin_main_readers
        files = [HERE, HITS, test_origin_main_readers.HERE, test_origin_main_readers.HITS, "tests/ref_reader_census.py"]
        self.assertTrue(all(os.path.isfile(os.path.join(str(ROOT), rel)) for rel in files),
                        "premise: they are in the tree")
        with open(os.path.join(str(ROOT), HERE)) as f:
            text = f.read().splitlines()
        self.assertTrue(any(spelled(line) for line in text), "premise: this file carries a spelling of this census")
        self.assertTrue(any(test_origin_main_readers.spelled(line) for line in text),
                        "premise: this file carries a spelling of the origin/main census")
        self.assertEqual(census(ROOT, files), {})
        self.assertEqual(test_origin_main_readers.census(ROOT, files), {})
        self.assertEqual(sorted(CENSUS_FILES), sorted(files), "CENSUS_FILES names the census files and no other")


class Findings(unittest.TestCase):
    """census_problems names each kind of finding, over a small census of its own: a hit in a file CLASSIFIED does not
    name, a changed hit line, a classified file with no hit left, a file in one of CLASSIFIED and HITS and not the
    other, a READERS line no hit carries, and kinds and READERS that disagree; with none of them, nothing."""

    def test_each_finding_is_named(self):
        hits = {"a.py": [(1, "git branch --show-current")], "b.sh": [(3, "git symbolic-ref HEAD refs/heads/main")]}
        judged_ = {"a.py": ["git branch --show-current"], "b.sh": ["git symbolic-ref HEAD refs/heads/main"]}
        classified = {"a.py": ((READS,), "reads it"), "b.sh": ((NOT_A_READ,), "a write")}
        readers = (("a.py", "--show-current", "reads it"),)
        self.assertEqual(census_problems(hits, judged_, classified, readers), [], "premise: a census with no finding")
        cases = (
            ("an unclassified hit", dict(hits, **{"c.py": [(2, "git rev-parse --abbrev-ref HEAD")]}), judged_,
             classified, readers, "c.py: 1 line(s) no entry of CLASSIFIED covers"),
            ("a changed line", dict(hits, **{"b.sh": [(3, "git symbolic-ref --short HEAD")]}), judged_, classified,
             readers, "b.sh: hit lines not judged in %s" % HITS),
            ("a stale entry", {"a.py": hits["a.py"]}, judged_, classified, readers,
             "b.sh: in CLASSIFIED, and no line there carries a spelling of the current branch now"),
            ("a file judged and not classified", hits, dict(judged_, **{"d.py": ["x"]}), classified, readers,
             "d.py: in %s and not in CLASSIFIED" % HITS),
            ("a reader gone", dict(hits, **{"a.py": [(1, "git branch")]}), dict(judged_, **{"a.py": ["git branch"]}),
             classified, readers, "a.py: READERS lists a read of the current branch of the checkout"),
            ("kinds and READERS apart", hits, judged_, dict(classified, **{"b.sh": ((READS,), "x")}), readers,
             "b.sh: CLASSIFIED names READS, and READERS does not list it"),
        )
        for what, h, j, c, r, want in cases:
            with self.subTest(finding=what):
                named = census_problems(h, j, c, r)
                self.assertTrue(any(p.startswith(want) for p in named), "%s not named: %r" % (what, named))


class BranchNameReaders(unittest.TestCase):
    """The census over this tree, against READERS and CLASSIFIED (the module docstring)."""

    @classmethod
    def setUpClass(cls):
        cls.rels = tracked_files()
        cls.hits = census(ROOT, cls.rels)
        cls.judged = judged()

    def test_the_scan_reads_the_tree_and_finds_hits(self):
        self.assertIn(HERE, self.rels, "premise: this file is tracked, so the listing is this repository's")
        self.assertIn("kernel/kernel.py", self.hits, "the kernel reads a session directory's branch: a scan that finds "
                                                     "nothing there read nothing")
        self.assertTrue(self.hits, "an empty scan")

    def test_every_hit_is_classified_and_every_listed_reader_still_reads(self):
        problems = census_problems(self.hits, self.judged)
        if problems:
            self.fail("the census of the tests that read the current branch (the 22:25Z ruling of 2026-10-03 on PR "
                      "959, item 2):\n\n" + "\n\n".join(problems))

    def test_a_reader_in_place_of_a_judged_line_is_named_at_the_tree_level(self):
        """census_problems, which the test above runs over this tree, compares each file's hit lines with its judged
        lines line by line, never by their count: here this tree's hits with one judged hit line of scripts/sweep.py
        replaced by a reader, the file's count kept, and with a second copy of a judged line added, are each named,
        with the line."""
        path = "scripts/sweep.py"
        lines = list(self.hits[path])
        reader = "git branch --show-current"
        self.assertNotIn(reader, [line for _n, line in lines], "premise: the reader is not a judged line")
        swapped = dict(self.hits, **{path: [(lines[0][0], reader)] + lines[1:]})
        named = [p for p in census_problems(swapped, self.judged) if p.startswith(path + ":")]
        self.assertEqual(len(named), 1, named)
        self.assertIn(reader, named[0])
        doubled = dict(self.hits, **{path: lines + [lines[-1]]})
        named = [p for p in census_problems(doubled, self.judged) if p.startswith(path + ":")]
        self.assertEqual(len(named), 1, named)
        self.assertIn(pinned_text(lines[-1][1])[:200], named[0])

    def test_every_entry_says_why(self):
        for path, (kinds, why) in CLASSIFIED.items():
            with self.subTest(path=path):
                self.assertTrue(self.judged.get(path), "judged lines in %s" % HITS)
                self.assertTrue(kinds and set(kinds) <= {READS, SYNTHETIC, NOT_A_READ}, kinds)
                self.assertTrue(why.strip(), "a reason")
        for path, text, why in READERS:
            with self.subTest(path=path):
                self.assertTrue(text.strip() and why.strip(), "a line and a reason")


if __name__ == "__main__":
    unittest.main()
