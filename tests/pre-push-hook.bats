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
# back on with the REAL scanner (skipped where none is installed) for the read
# the hook makes INSIDE it: gitleaks' own log, because its exit status does not
# carry its git's failure. A scanner reporting a clean scan after its git wrote
# to stderr, or handed it fewer commits than the push has, is refused as
# unscanned too; the count the hook checks it against is read from the OBJECTS,
# never from the patch stream gitleaks reads, so a transform of that stream (an
# attribute, a config key) cannot empty the scan and the count alike. The
# transform cases at the end show each named transform closed; a count read
# from an equally hardened log stream would pass every one of them too, so ONE
# case holds the derivation itself: a git shim that strips --root from the
# scanner's log alone, under log.showRoot=false with a root credential, where a
# stream count agrees with the shortened scan and the object count does not. A
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
fail_diff_tree_stdin() { git_refusing '[ "${1:-}" = diff-tree ] && [ "${2:-}" = --stdin ]' 128 "fatal: shim: diff-tree --stdin refused"; }   # the credential count's read alone

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

# ── the credential scan's own read: gitleaks' log ────────────────────────
# The credential scan is one read the hook makes INSIDE another program: gitleaks
# runs `git log -p` itself, and its exit status does not carry that git's failure.
# Any stderr line from that git that gitleaks does not allowlist (it allowlists
# the rename-detection warnings and the auto-gc notice) makes it log the line at
# its ERR level, drop the rest of the scan, report the commits it did read, say
# no leaks were found and exit 0, whatever git's own status was. Found by
# execution (2026-09-21): a git that wrote ONE benign line to stderr, and a git
# that handed gitleaks one commit fewer, each let two live credentials through a
# real push with nothing printed by the hook, on a clone with the denylist armed.
# The hook now reads gitleaks' log: an ERR line refuses the push as unscanned,
# and so does a reported commit count other than the hook's own count of the
# commits with content to scan, derived the way gitleaks counts them (a commit
# with a hunk in a file that is not a deletion; an empty commit, a deletion, a
# mode-only change and an empty new file count for nothing) from the OBJECTS
# (rev-list, diff-tree --raw, cat-file), never from the patch stream gitleaks
# reads: a count read from that same stream shared every transform of it, so it
# agreed with an emptied scan under colour, a textconv driver, a -diff attribute,
# format.pretty, log.date and log.showSignature (six found in two rounds,
# 2026-09-21; the first three published a credential). Two conditions, because
# either alone has a hole: a log shortened before it wrote any ERR line is
# caught by the count read alone (a silent ERR-line awk over such a log is
# vacuous, its answer the real one's), and a scan that logged an ERR line yet
# reported a count the hook's own matches (its git wrote the line after a whole
# scan) is caught by the ERR-line read alone; the two witnesses below drive
# each read silent past the other (round 8b corrected this from "a discarded
# scan can still report the whole count", which read as the shortened scan's
# count, the count read's own case).
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
# shape, first writes a line to stderr or appends one argument: the faults the
# scanner's own git can meet (a message from a filter or a wrapper; a log that
# returns fewer commits). The shape is gitleaks' invocation, `git -C <root> log`,
# which no read of the hook's own has, so the hook's git is untouched. Once per
# test, like git_refusing.
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
GITLEAKS_GIT='[ "${1:-}" = -C ] && [ "${3:-}" = log ]'
gitleaks_git_noisy()   { git_passing_through "$GITLEAKS_GIT" "note: a benign line on stderr"; }
gitleaks_git_short()   { git_passing_through "$GITLEAKS_GIT" "" --max-count=1; }
gitleaks_git_warning() { git_passing_through "$GITLEAKS_GIT" "warning: inexact rename detection was skipped due to too many files."; }

# The scanner as the hook invokes it, over everything the tip reaches (the
# fixture has no remote). The argument list is read out of the hook file itself
# (gitleaks_args), so the two invocations match by construction: over the
# fixture repo, where the hook's --config expands to nothing (no .gitleaks.toml
# there), the command is the hook's word for word. A hook that renames the
# function fails here loudly rather than drifting apart from the helper.
scan_direct() {   # <sha>
    eval "$(awk '/^gitleaks_args\(\) /,/^}$/' "$HOOK")"
    [ "$(type -t gitleaks_args)" = function ]
    gitleaks_args "$REPO" "$1"
    run _hook_in "$REPO" -c 'exec "$@"' _ "$GL" "${GL_ARGS[@]}"
}

@test "two planted credentials in two commits are both named and refused by the real scanner: the control for the cases below" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"slack-bot-token"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"$(probe_token)"* ]]           # --redact
    [[ "$output" != *"the scan is incomplete"* ]]   # a finding, not a failed scan
}

@test "a clean commit passes the real scanner, its reported count the hook's own: the count read refuses nothing extra" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 commits scanned"* ]]        # gitleaks' own log line, shown as before
    [[ "$output" != *"romp pre-push"* ]]
}

@test "commits with no content to scan (an empty commit, a deletion, a mode-only change, an empty new file) count for nothing, and a binary add and a pure rename count as their bytes say: no false refusal" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" commit -q --allow-empty -m "an empty commit"
    remove_file base.txt "a deletion"
    printf 'ab\0cd\0\1\2\n' > "$REPO/blob.bin"
    git -C "$REPO" add blob.bin
    git -C "$REPO" commit -qm "a binary add"                     # --text: diffed as text, scanned and counted
    git -C "$REPO" update-index --chmod=+x blob.bin
    git -C "$REPO" commit -qm "a mode-only change"               # the blob's sha unchanged: no hunk
    : > "$REPO/empty.txt"
    git -C "$REPO" add empty.txt
    git -C "$REPO" commit -qm "an empty new file"                # an empty blob: no hunk
    git -C "$REPO" mv blob.bin moved.bin
    git -C "$REPO" commit -qm "a pure rename"                    # --no-renames: a deletion and an addition, the addition counted
    [ "$(git -C "$REPO" rev-list --count HEAD)" -eq 7 ]          # seven commits, three of them with content gitleaks reads
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"3 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# Two more arms of the count (round 3's tests-3): a blob the count's size read
# cannot find, which fails the count (exit 3) rather than counting as empty,
# and an added gitlink, which counts by its sha and is no blob the size read
# asks about. The first runs the REAL scanner on purpose: under
# ROMP_NO_GITLEAKS=1 the count never runs, and with the real scanner a hook
# that miscounted the missing blob would still be refused on gitleaks' own ERR
# line, so only the exact clause tells the arms apart.

@test "a commit whose added file's BLOB is missing from the store fails the count with the REAL scanner, the exact clause naming the read: a blob that cannot be found is never counted as empty" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    blob="$(git -C "$REPO" rev-parse HEAD:probe.py)"
    remove_file probe.py "redact"
    rm "$REPO/.git/objects/${blob:0:2}/${blob:2}"       # loose in a fresh repo
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" -c 'echo "$1" | git cat-file --batch-check' _ "$blob"   # the size read as the count makes it
    [[ "$output" == *"missing"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the COMMITS of refs/heads/main (${sha:0:10}) could not be counted for the credential scan (a git read exited 3)"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
}

@test "an ADDED gitlink (a submodule entry, its commit not in this store) passes the real scanner cleanly, counted by both: a gitlink counts by its sha and is no blob the size read asks about" {
    real_gitleaks
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" update-index --add --cacheinfo "160000,0123456789abcdef0123456789abcdef01234567,sub"   # a superproject holds no object for the submodule's commit
    git -C "$REPO" commit -qm "an added gitlink"
    run _hook_in "$REPO" -c 'git ls-tree HEAD sub'
    [[ "$output" == "160000 commit 0123456789abcdef0123456789abcdef01234567"* ]]
    run _hook_in "$REPO" -c 'echo 0123456789abcdef0123456789abcdef01234567 | git cat-file --batch-check'   # the size read, asked about it, would say missing
    [[ "$output" == *"missing"* ]]
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a scan gitleaks reports as clean after its own git wrote to stderr is refused as unscanned: exit 0 is not a completed scan" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_noisy
    scan_direct "$sha"                                  # the scanner as the hook meets it: an ERR line, no finding, exit 0
    [ "$status" -eq 0 ]
    [[ "$output" == *"ERR"* ]]
    [[ "$output" == *"no leaks found"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CREDENTIAL scan of refs/heads/main (${sha:0:10}) did not complete: gitleaks logged an error"* ]]
    [[ "$output" == *"a benign line on stderr"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]      # the scanner advice, not the rotate advice
    [[ "$output" == *"git push --no-verify"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
}

@test "a scan whose reported count falls short of the commits with content to scan is refused as unscanned, with both numbers: a shorter log is not a clean one" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"   # the secret is in the OLDER commit: a log of one commit reads the clean tip alone
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_short
    scan_direct "$sha"                                  # the scanner as the hook meets it: one commit, no ERR line, exit 0
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 commits scanned"* ]]
    [[ "$output" != *"ERR"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"did not complete: gitleaks logged"* ]]   # the count condition alone caught this
    [[ "$output" != *"gitleaks found a credential"* ]]
}

@test "the rename-detection warning gitleaks allowlists passes: a WRN line is not an ERR line, and the count is whole" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    gitleaks_git_warning
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"inexact rename detection was skipped"* ]]
    [[ "$output" == *"1 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# The scanner's git is asked for no colour. With color.ui or color.diff set to
# always, git colours `log -p` written to a pipe; gitleaks finds no file header
# in the coloured stream and reports `0 commits scanned` with no ERR line, and a
# count once read from the same coloured stream agreed with it, so a push
# carrying a credential passed both conditions (found by execution, 2026-09-21,
# the review round's derivation). The scanner's git is given --no-color through
# --log-opts; the hook's own count reads the objects (rev-list, diff-tree --raw,
# cat-file), which carry no colour whatever color.ui or color.diff says.

@test "a credential is found under color.ui=always: the scanner's git is asked for no colour, and the hook's count reads the objects, which colour cannot reach" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config color.ui always
    run _hook_in "$REPO" -c 'git log -p -U0 --format="commit %H" HEAD'    # the stream as git colours it for a pipe
    [ "$status" -eq 0 ]
    [[ "$output" == *$'\e['* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under color.diff=always passes: neither read is coloured, so the counts agree for the right reason" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    git -C "$REPO" config color.diff always
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# The other two refusal arms of the credential scan's read (round 2's tests-1):
# a scanner that reports no count at all, and the hook's own count read
# failing. Each is a refusal a passing suite cannot tell from an arm that is
# not there, so each runs against its refusing input.

@test "a scanner that exits 0 and reports NO commit count is refused as unscanned: no count is no evidence of a scan" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    unset ROMP_NO_GITLEAKS
    export ROMP_GITLEAKS="$TEST_DIR/gitleaks-stub"      # a scanner that runs, says nothing of what it read, and exits clean
    printf '#!/usr/bin/env bash\necho "stub scanner ran, reporting no count" >&2\nexit 0\n' > "$ROMP_GITLEAKS"
    chmod 755 "$ROMP_GITLEAKS"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CREDENTIAL scan of refs/heads/main (${sha:0:10}) reported no commit count, so what it read is unknown"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"covered"* ]]                      # the absent-count arm, not the mismatch arm
    [[ "$output" != *"gitleaks found a credential"* ]]
}

@test "a hook whose OWN count read fails is refused as unscanned, naming that read: the scanner's word alone is not evidence" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_diff_tree_stdin                                # the shim keys on the count read's own shape (diff-tree --stdin), not on the derivation: gitleaks' git and the identifier scan's diff-tree run unchanged
    run _hook_in "$REPO" -c 'echo "$1" | git diff-tree --stdin -r --raw --no-renames --root' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1" >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the COMMITS of refs/heads/main (${sha:0:10}) could not be counted for the credential scan (a git read exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" == *"1 commits scanned"* ]]            # the scanner itself ran whole: the refusal is the hook's own read
    [[ "$output" != *"covered"* ]]                      # no count of its own to compare against
}

# ── transforms of the stream ──────────────────────────────────────────────
# Both conditions above once read the same `git log -p` stream, and a transform
# of that stream emptied both alike: after the colour road, round 2 found a
# textconv driver and a -diff attribute in .gitattributes (each published a
# credential with the hook reporting clean), format.pretty, log.date and
# log.showSignature (each refused a clean push), and a replace ref (both scans
# read a substitute while the push transfers the original). The hook's count is
# now read from the objects, and the scanner's git is given an option outranking
# each key, so a credential under each is found and a clean push under each
# passes; log.showRoot set to false is neutralised the same way, by --root on
# the scanner's log, so a root commit's credential is found and a clean root
# passes, and a scanner whose git does not honour the option refuses on the
# count, the line stating the facts and naming the key as a candidate cause.
# What these cases hold is that each named transform is closed. They do not
# hold WHERE the count comes from: a count read from a log stream given the
# same options would pass every one of them too, since the option that
# neutralises a key for the scanner's git neutralises it for such a count
# alike. The one case that tells the derivations apart is in the log.showRoot
# section below (a git shim stripping --root from the scanner's log alone).
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

@test "a credential in a file under a hiding textconv driver is found: the scanner's git converts nothing" {
    real_gitleaks
    hiding_textconv
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    run _hook_in "$REPO" -c 'git log -p -U0 -1 HEAD -- probe.py | grep -c "^@@"'    # the driver as git applies it: no hunk to read
    [ "$output" = 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under that driver passes" {
    real_gitleaks
    hiding_textconv
    commit_file file.txt "nothing to see" "clean"
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a credential in a file marked -diff is found: the scanner's git diffs it as text" {
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
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push with a file marked -diff passes, the file counted: the count and the scan read the same bytes" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"     # likewise: with the denylist armed the same push is refused on the attribute alone
    printf 'notes.txt -diff\n' > "$REPO/.gitattributes"
    git -C "$REPO" add .gitattributes
    git -C "$REPO" commit -qm "attributes"
    commit_file notes.txt "nothing to see" "clean"
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a credential is found under format.pretty=oneline: the scanner's git is given the header gitleaks parses" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config format.pretty oneline
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"covered"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under format.pretty=oneline passes" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    git -C "$REPO" config format.pretty oneline
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

@test "a credential is found under log.date=relative: the scanner's git is given the date format gitleaks parses" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.date relative
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"covered"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
}

@test "a clean push under log.date=relative passes" {
    real_gitleaks
    commit_file file.txt "nothing to see" "clean"
    git -C "$REPO" config log.date relative
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 commits scanned"* ]]
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

@test "a credential in a signed commit is found under log.showSignature=true: the scanner's git prints no signature report" {
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
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"covered"* ]]
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
    [[ "$output" == *"2 commits scanned"* ]]
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
    [[ "$output" == *"github-pat"* ]]                    # replacement off for the scanner's git too: the original is what it read
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

# The count condition's own pin: log.showRoot set to false hides a root commit's
# diff from `git log -p`, so the scanner sees one commit fewer with no ERR line,
# and a count read from the same stream agreed with it (a credential in a root
# commit passed) where a count read from the objects does not. The hook passes
# --root in the scanner's log options (gitleaks_args), the option that outranks
# the key in every scope, so the scanner's git reads the root's diff and the
# count agrees; the option travels on the command line, so a scanner whose git
# does not inherit the hook's environment reads it too, and the hook exports no
# configuration pair for the key (the negative pin below). scan_direct runs the
# hook's own argument list, --root included; scan_direct_without_root runs the
# same list with the option removed, the road as git applies the key, so each
# case shows what the option closes. The refusal stays for the one case the
# option cannot reach, a scanner whose git does not honour it: refused on the
# count as before, the line stating the two facts (a short count beside the key
# false and a root commit in the range) and naming the key as a candidate cause
# with its remedy, asserting neither that the option went unhonoured nor that
# the key lifts the refusal.

# The hook's argument list with --root taken out of its log options and every
# other word kept: the scanner as git applies log.showRoot, for the road.
scan_direct_without_root() {   # <sha>
    local i
    eval "$(awk '/^gitleaks_args\(\) /,/^}$/' "$HOOK")"
    [ "$(type -t gitleaks_args)" = function ]
    gitleaks_args "$REPO" "$1"
    for i in "${!GL_ARGS[@]}"; do
        case ${GL_ARGS[$i]} in --log-opts=*)
            [[ "${GL_ARGS[$i]}" == *" --root"* ]]          # the hook's list carries the option: the pin that it is there
            GL_ARGS[$i]="${GL_ARGS[$i]// --root/}" ;;
        esac
    done
    run _hook_in "$REPO" -c 'exec "$@"' _ "$GL" "${GL_ARGS[@]}"
}

@test "log.showRoot=false is neutralised by --root on the scanner's log: the root commit's credential is FOUND and the push refused as a finding, no coverage line" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    sha="$(git -C "$REPO" rev-parse HEAD)"
    scan_direct_without_root "$sha"                     # the road: without the option, one of the two commits, no finding, no ERR line
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 commits scanned"* ]]
    [[ "$output" != *"ERR"* ]]
    scan_direct "$sha"                                  # the hook's own list, --root included: both commits and the finding
    [ "$status" -eq 2 ]
    [[ "$output" == *"2 commits scanned"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"2 commits scanned"* ]]            # the option reached the scanner's git: the root's diff is in its log
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" != *"covered 1 of the 2"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" != *"log.showRoot"* ]]
    [[ "$output" != *"gitleaks could not scan"* ]]
}

@test "a clean push with a root commit under log.showRoot=false passes, the scanner's count the hook's own: --root reached the scanner's git" {
    real_gitleaks
    commit_file base.txt "notes-api" "a clean root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    sha="$(git -C "$REPO" rev-parse HEAD)"
    scan_direct_without_root "$sha"                     # the road: without the option the root's diff is hidden, one of the two
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 commits scanned"* ]]
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# A git that runs the real git unchanged and, for gitleaks' invocation shape,
# first writes the command-scope configuration it sees (the environment's pairs,
# in index order) to a file: what the scanner's git was given, read back, so the
# case below can assert the hook added nothing to it.
gitleaks_git_recording_pairs() {   # <file>
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then\n' "$GITLEAKS_GIT"
        printf '    %q -C "$2" config --show-scope --list | grep "^command" > %q\n' "$real_git" "$1"
        printf 'fi\n'
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "the hook exports no GIT_CONFIG pair of its own: with the caller's GIT_CONFIG_COUNT=1 (gc.auto) set, the scanner's git sees exactly that pair in its command scope, and a clean root-commit push under log.showRoot=false still passes, by --root" {
    real_gitleaks
    # the caller's environment: one pair of its own in place of the floor's five (the floor's global config file still carries those keys)
    export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=gc.auto GIT_CONFIG_VALUE_0=0
    unset GIT_CONFIG_KEY_1 GIT_CONFIG_VALUE_1 GIT_CONFIG_KEY_2 GIT_CONFIG_VALUE_2 GIT_CONFIG_KEY_3 GIT_CONFIG_VALUE_3 GIT_CONFIG_KEY_4 GIT_CONFIG_VALUE_4
    commit_file base.txt "notes-api" "a clean root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    gitleaks_git_recording_pairs "$TEST_DIR/scanner-git-pairs"
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
    # the caller's pair alone, nothing appended: the key is neutralised on the command line, not in the environment (a negative pin)
    run cat "$TEST_DIR/scanner-git-pairs"
    [ "$output" = "$(printf 'command\tgc.auto=0')" ]
}

# A scanner whose git does not inherit the hook's environment: a wrapper that
# unsets every GIT_CONFIG_COUNT, GIT_CONFIG_KEY_n and GIT_CONFIG_VALUE_n variable
# present (each name computed at run time from GIT_CONFIG_COUNT) and then runs
# the real gitleaks, whose git then reads the clone's files alone. An option on
# the command line reaches it all the same: the shape an environment override
# could not reach, kept to show the option does.
gitleaks_without_config_pairs() {
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'names=(); n=${GIT_CONFIG_COUNT:-0}; i=0\n'
        printf 'while [ "$i" -lt "$n" ]; do names+=(-u "GIT_CONFIG_KEY_$i" -u "GIT_CONFIG_VALUE_$i"); i=$((i + 1)); done\n'
        printf '[ -z "${GIT_CONFIG_COUNT+x}" ] || names+=(-u GIT_CONFIG_COUNT)\n'
        printf 'exec env "${names[@]}" %q "$@"\n' "$GL"
    } > "$TEST_DIR/shim/gitleaks"
    chmod 755 "$TEST_DIR/shim/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/shim/gitleaks"
}

@test "a scanner whose git does not inherit the hook's environment (a wrapper stripping every GIT_CONFIG pair) still scans a root commit under log.showRoot=false: --root travels on the command line, so the count agrees and a clean root push passes" {
    real_gitleaks
    commit_file base.txt "notes-api" "a clean root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    gitleaks_without_config_pairs
    run_hook
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 commits scanned"* ]]
    [[ "$output" != *"romp pre-push"* ]]
}

# A scanner whose git does not honour the option: a wrapper that removes the
# word --root from the --log-opts value, keeps every other word and runs the
# real gitleaks, whose git then applies log.showRoot as the clone's files set
# it. The one way the refusal arm can fire for this key now. The wrapper writes
# the argument list it ran to a file, so the case can show what it kept.
gitleaks_without_root_option() {   # <file>: the rewritten argument list, one word per line
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'args=()\n'
        printf 'for a in "$@"; do\n'
        printf '    case $a in --log-opts=*) a=" ${a#--log-opts=} "; a=${a// --root / }; a=${a# }; a="--log-opts=${a%% }" ;; esac\n'
        printf '    args+=("$a")\n'
        printf 'done\n'
        printf 'printf "%%s\\n" "${args[@]}" > %q\n' "$1"
        printf 'exec %q "${args[@]}"\n' "$GL"
    } > "$TEST_DIR/shim/gitleaks"
    chmod 755 "$TEST_DIR/shim/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/shim/gitleaks"
}

@test "a scanner whose git does not honour --root (a wrapper removing the option from the scanner's log options) is refused on the count under log.showRoot=false with a root credential: the line states the short count and the key false with a root in range, names the key as a candidate cause, and gives the remedy; no finding" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_without_root_option "$TEST_DIR/scanner-args"
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"romp pre-push: the scanner covered fewer commits than the push has content for while log.showRoot is false in this clone's configuration and the range holds a root commit; if the scanner's git did not honour the --root option the hook passes on its log, that key is what hid the root commit's diff: set it to true (git config log.showRoot true) or unset it and push again, or ROMP_NO_GITLEAKS=1 skips the credential scan for this one push"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
    # the wrapper removed --root alone: the options after the range are the hook's own list less that one word
    eval "$(awk '/^gitleaks_args\(\) /,/^}$/' "$HOOK")"
    gitleaks_args "$REPO" "$sha"
    hook_opts=; for a in "${GL_ARGS[@]}"; do case $a in --log-opts=*) hook_opts=$a ;; esac; done
    hook_tail=${hook_opts#* --diff-merges=first-parent}
    [[ "$hook_tail" == *" --root"* ]]
    run grep -- '^--log-opts=' "$TEST_DIR/scanner-args"
    [[ "$output" != *"--root"* ]]
    [ "${output#* --diff-merges=first-parent}" = "${hook_tail// --root/}" ]
}

@test "the same count shortfall with log.showRoot unset names no key: the line is the key's, not the shortfall's" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file clean.txt "nothing to see" "a clean tip"             # the secret in the OLDER commit again
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_short                                               # one commit fewer, by the scanner's git rather than by the key
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" != *"log.showRoot"* ]]
}

# The arm's line is an inference from two facts (a short count; the key false
# with a root commit in the range), and a log shortened for any OTHER reason
# meets both. By execution (the round 3 refuter: a --max-count and a --skip on
# the scanner's log with --root honoured): the line printed all the same, and
# setting the key lifted nothing. So the line states the two facts and names
# the key as a CANDIDATE cause, conditionally, and promises nothing beyond the
# bypass.

@test "a count shortfall from a NON-key cause under log.showRoot=false with a root commit in range prints the two facts and the key as a candidate, conditionally: no assertion that the option went unhonoured, no promise that the key lifts the refusal" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_short                                               # one commit fewer by the scanner's git, --root untouched: the key is not the cause
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" == *"romp pre-push: the scanner covered fewer commits than the push has content for while log.showRoot is false in this clone's configuration and the range holds a root commit; if the scanner's git did not honour the --root option"* ]]
    [[ "$output" != *"and the scanner's git did not honour"* ]]     # the retired assertion of a cause
    [[ "$output" != *"set the key to true"* ]]                      # the retired promise's wording
    [[ "$output" == *"ROMP_NO_GITLEAKS=1 skips the credential scan for this one push"* ]]
}

# The count's DERIVATION, held apart from its hardening (round 3's tests-1): a
# count read from a `git log -p` stream given the same plain-stream options as
# the scanner's passes every transform case above, since each option
# neutralises its key for both logs alike. What tells the derivations apart is
# a transform that reaches the scanner's log and not the hook's object reads: a
# git shim that strips --root from every invocation carrying the word `log`
# (gitleaks' `git -C <root> log ...`; the hook's own `git log -1` reads carry
# no --root) and leaves diff-tree alone. Under log.showRoot=false with a
# credential in the root commit, the scanner reads one commit fewer; a
# stream-derived count reads the same and agrees (exit 0, the credential
# published: confirmed by execution on a scratch hook with that derivation,
# round 3), the object-derived count says two and refuses.
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

@test "the count is derived from the OBJECTS: a git shim stripping --root from every log invocation (the scanner's; diff-tree untouched) under log.showRoot=false with a root credential is refused on the count with the key line, where a count read from the log stream would agree with the shortened scan and pass" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_stripping_root_from_log
    # the transform as the two reads meet it: the log loses the root's hunk (one of two), diff-tree keeps the root's entry
    run _hook_in "$REPO" -c 'git log -p -U0 --format="commit %H" --root "$1" | grep -c "^@@"' _ "$sha"
    [ "$output" = 1 ]
    run _hook_in "$REPO" -c 'echo "$1" | git diff-tree --stdin -r --raw --no-renames --root | grep -c "^:"' _ "$(git -C "$REPO" rev-parse "$sha^")"
    [ "$output" = 1 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" == *"log.showRoot is false in this clone's configuration and the range holds a root commit"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
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
# a tr per file, and a tr piped to wc for the newline test). Before round 3g
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
# shape (the rewrite; the newline test; since round 6b the joins' own tr,
# newline to NUL, for the join's fourth arm at the end of this file) and execs
# the real tr for every other, counting in a file since each invocation is its
# own process; the cases here refuse the rewrite and the test, and the joins'
# tr runs through. Once per test, like
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

@test "a newline test that fails (the first test tr exiting 1 under the pipe to wc) is a failed test and not a count of zero: the push is refused as unscanned, naming the tip and the test" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    tr_refusing test 1
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"shim: tr refused (test 1)"* ]]
    [[ "$output" == *"the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the newline test's tr or wc exited 1)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
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
# 2026-09-22).
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

@test "a wc that answers NOTHING (exit 0, no count) is not a newline count of zero: the push is refused as unscanned, naming the tip, the test and the empty answer, where a clean commit would otherwise pass on a test that read nothing" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    wc_silent
    run _hook_in "$REPO" -c 'printf "abc" | wc -c'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the newline test's wc answered \"\" for listing, not a count)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"holds a newline"* ]]
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
    # the read as chosen_emails makes it fails under the shim; the hook's other config read (log.showRoot, at its top) is untouched
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


# The arm's own read failing. The hook reads the clone's value of log.showRoot
# once, at its top (showroot_configured: git config --type=bool log.showRoot,
# a failure swallowed into an empty value), and the arm in scan_credentials
# reads that variable beside the short count. A shim that fails that one read
# leaves the arm silent, and the refusal is then the generic coverage line's
# alone: the count is derived from the objects, so no failure of the key's
# read can turn the refusal into a pass; what the failure costs is the key
# line, and the case records the refusal as it then reads (recorded, not
# chosen: the header's own rule is that a refusal a contributor cannot act on
# is a defect). The positive half, --root making the root scanned with the
# read intact and no wrapper, is the first two cases of this section (the
# root's credential FOUND; a clean root passes), not repeated here.
fail_config_showroot() { git_refusing '[ "${1:-}" = config ] && [ "${2:-}" = --type=bool ] && [ "${3:-}" = log.showRoot ]' 128 "fatal: shim: config --type=bool log.showRoot refused"; }   # the hook's one read of the key

@test "a failed read of log.showRoot (the hook's own config read exiting 128) beside a scanner that does not honour --root is still refused on the count: the coverage line stands on its own, the key line is absent since the read that names the key failed, and the push never passes" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    git -C "$REPO" config log.showRoot false
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_without_root_option "$TEST_DIR/scanner-args"
    run_hook                                            # the read intact: the arm fires beside the coverage line (the wrapper case above pins the whole line)
    [ "$status" -eq 1 ]
    [[ "$output" == *"covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" == *"romp pre-push: the scanner covered fewer commits than the push has content for while log.showRoot is false in this clone's configuration"* ]]
    fail_config_showroot
    run _hook_in "$REPO" -c 'git config --type=bool log.showRoot'    # the read as the hook makes it fails under the shim
    [ "$status" -eq 128 ]
    [[ "$output" == *"shim: config --type=bool log.showRoot refused"* ]]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    [[ "$output" != *"log.showRoot"* ]]                 # the arm read an empty value: no key line
    [[ "$output" != *"gitleaks found a credential"* ]]
    [[ "$output" != *"shim:"* ]]
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

# The credential half's own count (scannable_commits) answering NOTHING with a
# clean status: an empty count skipped the comparison with the scanner's
# reported count, so a scanner handed a shorter log passed. The count is now
# judged as a run of digits before the comparison.
awk_silent_on_count() {   # an awk that exits 0 printing nothing for the program that derives the count (the one naming a missing blob), the real awk for every other program
    local real_awk
    real_awk="$(command -v awk)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'case "$*" in *"is missing"*) cat > /dev/null; exit 0 ;; esac\n'
        printf 'exec %q "$@"\n' "$real_awk"
    } > "$TEST_DIR/shim/awk"
    chmod 755 "$TEST_DIR/shim/awk"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "the hook's own commit count answering NOTHING (the count's awk exiting 0 with no output) beside a scanner handed a shorter log is refused as unscanned naming the count read and the empty answer: an empty count is not a count that agrees" {
    real_gitleaks
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in a middle commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_short                                   # the scanner's git handed --max-count=1: one commit scanned, the clean tip
    awk_silent_on_count
    run _hook_in "$REPO" -c 'printf "x\n" | awk "{ print \"is missing\" }"; echo "status $?"'
    [ "$output" = "status 0" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the COMMITS of refs/heads/main (${sha:0:10}) could not be counted for the credential scan (the count read exited 0 and answered \"\", not a count)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"gitleaks could not scan"* ]]
    [[ "$output" != *"gitleaks found a credential"* ]]
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
        printf 'set -uo pipefail\nfailed_scan=0; read_rc=0; read_out=""\n'
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
# ^ the census's BOUND: a command line is a read only when its command word is one of these (the tools the hook reads
# with today, git, grep, awk, sed, tr, wc, od, cat, sort and head, and the reading tools it might start running); a read
# made with a tool outside the list is not counted, and this line is where the list is widened. Outside on purpose:
# mktemp (make_scratch, a writer whose failure its callers refuse) and the scanner binary (run through a variable, its
# exit judged under a marker); command -v resolves the scanner's path and runs nothing.
# What the census reads (round 8b, the round 7 rulings' B): the command word by its basename with a leading backslash
# dropped (/usr/bin/git and \git run git), past the keywords, the command prefixes and their option words (a word
# starting with -, and the operand of nice -n and env -u: env -i git, nice -n 19 git and command -p git run git), the
# assignments and the redirections; command -v and -V are lookups that run nothing, never reads. Code inside a $( ) or a
# backtick substitution is read wherever bash runs it, inside double quotes too, and so is the text after a judged_read
# call's -- past its first simple command, the tagged read the tags judge (the same splitter over that text, its first
# segment alone dropped, so a second command past an operator and a substitution inside the tagged command's arguments
# are read). Two shapes stay UNREAD, and census_unread_shapes pins each ABSENT from the hook's comment-stripped raw text
# (the raw text, since the masked text hides what double quotes hold): a command word held in a variable whose value
# names a reading tool (a default such as ${GIT:-git}, or a bare tool name assigned to a variable), and a read inside an
# eval'd string (no eval at all). The hook's own variable command words are three, each outside this bound by design:
# the tagged command judged_read runs ("$@"), its -d rider ("$detail", which prints and reads nothing) and the scanner
# ("$gl", above).
CENSUS_PREFIX='^(if|then|else|elif|fi|while|until|do|done|case|esac|in|for|select|function|!|time|exec|env|nice|local|export|readonly|declare|typeset|command|builtin)$'
CENSUS_BUILTIN='^(read|printf|echo|eval|trap|wait|true|false|:|return|exit|break|continue|shift|set|unset|test|\[|\[\[)$'
masked_text() {   # <bash file>: the text with quoted bytes and comments masked quote-aware (the section comment), one output line per input line
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
            if (c == ")") { if (par[depth] > 0) par[depth]--; else if (depth > 0 && s == "code") depth--; out = out c; i++; prev = c; continue }
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
    awk -f "$TEST_DIR/mask.awk" "$1"
}
census_segments() {   # <masked text>: its simple commands, one per line, split at the operators, the substitutions' and subshells' parentheses, the backtick, and a brace that opens no ${
    printf '%s' "$1" | sed -E 's/\|\||&&|\||;|`|\$\(\(|\$\(|<\(|>\(|\(|\)/\n/g; s/(^|[^$])[{}]/\1\n/g'
}
census_command() {   # <simple command>: sets cmd, the caller's, to the reading tool it runs (one of CENSUS_TOOLS), or empty
    local t p o
    cmd=""
    # shellcheck disable=SC2086  # the segment is split into its words on purpose
    set -- $1
    while [ $# -gt 0 ]; do                                      # past the keywords, the command prefixes and their option words, the assignments and the redirections
        t=$1
        if [[ "$t" =~ $CENSUS_PREFIX ]]; then
            p=$t; shift
            if [ "$p" = command ] && [[ "${1:-}" =~ ^-[pvV]*[vV][pvV]*$ ]]; then return 0; fi   # command -v or -V: a lookup that runs nothing
            while [ $# -gt 0 ] && [[ "$1" == -* ]]; do          # a prefix's option words (env -i, command -p, nice -n 19): the operand of nice -n and env -u goes with its option
                o=$1; shift
                if { [ "$p" = nice ] && [ "$o" = -n ]; } || { [ "$p" = env ] && [ "$o" = -u ]; }; then [ $# -eq 0 ] || shift; fi
            done
            continue
        fi
        if [[ "$t" =~ ^[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])?\+?= ]] || [[ "$t" =~ ^[0-9]*[\<\>] ]] || [[ "$t" =~ ^\&\> ]]; then shift; continue; fi
        break
    done
    [ $# -gt 0 ] || return 0
    t=${1#\\}; t=${t##*/}                                       # the command word by its basename, a leading backslash dropped: /usr/bin/git and \git run git
    [[ "$t" =~ $CENSUS_BUILTIN ]] && return 0                   # a builtin's arguments are not commands
    [[ "$t" =~ ^($CENSUS_TOOLS)$ ]] && cmd=$t
    return 0
}
undeclared_reads() {   # <hook text>: prints "undeclared: <line>:<text>" per command line the census finds declared by nothing, "declared: <body|array|marker> <line> <function or ->: <tools>" per command line it finds declared outside a judged_read call, "swallowed: ..." per `|| true` or `|| :` inside a body passed whole, and one "census: ..." line of counts; run under `run`
    local -a orig masked
    local -A fstart fend passed inpassed
    local i j name m rest after w f s t sgm found text tail cmd calls=0 total=0 body=0 array=0 marker=0 undeclared=0 swallowed=0
    mapfile -t orig < "$1"
    mapfile -t masked < <(masked_text "$1")
    [ "${#orig[@]}" -eq "${#masked[@]}" ] || { echo "census: the masking changed the line count"; return 1; }
    for ((i = 0; i < ${#orig[@]}; i++)); do                    # function bodies: the header line to the first line that is exactly }
        if [[ "${orig[i]}" =~ ^([a-zA-Z_][a-zA-Z0-9_]*)\(\)\ \{ ]]; then
            name=${BASH_REMATCH[1]}; fstart[$name]=$i; fend[$name]=$i
            for ((j = i + 1; j < ${#orig[@]}; j++)); do if [ "${orig[j]}" = "}" ]; then fend[$name]=$j; break; fi; done
        fi
    done
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
    for ((i = 0; i < ${#orig[@]}; i++)); do
        m=${masked[i]}
        [[ "$m" =~ (^|[^A-Za-z0-9_.-])($CENSUS_TOOLS)([^A-Za-z0-9_.-]|$) ]] || continue     # a tool word somewhere in the masked line: the cheap pre-check
        text=$m; tail=""
        # A call: its tagged command, the first simple command after the --, is the read the tags judge. What runs
        # before the --, and every other simple command after it (a second command past an operator, a substitution
        # or a backtick inside the tagged command's own arguments), is censused: the SAME splitter over the text
        # after the --, its first segment alone dropped.
        if [[ "$m" =~ (^|[[:space:]!\&\|\;\(])judged_read[[:space:]] ]]; then
            text=${m%% -- *}
            if [[ "$m" == *" -- "* ]]; then tail=$(census_segments "${m#* -- }" | sed 1d); fi
        fi
        found=""
        while IFS= read -r sgm; do
            census_command "$sgm"
            [ -z "$cmd" ] || found="$found $cmd"
        done <<< "$(census_segments "$text")"$'\n'"$tail"
        [ -n "$found" ] || continue
        found=${found# }
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
census_unread_shapes() {   # <bash file>: prints "<line>:<text>" for each line of the comment-stripped RAW text holding a shape the census cannot read (the bound above): an eval, a parameter expansion defaulting to a reading tool, a reading tool's bare name assigned to a variable
    sed -E 's/[[:space:]]+#.*$//' "$1" | grep -nvE '^[[:space:]]*#' \
        | grep -E "(^|[^A-Za-z0-9_-])eval([^A-Za-z0-9_-]|\$)|\\\$\{[A-Za-z_][A-Za-z0-9_]*:?[-=+?]($CENSUS_TOOLS)([^A-Za-z0-9_.-]|\$)|(^|[^A-Za-z0-9_\$])[A-Za-z_][A-Za-z0-9_]*=[\"']?($CENSUS_TOOLS)[\"']?([[:space:];)&|]|\$)" || true
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
    [ "$(sed -E 's/.*array=([0-9]+).*/\1/' <<< "$census")" -ge 1 ]
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
    # the two shapes the census cannot read, pinned ABSENT from the hook's comment-stripped raw text: none in the hook,
    # and each spelling found in a planted copy, so the pin is shown to red
    run census_unread_shapes "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    for plant in 'x=$(${GIT:-git} rev-parse HEAD)' 'r=${ROMP_GIT-git}' 'GIT=git; "$GIT" rev-parse HEAD' "tool='grep'" 'eval "git rev-parse HEAD"' 'x=$(eval "$probe")'; do
        { sed -n '1p' "$HOOK"; printf '%s\n' "$plant"; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/plant-g.sh"
        run census_unread_shapes "$TEST_DIR/plant-g.sh"
        [ "$output" = "2:$plant" ]
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
# read (it ran before the ref list was read and inherited the hook's stdin,
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

@test "the log.showRoot configuration read under a git that DRAINS the hook's stdin for that one read (exit 0, nothing printed, the ref list read to its end) changes nothing now: the ref list is read by the shell before any tool runs, so a tip carrying a banned string is refused through a real push and the remote holds nothing (the round 7 text ran that read first, and every ref of the push published with nothing printed)" {
    add_remote
    commit_file leak.txt "home is /home/zzsynthuser/code" "leak"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_draining_stdin_on '[ "${1:-}" = config ] && [ "${2:-}" = --type=bool ] && [ "${3:-}" = log.showRoot ]'   # the hook's one read of the key; the chosen-addresses read carries --get-all
    run _hook_in "$REPO" -c 'printf "a line for whoever reads next\n" | { git config --type=bool log.showRoot; echo "status $?"; cat; }'
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
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/feature (${sha:0:10}) was listed as empty (git ls-tree -r exited 0 and printed no entry) while git cat-file -s gives its tree's size as $size bytes, so the listing answered short; the scan is incomplete, so the push is refused"* ]]
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

@test "the scanner log's ERR line (a gate= read since round 8b3) under an awk exiting 0 and printing nothing, beside a scanner git that writes a line to stderr (so gitleaks does log an ERR line and drops the rest of the scan), is refused through a real push naming the read's empty answer, neither none nor an error line, and the remote holds nothing (the round 7 rulings' D; a silent awk over a log with no ERR line would witness nothing; the count line judged apart is no backstop since round 8b3, which found it counting a commit whole whose credential file the scanner dropped)" {
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_noisy
    scan_direct "$sha"
    [[ "$output" == *"ERR"* ]]                                       # the fixture's premise: the log carries an ERR line for the awk to miss (colour codes wrap it, so no surrounding spaces)
    [[ "$output" == *"no leaks found"* ]]                            # and gitleaks reports the scan clean, so the ERR line and the count are the only two facts that catch it
    awk_silent_on_program '$2 == "ERR"'
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" != *"gitleaks logged an error"* ]]                  # the ERR line went unread: the read is silent
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) could not be judged: its log's error-line read answered \"\" (awk exited 0), neither the word none nor an error line"* ]]   # the gate refuses the empty answer itself
    [[ "$output" == *"gitleaks could not scan"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

# The road found while the rows above were written (round 8b): every tool a loop runs inherits the loop's
# stdin, and four loops that run tools read their list on stdin, so a tool that reads its stdin (the
# silent shape the shims here share) took the rest of the list. A two-ref push published its second ref
# (an awk so silent on any of the three own= joins, during the first ref), a hidden file went unjudged (a
# git so silent on an empty blob's read, the blob's own answer), a second ref's credential was never
# scanned (a git so silent on the range probe), and the symlink loop's drain was caught only by its own
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

@test "a two-ref push whose FIRST ref meets a range probe that exits 0, prints nothing and reads its stdin still credential-scans the SECOND ref: the real scanner names its credential through a real push and the remote never gets it (the round 8 text read the refs on stdin, the git took the rest of them, and the second ref's credential published with nothing printed; round 8b)" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-denylist"           # the credential scan alone: the identifier scan's range listing has the probe's shape
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    git -C "$REPO" checkout -q -b feature
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    git -C "$REPO" checkout -q main
    commit_file more.txt "nothing to see" "more"
    tool_silent_on git '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]'   # the range probe (rev-list <sha> --not --remotes ...), its answer discarded
    push_refs_through_hook_with_shim main feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"github-pat"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

stdin_loops_running_tools() {   # <bash file>: prints "<first line>-<last line>: <tools>" for each while-read loop that reads its list on stdin (a read with no -u) and runs a reading tool in its body; reads the census's helpers
    local -a masked toks
    local i j k depth seen tok sgm tools cmd
    mapfile -t masked < <(masked_text "$1")
    for ((i = 0; i < ${#masked[@]}; i++)); do
        [[ "${masked[i]}" =~ (^|[[:space:]\;])while[[:space:]] ]] || continue
        [[ "${masked[i]}" =~ (^|[[:space:]\;])read[[:space:]] ]] || continue
        [[ "${masked[i]}" =~ read[[:space:]]+(-[^[:space:]]+[[:space:]]+)*-u[[:space:]]*[0-9] ]] && continue    # read -u N: the list on a descriptor of its own
        depth=0; seen=0; j=$i
        for ((k = i; k < ${#masked[@]}; k++)); do                # the loop's done: its do and done words counted from the while line
            read -r -a toks <<< "${masked[k]//[;&|()]/ }"
            for tok in ${toks[@]+"${toks[@]}"}; do
                case "$tok" in do) depth=$((depth + 1)); seen=1 ;; done) depth=$((depth - 1)) ;; esac
            done
            if [ "$seen" -ne 0 ] && [ "$depth" -le 0 ]; then j=$k; break; fi
        done
        tools=""
        for ((k = i; k <= j; k++)); do
            while IFS= read -r sgm; do census_command "$sgm"; [ -z "$cmd" ] || tools="$tools $cmd"; done <<< "$(census_segments "${masked[k]}")"
        done
        [ -z "$tools" ] || echo "$((i + 1))-$((j + 1)):$tools"
    done
}

@test "no loop that runs a reading tool reads its list on stdin (round 8b): every while-read loop whose body runs one reads with -u from a descriptor of its own, so a tool that reads its stdin empties no list; the census flags a planted loop that reads a herestring on stdin around a git, and passes the same loop on a descriptor and a loop of builtins" {
    run stdin_loops_running_tools "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    # the loops that run tools read on a descriptor: five in the hook (the two ref loops, the symlink loop, the commit loop and the byte judge's)
    [ "$(grep -cE 'while (IFS= )?read -r -u [0-9]' "$HOOK")" -eq 5 ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r x; do' '    git cat-file -t "$x"' 'done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-a.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-a.sh"
    [ "$output" = "2-4: git" ]
    { sed -n '1p' "$HOOK"; printf '%s\n' 'while read -r -u 5 x; do' '    git cat-file -t "$x"' 'done 5<<< "$refs"' 'while read -r x; do echo "$x"; done <<< "$refs"'; sed -n '2,$p' "$HOOK"; } > "$TEST_DIR/loop-b.sh"
    run stdin_loops_running_tools "$TEST_DIR/loop-b.sh"
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
# end and an end of no known kind. Round 8b matched the outside reads by COUNT, and the swapped table stayed
# green (the r8b audit, 2026-09-23); each row's key makes the match a bijection, read by read.
READS_TSV="$ROMP_DIR/tests/pre-push-reads.tsv"
READS_HEADER_GEN="$ROMP_DIR/tests/pre-push-reads-header.sh"
READS_BEGIN='# BEGIN generated block (tests/pre-push-reads-header.sh; edit the table)'
READS_END='# END generated block'
hook_generated_block() {   # <hook file>: the lines between the two marker lines, each with its newline; nothing when either marker is missing
    awk -v b="$READS_BEGIN" -v e="$READS_END" '$0 == b { p = 1; next } p && $0 == e { done = 1; exit } p { buf = buf $0 "\n" } END { if (done) printf "%s", buf }' "$1"
}
hook_with_block_of() {   # <hook file> <tsv> <out>: the hook with its generated block replaced by the generator's output for that table
    bash "$READS_HEADER_GEN" "$2" > "$TEST_DIR/block-of.txt"
    awk -v b="$READS_BEGIN" -v e="$READS_END" -v f="$TEST_DIR/block-of.txt" '$0 == b { print; while ((getline l < f) > 0) print l; skip = 1; next } $0 == e { skip = 0 } !skip { print }' "$1" > "$3"
}
reads_table_check() {   # <hook> <tsv> <generator> <dir of the pre-push-*.bats files>: prints the first disagreement and returns 1; returns 0 when the table and the hook agree
    local hook=$1 tsv=$2 gen=$3 dir=$4 work line n kind read fact caseref key class file sub body text hits k
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
    # with fired_short that the shim fired with a cut answer) or gives the reason no cut applies (round 8b3)
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
        [[ "$fact" == *"Its end: "?* ]] || { echo "the row of $read states no end"; return 1; }
        case "$end" in
            tail|count|size|digits|whole|terminator|verdict|join|fewer|bytes|emptiness|backstop|prefix|status|discarded|report) ;;
            *) echo "the row of $read carries the end $end, no known kind"; return 1 ;;
        esac
        case "$short" in
            "none: "?*) ;;
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
    # the swapped outside table: the core.bigFileThreshold read's row dropped and a row for a read the hook does not make
    # added, the count unchanged (round 8b's count match stayed green on this table); the added row reuses the dropped
    # row's case, read from the table
    ref="$(awk -F'\t' '$5 == "git config core.bigFileThreshold" { print $4 }' "$READS_TSV")"
    [ -n "$ref" ]
    { grep -v -F "$(printf '\tgit config core.bigFileThreshold\t')" "$READS_TSV"; printf 'outside\tthe PLANTED configuration read\tfor the report alone: planted. Its end: planted\t%s\tgit config core.zzsynthNoSuchKey\treport\tnone: planted\treport\n' "$ref"; } > "$P/tsv-swapped"
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
r8b2_credential_in_root_scanner_without_root() {   # the credential scan's count arm fed short: a root commit carrying a credential, a clean tip, log.showRoot false, and a scanner whose --root is stripped from its log options (it then reads the tip alone)
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in the root commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" config log.showRoot false
    gitleaks_without_root_option "$TEST_DIR/scanner-args"
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
    [[ "$output" == *"romp pre-push: the TREE of the tip of refs/heads/feature (${sha:0:10}) was listed as empty (git ls-tree -r exited 0 and printed no entry) while git cat-file -s gives its tree's size as "*" bytes, so the listing answered short"* ]]
    run remote_holds_ref refs/heads/feature
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the SIZE of the tip's tree: a git silent on the tree's size read alone, over a tip at the EMPTY tree (the one tree whose listing is empty, so the size is asked), is refused naming the size read's non-count answer through a real push, and the remote never gets the branch" {
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

@test "round 8b2 table case: the NEWLINE COUNT of a scratch listing: a wc silent on wc -c fed by a pipe alone (the newline test's pipeline; the byte counts read a file), through a real push of a clean tip, is refused naming the non-count, and the remote stays at its base" {
    clean_tip_after_base
    calls_silent_on wc newline-count '[ "${1:-}" = -c ] && [ "$#" -eq 1 ] && [ -p /dev/stdin ]'
    push_main_through_hook_with_shim
    fired newline-count "wc -c"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the LISTINGS of the tip of refs/heads/main (${sha:0:10}) could not be rewritten for the BINARY VERDICT check (the newline test's wc answered \"\" for listing, not a count)"* ]]
    at_base
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

@test "round 8b2 table case: the BYTE COUNT of a scratch listing: a wc silent on wc -c reading a file alone (the byte counts; the newline test's wc reads a pipe), through a real push of a clean tip, is refused naming the non-count, and the remote stays at its base" {
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

@test "round 8b2 table case: the REPOSITORY ROOT: a git silent on rev-parse --show-toplevel alone, through a real push of a credential under the real scanner, is refused naming the empty root, and the remote never gets the branch" {
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    calls_silent_on git repo-root '[ "${1:-}" = rev-parse ] && [ "${2:-}" = --show-toplevel ]'
    push_main_through_hook_with_shim
    fired repo-root "rev-parse --show-toplevel"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the REPOSITORY ROOT could not be read for the credential scan (git rev-parse exited 0 and answered nothing)"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the COUNT of commits with content to scan: an awk silent on the count's last program alone, beside a scanner git handed --max-count=1 (so the scan reads the clean tip alone), through a real push of a middle-commit credential, is refused naming the non-count, and the remote never gets the branch" {
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential in a middle commit"
    commit_file clean.txt "nothing to see" "a clean tip"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_short
    calls_silent_on_text awk commit-count '== "missing"'
    push_main_through_hook_with_shim
    fired commit-count '"missing"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the COMMITS of refs/heads/main (${sha:0:10}) could not be counted for the credential scan (the count read exited 0 and answered \"\", not a count)"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the COLOUR STRIP of the scanner log: a sed silent on the colour strip alone, through a real push of a credential under the real scanner, leaves no count line to read, and the count arm refuses the push: the remote never gets the branch" {
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on sed colour-strip '[[ "${1:-}" == *"m//g" ]]'
    push_main_through_hook_with_shim
    fired colour-strip "m//g"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) reported no commit count, so what it read is unknown"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the COMMIT COUNT line of the scanner log: an awk silent on the count line's program alone, through a real push of a credential under the real scanner, is refused naming the missing count, and the remote never gets the branch" {
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on_text awk count-line '$4 == "commits"'
    push_main_through_hook_with_shim
    fired count-line '$4 == "commits"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) reported no commit count, so what it read is unknown"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
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

@test "round 8b2 table case: the ERR line of the scanner log: an awk silent on the ERR line's program alone, beside a scanner git that writes a line to stderr (so the log carries an ERR line), is refused naming the read's empty answer, neither none nor an error line, and the remote never gets the branch (round 8b3: the count this case left to judge until then can count a commit whole whose credential file the scanner dropped)" {
    real_gitleaks
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    commit_file slack.txt "slack = \"$(probe_slack)\"" "another credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    gitleaks_git_noisy
    calls_silent_on_text awk err-line '$2 == "ERR"'
    push_main_through_hook_with_shim
    fired err-line '$2 == "ERR"'
    [ "$status" -ne 0 ]
    [[ "$output" != *"gitleaks logged an error"* ]]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) could not be judged: its log's error-line read answered \"\" (awk exited 0), neither the word none nor an error line"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the RANGE probe of the credential scan: a git silent on the probe alone (the identifier scan off, so its listing of the same shape never runs) keeps the range, whose count and scan still run: through a real push of a credential the scanner names it, and the remote never gets the branch" {
    real_gitleaks
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/no-such-denylist"
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    calls_silent_on git range-probe '[ "${1:-}" = rev-list ] && [ "${3:-}" = --not ]'
    push_main_through_hook_with_shim
    fired range-probe "rev-list $sha --not --remotes"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: BLOCKED. gitleaks found a credential in a pushed commit."* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the log.showRoot configuration read: a git silent on config --type=bool log.showRoot alone reads as the key unset and costs the advice line alone: through a real push the short scan is refused by the count arm, the advice absent, and the remote never gets the branch" {
    r8b2_credential_in_root_scanner_without_root
    calls_silent_on git showroot '[ "${1:-}" = config ] && [ "${2:-}" = --type=bool ] && [ "${3:-}" = log.showRoot ]'
    push_main_through_hook_with_shim
    fired showroot "config --type=bool log.showRoot"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" != *"while log.showRoot is false"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
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

@test "round 8b2 table case: the root-commit probe, for the advice line: a git silent on rev-list --max-parents=0 alone costs the advice line alone: through a real push the short scan is refused by the count arm, the advice absent, and the remote never gets the branch" {
    r8b2_credential_in_root_scanner_without_root
    calls_silent_on git root-probe '[ "${1:-}" = rev-list ] && [ "${2:-}" = --max-parents=0 ]'
    push_main_through_hook_with_shim
    fired root-probe "rev-list --max-parents=0 $sha --not --remotes"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" != *"while log.showRoot is false"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b2 table case: the scanner's argument list (gitleaks_args): the scanner run on it silent (exit 0, nothing logged) leaves no count line, and the count arm refuses: through a real push of a credential the remote never gets the branch" {
    unset ROMP_NO_GITLEAKS
    add_remote
    commit_file probe.py "token = \"$(probe_token)\"" "a credential"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    mkdir -p "$TEST_DIR/scanner"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = git ]; then printf "%%s\\n" "gitleaks $*" >> %q; cat > /dev/null; exit 0; fi\n' "$TEST_DIR/calls.scanner"
        printf 'exit 1\n'
    } > "$TEST_DIR/scanner/gitleaks"
    chmod 755 "$TEST_DIR/scanner/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/scanner/gitleaks"
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim
    fired scanner "gitleaks git "
    fired scanner "--no-banner --redact -v --exit-code 2"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) reported no commit count, so what it read is unknown"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

# ── round 8b3 (A.8, the END of every answer): every row of tests/pre-push-reads.tsv driven with its answer CUT SHORT ──
# A fact that bounds an answer's START (a head marker, a non-empty answer, the first word naming the
# object, an emptiness compared with a size) says nothing of its END: the round 8b2 audit found four reads
# publishing through real pushes with their real answer cut short and exit 0 (the commit listing cut to
# its tip, the added lines cut to their marker, the addresses cut inside the committed address, a symlink
# target cut to ten bytes) while each row stated a fact, and this round's cases found four more of the kind
# (the symlink listing cut inside a link's mode, the -z listing inside a hidden file's record, the
# repository root to a main clone's path, the chosen addresses to a prefix that a commit is stamped with)
# and an own= read publishing beside a silent awk (the scanner log's ERR line), each closed, each closure's
# case red at 6e34a9d89 by publication. The cases below are one per row that has an
# answer to cut, in the table's order, each named in the row's short column (a row with none says why
# there): each puts a tool first on the hook's PATH that, for THAT read's argument shape alone (or its
# input), runs the REAL tool, cuts its answer short by the cut the case names (bytes:N keeps the first N
# bytes, less:N drops the last N, lines:N keeps the first N lines), prints the cut answer and exits 0 (a
# real non-zero exit passes through uncut), and records the call with the whole and the cut byte counts;
# the case pushes for real through core.hooksPath, asserts the shim FIRED with an answer cut short
# (fired_short: fewer bytes than the whole), then asserts what the row claims of the END: the refusal
# naming the read, or, for a safe-side row, the refusal or the remote that never receives new content.
# The table case holds the short column to these cases.
calls_short_on_shim() {   # <plain|text|input> <tool> <calls name> <cut> <shape: a bash test over "$@", or the fixed text> [<input text>]: the shim of the three helpers below
    local how=$1 tool=$2 name=$3 cut=$4 shape=$5 p real r_cat r_wc r_head r_mktemp r_rm keep
    p=${PATH//"$TEST_DIR/shim:"/}
    real="$(PATH=$p command -v "$tool")"; r_cat="$(PATH=$p command -v cat)"; r_wc="$(PATH=$p command -v wc)"
    r_head="$(PATH=$p command -v head)"; r_mktemp="$(PATH=$p command -v mktemp)"; r_rm="$(PATH=$p command -v rm)"
    case "$cut" in
        bytes:*) keep="k=${cut#bytes:}" ;;
        less:*)  keep="k=\$((n - ${cut#less:})); [ \"\$k\" -ge 0 ] || k=0" ;;
        lines:*) keep="k=\$($(printf %q "$r_head") -n ${cut#lines:} \"\$w\" | $(printf %q "$r_wc") -c); k=\${k//[[:space:]]/}" ;;
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

@test "round 8b3 short case: the REPOSITORY ROOT: a git whose rev-parse answers all but its last four bytes (exit 0), through a real push from a worktree whose path extends its main clone's, is refused naming the missing tail line (the answer cut on the old format named the main clone, whose .gitleaks.toml has no rule), and the remote never gets the branch" {
    real_gitleaks
    add_remote
    commit_file base.txt "notes-api" "base"
    git -C "$REPO" push -q origin main
    printf 'title = "no rules"\n' > "$REPO/.gitleaks.toml"                 # the main clone's own configuration, untracked: no rule at all
    git -C "$REPO" worktree add -q -b wt "$TEST_DIR/repo-wt" main
    printf 'token = "%s"\n' "$(probe_token)" > "$TEST_DIR/repo-wt/probe.py"
    git -C "$TEST_DIR/repo-wt" add probe.py
    git -C "$TEST_DIR/repo-wt" commit -qm "a credential"
    mkdir -p "$TEST_DIR/shim"
    push_from_worktree_through_hook_with_shim "$TEST_DIR/repo-wt" wt   # the control: with no cut the same push is refused
    [ "$status" -ne 0 ]
    calls_short_on git repo-root '[ "${1:-}" = rev-parse ] && [ "${2:-}" = --show-toplevel ]' less:4
    push_from_worktree_through_hook_with_shim "$TEST_DIR/repo-wt" wt
    fired_short repo-root "rev-parse --show-toplevel"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the REPOSITORY ROOT could not be read for the credential scan (git rev-parse exited 0 and answered \"t\" on its last line, not the line true that --is-inside-work-tree asks for after the root)"* ]]
    run remote_holds_ref refs/heads/wt
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the COUNT of commits with content to scan: an awk whose count program answers the first digit of twelve (exit 0), beside the real scanner, through a real push of twelve clean commits, is refused naming the scanner's count against the cut one, and the remote never gets the push" {
    real_gitleaks
    r8b3_twelve_commits
    calls_short_on_text awk commit-count '== "missing"' bytes:1
    push_main_through_hook_with_shim
    fired_short commit-count '"missing"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 12 of the 1 commits with content to scan"* ]]
    at_base
}

@test "round 8b3 short case: the COLOUR STRIP of the scanner log: a sed whose colour strip answers ten bytes of the log (exit 0), beside the real scanner, through a real push of a clean commit, leaves no count line to read, and the count arm refuses the push: the remote stays at its base" {
    real_gitleaks
    clean_tip_after_base
    calls_short_on sed colour-strip '[[ "${1:-}" == *"m//g" ]]' bytes:10
    push_main_through_hook_with_shim
    fired_short colour-strip "m//g"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) reported no commit count, so what it read is unknown"* ]]
    at_base
}

@test "round 8b3 short case: the ERR line of the scanner log: an awk whose ERR line program answers three bytes of its word (exit 0), beside a scanner git that writes a line to stderr, is refused naming the cut answer, neither none nor an error line, and the remote stays at its base" {
    real_gitleaks
    clean_tip_after_base
    gitleaks_git_noisy
    calls_short_on_text awk err-line '$2 == "ERR"' bytes:3
    push_main_through_hook_with_shim
    fired_short err-line '$2 == "ERR"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) could not be judged: its log's error-line read answered \"err\" (awk exited 0), neither the word none nor an error line"* ]]
    at_base
}

@test "round 8b3 closure: the ERR line of the scanner log beside a scanner that logs an error and still counts the push whole: an awk silent on the ERR line's program, over the log of a scanner that logs an ERR line, reports the one commit scanned and no finding and exits 0 (what the real scanner did in six scans of twenty beside a git writing to stderr, the commit's credential file unread), is refused naming the read's empty answer, and the remote never gets the credential (6e34a9d89 read the empty answer as no error, the count agreed, and the credential published)" {
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
        printf 'if [ "${1:-}" = git ]; then printf "%%s\\n" "gitleaks $*" >> %q; printf "%%s\\n" "5:17PM ERR [git] note: a benign line on stderr" "5:17PM INF 1 commits scanned." "5:17PM INF no leaks found" >&2; exit 0; fi\n' "$TEST_DIR/calls.scanner"
        printf 'exit 1\n'
    } > "$TEST_DIR/scanner/gitleaks"
    chmod 755 "$TEST_DIR/scanner/gitleaks"
    export ROMP_GITLEAKS="$TEST_DIR/scanner/gitleaks"
    calls_silent_on_text awk err-line '$2 == "ERR"'
    push_main_through_hook_with_shim
    fired scanner "gitleaks git "
    fired err-line '$2 == "ERR"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) could not be judged: its log's error-line read answered \"\" (awk exited 0), neither the word none nor an error line"* ]]
    at_base
}

@test "round 8b3 short case: the COMMIT COUNT line of the scanner log: an awk whose count line program answers the first digit of twelve (exit 0), beside the real scanner, through a real push of twelve clean commits, is refused naming the cut count against the hook's, and the remote stays at its base" {
    real_gitleaks
    r8b3_twelve_commits
    calls_short_on_text awk count-line '$4 == "commits"' bytes:1
    push_main_through_hook_with_shim
    fired_short count-line '$4 == "commits"'
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 12 commits with content to scan"* ]]
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

@test "round 8b3 short case: the log.showRoot configuration read: a git whose config --type=bool log.showRoot answers three bytes of false (exit 0) reads as the key unset and costs the advice line alone: through a real push the short scan is refused by the count arm, the advice absent, and the remote never gets the branch" {
    r8b2_credential_in_root_scanner_without_root
    calls_short_on git showroot '[ "${1:-}" = config ] && [ "${2:-}" = --type=bool ] && [ "${3:-}" = log.showRoot ]' bytes:3
    push_main_through_hook_with_shim
    fired_short showroot "config --type=bool log.showRoot"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" != *"while log.showRoot is false"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
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
    at_base
}

@test "round 8b3 short case: the root-commit probe, for the advice line: a git whose rev-list --max-parents=0 answers five bytes of the root's name (exit 0) prints the advice as the whole answer does (only its emptiness is read): through a real push the short scan is refused by the count arm and the remote never gets the branch" {
    r8b2_credential_in_root_scanner_without_root
    calls_short_on git root-probe '[ "${1:-}" = rev-list ] && [ "${2:-}" = --max-parents=0 ]' bytes:5
    push_main_through_hook_with_shim
    fired_short root-probe "rev-list --max-parents=0 $sha --not --remotes"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) covered 1 of the 2 commits with content to scan"* ]]
    [[ "$output" == *"while log.showRoot is false"* ]]
    run remote_holds_main
    [ "$status" -ne 0 ]
}

@test "round 8b3 short case: the scanner's argument list (gitleaks_args): the real scanner run on it with its log cut to ten bytes (its exit kept) leaves no count line, and the count arm refuses: through a real push of a clean commit the remote stays at its base" {
    real_gitleaks
    clean_tip_after_base
    r8b3_scanner_log_short 10
    mkdir -p "$TEST_DIR/shim"
    push_main_through_hook_with_shim
    fired_short scanner-log "gitleaks git "
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp pre-push: the CREDENTIAL scan of refs/heads/main (${sha:0:10}) reported no commit count, so what it read is unknown"* ]]
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

@test "round 8b3 controls with the scanner: the root's tail line and the counts refuse no clean push: a clean root commit pushed from the clone and a clean commit pushed from a worktree whose path extends the clone's each pass under the real scanner with no romp line" {
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
