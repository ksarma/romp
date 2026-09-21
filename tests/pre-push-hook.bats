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
# transform cases at the end hold that line, and a replace ref, under which the
# scans and the push can read different objects, is refused before either scan,
# where a scan would run at all: a clone with no denylist and no credential scan
# makes no clean report a replace ref could falsify. The last section is the
# identifier scan's own transform: a text file whose PATH's diff attribute makes
# git call it binary is read by neither content check, and is refused rather
# than scanned, with the tip or the commit, the path and the attribute named.

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

# Both reads ask git for no colour. With color.ui or color.diff set to always,
# git colours `log -p` written to a pipe; gitleaks finds no file header in the
# coloured stream and reports `0 commits scanned` with no ERR line, and a count
# read from the same coloured stream agreed with it, so a push carrying a
# credential passed both conditions (found by execution, 2026-09-21, the review
# round's derivation). The scanner's git is given --no-color through --log-opts
# and the hook's own count reads with --no-color too.

@test "a credential is found under color.ui=always: the scanner's git and the hook's own count both ask git for no colour" {
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
    fail_diff_tree_stdin                                # the count's read alone: gitleaks' git and the identifier scan's diff-tree run unchanged
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
# count, naming the key and the remedy.
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

@test "a scanner whose git does not honour --root (a wrapper removing the option from the scanner's log options) is refused on the count under log.showRoot=false with a root credential: the line names the key, says the option was not honoured, and gives the remedy; no finding" {
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
    [[ "$output" == *"romp pre-push: log.showRoot is false in this clone's configuration and the scanner's git did not honour the --root option the hook passes on its log, which hides a root commit's diff; set the key to true (git config log.showRoot true) or unset it and push again, or ROMP_NO_GITLEAKS=1 skips the credential scan for this one push"* ]]
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

# ── the replace-ref gate: only where a scan would run ────────────────────
# The refusal above prevents a false CLEAN REPORT, and only a scan that runs
# makes one. Where the denylist file is absent and the credential scan is
# skipped (ROMP_NO_GITLEAKS) or has no binary, nothing is scanned and nothing is
# reported, so a replace ref falsifies nothing and the push is not the hook's
# to refuse: a clone that never asked for either scan is unaffected, the rule
# CLAUDE.md states. The gate reads the two predicates the scans' own early
# returns read (identifier_scan_armed, credential_scan_armed).

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

# ── a diff attribute that hides a text file from the identifier scan ─────
# Both content checks read what git calls text: git grep -I skips a blob git
# calls binary and diff-tree -p prints no line for one, and git calls a blob
# binary by its PATH's diff attribute as well as by its bytes (a -diff line or
# the binary macro, in .gitattributes, .git/info/attributes or the file
# core.attributesFile names; a driver with diff.<driver>.binary true). Found by
# execution (2026-09-21): a text file under -diff carrying a denylist string
# went through a real push with the denylist armed and nothing printed. The
# hook now reads the diff attribute of every regular file at the tip and in
# each new commit, and a hidden path whose blob is text by git's byte rule (no
# NUL in the first 8000 bytes) refuses the push rather than being scanned,
# naming the tip or the commit, the path and the attribute; a hidden blob that
# is binary by its bytes passes as binaries always have. The advice names the
# attribute as the cause and what to do about it (drop it, or keep the file text
# on purpose with an explicit diff line that outranks it), and a rename or copy
# of such a file is refused the same way, since its bytes reach the remote under
# the new path. The first two cases push for real with the hook installed, so
# the remote's state is asserted too.

# The hook installed for one real push of main to the bare remote; the
# fixture's own commits run no hooks before or after.
push_main_through_hook() {
    add_remote
    mkdir -p "$TEST_DIR/hooks"
    ln -s "$HOOK" "$TEST_DIR/hooks/pre-push"
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

@test "a text file under -diff carrying a banned string is refused rather than scanned, naming the tip, the commit, the path and the attribute; the remote holds nothing" {
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
    [[ "$output" == *"romp pre-push: notes.txt in commit ${sha:0:10} is text that its diff attribute (unset) hides from the identifier scan"* ]]
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
    [[ "$output" == *"romp pre-push: notes-b.txt in commit ${sha:0:10} is text that its diff attribute (unset) hides from the identifier scan, so the push is refused rather than scanned"* ]]
    [[ "$output" == *"notes-b.txt at the tip of refs/heads/main (${sha:0:10}) is text"* ]]
    [[ "$output" != *"notes-a.txt"* ]]                        # the old path is a deletion: nothing to read there
    [[ "$output" == *"Remove the diff attribute for each path named"* ]]
    [[ "$output" == *"or keep the file text on purpose with an explicit \"<path> diff\" line (a later line in .gitattributes overrides a -diff inherited from a broader pattern"* ]]
    [[ "$output" == *"A rename or copy of such a file is content too: its bytes reach the remote under the new path, so the refusal is about the attribute, not the rename."* ]]
    [[ "$output" != *"personal identifier"* ]]
}

@test "with no denylist a -diff text file passes and no such line prints: the identifier scan is a no-op, attribute or not" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    attributes 'notes.txt -diff'
    commit_file notes.txt "seen on TESTHOST" "a banned string in a -diff file"
    run_hook
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# The check's own reads fail closed like every other: the attribute read and
# the hidden blob's content read, each against its refusing input.

@test "a check-attr that fails refuses the push as unscanned, naming the read" {
    commit_file file.txt "nothing to see" "clean"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_refusing '[ "${1:-}" = check-attr ]' 128 "fatal: shim: check-attr refused"
    run _hook_in "$REPO" -c 'printf "file.txt\0" | git check-attr --stdin -z diff'
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the DIFF ATTRIBUTES of the paths refs/heads/main (${sha:0:10}) publishes could not be read (git check-attr exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "a hidden blob whose content cannot be read refuses the push as unscanned, naming the path and the attribute: an unread blob is not a binary one" {
    attributes 'notes.txt -diff'
    commit_file notes.txt "nothing to see" "a clean -diff file"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    blob="$(git -C "$REPO" rev-parse HEAD:notes.txt)"
    git_refusing "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = blob ] && [ \"\${3:-}\" = $blob ]" 128 "fatal: shim: cat-file blob refused for $blob"
    run _hook_in "$REPO" -c 'git cat-file blob "$1"' _ "$blob"
    [ "$status" -eq 128 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the CONTENT of notes.txt at the tip of refs/heads/main (${sha:0:10}), which its diff attribute (unset) hides from the identifier scan, could not be read (git cat-file exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"is text that its diff attribute"* ]]  # unread, so not called text either
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
    [[ "$output" == *"romp pre-push: log.showRoot is false in this clone's configuration"* ]]
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
