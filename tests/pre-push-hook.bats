#!/usr/bin/env bats

# .githooks/pre-push — the identifier scan, driven by hand against real commits.
#
# The hook refuses to publish a commit carrying a string from the machine's
# private-strings denylist. Every identifier below is SYNTHETIC (the repo may go
# public, and a real one written here would be the very leak the hook exists to
# stop): the denylist, the paths and the hostnames are all invented per test.
#
# The SYMLINK cases are the reason this file exists. `git grep` searches
# regular-file blobs only, so a symlink whose TARGET carries an identifier is
# invisible to it — a `node_modules -> /home/<user>/…` link created to run the
# extension tests in a worktree was swept up by `git add -A`, pushed to a public
# branch, and found by a human reviewer rather than by this hook (2026-08-13).
# A symlink's target IS its content once committed, so the hook reads those
# blobs directly and these tests hold that line.
#
# The two CONTENT rules, both about what a push changes on the remote: the TIP
# tree of each pushed ref must be clean (that is what a push exposes), and each
# commit no fetched remote already has must ADD no banned line: a commit that
# only inherits an older leak in its tree is not refused, a commit that
# introduced one is, even if a later commit removed it again. The hook's two
# METADATA rules (each new commit's author and committer addresses, and its
# message, with an annotated tag's own tagger and message under the same two)
# have their own files, pre-push-identity.bats and pre-push-message.bats.
# install-sh.bats exercises the hook through a real `git push`; this file feeds
# it ref lines directly, so it can model a remote and its remote-tracking refs
# the way a clone has them.
#
# The tip scan reads symlink TARGETS as well as regular files: git grep reads
# regular-file blobs only, and a committed link's target is its blob content, so
# a link pointing into a home directory is a leak the grep pass alone cannot see.
# The added-lines pass sees a NEW link the way it sees any added line.
#
# A read the hook cannot COMPLETE is not an empty result: a tip whose tree git
# grep could not scan, a tree whose listing failed, a link whose blob could not
# be read, a commit whose diff or parent count could not be read is refused as
# unscanned, the way a tag field the hook cannot read is (pre-push-identity.bats).
# The cases at the end hold that line, each with a git first on the hook's PATH
# that refuses one command shape. The last section turns the credential scan
# back on with the REAL scanner (skipped where none is installed): since round 9
# the hook reads the lines the pushed commits add itself (the credential feed,
# one diff-tree over the push, each commit's name bounding its diff at both
# ends), writes them to pieces, and gitleaks scans those files, running no git;
# a feed that came up short, an ERR line in the scanner's log, or a byte figure
# other than the bytes the feed wrote refuses the push as unscanned, and each
# finding is named with its commit and file. The transform cases there show
# each named transform closed for the feed, which is plumbing given every
# option explicitly, and the round 9d cases (the round 9d section, and the
# slots the retired reads held, each re-aimed in place) hold the feed's reads,
# the pieces' cap and overlap, the NUL mapping, the ~ line, the changed meaning
# of a merge and a rename, and the additive run over the five rules that fire
# on a file's path. A
# replace ref, under which the scans and the push can read different objects,
# is refused before either scan, where a scan would run at all: a clone with no
# denylist and no credential scan makes no clean report a replace ref could
# falsify. The last section is the identifier scan's own transform: a text file
# git calls binary (its path's diff attribute; its size over
# core.bigFileThreshold, a symlink's target included; a driver named one of
# check-attr's reserved words) is read by one content check or neither, and is
# refused rather than scanned on git's own verdict from each read, with the tip
# or the commit, the path and what the attribute reads named; a type change is
# judged as the diff prints it, a deletion and an addition, and a mode-only
# change, which it prints no content for, is not judged at all; a merge is
# judged by its combined patch, the read the scan makes for one, which applies
# no size rule and applies a path's attribute to a symlink, its rename
# candidates read from its deletions against each parent; and a blob the tip
# holds is the tip's to judge, read there or refused there, never the commit's.
# A commit that turns a file binary by its bytes into a text one (a one-parent
# commit's change or rename; a merge's result against a parent's version) is
# refused with the previous version named as the cause, key or no key, the
# header's disclosed fail-closed shape, and the tip reads the file where the
# tip keeps it. The check's reads fail closed in two classes, each with its
# cases at the end: a read whose status is non-zero, and a read that exits 0
# with an empty or a short answer where a second read in hand shows it short
# (the changed-path listing against its verdicts, the tip's listing against
# the symlink pass's count and the grep's read list, a rewrite against its
# input's bytes, the byte judge's zero against the blob's size).

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$ROMP_DIR/.githooks/pre-push"

load git-hermetic

setup() {
    # Hermetic git: the fixtures commit and merge with plain defaults, and a developer's global
    # config (merge.ff=only, commit.gpgsign, a hooks path) must not reach them (the #968 review).
    # The floor (tests/git-hermetic.bash) also forbids background git work in the repos below and
    # in the bare remote the pushes land in, and its exported identity is the one every commit
    # carries; the user.* lines below give the repo a configured user for anything that reads one.
    git_hermetic
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
    REPO="$TEST_DIR/repo"
    mkdir -p "$REPO"
    git -C "$REPO" init -q
    git -C "$REPO" symbolic-ref HEAD refs/heads/main     # whatever init.defaultBranch says
    git -C "$REPO" config user.email t@example.invalid
    git -C "$REPO" config user.name  Tester
    # The hook under test is run BY HAND below; the fixture's own git operations
    # (commits, pushes to the bare remote) must not run this machine's hooks.
    mkdir -p "$TEST_DIR/no-hooks"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"

    # the denylist: invented identifiers, nothing that exists on any real box
    STRINGS="$TEST_DIR/private-strings.txt"
    printf '# synthetic\nzzsynthuser\nTESTHOST\n' > "$STRINGS"

    export ROMP_PRIVATE_STRINGS="$STRINGS"
    export ROMP_NO_GITLEAKS=1          # the credential half: stubbed in install-sh.bats, real in gitleaks-config.bats and the last section here
}

teardown() { rm -rf "${TEST_DIR:-}"; }

ZERO=0000000000000000000000000000000000000000

# Run the hook from inside the repo, the way git does. bats' `run` executes the
# command in a subshell, so the cd here does not leak into the test. (A cd
# helper rather than `env -C`, which BSD env lacks.)
_hook_in() { cd "$1" && shift && bash "$@"; }

# Feed the hook a ref line the way git does: <local_ref> <sha> <remote_ref> <remote_sha>.
# The default remote sha of zero means a new branch, i.e. every commit here is
# being published; pass the sha the remote holds to model updating a branch it has.
run_hook() {
    local sha remote_sha="${1:-$ZERO}"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< \
        "refs/heads/main $sha refs/heads/main $remote_sha"
}

commit_file() {   # <path> <content> <message>
    printf '%s\n' "$2" > "$REPO/$1"
    git -C "$REPO" add "$1"
    git -C "$REPO" commit -qm "$3"
}

# A bare remote named origin, so refs/remotes/origin/* exist the way they do in a
# real clone: the hook decides what is "already on the remote" from those refs.
add_remote() {
    git init -q --bare "$TEST_DIR/remote.git"
    git -C "$REPO" remote add origin "$TEST_DIR/remote.git"
}

remove_file() {   # <path> <message>
    git -C "$REPO" rm -q "$1"
    git -C "$REPO" commit -qm "$2"
}

# The 2026-09-06 incident, reproduced. main publishes an identifier (LEAK_SHA,
# pushed, so the remote has it); a branch is cut from there and commits work of
# its own, whose tree INHERITS the leak although its diff is clean. Leaves HEAD on
# the branch; main has not yet redacted.
branch_inheriting_mains_leak() {
    add_remote
    commit_file base.txt "notes-api" "base"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    LEAK_SHA="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
}

# ...and main redacts the leak (pushed), and the branch merges main: its own
# earlier commit still has the leaky tree, but its tip is clean. The leak is
# leak.txt unless a path is given.
main_redacts_and_branch_merges() {   # [<path>]
    git -C "$REPO" checkout -q main
    remove_file "${1:-leak.txt}" "redact"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q feature
    git -C "$REPO" merge -q -m "merge main" main
}

# The same shape with a SYMLINK: main commits and pushes a link whose target is
# a home path (a node_modules link made to run tests in a worktree, swept up by
# a broad `git add`), and a branch cut from there inherits it. Leaves HEAD on
# the branch; main has not yet removed the link.
branch_inheriting_mains_symlink_leak() {
    add_remote
    commit_file base.txt "notes-api" "base"
    ln -s /home/zzsynthuser/code/romp/vscode-extension/node_modules "$REPO/node_modules"
    git -C "$REPO" add node_modules
    git -C "$REPO" commit -qm "symlink leak"
    LEAK_SHA="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
}

@test "a clean commit passes" {
    commit_file file.txt "nothing to see" "clean"
    run_hook
    [ "$status" -eq 0 ]
}

@test "an identifier in a regular file is blocked" {
    commit_file file.txt "home is /home/zzsynthuser/code" "leak"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"personal identifier"* ]]
}

@test "an identifier in an INTERMEDIATE commit is caught, not just the tip" {
    commit_file bad.txt "home is /home/zzsynthuser/x" "leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file bad.txt "remove it"               # tip is clean; history is not
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS a personal identifier"* ]]
    [[ "$output" == *"  bad.txt"* ]]
}

@test "an added line shaped like a diff header is content, not a new path" {
    # In a patch, content `++ b/decoy.txt` renders as `+++ b/decoy.txt`, the same
    # text as a file header. Only a header names the path the next hit belongs to.
    printf '%s\n' '++ b/decoy.txt' 'home is /home/zzsynthuser/x' > "$REPO/real.txt"
    git -C "$REPO" add real.txt
    git -C "$REPO" commit -qm "leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file real.txt "remove it"              # tip is clean, so the added-lines pass decides
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS a personal identifier"* ]]
    [[ "$output" == *"  real.txt"* ]]
    [[ "$output" != *"decoy.txt"* ]]
}

# The added lines are read through a scratch file, never captured in a command
# substitution: a substitution drops NUL bytes and prints bash's warning ("ignored
# null byte in input"), naming the hook's line and no commit, which a real push of
# this repository's own history did three times (the round 4 refuter, 2026-09-22).
# A file git calls text can carry a NUL among its lines all the same: the verdict
# reads the first 8000 bytes, and a NUL past them is inside a line the diff prints.
# The grep reads that file as text (-a); without it, a NUL among the lines makes
# grep call the file binary and print no line for a hit, which would drop the hit.
nul_past_the_verdict() {   # <path> <first line>: 9000 text bytes, then a line holding a NUL; text by git's rule, a NUL in the patch all the same
    { printf '%s\n' "$2"; head -c 9000 /dev/zero | tr '\0' 'a'; printf '\nlate\0nul\n'; } > "$REPO/$1"
    git -C "$REPO" add "$1"
    git -C "$REPO" commit -qm "a NUL past the text verdict"
}

@test "a commit adding a NUL byte inside a line of a file git calls text (the NUL past the first 8000 bytes) passes with nothing printed: no substitution drops the byte or prints bash's warning" {
    nul_past_the_verdict late.txt "nothing to see"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" | tr -cd "\0" | wc -c' _ "$sha"   # the patch prints the line, NUL and all
    [ "$output" -eq 1 ]
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat --root --no-commit-id "$1" -- late.txt' _ "$sha"                          # and git calls the file text
    [[ "$output" != *"-"$'\t'"-"* ]]
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"ignored null byte"* ]]
    [ -z "$output" ]
}

@test "the same file with the string on its first line, gone at the tip, is a HIT naming the commit and the path, with no warning: the grep reads the file as text, so the NUL among the lines drops no hit" {
    nul_past_the_verdict late.txt "seen on TESTHOST"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file late.txt "remove it"                 # tip is clean, so the added-lines pass decides
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  late.txt"* ]]
    [[ "$output" != *"ignored null byte"* ]]
    [[ "$output" != *"binary file matches"* ]]
}

@test "no denylist file means no identifier scan (a fresh clone is unaffected)" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    commit_file bad.txt "home is /home/zzsynthuser/x" "leak"
    run_hook
    [ "$status" -eq 0 ]
}

# The denylist is read line by line, and a file whose LAST line has no trailing
# newline (an editor that adds none, a `printf` or an `echo -n` that wrote it) ends
# in a line `read` returns with status 1, the line in hand. A plain `while read`
# loop stopped there and never saw it: the entry on that line was scanned for by
# nothing, and a one-entry file so written armed no scan at all, with nothing
# printed either way (2026-09-21). Both files below are written without the
# final newline on purpose.

@test "a denylist whose LAST entry has no trailing newline still bans that entry" {
    printf 'zzsynthuser\nTESTHOST' > "$STRINGS"       # two entries; the second is the unterminated last line
    commit_file hosts.txt "the TESTHOST machine" "leak"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"would publish a personal identifier"* ]]
    [[ "$output" == *"  hosts.txt"* ]]
}

@test "a ONE-entry denylist with no trailing newline still arms the scan" {
    printf 'TESTHOST' > "$STRINGS"                     # the whole file is one unterminated line
    commit_file hosts.txt "the TESTHOST machine" "leak"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"would publish a personal identifier"* ]]
    [[ "$output" == *"  hosts.txt"* ]]
}

# ── which commits a push publishes ────────────────────────────────────────
# A leak already on the remote is fixed forward on main, not by refusing every
# branch cut since: the tip tree must be clean, and only commits the remote lacks
# are read, for the lines they ADD.

@test "a branch that only INHERITED main's leak in its tree passes once its tip merged the redaction" {
    branch_inheriting_mains_leak
    main_redacts_and_branch_merges
    run_hook                                    # new ref: range = the branch commit + the merge
    [ "$status" -eq 0 ]
}

@test "the same branch is refused while its TIP still carries the inherited leak" {
    branch_inheriting_mains_leak
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the tip of refs/heads/main"* ]]   # named as the tip, not as an introduction
    [[ "$output" == *"leak.txt"* ]]
    [[ "$output" != *"ADDS"* ]]
    [[ "$output" == *"merge the main that has since redacted it"* ]]   # the remedy is spelled out
}

@test "a leak ADDED by a branch commit and removed by a later one is refused, naming the commit" {
    commit_file base.txt "notes-api" "base"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "redact"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS a personal identifier"* ]]
    [[ "$output" == *"leak.txt"* ]]
}

@test "an identifier in the branch's OWN new commit is still refused after merging main" {
    branch_inheriting_mains_leak
    main_redacts_and_branch_merges
    commit_file api.txt "home is /home/zzsynthuser/api" "branch leak"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"ADDS a personal identifier"* ]]
    [[ "$output" == *"api.txt"* ]]
    [[ "$output" != *"leak.txt"* ]]       # main's commits were skipped, not re-flagged
}

# ── symlinks ──────────────────────────────────────────────────────────────
# A committed symlink is a blob holding its target, and git grep reads
# regular-file blobs only, so the tip pass reads each link's target itself. A
# link into a home directory, made to run tests in a worktree and swept up by a
# broad `git add`, reached a public branch while a git grep of its tree saw it
# clean. The repo's own bin/ links are relative and must not trip it.

@test "a branch that only INHERITED main's SYMLINK leak passes once its tip merged the removal" {
    branch_inheriting_mains_symlink_leak
    main_redacts_and_branch_merges node_modules
    run_hook
    [ "$status" -eq 0 ]
}

@test "the same branch is refused while its TIP still carries an inherited SYMLINK leak" {
    branch_inheriting_mains_symlink_leak
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the tip of refs/heads/main"* ]]   # named as the tip, not as an introduction
    [[ "$output" == *"SYMLINK TARGET"* ]]
    [[ "$output" == *"node_modules -> /home/zzsynthuser/"* ]]
    [[ "$output" != *"ADDS"* ]]                          # main published the link; the branch added nothing
    [[ "$output" == *"merge the main that has since redacted it"* ]]
}

@test "a RELATIVE symlink with no identifier passes" {
    # the repo's own bin/romp-* links have this shape
    mkdir -p "$REPO/kernel" "$REPO/bin"
    printf '%s\n' "x" > "$REPO/kernel/kernel.py"
    ln -s ../kernel/kernel.py "$REPO/bin/romp-kernel"
    git -C "$REPO" add kernel bin
    git -C "$REPO" commit -qm "relative link"
    run_hook
    [ "$status" -eq 0 ]
}

@test "a NEW symlink at the tip is named with its link and target, by both passes" {
    ln -s /home/ZZSynthUser/notes "$REPO/notes-link"      # mixed case: matched case-insensitively, like a file
    git -C "$REPO" add notes-link
    git -C "$REPO" commit -qm "symlink leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"SYMLINK TARGET of notes-link -> /home/ZZSynthUser/notes"* ]]   # the tip pass
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS a personal identifier"* ]]   # and the commit that added it, as for a regular file
    [[ "$output" == *"  notes-link"* ]]
}

@test "an identifier in an INTERMEDIATE commit's SYMLINK TARGET is caught by the added-lines pass" {
    ln -s /home/zzsynthuser/x "$REPO/bad"
    git -C "$REPO" add bad
    git -C "$REPO" commit -qm "leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file bad "remove it"                   # tip is clean; history is not
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS a personal identifier"* ]]   # a new link's target is an added line of that path
    [[ "$output" == *"  bad"* ]]
    [[ "$output" != *"SYMLINK TARGET"* ]]        # the tip has no link left to name
}

@test "a dot in a denylist entry matches only a dot, in a file and in a symlink target" {
    # A hostname's dots are text, not "any character": every pass greps the
    # denylist as fixed strings, the symlink pass the same as the other two.
    printf 'nas.zzsynth.invalid\n' > "$STRINGS"
    commit_file mounts.txt "share on /mnt/nasXzzsynthXinvalid/" "near miss in a file"
    ln -s /mnt/nasXzzsynthXinvalid/share "$REPO/share"
    git -C "$REPO" add share
    git -C "$REPO" commit -qm "near miss in a link"
    run_hook
    [ "$status" -eq 0 ]
}

@test "a symlink whose blob cannot be read does not end the hook before its verdict" {
    # Under set -e a failed `target=$(git cat-file ...)` would exit the hook with
    # no message; the link is reported as unread (the cases at the end), its target
    # counts as empty, and the other findings still print beside it.
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    ln -s ../elsewhere "$REPO/link"
    git -C "$REPO" add link
    git -C "$REPO" commit -qm "link"
    blob="$(git -C "$REPO" rev-parse HEAD:link)"
    rm "$REPO/.git/objects/${blob:0:2}/${blob:2}"   # loose in a fresh repo; ls-tree still lists the entry
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]                              # the hook's refusal; a set -e death exits 128
    [[ "$output" == *"leak.txt"* ]]
    [[ "$output" == *"the SYMLINK TARGET of link at the tip of refs/heads/main (${sha:0:10}) could not be read"* ]]
    [[ "$output" == *"BLOCKED"* ]]                   # the verdict was reached
}

# ── two remotes: a fork and the project it forked from ────────────────────
# "New" means new to EVERY fetched remote, not only the one being pushed to. With
# the exclusion scoped to the pushed-to remote, a clean branch cut from the
# project's main was refused on its way to the fork as a new ref, over a commit
# only the project's main reaches — named as ADDING a string the project had
# since redacted, which no rewrite of the branch could fix — and syncing the
# fork's main to the project's was refused the same way (the #968 review). A
# string a remote already holds is fixed forward on that remote, whichever one.

# The project (upstream) publishes an identifier and redacts it; the fork
# (origin) still holds only the base. Leaves HEAD on main, at the project's tip.
project_leaked_and_redacted_fork_behind() {
    add_remote
    git init -q --bare "$TEST_DIR/upstream.git"
    git -C "$REPO" remote add upstream "$TEST_DIR/upstream.git"
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" push -q upstream main
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    LEAK_SHA="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "redact"
    git -C "$REPO" push -q upstream main          # the fork's main is still at the base
}

@test "a clean branch cut from the project's main passes to the fork as a NEW ref" {
    project_leaked_and_redacted_fork_behind
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
    run_hook                                      # to origin, which reaches none of the project's commits
    [ "$status" -eq 0 ]
}

@test "syncing the fork's main to the project's passes" {
    project_leaked_and_redacted_fork_behind
    run_hook "$(git -C "$REPO" rev-parse origin/main)"   # updating origin's main from the base
    [ "$status" -eq 0 ]
}

@test "a commit no remote has is still scanned on the way to either remote" {
    # the exclusion excuses what a remote already published, never a leak still local to this clone
    project_leaked_and_redacted_fork_behind
    git -C "$REPO" checkout -q -b feature
    commit_file api.txt "home is /home/zzsynthuser/api" "branch leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file api.txt "remove it"               # tip is clean; the branch's own history is not
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS a personal identifier"* ]]
    [[ "$output" == *"  api.txt"* ]]
    [[ "$output" != *"${LEAK_SHA:0:10}"* ]]       # the project's own commit is not re-flagged
}

@test "a commit only ANOTHER remote has is not rescanned on the way to this one" {
    # This case once asserted the opposite: the exclusion stopped at the pushed-to remote's refs,
    # so a leak another remote held was named again here. The #968 review turned rev_range around
    # (--remotes, every remote): a string a remote already holds is fixed forward on that remote,
    # and any refs/remotes/* ref counts, whether or not a remote of that name is configured.
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "redact"                # tip is clean
    git -C "$REPO" update-ref refs/remotes/elsewhere/main HEAD
    commit_file web.txt "the web session's work" "more work"   # the one commit new to every remote
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"${leak_sha:0:10}"* ]]       # the other remote's commit is not re-flagged
}

# ── merges ────────────────────────────────────────────────────────────────
# A merge's own additions are the lines in NONE of its parents: a conflict
# resolution, a line typed into the merge. A merge of main taken while main
# carried a string brings it in through the second parent, which the remote
# already has, and a diff against the first parent alone named the merge as
# adding it although the branch's tip was clean (the #968 review).

# A branch cut BEFORE main publishes an identifier merges main while the string
# is live (the merge's first-parent diff adds it; its second parent has it),
# then merges the redaction: the tip is clean. Leaves HEAD on the branch.
branch_merged_main_while_leak_was_live() {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
    git -C "$REPO" checkout -q main
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q feature
    git -C "$REPO" merge -q -m "merge main while the leak is live" main
    LIVE_MERGE_SHA="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q main
    remove_file leak.txt "redact"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q feature
    git -C "$REPO" merge -q -m "merge the redaction" main
}

@test "a merge of main taken while the leak was live is not the merge's own addition" {
    branch_merged_main_while_leak_was_live
    run_hook                # new ref: the branch commit and both merges are in the range, main's commits are not
    [ "$status" -eq 0 ]
}

@test "a string typed into a merge's conflict resolution is the merge's own addition, naming the merge" {
    add_remote
    commit_file notes.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file notes.txt "the web session's line" "branch side"
    git -C "$REPO" checkout -q main
    commit_file notes.txt "the api session's line" "main side"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q feature
    run git -C "$REPO" merge -q -m "merge main" main
    [ "$status" -ne 0 ]                           # both sides changed notes.txt: a conflict to resolve
    printf '%s\n' "resolved at /home/zzsynthuser/notes" > "$REPO/notes.txt"   # in neither parent
    git -C "$REPO" add notes.txt
    git -C "$REPO" commit -qm "merge main, resolved"
    merge_sha="$(git -C "$REPO" rev-parse HEAD)"
    commit_file notes.txt "settled" "settle"      # tip is clean, so the added-lines pass decides
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${merge_sha:0:10} ADDS a personal identifier"* ]]
    [[ "$output" == *"  notes.txt"* ]]
}

@test "with no remote-tracking refs, the same rule covers everything the remote ref lacks (the fallback)" {
    commit_file base.txt "notes-api" "base"
    remote_sha="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak_sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "redact"
    commit_file web.txt "the web session's work" "more work"   # tip is clean; the range is not
    run_hook "$remote_sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${leak_sha:0:10} ADDS"* ]]
}

# ── reads the hook cannot COMPLETE ────────────────────────────────────────
# Every read above is a git command whose output the hook greps, and a read that
# FAILS is another thing from one that finds nothing: the tip is then part-scanned,
# and what went unread may be exactly the string the scan exists for. The hook
# refuses such a push as unscanned, the way it does a tag field it cannot read
# (pre-push-identity.bats) and a gitleaks that cannot run, instead of reading the
# failure as a clean tree, a tree with no links, or an empty target. Found by
# execution (2026-09-20), one read at a time: a git grep exiting 2, an ls-tree
# that failed after listing the link, and a cat-file -p of the link's blob that
# failed each let a tip that only INHERITED main's leak, the tip scan's own case,
# through a real push with nothing printed and every counter at zero (the
# added-lines pass reads the range with grep, not git grep, and an inherited file
# is in no new commit's diff).
#
# The fault is a git first on the hook's PATH that refuses ONE command shape and
# runs the real git for every other, written into the test's temp dir at run
# time. The test body is its own subshell, so the PATH change does not outlive
# the test. Once per test: a second call would resolve `command -v git` to the
# first shim, and the new one would exec itself forever.
git_refusing() {   # <bash test over the shim's "$@"> <exit status> <stderr line>
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then\n' "$1"
        printf '    echo %q >&2\n    exit %d\nfi\n' "$3" "$2"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
fail_git_grep() { git_refusing '[ "${1:-}" = grep ]' 2 "shim: git grep refused"; }
fail_ls_tree()  { git_refusing '[ "${1:-}" = ls-tree ]' 128 "fatal: shim: ls-tree refused"; }
fail_cat_file_p() {   # <sha whose `cat-file -p` fails>
    git_refusing "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $1 ]" 128 "fatal: shim: cat-file -p refused for $1"
}
fail_diff_tree() {   # [<sha whose diff-tree fails; every commit's when omitted>]: the sha is the read's last argument, or, for the added-lines read, the first line of its stdin (--stdin, its last argument, since round 8b3), which the shim reads and hands on to the real git for every other commit
    local real_git
    if [ -n "${1:-}" ]; then
        real_git="$(command -v git)"
        mkdir -p "$TEST_DIR/shim"
        {
            printf '#!/usr/bin/env bash\n'
            printf 'if [ "${1:-}" = diff-tree ] && [ "${!#}" = --stdin ]; then\n'
            printf '    in=$(mktemp %q); cat > "$in"; first=""; { IFS= read -r first || :; } < "$in"\n' "$TEST_DIR/stdin.XXXXXX"
            printf '    if [ "$first" = %q ]; then echo %q >&2; exit 128; fi\n' "$1" "fatal: shim: diff-tree refused for $1"
            printf '    exec %q "$@" < "$in"\n' "$real_git"
            printf 'fi\n'
            printf 'if [ "${1:-}" = diff-tree ] && [ "${!#}" = %q ]; then echo %q >&2; exit 128; fi\n' "$1" "fatal: shim: diff-tree refused for $1"
            printf 'exec %q "$@"\n' "$real_git"
        } > "$TEST_DIR/shim/git"
        chmod 755 "$TEST_DIR/shim/git"
        export PATH="$TEST_DIR/shim:$PATH"
    else
        git_refusing '[ "${1:-}" = diff-tree ]' 128 "fatal: shim: diff-tree refused"
    fi
}
fail_rev_list_parents() { git_refusing '[ "${1:-}" = rev-list ] && [ "${2:-}" = --parents ]' 128 "fatal: shim: rev-list --parents refused"; }
fail_diff_tree_stdin() { git_refusing '[[ " $* " == *" diff-tree "*" --text "* ]]' 128 "fatal: shim: diff-tree --text refused"; }   # the credential feed's read alone (the one diff-tree given --text; re-keyed in round 9 from the retired count's --stdin read, and in round 9e from diff-tree as the first word, since the feed's git carries -c core.quotePath=true ahead of it)

# The tip's CONTENT scan is one `git grep` over the tree. It exits 1 for no match
# and above 1 when it could not scan (a git that would not run, a killed process,
# an argument list too long, a partial clone whose promisor is unreachable), and a
# blob it cannot read it reports on stderr and skips, exiting 1 or 0.

@test "a tip whose tree cannot be SCANNED is refused as unscanned, naming the ref: a failed content scan is not a clean tree" {
    branch_inheriting_mains_leak             # only the tip scan can see leak.txt: the leak is in no new commit's diff
    fail_git_grep
    sha="$(git -C "$REPO" rev-parse HEAD)"
    # the fault as the hook meets it, from the repo's top level: the grep fails above 1, the other reads work
    run _hook_in "$REPO" -c 'git grep -l -F -e x "$1" --' _ "$sha"
    [ "$status" -eq 2 ]
    run _hook_in "$REPO" -c 'git ls-tree -r "$1" >/dev/null && git rev-list "$1" --not --remotes >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CONTENT of the tip of refs/heads/main (${sha:0:10}) could not be"*"scanned"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    # reported as a failed scan, not as a finding: nothing was read to find
    [[ "$output" != *"would publish"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a clean tip beside that git is refused too: unscanned, it cannot be known clean" {
    commit_file file.txt "nothing to see" "clean"
    fail_git_grep
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CONTENT of the tip of refs/heads/main"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a regular file whose blob cannot be read is refused as unscanned, not read as clean" {
    # git grep reports the blob on stderr and exits as if the file had no match; the
    # inherited shape again, so no other pass reads the file (no worktree copy either:
    # diff-tree would read a checked-out file in the blob's place).
    branch_inheriting_mains_leak
    blob="$(git -C "$REPO" rev-parse HEAD:leak.txt)"
    rm "$REPO/.git/objects/${blob:0:2}/${blob:2}" "$REPO/leak.txt"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CONTENT of the tip of refs/heads/main (${sha:0:10}) could not be"*"scanned"* ]]
    [[ "$output" == *"unable to read"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

# The hit-or-error split above reads a hit as `<sha>:<path>` and anything else as
# an error line. With color.ui or color.grep set to always, git wraps each hit line
# of `git grep -l` in colour codes even off a terminal, so a real hit read as an
# error: the tip that carried the string was reported as a broken scanner (refused,
# but with the wrong report and only the bypass as advice), where every text of the
# hook before the split had named the file (2026-09-21). The grep asks for no colour.

@test "a hit in the tip is reported as a hit under color.ui=always: a coloured hit line is not an error line" {
    branch_inheriting_mains_leak             # only the tip scan can see leak.txt
    git -C "$REPO" config color.ui always
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git grep -i -I -l -F -e zzsynthuser "$1" --' _ "$sha"   # the hit line as git colours it
    [ "$status" -eq 0 ]
    [[ "$output" == *$'\e['* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the tip of refs/heads/main (${sha:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"  leak.txt"* ]]
    [[ "$output" == *"BLOCKED"* ]]
    [[ "$output" != *"could not be fully scanned"* ]]
}

@test "the same under color.grep=always, the other key that colours a hit line" {
    branch_inheriting_mains_leak
    git -C "$REPO" config color.grep always
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the tip of refs/heads/main (${sha:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"  leak.txt"* ]]
    [[ "$output" != *"could not be fully scanned"* ]]
}

# The symlink LISTING: `git ls-tree -r` was piped straight into the grep for link
# entries, so the pipeline's status was the grep's and a listing that FAILED read
# as a tree with no symlinks. The hook now names any link the listing did reach.

@test "a tip whose SYMLINKS cannot be listed is refused as unscanned, naming the ref: a failed listing is not a tree with no links" {
    branch_inheriting_mains_symlink_leak      # main's link, already published: only the tip pass can see it
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_ls_tree
    run _hook_in "$REPO" -c 'git ls-tree -r "$1"' _ "$sha"   # the fault as the hook meets it, from the repo's top level
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the SYMLINKS of the tip of refs/heads/main (${sha:0:10}) could not be listed"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    # reported as a failed listing, not as a finding: no link was listed to name
    [[ "$output" != *"SYMLINK TARGET"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a listing that fails PARTWAY still names the link it reached, and the push is refused as unscanned all the same" {
    # The fault's real shape: a subtree object missing from the store. ls-tree lists the
    # entries before it, the link among them, then exits 1. The subdirectory is main's,
    # published beside the link, so the branch's own diff never reads it.
    add_remote
    commit_file base.txt "notes-api" "base"
    ln -s /home/zzsynthuser/code/romp/vscode-extension/node_modules "$REPO/node_modules"
    mkdir -p "$REPO/sub"
    printf '%s\n' "clean" > "$REPO/sub/inner.txt"
    git -C "$REPO" add node_modules sub
    git -C "$REPO" commit -qm "symlink leak beside a subdirectory"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    tree="$(git -C "$REPO" rev-parse "$sha:sub")"
    rm "$REPO/.git/objects/${tree:0:2}/${tree:2}"   # loose in a fresh repo
    run _hook_in "$REPO" -c 'git ls-tree -r "$1"' _ "$sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"120000 "*"node_modules"* ]]      # listed before the failure
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the SYMLINKS of the tip of refs/heads/main (${sha:0:10}) could not be listed"* ]]
    [[ "$output" == *"SYMLINK TARGET of node_modules -> /home/zzsynthuser/code/romp/vscode-extension/node_modules"* ]]
    [[ "$output" == *"BLOCKED"* ]]
}

# Each link's TARGET is a `cat-file -p` of its blob. Read as empty when it failed,
# a link whose target could not be read was a link with nothing in it.

@test "a symlink whose TARGET cannot be read is refused as unscanned, naming the ref and the link: an unread target is not an empty one" {
    branch_inheriting_mains_symlink_leak      # main's link, already published: only the tip pass can see it
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$sha:node_modules")"
    fail_cat_file_p "$blob"
    # the fault as the hook meets it, from the repo's top level: the listing works, the blob read does not
    run _hook_in "$REPO" -c 'git ls-tree -r "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [[ "$output" == *"120000 "*"node_modules"* ]]
    run _hook_in "$REPO" -c 'git cat-file -p "$1"' _ "$blob"
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the SYMLINK TARGET of node_modules at the tip of refs/heads/main (${sha:0:10}) could not be read"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    # reported as a failed read, not as a finding: no target was read to name
    [[ "$output" != *"-> /home/zzsynthuser"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "the loop goes on past an unread link: a readable link beside it is still read and named, and the push is refused on both counts" {
    # ls-tree lists data-link before node_modules, so the unread link comes first
    add_remote
    commit_file base.txt "notes-api" "base"
    ln -s /home/zzsynthuser/code/romp/vscode-extension/node_modules "$REPO/node_modules"
    ln -s ../shared/data "$REPO/data-link"
    git -C "$REPO" add node_modules data-link
    git -C "$REPO" commit -qm "two links"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_cat_file_p "$(git -C "$REPO" rev-parse "$sha:data-link")"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the SYMLINK TARGET of data-link at the tip of refs/heads/main (${sha:0:10}) could not be read"* ]]
    [[ "$output" == *"SYMLINK TARGET of node_modules -> /home/zzsynthuser/code/romp/vscode-extension/node_modules"* ]]
    [[ "$output" == *"BLOCKED"* ]]
}

@test "a link whose target reads clean passes beside that git when the fault sits on another blob: the refusal is the failed read, not the shim's presence" {
    commit_file kernel.py "x" "a file"
    ln -s ./kernel.py "$REPO/romp-kernel"
    git -C "$REPO" add romp-kernel
    git -C "$REPO" commit -qm "relative link"
    fail_cat_file_p "$(git -C "$REPO" rev-parse HEAD:kernel.py)"   # a regular file's blob, which no read of the hook fetches by hand
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# A pushed object that PEELS TO A BLOB (a tag of a blob; git's own repository
# carries one for a public key) has no tree: `git ls-tree -r` fails on it with
# "not a tree object", and git grep reads the blob as one file, printing the bare
# sha for a hit. Neither is a failed read: the listing is absent, and the hit is a
# hit. Found by the round f4 audit, on the first text of the cases above, which
# refused every such tag as unlisted. The hook is fed a tag ref line here.

@test "a tag of a BLOB passes: a blob has no tree to list, so an absent listing is not a failed one" {
    commit_file f.txt "plain" "base"
    git -C "$REPO" tag -a blobtag "$(git -C "$REPO" rev-parse HEAD:f.txt)" -m "a tag of a blob"
    sha="$(git -C "$REPO" rev-parse refs/tags/blobtag)"
    run _hook_in "$REPO" -c 'git ls-tree -r "$1"' _ "$sha"      # the read as the hook meets it: not a tree
    [ "$status" -ne 0 ]
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< "refs/tags/blobtag $sha refs/tags/blobtag $ZERO"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "a tag of a blob whose CONTENT carries the string is refused as a finding, not as a failed scan" {
    commit_file f.txt "plain" "base"
    blob="$(printf '%s\n' "the TESTHOST machine" | git -C "$REPO" hash-object -w --stdin)"
    git -C "$REPO" tag -a dirtyblob "$blob" -m "a tag of a blob"
    sha="$(git -C "$REPO" rev-parse refs/tags/dirtyblob)"
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< "refs/tags/dirtyblob $sha refs/tags/dirtyblob $ZERO"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the tip of refs/tags/dirtyblob (${sha:0:10}) would publish a personal identifier"* ]]
    [[ "$output" == *"BLOCKED"* ]]
    [[ "$output" != *"could not be"* ]]
}

# Each commit the push publishes is read three ways, and each read was a git
# command piped into the grep or the loop that judged it: its ADDED LINES
# (diff-tree, below), its ADDRESSES (log; pre-push-identity.bats) and its MESSAGE
# (log; pre-push-message.bats). Piped, the read's failure was the grep's
# no-match: a diff-tree that failed read as a commit that added nothing, and
# git's own error line was the only sign. Found by execution (2026-09-20): with
# the diff-tree refused, a commit that added a banned line and the commit that
# removed it again went through a real push with every counter at zero, and the
# same with the real git once the added file's blob was gone from the store
# (fatal: unable to read, exit 128), the fault the second case below makes. The
# hook now reads the diff's status apart from the grep; whatever the diff did
# print is still grepped, so a hit ahead of the failure is still named. An EMPTY
# diff (an empty commit, a merge with no line of its own) is absent, not
# unreadable, and passes.

@test "a commit whose ADDED LINES cannot be read is refused as unscanned, naming the commit: a failed diff is not a commit that added nothing" {
    commit_file base.txt "notes-api" "base"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "redact"                       # the tip is clean: only the added-lines pass can see the leak
    fail_diff_tree
    # the fault as the hook meets it, from the repo's top level: the diff fails, the other reads work
    run _hook_in "$REPO" -c 'git diff-tree -p -r --root --no-commit-id "$1"' _ "$leak"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git rev-list "$1" --not --remotes >/dev/null && git log -1 --format=%B "$1" >/dev/null' _ "$leak"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the ADDED LINES of commit ${leak:0:10} could not be read (git diff-tree exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    # reported as a failed read, not as a finding: nothing was read to find
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a commit whose added file's BLOB is missing from the store is refused as unscanned: the real fault behind the diff-tree read" {
    # No shim: the patch needs the blob, and once the removing commit is made no
    # worktree copy stands in for it (diff-tree reads a checked-out file in the
    # blob's place). The tip is clean, so no other pass reads the file.
    commit_file base.txt "notes-api" "base"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse HEAD:leak.txt)"
    remove_file leak.txt "redact"
    rm "$REPO/.git/objects/${blob:0:2}/${blob:2}"       # loose in a fresh repo
    run _hook_in "$REPO" -c 'git diff-tree -p -r --root --no-commit-id "$1"' _ "$leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"unable to read"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the ADDED LINES of commit ${leak:0:10} could not be read (git diff-tree exited 128)"* ]]
    [[ "$output" == *"unable to read"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "the added-lines pass goes on past an unread commit: a leak in the commit beside it is still named, and the push is refused on both counts" {
    commit_file base.txt "notes-api" "base"
    commit_file web.txt "the web session's work" "clean commit"
    clean="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "redact"
    fail_diff_tree "$clean"                             # the fault sits on the clean commit alone
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the ADDED LINES of commit ${clean:0:10} could not be read"* ]]
    [[ "$output" == *"commit ${leak:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"BLOCKED"* ]]
}

@test "a commit whose PARENT COUNT cannot be read is refused as unscanned, naming that read: the added lines are two reads, and the refusal says which failed" {
    # Two CLEAN commits, so only the failed read can refuse: on a leaking fixture the
    # diff alone would refuse the push and only the wording would be under test. The
    # parent count decides how many columns a merge's combined diff has; read as one
    # when it fails, a merge is over-scanned, but a read that failed all the same.
    commit_file base.txt "notes-api" "base"
    commit_file web.txt "the web session's work" "clean commit"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_rev_list_parents
    # the fault as the hook meets it, from the repo's top level: the parent count fails, the diff and the range read
    run _hook_in "$REPO" -c 'git rev-list --parents -n 1 "$1"' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" >/dev/null && git rev-list "$1" --not --remotes >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the ADDED LINES of commit ${sha:0:10} could not be read (git rev-list --parents exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    [[ "$output" != *"diff-tree"* ]]                 # the read that worked is not the one named
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "an EMPTY commit and a merge with no line of its own pass beside that git when the fault sits on a commit not in the push: an empty diff is absent, not unreadable" {
    add_remote
    commit_file base.txt "notes-api" "base"
    base="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
    git -C "$REPO" checkout -q main
    git -C "$REPO" commit -q --allow-empty -m "an empty commit"
    git -C "$REPO" merge -q --no-ff -m "merge feature" feature     # every line of its tree is in one parent: -c prints nothing
    fail_diff_tree "$base"                              # base is on the remote: not a commit this push publishes
    # the reads as the hook meets them, from the repo's top level: an empty diff prints nothing and exits 0
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$(git -C "$REPO" rev-parse HEAD^1)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$(git -C "$REPO" rev-parse HEAD)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ── the credential scan: the feed the hook reads, the bytes gitleaks reads ──
# Until round 9 the credential scan was one read the hook made INSIDE another
# program: gitleaks ran `git log -p` itself, its exit status did not carry that
# git's failure, and the hook judged its log by an ERR line and a commit count
# read from the objects (found by execution, 2026-09-21: a git that wrote one
# benign line to stderr, and one that handed gitleaks a commit fewer, each let
# two live credentials through a real push with nothing printed). Whole at the
# granularity of commits and no finer: a stream cut inside a commit, by a git
# on PATH or a real git killed partway, published a credential through a real
# push under gitleaks 8.30.1 and 8.28.0 (the round 8 refuters, 2026-09-24).
# Since round 9 the hook reads the lines the pushed commits add itself (one git
# diff-tree over the push, each commit fed twice so its name bounds its diff at
# both ends; a merge by the lines in none of its parents, a rename by its edits,
# every blob of a root or one-parent commit as text, and since round 10a a
# merge's binary path read whole from its result blob), writes them to pieces
# of at most 98,304 bytes, and
# gitleaks scans that directory from inside it, running no git. The push is
# refused as unscanned when the feed's markers or its count of commits read
# whole fall short, on any ERR line, and when gitleaks' one byte figure is not
# the bytes the feed wrote; a second run, limited to the five rules that fire
# on a file's path, scans copies of the files those rules name (since round
# 10b each named by its piece's number and the suffix the rule keys on, until
# then by its basename), its figure checked the same way. Each finding is named with its
# commit and file. The cases below that held the retired reads (the count,
# the colour strip, the log.showRoot read and its advice arm) are re-aimed in
# place, each naming what it held, so no case number moves.
#
# These cases run the REAL scanner, as tests/gitleaks-config.bats does (skipped,
# out loud, where none is installed; CI installs it). The credential-shaped
# probes are assembled at run time: gitleaks scans this repo too, and a token
# written out longhand would flag the very test that proves the scan works.

real_gitleaks() {
    GL="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"
    if [ -z "$GL" ] || [ ! -x "$GL" ]; then skip "gitleaks not installed"; fi
    export ROMP_GITLEAKS="$GL"
    unset ROMP_NO_GITLEAKS
}
# ghp_ + 36 chars, as tests/gitleaks-config.bats builds it, and a slack bot token,
# so two rules fire and the control names both.
probe_token() { printf 'gh%s_%s%s' p "$(printf '0123456789%.0s' 1 2 3)" abcdef; }
probe_slack() { printf 'xox%s-%s-%s-%s' b 123456789012 123456789012 abcdefghijklmnopqrstuvwx; }

# A git that runs the real git UNCHANGED for every command and, for ONE command
# shape, first writes a line to stderr or appends one argument: a fault the
# feed's git can meet (a message from a filter or a wrapper). Once per test,
# like git_refusing.
git_passing_through() {   # <bash test over the shim's "$@"> <stderr line, or empty> [<argument appended>]
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then\n' "$1"
        [ -z "$2" ] || printf '    echo %q >&2\n' "$2"
        [ -z "${3:-}" ] || printf '    exec %q "$@" %q\n' "$real_git" "$3"
        printf 'fi\n'
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
# The feed's git: the one git of the credential scan whose arguments carry
# --text (the identifier scan's reads carry none), and at cad898dd2 the shape
# of gitleaks' own git log, so one shim drives the read at both heads.
FEED_GIT='[[ " $* " == *" --text "* ]]'
# A scanner of the case's own around the real one: bash lines run first in the
# scanner's working directory (the piece directory, or the path-scoped copies'),
# then the real scanner, then, when given, lines run after it with its status in
# s, which the wrapper exits with. The version read (gitleaks version, which the
# hook makes ahead of its first scanner run since round 10b, from the work
# tree's root) goes straight to the real scanner, so the lines act on the runs
# over the pieces alone.
scanner_wrapper() {   # <bash lines before> [<bash lines after>]
    mkdir -p "$TEST_DIR/scanner"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = version ]; then exec %q "$@"; fi\n' "$GL"
        printf '%s\n' "$1"
        if [ -n "${2:-}" ]; then
            printf '%q "$@"; s=$?\n' "$GL"
            printf '%s\n' "$2"
            printf 'exit "$s"\n'
        else
            printf 'exec %q "$@"\n' "$GL"
        fi
    } > "$TEST_DIR/scanner/gitleaks"
    chmod 755 "$TEST_DIR/scanner/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/scanner/gitleaks"
}
# The shape the round 8 refuters found publishing: one commit adding a clean
# a.txt and a z.py holding a credential, so a cut before the second diff --git
# line drops the credential's file whole.
two_files_credential_second() {   # sha is the commit
    printf 'clean\n' > "$REPO/a.txt"
    printf 'x = "%s"\n' "$(probe_token)" > "$REPO/z.py"
    git -C "$REPO" add a.txt z.py
    git -C "$REPO" commit -qm "two files, the credential in the second"
    sha="$(git -C "$REPO" rev-parse HEAD)"
}

@test "two planted credentials in two commits are both named and refused by the real scanner: the control for the cases below" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    first="$(git -C "$REPO" rev-parse HEAD)"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    second="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: commit ${first:0:10} ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"romp pre-push: commit ${second:0:10} ADDS a credential (slack-bot-token) in: slack.txt"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"$(probe_token)"* ]]           # --redact
    [[ "$output" != *"$(probe_slack)"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]   # a finding, not a failed scan
}

@test "a clean commit passes the real scanner, its byte figure the feed's own: the byte arm refuses nothing extra" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~17 bytes"* ]]        # gitleaks' own log line, shown: the ~ line and the one added line
    [[ "$output" != *"romp pre-push"* ]]
}

@test "commits that add no line (an empty commit, a deletion, a mode-only change, an empty new file, a pure rename) and a binary add pass: no false refusal, the binary read as text and the rename adding nothing" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" commit -q --allow-empty -m "an empty commit"
    remove_file base.txt "a deletion"
    printf 'ab\0cd\0\1\2\n' > "$REPO/blob.bin"
    git -C "$REPO" add blob.bin
    git -C "$REPO" commit -qm "a binary add"                     # --text: its bytes read as one line, each NUL mapped to 0x01
    git -C "$REPO" update-index --chmod=+x blob.bin
    git -C "$REPO" commit -qm "a mode-only change"               # no hunk
    : > "$REPO/empty.txt"
    git -C "$REPO" add empty.txt
    git -C "$REPO" commit -qm "an empty new file"                # no hunk
    git -C "$REPO" mv blob.bin moved.bin
    git -C "$REPO" commit -qm "a pure rename"                    # -M: a rename adds only its edits, here none
    [ "$(git -C "$REPO" rev-list --count HEAD)" -eq 7 ]
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~23 bytes"* ]]                     # two pieces: base.txt's line and blob.bin's, each behind its ~ line; the rename adds none
    [[ "$output" != *"romp pre-push"* ]]
}

# Two shapes the count met (round 3's tests-3), read by the feed since round 9:
# a blob missing from the store, which the feed's diff-tree cannot read, so the
# feed fails with the real git rather than feed the blob as empty, and an added
# gitlink, which the feed reads as its Subproject line.

@test "a commit whose added file's BLOB is missing from the store fails the credential feed with the REAL git, the exact clause naming the read: a blob that cannot be read is never fed as empty" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    blob="$(git -C "$REPO" rev-parse HEAD:probe.py)"
    remove_file probe.py "redact"
    rm "$REPO/.git/objects/${blob:0:2}/${blob:2}"       # loose in a fresh repo
    run _hook_in "$REPO" -c 'git cat-file -e "$1"' _ "$blob"   # the blob as the feed's diff-tree meets it: missing
    [ "$status" -ne 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push could not be read (a stage of git diff-tree, tr and awk exited 128); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
}

@test "an ADDED gitlink (a submodule entry, its commit not in this store) passes the real scanner cleanly: the feed reads its Subproject line, and no read asks for the submodule's commit" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" update-index --add --cacheinfo "160000,0123456789abcdef0123456789abcdef01234567,sub"   # a superproject holds no object for the submodule's commit
    git -C "$REPO" commit -qm "an added gitlink"
    run _hook_in "$REPO" -c 'git ls-tree HEAD sub'
    [[ "$output" == "160000 commit 0123456789abcdef0123456789abcdef01234567"* ]]
    run _hook_in "$REPO" -c 'echo 0123456789abcdef0123456789abcdef01234567 | git cat-file --batch-check'   # the commit itself: not in this store
    [[ "$output" == *"missing"* ]]
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~73 bytes"* ]]                     # base.txt's piece and the gitlink's Subproject line, each behind its ~ line
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a feed git that writes a benign line to stderr and answers whole is no failed read: the credentials are found and named, and no line calls the scan incomplete (until round 9 gitleaks logged such a line of its own git at ERR and dropped the rest of its scan)" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    git_passing_through "$FEED_GIT" "note: a benign line on stderr"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"a benign line on stderr"* ]]              # git's own line, shown
    [[ "$output" == *"ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"ADDS a credential (slack-bot-token) in: slack.txt"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]               # the feed's verdict is its markers and counts, not its stderr
}

@test "a scanner that read part of the pieces (a wrapper cutting every piece to 5 bytes before the real scanner reads them) is refused on the byte figure, both numbers named: a scan of fewer bytes than the feed wrote is not a clean one" {
    real_gitleaks
    two_files_credential_second
    scanner_wrapper 'for f in *; do head -c 5 "$f" > "../cut.$f"; mv "../cut.$f" "$f"; done'
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan read 10 of the 57 bytes of added lines it was fed; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
}

@test "a WRN line in the scanner's log is not an ERR line: a scanner that logs a warning and runs the real scan passes a clean push, the byte figure whole" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    scanner_wrapper 'echo "1:00AM WRN a warning of its own" >&2'
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"WRN a warning of its own"* ]]
    [[ "$output" == *"scanned ~17 bytes"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# No colour reaches the feed. With color.ui or color.diff set to always, git
# colours `log -p` written to a pipe; until round 9 gitleaks' own git log was
# given --no-color for it (a coloured stream carried no file header gitleaks
# could find, and a push carrying a credential passed; found by execution,
# 2026-09-21). The feed's diff-tree is given --no-color itself.

@test "a credential is found under color.ui=always: the feed's diff-tree is asked for no colour" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config color.ui always
    run _hook_in "$REPO" -c 'git log -p -U0 --format="commit %H" HEAD'    # the stream as git colours it for a pipe
    [ "$status" -eq 0 ]
    [[ "$output" == *$'\e['* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under color.diff=always passes: the feed is not coloured, so the byte figure is the feed's" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    git -C "$REPO" config color.diff always
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~17 bytes"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# Two more refusal arms (round 2's tests-1, re-aimed in round 9): a scanner
# that logs no byte figure at all, and the feed's own git failing. Each is a
# refusal a passing suite cannot tell from an arm that is not there, so each
# runs against its refusing input.

@test "a scanner that exits 0 and logs NO byte figure is refused as unscanned: no figure is no evidence of what it read" {
    commit_file file.txt "nothing to see" "clean"
    unset ROMP_NO_GITLEAKS
    export ROMP_GITLEAKS="$TEST_DIR/gitleaks-stub"      # a scanner that runs, says nothing of what it read, and exits clean
    # (its version answered as a release at the floor answers it: the hook reads it ahead of the scan since round 10b)
    printf '#!/usr/bin/env bash\nif [ "${1:-}" = version ]; then echo 8.25.0; exit 0; fi\necho "stub scanner ran, reporting no byte figure" >&2\nexit 0\n' > "$ROMP_GITLEAKS"
    chmod 755 "$ROMP_GITLEAKS"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan reported 0 byte-count lines where it writes one, so what it read is unknown; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"bytes of added lines it was fed"* ]]      # the absent-figure arm, not the mismatch arm
    [[ "$output" != *"gitleaks found a credential"* ]]
}

@test "a hook whose OWN feed read fails is refused as unscanned, naming that read: the scanner's word alone is not evidence" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_diff_tree_stdin                                # keyed on the feed's shape (diff-tree with --text): the identifier scan's diff-tree runs unchanged
    run _hook_in "$REPO" -c 'printf "%s\n%s %s\n" "$1" "$1" "$1" | git -c core.quotePath=true diff-tree --stdin -p -U0 -r -M -c --root --always --text' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push could not be read (a stage of git diff-tree, tr and awk exited 128); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"shim: diff-tree --text refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
}

# ── transforms of the stream ──────────────────────────────────────────────
# Until round 9 gitleaks read a `git log -p` stream, and a transform of it
# emptied the scan: after the colour road, round 2 found a textconv driver and a
# -diff attribute in .gitattributes (each published a credential with the hook
# reporting clean), format.pretty, log.date and log.showSignature (each refused
# a clean push), and a replace ref (both scans read a substitute while the push
# transfers the original); log.showRoot set to false hid a root commit's diff.
# The feed is plumbing given each option explicitly (--no-textconv, --text,
# --no-color, --root), and the porcelain keys are ones diff-tree never reads,
# so a credential under each is found and a clean push under each passes; the
# cases stay as regression pins.
# The identifier scan, when armed, refuses a TEXT file under a -diff attribute
# before either scan reads it (the attribute section at the end), so the two
# -diff cases here, the credential half's, run with the denylist absent.

hiding_textconv() {   # a diff driver whose textconv prints nothing: git's patch for a file under it has no hunk
    printf '#!/usr/bin/env bash\nexit 0\n' > "$TEST_DIR/hide.sh"
    chmod 755 "$TEST_DIR/hide.sh"
    git -C "$REPO" config diff.hide.textconv "$TEST_DIR/hide.sh"
    printf 'probe.py diff=hide\n' > "$REPO/.gitattributes"
    git -C "$REPO" add .gitattributes
    git -C "$REPO" commit -qm "attributes"
}

@test "a credential in a file under a hiding textconv driver is found: the feed's diff-tree converts nothing" {
    real_gitleaks
    hiding_textconv
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    run _hook_in "$REPO" -c 'git log -p -U0 -1 HEAD -- probe.py | grep -c "^@@"'    # the driver as git applies it: no hunk to read
    [ "$output" = 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under that driver passes" {
    real_gitleaks
    hiding_textconv
    commit_file file.txt "nothing to see" "clean"
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~"*" bytes"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a credential in a file marked -diff is found: the feed reads it as text" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"     # the identifier scan would refuse the -diff text file first (the attribute section)
    printf 'probe.py -diff\n' > "$REPO/.gitattributes"
    git -C "$REPO" add .gitattributes
    git -C "$REPO" commit -qm "attributes"
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    run _hook_in "$REPO" -c 'git log -p -U0 -1 HEAD -- probe.py'                    # the attribute as git applies it: a binary
    [[ "$output" == *"Binary files"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push with a file marked -diff passes, the file read: the byte figure counts its line" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"     # likewise: with the denylist armed the same push is refused on the attribute alone
    printf 'notes.txt -diff\n' > "$REPO/.gitattributes"
    git -C "$REPO" add .gitattributes
    git -C "$REPO" commit -qm "attributes"
    commit_file notes.txt "nothing to see" "clean"
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~35 bytes"* ]]                       # .gitattributes' piece and notes.txt's, each behind its ~ line
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a credential is found under format.pretty=oneline: a porcelain key the feed's diff-tree never reads" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config format.pretty oneline
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under format.pretty=oneline passes" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    git -C "$REPO" config format.pretty oneline
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~17 bytes"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a credential is found under log.date=relative: a porcelain key the feed's diff-tree never reads" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.date relative
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under log.date=relative passes" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    git -C "$REPO" config log.date relative
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~17 bytes"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# A commit signed with a signature git cannot verify (no key on the runner, and
# a made-up signature block): with log.showSignature set, git writes gpg's
# report into the log ahead of the patch. The commit is written by hand from
# the index, so no signing key is needed to make one.
signed_commit() {   # <message>: the index as a commit over HEAD, with an unverifiable gpgsig header, as the new tip
    local tree parent sig
    tree=$(git -C "$REPO" write-tree)
    parent=$(git -C "$REPO" rev-parse HEAD)
    sig=$(printf 'tree %s\nparent %s\nauthor romp tests <tests@example.invalid> 1700000000 +0000\ncommitter romp tests <tests@example.invalid> 1700000000 +0000\ngpgsig -----BEGIN PGP SIGNATURE-----\n \n iQEzBAABCAAdFiEEnotarealsignatureAAAAAAAAAAAAAAAAAAAAAAAFAmYAAAA\n =AAAA\n -----END PGP SIGNATURE-----\n\n%s\n' "$tree" "$parent" "$1" \
          | git -C "$REPO" hash-object -t commit -w --stdin)
    git -C "$REPO" update-ref refs/heads/main "$sig"
}

@test "a credential in a signed commit is found under log.showSignature=true: the feed's diff-tree prints no signature report" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    printf 'token = "%s"\n' "$(probe_token)" > "$REPO/probe.py"
    git -C "$REPO" add probe.py
    signed_commit "a signed commit adds a credential"
    git -C "$REPO" config log.showSignature true
    run _hook_in "$REPO" -c 'git log -1 --format=%s HEAD'                           # the key as git applies it: gpg's report in the stream
    [[ "$output" == *"gpg"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean signed commit passes under log.showSignature=true" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    printf 'nothing to see\n' > "$REPO/file.txt"
    git -C "$REPO" add file.txt
    signed_commit "a clean signed commit"
    git -C "$REPO" config log.showSignature true
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~29 bytes"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# A replace ref (git replace): every read of both scans follows the substitute
# while the push transfers the original. The hook runs every git with
# replacement off, so the scan below still finds the credential, and it refuses
# the push before either scan on the ref's presence alone, since under a
# replacement what a scan reads and what a push transfers can differ.
substitute_for() {   # <commit>: a clean commit over the same parent, with a clean file in place of the commit's own changes, and a replace ref pointing the commit at it
    local blob tree sub
    blob=$(printf 'nothing to see\n' | git -C "$REPO" hash-object -w --stdin)
    GIT_INDEX_FILE="$TEST_DIR/substitute.index" git -C "$REPO" read-tree "$1^"
    GIT_INDEX_FILE="$TEST_DIR/substitute.index" git -C "$REPO" update-index --add --cacheinfo "100644,$blob,clean.txt"
    tree=$(GIT_INDEX_FILE="$TEST_DIR/substitute.index" git -C "$REPO" write-tree)
    sub=$(git -C "$REPO" commit-tree "$tree" -p "$1^" -m "a clean substitute")
    git -C "$REPO" update-ref "refs/replace/$1" "$sub"
}

@test "a replace ref over a dirty commit is refused before either scan, naming the ref, and the scan still reads the original" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    dirty="$(git -C "$REPO" rev-parse HEAD)"
    substitute_for "$dirty"
    run git -C "$REPO" cat-file -e "$dirty:probe.py"                                # the replacement as git applies it: the file is not there
    [ "$status" -ne 0 ]
    run env GIT_NO_REPLACE_OBJECTS=1 git -C "$REPO" cat-file -e "$dirty:probe.py"   # the original the push transfers
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: this clone carries a replace ref (refs/replace/$dirty): under it what a scan reads and what the push transfers can differ, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"git replace -d"* ]]
    [[ "$output" == *"github-pat"* ]]                    # replacement off for the feed's git too: the original is what it read
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "a clean push from a clone carrying a replace ref is refused on the premise alone, not as a finding or a failed scan" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    commit_file file.txt "nothing to see" "clean"
    substitute_for "$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"this clone carries a replace ref (refs/replace/$(git -C "$REPO" rev-parse HEAD))"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

# log.showRoot set to false hides a root commit's diff from `git log -p`; until
# round 9 the hook passed --root on gitleaks' own git log and judged a short
# count with an advice line naming the key. The feed is diff-tree, plumbing that
# reads no log.showRoot, given --root itself, so a root commit's lines are read
# whatever the key says. The cases that held the count's advice arm, the
# option on the scanner's command line and the scanner's environment are
# re-aimed in place below, each naming what it held (round 9d), so no case
# number moves.

@test "log.showRoot=false changes nothing: the feed's diff-tree reads a root commit through --root, so the root commit's credential is FOUND, its commit and file named, and no line names the key" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    root="$(git -C "$REPO" rev-parse HEAD)"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    run _hook_in "$REPO" -c 'git log -p -U0 --format="commit %H" "$1" -- probe.py | grep -c "^@@"' _ "$root"   # the key as git log applies it: the root's diff hidden
    [ "$output" = 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: commit ${root:0:10} ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" != *"log.showRoot"* ]]
    [[ "$output" != *"gitleaks could not scan"* ]]
}

@test "a clean push with a root commit under log.showRoot=false passes, the byte figure the feed's own with the root's line in it: --root reached the feed's diff-tree (round 9d: this slot held --root on the scanner's git log, retired with gitleaks' own git)" {
    real_gitleaks
    commit_file base.txt "notes-api" "a clean root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~29 bytes"* ]]            # two pieces: the root's line (12 bytes with its ~ line) and the tip's (17); a feed without --root writes the tip's alone
    [[ "$output" != *"romp pre-push"* ]]
}

# A git that runs the real git unchanged and, for the feed's shape, first
# writes the command-scope configuration it sees (the environment's pairs, in
# index order, then the pairs its own leading -c options set, as git lists
# them) to a file, and for any call made under the scanner (a wrapper
# exports ROMP_UNDER_SCANNER) records the call: what the feed's git was given,
# and whether gitleaks ran a git at all.
git_recording_feed_pairs_and_scanner_calls() {   # <pairs file> <calls file>
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf '[ -z "${ROMP_UNDER_SCANNER:-}" ] || printf "%%s\\n" "git $*" >> %q\n' "$2"
        printf 'if %s; then\n' "$FEED_GIT"
        printf '    a=("$@"); c=(); i=0\n'
        printf '    while [ "${a[i]:-}" = -c ]; do c+=(-c "${a[i + 1]}"); i=$((i + 2)); done\n'
        printf '    %q "${c[@]}" config --show-scope --list | grep "^command" > %q\n' "$real_git" "$1"
        printf 'fi\n'
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "the hook exports no GIT_CONFIG pair of its own and gitleaks runs no git: with the caller's GIT_CONFIG_COUNT=1 (gc.auto) set, the feed's diff-tree sees exactly that pair and its own core.quotePath=true (git -c, round 9e) in its command scope, a git on PATH records no call made under the scanner, and a clean root-commit push under log.showRoot=false passes (round 9d: this slot held the scanner's own git log, which no longer runs)" {
    real_gitleaks
    # the caller's environment: one pair of its own in place of the floor's five (the floor's global config file still carries those keys)
    export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=gc.auto GIT_CONFIG_VALUE_0=0
    unset GIT_CONFIG_KEY_1 GIT_CONFIG_VALUE_1 GIT_CONFIG_KEY_2 GIT_CONFIG_VALUE_2 GIT_CONFIG_KEY_3 GIT_CONFIG_VALUE_3 GIT_CONFIG_KEY_4 GIT_CONFIG_VALUE_4
    commit_file base.txt "notes-api" "a clean root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    git_recording_feed_pairs_and_scanner_calls "$TEST_DIR/feed-git-pairs" "$TEST_DIR/calls.under-scanner"
    scanner_wrapper 'export ROMP_UNDER_SCANNER=1'
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    # the caller's pair, then the feed's one pair on its own command line (git -c core.quotePath=true, so the path
    # text is git's quoted form whatever the clone sets), nothing else appended (a negative pin)
    run cat "$TEST_DIR/feed-git-pairs"
    [ "$output" = "$(printf 'command\tgc.auto=0\ncommand\tcore.quotepath=true')" ]
    # no git ran under the scanner: it read the pieces (at cad898dd2 its own git log is recorded here)
    [ ! -e "$TEST_DIR/calls.under-scanner" ]
}

# gitleaks reads a .gitleaksignore from its working directory whatever -i says
# (measured on 8.30.1 and 8.28.0); it runs from the piece directory, which holds
# none, so no entry the work tree carries reaches it.

@test "a .gitleaksignore in the work tree excuses nothing: gitleaks runs from the piece directory, so entries naming the finding's piece, rule and line leave the credential refused and named (round 9d: this slot held a scanner git without the hook's environment, retired with gitleaks' own git)" {
    real_gitleaks
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    printf '1:github-pat:2\n:github-pat:2\n' > "$REPO/.gitleaksignore"     # the fingerprints -v prints for piece 1, line 2 (untracked: not in the push)
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: k.py"* ]]
    [[ "$output" == *"Fingerprint: 1:github-pat:2"* ]]                   # the entry names the finding exactly
    [[ "$output" == *"gitleaks found a credential"* ]]
}

# A scanner that reads fewer bytes than the feed wrote, three ways (a piece it
# cannot read, a second byte figure, a piece taken away): each refused on the
# byte figure, the arm that replaced the count's shortfall line.

@test "a scanner that skips a piece it cannot read (a wrapper taking every permission bit off the last piece) is refused on the byte figure: gitleaks logs the skip and leaves the file out of its figure (round 9d: this slot held a scanner git that did not honour --root, refused on the count, both retired)" {
    real_gitleaks
    two_files_credential_second
    scanner_wrapper 'last=$(ls | sort -n | tail -1); chmod 000 "$last"'
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan read 8 of the 57 bytes of added lines it was fed; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
}

@test "a scanner that logs a SECOND byte figure is refused: two figures say nothing of which one is the read (round 9d: this slot held the count shortfall's key line, retired with the count)" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    scanner_wrapper '' 'echo "1:00AM INF scanned ~5 bytes (5 bytes) in 1ms" >&2'
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan reported 2 byte-count lines where it writes one, so what it read is unknown; the scan is incomplete, so the push is refused"* ]]
}

@test "a scanner handed fewer pieces by a cause of its own (a wrapper taking the last piece away) is refused on the byte figure, and no line names a configuration key (round 9d: this slot held a count shortfall from a cause other than log.showRoot, retired with the count's advice arm)" {
    real_gitleaks
    two_files_credential_second
    scanner_wrapper 'rm -f -- "$(ls | sort -n | tail -1)"'
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan read 8 of the 57 bytes of added lines it was fed; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"log.showRoot"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
}

# A git shim that strips --root from every invocation carrying the word `log`
# and leaves diff-tree alone: until round 9 it shortened gitleaks' own log, and
# the count read from the objects refused where one read from the log agreed
# (round 3's tests-1). No git log runs in the credential scan since round 9.
git_stripping_root_from_log() {
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'args=(); islog=0\n'
        printf 'for a in "$@"; do [ "$a" = log ] && islog=1; args+=("$a"); done\n'
        printf 'if [ "$islog" -eq 1 ]; then kept=(); for a in "${args[@]}"; do [ "$a" = --root ] || kept+=("$a"); done; args=("${kept[@]}"); fi\n'
        printf 'exec %q "${args[@]}"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "a git shim stripping --root from every log invocation changes nothing: no git log runs in the credential scan, the feed's diff-tree keeps --root, and the root commit's credential under log.showRoot=false is found and named (round 9d: this slot held the count's derivation from the objects, retired with the count)" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    root="$(git -C "$REPO" rev-parse HEAD)"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    git_stripping_root_from_log
    run _hook_in "$REPO" -c 'git log -p -U0 --format="commit %H" --root "$1" | grep -c "^@@"' _ "$(git -C "$REPO" rev-parse HEAD)"   # the shim as git log meets it: the root's hunk gone, one of two
    [ "$output" = 1 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: commit ${root:0:10} ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

# ── the replace-ref gate: only where a scan would run ────────────────────
# The refusal above prevents a false CLEAN REPORT, and only a scan that runs
# makes one. Where the denylist file is absent and the credential scan is
# skipped (ROMP_NO_GITLEAKS) or has no binary, nothing is scanned and nothing is
# reported, so a replace ref falsifies nothing and the push is not the hook's
# to refuse: a clone that never asked for either scan is unaffected, the rule
# CLAUDE.md states. The gate reads the two predicates the scans' own early
# returns read (identifier_scan_armed, credential_scan_armed), and it is per
# CLONE, read once ahead of the per-ref loops: a push a scan would read nothing
# of (a deletion of a remote ref alone, which both scans skip before reading a
# byte; a denylist of comments alone, which arms a scan that greps for nothing)
# is refused under a replace ref all the same, whatever object the ref
# replaces. Fail-safe, and left so: a gate inside the two per-ref loops would
# refuse twice.

# A PATH with no gitleaks on it: every directory of PATH that holds one is
# replaced by a shadow directory linking to everything else in it, so the
# hook's other tools still resolve and `command -v gitleaks` finds nothing.
path_without_gitleaks() {
    local dir shadow rest="" f
    local IFS=:
    for dir in $PATH; do
        if [ -n "$dir" ] && [ -x "$dir/gitleaks" ]; then
            shadow="$TEST_DIR/no-gitleaks/${dir//\//_}"
            mkdir -p "$shadow"
            for f in "$dir"/*; do
                [ "${f##*/}" = gitleaks ] || ln -s "$f" "$shadow/${f##*/}"
            done
            dir="$shadow"
        fi
        rest="$rest${rest:+:}$dir"
    done
    export PATH="$rest"
}

@test "a replace ref in a clone that asked for neither scan passes with no replace line: no scan runs, so no clean report is at stake" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"      # no denylist; ROMP_NO_GITLEAKS=1 from setup skips the credential scan
    commit_file base.txt "notes-api" "base"
    commit_file file.txt "nothing to see" "clean"
    substitute_for "$(git -C "$REPO" rev-parse HEAD)"
    run git -C "$REPO" for-each-ref refs/replace/                    # the ref is there for the hook to find
    [ -n "$output" ]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "the same with the credential scan not skipped but no gitleaks on PATH: the notice prints, no replace line does, and the push passes" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    commit_file base.txt "notes-api" "base"
    commit_file file.txt "nothing to see" "clean"
    substitute_for "$(git -C "$REPO" rev-parse HEAD)"
    unset ROMP_NO_GITLEAKS ROMP_GITLEAKS                             # the premise is that NO binary resolves: not by name (a run under ROMP_GITLEAKS= a pinned copy names one) and not on PATH
    path_without_gitleaks
    run _hook_in "$REPO" -c 'command -v gitleaks'                    # the shape as the hook meets it: no binary resolves
    [ "$status" -ne 0 ]
    run _hook_in "$REPO" -c 'command -v git >/dev/null && command -v awk >/dev/null && command -v sed >/dev/null'   # its other tools still do
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"gitleaks not installed, pushing WITHOUT a secret scan"* ]]
    [[ "$output" != *"replace ref"* ]]
}

@test "a replace ref with the denylist alone (the credential scan skipped) is refused on the premise: the identifier scan would run and report" {
    commit_file base.txt "notes-api" "base"
    commit_file file.txt "nothing to see" "clean"
    substitute_for "$(git -C "$REPO" rev-parse HEAD)"
    run_hook                                                         # the denylist and ROMP_NO_GITLEAKS=1 from setup
    [ "$status" -eq 1 ]
    [[ "$output" == *"this clone carries a replace ref (refs/replace/$(git -C "$REPO" rev-parse HEAD))"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "a replace ref with gitleaks alone (no denylist) is refused on the premise: the credential scan would run and report" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    commit_file base.txt "notes-api" "base"
    commit_file file.txt "nothing to see" "clean"
    substitute_for "$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"this clone carries a replace ref (refs/replace/$(git -C "$REPO" rev-parse HEAD))"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "a push that only DELETES a remote ref is refused under a replace ref when a scan is armed: the gate is per clone, though both scans skip a delete line before reading a byte" {
    add_remote
    commit_file base.txt "notes-api" "base"
    commit_file file.txt "nothing to see" "clean"                # a second commit: the substitute is built over the commit's parent
    git -C "$REPO" push -q origin main
    sha="$(git -C "$REPO" rev-parse HEAD)"
    substitute_for "$sha"
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< "refs/heads/main $ZERO refs/heads/main $sha"   # the denylist armed (setup); a line neither scan reads past
    [ "$status" -eq 1 ]
    [[ "$output" == *"this clone carries a replace ref (refs/replace/$sha)"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

# ── a text file git calls binary, hidden from the identifier scan ────────
# Both content checks read what git calls text: git grep -I skips a blob git
# calls binary and diff-tree -p prints no line for one, and git calls a blob
# binary by its PATH's diff attribute (a -diff line or the binary macro, in
# .gitattributes, .git/info/attributes or the file core.attributesFile names;
# a driver with diff.<driver>.binary true, whatever its name) and by its SIZE
# (over core.bigFileThreshold, in the diff and not in the grep) as well as by
# its bytes. Found by execution (2026-09-21): a text file under -diff carrying
# a denylist string went through a real push with the denylist armed and
# nothing printed, and so did one over the size key, and one under a driver
# named `set` or `unspecified`, check-attr's own words. The hook keeps no list
# of git's rules: it takes git's own verdict from each half's read (the same
# grep, asked what it read; a --numstat over the pair a one-parent commit's
# diff reads; a merge's combined patch itself, section by section), and a
# blob so named whose bytes are text (no NUL in the first 8000)
# refuses the push rather than being scanned, naming the tip or the commit,
# the path and what its diff attribute reads; a blob that is binary by its
# bytes passes as binaries always have. The line quotes the attribute for the
# report alone and never decides by it (a driver may be named `set`,
# `unspecified` or `unset`). Each paragraph of the advice prints only where a
# line named its cause (the round 4 refuter, 2026-09-22): the attribute's where
# a line named one, or could not read it, with what to do about it (drop it, or
# keep the file text on purpose with an explicit diff line that outranks it),
# the configuration key's, which states that explicit line in its own words,
# where a line named none (or, for a one-parent commit's change of a file binary by its
# bytes, that previous version as the cause whether or not the key is set,
# the key's facts beside it where it is, with the fetch remedy and not the
# key's), and a rename or copy of such a file is refused the same way,
# since its bytes reach the remote under the new path. The real-push cases
# push with the hook installed, so the remote's state is asserted too.

# The hook installed for one real push of main to the bare remote; the
# fixture's own commits run no hooks before or after.
push_main_through_hook() {
    add_remote
    push_main_through_installed_hook
}
push_main_through_installed_hook() {   # the remote is the case's own (add_remote), so a case that pushed once without the hook pushes again with it
    mkdir -p "$TEST_DIR/hooks"
    ln -sf "$HOOK" "$TEST_DIR/hooks/pre-push"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/hooks"
    run git -C "$REPO" push origin main
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
}
remote_holds_main() { git -C "$TEST_DIR/remote.git" rev-parse -q --verify refs/heads/main >/dev/null; }
attributes() {   # <line>: a committed .gitattributes
    printf '%s\n' "$1" > "$REPO/.gitattributes"
    git -C "$REPO" add .gitattributes
    git -C "$REPO" commit -qm "attributes"
}

@test "a text file under -diff carrying a banned string is refused rather than scanned, naming the tip, the path and the attribute, and the commit that added the blob the tip holds is not named a second time; the remote holds nothing" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    # the road as git applies it: the grep skips the file and the diff prints no line for it
    run _hook_in "$REPO" -c 'git grep -i -I -l -F -e TESTHOST "$1" --' _ "$sha"
    [ "$status" -eq 1 ]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- notes.txt' _ "$sha"
    [[ "$output" == *"Binary files"* ]]
    push_main_through_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"notes.txt in commit ${sha:0:10} is text that"* ]]      # the tip holds the blob and judged it: the commit that added it is not a second verdict
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]
    [[ "$output" == *"core.attributesFile"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    [[ "$output" != *"personal identifier"* ]]      # refused as unscanned, not as a finding: the scan could not read the file
    ! remote_holds_main
}

@test "the same file carrying NO banned string is refused on the premise alone: what the scan cannot read it cannot call clean; the remote holds nothing" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides from the identifier scan"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" != *"BLOCKED"* ]]
    ! remote_holds_main
}

@test "a genuinely binary blob under the binary attribute passes: the scan never read binaries, and the attribute adds nothing" {
    attributes 'img.bin binary'
    printf 'ab\0cd TESTHOST ef\n' > "$REPO/img.bin"       # a NUL in the first bytes: binary by git's own rule, string and all
    git -C "$REPO" add img.bin
    git -C "$REPO" commit -qm "an image"
    run _hook_in "$REPO" -c 'git check-attr diff img.bin'
    [[ "$output" == *"diff: unset"* ]]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "a text file under a driver whose diff.<driver>.binary is true is refused, the line naming the driver" {
    git -C "$REPO" config diff.hide.binary true
    attributes 'notes.txt diff=hide'
    commit_file notes.txt "seen on TESTHOST" "a banned string under a binary driver"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git grep -i -I -l -F -e TESTHOST "$1" --' _ "$sha"
    [ "$status" -eq 1 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (diff=hide, binary) hides from the identifier scan"* ]]
    [[ "$output" != *"personal identifier"* ]]
}

@test "a driver with no binary setting hides nothing: the string under it is found as a hit, not refused as hidden" {
    hiding_textconv                                          # diff=hide with a textconv alone, as the credential cases use it
    commit_file probe.py "seen on TESTHOST" "a banned string under a textconv driver"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"would publish a personal identifier"* ]]
    [[ "$output" == *"  probe.py"* ]]
    [[ "$output" != *"hides from the identifier scan"* ]]
}

@test "the -diff line in .git/info/attributes rather than the tree hides the file the same way, and is refused the same way" {
    printf 'notes.txt -diff\n' > "$REPO/.git/info/attributes"
    commit_file notes.txt "seen on TESTHOST" "a banned string, the attribute outside the tree"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git grep -i -I -l -F -e TESTHOST "$1" --' _ "$sha"
    [ "$status" -eq 1 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides from the identifier scan"* ]]
    [[ "$output" == *".git/info/attributes"* ]]              # the advice names the place
}

@test "a text file under -diff added in a middle commit and deleted before the tip is refused, the line naming the commit" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file notes.txt "remove it"                        # the tip is clean: only the per-commit half can name it
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: notes.txt in commit ${leak:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]          # the attribute paragraph: the line named one
    [[ "$output" == *"A rename or copy of such a file is content too"* ]]
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]   # the key's paragraph: absent, no line having named the key's facts
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
}

@test "a pure RENAME of a hidden text file the remote already holds is refused too, the line naming the new path, and the advice naming the attribute as the cause, the explicit diff remedy and the rename clause" {
    add_remote
    attributes 'notes-*.txt -diff'
    commit_file notes-a.txt "nothing to see" "a clean file under a pattern -diff"
    git -C "$REPO" push -q origin main                       # the original is on the remote; the rename is all this push adds
    before="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" mv notes-a.txt notes-b.txt
    git -C "$REPO" commit -qm "rename"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook "$before"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: notes-b.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"notes-b.txt in commit ${sha:0:10} is text"* ]]         # the tip holds the renamed blob and refused it: the rename commit is not a second verdict (the per-commit rename rule is held by the removed-at-the-tip cases below)
    [[ "$output" != *"notes-a.txt"* ]]                        # the old path is a deletion: nothing to read there
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]
    [[ "$output" == *"or keep the file text on purpose with an explicit \"<path> diff\" line (a later line in .gitattributes overrides a -diff inherited from a broader pattern"* ]]
    [[ "$output" == *"A rename or copy of such a file is content too: its bytes reach the remote under the new path, so the refusal is about the attribute, not the rename."* ]]
    [[ "$output" != *"personal identifier"* ]]
}

# The per-commit read judges the PAIR the diff judges (-M): a renamed file is
# read with the path it came from, so a file under -diff renamed to a plain
# path and changed in the same commit prints "Binary files ... differ" and its
# new lines go unread, while a PURE rename prints nothing at all (the same blob
# under a new path) and is judged as the addition of its new path, the rule
# the case above set. So the explicit diff line for the NEW path, the remedy
# the advice names, lifts a pure rename's refusal; a changed rename from a
# hidden path is refused, the line saying the earlier path counted.

@test "the explicit diff line for the NEW path lifts a pure rename's refusal: the same rename with a later \"notes-b.txt diff\" line passes, the tip's grep reading the file" {
    # the tip holds the renamed blob and its grep reads it under the explicit line: the tip-owns rule decides this case, and the
    # exception itself (the addition verdict of the new path lifting a pure rename's binary pair verdict) is pinned by the two
    # cases below, which move the blob off the tip
    add_remote
    attributes 'notes-*.txt -diff'
    commit_file notes-a.txt "nothing to see" "a clean file under a pattern -diff"
    git -C "$REPO" push -q origin main
    before="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" mv notes-a.txt notes-b.txt
    git -C "$REPO" commit -qm "rename"
    printf '%s\n' 'notes-*.txt -diff' 'notes-b.txt diff' > "$REPO/.gitattributes"
    git -C "$REPO" add .gitattributes
    git -C "$REPO" commit -qm "keep notes-b.txt text on purpose"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git check-attr diff notes-a.txt notes-b.txt'          # the old path still hidden by the pattern, the new one text
    [[ "$output" == *"notes-a.txt: diff: unset"* ]]
    [[ "$output" == *"notes-b.txt: diff: set"* ]]
    run _hook_in "$REPO" -c 'git grep -I -l -e "" "$1" -- notes-b.txt' _ "$sha"    # the tip's grep reads it
    [ "$status" -eq 0 ]
    run_hook "$before"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "the same lifted rename with notes-b.txt GONE at the tip passes: the blob is on the remote and not at the tip, so the per-commit half judges the rename commit, where the pair verdict is binary (the old path under the pattern) and the addition verdict of the new path is text under the explicit line; the exception is what passes it" {
    add_remote
    attributes 'notes-*.txt -diff'
    commit_file notes-a.txt "nothing to see" "a clean file under a pattern -diff"
    git -C "$REPO" push -q origin main
    before="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" mv notes-a.txt notes-b.txt
    git -C "$REPO" commit -qm "rename"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    printf '%s\n' 'notes-*.txt -diff' 'notes-b.txt diff' > "$REPO/.gitattributes"
    git -C "$REPO" add .gitattributes
    git -C "$REPO" commit -qm "keep notes-b.txt text on purpose"
    remove_file notes-b.txt "remove it"                                            # gone at the tip: the rename commit's blob is the per-commit half's to judge
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -M --root --no-commit-id "$1"' _ "$sha"          # the pair: binary (the old path under the pattern)
    [ "$output" = "-"$'\t'"-"$'\t'"notes-a.txt => notes-b.txt" ]
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat --no-renames --root --no-commit-id "$1"' _ "$sha"   # the addition of the new path: text under the explicit line (one line added), the old path binary under the pattern
    [[ "$output" == *"1"$'\t'"0"$'\t'"notes-b.txt"* ]]
    [[ "$output" == *"-"$'\t'"-"$'\t'"notes-a.txt"* ]]
    run_hook "$before"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "the refusing twin: the same rename gone at the tip with NO later diff line for the new path is refused as hidden, the line naming the new path in the rename commit and the attribute: the addition verdict of the new path is binary under the pattern, so the exception does not apply" {
    add_remote
    attributes 'notes-*.txt -diff'
    commit_file notes-a.txt "nothing to see" "a clean file under a pattern -diff"
    git -C "$REPO" push -q origin main
    before="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" mv notes-a.txt notes-b.txt
    git -C "$REPO" commit -qm "rename"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file notes-b.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat --no-renames --root --no-commit-id "$1"' _ "$sha"   # the addition of the new path: binary under the pattern
    [[ "$output" == *"-"$'\t'"-"$'\t'"notes-b.txt"* ]]
    run_hook "$before"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: notes-b.txt in commit ${sha:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"notes-a.txt"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"answered for fewer paths"* ]]
    [[ "$output" != *"personal identifier"* ]]
}

@test "a file under -diff renamed to a plain path AND changed in the same commit, the change carrying the string, removed before the tip, is refused: the diff judged the pair by the path it came from and printed no hunk" {
    add_remote
    attributes 'notes-*.txt -diff'
    printf 'line %s\n' 1 2 3 4 5 6 7 8 9 10 > "$REPO/notes-a.txt"                 # ten lines, so one added line keeps the pair above git's similarity floor
    git -C "$REPO" add notes-a.txt
    git -C "$REPO" commit -qm "a clean file under a pattern -diff"
    git -C "$REPO" push -q origin main
    before="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" mv notes-a.txt plain.txt
    printf 'seen on TESTHOST\n' >> "$REPO/plain.txt"
    git -C "$REPO" add plain.txt
    git -C "$REPO" commit -qm "rename and change"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    size="$(git -C "$REPO" cat-file -s "$leak:plain.txt")"
    remove_file plain.txt "remove it"                                            # the tip is clean: only the per-commit half can name it
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$leak"   # the road as git applies it: a rename pair, no hunk
    [[ "$output" == *"rename from notes-a.txt"* ]]
    [[ "$output" == *"Binary files a/notes-a.txt and b/plain.txt differ"* ]]
    run _hook_in "$REPO" -c 'git check-attr diff plain.txt'
    [[ "$output" == *"diff: unspecified"* ]]
    run_hook "$before"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: plain.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the diff read it as a rename, so the attribute of the path it came from counted too) (the blob is $size bytes; core.bigFileThreshold is not set in this clone's configuration)"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"at the tip of"* ]]
}

@test "with no denylist a -diff text file passes and no such line prints: the identifier scan is a no-op, attribute or not" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# The size key: core.bigFileThreshold makes git call every blob over it binary
# in a diff (not in a grep), so the per-commit read prints no hunk for a text
# file over it while check-attr answers `unspecified` for its path: a banned
# string in such a file, added in a middle commit and removed before the tip,
# went through a real push with the denylist armed and nothing printed (the
# round 3 refuters, 2026-09-21). The threshold is stated in the clone's
# configuration, below the file's size.
big_text_file() {   # <path> <last line>: a 150-byte text line, then the line given; text by its bytes, over a threshold of 100
    head -c 150 /dev/zero | tr '\0' 'a' > "$REPO/$1"
    printf '\n%s\n' "$2" >> "$REPO/$1"
}

@test "a text file over core.bigFileThreshold carrying a banned string in a middle commit, the tip clean, is refused rather than scanned, the line naming the commit, the blob's size and the key's value; the remote holds nothing" {
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "seen on TESTHOST"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a banned string in a big text file"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file big.txt "remove it"                              # the tip is clean: only the per-commit half can name it
    # the road as git applies it: the diff prints no hunk, and the attribute names nothing
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- big.txt' _ "$leak"
    [[ "$output" == *"Binary files"* ]]
    run _hook_in "$REPO" -c 'git check-attr diff big.txt'
    [[ "$output" == *"diff: unspecified"* ]]
    push_main_through_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: big.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is 168 bytes; core.bigFileThreshold is 100 in this clone's configuration); the identifier scan did not read it, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary: core.bigFileThreshold"* ]]
    [[ "$output" == *"or keep the file text on purpose with an explicit \"<path> diff\" line in .gitattributes, which outranks the key for a regular file"* ]]   # the explicit-diff remedy, in the key paragraph's own words
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, no line having named an attribute
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    ! remote_holds_main
}

@test "an explicit \"<path> diff\" line outranks the key: the same big text file is judged by content (a hit at the tip and in the commit), never as hidden" {
    git -C "$REPO" config core.bigFileThreshold 100
    attributes 'big.txt diff'
    big_text_file big.txt "seen on TESTHOST"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a banned string in a big text file under an explicit diff line"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- big.txt' _ "$leak"   # the hunk prints
    [[ "$output" == *"+seen on TESTHOST"* ]]
    [[ "$output" != *"Binary files"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the tip of refs/heads/main (${leak:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"commit ${leak:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  big.txt"* ]]
    [[ "$output" != *"git calls binary"* ]]
    [[ "$output" != *"hides from the identifier scan"* ]]
}

@test "the tip half applies no size rule: a big text file carrying the string AT the tip under the key is a HIT by the tip grep, which reads it, and the tip is never called hidden; the commit whose diff printed no hunk for it is not either, since the tip holds the blob" {
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "seen on TESTHOST"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a banned string in a big text file at the tip"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git grep -i -I -l -F -e TESTHOST "$1" --' _ "$sha"       # the grep reads it: the key is the diff's rule, not the grep's
    [ "$status" -eq 0 ]
    [[ "$output" == *"big.txt"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the tip of refs/heads/main (${sha:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"  big.txt"* ]]
    [[ "$output" != *"big.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary"* ]]
    [[ "$output" != *"big.txt in commit ${sha:0:10} is text that"* ]]      # the per-commit diff printed no hunk, but the tip holds the blob and its grep read it: one verdict, the tip's (before: a second, commit-level line for the same bytes)
    [[ "$output" != *"git calls binary"* ]]
    [[ "$output" == *"BLOCKED"* ]]
}

# The population of the per-commit verdict is every post-image BLOB, a
# symlink's as much as a regular file's: a link's target is a blob under the
# size key like any other, the pairwise diff prints "Binary files differ" for
# one over the key and no target, and a link so hidden in a middle commit and
# gone at the tip is read by nothing else (the round 3 auditor, 2026-09-21: a
# real push published a banned string in such a target with the denylist
# armed, the derivation judging regular files alone). No attribute reaches a
# symlink in that diff (an explicit "link diff" line under the key still
# prints no target, checked by execution), so a link's line names none and
# the key is its remedy. Under no key a new link's target is a hunk the
# added-lines pass reads; at the tip the symlink pass reads every target by
# cat-file, key or no key. A TYPE change is judged as the diff prints it, a
# deletion and an addition each alone, by a numstat of the empty tree against
# the commit's tree for its path: the pair's stat is binary when either side
# is, and by it a binary file replaced by a link whose target the diff printed
# in full was refused as hidden. A MODE-ONLY change is not judged: the same
# blob under a new mode has no hunk and no Binary line, while the pair's stat
# calls an unchanged blob over the key binary, and by it a push that published
# nothing new was refused (the round 3 auditor, 2026-09-21).
long_target() {   # a symlink target of 96 bytes, over a threshold of 20, carrying a banned string unless another head is given
    printf '%s, a long target aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' "${1:-seen on TESTHOST}"
}
symlink_commit() {   # <path> <target> <message>: a committed symlink
    ln -s "$2" "$REPO/$1"
    git -C "$REPO" add "$1"
    git -C "$REPO" commit -qm "$3"
}

@test "a SYMLINK whose target is over core.bigFileThreshold and carries a banned string, added in a middle commit and gone at the tip, is refused rather than scanned, the line naming the commit, the link and no attribute; the remote holds nothing" {
    git -C "$REPO" config core.bigFileThreshold 20
    symlink_commit link "$(long_target)" "a banned string in a long symlink target"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    size="$(git -C "$REPO" cat-file -s "$leak:link")"
    remove_file link "remove it"                                 # the tip has no link left: only the per-commit half can name it
    # the road as git applies it: the diff prints no target, the pair's stat a dash for each count
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- link' _ "$leak"
    [[ "$output" == *"new file mode 120000"* ]]
    [[ "$output" == *"Binary files /dev/null and b/link differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1" -- link' _ "$leak"
    [ "$output" = "-"$'\t'"-"$'\t'"link" ]
    push_main_through_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: link in commit ${leak:0:10} is text that git calls binary although it is a symbolic link, whose target this read judges by its size and bytes and by no attribute of the path, so no attribute of its path accounts for the verdict (the blob is $size bytes; core.bigFileThreshold is 20 in this clone's configuration); the identifier scan did not read it, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary: core.bigFileThreshold"* ]]
    [[ "$output" == *"or keep the file text on purpose with an explicit \"<path> diff\" line in .gitattributes, which outranks the key for a regular file"* ]]   # the explicit-diff remedy, in the key paragraph's own words
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, no line having named an attribute
    [[ "$output" == *"for such a link the key is the remedy"* ]]
    [[ "$output" != *"link in commit ${leak:0:10} is text that its diff attribute"* ]]
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    ! remote_holds_main
}

@test "an explicit \"link diff\" line does not reach a symlink: the same link under it is hidden by the key all the same and refused the same way, so the advice names the key as a link's remedy" {
    git -C "$REPO" config core.bigFileThreshold 20
    attributes 'link diff'
    symlink_commit link "$(long_target)" "a banned string in a long symlink target under an explicit diff line"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file link "remove it"
    run _hook_in "$REPO" -c 'git check-attr diff link'
    [[ "$output" == *"link: diff: set"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- link' _ "$leak"   # the attribute lifted nothing: the pairwise diff applies none to a link
    [[ "$output" == *"Binary files /dev/null and b/link differ"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"link in commit ${leak:0:10} is text that git calls binary although it is a symbolic link"* ]]
    [[ "$output" == *"(a one-parent commit's diff applies no attribute to a symbolic link's target, so for such a link the key is the remedy)"* ]]
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, the line naming no attribute
    [[ "$output" != *"ADDS a personal identifier"* ]]
}

@test "the same symlink AT the tip under the key is a HIT by the tip's symlink pass, which reads every target by cat-file whatever the key says, and the tip is never called hidden; the commit whose diff printed no target for it is not either, since the tip holds the blob" {
    git -C "$REPO" config core.bigFileThreshold 20
    symlink_commit link "$(long_target)" "a banned string in a long symlink target at the tip"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the tip of refs/heads/main (${sha:0:10}) would publish a personal identifier"* ]]
    [[ "$output" == *"in the SYMLINK TARGET of link -> seen on TESTHOST, a long target"* ]]
    [[ "$output" != *"link at the tip of refs/heads/main (${sha:0:10}) is text"* ]]
    [[ "$output" != *"link in commit ${sha:0:10} is text that"* ]]         # the per-commit diff printed no target, but the tip holds the blob and its symlink pass read it: one verdict, the tip's
    [[ "$output" != *"git calls binary"* ]]
    [[ "$output" == *"BLOCKED"* ]]
}

@test "a symlink whose target carries the string under no key, added in a middle commit and gone at the tip, is a HIT by the added-lines pass, which reads the target as a hunk, and is never called hidden" {
    symlink_commit link "$(long_target)" "a banned string in a symlink target"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file link "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- link' _ "$leak"   # the target is a hunk
    [[ "$output" == *"+seen on TESTHOST, a long target"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${leak:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  link"* ]]
    [[ "$output" != *"git calls binary"* ]]
    [[ "$output" != *"hides from the identifier scan"* ]]
}

@test "a binary file replaced by a symlink (a TYPE change) whose target is clean, the link GONE at the tip, passes: the diff prints the change as a deletion and an addition and printed the target in full, so the link is judged as the addition it is by the numstat of its new object alone (text), though the pair's stat calls the pair binary; off the tip, that addition verdict is what decides" {
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    rm "$REPO/thing"
    symlink_commit thing "nothing to see" "replaced by a symlink"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file thing "remove it"                                             # gone at the tip: with the link at the tip the tip-owns rule would set the blob aside before the type-change rule is reached
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- thing' _ "$sha"
    [[ "$output" == *"Binary files a/thing and /dev/null differ"* ]]      # the deletion, judged alone
    [[ "$output" == *"+nothing to see"* ]]                                # the addition, printed in full
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1" -- thing' _ "$sha"
    [ "$output" = "-"$'\t'"-"$'\t'"thing" ]                              # the pair's stat: binary on either side
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "a text file under -diff replaced by a symlink whose target carries the string, the link GONE at the tip, is a HIT by the added-lines pass and not hidden: the addition the diff printed is what the link is judged as, and the addition verdict of the new object is text whatever the path's attribute says (the pairwise diff applies none to a link); off the tip, that verdict is what decides" {
    add_remote
    attributes 'thing -diff'
    commit_file thing "nothing to see" "a clean -diff file"
    git -C "$REPO" push -q origin main                          # the hidden file is on the remote; the type change is all this push adds
    before="$(git -C "$REPO" rev-parse HEAD)"
    rm "$REPO/thing"
    symlink_commit thing "seen on TESTHOST" "replaced by a symlink"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file thing "remove it"                               # gone at the tip: the tip's symlink pass reads no link, and the tip-owns rule sets nothing aside
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1" -- thing' _ "$sha"
    [ "$output" = "-"$'\t'"-"$'\t'"thing" ]                              # the pair's stat: binary (the old side under -diff)
    run_hook "$before"
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${sha:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  thing"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"would publish"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a file replaced by a symlink whose target is over the key and carries the string, gone at the tip, is refused, the line naming the commit and the link: the addition the diff judged alone is the one it printed no target for" {
    git -C "$REPO" config core.bigFileThreshold 20
    commit_file thing "clean" "a small file"
    rm "$REPO/thing"
    symlink_commit thing "$(long_target)" "replaced by a long symlink"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    size="$(git -C "$REPO" cat-file -s "$leak:thing")"
    remove_file thing "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- thing' _ "$leak"
    [[ "$output" == *"Binary files /dev/null and b/thing differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: thing in commit ${leak:0:10} is text that git calls binary although it is a symbolic link"* ]]
    [[ "$output" == *"(the blob is $size bytes; core.bigFileThreshold is 20 in this clone's configuration)"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"at the tip of"* ]]
}

@test "a MODE-ONLY change of a text file over the key, the denylist armed, passes through a real push: the same blob under a new mode has no hunk and no Binary line, and the remote holds main" {
    # the tip holds the blob: the tip-owns rule sets it aside before the skip for an unchanged blob is reached, so the skip
    # itself is pinned by the sibling below, which removes the file before the tip
    add_remote
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a clean big text file"
    git -C "$REPO" push -q origin main                          # the blob is on the remote; the mode change is all this push adds
    git -C "$REPO" update-index --chmod=+x big.txt
    git -C "$REPO" commit -qm "a mode-only change"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$sha"       # mode lines alone
    [[ "$output" == *"old mode 100644"* ]]
    [[ "$output" == *"new mode 100755"* ]]
    [[ "$output" != *"Binary files"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1"' _ "$sha"           # the pair's stat: a dash for each count all the same
    [ "$output" = "-"$'\t'"-"$'\t'"big.txt" ]
    push_main_through_installed_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$sha" ]
}

@test "the same MODE-ONLY change with the file GONE at the tip passes through a real push: the blob is on the remote and not at the tip, so the skip for an unchanged blob alone decides (the pair's stat is binary under the key, and judged by it the change would be refused as hidden); the remote holds main" {
    add_remote
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a clean big text file"
    git -C "$REPO" push -q origin main                          # the blob is on the remote
    chmod +x "$REPO/big.txt"                                    # the working tree's mode, then the index's: update-index --chmod alone leaves the working tree behind and the removal below refused
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a mode-only change"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" rm -qf big.txt
    git -C "$REPO" commit -qm "remove it"                       # gone at the tip: the blob is nowhere the tip half reads, so the per-commit half alone judges the mode-only commit
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$sha"       # mode lines alone
    [[ "$output" == *"old mode 100644"* ]]
    [[ "$output" == *"new mode 100755"* ]]
    [[ "$output" != *"Binary files"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1"' _ "$sha"           # the pair's stat: a dash for each count all the same
    [ "$output" = "-"$'\t'"-"$'\t'"big.txt" ]
    run _hook_in "$REPO" -c 'git ls-tree -r HEAD -- big.txt'
    [ -z "$output" ]
    push_main_through_installed_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "the control: the same file with one changed byte under the key, gone at the tip, is refused as hidden, the row kept, and the remote holds the blob's first commit alone" {
    add_remote
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a clean big text file"
    git -C "$REPO" push -q origin main
    before="$(git -C "$REPO" rev-parse HEAD)"
    printf 'x' >> "$REPO/big.txt"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "one byte more"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    size="$(git -C "$REPO" cat-file -s "$sha:big.txt")"
    remove_file big.txt "remove it"                              # gone at the tip: the changed blob is the commit's to judge (at the tip, the tip's grep reads it, whatever the key says)
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$sha"
    [[ "$output" == *"Binary files a/big.txt and b/big.txt differ"* ]]
    push_main_through_installed_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: big.txt in commit ${sha:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is $size bytes; core.bigFileThreshold is 100 in this clone's configuration)"* ]]
    [[ "$output" != *"at the tip of"* ]]      # the tip's grep applies no size rule and read the file
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$before" ]
}

# The TIP owns the blobs its tree holds: a per-commit candidate whose blob is
# at the tip under any path is not judged by the per-commit half, since the
# tip half read it (its grep, or its symlink pass for a link's target) or
# refused it as hidden there, so the per-commit road reaches only content
# absent from the tip. Before this rule a clean big text file added at the
# tip under the key was refused on the commit line while the tip's grep had
# read it, and a hit at the tip carried a second, commit-level hidden line
# for the same bytes (the round 3 auditors, 2026-09-21). The cases above that
# add a hidden file at the tip assert the tip's line alone for the same
# reason.

@test "a CLEAN big text file added at the tip under the key passes: the tip's grep read it, and the commit whose diff printed no hunk for it is not judged, since the tip holds the blob" {
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a clean big text file at the tip"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- big.txt' _ "$sha"   # the diff printed no hunk for it
    [[ "$output" == *"Binary files"* ]]
    run _hook_in "$REPO" -c 'git grep -I -l -e "" "$1" -- big.txt' _ "$sha"                                        # the grep read it: the key is the diff's rule, not the grep's
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "the same blob at the tip under ANOTHER path (moved after the commit that added it) is the tip's to judge too: neither the addition under the key nor the pure rename is called hidden, and the push passes" {
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a clean big text file"
    git -C "$REPO" mv big.txt moved.txt
    git -C "$REPO" commit -qm "moved"
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# A one-parent commit that turns a file binary by its bytes into a TEXT file:
# the pair is binary when either side is, so the diff prints "Binary files
# differ" and no hunk for the new text, and the commit is refused rather than
# scanned (the hook header's disclosed fail-closed shape). No attribute
# accounts for that verdict and the key cannot lift it, so the line names the
# cause the hook can read, the previous version's bytes, whether or not the
# key is set (with the key set, the r3e text named the key's facts and its
# remedy instead, a remedy that lifts nothing there; the round 3 auditor,
# 2026-09-22), and the advice names the remedy: the
# hook scans only commits new to every fetched remote, so a commit some remote
# holds is out of range once that remote is fetched. Three commits in this
# repository's own history have the shape, refused when a clone with no
# remote-tracking refs pushes the history as a new ref (2026-09-22). The
# merge twin (a parent's version binary, the merge's result text: the combined
# patch prints Binary the same way) and the rename twin (the file renamed in
# the same change, the diff reading the pair from the old path) name their
# cause the same way since round 5, the parent or the old path named in the
# line; before, each was refused with the two-fact line and the key's advice,
# the cause unnamed and the fetch remedy absent (the round 4 refuters,
# 2026-09-22). A type change and a merge's rename candidate read no previous
# version: the addition verdict of the new object alone decided them.

@test "a one-parent commit turning a NUL-carrying file into a text file carrying the string, gone at the tip, is refused rather than scanned, the line naming the previous version's bytes as the cause and the advice the fetch remedy; the key's facts and the key advice are absent, since the key is not the cause" {
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    commit_file thing "seen on TESTHOST" "now a text file carrying the string"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file thing "remove it"                            # gone at the tip: only the per-commit half can name it
    # the road as git applies it: the pair is binary on the old side, so the diff prints no hunk for the new text
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- thing' _ "$leak"
    [[ "$output" == *"Binary files a/thing and b/thing differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    run _hook_in "$REPO" -c 'git check-attr diff thing'
    [[ "$output" == *"diff: unspecified"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: thing in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict; the previous version of the file is binary by its bytes (a NUL in its first 8000), which made git print no text diff for the change, and the identifier scan could not read the new text, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names the previous version's bytes as the cause, the hook scans only commits new to every fetched remote: if the commit is already on some remote, fetch that remote first and push again, or push from a clone that has fetched it."* ]]
    [[ "$output" == *"set the diff attribute on the PREVIOUS version's path: an explicit \"<path> diff\" line in .gitattributes, for the old path where the line names one and for the file's own path otherwise"* ]]   # the second remedy of that line: the attribute on the pre-image's path lifts the pair to text (the round 5 refuter, 2026-09-22)
    [[ "$output" != *"core.bigFileThreshold is not set"* ]]   # the key is not the cause here: the line states the cause, not the key's facts
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, the line having said no attribute accounts for the verdict
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "the same shape with the text file KEPT at the tip is judged by the tip alone: the tip's grep reads the file and reports the hit, and the commit whose diff printed no hunk for it is not named, since the tip holds the blob" {
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    commit_file thing "seen on TESTHOST" "now a text file carrying the string"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the tip of refs/heads/main (${sha:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"  thing"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"previous version"* ]]
}

@test "the same shape with core.bigFileThreshold SET below the new blob's size is refused on the previous version's bytes all the same, the line naming that cause with the key's two facts beside it and the advice the fetch remedy; the key's advice is absent, since raising the key lifts nothing when the old side is binary by its bytes" {
    git -C "$REPO" config core.bigFileThreshold 10
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    commit_file thing "seen on TESTHOST" "now a text file carrying the string"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    size="$(git -C "$REPO" cat-file -s "$leak:thing")"
    [ "$size" -gt 10 ]                                       # over the key too: two candidate causes, one certain
    remove_file thing "remove it"                            # gone at the tip: only the per-commit half can name it
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- thing' _ "$leak"
    [[ "$output" == *"Binary files a/thing and b/thing differ"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: thing in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict; the previous version of the file is binary by its bytes (a NUL in its first 8000), which made git print no text diff for the change whatever the key says (the blob is $size bytes; core.bigFileThreshold is 10 in this clone's configuration), and the identifier scan could not read the new text, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names the previous version's bytes as the cause, the hook scans only commits new to every fetched remote"* ]]
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]   # the key's advice: absent, the key being no cause here
    [[ "$output" != *"raise the key above the size"* ]]
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, the line having said no attribute accounts for the verdict
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "a MERGE whose result turns a NUL-carrying file both parents hold into a text file carrying the string, gone at the tip, is refused rather than scanned, the line naming a parent's version as the cause and the advice the fetch remedy; the key advice is absent: the merge twin of the disclosed shape" {
    add_remote
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
    commit_file thing "seen on TESTHOST" "merge side, thing now a text file carrying the string"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file thing "remove it"                            # gone at the tip: only the per-commit half can name it
    # the road as git applies it: both parents' versions are binary by their bytes, so the combined patch prints no hunk for the new text
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- thing' _ "$merge"
    [[ "$output" == *"Binary files differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    run _hook_in "$REPO" -c 'git check-attr diff thing'
    [[ "$output" == *"diff: unspecified"* ]]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: thing in commit ${merge:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict; the previous version of the file in parent 1 of the merge is binary by its bytes (a NUL in its first 8000), which made git print no text diff for the change, and the identifier scan could not read the new text, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names the previous version's bytes as the cause, the hook scans only commits new to every fetched remote: if the commit is already on some remote, fetch that remote first and push again, or push from a clone that has fetched it."* ]]
    [[ "$output" == *"set the diff attribute on the PREVIOUS version's path: an explicit \"<path> diff\" line in .gitattributes, for the old path where the line names one and for the file's own path otherwise"* ]]   # the second remedy of that line: the attribute on the pre-image's path lifts the pair to text (the round 5 refuter, 2026-09-22)
    [[ "$output" != *"core.bigFileThreshold is not set"* ]]   # the key is not the cause here: the line states the cause, not the key's facts
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, the line having said no attribute accounts for the verdict
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "a one-parent commit RENAMING a NUL-carrying file into a text file carrying the string in the same change, gone at the tip, is refused rather than scanned, the line naming the previous version at the path the diff read it from as the cause and the advice the fetch remedy; the key advice and the rename clause are absent: the rename twin of the disclosed shape" {
    { printf 'line %s\n' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; printf 'x\0y\n'; } > "$REPO/old.txt"   # twenty lines and a NUL: binary by its bytes, and similar enough to the text version for -M to pair them
    git -C "$REPO" add old.txt
    git -C "$REPO" commit -qm "a file binary by its bytes"
    git -C "$REPO" mv old.txt new.txt
    { printf 'line %s\n' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; printf 'seen on TESTHOST\n'; } > "$REPO/new.txt"
    git -C "$REPO" add new.txt
    git -C "$REPO" commit -qm "renamed and made text, the string in the change"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file new.txt "remove it"                          # gone at the tip: only the per-commit half can name it
    # the road as git applies it: a rename pair whose old side is binary, so the diff prints no hunk for the new text
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$leak"
    [[ "$output" == *"rename from old.txt"* ]]
    [[ "$output" == *"Binary files a/old.txt and b/new.txt differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r --raw -M -z --root --no-commit-id "$1" | tr "\0" "|"' _ "$leak"      # the report re-derives the old path from this listing's R row
    [[ "$output" == *" R"*"|old.txt|new.txt|"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: new.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict; the previous version of the file (at old.txt, the path the diff read it from) is binary by its bytes (a NUL in its first 8000), which made git print no text diff for the change, and the identifier scan could not read the new text, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names the previous version's bytes as the cause, the hook scans only commits new to every fetched remote"* ]]
    [[ "$output" == *"set the diff attribute on the PREVIOUS version's path: an explicit \"<path> diff\" line in .gitattributes, for the old path where the line names one and for the file's own path otherwise"* ]]   # the second remedy: for a rename the OLD path, the one the line names (the round 5 refuter, 2026-09-22)
    [[ "$output" != *"the diff read it as a rename, so the attribute of the path it came from counted too"* ]]   # the cause line names the old path itself
    [[ "$output" != *"core.bigFileThreshold is not set"* ]]
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, the line having said no attribute accounts for the verdict
    [[ "$output" != *"at the tip of"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

# A MERGE is judged by its combined patch, the read the scan makes for one
# (diff-tree -p -c), parsed section by section, since that patch judges by a
# rule of its own that no verdict against each parent reproduces: it applies
# no size rule, so a big text file resolved in a merge prints its hunk and is
# read, and it applies a path's diff attribute to a SYMLINK as the pairwise
# diff does not, so a merge's own link at a -diff path prints "Binary files
# differ" and no target. Judged against each parent (the round 3 auditor,
# 2026-09-21, by real pushes), that link's banned target, gone at the tip,
# was PUBLISHED with the denylist armed, and a clean big file the merge
# resolved was refused as hidden. A path the patch prints nothing for is a
# pure rename (the same blob under a new path, held by some parent under a
# path the merge lacks: the candidates are read from the merge's deletions
# against EACH parent, since the combined listing names a deletion only when
# every parent held the path, and content both parents held under two paths,
# moved to a third with both gone, met no candidate and was refused as
# unscanned; the round 3 auditor, 2026-09-22), judged as the addition of its
# new path as a one-parent commit's is; a path it prints the header alone for
# (an added empty file:
# no hunk, no Binary line) that is no rename is a candidate judged by its
# bytes, where an empty blob passes (the r3d text refused such a merge as
# unscanned; the round 3 auditor, 2026-09-22); a path with no section at all
# that is no rename is a short read, refused with the other fail-closed arms
# below. The patch's header quotes a path holding a byte git escapes (a tab,
# a quote, a backslash, and any byte over 127 under core.quotePath's default,
# so every non-ASCII path) with C escapes, undone before the join so the line
# names the path byte for byte; a path left quoted would meet no row. Each of
# the four has its case, the octal one red with the octal loop narrowed (the
# round 4 refuter, 2026-09-22).
merge_fixture() {   # a base the remote holds, a side branch and a main commit, the merge left open (--no-commit) for the case's own change; BASE is the remote's sha
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
}
is_merge() {   # <sha>: two parents
    [ "$(git -C "$REPO" rev-list --parents -n 1 "$1" | wc -w)" -eq 3 ]
}

@test "a MERGE's own symlink at a -diff path, a banned string in its target and the link gone at the tip, is refused rather than scanned through a real push, the line naming the merge, the link and the attribute the combined patch applied to it; the remote stays at the base" {
    attributes 'link -diff'
    merge_fixture
    ln -s "seen on TESTHOST" "$REPO/link"
    git -C "$REPO" add link
    git -C "$REPO" commit -qm "the merge adds a link under -diff"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file link "remove it"                                 # gone at the tip: only the per-commit half can name it
    # the road as git applies it: the combined patch applies the attribute to the link and prints no target; the verdict against each parent prints a count
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- link' _ "$merge"
    [[ "$output" == *"Binary files differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1" -- link' _ "$merge"
    [[ "$output" != *"-"$'\t'"-"* ]]
    push_main_through_installed_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: link in commit ${merge:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]
    [[ "$output" != *"it is a symbolic link"* ]]                # the label read the attribute, which the combined patch applied to the link
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" != *"at the tip of"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the same merge's symlink under NO attribute is a HIT by the added-lines pass, which reads the target as the merge's own added line, and is never called hidden" {
    merge_fixture
    ln -s "seen on TESTHOST" "$REPO/link"
    git -C "$REPO" add link
    git -C "$REPO" commit -qm "the merge adds a link"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file link "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- link' _ "$merge"   # the target is a hunk, in neither parent
    [[ "$output" == *"++seen on TESTHOST"* ]]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${merge:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  link"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"printed no verdict"* ]]                  # the hunk was honoured: neither the hidden line nor the short read (a hunk not honoured would print one or the other)
}

@test "a clean big text file a MERGE adds under the key, gone at the tip, passes through a real push: the combined patch applies no size rule and printed its hunk, which the scan read; the remote holds main" {
    git -C "$REPO" config core.bigFileThreshold 100
    merge_fixture
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "the merge adds a big clean text file"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file big.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- big.txt' _ "$merge"   # the hunk prints: no size rule in the combined patch
    [[ "$output" == *"++nothing to see"* ]]
    [[ "$output" != *"Binary files"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1" -- big.txt' _ "$merge"        # the verdict against each parent: a dash for each count (before: the refusal's ground)
    [[ "$output" == *"-"$'\t'"-"$'\t'"big.txt"* ]]
    push_main_through_installed_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "a big text file a MERGE resolves from parents over the key, the resolution carrying the string and gone at the tip, is a HIT naming the merge and is not called hidden: the combined patch printed the hunk the scan read, whatever the verdict against each parent" {
    git -C "$REPO" config core.bigFileThreshold 100
    add_remote
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a big clean text file"
    git -C "$REPO" push -q origin main                          # the parents' blob is on the remote; the resolution is the merge's own
    base="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
    big_text_file big.txt "resolved on TESTHOST"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "merge side, the big file resolved"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file big.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- big.txt' _ "$merge"
    [[ "$output" == *"++resolved on TESTHOST"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root --no-commit-id "$1" -- big.txt' _ "$merge"
    [[ "$output" == *"-"$'\t'"-"$'\t'"big.txt"* ]]
    run_hook "$base"
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${merge:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  big.txt"* ]]
    [[ "$output" != *"is text that"* ]]                        # before: the same push carried a hidden line for the merge beside the hit
    [[ "$output" != *"git calls binary"* ]]
    [[ "$output" != *"printed no verdict"* ]]                  # the hunk was honoured: no short read either
}

@test "a MERGE's own pure RENAME of a big text file under the key, gone at the tip, is refused as hidden naming the new path: the combined patch prints nothing for a pure rename, so the addition verdict of its new path decides, as for a one-parent commit, and no rename clause is added since the patch reads the new path's attribute alone" {
    git -C "$REPO" config core.bigFileThreshold 100
    add_remote
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a big clean text file"
    git -C "$REPO" push -q origin main
    base="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
    git -C "$REPO" mv big.txt moved.txt
    git -C "$REPO" commit -qm "merge side, the big file moved"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    size="$(git -C "$REPO" cat-file -s "$merge:moved.txt")"
    remove_file moved.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- moved.txt big.txt' _ "$merge"   # nothing at all: the one change the patch prints nothing for
    [ -z "$output" ]
    run_hook "$base"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: moved.txt in commit ${merge:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is $size bytes; core.bigFileThreshold is 100 in this clone's configuration)"* ]]
    [[ "$output" != *"the diff read it as a rename"* ]]
    [[ "$output" != *"big.txt"* ]]
    [[ "$output" != *"printed no verdict"* ]]                  # a rename is not a short read
}

@test "a MERGE's own pure rename of a plain file, its mode changed, gone at the tip, passes: the patch prints the header alone for it, the addition verdict of the new path is text, and no short read is claimed" {
    add_remote
    commit_file plain.txt "nothing to see" "a plain file"
    git -C "$REPO" push -q origin main
    base="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
    git -C "$REPO" mv plain.txt moved.txt
    chmod 755 "$REPO/moved.txt"
    git -C "$REPO" add moved.txt
    git -C "$REPO" commit -qm "merge side, the plain file moved and made executable"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file moved.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- moved.txt plain.txt' _ "$merge"   # the header alone: the mode lines, no hunk, no Binary line (both paths named, so the rename is detected as it is in the hook's whole read; a pathspec that left the deletion out would show an addition)
    [[ "$output" == *"diff --combined moved.txt"* ]]
    [[ "$output" == *"mode 100644,100644..100755"* ]]
    [[ "$output" != *"@@"* ]]
    [[ "$output" != *"Binary files"* ]]
    run_hook "$base"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# Content BOTH parents hold under DIFFERENT paths, moved by the merge to a
# third path with both sources gone: the combined listing names a deletion
# only when every parent held the path, and each source differs from one
# parent alone, so neither reaches the merge's deletions and the new path was
# no rename candidate; the patch prints nothing for it (-M pairs it with an
# identical blob in every parent), so it had no section, and the join's
# short-read arm refused a legal merge as unscanned, naming a read that had
# answered whole (the round 3 auditor, 2026-09-22, by real pushes). The
# candidates now come from the merge's deletions against EACH parent, so
# such a path is judged as the addition of its new path like any pure
# rename: text passes, and a big file under the key is refused as hidden.
third_path_merge() {   # <content> [pushed]: parent A holds the content at a.txt, parent B at c.txt (both on the remote when asked); the merge holds it at b.txt alone, both sources gone; the file gone at the tip. BASE is the remote's main
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file c.txt "$1" "side: the content at c.txt"
    git -C "$REPO" checkout -q main
    commit_file a.txt "$1" "main: the same content at a.txt"
    if [ "${2:-}" = pushed ]; then
        git -C "$REPO" push -q origin main side
        BASE="$(git -C "$REPO" rev-parse HEAD)"
    fi
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
    git -C "$REPO" rm -q -f a.txt c.txt                     # -f: the open merge staged c.txt
    printf '%s\n' "$1" > "$REPO/b.txt"
}
third_path_committed() {   # the merge committed, then the file removed at the tip; merge is its sha
    git -C "$REPO" add b.txt
    git -C "$REPO" commit -qm "merge side, the shared content moved to a third path"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file b.txt "remove it"
}

@test "content BOTH parents hold under two paths, moved by a MERGE to a third path with both sources gone and gone at the tip, passes through a real push: the patch prints nothing for it and neither source is among the combined listing's deletions, but a parent holds the blob under a path the merge lacks, so it is a rename candidate judged by the addition verdict of its new path, text; no short read is claimed, and the remote holds main" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames --root -c --no-commit-id "$1"' _ "$merge"
    [[ "$output" == *"AA"$'\t'"b.txt"* ]]                     # the combined listing: the addition alone, neither deletion (each differs from one parent alone)
    [[ "$output" != *"a.txt"* ]]
    [[ "$output" != *"c.txt"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$merge"   # the patch: nothing at all for the merge
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames -m --no-commit-id "$1"' _ "$merge"         # against each parent: a deletion of each source
    [[ "$output" == *"D"$'\t'"a.txt"* ]]
    [[ "$output" == *"D"$'\t'"c.txt"* ]]
    push_main_through_installed_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "the same shape with the string in the content, the source commits new to the remote: the two source commits are the hits (each ADDS the line), the merge adds no line of its own and is neither called hidden nor a short read" {
    third_path_merge "seen on TESTHOST"
    third_path_committed
    a="$(git -C "$REPO" rev-parse "$merge^1")"
    c="$(git -C "$REPO" rev-parse "$merge^2")"
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${a:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  a.txt"* ]]
    [[ "$output" == *"commit ${c:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  c.txt"* ]]
    [[ "$output" != *"commit ${merge:0:10}"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "the same shape with a big text file under core.bigFileThreshold, the sources on the remote, is refused as hidden naming the new path in the merge: the addition verdict of b.txt is binary under the key and its bytes are text; no short read is claimed, and the remote stays at the base" {
    git -C "$REPO" config core.bigFileThreshold 100
    big="$(head -c 300 /dev/zero | tr '\0' 'x')"
    third_path_merge "$big" pushed
    third_path_committed
    size="$(git -C "$REPO" cat-file -s "$merge:b.txt")"
    [ "$size" -gt 100 ]
    push_main_through_installed_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: b.txt in commit ${merge:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is $size bytes; core.bigFileThreshold is 100 in this clone's configuration); the identifier scan did not read it, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"Remove the diff attribute"* ]]                            # the attribute paragraph: absent, the line naming the key's facts and no attribute
    [[ "$output" != *"a.txt"* ]]
    [[ "$output" != *"c.txt"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the same clean content moved to the third path under a NEW MODE passes: the patch prints the header alone for it (the mode line, no hunk, no Binary line), and a rename candidate is judged by the addition verdict of its new path before the header-only rule (the r3e text refused it as hidden with the two-fact line)" {
    third_path_merge "nothing to see" pushed
    chmod 755 "$REPO/b.txt"
    third_path_committed
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$merge"
    [[ "$output" == *"diff --combined b.txt"* ]]
    [[ "$output" == *"mode 100644,100644..100755"* ]]
    [[ "$output" != *"@@"* ]]
    [[ "$output" != *"Binary files"* ]]
    run_hook "$BASE"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "an evil MERGE adding an EMPTY file neither parent holds, gone at the tip, passes through a real push: the combined patch prints the header alone for it (no hunk, no Binary line), a candidate judged by its bytes, and an empty blob hides nothing; no short read is claimed, and the remote holds main" {
    merge_fixture
    : > "$REPO/empty.txt"
    git -C "$REPO" add empty.txt
    git -C "$REPO" commit -qm "the merge adds an empty file"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file empty.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- empty.txt' _ "$merge"   # the header alone
    [[ "$output" == *"diff --combined empty.txt"* ]]
    [[ "$output" == *"new file mode 100644"* ]]
    [[ "$output" != *"@@"* ]]
    [[ "$output" != *"Binary files"* ]]
    push_main_through_installed_hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "a text file a MERGE adds under -diff at a path the patch header QUOTES (a tab in the name), the string in it and the file gone at the tip, is refused as hidden through a real push, the line naming the path byte for byte: the header's C escapes are undone before the join, and a path left quoted would meet no row; the remote stays at the base" {
    qpath=$'tab\tx.txt'
    attributes '"tab\tx.txt" -diff'                             # gitattributes reads the same C quoting
    merge_fixture
    printf 'seen on TESTHOST\n' > "$REPO/$qpath"
    git -C "$REPO" add -- "$qpath"
    git -C "$REPO" commit -qm "the merge adds a -diff file at a quoted path"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file "$qpath" "remove it"
    run _hook_in "$REPO" -c 'git check-attr diff -- "$1"' _ "$qpath"
    [[ "$output" == *"diff: unset"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$merge"
    [[ "$output" == *'diff --combined "tab\tx.txt"'* ]]         # the header quotes the path, the tab as a C escape
    [[ "$output" == *"Binary files differ"* ]]
    push_main_through_installed_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: $qpath in commit ${merge:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *'"tab\tx.txt"'* ]]                          # the quoted form names nothing
    [[ "$output" != *"printed no verdict"* ]]                  # a path left quoted meets no row and is refused as unscanned instead
    [[ "$output" != *"personal identifier"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the same at a path with a DOUBLE QUOTE in the name: refused as hidden, the line naming the path byte for byte and no short read claimed" {
    qpath='a"b.txt'
    attributes '"a\"b.txt" -diff'
    merge_fixture
    printf 'seen on TESTHOST\n' > "$REPO/$qpath"
    git -C "$REPO" add -- "$qpath"
    git -C "$REPO" commit -qm "the merge adds a -diff file at a quoted path"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file "$qpath" "remove it"
    run _hook_in "$REPO" -c 'git check-attr diff -- "$1"' _ "$qpath"
    [[ "$output" == *"diff: unset"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$merge"
    [[ "$output" == *'diff --combined "a\"b.txt"'* ]]
    [[ "$output" == *"Binary files differ"* ]]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: $qpath in commit ${merge:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *'"a\"b.txt"'* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"personal identifier"* ]]
}

@test "the same at a path with a byte over 127 in the name (two UTF-8 bytes, each an octal escape in the header under core.quotePath's default): refused as hidden, the line naming the path byte for byte and no short read claimed" {
    qpath=$'caf\xc3\xa9.txt'
    attributes '"caf\303\251.txt" -diff'                     # gitattributes reads the same C quoting: each byte over 127 as a three-digit octal escape
    merge_fixture
    printf 'seen on TESTHOST\n' > "$REPO/$qpath"
    git -C "$REPO" add -- "$qpath"
    git -C "$REPO" commit -qm "the merge adds a -diff file at a quoted path"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file "$qpath" "remove it"
    [ -z "$(git -C "$REPO" config core.quotePath || true)" ]     # the key at its default: a byte over 127 is quoted
    run _hook_in "$REPO" -c 'git check-attr diff -- "$1"' _ "$qpath"
    [[ "$output" == *"diff: unset"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$merge"
    [[ "$output" == *'diff --combined "caf\303\251.txt"'* ]]    # the header quotes the path, the two bytes as octal escapes
    [[ "$output" == *"Binary files differ"* ]]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: $qpath in commit ${merge:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *'"caf\303\251.txt"'* ]]                    # the quoted form names nothing
    [[ "$output" != *"printed no verdict"* ]]                  # an escape left undone meets no row and is refused as unscanned instead
    [[ "$output" != *"personal identifier"* ]]
}

@test "the same at a path with a BACKSLASH in the name (the -diff line a glob: a quoted gitattributes pattern reads a backslash as the glob's escape): refused as hidden, the line naming the path byte for byte and no short read claimed" {
    qpath='a\b.txt'
    attributes 'a*.txt -diff'
    merge_fixture
    printf 'seen on TESTHOST\n' > "$REPO/$qpath"
    git -C "$REPO" add -- "$qpath"
    git -C "$REPO" commit -qm "the merge adds a -diff file at a quoted path"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file "$qpath" "remove it"
    run _hook_in "$REPO" -c 'git check-attr diff -- "$1"' _ "$qpath"
    [[ "$output" == *"diff: unset"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$merge"
    [[ "$output" == *'diff --combined "a\\b.txt"'* ]]            # the header doubles the backslash
    [[ "$output" == *"Binary files differ"* ]]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: $qpath in commit ${merge:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *'"a\\b.txt"'* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"personal identifier"* ]]
}

# A merge with THREE parents (an octopus): the combined listing carries one more
# leading colon, mode and sha per parent, and the hook reads the post-image's
# fields by the parent count (k), while the combined patch prints one column per
# parent and the added-lines pass keys its plus prefix on the same count. Every
# other merge case here has two parents, and a hook whose field arithmetic was
# right for two alone published this pair's hidden file through a real push (the
# round 4 refuter, 2026-09-22).
octopus_fixture() {   # a base the remote holds, two side branches and a main commit, the three-parent merge left open (--no-commit) for the case's own change; BASE is the remote's sha
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b web
    commit_file web.txt "the web session's line" "web side"
    git -C "$REPO" checkout -q -b api main
    commit_file api.txt "the api session's line" "api side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the tests session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit web api > /dev/null 2>&1
}
is_octopus() {   # <sha>: three parents (rev-list --parents prints the commit and then each parent: four words)
    [ "$(git -C "$REPO" rev-list --parents -n 1 "$1" | wc -w)" -eq 4 ]
}

@test "a THREE-PARENT merge (an octopus) whose own addition is a text file under -diff carrying the string, gone at the tip, is refused as hidden through a real push, the line naming the merge and the path: the listing's fields are read by the parent count, not a two-parent shape; the remote stays at the base" {
    attributes 'notes.txt -diff'
    octopus_fixture
    commit_file notes.txt "seen on TESTHOST" "the octopus adds a -diff file"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_octopus "$merge"
    remove_file notes.txt "remove it"                            # gone at the tip: only the per-commit half can name it
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames --root -c -z --no-commit-id "$1" | tr "\0" "|"' _ "$merge"
    [[ "$output" == *":::000000 000000 000000 100644 "*" AAA|notes.txt|"* ]]      # three parents: three leading colons, and three pre-image modes and shas ahead of the post-image's
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- notes.txt' _ "$merge"
    [[ "$output" == *"Binary files differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    push_main_through_installed_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt in commit ${merge:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" != *"at the tip of"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the same octopus adding the file under NO attribute is a HIT by the added-lines pass, which reads a line in none of the three parents (three plus columns) as the merge's own, and is never called hidden" {
    octopus_fixture
    commit_file notes.txt "seen on TESTHOST" "the octopus adds a plain file"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_octopus "$merge"
    remove_file notes.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- notes.txt' _ "$merge"
    [[ "$output" == *"+++seen on TESTHOST"* ]]                   # one plus per parent
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${merge:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  notes.txt"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"printed no verdict"* ]]
}

# check-attr's three reserved words (set, unspecified, unset) are also names a
# driver may take: `diff=set` on a path with diff.set.binary true makes
# check-attr answer `set`, the word a bare `diff` attribute answers, and a
# verdict read from the value passed the path over (a real push published a
# banned string under drivers named set and unspecified, 2026-09-21). The hook
# decides by git's verdict and quotes the answer, so the driver is named.

@test "a text file under a driver NAMED set (diff.set.binary true) is refused, the line naming the driver: check-attr's reserved word decides nothing; the remote holds nothing" {
    git -C "$REPO" config diff.set.binary true
    attributes 'notes.txt diff=set'
    commit_file notes.txt "seen on TESTHOST" "a banned string under a driver named set"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git check-attr diff notes.txt'
    [[ "$output" == *"diff: set"* ]]
    run _hook_in "$REPO" -c 'git grep -i -I -l -F -e TESTHOST "$1" --' _ "$sha"
    [ "$status" -eq 1 ]
    push_main_through_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (diff=set, binary) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"notes.txt in commit ${sha:0:10} is text that"* ]]      # the tip holds the blob: one verdict, the tip's
    [[ "$output" != *"personal identifier"* ]]
    ! remote_holds_main
}

@test "a text file under a driver NAMED unspecified (diff.unspecified.binary true) is refused the same way; the remote holds nothing" {
    git -C "$REPO" config diff.unspecified.binary true
    attributes 'notes.txt diff=unspecified'
    commit_file notes.txt "seen on TESTHOST" "a banned string under a driver named unspecified"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git check-attr diff notes.txt'
    [[ "$output" == *"diff: unspecified"* ]]
    push_main_through_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (diff=unspecified, binary) hides from the identifier scan"* ]]
    [[ "$output" != *"notes.txt in commit ${sha:0:10} is text that"* ]]      # the tip holds the blob: one verdict, the tip's
    [[ "$output" != *"personal identifier"* ]]
    ! remote_holds_main
}

@test "a driver merely NAMED unspecified, with no attribute naming it on any path, hides nothing: a clean push passes with nothing printed (the control: unspecified is also check-attr's answer for a path with no attribute)" {
    git -C "$REPO" config diff.unspecified.binary true
    commit_file notes.txt "nothing to see" "a clean file with no attribute"
    run _hook_in "$REPO" -c 'git check-attr diff notes.txt'
    [[ "$output" == *"diff: unspecified"* ]]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# The check's own reads fail closed like every other, each against its refusing
# input: the scratch directory (for the added lines' capture and the verdict
# check alike), the tip's listing and the grep's read list, each
# commit's listing and its numstat, a numstat that answers for fewer paths than
# the listing names (the line naming the first path met no verdict; named by
# the commit alone, the pusher had to find the path themselves, the round 4
# refuter 2026-09-22), a type change's two reads (the empty tree's name, the
# numstat against it), a merge's combined patch (a read that fails; one that
# prints no verdict for a path the merge changes; the addition numstat for its
# renames answering short), a path with a newline, the listings' rewrite for
# the joins (a tr that fails on one file and runs on the next; the newline
# test's pipeline), the hidden blob's content
# read; and the label's check-attr, which cannot lift a refusal git's verdict
# made. The
# replace-ref listing (refuse_replace_refs) is here too. The round 3 refuters
# deleted each such arm alone and together and the suite stayed green, which is
# why each has a case: a refusal that never fires cannot be told from an arm
# that is not there.
# The second class (the hook header): a read that exits 0 with an empty or a
# short answer, refused where a second read in hand shows it short, each with
# its cases below: the tip's -z listing against the symlink pass's entry count
# and the grep's read list; the changed-path listing against the paths its
# verdicts name (a one-parent commit's and a merge's, the reference read
# chosen by the parent count the caller read); each scratch listing's rewrite
# against its input's byte count, and every count against the digits; and the
# byte judge's zero against the blob's size. Each was red at the round 4 head
# by execution before its gate landed, the string published through a real
# push or the wrong cause named (the round 4 refuters, 2026-09-22).

fail_for_each_ref()      { git_refusing '[ "${1:-}" = for-each-ref ]' 128 "fatal: shim: for-each-ref refused"; }
fail_ls_tree_z()         { git_refusing '[ "${1:-}" = ls-tree ] && [ "${3:-}" = -z ]' 128 "fatal: shim: ls-tree -z refused"; }   # the verdict check's listing alone: a plain ls-tree shim clears tip_listed in the symlink pass first
fail_grep_read_list()    { git_refusing '[ "${1:-}" = grep ] && [ "${5:-}" = -z ]' 2 "shim: git grep -l -z refused"; }         # the read list alone: the content grep carries no -z
fail_diff_tree_raw()     { git_refusing 'case " $* " in *" --raw "*) true ;; *) false ;; esac' 128 "fatal: shim: diff-tree --raw refused"; }             # the changed-path listing alone: the added-lines diff carries no --raw, and the count's --stdin --raw read runs only with the credential scan armed, which setup disarms
fail_diff_tree_numstat() { git_refusing 'case " $* " in *" --numstat "*) true ;; *) false ;; esac' 128 "fatal: shim: diff-tree --numstat refused"; }   # the verdict read alone: the generic diff-tree shim is consumed by the added-lines arm
empty_diff_tree_numstat() { git_refusing 'case " $* " in *" --numstat "*) true ;; *) false ;; esac' 0 ""; }                      # a numstat that exits 0 and answers nothing: a short read, not a failed one
fail_hash_object()        { git_refusing '[ "${1:-}" = hash-object ]' 128 "fatal: shim: hash-object refused"; }                   # the empty tree's name, read for a type change alone: no other read of the hook asks it
fail_empty_tree_numstat() { git_refusing 'case " $* " in *" --numstat "*" -- :(literal)"*) true ;; *) false ;; esac' 128 "fatal: shim: diff-tree --numstat against the empty tree refused"; }   # the type change's numstat alone: the literal pathspecs are its own
empty_empty_tree_numstat() { git_refusing 'case " $* " in *" --numstat "*" -- :(literal)"*) true ;; *) false ;; esac' 0 ""; }   # the same read answering nothing: a short read
fail_combined_patch()     { git_refusing 'case " $* " in *" -p "*" -c "*) true ;; *) false ;; esac' 128 "fatal: shim: diff-tree -p -c refused"; }   # the combined patch, the read the scan makes: the added-lines pass reads it too, and both arms name their read
empty_combined_patch()    { git_refusing 'case " $* " in *" -p "*" -c "*) true ;; *) false ;; esac' 0 ""; }                                        # the same read printing nothing: no verdict for the paths the merge changes
fail_per_parent_listing() { git_refusing 'case " $* " in *" --raw "*" -m "*) true ;; *) false ;; esac' 128 "fatal: shim: diff-tree --raw -m refused"; }   # the merge's listing against each parent alone: the combined listing carries -c and no -m
empty_per_parent_listing() { git_refusing 'case " $* " in *" --raw "*" -m "*) true ;; *) false ;; esac' 0 ""; }                                    # the same read answering nothing: no candidate for a path the patch prints nothing for
check_attr_answering() {   # <printf format of the answer, NUL-delimited>: a git whose check-attr prints that and exits 0, the real git for every other command
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = check-attr ]; then printf %q; exit 0; fi\n' "$1"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "a replace-ref listing that fails (git for-each-ref exiting 128) refuses the push as unscanned, naming the read" {
    commit_file file.txt "nothing to see" "clean"
    fail_for_each_ref
    run _hook_in "$REPO" -c 'git for-each-ref --format="%(refname)" refs/replace/'
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the REPLACE REFS of this clone could not be listed (git for-each-ref exited 128), so whether the scans read what the push transfers is unknown"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a scratch directory that cannot be made (TMPDIR at a missing path) refuses the push as unscanned, naming mktemp for both reads that write there: the added lines' capture and the verdict check" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    export TMPDIR="$TEST_DIR/no-such-dir"
    run _hook_in "$REPO" -c 'mktemp -d "$TMPDIR/romp-pre-push.XXXXXX"'
    [ "$status" -ne 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the ADDED LINES of commit ${sha:0:10} could not be read (no scratch directory for the capture: mktemp failed)"* ]]
    [[ "$output" == *"the BINARY VERDICTS on the paths refs/heads/main (${sha:0:10}) publishes could not be checked (no scratch directory: mktemp failed)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a tip whose tree cannot be listed for the verdict check (ls-tree -z exiting 128, the symlink pass's plain ls-tree untouched) refuses the push as unscanned, naming the read" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_ls_tree_z
    run _hook_in "$REPO" -c 'git ls-tree -r -z -l "$1"' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git ls-tree -r "$1"' _ "$sha"      # the symlink pass's listing works, so tip_listed stays 1 and the -z read is reached
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the TREE of the tip of refs/heads/main (${sha:0:10}) could not be listed for the BINARY VERDICT check (git ls-tree exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"SYMLINKS of the tip"* ]]
}

@test "a grep that cannot list the files it read (git grep -l -z exiting 2, the content grep untouched) refuses the push as unscanned, naming the read" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_grep_read_list
    run _hook_in "$REPO" -c 'git grep --no-color -I -l -z -e "" "$1" --' _ "$sha"
    [ "$status" -eq 2 ]
    run _hook_in "$REPO" -c 'git grep --no-color -i -I -l -F -e x "$1" --' _ "$sha"   # the content grep: no match, exit 1, not the shim
    [ "$status" -eq 1 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the FILES the grep of the tip of refs/heads/main (${sha:0:10}) reads could not be listed for the BINARY VERDICT check (git grep exited 2)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"could not be fully scanned"* ]]
}

# The tip's -z listing answering with a clean status and too few (or too many)
# entries: the tip's complement and blob set are built from it alone, so an
# emptied or shortened listing left a hidden text file the remote already
# holds judged by nothing, and a real push published it (the round 4
# refuters, 2026-09-22). The gate is the entry count of the symlink pass's
# plain listing of the same tree, read anyway, and the grep's read list, whose
# every file must be one listed. The fixture is the hidden file ON the remote
# and a clean commit pushed after it, so only the tip half can judge the file.
empty_ls_tree_z() { git_refusing '[ "${1:-}" = ls-tree ] && [ "${3:-}" = -z ]' 0 ""; }   # the verdict check's listing answering nothing with a clean status; the symlink pass's plain ls-tree untouched
ls_tree_z_dropping() {   # <path>: a git whose ls-tree -r -z -l answers without that path's record and exits 0, the real git for every other command
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = ls-tree ] && [ "${3:-}" = -z ]; then %q "$@" | tr "\\0" "\\n" | grep -vF -e %q | tr "\\n" "\\0"; exit 0; fi\n' "$real_git" "$(printf '\t%s' "$1")"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
hidden_file_on_remote_then_clean_commit() {   # the shape: .gitattributes and a -diff file carrying the string on the remote (BASE), then one clean commit; sha is the tip
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    add_remote
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file other.txt "nothing to see" "a clean commit"
    sha="$(git -C "$REPO" rev-parse HEAD)"
}

@test "a tip listing for the verdict check that answers NOTHING (ls-tree -r -z -l exiting 0 with no entry, the symlink pass's plain ls-tree untouched) is a short read, refused as unscanned with both counts through a real push: an empty listing is not an empty tree, and the hidden text file the remote already holds is not passed by it; the remote stays at the base" {
    hidden_file_on_remote_then_clean_commit
    empty_ls_tree_z
    run _hook_in "$REPO" -c 'git ls-tree -r -z -l "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git ls-tree -r "$1" | grep -c .' _ "$sha"       # the symlink pass's listing: .gitattributes, notes.txt, other.txt
    [ "$output" = 3 ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the TREE of the tip of refs/heads/main (${sha:0:10}) was listed short or long for the BINARY VERDICT check (git ls-tree -r -z -l exited 0 and listed 0 entries where the symlink pass's git ls-tree -r of the same tree listed 3)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"exited 128"* ]]
    [[ "$output" != *"is text that"* ]]                      # judged by nothing: refused for the read, not for the blob
    [[ "$output" != *"personal identifier"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "a tip listing that DROPS one record, the hidden file's, is refused the same way with the counts 2 and 3: the grep's read list agrees with what was listed (the hidden file is one the grep skipped), so the count is the gate that closes a dropped record; the remote stays at the base" {
    hidden_file_on_remote_then_clean_commit
    ls_tree_z_dropping notes.txt
    run _hook_in "$REPO" -c 'git ls-tree -r -z -l "$1" | tr "\0" "\n"' _ "$sha"
    [ "$status" -eq 0 ]
    [[ "$output" != *"notes.txt"* ]]
    [[ "$output" == *"other.txt"* ]]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the TREE of the tip of refs/heads/main (${sha:0:10}) was listed short or long for the BINARY VERDICT check (git ls-tree -r -z -l exited 0 and listed 2 entries where the symlink pass's git ls-tree -r of the same tree listed 3)"* ]]
    [[ "$output" != *"its listing lacks"* ]]                 # the read-list arm is silent: every file the grep read is listed
    [[ "$output" != *"is text that"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "a tip listing that DROPS a record the grep READ (other.txt) is refused on both arms, the count and the read list, the second naming the file: a file the grep read is one the tree holds; the remote stays at the base" {
    hidden_file_on_remote_then_clean_commit
    ls_tree_z_dropping other.txt
    run _hook_in "$REPO" -c 'git ls-tree -r -z -l "$1" | tr "\0" "\n"' _ "$sha"
    [[ "$output" != *"other.txt"* ]]
    run _hook_in "$REPO" -c 'git grep --no-color -I -l -z -e "" "$1" -- | tr "\0" "\n"' _ "$sha"          # the grep's read list names it
    [[ "$output" == *":other.txt"* ]]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"was listed short or long for the BINARY VERDICT check (git ls-tree -r -z -l exited 0 and listed 2 entries where the symlink pass's git ls-tree -r of the same tree listed 3)"* ]]
    [[ "$output" == *"the TREE of the tip of refs/heads/main (${sha:0:10}) was listed short for the BINARY VERDICT check (git ls-tree -r -z -l exited 0 and its listing lacks other.txt, a file the grep of the tip lists as read)"* ]]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides"* ]]   # whatever was listed is still judged: the hidden file's record stayed
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "a commit whose changed paths cannot be listed for the verdict check (diff-tree --raw exiting 128, the added-lines diff untouched) refuses the push as unscanned, naming the read" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_diff_tree_raw
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames --root -c -z --no-commit-id "$1"' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CHANGED PATHS of commit ${sha:0:10} could not be listed for the BINARY VERDICT check (git diff-tree exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"ADDED LINES"* ]]
    [[ "$output" != *"BINARY VERDICTS of commit"* ]]      # the numstat reads run (the listing is checked against them since round 5) and answer whole; the listing was refused on its status
    [[ "$output" != *"were listed short"* ]]              # and the population gate stands down for a listing that failed on its status: one cause, not two
}

@test "a commit whose binary verdicts cannot be read (diff-tree --numstat exiting 128, the added-lines diff untouched) refuses the push as unscanned, naming that read and not the short-answer one" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_diff_tree_numstat
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root -z --no-commit-id "$1"' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat -M exited 128)"* ]]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat --no-renames exited 128)"* ]]   # both verdict reads, each named
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"answered for fewer paths"* ]]       # the reads' own failures and not a third cause: the short-answer arm is gated on both having exited 0
    [[ "$output" != *"ADDED LINES"* ]]
}

@test "a numstat that exits 0 and answers for FEWER paths than the commit changes is a short read, refused as unscanned naming the path met no verdict: a missing answer is not an answer of text" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file file.txt "remove it"                             # gone at the tip: the blob is the commit's to judge, so the commit's reads are the ones that must answer (a blob the tip holds is the tip's, whatever a per-commit read says)
    empty_diff_tree_numstat
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root -z --no-commit-id "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes and printed no verdict for file.txt)"* ]]
    [[ "$output" != *"exited"* ]]
}

type_change_to_symlink() {   # a small text file replaced by a clean symlink: one T row, the pair's stat text, the addition verdict the read that decides
    commit_file thing "clean" "a small file"
    rm "$REPO/thing"
    symlink_commit thing "nothing to see" "replaced by a symlink"
    sha="$(git -C "$REPO" rev-parse HEAD)"
}

@test "a type change whose addition verdict cannot be read (git hash-object, asked for the empty tree's name, exiting 128) refuses the push as unscanned, naming that read; the pair verdicts stand and no other cause is named" {
    type_change_to_symlink
    fail_hash_object
    run _hook_in "$REPO" -c 'git hash-object -t tree --stdin < /dev/null'
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root -z --no-commit-id "$1" >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git hash-object, asked for the empty tree's name, exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"against the empty tree exited"* ]]
    [[ "$output" != *"answered for fewer paths"* ]]       # the short-answer arm is gated on every read having exited 0: one cause
    [[ "$output" != *"--numstat -M exited"* ]]
}

@test "a type change whose addition verdict cannot be read (diff-tree --numstat against the empty tree exiting 128, the pair numstats untouched) refuses the push as unscanned, naming that read" {
    type_change_to_symlink
    fail_empty_tree_numstat
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -z --no-commit-id --no-renames "$(git hash-object -t tree --stdin < /dev/null)" "$1" -- ":(literal)thing"' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root -z --no-commit-id "$1" >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat against the empty tree exited 128)"* ]]
    [[ "$output" != *"hash-object"* ]]
    [[ "$output" != *"--numstat -M exited"* ]]
    [[ "$output" != *"answered for fewer paths"* ]]
}

@test "a type change whose addition verdict answers nothing (the numstat against the empty tree exiting 0 with no row) is a short read, refused as unscanned naming the path: no answer is not an answer of text" {
    type_change_to_symlink
    remove_file thing "remove it"                                # gone at the tip: the new object is the commit's to judge (case 120's note)
    empty_empty_tree_numstat
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -z --no-commit-id --no-renames "$(git hash-object -t tree --stdin < /dev/null)" "$1" -- ":(literal)thing"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes and printed no verdict for thing)"* ]]
    [[ "$output" != *"exited"* ]]
}

merge_with_hidden_link() {   # a merge whose own change is a symlink at a -diff path, gone at the tip: the combined patch's verdict is the read that decides
    attributes 'link -diff'
    merge_fixture
    ln -s "nothing to see" "$REPO/link"
    git -C "$REPO" add link
    git -C "$REPO" commit -qm "the merge adds a link under -diff"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file link "remove it"
}

@test "a merge whose combined patch cannot be read (diff-tree -p -c exiting 128) refuses the push as unscanned, naming that read beside the added-lines arm, which reads the same patch; no short read is claimed" {
    merge_with_hidden_link
    fail_combined_patch
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$sha"
    [ "$status" -eq 128 ]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, exited 128)"* ]]
    [[ "$output" == *"the ADDED LINES of commit ${sha:0:10} could not be read (git diff-tree exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"printed no verdict"* ]]              # the read's own failure and not a second cause: the short arm is gated on every read having exited 0
    [[ "$output" != *"is text that"* ]]
}

@test "a merge whose combined patch prints NOTHING (diff-tree -p -c exiting 0 with no output) is a short read, refused as unscanned naming the path: no section is not a verdict of text, and the hidden link is not called hidden either; the ADDED LINES diff of the same merge, silent under the same shim, is refused at its marker (round 8)" {
    merge_with_hidden_link
    empty_combined_patch
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --always --no-color "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]                                             # the shim silences both -p -c reads: the combined patch and the added-lines diff (not even the marker line)
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for link, a path the merge changes)"* ]]
    [[ "$output" != *"the merge's combined patch, exited"* ]]    # the patch read's own failed-status arm is not claimed: the read exited 0 (until round 8 no "exited" at all, before the added-lines diff's git stage had a marker to miss)
    [[ "$output" == *"the ADDED LINES of commit ${sha:0:10} could not be read (git diff-tree exited 0 and printed no line naming the commit, the marker --always asks for ahead of the diff, so the read answered short)"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"against the empty tree"* ]]
}

@test "a merge's pure rename whose addition verdict answers nothing (the numstat against the empty tree exiting 0 with no row) is a short read, refused as unscanned, naming that read and the path, not the patch" {
    merge_fixture
    git -C "$REPO" mv base.txt moved.txt
    git -C "$REPO" commit -qm "merge side, base.txt moved"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$sha"
    remove_file moved.txt "remove it"
    empty_empty_tree_numstat
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -z --no-commit-id --no-renames "$(git hash-object -t tree --stdin < /dev/null)" "$1" -- ":(literal)moved.txt"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat against the empty tree answered for fewer paths than the merge renames and printed no verdict for moved.txt)"* ]]
    [[ "$output" != *"exited"* ]]
    [[ "$output" != *"the merge's combined patch"* ]]
}

@test "a merge whose changes against each parent cannot be listed (diff-tree --raw -m exiting 128, the combined listing and the patch untouched) refuses the push as unscanned, naming that read; the third-path content, a candidate that listing alone names, is claimed neither hidden nor a short read" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    fail_per_parent_listing
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames -m -z --no-commit-id "$1"' _ "$merge"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames --root -c -z --no-commit-id "$1" > /dev/null' _ "$merge"
    [ "$status" -eq 0 ]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${merge:0:10} could not be read (git diff-tree --raw -m, the merge's changes against each parent, exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"printed no verdict"* ]]              # the read's own failure and not a second cause: the short arm is gated on every read having exited 0
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"CHANGED PATHS"* ]]
}

@test "a merge whose listing against each parent answers NOTHING (diff-tree --raw -m exiting 0 with no output) leaves the third-path content a short read, refused as unscanned by the patch's arm naming that path: a listing that came up short names no candidate, and the path passes on nothing" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    empty_per_parent_listing
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames -m -z --no-commit-id "$1"' _ "$merge"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${merge:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for b.txt, a path the merge changes)"* ]]
    [[ "$output" != *"exited"* ]]
    [[ "$output" != *"is text that"* ]]
}

# The changed-path listing (diff-tree --raw -c) answering with a clean status
# and no entry: the per-commit population is built from it alone, so an
# emptied listing named no post-image and the commit was passed over unjudged,
# a banned string in a -diff file published through a real push (the round 4
# refuters, 2026-09-22), for a one-parent commit and for a merge alike. The
# gate is the verdicts, read for every commit since: a path a numstat row or
# a combined-patch section names that the listing did not name is a listing
# that answered short. The reference read is chosen by the parent count the
# caller read, never by the listing's shape: a merge whose listing was emptied
# would otherwise read as a one-parent commit, whose pair numstat prints
# nothing for a merge, and the two empty answers would agree.
empty_diff_tree_raw_c() { git_refusing 'case " $* " in *" --raw "*" -c "*) true ;; *) false ;; esac' 0 ""; }   # the combined changed-path listing alone (--raw and -c both present, in that order): the per-parent listing carries -m and no -c, the numstats no --raw, the added-lines patch no --raw

@test "a commit whose changed-path listing answers NOTHING (diff-tree --raw -c exiting 0 with no entry) is a short read, refused as unscanned naming the listing and the first path its verdicts name, through a real push: a listing that came up short is not a commit that changed nothing, and the remote stays at the base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'notes.txt -diff\n' > "$REPO/.git/info/attributes"       # the attribute outside the tree, so the commit changes one path
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file notes.txt "remove it"                                # gone at the tip: only the per-commit half can name it
    empty_diff_tree_raw_c
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames --root -c -z --no-commit-id "$1"' _ "$leak"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -z --no-commit-id -M --root "$1" | tr "\0" "|"' _ "$leak"    # the verdicts still name the path
    [[ "$output" == *"notes.txt|"* ]]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the CHANGED PATHS of commit ${leak:0:10} were listed short for the BINARY VERDICT check (git diff-tree --raw exited 0 and its listing lacks notes.txt, a path git diff-tree --numstat answered for)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"exited 128"* ]]
    [[ "$output" != *"is text that"* ]]                      # judged by nothing: refused for the read, not for the blob
    [[ "$output" != *"answered for fewer paths"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "a MERGE whose combined listing answers NOTHING (diff-tree --raw -c exiting 0 with no entry) is refused the same way, the reference read chosen by the parent count and not by the listing's shape: the combined patch names the path the listing lacks, and the remote stays at the base" {
    merge_with_hidden_link
    empty_diff_tree_raw_c
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames --root -c -z --no-commit-id "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames -m -z --no-commit-id "$1" | tr "\0" "|"' _ "$sha"   # the per-parent listing is untouched (no -c), and is never compared
    [[ "$output" == *"link|"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -z --no-commit-id -M --root "$1"' _ "$sha"                   # the pair numstat prints nothing for a merge: read as a one-parent commit, the two empty answers would agree
    [ -z "$output" ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the CHANGED PATHS of commit ${sha:0:10} were listed short for the BINARY VERDICT check (git diff-tree --raw -c exited 0 and its listing lacks link, a path the merge's combined patch printed a section for)"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"exited 128"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "a path holding a newline byte is refused as unscanned at the tip and in the commit: the listings are joined line by line, and such a path would be judged by nothing; a later commit that only DELETES the path the remote holds is refused too, since every changed path is rewritten and checked against the commit's verdicts (the widening the hook header discloses)" {
    commit_file file.txt "nothing to see" "clean"
    printf 'x\n' > "$REPO/"$'odd\nname.txt'
    git -C "$REPO" add -- $'odd\nname.txt'
    git -C "$REPO" commit -qm "a path with a newline"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"a path at the tip of refs/heads/main (${sha:0:10}) holds a newline, which the BINARY VERDICT check cannot judge"* ]]
    [[ "$output" == *"a path commit ${sha:0:10} changes holds a newline, which the BINARY VERDICT check cannot judge"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    # the widening (round 5, disclosed in the hook header): the remote holds the path, and the one commit in range only deletes it;
    # its listing names the path, so the listing is rewritten for the check against its verdicts and refused, where the round 4
    # text passed a commit with no post-image before any rewrite
    add_remote
    git -C "$REPO" push -q origin main                            # the adding commit on the remote: out of range below
    git -C "$REPO" rm -q -- $'odd\nname.txt'
    git -C "$REPO" commit -qm "delete the path with a newline"
    gone="$(git -C "$REPO" rev-parse HEAD)"
    run_hook "$sha"
    [ "$status" -eq 1 ]
    [[ "$output" != *"a path at the tip of"* ]]                   # the tip no longer holds it
    [[ "$output" != *"commit ${sha:0:10}"* ]]                    # out of range: the remote holds it
    [[ "$output" == *"a path commit ${gone:0:10} changes holds a newline, which the BINARY VERDICT check cannot judge"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
}

# The listings are joined in POSIX awk over newline-for-NUL rewrites (as_lines:
# a tr per file; the newline test was a tr piped to wc until round 9a, which
# reads its records in the shell alone, H.3). Before round 3g
# the rewrite carried no status arm and the function returned its LAST file's
# status, so a tr that failed on an earlier file and ran on the last handed the
# join an empty rewrite with no status to read: an empty tip listing emptied
# the tip's skip set and blob set (the tip half judged nothing, and a hidden
# text file the remote already held passed), an empty post listing emptied a
# commit's population (the commit passed unjudged by that half, a banned string
# under -diff published), and a merge's empty listing left its rename
# candidates underived (a short read claimed, the wrong cause); the newline
# test read a failed pipeline as a count of zero. Each test and each rewrite
# now reads its own status and the caller names the read. The fault is a tr
# first on the hook's PATH that refuses the Nth invocation of ONE argument
# shape (the rewrite; the newline test's old shape, tr -cd, which no read has
# run since round 9a; since round 6b the joins' own tr, newline to NUL, for the
# join's fourth arm at the end of this file) and execs the real tr for every
# other, counting in a file since each invocation is its own process; the
# cases here refuse the rewrite, one holds that the test's old shape never
# runs, and the joins' tr runs through. Once per test, like
# git_refusing. Since round 5 every commit's scratch files are rewritten, a
# deletion-only commit's too (its listing is checked against its verdicts), so
# the count of a rewrite is the tip's two, then eight per one-parent commit
# (post, gone, rows, rows2, links, tpaths, rows3, listed), read newest first.
# The second class has its own shims: a tr whose rewrite of the ONE input
# holding a marker exits 0 and writes nothing (tr_silent_on, keyed on the
# content and not on a count, so the same fault reaches the same file at any
# hook text), and a wc that reads its input and answers nothing.
tr_refusing() {   # <rewrite|test|join> <N>: the Nth tr of that shape exits 1, the real tr runs otherwise (join: the joins' newline-to-NUL tr, which reads its input before it refuses, as a tr that failed after reading would)
    local real_tr
    real_tr="$(command -v tr)"
    mkdir -p "$TEST_DIR/shim"
    echo 0 > "$TEST_DIR/tr-calls"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'real_tr=%q; counter=%q; want=%q; n=%d\n' "$real_tr" "$TEST_DIR/tr-calls" "$1" "$2"
        cat <<'SHIM'
shape=""
if [ $# -eq 2 ] && [ "$1" = '\0' ] && [ "$2" = '\n' ]; then shape=rewrite; fi
if [ $# -eq 2 ] && [ "$1" = -cd ] && [ "$2" = '\n' ]; then shape=test; fi
if [ $# -eq 2 ] && [ "$1" = '\n' ] && [ "$2" = '\0' ]; then shape=join; fi
if [ "$shape" = "$want" ]; then
    seen=$(( $(cat "$counter") + 1 )); echo "$seen" > "$counter"
    if [ "$seen" -eq "$n" ]; then [ "$shape" != join ] || cat > /dev/null; echo "shim: tr refused ($shape $n)" >&2; exit 1; fi
fi
exec "$real_tr" "$@"
SHIM
    } > "$TEST_DIR/shim/tr"
    chmod 755 "$TEST_DIR/shim/tr"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "a tip listing whose rewrite for the joins fails (the first rewrite tr exiting 1, the read list's rewrite untouched) refuses the push as unscanned, naming the tip and the tool: an empty rewrite is not an empty tip, and a hidden text file the remote already holds is not passed by it" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    add_remote
    git -C "$REPO" push -q origin main                        # the remote holds the hidden file: no new commit adds it, so the tip half alone can judge it
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file other.txt "nothing to see" "a clean commit"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    tr_refusing rewrite 1                                     # the tip's listing is the first file as_lines rewrites
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"shim: tr refused (rewrite 1)"* ]]
    [[ "$output" == *"the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (tr exited 1)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
    [[ "$output" != *"is text that"* ]]                      # the tip was not judged: refused for the read, not for the blob
    [ "$(cat "$TEST_DIR/tr-calls")" -ge 1 ]
}

@test "a commit's listing whose rewrite fails (the eleventh rewrite tr exiting 1: the tip's two listings and the removal commit's eight scratch files rewritten, the leak commit's post-images not) refuses the push as unscanned, naming the commit and the tool, where a hidden text file carrying a banned string in that commit and gone at the tip would otherwise pass unjudged" {
    # the range is the removal (read first: rev-list names a child before its parent) and the leak commit, each rewriting eight
    # scratch files after the tip's two, so the leak commit's post-images are the eleventh rewrite; the attribute and the file in
    # one commit, so that commit alone holds the hidden blob
    printf 'notes.txt -diff\n' > "$REPO/.gitattributes"
    printf 'seen on TESTHOST\n' > "$REPO/notes.txt"
    git -C "$REPO" add .gitattributes notes.txt
    git -C "$REPO" commit -qm "a banned string in a -diff file, with its attribute"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file notes.txt "remove it"                          # the tip is clean: only the per-commit half can name it
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- notes.txt' _ "$leak"
    [[ "$output" == *"Binary files"* ]]                        # the road: the diff prints no hunk, so the added-lines pass sees nothing
    tr_refusing rewrite 11
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"shim: tr refused (rewrite 11)"* ]]
    [[ "$output" == *"the LISTINGS of commit ${leak:0:10} could not be rewritten for the BINARY VERDICT check (tr exited 1)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"personal identifier"* ]]
}

@test "a MERGE's listing whose rewrite for its rename candidates fails (the eleventh rewrite tr exiting 1: the merge's post-images, read before its deletions, after the tip's two rewrites and the removal commit's eight) refuses the push as unscanned, naming the merge and the tool, and claims no short read: the candidates were not derived, not absent" {
    third_path_merge "nothing to see" pushed                  # the sources on the remote: the range is the removal at the tip (read first, eight rewrites) and the merge
    third_path_committed
    tr_refusing rewrite 11
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"shim: tr refused (rewrite 11)"* ]]
    [[ "$output" == *"the LISTINGS of commit ${merge:0:10} could not be rewritten for the BINARY VERDICT check (tr exited 1)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
    [[ "$output" != *"printed no verdict"* ]]                 # the short-read line, the wrong cause: the merge's candidates were never derived
    [[ "$output" != *"is text that"* ]]
}

@test "a tr that refuses the newline test's old shape (tr -cd, exiting 1) changes nothing since round 9a: the test reads each record in the shell (H.3), so no tr of that shape runs and a clean commit passes with nothing printed (until round 9a this case held a failed test tr refused as a failed test, not a count of zero; the round 9a newline case is the retired tool's twin)" {
    commit_file file.txt "nothing to see" "clean"
    tr_refusing test 1
    run _hook_in "$REPO" -c 'printf "a\\nb" | tr -cd "\\n"'
    [[ "$output" == *"shim: tr refused (test 1)"* ]]              # the shim refuses that shape when it runs
    echo 0 > "$TEST_DIR/tr-calls"
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ "$(cat "$TEST_DIR/tr-calls")" -eq 0 ]                       # the hook ran no tr of the test's shape
}

# The rewrite answering nothing with a clean status (the second class): as_lines
# read tr's status alone, so a rewrite that exited 0 and wrote nothing handed a
# join an empty file, and each caller passed on it: the tip judging nothing (a
# hidden text file the remote already holds passed), a one-parent commit's
# post-images empty (the commit passed unjudged, a banned string under -diff
# published), a merge's post-images empty (the candidates underived, the
# commit passed or the short read named, the wrong cause). The byte count of
# each rewrite is now compared with its input's, and every count read as a
# number first: a wc answering nothing read as a newline count of zero, the
# count of a clean file, and passed the newline test (the round 4 refuters,
# 2026-09-22), which reads no wc since round 9a (H.3).
tr_silent_on() {   # <marker>: a tr whose rewrite (the '\0' '\n' shape) of an input holding the marker exits 0 and writes nothing; the real tr for every other input and shape
    local real_tr
    real_tr="$(command -v tr)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'real_tr=%q; marker=%q; tmp=%q\n' "$real_tr" "$1" "$TEST_DIR/tr-input"
        cat <<'SHIM'
if [ $# -eq 2 ] && [ "$1" = '\0' ] && [ "$2" = '\n' ]; then
    cat > "$tmp"
    if grep -a -q -F -e "$marker" "$tmp"; then exit 0; fi
    exec "$real_tr" "$@" < "$tmp"
fi
exec "$real_tr" "$@"
SHIM
    } > "$TEST_DIR/shim/tr"
    chmod 755 "$TEST_DIR/shim/tr"
    export PATH="$TEST_DIR/shim:$PATH"
}
wc_silent() {   # a wc that reads its input and answers nothing, exit 0
    mkdir -p "$TEST_DIR/shim"
    printf '#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n' > "$TEST_DIR/shim/wc"
    chmod 755 "$TEST_DIR/shim/wc"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "a tip listing whose rewrite answers NOTHING (a tr exiting 0 and writing nothing for the tip's listing) is a short rewrite, refused as unscanned naming the tip, the rewrite and both byte counts: an empty rewrite is not an empty tip, and the hidden text file the remote already holds is not passed by it" {
    hidden_file_on_remote_then_clean_commit
    blob="$(git -C "$REPO" rev-parse "$sha:notes.txt")"
    expected="$(git -C "$REPO" ls-tree -r -z -l "$sha" | wc -c)"                # the listing's bytes: the input the rewrite must match
    tr_silent_on "$blob"                                                        # the hidden blob's sha is in the tip's listing and in no other scratch file of this push
    run _hook_in "$REPO" -c 'printf "a\\0b" | tr "\\0" "\\n" | wc -c'          # a clean input runs through the real tr
    [ "$output" = 3 ]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the rewrite of listing wrote 0 bytes for $expected read; tr exited 0)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
    [[ "$output" != *"exited 1"* ]]
    [[ "$output" != *"is text that"* ]]                      # the tip was not judged: refused for the read, not for the blob
}

@test "a commit's listing whose rewrite answers NOTHING (the leak commit's post-images) is refused the same way naming the commit, where a hidden text file carrying a banned string in that commit and gone at the tip would otherwise pass unjudged" {
    printf 'notes.txt -diff\n' > "$REPO/.gitattributes"
    printf 'seen on TESTHOST\n' > "$REPO/notes.txt"
    git -C "$REPO" add .gitattributes notes.txt
    git -C "$REPO" commit -qm "a banned string in a -diff file, with its attribute"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$leak:notes.txt")"
    remove_file notes.txt "remove it"                          # the tip is clean: only the per-commit half can name it
    attrs="$(git -C "$REPO" rev-parse "$leak:.gitattributes")"
    expected="$(printf '%s\t%s\0%s\t%s\0' "$attrs" .gitattributes "$blob" notes.txt | wc -c)"   # the post-images file holds the commit's two records
    tr_silent_on "$(printf '%s\t%s' "$blob" notes.txt)"        # the blob and the path: the leak commit's post-images, and no other scratch file (the removal's deletions hold the blob alone)
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the LISTINGS of commit ${leak:0:10} could not be rewritten for the BINARY VERDICT check (the rewrite of post wrote 0 bytes for $expected read; tr exited 0)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"personal identifier"* ]]
}

@test "a MERGE's listing whose rewrite for its rename candidates answers NOTHING (the merge's post-images) is refused the same way naming the merge, and claims no short read: the candidates were not derived, not absent" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    blob="$(git -C "$REPO" rev-parse "$merge:b.txt")"
    expected="$(printf '%s\t%s\0' "$blob" b.txt | wc -c)"
    tr_silent_on "$(printf '%s\t%s' "$blob" b.txt)"            # the merge's post-images alone: the sources are on the remote, the removal's deletions hold the blob without the path
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the LISTINGS of commit ${merge:0:10} could not be rewritten for the BINARY VERDICT check (the rewrite of post wrote 0 bytes for $expected read; tr exited 0)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
    [[ "$output" != *"printed no verdict"* ]]                 # the short-read line, the wrong cause: the merge's candidates were never derived
    [[ "$output" != *"is text that"* ]]
}

@test "a wc that answers NOTHING (exit 0, no count) is not a count of zero: the push is refused as unscanned, naming the tip, the byte count and the empty answer, where a clean commit would otherwise pass on a count that read nothing (the newline test's wc was the one named here until round 9a, whose test reads the records in the shell: H.3)" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    wc_silent
    run _hook_in "$REPO" -c 'printf "abc" | wc -c'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the byte count's wc answered \"\" for listing, not a count)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
    [[ "$output" != *"newline test"* ]]
    [[ "$output" != *"exited"* ]]
}

@test "a hidden blob whose content cannot be read refuses the push as unscanned, naming the path: an unread blob is not a binary one" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse HEAD:notes.txt)"
    git_refusing "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [ \"\${3:-}\" = $blob ]" 128 "fatal: shim: cat-file blob refused for $blob"
    run _hook_in "$REPO" -c 'git cat-file blob "$1"' _ "$blob"
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CONTENT of notes.txt at the tip of refs/heads/main (${sha:0:10}), which git calls binary and the identifier scan therefore skipped, could not be read (git cat-file exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is text that"* ]]                      # unread, so not called text either
}

# The byte judge's count of zero (the second class): a cat-file that exits 0
# and prints nothing, or an od that fails inside the counting group (whose
# status is the drain's), left awk a count of zero bytes for a blob with
# bytes, and the blob passed as empty content, a banned string in a -diff file
# published through a real push (the round 4 refuters, 2026-09-22). The gate
# is the blob's size (cat-file -s), read apart: zero bytes read is empty
# content only when the size is zero. The fixture puts the attribute in
# .git/info/attributes so the leak commit changes one path, and the leak is a
# middle commit gone at the tip.
silent_cat_file_blob() {   # <blob>: a git whose `cat-file blob <blob>` exits 0 and prints nothing, the real git for every other command (cat-file -s included)
    git_refusing "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [ \"\${3:-}\" = $1 ]" 0 ""
}
od_failing() {   # an od that reads its input and exits 1
    mkdir -p "$TEST_DIR/shim"
    printf '#!/usr/bin/env bash\ncat > /dev/null\necho "shim: od refused" >&2\nexit 1\n' > "$TEST_DIR/shim/od"
    chmod 755 "$TEST_DIR/shim/od"
    export PATH="$TEST_DIR/shim:$PATH"
}
hidden_file_in_middle_commit_after_base() {   # a base on the remote (BASE), then a -diff file (the attribute in .git/info/attributes) carrying the string, removed at the tip; leak, blob and size are its commit, blob and byte size
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'notes.txt -diff\n' > "$REPO/.git/info/attributes"
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$leak:notes.txt")"
    size="$(git -C "$REPO" cat-file -s "$blob")"
    remove_file notes.txt "remove it"
}

@test "a hidden blob whose content read answers NOTHING (cat-file blob exiting 0 with no output, the size read untouched) is refused as unscanned naming the path, the zero bytes read and the size, through a real push: an empty answer is empty content only when the blob is empty; the remote stays at the base" {
    hidden_file_in_middle_commit_after_base
    [ "$size" -gt 0 ]
    silent_cat_file_blob "$blob"
    run _hook_in "$REPO" -c 'git cat-file blob "$1"' _ "$blob"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git cat-file -s "$1"' _ "$blob"
    [ "$output" = "$size" ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the CONTENT of notes.txt in commit ${leak:0:10}, which git calls binary and the identifier scan therefore skipped, was read as 0 bytes while git cat-file -s gives its size as $size bytes, so the read answered short (git cat-file blob exited 0)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is text that"* ]]                      # judged by nothing: refused for the read, not for the blob
    [[ "$output" != *"could not be read (git cat-file exited"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "an od that FAILS inside the counting group (exit 1, no git shim) leaves the same count of zero and is refused the same way through a real push: the group's status is the drain's, so the size is the gate; the remote stays at the base" {
    hidden_file_in_middle_commit_after_base
    od_failing
    run _hook_in "$REPO" -c 'printf "ab" | od -An -v -tu1'
    [ "$status" -eq 1 ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the CONTENT of notes.txt in commit ${leak:0:10}, which git calls binary and the identifier scan therefore skipped, was read as 0 bytes while git cat-file -s gives its size as $size bytes, so the read answered short (git cat-file blob exited 0)"* ]]
    [[ "$output" != *"is text that"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the control: a genuinely EMPTY file under -diff in a middle commit, gone at the tip, still passes: the numstat calls the empty blob binary, the byte judge reads 0 bytes and the size read agrees" {
    printf 'empty.txt -diff\n' > "$REPO/.git/info/attributes"
    : > "$REPO/empty.txt"
    git -C "$REPO" add empty.txt
    git -C "$REPO" commit -qm "an empty file under -diff"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file empty.txt "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -M --root --no-commit-id "$1" -- empty.txt' _ "$sha"     # a candidate: a dash for each count
    [ "$output" = "-"$'\t'"-"$'\t'"empty.txt" ]
    run _hook_in "$REPO" -c 'git cat-file -s "$(git rev-parse "$1:empty.txt")"' _ "$sha"
    [ "$output" = 0 ]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# The label's read: check-attr answers for the report line alone, after git's
# verdict and the byte rule have refused the blob, so its failure changes the
# words and never the verdict. Three faults, three clauses: a read that fails,
# an answer about another path, and no answer at all (the short read the
# round 3 refuters found fail-open in the batch read this replaced).

@test "a check-attr that fails leaves the refusal standing, the failure in the attribute's place and the tail open (whether an attribute accounts for the verdict is unknown), both remedies printed: the label read cannot lift a verdict git made" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_refusing '[ "${1:-}" = check-attr ]' 128 "fatal: shim: check-attr refused"
    run _hook_in "$REPO" -c 'git check-attr -z diff -- notes.txt'
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr exited 128), so whether an attribute of its path accounts for the verdict is unknown (the blob is "*" bytes; core.bigFileThreshold is not set in this clone's configuration); the identifier scan did not read it, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"so no attribute of its path accounts for the verdict"* ]]   # the failed read establishes no such thing
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]          # both remedies: either may be the cause
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"(unset)"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a check-attr that answers about ANOTHER path leaves the refusal standing, the answer named as out of step with the path asked and the tail open, both remedies printed" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    check_attr_answering 'other.txt\0diff\0unset\0'
    run _hook_in "$REPO" -c 'git check-attr -z diff -- notes.txt | tr "\0" "|"'
    [ "$output" = "other.txt|diff|unset|" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr answered out of step with the path asked), so whether an attribute of its path accounts for the verdict is unknown (the blob is "* ]]
    [[ "$output" != *"so no attribute of its path accounts for the verdict"* ]]
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"(unset)"* ]]
}

@test "a check-attr that answers NOTHING (a truncated read) leaves the refusal standing, the short answer named and the tail open, both remedies printed: the push does not pass" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    check_attr_answering ''
    run _hook_in "$REPO" -c 'git check-attr -z diff -- notes.txt'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr answered nothing for the path asked), so whether an attribute of its path accounts for the verdict is unknown (the blob is "* ]]
    [[ "$output" != *"so no attribute of its path accounts for the verdict"* ]]
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" == *"the push is refused rather than scanned"* ]]
}


# ── the chosen-addresses read: its failure is refused, naming the read ───────
# The address rule (each new commit's author and committer address is checked
# unless the clone CHOSE it: user.email in any scope, or the environment's
# GIT_AUTHOR_EMAIL, GIT_COMMITTER_EMAIL or EMAIL) has its own file,
# pre-push-identity.bats; the two cases here are about the READ behind it.
# chosen_emails reads user.email once per push (git config --get-all
# user.email) through judged_read (own=: an unset key is git's own exit 1 with
# no value, and no address is chosen; the set is 0 and 1), called in the shell
# so the refusal's counter is kept. A failure of that read is refused as
# unscanned naming the read, and the two address lines then lead with it:
# until round 7b the failure was swallowed as no chosen address (the strict
# side, since a failed read can refuse an address the clone did configure but
# never excuse one), and a commit stamped under the very address the clone IS
# configured to use was refused as "an address this clone is not configured to
# use", a false cause with an inapplicable remedy, with no line naming the
# read that failed (the round 6 refuters, by a real push, 2026-09-22). The
# strict side is kept (every stamped address is still judged against the
# environment's addresses alone); what changed is that the failure is named
# and the cause printed is the one the reads established. Both cases push for
# REAL through the hook so the remote's state is asserted too, which takes a
# wrapper: git prepends its own exec path to the PATH a hook sees, so a shim
# first on the test's PATH reaches a hook run by hand (run_hook) but not one a
# real push runs (verified by execution, git 2.43.0: through
# push_main_through_hook the hook's git resolved to git's exec path). The
# tag's address line under the same failed read is the last case of the round
# 7b section at the end of this file.

# The hook installed for one real push of main, behind a wrapper that puts the
# test's shim directory first on the hook's own PATH (the shim a git_refusing
# call made before this), so the fault reaches the hook's reads the way it does
# under run_hook. The remote is the case's (add_remote), so a case can push
# more than once.
push_main_through_hook_with_shim() {
    mkdir -p "$TEST_DIR/hooks"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'export PATH=%q:"$PATH"\n' "$TEST_DIR/shim"
        printf 'exec %q "$@"\n' "$HOOK"
    } > "$TEST_DIR/hooks/pre-push"
    chmod 755 "$TEST_DIR/hooks/pre-push"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/hooks"
    run git -C "$REPO" push origin main
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
}
fail_config_user_email() { git_refusing '[ "${1:-}" = config ] && [ "${2:-}" = --get-all ] && [ "${3:-}" = user.email ]' 128 "fatal: shim: config --get-all user.email refused"; }   # the chosen-addresses read alone
commit_stamped_as() {   # <address> <path> <message>: one clean file, author and committer both the address (the environment identity outranks config, so this is exactly the commit's identity)
    printf '%s\n' "the web session's work on $2" > "$REPO/$2"
    git -C "$REPO" add "$2"
    GIT_AUTHOR_EMAIL="$1" GIT_COMMITTER_EMAIL="$1" git -C "$REPO" commit -qm "$3"
}

@test "a chosen-addresses read that FAILS (git config --get-all user.email exiting 128) is refused as unscanned naming the read, through a real push, and a commit stamped under a banned domain is refused beside it with the address line leading with the failed read, not with a cause the read could not establish: the remote holds nothing, and configuring the clone to use that address changes nothing while the read fails, the line saying why; the remedy paragraph leads with the failed read and its repair, and its say-so line and bullets, whose causes the failed read leaves unknown, are absent (round 8b)" {
    add_remote
    commit_stamped_as dev@zzsynthuser.example web.txt "stamped under a banned domain the clone did not choose"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_config_user_email
    # the read as chosen_emails makes it fails under the shim; a config read of another shape (log.showRoot, which the hook read at its top until round 9) is untouched
    run _hook_in "$REPO" -c 'git config --get-all user.email'
    [ "$status" -eq 128 ]
    [[ "$output" == *"shim: config --get-all user.email refused"* ]]
    run _hook_in "$REPO" -c 'git config --type=bool log.showRoot; echo "status $?"'
    [ "$output" = "status 1" ]                          # the key unset: git's own status, no shim line
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDRESSES this clone is configured to use could not be read (git config --get-all user.email exited 128), so whether a stamped address is one it chose is unknown; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} is authored as <dev@zzsynthuser.example>: whether this clone is configured to use that address could not be read (git config --get-all user.email exited 128, refused above), and its domain carries a personal identifier"* ]]
    [[ "$output" == *"commit ${sha:0:10} is committed as <dev@zzsynthuser.example>: whether this clone is configured to use that address could not be read"* ]]
    [[ "$output" != *"not configured to use, whose domain"* ]]   # the round 7 text's cause, which the failed read cannot establish (the remedy paragraph's general sentence stays)
    [[ "$output" == *"BLOCKED"* ]]
    # the remedy paragraph under BLOCKED (round 8b, flag 80): the failed read and its repair lead, the general rule
    # stays, and the say-so line and the two bullets, remedies for causes the failed read leaves unknown, are absent
    # (the round 8 text printed the say-so line beside the failed read, a remedy that changes nothing while it fails)
    [[ "$output" == *"  The addresses this clone is configured to use could not be read (git config --get-all user.email exited 128, refused above), so whether it chose each address named is unknown: run git config --get-all user.email yourself to see git's own error, repair that read and push again; configuring an address changes nothing until then."$'\n'"  An address this clone is not configured to use, with a banned string in its domain, is refused on every commit it stamps."$'\n'* ]]
    [[ "$output" != *"say so (git config --global user.email"* ]]
    [[ "$output" != *"if git filled it from the hostname"* ]]
    [[ "$output" != *"--reset-author"* ]]
    [[ "$output" != *"shim:"* ]]                        # the shim's own line went to the -q the helper puts on the read
    run remote_holds_main                             # the checked form (tests/test_bats_bare_negation.py): a bare ! mid-test checks nothing under bats
    [ "$status" -ne 0 ]
    # the clone now chooses the address: with the read intact that excuses it, whatever its domain says
    # (pre-push-identity.bats, the configured-address case); behind the failed read the choice is not
    # seen, the push stays refused, and the line says the read failed rather than calling the address
    # one the clone is not configured to use. Stricter, not looser, and the cause is the true one.
    git -C "$REPO" config user.email dev@zzsynthuser.example
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the ADDRESSES this clone is configured to use could not be read (git config --get-all user.email exited 128)"* ]]
    [[ "$output" == *"commit ${sha:0:10} is authored as <dev@zzsynthuser.example>: whether this clone is configured to use that address could not be read"* ]]
    [[ "$output" != *"not configured to use, whose domain"* ]]
    ! remote_holds_main
}

@test "the same failed read beside a commit stamped under a clean domain the clone did not choose is refused as unscanned naming the read alone, through a real push: no address line, since the domain is clean, and the remote holds nothing (the round 7 text passed it, the failure swallowed as no chosen address)" {
    add_remote
    commit_stamped_as dev@example.invalid web.txt "stamped under a clean domain the clone did not choose"
    fail_config_user_email
    run _hook_in "$REPO" -c 'git config --get-all user.email'
    [ "$status" -eq 128 ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDRESSES this clone is configured to use could not be read (git config --get-all user.email exited 128), so whether a stamped address is one it chose is unknown; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is authored as"* ]]
    [[ "$output" != *"is committed as"* ]]
    [[ "$output" != *"BLOCKED"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}


# Until round 9 the hook read the clone's value of log.showRoot once, at its
# top, for the credential scan's advice arm, and the case below held that
# read's failure beside the count arm. Both are retired; the case, re-aimed in
# place, holds that the credential scan makes no configuration read at all, and
# since round 10b shows it by a POSITIVE record (the round 9 rulings' H,
# tests-5): the shim appends every git argv it is given to calls.git, whatever
# it prints, so a read whose stderr the hook swallowed (the retired read was
# made with 2>/dev/null || true) is recorded all the same, where the absence of
# the shim's refused line, the case's evidence until then, was left by such a
# read too.
fail_config_showroot() {   # a git that appends every argv to calls.git and refuses the log.showRoot read (exit 128, a line on stderr); the real git for every other command
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'printf "%%s\\n" "git $*" >> %q\n' "$TEST_DIR/calls.git"
        printf 'if [ "${1:-}" = config ] && [ "${2:-}" = --type=bool ] && [ "${3:-}" = log.showRoot ]; then\n'
        printf '    echo %q >&2\n    exit 128\nfi\n' "fatal: shim: config --type=bool log.showRoot refused"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "a git failing the log.showRoot configuration read (exit 128) changes nothing for the credential scan, which makes no configuration read: the root commit's credential under log.showRoot=false is found and named, and a git recording every argv it runs shows the hook's calls, none reading the key, matched in any case (round 9d: this slot held that read's failure beside the count arm, both retired in round 9; round 10b: the record in place of the absence of the shim's line)" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"        # the credential scan alone
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    root="$(git -C "$REPO" rev-parse HEAD)"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    fail_config_showroot
    run _hook_in "$REPO" -c 'git config --type=bool log.showRoot'    # the read as the hook made it fails under the shim
    [ "$status" -eq 128 ]
    [[ "$output" == *"shim: config --type=bool log.showRoot refused"* ]]
    [ "$(grep -ci 'log\.showroot' "$TEST_DIR/calls.git")" -eq 1 ]   # the recorder records the read it refuses
    rm -f "$TEST_DIR/calls.git"                                     # cleared after the case's own proving call
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: commit ${root:0:10} ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"shim:"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [ -s "$TEST_DIR/calls.git" ]                                    # a positive record: the hook's git calls went through the recorder
    grep -q -F -- ' --text ' "$TEST_DIR/calls.git"                  # the feed's own read among them
    [ "$(grep -ci 'log\.showroot' "$TEST_DIR/calls.git" || true)" -eq 0 ]   # and no argv reads the key, in any case
}


# ── every read through one helper: the exit-0 empty answer closed by construction ─────
# Round 4 gated six exit-0 empty answers read by read and the header claimed the
# class; round 5 found six more reads of the same class, each shown by a real
# push with a shim publishing a banned line with nothing printed (a grep exiting
# 2 over the added lines, a rev-list listing no commit, a parent count of
# nothing beside an empty combined listing, a type of nothing, an empty symlink
# target over a blob with bytes). The hook now makes every read it judges
# through one helper (judged_read): a status outside the read's expected set is
# refused naming the read, and an exit-0 empty answer is judged against a
# sibling fact where one exists (gate=) or declared the object's own (own=) at
# the call site; the header's two lists of reads are derived from those tags,
# and the first case below pins that derivation. The rest are the six reads,
# each through a real push with the shim that published at the earlier text,
# and the remote asserted to hold nothing new.

# The hook installed for one real push of the given branch, behind the wrapper
# that puts the shim directory first on the hook's PATH (push_main_through_hook_with_shim
# pushes main; this one any branch or tag ref).
push_ref_through_hook_with_shim() {   # <refspec>
    mkdir -p "$TEST_DIR/hooks"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'export PATH=%q:"$PATH"\n' "$TEST_DIR/shim"
        printf 'exec %q "$@"\n' "$HOOK"
    } > "$TEST_DIR/hooks/pre-push"
    chmod 755 "$TEST_DIR/hooks/pre-push"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/hooks"
    run git -C "$REPO" push origin "$1"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
}
remote_holds_ref() { git -C "$TEST_DIR/remote.git" rev-parse -q --verify "$1" >/dev/null; }   # <ref>

# A grep first on the hook's PATH that exits 2 (an error, not a no-match) for
# ONE argument shape and runs the real grep for every other: the shape is the
# read's own flags, so the fixture decides which read meets it.
grep_refusing() {   # <bash test over the shim's "$@">
    local real_grep
    real_grep="$(command -v grep)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then echo "shim: grep refused" >&2; exit 2; fi\n' "$1"
        printf 'exec %q "$@"\n' "$real_grep"
    } > "$TEST_DIR/shim/grep"
    chmod 755 "$TEST_DIR/shim/grep"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "the header's two lists of reads are DERIVED from the tags at the helper's call sites: every judged_read call carries an own= or a gate= tag, and each list names exactly the tags of its kind (a name added or dropped by hand is red here)" {
    # the tags, one per call site (a call's tag is on the same line as the helper's name)
    tags="$(grep -oE 'judged_read (own|gate)="[^"]*"' "$HOOK" | sed 's/^judged_read //' | sort -u)"
    [ -n "$tags" ]
    # every invocation of the helper carries a tag: the lines naming it as a command
    # (its definition and the comments set aside, a trailing comment stripped first)
    calls="$(sed -E 's/[[:space:]]+#.*$//' "$HOOK" | grep -vE '^[[:space:]]*#' | grep -E '(^|[[:space:]!&|;(])judged_read([[:space:]]|$)' | grep -v 'judged_read()' | grep -vcE 'judged_read (own|gate)="[^"]*"')" || true
    [ "$calls" = 0 ]
    [ "$(grep -cE '(^|[[:space:]!&|;(])judged_read (own|gate)="' "$HOOK")" -gt 40 ]      # the call sites are many: a regex that matched none would pass the count above for the wrong reason
    # the header's lists: the indented names under each heading, until the first line that is not one; a line
    # indented deeper under a name is that read's fact, which the lists carry since round 8b2 (both generated
    # from tests/pre-push-reads.tsv), and is no name
    listed="$(awk '/^# Reads gated by a sibling fact \(gate=\):$/ { m = "gate"; next }
                   /^# Reads whose empty answer is the object.s own \(own=\):$/ { m = "own"; next }
                   m != "" && /^#    / { next }
                   m != "" && /^#   / { sub(/^#   /, ""); print m "=\"" $0 "\""; next }
                   m != "" { m = "" }' "$HOOK" | sort -u)"
    [ -n "$listed" ]
    [ "$tags" = "$listed" ]
    # both kinds are in use, and the two lists are disjoint
    [[ "$tags" == *'gate="'* ]]
    [[ "$tags" == *'own="'* ]]
    [ "$(printf '%s\n' "$tags" | sed 's/^[a-z]*=//' | sort | uniq -d | wc -l)" = 0 ]
}

@test "the ADDED LINES grep exiting 2 (an error, not a no-match) is refused as unscanned naming the read, through a real push: a grep that could not read the lines is not a commit that added nothing, and the remote stays at the base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "remove it"                     # gone at the tip: the added-lines pass alone can name it
    grep_refusing '[ "${1:-}" = -a ]'                    # the added-lines grep's shape (-a -i -F); no other grep of the hook reads a file as text
    run _hook_in "$REPO" -c 'printf "x\n" | grep -a -i -F -e x; echo "status $?"'
    [[ "$output" == *"status 2"* ]]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the ADDED LINES of commit ${leak:0:10} could not be grepped (grep exited 2)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]     # nothing was read to find
    [[ "$output" != *"BLOCKED"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the SYMLINK TARGET grep exiting 2 is refused as unscanned naming the link, through a real push of a branch whose tip inherits the link: an unread target is not a clean one, and the remote never gets the branch" {
    branch_inheriting_mains_symlink_leak                 # main published the link; the branch adds a clean file, under the chosen identity, so no address grep runs
    sha="$(git -C "$REPO" rev-parse HEAD)"
    grep_refusing '[ "${1:-}" = -qi ]'                   # the target grep's shape (-qi -F), shared with the address-domain grep, which this fixture never reaches
    push_ref_through_hook_with_shim feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"the SYMLINK TARGET of node_modules at the tip of refs/heads/feature (${sha:0:10}) could not be grepped (grep exited 2)"* ]]
    [[ "$output" != *"-> /home/zzsynthuser"* ]]
    [[ "$output" != *"BLOCKED"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

# The commit listing (rev-list over the range) answering NOTHING with a clean
# status: read as "no commit to scan", the per-commit loop ran zero times and a
# middle commit's banned line was published through a real push, on a new
# branch and on a ref update alike (the round 5 refuters, 2026-09-22). The
# empty listing is now judged against the type the pushed object peels to (a
# blob or a tree names no commit), else against the remote-tracking refs
# containing the pushed commit OR its ancestry over the remote's current
# commit, and refused naming the read and the empty answer when neither holds.
empty_rev_list() { git_refusing '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]' 0 ""; }   # the range listing alone (<sha> --not --remotes ...): the parent count carries --parents, the credential probe is skipped

@test "a commit listing that answers NOTHING (rev-list exiting 0 with no commit) on a NEW branch is refused as unscanned naming the read and the empty answer, through a real push: no remote-tracking ref contains the tip, so the listing answered short, and the remote holds nothing" {
    add_remote
    commit_file base.txt "notes-api" "base"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    remove_file leak.txt "remove it"                     # gone at the tip: only the per-commit half can name it
    sha="$(git -C "$REPO" rev-parse HEAD)"
    empty_rev_list
    run _hook_in "$REPO" -c 'git rev-list "$1" --not --remotes' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git rev-list --parents -n 1 "$1"' _ "$sha"       # the parent count read is untouched
    [[ "$output" == "$sha "* ]]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the COMMITS of refs/heads/main (${sha:0:10}) were listed as none (git rev-list exited 0 and printed nothing) while no remote-tracking ref contains the pushed commit and the ref is new on the remote, so the listing answered short"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]     # the loop ran over nothing: refused for the read, not as a finding
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "the same empty listing on a REF UPDATE is refused the same way, the line naming the remote's commit the tip does not descend from, and the remote stays at the base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    remove_file leak.txt "remove it"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    empty_rev_list
    run _hook_in "$REPO" -c 'git merge-base --is-ancestor "$1" "$2"; echo "status $?"' _ "$sha" "$BASE"   # the tip is no ancestor of the base
    [[ "$output" == *"status 1"* ]]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the COMMITS of refs/heads/main (${sha:0:10}) were listed as none (git rev-list exited 0 and printed nothing) while no remote-tracking ref contains the pushed commit and it is not an ancestor of the remote's ${BASE:0:10}, so the listing answered short"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "a tag of a BLOB passes through a real push beside that shim: the empty listing is the object's own (the pushed object peels to a blob, which names no commit), and the remote gets the tag" {
    add_remote
    commit_file f.txt "plain" "base"
    git -C "$REPO" tag -a blobtag "$(git -C "$REPO" rev-parse HEAD:f.txt)" -m "a tag of a blob"
    sha="$(git -C "$REPO" rev-parse refs/tags/blobtag)"
    empty_rev_list
    run _hook_in "$REPO" -c 'git cat-file -t "$1^{}"' _ "$sha"
    [ "$output" = blob ]
    push_ref_through_hook_with_shim refs/tags/blobtag
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    remote_holds_ref refs/tags/blobtag
}

@test "a REWIND (the pushed commit an ancestor of the remote's current one) passes with nothing printed: the real listing is empty and the ancestry agrees, so the empty answer is right; a tip on a remote-tracking ref of another remote agrees the same way" {
    add_remote
    commit_file base.txt "notes-api" "base"
    base="$(git -C "$REPO" rev-parse HEAD)"
    commit_file web.txt "the web session's work" "later"
    git -C "$REPO" push -q origin main
    later="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" reset -q --hard "$base"
    git -C "$REPO" update-ref -d refs/remotes/origin/main                                                             # no remote-tracking ref contains the tip: the ancestry alone can agree
    run _hook_in "$REPO" -c 'git rev-list "$1" --not --remotes "$2"' _ "$base" "$later"
    [ -z "$output" ]
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< "refs/heads/main $base refs/heads/main $later"   # the rewind, as a force-push would feed it
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    git -C "$REPO" update-ref refs/remotes/upstream/main "$base"                                                      # the same tip on ANOTHER remote's ref, pushed as a new ref here: the remote refs agree
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< "refs/heads/sync $base refs/heads/sync $ZERO"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# The parent count (rev-list --parents -n 1) answering NOTHING with a clean
# status beside a combined listing answering nothing: the merge read as a
# one-parent commit, the two empty answers agreed, and the merge's hidden link
# was published through a real push (the round 5 refuters, 2026-09-22). The
# count is now read in bash and judged against the commit named first once the
# read exited 0; a short answer is refused naming it.
empty_parents_and_listing() {   # <sha>: a git whose `rev-list --parents -n 1 <sha>` and `diff-tree ... --raw ... -c ... <sha>` exit 0 and print nothing, the real git for every other command and every other commit
    git_refusing "[ \"\${!#}\" = $1 ] && { { [ \"\${1:-}\" = rev-list ] && [ \"\${2:-}\" = --parents ]; } || case \" \$* \" in *\" --raw \"*\" -c \"*) true ;; *) false ;; esac; }" 0 ""
}

@test "a parent count that answers NOTHING beside a combined listing that answers nothing is refused as unscanned naming the count's short answer, through a real push of a merge with a hidden link: two empty answers agreeing is not a one-parent commit, and the remote stays at the base" {
    merge_with_hidden_link
    empty_parents_and_listing "$sha"
    run _hook_in "$REPO" -c 'git rev-list --parents -n 1 "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames --root -c -z --no-commit-id "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the ADDED LINES of commit ${sha:0:10} could not be read (git rev-list --parents exited 0 and answered \"\", not the commit and its parents)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"exited 128"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

# The tip's symlink TARGET read (cat-file -p of the link blob) answering NOTHING
# with a clean status: read as an empty target, a link the remote already held
# whose target carried a banned string passed through a real push (the round 5
# refuters, 2026-09-22). The empty answer is now judged against the blob's
# size, emptiness against emptiness; the capture keeps a target of a newline
# alone distinct from an empty one.
silent_cat_file_p() {   # <blob>: a git whose `cat-file -p <blob>` exits 0 and prints nothing, the real git for every other command (cat-file -s included)
    git_refusing "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $1 ]" 0 ""
}

@test "a symlink TARGET read that answers NOTHING (cat-file -p exiting 0 with no output, the size read untouched) over a link the remote already holds is refused as unscanned naming the link, the empty answer and the size, through a real push: an empty answer is an empty target only when the blob is, and the remote never gets the branch" {
    branch_inheriting_mains_symlink_leak                 # main published the link: the tip's symlink pass alone reads it
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$sha:node_modules")"
    size="$(git -C "$REPO" cat-file -s "$blob")"
    [ "$size" -gt 0 ]
    silent_cat_file_p "$blob"
    run _hook_in "$REPO" -c 'git cat-file -p "$1"' _ "$blob"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    push_ref_through_hook_with_shim feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"the SYMLINK TARGET of node_modules at the tip of refs/heads/feature (${sha:0:10}) was read as empty while git cat-file -s gives its size as $size bytes, so the read answered short (git cat-file -p exited 0)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"-> /home/zzsynthuser"* ]]          # judged by nothing: refused for the read, not as a finding
    [[ "$output" != *"could not be read"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "the controls: a link over the EMPTY blob passes (the size agrees with the empty answer), and a link whose target is a newline alone passes too (the capture keeps it distinct from empty, so the size is never asked)" {
    commit_file f.txt "plain" "base"
    empty="$(git -C "$REPO" hash-object -w --stdin < /dev/null)"
    nl="$(printf '\n' | git -C "$REPO" hash-object -w --stdin)"
    git -C "$REPO" update-index --add --cacheinfo "120000,$empty,emptylink"
    git -C "$REPO" update-index --add --cacheinfo "120000,$nl,newlinelink"
    git -C "$REPO" commit -qm "two odd links"
    [ "$(git -C "$REPO" cat-file -s "$nl")" = 1 ]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# The tip's content grep answering NOTHING with exit 0: git grep exits 0 for a
# match, so a match that printed no hit line is a short answer, judged against
# the grep's own status (the helper's road for a read whose sibling fact is its
# status). Real git never does this; the shim shows the gate.
silent_content_grep() { git_refusing '[ "${1:-}" = grep ] && [ "${3:-}" = -i ]' 0 ""; }   # the content grep alone (--no-color -i -I -l -F): the read list's grep carries -I -l -z and no -i

@test "a tip content grep that exits 0 (a match) and prints NO hit line is refused as unscanned naming the read and the short answer, through a real push of a branch whose tip inherits main's leak: the status says a match, the answer says none, and the remote never gets the branch" {
    branch_inheriting_mains_leak                         # main published leak.txt; the branch adds a clean file, so the tip grep alone can name the leak
    sha="$(git -C "$REPO" rev-parse HEAD)"
    silent_content_grep
    run _hook_in "$REPO" -c 'git grep --no-color -i -I -l -F -e zzsynthuser "$1" --' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    push_ref_through_hook_with_shim feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"the CONTENT of the tip of refs/heads/feature (${sha:0:10}) was scanned with no hit listed (git grep exited 0, a match, and printed no hit line), so the answer is short"* ]]
    [[ "$output" != *"would publish a personal identifier"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

# Until round 9 the credential half's own count (scannable_commits) answering
# NOTHING with a clean status skipped the comparison with the scanner's count,
# and the case below held that; the count is retired, and the slot holds its
# successor, the feed's awk recording nothing (an awk silent on the program that
# names the record file in its environment).

@test "the feed's awk answering NOTHING (exit 0, no record written) is refused as unscanned naming the feed and the empty record: an empty record is not five counts (four until round 10a, which counts the binary notices the awk routes; round 9d: this slot held the hook's own commit count answering nothing, a read retired in round 9)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    awk_silent_on_program 'ENVIRON["ROMP_RECORD_FILE"]'
    run _hook_in "$REPO" -c 'printf "x\n" | awk "BEGIN { r = ENVIRON[\"ROMP_RECORD_FILE\"] } { print }"; echo "status $?"'
    [ "$output" = "status 0" ]                          # the shim as the feed meets it: nothing printed, exit 0
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push could not be read (its awk exited 0 and recorded \"\", not five counts); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    at_base
}


# ── round 6b: the previous-version line's two remedies, the join's fourth arm, the short file's path ──
# Round 5's refuters, by execution on the round 5 text: (1) a merge's rename
# candidate whose combined section printed Binary (a text file moved onto a
# path a parent holds a binary file at) was marked as judged by the addition
# verdict alone, so the report skipped every parent's version and printed the
# key's facts and the key's advice with no cause named; the marker is now set
# only where the addition verdict decided (a type change; a merge's rename
# candidate the patch printed no section for), and such a candidate takes the
# parent loop. (2) The previous-version line printed the fetch remedy alone on
# the claim that neither the key nor an attribute lifts a pair binary by its
# bytes; an explicit diff attribute on the PREVIOUS version's path (the old
# path for a rename; the file's own path otherwise) does, so the paragraph
# names that line too, whatever the attribute read did, and two cases below
# show it turning the refusal into the ADDS hit. (3) The join's tools failing
# for a reason of their own (a tr exiting 1, an awk exiting 2) were reported as
# a numstat that answered short, a cause the status does not establish; the
# fourth arm names the JOIN's own failure, its pipeline's status, the tool's
# error line above it and whether the join had written the short file before
# the failure. (4) The short file's path reached awk through -v, which
# escape-processes its value: under a TMPDIR carrying a backslash pair gawk
# warned on every clean push and lost the path at a short read; the path
# travels through the environment now, which awk leaves alone.
awk_refusing_join() {   # an awk that exits 2 with a line on stderr for the join's program (the one given -v rev=, the join's alone) and runs the real awk for every other
    local real_awk
    real_awk="$(command -v awk)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = -v ] && [[ "${2:-}" == rev=* ]]; then echo "shim: awk refused (the join)" >&2; exit 2; fi\n'
        printf 'exec %q "$@"\n' "$real_awk"
    } > "$TEST_DIR/shim/awk"
    chmod 755 "$TEST_DIR/shim/awk"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "a MERGE moving a text file carrying the string onto a path a parent holds a BINARY file at (a rename candidate whose combined section printed Binary), gone at the tip, is refused on the parent's version: the line names parent 1's bytes as the cause, with the fetch remedy and the attribute line, and the key's facts and advice are absent, since the patch's verdict decided it and not the addition numstat's" {
    add_remote
    printf 'ab\0cd\n' > "$REPO/bin.dat"
    git -C "$REPO" add bin.dat
    commit_file notes.txt "seen on TESTHOST" "a binary file and a text file"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
    git -C "$REPO" mv -f notes.txt bin.dat
    git -C "$REPO" commit -qm "merge side, notes.txt moved onto bin.dat"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    remove_file bin.dat "remove it"                              # gone at the tip: only the per-commit half can name it
    # the road as git applies it: both parents hold a NUL-carrying bin.dat, so the section prints Binary and no hunk for the new text;
    # notes.txt is a deletion against each parent, so the new path is a rename candidate as well, on the Binary section
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- bin.dat' _ "$merge"
    [[ "$output" == *"Binary files differ"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames -m -z --no-commit-id "$1" | tr "\0" "|"' _ "$merge"
    [[ "$output" == *" D|notes.txt|"* ]]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: bin.dat in commit ${merge:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict; the previous version of the file in parent 1 of the merge is binary by its bytes (a NUL in its first 8000), which made git print no text diff for the change, and the identifier scan could not read the new text, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names the previous version's bytes as the cause, the hook scans only commits new to every fetched remote"* ]]
    [[ "$output" == *"set the diff attribute on the PREVIOUS version's path"* ]]
    [[ "$output" != *"core.bigFileThreshold is not set"* ]]       # the round 5 text printed the key's facts here, the marker having skipped every parent
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"Remove the diff attribute"* ]]
    [[ "$output" != *"the diff read it as a rename"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"personal identifier"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "a one-parent commit turning a NUL-carrying file into a text file (the disclosed shape) whose check-attr FAILS is refused on the previous version's bytes, the failure in the attribute's place, with both remedies of that line, the fetch paragraph and the attribute line; the attribute paragraph (remove a -diff) and the key's sentence are absent, since the line named the bytes as the cause" {
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    commit_file thing "seen on TESTHOST" "now a text file carrying the string"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file thing "remove it"                                # gone at the tip: only the per-commit half can name it
    git_refusing '[ "${1:-}" = check-attr ]' 128 "fatal: shim: check-attr refused"
    run _hook_in "$REPO" -c 'git check-attr -z diff -- thing'
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: thing in commit ${leak:0:10} is text that git calls binary although its diff attribute could not be read (git check-attr exited 128), so whether an attribute of its path accounts for the verdict is unknown; the previous version of the file is binary by its bytes (a NUL in its first 8000), which made git print no text diff for the change, and the identifier scan could not read the new text, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"Where a line names the previous version's bytes as the cause, the hook scans only commits new to every fetched remote"* ]]
    [[ "$output" == *"set the diff attribute on the PREVIOUS version's path"* ]]      # the attribute line: present whatever the attribute read did
    [[ "$output" != *"Remove the diff attribute"* ]]                                  # the attribute paragraph: withheld, the line having named the bytes (red with the gate's prior clause dropped)
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"so no attribute of its path accounts for the verdict"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "the same shape with an explicit diff attribute on the file's path (the previous version's path for a one-parent change) is the ADDS hit naming the commit and the path, and no line calls it hidden: under the attribute git treats the NUL-carrying version as text, so the diff prints the change and the scan reads it" {
    attributes 'thing diff'
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    commit_file thing "seen on TESTHOST" "now a text file carrying the string"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file thing "remove it"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" -- thing' _ "$leak"
    [[ "$output" == *"+seen on TESTHOST"* ]]                     # the road: the attribute lifts the pair to text, so the hunk prints
    [[ "$output" != *"Binary files"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: commit ${leak:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  thing"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"previous version"* ]]
}

@test "the rename twin: an explicit diff attribute on the NEW path alone leaves the refusal standing, the line naming the old path as the previous version's; the attribute on the OLD path, the pre-image's, turns it into the ADDS hit naming the new path" {
    { printf 'line %s\n' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; printf 'x\0y\n'; } > "$REPO/old.txt"
    git -C "$REPO" add old.txt
    git -C "$REPO" commit -qm "a file binary by its bytes"
    git -C "$REPO" mv old.txt new.txt
    { printf 'line %s\n' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; printf 'seen on TESTHOST\n'; } > "$REPO/new.txt"
    git -C "$REPO" add new.txt
    git -C "$REPO" commit -qm "renamed and made text, the string in the change"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file new.txt "remove it"
    attributes 'new.txt diff'                                    # the wrong path: the new side was text already, and the old side's bytes decide
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$leak"
    [[ "$output" == *"Binary files a/old.txt and b/new.txt differ"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: new.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads set, so no attribute of its path accounts for the verdict; the previous version of the file (at old.txt, the path the diff read it from) is binary by its bytes"* ]]
    [[ "$output" == *"set the diff attribute on the PREVIOUS version's path"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    attributes 'old.txt diff'                                    # the pre-image's path, the one the paragraph names for a rename
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$leak"
    [[ "$output" == *"+seen on TESTHOST"* ]]
    [[ "$output" != *"Binary files"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: commit ${leak:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"  new.txt"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"previous version"* ]]
}

@test "the join's tr failing for a reason of its own (exit 1, after the awk had met a post-image with no verdict) is refused as the JOIN's own failure: the line names the pipeline's status, says the tool's error line is above it, names the path the join had recorded, and claims no short read, since a tr that failed is not a numstat that answered short" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file file.txt "remove it"                             # gone at the tip: the blob is the commit's to judge
    empty_diff_tree_numstat                                      # every numstat answers nothing: the join meets file.txt with no verdict (status 3) and writes the short file before its tr runs
    tr_refusing join 2                                           # the tip's candidates join is the first tr of the joins' shape, the commit's join the second (the removal commit has no post-image and no join)
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"shim: tr refused (join 2)"*"romp pre-push: the JOIN of commit ${sha:0:10}'s verdicts could not be made for the BINARY VERDICT check (its pipeline exited 1; the tool's own error line, where it printed one, is above; the join had recorded file.txt as a post-image met no verdict for before the pipeline failed)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"answered for fewer paths"* ]]              # the round 5 text's cause: the status does not establish a short read
    [[ "$output" != *"could not be joined"* ]]
    [[ "$output" != *"exited 3"* ]]
    [ "$(cat "$TEST_DIR/tr-calls")" -eq 2 ]
}

@test "the join's awk failing for a reason of its own (exit 2) on a MERGE with a hidden link is refused the same way, the line naming the status and that the join had recorded no path; the link is neither called hidden nor a short read" {
    merge_with_hidden_link
    awk_refusing_join
    run _hook_in "$REPO" -c 'echo x | awk -v rev=abc "{ print }"'
    [ "$status" -eq 2 ]
    [[ "$output" == *"shim: awk refused (the join)"* ]]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"shim: awk refused (the join)"*"romp pre-push: the JOIN of commit ${sha:0:10}'s verdicts could not be made for the BINARY VERDICT check (its pipeline exited 2; the tool's own error line, where it printed one, is above; the join had recorded no post-image as met no verdict for)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [[ "$output" != *"could not be joined"* ]]
}

@test "a clean push under a TMPDIR whose path carries a backslash-q pair prints NOTHING: the short file's path reaches the join's awk through the environment, which awk does not escape-process (through -v, gawk warned on every commit's join)" {
    export TMPDIR="$TEST_DIR/tmp\\qdir"
    mkdir -p "$TMPDIR"
    commit_file file.txt "nothing to see" "clean"
    run _hook_in "$REPO" -c 'printf "%s" "$TMPDIR"'
    [[ "$output" == *'\q'* ]]
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ "$(ls -1 "$TMPDIR" | grep -c '^romp-pre-push\.')" -eq 0 ]
}

@test "a short read under a TMPDIR carrying a backslash-q pair, and under one carrying a backslash-n pair, names the path met no verdict for and prints no fatal or warning line: the short file's path is not altered on its way to awk (through -v, the backslash-n cut it at a newline, the join ended on a failed redirect and the line named no path)" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file file.txt "remove it"
    empty_diff_tree_numstat
    for d in 'tmp\qdir' 'tmp\ndir'; do
        export TMPDIR="$TEST_DIR/$d"
        mkdir -p "$TMPDIR"
        run_hook
        [ "$status" -eq 1 ]
        [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes and printed no verdict for file.txt)"* ]]
        [[ "$output" != *"fatal:"* ]]
        [[ "$output" != *"warning:"* ]]
        [[ "$output" != *"did not record"* ]]
        [[ "$output" != *"could not be made"* ]]
        [ "$(ls -1 "$TMPDIR" | grep -c '^romp-pre-push\.')" -eq 0 ]
    done
}

# ── round 7: the exit-0 empty-answer class closed for real ──────────────────
# Round 6's refuters drove every read tagged own= with a tool exiting 0 and
# printing nothing, through real pushes: five of them and the ref list itself
# published (the tip's candidate join under a silent awk or tr, the join of a
# commit's verdicts under either, the added-lines diff under a silent awk, the
# message grep under a silent grep, a tag's tagger and message under a silent
# awk, and every ref of a push under a silent cat), and a capture file that
# could not be opened published too, bash's own error line the only sign. The
# hook now reads the ref list and the tag object by the shell alone, gates each
# candidate join on a count (in hand for the tip: the listing's regular files
# with bytes less the grep's read list; recorded by the join's own awk for a
# commit), gates the added-lines diff on the count its awk records, refuses a
# match that printed no hit line for the message and the added-lines greps,
# and opens every capture file once to a descriptor before the command runs,
# refusing a failed open whatever the expected set. The cases below are those
# reads, each through a real push with the shim that published at the round 6
# text and the remote asserted to hold nothing new; the last two are the
# capture open, through a push and as a unit over the helper's two branches.
# The message grep's and the tag's cases are in pre-push-message.bats and
# pre-push-identity.bats, beside the reads they drive.
grep_silent() {   # <bash test over the shim's "$@">: a grep exiting 0 (a match) and printing nothing for that shape, the real grep otherwise
    local real_grep
    real_grep="$(command -v grep)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then cat > /dev/null; exit 0; fi\n' "$1"
        printf 'exec %q "$@"\n' "$real_grep"
    } > "$TEST_DIR/shim/grep"
    chmod 755 "$TEST_DIR/shim/grep"
    export PATH="$TEST_DIR/shim:$PATH"
}
awk_silent_on_program() {   # <text of an awk program>: an awk exiting 0 and printing nothing when its arguments carry that text, the real awk for every other program
    local real_awk
    real_awk="$(command -v awk)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'real_awk=%q; marker=%q\n' "$real_awk" "$1"
        cat <<'SHIM'
case "$*" in *"$marker"*) cat > /dev/null; exit 0 ;; esac
exec "$real_awk" "$@"
SHIM
    } > "$TEST_DIR/shim/awk"
    chmod 755 "$TEST_DIR/shim/awk"
    export PATH="$TEST_DIR/shim:$PATH"
}
tr_silent_join() {   # <N>: the Nth tr of the joins' shape ('\n' '\0') reads its input and exits 0 writing nothing; the real tr runs otherwise
    local real_tr
    real_tr="$(command -v tr)"
    mkdir -p "$TEST_DIR/shim"
    echo 0 > "$TEST_DIR/tr-calls"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'real_tr=%q; counter=%q; n=%d\n' "$real_tr" "$TEST_DIR/tr-calls" "$1"
        cat <<'SHIM'
if [ $# -eq 2 ] && [ "$1" = '\n' ] && [ "$2" = '\0' ]; then
    seen=$(( $(cat "$counter") + 1 )); echo "$seen" > "$counter"
    if [ "$seen" -eq "$n" ]; then cat > /dev/null; exit 0; fi
fi
exec "$real_tr" "$@"
SHIM
    } > "$TEST_DIR/shim/tr"
    chmod 755 "$TEST_DIR/shim/tr"
    export PATH="$TEST_DIR/shim:$PATH"
}
cat_silent() {   # a cat that reads its input and exits 0 writing nothing (the round 6 refuters' shim over the ref list)
    mkdir -p "$TEST_DIR/shim"
    printf '#!/usr/bin/env bash\nwhile IFS= read -r line; do :; done\nexit 0\n' > "$TEST_DIR/shim/cat"
    chmod 755 "$TEST_DIR/shim/cat"
    export PATH="$TEST_DIR/shim:$PATH"
}
mktemp_making_hits_a_directory() {   # a mktemp that makes the scratch directory as the real one does, and a DIRECTORY named hits inside it, so the added-lines grep's capture file cannot be opened
    local real_mktemp
    real_mktemp="$(command -v mktemp)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'real_mktemp=%q\n' "$real_mktemp"
        cat <<'SHIM'
d=$("$real_mktemp" "$@") || exit $?
mkdir "$d/hits"
printf '%s\n' "$d"
SHIM
    } > "$TEST_DIR/shim/mktemp"
    chmod 755 "$TEST_DIR/shim/mktemp"
    export PATH="$TEST_DIR/shim:$PATH"
}
leak_in_middle_commit_after_base() {   # a base on the remote (BASE), then a commit adding a banned line (leak), removed at the tip: the added-lines pass alone can name it
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file leak.txt "remove it"
}

@test "the ADDED LINES grep exiting 0 (a match) and printing NO line is refused as unscanned naming the grep and the short answer before the sort runs, through a real push (case 175's shape, silent instead of failing): the sort is not named for a grep that answered nothing, and the remote stays at the base" {
    leak_in_middle_commit_after_base
    grep_silent '[ "${1:-}" = -a ]'                      # the added-lines grep's shape (-a -i -F), as in case 175
    run _hook_in "$REPO" -c 'printf "x\n" | grep -a -i -F -e x; echo "status $?"'
    [ "$output" = "status 0" ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the ADDED LINES of commit ${leak:0:10} were grepped with no hit line listed (grep exited 0, a match, and printed no line), so the answer is short"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"sort exited 0"* ]]                 # the round 6 text's line, naming the wrong tool
    [[ "$output" != *"could not be reported"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the TIP CANDIDATES join under an awk exiting 0 and printing nothing is refused as unscanned naming the read and the three counts, through a real push: the -z listing names 3 regular files with bytes and the grep read 2, so 1 candidate was due and 0 came, and the hidden text file the remote already holds is not passed by the empty join; the remote stays at the base" {
    hidden_file_on_remote_then_clean_commit
    awk_silent_on_program 'printf "tip'                  # the tip join's program alone (its rows begin with the word tip)
    run _hook_in "$REPO" -c 'printf "x\n" | awk "{ printf \"tip\\t%s\\n\", \$0 }"; echo "status $?"'
    [ "$output" = "status 0" ]
    run _hook_in "$REPO" -c 'git grep --no-color -I -l -z -e "" "$1" -- | tr "\0" "\n" | wc -l' _ "$sha"
    [ "$output" = 2 ]                                      # .gitattributes and other.txt read; notes.txt skipped under -diff
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the TREE of the tip of refs/heads/main (${sha:0:10}) was joined short with the grep's read list for the BINARY VERDICT check (the join appended 0 candidate rows where the -z listing names 3 regular files with bytes and the grep's read list 2 of them, so the count expected is 1; awk and tr exited 0)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is text that"* ]]                  # judged by nothing: refused for the read, not for the blob
    [[ "$output" != *"could not be joined"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the same join under a tr exiting 0 and writing nothing (the first tr of the joins' shape: the tip's) is refused the same way, naming the same three counts; the remote stays at the base" {
    hidden_file_on_remote_then_clean_commit
    tr_silent_join 1
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the TREE of the tip of refs/heads/main (${sha:0:10}) was joined short with the grep's read list for the BINARY VERDICT check (the join appended 0 candidate rows where the -z listing names 3 regular files with bytes and the grep's read list 2 of them, so the count expected is 1; awk and tr exited 0)"* ]]
    [[ "$output" != *"is text that"* ]]
    [ "$(cat "$TEST_DIR/tr-calls")" -ge 1 ]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the JOIN of a commit's verdicts under an awk exiting 0 and printing nothing is refused as unscanned naming the read and the missing count, through a real push: the join's awk records the count of rows it printed and a join that recorded none is not a join that found none, so the hidden text file in the middle commit is not passed by it; the remote stays at the base" {
    hidden_file_in_middle_commit_after_base
    awk_silent_on_program 'ENVIRON["ROMP_SHORT_FILE"]'   # the join's program alone: the short file's path is read from the environment there
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the JOIN of commit ${leak:0:10}'s verdicts could not be made for the BINARY VERDICT check (its pipeline exited 0 and its awk recorded \"\" as the count of candidate rows it printed, not a count, so whether every candidate was appended is unknown)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"printed no verdict"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the same join under a tr exiting 0 and writing nothing (the second tr of the joins' shape: the tip's join is the first, and the removal commit has no post-image to join) is refused naming the rows appended against the count the awk recorded; the remote stays at the base" {
    hidden_file_in_middle_commit_after_base
    tr_silent_join 2
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the JOIN of commit ${leak:0:10}'s verdicts appended 0 candidate rows for the BINARY VERDICT check where its awk recorded 1 printed (its pipeline exited 0), so the join answered short"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is text that"* ]]
    [ "$(cat "$TEST_DIR/tr-calls")" -eq 2 ]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the ADDED LINES diff under an awk exiting 0 and printing nothing is refused as unscanned naming the read and the missing count, through a real push: the diff's awk records the count of lines it printed, so an empty capture with no count is not a commit that added nothing, and the remote stays at the base" {
    leak_in_middle_commit_after_base
    awk_silent_on_program 'plus = plus "+"'              # the added-lines program alone (the column of pluses it builds)
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the ADDED LINES of commit ${leak:0:10} could not be read (the diff's awk exited 0 and recorded \"\" as the count of lines it printed, not a count)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"could not be grepped"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the REF LIST under a cat exiting 0 and printing nothing: every ref is still scanned, since the shell's own read builtin takes git's list and no tool on PATH stands between them; a tip carrying a banned string is refused through a real push and the remote holds nothing, while an EMPTY list stays git's own answer and passes with nothing printed" {
    add_remote
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    cat_silent
    run _hook_in "$REPO" -c 'printf "x\n" | cat; echo "status $?"'
    [ "$output" = "status 0" ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the tip of refs/heads/main (${sha:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"leak.txt"* ]]
    [[ "$output" == *"BLOCKED"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
    # the control: no ref line at all (nothing to update) is read as no ref, the hook exits 0 and prints nothing
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git < /dev/null
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "a capture file the helper cannot OPEN (a mktemp whose scratch directory holds hits as a DIRECTORY) is refused as unscanned naming the read and the file, through a real push: the file is opened once before the grep runs, so a failed open is not a grep that found nothing, and the remote stays at the base" {
    leak_in_middle_commit_after_base
    mktemp_making_hits_a_directory
    run _hook_in "$REPO" -c 'd=$(mktemp -d "${TMPDIR:-/tmp}/romp-pre-push.XXXXXX"); [ -d "$d/hits" ] && echo "hits is a directory"; rm -rf "$d"'
    [ "$output" = "hits is a directory" ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the ADDED LINES of commit ${leak:0:10} could not be grepped (grep was not run: its output file "*"/hits could not be opened for writing)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"grep exited"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "judged_read opens its capture file ONCE before the command runs and refuses a failed open whatever the expected set, in the -o branch and in the -a branch (the helper read out of the hook): a set holding 1 does not admit a command that never ran, a good open writes or appends, and a status outside the set is still the set's refusal" {
    probe="$TEST_DIR/probe.sh"
    {
        printf 'set -uo pipefail\nfailed_scan=0; unscanned_n=0; read_rc=0; read_out=""\n'          # the hook's globals the two helpers read (unscanned_n since round 9d)
        sed -n '/^unscanned() {/,/^}/p; /^judged_read() {/,/^}/p' "$HOOK"
        cat <<'PROBE'
mkdir -p "$1/dir"
echo "--- -o onto a directory, the set 0,1"
judged_read own="the PROBE read" 0,1 "the PROBE of x could not be read (probe exited {rc})" -o "$1/dir" -- printf 'x\n'; echo "o-dir rc=$? failed_scan=$failed_scan"
failed_scan=0
echo "--- -a onto a directory, the set 0,1"
judged_read own="the PROBE read" 0,1 "the PROBE of x could not be read (probe exited {rc})" -a "$1/dir" -- printf 'x\n'; echo "a-dir rc=$? failed_scan=$failed_scan"
failed_scan=0
echo "--- -o onto a file: written once, the old content gone"
printf 'old\n' > "$1/out"
judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -o "$1/out" -- printf 'x\n'; echo "o-file rc=$? failed_scan=$failed_scan out=$(tr '\n' , < "$1/out")"
echo "--- -a onto the same file: appended"
judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -a "$1/out" -- printf 'y\n'; echo "a-file rc=$? failed_scan=$failed_scan out=$(tr '\n' , < "$1/out")"
echo "--- a status outside the set with the file open is the set's own refusal"
judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -o "$1/out" -- bash -c 'exit 3'; echo "o-status rc=$? failed_scan=$failed_scan"
echo "--- the descriptor is closed again: a second read after the first opens afresh"
failed_scan=0
judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -o "$1/out2" -- bash -c 'ls /proc/self/fd 2>/dev/null | tr "\n" " "'; echo "fds=$(cat "$1/out2")"
PROBE
    } > "$probe"
    run bash "$probe" "$TEST_DIR/p"
    [ "$status" -eq 0 ]
    [ "$(grep -c "the PROBE of x could not be read (probe was not run: its output file $TEST_DIR/p/dir could not be opened for writing); the scan is incomplete, so the push is refused" <<< "$output")" -eq 2 ]
    [[ "$output" == *"o-dir rc=1 failed_scan=1"* ]]
    [[ "$output" == *"a-dir rc=1 failed_scan=1"* ]]
    [[ "$output" == *"o-file rc=0 failed_scan=0 out=x,"* ]]
    [[ "$output" == *"a-file rc=0 failed_scan=0 out=x,y,"* ]]
    [[ "$output" == *"the PROBE of x could not be read (probe exited 3); the scan is incomplete"* ]]
    [[ "$output" == *"o-status rc=1 failed_scan=1"* ]]
    [[ "$output" != *"exited 1)"* ]]                      # the failed open is never reported as the command's status 1
    [[ "$output" == *"fds="*" 9 "* ]]                     # the command writes to descriptor 9, the one open
}

# ── round 7b: the population half of the guarantee, the chosen-addresses read, the -d splice, the odd tag, the count grep ──
# Round 6's refuters (2026-09-22) left four things beside the class group A
# closed: (1) case 174 pins the header's two LISTS against the tags at the
# helper's call sites, but nothing pinned the POPULATION: a read added outside
# judged_read with neither a tag nor a marker was invisible to every case (a
# planted `tipname=$(git rev-parse ...)` left 174 and the whole file green).
# The census case below reads the hook's text: every line running a reading
# tool (the vocabulary stated at CENSUS_TOOLS, the census's bound) must be a
# judged_read call, a line inside a function the helper is handed WHOLE (the
# functions derived from the call sites: the first word after the call's --),
# an array-literal assignment (the scanner's argument list) or a line under an
# `outside judged_read:` marker (a trailing comment, the comment block above
# the statement or its backslash-continued first line, or the block above the
# header of the function holding it). Quoted text is masked quote-aware: the
# bytes inside single quotes, $'' quotes, double quotes and comments are hidden,
# and code inside a $( ) within double quotes stays visible, since stripping
# every double-quoted string whole would hide `x="$(git ...)"`, a spelling the
# hook itself uses (the second refuter's bypass). The case also runs the census
# over planted copies, so its own sensitivity is executed here, not assumed.
# (2) The chosen-addresses read (git config --get-all user.email) was the one
# read of the clone's configuration outside the helper whose failure the hook
# swallowed as no chosen address: a commit stamped under the very address the
# clone IS configured to use was then refused as "an address this clone is not
# configured to use", a false cause with an inapplicable remedy, through a real
# push. The read goes through judged_read now (own=, set 0 and 1), called in
# the shell, and the two address lines lead with the failed read where it
# failed (cases 171, 172 and the tag case below). (3) The -d rider's answer
# was spliced into the clause by an UNQUOTED pattern substitution, which bash
# 5.2's patsub_replacement rewrites (& to the matched text, \& to &), and
# {detail} was spliced before {rc}, so a path holding an ampersand or the
# text {rc} misprinted in the join's fourth-arm line. (4) Two reads had no
# case: the fallback commit listing over an object git cannot peel (the round
# 5 text died mid-report at 128 on its bare substitution) and the ENTRY COUNT
# grep -c under the shape that is truly silent, the full count printed and
# status 2 (an empty exit-2 answer is refused already, with the wrong cause).
CENSUS_TOOLS='git|grep|egrep|fgrep|awk|gawk|mawk|sed|tr|wc|od|cat|cut|sort|uniq|head|tail|tac|nl|paste|join|comm|diff|cmp|xxd|hexdump|base64|file|stat|find|xargs|ls|readlink|realpath|basename|dirname|sha1sum|sha256sum|md5sum|cksum|strings|tee|gzip|gunzip|zcat|tar|perl|python|python3|ruby|jq|curl|wget|dd|split|csplit|fold|expand|column|seq|expr|bc|date|gitleaks'
# ^ the census's BOUND: a command line is a read only when it runs one of these (the tools the hook reads with today,
# git, grep, awk, sed, tr, wc, od, cat, sort and head, and the reading tools it might start running); a read made with
# a tool outside the list is not counted, and this line is where the list is widened. Outside on purpose: mktemp
# (make_scratch, a writer whose failure its callers refuse) and the scanner binary (run through a variable, its exit
# judged under a marker); command -v resolves the scanner's path and runs nothing.
# What the census reads (round 8b, the round 7 rulings' B, widened in round 9b by the round 8 rulings' F): each simple
# command census_records finds, the masked text split at ||, &&, |, |&, a lone &, ;, the substitutions' and subshells'
# parentheses, the backtick, a brace that opens no ${, a case pattern's close and a judged_read call's first --. Its
# command word is taken past the keywords (coproc among them), the command prefixes and their option words (a word
# starting with -, and the operand of nice -n and env -u: env -i git, nice -n 19 git and command -p git run git), the
# assignments and the redirections, a redirection operator standing alone with its operand (< /dev/null git runs git),
# and is read back from the RAW text at its offset in the masked text (masking keeps every byte's place), unquoted
# (its quote and backslash characters removed, $'' and $"" read as quotes), then by its basename: "git", 'git', \git,
# /usr/bin/git and a word whose quoting or escaping splits the name (gi\t, g''it, "g"it) run git. census_records
# keeps a simple command for this reading when one of its words, with its quote and backslash characters removed,
# holds a reading tool's name (round 9bc: until then it tested the raw word, and the split spellings passed). A
# command word the census knows is a keyword, a prefix, a builtin (the declarations local, export, readonly, declare
# and typeset among them: their words are names), a lookup that runs nothing (command -v and -V, type, which), a
# function of the hook, judged_read or a reading tool; any other command word counts as a read of a reading tool's
# word later in its simple command (fail-closed, since a wrapper such as timeout, nohup, stdbuf, ionice or setsid runs
# its operand and no list of wrappers has an end; a case pattern, arithmetic and an array literal's elements run
# nothing). Its run over the hook found no such command line (round 9b; round 9bc's unquoted test added no record
# over the hook), so no exception is kept for it. Code inside a $( ) or a backtick substitution is read wherever bash
# runs it, inside double quotes too, and so is the text after a judged_read call's -- past its first simple command,
# the tagged read the tags judge.
# What is PINNED ABSENT: census_unread_shapes lists these shapes in the hook's comment-stripped RAW text (the masked
# text hides what quotes hold), each once per line: a command word that BEGINS with a parameter expansion or a
# substitution, other than the three the hook's own reads use (the tagged command judged_read runs, "$@"; its -d
# rider, "$detail", which prints and reads nothing; and the scanner, "$gl", above); a variable assigned a reading
# tool's name or path, and a default naming one by a path or not (${GIT:-git}, ${GIT:-/usr/bin/git}); a substitution
# whose first word is a lookup (command -v or -V, type or which) naming a reading tool, the scanner's own lookup
# excepted by its exact text, gl="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}" (on one line in the hook), whose
# answer runs only as "$gl"; an eval; a here-doc (a << that is not <<<, whose body the masker would read as code or as
# an open quote); a trap action holding a reading tool's word; source or . of a substitution; and bash -c or sh -c.
# The hook holds none of these.
# What is DISCLOSED: a shape neither read above nor pinned here passes both, and five such shapes are known. Case 203
# plants a witness of each that passes the census and the pins unflagged, so this list states what goes unseen, shown
# true by execution, and claims no coverage: a variable command word under a wrapper the census does not know
# (timeout 5 "$1" rev-parse HEAD: the pin reads only a command word that begins with an expansion, and the fail-closed
# rule looks only for a reading tool's word); a command word holding an expansion that does not begin it
# (/usr/bin/$t rev-parse HEAD); a command after a string continued from the line before (x="a on one line, then
# b" git rev-parse HEAD: a word that starts inside such a string is no command word); an ANSI-C quoted word, whose
# escapes are not decoded ($'\x67it' rev-parse HEAD); and env -S with a command string (env -S "git rev-parse HEAD":
# the quoted string is read as one command word, which equals no reading tool's name). The hook holds none of these
# either (the round 9b audit, 2026-09-24).
# Until round 9b this comment said two shapes stay unread: a lone redirection, a quoted command word, a command after
# a lone & or |&, a wrapper outside the prefixes, and a command word held in a variable by a path or a lookup each
# passed the census and its pins then (the round 8 refuters, 2026-09-24). Until round 9bc it said that what the census
# cannot read is pinned absent, while the five disclosed shapes and a command word split by its quoting passed both
# (the round 9b audit).
CENSUS_PREFIX='^(if|then|else|elif|fi|while|until|do|done|case|esac|in|for|select|function|!|time|coproc|exec|env|nice|command|builtin)$'
CENSUS_BUILTIN='^(read|printf|echo|eval|trap|wait|true|false|:|return|exit|break|continue|shift|set|unset|test|\[|\[\[|local|export|readonly|declare|typeset|shopt|mapfile|readarray|cd|pwd|let|type|hash|getopts|kill|ulimit|umask|alias|unalias|caller|jobs|disown|times|dirs|pushd|popd|help|history)$'
CENSUS_LOOKUP='^(which)$'
masked_text() {   # <bash file>: the text with quoted bytes and comments masked quote-aware (the section comment), one output line per input line, byte for byte (LC_ALL=C), a case pattern's closing ) written as the byte 001
    if [ ! -f "$TEST_DIR/mask.awk" ]; then
        cat > "$TEST_DIR/mask.awk" <<'AWK'
BEGIN { depth = 0; st[0] = "code"; par[0] = 0 }
{
    line = $0; out = ""; n = length(line); i = 1; prev = " "
    while (i <= n) {
        c = substr(line, i, 1); c2 = substr(line, i, 2); s = st[depth]
        if (s == "code" || s == "bq") {
            if (c == "\\") { out = out c substr(line, i + 1, 1); i += 2; prev = "x"; continue }
            if (c == "#" && (i == 1 || prev ~ /[ \t;]/)) { out = out sprintf("%" (n - i + 1) "s", ""); break }
            if (c == "`") { if (s == "bq") depth--; else { depth++; st[depth] = "bq"; par[depth] = 0 }; out = out c; i++; prev = c; continue }
            if (c2 == "$'") { depth++; st[depth] = "ansi"; out = out c2; i += 2; prev = "'"; continue }
            if (c == "'") { depth++; st[depth] = "sq"; out = out c; i++; prev = c; continue }
            if (c == "\"") { depth++; st[depth] = "dq"; out = out c; i++; prev = c; continue }
            if (c2 == "$(") { depth++; st[depth] = "code"; par[depth] = 0; out = out c2; i += 2; prev = "("; continue }
            if (c == "(") { par[depth]++; out = out c; i++; prev = c; continue }
            if (c == ")") {
                if (par[depth] > 0) par[depth]--
                else if (depth > 0 && s == "code") depth--
                else if (depth == 0) { out = out "\001"; i++; prev = c; continue }   # no ( open: a case pattern's close
                out = out c; i++; prev = c; continue
            }
            out = out c; prev = c; i++; continue
        }
        if (s == "sq") { if (c == "'") { depth--; out = out c } else out = out "."; i++; prev = c; continue }
        if (s == "ansi") {
            if (c == "\\") { out = out ".."; i += 2; continue }
            if (c == "'") { depth--; out = out c } else out = out "."
            i++; prev = c; continue
        }
        if (s == "dq") {
            if (c == "\\") { out = out ".."; i += 2; continue }
            if (c == "\"") { depth--; out = out c; i++; prev = c; continue }
            if (c2 == "$(") { depth++; st[depth] = "code"; par[depth] = 0; out = out c2; i += 2; prev = "("; continue }
            if (c == "`") { depth++; st[depth] = "bq"; par[depth] = 0; out = out c; i++; prev = c; continue }
            out = out "."; i++; prev = c; continue
        }
    }
    print out
}
AWK
    fi
    LC_ALL=C awk -f "$TEST_DIR/mask.awk" "$1"
}
census_records() {   # <bash file> <mode: tools, vars or calls> [<word regex, for calls>]: the file's simple commands as records, one per line (the splitter below reads the masked text and the raw text side by side)
    local tmp
    if [ ! -f "$TEST_DIR/split.awk" ]; then
        cat > "$TEST_DIR/split.awk" <<'AWK'
# Splits each masked line at the operators (||, &&, |, |&, a lone &, ;), the substitutions' and subshells' parentheses, the
# backtick, a brace that opens no ${, a case pattern's close (the byte 001) and, on a line holding a judged_read call, its
# first " -- ", and prints one record per simple command: the line number, the start, the flags (P a case pattern, A
# arithmetic, R an array literal's elements, T the tagged command after a call's --), the token that ends it, whether its
# last word touches that token, then each word masked and RAW, read back from the raw text at the same offset (masking
# keeps every byte's place), unit-separated. mode tools keeps a record with a reading tool's word in its raw words, each
# word tested unquoted (a copy with its quote and backslash characters removed, so a word whose quoting or escaping
# splits the tool's name, gi\t, g''it or "g"it, is kept), not T; vars one with a $ in its raw words or ending at a
# substitution, not P, A, R or T; calls one with a tool's word (tested the same way) or a word matching names.
BEGIN { US = sprintf("%c", 31); toolre = "(^|[^A-Za-z0-9_.-])(" tools ")([^A-Za-z0-9_.-]|$)" }
function top() { return sp > 0 ? stk[sp] : "" }
function ctxflag(   t) { t = top(); return (t == "A" || t == "a") ? "A" : (t == "R" ? "R" : "") }
function endseg(pos, tok,   k) {
    ns++; sst[ns] = start; slen[ns] = pos - start; stok[ns] = tok; sfl[ns] = cur
    if (tok == "pat") { sfl[ns] = sfl[ns] "P"; for (k = ns - 1; k >= 1 && stok[k] == "|"; k--) sfl[k] = sfl[k] "P" }
}
function emit(k,   s, L, ms, rs, j, ws, w, x, y, out, tool, dol, fn, touch) {
    s = sst[k]; L = slen[k]; ms = substr(m, s, L); rs = substr(r, s, L)
    touch = (L > 0 && substr(ms, L, 1) !~ /[ \t]/) ? 1 : 0
    out = ""; tool = 0; dol = 0; fn = 0; j = 1
    while (j <= L) {
        while (j <= L && substr(ms, j, 1) ~ /[ \t]/) j++
        if (j > L) break
        ws = j; while (j <= L && substr(ms, j, 1) !~ /[ \t]/) j++
        w = substr(ms, ws, j - ws); x = substr(rs, ws, j - ws)
        out = out US w US x
        y = x; gsub(/["'\\]/, "", y); if (y ~ toolre) tool = 1   # the word unquoted: gi\t, g''it and "g"it run git
        if (x ~ /\$/) dol = 1
        if (names != "" && x ~ names) fn = 1
    }
    if (mode == "tools" && (index(sfl[k], "T") || !tool)) return
    if (mode == "vars" && (sfl[k] ~ /[APRT]/ || (!dol && stok[k] != "$(" && stok[k] != "`"))) return
    if (mode == "calls" && !tool && !fn) return
    printf "%d%s%d%s%s%s%s%s%d%s\n", NR, US, s, US, sfl[k], US, stok[k], US, touch, out
}
{
    m = $0; r = ""; if ((getline r < rawf) <= 0) r = ""
    n = length(m); ns = 0; sp = 0; start = 1; cur = ""; jd = 0
    if (m ~ /(^|[ \t!&|;(])judged_read[ \t]/) jd = index(m, " -- ")
    i = 1
    while (i <= n) {
        c = substr(m, i, 1); c2 = substr(m, i, 2); L = 0
        if (jd && i == jd) { endseg(i, "--"); i += 4; start = i; cur = ctxflag() "T"; continue }
        if (c == "\\") { i += 2; continue }
        if (substr(m, i, 3) == "$((") { tok = "$(("; L = 3; stk[++sp] = "A" }
        else if (c2 == "((") { tok = c2; L = 2; stk[++sp] = "A" }
        else if (c2 == "$(" || c2 == "<(" || c2 == ">(") { tok = c2; L = 2; stk[++sp] = "C" }
        else if (c2 == "||" || c2 == "&&" || c2 == "|&") { tok = c2; L = 2 }
        else if (c == "|" || c == ";" || c == "`") { tok = c; L = 1 }
        else if (c == "&") { if (substr(m, i - 1, 1) !~ /[<>]/ && substr(m, i + 1, 1) != ">") { tok = c; L = 1 } }
        else if (c == "(") { tok = c; L = 1; stk[++sp] = (substr(m, i - 1, 1) == "=") ? "R" : ((top() == "A" || top() == "a") ? "a" : "P") }
        else if (c == ")") { tok = c; L = 1; if (top() == "A" && substr(m, i + 1, 1) == ")") L = 2; if (sp > 0) sp-- }
        else if (c == "\001") { tok = "pat"; L = 1 }
        else if ((c == "{" || c == "}") && substr(m, i - 1, 1) != "$") { tok = c; L = 1 }
        if (L) { endseg(i, tok); i += L; start = i; cur = ctxflag(); continue }
        i++
    }
    endseg(n + 1, "eol")
    for (k = 1; k <= ns; k++) emit(k)
}
AWK
    fi
    tmp=$(mktemp "$TEST_DIR/census.XXXXXX")
    masked_text "$1" > "$tmp"
    LC_ALL=C awk -v rawf="$1" -v tools="$CENSUS_TOOLS" -v mode="$2" -v names="${3:-}" -f "$TEST_DIR/split.awk" "$tmp"
    rm -f "$tmp"
}
census_rec() {   # <record fields...>: sets ln, fl, et, touch, mw and rw (the words masked and raw), the caller's
    ln=$1; fl=$3; et=$4; touch=$5
    shift 5
    mw=(); rw=()
    while [ $# -gt 1 ]; do mw+=("$1"); rw+=("$2"); shift 2; done
}
census_unquote() {   # <raw word>: sets u, the caller's, to the word with its quotes and backslashes removed ($'' and $"" read as quotes)
    u=${1//\$\'/\'}; u=${u//\$\"/\"}; u=${u//[\"\'\\]/}
}
census_functions() {   # fills fstart and fend, the caller's, from orig, the caller's: each function's header line to the first line that is exactly }
    local i j name
    for ((i = 0; i < ${#orig[@]}; i++)); do
        if [[ "${orig[i]}" =~ ^([a-zA-Z_][a-zA-Z0-9_]*)\(\)\ \{ ]]; then
            name=${BASH_REMATCH[1]}; fstart[$name]=$i; fend[$name]=$i
            for ((j = i + 1; j < ${#orig[@]}; j++)); do if [ "${orig[j]}" = "}" ]; then fend[$name]=$j; break; fi; done
        fi
    done
}
census_command() {   # reads mw and rw (a record's words), fl, et and touch, and fstart, the caller's; sets cmd (the reading tool the simple command runs, one of CENSUS_TOOLS, or empty), word (its command word read back RAW and unquoted, or $( for a substitution), rword (that word raw) and wkind (none, lookup, builtin, tool, judged, function, var or unknown)
    local k=0 n=${#mw[@]} t p o b j u
    cmd=""; word=""; rword=""; wkind=none
    while [ "$k" -lt "$n" ]; do                                 # past the keywords, the command prefixes and their option words, the assignments and the redirections
        t=${mw[k]}
        if [[ "$t" =~ $CENSUS_PREFIX ]]; then
            p=$t; k=$((k + 1))
            case "$p" in case|for|select) return 0 ;; esac     # a case subject, a loop's variable and list: no command
            if [ "$p" = command ] && [[ "${mw[k]:-}" =~ ^-[pvV]*[vV][pvV]*$ ]]; then wkind=lookup; return 0; fi   # command -v or -V: a lookup that runs nothing
            while [ "$k" -lt "$n" ] && [[ "${mw[k]}" == -* ]]; do   # a prefix's option words (env -i, command -p, nice -n 19): the operand of nice -n and env -u goes with its option
                o=${mw[k]}; k=$((k + 1))
                if { [ "$p" = nice ] && [ "$o" = -n ]; } || { [ "$p" = env ] && [ "$o" = -u ]; }; then k=$((k + 1)); fi
            done
            continue
        fi
        if [[ "$t" =~ ^[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])?\+?= ]]; then k=$((k + 1)); continue; fi
        if [[ "$t" =~ ^([0-9]*(\<|\>|\>\>|\<\<\<|\<\<-?|\<\>|\>\||\<\&|\>\&)|\&\>\>?)$ ]]; then k=$((k + 2)); continue; fi   # a redirection operator standing alone: its operand is the next word
        if [[ "$t" =~ ^[0-9]*[\<\>] ]] || [[ "$t" =~ ^\&\> ]]; then k=$((k + 1)); continue; fi
        break
    done
    if [ "$k" -ge "$n" ]; then                                  # no word left: a substitution the command ends at stands as its command word when nothing touches it
        if [ "$k" -eq "$n" ] && { [ "$et" = '$(' ] || [ "$et" = '`' ]; } && { [ "$n" -eq 0 ] || [ "$touch" -eq 0 ]; }; then word='$('; wkind=var; fi
        return 0
    fi
    rword=${rw[k]}
    if [ "${mw[k]:0:1}" = . ] && [ "${rword:0:1}" != . ]; then return 0; fi   # a word that starts inside a string opened on an earlier line: no command word
    census_unquote "$rword"                                     # the command word read back RAW: "git", 'git' and \git run git, which the masked text hides
    if [ -z "$u" ]; then                                        # quotes alone, then a substitution: "$(...)" as the command word
        if [ "$k" -eq $((n - 1)) ] && [ "$touch" -eq 1 ] && { [ "$et" = '$(' ] || [ "$et" = '`' ]; }; then word='$('; wkind=var; fi
        return 0
    fi
    word=$u; b=${u##*/}                                         # by its basename: /usr/bin/git runs git
    [[ "$u" != \$* ]] || wkind=var                              # a parameter expansion or a substitution
    if [[ "$b" =~ $CENSUS_BUILTIN ]]; then [ "$wkind" = var ] || wkind=builtin; return 0; fi   # a builtin's arguments are not commands
    if [[ "$b" =~ $CENSUS_LOOKUP ]]; then [ "$wkind" = var ] || wkind=lookup; return 0; fi
    if [[ "$b" =~ ^($CENSUS_TOOLS)$ ]]; then cmd=$b; [ "$wkind" = var ] || wkind=tool; return 0; fi
    if [ "$wkind" != var ] && [ "$b" = judged_read ]; then wkind=judged; return 0; fi
    if [ "$wkind" != var ] && [ -n "$b" ] && [ -n "${fstart[$b]:-}" ]; then wkind=function; return 0; fi
    [ "$wkind" = var ] || wkind=unknown
    # A command word the census does not know counts as a read of any reading tool's word later in its simple command
    # (fail-closed: a wrapper such as timeout, nohup or setsid runs its operand); a case pattern, arithmetic and an
    # array literal's elements run nothing.
    case "$fl" in *[APR]*) return 0 ;; esac
    for ((j = k + 1; j < n; j++)); do
        t=${mw[j]}
        if [[ "$t" =~ ^([0-9]*(\<|\>|\>\>|\<\<\<|\<\<-?|\<\>|\>\||\<\&|\>\&)|\&\>\>?)$ ]]; then j=$((j + 1)); continue; fi
        if [[ "$t" =~ ^[0-9]*[\<\>] ]] || [[ "$t" =~ ^\&\> ]]; then continue; fi
        if [ "${t:0:1}" = . ] && [ "${rw[j]:0:1}" != . ]; then continue; fi
        census_unquote "${rw[j]}"; b=${u##*/}
        if [[ "$b" =~ ^($CENSUS_TOOLS)$ ]]; then cmd=$b; return 0; fi
    done
    return 0
}
undeclared_reads() {   # <hook text>: prints "undeclared: <line>:<text>" per command line the census finds declared by nothing, "declared: <body|array|marker> <line> <function or ->: <tools>" per command line it finds declared outside a judged_read call, "swallowed: ..." per `|| true` or `|| :` inside a body passed whole, and one "census: ..." line of counts; run under `run`
    local -a orig masked mw rw rec
    local -A fstart fend passed inpassed found_at
    local i name m rest after w f s found cmd word rword wkind u ln fl et touch calls=0 total=0 body=0 array=0 marker=0 undeclared=0 swallowed=0
    mapfile -t orig < "$1"
    mapfile -t masked < <(masked_text "$1")
    [ "${#orig[@]}" -eq "${#masked[@]}" ] || { echo "census: the masking changed the line count"; return 1; }
    census_functions
    for ((i = 0; i < ${#orig[@]}; i++)); do                    # the functions passed whole: the first word after the -- of a call, when a function defined here
        m=${masked[i]}
        [[ "$m" =~ (^|[[:space:]!\&\|\;\(])judged_read[[:space:]] ]] || continue
        calls=$((calls + 1))
        rest=${m#*judged_read}
        [[ "$rest" == *" -- "* ]] || continue
        after=${rest#* -- }; after=${after#"${after%%[![:space:]]*}"}
        w=${after%%[[:space:]]*}
        if [ -n "${fstart[$w]:-}" ]; then passed[$w]=1; fi
    done
    for f in "${!passed[@]}"; do
        for ((i = fstart[$f]; i <= fend[$f]; i++)); do
            inpassed[$i]=$f
            if [[ "${masked[i]}" =~ \|\|[[:space:]]*(true|:)([[:space:]]|$) ]]; then echo "swallowed: $((i + 1)):${orig[i]}"; swallowed=$((swallowed + 1)); fi
        done
    done
    # Each simple command the splitter finds with a reading tool's word in its raw words (a call's tagged command, the
    # read the tags judge, set aside): the tool it runs, by census_command.
    while IFS=$'\x1f' read -r -a rec; do
        census_rec "${rec[@]}"
        census_command
        [ -z "$cmd" ] || found_at[$ln]="${found_at[$ln]:-} $cmd"
    done < <(census_records "$1" tools)
    for ((i = 0; i < ${#orig[@]}; i++)); do
        found=${found_at[$((i + 1))]:-}
        [ -n "$found" ] || continue
        found=${found# }
        m=${masked[i]}
        total=$((total + 1))
        f=""; for name in "${!fstart[@]}"; do if [ "$i" -ge "${fstart[$name]}" ] && [ "$i" -le "${fend[$name]}" ]; then f=$name; break; fi; done
        if [ -n "${inpassed[$i]:-}" ]; then body=$((body + 1)); echo "declared: body $((i + 1)) ${inpassed[$i]}: $found"; continue; fi
        if [[ "$m" =~ ^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*\+?=\( ]]; then array=$((array + 1)); echo "declared: array $((i + 1)) ${f:--}: $found"; continue; fi
        if [[ "${orig[i]}" == *"#"*"outside judged_read"* ]]; then marker=$((marker + 1)); echo "declared: marker $((i + 1)) ${f:--}: $found"; continue; fi
        s=$i; while [ "$s" -gt 0 ] && [[ "${orig[s - 1]}" == *\\ ]]; do s=$((s - 1)); done          # the statement's first line
        if census_block_above_has_marker "$s"; then marker=$((marker + 1)); echo "declared: marker $((i + 1)) ${f:--}: $found"; continue; fi
        if [ -n "$f" ] && { census_block_above_has_marker "${fstart[$f]}" || [[ "${orig[fstart[$f]]}" == *"#"*"outside judged_read"* ]]; }; then marker=$((marker + 1)); echo "declared: marker $((i + 1)) $f: $found"; continue; fi
        undeclared=$((undeclared + 1))
        echo "undeclared: $((i + 1)):${orig[i]}"
    done
    echo "census: calls=$calls passed=$(printf '%s\n' "${!passed[@]}" | sort | tr '\n' ',') lines=$total body=$body array=$array marker=$marker swallowed=$swallowed undeclared=$undeclared"
    return 0
}
census_block_above_has_marker() {   # <index>: the contiguous comment lines directly above that line carry the marker; reads orig, the caller's
    local i=$1
    while [ "$i" -gt 0 ]; do
        i=$((i - 1))
        [[ "${orig[i]}" =~ ^[[:space:]]*# ]] || return 1
        [[ "${orig[i]}" == *"outside judged_read"* ]] && return 0
    done
    return 1
}
CENSUS_LOOKUP_KEPT='gl="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"'
census_unread_shapes() {   # <bash file>: prints "<line>:<text>" once for each line of the comment-stripped RAW text holding a shape the census cannot read (the bound above)
    local -a orig stripped mw rw rec
    local -A fstart fend hit
    local n text t ln fl et touch cmd word rword wkind u re
    mapfile -t orig < "$1"
    mapfile -t stripped < <(sed -E 's/[[:space:]]+#.*$//' "$1")
    census_functions
    re="(^|[^A-Za-z0-9_-])eval([^A-Za-z0-9_-]|\$)"                                                                            # an eval
    re="$re|\\\$\{[A-Za-z_][A-Za-z0-9_]*:?[-=+?]([^}[:space:]]*/)?($CENSUS_TOOLS)([^A-Za-z0-9_.-]|\$)"                      # a default naming a reading tool, by a path or not
    re="$re|(^|[^A-Za-z0-9_\$])[A-Za-z_][A-Za-z0-9_]*=[\"']?([^[:space:]\"';|&()]*/)?($CENSUS_TOOLS)[\"']?([[:space:];)&|]|\$)"   # a variable assigned a reading tool's name or path
    re="$re|(\\\$\(|\`)[[:space:]]*(command[[:space:]]+-[pvV]*[vV][pvV]*|type([[:space:]]+-[A-Za-z]+)*|which)[[:space:]]+([^)\`]*[[:space:]/])?($CENSUS_TOOLS)([^A-Za-z0-9_.-]|\$)"   # a lookup answering a reading tool's path
    re="$re|(^|[^<])<<([^<]|\$)"                                                                                             # a here-doc
    re="$re|(^|[^A-Za-z0-9_-])trap[[:space:]](.*[^A-Za-z0-9_.-])?($CENSUS_TOOLS)([^A-Za-z0-9_.-]|\$)"                         # a trap action holding a reading tool's word
    re="$re|(^|[;&|({[:space:]])(source|\\.)[[:space:]]+[\"']?(<\(|\\\$\(|\`)"                                                 # source or . of a substitution
    re="$re|(^|[^A-Za-z0-9_.-])(bash|sh)([[:space:]]+-[-A-Za-z]+)*[[:space:]]+-[A-Za-z]*c[A-Za-z]*([[:space:]]|\$)"             # bash -c or sh -c
    while IFS= read -r t; do                                    # the shapes found in the text, the scanner's own lookup excepted by its exact text
        n=${t%%:*}; text=${t#*:}
        [ "${text#"${text%%[![:space:]]*}"}" = "$CENSUS_LOOKUP_KEPT" ] || hit[$n]=1
    done < <(printf '%s\n' "${stripped[@]}" | sed -E 's/^[[:space:]]*#.*$//' | grep -nE -- "$re" || true)
    while IFS=$'\x1f' read -r -a rec; do                        # a command word that begins with a parameter expansion or a substitution: one of the three the bound names
        census_rec "${rec[@]}"
        census_command
        [ "$wkind" = var ] || continue
        case "$rword" in '"$@"'|'"$detail"'|'"$gl"') continue ;; esac
        hit[$ln]=1
    done < <(census_records "$1" vars)
    for n in $(printf '%s\n' "${!hit[@]}" | sort -n); do echo "$n:${stripped[n - 1]}"; done
    return 0
}

@test "every read of the hook is DECLARED (the population half of case 174's guarantee): a census over the hook's text finds no command line running a reading tool that is not a judged_read call, inside a function the helper is handed whole, an array literal or under an outside-judged_read marker; the census flags a planted read in a copy, the double-quoted substitution spelling and a grep over captured content included, and passes a planted marker, an array literal and tool words inside a string" {
    run undeclared_reads "$HOOK"
    [ "$status" -eq 0 ]
    [[ "$output" != *"undeclared: "* ]]
    # the census read the hook: the call sites are many, and the functions the helper is handed whole are derived from them
    # (the joins, the diff and the byte judge among them), so a regex matching nothing cannot pass the line above for the wrong reason
    census="${output##*$'\n'}"
    [[ "$census" == "census: calls="* ]]
    [ "${census#*calls=}" != "$census" ] && [ "$(sed -E 's/.*calls=([0-9]+).*/\1/' <<< "$census")" -gt 40 ]
    [[ "$census" == *"passed="*"added_lines,"* ]]
    [[ "$census" == *"passed="*"byte_counts,"* ]]
    [[ "$census" == *"passed="*"join_candidates,"* ]]
    [[ "$census" == *"passed="*"tip_candidates,"* ]]
    [ "$(sed -E 's/.*lines=([0-9]+).*/\1/' <<< "$census")" -ge 20 ]          # command lines the census judged (each declared by one of the four ways)
    [ "$(sed -E 's/.*body=([0-9]+).*/\1/' <<< "$census")" -ge 10 ]
    [ "$(sed -E 's/.*marker=([0-9]+).*/\1/' <<< "$census")" -ge 8 ]
    [ "$(sed -E 's/.*array=([0-9]+).*/\1/' <<< "$census")" -eq 0 ]          # since round 9d no array literal of the hook names a tool (gitleaks_args' list begins with dir); the class stays read, pinned on plant-e below
    # the bound the passed-whole rule rests on: a body handed to the helper reaches it through pipefail, so a `|| true` or
    # `|| :` inside one would hide a stage's status from the set; none is there, and the census names any that appears
    [[ "$output" != *"swallowed: "* ]]
    [[ "$census" == *"swallowed=0 "* ]]
    # the census's own sensitivity, executed over planted copies (the first line is the shebang; the plant is line 2)
    sed '1a x=$(git rev-parse HEAD 2>/dev/null || true)' "$HOOK" > "$TEST_DIR/plant-a.sh"                    # the plain substitution
    run undeclared_reads "$TEST_DIR/plant-a.sh"
    [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 1 ]
    [[ "$output" == *'undeclared: 2:x=$(git rev-parse HEAD 2>/dev/null || true)'* ]]
    sed '1a tipname="$(git rev-parse --short HEAD 2>/dev/null || true)"' "$HOOK" > "$TEST_DIR/plant-b.sh"    # the spelling the hook uses: the substitution inside double quotes stays visible
    run undeclared_reads "$TEST_DIR/plant-b.sh"
    [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 1 ]
    [[ "$output" == *'undeclared: 2:tipname="$(git rev-parse --short HEAD 2>/dev/null || true)"'* ]]
    sed '1a hits=$(printf "%s\\n" "$read_out" | grep -c x || true)' "$HOOK" > "$TEST_DIR/plant-c.sh"          # a grep over captured content, the class round 5 reopened
    run undeclared_reads "$TEST_DIR/plant-c.sh"
    [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 1 ]
    [[ "$output" == *'undeclared: 2:hits=$(printf "%s\n" "$read_out" | grep -c x || true)'* ]]
    { sed -n '1p' "$HOOK"; echo '# outside judged_read: a probe of the census'; echo 'tipname="$(git rev-parse --short HEAD 2>/dev/null || true)"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-d.sh"   # the marker above the statement is honoured
    run undeclared_reads "$TEST_DIR/plant-d.sh"
    [[ "$output" != *"undeclared: "* ]]
    { sed -n '1p' "$HOOK"; echo 'msg="run git fsck and grep the log"'; echo 'PROBE_ARGS=(git log -1)'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-e.sh"   # tool words inside a string, and an array-literal assignment line (the exempt form: the assignment starts the line, as the scanner's argument list does), are not commands
    run undeclared_reads "$TEST_DIR/plant-e.sh"
    [[ "$output" != *"undeclared: "* ]]
    [[ "${output##*$'\n'}" == *" array=1 "* ]]                              # the planted array literal is read as one (round 9d: the hook holds none)
    # round 8b (the round 7 rulings' B): the shapes the census read nothing of until then, each planted alone and
    # flagged ONCE: a backtick substitution, bare and inside double quotes (bash runs both); a read past a call's --
    # after || and after ;; a substitution and a backtick nested inside the tagged command's own arguments; a
    # path-qualified and a backslash-escaped command word; the prefixes with option words (env -i, env -u NAME,
    # nice -n 19, command -p). Each was undeclared=0 under the round 8 census.
    local -a plants=(
        'x=`git rev-parse HEAD`'
        'x="`git rev-parse HEAD`"'
        'judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -- true || git rev-parse HEAD'
        'judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -- true; git rev-parse HEAD'
        'judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -- printf "%s\n" "$(git rev-parse HEAD)"'
        'judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -- printf "%s\n" "`git rev-parse HEAD`"'
        '/usr/bin/git rev-parse HEAD'
        '\git rev-parse HEAD'
        'env -i git rev-parse HEAD'
        'env -u HOME git rev-parse HEAD'
        'nice -n 19 git rev-parse HEAD'
        'command -p git rev-parse HEAD'
    )
    local plant k=0
    for plant in "${plants[@]}"; do
        k=$((k + 1))
        { sed -n '1p' "$HOOK"; printf '%s\n' "$plant"; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-b$k.sh"
        run undeclared_reads "$TEST_DIR/plant-b$k.sh"
        [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 1 ]
        [[ "$output" == *"undeclared: 2:$plant"* ]]
    done
    # the backtick a double-quoted string opens is closed by the code branch's backtick, so a read on the next line
    # is still read (a masker that opened it and never closed it hid the rest of the line's string and the lines after)
    { sed -n '1p' "$HOOK"; printf '%s\n' 'x="`git rev-parse HEAD`"' 'git rev-parse HEAD'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-h.sh"
    run undeclared_reads "$TEST_DIR/plant-h.sh"
    [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 2 ]
    [[ "$output" == *"undeclared: 3:git rev-parse HEAD"* ]]
    # command -v and -V are lookups that run nothing (the hook's own command -v gitleaks among them): no read
    { sed -n '1p' "$HOOK"; echo 'command -v git >/dev/null'; echo 'command -V git'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-f.sh"
    run undeclared_reads "$TEST_DIR/plant-f.sh"
    [[ "$output" != *"undeclared: "* ]]
    # the shapes the census cannot read, pinned ABSENT from the hook's comment-stripped raw text: none in the hook,
    # and each spelling found in a planted copy, so the pin is shown to red
    run census_unread_shapes "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    for plant in 'x=$(${GIT:-git} rev-parse HEAD)' 'r=${ROMP_GIT-git}' 'GIT=git; "$GIT" rev-parse HEAD' "tool='grep'" 'eval "git rev-parse HEAD"' 'x=$(eval "$probe")'; do
        { sed -n '1p' "$HOOK"; printf '%s\n' "$plant"; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-g.sh"
        run census_unread_shapes "$TEST_DIR/plant-g.sh"
        [ "$output" = "2:$plant" ]
    done
    # round 9b (the round 8 rulings' F): the shapes the census and its pins read nothing of until then (the round 8
    # refuters' probes: undeclared=0 and no pin line for each at cad898dd2), each planted alone and flagged ONCE, by
    # the census or by the pin and never both. The census reads a redirection operator standing alone ahead of the
    # command word, a quoted command word (read back from the raw text), a command after a lone & and after |&, and a
    # wrapper outside the prefixes (the fail-closed rule; coproc is a keyword)
    local -a census_plants=(
        '< /dev/null git rev-parse HEAD'
        '2> /dev/null git rev-parse HEAD'
        '"git" rev-parse HEAD'
        "'git' rev-parse HEAD"
        ': & git rev-parse HEAD'
        ': |& git rev-parse HEAD'
        'coproc git rev-parse HEAD'
        'timeout 5 git rev-parse HEAD'
        'nohup git rev-parse HEAD'
        'stdbuf -o0 git rev-parse HEAD'
        'ionice -c3 git rev-parse HEAD'
        'setsid git rev-parse HEAD'
        # round 9bc (F.1 (2), the round 9b audit): a command word whose quoting or escaping splits the tool's name, alone
        # and under a wrapper, read since census_records tests each word with its quote and backslash characters
        # removed; each passed the census and its pins at ce33ff8f4 and at cad898dd2, where the raw word was tested
        'gi\t rev-parse HEAD'
        "g''it rev-parse HEAD"
        '"g"it rev-parse HEAD'
        'timeout 5 gi\t rev-parse HEAD'
    )
    k=0
    for plant in "${census_plants[@]}"; do
        k=$((k + 1))
        { sed -n '1p' "$HOOK"; printf '%s\n' "$plant"; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-r9b-c$k.sh"
        run undeclared_reads "$TEST_DIR/plant-r9b-c$k.sh"
        [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 1 ]
        [[ "$output" == *"undeclared: 2:$plant"* ]]
        run census_unread_shapes "$TEST_DIR/plant-r9b-c$k.sh"
        [ -z "$output" ]
    done
    # ... and pins absent a command word held in a variable by a lookup or a path-qualified default, a lookup's answer
    # standing as the command word, a trap action running a reading tool, source or . of a substitution, and bash -c
    local -a pin_plants=(
        'x=$(command -v git)'
        'x=$(type -P git)'
        '$(which git) rev-parse HEAD'
        '"$(command -v git)" rev-parse HEAD'
        # F.2 names ${GIT:-/usr/bin/git} as a command word. Bare, that spelling was flagged already at cad898dd2 (the
        # census's brace split leaves ${GIT:-/usr/bin/git, whose basename is git) and is flagged by both instruments
        # now, so it owes no red; quoted, it passed both at cad898dd2 and is flagged once, by the pin, so the quoted
        # spelling is the plant (round 9bc, the round 9b audit)
        '"${GIT:-/usr/bin/git}" rev-parse HEAD'
        "trap 'git rev-parse HEAD' EXIT"
        "source <(printf '%s\n' 'git rev-parse HEAD')"
        ". <(printf '%s\n' 'git rev-parse HEAD')"
        "bash -c 'git rev-parse HEAD'"
    )
    k=0
    for plant in "${pin_plants[@]}"; do
        k=$((k + 1))
        { sed -n '1p' "$HOOK"; printf '%s\n' "$plant"; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-r9b-p$k.sh"
        run census_unread_shapes "$TEST_DIR/plant-r9b-p$k.sh"
        [ "$output" = "2:$plant" ]
        run undeclared_reads "$TEST_DIR/plant-r9b-p$k.sh"
        [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 0 ]
    done
    # a variable given a reading tool's path and then run as the command word: each line pinned once (the property: a
    # command word that begins with a parameter expansion is one of the three the bound names)
    { sed -n '1p' "$HOOK"; printf '%s\n' 'g=/usr/bin/git' '"$g" rev-parse HEAD'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-r9b-g.sh"
    run census_unread_shapes "$TEST_DIR/plant-r9b-g.sh"
    [ "$output" = $'2:g=/usr/bin/git\n3:"$g" rev-parse HEAD' ]
    run undeclared_reads "$TEST_DIR/plant-r9b-g.sh"
    [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 0 ]
    # a here-doc: its operator pinned, whatever its body holds
    { sed -n '1p' "$HOOK"; printf '%s\n' ": <<'EOF'" 'no read here' 'EOF'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-r9b-h.sh"
    run census_unread_shapes "$TEST_DIR/plant-r9b-h.sh"
    [ "$output" = "2:: <<'EOF'" ]
    run undeclared_reads "$TEST_DIR/plant-r9b-h.sh"
    [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 0 ]
    # the scanner's lookup is excepted by its EXACT text, the line the hook holds (so the exception is live), and the
    # same lookup under another name is pinned
    [ "$(grep -cxF '    gl="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"' "$HOOK")" -eq 1 ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'gx="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-r9b-l.sh"
    run census_unread_shapes "$TEST_DIR/plant-r9b-l.sh"
    [ "$output" = '2:gx="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"' ]
    # round 9bc (F.1 (7), the round 9b audit): the five shapes the bound DISCLOSES, neither read by the census nor
    # pinned absent, each planted alone and passing both unflagged, the census's counts over the copy equal to its
    # counts over the hook, so the disclosure is shown true by execution and no reader takes it for coverage: a
    # variable command word under a wrapper the census does not know, a command word holding an expansion that does
    # not begin it, a command after a string continued from the line before, an ANSI-C quoted word, and env -S with a
    # command string. A change that reads or pins one of them turns its witness red; the witness then moves out of
    # this list, and the shape out of the bound's disclosed list, in the same change.
    local -a disclosed_plants=(
        'timeout 5 "$1" rev-parse HEAD'
        '/usr/bin/$t rev-parse HEAD'
        $'x="a\nb" git rev-parse HEAD'
        "\$'\\x67it' rev-parse HEAD"
        'env -S "git rev-parse HEAD"'
    )
    k=0
    for plant in "${disclosed_plants[@]}"; do
        k=$((k + 1))
        { sed -n '1p' "$HOOK"; printf '%s\n' "$plant"; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-r9bc-w$k.sh"
        [ "$(sed -n '2p' "$TEST_DIR/plant-r9bc-w$k.sh")" = "${plant%%$'\n'*}" ]
        run undeclared_reads "$TEST_DIR/plant-r9bc-w$k.sh"
        [ "$status" -eq 0 ]
        [ "$(grep -c '^undeclared: ' <<< "$output")" -eq 0 ]
        [ "${output##*$'\n'}" = "$census" ]
        run census_unread_shapes "$TEST_DIR/plant-r9bc-w$k.sh"
        [ "$status" -eq 0 ]
        [ -z "$output" ]
    done
}

@test "the join's fourth arm prints a recorded path holding an ampersand, a backslash-ampersand and the text {rc} byte for byte: {rc} is substituted first and the -d rider's answer is spliced by a QUOTED replacement, so patsub_replacement rewrites no & and the answer is not re-scanned for the status (the round 7 text printed a{detail}b&1.txt)" {
    commit_file 'a&b\&{rc}.txt' "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file 'a&b\&{rc}.txt' "remove it"                     # gone at the tip: the blob is the commit's to judge
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -z --no-commit-id --root "$1" | tr "\0" "|"' _ "$sha"
    [[ "$output" == *$'\t''a&b\&{rc}.txt|'* ]]                   # git prints the path raw under -z (after the two counts and a tab): the join records these bytes
    empty_diff_tree_numstat                                      # every numstat answers nothing: the join meets the path with no verdict and writes the short file before its tr runs
    tr_refusing join 2                                           # the tip's candidates join is the first tr of the joins' shape, the commit's the second
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the JOIN of commit ${sha:0:10}'s verdicts could not be made for the BINARY VERDICT check (its pipeline exited 1; the tool's own error line, where it printed one, is above; the join had recorded a&b\&{rc}.txt as a post-image met no verdict for before the pipeline failed)"* ]]
    [[ "$output" != *"{detail}"* ]]                              # the & rewritten to the matched text
    [[ "$output" != *"a&b&"* ]]                                  # the \& rewritten to &
    [[ "$output" != *"1.txt"* ]]                                 # the {rc} in the path rewritten to the status
    [ "$(cat "$TEST_DIR/tr-calls")" -eq 2 ]
}

@test "a hand-made tag object with NO object line (one git cannot peel: rev-list exits 128 on the range and on the fallback listing alike), fed on stdin, is refused at status 1 with the report WHOLE: the COMMITS line names git rev-list's status 128, the OBJECT line names the absent field, and the bypass line follows (the round 5 text died at 128 on the fallback's bare substitution, the report cut short after two lines)" {
    commit_file f.txt "plain" "base"
    obj="$(printf 'type commit\ntag odd\ntagger Tester <t@example.invalid> 1700000000 +0000\n\nno object line\n' | git -C "$REPO" hash-object -t tag -w --stdin --literally)"
    run _hook_in "$REPO" -c 'git cat-file -t "$1"' _ "$obj"
    [ "$output" = tag ]
    run _hook_in "$REPO" -c 'git rev-list "$1" --not --remotes; echo "status $?"' _ "$obj"
    [[ "$output" == *"status 128"* ]]                            # the range listing: the fallback runs
    run _hook_in "$REPO" -c 'git rev-list "$1"; echo "status $?"' _ "$obj"
    [[ "$output" == *"status 128"* ]]                            # the fallback listing fails the same way: refused by its set, not the hook's end
    # fed by hand: update-ref refuses a ref to such an object, so no real push can carry it
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< "refs/tags/odd $obj refs/tags/odd $ZERO"
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/tags/odd (${obj:0:10}) could not be listed for the identifier scan (git rev-list exited 128); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"romp pre-push: the OBJECT field of tag refs/tags/odd (${obj:0:10}) is absent (git cat-file -p exited 0 and printed a tag object with no object line) while its type read as tag, which ends the peel here"* ]]
    [[ "$output" == *"could not be listed for the identifier scan"*"the OBJECT field of tag refs/tags/odd"*"git push --no-verify"* ]]   # the report ran on past the listing to the tag's fields and the bypass line
}

grep_answering_then_failing() {   # <bash test over the shim's "$@">: for that shape the real grep runs and prints its answer, then the shim exits 2 in its place; the real grep for every other shape
    local real_grep
    real_grep="$(command -v grep)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then %q "$@"; echo "shim: grep answered, then refused" >&2; exit 2; fi\n' "$1" "$real_grep"
        printf 'exec %q "$@"\n' "$real_grep"
    } > "$TEST_DIR/shim/grep"
    chmod 755 "$TEST_DIR/shim/grep"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "the ENTRY COUNT grep -c over the tip's rewritten listing answering the FULL count and exiting 2 is refused as unscanned naming the read and its status, through a real push of a clean tip: the count agrees with the symlink pass, so the expected set alone refuses it (the eighth grep read, the fifth shim shape, -c; a set widened to 2 publishes with nothing printed), and the remote stays at the base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file clean.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    grep_answering_then_failing '[ "${1:-}" = -c ] && [[ "${2:-}" == "^[0-7]"* ]] && [[ "${3:-}" == *"/listing.nl" ]]'   # the ENTRY COUNT's shape alone (grep -c <the whole-entry pattern> <scratch>/listing.nl, since round 8b3): the FILE COUNT carries -E, the LINE COUNT reads read.nl
    printf '100644 blob 0123abcd       5\ta\n100644 blob 4567cdef       5\tb\n' > "$TEST_DIR/listing.nl"
    run _hook_in "$REPO" -c 'grep -c "^[0-7]\{6\} [a-z][a-z]* [0-9a-f][0-9a-f]*  *[-0-9][0-9]*"$'"'"'\t'"'"' "$1/listing.nl"; echo "status $?"' _ "$TEST_DIR"
    [[ "$output" == "2"$'\n'*"status 2"* ]]                     # the answer in full, then the status 2
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) could not be counted for the BINARY VERDICT check (grep -c exited 2); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"not two counts"* ]]                        # the digit check's cause: the answer was a count
    [[ "$output" != *"listed short or long"* ]]                  # the comparison's cause: the count agreed
    [[ "$output" != *"grep -c over"* ]]                          # the candidates gate's two count reads are not met by the shim
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "an annotated TAG stamped under a banned domain beside the failed chosen-addresses read is refused with the tag's address line leading with the failed read, through a real push: whether the clone chose the address could not be read, so the line says that and not that the clone is not configured to use it, and the remote never gets the tag" {
    add_remote
    commit_file f.txt "plain" "base"
    GIT_COMMITTER_EMAIL=dev@zzsynthuser.example git -C "$REPO" tag -a v1 -m "a release"    # the tagger is the committer identity
    sha="$(git -C "$REPO" rev-parse refs/tags/v1)"
    run _hook_in "$REPO" -c 'git cat-file -p "$1" | grep "^tagger "' _ "$sha"
    [[ "$output" == *"<dev@zzsynthuser.example>"* ]]
    fail_config_user_email
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDRESSES this clone is configured to use could not be read (git config --get-all user.email exited 128), so whether a stamped address is one it chose is unknown; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"romp pre-push: tag refs/tags/v1 (${sha:0:10}) is tagged as <dev@zzsynthuser.example>: whether this clone is configured to use that address could not be read (git config --get-all user.email exited 128, refused above), and its domain carries a personal identifier"* ]]
    [[ "$output" != *"not configured to use, whose domain"* ]]  # the round 7 text's cause, which the failed read cannot establish
    # the remedy paragraphs (round 8b, flag 80, the tag's arm): the failed read and its repair lead, each paragraph's
    # general rule stays, and the remedies whose causes the failed read leaves unknown (the say-so line, the bullets,
    # re-creating the tag under the configured address) are absent
    [[ "$output" == *"  The addresses this clone is configured to use could not be read (git config --get-all user.email exited 128, refused above), so whether it chose each address named is unknown: run git config --get-all user.email yourself to see git's own error, repair that read and push again; configuring an address changes nothing until then."* ]]
    [[ "$output" == *"  An annotated TAG's tagger and message are the tag object's own."$'\n'* ]]
    [[ "$output" != *"say so (git config --global user.email"* ]]
    [[ "$output" != *"re-create it under your configured address"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

# ── round 8: the exit-0 empty-or-short answer at the reads round 7 found open ──
# Round 7's refuters (2026-09-23) drove five more reads with a git exiting 0
# and printing nothing, or answering short, each through a real push that
# published: the ADDED LINES diff's git stage (a silent diff-tree -p read as a
# commit adding no line, where case 199's shim silenced the awk: a banned line
# in a one-parent middle commit published), the log.showRoot configuration
# read (retired in round 9; it ran before the ref list was read and inherited the hook's stdin,
# so a git draining stdin there emptied the list and every ref published), the
# SYMLINK listing (a git silent on ls-tree in both its shapes over a tip whose
# tree held a symlink alone passed the tip, both listings agreeing on zero
# entries and the grep's read list empty for a tree with no regular file with
# bytes), the tag OBJECT capture (a header-only answer parsed as a tag with no
# message: pre-push-message.bats) and the CHOSEN ADDRESS match (a grep -q
# silent with exit 0 made every stamped address chosen: pre-push-identity.bats).
# Each read holds a sibling fact now: the diff leads with the commit's own sha
# (--always) and its awk records a count only after that line; the ref list is
# read by the shell before any tool runs; an empty listing under exit 0 is
# judged against the tree's size (the empty tree, size 0, is the one tree with
# no entry). The scratch directory is removed from an EXIT trap, so a hook
# ended by bash (a scratch directory it cannot write into: the header's scratch
# paragraph records that every such arm refuses with bash's own line) leaves
# nothing under TMPDIR, where the removal at the end of the identifier scan
# never ran on that road. Cases 208 to 212 below; 208 stands beside 199 in
# purpose (the same read, the other stage).
git_silent_on() {   # <bash test over the shim's "$@">: a git exiting 0 and printing nothing, on either stream, for that argument shape; the real git for every other command
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then exit 0; fi\n' "$1"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
git_draining_stdin_on() {   # <bash test over the shim's "$@">: for that shape a git that reads its stdin (the hook's, inherited) to the end, prints nothing and exits 0 (the round 7 refuters' shim); the real git for every other command
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then cat > /dev/null; exit 0; fi\n' "$1"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
mktemp_making_scratch_unwritable() {   # a mktemp that makes the scratch directory as the real one does and takes its write bit away (mode 500), so the hook's first write there fails with bash's own line
    local real_mktemp
    real_mktemp="$(command -v mktemp)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'real_mktemp=%q\n' "$real_mktemp"
        cat <<'SHIM'
d=$("$real_mktemp" "$@") || exit $?
chmod 500 "$d"
printf '%s\n' "$d"
SHIM
    } > "$TEST_DIR/shim/mktemp"
    chmod 755 "$TEST_DIR/shim/mktemp"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "the ADDED LINES diff under a git exiting 0 and printing nothing for diff-tree -p (the read's GIT stage; case 199's shim silenced its awk) is refused as unscanned naming the git read and the marker, through a real push of a one-parent middle commit's leak: the diff leads with the commit's own sha (--always) and its awk records a count only after that line, so a silent git is not a commit adding nothing, the awk's own arm is not the cause named, and the remote stays at the base (the round 7 text published the leak with nothing printed)" {
    leak_in_middle_commit_after_base
    git_silent_on 'case " $* " in " diff-tree -p "*) true ;; *) false ;; esac'   # the added-lines diff's shape (diff-tree -p first): the changed-paths listing and the numstats carry -r first, and this push has no merge for the combined-patch read
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --always --no-color "$1"; echo "status $?"' _ "$leak"
    [ "$output" = "status 0" ]                                # nothing printed, not even the marker line the real git prints first
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat --root --no-commit-id "$1"' _ "$leak"
    [[ "$output" == *"leak.txt"* ]]                            # the other diff-tree shapes reach the real git
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${leak:0:10} could not be read (git diff-tree exited 0 and printed no line naming the commit, the marker --always asks for ahead of the diff, so the read answered short); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"recorded \"\""* ]]                        # the awk ran and recorded the missing marker: case 199's arm (the awk that never ran) is not the cause named
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"could not be grepped"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
}

@test "the controls for the marker: an EMPTY commit and a merge with no line of its own pass with nothing printed (the real diff prints the commit's sha alone, so the marker is seen and the count is zero, where --no-commit-id printed nothing for either), and a one-parent commit's added line is still named past the marker" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" commit -q --allow-empty -m "an empty commit"
    empty="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side "$BASE"
    commit_file side.txt "the side's work" "side"
    git -C "$REPO" checkout -q main
    git -C "$REPO" merge -q --no-ff -m "merge side" side
    merge="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --always --no-color "$1"' _ "$empty"
    [ "$output" = "$empty" ]                                  # the sha alone
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --always --no-color "$1"' _ "$merge"
    [ "$output" = "$merge" ]                                  # a merge with no line of its own: the sha alone too
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$merge"
    [ -z "$output" ]                                          # the round 7 text's command printed nothing here, the same as a silent git
    run_hook "$BASE"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"commit ${leak:0:10} ADDS a personal identifier in:"* ]]
    [[ "$output" == *"leak.txt"* ]]
    [[ "$output" != *"could not be read"* ]]
}

@test "the REPLACE REFS listing, the first tool the hook runs after reading the ref list, under a git that DRAINS the hook's stdin for that one read (exit 0, nothing printed, the ref list read to its end) changes nothing: the ref list is read by the shell before any tool runs, so a tip carrying a banned string is refused through a real push and the remote holds nothing (the round 7 text ran a configuration read first, and every ref of the push published with nothing printed; re-aimed in round 9, when that read, of log.showRoot, was retired)" {
    add_remote
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_draining_stdin_on '[ "${1:-}" = for-each-ref ] && [ "${3:-}" = refs/replace/ ]'   # refuse_replace_refs' listing; the listing's remote-refs read carries --contains
    run _hook_in "$REPO" -c 'printf "a line for whoever reads next\n" | { git for-each-ref --format="%(refname)" refs/replace/; echo "status $?"; cat; }'
    [ "$output" = "status 0" ]                                # the shim took the line, printed nothing and exited 0: the cat after it found stdin empty
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"the tip of refs/heads/main (${sha:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"leak.txt"* ]]
    [[ "$output" == *"BLOCKED"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "a git silent on ls-tree in BOTH its shapes (the symlink pass's plain listing and the verdict check's -z listing) over a tip whose tree holds a symlink alone, inherited from a commit the remote holds, is refused as unscanned naming the listing and the tree's SIZE, through a real push: both listings agreed on zero entries and the grep's read list was empty for a tree with no regular file with bytes, so the tree's size is the fact that shows the listing short, and the remote never gets the branch (the round 7 text published it with nothing printed); an EMPTY-TREE tip, size 0, passes under the same shim" {
    add_remote
    ln -s /home/zzsynthuser/code/romp/vscode-extension/node_modules "$REPO/node_modules"
    git -C "$REPO" add node_modules
    git -C "$REPO" commit -qm "a symlink alone"
    git -C "$REPO" push -q origin main                        # the remote holds the link: the tip half alone can name it
    git -C "$REPO" checkout -q -b feature
    : > "$REPO/empty.txt"
    git -C "$REPO" add empty.txt
    git -C "$REPO" commit -qm "an empty file"                 # the tip's tree: the link and a regular file of no bytes, which the grep never lists as read
    sha="$(git -C "$REPO" rev-parse HEAD)"
    size="$(git -C "$REPO" cat-file -s "$sha^{tree}")"
    [ "$size" -gt 0 ]
    run _hook_in "$REPO" -c 'git grep --no-color -I -l -z -e "" "$1" --; echo "status $?"' _ "$sha"
    [ "$output" = "status 1" ]                                # the read list is empty (nothing printed, exit 1): no regular file with bytes
    git_silent_on '[ "${1:-}" = ls-tree ]'
    run _hook_in "$REPO" -c 'git ls-tree -r "$1"; echo "status $?"; git ls-tree -r -z -l "$1"; echo "status $?"' _ "$sha"
    [ "$output" = "status 0"$'\n'"status 0" ]                 # both shapes silent
    push_ref_through_hook_with_shim refs/heads/feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/feature (${sha:0:10}) was listed as empty (git ls-tree -r exited 0 and printed no entry) while git cat-file -s gives its tree's size as $size bytes, so either the listing answered short or the tree holds only empty directories, which git's own index never writes; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"SYMLINK TARGET"* ]]                     # no link was listed, so none was read
    [[ "$output" != *"listed short or long"* ]]               # the two listings agreed on zero: the entry count refuses nothing here
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
    # the control: a tip over the EMPTY tree (size 0) passes under the same silent shim, since an empty listing is that tree's own answer
    git -C "$REPO" checkout -q --orphan bare
    git -C "$REPO" rm -rq --cached .
    rm -f "$REPO/node_modules" "$REPO/empty.txt"
    git -C "$REPO" commit -q --allow-empty -m "the empty tree"
    bare="$(git -C "$REPO" rev-parse HEAD)"
    [ "$(git -C "$REPO" cat-file -s "$bare^{tree}")" = 0 ]
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< "refs/heads/bare $bare refs/heads/bare $ZERO"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "a scratch directory the hook cannot WRITE into (mode 500, from a mktemp shim) ends the hook at its first write under set -e with bash's own line and no romp line, the push refused and the remote at the base (the shape the header's scratch paragraph records), and the directory is GONE afterwards: the removal runs from an EXIT trap, where the round 7 text's removal at the end of the identifier scan never ran on that road and left the directory under TMPDIR" {
    leak_in_middle_commit_after_base
    export TMPDIR="$TEST_DIR/tmp"
    mkdir -p "$TMPDIR"
    mktemp_making_scratch_unwritable
    run _hook_in "$REPO" -c 'd=$(mktemp -d "${TMPDIR:-/tmp}/romp-pre-push.XXXXXX") && { ( : > "$d/x" ) 2>/dev/null && echo writable || echo unwritable; rmdir "$d"; }'
    [ "$output" = unwritable ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"/added.count: Permission denied"* ]]     # bash's own line for the first write (the added-lines count file, emptied before the diff runs), naming the hook's line
    [[ "$output" != *"romp pre-push"* ]]                      # no romp line: the writers stay outside the helper's guard, every arm refusing (the header)
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]
    [ "$(ls -1 "$TMPDIR" | grep -c '^romp-pre-push\.')" -eq 0 ]   # the EXIT trap removed the minted directory (the round 7 text left it)
}

# ── round 8b: every read has a row in tests/pre-push-reads.tsv, and every row is driven through a real push ──
# Round 7's rulings made the population the predicate (A.8): tests/pre-push-reads.tsv holds one row per read
# of the hook, every judged_read call site and every command line the census above finds reading outside
# the helper, each with the sibling fact that shows its answer whole or the reason an empty or cut-short
# exit-0 answer there refuses or publishes nothing, and the case that drives the read with a silent or a
# short tool through a real push. The cases below were round 8b's, for rows it found no earlier case drove
# that way (its audit found 35 rows still undriven; the round 8b2 section at the end of this file drives
# every row, one case each, and the table names those): each puts a
# tool first on the hook's PATH that, for ONE read's shape, exits 0 printing nothing (reading its stdin, as
# the round 7 refuters' shims did) or answers short, pushes for real, and asserts the refusal the row names
# and the remote unchanged. D of the same rulings adds one case per refusal arm the round 7 delta added
# (the FILE COUNT and LINE COUNT greps, the added-lines wc, the three SIZE reads), each shaped like the
# ENTRY COUNT case above and red when that read's expected set is widened, and the witnesses for the three
# own= joins and the scanner log's ERR line. Four cases drive the road found while the rows were written:
# a tool that reads its stdin inside a loop that read its list on stdin took the rest of the list, and a
# second ref, a hidden file and a credential each published through a real push; the loops read on a
# descriptor of their own now, and a census case holds every loop that runs a tool to that. The table case
# after them derives the reads from the hook's tags and census and fails on a read without a row, a row
# without a read, a row whose case names none, and a header block the generator does not print.
tool_silent_on() {   # <tool> <bash test over the shim's "$@">: for that shape a <tool> that reads its stdin, prints nothing and exits 0 (the class's silent tool); the real one for every other shape
    local real real_cat
    real="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v "$1")"      # the shim directory stripped: a shim written before this one is not the real tool
    real_cat="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v cat)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then %q > /dev/null; exit 0; fi\n' "$2" "$real_cat"
        printf 'exec %q "$@"\n' "$real"
    } > "$TEST_DIR/shim/$1"
    chmod 755 "$TEST_DIR/shim/$1"
    export PATH="$TEST_DIR/shim:$PATH"
}
tool_answering_then_exiting() {   # <tool> <bash test over the shim's "$@"> <status>: for that shape the real <tool> runs and prints its answer, then the shim exits with the status in its place; the real one for every other shape
    local real
    real="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v "$1")"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then %q "$@"; exit %d; fi\n' "$2" "$real" "$3"
        printf 'exec %q "$@"\n' "$real"
    } > "$TEST_DIR/shim/$1"
    chmod 755 "$TEST_DIR/shim/$1"
    export PATH="$TEST_DIR/shim:$PATH"
}
git_shim() {   # <bash lines, run first with the git's arguments in "$@" and the real git in $real_git>: a git of the case's own; the real git for every command the lines do not end
    local real_git
    real_git="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\nreal_git=%q\n' "$real_git"
        printf '%s\n' "$1"
        printf 'exec "$real_git" "$@"\n'
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
push_refs_through_hook_with_shim() {   # <refspec>...: the hook installed for one real push of every refspec named, behind the wrapper that puts the shim directory first on the hook's PATH
    mkdir -p "$TEST_DIR/hooks"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'export PATH=%q:"$PATH"\n' "$TEST_DIR/shim"
        printf 'exec %q "$@"\n' "$HOOK"
    } > "$TEST_DIR/hooks/pre-push"
    chmod 755 "$TEST_DIR/hooks/pre-push"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/hooks"
    run git -C "$REPO" push origin "$@"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
}
clean_tip_after_base() {   # a base on the remote (BASE), then one clean commit (sha): the tip holds two regular files with bytes, both read by the tip's grep
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file clean.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
}
at_base() { [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$BASE" ]; }

@test "the FILE COUNT grep -c over the tip's rewritten -z listing, answering the FULL count and exiting 2, is refused as unscanned naming the read and its status through a real push of a clean tip, the remote at the base (a set widened to 2 publishes with nothing printed); the same read exiting 0 and answering NOTHING is refused on its digit check, naming both answers (round 8b: the round 7 rulings' D, and A.8's row)" {
    clean_tip_after_base
    grep_answering_then_failing '[ "${1:-}" = -c ] && [ "${2:-}" = -E ] && [[ "${4:-}" == *"/listing.nl" ]]'   # the FILE COUNT's shape alone (grep -c -E <pattern> <scratch>/listing.nl): the ENTRY COUNT and the LINE COUNT carry no -E
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) could not be counted for the BINARY VERDICT check (grep -c over the -z listing exited 2); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"not two counts"* ]]
    [[ "$output" != *"joined short"* ]]
    at_base
    tool_silent_on grep '[ "${1:-}" = -c ] && [ "${2:-}" = -E ] && [[ "${4:-}" == *"/listing.nl" ]]'
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) could not be counted for the BINARY VERDICT check (grep -c counted the -z listing's regular files with bytes as \"\" and the grep's read list as \"2\", not two counts); the scan is incomplete"* ]]
    at_base
}

@test "the LINE COUNT grep -c over the grep's rewritten read list, answering the FULL count and exiting 2, is refused as unscanned naming the read and its status through a real push of a clean tip, the remote at the base (a set widened to 2 publishes with nothing printed); the same read exiting 0 and answering NOTHING is refused on its digit check (round 8b: the round 7 rulings' D, and A.8's row)" {
    clean_tip_after_base
    grep_answering_then_failing '[ "${1:-}" = -c ] && [ "${2:-}" = . ] && [[ "${3:-}" == *"/read.nl" ]]'   # the LINE COUNT's shape alone: the ENTRY COUNT reads listing.nl
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) could not be counted for the BINARY VERDICT check (grep -c over the grep's read list exited 2); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"not two counts"* ]]
    at_base
    tool_silent_on grep '[ "${1:-}" = -c ] && [ "${2:-}" = . ] && [[ "${3:-}" == *"/read.nl" ]]'
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"(grep -c counted the -z listing's regular files with bytes as \"2\" and the grep's read list as \"\", not two counts)"* ]]
    at_base
}

@test "the added lines' LINE COUNT under a wc -l that prints the real count and exits 1 is refused as unscanned naming wc and its status, through a real push of a clean commit, the remote at the base (a set widened to 1 publishes with nothing printed); a wc -l exiting 0 and answering NOTHING is refused on its digit check (round 8b: the round 7 rulings' D, and A.8's row)" {
    clean_tip_after_base
    tool_answering_then_exiting wc '[ "${1:-}" = -l ]' 1          # the added lines' count alone: every other wc of the hook is -c
    run _hook_in "$REPO" -c 'printf "a\nb\n" | wc -l; echo "status $?"'
    [[ "$output" == *"2"$'\n'"status 1" ]]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${sha:0:10} could not be counted (wc exited 1); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"not a count"* ]]
    at_base
    tool_silent_on wc '[ "${1:-}" = -l ]'
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${sha:0:10} could not be counted (wc answered \"\", not a count); the scan is incomplete"* ]]
    at_base
}

@test "a hidden blob's SIZE read FAILING (cat-file -s exiting 128) behind a content read that answers nothing (cat-file blob exiting 0, a hand-written two-shape git) is refused naming the size read and its status, through a real push, the remote at the base (a set widened to 128 refuses on the digit check instead, the line naming no status); the size read exiting 0 and answering NOTHING is refused on that digit check (round 8b: the round 7 rulings' D, and A.8's row)" {
    hidden_file_in_middle_commit_after_base
    git_shim "if [ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [ \"\${3:-}\" = $blob ]; then cat > /dev/null; exit 0; fi
if [ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $blob ]; then echo 'fatal: shim: cat-file -s refused' >&2; exit 128; fi"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of notes.txt in commit ${leak:0:10}, which git calls binary and the identifier scan therefore skipped, was read as 0 bytes while its SIZE could not be read (git cat-file -s exited 128), so whether the blob is empty is unknown; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"not a size"* ]]
    at_base
    git_shim "if [ \"\${1:-}\" = cat-file ] && { [ \"\${2:-}\" = blob ] || [ \"\${2:-}\" = -s ]; } && [ \"\${3:-}\" = $blob ]; then cat > /dev/null; exit 0; fi"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of notes.txt in commit ${leak:0:10}, which git calls binary and the identifier scan therefore skipped, was read as 0 bytes while its SIZE reads \"\" (git cat-file -s), not a size, so whether the blob is empty is unknown"* ]]
    at_base
}

@test "a symlink target's SIZE read FAILING (cat-file -s exiting 128) behind a target read that answers nothing (cat-file -p exiting 0, a hand-written two-shape git) over a link the remote holds is refused naming the size read and its status, through a real push, and the remote never gets the branch (a set widened to 128 refuses on the digit check instead); the size read exiting 0 and answering NOTHING is refused on that digit check (round 8b: the round 7 rulings' D, and A.8's row)" {
    branch_inheriting_mains_symlink_leak
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$sha:node_modules")"
    git_shim "if [ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $blob ]; then cat > /dev/null; exit 0; fi
if [ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $blob ]; then echo 'fatal: shim: cat-file -s refused' >&2; exit 128; fi"
    push_ref_through_hook_with_shim feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SYMLINK TARGET of node_modules at the tip of refs/heads/feature (${sha:0:10}) was read as empty while its SIZE could not be read (git cat-file -s exited 128), so whether the target is empty is unknown; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"not a size"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
    git_shim "if [ \"\${1:-}\" = cat-file ] && { [ \"\${2:-}\" = -p ] || [ \"\${2:-}\" = -s ]; } && [ \"\${3:-}\" = $blob ]; then cat > /dev/null; exit 0; fi"
    push_ref_through_hook_with_shim feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SYMLINK TARGET of node_modules at the tip of refs/heads/feature (${sha:0:10}) was read as empty while its SIZE reads \"\" (git cat-file -s), not a size, so whether the target is empty is unknown"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "the TIP LISTING join (the -z listing against the grep's read list, an own= read) under an awk exiting 0 and printing nothing changes nothing by itself: the hidden text file the remote already holds is still named at the tip through a real push, and the remote stays at the base (the round 7 rulings' D: the join's gate is disarmed, the reads it gates stand)" {
    hidden_file_on_remote_then_clean_commit
    awk_silent_on_program 'listed[substr($0, i + 1)] = 1'       # tip_unlisted_read_file's program alone
    run _hook_in "$REPO" -c 'printf "a\tb\n" > "$1/l"; printf "s:b\n" > "$1/r"; awk -v sha=s "FILENAME == ARGV[1] { i = index(\$0, \"\\t\"); listed[substr(\$0, i + 1)] = 1; next }" "$1/l" "$1/r"; echo "status $?"' _ "$TEST_DIR"
    [ "$output" = "status 0" ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "the TIP BLOBS read (the blob set of the tip, an own= read) under an awk exiting 0 and printing nothing changes nothing by itself: emptied, it sends every per-commit candidate to the byte judge, so the hidden file added in the pushed commit and kept at the tip is named at the tip AND in its commit through a real push, the safe side, and the remote stays at the base (the round 7 rulings' D)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'notes.txt -diff\n' > "$REPO/.git/info/attributes"
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file, kept at the tip"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim                                 # no shim: the tip half alone names the blob the tip holds
    [ "$status" -ne 0 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides"* ]]
    [[ "$output" != *"notes.txt in commit ${sha:0:10}"* ]]
    awk_silent_on_program 'f[1] == "120000") print f[3]'           # tip_blobs' program alone
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides"* ]]
    [[ "$output" == *"romp pre-push: notes.txt in commit ${sha:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "the LISTING join of a commit (its changed-path listing against its verdicts, an own= read) under an awk exiting 0 and printing nothing changes nothing by itself: the hidden text file in the middle commit, gone at the tip, is still named in its commit through a real push, and the remote stays at the base (the round 7 rulings' D)" {
    hidden_file_in_middle_commit_after_base
    awk_silent_on_program 'p = substr($0, 4); if (!(p in listed))'   # unlisted_verdict_path's program alone (the tip's listing join names listed[substr(...)])
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt in commit ${leak:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"listed short"* ]]
    at_base
}

@test "the scanner log's ERR line (a gate= read since round 8b3) under an awk exiting 0 and printing nothing, beside a scanner that logs an ERR line and runs the real scan, is refused through a real push naming the read's empty answer, neither none nor an error line, and the remote holds nothing (the round 7 rulings' D; a silent awk over a log with no ERR line would witness nothing; since round 9 the line comes from a scanner wrapper, gitleaks running no git of its own)" {
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    scanner_wrapper 'echo "1:00AM ERR something went wrong" >&2'
    awk_silent_on_program '$2 == "ERR"'
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"ERR something went wrong"* ]]                    # the fixture's premise: the log carries an ERR line for the awk to miss
    [[ "$output" != *"gitleaks logged an error"* ]]                  # the ERR line went unread: the read is silent
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan could not be judged: its log's error-line read answered \"\" (awk exited 0), neither the word none nor an error line"* ]]   # the gate refuses the empty answer itself
    [[ "$output" == *"gitleaks could not scan"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

# The road found while the rows above were written (round 8b): every tool a loop runs inherits the loop's
# stdin, and four loops that run tools read their list on stdin, so a tool that reads its stdin (the
# silent shape the shims here share) took the rest of the list. A two-ref push published its second ref
# (an awk so silent on any of the three own= joins, during the first ref), a hidden file went unjudged (a
# git so silent on an empty blob's read, the blob's own answer), a second ref's credential was never
# scanned (a git so silent on the range probe, a read retired in round 9), and the symlink loop's drain was caught only by its own
# entry count. The loops read on a descriptor of their own now (the refs on 5, the links and the byte
# judge's entries on 6), so such a tool meets the end of the hook's stdin; the census case at the end of
# this block holds every loop that runs a tool to that.
two_refs_second_leaking() {   # a base on the remote (BASE); main one clean commit ahead of it; feature, from the base, adding a banned line (fsha); main is pushed first
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b feature
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    fsha="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q main
    commit_file more.txt "nothing to see" "more"
}

@test "a two-ref push whose FIRST ref meets an awk that exits 0, prints nothing and reads its stdin, on each of the three own= joins in turn (the tip's listing against the read list, the tip's blob set, a commit's listing against its verdicts), still scans the SECOND ref: its banned line is named and the remote never gets it (the round 8 text read the refs on stdin, the awk took the rest of them, and the second ref published with nothing printed; round 8b)" {
    two_refs_second_leaking
    for program in 'listed[substr($0, i + 1)] = 1' 'f[1] == "120000") print f[3]' 'p = substr($0, 4); if (!(p in listed))'; do
        rm -rf "$TEST_DIR/shim"
        awk_silent_on_program "$program"
        push_refs_through_hook_with_shim main feature
        [ "$status" -ne 0 ]
        [[ "$output" == *"romp pre-push: the tip of refs/heads/feature (${fsha:0:10}) would publish a personal identifier in:"* ]]
        [[ "$output" == *"romp pre-push: commit ${fsha:0:10} ADDS a personal identifier in:"* ]]
        run remote_holds_ref refs/heads/feature
        [ "$status" -ne 0 ]
        at_base
    done
}

@test "a byte judge that meets an EMPTY hidden blob first (its content read exiting 0 and printing nothing, the blob's own answer, while the git reads its stdin) still judges the hidden text file after it: the file is named in its commit through a real push and the remote stays at the base (the round 8 text read the entries on stdin, the git took the rest of them, and the push published with nothing printed; round 8b)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'a-empty.txt -diff\nb-notes.txt -diff\n' > "$REPO/.git/info/attributes"
    : > "$REPO/a-empty.txt"
    printf 'seen on TESTHOST\n' > "$REPO/b-notes.txt"
    git -C "$REPO" add a-empty.txt b-notes.txt
    git -C "$REPO" commit -qm "an empty file and a banned one, both under -diff"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" rm -q a-empty.txt b-notes.txt
    git -C "$REPO" commit -qm "remove them"
    empty="$(git -C "$REPO" hash-object --stdin < /dev/null)"
    git_shim "if [ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [ \"\${3:-}\" = $empty ]; then cat > /dev/null; exit 0; fi"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: b-notes.txt in commit ${leak:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"a-empty.txt"* ]]                           # the empty file passes as empty, its size agreeing
    at_base
}

@test "a symlink loop that meets a link over the EMPTY blob first (its target read exiting 0 and printing nothing, the blob's own answer, while the git reads its stdin) still reads the link after it: its banned target is named through a real push, and the remote never gets the branch (the round 8 text read the links on stdin, the git took the rest of them, and only the entry count refused, the banned target unread; round 8b)" {
    add_remote
    empty="$(git -C "$REPO" hash-object -w --stdin < /dev/null)"
    target="$(printf '/home/zzsynthuser/code' | git -C "$REPO" hash-object -w --stdin)"
    git -C "$REPO" update-index --add --cacheinfo "120000,$empty,a-empty" --cacheinfo "120000,$target,b-link"
    git -C "$REPO" commit -qm "two links"
    git -C "$REPO" push -q origin main                        # the remote holds both: the tip half alone reads them
    git -C "$REPO" checkout -q -b feature
    commit_file c.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_shim "if [ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $empty ]; then cat > /dev/null; exit 0; fi"
    push_ref_through_hook_with_shim feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the tip of refs/heads/feature (${sha:0:10}) would publish a personal identifier"$'\n'"  in the SYMLINK TARGET of b-link -> /home/zzsynthuser/code"* ]]
    [[ "$output" != *"listed short or long"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "a two-ref push whose FIRST ref's credential listing meets a git that exits 0, prints nothing and reads its stdin still credential-scans the SECOND ref: the real scanner names its credential through a real push and the remote never gets it (the round 8 text read the refs on stdin, the git took the rest of them, and the second ref's credential published with nothing printed; round 8b; re-aimed in round 9 from the retired range probe to the listing the credential scan shares with the identifier scan, where the first ref is refused as listed short)" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"           # the credential scan alone: the identifier scan's listing has the same shape
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    fsha="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q main
    commit_file more.txt "nothing to see" "more"
    msha="$(git -C "$REPO" rev-parse HEAD)"
    git_draining_stdin_on "[ \"\${1:-}\" = rev-list ] && [ \"\${2:-}\" = $msha ] && [ \"\${3:-}\" = --not ]"   # main's listing alone (rev-list <main> --not --remotes ...)
    push_refs_through_hook_with_shim main feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"the COMMITS of refs/heads/main (${msha:0:10}) were listed as none"* ]]
    [[ "$output" == *"romp pre-push: commit ${fsha:0:10} ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

stdin_loops_running_tools() {   # <bash file>: prints "<first line>-<last line>: <tools>" for each while-read loop that reads its list on stdin (no read -u with a descriptor from 1 to 9) and runs a tool in its body: a reading tool, a judged_read call, or a call to a function the file defines whose body runs one, resolved transitively over the function extents undeclared_reads derives; reads the census's helpers
    local -a orig masked toks mw rw rec segln segwhat
    local -A fstart fend runs
    local i j k r depth seen tok tools cmd word rword wkind u ln fl et touch f g changed names line
    mapfile -t orig < "$1"
    mapfile -t masked < <(masked_text "$1")
    census_functions
    names="(^|[^A-Za-z0-9_])(judged_read$(printf '|%s' "${!fstart[@]}"))([^A-Za-z0-9_]|\$)"
    while IFS=$'\x1f' read -r -a rec; do                        # every simple command that runs something, with its line: a reading tool, judged_read or a function of the file
        census_rec "${rec[@]}"
        census_command
        if [ -n "$cmd" ]; then segln+=("$ln"); segwhat+=("$cmd")
        elif [ "$wkind" = judged ]; then segln+=("$ln"); segwhat+=(judged_read)
        elif [ "$wkind" = function ]; then segln+=("$ln"); segwhat+=("call:$word")
        fi
    done < <(census_records "$1" calls "$names")
    changed=1
    while [ "$changed" -ne 0 ]; do                              # the functions whose body runs a tool, directly, through judged_read or through such a function, to a fixed point
        changed=0
        for ((r = 0; r < ${#segln[@]}; r++)); do
            case "${segwhat[r]}" in call:*) g=${segwhat[r]#call:}; [ -n "${runs[$g]:-}" ] || continue ;; esac
            i=$((segln[r] - 1))
            for f in "${!fstart[@]}"; do
                if [ -z "${runs[$f]:-}" ] && [ "$i" -gt "${fstart[$f]}" ] && [ "$i" -le "${fend[$f]}" ]; then runs[$f]=1; changed=1; fi
            done
        done
    done
    for ((i = 0; i < ${#masked[@]}; i++)); do
        [[ "${masked[i]}" =~ (^|[[:space:]\;])while[[:space:]] ]] || continue
        [[ "${masked[i]}" =~ (^|[[:space:]\;])read[[:space:]] ]] || continue
        [[ "${masked[i]}" =~ read[[:space:]]+(-[^[:space:]]+[[:space:]]+)*-u[[:space:]]*[1-9]([^0-9]|$) ]] && continue    # read -u 1 to 9: the list on a descriptor of its own (-u 0 is stdin)
        depth=0; seen=0; j=$i
        for ((k = i; k < ${#masked[@]}; k++)); do                # the loop's done: its do and done words counted from the while line
            line=${masked[k]//$'\001'/ }
            read -r -a toks <<< "${line//[;&|()]/ }"
            for tok in ${toks[@]+"${toks[@]}"}; do
                case "$tok" in do) depth=$((depth + 1)); seen=1 ;; done) depth=$((depth - 1)) ;; esac
            done
            if [ "$seen" -ne 0 ] && [ "$depth" -le 0 ]; then j=$k; break; fi
        done
        tools=""
        for ((r = 0; r < ${#segln[@]}; r++)); do
            [ "${segln[r]}" -gt "$i" ] && [ "${segln[r]}" -le $((j + 1)) ] || continue
            case "${segwhat[r]}" in
                call:*) g=${segwhat[r]#call:}; [ -z "${runs[$g]:-}" ] || tools="$tools $g" ;;
                *) tools="$tools ${segwhat[r]}" ;;
            esac
        done
        [ -z "$tools" ] || echo "$((i + 1))-$((j + 1)):$tools"
    done
}
descriptor_loops() {   # <bash file>: the count of while-read loops that read their list with -u from a descriptor 1 to 9 (-u 0 is stdin), whatever IFS they set
    grep -cE 'while (IFS=[^[:space:]]* )?read -r -u [1-9]([^0-9]|$)' "$1" || true
}

@test "no loop that runs a tool reads its list on stdin (round 8b, widened in round 9b): every while-read loop whose body runs a reading tool, a judged_read call or a function of the hook whose body runs one (resolved transitively) reads with -u from a descriptor 1 to 9, so a tool that reads its stdin empties no list; the census flags each loop round 8b moved reverted to stdin, loops running a tool through judged_read, through hook functions and through a function that reaches one only transitively, and a -u 0 loop, and passes the same loop on a descriptor and loops of builtins and of functions that run no tool" {
    run stdin_loops_running_tools "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    # the loops that run tools read on a descriptor 1 to 9: seven in the hook (the two ref loops, the symlink loop, the
    # commit loop, the byte judge's, since round 9b the addresses loop, whose IFS=$'\t' the count reads, and since
    # round 10a the loop over a merge's binary paths, merge_binary_reads, whose reads are judged_read calls), and
    # since round 9d four loops of the credential scan that run no tool but read on a descriptor all the same (the
    # index read into arrays, the two passes over the path-scoped index, the report's findings): eleven
    [ "$(descriptor_loops "$HOOK")" -eq 11 ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r x; do' '    git cat-file -t "$x"' 'done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-a.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-a.sh"
    [ "$output" = "2-4: git" ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r -u 5 x; do' '    git cat-file -t "$x"' 'done 5<<< "$refs"' 'while read -r x; do echo "$x"; done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-b.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-b.sh"
    [ -z "$output" ]
    # round 9b (the round 8 rulings' C): the census counted a tool only as a command word on the loop's own lines, so a
    # loop running its tools through judged_read or a hook function passed it; the identifier ref loop reverted to stdin
    # published a second ref (case 222) while this case stayed green (the round 8 refuters, 2026-09-24). Each of the four
    # loops round 8b moved to a descriptor (the byte judge's entries, the two ref loops, the symlink loop), reverted to
    # stdin in a copy, is flagged, one line naming that loop (the identifier ref loop and the symlink loop passed the
    # census at cad898dd2)
    local -a whiles=("while IFS= read -r -u 6 -d '' entry; do" 'while read -r -u 5 local_ref local_sha _remote_ref remote_sha; do' 'while IFS= read -r -u 6 link; do' 'while read -r -u 5 local_ref local_sha _remote_ref remote_sha; do')
    local -a nth=(1 1 1 2)
    local -a dones=('done 6< "$scratch/entries"' 'done 5<<< "$refs"' 'done 6<<< "$listing"' 'done 5<<< "$refs"')
    local -a dnth=(1 1 1 2)                                          # the credential ref loop's done line reads "$refs" since round 9, as the identifier ref loop's does
    local k w d
    for k in 0 1 2 3; do
        w=$(grep -nF -- "${whiles[k]}" "$HOOK" | sed -n "${nth[k]}p" | cut -d: -f1)
        d=$(grep -nF -- "${dones[k]}" "$HOOK" | sed -n "${dnth[k]}p" | cut -d: -f1)
        [ -n "$w" ] && [ -n "$d" ]
        sed -E "${w}s/ -u [0-9] / /; ${d}s/done [0-9]</done </" "$HOOK" > "$TEST_DIR/loop-rev$k.sh"
        run cmp -s "$HOOK" "$TEST_DIR/loop-rev$k.sh"
        [ "$status" -ne 0 ]                                        # the revert landed
        run stdin_loops_running_tools "$TEST_DIR/loop-rev$k.sh"
        [ -n "$output" ]
        [ "$(wc -l <<< "$output")" -eq 1 ]
        [[ "$output" == "$w-$d: "* ]]
    done
    # planted loops on stdin that run a tool through judged_read (its tagged command a git, then a builtin), through a
    # hook function whose one tool runs through judged_read (object_type), through one whose body runs git, tr and awk
    # itself (credential_feed since round 9d, in place of the retired scannable_commits, which ran git, sort and
    # cat-file), and through a planted function whose body only calls object_type: each flagged once (each passed at
    # cad898dd2)
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r x; do' '    judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -- git cat-file -t "$x" || :' 'done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-c.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-c.sh"
    [ "$output" = "2-4: judged_read git" ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r x; do judged_read own="the PROBE read" 0 "the PROBE of x could not be read (probe exited {rc})" -- printf "%s\n" "$x" || :; done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-c2.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-c2.sh"
    [ "$output" = "2-2: judged_read" ]                               # a judged_read call counts whatever its tagged command
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r x; do object_type refs/heads/x "$x"; done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-d.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-d.sh"
    [ "$output" = "2-2: object_type" ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r x; do credential_feed "$x" r d i p; done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-e.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-e.sh"
    [ "$output" = "2-2: credential_feed" ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'probe_type() {' '    object_type "$1" "$2"' '}' 'while read -r x; do probe_type refs/heads/x "$x"; done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-f.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-f.sh"
    [ "$output" = "5-5: probe_type" ]
    # -u 0 reads stdin: the loop is flagged, and the count of descriptor loops does not count it (cad898dd2's census
    # skipped it and its count pin counted it)
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r -u 0 x; do' '    git cat-file -t "$x"' 'done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-g.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-g.sh"
    [ "$output" = "2-4: git" ]
    [ "$(descriptor_loops "$TEST_DIR/loop-g.sh")" -eq "$(descriptor_loops "$HOOK")" ]
    # a loop on stdin that calls hook functions whose bodies run no tool (unscanned prints, is_chosen compares in the
    # shell) passes
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r x; do unscanned "x"; is_chosen "$x" "$y" || :; done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-h.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-h.sh"
    [ -z "$output" ]
}

# ── round 8b (A.8): the population as the predicate, a table of every read ──
# tests/pre-push-reads.tsv holds one row per tool read of the hook: every judged_read tag (gate= and own=)
# and every read the census finds outside judged_read (its marker and array classes), each with the sibling
# fact that shows a whole answer or the reason an empty or short exit-0 answer is the safe side there, and
# the case that drives THAT read with a silent tool keyed on its own shape through a real push (one case per
# row, in the round 8b2 section at the end of this file), and since round 8b3 the END of its answer (how an
# answer cut short is told from a whole one) with the case that drives it with that answer cut short, or the
# reason no cut applies (the round 8b3 section after it). The block between the hook's two marker lines, the
# bound and own= paragraphs and both lists with each read's fact, is generated from the table
# (tests/pre-push-reads-header.sh), never typed. reads_table_check is the predicate over a hook, a table and
# a generator; the case below runs it over the files in the tree and then over planted copies, so each red it
# claims is executed rather than assumed: a planted read with no row, a row with no read, a row naming no
# case, a row naming a case that pushes through no hook, a hand edit of a list, of a paragraph and of a row's
# fact, a table whose outside rows are swapped (a real read's row dropped, a row for a read the hook does not
# make added), a duplicated key, a planted outside read with no row, and since round 8b3 a row with no short
# column, a short column naming a silent case, a short column of none with no reason, a fact that states no
# end and an end of no known kind, and since round 8c an outside row whose short column is none with a reason
# (a cut of a read made for the report can change what the report says, so every outside row names the case
# that cuts it; the pcount row's none with a reason stayed green, the r8b5 audit, 2026-09-23). Round 8b
# matched the outside reads by COUNT, and the swapped table stayed green (the r8b audit, 2026-09-23); each
# row's key makes the match a bijection, read by read. Since round 9b (the round 8 rulings' G) the case also
# plants rows naming another read's case (the case columns of two rows swapped, their short columns swapped, a
# row copying its neighbour's cases, a read whose name begins another's naming the longer read's case), each
# refused by the title's read, and a begin marker line doubled, inside the block and just before its end, each
# refused by the block comparison.
READS_TSV="$ROMP_DIR/tests/pre-push-reads.tsv"
READS_HEADER_GEN="$ROMP_DIR/tests/pre-push-reads-header.sh"
READS_BEGIN='# BEGIN generated block (tests/pre-push-reads-header.sh; edit the table)'
READS_END='# END generated block'
hook_generated_block() {   # <hook file>: the lines between the FIRST begin marker line and the end marker after it, each with its newline; nothing when either marker is missing (a later begin marker line is content, so a hand-made one differs from the generator's output: round 9b)
    awk -v b="$READS_BEGIN" -v e="$READS_END" '$0 == b && !p { p = 1; next } p && $0 == e { done = 1; exit } p { buf = buf $0 "\n" } END { if (done) printf "%s", buf }' "$1"
}
hook_with_block_of() {   # <hook file> <tsv> <out>: the hook with its generated block replaced by the generator's output for that table
    bash "$READS_HEADER_GEN" "$2" > "$TEST_DIR/block-of.txt"
    awk -v b="$READS_BEGIN" -v e="$READS_END" -v f="$TEST_DIR/block-of.txt" '$0 == b { print; while ((getline l < f) > 0) print l; skip = 1; next } $0 == e { skip = 0 } !skip { print }' "$1" > "$3"
}
reads_table_check() {   # <hook> <tsv> <generator> <dir of the pre-push-*.bats files>: prints the first disagreement and returns 1; returns 0 when the table and the hook agree
    local hook=$1 tsv=$2 gen=$3 dir=$4 work line n kind read fact caseref key class file sub body text hits k title
    work=$(mktemp -d "$TEST_DIR/table.XXXXXX")
    # the rows: printable ASCII and TAB alone (the generator folds by bytes), a prose row of three fields, a read row of six
    if LC_ALL=C grep -q $'[^\t -~]' "$tsv"; then echo "the table holds a byte outside printable ASCII and TAB"; return 1; fi
    while IFS= read -r line; do
        case "$line" in '#'*|'') continue ;; esac
        n=$(awk -F'\t' '{ print NF }' <<< "$line")
        case "${line%%$'\t'*}" in
            prose) [ "$n" -eq 3 ] || { echo "a prose row of $n fields: $line"; return 1; } ;;
            gate|own|outside) [ "$n" -eq 8 ] || { echo "a read row of $n fields: $line"; return 1; } ;;
            *) echo "a row of no known kind: $line"; return 1 ;;
        esac
    done < "$tsv"
    # the header: the lines between the hook's marker lines are the generator's output, byte for byte
    bash "$gen" "$tsv" > "$work/gen" || { echo "the generator failed"; return 1; }
    hook_generated_block "$hook" > "$work/block"
    [ -s "$work/block" ] || { echo "the hook holds no generated block between the two marker lines"; return 1; }
    cmp -s "$work/gen" "$work/block" || { echo "the hook's generated block differs from the generator's output for the table"; return 1; }
    # the tags: each kind's distinct judged_read names are the table's rows of that kind, one row each
    for kind in gate own; do
        grep -oE "judged_read $kind=\"[^\"]*\"" "$hook" | sed -E "s/^judged_read $kind=\"//; s/\"\$//" | sort -u > "$work/tags"
        awk -F'\t' -v k="$kind" '$1 == k { print $2 }' "$tsv" | sort > "$work/rows"
        [ -s "$work/tags" ] || { echo "the hook carries no $kind= tag"; return 1; }
        sort -u "$work/rows" | cmp -s - "$work/rows" || { echo "a $kind= read has two rows"; return 1; }
        cmp -s "$work/tags" "$work/rows" || { echo "the $kind= tags and the table's $kind rows differ: $(diff "$work/tags" "$work/rows" | grep '^[<>]' | head -n 2 | tr '\n' ' ')"; return 1; }
    done
    # each read row: its case resolves to one case title, that case pushes through the hook and checks the calls
    # file its shim appends to, and its class is one its kind and its fact take; its fact states its END after
    # "Its end:", its end column names one of the ways an end is bounded, and its short column names the case
    # that drives the read with its answer cut short (one case title, pushing through the hook and checking
    # with fired_short that the shim fired with a cut answer) or gives the reason no cut applies (round 8b3),
    # the reason on a gate= or own= row alone: an outside row names its case (round 8c). Since round 9b each
    # case's title, and the short case's, carries the row's read as ": <read>:", the titles' own convention (the
    # trailing colon refuses a read whose name is a prefix of a neighbour's): until then rows naming each other's
    # cases passed, the defect the round 8b audit found in 27 rows (the round 8 refuters, 2026-09-24)
    while IFS=$'\t' read -r kind read fact caseref key class short end; do
        case "$kind" in gate|own|outside) ;; *) continue ;; esac
        file=${caseref%%:*}; sub=${caseref#*:}
        if [ "$file" = "$caseref" ] || [ ! -f "$dir/pre-push-$file.bats" ]; then echo "the case of $read names no bats file: $caseref"; return 1; fi
        n=$(grep -c -F -- "$sub" "$dir/pre-push-$file.bats" || true)
        [ "$n" -eq 1 ] || { echo "the case of $read matches $n lines: $sub"; return 1; }
        grep -F -- "$sub" "$dir/pre-push-$file.bats" | grep -q '^@test ' || { echo "the case of $read names no case: $sub"; return 1; }
        body=$(SUB=$sub awk 'index($0, ENVIRON["SUB"]) && /^@test / { p = 1 } p { print } p && /^}$/ { exit }' "$dir/pre-push-$file.bats")
        [[ "$body" == *"_through_hook_with_shim"* ]] || { echo "the case of $read pushes through no hook: $sub"; return 1; }
        [[ "$body" == *$'\n    fired '* ]] || { echo "the case of $read checks no calls file: $sub"; return 1; }
        title=$(grep -F -- "$sub" "$dir/pre-push-$file.bats" | sed -E 's/^@test "//; s/" \{$//')
        [[ "$title" == *": $read:"* ]] || { echo "the case of $read names another read: $title"; return 1; }
        [[ "$fact" == *"Its end: "?* ]] || { echo "the row of $read states no end"; return 1; }
        case "$end" in
            tail|count|size|digits|whole|terminator|verdict|join|fewer|bytes|emptiness|backstop|prefix|status|discarded|report) ;;
            *) echo "the row of $read carries the end $end, no known kind"; return 1 ;;
        esac
        case "$short" in
            "none: "?*) [ "$kind" != outside ] || { echo "the short column of $read gives none: on an outside row, which names its short case"; return 1; } ;;
            none*|'') echo "the short column of $read gives no case and no reason"; return 1 ;;
            *)
                file=${short%%:*}; sub=${short#*:}
                if [ "$file" = "$short" ] || [ ! -f "$dir/pre-push-$file.bats" ]; then echo "the short case of $read names no bats file: $short"; return 1; fi
                n=$(grep -c -F -- "$sub" "$dir/pre-push-$file.bats" || true)
                [ "$n" -eq 1 ] || { echo "the short case of $read matches $n lines: $sub"; return 1; }
                grep -F -- "$sub" "$dir/pre-push-$file.bats" | grep -q '^@test ' || { echo "the short case of $read names no case: $sub"; return 1; }
                body=$(SUB=$sub awk 'index($0, ENVIRON["SUB"]) && /^@test / { p = 1 } p { print } p && /^}$/ { exit }' "$dir/pre-push-$file.bats")
                [[ "$body" == *"_through_hook_with_shim"* ]] || { echo "the short case of $read pushes through no hook: $sub"; return 1; }
                [[ "$body" == *$'\n    fired_short '* ]] || { echo "the short case of $read checks no cut answer: $sub"; return 1; }
                title=$(grep -F -- "$sub" "$dir/pre-push-$file.bats" | sed -E 's/^@test "//; s/" \{$//')
                [[ "$title" == *": $read:"* ]] || { echo "the short case of $read names another read: $title"; return 1; }
                ;;
        esac
        case "$kind:$class" in
            gate:marker|gate:count|gate:size|gate:listing|gate:digits|gate:status|gate:answer)
                [[ "$fact" != safe:* ]] || { echo "the row of $read gives a safe reason under the fact class $class"; return 1; } ;;
            gate:strict|gate:join|gate:backstop|own:strict|own:transfer|own:disarm|own:backstop|own:probe)
                [[ "$fact" == safe:* ]] || { echo "the row of $read gives no safe reason under the safe class $class"; return 1; } ;;
            outside:report|outside:backstop) ;;
            *) echo "the row of $read carries the class $class, which its kind does not take"; return 1 ;;
        esac
        if [ "$kind" = outside ]; then [ "$key" != - ] || { echo "the outside row of $read carries no key"; return 1; }; else [ "$key" = - ] || { echo "the $kind= row of $read carries a key"; return 1; }; fi
    done < "$tsv"
    # the reads outside judged_read: a bijection between the census's marker and array lines and the outside rows'
    # keys, each line matched by exactly one key and each key matching exactly one line (read by read, never a count)
    undeclared_reads "$hook" > "$work/census" || { echo "the census failed"; return 1; }
    awk '$1 == "declared:" && ($2 == "marker" || $2 == "array") { print $3 }' "$work/census" > "$work/lines"
    [ -s "$work/lines" ] || { echo "the census found no read outside judged_read"; return 1; }
    awk -F'\t' '$1 == "outside" { print $5 }' "$tsv" > "$work/keys"
    while IFS= read -r n; do
        text=$(sed -n "${n}p" "$hook"); hits=0
        while IFS= read -r k; do if [[ "$text" == *"$k"* ]]; then hits=$((hits + 1)); fi; done < "$work/keys"
        [ "$hits" -eq 1 ] || { echo "the read outside judged_read at line $n is matched by $hits keys: ${text#"${text%%[![:space:]]*}"}"; return 1; }
    done < "$work/lines"
    while IFS= read -r k; do
        hits=0
        while IFS= read -r n; do if [[ "$(sed -n "${n}p" "$hook")" == *"$k"* ]]; then hits=$((hits + 1)); fi; done < "$work/lines"
        [ "$hits" -eq 1 ] || { echo "the key $k matches $hits reads outside judged_read"; return 1; }
    done < "$work/keys"
    return 0
}

@test "every read of the hook has a row in tests/pre-push-reads.tsv, keyed to it, and every row names the case that drives THAT read through a real push (A.8, rounds 8b and 8b2) and, since round 8b3, the END of its answer and the case that drives it with that answer cut short, or why no cut applies: the predicate holds over the tree, the header block is the table's generated output byte for byte, and each red the predicate claims is executed over a planted copy" {
    [ -f "$READS_TSV" ]
    [ -x "$READS_HEADER_GEN" ]
    run reads_table_check "$HOOK" "$READS_TSV" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$output" = "" ]
    [ "$status" -eq 0 ]
    P="$TEST_DIR/planted"; mkdir -p "$P"
    # a planted read with no row: a judged_read call whose tag the table lacks
    sed '2a judged_read gate="the PLANTED read with no row" 0 "the PLANTED read could not be made (a probe exited {rc})" -- git rev-parse HEAD' "$HOOK" > "$P/hook-read"
    run reads_table_check "$P/hook-read" "$READS_TSV" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [[ "$output" == "the gate= tags and the table's gate rows differ: < the PLANTED read with no row"* ]]
    # a row with no read: a gate row the hook carries no tag for, the hook's block regenerated from that table
    awk -F'\t' -v OFS='\t' '{ print } $2 == "the EMPTY TREE name" { $2 = "the PLANTED row with no read"; print }' "$READS_TSV" > "$P/tsv-row"
    hook_with_block_of "$HOOK" "$P/tsv-row" "$P/hook-row"
    run reads_table_check "$P/hook-row" "$P/tsv-row" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [[ "$output" == "the gate= tags and the table's gate rows differ: > the PLANTED row with no read"* ]]
    # a row naming no case
    missing="zzsynth-no-case-$$-$RANDOM"                           # made here, so no line of this file carries it
    MISSING=$missing awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { $4 = "hook:" ENVIRON["MISSING"] } { print }' "$READS_TSV" > "$P/tsv-no-case"
    run reads_table_check "$HOOK" "$P/tsv-no-case" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the case of the EMPTY TREE name matches 0 lines: $missing" ]
    # a row naming a case that drives no read (the tags case above: it pushes nothing); its title assembled here, so this file carries it once
    sub="the header's two lists of reads are "; sub="${sub}DERIVED from the tags"
    SUB=$sub awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { $4 = "hook:" ENVIRON["SUB"] } { print }' "$READS_TSV" > "$P/tsv-no-push"
    run reads_table_check "$HOOK" "$P/tsv-no-push" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the case of the EMPTY TREE name pushes through no hook: $sub" ]
    # a hand edit of a list, of a paragraph, and of a row's fact left ungenerated: the block differs from the generator's output
    sed 's/^#   the EMPTY TREE name$/#   the EMPTY TREE name, edited by hand/' "$HOOK" > "$P/hook-list"
    sed 's/^# The bound of each sibling fact, stated once:/# The bound of every sibling fact, stated once:/' "$HOOK" > "$P/hook-prose"
    run cmp -s "$HOOK" "$P/hook-list"
    [ "$status" -ne 0 ]                                            # each edit landed
    run cmp -s "$HOOK" "$P/hook-prose"
    [ "$status" -ne 0 ]
    awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { $3 = $3 " (a fact edited in the table alone)" } { print }' "$READS_TSV" > "$P/tsv-fact"
    run reads_table_check "$P/hook-list" "$READS_TSV" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the hook's generated block differs from the generator's output for the table" ]
    run reads_table_check "$P/hook-prose" "$READS_TSV" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the hook's generated block differs from the generator's output for the table" ]
    run reads_table_check "$HOOK" "$P/tsv-fact" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the hook's generated block differs from the generator's output for the table" ]
    # the swapped outside table: the core.bigFileThreshold read's row dropped and a row keyed to a read the hook does not
    # make added, the count unchanged (round 8b's count match stayed green on this table); the added row keeps the
    # dropped row's read, case and short case, each read from the table by awk (a literal copy of a title here would
    # match two lines), so it passes the row checks, the title's read among them since round 9b, and meets the key match
    read="$(awk -F'\t' '$5 == "git config core.bigFileThreshold" { print $2 }' "$READS_TSV")"
    ref="$(awk -F'\t' '$5 == "git config core.bigFileThreshold" { print $4 }' "$READS_TSV")"
    sref="$(awk -F'\t' '$5 == "git config core.bigFileThreshold" { print $7 }' "$READS_TSV")"
    [ -n "$read" ]
    [ -n "$ref" ]
    [ -n "$sref" ]
    { grep -v -F "$(printf '\tgit config core.bigFileThreshold\t')" "$READS_TSV"; printf 'outside\t%s\tfor the report alone: planted. Its end: planted\t%s\tgit config core.zzsynthNoSuchKey\treport\t%s\treport\n' "$read" "$ref" "$sref"; } > "$P/tsv-swapped"
    [ "$(grep -c $'^outside\t' "$P/tsv-swapped")" -eq "$(grep -c $'^outside\t' "$READS_TSV")" ]
    run reads_table_check "$HOOK" "$P/tsv-swapped" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [[ "$output" == "the read outside judged_read at line "*" is matched by 0 keys: threshold=\$(git config core.bigFileThreshold "* ]]
    # a duplicated key: the rename source's row given the threshold read's key
    awk -F'\t' -v OFS='\t' '$2 == "the rename source, for the report" { $5 = "git config core.bigFileThreshold" } { print }' "$READS_TSV" > "$P/tsv-dup"
    run reads_table_check "$HOOK" "$P/tsv-dup" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [[ "$output" == "the read outside judged_read at line "*" is matched by 2 keys: threshold=\$(git config core.bigFileThreshold "* ]]
    # a planted read outside judged_read, declared at its site, with no row
    sed '2a # outside judged_read: planted for the table case\
zz_planted=$(git config core.zzsynthPlanted 2>/dev/null || true)' "$HOOK" > "$P/hook-outside"
    run reads_table_check "$P/hook-outside" "$READS_TSV" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [[ "$output" == "the read outside judged_read at line 4 is matched by 0 keys: zz_planted=\$(git config core.zzsynthPlanted"* ]]
    # round 8b3: a row with no short column; a short column naming the row's silent case, which checks no cut
    # answer; a short column of none with no reason; a fact that states no end (the hook's block regenerated from
    # that table, so the block agrees); and an end of no known kind
    awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { NF = 7 } { print }' "$READS_TSV" > "$P/tsv-no-short"
    run reads_table_check "$HOOK" "$P/tsv-no-short" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [[ "$output" == "a read row of 7 fields: gate"$'\t'"the EMPTY TREE name"$'\t'* ]]
    silent_ref="$(awk -F'\t' '$2 == "the EMPTY TREE name" { print $4 }' "$READS_TSV")"   # read from the table, so this file carries the title once
    [ -n "$silent_ref" ]
    awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { $7 = $4 } { print }' "$READS_TSV" > "$P/tsv-short-silent"
    run reads_table_check "$HOOK" "$P/tsv-short-silent" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the short case of the EMPTY TREE name checks no cut answer: ${silent_ref#hook:}" ]
    awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { $7 = "none:" } { print }' "$READS_TSV" > "$P/tsv-short-bare"
    run reads_table_check "$HOOK" "$P/tsv-short-bare" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the short column of the EMPTY TREE name gives no case and no reason" ]
    awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { sub(/ Its end: .*/, "", $3) } { print }' "$READS_TSV" > "$P/tsv-no-end"
    run cmp -s "$READS_TSV" "$P/tsv-no-end"
    [ "$status" -ne 0 ]                                            # the edit landed
    hook_with_block_of "$HOOK" "$P/tsv-no-end" "$P/hook-no-end"
    run reads_table_check "$P/hook-no-end" "$P/tsv-no-end" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the row of the EMPTY TREE name states no end" ]
    awk -F'\t' -v OFS='\t' '$2 == "the EMPTY TREE name" { $8 = "zzsynth" } { print }' "$READS_TSV" > "$P/tsv-end"
    run reads_table_check "$HOOK" "$P/tsv-end" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the row of the EMPTY TREE name carries the end zzsynth, no known kind" ]
    # round 8c: an outside row whose short column is none with a reason, the pcount row's shape before round 8b5
    # (a cut applied there all along); a gate= or own= row's none with a reason passes, as seven of the tree's rows show
    awk -F'\t' -v OFS='\t' '$1 == "outside" && $2 == "the parent count re-read from pcount, for the report" { $7 = "none: the count is read for the report alone (planted)" } { print }' "$READS_TSV" > "$P/tsv-outside-none"
    run cmp -s "$READS_TSV" "$P/tsv-outside-none"
    [ "$status" -ne 0 ]                                            # the edit landed
    run reads_table_check "$HOOK" "$P/tsv-outside-none" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the short column of the parent count re-read from pcount, for the report gives none: on an outside row, which names its short case" ]
    # round 9b (the round 8 rulings' G.1): a row naming another read's case, in either column, is refused by the title,
    # which carries its read as ": <read>:". The case columns of two neighbouring rows swapped, then their short columns
    # swapped (apart: a combined swap meets the case check first), a row copying its neighbour's two cases, and the
    # prefix collision, a read whose name begins another's naming the longer read's case; each passed at cad898dd2.
    # The references and titles are read from the table and this file, so no title is copied here.
    title_of() { grep -F -- "${1#hook:}" "$ROMP_DIR/tests/pre-push-hook.bats" | sed -E 's/^@test "//; s/" \{$//'; }
    ra="the CONTENT grep of the tip"; rb="the SYMLINK listing of the tip"
    ca="$(RA=$ra awk -F'\t' '$2 == ENVIRON["RA"] { print $4 }' "$READS_TSV")"; sa="$(RA=$ra awk -F'\t' '$2 == ENVIRON["RA"] { print $7 }' "$READS_TSV")"
    cb="$(RB=$rb awk -F'\t' '$2 == ENVIRON["RB"] { print $4 }' "$READS_TSV")"; sb="$(RB=$rb awk -F'\t' '$2 == ENVIRON["RB"] { print $7 }' "$READS_TSV")"
    [ -n "$ca" ] && [ -n "$sa" ] && [ -n "$cb" ] && [ -n "$sb" ]
    [ -n "$(title_of "$cb")" ] && [ -n "$(title_of "$sb")" ] && [ -n "$(title_of "$ca")" ]
    RA=$ra RB=$rb CA=$ca CB=$cb awk -F'\t' -v OFS='\t' '$2 == ENVIRON["RA"] { $4 = ENVIRON["CB"] } $2 == ENVIRON["RB"] { $4 = ENVIRON["CA"] } { print }' "$READS_TSV" > "$P/tsv-swap-case"
    run reads_table_check "$HOOK" "$P/tsv-swap-case" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the case of $ra names another read: $(title_of "$cb")" ]
    RA=$ra RB=$rb SA=$sa SB=$sb awk -F'\t' -v OFS='\t' '$2 == ENVIRON["RA"] { $7 = ENVIRON["SB"] } $2 == ENVIRON["RB"] { $7 = ENVIRON["SA"] } { print }' "$READS_TSV" > "$P/tsv-swap-short"
    run reads_table_check "$HOOK" "$P/tsv-swap-short" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the short case of $ra names another read: $(title_of "$sb")" ]
    RB=$rb CA=$ca SA=$sa awk -F'\t' -v OFS='\t' '$2 == ENVIRON["RB"] { $4 = ENVIRON["CA"]; $7 = ENVIRON["SA"] } { print }' "$READS_TSV" > "$P/tsv-copy"
    run reads_table_check "$HOOK" "$P/tsv-copy" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the case of $rb names another read: $(title_of "$ca")" ]
    rs="the SIZE of a hidden blob"; rl="$rs, for the report"
    cl="$(RL=$rl awk -F'\t' '$2 == ENVIRON["RL"] { print $4 }' "$READS_TSV")"
    [ -n "$cl" ]
    [[ "$(title_of "$cl")" == *": $rs"* ]]                        # the longer read's title holds the shorter name
    RS=$rs CL=$cl awk -F'\t' -v OFS='\t' '$2 == ENVIRON["RS"] { $4 = ENVIRON["CL"] } { print }' "$READS_TSV" > "$P/tsv-prefix"
    run reads_table_check "$HOOK" "$P/tsv-prefix" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
    [ "$status" -ne 0 ]
    [ "$output" = "the case of $rs names another read: $(title_of "$cl")" ]
    # round 9b (G.2): the block starts at the FIRST begin marker line, so a begin marker doubled, inserted inside the
    # block or just before its end is content, and the block differs from the generator's output (hook_generated_block
    # dropped each until then, and each hand edit stayed green)
    awk -v b="$READS_BEGIN" '{ print } $0 == b && !d { print; d = 1 }' "$HOOK" > "$P/hook-begin-doubled"
    awk -v b="$READS_BEGIN" '{ print } $0 == "# Reads gated by a sibling fact (gate=):" && !d { print b; d = 1 }' "$HOOK" > "$P/hook-begin-inside"
    awk -v b="$READS_BEGIN" -v e="$READS_END" '$0 == e && !d { print b; d = 1 } { print }' "$HOOK" > "$P/hook-begin-before-end"
    for f in doubled inside before-end; do
        [ "$(grep -cxF -- "$READS_BEGIN" "$P/hook-begin-$f")" -eq 2 ]       # the plant landed
        run reads_table_check "$P/hook-begin-$f" "$READS_TSV" "$READS_HEADER_GEN" "$ROMP_DIR/tests"
        [ "$status" -ne 0 ]
        [ "$output" = "the hook's generated block differs from the generator's output for the table" ]
    done
}

# ── round 8b2 (A.8, completed): every row of tests/pre-push-reads.tsv driven through a real push ──
# Round 8b's audit found the table's case column true for 28 of its 63 reads: 27 rows named a case that
# drove another read (or a failing shape, or no shim at all) and 8 ran the hook by hand. The cases below
# are one per row, every row's read in the table order: each puts a tool first on the hook's PATH that,
# for THAT read's argument shape alone (or its input, where two reads share a shape), appends the call
# to a calls file of its own, reads its stdin, prints nothing and exits 0, pushes for real through
# core.hooksPath to a bare remote, asserts the shim FIRED on that shape (a case whose shim never fires
# witnesses nothing), then asserts what the row claims: for a gate row, the refusal naming that read
# and the remote at its base or without the pushed ref; for a row whose reason is the safe side, the
# refusal or the remote that never receives the banned content, by execution. Where a read is consulted
# only beside another read's empty answer (the ANCESTRY, asked only when the commit listing is empty
# and no remote-tracking ref contains the commit), the case silences both shapes of the one tool. The
# table's case column names these cases; the table case after them holds the column to that.
calls_silent_on() {   # <tool> <calls name> <bash test over the shim's "$@">: for that shape a <tool> that appends "<tool> <arguments>" to $TEST_DIR/calls.<name>, reads its stdin, prints nothing and exits 0; the real one for every other shape
    local real real_cat
    real="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v "$1")"
    real_cat="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v cat)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then printf "%%s\\n" %q"$*" >> %q; %q > /dev/null; exit 0; fi\n' "$3" "$1 " "$TEST_DIR/calls.$2" "$real_cat"
        printf 'exec %q "$@"\n' "$real"
    } > "$TEST_DIR/shim/$1"
    chmod 755 "$TEST_DIR/shim/$1"
    export PATH="$TEST_DIR/shim:$PATH"
}
calls_silent_on_text() {   # <tool> <calls name> <fixed text>: the same, for a call whose arguments carry that text (an awk program, a sed script)
    local real real_cat
    real="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v "$1")"
    real_cat="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v cat)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'marker=%q\n' "$3"
        printf 'case "$*" in *"$marker"*) printf "%%s\\n" %q"$*" >> %q; %q > /dev/null; exit 0 ;; esac\n' "$1 " "$TEST_DIR/calls.$2" "$real_cat"
        printf 'exec %q "$@"\n' "$real"
    } > "$TEST_DIR/shim/$1"
    chmod 755 "$TEST_DIR/shim/$1"
    export PATH="$TEST_DIR/shim:$PATH"
}
calls_silent_on_input() {   # <tool> <calls name> <bash test over the shim's "$@"> <fixed text>: the same, for a call of that shape whose INPUT carries that text (two reads of one shape told apart by what they read); the real one, fed the same input, otherwise
    local real
    real="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v "$1")"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'marker=%q; in=%q\n' "$4" "$TEST_DIR/input.$2"
        printf 'if %s; then\n' "$3"
        printf '    cat > "$in"\n'
        printf '    case "$(cat "$in")" in *"$marker"*) printf "%%s\\n" %q"$*" >> %q; exit 0 ;; esac\n' "$1 " "$TEST_DIR/calls.$2"
        printf '    exec %q "$@" < "$in"\n' "$real"
        printf 'fi\n'
        printf 'exec %q "$@"\n' "$real"
    } > "$TEST_DIR/shim/$1"
    chmod 755 "$TEST_DIR/shim/$1"
    export PATH="$TEST_DIR/shim:$PATH"
}
fired() {   # <calls name> <fixed text the shape carries>: the shim fired during the push, on that shape
    [ -s "$TEST_DIR/calls.$1" ]
    grep -q -F -- "$2" "$TEST_DIR/calls.$1"
}
r8b2_tag_naming_the_host() {   # a clean base on the remote (BASE) and an annotated tag over it whose message names the host; tag is the tag object's sha
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" tag -a v1 -m "release one" -m "cut on TESTHOST"
    tag="$(git -C "$REPO" rev-parse refs/tags/v1)"
}
r8b2_merge_with_hidden_link() {   # a merge whose own change is a symlink under -diff carrying the string in its target, gone at the tip: only the combined patch's verdict can name it; sha is the merge
    attributes 'link -diff'
    merge_fixture
    ln -s "seen on TESTHOST" "$REPO/link"
    git -C "$REPO" add link
    git -C "$REPO" commit -qm "the merge adds a link under -diff"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file link "remove it"
}
r8b2_big_file_in_middle_commit() {   # a base on the remote (BASE), then a text file over core.bigFileThreshold carrying the string, removed at the tip: hidden by its size, no attribute accounts for it; leak and blob are its commit and blob
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "seen on TESTHOST"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a text file over the threshold"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$leak:big.txt")"
    remove_file big.txt "remove it"
}
r8b2_binary_turned_text() {   # a base on the remote (BASE), a file binary by its bytes, then the same path as text carrying the string (leak), removed at the tip: the refused line names the previous version when the report reads it
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'ab\0cd\n' > "$REPO/thing"
    git -C "$REPO" add thing
    git -C "$REPO" commit -qm "a binary file"
    commit_file thing "seen on TESTHOST" "now a text file carrying the string"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file thing "remove it"
}
r8b2_merge_text_onto_binary() {   # a merge moving a text file carrying the string onto a path a parent holds a binary file at, gone at the tip (BASE on the remote); merge is its sha
    add_remote
    printf 'ab\0cd\n' > "$REPO/bin.dat"
    git -C "$REPO" add bin.dat
    commit_file notes.txt "seen on TESTHOST" "a binary file and a text file"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1
    git -C "$REPO" mv -f notes.txt bin.dat
    git -C "$REPO" commit -qm "merge side, notes.txt moved onto bin.dat"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    remove_file bin.dat "remove it"
}
r8b2_rename_twin() {   # a base on the remote (BASE), a file binary by its bytes, renamed and made text carrying the string (leak), removed at the tip, an explicit diff attribute on the new path
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    { printf 'line %s\n' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; printf 'x\0y\n'; } > "$REPO/old.txt"
    git -C "$REPO" add old.txt
    git -C "$REPO" commit -qm "a file binary by its bytes"
    git -C "$REPO" mv old.txt new.txt
    { printf 'line %s\n' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; printf 'seen on TESTHOST\n'; } > "$REPO/new.txt"
    git -C "$REPO" add new.txt
    git -C "$REPO" commit -qm "renamed and made text, the string in the change"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file new.txt "remove it"
    attributes 'new.txt diff'
}
r9d_base() {   # the real scanner armed, the identifier scan off, and a clean base on the remote (BASE); the shim directory made
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/shim"
}
feed_git_cut_then() {   # <bash line run after the cut>: a git whose feed answer (the one diff-tree given --text) is kept up to its second diff --git line, the call recorded in calls.feedcut, then the line given runs (exit 1, a SIGKILL of itself); the real git for every other command
    local real_git real_awk
    real_git="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v git)"
    real_awk="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v awk)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then\n' "$FEED_GIT"
        printf '    w=$(mktemp %q); %q "$@" > "$w"\n' "$TEST_DIR/cut.XXXXXX" "$real_git"
        printf '    LC_ALL=C %q '"'"'/^diff --git / { if (++d == 2) exit } { print }'"'"' "$w"\n' "$real_awk"
        printf '    printf "%%s\\n" "git $*" >> %q; rm -f "$w"\n' "$TEST_DIR/calls.feedcut"
        printf '    %s\n' "$1"
        printf 'fi\n'
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "round 8b2 table case: the CONTENT grep of the tip: a git silent on the tip's content grep alone, through a real push of a branch whose tip inherits main's leak, is refused naming the short answer, and the remote never gets the branch" {
    branch_inheriting_mains_leak
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git content-grep '[ "${1:-}" = grep ] && [ "${3:-}" = -i ]'
    push_ref_through_hook_with_shim feature
    fired content-grep "grep --no-color -i -I -l -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of the tip of refs/heads/feature (${sha:0:10}) was scanned with no hit listed (git grep exited 0, a match, and printed no hit line), so the answer is short"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the SYMLINK listing of the tip: a git silent on the symlink pass's plain ls-tree alone, through a real push of a branch whose tip inherits main's symlink leak, is refused on the tree's size, and the remote never gets the branch" {
    branch_inheriting_mains_symlink_leak
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git plain-listing '[ "${1:-}" = ls-tree ] && [ "${2:-}" = -r ] && [ "$#" -eq 3 ]'
    push_ref_through_hook_with_shim feature
    fired plain-listing "ls-tree -r $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/feature (${sha:0:10}) was listed as empty (git ls-tree -r exited 0 and printed no entry) while git cat-file -s gives its tree's size as "*" bytes, so either the listing answered short or the tree holds only empty directories, which git's own index never writes"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the SIZE of the tip's tree: a git silent on the tree's size read alone, over a tip at the EMPTY tree (whose recursive listing is empty, so the size is asked), is refused naming the size read's non-count answer through a real push, and the remote never gets the branch" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q --orphan bare
    git -C "$REPO" rm -rq --cached .
    rm -f "$REPO/base.txt"
    git -C "$REPO" commit -q --allow-empty -m "the empty tree"
    bare="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git tree-size '[ "${1:-}" = cat-file ] && [ "${2:-}" = -s ] && [[ "${3:-}" == *"^{tree}" ]]'
    push_ref_through_hook_with_shim bare
    fired tree-size "cat-file -s $bare^{tree}"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/bare (${bare:0:10}) was listed as empty while its SIZE reads \"\" (git cat-file -s), not a size, so whether the listing is whole is unknown"* ]]
    run remote_holds_ref refs/heads/bare
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the TYPE of the object the tip peels to: a git silent on the peel's type read alone, over a tag of a blob (whose symlink listing exits 128, so the peel is asked), is refused naming the empty type through a real push, and the remote never gets the tag" {
    add_remote
    commit_file f.txt "plain" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" tag -a blobtag "$(git -C "$REPO" rev-parse HEAD:f.txt)" -m "a tag of a blob"
    t="$(git -C "$REPO" rev-parse refs/tags/blobtag)"
    calls_silent_on git peel-type '[ "${1:-}" = cat-file ] && [ "${2:-}" = -t ] && [[ "${3:-}" == *"^{}" ]]'
    push_ref_through_hook_with_shim refs/tags/blobtag
    fired peel-type "cat-file -t $t^{}"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TYPE of the object the tip of refs/tags/blobtag (${t:0:10}) peels to was read as \"\" (git cat-file -t exited 0), not an object type"* ]]
    run remote_holds_ref refs/tags/blobtag
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the SYMLINK TARGET of a link at the tip: a git silent on the link's target read alone, through a real push of a branch whose tip inherits main's symlink leak, is refused on the blob's size, and the remote never gets the branch" {
    branch_inheriting_mains_symlink_leak
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$sha:node_modules")"
    size="$(git -C "$REPO" cat-file -s "$blob")"
    calls_silent_on git link-target "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $blob ]"
    push_ref_through_hook_with_shim feature
    fired link-target "cat-file -p $blob"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SYMLINK TARGET of node_modules at the tip of refs/heads/feature (${sha:0:10}) was read as empty while git cat-file -s gives its size as $size bytes, so the read answered short (git cat-file -p exited 0)"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the SIZE of a symlink target blob: a git silent on the size read alone, over a link to the EMPTY blob (the one target read as empty, so the size is asked), is refused naming the size read's non-count answer through a real push, the remote at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    empty="$(git -C "$REPO" hash-object -w --stdin < /dev/null)"
    git -C "$REPO" update-index --add --cacheinfo "120000,$empty,elink"
    git -C "$REPO" commit -qm "a link over the empty blob"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git link-size "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $empty ]"
    push_main_through_hook_with_shim
    fired link-size "cat-file -s $empty"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SYMLINK TARGET of elink at the tip of refs/heads/main (${sha:0:10}) was read as empty while its SIZE reads \"\" (git cat-file -s), not a size, so whether the target is empty is unknown"* ]]
    at_base
}

@test "round 8b2 table case: the COMMIT listing of a pushed ref: a git silent on the range listing alone, through a real push of a NEW branch whose middle commit adds a banned line, is refused naming the empty listing, and the remote never gets the branch" {
    add_remote
    commit_file base.txt "notes-api" "base"
    commit_file leak.txt "seen on TESTHOST" "leak"
    remove_file leak.txt "remove it"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git range-listing '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]'
    push_main_through_hook_with_shim
    fired range-listing "rev-list $sha --not --remotes"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) were listed as none (git rev-list exited 0 and printed nothing) while no remote-tracking ref contains the pushed commit and the ref is new on the remote, so the listing answered short"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the REMOTE REFS containing the pushed commit: a git silent on the --contains read alone, over a new branch at a commit the remote already holds (the one listing a real rev-list leaves empty), withholds the agreement: the push is refused naming the empty listing, and the remote never gets the branch" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" branch again
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git contains '[ "${1:-}" = for-each-ref ] && [ "${3:-}" = --contains ]'
    push_ref_through_hook_with_shim again
    fired contains "for-each-ref --format=%(refname) --contains $sha refs/remotes/"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/again (${sha:0:10}) were listed as none (git rev-list exited 0 and printed nothing) while no remote-tracking ref contains the pushed commit and the ref is new on the remote, so the listing answered short"* ]]
    run remote_holds_ref refs/heads/again
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the ANCESTRY of the pushed commit over the remote commit: a git silent on BOTH the range listing and the ancestry read (the read is asked only beside an empty listing, so one git silent on both is its shape), through a real push of a ref update whose middle commit adds a banned line, is refused naming the ancestry read's answer, and the remote stays at its base (round 8b2: under --is-ancestor the silent exit 0 WAS the ancestor answer and the leak published)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "seen on TESTHOST" "leak"
    remove_file leak.txt "remove it"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git ancestry '{ [ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]; } || [ "${1:-}" = merge-base ]'
    push_main_through_hook_with_shim
    fired ancestry "rev-list $sha --not --remotes"
    fired ancestry "merge-base "
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) were listed as none, and whether the pushed commit is an ancestor of the remote's ${BASE:0:10} could not be read (git merge-base exited 0 and answered \"\", not a commit)"* ]]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) were listed as none (git rev-list exited 0 and printed nothing)"* ]]
    at_base
}

@test "round 8b2 table case: the PARENT COUNT of a commit: a git silent on rev-list --parents alone, through a real push of a middle-commit leak, is refused naming the empty answer, and the remote stays at its base" {
    leak_in_middle_commit_after_base
    calls_silent_on git parents '[ "${1:-}" = rev-list ] && [ "${2:-}" = --parents ]'
    push_main_through_hook_with_shim
    fired parents "rev-list --parents -n 1 $leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${leak:0:10} could not be read (git rev-list --parents exited 0 and answered \"\", not the commit and its parents)"* ]]
    at_base
}

@test "round 8b2 table case: the ADDED LINES diff of a commit: a git silent on the added-lines diff-tree alone (the --always shape), through a real push of a middle-commit leak, is refused naming the missing marker, and the remote stays at its base" {
    leak_in_middle_commit_after_base
    calls_silent_on git added-diff '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --always "* ]]'
    push_main_through_hook_with_shim
    fired added-diff "diff-tree -p -r -M -c --root --always --no-color --stdin"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${leak:0:10} could not be read (git diff-tree exited 0 and printed no line naming the commit, the marker --always asks for ahead of the diff, so the read answered short)"* ]]
    at_base
}

@test "round 8b2 table case: the LINE COUNT of the added lines: a wc silent on wc -l alone, through a real push of a clean commit, is refused naming the non-count, and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on wc line-count '[ "${1:-}" = -l ] && [ "$#" -eq 1 ]'
    push_main_through_hook_with_shim
    fired line-count "wc -l"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${sha:0:10} could not be counted (wc answered \"\", not a count)"* ]]
    at_base
}

@test "round 8b2 table case: the ADDED LINES grep: a grep silent on the added-lines shape alone (exit 0, a match, no line), through a real push of a middle-commit leak, is refused naming the short answer, and the remote stays at its base" {
    leak_in_middle_commit_after_base
    calls_silent_on grep added-grep '[ "${1:-}" = -a ] && [ "${2:-}" = -i ]'
    push_main_through_hook_with_shim
    fired added-grep "grep -a -i -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${leak:0:10} were grepped with no hit line listed (grep exited 0, a match, and printed no line), so the answer is short"* ]]
    at_base
}

@test "round 8b2 table case: the SORT of the paths a grep named: a sort silent on sort -u alone (the credential scan off, so its own sort -u never runs), through a real push of a middle-commit leak, is refused naming the empty report, and the remote stays at its base" {
    leak_in_middle_commit_after_base
    calls_silent_on sort sort-paths '[ "${1:-}" = -u ] && [ "$#" -eq 1 ]'
    push_main_through_hook_with_shim
    fired sort-paths "sort -u"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${leak:0:10} could not be reported (sort exited 0 and answered nothing for the paths the grep named)"* ]]
    at_base
}

@test "round 8b2 table case: the ADDRESSES log of a commit: a git silent on the addresses log alone, through a real push of a commit stamped under a banned domain, is refused naming the empty answer, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    GIT_AUTHOR_EMAIL=dev@testhost.example GIT_COMMITTER_EMAIL=dev@testhost.example git -C "$REPO" commit -q --allow-empty -m "stamped under a banned domain"
    c="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git addresses '[ "${1:-}" = log ] && [[ "${4:-}" == --format=authored* ]]'
    push_main_through_hook_with_shim
    fired addresses "log -1 --no-show-signature --format=authored"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDRESSES of commit ${c:0:10} could not be read (git log exited 0 and answered \"\", not the two stamped roles)"* ]]
    at_base
}

@test "round 8b2 table case: the MESSAGE log of a commit: a git silent on the message log alone, through a real push of a commit whose message body names the host, is refused naming the missing head marker, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" commit -q --allow-empty -m "a clean subject" -m "cut on TESTHOST"
    c="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git message-log '[ "${1:-}" = log ] && [[ "${4:-}" == --format=message* ]]'
    push_main_through_hook_with_shim
    fired message-log "log -1 --no-show-signature --format=message"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the MESSAGE of commit ${c:0:10} could not be read (git log exited 0 and answered \"\" on its first line, not the marker line the format asks for ahead of the message)"* ]]
    at_base
}

@test "round 8b2 table case: the MESSAGE grep: a grep silent on the message shape alone (exit 0, a match, no line), through a real push of a commit whose message names the host, is refused naming the short answer, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" commit -q --allow-empty -m "cut on TESTHOST"
    c="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on grep message-grep '[ "${1:-}" = -in ]'
    push_main_through_hook_with_shim
    fired message-grep "grep -in -a -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the MESSAGE of commit ${c:0:10} was grepped with no hit line listed (grep exited 0, a match, and printed no line), so the answer is short"* ]]
    at_base
}

@test "round 8b2 table case: the TYPE of a pushed object: a git silent on the pushed tag's type read alone, through a real push of a tag whose message names the host, is refused naming the empty type, and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    calls_silent_on git object-type "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -t ] && [ \"\${3:-}\" = $tag ]"
    push_ref_through_hook_with_shim refs/tags/v1
    fired object-type "cat-file -t $tag"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TYPE of the object refs/tags/v1 pushes (${tag:0:10}) was read as \"\" (git cat-file -t exited 0), not an object type, so whether it is an annotated tag is unknown"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the OBJECT of a tag: a git silent on the tag object's read alone, through a real push of a tag whose message names the host, is refused on the object's size, and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    size="$(git -C "$REPO" cat-file -s "$tag")"
    calls_silent_on git tag-object "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $tag ]"
    push_ref_through_hook_with_shim refs/tags/v1
    fired tag-object "cat-file -p $tag"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the OBJECT of tag refs/tags/v1 (${tag:0:10}) was read short (git cat-file -p exited 0 and its capture holds 0 bytes where git cat-file -s gives the object's size as $size), which ends the peel here"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the SIZE of a tag object: a git silent on the tag's size read alone, through a real push of a tag whose message names the host, is refused naming the two answers, and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    size="$(git -C "$REPO" cat-file -s "$tag")"
    calls_silent_on git tag-size "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $tag ]"
    push_ref_through_hook_with_shim refs/tags/v1
    fired tag-size "cat-file -s $tag"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the OBJECT of tag refs/tags/v1 (${tag:0:10}) was captured while its SIZE reads \"\" (git cat-file -s) and the capture's BYTE COUNT \"$size\" (wc -c), not two counts"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the BYTE COUNT of a tag capture: a wc silent on wc -c over the tag capture alone (keyed on its input, which begins with the object line), through a real push of a tag whose message names the host, is refused naming the two answers, and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    size="$(git -C "$REPO" cat-file -s "$tag")"
    calls_silent_on_input wc tag-count '[ "${1:-}" = -c ] && [ "$#" -eq 1 ]' "object "
    push_ref_through_hook_with_shim refs/tags/v1
    fired tag-count "wc -c"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the OBJECT of tag refs/tags/v1 (${tag:0:10}) was captured while its SIZE reads \"$size\" (git cat-file -s) and the capture's BYTE COUNT \"\" (wc -c), not two counts"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the -z listing of the tip: a git silent on the verdict check's ls-tree -r -z -l alone, through a real push over a hidden file the remote holds at the tip, is refused on the symlink pass's entry count, and the remote stays at its base" {
    hidden_file_on_remote_then_clean_commit
    calls_silent_on git z-listing '[ "${1:-}" = ls-tree ] && [ "${3:-}" = -z ]'
    push_main_through_hook_with_shim
    fired z-listing "ls-tree -r -z -l $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was listed short or long for the BINARY VERDICT check (git ls-tree -r -z -l exited 0 and listed 0 entries where the symlink pass's git ls-tree -r of the same tree listed 3)"* ]]
    at_base
}

@test "round 8b2 table case: the READ LIST of the grep of the tip: a git silent on the read list's grep alone, through a real push of a clean tip, sends every regular file with bytes to the byte judge, which refuses each text file as hidden (the safe side): the push is refused and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on git read-list '[ "${1:-}" = grep ] && [ "${5:-}" = -z ]'
    push_main_through_hook_with_shim
    fired read-list "grep --no-color -I -l -z -e  $sha --"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: base.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute reads unspecified"* ]]
    [[ "$output" == *"romp pre-push: clean.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute reads unspecified"* ]]
    at_base
}

@test "round 8b2 table case: the ENTRY COUNT of the -z listing: a grep silent on the whole-entry grep -c over the rewritten -z listing alone, through a real push of a clean tip, is refused naming the non-count, and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on grep entry-count '[ "${1:-}" = -c ] && [[ "${2:-}" == "^[0-7]"* ]] && [[ "${3:-}" == */listing.nl ]]'
    push_main_through_hook_with_shim
    fired entry-count "listing.nl"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) could not be counted for the BINARY VERDICT check (the -z listing's entries counted as \"\" and the symlink pass's as \"2\", not two counts)"* ]]
    at_base
}

@test "round 8b2 table case: the TIP CANDIDATES join: an awk silent on the tip candidates program alone, through a real push over a hidden file the remote holds at the tip, is refused naming the short join, and the remote stays at its base" {
    hidden_file_on_remote_then_clean_commit
    calls_silent_on_text awk tip-candidates 'printf "tip\t'
    push_main_through_hook_with_shim
    fired tip-candidates 'printf "tip\t'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was joined short with the grep's read list for the BINARY VERDICT check (the join appended 0 candidate rows where the -z listing names 3 regular files with bytes and the grep's read list 2 of them, so the count expected is 1; awk and tr exited 0)"* ]]
    at_base
}

@test "round 8b2 table case: the FILE COUNT of the -z listing: a grep silent on grep -c -E over the rewritten -z listing alone, through a real push of a clean tip, is refused naming the non-count, and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on grep file-count '[ "${1:-}" = -c ] && [ "${2:-}" = -E ] && [[ "${4:-}" == */listing.nl ]]'
    push_main_through_hook_with_shim
    fired file-count "grep -c -E"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) could not be counted for the BINARY VERDICT check (grep -c counted the -z listing's regular files with bytes as \"\" and the grep's read list as \"2\", not two counts)"* ]]
    at_base
}

@test "round 8b2 table case: the LINE COUNT of the read list: a grep silent on grep -c . over the rewritten read list alone, through a real push of a clean tip, is refused naming the non-count, and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on grep read-count '[ "${1:-}" = -c ] && [ "${2:-}" = . ] && [[ "${3:-}" == */read.nl ]]'
    push_main_through_hook_with_shim
    fired read-count "read.nl"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) could not be counted for the BINARY VERDICT check (grep -c counted the -z listing's regular files with bytes as \"2\" and the grep's read list as \"\", not two counts)"* ]]
    at_base
}

@test "round 8b2 table case, its row retired in round 9a: the newline test of a scratch listing runs no wc: a wc silent on wc -c fed by a pipe alone (the test's pipeline until round 9a; the byte counts read a file), through a real push of a clean tip, never fires, and the push passes, the remote at the tip (H.3 took the tool out of the test and its row out of the table; the round 9a newline case is the retired row's twin)" {
    clean_tip_after_base
    calls_silent_on wc newline-count '[ "${1:-}" = -c ] && [ "$#" -eq 1 ] && [ -p /dev/stdin ]'
    run _hook_in "$REPO" -c 'printf "a\\n" | wc -c; echo "status $?"'
    [ "$output" = "status 0" ]                                     # the shim answers nothing for that shape when it runs
    rm -f "$TEST_DIR/calls.newline-count"
    push_main_through_hook_with_shim
    [ ! -e "$TEST_DIR/calls.newline-count" ]                       # the hook ran no wc on a pipe
    [ "$status" -eq 0 ]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$sha" ]
}

@test "round 8b2 table case: the REWRITE of a scratch listing: a tr silent on the NUL-to-newline rewrite alone, through a real push of a clean tip, is refused naming the rewrite's byte count against its input's, and the remote stays at its base" {
    clean_tip_after_base
    n="$(git -C "$REPO" ls-tree -r -z -l "$sha" | wc -c | tr -d ' ')"
    calls_silent_on tr rewrite '[ "$#" -eq 2 ] && [ "${1:-}" = '"'"'\0'"'"' ] && [ "${2:-}" = '"'"'\n'"'"' ]'
    push_main_through_hook_with_shim
    fired rewrite 'tr \0 \n'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the rewrite of listing wrote 0 bytes for $n read; tr exited 0)"* ]]
    at_base
}

@test "round 8b2 table case: the BYTE COUNT of a scratch listing: a wc silent on wc -c reading a file alone (the byte counts; the newline test's wc read a pipe until round 9a), through a real push of a clean tip, is refused naming the non-count, and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on wc byte-count '[ "${1:-}" = -c ] && [ "$#" -eq 1 ] && [ -f /dev/stdin ]'
    push_main_through_hook_with_shim
    fired byte-count "wc -c"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the byte count's wc answered \"\" for listing, not a count)"* ]]
    at_base
}

@test "round 8b2 table case: the CHANGED PATHS listing of a commit: a git silent on the combined --raw -c listing alone, through a real push of a middle commit adding a hidden file, is refused on the path its numstat names, and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_silent_on git changed-paths '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --raw "*" -c "* ]]'
    push_main_through_hook_with_shim
    fired changed-paths "diff-tree -r --raw --no-renames --root -c -z --no-commit-id $leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CHANGED PATHS of commit ${leak:0:10} were listed short for the BINARY VERDICT check (git diff-tree --raw exited 0 and its listing lacks notes.txt, a path git diff-tree --numstat answered for)"* ]]
    at_base
}

@test "round 8b2 table case: the COMBINED PATCH of a merge: a git silent on the combined patch alone (the --no-commit-id shape; the added-lines diff asks --always), through a real push of a merge adding a hidden link that carries the string, is refused naming the path with no verdict, and the remote stays at its base" {
    r8b2_merge_with_hidden_link
    calls_silent_on git combined-patch '[ "${1:-}" = diff-tree ] && [[ " $* " == *" -p "*" --no-commit-id "* ]]'
    push_main_through_hook_with_shim
    fired combined-patch "diff-tree -p -r -M -c --root --no-commit-id --no-color $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for link, a path the merge changes)"* ]]
    at_base
}

@test "round 8b2 table case: the SECTION ROWS of a combined patch: an awk silent on the section parser alone, through a real push of a merge adding a hidden link that carries the string, leaves every merge path a short read at the join: refused naming the path, the remote at its base" {
    r8b2_merge_with_hidden_link
    calls_silent_on_text awk section-rows 'hdr && /^Binary files /'
    push_main_through_hook_with_shim
    fired section-rows "Binary files"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for link, a path the merge changes)"* ]]
    at_base
}

@test "round 8b2 table case: the PER-PARENT listing of a merge: a git silent on diff-tree --raw -m alone, through a real push of a merge moving content two parents held to a third path, leaves the moved path no rename candidate and so a short read at the join: refused naming it, the remote at its base" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    calls_silent_on git per-parent '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --raw "*" -m "* ]]'
    push_main_through_hook_with_shim
    fired per-parent "diff-tree -r --raw --no-renames -m -z --no-commit-id $merge"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${merge:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for b.txt, a path the merge changes)"* ]]
    at_base
}

@test "round 8b2 table case: the RENAME CANDIDATES of a merge: an awk silent on the rename candidates program alone, through a real push of a merge moving content two parents held to a third path, leaves the moved path a short read at the join: refused naming it, the remote at its base" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    calls_silent_on_text awk rename-candidates 'in gone) print'
    push_main_through_hook_with_shim
    fired rename-candidates 'in gone) print'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${merge:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for b.txt, a path the merge changes)"* ]]
    at_base
}

@test "round 8b2 table case: the NUMSTAT of a commit: a git silent on diff-tree --numstat alone, through a real push of a middle commit adding a hidden file, is refused naming the path the numstat did not answer for, and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_silent_on git numstat '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --numstat "* ]]'
    push_main_through_hook_with_shim
    fired numstat "diff-tree -r --numstat -z --no-commit-id -M --root $leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${leak:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes and printed no verdict for notes.txt)"* ]]
    at_base
}

@test "round 8b2 table case: the EMPTY TREE name: a git silent on hash-object -t tree alone, through a real push of a type change, is refused naming the empty answer, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    type_change_to_symlink
    calls_silent_on git empty-tree '[ "${1:-}" = hash-object ] && [ "${2:-}" = -t ] && [ "${3:-}" = tree ]'
    push_main_through_hook_with_shim
    fired empty-tree "hash-object -t tree --stdin"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${sha:0:10} could not be read (git hash-object, asked for the empty tree's name, answered nothing)"* ]]
    at_base
}

@test "round 8b2 table case: the JOIN of the verdicts of a commit: an awk silent on the join's program alone, through a real push of a middle commit adding a hidden file, is refused naming the count its awk did not record, and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_silent_on_text awk verdict-join 'ENVIRON["ROMP_SHORT_FILE"]'
    push_main_through_hook_with_shim
    fired verdict-join 'ROMP_SHORT_FILE'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the JOIN of commit ${leak:0:10}'s verdicts could not be made for the BINARY VERDICT check (its pipeline exited 0 and its awk recorded \"\" as the count of candidate rows it printed, not a count"* ]]
    at_base
}

@test "round 8b2 table case: the BYTE COUNTS of a hidden blob: a git silent on the hidden blob's content read alone, through a real push of a middle commit adding a hidden file, is refused on the blob's size, and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_silent_on git blob-bytes "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [ \"\${3:-}\" = $blob ]"
    push_main_through_hook_with_shim
    fired blob-bytes "cat-file blob $blob"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of notes.txt in commit ${leak:0:10}, which git calls binary and the identifier scan therefore skipped, was read as 0 bytes while git cat-file -s gives its size as $size bytes, so the read answered short (git cat-file blob exited 0)"* ]]
    at_base
}

@test "round 8b2 table case: the SIZE of a hidden blob: a git silent on the size read alone, over an EMPTY file under -diff in a middle commit (the one hidden blob read as 0 bytes, so the size is asked), is refused naming the size read's non-count answer through a real push, the remote at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'empty.txt -diff\n' > "$REPO/.git/info/attributes"
    : > "$REPO/empty.txt"
    git -C "$REPO" add empty.txt
    git -C "$REPO" commit -qm "an empty file under -diff"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    empty="$(git -C "$REPO" rev-parse "$leak:empty.txt")"
    remove_file empty.txt "remove it"
    calls_silent_on git blob-size "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $empty ]"
    push_main_through_hook_with_shim
    fired blob-size "cat-file -s $empty"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of empty.txt in commit ${leak:0:10}, which git calls binary and the identifier scan therefore skipped, was read as 0 bytes while its SIZE reads \"\" (git cat-file -s), not a size, so whether the blob is empty is unknown"* ]]
    at_base
}

@test "round 9d table case: the CREDENTIAL FEED of the push: a git silent on the one git whose arguments carry --text (exit 0, its stdin drained), the identifier scan off, through a real push of a credential, is refused naming the commits the feed ended short of, and the remote stays at its base (this slot held the REPOSITORY ROOT's table case, a read retired in round 9)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    calls_silent_on git feed "$FEED_GIT"
    push_main_through_hook_with_shim
    fired feed "--text"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push was read short (git diff-tree exited 0 and ended after 0 of the 1 commits it was given); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9d: the CREDENTIAL FEED of the push, the refuters' within-commit cut with exit 1 in place of 0 (the feed's git answer kept up to its second diff --git line), through a real push, is refused naming the feed's status, and the remote stays at its base (this slot held the COUNT of commits' table case, a read retired in round 9; at cad898dd2 gitleaks read the same cut of its own git log past that status and published)" {
    r9d_base
    two_files_credential_second
    feed_git_cut_then 'exit 1'
    push_main_through_hook_with_shim
    [ -s "$TEST_DIR/calls.feedcut" ]
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push could not be read (a stage of git diff-tree, tr and awk exited 1); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9d: the CREDENTIAL FEED of the push through a tr silent on its NUL mapping (exit 0, its input drained): both markers of every commit are lost, and the push is refused naming the commits the feed ended short of, the remote at its base (this slot held the COLOUR STRIP's table case, a read retired in round 9)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    calls_silent_on tr feedtr '[[ "${1:-}" == *000 ]]'
    push_main_through_hook_with_shim
    [ -s "$TEST_DIR/calls.feedtr" ]
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push was read short (git diff-tree exited 0 and ended after 0 of the 1 commits it was given); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9d table case: the BYTE COUNT line of the scanner log: an awk silent on the byte figure's program alone, through a real push of a credential under the real scanner, is refused naming the empty answer, neither a byte count nor a count of such lines, and the remote never gets the branch (re-aimed in place from the COMMIT COUNT line's table case, the row it replaces)" {
    r9d_base
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    calls_silent_on_text awk byte-line '$3 == "scanned"'
    push_main_through_hook_with_shim
    fired byte-line '$3 == "scanned"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan could not be judged: its byte-count read answered \"\" (awk exited 0), neither a byte count nor a count of such lines; the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 8b2 table case: the ADDRESS DOMAIN grep: a grep silent on the domain grep alone (exit 0 IS the hit), through real pushes of a commit and of a tag stamped under a clean domain, refuses each address (the strict side): the remote at its base and without the tag" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    GIT_AUTHOR_EMAIL=dev@clean.example GIT_COMMITTER_EMAIL=dev@clean.example git -C "$REPO" commit -q --allow-empty -m "stamped clean"
    c="$(git -C "$REPO" rev-parse HEAD)"
    GIT_COMMITTER_EMAIL=dev@clean.example git -C "$REPO" tag -a v1 "$BASE" -m "release one"
    t="$(git -C "$REPO" rev-parse refs/tags/v1)"
    calls_silent_on_input grep domain '[ "${1:-}" = -qi ] && [ "${2:-}" = -F ]' "clean.example"
    push_main_through_hook_with_shim
    fired domain "grep -qi -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${c:0:10} is authored as <dev@clean.example>, an address this clone is not configured to use, whose domain carries a personal identifier"* ]]
    at_base
    rm -f "$TEST_DIR/calls.domain"
    push_ref_through_hook_with_shim refs/tags/v1
    fired domain "grep -qi -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: tag refs/tags/v1 (${t:0:10}) is tagged as <dev@clean.example>, an address this clone is not configured to use, whose domain carries a personal identifier"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the CHOSEN ADDRESSES of this clone: a git silent on config --get-all user.email alone chooses no address, so a banned-domain stamp the clone IS configured to use is judged (the strict side): the control push passes, the silenced one is refused, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" config user.email dev@testhost.example
    GIT_AUTHOR_EMAIL=dev@testhost.example GIT_COMMITTER_EMAIL=dev@testhost.example git -C "$REPO" commit -q --allow-empty -m "stamped by the clone's own choice"
    c="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim                              # the control: the clone chose the address, so it passes
    [ "$status" -eq 0 ]
    git -C "$TEST_DIR/remote.git" update-ref refs/heads/main "$BASE"
    git -C "$REPO" update-ref refs/remotes/origin/main "$BASE"
    calls_silent_on git chosen '[ "${1:-}" = config ] && [ "${2:-}" = --get-all ] && [ "${3:-}" = user.email ]'
    push_main_through_hook_with_shim
    fired chosen "config --get-all user.email"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${c:0:10} is authored as <dev@testhost.example>, an address this clone is not configured to use, whose domain carries a personal identifier"* ]]
    at_base
}

@test "round 8b2 table case: the SYMLINK TARGET grep: a grep silent on the target grep alone (exit 0 IS the hit), through a real push of a branch whose tip holds a clean link the remote has, refuses the link (the strict side), and the remote never gets the branch" {
    add_remote
    ln -s ./base.txt "$REPO/link"
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" add link
    git -C "$REPO" commit -qm "a clean link"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file c.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on_input grep link-grep '[ "${1:-}" = -qi ] && [ "${2:-}" = -F ]' "./base.txt"
    push_ref_through_hook_with_shim feature
    fired link-grep "grep -qi -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the tip of refs/heads/feature (${sha:0:10}) would publish a personal identifier"* ]]
    [[ "$output" == *"in the SYMLINK TARGET of link -> ./base.txt"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the REPLACE REFS listing: a git silent on the replace-ref listing alone, over a clone that HAS a replace ref, leaves the scans reading what the push transfers (both read with replacement off): a clean tip replaced by a leaking commit publishes the clean one and never the leak, and a leaking tip replaced by a clean commit is refused on its own leak" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "seen on TESTHOST" "leak"
    L="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" reset -q --hard "$BASE"
    commit_file clean.txt "nothing to see" "clean"
    C="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" replace "$C" "$L"                               # the pushed tip C reads as the leaking L wherever replacement is on
    calls_silent_on git replace-refs '[ "${1:-}" = for-each-ref ] && [[ "${3:-}" == refs/replace/* ]]'
    push_main_through_hook_with_shim
    fired replace-refs "for-each-ref --format=%(refname) refs/replace/"
    [ "$status" -eq 0 ]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$C" ]
    run git -C "$TEST_DIR/remote.git" cat-file -e "$L"
    [ "$status" -ne 0 ]                                           # the leak never reached the remote
    git -C "$REPO" replace -d "$C" > /dev/null
    git -C "$TEST_DIR/remote.git" update-ref refs/heads/main "$BASE"
    git -C "$REPO" update-ref refs/remotes/origin/main "$BASE"
    git -C "$REPO" update-ref refs/heads/main "$L"
    git -C "$REPO" replace "$L" "$C"                               # the pushed tip is L itself, reading as the clean C wherever replacement is on
    rm -f "$TEST_DIR/calls.replace-refs"
    push_main_through_hook_with_shim
    fired replace-refs "for-each-ref --format=%(refname) refs/replace/"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the tip of refs/heads/main (${L:0:10}) would publish a personal identifier in:"* ]]
    [[ "$output" == *"leak.txt"* ]]
    at_base
}

@test "round 8b2 table case: the TIP LISTING join against the read list: an awk silent on that join alone disarms that one gate while the listing and its other gates stand: through a real push over a hidden file the remote holds at the tip, the file is still named and the remote stays at its base" {
    hidden_file_on_remote_then_clean_commit
    calls_silent_on_text awk tip-listing-join 'listed[substr($0, i + 1)] = 1'
    push_main_through_hook_with_shim
    fired tip-listing-join 'listed[substr($0, i + 1)] = 1'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    at_base
}

@test "round 8b2 table case: the TIP BLOBS of the -z listing: an awk silent on the tip's blob set alone sends every per-commit candidate to the byte judge (the safe side): through a real push over a hidden file the remote holds at the tip, the file is still named and the remote stays at its base" {
    hidden_file_on_remote_then_clean_commit
    calls_silent_on_text awk tip-blobs 'f[1] == "120000") print f[3]'
    push_main_through_hook_with_shim
    fired tip-blobs 'print f[3]'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    at_base
}

@test "round 8b2 table case: the LISTING join of a commit against its verdicts: an awk silent on that join alone disarms that one gate while the listing and the verdicts stand: through a real push of a middle commit adding a hidden file, the file is still named and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_silent_on_text awk listing-join 'listed[$0] = 1'
    push_main_through_hook_with_shim
    fired listing-join 'listed[$0] = 1'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt in commit ${leak:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    at_base
}

@test "round 8b2 table case: the ERR line of the scanner log: an awk silent on the ERR line's program alone, beside a scanner that logs an ERR line and runs the real scan, is refused naming the read's empty answer, neither none nor an error line, and the remote never gets the branch (round 8b3: the count this case left to judge until then can count a commit whole whose credential file the scanner dropped; since round 9 the ERR line comes from a scanner wrapper, gitleaks running no git)" {
    r9d_base
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    scanner_wrapper 'echo "1:00AM ERR something went wrong" >&2'
    calls_silent_on_text awk err-line '$2 == "ERR"'
    push_main_through_hook_with_shim
    fired err-line '$2 == "ERR"'
    [ "$status" -ne 0 ]
    [[ "$output" != *"gitleaks logged an error"* ]]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan could not be judged: its log's error-line read answered \"\" (awk exited 0), neither the word none nor an error line"* ]]
    at_base
}

@test "round 9d: the credential scan lists its commits through the listing and the gates it shares with the identifier scan: a git silent on the range listing alone (the identifier scan off) is refused naming the empty listing, where the range probe it replaced kept the range for the scanner; and a range listing that exits 1 is refused naming the credential scan; the remote stays at its base (this slot held the RANGE probe's table case, a read retired in round 9)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git listing '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]'
    push_main_through_hook_with_shim
    [ -s "$TEST_DIR/calls.listing" ]
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) were listed as none (git rev-list exited 0 and printed nothing) while no remote-tracking ref contains the pushed commit and it is not an ancestor of the remote's ${BASE:0:10}, so the listing answered short"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    at_base
    rm -f "$TEST_DIR/shim/git"; export PATH="${PATH//"$TEST_DIR/shim:"/}"   # git_refusing resolves the real git on PATH: the silent shim leaves first
    git_refusing '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]' 1 "shim: rev-list refused"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) could not be listed for the credential scan (git rev-list exited 1); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9d: the CREDENTIAL FEED of the push from a git that prints a 40-digit line ahead of its answer is refused: that line is not the head marker of commit 1, and the remote stays at its base (this slot held the log.showRoot read's table case, a read retired in round 9)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    git_shim "if $FEED_GIT; then echo 1111111111111111111111111111111111111111; exec \"\$real_git\" \"\$@\"; fi"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push was read short (git diff-tree exited 0 and did not open commit 1 of the 1 it was given with the line naming it, the marker --always asks for ahead of each diff); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 8b2 table case: the diff attribute of a hidden path (check-attr): a git silent on check-attr alone leaves the refused line's tail open (both remedies printed): through a real push of a hidden file carrying the string the push is refused and the remote never gets the branch" {
    add_remote
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git check-attr '[ "${1:-}" = check-attr ]'
    push_main_through_hook_with_shim
    fired check-attr "check-attr -z diff -- notes.txt"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr answered nothing for the path asked), so whether an attribute of its path accounts for the verdict is unknown"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the diff driver's binary key: a git silent on config --type=bool diff.<driver>.binary alone leaves the label at the two facts: through a real push of a middle commit hiding a file carrying the string behind a driver, the push is refused and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'notes.txt diff=zzdrv\n' > "$REPO/.git/info/attributes"
    git -C "$REPO" config diff.zzdrv.binary true
    commit_file notes.txt "seen on TESTHOST" "a banned string in a file git calls binary by its driver"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file notes.txt "remove it"
    calls_silent_on git driver-key '[ "${1:-}" = config ] && [ "${2:-}" = --type=bool ] && [[ "${3:-}" == diff.*.binary ]]'
    push_main_through_hook_with_shim
    fired driver-key "config --type=bool diff.zzdrv.binary"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads zzdrv, so no attribute of its path accounts for the verdict"* ]]
    at_base
}

@test "round 8b2 table case: the SIZE of a hidden blob, for the report: a git silent on the report's cat-file -s alone leaves the size out of the two-fact line: through a real push of a middle commit adding a text file over core.bigFileThreshold carrying the string, the push is refused and the remote stays at its base" {
    r8b2_big_file_in_middle_commit
    calls_silent_on git report-size "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $blob ]"
    push_main_through_hook_with_shim
    fired report-size "cat-file -s $blob"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: big.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is  bytes; core.bigFileThreshold is 100 in this clone's configuration)"* ]]
    at_base
}

@test "round 8b2 table case: the core.bigFileThreshold read, for the report: a git silent on config core.bigFileThreshold alone reads as the key unset in the two-fact line: through a real push of a middle commit adding a text file over the threshold carrying the string, the push is refused and the remote stays at its base" {
    r8b2_big_file_in_middle_commit
    calls_silent_on git report-threshold '[ "${1:-}" = config ] && [ "${2:-}" = core.bigFileThreshold ]'
    push_main_through_hook_with_shim
    fired report-threshold "config core.bigFileThreshold"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: big.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is "*" bytes; core.bigFileThreshold is not set in this clone's configuration)"* ]]
    at_base
}

@test "round 8b2 table case: the parent count re-read from pcount, for the report: an awk silent on the pcount program alone leaves the previous version unread: through a real push of a commit turning a binary file into text carrying the string, the push is refused on the two-fact line and the remote stays at its base" {
    r8b2_binary_turned_text
    calls_silent_on_text awk pcount '$1 == r { print $2; exit }'
    push_main_through_hook_with_shim
    fired pcount '$1 == r'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: thing in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    at_base
}

@test "round 8b2 table case: the rename source, for the report: a git silent on the report's diff-tree --raw -M alone leaves the previous version unnamed: through a real push of a rename made text carrying the string, the push is refused on the two-fact line and the remote stays at its base" {
    r8b2_rename_twin
    calls_silent_on git rename-source '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --raw -M -z --root --no-commit-id "* ]]'
    push_main_through_hook_with_shim
    fired rename-source "diff-tree -r --raw -M -z --root --no-commit-id $leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: new.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads set, so no attribute of its path accounts for the verdict (the diff read it as a rename, so the attribute of the path it came from counted too) (the blob is"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    at_base
}

@test "round 8b2 table case: the previous version's bytes, one-parent, for the report: a git silent on the parent's version read alone leaves the two-fact line: through a real push of a commit turning a binary file into text carrying the string, the push is refused and the remote stays at its base" {
    r8b2_binary_turned_text
    calls_silent_on git prev-version "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [[ \"\${3:-}\" == $leak^:* ]]"
    push_main_through_hook_with_shim
    fired prev-version "cat-file blob $leak^:thing"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: thing in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    at_base
}

@test "round 8b2 table case: the previous version's bytes, a merge parent, for the report: a git silent on each parent's version read alone leaves the two-fact line: through a real push of a merge moving a text file carrying the string onto a binary file's path, the push is refused and the remote stays at its base" {
    r8b2_merge_text_onto_binary
    calls_silent_on git parent-version "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [[ \"\${3:-}\" == $merge^* ]]"
    push_main_through_hook_with_shim
    fired parent-version "cat-file blob $merge^1:bin.dat"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: bin.dat in commit ${merge:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    at_base
}

@test "round 9d: the CREDENTIAL FEED of the push from a git that prints the tip's name again after its whole answer is refused: a line after the tail marker of the last commit (the awk drains it and records where it fell), and the remote stays at its base (this slot held the root-commit probe's table case, a read retired in round 9)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    git_shim "if $FEED_GIT; then \"\$real_git\" \"\$@\"; s=\$?; \"\$real_git\" rev-parse HEAD; exit \$s; fi"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push was read short (git diff-tree exited 0 and printed a line after the tail marker of the last of the 1 commits it was given); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9d: a scanner run silent (exit 0, nothing logged, nothing read) is refused as unscanned, having logged no byte figure: through a real push of a credential the remote never gets the branch (re-aimed from the scanner's argument list's table case, a row retired in round 9: the list names no tool now that gitleaks runs no git, so it is no census read)" {
    unset ROMP_NO_GITLEAKS
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    mkdir -p "$TEST_DIR/scanner" "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = version ]; then echo 8.25.0; exit 0; fi\n'          # a release at the floor's answer: the version read precedes the run (round 10b)
        printf 'printf "%%s\\n" "gitleaks $*" >> %q; exit 0\n' "$TEST_DIR/calls.scanner"
    } > "$TEST_DIR/scanner/gitleaks"
    chmod 755 "$TEST_DIR/scanner/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/scanner/gitleaks"
    push_main_through_hook_with_shim
    grep -q -F -- "gitleaks dir . --no-banner --redact -v --no-color --exit-code 2" "$TEST_DIR/calls.scanner"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan reported 0 byte-count lines where it writes one, so what it read is unknown; the scan is incomplete, so the push is refused"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

# ── round 8b3 (A.8, the END of every answer): every row of tests/pre-push-reads.tsv driven with its answer CUT SHORT ──
# A fact that bounds an answer's START (a head marker, a non-empty answer, the first word naming the
# object, an emptiness compared with a size) says nothing of its END: the round 8b2 audit found four reads
# publishing through real pushes with their real answer cut short and exit 0 (the commit listing cut to
# its tip, the added lines cut to their marker, the addresses cut inside the committed address, a symlink
# target cut to ten bytes) while each row stated a fact, and this round's cases found three more of the kind
# (the symlink listing cut inside a link's mode, the -z listing inside a hidden file's record, the
# repository root to a main clone's path) and two own= reads publishing while their rows said safe (the
# scanner log's ERR line beside a silent awk, and the chosen addresses under an answer cut to a prefix that
# a commit is stamped with), each closed, each closure's case red at 6e34a9d89 by publication. The cases
# below are one per row that has an
# answer to cut, in the table's order, each named in the row's short column (a row with none says why
# there): each puts a tool first on the hook's PATH that, for THAT read's argument shape alone (or its
# input), runs the REAL tool, cuts its answer short by the cut the case names (bytes:N keeps the first N
# bytes, less:N drops the last N, lines:N keeps the first N lines, and since round 9d before:<prefix>:<n> keeps the
# bytes ahead of the n-th line that begins with the prefix), prints the cut answer and exits 0 (a
# real non-zero exit passes through uncut), and records the call with the whole and the cut byte counts;
# the case pushes for real through core.hooksPath, asserts the shim FIRED with an answer cut short
# (fired_short: fewer bytes than the whole), then asserts what the row claims of the END: the refusal
# naming the read, or, for a safe-side row, the refusal or the remote that never receives new content.
# The table case holds the short column to these cases.
calls_short_on_shim() {   # <plain|text|input> <tool> <calls name> <cut> <shape: a bash test over "$@", or the fixed text> [<input text>]: the shim of the three helpers below
    local how=$1 tool=$2 name=$3 cut=$4 shape=$5 p real r_cat r_wc r_head r_mktemp r_rm r_awk keep b_rest b_n b_pre
    p=${PATH//"$TEST_DIR/shim:"/}
    real="$(PATH=$p command -v "$tool")"; r_cat="$(PATH=$p command -v cat)"; r_wc="$(PATH=$p command -v wc)"; r_awk="$(PATH=$p command -v awk)"
    r_head="$(PATH=$p command -v head)"; r_mktemp="$(PATH=$p command -v mktemp)"; r_rm="$(PATH=$p command -v rm)"
    case "$cut" in
        bytes:*) keep="k=${cut#bytes:}" ;;
        less:*)  keep="k=\$((n - ${cut#less:})); [ \"\$k\" -ge 0 ] || k=0" ;;
        lines:*) keep="k=\$($(printf %q "$r_head") -n ${cut#lines:} \"\$w\" | $(printf %q "$r_wc") -c); k=\${k//[[:space:]]/}" ;;
        before:*)                                       # round 9d: the bytes ahead of the n-th line that begins with the prefix (before:<prefix>:<n>)
            b_rest=${cut#before:}; b_n=${b_rest##*:}; b_pre=${b_rest%:*}
            keep="k=\$(LC_ALL=C $(printf %q "$r_awk") -v n=$b_n -v p=$(printf %q "$b_pre") 'index(\$0, p) == 1 && ++c == n { exit } { b += length(\$0) + 1 } END { print b + 0 }' \"\$w\")" ;;
        *) echo "calls_short_on: unknown cut $cut" >&2; return 1 ;;
    esac
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'in=""\n'
        case "$how" in
            plain) printf 'if %s; then\n' "$shape" ;;
            text)  printf 'marker=%q\n' "$shape"; printf 'if [[ "$*" == *"$marker"* ]]; then\n' ;;
            input) printf 'marker=%q\n' "$6"; printf 'if %s; then in=$(%q %q); %q > "$in"; fi\n' "$shape" "$r_mktemp" "$TEST_DIR/in.XXXXXX" "$r_cat"
                   printf 'if [ -n "$in" ] && [[ "$(%q "$in")" == *"$marker"* ]]; then\n' "$r_cat" ;;
        esac
        printf '    w=$(%q %q); if [ -n "$in" ]; then %q "$@" < "$in" > "$w"; s=$?; else %q "$@" > "$w"; s=$?; fi\n' "$r_mktemp" "$TEST_DIR/short.XXXXXX" "$real" "$real"
        printf '    if [ "$s" -ne 0 ]; then %q "$w"; %q -f "$w"; exit "$s"; fi\n' "$r_cat" "$r_rm"
        printf '    n=$(%q -c < "$w"); n=${n//[[:space:]]/}; %s\n' "$r_wc" "$keep"
        printf '    a="$*"; printf "%%s\\n" %q"${a//$'"'"'\\n'"'"'/ } [whole $n cut $k]" >> %q\n' "$tool " "$TEST_DIR/calls.$name"
        printf '    %q -c "$k" "$w"; %q -f "$w"; exit 0\n' "$r_head" "$r_rm"
        printf 'fi\n'
        printf '[ -z "$in" ] || exec %q "$@" < "$in"\n' "$real"
        printf 'exec %q "$@"\n' "$real"
    } > "$TEST_DIR/shim/$tool"
    chmod 755 "$TEST_DIR/shim/$tool"
    export PATH="$TEST_DIR/shim:$PATH"
}
calls_short_on() {   # <tool> <calls name> <bash test over the shim's "$@"> <cut>: for that shape the real <tool>'s answer cut short, exit 0, the call recorded with both byte counts; the real one for every other shape
    calls_short_on_shim plain "$1" "$2" "$4" "$3"
}
calls_short_on_text() {   # <tool> <calls name> <fixed text the arguments carry> <cut>: the same, for a call whose arguments carry that text (an awk program, a sed script)
    calls_short_on_shim text "$1" "$2" "$4" "$3"
}
calls_short_on_input() {   # <tool> <calls name> <bash test over the shim's "$@"> <fixed text the input carries> <cut>: the same, for a call of that shape whose INPUT carries that text; the real one, fed the same input, otherwise
    calls_short_on_shim input "$1" "$2" "$5" "$3" "$4"
}
fired_short() {   # <calls name> <fixed text the shape carries>: the shim fired during the push, on that shape, with an answer cut short (fewer bytes than the whole)
    [ -s "$TEST_DIR/calls.$1" ]
    grep -F -- "$2" "$TEST_DIR/calls.$1" | awk '{ for (i = 1; i < NF; i++) if ($i == "[whole") { w = $(i + 1); c = $(i + 3); sub(/]$/, "", c); if (c + 0 < w + 0) found = 1 } } END { exit !found }'
}
push_from_worktree_through_hook_with_shim() {   # <worktree of REPO> <refspec>: push_ref_through_hook_with_shim's push, made from that worktree (the hook then runs at its top, and the worktree shares the clone's configuration)
    mkdir -p "$TEST_DIR/hooks"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'export PATH=%q:"$PATH"\n' "$TEST_DIR/shim"
        printf 'exec %q "$@"\n' "$HOOK"
    } > "$TEST_DIR/hooks/pre-push"
    chmod 755 "$TEST_DIR/hooks/pre-push"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/hooks"
    run git -C "$1" push origin "$2"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
}
r8b3_link_sorted_last() {   # a base on the remote carrying a link whose target names the host (zlink, the tip listing's last line), and a branch (feature, sha) whose own commit is clean
    add_remote
    commit_file base.txt "notes-api" "base"
    ln -s /home/zzsynthuser/code/node_modules "$REPO/zlink"
    git -C "$REPO" add zlink
    git -C "$REPO" commit -qm "a link carrying the string, sorted last"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
    sha="$(git -C "$REPO" rev-parse HEAD)"
}
r8b3_hidden_sorted_last() {   # a -diff file carrying the string (zz.txt, the -z listing's last record) on the remote (BASE), then one clean commit (sha)
    attributes 'zz.txt -diff'
    commit_file zz.txt "seen on TESTHOST" "a banned string in a -diff file, sorted last"
    add_remote
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file other.txt "nothing to see" "a clean commit"
    sha="$(git -C "$REPO" rev-parse HEAD)"
}
r8b3_twelve_files() {   # a base on the remote (BASE), then one clean commit adding eleven files (sha): twelve regular files with bytes at the tip, each read by the tip's grep, so each count of them has two digits
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    for i in 01 02 03 04 05 06 07 08 09 10 11; do printf 'nothing to see %s\n' "$i" > "$REPO/f$i.txt"; done
    git -C "$REPO" add .
    git -C "$REPO" commit -qm "eleven clean files"
    sha="$(git -C "$REPO" rev-parse HEAD)"
}
r8b3_twelve_commits() {   # a base on the remote (BASE), then twelve clean commits, each adding a file (sha the last): every count of them has two digits
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    for i in 01 02 03 04 05 06 07 08 09 10 11 12; do commit_file "f$i.txt" "nothing to see $i" "clean commit $i"; done
    sha="$(git -C "$REPO" rev-parse HEAD)"
}
r8b3_scanner_log_short() {   # <cut bytes>: a gitleaks on ROMP_GITLEAKS that runs the real one and cuts its LOG (stderr, which the hook reads) to that many bytes, recording the call with both byte counts in calls.scanner-log
    local real=$GL r_head r_wc
    r_head="$(command -v head)"; r_wc="$(command -v wc)"
    mkdir -p "$TEST_DIR/scanner"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'e=$(mktemp %q); %q "$@" 2> "$e"; s=$?\n' "$TEST_DIR/log.XXXXXX" "$real"
        printf 'n=$(%q -c < "$e"); n=${n//[[:space:]]/}; k=%d\n' "$r_wc" "$1"
        printf 'printf "%%s\\n" "gitleaks $* [whole $n cut $k]" >> %q\n' "$TEST_DIR/calls.scanner-log"
        printf '%q -c "$k" "$e" >&2; rm -f "$e"; exit "$s"\n' "$r_head"
    } > "$TEST_DIR/scanner/gitleaks"
    chmod 755 "$TEST_DIR/scanner/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/scanner/gitleaks"
}

@test "round 8b3 short case: the CONTENT grep of the tip: a git whose content grep answers its hit line cut inside the tip's name (exit 0), through a real push of a branch whose tip inherits main's leak, is refused naming the incomplete scan (exit 0 is the match, and a line that is no hit is an error line), and the remote never gets the branch" {
    branch_inheriting_mains_leak
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_short_on git content-grep '[ "${1:-}" = grep ] && [ "${3:-}" = -i ]' bytes:20
    push_ref_through_hook_with_shim feature
    fired_short content-grep "grep --no-color -i -I -l -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of the tip of refs/heads/feature (${sha:0:10}) could not be fully scanned (git grep exited 0)"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the SYMLINK listing of the tip: a git whose symlink pass's ls-tree answers its last line, a link, cut inside its mode (exit 0), through a real push of a branch whose tip inherits main's link naming the host, is refused naming the line that is no whole entry, and the remote never gets the branch (6e34a9d89 read the line as no link and published)" {
    r8b3_link_sorted_last
    last="$(git -C "$REPO" ls-tree -r "$sha" | tail -n 1 | wc -c)"
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim feature   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git plain-listing '[ "${1:-}" = ls-tree ] && [ "${2:-}" = -r ] && [ "$#" -eq 3 ]' "less:$((last - 4))"
    push_ref_through_hook_with_shim feature
    fired_short plain-listing "ls-tree -r $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SYMLINKS of the tip of refs/heads/feature (${sha:0:10}) were listed short (git ls-tree -r exited 0 and answered \"1200\" on a line that is no whole entry: a mode, a type, an object name, a tab and a path)"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the TYPE of the object the tip peels to: a git whose peel type read answers its word cut to three bytes (exit 0), over a tag of a blob, is refused naming the cut word through a real push (no type word is a prefix of another), and the remote never gets the tag" {
    add_remote
    commit_file f.txt "plain" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" tag -a blobtag "$(git -C "$REPO" rev-parse HEAD:f.txt)" -m "a tag of a blob"
    t="$(git -C "$REPO" rev-parse refs/tags/blobtag)"
    calls_short_on git peel-type '[ "${1:-}" = cat-file ] && [ "${2:-}" = -t ] && [[ "${3:-}" == *"^{}" ]]' bytes:3
    push_ref_through_hook_with_shim refs/tags/blobtag
    fired_short peel-type "cat-file -t $t^{}"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TYPE of the object the tip of refs/tags/blobtag (${t:0:10}) peels to was read as \"blo\" (git cat-file -t exited 0), not an object type"* ]]
    run remote_holds_ref refs/tags/blobtag
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the SYMLINK TARGET of a link at the tip: a git whose target read answers ten bytes of it (exit 0), through a real push of a branch whose tip inherits main's link naming the host past those bytes, is refused naming both numbers against the blob's size, and the remote never gets the branch (6e34a9d89 asked the size for an empty target alone and published)" {
    branch_inheriting_mains_symlink_leak
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$sha:node_modules")"
    size="$(git -C "$REPO" cat-file -s "$blob")"
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim feature   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git link-target "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $blob ]" bytes:10
    push_ref_through_hook_with_shim feature
    fired_short link-target "cat-file -p $blob"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SYMLINK TARGET of node_modules at the tip of refs/heads/feature (${sha:0:10}) was read as 10 bytes while git cat-file -s gives its size as $size bytes, so one of the two reads answered short (git cat-file -p exited 0)"* ]]
    [[ "$output" != *"would publish a personal identifier"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the SIZE of a symlink target blob: a git whose size read answers the first digit of a two-digit size (exit 0), over a clean link the push adds, is refused naming both numbers through a real push (the size is read for every target since round 8b3), and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    symlink_commit link ./docs/a-clean-target "a clean link"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$sha:link")"
    size="$(git -C "$REPO" cat-file -s "$blob")"
    [ "$size" -ge 10 ]
    calls_short_on git link-size "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $blob ]" bytes:1
    push_main_through_hook_with_shim
    fired_short link-size "cat-file -s $blob"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SYMLINK TARGET of link at the tip of refs/heads/main (${sha:0:10}) was read as $size bytes while git cat-file -s gives its size as ${size:0:1} bytes, so one of the two reads answered short (git cat-file -p exited 0)"* ]]
    at_base
}

@test "round 8b3 short case: the COMMIT listing of a pushed ref: a git whose range listing answers its first line alone, the pushed tip (exit 0), through a real push of a ref update whose middle commit adds a banned line, is refused naming the count git rev-list --count gives for the same range, and the remote stays at its base (6e34a9d89 scanned the tip alone and published)" {
    leak_in_middle_commit_after_base
    sha="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git range-listing '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]' lines:1
    push_main_through_hook_with_shim
    fired_short range-listing "rev-list $sha --not --remotes $BASE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) could not be listed whole for the identifier scan (git rev-list exited 0 and listed 1 where git rev-list --count of the same range counts 2, so one of the two answered short)"* ]]
    at_base
}

@test "round 8b3 closure: the COMMIT listing of a pushed ref on a NEW branch: a git whose range listing answers its first line alone (exit 0), through a real push of a new branch whose middle commit adds a banned line, is refused naming the count, and the remote never gets the branch (6e34a9d89 published it)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file leak.txt "seen on TESTHOST" "leak"
    remove_file leak.txt "remove it"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim feature   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git range-listing '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]' lines:1
    push_ref_through_hook_with_shim feature
    fired_short range-listing "rev-list $sha --not --remotes"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/feature (${sha:0:10}) could not be listed whole for the identifier scan (git rev-list exited 0 and listed 1 where git rev-list --count of the same range counts 2, so one of the two answered short)"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b3 table case: the COMMIT COUNT of a pushed ref: a git silent on rev-list --count alone, through a real push of a clean commit, is refused naming the non-count, and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on git commit-count '[ "${1:-}" = rev-list ] && [ "${2:-}" = --count ]'
    push_main_through_hook_with_shim
    fired commit-count "rev-list --count $sha --not --remotes $BASE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) could not be counted for the identifier scan (git rev-list --count exited 0 and answered \"\", not a count)"* ]]
    at_base
}

@test "round 8b3 short case: the COMMIT COUNT of a pushed ref: a git whose count answers the first digit of twelve (exit 0), through a real push of twelve clean commits, is refused naming both numbers, and the remote stays at its base" {
    r8b3_twelve_commits
    calls_short_on git commit-count '[ "${1:-}" = rev-list ] && [ "${2:-}" = --count ]' bytes:1
    push_main_through_hook_with_shim
    fired_short commit-count "rev-list --count $sha --not --remotes $BASE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) could not be listed whole for the identifier scan (git rev-list exited 0 and listed 12 where git rev-list --count of the same range counts 1, so one of the two answered short)"* ]]
    at_base
}

@test "round 8b3 short case: the REMOTE REFS containing the pushed commit: a git whose --contains read answers five bytes of the ref it names (exit 0), over a new branch at a commit the remote holds, agrees as the whole answer does (only its emptiness is read): the push passes and the branch names a commit the remote held already" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" branch again
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_short_on git contains '[ "${1:-}" = for-each-ref ] && [ "${3:-}" = --contains ]' bytes:5
    push_ref_through_hook_with_shim again
    fired_short contains "for-each-ref --format=%(refname) --contains $sha refs/remotes/"
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/again)" = "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" ]
}

@test "round 8b3 short case: the ANCESTRY of the pushed commit over the remote commit: a git whose merge-base answers ten hex digits of the pushed commit (exit 0), over a rewind no remote-tracking ref covers (the one push the ancestry is asked for), is refused naming the read's cut answer: the control rewind passes, and the remote stays where it was" {
    add_remote
    commit_file base.txt "notes-api" "base"
    c1="$(git -C "$REPO" rev-parse HEAD)"
    commit_file second.txt "nothing to see" "second"
    git -C "$REPO" push -q origin main
    c2="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" update-ref -d refs/remotes/origin/main                 # no remote-tracking ref contains the rewound commit
    git -C "$REPO" reset -q --hard "$c1"
    mkdir -p "$TEST_DIR/shim"
    push_refs_through_hook_with_shim +main                                 # the control: a rewind publishes nothing new
    [ "$status" -eq 0 ]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$c1" ]
    git -C "$TEST_DIR/remote.git" update-ref refs/heads/main "$c2"
    git -C "$REPO" update-ref -d refs/remotes/origin/main                 # the control's push set it again
    calls_short_on git ancestry '[ "${1:-}" = merge-base ]' bytes:10
    push_refs_through_hook_with_shim +main
    fired_short ancestry "merge-base $c1 $c2"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${c1:0:10}) were listed as none, and whether the pushed commit is an ancestor of the remote's ${c2:0:10} could not be read (git merge-base exited 0 and answered \"${c1:0:10}\", not a commit)"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$c2" ]
}

@test "round 8b3 short case: the PARENT COUNT of a commit: a git whose rev-list --parents answers the merge's own name alone (exit 0), a cut that names fewer parents, through a real push of a merge adding a hidden link that carries the string, meets no numstat row for the merge's post-image, a short read refused naming it, and the remote stays at its base" {
    r8b2_merge_with_hidden_link
    calls_short_on git parents "[ \"\${1:-}\" = rev-list ] && [ \"\${2:-}\" = --parents ] && [ \"\${5:-}\" = $sha ]" "bytes:${#sha}"
    push_main_through_hook_with_shim
    fired_short parents "rev-list --parents -n 1 $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes and printed no verdict for link)"* ]]
    at_base
}

@test "round 8b3 short case: the ADDED LINES diff of a commit: a git whose added-lines diff-tree answers its marker line alone (exit 0), through a real push of a middle-commit leak, is refused naming the missing tail marker, and the remote stays at its base (6e34a9d89 read the marker as a commit adding nothing and published)" {
    leak_in_middle_commit_after_base
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git added-diff '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --always "* ]]' lines:1
    push_main_through_hook_with_shim
    fired_short added-diff "diff-tree -p -r -M -c --root --always --no-color"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${leak:0:10} were read short (git diff-tree exited 0 and its answer does not end with the line naming the commit, the tail marker its second --stdin line asks for after the diff)"* ]]
    [[ "$output" != *"ADDS a personal identifier"* ]]
    at_base
}

@test "round 8b3 short case: the LINE COUNT of the added lines: a wc whose wc -l answers the first digit of twelve (exit 0), through a real push of a commit adding twelve clean lines, is refused naming both numbers, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'nothing to see %s\n' 01 02 03 04 05 06 07 08 09 10 11 12 > "$REPO/twelve.txt"
    git -C "$REPO" add twelve.txt
    git -C "$REPO" commit -qm "twelve clean lines"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_short_on wc line-count '[ "${1:-}" = -l ] && [ "$#" -eq 1 ]' bytes:1
    push_main_through_hook_with_shim
    fired_short line-count "wc -l"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${sha:0:10} were captured short (the diff's awk recorded 12 lines printed and the capture holds 1; the pipeline exited 0)"* ]]
    at_base
}

@test "round 8b3 short case: the ADDED LINES grep: a grep whose added-lines grep answers three bytes of its hit line (exit 0), through a real push of a middle-commit leak, still refuses (exit 0 is the match: the answer names the path for the report alone, and the cut hit line, unterminated, is read as no path, the sort then answering nothing), and the remote stays at its base" {
    leak_in_middle_commit_after_base
    calls_short_on grep added-grep '[ "${1:-}" = -a ] && [ "${2:-}" = -i ]' bytes:3
    push_main_through_hook_with_shim
    fired_short added-grep "grep -a -i -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDED LINES of commit ${leak:0:10} could not be reported (sort exited 0 and answered nothing for the paths the grep named)"* ]]
    at_base
}

@test "round 8b3 short case: the SORT of the paths a grep named: a sort whose sort -u answers the first of two paths (exit 0), through a real push of a middle commit adding a banned line in two files, reports one path of a push the hit refuses already, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'seen on TESTHOST\n' > "$REPO/a.txt"; printf 'seen on TESTHOST\n' > "$REPO/b.txt"
    git -C "$REPO" add a.txt b.txt
    git -C "$REPO" commit -qm "two files carrying the string"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" rm -q a.txt b.txt
    git -C "$REPO" commit -qm "remove them"
    calls_short_on sort sort-paths '[ "${1:-}" = -u ] && [ "$#" -eq 1 ]' lines:1
    push_main_through_hook_with_shim
    fired_short sort-paths "sort -u"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${leak:0:10} ADDS a personal identifier in:"$'\n'"  a.txt"* ]]
    [[ "$output" != *"  b.txt"* ]]
    at_base
}

@test "round 8b3 short case: the ADDRESSES log of a commit: a git whose addresses log answers up to the middle of the committed address (exit 0), through a real push of a commit authored clean and committed under a banned domain, is refused naming its last line, not the tail marker, and the remote stays at its base (6e34a9d89 read the cut address and published)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    GIT_AUTHOR_EMAIL=dev@clean.example GIT_COMMITTER_EMAIL=dev@testhost.example git -C "$REPO" commit -q --allow-empty -m "committed under a banned domain"
    c="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git addresses '[ "${1:-}" = log ] && [[ "${4:-}" == --format=authored* ]]' bytes:43
    push_main_through_hook_with_shim
    fired_short addresses "log -1 --no-show-signature --format=authored"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDRESSES of commit ${c:0:10} were read short (git log exited 0 and answered \"committed"$'\t'"dev@te\" on its last line, not the tail marker line the format asks for after the two roles)"* ]]
    at_base
}

@test "round 8b3 short case: the MESSAGE log of a commit: a git whose message log answers its head marker and the subject alone (exit 0), through a real push of a commit whose message body names the host, is refused naming its last line, not the tail marker, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" commit -q --allow-empty -m "a clean subject" -m "cut on TESTHOST"
    c="$(git -C "$REPO" rev-parse HEAD)"
    calls_short_on git message-log '[ "${1:-}" = log ] && [[ "${4:-}" == --format=message* ]]' lines:2
    push_main_through_hook_with_shim
    fired_short message-log "log -1 --no-show-signature --format=message"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the MESSAGE of commit ${c:0:10} was read short (git log exited 0 and answered \"a clean subject\" on its last line, not the tail marker line the format asks for after the message)"* ]]
    at_base
}

@test "round 8b3 short case: the MESSAGE grep: a grep whose message grep answers one byte of its hit line (exit 0), through a real push of a commit whose subject names the host, still refuses (exit 0 is the match: the answer numbers the line for the report alone), and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" commit -q --allow-empty -m "cut on TESTHOST"
    c="$(git -C "$REPO" rev-parse HEAD)"
    calls_short_on grep message-grep '[ "${1:-}" = -in ]' bytes:1
    push_main_through_hook_with_shim
    fired_short message-grep "grep -in -a -F"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the MESSAGE of commit ${c:0:10} carries a personal identifier on line 1 (line 1 is the subject)"* ]]
    at_base
}

@test "round 8b3 short case: the TYPE of a pushed object: a git whose type read of the pushed tag answers two bytes of its word (exit 0), through a real push of a tag whose message names the host, is refused naming the cut word (no type word is a prefix of another), and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    calls_short_on git object-type "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -t ] && [ \"\${3:-}\" = $tag ]" bytes:2
    push_ref_through_hook_with_shim refs/tags/v1
    fired_short object-type "cat-file -t $tag"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TYPE of the object refs/tags/v1 pushes (${tag:0:10}) was read as \"ta\" (git cat-file -t exited 0), not an object type, so whether it is an annotated tag is unknown"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the OBJECT of a tag: a git whose tag object read answers all but its last message line (exit 0), through a real push of a tag whose message names the host on that line, is refused naming both numbers against the object's size, and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    size="$(git -C "$REPO" cat-file -s "$tag")"
    calls_short_on git tag-object "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $tag ]" less:16
    push_ref_through_hook_with_shim refs/tags/v1
    fired_short tag-object "cat-file -p $tag"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the OBJECT of tag refs/tags/v1 (${tag:0:10}) was read short (git cat-file -p exited 0 and its capture holds $((size - 16)) bytes where git cat-file -s gives the object's size as $size), which ends the peel here"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the SIZE of a tag object: a git whose tag size read answers the first digit of its size (exit 0), through a real push of a tag whose message names the host, is refused naming both numbers, and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    size="$(git -C "$REPO" cat-file -s "$tag")"
    [ "$size" -ge 100 ]
    calls_short_on git tag-size "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $tag ]" bytes:1
    push_ref_through_hook_with_shim refs/tags/v1
    fired_short tag-size "cat-file -s $tag"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the OBJECT of tag refs/tags/v1 (${tag:0:10}) was read short (git cat-file -p exited 0 and its capture holds $size bytes where git cat-file -s gives the object's size as ${size:0:1}), which ends the peel here"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the BYTE COUNT of a tag capture: a wc whose wc -c over the tag capture answers the first digit of its count (exit 0), through a real push of a tag whose message names the host, is refused naming both numbers, and the remote never gets the tag" {
    r8b2_tag_naming_the_host
    size="$(git -C "$REPO" cat-file -s "$tag")"
    calls_short_on_input wc tag-count '[ "${1:-}" = -c ] && [ "$#" -eq 1 ]' "object " bytes:1
    push_ref_through_hook_with_shim refs/tags/v1
    fired_short tag-count "wc -c"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the OBJECT of tag refs/tags/v1 (${tag:0:10}) was read short (git cat-file -p exited 0 and its capture holds ${size:0:1} bytes where git cat-file -s gives the object's size as $size), which ends the peel here"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the -z listing of the tip: a git whose verdict check's ls-tree -r -z -l answers its last record, a hidden file, cut before its tab (exit 0), through a real push over that file the remote holds at the tip, is refused on the whole entries it counts against the symlink pass's, and the remote stays at its base (6e34a9d89 counted the cut record and published)" {
    r8b3_hidden_sorted_last
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git z-listing '[ "${1:-}" = ls-tree ] && [ "${3:-}" = -z ]' less:48
    push_main_through_hook_with_shim
    fired_short z-listing "ls-tree -r -z -l $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was listed short or long for the BINARY VERDICT check (git ls-tree -r -z -l exited 0 and listed 2 entries where the symlink pass's git ls-tree -r of the same tree listed 3)"* ]]
    at_base
}

@test "round 8b3 short case: the READ LIST of the grep of the tip: a git whose read list's grep answers its first record alone (exit 0), through a real push of a clean tip, sends the file it cut away to the byte judge, which refuses it as hidden text (the safe side), and the remote stays at its base" {
    clean_tip_after_base
    calls_short_on git read-list '[ "${1:-}" = grep ] && [ "${5:-}" = -z ]' "bytes:$(( ${#sha} + 10 ))"
    push_main_through_hook_with_shim
    fired_short read-list "grep --no-color -I -l -z -e  $sha --"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: clean.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute reads unspecified"* ]]
    [[ "$output" != *"base.txt at the tip"* ]]
    at_base
}

@test "round 8b3 short case: the ENTRY COUNT of the -z listing: a grep whose whole-entry count over the rewritten -z listing answers the first digit of twelve (exit 0), through a real push of a tip of twelve clean files, is refused naming both counts, and the remote stays at its base" {
    r8b3_twelve_files
    calls_short_on grep entry-count '[ "${1:-}" = -c ] && [[ "${2:-}" == "^[0-7]"* ]] && [[ "${3:-}" == */listing.nl ]]' bytes:1
    push_main_through_hook_with_shim
    fired_short entry-count "listing.nl"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was listed short or long for the BINARY VERDICT check (git ls-tree -r -z -l exited 0 and listed 1 entries where the symlink pass's git ls-tree -r of the same tree listed 12)"* ]]
    at_base
}

@test "round 8b3 short case: the TIP CANDIDATES join: an awk whose tip candidates program answers five bytes of its one row (exit 0), through a real push over a hidden file the remote holds at the tip, is refused naming the three counts (a row cut before its terminator is not counted), and the remote stays at its base" {
    hidden_file_on_remote_then_clean_commit
    calls_short_on_text awk tip-candidates 'printf "tip\t' bytes:5
    push_main_through_hook_with_shim
    fired_short tip-candidates 'printf "tip\t'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was joined short with the grep's read list for the BINARY VERDICT check (the join appended 0 candidate rows where the -z listing names 3 regular files with bytes and the grep's read list 2 of them, so the count expected is 1; awk and tr exited 0)"* ]]
    at_base
}

@test "round 8b3 short case: the FILE COUNT of the -z listing: a grep whose file count answers the first digit of twelve (exit 0), through a real push of a tip of twelve clean files, is refused naming the three counts, and the remote stays at its base" {
    r8b3_twelve_files
    calls_short_on grep file-count '[ "${1:-}" = -c ] && [ "${2:-}" = -E ] && [[ "${4:-}" == */listing.nl ]]' bytes:1
    push_main_through_hook_with_shim
    fired_short file-count "grep -c -E"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was joined short with the grep's read list for the BINARY VERDICT check (the join appended 0 candidate rows where the -z listing names 1 regular files with bytes and the grep's read list 12 of them"* ]]
    at_base
}

@test "round 8b3 short case: the LINE COUNT of the read list: a grep whose count over the rewritten read list answers the first digit of twelve (exit 0), through a real push of a tip of twelve clean files, is refused naming the three counts, and the remote stays at its base" {
    r8b3_twelve_files
    calls_short_on grep read-count '[ "${1:-}" = -c ] && [ "${2:-}" = . ] && [[ "${3:-}" == */read.nl ]]' bytes:1
    push_main_through_hook_with_shim
    fired_short read-count "read.nl"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was joined short with the grep's read list for the BINARY VERDICT check (the join appended 0 candidate rows where the -z listing names 12 regular files with bytes and the grep's read list 1 of them"* ]]
    at_base
}

@test "round 8b3 short case: the REWRITE of a scratch listing: a tr whose NUL-to-newline rewrite answers all but its last five bytes (exit 0), through a real push of a clean tip, is refused naming both byte counts, and the remote stays at its base" {
    clean_tip_after_base
    n="$(git -C "$REPO" ls-tree -r -z -l "$sha" | wc -c | tr -d ' ')"
    calls_short_on tr rewrite '[ "$#" -eq 2 ] && [ "${1:-}" = '"'"'\0'"'"' ] && [ "${2:-}" = '"'"'\n'"'"' ]' less:5
    push_main_through_hook_with_shim
    fired_short rewrite 'tr \0 \n'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the rewrite of listing wrote $((n - 5)) bytes for $n read; tr exited 0)"* ]]
    at_base
}

@test "round 8b3 short case: the BYTE COUNT of a scratch listing: a wc whose byte count of the listing's rewrite answers the first digit of its count (exit 0; the input's count read whole), through a real push of a clean tip, is refused naming both byte counts, and the remote stays at its base" {
    clean_tip_after_base
    n="$(git -C "$REPO" ls-tree -r -z -l "$sha" | wc -c | tr -d ' ')"
    [ "$n" -ge 100 ]
    calls_short_on wc rewrite-count '[ "${1:-}" = -c ] && [ "$#" -eq 1 ] && [ -f /dev/stdin ] && [[ "$(readlink /proc/self/fd/0)" == */listing.nl ]]' bytes:1
    push_main_through_hook_with_shim
    fired_short rewrite-count "wc -c"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the rewrite of listing wrote ${n:0:1} bytes for $n read; tr exited 0)"* ]]
    at_base
}

@test "round 8b3 short case: the CHANGED PATHS listing of a commit: a git whose combined --raw -c listing answers its last record cut inside the path (exit 0), through a real push of a middle commit adding a hidden file, drops the cut record and is refused on the path its numstat names, and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_short_on git changed-paths '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --raw "*" -c "* ]]' less:3
    push_main_through_hook_with_shim
    fired_short changed-paths "diff-tree -r --raw --no-renames --root -c -z --no-commit-id $leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CHANGED PATHS of commit ${leak:0:10} were listed short for the BINARY VERDICT check (git diff-tree --raw exited 0 and its listing lacks notes.txt, a path git diff-tree --numstat answered for)"* ]]
    at_base
}

@test "round 8b3 short case: the COMBINED PATCH of a merge: a git whose combined patch answers its first line alone (exit 0), through a real push of a merge adding a hidden link that carries the string, leaves the link's section a header alone, a candidate the byte judge refuses as hidden text, and the remote stays at its base" {
    r8b2_merge_with_hidden_link
    calls_short_on git combined-patch '[ "${1:-}" = diff-tree ] && [[ " $* " == *" -p "*" --no-commit-id "* ]]' lines:1
    push_main_through_hook_with_shim
    fired_short combined-patch "diff-tree -p -r -M -c --root --no-commit-id --no-color $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: link in commit ${sha:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    at_base
}

@test "round 8b3 short case: the SECTION ROWS of a combined patch: an awk whose section parser answers four bytes of its one row (exit 0), through a real push of a merge adding a hidden link that carries the string, leaves the link with no row, a short read refused naming it, and the remote stays at its base" {
    r8b2_merge_with_hidden_link
    calls_short_on_text awk section-rows 'hdr && /^Binary files /' bytes:4
    push_main_through_hook_with_shim
    fired_short section-rows "Binary files"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for link, a path the merge changes)"* ]]
    at_base
}

@test "round 8b3 short case: the PER-PARENT listing of a merge: a git whose diff-tree --raw -m answers ten bytes of its first record (exit 0), through a real push of a merge moving content two parents held to a third path, names no deletion, so the moved path is no rename candidate and a short read at the join, refused naming it, and the remote stays at its base" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    calls_short_on git per-parent '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --raw "*" -m "* ]]' bytes:10
    push_main_through_hook_with_shim
    fired_short per-parent "diff-tree -r --raw --no-renames -m -z --no-commit-id $merge"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${merge:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for b.txt, a path the merge changes)"* ]]
    at_base
}

@test "round 8b3 short case: the RENAME CANDIDATES of a merge: an awk whose rename candidates program answers two bytes of its one path (exit 0), through a real push of a merge moving content two parents held to a third path, leaves the moved path a short read at the join, refused naming it, and the remote stays at its base" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    calls_short_on_text awk rename-candidates 'in gone) print' bytes:2
    push_main_through_hook_with_shim
    fired_short rename-candidates 'in gone) print'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${merge:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for b.txt, a path the merge changes)"* ]]
    at_base
}

@test "round 8b3 short case: the NUMSTAT of a commit: a git whose diff-tree --numstat answers its last row cut inside the path (exit 0), through a real push of a middle commit adding a hidden file, drops the cut row, a short read refused naming the path, and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_short_on git numstat '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --numstat "* ]]' less:3
    push_main_through_hook_with_shim
    fired_short numstat "diff-tree -r --numstat -z --no-commit-id -M --root $leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${leak:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes and printed no verdict for notes.txt)"* ]]
    at_base
}

@test "round 8b3 short case: the EMPTY TREE name: a git whose hash-object answers twenty hex digits of the empty tree's name (exit 0), through a real push of a type change, is refused naming the cut name before any numstat reads it, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    type_change_to_symlink
    e="$(git -C "$REPO" hash-object -t tree --stdin < /dev/null)"
    calls_short_on git empty-tree '[ "${1:-}" = hash-object ] && [ "${2:-}" = -t ] && [ "${3:-}" = tree ]' bytes:20
    push_main_through_hook_with_shim
    fired_short empty-tree "hash-object -t tree --stdin"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the BINARY VERDICTS of commit ${sha:0:10} could not be read (git hash-object, asked for the empty tree's name, answered \"${e:0:20}\", not a whole object name as long as the commit's own)"* ]]
    at_base
}

@test "round 8b3 short case: the JOIN of the verdicts of a commit: an awk whose join program answers five bytes of its one row (exit 0), through a real push of a middle commit adding a hidden file, is refused naming the rows appended against the count its awk recorded, and the remote stays at its base" {
    hidden_file_in_middle_commit_after_base
    calls_short_on_text awk verdict-join 'ENVIRON["ROMP_SHORT_FILE"]' bytes:5
    push_main_through_hook_with_shim
    fired_short verdict-join 'ROMP_SHORT_FILE'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the JOIN of commit ${leak:0:10}'s verdicts appended 0 candidate rows for the BINARY VERDICT check where its awk recorded 1 printed (its pipeline exited 0), so the join answered short"* ]]
    at_base
}

@test "round 8b3 short case: the BYTE COUNTS of a hidden blob: a git whose content read of a binary blob answers its two bytes ahead of the NUL (exit 0), through a real push of a middle commit adding that binary file, makes the byte judge read text and refuse it as hidden (a cut drops bytes and never adds a NUL: the safe side); the control push passes, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'ab\0cd\n' > "$REPO/bin.dat"
    git -C "$REPO" add bin.dat
    git -C "$REPO" commit -qm "a binary file"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse "$leak:bin.dat")"
    remove_file bin.dat "remove it"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim                                 # the control: binary by its bytes, it passes as binaries always have
    [ "$status" -eq 0 ]
    git -C "$TEST_DIR/remote.git" update-ref refs/heads/main "$BASE"
    git -C "$REPO" update-ref refs/remotes/origin/main "$BASE"
    calls_short_on git blob-bytes "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [ \"\${3:-}\" = $blob ]" bytes:2
    push_main_through_hook_with_shim
    fired_short blob-bytes "cat-file blob $blob"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: bin.dat in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified"* ]]
    at_base
}

@test "round 9d short case: the CREDENTIAL FEED of the push: the refuters' within-commit cut, the feed's git answer kept up to its second diff --git line (exit 0, nothing on stderr), through a real push of a commit adding a clean a.txt and a z.py holding a credential, is refused naming the tail marker it lost, and the remote stays at its base (this slot held the REPOSITORY ROOT's short case, a read retired in round 9; at cad898dd2 the same cut of gitleaks' own git log published the credential through this push, the round 8 refuters' finding, A.1)" {
    r9d_base
    two_files_credential_second
    calls_short_on_text git feedcut --text "before:diff --git :2"
    push_main_through_hook_with_shim
    fired_short feedcut "--text"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push was read short (git diff-tree exited 0 and did not close commit 1 of the 1 it was given with the line naming it again, the tail marker its second --stdin line asks for); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9d: the CREDENTIAL FEED of the push, the refuters' within-commit cut ended by a SIGKILL of the feed's git, through a real push, is refused naming the feed's status 137, and the remote stays at its base (this slot held the COUNT of commits' short case, a read retired in round 9; at cad898dd2 gitleaks read the same cut of its own git log past the kill and published)" {
    r9d_base
    two_files_credential_second
    feed_git_cut_then 'kill -9 $$'
    push_main_through_hook_with_shim
    [ -s "$TEST_DIR/calls.feedcut" ]
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push could not be read (a stage of git diff-tree, tr and awk exited 137); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9d: the CREDENTIAL FEED of the push through a tr whose answer loses its last line (the tail marker, 41 bytes, exit 0) is refused naming the tail marker, and the remote stays at its base (this slot held the COLOUR STRIP's short case, a read retired in round 9)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    calls_short_on tr feedtr '[[ "${1:-}" == *000 ]]' less:41
    push_main_through_hook_with_shim
    fired_short feedtr "000"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push was read short (git diff-tree exited 0 and did not close commit 1 of the 1 it was given with the line naming it again, the tail marker its second --stdin line asks for); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 8b3 short case: the ERR line of the scanner log: an awk whose ERR line program answers three bytes of its word (exit 0), beside a scanner that logs an ERR line, is refused naming the cut answer, neither none nor an error line, and the remote stays at its base (since round 9 the ERR line comes from a scanner wrapper, gitleaks running no git)" {
    real_gitleaks
    clean_tip_after_base
    scanner_wrapper 'echo "1:00AM ERR something went wrong" >&2'
    calls_short_on_text awk err-line '$2 == "ERR"' bytes:3
    push_main_through_hook_with_shim
    fired_short err-line '$2 == "ERR"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan could not be judged: its log's error-line read answered \"err\" (awk exited 0), neither the word none nor an error line"* ]]
    at_base
}

@test "round 8b3 closure: the ERR line of the scanner log beside a scanner that logs an error and still reports the push whole: an awk silent on the ERR line's program, over the log of a scanner that logs an ERR line, reports the bytes the feed wrote and no finding and exits 0, is refused naming the read's empty answer, and the remote never gets the credential (6e34a9d89 read the empty answer as no error, the count agreed, and the credential published; since round 9 the scanner stub reports the byte figure in place of the count)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    unset ROMP_NO_GITLEAKS
    mkdir -p "$TEST_DIR/scanner"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = dir ]; then printf "%%s\\n" "gitleaks $*" >> %q; n=$(cat ./* | wc -c); n=${n//[[:space:]]/}; printf "%%s\\n" "5:17PM ERR a scan dropped partway" "5:17PM INF scanned ~$n bytes ($n bytes) in 1ms" "5:17PM INF no leaks found" >&2; exit 0; fi\n' "$TEST_DIR/calls.scanner"
        printf 'if [ "${1:-}" = version ]; then echo 8.25.0; exit 0; fi\n'          # a release at the floor's answer: the version read precedes the run (round 10b)
        printf 'exit 1\n'
    } > "$TEST_DIR/scanner/gitleaks"
    chmod 755 "$TEST_DIR/scanner/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/scanner/gitleaks"
    calls_silent_on_text awk err-line '$2 == "ERR"'
    push_main_through_hook_with_shim
    fired scanner "gitleaks dir "
    fired err-line '$2 == "ERR"'
    [ "$status" -ne 0 ]
    [[ "$output" != *"bytes of added lines it was fed"* ]]            # the figure agreed: the ERR line is the one fact left to catch it
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan could not be judged: its log's error-line read answered \"\" (awk exited 0), neither the word none nor an error line"* ]]
    at_base
}

@test "round 9d short case: the BYTE COUNT line of the scanner log: an awk whose byte figure program answers seven bytes of its answer (exit 0), beside the real scanner, through a real push of a clean commit, is refused naming the cut figure against the feed's bytes, and the remote stays at its base (re-aimed in place from the COMMIT COUNT line's short case, the row it replaces)" {
    r9d_base
    commit_file a.txt "clean line long enough for two digits" "clean"
    calls_short_on_text awk byte-line '$3 == "scanned"' bytes:7
    push_main_through_hook_with_shim
    fired_short byte-line '$3 == "scanned"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan read 4 of the 40 bytes of added lines it was fed; the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 8b3 short case: the CHOSEN ADDRESSES of this clone: a git whose config --get-all user.email answers its one address cut short to a prefix of it (exit 0), dev@testhost.example of dev@testhost.example.org, through a real push of a commit stamped with that prefix, drops the unterminated address rather than choose it, so the banned domain is judged: the push is refused and the remote stays at its base (6e34a9d89 chose the prefix and published)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" config user.email dev@testhost.example.org
    GIT_AUTHOR_EMAIL=dev@testhost.example GIT_COMMITTER_EMAIL=dev@testhost.example git -C "$REPO" commit -q --allow-empty -m "stamped under an address the clone never chose"
    c="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim                                 # the control: the whole answer chooses dev@testhost.example.org alone
    [ "$status" -ne 0 ]
    at_base
    calls_short_on git chosen '[ "${1:-}" = config ] && [ "${2:-}" = --get-all ] && [ "${3:-}" = user.email ]' less:5
    push_main_through_hook_with_shim
    fired_short chosen "config --get-all user.email"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${c:0:10} is authored as <dev@testhost.example>, an address this clone is not configured to use, whose domain carries a personal identifier"* ]]
    at_base
}

@test "round 8b3 short case: the REPLACE REFS listing: a git whose replace-ref listing answers five bytes of the ref it names (exit 0), over a clone that has a replace ref, refuses as the whole answer does (only its emptiness is read), and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file clean.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" replace "$sha" "$BASE"
    calls_short_on git replace-refs '[ "${1:-}" = for-each-ref ] && [[ "${3:-}" == refs/replace/* ]]' bytes:5
    push_main_through_hook_with_shim
    fired_short replace-refs "for-each-ref --format=%(refname) refs/replace/"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: this clone carries a replace ref (refs/): under it what a scan reads and what the push transfers can differ, so the push is refused rather than scanned"* ]]
    at_base
}

@test "round 8b3 short case: the TIP BLOBS of the -z listing: an awk whose tip blob set answers its first line alone (exit 0), through a real push of a clean text file over core.bigFileThreshold that the tip holds, sends the commit's candidate the cut set lost to the byte judge, which refuses it as hidden text (the safe side); the control push passes, and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" config core.bigFileThreshold 100
    big_text_file big.txt "nothing to see"
    git -C "$REPO" add big.txt
    git -C "$REPO" commit -qm "a clean text file over the threshold"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim                                 # the control: the tip's grep read the file, so the commit's candidate is the tip's to judge
    [ "$status" -eq 0 ]
    git -C "$TEST_DIR/remote.git" update-ref refs/heads/main "$BASE"
    git -C "$REPO" update-ref refs/remotes/origin/main "$BASE"
    calls_short_on_text awk tip-blobs 'f[1] == "120000") print f[3]' lines:1
    push_main_through_hook_with_shim
    fired_short tip-blobs 'print f[3]'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: big.txt in commit ${sha:0:10} is text that git calls binary although its diff attribute reads unspecified"* ]]
    at_base
}

@test "round 9d: a blob whose added lines hold a NUL byte (ab, NUL, cd, then a credential line, in blob.bin) is read whole: the feed maps NUL to 0x01, so the credential on the next line is found and named, and the remote stays at its base (this slot held the log.showRoot read's short case, a read retired in round 9; at cad898dd2 this push published, gitleaks' git mode reading no line of the file)" {
    r9d_base
    printf 'ab\0cd\nk = "%s"\n' "$(probe_token)" > "$REPO/blob.bin"
    git -C "$REPO" add blob.bin
    git -C "$REPO" commit -qm "a NUL, then a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: blob.bin"* ]]
    at_base
}

@test "round 8b3 short case: the diff attribute of a hidden path (check-attr): a git whose check-attr answers all but its last three bytes (exit 0) leaves the attribute unread in the refused line: through a real push of a hidden file carrying the string the push is refused and the remote never gets the branch" {
    add_remote
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_short_on git check-attr '[ "${1:-}" = check-attr ]' less:3
    push_main_through_hook_with_shim
    fired_short check-attr "check-attr -z diff -- notes.txt"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr answered nothing for the path asked), so whether an attribute of its path accounts for the verdict is unknown"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]   # round 8c: the cut changes the advice too, the key's beside the attribute paragraph (the whole answer printed that paragraph alone)
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the diff driver's binary key: a git whose config --type=bool diff.<driver>.binary answers two bytes of true (exit 0) leaves the label at the two facts: through a real push of a middle commit hiding a file carrying the string behind a driver, the push is refused and the remote stays at its base" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'notes.txt diff=zzdrv\n' > "$REPO/.git/info/attributes"
    git -C "$REPO" config diff.zzdrv.binary true
    commit_file notes.txt "seen on TESTHOST" "a banned string in a file git calls binary by its driver"
    leak="$(git -C "$REPO" rev-parse HEAD)"
    remove_file notes.txt "remove it"
    calls_short_on git driver-key '[ "${1:-}" = config ] && [ "${2:-}" = --type=bool ] && [[ "${3:-}" == diff.*.binary ]]' bytes:2
    push_main_through_hook_with_shim
    fired_short driver-key "config --type=bool diff.zzdrv.binary"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: notes.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads zzdrv, so no attribute of its path accounts for the verdict"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]   # round 8c: the key's advice in place of the attribute paragraph, which the whole answer printed
    [[ "$output" != *"Remove the diff attribute for each path named"* ]]
    at_base
}

@test "round 8b3 short case: the SIZE of a hidden blob, for the report: a git whose report cat-file -s answers the first digit of the size (exit 0) misstates the size in the two-fact line alone: through a real push of a middle commit adding a text file over core.bigFileThreshold carrying the string, the push is refused and the remote stays at its base" {
    r8b2_big_file_in_middle_commit
    size="$(git -C "$REPO" cat-file -s "$blob")"
    calls_short_on git report-size "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -s ] && [ \"\${3:-}\" = $blob ]" bytes:1
    push_main_through_hook_with_shim
    fired_short report-size "cat-file -s $blob"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: big.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is ${size:0:1} bytes; core.bigFileThreshold is 100 in this clone's configuration)"* ]]
    at_base
}

@test "round 8b3 short case: the core.bigFileThreshold read, for the report: a git whose config core.bigFileThreshold answers the first digit of the key (exit 0) misstates it in the two-fact line alone: through a real push of a middle commit adding a text file over the threshold carrying the string, the push is refused and the remote stays at its base" {
    r8b2_big_file_in_middle_commit
    calls_short_on git report-threshold '[ "${1:-}" = config ] && [ "${2:-}" = core.bigFileThreshold ]' bytes:1
    push_main_through_hook_with_shim
    fired_short report-threshold "config core.bigFileThreshold"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: big.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is "*" bytes; core.bigFileThreshold is 1 in this clone's configuration)"* ]]
    at_base
}

@test "round 8b3 short case: the rename source, for the report: a git whose report diff-tree --raw -M answers all but its last three bytes (exit 0) leaves the previous version unnamed: through a real push of a rename made text carrying the string, the push is refused on the two-fact line and the remote stays at its base" {
    r8b2_rename_twin
    calls_short_on git rename-source '[ "${1:-}" = diff-tree ] && [[ " $* " == *" --raw -M -z --root --no-commit-id "* ]]' less:3
    push_main_through_hook_with_shim
    fired_short rename-source "diff-tree -r --raw -M -z --root --no-commit-id $leak"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: new.txt in commit ${leak:0:10} is text that git calls binary although its diff attribute reads set, so no attribute of its path accounts for the verdict (the diff read it as a rename, so the attribute of the path it came from counted too) (the blob is"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]   # round 8c: the key's advice in place of the fetch remedy and the attribute line, which the whole answer printed
    [[ "$output" != *"Where a line names the previous version's bytes as the cause"* ]]
    at_base
}

@test "round 8b3 short case: the previous version's bytes, one-parent, for the report: a git whose read of the parent's version answers its two bytes ahead of the NUL (exit 0) leaves the two-fact line: through a real push of a commit turning a binary file into text carrying the string, the push is refused and the remote stays at its base" {
    r8b2_binary_turned_text
    calls_short_on git prev-version "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [[ \"\${3:-}\" == $leak^:* ]]" bytes:2
    push_main_through_hook_with_shim
    fired_short prev-version "cat-file blob $leak^:thing"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: thing in commit ${leak:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]   # round 8c: the key's advice in place of the fetch remedy and the attribute line, which the whole answer printed
    [[ "$output" != *"Where a line names the previous version's bytes as the cause"* ]]
    at_base
}

@test "round 8b3 short case: the previous version's bytes, a merge parent, for the report: a git whose read of each parent's version answers its two bytes ahead of the NUL (exit 0) leaves the two-fact line: through a real push of a merge moving a text file carrying the string onto a binary file's path, the push is refused and the remote stays at its base" {
    r8b2_merge_text_onto_binary
    calls_short_on git parent-version "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [[ \"\${3:-}\" == $merge^* ]]" bytes:2
    push_main_through_hook_with_shim
    fired_short parent-version "cat-file blob $merge^1:bin.dat"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: bin.dat in commit ${merge:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]   # round 8c: the key's advice in place of the fetch remedy and the attribute line, which the whole answer printed
    [[ "$output" != *"Where a line names the previous version's bytes as the cause"* ]]
    at_base
}

@test "round 9d: a NUL byte and a credential on ONE line of blob.bin: the pieces carry byte 0x01 where the blob had NUL and every byte after it, so the credential is found and named, and the remote stays at its base (this slot held the root-commit probe's short case, a read retired in round 9; at cad898dd2 this push published)" {
    r9d_base
    printf 'ab\0cd k = "%s"\n' "$(probe_token)" > "$REPO/blob.bin"
    git -C "$REPO" add blob.bin
    git -C "$REPO" commit -qm "a NUL and a credential on one line"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/pieces"
    scanner_wrapper "cp -- ./* $(printf %q "$TEST_DIR/pieces")/"          # the pieces as the scanner reads them
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: blob.bin"* ]]
    LC_ALL=C grep -q "$(printf 'ab\001cd k = ')" "$TEST_DIR/pieces/1"      # 0x01 in the NUL's place, the rest of the line kept
    [ "$(LC_ALL=C tr -cd '\000' < "$TEST_DIR/pieces/1" | wc -c)" -eq 0 ]    # no NUL reached the piece
    at_base
}

@test "round 9d: the real scanner with its log cut to ten bytes (its exit kept) logs no byte figure, and the push is refused: through a real push of a clean commit the remote stays at its base (re-aimed from the scanner's argument list's short case, a row retired in round 9)" {
    real_gitleaks
    clean_tip_after_base
    r8b3_scanner_log_short 10
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim
    fired_short scanner-log "gitleaks dir . "
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan reported 0 byte-count lines where it writes one, so what it read is unknown; the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 8b3 controls: the END bounds refuse no legitimate answer: a root commit on a new branch, an empty commit, a commit with an empty message, a rename, a clean merge, a link whose target is empty, a ref update carrying them all and a new branch with nothing banned each pass through a real push with no romp line" {
    add_remote
    mkdir -p "$TEST_DIR/shim"
    commit_file base.txt "notes-api" "base"                                  # a root commit, pushed as a new branch
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    git -C "$REPO" commit -q --allow-empty -m "an empty commit"
    git -C "$REPO" commit -q --allow-empty --allow-empty-message -m ""
    git -C "$REPO" mv base.txt renamed.txt
    git -C "$REPO" commit -qm "a rename"
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    git -C "$REPO" merge -q --no-ff -m "a clean merge" side
    empty="$(git -C "$REPO" hash-object -w --stdin < /dev/null)"
    git -C "$REPO" update-index --add --cacheinfo "120000,$empty,elink"
    git -C "$REPO" commit -qm "a link whose target is empty"
    push_main_through_hook_with_shim                                          # a ref update carrying every shape above
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
    git -C "$REPO" checkout -q -b feature
    commit_file web.txt "the web session's work" "branch work"
    push_ref_through_hook_with_shim feature                                   # a new branch
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
}

@test "round 8b3 controls with the scanner: the feed's markers and the byte figure refuse no clean push: a clean root commit pushed from the clone and a clean commit pushed from a worktree whose path extends the clone's each pass under the real scanner with no romp line (round 9d: the root's tail line and the counts this case held are retired; the controls stand)" {
    real_gitleaks
    add_remote
    mkdir -p "$TEST_DIR/shim"
    commit_file base.txt "notes-api" "base"
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    git -C "$REPO" worktree add -q -b wt "$TEST_DIR/repo-wt" main
    printf 'nothing to see\n' > "$TEST_DIR/repo-wt/clean.txt"
    git -C "$TEST_DIR/repo-wt" add clean.txt
    git -C "$TEST_DIR/repo-wt" commit -qm "a clean commit in the worktree"
    push_from_worktree_through_hook_with_shim "$TEST_DIR/repo-wt" wt
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/wt)" = "$(git -C "$TEST_DIR/repo-wt" rev-parse HEAD)" ]
}

# ── round 8b4 (A.8, a closing round): the COMMIT listing's whole-name arm, pinned ──
# The r8b3 audit found that the arm refusing a listed line that is no whole commit name turned no case red
# when disabled: a listing cut inside its LAST name keeps its line count, so git rev-list --count agrees with
# it, and with the arm gone the same push is refused all the same, first by the PARENT COUNT gate (the scan's
# parent read answers the whole name the cut dropped) and then by each later read of that commit. The arm
# stays, a hardening that names the cut line first, and the case below pins its line, red with the arm
# disabled. The COMMIT listing row's short column keeps the round 8b3 case, the cut that published at
# 6e34a9d89; the row's fact names this one.
@test "round 8b4 hardening case: the COMMIT listing of a pushed ref, its whole-name arm: a git whose range listing answers the tip's line whole and the last name, the leak commit's, cut to half its digits (exit 0), through a real push of a ref update whose middle commit adds a banned line, lists as many lines as git rev-list --count counts and is refused by the arm naming the cut line (the PARENT COUNT gate stands behind it), and the remote stays at its base" {
    leak_in_middle_commit_after_base
    sha="$(git -C "$REPO" rev-parse HEAD)"
    n=${#sha}; half=$((n / 2))
    mkdir -p "$TEST_DIR/shim"
    calls_short_on git range-listing '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]' "less:$((n - half + 1))"
    push_main_through_hook_with_shim
    fired_short range-listing "rev-list $sha --not --remotes $BASE"
    grep -q -F -- "rev-list $sha --not --remotes $BASE [whole $((2 * (n + 1))) cut $((n + 1 + half))]" "$TEST_DIR/calls.range-listing"   # two lines, the tip's whole and the last name cut to half its digits: as many as git rev-list --count counts (the whole answer's two lines), so the line count agrees
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) were listed short (git rev-list exited 0 and answered \"${leak:0:$half}\" on a line that is no whole commit name)"* ]]
    at_base
}

# ── round 8b5 (A.8, a closing check): the parent count re-read from pcount, driven with its answer cut ──
# The row's short column said none while its reason described a cut, and the r8b4 audit drove that cut
# through a real push: a count of ten or more parents has a proper prefix that is not empty, whatever its
# number of digits, and that prefix is a smaller count, so the report reads the previous versions of the
# first parents alone. The case below cuts an eleven-parent merge's count to its first digit, the eleventh
# parent alone holding the binary previous version: the report line becomes the two-fact line and the advice
# under it the configuration key's, while the verdict and the remote are those of the whole count. The row's
# short column names this case.
r8b5_eleven_parent_merge() {   # a base on the remote (BASE); ten sides from it, the tenth alone adding bin.dat binary by its bytes, and main's own commit; an eleven-parent merge of main and the ten sides (merge) making bin.dat text carrying the string, parent 11 alone holding the binary version; bin.dat removed at the tip
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    local i sides=()
    for i in 01 02 03 04 05 06 07 08 09 10; do
        git -C "$REPO" checkout -q -b "s$i" main
        if [ "$i" = 10 ]; then
            printf 'ab\0cd\n' > "$REPO/bin.dat"
            git -C "$REPO" add bin.dat
            git -C "$REPO" commit -qm "side $i: a binary file"
        else
            commit_file "s$i.txt" "side $i" "side $i"
        fi
        sides+=("s$i")
    done
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit "${sides[@]}" > /dev/null 2>&1
    printf 'seen on TESTHOST\n' > "$REPO/bin.dat"
    git -C "$REPO" add bin.dat
    git -C "$REPO" commit -qm "an eleven-parent merge making bin.dat text"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    remove_file bin.dat "remove it"
}
@test "round 8b5 short case: the parent count re-read from pcount, for the report: an awk whose read of an eleven-parent merge's count answers its first digit (exit 0), a smaller count, leaves the previous versions of the later parents unread: through a real push of an eleven-parent merge whose eleventh parent alone holds the binary previous version, the push is refused on the two-fact line with the configuration key's advice, as the whole count refuses it, and the remote stays at its base" {
    r8b5_eleven_parent_merge
    [ "$(git -C "$REPO" rev-list --parents -n 1 "$merge" | wc -w)" -eq 12 ]   # the merge and its eleven parents
    git -C "$REPO" cat-file -e "$merge^11:bin.dat"                              # the binary previous version, in parent 11
    run git -C "$REPO" cat-file -e "$merge^1:bin.dat"
    [ "$status" -ne 0 ]                                                         # and none in parent 1, the version a count of 1 reads
    mkdir -p "$TEST_DIR/shim"
    calls_short_on_text awk pcount '$1 == r { print $2; exit }' bytes:1
    push_main_through_hook_with_shim
    fired_short pcount '$1 == r'
    grep -F -- "-v r=$merge " "$TEST_DIR/calls.pcount" | grep -q -F -- "[whole 3 cut 1]"   # the merge's count, 11 and its newline, cut to its first digit
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: bin.dat in commit ${merge:0:10} is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is "*" bytes; core.bigFileThreshold is not set in this clone's configuration); the identifier scan did not read it, so the push is refused rather than scanned"* ]]
    [[ "$output" != *"the previous version of the file"* ]]
    [[ "$output" == *"Where a line names no attribute, a configuration key can be what makes git call the file binary"* ]]
    [[ "$output" != *"Where a line names the previous version's bytes as the cause"* ]]
    at_base
}

# ── round 9a (the round 8 rulings' B, D, E and H.3): the peel beside the ancestry, a tree of empty ──
# directories, the tag remedy per cause, and the newline test without a tool.
# B: merge-base peels an annotated tag and answers a commit, and round 8b2 compared that answer with the
# pushed object's own name, so an annotated tag moved back to an ancestor, re-created on its commit or
# replacing a lightweight tag there was refused with a false "not an ancestor" line whenever no
# remote-tracking ref contained the commit (the round 8 refuters, 2026-09-24). The answer is compared
# with the commit the pushed object peels to, a read of its own (rev-parse --verify on <object>^{commit})
# judged a whole name first, so an empty peel never agrees with an empty merge-base answer: the three
# tag pushes pass, the new read has its table case and short case, and a git silent on the listing, the
# peel and merge-base at once is refused naming the peel. D: the recursive listing omits tree entries,
# so a tip whose tree holds only empty directories lists nothing while its size is not 0; the refusal
# stays, a disclosed residual, and its line names both causes. E: the tag remedy is keyed per cause,
# not per push. H.3: the newline test reads its records in the shell, so no tool stands between the
# listing and the verdict.
@test "round 9a case: an annotated TAG moved back to an ancestor of its commit and force-pushed, over a remote whose commits no remote-tracking ref of this clone contains, passes through a real push and the remote holds the new tag: merge-base's answer is compared with the commit the tag peels to (cad898dd2 compared it with the tag object's own name and refused with a false not-an-ancestor line)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    c1="$(git -C "$REPO" rev-parse HEAD)"
    commit_file second.txt "nothing to see" "second"
    c2="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" tag -a v1 -m "release one" "$c2"
    git -C "$REPO" push -q origin main refs/tags/v1
    git -C "$REPO" update-ref -d refs/remotes/origin/main                  # no remote-tracking ref contains either commit
    old="$(git -C "$REPO" rev-parse refs/tags/v1)"
    git -C "$REPO" tag -f -a v1 -m "release one, moved back" "$c1" > /dev/null
    new="$(git -C "$REPO" rev-parse refs/tags/v1)"
    run _hook_in "$REPO" -c 'git rev-list "$1" --not --remotes "$2"' _ "$new" "$old"
    [ "$status" -eq 0 ]
    [ -z "$output" ]                                                        # the listing is empty, so the ancestry is asked
    [ "$(git -C "$REPO" merge-base "$new" "$old")" = "$c1" ]               # merge-base answers the commit, not the tag object
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim +refs/tags/v1
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push:"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/tags/v1)" = "$new" ]
}

@test "round 9a case: an annotated TAG re-created on its own commit with a corrected message and force-pushed, over a remote whose commit no remote-tracking ref of this clone contains, passes through a real push and the remote holds the new tag (cad898dd2 refused it with a false not-an-ancestor line)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    c="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" tag -a v1 -m "release one"
    git -C "$REPO" push -q origin main refs/tags/v1
    git -C "$REPO" update-ref -d refs/remotes/origin/main
    old="$(git -C "$REPO" rev-parse refs/tags/v1)"
    git -C "$REPO" tag -f -a v1 -m "release one, the message corrected" > /dev/null
    new="$(git -C "$REPO" rev-parse refs/tags/v1)"
    [ "$new" != "$old" ]
    [ "$(git -C "$REPO" rev-parse "$new^{commit}")" = "$c" ]                # the same commit under a new tag object
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim +refs/tags/v1
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push:"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/tags/v1)" = "$new" ]
}

@test "round 9a case: a lightweight TAG replaced by an annotated tag at the same commit and force-pushed, over a remote whose commit no remote-tracking ref of this clone contains, passes through a real push and the remote holds the annotated tag (cad898dd2 refused it with a false not-an-ancestor line)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    c="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" tag v1
    git -C "$REPO" push -q origin main refs/tags/v1
    git -C "$REPO" update-ref -d refs/remotes/origin/main
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/tags/v1)" = "$c" ]   # the remote's tag names the commit itself
    git -C "$REPO" tag -f -a v1 -m "release one" > /dev/null
    new="$(git -C "$REPO" rev-parse refs/tags/v1)"
    [ "$(git -C "$REPO" cat-file -t "$new")" = tag ]
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim +refs/tags/v1
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push:"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/tags/v1)" = "$new" ]
}

@test "round 9a table case: the COMMIT the pushed object peels to: a git silent on the peel read alone (rev-parse --verify on the pushed object's ^{commit}), over a rewind no remote-tracking ref covers (a push the ancestry is asked for), is refused naming the peel read's empty answer through a real push, and the remote stays where it was" {
    add_remote
    commit_file base.txt "notes-api" "base"
    c1="$(git -C "$REPO" rev-parse HEAD)"
    commit_file second.txt "nothing to see" "second"
    git -C "$REPO" push -q origin main
    c2="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" update-ref -d refs/remotes/origin/main                  # no remote-tracking ref contains the rewound commit
    git -C "$REPO" reset -q --hard "$c1"
    calls_silent_on git peel '[ "${1:-}" = rev-parse ] && [ "${2:-}" = --verify ]'
    push_refs_through_hook_with_shim +main
    fired peel "rev-parse --verify $c1^{commit}"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${c1:0:10}) were listed as none, and the commit the pushed object peels to, which the ancestry is compared with, could not be read (git rev-parse --verify exited 0 and answered \"\", not a commit)"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$c2" ]
}

@test "round 9a short case: the COMMIT the pushed object peels to: a git whose peel read answers ten hex digits of the commit (exit 0), over a rewind no remote-tracking ref covers, is refused naming the read's cut answer through a real push: the control rewind passes, and the remote stays where it was" {
    add_remote
    commit_file base.txt "notes-api" "base"
    c1="$(git -C "$REPO" rev-parse HEAD)"
    commit_file second.txt "nothing to see" "second"
    git -C "$REPO" push -q origin main
    c2="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" update-ref -d refs/remotes/origin/main
    git -C "$REPO" reset -q --hard "$c1"
    mkdir -p "$TEST_DIR/shim"
    push_refs_through_hook_with_shim +main                                 # the control: the whole peel agrees with merge-base's answer
    [ "$status" -eq 0 ]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$c1" ]
    git -C "$TEST_DIR/remote.git" update-ref refs/heads/main "$c2"
    git -C "$REPO" update-ref -d refs/remotes/origin/main                 # the control's push set it again
    calls_short_on git peel '[ "${1:-}" = rev-parse ] && [ "${2:-}" = --verify ]' bytes:10
    push_refs_through_hook_with_shim +main
    fired_short peel "rev-parse --verify $c1^{commit}"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${c1:0:10}) were listed as none, and the commit the pushed object peels to, which the ancestry is compared with, could not be read (git rev-parse --verify exited 0 and answered \"${c1:0:10}\", not a commit)"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$c2" ]
}

@test "round 9a closure: the COMMIT the pushed object peels to beside a silent ancestry: a git silent on the range listing, the peel read and merge-base at once, through a real push of a ref update whose middle commit adds a banned line, is refused naming the peel read's empty answer, and the remote stays at its base (an empty peel compared with an empty merge-base answer would agree, and the leak would publish)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file leak.txt "seen on TESTHOST" "leak"
    remove_file leak.txt "remove it"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git ancestry '{ [ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]; } || { [ "${1:-}" = rev-parse ] && [ "${2:-}" = --verify ]; } || [ "${1:-}" = merge-base ]'
    push_main_through_hook_with_shim
    fired ancestry "rev-list $sha --not --remotes"
    fired ancestry "rev-parse --verify $sha^{commit}"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) were listed as none, and the commit the pushed object peels to, which the ancestry is compared with, could not be read (git rev-parse --verify exited 0 and answered \"\", not a commit)"* ]]
    at_base
}

@test "round 9a case: the SIZE of the tip's tree over a tip whose tree holds one EMPTY directory alone (a tree built with git mktree and git commit-tree, fsck-clean, which git's own index never writes): the recursive listing is empty while the size is not 0, so a real push is refused naming both causes, a listing that answered short or a tree of empty directories alone (the disclosed residual), and the remote stays at its base (cad898dd2's line named the short listing alone)" {
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    empty="$(git -C "$REPO" mktree < /dev/null)"
    tree="$(printf '040000 tree %s\tempty\n' "$empty" | git -C "$REPO" mktree)"
    sha="$(git -C "$REPO" commit-tree "$tree" -p "$BASE" -m "a tree holding one empty directory")"
    git -C "$REPO" update-ref refs/heads/main "$sha"
    run git -C "$REPO" fsck --no-progress --no-dangling
    [ "$status" -eq 0 ]
    [ -z "$(git -C "$REPO" ls-tree -r "$sha")" ]                            # the recursive listing omits the tree entry
    size="$(git -C "$REPO" cat-file -s "$sha^{tree}")"
    [ "$size" -gt 0 ]
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/main (${sha:0:10}) was listed as empty (git ls-tree -r exited 0 and printed no entry) while git cat-file -s gives its tree's size as $size bytes, so either the listing answered short or the tree holds only empty directories, which git's own index never writes; the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 9a case: two annotated TAGS beside the failed chosen-addresses read, one refused on its tagger's address and one on its message alone, through a real push: the message tag keeps its remedy, re-create it with a clean message, without the configured address the failed read leaves unknown, and the remote gets neither tag (cad898dd2 keyed the tagger's flag on the whole push and withheld it)" {
    add_remote
    commit_file f.txt "plain" "base"
    GIT_COMMITTER_EMAIL=dev@zzsynthuser.example git -C "$REPO" tag -a v1 -m "a release"   # the tagger is the committer identity
    git -C "$REPO" tag -a v2 -m "release two" -m "cut on TESTHOST"                        # the hermetic tagger, a banned message
    fail_config_user_email
    push_refs_through_hook_with_shim refs/tags/v1 refs/tags/v2
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: tag refs/tags/v1 ("*") is tagged as <dev@zzsynthuser.example>: whether this clone is configured to use that address could not be read"* ]]
    [[ "$output" == *"romp pre-push: the MESSAGE of tag refs/tags/v2 ("*") carries a personal identifier on line "* ]]
    [[ "$output" == *"  An annotated TAG's tagger and message are the tag object's own: re-create it with a clean message (git tag -f -a <name> <commit>), and push it again."* ]]
    [[ "$output" != *"re-create it under your configured address"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
    run remote_holds_ref refs/tags/v2
    [ "$status" -ne 0 ]
}

@test "round 9a case: an annotated TAG under the hermetic tagger whose message names the host, beside the failed chosen-addresses read, is refused on its message alone through a real push, and its remedy is the re-create line without the configured address, which the failed read leaves unknown: the remote never gets the tag (cad898dd2 printed the configured-address form)" {
    add_remote
    commit_file f.txt "plain" "base"
    git -C "$REPO" tag -a v2 -m "release two" -m "cut on TESTHOST"
    fail_config_user_email
    push_ref_through_hook_with_shim refs/tags/v2
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the ADDRESSES this clone is configured to use could not be read (git config --get-all user.email exited 128)"* ]]
    [[ "$output" == *"romp pre-push: the MESSAGE of tag refs/tags/v2 ("*") carries a personal identifier on line "* ]]
    [[ "$output" != *"is tagged as <"* ]]                                  # the tagger's address is not refused
    [[ "$output" == *"  An annotated TAG's tagger and message are the tag object's own: re-create it with a clean message (git tag -f -a <name> <commit>), and push it again."* ]]
    [[ "$output" != *"re-create it under your configured address"* ]]
    run remote_holds_ref refs/tags/v2
    [ "$status" -ne 0 ]
}

@test "round 9a case: an annotated TAG refused on both counts, its tagger's address and its message, beside the failed chosen-addresses read, through a real push: the re-create line prints without the configured address, in place of the tag paragraph's first sentence alone, and the remote never gets the tag (cad898dd2 printed the first sentence alone)" {
    add_remote
    commit_file f.txt "plain" "base"
    GIT_COMMITTER_EMAIL=dev@zzsynthuser.example git -C "$REPO" tag -a v1 -m "a release" -m "cut on TESTHOST"
    fail_config_user_email
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: tag refs/tags/v1 ("*") is tagged as <dev@zzsynthuser.example>: whether this clone is configured to use that address could not be read"* ]]
    [[ "$output" == *"romp pre-push: the MESSAGE of tag refs/tags/v1 ("*") carries a personal identifier on line "* ]]
    [[ "$output" == *"  An annotated TAG's tagger and message are the tag object's own: re-create it with a clean message (git tag -f -a <name> <commit>), and push it again."* ]]
    [[ "$output" != *"  An annotated TAG's tagger and message are the tag object's own."$'\n'* ]]
    [[ "$output" != *"re-create it under your configured address"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 9a case: an annotated TAG refused on its tagger's address alone, with the chosen-addresses read whole, keeps the full remedy line, re-create it under your configured address with a clean message, through a real push, and the remote never gets the tag (a remedy that printed the tag paragraph's first sentence alone for it would be red here)" {
    add_remote
    commit_file f.txt "plain" "base"
    GIT_COMMITTER_EMAIL=dev@zzsynthuser.example git -C "$REPO" tag -a v1 -m "a release"
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: tag refs/tags/v1 ("*") is tagged as <dev@zzsynthuser.example>, an address this clone is not configured to use, whose domain carries a personal identifier"* ]]
    [[ "$output" != *"could not be read"* ]]
    [[ "$output" == *"  An annotated TAG's tagger and message are the tag object's own: re-create it under your configured address, with a clean message (git tag -f -a <name> <commit>), and push it again."* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "round 9a case: the newline test reads its records in the shell: a path holding ONE newline, pushed for real under a tr silent on the old test's shape (tr -cd) and again under a tr cutting that answer by one byte, is refused as holding a newline, that line leading, and the remote stays at its base each time (cad898dd2's tr -cd piped to wc counted 0 under both shims, the one passing answer, and never printed the line)" {
    local l first
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'x\n' > "$REPO/"$'odd\nname.txt'
    git -C "$REPO" add -- $'odd\nname.txt'
    git -C "$REPO" commit -qm "a path holding one newline"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on tr newline-test '[ "${1:-}" = -cd ]'
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    first=""; for l in "${lines[@]}"; do case "$l" in "romp pre-push: "*) first=$l; break ;; esac; done
    [ "$first" = "romp pre-push: a path at the tip of refs/heads/main (${sha:0:10}) holds a newline, which the BINARY VERDICT check cannot judge; the scan is incomplete, so the push is refused" ]
    at_base
    calls_short_on tr newline-test '[ "${1:-}" = -cd ]' less:1
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    first=""; for l in "${lines[@]}"; do case "$l" in "romp pre-push: "*) first=$l; break ;; esac; done
    [ "$first" = "romp pre-push: a path at the tip of refs/heads/main (${sha:0:10}) holds a newline, which the BINARY VERDICT check cannot judge; the scan is incomplete, so the push is refused" ]
    at_base
}

@test "round 9a case: a scratch listing the newline test cannot OPEN (a git whose read list of the tip, grep -l -z, takes the read bit off its output file after writing it) is refused naming the test and the file, through a real push of a clean tip, and the remote stays at its base: a failed open is not a listing with no newline (the old pipeline's tr refused it by its status; without this arm the rewrite's own open fails before its read runs, nothing is printed for the tip, and the push passes)" {
    clean_tip_after_base
    git_shim 'if [ "${1:-}" = grep ] && [ "${5:-}" = -z ]; then "$real_git" "$@"; s=$?; chmod 000 /dev/stdout; exit "$s"; fi'   # the read list alone: the content grep carries no -z
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the newline test could not open read); the scan is incomplete, so the push is refused"* ]]
    at_base
}

# ── round 9b (the round 8 rulings' C, F, G and H): the censuses widened, the table's titles read, a cut inside a path ──
# C, F and G live in cases 226, 203 and 227 (their plants appended there, each red at cad898dd2). H.2: the -z listing
# row's end said a record cut inside counts as none, which holds for a cut before the record's tab; a record cut after
# its tab counts as an entry whose object name is whole, and the byte judge refuses it by that name, the refused line
# naming the cut path and a cause read from the cut path's own attributes (the round 8 refuter found nothing published
# at any of 11 cut depths, 2026-09-24). The case below drives that cut through a real push; it owes no red at
# cad898dd2, where the hook behaved so already and the row's text was the defect.
@test "round 9b short case: the -z listing of the tip, cut inside the last path: a git whose verdict check's ls-tree -r -z -l answers its last record, a hidden file, cut two bytes short (inside the path, after the tab; exit 0), through a real push over that file the remote holds at the tip, counts the record as an entry whose object name is whole, which the byte judge refuses by that name: the refused line names the cut path with the unexplained-binary cause and the configuration-key remedy, not the whole path's -diff, and the remote stays at its base" {
    r8b3_hidden_sorted_last
    calls_short_on git z-listing '[ "${1:-}" = ls-tree ] && [ "${3:-}" = -z ]' less:2
    push_main_through_hook_with_shim
    fired_short z-listing "ls-tree -r -z -l $sha"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: zz.tx at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute reads unspecified, so no attribute of its path accounts for the verdict (the blob is 17 bytes; core.bigFileThreshold is not set in this clone's configuration); the identifier scan did not read it, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"  Where a line names no attribute, a configuration key can be what makes git call the file binary: core.bigFileThreshold makes it call every blob over that size binary"* ]]
    [[ "$output" != *"zz.txt"* ]]                                  # the whole path, and its -diff attribute, named nowhere
    at_base
}
# ── round 9d (the round 8 rulings' A, option (b)): the credential feed, its pieces, and the additive run ──
# The round 8 refuters (A.1) found the read inside gitleaks publishing: gitleaks ran git log -p itself and counted
# a commit whole once one of its files had a hunk, so a stream cut inside a commit passed the ERR arm and the
# count arm and a credential in a dropped file published through a real push. The repository owner took option
# (b) (A.2): the hook reads the lines the pushed commits add itself and gitleaks scans exactly those bytes,
# running no git (the design, fold 3's design-b-final, built under romp-manager's rulings of 2026-09-24 on its
# three owner points). The feed's row (the CREDENTIAL FEED of the push) is driven by the cases re-aimed into the
# slots the retired reads held (the table's case and short case, the cut with exit 1 and with a SIGKILL, the tr
# silent and cut, the awk silent, a line before and after the answer); the cases below hold the rest: each
# finding named with its commit and file, the ~ line (the zip and PDF witnesses, red under the mutant that drops
# it), the cap and the overlap of the pieces (the chunk and piece-boundary witnesses, which the round 9 refuters
# found green under CAP=110000 and 130000 and V=4096 and 2500, far from the bounds: each title names the mutant
# range it is red for, and since round 10b the witnesses at the bounds, CAP and V read from the hook, hold both
# bounds, beside the value pins in tests/gitleaks-config.bats; until round 10b this comment said each was red
# under a one-constant mutant of the hook), the changed meaning of a merge and a rename (the owner's item 2: a merge
# that brings in content a remote holds and a pure rename of a published file pass), two refs at one commit fed
# once, the allowlist, and the additive run over the five rules that fire on a file's path (the owner's item 1:
# each rule's witness refused, silent with the run removed; its figure checked like the main run's, the files
# gitleaks' global path allowlist skips left out by the rule the hook states, under either core.quotePath since
# round 9e). Every credential-shaped string is assembled at run time: gitleaks scans this file too.

r9d_witness() {   # <rule>: writes the file the path-scoped rule names, with content only that rule catches (silent in the main run under a piece's digit name); sets wfile
    case "$1" in
        pkcs12-file) wfile=cert.p12; head -c 600 /dev/zero | tr '\0' '\301' > "$REPO/$wfile" ;;
        nuget-config-password) wfile=nuget.config
            printf '<configuration>\n  <packageSourceCredentials>\n    <feed>\n      <add key="Username" value="builder" />\n      <add key="Clear%sPassword" value="%s" />\n    </feed>\n  </packageSourceCredentials>\n</configuration>\n' Text "Qz7$(printf 'w%.0s' 1 2)Kp9Lm2Xv" > "$REPO/$wfile" ;;
        kubernetes-secret-yaml) wfile=secret.yaml
            printf 'apiVersion: v1\nkind: Sec%s\nmetadata:\n  name: probe\ndata:\n  blob: %s\n' ret "$(printf 'QUJD%.0s' 1 2 3)RA==" > "$REPO/$wfile" ;;
        hashicorp-tf-password) wfile=main.tf
            printf 'resource "x" "y" {\n  administrator_login_pass%s = "%s"\n}\n' word "$(printf 'abcde%.0s' 1 2)ab" > "$REPO/$wfile" ;;
        freemius-secret-key) wfile=app.php
            printf '<?php\n$c = array(\n  %ssecret_key%s => %ssk_%s%s,\n);\n' "'" "'" "'" "$(printf 'ab%.0s' 1 2 3 4 5 6 7 8 9 10 11 12 13 14)a" "'" > "$REPO/$wfile" ;;
        *) echo "r9d_witness: no rule $1" >&2; return 1 ;;
    esac
}
r9d_witness_case() {   # <rule>: the witness committed and pushed for real: refused naming the rule, the commit and the file, the remote at its base
    r9d_base
    r9d_witness "$1"
    git -C "$REPO" add -- "$wfile"
    git -C "$REPO" commit -qm "a file the path-scoped rule names"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential ($1) in: $wfile"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [ "$(grep -c 'INF scanned ~' <<< "$output")" -eq 2 ]            # two runs: the pieces, and the path-scoped copy
    at_base
}

@test "round 9d: a finding is named with its commit and file: a credential in a middle commit's a/x.py, between clean commits, is refused naming that commit and path, the token itself never printed, and the remote stays at its base" {
    r9d_base
    for i in 1 2 3; do commit_file "f$i.txt" "clean $i" "c$i"; done
    mkdir -p "$REPO/a"
    commit_file a/x.py "k = \"$(probe_token)\"" "dirty"
    dirty="$(git -C "$REPO" rev-parse HEAD)"
    for i in 6 7; do commit_file "f$i.txt" "clean $i" "c$i"; done
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${dirty:0:10} ADDS a credential (github-pat) in: a/x.py"* ]]
    [ "$(grep -c 'ADDS a credential' <<< "$output")" -eq 1 ]
    [[ "$output" != *"$(probe_token)"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 9d: a credential typed into a merge's conflict resolution (a slack token in r.cfg, a file neither parent holds) is found in the lines in none of its parents and named with the merge commit, and the remote stays at its base" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"
    merge_fixture
    printf 'k = "%s"\n' "$(probe_slack)" > "$REPO/r.cfg"
    git -C "$REPO" add r.cfg
    git -C "$REPO" commit -qm "merge side, with a line of its own"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (slack-bot-token) in: r.cfg"* ]]
    [[ "$output" != *"$(probe_slack)"* ]]
    at_base
}

@test "round 9d: a credential typed into an octopus merge's resolution is found in the lines in none of its three parents (three columns, the hunk header's @ count less one) and named with the merge, and the remote stays at its base" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"
    octopus_fixture
    printf 'k = "%s"\n' "$(probe_token)" > "$REPO/o.cfg"
    git -C "$REPO" add o.cfg
    git -C "$REPO" commit -qm "an octopus with a line of its own"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_octopus "$merge"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (github-pat) in: o.cfg"* ]]
    at_base
}

@test "round 9d: a file whose first line is a zip signature passes clean: the ~ line moves the signature off byte 0, so gitleaks reads the piece whole (a piece that began with it would be read as 0 bytes and refused on the figure: red under the mutant that drops the ~ line)" {
    r9d_base
    printf 'PK\003\004\024\000\nnothing here\n' > "$REPO/aa.zip"
    git -C "$REPO" add aa.zip
    git -C "$REPO" commit -qm "a zip signature, then text"
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" == *"scanned ~22 bytes"* ]]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "round 9d: a file whose first line is a PDF signature with a credential below it is refused naming the commit and file: behind the ~ line gitleaks reads the piece, where it skips a file that begins with the signature, and the remote stays at its base (red under the mutant that drops the ~ line)" {
    r9d_base
    printf '%%PDF-1.4\nk = "%s"\n' "$(probe_token)" > "$REPO/aa.txt"
    git -C "$REPO" add aa.txt
    git -C "$REPO" commit -qm "a PDF signature, then a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: aa.txt"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 9d: the chunk witness: a credential at byte 124,976 of a 3,000,001-byte line with no blank line is found and named, the line cut into overlapping windows of pieces under gitleaks' 100,000-byte read (a single stream of it, read in chunks, missed the token), and the remote stays at its base (red for a CAP of 157,750 or more with V at 16,384, where the next window starts past the token and gitleaks cuts the token's window at its byte 125,000; green under CAP=110000, 130000 and 150000, V=4096, 2500 and 1000 and a one-byte change to the window step or the replay: the round 10b witnesses hold the cap at its bound)" {
    r9d_base
    { head -c 124976 /dev/zero | tr '\0' .; printf ' %s ' "$(probe_token)"; head -c 2874982 /dev/zero | tr '\0' .; printf '\n'; } > "$REPO/bundle.min.js"
    [ "$(wc -c < "$REPO/bundle.min.js")" -eq 3000001 ]
    git -C "$REPO" add bundle.min.js
    git -C "$REPO" commit -qm "one long line"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: bundle.min.js"* ]]
    at_base
}

@test "round 9d: the piece-boundary witness: a PGP private key block that crosses the 98,304-byte cap of a file's first piece, after 97,266 bytes of code lines with no blank line, is found whole in the continuation piece, which repeats the last 16,384 bytes, and named; the remote stays at its base (red for a V of 1,028 or less, whose replay starts past the block's first byte, 1,029 of its bytes lying before the cap; green under CAP=110000, 130000 and 150000, V=4096 and 2500 and a one-byte change to the replay: the round 10b witnesses hold the overlap at its bound)" {
    r9d_base
    k="PGP ""PRIVATE"" KEY BLOCK"
    {
        awk 'BEGIN { for (i = 0; i < 1247; i++) printf "x_%06d = compute(%06d)%51s\n", i, i, "" }'
        printf -- '-----BEGIN %s-----\nVersion: probe\n\n' "$k"
        for i in $(seq 1 31); do printf 'QUJDRUZH%.0s' 1 2 3 4 5 6 7 8; printf '\n'; done
        printf -- '=abcd\n-----END %s-----\n' "$k"
    } > "$REPO/keys.txt"
    git -C "$REPO" add keys.txt
    git -C "$REPO" commit -qm "a key block across the cap"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (private-key) in: keys.txt"* ]]
    at_base
}

@test "round 9d: a merge that brings in content a remote already holds passes (the owner's item 2): main published a credential, a branch merges main, and the merge adds no line in none of its parents, so the branch is pushed with nothing refused (until round 9 the scan read a merge by its first-parent diff and refused this push)" {
    r9d_base
    git -C "$REPO" checkout -q -b feat
    commit_file f.txt "feature" "f1"
    git -C "$REPO" checkout -q main
    commit_file leak.py "k = \"$(probe_token)\"" "leak"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q feat
    git -C "$REPO" merge -q --no-edit main
    is_merge "$(git -C "$REPO" rev-parse HEAD)"
    push_ref_through_hook_with_shim feat
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/feat)" = "$(git -C "$REPO" rev-parse feat)" ]
}

@test "round 9d: a pure rename of a published file passes (the owner's item 2): the rename adds only its edits, none here, so nothing is fed and no scanner runs (until round 9 the scan read a rename as a deletion and an addition and refused this push); a commit removing the published credential passes too" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"
    add_remote
    mkdir -p "$TEST_DIR/shim"
    commit_file old.py "k = \"$(probe_token)\"" "a credential, published"
    git -C "$REPO" push -q origin main
    git -C "$REPO" mv old.py new.py
    git -C "$REPO" commit -qm "a pure rename"
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [[ "$output" != *"scanned ~"* ]]                                  # nothing fed: the scanner never ran
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
    git -C "$REPO" rm -q new.py
    git -C "$REPO" commit -qm "remove it"
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "round 9d: two refs at one commit (a branch and its tag) are fed once each and written once, so one finding line names the commit and the byte figure is one ref's; a tag of a commit the remote holds and a push that only deletes a ref feed nothing, so no scanner runs; and an annotated tag pushed with its new commits passes clean" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" tag v1
    push_refs_through_hook_with_shim main v1
    [ "$status" -ne 0 ]
    [ "$(grep -c "romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: k.py" <<< "$output")" -eq 1 ]
    [[ "$output" == *"scanned ~49 bytes"* ]]                          # one ref's piece: written once though fed twice
    at_base
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
    git -C "$REPO" tag v0 "$BASE"                                     # a tag of the base, which the remote holds
    push_ref_through_hook_with_shim v0
    [ "$status" -eq 0 ]
    [[ "$output" != *"scanned ~"* ]]
    remote_holds_ref refs/tags/v0
    git -C "$REPO" push -q origin "$BASE:refs/heads/gone"
    push_ref_through_hook_with_shim :refs/heads/gone                  # a deletion alone
    [ "$status" -eq 0 ]
    [[ "$output" != *"scanned ~"* ]]
    run remote_holds_ref refs/heads/gone
    [ "$status" -ne 0 ]
    git -C "$REPO" checkout -q -b rel "$BASE"
    commit_file rel.txt "release notes" "a clean release commit"
    git -C "$REPO" tag -a v2 -m "release two"
    push_refs_through_hook_with_shim rel v2
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    remote_holds_ref refs/tags/v2
    remote_holds_ref refs/heads/rel
}

@test "round 9d: the repository's .gitleaks.toml applies to the pieces: RFC 6455's example key is refused without the config, passes with it committed, and a key holding it as a substring is refused under the config, each through a real push" {
    r9d_base
    n="$(printf 'dGhlIHNhbXBsZSBub25jZQ%s' '==')"
    printf 'headers = {"Sec-WebSocket-Key": "%s"}\n' "$n" > "$REPO/ws.py"
    git -C "$REPO" add ws.py
    git -C "$REPO" commit -qm "the nonce, no config"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (generic-api-key) in: ws.py"* ]]
    at_base
    git -C "$REPO" reset -q --hard "$BASE"
    cp "$ROMP_DIR/.gitleaks.toml" "$REPO/.gitleaks.toml"
    git -C "$REPO" add .gitleaks.toml
    git -C "$REPO" commit -qm "the repository's config"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    printf 'headers = {"Sec-WebSocket-Key": "%s"}\n' "$n" > "$REPO/ws.py"
    git -C "$REPO" add ws.py
    git -C "$REPO" commit -qm "the nonce, under the config"
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    printf 'headers = {"Sec-WebSocket-Key": "x%sQ"}\n' "${n%==}" > "$REPO/ws.py"
    git -C "$REPO" add ws.py
    git -C "$REPO" commit -qm "a key holding the nonce"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    BASE="$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (generic-api-key) in: ws.py"* ]]
    at_base
}

@test "round 9d: the path-scoped run, pkcs12-file: a keystore added as cert.p12 is refused naming the rule, the commit and the file (the owner's item 1; the pieces' digit names cannot trigger a rule that fires on a path)" {
    r9d_witness_case pkcs12-file
}

@test "round 9d: the path-scoped run, nuget-config-password: a password in an added nuget.config is refused naming the rule, the commit and the file (the owner's item 1)" {
    r9d_witness_case nuget-config-password
}

@test "round 9d: the path-scoped run, kubernetes-secret-yaml: a Kubernetes Secret in an added secret.yaml is refused naming the rule, the commit and the file (the owner's item 1)" {
    r9d_witness_case kubernetes-secret-yaml
}

@test "round 9d: the path-scoped run, hashicorp-tf-password: a password in an added main.tf is refused naming the rule, the commit and the file (the owner's item 1)" {
    r9d_witness_case hashicorp-tf-password
}

@test "round 9d: the path-scoped run, freemius-secret-key: a secret key in an added app.php is refused naming the rule, the commit and the file (the owner's item 1)" {
    r9d_witness_case freemius-secret-key
}

@test "round 9d: the path-scoped run over the nuget.config and cert.p12 pair in one commit names both, each with its rule, and the remote stays at its base (the pair the design found publishing through a scan of pieces alone)" {
    r9d_base
    r9d_witness nuget-config-password
    r9d_witness pkcs12-file
    git -C "$REPO" add nuget.config cert.p12
    git -C "$REPO" commit -qm "the pair"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (nuget-config-password) in: nuget.config"* ]]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (pkcs12-file) in: cert.p12"* ]]
    at_base
}

@test "round 9d: the path-scoped run leaves out a file gitleaks' global path allowlist skips under its name, by the rule the header states: a pnpm-lock.yaml holding a Kubernetes Secret beside a clean ok.yaml passes, the second run reading ok.yaml's copy alone (until round 10b a copy carried the file's name, and gitleaks would have skipped the lockfile's copy and read fewer bytes than were copied; under the fixed stem it would read it); and a clean file named with the Kelvin sign in place of the lockfile's k passes under core.quotePath=false exactly as under true, since the feed's git quotes every path whatever the clone sets (round 9e)" {
    r9d_base
    r9d_witness kubernetes-secret-yaml
    mv "$REPO/secret.yaml" "$REPO/pnpm-lock.yaml"
    printf 'name: probe\n' > "$REPO/ok.yaml"
    git -C "$REPO" add pnpm-lock.yaml ok.yaml
    git -C "$REPO" commit -qm "a lockfile and a clean yaml"
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(grep -c 'INF scanned ~' <<< "$output")" -eq 2 ]
    [[ "$output" == *"scanned ~14 bytes"* ]]                          # the second run: ok.yaml's copy, its ~ line and its one line
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
    # Round 9e (the round 9d audit's finding 9): pnpm-loc, U+212A (the Kelvin sign, which gitleaks' allowlist
    # case-folds to k) and .yaml, a name the hook's C-locale test does not fold, so the path-scoped run selects it.
    # The feed's git runs as git -c core.quotePath=true, so the name reaches the selection in git's quoted form
    # under either setting, its copy carrying the escapes, which gitleaks reads. Without the -c, core.quotePath=false
    # printed the name raw, gitleaks skipped its copy as pnpm-lock.yaml, and the clean push was refused on that
    # run's figure (read 0 of the 14 bytes). The name is built at run time; the push under true is the control.
    kelvin="$(printf 'pnpm-loc\342\204\252.yaml')"
    mkdir -p "$REPO/qt" "$REPO/qf"
    printf 'name: probe\n' > "$REPO/qt/$kelvin"
    git -C "$REPO" add -- "qt/$kelvin"
    git -C "$REPO" commit -qm "the folded lockfile name, pushed under core.quotePath=true"
    git -C "$REPO" config core.quotePath true
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    under_true="$(grep -o 'INF scanned ~[0-9]* bytes' <<< "$output")"
    [ "$under_true" = "$(printf 'INF scanned ~14 bytes\nINF scanned ~14 bytes')" ]   # the piece, then its copy
    printf 'name: probe\n' > "$REPO/qf/$kelvin"
    git -C "$REPO" add -- "qf/$kelvin"
    git -C "$REPO" commit -qm "the same name, pushed under core.quotePath=false"
    git -C "$REPO" config core.quotePath false
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(grep -o 'INF scanned ~[0-9]* bytes' <<< "$output")" = "$under_true" ]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "round 9d: the disclosed cost of pieces with no real path: a credential in package-lock.json, which gitleaks' git mode exempts by its path, is refused naming the commit and file (excused, where it is a false alarm, in .gitleaks.toml by exact value), and the remote stays at its base" {
    r9d_base
    printf '{\n  "name": "x",\n  "token": "%s"\n}\n' "$(probe_token)" > "$REPO/package-lock.json"
    git -C "$REPO" add package-lock.json
    git -C "$REPO" commit -qm "a token in a lockfile"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: package-lock.json"* ]]
    at_base
}

@test "round 9d: the path-scoped run's figure is checked like the main run's: a scanner that reads the copies cut to three bytes each (a wrapper acting in the copies' directory alone) is refused naming that run and both numbers, and the remote stays at its base" {
    r9d_base
    r9d_witness nuget-config-password
    git -C "$REPO" add nuget.config
    git -C "$REPO" commit -qm "a nuget.config"
    scanner_wrapper 'case "$PWD" in */creds.p) for f in */*; do head -c 3 "$f" > ../cut.tmp; mv ../cut.tmp "$f"; done ;; esac'
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan under the path-scoped rules read 3 of the 222 bytes of added lines it was fed; the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
    at_base
}

# ── round 10a (the round 9 rulings' A, with the coordinator's decisions 1 to 3): every line of the feed accounted for, a merge's binary path read whole, a commit of 64 or more parents refused ──
# The round 9 refuters found the feed's awk passing, silently, every line it did not read (correctness-1): a merge's
# combined diff applies git's binary verdict whatever --text says, printing Binary files differ and no hunk for a
# path git calls binary in the result or in any parent, and a credential in the merge's own lines there published
# through real pushes for each of five causes with the byte figure agreeing; merges of 64 and 65 parents published
# the same way (the rulings' A.5). The cases below hold the fix. A.1: a foreign line and a Binary notice injected
# into a diff --git section are refused, and each shape the awk recognizes passes through a clean push. A.2: a
# merge's binary path is read whole (a witness per cause, the sixth trigger, the large blob across gitleaks' cut, a
# quoted name, the two path-scoped rules; the must-pass merges; a deletion and a gitlink read nothing; the three
# new reads' table and short cases). A.3: the one-parent witnesses, refused at both heads (--text holds there).
# A.5: the parent counts, in both scans, with the new read's table and short cases. A title that says a witness
# published at eee3938a8 records the push made against that head's hook for the round's log; every
# credential-shaped string is assembled at run time.

r10a_cause() {   # <nul|attr|info|afile|driver>: the setting that makes git call evil.txt binary, committed on the remote's base (BASE moves) or configured in REPO (nul: none, the file's own NUL)
    case "$1" in
        nul) ;;
        attr) attributes 'evil.txt -diff'; git -C "$REPO" push -q origin main; BASE="$(git -C "$REPO" rev-parse HEAD)" ;;
        info) mkdir -p "$REPO/.git/info"; printf 'evil.txt -diff\n' >> "$REPO/.git/info/attributes" ;;
        afile) printf 'evil.txt -diff\n' > "$TEST_DIR/attributes-file"; git -C "$REPO" config core.attributesFile "$TEST_DIR/attributes-file" ;;
        driver) attributes 'evil.txt diff=opaque'; git -C "$REPO" config diff.opaque.binary true; git -C "$REPO" push -q origin main; BASE="$(git -C "$REPO" rev-parse HEAD)" ;;
        *) echo "r10a_cause: no cause $1" >&2; return 1 ;;
    esac
}
r10a_evil() {   # <cause>: evil.txt holding a credential line, a NUL ahead of it for the nul cause
    if [ "$1" = nul ]; then printf 'x\0y\nk = "%s"\n' "$(probe_token)"; else printf 'k = "%s"\n' "$(probe_token)"; fi > "$REPO/evil.txt"
}
r10a_merge_open() {   # side and main branches over the current main, each adding a file of its own, and the merge of side into main left open (--no-commit) for the case's own change
    git -C "$REPO" checkout -q -b side
    commit_file side.txt "the web session's line" "side"
    git -C "$REPO" checkout -q main
    commit_file main.txt "the api session's line" "main side"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1 || :
}
r10a_merge_commit() {   # <path>...: the open merge committed with those paths added; merge is its sha, and its combined diff prints exactly one Binary notice, whatever --text says
    git -C "$REPO" add -- "$@"
    git -C "$REPO" commit -qm "the merge, with a change of its own"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    [ "$(git -C "$REPO" diff-tree -p -c --text "$merge" | grep -c '^Binary files differ$')" -eq 1 ]
}
r10a_merge_witness() {   # <cause>: the merge adds evil.txt with a credential, binary by the cause, pushed for real: refused naming the merge and the file, the remote at its base
    r9d_base
    r10a_cause "$1"
    r10a_merge_open
    r10a_evil "$1"
    r10a_merge_commit evil.txt
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (github-pat) in: evil.txt"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" != *"$(probe_token)"* ]]
    at_base
}
r10a_one_parent_witness() {   # <cause>: a one-parent commit adds evil.txt with a credential, binary by the cause (its pairwise diff without --text prints a Binary notice), pushed for real: refused naming the commit and the file
    r9d_base
    r10a_cause "$1"
    r10a_evil "$1"
    git -C "$REPO" add evil.txt
    git -C "$REPO" commit -qm "a file git calls binary"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    [ "$(git -C "$REPO" diff-tree -p "$sha" | grep -c '^Binary files ')" -eq 1 ]
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: evil.txt"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}
r10a_feed_git_rewriting() {   # <awk program>: a git whose feed answer (the one diff-tree given --text) is rewritten by the program, its status kept, the call recorded in calls.rewrite; the real git for every other command
    local real_git real_awk
    real_git="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v git)"
    real_awk="$(PATH=${PATH//"$TEST_DIR/shim:"/} command -v awk)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then\n' "$FEED_GIT"
        printf '    w=$(mktemp %q); %q "$@" > "$w"; s=$?\n' "$TEST_DIR/rewrite.XXXXXX" "$real_git"
        printf '    LC_ALL=C %q %q "$w"\n' "$real_awk" "$1"
        printf '    printf "%%s\\n" "git $*" >> %q; rm -f "$w"; exit "$s"\n' "$TEST_DIR/calls.rewrite"
        printf 'fi\n'
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
r10a_passes() {   # the push of main just made passed: status 0, no romp line, the remote holding main's tip
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse main)" ]
}
r10a_octopus() {   # <parents>: a base on the remote (BASE), that many parents over it, each adding a file of its own, all on the remote, and main moved to a merge of them all that adds evil.txt holding a credential line and a line naming the host, then a commit removing evil.txt; merge is the merge's sha
    local n=$1 i blob tree c base_tree
    local -a parents=() entries=()
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    base_tree="$(git -C "$REPO" ls-tree "$BASE")"
    for ((i = 1; i <= n; i++)); do
        blob="$(printf 'side %d\n' "$i" | git -C "$REPO" hash-object -w --stdin)"
        entries+=("$(printf '100644 blob %s\tp%d.txt' "$blob" "$i")")
        tree="$(printf '%s\n' "$base_tree" "${entries[$((i - 1))]}" | git -C "$REPO" mktree)"
        c="$(git -C "$REPO" commit-tree -p "$BASE" -m "side $i" "$tree")"
        parents+=(-p "$c")
        git -C "$REPO" update-ref "refs/heads/p$i" "$c"
    done
    git -C "$REPO" push -q origin 'refs/heads/p*:refs/heads/p*'
    blob="$(printf 'k = "%s"\nseen on TESTHOST\n' "$(probe_token)" | git -C "$REPO" hash-object -w --stdin)"
    tree="$(printf '%s\n' "$base_tree" "${entries[@]}" "$(printf '100644 blob %s\tevil.txt' "$blob")" | git -C "$REPO" mktree)"
    merge="$(git -C "$REPO" commit-tree "${parents[@]}" -m "a merge of $n parents" "$tree")"
    git -C "$REPO" update-ref refs/heads/main "$merge"
    git -C "$REPO" reset -q --hard main
    [ "$(git -C "$REPO" rev-list --parents -n 1 "$merge" | wc -w)" -eq $((n + 1)) ]
    remove_file evil.txt "remove it"
}
r10a_octopus_scans() {   # <parents>: r10a_octopus, pushed twice for real, once with the credential scan alone and once with the identifier scan alone; each result in cred_status/cred_output and id_status/id_output, the remote at its base after each
    r10a_octopus "$1"
    mkdir -p "$TEST_DIR/shim"
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"
    push_main_through_hook_with_shim
    cred_status=$status; cred_output=$output
    at_base
    export ROMP_NO_GITLEAKS=1 ROMP_PRIVATE_STRINGS="$STRINGS"
    push_main_through_hook_with_shim
    id_status=$status; id_output=$output
    at_base
}

@test "round 10a (A.1): a synthesized foreign line inside a section is refused naming the read and the commit: a feed git that rewrites the credential's added line with a tilde in place of its plus, a line of none of the shapes the awk reads or recognizes, through a real push, is refused as a read the feed could not make, and the remote stays at its base (at eee3938a8 the awk skipped the line silently, nothing was fed, and the credential published)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    r10a_feed_git_rewriting '/^\+k = / { print "~" substr($0, 2); next } { print }'
    push_main_through_hook_with_shim
    [ -s "$TEST_DIR/calls.rewrite" ]
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push could not be read whole (git diff-tree exited 0 and printed a line inside commit 1 of the 1 it was given, ${sha:0:10}, that is none of the shapes the feed reads or recognizes, so what that line stands for went unread); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    at_base
}

@test "round 10a (A.1, A.3): a Binary notice injected into a diff --git section, which --text keeps a real git from printing there, is refused as a foreign line: a feed git that replaces a one-parent commit's hunk for k.py with Binary files /dev/null and b/k.py differ, through a real push of a credential, is refused naming the read and the commit, and the remote stays at its base (at eee3938a8 the awk passed the notice silently and the credential published)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    r10a_feed_git_rewriting '/^(--- |\+\+\+ |@@|\+)/ { next } { print } /^index / { print "Binary files /dev/null and b/k.py differ" }'
    push_main_through_hook_with_shim
    [ -s "$TEST_DIR/calls.rewrite" ]
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push could not be read whole (git diff-tree exited 0 and printed a line inside commit 1 of the 1 it was given, ${sha:0:10}, that is none of the shapes the feed reads or recognizes"* ]]
    at_base
}

@test "round 10a (A.1): each shape the feed's awk recognizes passes through a clean push that produces it, the byte figure agreeing: a new file, an empty file, a missing final newline added and edited, a pure rename and a rename with an edit, a mode change, a deleted file, a symlink and a type change, a gitlink added, changed and removed, names with a space, a tab and a byte past ASCII, and a two-parent merge whose combined hunk carries lines added against one parent and a mode line (a shape dropped from the recognized set refuses its push)" {
    r9d_base
    printf 'one\n' > "$REPO/new.txt"; : > "$REPO/empty.txt"; printf 'no newline' > "$REPO/nonl.txt"
    printf 'a spaced name, line one\n' > "$REPO/a b.txt"; printf 'tabbed\n' > "$REPO/$(printf 't\tb.txt')"; printf 'quoted\n' > "$REPO/$(printf 'na\303\257ve.txt')"
    printf 'mode\n' > "$REPO/run.sh"; printf 'keep\n' > "$REPO/gone.txt"; ln -s new.txt "$REPO/link"
    git -C "$REPO" add -A
    git -C "$REPO" commit -qm "new files: empty, no final newline, spaced, tab and quoted names, a symlink"
    push_main_through_hook_with_shim
    r10a_passes
    [[ "$output" == *"scanned ~"* ]]
    printf 'still no newline' > "$REPO/nonl.txt"
    git -C "$REPO" mv new.txt moved.txt
    git -C "$REPO" mv "a b.txt" "c d.txt"; printf 'a spaced name, line one\nedited\n' > "$REPO/c d.txt"
    chmod +x "$REPO/run.sh"
    git -C "$REPO" rm -q gone.txt
    rm "$REPO/link"; printf 'a file now\n' > "$REPO/link"
    git -C "$REPO" add -A
    git -C "$REPO" commit -qm "an edit without a final newline, renames, a mode change, a deletion, a type change"
    [ "$(git -C "$REPO" diff-tree -M -r --no-commit-id --name-status HEAD | cut -c1 | sort | tr -d '\n')" = "DMMRRT" ]
    push_main_through_hook_with_shim
    r10a_passes
    sub="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" update-index --add --cacheinfo "160000,$sub,sub"
    git -C "$REPO" commit -qm "a gitlink added"
    push_main_through_hook_with_shim
    r10a_passes
    git -C "$REPO" update-index --cacheinfo "160000,$BASE,sub"
    git -C "$REPO" commit -qm "the gitlink changed"
    git -C "$REPO" update-index --force-remove sub
    git -C "$REPO" commit -qm "the gitlink removed"
    push_main_through_hook_with_shim
    r10a_passes
    commit_file m.txt "$(printf 'a\nb\nc')" "a file both sides edit"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b two
    commit_file m.txt "$(printf 'a side\nb\nc')" "one side"
    git -C "$REPO" checkout -q main
    commit_file m.txt "$(printf 'a\nb\nc other')" "the other side"
    git -C "$REPO" merge -q --no-ff --no-commit two > /dev/null 2>&1 || :
    printf 'a side\nb\nc other\nresolved\n' > "$REPO/m.txt"; chmod +x "$REPO/m.txt"
    git -C "$REPO" add m.txt
    git -C "$REPO" commit -qm "the merge, with lines of its own and a mode change"
    is_merge "$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" diff-tree -p -c "$(git -C "$REPO" rev-parse HEAD)" > "$TEST_DIR/combined"
    grep -q '^mode ' "$TEST_DIR/combined"
    grep -q '^++resolved$' "$TEST_DIR/combined"
    grep -qE '^( \+|\+ )' "$TEST_DIR/combined"
    push_main_through_hook_with_shim
    r10a_passes
}

@test "round 10a (A.2): a merge's binary path by a NUL in its first 8000 bytes: the merge adds evil.txt with a NUL and a credential line, its combined diff prints Binary files differ whatever --text says, and the hook reads the merge's own version of the path whole, so the push is refused naming the merge and the file, the remote at its base (published at eee3938a8)" {
    r10a_merge_witness nul
}

@test "round 10a (A.2): a merge's binary path by a committed -diff attribute: refused naming the merge and the file, the remote at its base (published at eee3938a8)" {
    r10a_merge_witness attr
}

@test "round 10a (A.2): a merge's binary path by .git/info/attributes: refused naming the merge and the file, the remote at its base (published at eee3938a8)" {
    r10a_merge_witness info
}

@test "round 10a (A.2): a merge's binary path by the file core.attributesFile names: refused naming the merge and the file, the remote at its base (published at eee3938a8)" {
    r10a_merge_witness afile
}

@test "round 10a (A.2): a merge's binary path by a diff driver whose binary key is true: refused naming the merge and the file, the remote at its base (published at eee3938a8)" {
    r10a_merge_witness driver
}

@test "round 10a (A.2, the coordinator's sixth trigger): a NUL on a parent's side with a text result: the merge resolves evil.txt, binary on one parent, to a text line holding a credential, its combined diff prints Binary files differ for the pair, and the push is refused naming the merge and the file, the remote at its base (published at eee3938a8)" {
    r9d_base
    git -C "$REPO" checkout -q -b side
    printf 'x\0y\n' > "$REPO/evil.txt"
    git -C "$REPO" add evil.txt
    git -C "$REPO" commit -qm "a binary evil.txt on one side"
    git -C "$REPO" checkout -q main
    commit_file evil.txt "the api session's line" "a text evil.txt on the other"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1 || :
    printf 'k = "%s"\n' "$(probe_token)" > "$REPO/evil.txt"
    r10a_merge_commit evil.txt
    [ "$(git -C "$REPO" cat-file -p "$merge:evil.txt" | tr -cd '\0' | wc -c)" -eq 0 ]    # the result is text
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (github-pat) in: evil.txt"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10a (A.2): a merge's binary path of 140,000 bytes with the credential at byte 124,990, across gitleaks' 125,000-byte cut of one file: the whole read is pieced as the feed pieces added lines, so the credential lies whole in a window, and the push is refused naming the merge and the file, the remote at its base (published at eee3938a8; read as one unpieced file it published too, the round 9 rulings)" {
    r9d_base
    r10a_merge_open
    { printf 'x\0\n'; head -c 124986 /dev/zero | tr '\0' .; printf ' %s ' "$(probe_token)"; head -c 14968 /dev/zero | tr '\0' .; printf '\n'; } > "$REPO/big.txt"
    [ "$(wc -c < "$REPO/big.txt")" -eq 140000 ]
    [ "$(grep -abo 'ghp_' "$REPO/big.txt" | cut -d: -f1)" -eq 124990 ]
    r10a_merge_commit big.txt
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (github-pat) in: big.txt"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10a (A.2, the coordinator's decision 1): a merge's binary path whose name git quotes (a byte past ASCII) is matched to the merge's listing by its quoted form, read whole, and refused naming the merge and the quoted path, the remote at its base (published at eee3938a8)" {
    r9d_base
    r10a_merge_open
    q="$(printf 'na\303\257ve.txt')"
    printf 'x\0\nk = "%s"\n' "$(probe_token)" > "$REPO/$q"
    r10a_merge_commit "$q"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (github-pat) in: \"na\\303\\257ve.txt\""* ]]
    at_base
}

@test "round 10a (A.2, the coordinator's decision 1): a merge's cert.p12 binary by a NUL joins the path-scoped run under its name: refused naming pkcs12-file, the merge and the file, two scanner runs logged, the remote at its base (published at eee3938a8)" {
    r9d_base
    r10a_merge_open
    { printf '\0'; head -c 600 /dev/zero | tr '\0' '\301'; } > "$REPO/cert.p12"
    r10a_merge_commit cert.p12
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (pkcs12-file) in: cert.p12"* ]]
    [ "$(grep -c 'INF scanned ~' <<< "$output")" -eq 2 ]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10a (A.2, the coordinator's decision 1): a merge's nuget.config under a committed -diff attribute joins the path-scoped run under its name: refused naming nuget-config-password, the merge and the file, two scanner runs logged, the remote at its base (published at eee3938a8)" {
    r9d_base
    attributes 'nuget.config -diff'
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    r10a_merge_open
    r9d_witness nuget-config-password
    r10a_merge_commit nuget.config
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (nuget-config-password) in: nuget.config"* ]]
    [ "$(grep -c 'INF scanned ~' <<< "$output")" -eq 2 ]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10a (A.2, the coordinator's decision 3, must pass): a clean auto-merge of a -diff file edited on different lines by two branches passes, its path read whole: the byte figure is the two sides' pieces and the whole result blob's, and the remote holds the merge" {
    r9d_base
    printf 'a\nb\nc\nd\ne\nf\ng\n' > "$REPO/lock.dat"
    printf 'lock.dat -diff\n' > "$REPO/.gitattributes"
    git -C "$REPO" add lock.dat .gitattributes
    git -C "$REPO" commit -qm "a -diff file"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b side
    printf 'a\nB side\nc\nd\ne\nf\ng\n' > "$REPO/lock.dat"; git -C "$REPO" commit -qam "one line on one side"
    git -C "$REPO" checkout -q main
    printf 'a\nb\nc\nd\ne\nF main\ng\n' > "$REPO/lock.dat"; git -C "$REPO" commit -qam "another line on the other"
    git -C "$REPO" merge -q --no-ff --no-edit side > /dev/null 2>&1
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    [ "$(git -C "$REPO" diff-tree -p -c --text "$merge" | grep -c '^Binary files differ$')" -eq 1 ]
    size="$(git -C "$REPO" cat-file -s "$merge:lock.dat")"
    push_main_through_hook_with_shim
    r10a_passes
    [[ "$output" == *"scanned ~$((9 + 9 + 2 + size)) bytes"* ]]              # each side's piece (~ and its line), and the whole result behind its ~ line
}

@test "round 10a (A.2, must pass): clean merges of a zip path and of a pdf path, each resolved to a new version that opens with its signature and holds a NUL, pass: the whole read's pieces open with the ~ line, so gitleaks reads them and the byte figure agrees, and the remote holds each merge (read as one unpieced file, gitleaks skipped it and the byte figure refused the clean push: the round 9 rulings)" {
    r9d_base
    for kind in zip pdf; do
        if [ "$kind" = zip ]; then sig='PK\003\004'; else sig='%%PDF-1.4\n'; fi
        printf "$sig"'\0base\n' > "$REPO/x.$kind"
        git -C "$REPO" add "x.$kind"
        git -C "$REPO" commit -qm "a $kind"
        git -C "$REPO" push -q origin main
        git -C "$REPO" checkout -q -b "side-$kind"
        printf "$sig"'\0side\n' > "$REPO/x.$kind"; git -C "$REPO" commit -qam "one side"
        git -C "$REPO" checkout -q main
        printf "$sig"'\0main\n' > "$REPO/x.$kind"; git -C "$REPO" commit -qam "the other"
        git -C "$REPO" merge -q --no-ff --no-commit "side-$kind" > /dev/null 2>&1 || :
        printf "$sig"'\0resolved\nclean text\n' > "$REPO/x.$kind"
        r10a_merge_commit "x.$kind"
        push_main_through_hook_with_shim
        r10a_passes
    done
}

@test "round 10a (A.2, the coordinator's decision 3): a merge's Binary notices for a path it deletes and for a path whose result is a gitlink read nothing: a zero result blob transfers nothing, and a gitlink (mode 160000) is a commit with no blob of its own, so the push passes with the byte figure of the sides' pieces alone (reading either would ask git for an object the clone lacks and refuse the push)" {
    r9d_base
    printf 'bin\0x\n' > "$REPO/tolink.bin"; printf 'bin\0y\n' > "$REPO/del.bin"
    git -C "$REPO" add tolink.bin del.bin
    git -C "$REPO" commit -qm "two binary files"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b side
    printf 'bin\0y side\n' > "$REPO/del.bin"; git -C "$REPO" commit -qam "one side"
    git -C "$REPO" checkout -q main
    printf 'bin\0y main\n' > "$REPO/del.bin"; git -C "$REPO" commit -qam "the other"
    git -C "$REPO" merge -q --no-ff --no-commit side > /dev/null 2>&1 || :
    git -C "$REPO" rm -q -f del.bin
    git -C "$REPO" rm -q -f --cached tolink.bin
    absent="$(printf 'a commit this clone lacks\n' | git -C "$REPO" hash-object --stdin)"
    run git -C "$REPO" cat-file -e "$absent"
    [ "$status" -ne 0 ]
    git -C "$REPO" update-index --add --cacheinfo "160000,$absent,tolink.bin"
    git -C "$REPO" commit -qm "the merge deletes one and makes the other a gitlink"
    merge="$(git -C "$REPO" rev-parse HEAD)"
    [ "$(git -C "$REPO" diff-tree -p -c --text "$merge" | grep -c '^Binary files differ$')" -eq 2 ]
    push_main_through_hook_with_shim
    r10a_passes
    [[ "$output" == *"scanned ~26 bytes"* ]]                                  # the two sides' pieces alone: each a ~ line and bin, 0x01, y and its side's word
}

@test "round 10a (A.3): a one-parent commit adding a file binary by a NUL is read as text (--text), and its credential refused naming the commit and the file (refused at eee3938a8 too: --text holds on a one-parent commit)" {
    r10a_one_parent_witness nul
}

@test "round 10a (A.3): a one-parent commit adding a file under a committed -diff attribute: refused naming the commit and the file (refused at eee3938a8 too)" {
    r10a_one_parent_witness attr
}

@test "round 10a (A.3): a one-parent commit adding a file under .git/info/attributes: refused naming the commit and the file (refused at eee3938a8 too)" {
    r10a_one_parent_witness info
}

@test "round 10a (A.3): a one-parent commit adding a file under the file core.attributesFile names: refused naming the commit and the file (refused at eee3938a8 too)" {
    r10a_one_parent_witness afile
}

@test "round 10a (A.3): a one-parent commit adding a file under a diff driver whose binary key is true: refused naming the commit and the file (refused at eee3938a8 too)" {
    r10a_one_parent_witness driver
}

@test "round 10a (A.5): a merge of 63 parents adding a credential and a line naming the host, removed at the tip, is refused in both scans on what it adds, through real pushes, the remote at its base after each (refused at eee3938a8 too: the feed's awk reads 63 columns)" {
    r10a_octopus_scans 63
    [ "$cred_status" -ne 0 ]
    [[ "$cred_output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (github-pat) in: evil.txt"* ]]
    [[ "$cred_output" != *"parents, and git's combined diff"* ]]
    [ "$id_status" -ne 0 ]
    [[ "$id_output" == *"romp pre-push: commit ${merge:0:10} ADDS a personal identifier in:"* ]]
    [[ "$id_output" != *"parents, and git's combined diff"* ]]
}

@test "round 10a (A.5, the coordinator's decision 2): a merge of 64 parents, whose combined diff prints no hunk for what it adds, is refused by name in both scans, through real pushes, the remote at its base after each (at eee3938a8 the credential published, and the identifier scan refused it only as a hidden file)" {
    r10a_octopus_scans 64
    [ "$cred_status" -ne 0 ]
    [[ "$cred_output" == *"romp pre-push: the ADDED LINES of commit ${merge:0:10} cannot be read for the credential scan: it has 64 parents, and git's combined diff of a merge of 64 or more parents prints no hunk for the lines it adds, or prints them with a space in their last column; the scan is incomplete, so the push is refused"* ]]
    [ "$id_status" -ne 0 ]
    [[ "$id_output" == *"romp pre-push: the ADDED LINES of commit ${merge:0:10} cannot be read for the identifier scan: it has 64 parents"* ]]
}

@test "round 10a (A.5, the coordinator's decision 2): a merge of 65 parents, whose combined diff prints each line it adds with a space in its last column, is refused by name in both scans, through real pushes, the remote at its base after each (at eee3938a8 both scans published it)" {
    r10a_octopus_scans 65
    [ "$cred_status" -ne 0 ]
    [[ "$cred_output" == *"romp pre-push: the ADDED LINES of commit ${merge:0:10} cannot be read for the credential scan: it has 65 parents"* ]]
    [ "$id_status" -ne 0 ]
    [[ "$id_output" == *"romp pre-push: the ADDED LINES of commit ${merge:0:10} cannot be read for the identifier scan: it has 65 parents"* ]]
}

@test "round 10a (A.5): the identifier scan's PARENT COUNT of a commit cut short over merges of 64 and 65 parents (a git whose rev-list --parents answers the merge and 63 of its parents, exit 0) escapes the refusal by name and is refused all the same: at 64 its header-only section is judged by its bytes, at 65 its lines are read in fewer columns, each through a real push, the remote at its base" {
    for n in 64 65; do
        rm -rf "$REPO" "$TEST_DIR/remote.git"
        rm -f "$TEST_DIR/shim/git"; hash -r                    # the first pass's shim: the fixture's own git is the real one
        git -C "$TEST_DIR" init -q repo
        git -C "$REPO" symbolic-ref HEAD refs/heads/main
        git -C "$REPO" config user.email t@example.invalid
        git -C "$REPO" config user.name Tester
        git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
        r10a_octopus "$n"
        export ROMP_NO_GITLEAKS=1 ROMP_PRIVATE_STRINGS="$STRINGS"
        calls_short_on git idcount '[ "${1:-}" = rev-list ] && [ "${2:-}" = --parents ] && [ "${3:-}" = -n ]' "bytes:$((41 * 64 - 1))"
        push_main_through_hook_with_shim
        fired_short idcount "--parents"
        [ "$status" -ne 0 ]
        [[ "$output" != *"parents, and git's combined diff"* ]]
        if [ "$n" -eq 64 ]; then
            [[ "$output" == *"romp pre-push: evil.txt in commit ${merge:0:10} is text that git calls binary"* ]]
        else
            [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a personal identifier in:"* ]]
        fi
        at_base
    done
}

@test "round 10a table case: the PARENT COUNTS of the pushed commits: a git silent on the parent counts' rev-list alone (--no-walk=unsorted, exit 0, its stdin drained), the identifier scan off, through a real push of a credential, is refused naming the commits it ended short of, and the remote stays at its base" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    calls_silent_on git parents '[[ " $* " == *" --no-walk=unsorted "* ]]'
    push_main_through_hook_with_shim
    fired parents "--no-walk=unsorted"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the PARENT COUNTS of the pushed commits were read short for the credential scan (git rev-list exited 0 and ended after 0 of the commits it was given); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 10a short case: the PARENT COUNTS of the pushed commits: a git whose parent counts' rev-list answers a merge's header and its parents cut inside the second parent's name (exit 0, the tail marker lost), through a real push of the merge, is refused naming the tail marker, and the remote stays at its base: a cut there reads a merge as fewer parents, which would pass a merge of 64 or more" {
    r9d_base
    r10a_merge_open
    git -C "$REPO" push -q origin main side                  # both parents on the remote: the merge is the push's one commit, its parents the answer's last line
    BASE="$(git -C "$REPO" rev-parse main)"
    printf 'k = "%s"\n' "$(probe_token)" > "$REPO/own.txt"
    git -C "$REPO" add own.txt
    git -C "$REPO" commit -qm "the merge, with a file of its own"
    is_merge "$(git -C "$REPO" rev-parse HEAD)"
    calls_short_on git parents '[[ " $* " == *" --no-walk=unsorted "* ]]' less:60
    push_main_through_hook_with_shim
    fired_short parents "--no-walk=unsorted"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the PARENT COUNTS of the pushed commits were read short for the credential scan (git rev-list exited 0 and did not close commit 1 of those it was given with the line naming it again, the tail marker its format asks for after the parents); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 10a table case: the RESULT listing of a merge: a git silent on the merge's combined raw listing alone (-c --raw --no-commit-id --no-abbrev), through a real push of a merge whose binary path holds a credential, is refused naming the path the listing named no record for, and the remote stays at its base" {
    r9d_base
    r10a_merge_open
    r10a_evil nul
    r10a_merge_commit evil.txt
    calls_silent_on git rlist '[[ " $* " == *" -c --raw --no-commit-id --no-abbrev "* ]]'
    push_main_through_hook_with_shim
    fired rlist "--no-abbrev"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the RESULT listing of merge ${merge:0:10} names 0 records for evil.txt, a path its combined diff calls binary, where a merge's listing holds one (git diff-tree exited 0), so that path cannot be read whole for the credential scan; the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 10a short case: the RESULT listing of a merge: a git whose combined raw listing answers its one record cut inside the path (exit 0), through a real push of a merge whose binary path holds a credential, is refused naming the path that matched no record, and the remote stays at its base" {
    r9d_base
    r10a_merge_open
    r10a_evil nul
    r10a_merge_commit evil.txt
    calls_short_on git rlist '[[ " $* " == *" -c --raw --no-commit-id --no-abbrev "* ]]' less:3
    push_main_through_hook_with_shim
    fired_short rlist "--no-abbrev"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the RESULT listing of merge ${merge:0:10} names 0 records for evil.txt, a path its combined diff calls binary"* ]]
    at_base
}

@test "round 10a table case: the SIZE of a merge's binary blob: a git silent on cat-file -s alone, through a real push of a merge whose binary path holds a credential, is refused naming the empty answer, not a count, and the remote stays at its base" {
    r9d_base
    r10a_merge_open
    r10a_evil nul
    r10a_merge_commit evil.txt
    calls_silent_on git bsize '[ "${1:-}" = cat-file ] && [ "${2:-}" = -s ]'
    push_main_through_hook_with_shim
    fired bsize "cat-file -s"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the SIZE of evil.txt in merge ${merge:0:10}, a path the credential scan reads whole, could not be read (git cat-file -s exited 0 and answered \"\", not a count); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 10a short case: the SIZE of a merge's binary blob: a git whose cat-file -s answers the first digit of the size (exit 0), through a real push of a merge whose binary path holds a credential, is refused naming both counts, the bytes read and the cut size, and the remote stays at its base" {
    r9d_base
    r10a_merge_open
    r10a_evil nul
    r10a_merge_commit evil.txt
    size="$(git -C "$REPO" cat-file -s "$merge:evil.txt")"
    calls_short_on git bsize '[ "${1:-}" = cat-file ] && [ "${2:-}" = -s ]' bytes:1
    push_main_through_hook_with_shim
    fired_short bsize "cat-file -s"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of evil.txt in merge ${merge:0:10} was read short for the credential scan (git cat-file -p exited 0 and answered $size bytes of the ${size:0:1} its SIZE read names); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 10a table case: the CONTENT of a merge's binary blob: a git silent on cat-file -p alone (exit 0, nothing printed), the identifier scan off, through a real push of a merge whose binary path holds a credential, is refused naming the bytes it answered against the blob's size, and the remote stays at its base" {
    r9d_base
    r10a_merge_open
    r10a_evil nul
    r10a_merge_commit evil.txt
    size="$(git -C "$REPO" cat-file -s "$merge:evil.txt")"
    calls_silent_on git bcontent '[ "${1:-}" = cat-file ] && [ "${2:-}" = -p ]'
    push_main_through_hook_with_shim
    fired bcontent "cat-file -p"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of evil.txt in merge ${merge:0:10} was read short for the credential scan (git cat-file -p exited 0 and answered 0 bytes of the $size its SIZE read names); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 10a short case: the CONTENT of a merge's binary blob: a git whose cat-file -p answers all but its last five bytes (exit 0, the credential cut with them), through a real push of a merge whose binary path holds a credential, is refused naming the bytes it answered against the blob's size, and the remote stays at its base" {
    r9d_base
    r10a_merge_open
    r10a_evil nul
    r10a_merge_commit evil.txt
    size="$(git -C "$REPO" cat-file -s "$merge:evil.txt")"
    calls_short_on git bcontent '[ "${1:-}" = cat-file ] && [ "${2:-}" = -p ]' less:5
    push_main_through_hook_with_shim
    fired_short bcontent "cat-file -p"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CONTENT of evil.txt in merge ${merge:0:10} was read short for the credential scan (git cat-file -p exited 0 and answered $((size - 5)) bytes of the $size its SIZE read names); the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"ADDS a credential"* ]]                                  # the cut took the credential: the refusal is the read's alone
    at_base
}

# ── round 10b (the round 9 rulings' B, C, E, F, G, H and A.2's cost, with the coordinator's decisions 4 to 7): a spaced path-scoped name, the bounds at the bounds, the scanner's floor, the copies' fixed names, the directories past the argument limit, three arms, the cost ──
# The round 9 rulings' groups after round 10a. B (tests-1): the feed strips git's trailing tab from a +++ line
# whose path holds a space, so a spaced path-scoped name reaches the additive run. C (tests-2, decision 5): the
# cap and the overlap tested at their bounds, CAP and V read from the hook's awk line, never a literal (the value
# pins, CAP at most 100,000 and V equal to 16,384, live in tests/gitleaks-config.bats); what decides a match
# across a piece boundary is how many of its bytes lie BEFORE the boundary, so the property witnesses place a
# match with exactly V there (refused) and one with V + 1 (published: the disclosed limit, outside the stated
# bound), by the windows of a long line and by the replay between lines; the CAP witnesses are sized by
# gitleaks' own read (100,000 bytes and a 25,000-byte peek that stops at a blank line), so a CAP past either
# bound puts a whole witness file in one piece that gitleaks cuts. E (regression-1, decision 6): the scanner's
# version, read where a scan would run, gitleaks 8.25.0 or later. F (correctness-2, regression-2, decision 4):
# each path-scoped copy named by its piece's number and the matched suffix, lower-cased, in its piece's
# directory. G (correctness-3, decision 7): those directories made past the argument limit. H (tests-3, tests-4):
# the feed's count arm driven by a short list file, the dropped-rule refusal and a relative ROMP_GITLEAKS;
# tests-5's positive record is the re-aimed log.showRoot case above. And A.2's disclosed cost with its witness.
# A title that says a witness is red at eee3938a8 or under a mutant records the run made against that hook for
# the round's log; every credential-shaped string is assembled at run time.

r10b_constants() {   # CAP, V and LW read from the hook's one awk line CAP = <n>; V = <n>; LW = CAP - V - 4, never a literal: no such line, or two, fails the case
    local line
    line="$(grep -E '^[[:space:]]*CAP = [0-9]+; V = [0-9]+; LW = CAP - V - 4$' "$HOOK" || true)"
    [ -n "$line" ] || { echo "the hook holds no line CAP = <n>; V = <n>; LW = CAP - V - 4" >&2; return 1; }
    [ "$(wc -l <<< "$line")" -eq 1 ] || { echo "the hook holds more than one CAP and V line" >&2; return 1; }
    CAP="$(sed -E 's/.*CAP = ([0-9]+);.*/\1/' <<< "$line")"
    V="$(sed -E 's/.*; V = ([0-9]+);.*/\1/' <<< "$line")"
    LW=$((CAP - V - 4))
}
r10b_key() {   # <bytes>: a private key block of exactly that many bytes on one line, its markers and a body of A between them, no newline (the marker words split, so this file holds no block); fewer than 116 bytes (the markers and the rule's 64-byte body) fails
    local k="PRIVATE"" KEY"
    [ "$1" -ge 116 ] || { echo "r10b_key: a block of $1 bytes is shorter than the 116 the private-key rule reads" >&2; return 1; }
    printf -- '-----BEGIN %s-----' "$k"; head -c "$(($1 - 52))" /dev/zero | tr '\0' A; printf -- '-----END %s-----' "$k"
}
r10b_window_push() {   # <bytes of the block before the first window's end>: one line longer than LW whose key block, one byte longer than those bytes, ends one byte past the first window's end (LW and V from r10b_constants, the caller's), committed as wide.txt and pushed for real; sha is the commit
    local before=$1
    { head -c "$((LW - before))" /dev/zero | tr '\0' .; r10b_key "$((before + 1))"; head -c 1000 /dev/zero | tr '\0' .; printf '\n'; } > "$REPO/wide.txt"
    [ "$(wc -c < "$REPO/wide.txt")" -eq $((LW + 1002)) ]
    [ "$(LC_ALL=C grep -abo -- '-----BEGIN' "$REPO/wide.txt" | cut -d: -f1)" -eq $((LW - before)) ]    # the block's first byte, 0-based: before bytes of it lie in the first window
    git -C "$REPO" add wide.txt
    git -C "$REPO" commit -qm "a key block across a window's end"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
}
r10b_block_lines() {   # <bytes>: key block lines of exactly that many bytes, newlines counted: the BEGIN line (28 bytes), body lines of 64 A, and two shorter body lines to make the count; fewer than 30 bytes fails
    local n=$(($1 - 28)) a k="PRIVATE"" KEY"
    [ "$1" -ge 30 ] || { echo "r10b_block_lines: $1 bytes cannot hold the BEGIN line and a body line" >&2; return 1; }
    printf -- '-----BEGIN %s-----\n' "$k"
    while [ "$n" -gt 130 ]; do printf '%064d\n' 0 | tr 0 A; n=$((n - 65)); done
    if [ "$n" -gt 65 ]; then a=$((n / 2)); head -c "$((a - 1))" /dev/zero | tr '\0' A; printf '\n'; n=$((n - a)); fi
    [ "$n" -eq 0 ] || { head -c "$((n - 1))" /dev/zero | tr '\0' A; printf '\n'; }
}
r10b_replay_push() {   # <bytes of the block before the piece boundary>: code lines and the key block's first lines filling a first piece to exactly CAP bytes with its ~ line (CAP and V from r10b_constants, the caller's), the rest of the block after it, so the block's next line starts the second piece, which replays the last V bytes; committed as keys.pem and pushed for real; sha is the commit
    local before=$1 p i
    p=$((CAP - 2 - before))                                          # the code lines' bytes: one line of 100 to 199, then lines of 100
    {
        head -c "$((100 + p % 100 - 1))" /dev/zero | tr '\0' x; printf '\n'
        for ((i = 1; i < p / 100; i++)); do printf 'x_%06d = compute(%06d) # %070d\n' "$i" "$i" 0; done
        r10b_block_lines "$before"
        for i in 1 2 3; do printf '%064d\n' 0 | tr 0 A; done
        printf -- '-----END %s-----\n' "PRIVATE"" KEY"
    } > "$REPO/keys.pem"
    [ "$(LC_ALL=C grep -abo -- '-----BEGIN' "$REPO/keys.pem" | cut -d: -f1)" -eq "$p" ]            # the block starts p bytes in: the ~ line, p bytes and before bytes of the block make CAP
    [ "$(head -c "$((p + before))" "$REPO/keys.pem" | tail -c 1 | od -An -c | tr -d ' ')" = '\n' ]   # the boundary falls between lines
    git -C "$REPO" add keys.pem
    git -C "$REPO" commit -qm "a key block across the cap"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
}
r10b_spaced_witness() {   # <rule> <path holding a space>: the rule's witness committed under that path and pushed for real: refused naming the rule, the commit and the path, two scanner runs logged (the path-scoped run happened), the remote at its base
    r9d_base
    r9d_witness "$1"
    mkdir -p "$REPO/$(dirname -- "$2")"
    mv "$REPO/$wfile" "$REPO/$2"
    git -C "$REPO" add -- "$2"
    git -C "$REPO" commit -qm "a path-scoped file under a name holding a space"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    [ "$(git -C "$REPO" diff-tree -p --text "$sha" | grep -c $'^+++ b/.*\t$')" -eq 1 ]            # git ends that +++ line with a tab
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential ($1) in: $2"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [ "$(grep -c 'INF scanned ~' <<< "$output")" -eq 2 ]
    at_base
}
r10b_scanner_answering() {   # <answer>: a gitleaks on ROMP_GITLEAKS that answers gitleaks version with that line (exit 0) and runs the real scanner (GL at the first call, from r9d_base) for every other command, each call recorded in calls.scanner
    : "${R10B_GL:=$GL}"
    mkdir -p "$TEST_DIR/scanner"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'printf "%%s\\n" "gitleaks $*" >> %q\n' "$TEST_DIR/calls.scanner"
        printf 'if [ "${1:-}" = version ]; then printf "%%s\\n" %q; exit 0; fi\n' "$1"
        printf 'exec %q "$@"\n' "$R10B_GL"
    } > "$TEST_DIR/scanner/gitleaks"
    chmod 755 "$TEST_DIR/scanner/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/scanner/gitleaks"
}
r10b_gitleaks_on_path() {   # the real scanner first on PATH as gitleaks, so the calls_* shims take it for the real tool; the case then names their shim in ROMP_GITLEAKS
    real_gitleaks
    mkdir -p "$TEST_DIR/glbin"
    ln -sf "$GL" "$TEST_DIR/glbin/gitleaks"
    export PATH="$TEST_DIR/glbin:$PATH"
}
R10B_FLOOR_FIX="the credential scan needs gitleaks 8.25.0 or later: upgrade it, point ROMP_GITLEAKS at another binary, or set ROMP_NO_GITLEAKS=1 for one push; the scan is incomplete, so the push is refused"
r10b_long_name() {   # <suffix>: name, 35 two-byte characters (70 bytes past ASCII) and the suffix, and quoted, the name as git quotes it (four bytes for each of those, and the double quotes)
    name="$(printf '\303\251%.0s' $(seq 1 35))$1"
    quoted="\"$(printf '\\303\\251%.0s' $(seq 1 35))$1\""
}
r10b_long_witness() {   # <rule> <suffix>: the rule's witness under a long name ending in the suffix, pushed for real: refused naming the rule, the commit and the real path as git quotes it, two scanner runs logged, the remote at its base
    r9d_base
    r9d_witness "$1"
    r10b_long_name "$2"
    mv "$REPO/$wfile" "$REPO/$name"
    git -C "$REPO" add -- "$name"
    git -C "$REPO" commit -qm "a path-scoped file under a long name"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    [ "${#quoted}" -gt 257 ]                                              # past 255 bytes as git quotes it, its two double quotes aside
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential ($1) in: $quoted"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" != *"File name too long"* ]]
    [ "$(grep -c 'INF scanned ~' <<< "$output")" -eq 2 ]
    at_base
}

@test "round 10b (B, tests-1): a path-scoped credential under a name holding a space, my nuget.config (nuget-config-password, which only the additive run catches), pushed for real, is refused naming the rule, the commit and the file, two scanner runs logged, the remote at its base: the feed strips the tab git ends that +++ line with (red by publication under the mutant deleting the strip, which leaves the name ending in a tab, so the selection skips it)" {
    r10b_spaced_witness nuget-config-password "my nuget.config"
}

@test "round 10b (B, tests-1): a path-scoped credential under a path whose DIRECTORY holds a space, prod certs/cert.p12 (pkcs12-file), pushed for real, is refused naming the rule, the commit and the path, two scanner runs logged, the remote at its base: git ends the +++ line with a tab whenever the path holds a space anywhere (red by publication under the mutant deleting the strip)" {
    r10b_spaced_witness pkcs12-file "prod certs/cert.p12"
}

@test "round 10b (C, the property pin by windows): a private key block of V + 1 bytes with exactly V of them before the end of a long line's first window (V and LW read from the hook) is whole in the next window, which starts V bytes back, and refused naming it, the remote at its base (red under a mutant whose windows overlap by fewer than V bytes, a window step past LW - V; green under a V mutant, which moves the placement with it and which the value pin catches)" {
    r9d_base
    r10b_constants
    r10b_window_push "$V"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (private-key) in: wide.txt"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10b (C, OUTSIDE the stated bound, the disclosed limit): a private key block of V + 2 bytes with V + 1 of them before the end of a long line's first window, the first loss measured on the hook's own windows, is whole in neither window and PUBLISHED, the byte figure agreeing (published at eee3938a8 too; red, refused, under a mutant whose windows overlap by more than V bytes, which would widen the bound the header states)" {
    r9d_base
    r10b_constants
    r10b_window_push "$((V + 1))"
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$sha" ]
}

@test "round 10b (C, the property pin by the replay): a private key block with exactly V of its bytes before a piece boundary between lines (a first piece of exactly CAP bytes, CAP and V read from the hook) is whole in the next piece, which replays the last V bytes, and refused naming it, the remote at its base (red under a mutant replaying fewer than V bytes; green under a V mutant, which the value pin catches)" {
    r9d_base
    r10b_constants
    r10b_replay_push "$V"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (private-key) in: keys.pem"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10b (C, OUTSIDE the stated bound, the disclosed limit): a private key block with V + 1 of its bytes before a piece boundary between lines is whole in neither piece and PUBLISHED, the byte figure agreeing (published at eee3938a8 too; red, refused, under a mutant replaying more than V bytes)" {
    r9d_base
    r10b_constants
    r10b_replay_push "$((V + 1))"
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$sha" ]
}

@test "round 10b (C, the CAP witness at gitleaks' 125,000-byte cut): a 125,101-byte file with no blank line, a token across its byte 125,000, is pieced at CAP (read from the hook) with the token whole in the second piece and refused naming it, the figure the file, two ~ lines and V replayed bytes, the remote at its base (red by publication for any CAP of 125,103 or more, where the file and its ~ line make one piece gitleaks cuts at byte 125,000: the CAP=130000 mutant)" {
    r9d_base
    r10b_constants
    {
        awk 'BEGIN { for (i = 0; i < 1249; i++) printf "x_%06d = compute(%06d) # %070d\n", i, i, 0 }'
        head -c 89 /dev/zero | tr '\0' .; printf ' %s ' "$(probe_token)"; head -c 69 /dev/zero | tr '\0' .; printf '\n'
    } > "$REPO/long.txt"
    [ "$(wc -c < "$REPO/long.txt")" -eq 125101 ]
    [ "$(grep -abo 'ghp_' "$REPO/long.txt" | cut -d: -f1)" -eq 124990 ]
    git -C "$REPO" add long.txt
    git -C "$REPO" commit -qm "a token across byte 125,000"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: long.txt"* ]]
    [[ "$output" == *"scanned ~$((125101 + 4 + V)) bytes"* ]]                    # two pieces, the second replaying V bytes
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10b (C, the blank-line witness for the band from 100,000 to 125,000): a PGP private key block whose blank line falls at byte 100,000 of a one-piece reading (a 100,035-byte file) is pieced at CAP (read from the hook) with the block whole in the second piece and refused naming it, the figure the file, two ~ lines and V replayed bytes, the remote at its base (red by publication for any CAP of 100,037 or more, where the file and its ~ line make one piece that gitleaks cuts at that blank line inside its 25,000-byte peek: the CAP=110000 and CAP=130000 mutants; the 36 values above 100,000 below that are the value pin's)" {
    r9d_base
    r10b_constants
    k="PGP ""PRIVATE"" KEY BLOCK"
    {
        awk 'BEGIN { for (i = 0; i < 998; i++) printf "x_%06d = compute(%06d) # %070d\n", i, i, 0 }'
        printf -- '-----BEGIN %s-----\nVersion: probe\nComment: ' "$k"; head -c 135 /dev/zero | tr '\0' c; printf '\n\n'
        printf -- '-----END %s-----\n' "$k"
    } > "$REPO/keys.asc"
    [ "$(wc -c < "$REPO/keys.asc")" -eq 100035 ]
    [ "$(LC_ALL=C grep -ab -x '' "$REPO/keys.asc" | head -n 1 | cut -d: -f1)" -eq 99998 ]   # the blank line: byte 100,000 behind the ~ line
    git -C "$REPO" add keys.asc
    git -C "$REPO" commit -qm "a key block whose blank line falls past byte 100,000"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (private-key) in: keys.asc"* ]]
    [[ "$output" == *"scanned ~$((100035 + 4 + V)) bytes"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}

@test "round 10b table case: the VERSION of the scanner: a gitleaks silent on its version alone (exit 0, nothing printed), through a real push of a credential, is refused naming the empty answer, the floor and the three remedies, neither scanner run made, and the remote stays at its base" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    r10b_gitleaks_on_path
    calls_silent_on gitleaks gversion '[ "${1:-}" = version ]'
    export ROMP_GITLEAKS="$TEST_DIR/shim/gitleaks"
    push_main_through_hook_with_shim
    fired gversion "gitleaks version"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the VERSION of gitleaks ($ROMP_GITLEAKS) answered nothing (gitleaks version exited 0), where a release answers its dotted version, so whether it can run the scan is unknown; $R10B_FLOOR_FIX"* ]]
    [[ "$output" != *"scanned ~"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    at_base
}

@test "round 10b short case: the VERSION of the scanner: a gitleaks whose version answer is cut to its first four bytes (exit 0: a release's 8.30.1 read as 8.30), through a real push of a credential, is refused naming the cut answer, not a dotted version, neither scanner run made, and the remote stays at its base" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    r10b_gitleaks_on_path
    calls_short_on gitleaks gversion '[ "${1:-}" = version ]' bytes:4
    export ROMP_GITLEAKS="$TEST_DIR/shim/gitleaks"
    push_main_through_hook_with_shim
    fired_short gversion "gitleaks version"
    [ "$status" -ne 0 ]
    cut="$("$GL" version | head -c 4)"
    [[ "$output" == *"romp pre-push: the VERSION of gitleaks ($ROMP_GITLEAKS) answered \"$cut\" (gitleaks version exited 0), not a dotted version such as 8.30.1, so whether it can run the scan is unknown; $R10B_FLOOR_FIX"* ]]
    [[ "$output" != *"scanned ~"* ]]
    at_base
}

@test "round 10b (E): a gitleaks older than the floor is refused by name at the version gate: a scanner answering 8.24.3, 8.9.0 (a floor compared as text would take 9 for more than 25) or 7.30.0 to its version, the real scanner otherwise, through a real push of a clean commit, is refused naming the version, the floor 8.25.0 and the three remedies, neither scanner run made, the remote at its base (red at eee3938a8, which reads no version: the clean push published there)" {
    r9d_base
    commit_file ok.txt "nothing to see" "a clean commit"
    for old in 8.24.3 8.9.0 7.30.0; do
        rm -f "$TEST_DIR/calls.scanner"
        r10b_scanner_answering "$old"
        push_main_through_hook_with_shim
        [ "$status" -ne 0 ]
        [[ "$output" == *"romp pre-push: gitleaks $old ($ROMP_GITLEAKS) is older than 8.25.0, so the scan cannot run; $R10B_FLOOR_FIX"* ]]
        [[ "$output" == *"gitleaks could not scan"* ]]
        [[ "$output" == *"Fix the scanner (gitleaks 8.25.0 or later) or its config"* ]]
        [[ "$output" != *"scanned ~"* ]]
        [ "$(grep -c '^gitleaks dir ' "$TEST_DIR/calls.scanner" || true)" -eq 0 ]
        at_base
    done
}

@test "round 10b (E): a gitleaks at the floor proceeds: a scanner answering 8.25.0, or v8.25.0 (a leading v taken), runs both scans as the real one does, so a clean push passes with the byte figure agreeing and a credential is refused naming it, each through a real push" {
    r9d_base
    for answer in 8.25.0 v8.25.0; do
        rm -f "$TEST_DIR/calls.scanner"
        r10b_scanner_answering "$answer"
        commit_file "ok-$answer.txt" "nothing to see" "a clean commit"
        push_main_through_hook_with_shim
        r10a_passes
        [[ "$output" == *"scanned ~"* ]]
        grep -q '^gitleaks version$' "$TEST_DIR/calls.scanner"
        grep -q '^gitleaks dir ' "$TEST_DIR/calls.scanner"
        BASE="$(git -C "$REPO" rev-parse HEAD)"
    done
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: k.py"* ]]
    at_base
}

@test "round 10b (E): an answer that is not a dotted version is refused naming it: a scanner answering version is set by build process, a build from source's answer, the real scanner otherwise, through a real push of a clean commit, is refused naming the answer, the floor and the three remedies, neither scanner run made, the remote at its base" {
    r9d_base
    commit_file ok.txt "nothing to see" "a clean commit"
    r10b_scanner_answering "version is set by build process"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the VERSION of gitleaks ($ROMP_GITLEAKS) answered \"version is set by build process\" (gitleaks version exited 0), not a dotted version such as 8.30.1, so whether it can run the scan is unknown; $R10B_FLOOR_FIX"* ]]
    [[ "$output" != *"scanned ~"* ]]
    at_base
}

@test "round 10b (E): the version is read where a scan would run, and nowhere else: under a scanner answering 8.24.3, a push that feeds no bytes (a pure rename of a published file, then a commit deleting it) passes with no gitleaks call at all, where a push with content is then refused at the gate" {
    r9d_base
    commit_file old.txt "published" "a file, published"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    r10b_scanner_answering 8.24.3
    git -C "$REPO" mv old.txt new.txt
    git -C "$REPO" commit -qm "a pure rename"
    git -C "$REPO" rm -q new.txt
    git -C "$REPO" commit -qm "remove it"
    push_main_through_hook_with_shim
    r10a_passes
    [ ! -e "$TEST_DIR/calls.scanner" ]
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    commit_file ok.txt "nothing to see" "a clean commit"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: gitleaks 8.24.3 ($ROMP_GITLEAKS) is older than 8.25.0"* ]]
    at_base
}

@test "round 10b (F): a clean push of a selected file whose quoted basename passes 255 bytes, 35 two-byte characters and .yaml (70 bytes past ASCII, 285 bytes as git quotes them), passes: its copy is named by its piece's number and .yaml, so both runs read it and the byte figures agree (red at eee3938a8: the copy took the quoted basename, and the redirect failed with File name too long, status 1, no romp line)" {
    r9d_base
    r10b_long_name .yaml
    printf 'name: probe\n' > "$REPO/$name"
    git -C "$REPO" add -- "$name"
    git -C "$REPO" commit -qm "a long name past ASCII"
    push_main_through_hook_with_shim
    r10a_passes
    [ "$(grep -o 'INF scanned ~[0-9]* bytes' <<< "$output")" = "$(printf 'INF scanned ~14 bytes\nINF scanned ~14 bytes')" ]
    [[ "$output" != *"File name too long"* ]]
}

@test "round 10b (F): a clean push of an all-ASCII selected name of 253 bytes holding three double quotes (256 as git quotes it, each quote costing two) passes, both byte figures agreeing (red at eee3938a8: File name too long, status 1, no romp line)" {
    r9d_base
    name="$(printf '"a"b"%s.yaml' "$(head -c 243 /dev/zero | tr '\0' c)")"
    [ "${#name}" -eq 253 ]
    printf 'name: probe\n' > "$REPO/$name"
    git -C "$REPO" add -- "$name"
    git -C "$REPO" commit -qm "a long name with quotes"
    push_main_through_hook_with_shim
    r10a_passes
    [ "$(grep -o 'INF scanned ~[0-9]* bytes' <<< "$output")" = "$(printf 'INF scanned ~14 bytes\nINF scanned ~14 bytes')" ]
    [[ "$output" != *"File name too long"* ]]
}

@test "round 10b (F, the coordinator's decision 4): pkcs12-file under a fixed stem: a keystore under a long name ending .p12 is refused naming the rule and the real path as git quotes it (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness pkcs12-file .p12
}

@test "round 10b (F, the coordinator's decision 4): pkcs12-file under a fixed stem: a keystore under a long name ending .pfx is refused naming the rule and the real path (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness pkcs12-file .pfx
}

@test "round 10b (F, the coordinator's decision 4): nuget-config-password under its fixed name: a password in a file under a long name ending nuget.config, copied as nuget.config in its piece's directory, is refused naming the rule and the real path (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness nuget-config-password nuget.config
}

@test "round 10b (F, the coordinator's decision 4): kubernetes-secret-yaml under a fixed stem: a Secret under a long name ending .yaml is refused naming the rule and the real path (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness kubernetes-secret-yaml .yaml
}

@test "round 10b (F, the coordinator's decision 4): kubernetes-secret-yaml under a fixed stem: a Secret under a long name ending .yml is refused naming the rule and the real path (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness kubernetes-secret-yaml .yml
}

@test "round 10b (F, the coordinator's decision 4): hashicorp-tf-password under a fixed stem: a password under a long name ending .tf is refused naming the rule and the real path (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness hashicorp-tf-password .tf
}

@test "round 10b (F, the coordinator's decision 4): hashicorp-tf-password under a fixed stem: a password under a long name ending .hcl is refused naming the rule and the real path (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness hashicorp-tf-password .hcl
}

@test "round 10b (F, the coordinator's decision 4): freemius-secret-key under a fixed stem: a secret key under a long name ending .php is refused naming the rule and the real path (red at eee3938a8: File name too long, no rule named)" {
    r10b_long_witness freemius-secret-key .php
}

@test "round 10b (G): the path-scoped copies' directories are made past the argument limit: 4,000 one-line .yaml files in one commit, pushed for real with the stack limit lowered to 512 KB in the case's own subshell (an exec's arguments then capped at 128 KB), pass, both byte figures agreeing (red at eee3938a8: one mkdir took every directory, exited 126 on Argument list too long, and set -e ended the hook with no romp line)" {
    r9d_base
    mkdir -p "$REPO/k8s"
    for ((i = 1; i <= 4000; i++)); do printf 'name: probe\n' > "$REPO/k8s/f$i.yaml"; done
    git -C "$REPO" add k8s
    git -C "$REPO" commit -qm "4,000 yaml files"
    mkdir -p "$TEST_DIR/hooks"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'export PATH=%q:"$PATH"\n' "$TEST_DIR/shim"
        printf 'exec %q "$@"\n' "$HOOK"
    } > "$TEST_DIR/hooks/pre-push"
    chmod 755 "$TEST_DIR/hooks/pre-push"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/hooks"
    run bash -c 'ulimit -s 512 && exec git -C "$1" push origin main' _ "$REPO"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    [[ "$output" != *"Argument list too long"* ]]
    [ "$(grep -o 'INF scanned ~[0-9]* bytes' <<< "$output")" = "$(printf 'INF scanned ~56000 bytes\nINF scanned ~56000 bytes')" ]   # 4,000 pieces of 14 bytes, then their copies
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse refs/heads/main)" = "$(git -C "$REPO" rev-parse HEAD)" ]
}

@test "round 10b (H, tests-3): the feed's count arm guards its list file: two commits pushed (a credential, then a clean tip) while both of the list file's readers see only the tip (a git whose parent counts' rev-list first cuts the feed's list file to the tip's two lines) is refused naming the awk's count of commits read whole against the count fed, and the remote stays at its base (red by publication under the mutant that neutralizes the arm: the scanner reads the tip's piece alone, clean)" {
    r9d_base
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    commit_file ok.txt "nothing to see" "a clean tip"
    tip="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/tmp"
    export TMPDIR="$TEST_DIR/tmp"
    git_shim "$(printf 'if [[ " $* " == *" --no-walk=unsorted "* ]]; then\n    for l in %q/romp-pre-push.*/creds.list; do [ -e "$l" ] || continue; printf "%%s\\n%%s %%s\\n" %q %q %q > "$l"; printf "%%s\\n" "$l" >> %q; done\nfi' "$TEST_DIR/tmp" "$tip" "$tip" "$tip" "$TEST_DIR/calls.shortlist")"
    push_main_through_hook_with_shim
    [ "$(wc -l < "$TEST_DIR/calls.shortlist")" -eq 1 ]
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL FEED of the push was read short (its awk recorded 1 commits read whole of the 2 it was given); the scan is incomplete, so the push is refused"* ]]
    at_base
}

@test "round 10b (H, tests-4, flag 118): a repository config dropping a path-scoped rule (disabledRules holding pkcs12-file) makes the additive run fail on a pushed cert.p12, refused as a scan that could not complete, gitleaks' FTL line naming the missing rule (the path-scoped run's own failure: the exit arm is shared with the main run), the remote at its base (red under the other option, the run returning clean on not found in rules: the keystore published)" {
    r9d_base
    printf '[extend]\nuseDefault = true\ndisabledRules = ["pkcs12-file"]\n' > "$REPO/.gitleaks.toml"
    git -C "$REPO" add .gitleaks.toml
    git -C "$REPO" commit -qm "a config dropping a path-scoped rule"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    r9d_witness pkcs12-file
    git -C "$REPO" add cert.p12
    git -C "$REPO" commit -qm "a keystore"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"FTL"*"pkcs12-file not found in rules"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
    at_base
}

@test "round 10b (H, tests-4, flag 122): a relative ROMP_GITLEAKS (.tools/gitleaks, from the work tree's root, where git runs the hook) is made absolute before the scanner runs from the piece directory: a credential is refused naming it, and a clean push passes, each through a real push (red under the mutant deleting that line, which refuses both: the relative name resolves nowhere from the piece directory)" {
    r9d_base
    mkdir -p "$REPO/.tools" "$REPO/.git/info"
    ln -s "$GL" "$REPO/.tools/gitleaks"
    printf '.tools/\n' >> "$REPO/.git/info/exclude"
    export ROMP_GITLEAKS=.tools/gitleaks
    commit_file k.py "k = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: k.py"* ]]
    at_base
    git -C "$REPO" reset -q --hard "$BASE"
    commit_file ok.txt "nothing to see" "a clean commit"
    push_main_through_hook_with_shim
    r10a_passes
}

@test "round 10b (A.2's disclosed cost, with its witness): a merge whose binary path's whole result blob holds a credential a remote already holds is refused: d.dat, under a committed -diff attribute and carrying a credential main already published, auto-merged by a merge whose own lines add nothing to it, is read whole from the merge's result blob, so the published credential is named with the merge, and the remote stays at its base (published at eee3938a8, which read no line of the path; the cost the header discloses)" {
    r9d_base
    printf 'd.dat -diff\n' > "$REPO/.gitattributes"
    { printf 'row %d\n' 1 2 3 4 5 6 7 8; printf 'token = "%s"\n' "$(probe_token)"; } > "$REPO/d.dat"
    git -C "$REPO" add .gitattributes d.dat
    git -C "$REPO" commit -qm "a -diff file carrying a credential, published"
    git -C "$REPO" push -q origin main
    BASE="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q -b side
    { printf 'row 1\nrow two, side\n'; printf 'row %d\n' 3 4 5 6 7 8; printf 'token = "%s"\n' "$(probe_token)"; } > "$REPO/d.dat"
    git -C "$REPO" commit -qam "one line on one side"
    git -C "$REPO" checkout -q main
    { printf 'row %d\n' 1 2 3 4 5 6; printf 'row seven, main\nrow 8\n'; printf 'token = "%s"\n' "$(probe_token)"; } > "$REPO/d.dat"
    git -C "$REPO" commit -qam "another line on the other"
    git -C "$REPO" merge -q --no-ff --no-edit side                        # an auto-merge: no line of the merge's own
    merge="$(git -C "$REPO" rev-parse HEAD)"
    is_merge "$merge"
    [ "$(git -C "$REPO" diff-tree -p -c --text "$merge" | grep -c '^Binary files differ$')" -eq 1 ]
    [ "$(git -C "$REPO" diff-tree -p -U0 --text "$merge^1" "$merge^2" | grep -c -F "$(probe_token)" || true)" -eq 0 ]   # the two sides differ by their own lines alone
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: commit ${merge:0:10} ADDS a credential (github-pat) in: d.dat"* ]]
    [ "$(grep -c 'ADDS a credential' <<< "$output")" -eq 1 ]             # the merge alone: its parents' own lines hold no credential
    [[ "$output" != *"the scan is incomplete"* ]]
    at_base
}
