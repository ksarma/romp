#!/usr/bin/env bats

# tests/git-hermetic.bash: after git_hermetic, git reads no global or system config and every
# commit has an identity, whatever the box is configured with.

load git-hermetic

setup() {
    TEST_DIR="$(mktemp -d)"
    # A stand-in for the developer's global config: a hooks directory whose pre-commit refuses
    # every commit and leaves a marker, wired in through core.hooksPath.
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME" "$TEST_DIR/hooks"
    printf '#!/bin/sh\necho ran > "%s/hook-ran"\nexit 1\n' "$TEST_DIR" > "$TEST_DIR/hooks/pre-commit"
    chmod +x "$TEST_DIR/hooks/pre-commit"
    printf '[core]\n\thooksPath = %s\n[user]\n\tname = Global Person\n\temail = global@example.invalid\n' \
        "$TEST_DIR/hooks" > "$HOME/.gitconfig"
    unset GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM XDG_CONFIG_HOME
    unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
    REPO="$TEST_DIR/repo"
    git init -q "$REPO"
    echo a > "$REPO/a.txt"
    git -C "$REPO" add a.txt
}

teardown() { rm -rf "${TEST_DIR:-}"; }

@test "the probe is live: without git_hermetic the global hooksPath blocks the commit" {
    run git -C "$REPO" commit -qm seed
    [ "$status" -ne 0 ]
    [ -f "$TEST_DIR/hook-ran" ]
}

@test "with git_hermetic the global hook never runs and the commit lands" {
    git_hermetic
    run git -C "$REPO" commit -qm seed
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_DIR/hook-ran" ]
    [ "$(git -C "$REPO" config --global --get core.hooksPath || true)" = "" ]
}

@test "the identity is the synthetic one, not the global config's" {
    git_hermetic
    git -C "$REPO" commit -qm seed
    [ "$(git -C "$REPO" log -1 --format='%an <%ae>')" = "romp tests <tests@example.invalid>" ]
    [ "$(git -C "$REPO" log -1 --format='%cn <%ce>')" = "romp tests <tests@example.invalid>" ]
}

@test "a test's own identity exports after git_hermetic still win" {
    git_hermetic
    # The env identity outranks `git config user.*` and `-c user.*`, so a test that must pin a
    # particular author exports its own GIT_AUTHOR_* / GIT_COMMITTER_* after git_hermetic.
    GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@e.invalid git -C "$REPO" commit -qm seed
    [ "$(git -C "$REPO" log -1 --format='%an <%ae>')" = "t <t@e.invalid>" ]
}
