#!/usr/bin/env python3
"""The tests that read the origin/main of the repository they run in, derived from the tree and pinned (round 1 of PR
959, ruling D), so a new one is noticed and judged.

Why it matters: each job's checkout in the local sweep holds refs/remotes/origin/main, at the commit the batcher's
origin/main named when the run started (scripts/sweep.py, make_checkout), and CI's job checkouts hold none except in a
run on main.
actions/checkout@v4, at its default depth 1 in every job a sweep leg stands in for, fetches the one commit as the
remote-tracking ref of the branch the run is on, so only a run on main itself holds origin/main, at the commit it
checks out. A test that reads the checkout's own origin/main can therefore behave differently in the sweep than in
CI, and the sweep is the landing gate for every member PR (docs/batching.md).

The census is a text scan. It reads every tracked file (`git ls-files` at the repository root) that is text (no NUL in
its first 8000 bytes, git's own test), whatever directory it is in, since a test runs code from tests/, scripts/,
.githooks/, bin/, kernel/, tools/, ui/ and more; of a Markdown file only the lines inside fenced code blocks, at any
indent, in a list item or a blockquote too, since a test runs a fenced block (tests/test_env_credential_names.py runs
one of docs/reference.md's) and never the prose around one; and none of the census files (CENSUS_FILES: this file and
HITS, tests/test_branch_name_readers.py and its fixture, and tests/ref_reader_census.py, the machinery the two censuses
share), which run `git ls-files` and nothing else, or run nothing, and whose texts hold every spelling the censuses look
for. A line is a hit when it carries a spelling git resolves to
refs/remotes/origin/main, or one a reader composes that ref from (SPELLINGS): the ref itself (origin/main,
refs/remotes/origin, remotes/origin, origin/HEAD); the upstream and push shorthands (@{u}, @{upstream}, @{push}, in any
case); a remote-tracking prefix with the remote composed (refs/remotes/ or remotes/ followed by anything but origin);
origin/ with the branch composed; /main with the remote composed; a spelling that reads every ref or every
remote-tracking ref, origin/main among them (--all, --remotes, --glob, for-each-ref, show-ref, name-rev, --decorate,
branch or show-branch with -a or -r, in any position or combined form, an argument list's included, or with --remotes
or --all cut to any prefix git accepts there: git 2.43 takes --rem and --al for branch, --rem and --a for show-branch,
and no prefix for log or rev-list); a decoration format or setting (%d or
%D in a --format or --pretty, log.decorate, a decorate setting); a reflog walk (--reflog, --walk-reflogs: origin/main's
reflog, which make_checkout's update-ref writes, among them); a commit-message search over every ref (:/<text>); the
repository itself named as the remote (an ls-remote, fetch or push of `.`); the loose ref file's path spelled by its
components ("remotes" as one); and the remote name origin bound to a name (assigned, returned, a default), for the
reader that joins it to a branch elsewhere ("%s/%s" % (REMOTE, MAIN) in scripts/batch.py, "$canonical/$REF" in
scripts/release.sh); the components may be joined by commas or by pathlib's /, "refs/remotes" may be one of them, and
a component may stand last on a line or before ] or } (a dict key, which a colon follows, and a subscript, which a
bracket precedes, are not components); a binding may wrap the value in parentheses.
A run of two or three consecutive lines is a hit too when its text, the lines joined, carries a spelling made of more
than one word that none of its lines carries alone (split_hits: an argument list split over lines, a backslash
continuation). A bare `origin` handed to git is not a spelling: git's rev-parse rules resolve it to
refs/remotes/origin/HEAD, never to origin/main, and a fetch, a push or an ls-remote that names a remote reads that
remote, which no sweep checkout has; one that names `.` reads the repository's own refs, origin/main among them. What
the scan cannot see: a remote name reaching a composition through a positional argument or any other route than a
binding; an ls-remote, fetch or push that names the repository by its path (a variable, or a path other than `.`), which
reads its own refs as `.` does and cannot be told from a remote name by its text; a git subcommand or flag assembled at
run time; a spelling split over more than three lines; a reader that is a judged line moved to another place in its
file (a read moved from a test into code it runs in the same file, or back), since each file's hit lines are compared
with its judged lines by their text, as many times as each appears, wherever they stand; and code that is not tracked
(node_modules, a venv's packages).

Every hit is classified, by file (CLASSIFIED: the kinds of its hits and why), and pinned by its text (HITS, a JSON file
of each classified file's judged hit lines, stripped, as many times as each appears): READS, a line of a test, or of
code a test runs, that reads the checkout's own origin/main (READERS names each such line); SYNTHETIC, a read of the
origin/main, or of the remote-tracking refs, of a repository the test or the code under test builds, which the entry
names; and NOT_A_READ, prose, a message, an expected text, a write, a command string that is never run, a read of
configuration, or a command that is not git. The pin fails, naming each one, on a hit in a file CLASSIFIED does not
name; a hit line in a classified file that HITS does not hold, or a judged line no longer there, each named (a line
changed, added or gone, a second copy of a judged line among them, so a mention replaced by a reader in the same file is
seen, where a count of hits per file kept the same number); a READERS line no hit carries any longer (that reader no
longer reads, or moved); a CLASSIFIED file with no hit left; a file in one of CLASSIFIED and HITS and not the other; and
an empty scan (census_problems, which compares the lines, never their count; its tree-level pin holds that). The
classification was confirmed by execution where the text did not settle it: the modules and bats files that run
scripts/batch.py, scripts/pr-orphans.sh, scripts/release.sh, the kernel's release and GitHub-link probes and
scripts/sweep.py were run in a checkout make_checkout made, with a git first on PATH logging each call made through it,
and none read that checkout's origin/main, nor any ref of it but HEAD (2026-10-03).

At this head three tests read the checkout's own origin/main (READERS), all brought by the merge of fork main through
fork PR 926's merge of it. The history case of tests/gitleaks-config.bats (fork PR 954) calls history_scan_range on
the checkout: in CI's depth-1 checkout its shallow test comes first and it scans the one commit, whatever refs are
there; in a sweep checkout that holds origin/main it scans the commits HEAD adds over it; in one that holds none it
scans all of HEAD's history, which can take longer than the 180 s the bats leg allows a test. The verdict on a clean
branch is a pass in each; the commits read, and the time, differ, and the sweep's checkouts hold origin/main for this
case. tools/markdown-viewer-plan-linknav.test.mjs and ui/webview/linknav-records-attribution.test.ts (fork PR 862)
read the merge-base of HEAD with it for a gate that holds their delta checks off unless origin/main is known, the
merge-base is not origin/main itself, and the diff since the merge-base adds the module. In CI the gate holds them
with "no origin/main"; in a sweep checkout it holds them too, naming another part, on every head whose diff since the
merge-base does not add the module, which since the module landed on main is every head that has it from main. Run on
2026-10-04 in a checkout make_checkout made of this merge, with origin/main at fork main's tip, the history case
scanned the commits HEAD adds over origin/main, and both gates held with "the merge-base is origin/main"; in one with
no origin/main the history case's range was all of HEAD's history, which passed in one run and went past the 180 s in
another, and both gates held with "no origin/main".
"""
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tests import ref_reader_census
from tests.ref_reader_census import (HEX_RUN, NOT_A_READ, SYNTHETIC, Census, pinned_text, scanned_lines, tracked_files,
                                     unpinned)

ROOT = Path(__file__).resolve().parent.parent
HERE = "tests/test_origin_main_readers.py"
# {path: [each judged hit line, stripped, as pinned_text gives it, sorted]}: the lines of each CLASSIFIED file judged so
# far, written with json.dump(..., ensure_ascii=True, sort_keys=True, indent=1), so the tree stays ASCII. It holds every
# spelling, so the census reads it no more than it reads this file (CENSUS_FILES).
HITS = "tests/fixtures/origin-main-hits.json"

# A branch listing of every remote-tracking ref or every ref: git branch, or git show-branch, with -r or -a among its
# short options, or --remotes or --all spelled out or cut to a prefix git accepts (git 2.43.0, 2026-10-03, by running
# each: branch takes --rem to --remotes and --al to --all, show-branch --rem to --remotes and --a to --all; log and
# rev-list take no abbreviation, so the spellings below match those options whole).
_BRANCH_LISTING = (r"\bbranch\b(?=[^\n]*?(?:^|[\s\"'`,\[(])"
                   r"(?:-[A-Za-z]*[ar][A-Za-z]*|--rem(?:o(?:t(?:es?)?)?)?|--a(?:ll?)?)(?![\w-]))")
# (what it is, the pattern): every spelling the census looks for, each matched anywhere in a line.
SPELLINGS = (
    ("the ref", re.compile(r"origin/main|refs/remotes/origin|remotes/origin|origin/HEAD")),
    ("an upstream or push shorthand", re.compile(r"@\{(?:u|upstream|push)\}", re.IGNORECASE)),
    ("a remote-tracking prefix with the remote composed", re.compile(r"(?<![\w.-])(?:refs/)?remotes/(?!origin\b)")),
    ("origin/ with the branch composed", re.compile(r"\borigin/(?=[$%{*\"'`+(\[])")),
    ("/main with the remote composed",
     re.compile(r"(?:%s|%\(\w+\)s|\}|\$\w+|\$\{[^}]*\})/main(?![\w.-])|[\"'`]/main(?![\w.-])")),
    ("a read of every ref or every remote-tracking ref",
     re.compile(r"--(?:remotes|all|glob)(?![\w-])|for-each-ref|show-ref|name-rev|--decorate(?![\w-])|"
                + _BRANCH_LISTING)),
    ("a decoration format or setting",
     re.compile(r"(?:--(?:format|pretty)=|\bt?format:)[^\s\"'`]*%(?:[dD]|\(decorate)|\blog\.decorate\b|\bdecorate\s*=")),
    ("a reflog walk", re.compile(r"--reflog\b|--walk-reflogs\b")),
    ("a commit-message search over every ref", re.compile(r"\bgit\b[^\n]*(?:^|[\s\"'`=,(\[]):/(?!/)")),
    ("the repository itself named as the remote",
     re.compile(r"\b(?:ls-remote|fetch|push)(?:\s+-[-\w=]+)*\s+[\"'`]?\.(?:git)?(?=[\"'`]?(?:\s|$|[|;)]))"
                r"|[\"'](?:ls-remote|fetch|push)[\"'](?:\s*,\s*[\"']-[-\w=]+[\"'])*\s*,\s*[\"']\.(?:git)?[\"']")),
    ("the ref by path components", re.compile(r"(?<!\[)[\"'](?:refs/)?remotes[\"'](?!\w|\s*:)")),
    ("origin bound as a remote name",
     re.compile(r"(?:(?<![=!<>])=\s*|\breturn\s+|\bor\s+|\belse\s+)(?:\(\s*)?[\"'`]origin[\"'`]"
                r"|(?:\becho\s+|:-|(?<=[A-Za-z_])=)origin(?=[\s;}\"']|$)")),
)
# Every line a spelling can match holds one of these, so the lines that hold none are not matched against SPELLINGS.
_CANDIDATE = re.compile(r"origin|remotes|@\{|/main|--all|--glob|for-each-ref|show-ref|name-rev|decorate|branch"
                        r"|%|reflog|:/|ls-remote|fetch|push", re.IGNORECASE)
# The most consecutive lines split_hits joins to read a spelling written across them: an argument list over three lines
# (["git",\n "branch",\n "-r"]) is the longest such shape the census looks for.
WINDOW = 3
# The spellings made of more than one word, which a line break can split (a subcommand and its arguments, a name bound
# to a value, a path's components), as split_hits reads them; each other spelling is one word, seen or not in the line
# that holds it. A run of lines holds a word of one of them (_SPLIT_CANDIDATE), in some line, before it is joined.
SPLIT_SPELLINGS = (("a read of every ref or every remote-tracking ref", re.compile(_BRANCH_LISTING)),) + tuple(
    (what, rx) for what, rx in SPELLINGS if what in ("a commit-message search over every ref",
                                                     "the repository itself named as the remote",
                                                     "the ref by path components", "origin bound as a remote name"))
_SPLIT_CANDIDATE = re.compile(r"branch|:/|fetch|push|ls-remote|remotes|origin")

READS = "reads the checkout's origin/main"

# The lines that read the checkout's own origin/main: (path, text the line holds, why). Each one's file is in
# CLASSIFIED too, with READS among its kinds (the module docstring says how each behaves in the sweep and in CI).
READERS = (
    ("tests/gitleaks-config.bats",
     'if git -C "$repo" rev-parse --verify --quiet refs/remotes/origin/main > /dev/null; then',
     "history_scan_range, which the history case calls on ROMP_DIR, the checkout: past the shallow test, a clone with "
     "origin/main gets the commits HEAD adds over it, and one without gets all of HEAD's history"),
    ("tests/gitleaks-config.bats", "ref=refs/remotes/origin/main name=origin/main",
     "history_scan_range's name for the ref that its merge-base HEAD \"$ref\" and rev-parse --verify \"$ref\" then read "
     "in the same repository, the checkout under the history case"),
    ("tools/markdown-viewer-plan-linknav.test.mjs",
     "base = git('merge-base', 'origin/main', 'HEAD'); main = git('rev-parse', 'origin/main');",
     "deltaOf, which gated calls on REPO, the checkout, for the gate over L6's checks keyed on the delta: with no "
     "origin/main it holds them (CI), and in a sweep checkout it holds them unless the diff since the merge-base adds "
     "the module"),
    ("ui/webview/linknav-records-attribution.test.ts",
     'base = git("merge-base", "origin/main", "HEAD"); main = git("rev-parse", "origin/main");',
     "roadTwo, which the road test calls on REPO, the checkout, for the gate over road 2: with no origin/main it holds "
     "it (CI), and in a sweep checkout it holds it unless the diff since the merge-base adds the module"),
)

# path: (the kinds its hits are, why): every file with a hit; HITS holds the lines judged.
CLASSIFIED = {
    ".githooks/pre-push": ((SYNTHETIC, NOT_A_READ),
                           "`--not --remotes` and `for-each-ref --contains ... refs/remotes/` read every remote-tracking "
                           "ref of the repository the hook runs in; the tests run it in a repository they build "
                           "(tests/pre-push*.bats: _hook_in \"$REPO\", setup's `git -C \"$REPO\" init`; "
                           "tests/gitleaks-config.bats and tests/install-sh.bats copy it into $WORK/.git/hooks); the "
                           "rest are comments and the refs/replace/ listing's message"),
    ".github/workflows/ci.yml": ((SYNTHETIC, NOT_A_READ),
                                 "the secrets job's history scan, `--all`, which GitHub runs in CI's full-depth checkout "
                                 "and no sweep leg runs; tests/gitleaks-config.bats runs its arguments over a repository "
                                 "the case builds ($R); and comments"),
    ".github/workflows/secret-scan.yml": ((NOT_A_READ,), "the same history scan, which GitHub alone runs"),
    "kernel/kernel.py": ((SYNTHETIC, NOT_A_READ),
                         "_release_remote returns origin, and its users name the remote to ls-remote, fetch and the "
                         "update script, which read no local ref; _origin_has_branch reads refs/remotes/origin/<ref> in "
                         "a viewed file's own repository only after `git remote get-url origin` succeeds there "
                         "(_file_github_link), which no sweep checkout passes, having no remote, and its tests build "
                         "that repository (tests/test_file_github.py); _origin_tracks compares the composed name with "
                         "configuration; the rest are docstrings, comments and a message"),
    "kernel/sdk_backend.py": ((NOT_A_READ,), "systemctl's --all, not git; and comments naming a transport's attach "
                                             "branch and, two lines on, the -refused rows (split_hits)"),
    "scripts/batch.py": ((SYNTHETIC, NOT_A_READ),
                         "REMOTE, in MAIN_REF and remote_ref (full refs) and in remote_main (messages), and listed "
                         "under refs/remotes/origin/batch/, is read in the batch tool's clone, as is every ref listed "
                         "before a call that runs that clone's hooks (_refs_listed) (ROMP_BATCH_REPO, else the "
                         "directory above its scripts/); the tests run it in a clone they build "
                         "(tests/test_batch_tool.py: Fixture.__init__ copies it into its dev clone, or ROMP_BATCH_REPO "
                         "names a built repository), and its runs of this checkout's copy print help or meet a planted "
                         "git first; the rest are docstrings and messages"),
    "scripts/fork-remotes.sh": ((NOT_A_READ,), "comparisons of configuration values with origin; and a comment naming "
                                               "a per-branch push beside the next line's `read -r` (split_hits)"),
    "scripts/pr-orphans.sh": ((SYNTHETIC, NOT_A_READ),
                              "reads refs/remotes/origin/$MAIN in the clone above its own scripts/ (it cds there); "
                              "tests/pr-orphans.bats copies it into a repository its setup builds, and batch.py's finish "
                              "runs the copy in the test fixture's clone; and a comment"),
    "scripts/release.sh": ((SYNTHETIC, NOT_A_READ),
                           "canonical_remote's origin, joined to the branch in `git merge --ff-only \"$canonical/$REF\"`, "
                           "is read in the clone above its own scripts/ (it cds there); tests/release-sh.bats copies it "
                           "into a repository its setup builds; and comments"),
    "scripts/sweep.py": ((SYNTHETIC, NOT_A_READ),
                         "main_ref_checked and main_snapshot read the BATCHER's origin/main (the repository --tree names) "
                         "and make_checkout writes it into each job's checkout; the tests' batchers are repositories they "
                         "build (tests/test_sweep_runner.py: World, MainSnapshot.setUp; tests/test_batch_tool.py: the "
                         "Fixture's dev clone); the rest are docstrings, comments and messages"),
    "scripts/upstream-ledger.py": ((NOT_A_READ,), "a docstring naming git URLs beside the regular expression that "
                                                  "parses one (its [:/]); it runs no git (split_hits)"),
    "tests/bootstrap-sh.bats": ((NOT_A_READ,), "compares `git remote` of the clone made from the built origin "
                                                  "($ROMP_REPO, setup) with origin: configuration"),
    "tests/fork-remotes.bats": ((NOT_A_READ,), "configuration values of the clone its setup builds, and a comment"),
    "tests/gitleaks-config.bats": ((READS, SYNTHETIC, NOT_A_READ),
                                   "history_scan_range reads origin/main of the repository it is given, and the history "
                                   "case gives it ROMP_DIR, the checkout (READERS); the range's cases give it the "
                                   "repositories they build ($R, $S, $U), where they write, delete and read origin/main "
                                   "(synth_origin_main, update-ref, merge-base), and `--all` runs over the repository "
                                   "each case builds ($R); the rest are comments, the scopes history_scan_range states, "
                                   "case titles and expected texts"),
    "tests/pr-orphans.bats": ((NOT_A_READ,), "a case title and an expected text"),
    "tests/pre-push-hook.bats": ((SYNTHETIC, NOT_A_READ),
                                 "every git call in the repository setup builds ($REPO) or its bare remote, "
                                 "rewind_remote's update-ref of origin/<ref> there among them; comments, expected "
                                 "texts, test titles, and the shell lines the one-shot cases plant for the hook's read "
                                 "census, whose read -r is bash's, not git's, beside a branch their texts name"),
    "tests/pre-push-identity.bats": ((SYNTHETIC, NOT_A_READ), "the repository setup builds ($REPO), and a test title "
                                                              "naming a branch two lines above a `git tag -a` there "
                                                              "(split_hits)"),
    "tests/pre-push-message.bats": ((SYNTHETIC,), "the repository setup builds ($REPO)"),
    "tests/release-sh.bats": ((SYNTHETIC, NOT_A_READ), "the stub's push in the repository setup builds; comments"),
    "tests/test_batch_tool.py": ((SYNTHETIC, NOT_A_READ),
                                 "the Fixture's bare origin and its clones (Fixture.__init__), git's rev-parse rules "
                                 "among them naming where the batch pins plant in a Fixture's clone (REV_PARSE_RULES); "
                                 "expected texts"),
    "tests/test_ci_secret_scan.py": ((NOT_A_READ,), "reads ci.yml's text; runs no git"),
    "tests/test_codex_backend.py": ((NOT_A_READ,), "comments naming origin/main as the code before a fix"),
    "tests/test_converge_declined.py": ((SYNTHETIC,), "_release_remote stubbed, ROOT the clone setUp builds"),
    "tests/test_converge_main_branch.py": ((SYNTHETIC, NOT_A_READ),
                                           "_release_remote stubbed, ROOT the clone setUp builds; an expected text"),
    "tests/test_federated_linkdrop_served.py": ((NOT_A_READ,), "a comment"),
    "tests/test_file_github.py": ((SYNTHETIC, NOT_A_READ),
                                  "the repository each case builds (self.tmp), and refspec strings handed to "
                                  "_origin_tracks"),
    "tests/test_github_repo.py": ((NOT_A_READ,), "comments: a clone's branch named two lines above an `rm -rf` "
                                                 "(split_hits)"),
    "tests/test_kernel_names.py": ((NOT_A_READ,), "comments naming origin/main as the code before a fix"),
    "tests/test_kernel_order.py": ((NOT_A_READ,), "comments and a docstring"),
    "tests/test_kernel_session_flags.py": ((NOT_A_READ,), "a comment and a docstring"),
    "tests/test_kernel_update.py": ((SYNTHETIC, NOT_A_READ),
                                    "_release_remote stubbed, with ROOT the install clone _repos builds or every "
                                    "subprocess swallowed; the old banner's walk run in that clone; a comment"),
    "tests/test_land_sh.py": ((NOT_A_READ,), "an expected text"),
    "tests/test_main_drift_notice.py": ((NOT_A_READ,),
                                        "a docstring, and asserts that the kernel composes no <remote>/main and that no "
                                        "checkout argument names one"),
    "tests/test_manager_write_token.py": ((NOT_A_READ,), "_release_remote stubbed with every subprocess swallowed"),
    "tests/test_notify_bells.py": ((NOT_A_READ,), "a comment and a docstring"),
    "tests/test_peer_payloads_as_text.py": ((NOT_A_READ,), "a comment"),
    "tests/test_postal_peers.py": ((NOT_A_READ,), "docstrings"),
    "tests/test_postal_token.py": ((NOT_A_READ,), "a docstring"),
    "tests/test_reader_stream_peak.py": ((NOT_A_READ,), "a comment"),
    "tests/test_sdk_rename_ping.py": ((NOT_A_READ,), "comments"),
    "tests/test_sweep_runner.py": ((SYNTHETIC, NOT_A_READ),
                                   "the World's repository and the checkouts its runs make (World), MainSnapshot's "
                                   "repository (setUp), and the fake legs' git calls, each in its own World checkout, the "
                                   "loose ref file's path spelled by its components among them, read or planted in those "
                                   "repositories; docstrings, comments and expected texts"),
    "tests/test_timeline_dismissals.py": ((NOT_A_READ,), "comments, docstrings and messages naming origin/main as the "
                                                             "code before a fix"),
    "tests/test_update_banner_confirm_served.py": ((NOT_A_READ,), "a comment"),
    "tools/markdown-viewer-plan-gate-adopt.test.mjs": ((NOT_A_READ,), "a recorded document's text"),
    "tools/markdown-viewer-plan-linknav-review.test.mjs": ((NOT_A_READ,), "an expected text, the plan's L6 sentence, "
                                                                          "which names a git command"),
    "tools/markdown-viewer-plan-linknav.test.mjs": ((READS, SYNTHETIC, NOT_A_READ),
                                                    "deltaOf reads origin/main and the merge-base with it in the "
                                                    "repository it is given, and gated gives it REPO, the checkout "
                                                    "(READERS); the gate's case gives it a temporary repository it "
                                                    "builds and writes origin/main there (update-ref); the rest are "
                                                    "comments, the gate's held texts, test titles and assertions on the "
                                                    "plan's text, on the workflows' text and on gateOf's answers"),
    "tools/romp-track-bash-guard-corpus.json": ((NOT_A_READ,),
                                                "a command string the guard judges, in its own scratch project "
                                                "(corpusWorld), never run"),
    "tools/upstream-ledger-figure-gate-before-adoption.test.mjs": ((NOT_A_READ,), "a docstring on recorded output"),
    "tools/viewer-resize-summarize.mjs": ((NOT_A_READ,), "a report's text"),
    "ui/webview/file-comments-markclick-controls.test.ts": ((NOT_A_READ,), "a comment"),
    "ui/webview/linknav-records-attribution.test.ts": ((READS, SYNTHETIC, NOT_A_READ),
                                                       "roadTwo reads origin/main and the merge-base with it in the "
                                                       "repository it is given, and the road test gives it REPO, the "
                                                       "checkout (READERS); the gate's case gives it a temporary "
                                                       "repository it builds and writes origin/main there (update-ref); "
                                                       "the rest are comments, the gate's type and held texts, test "
                                                       "titles and assertions on gateOf's answers"),
    "upstream/2026-09-20-pre-push-tag-read-fail-closed.md": ((NOT_A_READ,),
                                                             "an awk program quoted in a fenced block, run by no test"),
}


CENSUS = Census(SPELLINGS, _CANDIDATE, SPLIT_SPELLINGS, _SPLIT_CANDIDATE, WINDOW, HITS, READS,
                "the origin/main of the checkout the test runs in", "origin/main")


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
        ("the ref", 'git rev-parse --verify origin/main'),
        ("the ref", 'git -C "$repo" merge-base HEAD refs/remotes/origin/main'),
        ("the ref", 'git log remotes/origin/main..HEAD'),
        ("the ref", 'git symbolic-ref refs/remotes/origin/HEAD'),
        ("an upstream or push shorthand", 'git rev-parse @{u}'),
        ("an upstream or push shorthand", 'git log HEAD@{UPSTREAM}..'),
        ("an upstream or push shorthand", 'git rev-parse @{push}'),
        ("a remote-tracking prefix with the remote composed", 'ref = "refs/remotes/%s/%s" % (remote, branch)'),
        ("a remote-tracking prefix with the remote composed", 'git for-each-ref refs/remotes/'),
        ("origin/ with the branch composed", 'ref="origin/$MAIN"'),
        ("origin/ with the branch composed", 'base = "origin/" + name'),
        ("/main with the remote composed", 'git merge --ff-only "${canonical}/main"'),
        ("/main with the remote composed", 'return "%s/main" % remote'),
        ("a read of every ref or every remote-tracking ref", 'git rev-list "$1" --not --remotes'),
        ("a read of every ref or every remote-tracking ref", 'git log -p --all'),
        ("a read of every ref or every remote-tracking ref", 'git branch -a'),
        ("a read of every ref or every remote-tracking ref", 'git for-each-ref --format=%(refname)'),
        ("a read of every ref or every remote-tracking ref", 'subprocess.run(["git", "branch", "-r"], cwd=co)'),
        ("a read of every ref or every remote-tracking ref", 'git branch -v -r'),
        ("a read of every ref or every remote-tracking ref", 'git branch -rv'),
        ("a read of every ref or every remote-tracking ref", 'git branch --list -r'),
        ("a decoration format or setting", 'git log -1 --format=%D'),
        ("a decoration format or setting", '["git", "log", "--pretty=format:%h%d"]'),
        ("a decoration format or setting", 'git -c log.decorate=short log -1'),
        ("a reflog walk", 'git rev-list --reflog'),
        ("a reflog walk", 'git log --walk-reflogs'),
        ("a commit-message search over every ref", 'git rev-parse ":/fix the thing"'),
        ("the repository itself named as the remote", 'git ls-remote . | grep main'),
        ("the repository itself named as the remote", 'git -C "$repo" fetch -q . "$ref":refs/heads/copied'),
        ("the repository itself named as the remote", 'git push . HEAD:refs/heads/x'),
        ("the repository itself named as the remote", 'subprocess.run(["git", "ls-remote", "."])'),
        ("the ref by path components", 'os.path.join(root, ".git", "refs", "remotes", "origin", "main")'),
        ("the ref by path components", 'ref = ROOT / ".git" / "refs" / "remotes" / "origin" / "main"'),
        ("the ref by path components", 'ref = Path(git_dir) / "refs/remotes" / "origin" / "main"'),
        ("the ref by path components", 'remotes = Path(co) / ".git" / "refs" / "remotes"'),
        ("the ref by path components", 'base = Path(co, ".git") / "refs/remotes"'),
        ("the ref by path components", 'parts = [gd, "refs", "remotes"]'),
        ("a read of every ref or every remote-tracking ref", 'git branch --rem'),
        ("a read of every ref or every remote-tracking ref", 'git branch --remote'),
        ("a read of every ref or every remote-tracking ref", 'git branch --al'),
        ("a read of every ref or every remote-tracking ref", 'git show-branch --remote'),
        ("a read of every ref or every remote-tracking ref", 'subprocess.run(["git", "show-branch", "--a"])'),
        ("origin bound as a remote name", 'REMOTE = "origin"'),
        ("origin bound as a remote name", '    return "origin"'),
        ("origin bound as a remote name", 'REMOTE = ( "origin"'),
        ("origin bound as a remote name", 'printf \'%s\\n\' "${p:-origin}"'),
        ("origin bound as a remote name", 'then echo upstream; else echo origin; fi'),
    )
    CARRIES_NONE = (
        'git push -q origin main',
        'git fetch origin',
        'headers.get("origin")',
        'self.assertEqual(em.author_of(text, origin=origin), "teammate")',
        'git rev-parse --verify refs/heads/main',
        'import { main } from "./main.js"',
        'git --all-open',
        'print("%d items" % n)',
        'git branch -d topic',
        'git branch --abbrev=7 topic',
        'git branch --list "remote-*"',
        'git ls-remote --tags origin',
        'git push -q origin HEAD:refs/heads/x',
        'git fetch ./other main',
        'assert.match(KERNEL, /if p == "merged":/)',
        'json.dump({"remotes": {"peer": {"ok": True}}}, fh)',
        'self.assertEqual(c["remotes"], [])',
    )

    def test_each_spelling_is_seen_and_a_line_with_none_is_not(self):
        for what, line in self.CARRIES:
            with self.subTest(line=line):
                self.assertIn(what, spelled(line), "the census does not see %s in %r" % (what, line))
        for line in self.CARRIES_NONE:
            with self.subTest(line=line):
                self.assertEqual(spelled(line), [], "%r carries no spelling of origin/main" % line)
        self.assertEqual(sorted({what for what, _ in self.CARRIES}), sorted(what for what, _ in SPELLINGS),
                         "every spelling has a line that carries it")

    # A file whose spellings are each split across lines (round 1 of PR 959's spot-check, S5): argument lists over two
    # lines and over three, a backslash continuation, and a keyword argument bound across a line break; and two lines
    # that name a branch and print -r, which the census reads as a run like any other.
    SPLIT = r"""subprocess.run(["git", "branch",
                "-r"], cwd=co)
subprocess.run(["git", "branch",
                "--list",
                "-a"])
out = subprocess.run(["git",
                      "fetch",
                      "."])
git branch \
    -a
configure(remote=
          "origin")
print("a branch")
print("-r is not here")
"""

    def test_a_spelling_split_across_lines_is_seen_once_at_its_first_line(self):
        """split_hits joins up to WINDOW consecutive lines and names a run whose joined text carries a spelling that
        none of its lines, and no shorter run inside it, carries alone; the census adds each such run, by its first
        line's number and its lines joined by a space, beside the lines that carry a spelling themselves. Two lines
        that name a branch and print -r are such a run too: the census reads text, and a run is judged like any hit.
        Red under a census that scans each line alone (the head before S5)."""
        lines = list(enumerate(self.SPLIT.splitlines(), 1))
        self.assertEqual([n for n, line in lines if spelled(line)], [], "premise: no line carries a spelling alone")
        self.assertEqual(split_hits(lines), [
            (1, 'subprocess.run(["git", "branch", "-r"], cwd=co)'),
            (3, 'subprocess.run(["git", "branch", "--list", "-a"])'),
            (7, '"fetch", "."])'),
            (9, 'git branch \\ -a'),
            (11, 'configure(remote= "origin")'),
            (13, 'print("a branch") print("-r is not here")'),
        ])
        d = tempfile.mkdtemp(prefix="omr-split-")
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "split.py"), "w") as f:
            f.write(self.SPLIT)
        self.assertEqual([n for n, _line in census(Path(d), ["tests/split.py"])["tests/split.py"]],
                         [1, 3, 7, 9, 11, 13])

    def test_markdown_is_read_inside_fenced_blocks_alone(self):
        text = ("prose naming origin/main\n````bash\ngit rev-parse origin/main\n```\nstill inside, origin/main\n"
                "````\nafter naming origin/main\n~~~\ngit log --all\n~~~\n")
        self.assertEqual([(n, line) for n, line in scanned_lines("docs/x.md", text) if spelled(line)],
                         [(3, "git rev-parse origin/main"), (5, "still inside, origin/main"), (9, "git log --all")],
                         "a fence of three backticks inside one of four is text, and the prose outside both is not read")
        self.assertEqual(len(scanned_lines("tests/x.py", text)), len(text.splitlines()), "every line of anything else")

    def test_a_fence_in_a_list_item_or_a_blockquote_is_read(self):
        # the test that runs a fenced block finds it with an unanchored search (tests/test_env_credential_names.py), so a
        # block indented four spaces under a list item (as docs/install.md has one) or behind quote marks is a block a
        # test can run
        text = ("- a step\n\n    ```bash\n    git merge-base HEAD origin/main\n    ```\nprose origin/main\n"
                "> ```\n> git log origin/main\n> ```\nbetween, origin/main\n- ```bash\n  git rev-parse origin/main\n  ```\n"
                "after, origin/main\n")
        self.assertEqual([n for n, line in scanned_lines("docs/x.md", text) if spelled(line)], [4, 8, 12],
                         "the fenced lines under a list item, behind quote marks and on a list marker's line, and no prose")


class Pinned(unittest.TestCase):
    """unpinned, the comparison of a file's hit lines with its judged lines: a count of hits per file kept the same
    number when a mention was replaced by a reader in the same file, or a read was added to a line that already carried
    a hit, so a new reader passed (round 1 of PR 959's build review, census-2 and vt-2)."""

    def test_a_changed_line_and_a_second_copy_are_named(self):
        judged = ["# the code before the fix read origin/main", "git log origin/main..HEAD", "git log origin/main..HEAD"]
        self.assertEqual(unpinned(list(reversed(judged)), judged), ([], []), "the judged lines, in any order")
        swapped = ["git merge-base HEAD origin/main"] + judged[1:]
        self.assertEqual(unpinned(swapped, judged), (["git merge-base HEAD origin/main"], [judged[0]]),
                         "a mention replaced by a reader, the count kept: named as added and as gone")
        self.assertEqual(unpinned(judged + [judged[1]], judged), ([judged[1]], []),
                         "a second copy of a judged line is named as added")
        self.assertEqual(pinned_text("tree %s = origin/main, x%s and %s" % ("f" * 12, "f" * 8, "f" * 6)),
                         "tree %s = origin/main, x%s and %s" % (HEX_RUN, "f" * 8, "f" * 6),
                         "a standalone run of seven hex digits or more is written as HEX_RUN, and no other")


class OriginMainReaders(unittest.TestCase):
    """The census over this tree, against READERS and CLASSIFIED (the module docstring)."""

    @classmethod
    def setUpClass(cls):
        cls.rels = tracked_files()
        cls.hits = census(ROOT, cls.rels)
        cls.judged = judged()

    def test_the_scan_reads_the_tree_and_finds_hits(self):
        self.assertIn(HERE, self.rels, "premise: this file is tracked, so the listing is this repository's")
        self.assertIn("scripts/sweep.py", self.hits, "the runner itself spells origin/main: a scan that finds nothing "
                                                     "there read nothing")
        self.assertTrue(self.hits, "an empty scan")

    def test_every_hit_is_classified_and_every_listed_reader_still_reads(self):
        problems = census_problems(self.hits, self.judged)
        if problems:
            self.fail("the census of the tests that read origin/main (round 1 of PR 959, ruling D):\n\n"
                      + "\n\n".join(problems))

    def test_a_reader_in_place_of_a_judged_line_is_named_at_the_tree_level(self):
        """census_problems, which the test above runs over this tree, compares each file's hit lines with its judged
        lines line by line (unpinned), never by their count: here this tree's hits with one judged hit line of
        scripts/sweep.py replaced by a reader, the file's count kept, and with a second copy of a judged line added, are
        each named, with the line. Red under census_problems comparing counts (the spot-check of round 1 of PR 959, S5:
        the pin of unpinned alone, Pinned, held the comparison; a census_problems that stopped calling it was held by
        nothing)."""
        path = "scripts/sweep.py"
        lines = list(self.hits[path])
        reader = "git merge-base HEAD origin/main"
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
