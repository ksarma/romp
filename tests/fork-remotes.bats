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

# origin set by mistake to the url of another remote the clone carries (another fork kept as a second
# remote, say) passes every check that compares origin with the project or with itself, and a fetch,
# a bare gh PR number and possibly every push would go to that repository. --check compares each of
# origin's urls (its first, any extra, and its push urls) with each url of every other remote, by
# repo_id and as git resolves them. A mistake planted before configuring is left standing
# (configuring never rewrites origin's fetch url) while the push guards go in place, so the shared
# repository is the only thing wrong. The other remotes name local paths nothing fetches.

@test "--check fails when origin is the same repository as another remote's fetch url, naming both" {
    # Two spellings of one repository, a file:// url and a bare path: repo_id counts them equal.
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "file://$TEST_DIR/mirror.git"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url file://$TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]]
    # configuring copied the wrong fetch url onto the push url, and the note says so
    [[ "$output" == *"a push to origin goes to file://$TEST_DIR/mirror.git. "* ]]
    # the steps cover the push url as well as the fetch url, with the rerun after them, and the
    # standalone rerun line stays out
    [[ "$output" == *"(git remote set-url origin <your-fork-url>, then git remote set-url --push origin <your-fork-url>), then run scripts/fork-remotes.sh"* ]]
    [[ "$output" != *"Run scripts/fork-remotes.sh to fix."* ]]
    # and following them, in that order, clears --check
    git -C "$REPO" remote set-url origin "$FORK"
    git -C "$REPO" remote set-url --push origin "$FORK"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check gives no rerun line when origin's fetch url moved after configuring, and says where pushes go" {
    # Configured on the fork, then origin's fetch url set to another remote's: the push url that
    # configuring set still names the fork. A rerun now would copy the wrong fetch url onto the push
    # url and move pushes as well, so the rerun line is withheld though the push check also fires.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]]
    [[ "$output" == *"a push to origin goes to $FORK. "* ]]
    [[ "$output" == *"origin PUSHES to $FORK"* ]]        # a note a rerun would otherwise answer
    [[ "$output" != *"Run scripts/fork-remotes.sh to fix."* ]]
}

@test "--check fails when origin is the same repository as another remote's push url" {
    # The other remote fetches from one repository and pushes to another, and origin is the one it
    # pushes to: a check that read only each remote's fetch url would pass this clone.
    git -C "$REPO" remote add mirror "$TEST_DIR/elsewhere.git"
    git -C "$REPO" remote set-url --push mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (push url $TEST_DIR/mirror.git)"* ]]
}

@test "--check fails when origin's second push url is another remote's repository" {
    # A push goes to every push url a remote carries. origin's first is the fork, which is all the
    # origin push check reads; the second is the other remote's repository, so every push lands there
    # as well. Planted after configuring, whose set-url refuses a remote with two push urls.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url --add --push origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's push url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]]
    [[ "$output" == *"git remote set-url --delete --push origin <that-url>"* ]]
    [[ "$output" != *"Run scripts/fork-remotes.sh to fix."* ]]
}

@test "--check fails when a url of origin's after its first is another remote's repository" {
    # git fetches from a remote's first url only, but with no push url a push goes to every url it
    # carries, so the second one is a push destination and not a fetch url. Its remedy is the one git
    # accepts on a remote with several urls (a plain set-url origin refuses those). Planted after
    # configuring, with the push url that configuring set removed again, so pushes follow the urls.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config --unset remote.origin.pushurl
    git -C "$REPO" config --add remote.origin.url "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's extra url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git): git fetches only from origin's first url, and a push to origin goes to $FORK, $TEST_DIR/mirror.git. "* ]]
    [[ "$output" == *"git remote set-url --delete origin <that-url>"* ]]
    [[ "$output" != *"origin's fetch url"* ]]
    # and that remedy clears it
    git -C "$REPO" remote set-url --delete origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check reads another remote's url after git's insteadOf rewrite" {
    # The other remote is written as an alias that url.<base>.insteadOf expands to origin's url. git
    # fetches and pushes the expanded url, so the check must compare that one, not the alias.
    git -C "$REPO" config "url.$TEST_DIR/.insteadOf" "short:"
    git -C "$REPO" remote add mirror "short:mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]]
}

@test "--check reads origin's push url set to the dead sentinel as a push to fix, not a shared repository" {
    # upstream's push url is the sentinel, which names no repository, so origin carrying it too shares
    # nothing with upstream: the origin push check names it, and a rerun resets it.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote set-url --push origin "no-push://upstream-is-fetch-only"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin PUSHES to"* ]]
    [[ "$output" != *"is the same repository as"* ]]
    [[ "$output" == *"Run scripts/fork-remotes.sh to fix."* ]]
}

@test "--check passes with origin, a fetch-only upstream and a third remote of its own" {
    # The healthy shape: a third remote whose fetch and push urls are both repositories other than
    # origin's.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url --push mirror "$TEST_DIR/mirror-push.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"✗"* ]]
    # the all-clear names what --check verified and nothing more: the third remote stays pushable, and
    # no clause says where a bare push goes
    [[ "$output" == *"✓ upstream fetches from the project and is fetch-only; origin pushes to the repository it fetches from, shares no repository with another remote, and is gh's only default repository; no pushDefault or pushRemote is set to anything but origin"* ]]
}

@test "--check counts origin with a slash after .git as the same repository as a remote without one" {
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git/"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git/ is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]]
}

@test "--check counts a local repository and its .git directory as one repository" {
    # A strip of trailing slashes ahead of the .git suffix alone would read 'X/.git' as 'X/', so this
    # pins the strip after the suffix.
    git -C "$REPO" remote add mirror "$TEST_DIR/work"
    git -C "$REPO" remote set-url origin "$TEST_DIR/work/.git"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/work/.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/work)"* ]]
}

@test "--check compares a remote whose name starts with a dash or a space" {
    # git accepts both names ('remote add --', and a config section). Without the -- get-url reads a
    # dash-led name as an option, and without IFS= read trims a space-led one, so neither is compared.
    # '-mirror' shares origin's repository by its fetch url and '-pusher' by its push url only, one
    # for each get-url call.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add -- -mirror "$FORK"
    git -C "$REPO" remote add -- -pusher "$TEST_DIR/elsewhere.git"
    git -C "$REPO" remote set-url --push -- -pusher "$FORK"
    git -C "$REPO" config "remote. mirror.url" "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"is the same repository as remote '-mirror' (fetch url $FORK)"* ]]
    [[ "$output" == *"is the same repository as remote '-pusher' (push url $FORK)"* ]]
    [[ "$output" == *"is the same repository as remote ' mirror' (fetch url $FORK)"* ]]
}

@test "--check names the url to replace when origin carries several urls, and following the steps clears it" {
    # git refuses a plain 'set-url origin <url>' on a remote with several urls; naming the url to
    # replace is the form it accepts. Never configured, so a push goes to both of origin's urls, and a
    # rerun now would move every push onto the other remote's repository. Each step is followed
    # literally, and none of them sends a push there.
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    git -C "$REPO" config --add remote.origin.url "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]]
    [[ "$output" == *"a push to origin goes to $TEST_DIR/mirror.git, $FORK. "* ]]
    [[ "$output" == *"(git remote set-url origin <your-fork-url> <that-url>, which replaces only that one of origin's urls, then git remote set-url --push origin <your-fork-url>), then run scripts/fork-remotes.sh"* ]]
    [[ "$output" != *"Run scripts/fork-remotes.sh to fix."* ]]
    git -C "$REPO" remote set-url origin "$FORK" "$TEST_DIR/mirror.git"
    [[ "$(git -C "$REPO" remote get-url --push --all origin)" != *"$TEST_DIR/mirror.git"* ]]
    git -C "$REPO" remote set-url --push origin "$FORK"
    [[ "$(git -C "$REPO" remote get-url --push --all origin)" != *"$TEST_DIR/mirror.git"* ]]
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" remote get-url --push --all origin)" = "$FORK" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check keeps the rerun line beside a fetch note when a rerun moves no push, and the rerun clears it" {
    # origin is right and upstream was added with the fork's url by mistake. The fetch note fires, but
    # a push to origin already goes only to its fetch url, so a rerun moves no push and fixes upstream.
    git -C "$REPO" remote add upstream "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote 'upstream' (fetch url $FORK)"* ]]
    [[ "$output" == *"a push to origin goes to $FORK. "* ]]
    [[ "$output" == *"Run scripts/fork-remotes.sh to fix."* ]]
    # the same once origin's push url spells the fork another way and origin carries a second url that
    # names another repository: the rerun line is judged by the repositories a push goes to, and that
    # url is not one of them while origin has a push url
    git -C "$REPO" remote set-url --push origin "$FORK/"
    git -C "$REPO" config --add remote.origin.url "$TEST_DIR/elsewhere.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"a push to origin goes to $FORK/. "* ]]
    [[ "$output" == *"Run scripts/fork-remotes.sh to fix."* ]]
    # and the first step names the url to replace, which origin's several urls need, push url or not
    [[ "$output" == *"(git remote set-url origin <your-fork-url> <that-url>, which replaces only that one of origin's urls, then"* ]]
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

# gh resolves a bare PR number (`gh pr view N`, `gh pr merge N` without -R) against a default
# repository it reads from git config: the remote carrying `gh-resolved = base`. With no such key
# and no terminal to ask on, a clone with both remotes reads the PROJECT's PR N, not the fork's; a
# script that merges by number would aim there. The guard sets the key on origin and --check reads
# it, the way it reads pushDefault. These tests set the key by hand on fixture clones only.

@test "--check fails when gh has no default repository for a bare PR number" {
    # A clone the guard configured before it learned about gh's default: every push guard is in
    # place and the key alone is missing.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config --unset remote.origin.gh-resolved || true
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"gh has no default repository"* ]]
}

@test "configuring makes origin gh's default repository and --check passes" {
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" config --get remote.origin.gh-resolved)" = "base" ]
    run git -C "$REPO" config --get remote.upstream.gh-resolved
    [ "$status" -ne 0 ]                              # only origin carries the key
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check fails when gh's default repository is upstream, and configuring moves it" {
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config --unset remote.origin.gh-resolved || true
    git -C "$REPO" config remote.upstream.gh-resolved base
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote.upstream.gh-resolved"* ]]
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" config --get remote.origin.gh-resolved)" = "base" ]
    run git -C "$REPO" config --get remote.upstream.gh-resolved
    [ "$status" -ne 0 ]                              # unset by configure
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check fails when upstream also carries the key, which gh reads before origin's" {
    # gh consults the remotes in its own order, upstream before origin, so a key on upstream shadows
    # origin's even when origin's is right. Verified against gh 2.97: both remotes resolved as base,
    # a bare PR number went to the project.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config remote.upstream.gh-resolved base
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote.upstream.gh-resolved"* ]]
}

@test "configuring collapses a doubled gh default on origin to one value" {
    # `git config --add` by hand leaves two values under remote.origin.gh-resolved (gh itself unsets
    # before it adds), and a plain `git config <key> <value>` then refuses to overwrite them. Set
    # mode must still finish, with exactly one value, and not stop after the push guards. The two
    # values are planted here, not left by a first run of set mode: a script that never writes the
    # key (the base) would otherwise see one value after the add and pass.
    git -C "$REPO" config --add remote.origin.gh-resolved base
    git -C "$REPO" config --add remote.origin.gh-resolved base
    [ "$(git -C "$REPO" config --get-all remote.origin.gh-resolved | wc -l)" -eq 2 ]
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]]
    [ "$(git -C "$REPO" config --get-all remote.origin.gh-resolved | wc -l)" -eq 1 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "configuring clears a doubled gh default on upstream, and --check names the remote and the count while it stands" {
    # a plain `git config --unset` refuses a key with two values, and the `|| true` after it swallowed
    # the refusal: the key survived a run that printed configured, and --check then failed with advice
    # (a rerun) that could not clear it. Set mode unsets every value now; --check, while the values
    # stand, says which remote carries them and how many.
    git -C "$REPO" config --add remote.upstream.gh-resolved base
    git -C "$REPO" config --add remote.upstream.gh-resolved base
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote 'upstream' carries gh's default-repository key"* ]]
    [[ "$output" == *"2 value(s)"* ]]
    [ "$(echo "$output" | grep -c "remote 'upstream' carries")" -eq 1 ]
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]]
    run git -C "$REPO" config --get-all remote.upstream.gh-resolved
    [ "$status" -ne 0 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
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

@test "it refuses a clone whose origin is the project with a slash after .git" {
    git -C "$REPO" remote set-url origin "$UP/"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]]
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
}

@test "running it twice changes nothing the second time" {
    "$REPO/scripts/fork-remotes.sh"
    before="$(git -C "$REPO" remote -v)"
    # The whole local config, not only the remotes: a second run must not add a second value under
    # any key it sets (pushDefault, gh-resolved) or drop anything it left in place the first time.
    config_before="$(git -C "$REPO" config --list --local)"
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" remote -v)" = "$before" ]
    [ "$(git -C "$REPO" config --list --local)" = "$config_before" ]
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
