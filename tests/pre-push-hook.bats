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
fail_diff_tree() {   # [<sha whose diff-tree fails; every commit's when omitted>]
    if [ -n "${1:-}" ]; then
        git_refusing "[ \"\${1:-}\" = diff-tree ] && [ \"\${!#}\" = $1 ]" 128 "fatal: shim: diff-tree refused for $1"
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
# either alone has a hole: the shorter log writes no ERR line, and a discarded
# scan can still report the whole count.
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
# count as before, the line naming the key, saying the option was not honoured,
# and the remedy.

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
# `unspecified` or `unset`). The advice names the attribute as the cause where
# one is named and what to do about it (drop it, or keep the file text on
# purpose with an explicit diff line that outranks it), the configuration key
# where none is (or, for a one-parent commit's change of a file binary by its
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
    [[ "$output" != *"core.bigFileThreshold is not set"* ]]   # the key is not the cause here: the line states the cause, not the key's facts
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
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
    [[ "$output" != *"core.bigFileThreshold is not set"* ]]   # the key is not the cause here: the line states the cause, not the key's facts
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
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
    [[ "$output" != *"the diff read it as a rename, so the attribute of the path it came from counted too"* ]]   # the cause line names the old path itself
    [[ "$output" != *"core.bigFileThreshold is not set"* ]]
    [[ "$output" != *"a configuration key can be what makes git call the file binary"* ]]
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
# a quote, a backslash) with C escapes, undone before the join so the line
# names the path byte for byte; a path left quoted would meet no row.
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
# input: the scratch directory, the tip's listing and the grep's read list, each
# commit's listing and its numstat, a numstat that answers for fewer paths than
# the listing names, a type change's two reads (the empty tree's name, the
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

@test "a scratch directory that cannot be made (TMPDIR at a missing path) refuses the push as unscanned, naming mktemp" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    export TMPDIR="$TEST_DIR/no-such-dir"
    run _hook_in "$REPO" -c 'mktemp -d "$TMPDIR/romp-pre-push.XXXXXX"'
    [ "$status" -ne 0 ]
    run_hook
    [ "$status" -eq 1 ]
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

@test "a numstat that exits 0 and answers for FEWER paths than the commit changes is a short read, refused as unscanned: a missing answer is not an answer of text" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    remove_file file.txt "remove it"                             # gone at the tip: the blob is the commit's to judge, so the commit's reads are the ones that must answer (a blob the tip holds is the tip's, whatever a per-commit read says)
    empty_diff_tree_numstat
    run _hook_in "$REPO" -c 'git diff-tree -r -m -M --numstat --root -z --no-commit-id "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes)"* ]]
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

@test "a type change whose addition verdict answers nothing (the numstat against the empty tree exiting 0 with no row) is a short read, refused as unscanned: no answer is not an answer of text" {
    type_change_to_symlink
    remove_file thing "remove it"                                # gone at the tip: the new object is the commit's to judge (case 120's note)
    empty_empty_tree_numstat
    run _hook_in "$REPO" -c 'git diff-tree -r --numstat -z --no-commit-id --no-renames "$(git hash-object -t tree --stdin < /dev/null)" "$1" -- ":(literal)thing"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat answered for fewer paths than the commit changes)"* ]]
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

@test "a merge whose combined patch prints NOTHING (diff-tree -p -c exiting 0 with no output) is a short read, refused as unscanned: no section is not a verdict of text, and the hidden link is not called hidden either" {
    merge_with_hidden_link
    empty_combined_patch
    run _hook_in "$REPO" -c 'git diff-tree -p -r -M -c --root --no-commit-id --no-color "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for a path the merge changes)"* ]]
    [[ "$output" != *"exited"* ]]
    [[ "$output" != *"is text that"* ]]
    [[ "$output" != *"against the empty tree"* ]]
}

@test "a merge's pure rename whose addition verdict answers nothing (the numstat against the empty tree exiting 0 with no row) is a short read, refused as unscanned, naming that read and not the patch" {
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
    [[ "$output" == *"the BINARY VERDICTS of commit ${sha:0:10} could not be read (git diff-tree --numstat against the empty tree answered for fewer paths than the merge renames)"* ]]
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

@test "a merge whose listing against each parent answers NOTHING (diff-tree --raw -m exiting 0 with no output) leaves the third-path content a short read, refused as unscanned by the patch's arm: a listing that came up short names no candidate, and the path passes on nothing" {
    third_path_merge "nothing to see" pushed
    third_path_committed
    empty_per_parent_listing
    run _hook_in "$REPO" -c 'git diff-tree -r --raw --no-renames -m -z --no-commit-id "$1"' _ "$merge"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook "$BASE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"the BINARY VERDICTS of commit ${merge:0:10} could not be read (git diff-tree -p -c, the merge's combined patch, printed no verdict for a path the merge changes)"* ]]
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

@test "a path holding a newline byte is refused as unscanned at the tip and in the commit: the listings are joined line by line, and such a path would be judged by nothing" {
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
# shape (the rewrite; the newline test) and execs the real tr for every other,
# counting in a file since each invocation is its own process; the joins' own
# tr (newline to NUL) is neither shape and runs through. Once per test, like
# git_refusing. Since round 5 every commit's scratch files are rewritten, a
# deletion-only commit's too (its listing is checked against its verdicts), so
# the count of a rewrite is the tip's two, then eight per one-parent commit
# (post, gone, rows, rows2, links, tpaths, rows3, listed), read newest first.
# The second class has its own shims: a tr whose rewrite of the ONE input
# holding a marker exits 0 and writes nothing (tr_silent_on, keyed on the
# content and not on a count, so the same fault reaches the same file at any
# hook text), and a wc that reads its input and answers nothing.
tr_refusing() {   # <rewrite|test> <N>: the Nth tr of that shape exits 1, the real tr runs otherwise
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
if [ "$shape" = "$want" ]; then
    seen=$(( $(cat "$counter") + 1 )); echo "$seen" > "$counter"
    if [ "$seen" -eq "$n" ]; then echo "shim: tr refused ($shape $n)" >&2; exit 1; fi
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

@test "a check-attr that fails leaves the refusal standing, the failure in the attribute's place: the label read cannot lift a verdict git made" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_refusing '[ "${1:-}" = check-attr ]' 128 "fatal: shim: check-attr refused"
    run _hook_in "$REPO" -c 'git check-attr -z diff -- notes.txt'
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr exited 128), so no attribute of its path accounts for the verdict"* ]]
    [[ "$output" == *"the push is refused rather than scanned"* ]]
    [[ "$output" != *"(unset)"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a check-attr that answers about ANOTHER path leaves the refusal standing, the answer named as out of step with the path asked" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    check_attr_answering 'other.txt\0diff\0unset\0'
    run _hook_in "$REPO" -c 'git check-attr -z diff -- notes.txt | tr "\0" "|"'
    [ "$output" = "other.txt|diff|unset|" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr answered out of step with the path asked), so no attribute of its path accounts for the verdict"* ]]
    [[ "$output" != *"(unset)"* ]]
}

@test "a check-attr that answers NOTHING (a truncated read) leaves the refusal standing, the short answer named: the push does not pass" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    check_attr_answering ''
    run _hook_in "$REPO" -c 'git check-attr -z diff -- notes.txt'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"notes.txt at the tip of refs/heads/main (${sha:0:10}) is text that git calls binary although its diff attribute could not be read (git check-attr answered nothing for the path asked), so no attribute of its path accounts for the verdict"* ]]
    [[ "$output" == *"the push is refused rather than scanned"* ]]
}


# ── the chosen-addresses read: its failure is the strict side ─────────────
# The address rule (each new commit's author and committer address is checked
# unless the clone CHOSE it: user.email in any scope, or the environment's
# GIT_AUTHOR_EMAIL, GIT_COMMITTER_EMAIL or EMAIL) has its own file,
# pre-push-identity.bats; the two cases here are about the READ behind it.
# chosen_emails reads user.email once per push (git config --get-all
# user.email) and swallows a failure of that read: unlike the reads above it is
# neither reported nor refused as unscanned; it contributes no address, the way
# an unset key does, and every stamped address is then checked against the
# environment's addresses alone. That is the strict side (a failed read can
# refuse an address the clone did configure; it can never excuse one), so the
# cases record that shape as the hook's, not a refusal as unscanned. Both push
# for REAL through the hook so the remote's state is asserted too, which takes
# a wrapper: git prepends its own exec path to the PATH a hook sees, so a shim
# first on the test's PATH reaches a hook run by hand (run_hook) but not one a
# real push runs (verified by execution, git 2.43.0: through
# push_main_through_hook the hook's git resolved to git's exec path).

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

@test "a chosen-addresses read that FAILS (git config --get-all user.email exiting 128) is swallowed as no chosen address, the strict side: a commit stamped under a banned domain is refused with the address line through a real push and the remote holds nothing, and configuring the clone to use that address changes nothing while the read fails" {
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
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} is authored as <dev@zzsynthuser.example>, an address this clone is not configured to use, whose domain carries a personal identifier"* ]]
    [[ "$output" == *"commit ${sha:0:10} is committed as <dev@zzsynthuser.example>"* ]]
    [[ "$output" == *"if it is yours, say so (git config --global user.email <address>)"* ]]
    [[ "$output" == *"BLOCKED"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]       # the failed read is swallowed, not reported: the refusal is the address's alone
    [[ "$output" != *"shim:"* ]]                        # the shim's own line went to the redirection chosen_emails puts on the read
    run remote_holds_main                             # the checked form (tests/test_bats_bare_negation.py): a bare ! mid-test checks nothing under bats
    [ "$status" -ne 0 ]
    # the clone now chooses the address: with the read intact that excuses it, whatever its domain says
    # (pre-push-identity.bats, the configured-address case); behind the failed read the choice is not
    # seen, the push stays refused and the line still calls the address unconfigured. Stricter, not looser.
    git -C "$REPO" config user.email dev@zzsynthuser.example
    push_main_through_hook_with_shim
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${sha:0:10} is authored as <dev@zzsynthuser.example>, an address this clone is not configured to use"* ]]
    ! remote_holds_main
}

@test "the same failed read beside a commit stamped under a clean domain the clone did not choose passes through a real push and the remote holds main: the failure itself refuses nothing" {
    add_remote
    commit_stamped_as dev@example.invalid web.txt "stamped under a clean domain the clone did not choose"
    fail_config_user_email
    run _hook_in "$REPO" -c 'git config --get-all user.email'
    [ "$status" -eq 128 ]
    push_main_through_hook_with_shim
    [ "$status" -eq 0 ]
    [[ "$output" != *"romp pre-push"* ]]
    remote_holds_main
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
