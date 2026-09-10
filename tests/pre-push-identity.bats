#!/usr/bin/env bats

# .githooks/pre-push — the ADDRESS scan: the author and committer a commit is
# stamped with, driven by hand against real commits.
#
# A commit is published with its metadata, and the hook's two content scans (the
# tip's tree, each new commit's added lines) read none of it. A clone with no
# user.email set in any scope makes git stamp <login>@<hostname -f> on every
# commit, and a machine's name and its tailnet suffix are exactly what a
# private-strings denylist holds: three commits of one slice and a pushed merge
# carried such an address through both scans and gitleaks (2026-09-09). So the
# hook now greps the DOMAIN of each address a new commit carries, like a line of
# content, for every commit no fetched remote already has.
#
# Two limits, both pinned here because a scan of the whole identity would refuse
# every push its owner makes: the login before the @ and the name are not read
# (they are the author's own, on the denylist too because a FILE must not name
# them, and on every commit they make), and an address the clone is configured
# to use — user.email in any scope, or GIT_AUTHOR_EMAIL / GIT_COMMITTER_EMAIL /
# EMAIL in the environment — is excused whatever its domain says, since it is
# its owner's to publish and its domain may be their own name. An unset
# user.email chooses nothing, which is the case the scan exists for.
#
# An annotated TAG carries a tagger the same way, and every other read the hook
# makes peels a tag to the commit it names, so the tag object's own address is
# read here too: the tag cases at the end hold that.
#
# Every identifier below is SYNTHETIC: the denylist, the logins, the hosts and
# the domains are invented per test (the repo may go public, and a real one
# written here would be the very leak the hook exists to stop). pre-push-hook.bats
# holds the content scans' cases; this file holds the address scan's.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$ROMP_DIR/.githooks/pre-push"

load git-hermetic

setup() {
    # Hermetic git: the fixture commits with plain defaults and a synthetic identity
    # (git-hermetic exports GIT_AUTHOR_EMAIL / GIT_COMMITTER_EMAIL as tests@example.invalid);
    # a developer's global config, above all their user.email, must not reach the commits
    # or the hook, whose whole subject is which address a clone is configured to use.
    git_hermetic
    TEST_DIR="$(mktemp -d)"
    REPO="$TEST_DIR/repo"
    mkdir -p "$REPO"
    git -C "$REPO" init -q
    git -C "$REPO" symbolic-ref HEAD refs/heads/main     # whatever init.defaultBranch says
    # No user.email in the repo's config: the finding's clone. A test that models a
    # configured address sets one itself.
    git -C "$REPO" config user.name Tester
    # The hook under test is run BY HAND below; the fixture's own git operations must
    # not run this machine's hooks.
    mkdir -p "$TEST_DIR/no-hooks"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"

    # the denylist: an invented login, host and tailnet suffix, nothing that exists on any real box
    STRINGS="$TEST_DIR/private-strings.txt"
    printf '# synthetic\nzzsynthuser\nTESTHOST\nzzsynthnet\n' > "$STRINGS"

    export ROMP_PRIVATE_STRINGS="$STRINGS"
    export ROMP_NO_GITLEAKS=1          # the credential half has its own test file
}

teardown() { rm -rf "${TEST_DIR:-}"; }

ZERO=0000000000000000000000000000000000000000

# What an unset user.email would have stamped on this fixture's box: the login and
# the machine's tailnet FQDN, all three on the denylist. The login alone is a
# banned string too, which the login-only case below relies on.
STAMPED="zzsynthuser@TESTHOST.zzsynthnet.example"

# Run the hook from inside the repo, the way git does. bats' `run` executes the
# command in a subshell, so the cd here does not leak into the test. The hook sees
# the hermetic identity in its environment (tests@example.invalid), never the
# address a fixture commit was stamped with — commit_as sets that for one command.
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

# A commit of one file, stamped with the given author and committer addresses (the
# environment identity outranks config, so this is exactly the commit's identity).
commit_as() {   # <author_email> <committer_email> <path> <message>
    printf '%s\n' "the web session's work on $3" > "$REPO/$3"
    git -C "$REPO" add "$3"
    GIT_AUTHOR_EMAIL="$1" GIT_COMMITTER_EMAIL="$2" git -C "$REPO" commit -qm "$4"
}

# A commit under the hermetic identity, with a clean tree: the control.
commit_clean() {   # <path> <message>
    commit_as tests@example.invalid tests@example.invalid "$1" "$2"
}

# Feed the hook a TAG ref line: <refs/tags/name> pushed as new (the remote sha zero).
run_hook_tag() {   # <name>
    local sha
    sha="$(git -C "$REPO" rev-parse "refs/tags/$1")"
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< \
        "refs/tags/$1 $sha refs/tags/$1 $ZERO"
}

@test "a commit under the hermetic identity passes (the control)" {
    commit_clean ok.txt "clean"
    run_hook
    [ "$status" -eq 0 ]
}

@test "an address whose domain carries a banned string is refused, naming the commit, the roles and the address" {
    commit_as "$STAMPED" "$STAMPED" web.txt "stamped by an unset user.email"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${sha:0:10} is authored as <$STAMPED>"* ]]
    [[ "$output" == *"commit ${sha:0:10} is committed as <$STAMPED>"* ]]
    [[ "$output" == *"whose domain carries a personal identifier"* ]]
    [[ "$output" == *"BLOCKED"* ]]
    # the remedy names both readings: the address is yours (configure it), or git filled it (set yours and rewrite)
    [[ "$output" == *"git config --global user.email"* ]]
    [[ "$output" == *"user.useConfigOnly true"* ]]
    [[ "$output" == *"--reset-author"* ]]
}

@test "the address remedy is not offered for a content hit" {
    printf '%s\n' "home is /home/zzsynthuser/code" > "$REPO/leak.txt"
    git -C "$REPO" add leak.txt
    git -C "$REPO" commit -qm "leak in a file"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"personal identifier in:"* ]]
    [[ "$output" != *"--reset-author"* ]]
}

@test "the domain is matched case-insensitively, like a line of content" {
    commit_as "dev@testhost.example" "dev@testhost.example" web.txt "lowercase host"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"is authored as <dev@testhost.example>"* ]]
}

@test "the login before the @ is the author's own and is not read" {
    commit_as "zzsynthuser@example.invalid" "zzsynthuser@example.invalid" web.txt "login on the denylist"
    run_hook
    [ "$status" -eq 0 ]
}

@test "the address the clone is configured to use is excused, whatever its domain says" {
    # the owner's own address, with their own name for a domain: on every commit they make
    git -C "$REPO" config user.email dev@zzsynthuser.example
    commit_as dev@zzsynthuser.example dev@zzsynthuser.example web.txt "the owner's address"
    run_hook
    [ "$status" -eq 0 ]
}

@test "the same address on a clone that did NOT configure it is refused" {
    # an unset user.email vouches for nothing: the hook cannot tell the owner's address
    # from one git filled in, and the remedy says which one-line config settles it
    commit_as dev@zzsynthuser.example dev@zzsynthuser.example web.txt "the owner's address, unconfigured"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${sha:0:10} is authored as <dev@zzsynthuser.example>, an address this clone is not configured to use"* ]]
    [[ "$output" == *"if it is yours, say so (git config --global user.email <address>)"* ]]
}

@test "an address the environment chooses is excused too (EMAIL, git's fallback for an unset user.email)" {
    commit_as dev@zzsynthuser.example dev@zzsynthuser.example web.txt "the owner's address"
    EMAIL=dev@zzsynthuser.example run_hook
    [ "$status" -eq 0 ]
}

@test "the configured address excuses only itself: a second stamped address is still refused" {
    git -C "$REPO" config user.email dev@zzsynthuser.example
    commit_as dev@zzsynthuser.example dev@zzsynthuser.example ok.txt "the owner's address"
    commit_as "$STAMPED" "$STAMPED" web.txt "stamped elsewhere"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${sha:0:10} is authored as <$STAMPED>"* ]]
    [[ "$output" != *"dev@zzsynthuser.example"* ]]
}

@test "a commit authored cleanly but COMMITTED under the machine's name is refused as committed, not authored" {
    # the shape of a cherry-pick or a rebase on the unconfigured clone: the author kept, the committer stamped
    commit_as tests@example.invalid "$STAMPED" web.txt "rebased here"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${sha:0:10} is committed as <$STAMPED>"* ]]
    [[ "$output" != *"is authored as"* ]]
}

@test "an empty address is nothing to publish" {
    # `<>` is what an explicitly empty identity leaves on a commit; there is no domain in it
    commit_as "" "" web.txt "no address at all"
    [[ "$(git -C "$REPO" log -1 --format='%ae|%ce')" == "|" ]]
    run_hook
    [ "$status" -eq 0 ]
}

@test "a stamped INTERMEDIATE commit is caught and named when the tip's identity is clean" {
    commit_as "$STAMPED" "$STAMPED" web.txt "stamped"
    stamped_sha="$(git -C "$REPO" rev-parse HEAD)"
    commit_clean api.txt "configured since"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${stamped_sha:0:10} is authored as <$STAMPED>"* ]]
}

@test "a stamped commit a remote already has is not rechecked: only what THIS push publishes counts" {
    # the address is already public through that remote; refusing every later push of the
    # branch would fix nothing (its remedy is a deliberate rewrite and force-push, the owner's call)
    commit_as "$STAMPED" "$STAMPED" web.txt "stamped, then pushed"
    git -C "$REPO" update-ref refs/remotes/origin/main HEAD
    commit_clean api.txt "the one commit new to every remote"
    run_hook "$(git -C "$REPO" rev-parse origin/main)"
    [ "$status" -eq 0 ]
}

@test "no denylist file means no address scan (a fresh clone is unaffected)" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    commit_as "$STAMPED" "$STAMPED" web.txt "stamped"
    run_hook
    [ "$status" -eq 0 ]
}

@test "a merge commit's addresses are read like any other commit's" {
    # the pushed merge of the 2026-09-09 finding: a clean tree on both sides, the merge itself stamped
    commit_clean base.txt "base"
    git -C "$REPO" checkout -q -b feature
    commit_clean web.txt "branch work"
    git -C "$REPO" checkout -q main
    commit_clean api.txt "main work"
    git -C "$REPO" checkout -q feature
    GIT_AUTHOR_EMAIL="$STAMPED" GIT_COMMITTER_EMAIL="$STAMPED" git -C "$REPO" merge -q --no-ff -m "merge main" main
    merge_sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${merge_sha:0:10} is committed as <$STAMPED>"* ]]
}

@test "an annotated tag's TAGGER is read like a committer: stamped by an unset user.email, the tag is refused naming the tag, the address and its own remedy" {
    commit_clean ok.txt "clean"
    # the tagger is the committer identity of the clone that cut the tag
    GIT_COMMITTER_EMAIL="$STAMPED" git -C "$REPO" tag -a v1 -m "release one"
    sha="$(git -C "$REPO" rev-parse refs/tags/v1)"
    [ "$(git -C "$REPO" cat-file -t "$sha")" = tag ]
    run_hook_tag v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"tag refs/tags/v1 (${sha:0:10}) is tagged as <$STAMPED>, an address this clone is not configured to use"* ]]
    [[ "$output" == *"git tag -f -a <name> <commit>"* ]]
    # the commit the tag names is clean, and is reported as nothing
    [[ "$output" != *"is authored as"* ]]
    [[ "$output" != *"is committed as"* ]]
}

@test "an annotated tag under the configured address passes, and a lightweight tag has no metadata of its own" {
    git -C "$REPO" config user.email dev@zzsynthuser.example
    commit_as dev@zzsynthuser.example dev@zzsynthuser.example ok.txt "the owner's commit"
    GIT_COMMITTER_EMAIL=dev@zzsynthuser.example git -C "$REPO" tag -a v1 -m "release one"
    run_hook_tag v1
    [ "$status" -eq 0 ]
    git -C "$REPO" tag light
    [ "$(git -C "$REPO" cat-file -t refs/tags/light)" = commit ]
    run_hook_tag light
    [ "$status" -eq 0 ]
}

@test "the commit an annotated tag names is still read through the tag: a clean tagger over a stamped commit is refused naming the commit" {
    commit_as "$STAMPED" "$STAMPED" web.txt "stamped by an unset user.email"
    commit_sha="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" tag -a v1 -m "release one"     # the hermetic identity: an address the environment chose
    run_hook_tag v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"commit ${commit_sha:0:10} is authored as <$STAMPED>"* ]]
    [[ "$output" != *"is tagged as"* ]]
}
