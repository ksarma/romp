#!/usr/bin/env bats

# scripts/fork-remotes.sh and scripts/upstream-check.sh — the fork's guard rail.
# The thing under test is that a push can only ever reach the fork: `upstream`
# exists to fetch from and dies loudly if anyone pushes at it. Everything runs
# against local bare repos, and a url with a host names one that nothing
# contacts, so no test touches the network.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
NL=$'\n'

load git-hermetic

setup() {
    git_hermetic
    TEST_DIR="$(mktemp -d)"
    UP="$TEST_DIR/project.git"          # what we forked from
    FORK="$TEST_DIR/fork.git"           # our copy
    REPO="$TEST_DIR/clone"              # the working clone under test
    # The script reads the clone's top level physically (symlinks resolved, as git does), so a path it
    # prints, and a relative url it resolves, is under these: on macOS mktemp's directory sits behind a
    # symlink. QREPO is the top level as the commands it prints spell it.
    PTEST_DIR="$(cd "$TEST_DIR" && pwd -P)"
    PREPO="$PTEST_DIR/clone"
    QREPO="$(printf '%q' "$PREPO")"
    # The rerun line and the lines that say to run --check again name the script by its path in the
    # clone, quoted as the commands quote the top level, so they act on this clone wherever they are run.
    RERUN="Run $QREPO/scripts/fork-remotes.sh to fix."
    AGAIN="then run $QREPO/scripts/fork-remotes.sh --check again"
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

# A bare repository at $1, where a push can land, so a row can see where a push went.
bare() { git init -q --bare "$1"; }

# Set mode refuses this clone, says nothing was changed and names $1, and the clone's own config file
# is byte for byte what it was. It keeps its own output, so $output still holds the last `run`.
set_mode_refuses() {  # <text the refusal names>
    local before out rc=0
    before="$(cat "$REPO/.git/config")"
    out="$("$REPO/scripts/fork-remotes.sh" 2>&1)" || rc=$?
    [ "$rc" -ne 0 ] || return 1
    [[ "$out" == *"nothing was changed"* ]] || return 1
    [[ "$out" == *"$1"* ]] || return 1
    [ "$(cat "$REPO/.git/config")" = "$before" ] || return 1
}

# Follow the commands the last `run` printed, literally: each output line that is four spaces and
# 'git ', with <your-fork-url> replaced by the fork's url, run from the directory of another clone,
# which they must leave as it was (each names the clone it acts on). Every one must succeed, and there
# must be at least one.
follow_steps() {
    local line n=0 other="$TEST_DIR/other" before
    if [ ! -d "$other" ]; then
        git init -q "$other" || return 1
        git -C "$other" remote add origin "$TEST_DIR/other-origin.git" || return 1
    fi
    before="$(cat "$other/.git/config")"
    while IFS= read -r line; do
        case "$line" in "    git "*) ;; *) continue ;; esac
        line="${line#    }"
        line="${line//<your-fork-url>/$FORK}"
        (cd "$other" && eval "$line") || return 1
        n=$((n + 1))
    done <<<"$output"
    [ "$(cat "$other/.git/config")" = "$before" ] || return 1
    [ "$n" -gt 0 ]
}

# The last `run` of --check printed no command to follow and no rerun line, only the line that says to
# fix what the notes name and run --check again.
no_commands_no_rerun() {
    [[ "$output" != *"    git "* ]] || return 1
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || return 1
    [[ "$output" == *"Fix what the notes above name, $AGAIN"* ]] || return 1
}

# A value of origin's, a rule that rewrites one, or a setting that aims a bare push or a bare gh PR
# number away from origin, held outside the clone's own config file fails closed: --check fails and
# lists it, as $1 spells it (the key, the value and where it lives), with no command and no rerun line,
# and set mode refuses, naming it and changing nothing.
outside_refused() {  # <the listed line>
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ] || return 1
    [[ "$output" == *"held outside the clone's own config file"* ]] || return 1
    [[ "$output" == *"$NL    $1"* ]] || return 1
    no_commands_no_rerun || return 1
    set_mode_refuses "$NL    $1" || return 1
}

# A commit pushed to origin lands on the fork, and on none of the repositories named.
push_lands_on_fork_only() {  # <bare repository>...
    local head r
    echo "change" >> "$REPO/kernel.py"
    git -C "$REPO" commit -qam "a fork change" || return 1
    head="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" push -q origin main || return 1
    [ "$(git -C "$FORK" rev-parse main)" = "$head" ] || return 1
    for r in "$@"; do
        if git -C "$r" cat-file -e "$head^{commit}" 2>/dev/null; then return 1; fi
    done
}

# --check counts origin, set to $1, as the same repository as a remote 'mirror' at $2, and names both.
same_repository() {  # <origin url> <mirror url>
    git -C "$REPO" remote add mirror "$2"
    git -C "$REPO" remote set-url origin "$1"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ] || return 1
    [[ "$output" == *"origin's fetch url $1 is the same repository as remote 'mirror' (fetch url $2)"* ]] || return 1
}

# A commit pushed with a bare `git push` from main, which goes where remote.pushDefault or the branch's
# pushRemote sends it, lands on the fork, and on none of the repositories named.
bare_push_lands_on_fork_only() {  # <bare repository>...
    local head r
    echo "change" >> "$REPO/kernel.py"
    git -C "$REPO" commit -qam "a fork change" || return 1
    head="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" push -q || return 1
    [ "$(git -C "$FORK" rev-parse main)" = "$head" ] || return 1
    for r in "$@"; do
        if git -C "$r" cat-file -e "$head^{commit}" 2>/dev/null; then return 1; fi
    done
}

# Another clone of the fork, at $B, carrying its own copy of the script and never configured: run from
# its directory, a line that named the script by a path relative to the reader's directory would run
# that copy, on that clone.
other_clone() {
    B="$TEST_DIR/cloneB"
    if [ ! -d "$B" ]; then
        git clone -q "$FORK" "$B" || return 1
        mkdir -p "$B/scripts" || return 1
        cp "$ROMP_DIR/scripts/fork-remotes.sh" "$B/scripts/" || return 1
        chmod +x "$B/scripts/fork-remotes.sh" || return 1
    fi
}

# Run what a printed line names, as a reader would type it, from the other clone's directory: the
# command is the text between $2 and $3 on the first line of $1 that holds both. Its output and status
# replace the last `run`'s, and the other clone's config must be unchanged.
run_from_other() {  # <printed text> <text before the command> <text after it>
    local line cmd before
    line="$(printf '%s\n' "$1" | grep -F -- "$2" | grep -F -- "$3" | head -n 1)"
    [ -n "$line" ] || return 1
    cmd="${line#*"$2"}"; cmd="${cmd%%"$3"*}"
    before="$(cat "$B/.git/config")"
    run bash -c 'cd "$1" && eval "$2"' _ "$B" "$cmd"
    [ "$(cat "$B/.git/config")" = "$before" ]
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
    # project sends a bare push there while --check used to print the all-clear. That push url is also
    # the repository upstream fetches from, so origin shares a repository with upstream: set mode
    # refuses, --check gives no rerun line, and the commands it prints point origin back at the fork.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote set-url --push origin "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin PUSHES to $UP"* ]] || false
    [[ "$output" == *"origin's push url $UP is the same repository as remote 'upstream' (fetch url $UP): a push to origin goes to $UP. "* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "origin's push url $UP is the same repository as remote 'upstream'"
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

# origin set by mistake to the url of another remote the clone carries (another fork kept as a second
# remote, say) passes every check that compares origin with the project or with itself, and a fetch,
# a bare gh PR number and possibly every push would go to that repository. --check compares each of
# origin's urls (its first, any extra, and its push urls) with each url of every other remote, by
# repo_id and as git resolves them. Set mode refuses a clone in that state and changes nothing, so a
# row plants the mistake before configuring (and --check also names what configuring would have set)
# or after it. A row that follows the commands --check prints runs each one as printed, with the
# fork's url for <your-fork-url>, and ends with a real push that must land on the fork and nowhere
# else. The other remotes name local paths: bare repositories where a push could land, when it matters.

@test "--check fails when origin is the same repository as another remote's fetch url, naming both" {
    # Two spellings of one repository, a file:// url and a bare path: repo_id counts them equal.
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "file://$TEST_DIR/mirror.git"
    set_mode_refuses "origin's fetch url file://$TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url file://$TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    [[ "$output" == *"a push to origin goes to file://$TEST_DIR/mirror.git. "* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    [[ "$output" == *"$AGAIN"* ]] || false
    # the commands, then --check, which now asks for set mode, then set mode clear it
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" != *"is the same repository as"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "--check gives no rerun line when origin's fetch url moved after configuring, and says where pushes go" {
    # Configured on the fork, then origin's fetch url set to another remote's: the push url that
    # configuring set still names the fork. A rerun would copy the wrong fetch url onto the push url
    # and move pushes as well, so set mode refuses and the rerun line is withheld, though the push check
    # also fires.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    [[ "$output" == *"a push to origin goes to $FORK. "* ]] || false
    [[ "$output" == *"origin PUSHES to $FORK"* ]] || false        # a note a rerun would otherwise answer
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
}

@test "--check fails when origin is the same repository as another remote's push url" {
    # The other remote fetches from one repository and pushes to another, and origin is the one it
    # pushes to: a check that read only each remote's fetch url would pass this clone.
    git -C "$REPO" remote add mirror "$TEST_DIR/elsewhere.git"
    git -C "$REPO" remote set-url --push mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    set_mode_refuses "origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (push url $TEST_DIR/mirror.git)"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (push url $TEST_DIR/mirror.git)"* ]]
}

@test "--check fails when origin's second push url is another remote's repository, and its commands clear it" {
    # A push goes to every push url a remote carries. origin's first is the fork and its second the
    # other remote's repository, so every push lands there as well. The note lists both destinations,
    # and the commands remove both push urls whatever their spelling.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url --add --push origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's push url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git): a push to origin goes to $FORK, $TEST_DIR/mirror.git. "* ]] || false
    [[ "$output" == *"    git -C $QREPO config --unset-all remote.origin.pushurl"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "--check fails when a url of origin's after its first is another remote's repository, and its commands clear it" {
    # git fetches from a remote's first url only, but with no push url (and no pushInsteadOf rule
    # rewriting its urls) a push goes to every url it carries, so the second one is a push destination
    # and not a fetch url. Planted after configuring, with the push url that configuring set removed
    # again, so pushes follow the urls.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config --unset remote.origin.pushurl
    git -C "$REPO" config --add remote.origin.url "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's extra url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git): git fetches only from origin's first url, and a push to origin goes to $FORK, $TEST_DIR/mirror.git. "* ]] || false
    [[ "$output" != *"origin's fetch url"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "origin's extra url $TEST_DIR/mirror.git"
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "--check reads another remote's url after git's insteadOf rewrite" {
    # The other remote is written as an alias that url.<base>.insteadOf expands to origin's url. git
    # fetches and pushes the expanded url, so the check must compare that one, not the alias.
    git -C "$REPO" config "url.$TEST_DIR/.insteadOf" "short:"
    git -C "$REPO" remote add mirror "short:mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    set_mode_refuses "remote 'mirror' (fetch url $TEST_DIR/mirror.git)"
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
    [[ "$output" == *"origin PUSHES to"* ]] || false
    [[ "$output" != *"is the same repository as"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check passes with origin, a fetch-only upstream and a third remote of its own" {
    # The healthy shape: a third remote whose fetch and push urls are both repositories other than
    # origin's.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url --push mirror "$TEST_DIR/mirror-push.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"✗"* ]] || false
    # the all-clear names what --check verified and nothing more: the third remote stays pushable
    [[ "$output" == *"✓ upstream fetches from the project and is fetch-only; origin's urls, and any rule that rewrites them, are in the clone's own config file; every push to origin goes to the repository it fetches from, and origin shares no repository with another remote; remote.pushDefault is origin and no branch's pushRemote names another remote; origin is gh's only default repository"* ]]
}

@test "--check counts origin with a slash after .git as the same repository as a remote without one" {
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git/"
    set_mode_refuses "remote 'mirror'"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git/ is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]]
}

@test "--check counts a local repository and its .git directory as one repository" {
    # A strip of trailing slashes ahead of the .git suffix alone would read 'X/.git' as 'X/', so this
    # pins the strip after the suffix.
    git -C "$REPO" remote add mirror "$TEST_DIR/work"
    git -C "$REPO" remote set-url origin "$TEST_DIR/work/.git"
    set_mode_refuses "remote 'mirror'"
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
    [[ "$output" == *"is the same repository as remote '-mirror' (fetch url $FORK)"* ]] || false
    [[ "$output" == *"is the same repository as remote '-pusher' (push url $FORK)"* ]] || false
    [[ "$output" == *"is the same repository as remote ' mirror' (fetch url $FORK)"* ]]
}

@test "--check gives commands that clear an origin with several urls, the first another remote's" {
    # Never configured, so a push goes to both of origin's urls, and a rerun now would move every push
    # onto the other remote's repository. The commands remove both urls whatever their spelling and set
    # the fork's url; --check then asks for set mode, which completes the clone.
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    git -C "$REPO" config --add remote.origin.url "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    [[ "$output" == *"a push to origin goes to $TEST_DIR/mirror.git, $FORK. "* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
    follow_steps
    [ "$(git -C "$REPO" remote get-url --push --all origin)" = "$FORK" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "--check gives no rerun line when upstream was given the fork's url, and removing upstream clears it" {
    # origin is right and upstream was added with the fork's url by mistake. Set mode would point
    # upstream at the project here, but it cannot tell this clone from one where origin is the mistake
    # (the next row), so it refuses, and the note names removing the other remote as this case's fix.
    git -C "$REPO" remote add upstream "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote 'upstream' (fetch url $FORK)"* ]] || false
    [[ "$output" == *"Remove 'upstream' if it is a second name for your fork"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'upstream'"
    git -C "$REPO" remote remove upstream
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "set mode refuses an origin that names the same other repository as upstream, so --check cannot pass with origin wrong" {
    # origin and upstream both given another repository's url. A rerun would point upstream at the
    # project, after which nothing would compare origin with that repository and --check would pass
    # while origin still names it. Set mode refuses instead, and --check gives no rerun line.
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add upstream "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'upstream' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'upstream'"
}

@test "a clone whose path holds a space: the commands and the rerun line quote it so they run as printed, and a listing names a file by its path as it is" {
    REPO="$TEST_DIR/my clone"
    PREPO="$PTEST_DIR/my clone"
    git clone -q "$FORK" "$REPO"
    mkdir -p "$REPO/scripts"
    cp "$ROMP_DIR/scripts/fork-remotes.sh" "$REPO/scripts/"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"    git -C $(printf '%q' "$PREPO") config remote.origin.url <your-fork-url>"* ]] || false
    follow_steps
    [ "$(git -C "$REPO" remote get-url --all origin)" = "$FORK" ]
    # the rerun line names the script the same way, so it too runs as printed, here from another clone
    other_clone
    run "$REPO/scripts/fork-remotes.sh" --check
    [[ "$output" == *"Run $(printf '%q' "$PREPO")/scripts/fork-remotes.sh to fix."* ]] || false
    run_from_other "$output" "Run " " to fix."
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    # a listed value names its file by the path as it is, not quoted as for a command
    git -C "$REPO" config extensions.worktreeConfig true
    git -C "$REPO" config --worktree remote.origin.pushurl "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$NL    remote.origin.pushurl $FORK (in file:$PREPO/.git/config.worktree)"* ]] || false
}

@test "set mode's refusal line, the closing line and the rerun line name this clone's script, so they act on it from another clone" {
    # Each is run as printed from the directory of another clone of the fork that carries its own copy
    # of the script: named by a relative path, each would check or configure that clone instead.
    other_clone
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    cd "$B"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Run $QREPO/scripts/fork-remotes.sh --check for what to change."* ]] || false
    run_from_other "$output" "Run " " for what to change."
    [ "$status" -ne 0 ]
    [[ "$output" == *"is the same repository as remote 'mirror'"* ]] || false
    run_from_other "$output" "Fix what the notes above name, then run " " again"
    [ "$status" -ne 0 ]
    [[ "$output" == *"is the same repository as remote 'mirror'"* ]] || false
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    run_from_other "$output" "Run " " to fix."
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "the lines that say to remove a value where it lives name this clone's script, so --check again checks it from another clone" {
    # A url of origin's and a branch pushRemote naming another remote, both in a file this clone's
    # config includes, which the other clone does not
    other_clone
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    printf '[remote "origin"]\n\turl = %s\n[branch "main"]\n\tpushRemote = mirror\n' "$TEST_DIR/mirror.git" > "$TEST_DIR/a.inc"
    git -C "$REPO" config include.path "$TEST_DIR/a.inc"
    cd "$B"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    local printed="$output"
    run_from_other "$printed" "nor a command printed here can change them: remove each one where it lives, then run " " again"
    [ "$status" -ne 0 ]
    [[ "$output" == *"$NL    remote.origin.url $TEST_DIR/mirror.git (in file:$TEST_DIR/a.inc)"* ]] || false
    run_from_other "$printed" "where set mode cannot change them: remove each one where it lives, then run " " again"
    [ "$status" -ne 0 ]
    [[ "$output" == *"$NL    branch.main.pushremote mirror (in file:$TEST_DIR/a.inc)"* ]] || false
    rm "$TEST_DIR/a.inc"
    run_from_other "$printed" "Fix what the notes above name, then run " " again"
    [ "$status" -eq 0 ]
}

# The commands --check prints for a shared repository name no configured value, so no spelling can make
# one of them miss: each row below plants a layout where a command that named a url (an insteadOf
# alias, a regex metacharacter, a pushInsteadOf rewrite) would match nothing or the wrong value,
# follows the commands literally, and pushes.

@test "the commands clear an origin whose first url is an insteadOf alias for another remote's repository" {
    # origin's first url is written as an alias that url.<base>.insteadOf expands to the other remote's
    # repository, with the fork as its second url.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" config "url.$TEST_DIR/.insteadOf" "ex:"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config --unset-all remote.origin.url
    git -C "$REPO" config --add remote.origin.url "ex:mirror.git"
    git -C "$REPO" config --add remote.origin.url "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "the commands clear an origin push url that holds a regex metacharacter" {
    # git config matches a value it is given as a regular expression, where '+' is an operator, so a
    # command that named this url would match no value.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror+1.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror+1.git"
    git -C "$REPO" remote set-url --add --push origin "$TEST_DIR/mirror+1.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's push url $TEST_DIR/mirror+1.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror+1.git)"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror+1.git" "$UP"
}

@test "the commands clear an origin whose pushes a pushInsteadOf rule sends to another remote's repository" {
    # origin has no push url, and its second url is an alias that url.<base>.pushInsteadOf expands, for
    # pushes only, to the other remote's repository: git then pushes there and nowhere else. No
    # configured value spells that push url.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config "url.$TEST_DIR/.pushInsteadOf" "pshort:"
    git -C "$REPO" config --unset remote.origin.pushurl
    git -C "$REPO" config --add remote.origin.url "pshort:mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's push url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git): a push to origin goes to $TEST_DIR/mirror.git. "* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

# A rule that rewrites the fork's url itself, as the reader types it, for pushes: the commands end by
# setting that url as origin's push url, to which git applies no pushInsteadOf rule, so the push that
# follows them, before --check runs again, lands on the fork. Set as a url alone, the fork's url would
# push through the rule.

@test "the commands set a push url, so a pushInsteadOf rule in the clone's own config file on the fork's url cannot move pushes" {
    # Configured, then origin's url set to another remote's repository by mistake; a rule in the clone's
    # own config file rewrites the fork's url, for pushes, to that repository. The commands remove the
    # push url configuring set, which kept pushes on the fork.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config "url.$TEST_DIR/mirror.git.pushInsteadOf" "$FORK"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    [[ "$output" == *"these commands, which act on this clone from any directory, remove every url and push url origin has in the clone's own config file, then set your fork's url as its url and its push url. git applies no pushInsteadOf rule to a push url; an insteadOf rule that matches the url you type rewrites both."* ]] || false
    [[ "$output" == *"$NL    git -C $QREPO config remote.origin.url <your-fork-url>$NL    git -C $QREPO config remote.origin.pushurl <your-fork-url>$NL"* ]] || false
    set_mode_refuses "remote 'mirror'"
    follow_steps
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "the commands set a push url, so a pushInsteadOf rule in global config on the fork's url cannot move pushes, and --check then lists the rule" {
    # origin was configured while its url was spelled as an alias that a rule in the clone's own config
    # file expands to the fork, so the push url configuring set is that alias; then its url was set to
    # another remote's repository. A rule in global config rewrites the fork's url, as typed, for pushes.
    # It starts none of origin's values, so --check does not list it and prints the commands; once they
    # have set the fork's url, it does, and --check passes when the rule is removed.
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" config "url.$TEST_DIR/.insteadOf" "ex:"
    git -C "$REPO" remote set-url origin "ex:fork.git"
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global "url.$TEST_DIR/mirror.git.pushInsteadOf" "$FORK"
    git -C "$REPO" remote set-url origin "$TEST_DIR/mirror.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    [[ "$output" != *"held outside the clone's own config file"* ]] || false
    follow_steps
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
    outside_refused "url.$TEST_DIR/mirror.git.pushinsteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"
    git config --global --unset-all "url.$TEST_DIR/mirror.git.pushInsteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "the commands set a push url on a clone never configured, so a pushInsteadOf rule in its own config file on the fork's url cannot move pushes" {
    # origin is the fork, with no push url, and a rule in the clone's own config file sends every push to
    # the fork's url to another remote's repository. After the commands and a push, --check asks for set
    # mode, which completes the clone.
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config "url.$TEST_DIR/mirror.git.pushInsteadOf" "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's push url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git): a push to origin goes to $TEST_DIR/mirror.git. "* ]] || false
    set_mode_refuses "remote 'mirror'"
    follow_steps
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

# A url or push url of origin's, or an insteadOf or pushInsteadOf rule that rewrites one, held outside
# the clone's own config file (an included file, config.worktree, global config, the environment) is
# something neither set mode nor a printed command can change, and while it stands nothing can say
# where a push to origin would go once the clone is fixed. So it fails closed: --check lists each one
# with where it lives and prints no command and no rerun line, and set mode refuses, writing nothing.
# Each row plants one on a configured clone and then removes it where --check says it lives; --check
# then passes, at once or after the rerun it asks for.

@test "an included file ahead of the remote section holding origin's first url fails closed, with no commands beside a shared note" {
    # The include is read first, so its url is origin's first: the fetch url, shared with remote
    # 'mirror'. The commands would remove the clone's own push url, which keeps pushes on the fork.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    printf '[remote "origin"]\n\turl = %s\n' "$TEST_DIR/mirror.git" > "$TEST_DIR/origin.inc"
    { printf '[include]\n\tpath = %s\n' "$TEST_DIR/origin.inc"; cat "$REPO/.git/config"; } > "$TEST_DIR/config.new"
    mv "$TEST_DIR/config.new" "$REPO/.git/config"
    outside_refused "remote.origin.url $TEST_DIR/mirror.git (in file:$TEST_DIR/origin.inc)"
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror'"* ]] || false
    [[ "$output" == *"remove what the note on values held outside the clone's own config file lists, and --check then gives the commands"* ]] || false
    git config --file "$TEST_DIR/origin.inc" --unset-all remote.origin.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "an included file after the remote section holding a second url of origin's fails closed" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    printf '[remote "origin"]\n\turl = %s\n' "$TEST_DIR/mirror.git" > "$TEST_DIR/origin.inc"
    git -C "$REPO" config include.path "$TEST_DIR/origin.inc"
    outside_refused "remote.origin.url $TEST_DIR/mirror.git (in file:$TEST_DIR/origin.inc)"
    [[ "$output" == *"origin's extra url $TEST_DIR/mirror.git is the same repository as remote 'mirror'"* ]] || false
    git config --file "$TEST_DIR/origin.inc" --unset-all remote.origin.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a url of origin's in global config, naming a repository no remote names, fails closed, so set mode cannot copy it onto the push url" {
    # git reads global config first, so this url is origin's first. Its push url still names the fork,
    # so the push note alone fires: a rerun line here sent set mode to copy the global url onto the
    # push url, moving every push there.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/elsewhere.git"
    git config --global remote.origin.url "$TEST_DIR/elsewhere.git"
    outside_refused "remote.origin.url $TEST_DIR/elsewhere.git (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"origin PUSHES to $FORK, not the repository it fetches from ($TEST_DIR/elsewhere.git)"* ]] || false
    set_mode_refuses "held outside the clone's own config file, where set mode cannot change them, so what it writes could not decide where a push to origin goes:$NL    remote.origin.url $TEST_DIR/elsewhere.git"
    git config --global --unset-all remote.origin.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/elsewhere.git" "$UP"
}

@test "a url of origin's set by a GIT_CONFIG_COUNT pair fails closed, and the listing says it is set in the environment" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    # the floor's five pairs stay exported, and this adds a sixth
    export GIT_CONFIG_COUNT=6 GIT_CONFIG_KEY_5=remote.origin.url GIT_CONFIG_VALUE_5="$TEST_DIR/mirror.git"
    outside_refused "remote.origin.url $TEST_DIR/mirror.git (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS)"
    [[ "$output" != *"command line:"* ]] || false
    export GIT_CONFIG_COUNT=5
    unset GIT_CONFIG_KEY_5 GIT_CONFIG_VALUE_5
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a url of origin's in config.worktree fails closed" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config extensions.worktreeConfig true
    git -C "$REPO" config --worktree --add remote.origin.url "$TEST_DIR/mirror.git"
    outside_refused "remote.origin.url $TEST_DIR/mirror.git (in file:$PREPO/.git/config.worktree)"
    git -C "$REPO" config --worktree --unset-all remote.origin.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a pushInsteadOf rule in global config that matches the fork's url fails closed" {
    # With no push url of origin's, the rule sends every push to the other remote's repository; the
    # commands would remove origin's urls and set the fork's url, which the rule rewrites again.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config --unset-all remote.origin.pushurl
    git config --global "url.$TEST_DIR/mirror.git.pushInsteadOf" "$FORK"
    outside_refused "url.$TEST_DIR/mirror.git.pushinsteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"origin's push url $TEST_DIR/mirror.git is the same repository as remote 'mirror'"* ]] || false
    git config --global --unset-all "url.$TEST_DIR/mirror.git.pushInsteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "an insteadOf rule in global config that rewrites origin's url fails closed" {
    # The rule moves every url under the test directory, origin's fetch and push urls among them, to
    # another tree, where a push would land.
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$TEST_DIR/w"
    bare "$TEST_DIR/w/fork.git"
    git config --global "url.$TEST_DIR/w/.insteadOf" "$TEST_DIR/"
    outside_refused "url.$TEST_DIR/w/.insteadof $TEST_DIR/ (in file:$GIT_CONFIG_GLOBAL)"
    git config --global --unset-all "url.$TEST_DIR/w/.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/w/fork.git" "$UP"
}

@test "an insteadOf rule in global config that rewrites only origin's push url fails closed" {
    # origin's push url, in the clone's own config file, is an alias that only the global rule expands
    # to the fork; the rule starts none of origin's urls. Once the rule is gone the alias names no
    # repository, and a rerun of set mode replaces it.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config --replace-all remote.origin.pushurl "pushalias:fork.git"
    git config --global "url.$TEST_DIR/.insteadOf" "pushalias:"
    [ "$(git -C "$REPO" remote get-url --push origin)" = "$TEST_DIR/fork.git" ]
    outside_refused "url.$TEST_DIR/.insteadof pushalias: (in file:$GIT_CONFIG_GLOBAL)"
    git config --global --unset-all "url.$TEST_DIR/.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

@test "a push url of origin's in global config, another remote's repository, fails closed, and the push note says set mode cannot remove it" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global remote.origin.pushurl "$TEST_DIR/mirror.git"
    outside_refused "remote.origin.pushurl $TEST_DIR/mirror.git (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"origin PUSHES to $TEST_DIR/mirror.git, not the repository it fetches from ($FORK); a push to origin goes to $TEST_DIR/mirror.git, $FORK. Set mode cannot remove $TEST_DIR/mirror.git, held outside the clone's own config file"* ]] || false
    git config --global --unset-all remote.origin.pushurl
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a push url of origin's in global config gets no rerun line even beside a note a rerun fixes" {
    # remote.pushDefault unset is a note set mode fixes, but set mode refuses while the global push
    # url stands. Once it is removed, the rerun line comes back and set mode clears the rest.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config --unset remote.pushDefault
    git config --global remote.origin.pushurl "$TEST_DIR/elsewhere.git"
    outside_refused "remote.origin.pushurl $TEST_DIR/elsewhere.git (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"remote.pushDefault is unset"* ]] || false
    git config --global --unset-all remote.origin.pushurl
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "the push note says set mode cannot remove a push url only when the offending one is held outside the clone's own config file" {
    # The fork's url as a push url in global config, and a push url to another repository in the
    # clone's own: the offending one is the clone's own, which set mode would replace, so the push
    # note does not say it cannot. The global value still fails closed until it is removed.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/elsewhere.git"
    git config --global remote.origin.pushurl "$FORK"
    git -C "$REPO" config --replace-all remote.origin.pushurl "$TEST_DIR/elsewhere.git"
    outside_refused "remote.origin.pushurl $FORK (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"origin PUSHES to $TEST_DIR/elsewhere.git, not the repository it fetches from ($FORK); a push to origin goes to $FORK, $TEST_DIR/elsewhere.git"* ]] || false
    [[ "$output" != *"Set mode cannot remove"* ]] || false
    git config --global --unset-all remote.origin.pushurl
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/elsewhere.git" "$UP"
}

# remote.pushDefault, a branch's pushRemote and gh-resolved decide where a bare push and a bare gh PR
# number go. One held outside the clone's own config file that aims away from origin is a value set
# mode cannot change, so a rerun line beside it would loop: it fails closed as origin's values do, and
# --check passes once it is removed where it lives.

@test "a branch pushRemote in global config naming another remote fails closed, and a bare push lands on the fork once it is removed" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global branch.main.pushRemote mirror
    outside_refused "branch.main.pushremote mirror (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"branch.main.pushremote is 'mirror': a bare push from that branch would not go to your fork"* ]] || false
    git config --global --unset-all branch.main.pushRemote
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "gh's default-repository key on upstream in global config fails closed" {
    "$REPO/scripts/fork-remotes.sh"
    git config --global remote.upstream.gh-resolved base
    outside_refused "remote.upstream.gh-resolved base (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"remote 'upstream' carries gh's default-repository key"* ]] || false
    git config --global --unset-all remote.upstream.gh-resolved
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "remote.pushDefault set to another remote by a GIT_CONFIG_COUNT pair fails closed, and a bare push lands on the fork once it is gone" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    # the floor's five pairs stay exported, and this adds a sixth, which git reads after the clone's own
    # config file, so it overrides the pushDefault that configuring set
    export GIT_CONFIG_COUNT=6 GIT_CONFIG_KEY_5=remote.pushDefault GIT_CONFIG_VALUE_5=mirror
    outside_refused "remote.pushdefault mirror (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS)"
    [[ "$output" == *"remote.pushDefault is 'mirror': a bare 'git push' would not go to your fork"* ]] || false
    export GIT_CONFIG_COUNT=5
    unset GIT_CONFIG_KEY_5 GIT_CONFIG_VALUE_5
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "those settings held outside the clone's own config file pass when they aim at origin, and set mode configures beside them" {
    # remote.pushDefault and a branch's pushRemote naming origin, and gh-resolved = base on origin, aim
    # nowhere else, so none is listed.
    git config --global remote.pushDefault origin
    git config --global branch.main.pushRemote origin
    git config --global remote.origin.gh-resolved base
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

# A remote git can push to but whose urls it cannot read could be origin's repository, so --check fails
# closed on it and set mode refuses. git remote lists remotes from every config scope, but get-url reads
# only a remote that the repository's config (.git/config, a file it includes, config.worktree) or a
# legacy file defines; git remote leaves out a remote that a legacy .git/remotes or .git/branches file
# defines, though get-url and a push read those.

@test "--check fails closed on a remote defined in global config, whose urls git cannot read" {
    # a blank legacy branches file of the same name, which git ignores, does not hide it
    "$REPO/scripts/fork-remotes.sh"
    git config --global remote.gmirror.url "$FORK"
    mkdir -p "$REPO/.git/branches"
    : > "$REPO/.git/branches/gmirror"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"git cannot read the urls of remote 'gmirror' ("*"No such remote"*"): a remote that only global or system config, or the environment (GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS), defines reads this way"* ]] || false
    [[ "$output" == *"set mode does not change remotes defined there: remove it where it is defined (git -C $QREPO config --show-origin --get-regexp '^remote\.' lists where"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "git cannot read the urls of remote 'gmirror'"
}

@test "--check fails closed on a remote defined by a GIT_CONFIG_COUNT pair, with no rerun line beside notes a rerun fixes" {
    # Never configured, so --check also names what set mode would set; set mode refuses here, so the
    # rerun line stays out all the same.
    # the floor's five pairs stay exported, and this adds a sixth
    export GIT_CONFIG_COUNT=6 GIT_CONFIG_KEY_5=remote.cmirror.url GIT_CONFIG_VALUE_5="$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"git cannot read the urls of remote 'cmirror' ("*"No such remote"*")"* ]] || false
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "git cannot read the urls of remote 'cmirror'"
}

@test "--check compares a remote that a legacy .git/remotes file defines, and names the file to delete" {
    # git remote remove leaves a legacy file in place, so the note names the file
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$REPO/.git/remotes"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/legacy"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote 'legacy' (fetch url $FORK)"* ]] || false
    [[ "$output" == *"Remove 'legacy' if it is a second name for your fork (delete $PREPO/.git/remotes/legacy, which defines it)"* ]] || false
    set_mode_refuses "remote 'legacy'"
    rm "$REPO/.git/remotes/legacy"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check compares a remote that a legacy .git/branches file defines, and names the file to delete" {
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$REPO/.git/branches"
    printf '%s\n' "$FORK" > "$REPO/.git/branches/legacy2"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote 'legacy2' (fetch url $FORK)"* ]] || false
    [[ "$output" == *"Remove 'legacy2' if it is a second name for your fork (delete $PREPO/.git/branches/legacy2, which defines it)"* ]] || false
    set_mode_refuses "remote 'legacy2'"
    rm "$REPO/.git/branches/legacy2"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check compares remotes that legacy files whose names start with a dot define" {
    # git takes any name with no slash, other than . and .., as a remote's name, so it reads these files
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$REPO/.git/remotes"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/.hidden"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/..twodots"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"is the same repository as remote '.hidden' (fetch url $FORK)"* ]] || false
    [[ "$output" == *"is the same repository as remote '..twodots' (fetch url $FORK)"* ]]
}

@test "--check names a remote once when both git config and a legacy file define it" {
    # git reads the legacy file only for a remote that config gives no url, and the name is compared once
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$FORK"
    mkdir -p "$REPO/.git/remotes"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/mirror"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [ "$(grep -c "is the same repository as remote 'mirror'" <<<"$output")" -eq 1 ]
    # config defines it, so the note names no legacy file to delete
    [[ "$output" != *"(delete "* ]] || false
}

@test "--check passes legacy remotes that name other repositories" {
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$REPO/.git/remotes" "$REPO/.git/branches"
    printf 'URL: %s\n' "$TEST_DIR/elsewhere.git" > "$REPO/.git/remotes/other"
    printf '%s\n' "$TEST_DIR/elsewhere2.git" > "$REPO/.git/branches/other2"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check passes, and set mode configures, a clone with empty and blank legacy files, which name no remote" {
    # git ignores a branches file whose first line is blank (get-url and a push say there is no such
    # remote), and reads a remotes file with no URL line as a remote whose url is its own name.
    mkdir -p "$REPO/.git/remotes" "$REPO/.git/branches"
    : > "$REPO/.git/branches/empty"
    printf ' \t\n%s\n' "$FORK" > "$REPO/.git/branches/blank"
    : > "$REPO/.git/remotes/emptyr"
    printf '  \n' > "$REPO/.git/remotes/blankr"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check fails closed on legacy files git cannot read, naming each file" {
    # an unreadable branches file is not taken for a blank one, which git ignores
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$REPO/.git/remotes" "$REPO/.git/branches"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/locked"
    printf '%s\n' "$FORK" > "$REPO/.git/branches/locked2"
    chmod 000 "$REPO/.git/remotes/locked" "$REPO/.git/branches/locked2"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"git cannot read the urls of remote 'locked' ("*"Permission denied"*"): the legacy file $PREPO/.git/remotes/locked defines it, and git reads no url from that file"* ]] || false
    [[ "$output" == *"git cannot read the urls of remote 'locked2' ("*"Permission denied"*"): the legacy file $PREPO/.git/branches/locked2 defines it, and git reads no url from that file"* ]] || false
    [[ "$output" != *"global or system config"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "git cannot read the urls of remote 'locked'"
    rm -f "$REPO/.git/remotes/locked" "$REPO/.git/branches/locked2"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

# Every push destination: a push goes to each push url a remote carries, and when it has none, to each
# of its urls (or, when a pushInsteadOf rule rewrites any of them, to the rewritten urls only), so
# --check reads them all, as get-url --push prints them, for origin and for upstream.

@test "--check fails when origin's second push url is a repository no remote names, and a rerun clears it" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/elsewhere.git"
    git -C "$REPO" remote set-url --add --push origin "$TEST_DIR/elsewhere.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin PUSHES to $TEST_DIR/elsewhere.git, not the repository it fetches from ($FORK); a push to origin goes to $FORK, $TEST_DIR/elsewhere.git"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/elsewhere.git" "$UP"
}

@test "--check fails when origin, with no push url, carries a second url no remote names, and a rerun clears it" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/elsewhere.git"
    git -C "$REPO" config --unset remote.origin.pushurl
    git -C "$REPO" config --add remote.origin.url "$TEST_DIR/elsewhere.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin PUSHES to $TEST_DIR/elsewhere.git, not the repository it fetches from ($FORK); a push to origin goes to $FORK, $TEST_DIR/elsewhere.git"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/elsewhere.git" "$UP"
}

@test "--check catches a second push url on upstream, and configuring clears it" {
    # upstream's first push url is the sentinel, but a push goes to every push url, so a second one at
    # the project lands there. Set mode replaces every push url upstream carries with the sentinel.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote set-url --add --push upstream "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"upstream is PUSHABLE ($UP)"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" remote get-url --push --all upstream)" = "no-push://upstream-is-fetch-only" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an upstream with two urls, the first another repository, is cleared by the rerun --check asks for" {
    # git remote set-url refuses a remote with several urls, which stopped set mode before it wrote
    # anything, so --check asked for the same rerun every time; set mode replaces every url upstream
    # carries.
    git -C "$REPO" remote add upstream "$TEST_DIR/elsewhere.git"
    git -C "$REPO" config --add remote.upstream.url "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"upstream fetches from $TEST_DIR/elsewhere.git, expected $UP"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" remote get-url --all upstream)" = "$UP" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

# repo_id reads each of git's documented url forms of one repository as one id (see its comment). The
# remotes here name hosts nothing contacts: --check compares urls and fetches nothing.

@test "--check reads the scp form without a user as the ssh url with the same path, as a forge serves them" {
    same_repository "example.invalid:someone/romp.git" "ssh://example.invalid/someone/romp.git"
}

@test "--check counts the scp form with an absolute path as the ssh url of the same repository" {
    same_repository "git@example.invalid:/srv/romp.git" "ssh://example.invalid/srv/romp.git"
}

@test "--check counts an https url with port 443 as the same repository as one without" {
    same_repository "https://example.invalid:443/someone/romp.git" "https://example.invalid/someone/romp"
}

@test "--check counts an http url with port 80 as the same repository as one without" {
    same_repository "http://example.invalid:80/someone/romp.git" "http://example.invalid/someone/romp.git"
}

@test "--check counts an ssh url with port 22 as the scp form of the same repository" {
    same_repository "ssh://git@example.invalid:22/someone/romp.git" "git@example.invalid:someone/romp.git"
}

@test "--check counts git+ssh and ssh+git urls with port 22 as the scp form of the same repository" {
    git -C "$REPO" remote add m1 "git+ssh://git@example.invalid:22/someone/romp.git"
    git -C "$REPO" remote add m2 "ssh+git://example.invalid:22/someone/romp.git"
    git -C "$REPO" remote set-url origin "git@example.invalid:someone/romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"is the same repository as remote 'm1' (fetch url git+ssh://git@example.invalid:22/someone/romp.git)"* ]] || false
    [[ "$output" == *"is the same repository as remote 'm2' (fetch url ssh+git://example.invalid:22/someone/romp.git)"* ]]
}

@test "--check counts a git url with port 9418 as the same repository as one without" {
    same_repository "git://example.invalid:9418/someone/romp.git" "git://example.invalid/someone/romp.git"
}

@test "--check counts a relative local path as the path it names from the clone's top level" {
    same_repository "$PTEST_DIR/mirror.git" "../mirror.git"
}

@test "--check counts a local path that starts with ./ as the path it names from the clone's top level" {
    same_repository "$PREPO/mirror.git" "./mirror.git"
}

@test "--check counts a file:// url with a .. segment as the path it names" {
    same_repository "file://$TEST_DIR/sub/../mirror.git" "$TEST_DIR/mirror.git"
}

@test "--check reads a difference in case as a different repository: X.GIT is not X, and Someone is not someone" {
    # Nothing is lowercased (see repo_id's comment): a forge strips only a lowercase .git suffix, so
    # romp.GIT names another repository there, and a case difference elsewhere reads as another
    # repository too. Each spelling is compared on its own, so a match on one cannot hide the other.
    git -C "$REPO" remote set-url origin "https://example.invalid/someone/romp.git"
    git -C "$REPO" remote add mirror "https://example.invalid/someone/romp.GIT"
    run "$REPO/scripts/fork-remotes.sh" --check
    [[ "$output" == *"fork-remotes: checking"* ]] || false
    [[ "$output" != *"is the same repository as"* ]] || false
    git -C "$REPO" remote set-url mirror "https://example.invalid/Someone/romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [[ "$output" == *"fork-remotes: checking"* ]] || false
    [[ "$output" != *"is the same repository as"* ]] || false
    git -C "$REPO" remote set-url mirror "https://EXAMPLE.invalid/someone/romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [[ "$output" == *"fork-remotes: checking"* ]] || false
    [[ "$output" != *"is the same repository as"* ]] || false
}

@test "--check resolves a relative local url against the clone's physical top level when reached through a symlink" {
    # git resolves a relative url from the top level it reaches with symlinks resolved, so '../fork.git'
    # from this clone names the fork wherever the script was called through
    mkdir -p "$TEST_DIR/via"
    ln -s "$PREPO" "$TEST_DIR/via/link"
    git -C "$REPO" remote set-url origin "$PTEST_DIR/fork.git"
    git -C "$REPO" remote add mirror "../fork.git"
    run "$TEST_DIR/via/link/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $PTEST_DIR/fork.git is the same repository as remote 'mirror' (fetch url ../fork.git)"* ]] || false
    run "$TEST_DIR/via/link/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"nothing was changed"* ]] || false
}

# The two ways git rewrites a push url: pushInsteadOf for a push url it derives from a url, insteadOf
# for one set explicitly. And set mode's own push url write, which a second rewrite must not move.

@test "--check reads another remote's push url after git's pushInsteadOf rewrite" {
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/elsewhere.git"
    git -C "$REPO" config "url.$FORK.pushInsteadOf" "$TEST_DIR/elsewhere.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote 'mirror' (push url $FORK)"* ]]
}

@test "--check reads another remote's explicit push url after git's insteadOf rewrite" {
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config "url.$TEST_DIR/.insteadOf" "short:"
    git -C "$REPO" remote add mirror "$TEST_DIR/elsewhere.git"
    git -C "$REPO" remote set-url --push mirror "short:fork.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote 'mirror' (push url $FORK)"* ]]
}

@test "set mode copies origin's raw url onto its push url, so chained insteadOf rules leave pushes on the fork" {
    # url.<w>/me/.insteadOf ex: and url.<w>/other/.insteadOf <w>/me/: origin's url ex:romp.git reads as
    # <w>/me/romp.git, the fork of this row. Written back as a push url in that resolved form, git would
    # rewrite it again, to <w>/other/romp.git, another remote's repository; the raw value goes through
    # one rewrite, as the fetch url does. An upstream made pushable gives --check a note a rerun fixes.
    local w="$TEST_DIR/w"
    mkdir -p "$w/me" "$w/other"
    bare "$w/me/romp.git"
    bare "$w/other/romp.git"
    FORK="$w/me/romp.git"
    git -C "$REPO" config "url.$w/me/.insteadOf" "ex:"
    git -C "$REPO" config "url.$w/other/.insteadOf" "$w/me/"
    git -C "$REPO" remote set-url origin "ex:romp.git"
    git -C "$REPO" remote set-url --push origin "ex:romp.git"
    git -C "$REPO" remote add mirror "$w/other/romp.git"
    git -C "$REPO" remote add upstream "$UP"
    git -C "$REPO" remote set-url --push upstream "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" != *"is the same repository as"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" config --get remote.origin.pushurl)" = "ex:romp.git" ]
    [ "$(git -C "$REPO" remote get-url --push origin)" = "$w/me/romp.git" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$w/other/romp.git" "$UP"
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

@test "--check fails when remote.pushDefault is unset, and configuring sets it" {
    # Without remote.pushDefault a bare push from a branch goes to the remote the branch tracks, which
    # need not be origin. Set mode sets it, so the rerun line is honest.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config --unset remote.pushDefault
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote.pushDefault is unset: a bare 'git push' from a branch that tracks another remote goes there, not to your fork"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" config --get remote.pushDefault)" = "origin" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check reads remote.pushDefault exactly, so origin with a trailing newline is another remote" {
    # git takes the value whole, and a legacy .git/remotes file of that name then receives every bare
    # push, here the project's repository. A reader that dropped trailing newlines would read origin.
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$REPO/.git/remotes"
    printf 'URL: %s\n' "$UP" > "$REPO/.git/remotes/origin"$'\n'
    git -C "$REPO" config remote.pushDefault "origin"$'\n'
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote.pushDefault is 'origin"$'\n'"': a bare 'git push' would not go to your fork"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "--check reads a branch.pushRemote of ' origin' as another remote, and configuring clears it" {
    # A remote may be named ' origin' (a config section, by hand). A reader that trimmed the value
    # would take that pushRemote for origin while a bare push from the branch goes to ' origin'.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config "remote. origin.url" "$UP"
    git -C "$REPO" config branch.main.pushRemote " origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"branch.main.pushremote is ' origin': a bare push from that branch would not go to your fork"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run git -C "$REPO" config --get branch.main.pushRemote
    [ "$status" -ne 0 ]                              # unset by configure
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
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

@test "--check names a remote whose name holds a space when it carries gh's key, and configuring clears it" {
    # The key is read whole, with -z: split on whitespace it named a key git refused, and --check
    # stopped on git's error with no note.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config "remote.my mirror.url" "$TEST_DIR/elsewhere.git"
    git -C "$REPO" config "remote.my mirror.gh-resolved" base
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote 'my mirror' carries gh's default-repository key (remote.my mirror.gh-resolved: 1 value(s), 'base')"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run git -C "$REPO" config --get "remote.my mirror.gh-resolved"
    [ "$status" -ne 0 ]                              # unset by configure
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
    [[ "$output" == *"points at the upstream project"* ]] || false
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
}

@test "it refuses an origin that names the project's .git directory by its checkout with a slash" {
    # ROMP_UPSTREAM_URL names the .git directory of a checkout in a directory called proj.git, and
    # origin names that checkout with a trailing slash: one repository. The suffix strip runs until no
    # slash or .git is left, so both read alike.
    export ROMP_UPSTREAM_URL="$TEST_DIR/proj.git/.git"
    git -C "$REPO" remote set-url origin "$TEST_DIR/proj.git/"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]] || false
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
}

@test "the refusal of an origin that is the project gives commands that clear it, whatever its urls" {
    # origin carries the project's url first and the fork's second: a set-url of one value refuses a
    # remote with several, and the commands depend on no spelling
    git -C "$REPO" remote set-url origin "$UP"
    git -C "$REPO" config --add remote.origin.url "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]] || false
    [[ "$output" == *"then set your fork's url as its url and its push url:$NL    git -C $QREPO config --unset-all remote.origin.url$NL"* ]] || false
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

@test "the refusal of an origin that is the project lists a url held in an included file and gives no commands" {
    printf '[remote "origin"]\n\turl = %s\n' "$UP" > "$TEST_DIR/origin.inc"
    { printf '[include]\n\tpath = %s\n' "$TEST_DIR/origin.inc"; cat "$REPO/.git/config"; } > "$TEST_DIR/config.new"
    mv "$TEST_DIR/config.new" "$REPO/.git/config"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]] || false
    [[ "$output" == *"$NL    remote.origin.url $UP (in file:$TEST_DIR/origin.inc)"* ]] || false
    [[ "$output" != *"    git "* ]] || false
    # the line names this clone's script: run as printed from another clone, it checks this one
    other_clone
    run_from_other "$output" "Remove each one where it lives, then run " " again"
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]] || false
    git config --file "$TEST_DIR/origin.inc" --unset-all remote.origin.url
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

@test "--check names the legacy file that alone defines origin, gives no rerun line, and its command clears it" {
    # Set mode refuses here (there is no url in config to copy onto the push url), so a rerun line would
    # send the reader to a refusal. The command sets origin's url in the clone's own config file, after
    # which git reads no legacy file for origin.
    git -C "$REPO" config --unset-all remote.origin.url
    mkdir -p "$REPO/.git/branches"
    printf '%s\n' "$FORK" > "$REPO/.git/branches/origin"
    # with a push url of origin's in global config too, the commands wait until it is removed
    git config --global remote.origin.pushurl "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's url is not in git config (the legacy file $PREPO/.git/branches/origin defines it), and set mode, which copies origin's url onto its push url, refuses to run: once the values held outside the clone's own config file are gone, --check gives the commands"* ]] || false
    no_commands_no_rerun
    git config --global --unset-all remote.origin.pushurl
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's url is not in git config (the legacy file $PREPO/.git/branches/origin defines it), and set mode, which copies origin's url onto its push url, refuses to run: set origin's url in the clone's own config file with the commands below"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    [[ "$output" == *"Fix what the notes above name, $AGAIN; set mode refuses to run while origin shares a repository with another remote, git cannot read a remote's urls, git config holds no url for origin, or one of these is held anywhere but the clone's own config file: a url of origin's, a rule that rewrites one, or a setting that aims a bare push or a bare gh PR number away from origin."* ]] || false
    set_mode_refuses "origin's url is not in git config"
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

@test "--check fails with git's own error when git cannot parse an included file" {
    printf '[[[\n' > "$TEST_DIR/bad.inc"
    git -C "$REPO" config include.path "$TEST_DIR/bad.inc"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 2 ]
    [[ "$output" == *"fork-remotes: git cannot read this clone: fatal: bad config line 1 in file $TEST_DIR/bad.inc"* ]] || false
    [[ "$output" != *"not a git clone"* ]] || false
}

@test "--check fails with git's own error on a remote url key written with no value" {
    printf '[remote "mirror"]\n\turl\n' >> "$REPO/.git/config"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 2 ]
    [[ "$output" == *"fork-remotes: git cannot read origin's url: "*"remote.mirror.url"* ]] || false
    [[ "$output" != *"has no 'origin' remote"* ]] || false
}

@test "set mode refuses an origin whose url only a legacy .git/remotes file holds, and changes nothing" {
    # Set mode copies origin's url as git config holds it onto its push url; with none in config there
    # is nothing to copy, so it says so rather than write an empty push url.
    git -C "$REPO" config --unset-all remote.origin.url
    mkdir -p "$REPO/.git/remotes"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/origin"
    [ "$(git -C "$REPO" remote get-url origin)" = "$FORK" ]
    set_mode_refuses "origin's url is not in git config"
}

@test "--check names both legacy files when both define origin" {
    git -C "$REPO" config --unset-all remote.origin.url
    mkdir -p "$REPO/.git/remotes" "$REPO/.git/branches"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/origin"
    printf '%s\n' "$FORK" > "$REPO/.git/branches/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's url is not in git config (the legacy files $PREPO/.git/remotes/origin and $PREPO/.git/branches/origin define it)"* ]] || false
    set_mode_refuses "(the legacy files $PREPO/.git/remotes/origin and $PREPO/.git/branches/origin define it)"
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
