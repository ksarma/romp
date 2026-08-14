#!/usr/bin/env bats

# .githooks/pre-push — the identifier scan, exercised against real commits.
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

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$ROMP_DIR/.githooks/pre-push"

setup() {
    TEST_DIR="$(mktemp -d)"
    REPO="$TEST_DIR/repo"
    mkdir -p "$REPO"
    git -C "$REPO" init -q
    git -C "$REPO" config user.email t@example.invalid
    git -C "$REPO" config user.name  Tester

    # the denylist: one invented identifier, nothing that exists on any real box
    STRINGS="$TEST_DIR/private-strings.txt"
    printf '# synthetic\nzzsynthuser\nTESTHOST\n' > "$STRINGS"

    export ROMP_PRIVATE_STRINGS="$STRINGS"
    export ROMP_NO_GITLEAKS=1          # the credential half has its own test file
}

teardown() { rm -rf "${TEST_DIR:-}"; }

# Feed the hook a ref line the way git does: <local_ref> <sha> <remote_ref> <zero>
# (zero remote sha = a new branch, i.e. every commit here is being published).
run_hook() {
    local sha
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run env -C "$REPO" bash "$HOOK" origin git@example.invalid:x/y.git <<< \
        "refs/heads/main $sha refs/heads/main 0000000000000000000000000000000000000000"
}

@test "a clean commit passes" {
    echo "nothing to see" > "$REPO/file.txt"
    git -C "$REPO" add file.txt
    git -C "$REPO" commit -qm "clean"
    run_hook
    [ "$status" -eq 0 ]
}

@test "an identifier in a regular file is blocked" {
    echo "home is /home/zzsynthuser/code" > "$REPO/file.txt"
    git -C "$REPO" add file.txt
    git -C "$REPO" commit -qm "leak"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"personal identifier"* ]]
}

@test "an identifier in a SYMLINK TARGET is blocked" {
    # the 2026-08-13 incident, reproduced: git grep cannot see this, the hook must
    ln -s /home/zzsynthuser/code/romp/vscode-extension/node_modules "$REPO/node_modules"
    git -C "$REPO" add node_modules
    git -C "$REPO" commit -qm "symlink leak"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"SYMLINK TARGET"* ]]
    [[ "$output" == *"node_modules"* ]]
}

@test "the symlink scan names the offending link and its target" {
    ln -s /home/zzsynthuser/notes "$REPO/notes-link"
    git -C "$REPO" add notes-link
    git -C "$REPO" commit -qm "symlink leak"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"notes-link -> /home/zzsynthuser/notes"* ]]
}

@test "a RELATIVE symlink with no identifier still passes" {
    # the repo's own bin/romp-* links are all of this shape — they must not trip it
    mkdir -p "$REPO/kernel" "$REPO/bin"
    echo "x" > "$REPO/kernel/kernel.py"
    ln -s ../kernel/kernel.py "$REPO/bin/romp-kernel"
    git -C "$REPO" add .
    git -C "$REPO" commit -qm "relative link"
    run_hook
    [ "$status" -eq 0 ]
}

@test "an identifier in an INTERMEDIATE commit is caught, not just the tip" {
    ln -s /home/zzsynthuser/x "$REPO/bad"
    git -C "$REPO" add bad
    git -C "$REPO" commit -qm "leak"
    git -C "$REPO" rm -q bad                      # tip is clean; history is not
    git -C "$REPO" commit -qm "remove it"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"SYMLINK TARGET"* ]]
}

@test "no denylist file means no identifier scan (a fresh clone is unaffected)" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    ln -s /home/zzsynthuser/x "$REPO/bad"
    git -C "$REPO" add bad
    git -C "$REPO" commit -qm "leak"
    run_hook
    [ "$status" -eq 0 ]
}
