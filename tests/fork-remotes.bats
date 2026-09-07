#!/usr/bin/env bats

# scripts/fork-remotes.sh and scripts/upstream-check.sh — the fork's guard rail.
# The thing under test is that a push can only ever reach the fork: `upstream`
# exists to fetch from and dies loudly if anyone pushes at it. Everything runs
# against two local bare repos, so no test touches the network.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

load git-hermetic

setup() {
    git_hermetic
    TEST_DIR="$(mktemp -d)"
    UP="$TEST_DIR/project.git"          # what we forked from
    FORK="$TEST_DIR/fork.git"           # our copy
    REPO="$TEST_DIR/clone"              # the working clone under test
    git init -q --bare "$UP"
    git init -q --bare "$FORK"
    # Both bare repos default HEAD to master; the branch we push is main, and a
    # clone of a repo whose HEAD names a missing ref checks nothing out.
    git -C "$UP" symbolic-ref HEAD refs/heads/main
    git -C "$FORK" symbolic-ref HEAD refs/heads/main

    git init -q "$TEST_DIR/seed"
    git -C "$TEST_DIR/seed" config user.email t@e.invalid
    git -C "$TEST_DIR/seed" config user.name t
    git -C "$TEST_DIR/seed" checkout -q -b main
    echo "one" > "$TEST_DIR/seed/kernel.py"
    echo "docs" > "$TEST_DIR/seed/guide.md"
    git -C "$TEST_DIR/seed" add -A
    git -C "$TEST_DIR/seed" commit -qm "first"
    git -C "$TEST_DIR/seed" push -q "$UP" main
    git -C "$TEST_DIR/seed" push -q "$FORK" main

    git clone -q "$FORK" "$REPO"
    git -C "$REPO" config user.email t@e.invalid
    git -C "$REPO" config user.name t
    mkdir -p "$REPO/scripts"
    cp "$ROMP_DIR/scripts/fork-remotes.sh" "$ROMP_DIR/scripts/upstream-check.sh" "$REPO/scripts/"
    chmod +x "$REPO/scripts"/*.sh
    export ROMP_UPSTREAM_URL="$UP"
}

teardown() {
    rm -rf "$TEST_DIR"
    return 0
}

# Add a commit to the upstream project, as a merged PR would.
upstream_commit() {  # <file> <text> <subject>
    git -C "$TEST_DIR/seed" pull -q "$UP" main
    echo "$2" > "$TEST_DIR/seed/$1"
    git -C "$TEST_DIR/seed" add -A
    git -C "$TEST_DIR/seed" commit -qm "$3"
    git -C "$TEST_DIR/seed" push -q "$UP" main
}

@test "it adds upstream as a fetch source and leaves origin alone" {
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" remote get-url upstream)" = "$UP" ]
    [ "$(git -C "$REPO" remote get-url origin)" = "$FORK" ]
}

@test "a push aimed at upstream fails instead of landing on the project" {
    "$REPO/scripts/fork-remotes.sh"
    run git -C "$REPO" push upstream main
    [ "$status" -ne 0 ]
    # And the project's history is untouched by the attempt.
    [ "$(git -C "$UP" rev-list --count main)" = "1" ]
}

@test "a bare push still reaches the fork" {
    "$REPO/scripts/fork-remotes.sh"
    echo "mine" > "$REPO/kernel.py"
    git -C "$REPO" commit -qam "a fork change"
    run git -C "$REPO" push origin main
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" config --get remote.pushDefault)" = "origin" ]
    [ "$(git -C "$FORK" rev-list --count main)" = "2" ]
}

@test "--check fails on an unguarded clone and passes once configured" {
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"no 'upstream' remote"* ]]

    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check catches an upstream someone made pushable again" {
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote set-url --push upstream "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"PUSHABLE"* ]]
}

@test "--check catches origin's PUSH url repointed at the project" {
    # The repo_id check only reads origin's FETCH url; a separately-set push url that aims at the
    # project sends a bare push there while --check used to print the all-clear.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote set-url --push origin "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin PUSHES to"* ]]
    # ...and configuring again fixes it, so the "run fork-remotes.sh to fix" advice is honest.
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check catches a branch.pushRemote that overrides pushDefault" {
    # branch.<name>.pushRemote wins over remote.pushDefault, so a bare push from that branch can land
    # on the project even with pushDefault=origin. --check must inspect it, and configure must clear it.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add proj "$UP"
    git -C "$REPO" config branch.main.pushRemote proj
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    # git lowercases config keys in --get-regexp output, so match on the stable message tail.
    [[ "$output" == *"a bare push from that branch would not go to your fork"* ]]
    "$REPO/scripts/fork-remotes.sh"
    run git -C "$REPO" config --get branch.main.pushRemote
    [ "$status" -ne 0 ]                              # unset by configure
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check leaves a branch.pushRemote that already points at origin alone" {
    # Pointing a branch's pushRemote AT the fork is harmless and legitimate — the guard must not
    # flag or strip it, only the ones aimed elsewhere.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config branch.main.pushRemote origin
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" config --get branch.main.pushRemote)" = "origin" ]
}

@test "it refuses a clone whose origin is the project itself" {
    git -C "$REPO" remote set-url origin "$UP"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]]
    # Nothing half-configured is left behind.
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
}

@test "running it twice changes nothing the second time" {
    "$REPO/scripts/fork-remotes.sh"
    before="$(git -C "$REPO" remote -v)"
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" remote -v)" = "$before" ]
}

@test "upstream-check says nothing when there is nothing new" {
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/upstream-check.sh" --quiet
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "upstream-check lists what the project added and flags the files we also changed" {
    "$REPO/scripts/fork-remotes.sh"
    echo "our version" > "$REPO/kernel.py"
    git -C "$REPO" commit -qam "our own change"
    upstream_commit kernel.py "their version" "their kernel change"
    upstream_commit guide.md "their docs" "their docs change"

    run "$REPO/scripts/upstream-check.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 new commit(s)"* ]]
    [[ "$output" == *"their kernel change"* ]]
    [[ "$output" == *"the merge lands here"* ]]
    [[ "$output" == *"kernel.py"* ]]
    # It reports and stops: our branch is where it was, no merge happened.
    [ "$(git -C "$REPO" rev-list --count main)" = "2" ]
}

@test "upstream-check says the merge is clean when the changes do not overlap" {
    "$REPO/scripts/fork-remotes.sh"
    echo "our docs" > "$REPO/guide.md"
    git -C "$REPO" commit -qam "our docs change"
    upstream_commit kernel.py "their version" "their kernel change"

    run "$REPO/scripts/upstream-check.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"should be clean"* ]]
}

@test "upstream-check refuses to guess when the clone has no upstream" {
    run "$REPO/scripts/upstream-check.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"run scripts/fork-remotes.sh first"* ]]
}
