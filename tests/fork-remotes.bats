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

# A value of origin's, a pushInsteadOf rule that matches one while origin has no push url, or a setting
# that aims a bare push or a bare gh PR number away from origin, held outside the clone's own config
# file fails closed: --check fails and lists it, as $1 spells it (the key, the value and where it
# lives), with no command and no rerun line, and set mode refuses, naming it and changing nothing.
outside_refused() {  # <the listed line>
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ] || return 1
    [[ "$output" == *"held outside the clone's own config file"* ]] || return 1
    [[ "$output" == *"$NL    $1"* ]] || return 1
    no_commands_no_rerun || return 1
    set_mode_refuses "$NL    $1" || return 1
}

# An empty url or push url value of any remote's, or an insteadOf or pushInsteadOf rule whose base is
# empty, fails closed, the same under every git: --check lists every one, as the arguments spell them
# (each the key and, for a rule, its value, or the legacy line, and where it lives), in the order git
# reads them, and nothing else, then either the commands or the closing line; it gives no rerun line and
# the same answer twice. Set mode refuses, listing them and nothing else, and changes nothing. The last
# `run` is the second --check.
empty_refused() {  # <listed line>...
    local l list="" first h
    for l in "$@"; do list="$list$NL    $l"; done
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ] || return 1
    h="fork-remotes: checking$NL  ✗ each of these is an empty url or push url value, or an insteadOf or pushInsteadOf rule whose base is empty, which rewrites a url it matches to an empty one: a newer git (2.55, say) reads an empty url value, and some of the urls such a rule rewrites to nothing, as clearing the urls read before it, and an older one (2.43, say) reads each as an empty url, so such a config can name different urls to different gits, and --check reads nothing further while one stands. Remove each one where it lives, $AGAIN$list$NL"
    [[ "$output" == "$h""These commands, "* ]] || [ "$output" = "$h""Fix what the notes above name, $AGAIN." ] || return 1
    [[ "$output" == *"$NL""Fix what the notes above name, $AGAIN." ]] || return 1
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || return 1
    first="$output"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$output" = "$first" ] || return 1
    set_mode_refuses "  Each of these is an empty url or push url value, or an insteadOf or pushInsteadOf rule whose base is empty, which rewrites a url it matches to an empty one: a newer git (2.55, say) reads an empty url value, and some of the urls such a rule rewrites to nothing, as clearing the urls read before it, and an older one (2.43, say) reads each as an empty url, so set mode cannot tell which urls git uses:$list$NL""Run " || return 1
}

# The last `run` printed, after the listing, the commands that remove what the clone's own config file
# holds under each key named (its empty values, or every value of a rule's key), each key quoted as the
# shell reads it, and nothing between them and the closing line.
empty_commands() {  # <key>...
    local k cmds=""
    for k in "$@"; do
        case "$k" in
            url..*) cmds="$cmds$NL    git -C $QREPO config --unset-all $k" ;;
            *) cmds="$cmds$NL    git -C $QREPO config --unset-all $(printf '%q' "$k") '^\$'" ;;
        esac
    done
    [[ "$output" == *"$NL""These commands, which act on this clone from any directory, remove each empty value and each rule above that the clone's own config file holds, there, and leave its other values:$cmds$NL""Fix what the notes above name, $AGAIN." ]] || return 1
}

# The last `run` printed no such commands: none of the entries listed is in the clone's own config file.
no_empty_commands() {
    [[ "$output" != *"These commands"* ]] || return 1
    [[ "$output" != *"    git "* ]] || return 1
}

# The last `run` lists $1 (a rule's key, its value and where it lives) first under the information
# beside its notes: a rule held outside the clone's own config file that fails nothing by itself.
rule_listed() {  # <the listed line>
    [[ "$output" == *"  For information: these rules, held outside the clone's own config file, match a url of origin's, and neither set mode nor a command printed here can change them. An insteadOf rule rewrites the urls it matches for fetches and pushes alike, and --check reads urls as rewritten; a pushInsteadOf rule rewrites nothing while origin has a push url:$NL    $1"* ]] || return 1
}

# An includeIf "onbranch:" or "hasconfig:remote.*.url:" entry that may change where a push goes once a
# branch switch or a remote write makes its condition hold fails closed: --check fails and names it, as
# $1 spells it (the entry, its path, where it lives, the file it names and what that file sets or git's
# error), with no rerun line, and set mode refuses, naming it and changing nothing.
cond_include_refused() {  # <the listed line>
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ] || return 1
    [[ "$output" == *"these includeIf \"onbranch:\" and \"hasconfig:remote.*.url:\" entries name a file that sets a remote.*, url.* or branch.*.pushRemote key, or that --check cannot read in full."* ]] || return 1
    [[ "$output" == *"$NL    $1"* ]] || return 1
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || return 1
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
    # A separately-set push url that aims at the project sends a bare push there while --check, reading
    # only origin's fetch url, used to print the all-clear. The refusal of an origin that is the project
    # reads every url of origin's, its push urls among them, and both modes refuse, changing nothing;
    # the commands it prints point origin back at the fork.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote set-url --push origin "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin points at the upstream project, not at your fork.$NL  origin = $FORK$NL  project = $UP$NL  origin's push url $UP is the project's repository$NL"* ]] || false
    [[ "$output" != *"origin's fetch url"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    local before; before="$(cat "$REPO/.git/config")"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's push url $UP is the project's repository"* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
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
    [[ "$output" != *"git remote remove does not reach"* ]] || false      # 'mirror' is the clone's own
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
    [[ "$output" == *"✓ upstream fetches from the project, as git resolves both urls, and is fetch-only; origin's urls, and any pushInsteadOf rule that matches one while origin has no push url, are in the clone's own config file, no remote's url or push url value is empty and no insteadOf or pushInsteadOf rule has an empty base, and no includeIf \"onbranch:\" or \"hasconfig:remote.*.url:\" entry names a file that sets a remote.*, url.* or branch.*.pushRemote key or that --check cannot read in full; every push to origin goes to the repository it fetches from, and origin shares no repository with another remote; the remote.pushDefault git uses is origin, and no branch's pushRemote that git uses names another remote; origin is gh's only default repository"* ]]
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

@test "a second name for the fork defined in an included file is listed with where it lives, which git remote remove cannot reach" {
    "$REPO/scripts/fork-remotes.sh"
    printf '[remote "dup"]\n\turl = %s\n\tpushurl = %s\n' "$FORK" "$TEST_DIR/elsewhere.git" > "$TEST_DIR/dup.inc"
    git -C "$REPO" config include.path "$TEST_DIR/dup.inc"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote 'dup' (fetch url $FORK): a fetch from origin and a bare gh PR number read that repository, and a push to origin goes to $FORK. Remove 'dup' if it is a second name for your fork; git remote remove does not reach its url and push url values held outside the clone's own config file, listed below, so remove each where it lives; if origin was set to that url by mistake, the commands below point it at your fork$NL    remote.dup.url $FORK (in file:$TEST_DIR/dup.inc)$NL    remote.dup.pushurl $TEST_DIR/elsewhere.git (in file:$TEST_DIR/dup.inc)$NL"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'dup'"
    # the section is not in the clone's own config file, so git refuses to remove it
    run git -C "$REPO" remote remove dup
    [ "$status" -ne 0 ]
    git config --file "$TEST_DIR/dup.inc" --remove-section remote.dup
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "a second name for the fork in config.worktree, and one whose section is the clone's own but whose url is in an included file, are listed with where each lives" {
    # git remote remove clears the second one's section and exits 0, but its url, in the included file,
    # leaves it a remote that shares origin's repository.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config extensions.worktreeConfig true
    git -C "$REPO" config --worktree remote.wdup.url "$FORK"
    git -C "$REPO" config remote.mdup.fetch '+refs/heads/*:refs/remotes/mdup/*'
    printf '[remote "mdup"]\n\turl = %s\n' "$FORK" > "$TEST_DIR/mdup.inc"
    git -C "$REPO" config include.path "$TEST_DIR/mdup.inc"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote 'wdup' (fetch url $FORK)"*"so remove each where it lives; if origin was set to that url by mistake, the commands below point it at your fork$NL    remote.wdup.url $FORK (in file:$PREPO/.git/config.worktree)$NL"* ]] || false
    [[ "$output" == *"remote 'mdup' (fetch url $FORK)"*"so remove each where it lives; if origin was set to that url by mistake, the commands below point it at your fork$NL    remote.mdup.url $FORK (in file:$TEST_DIR/mdup.inc)$NL"* ]] || false
    git -C "$REPO" remote remove mdup
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote 'mdup' (fetch url $FORK)"* ]] || false
    git config --file "$TEST_DIR/mdup.inc" --unset-all remote.mdup.url
    git -C "$REPO" config --worktree --unset-all remote.wdup.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
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

@test "set mode's refusal line, the closing line, the rerun line and set mode's last line name this clone's scripts, so they act on it from another clone" {
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
    # set mode's last line names this clone's upstream-check.sh too: run as printed from the other clone,
    # which has no copy of it, it reports on this one
    [[ "$output" == *"$NL""Check what the project has added since:  $QREPO/scripts/upstream-check.sh" ]] || false
    local uc="${output##*Check what the project has added since:  }"
    run bash -c 'cd "$1" && eval "$2"' _ "$B" "$uc"
    [ "$status" -eq 0 ]
    [[ "$output" == *"upstream-check: main is up to date with upstream/main"* ]] || false
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

@test "the commands set a push url, so a pushInsteadOf rule in global config on the fork's url cannot move pushes, and --check then passes beside the rule" {
    # origin was configured while its url was spelled as an alias that a rule in the clone's own config
    # file expands to the fork, so the push url configuring set is that alias; then its url was set to
    # another remote's repository. A rule in global config rewrites the fork's url, as typed, for pushes.
    # It starts none of origin's values, so --check does not list it and prints the commands. Once they
    # have set the fork's url as origin's push url too, the rule matches origin's values but rewrites
    # nothing, and --check passes with it in place.
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
    [[ "$output" != *"url.$TEST_DIR/mirror.git.pushinsteadof"* ]] || false
    [[ "$output" != *"For information"* ]] || false
    follow_steps
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
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

# A url or push url of origin's, or a pushInsteadOf rule that matches one while origin has no push url,
# held outside the clone's own config file (an included file, config.worktree, global config, the
# environment) is something neither set mode nor a printed command can change, and it decides where a
# push to origin goes. So it fails closed: --check lists each one with where it lives and prints no
# command and no rerun line, and set mode refuses, writing nothing. Each row plants one on a configured
# clone and then removes it where --check says it lives; --check then passes, at once or after the
# rerun it asks for.

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
    # With no push url of origin's, the rule sends every push to the other remote's repository: it
    # decides where a push to origin goes, from outside the clone's own config file.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config --unset-all remote.origin.pushurl
    git config --global "url.$TEST_DIR/mirror.git.pushInsteadOf" "$FORK"
    outside_refused "url.$TEST_DIR/mirror.git.pushinsteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"origin's push url $TEST_DIR/mirror.git is the same repository as remote 'mirror'"* ]] || false
    [[ "$output" == *"these urls of origin's, or pushInsteadOf rules that match one while origin has no push url, are held outside the clone's own config file (the one git config --local writes)"* ]] || false
    [[ "$output" != *"For information"* ]] || false
    [[ "$output" == *"remove each one where it lives (or, for a pushInsteadOf rule listed here, give origin a push url in the clone's own config file with git -C $QREPO config remote.origin.pushurl <your-fork-url>: git applies no pushInsteadOf rule to a push url, so the rule then rewrites nothing), $AGAIN$NL"* ]] || false
    set_mode_refuses "These urls of origin's, or pushInsteadOf rules that match one while origin has no push url, are held outside the clone's own config file, where set mode cannot change them"
    # the second way out the note names, followed as printed: the rule stays, and rewrites nothing
    local cmd="${output#*with git -C }"; cmd="git -C ${cmd%%: git applies no*}"
    cmd="${cmd//<your-fork-url>/$FORK}"
    (cd "$TEST_DIR" && eval "$cmd")
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
    git config --global --unset-all "url.$TEST_DIR/mirror.git.pushInsteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "a push url of origin's in global config, another remote's repository, fails closed, and the push note says set mode cannot remove it" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global remote.origin.pushurl "$TEST_DIR/mirror.git"
    outside_refused "remote.origin.pushurl $TEST_DIR/mirror.git (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"origin PUSHES to $TEST_DIR/mirror.git, not the repository it fetches from ($FORK); a push to origin goes to $TEST_DIR/mirror.git, $FORK. Set mode cannot remove $TEST_DIR/mirror.git (in file:$GIT_CONFIG_GLOBAL), held outside the clone's own config file"* ]] || false
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

@test "an empty push url value of origin's fails closed with where it lives, in global config or in the clone's own, where the command removes it" {
    # git 2.55 reads an empty push url as clearing the push urls read before it, and git 2.43 reads it as
    # an empty url, so the two gits push to different places from one config; both get this note, and set
    # mode refuses. First an empty push url in global config beside one to another repository in the
    # clone's own: no command, since none acts there. Then the fork's url as a push url in global config,
    # and an empty one and the other repository's in the clone's own: the command removes the empty one
    # there, and the global value then fails closed as a value of origin's held outside.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/elsewhere.git"
    git config --global remote.origin.pushurl ""
    git -C "$REPO" config --replace-all remote.origin.pushurl "$TEST_DIR/elsewhere.git"
    empty_refused "remote.origin.pushurl, an empty value (in file:$GIT_CONFIG_GLOBAL)"
    no_empty_commands
    git config --global remote.origin.pushurl "$FORK"
    git -C "$REPO" config --replace-all remote.origin.pushurl ""
    git -C "$REPO" config --add remote.origin.pushurl "$TEST_DIR/elsewhere.git"
    empty_refused "remote.origin.pushurl, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.origin.pushurl
    follow_steps
    [ "$(git -C "$REPO" config --local --get-all remote.origin.pushurl)" = "$TEST_DIR/elsewhere.git" ]
    outside_refused "remote.origin.pushurl $FORK (in file:$GIT_CONFIG_GLOBAL)"
    git config --global --unset-all remote.origin.pushurl
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin PUSHES to $TEST_DIR/elsewhere.git, not the repository it fetches from ($FORK); a push to origin goes to $TEST_DIR/elsewhere.git$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/elsewhere.git" "$UP"
}

# An insteadOf rule held outside the clone's own config file rewrites the urls it matches for fetches
# and pushes alike, and --check reads origin's urls as rewritten, so the rule decides nothing the other
# checks miss; a pushInsteadOf rule rewrites nothing while origin has a push url. Neither fails --check
# by itself: --check fails on what it finds in the rewritten urls, and lists such a rule beside a
# failing note as information, with where it lives. Set mode configures beside one.

@test "an insteadOf rule in global config that respells origin's urls as the same repository passes, and set mode configures beside it" {
    # A rule that rewrites a url to another spelling of the same repository (on a developer machine, an
    # https-to-ssh rewrite) changes nothing about where a push to origin goes. Never configured, so
    # --check first names what set mode sets, lists the rule beside those notes, and keeps the rerun
    # line, which configures the clone with the rule in place.
    git config --global "url.file://$TEST_DIR/.insteadOf" "$TEST_DIR/"
    [ "$(git -C "$REPO" remote get-url origin)" = "file://$TEST_DIR/fork.git" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    rule_listed "url.file://$TEST_DIR/.insteadof $TEST_DIR/ (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"For information"* ]] || false     # listed beside a failing note only
    push_lands_on_fork_only "$UP"
}

@test "an https-to-ssh insteadOf rule in global config passes beside an https origin" {
    # The common developer setup: the rule respells origin's url, and the push url set mode copies from
    # it, as the scp form of the same repository. --check compares urls and contacts no host.
    git -C "$REPO" remote set-url origin "https://example.invalid/someone/romp.git"
    git config --global "url.git@example.invalid:.insteadOf" "https://example.invalid/"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" remote get-url --push origin)" = "git@example.invalid:someone/romp.git" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an insteadOf rule in global config that rewrites origin's urls to another remote's repository fails on the shared repository, with the rule listed" {
    # The rule rewrites the fork's url, which is origin's url and push url, to the repository remote
    # 'mirror' names. --check reads origin's urls as rewritten and finds the shared repository; the
    # rule is listed beside that note, and is not itself a note. Once it is gone, --check passes.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global "url.$TEST_DIR/mirror.git.insteadOf" "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $TEST_DIR/mirror.git is the same repository as remote 'mirror' (fetch url $TEST_DIR/mirror.git)"* ]] || false
    rule_listed "url.$TEST_DIR/mirror.git.insteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"
    [ "$(grep -c "url.$TEST_DIR/mirror.git.insteadof" <<<"$output")" -eq 1 ]   # it matches two values
    [[ "$output" != *"are held outside the clone's own config file"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
    git config --global --unset-all "url.$TEST_DIR/mirror.git.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a rule in global config that rewrites another remote's url to the fork's repository is listed beside the shared note with where it lives, and removing it clears the note" {
    # mirror's url as its config holds it is mx:, which the rule rewrites to the fork's url; the note
    # names the rewritten url, and the rule says where that comes from. Then a pushInsteadOf rule on that
    # url, while mirror has no push url, rewrites its pushes alone.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "mx:"
    git config --global "url.$FORK.insteadOf" "mx:"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin's fetch url $FORK is the same repository as remote 'mirror' (fetch url $FORK): a fetch from origin and a bare gh PR number read that repository, and a push to origin goes to $FORK. Remove 'mirror' if it is a second name for your fork; git reads its url named above through the rules listed below, held outside the clone's own config file; if origin was set to that url by mistake, the commands below point it at your fork$NL    url.$FORK.insteadof mx: (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "remote 'mirror'"
    git config --global --unset-all "url.$FORK.insteadOf"
    git config --global "url.$FORK.pushInsteadOf" "mx:"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin's fetch url $FORK is the same repository as remote 'mirror' (push url $FORK): "*"$NL    url.$FORK.pushinsteadof mx: (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    # with a push url of its own, which an insteadOf rule rewrites, that rule is listed, and the
    # pushInsteadOf rule, which then rewrites nothing, is not
    git -C "$REPO" config remote.mirror.pushurl "mp:"
    git -C "$REPO" config --add remote.mirror.pushurl "mp:2"
    git config --global "url.$FORK.insteadOf" "mp:"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin's fetch url $FORK is the same repository as remote 'mirror' (push url $FORK): "*"$NL    url.$FORK.insteadof mp: (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [ "$(grep -c "insteadof mp: " <<<"$output")" -eq 1 ]
    [[ "$output" != *"pushinsteadof mx:"* ]] || false
    git config --global --unset-all "url.$FORK.pushInsteadOf"
    git config --global --unset-all "url.$FORK.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an insteadOf rule in global config that expands origin's push url alias to the fork passes, and once it is gone the rerun --check asks for replaces the alias" {
    # origin's push url, in the clone's own config file, is an alias that only the global rule expands,
    # to the fork: a push to origin lands where origin fetches from, so --check passes with the rule in
    # place. Once the rule is gone the alias names no repository, and a rerun of set mode replaces it.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config --replace-all remote.origin.pushurl "pushalias:fork.git"
    git config --global "url.$TEST_DIR/.insteadOf" "pushalias:"
    [ "$(git -C "$REPO" remote get-url --push origin)" = "$TEST_DIR/fork.git" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
    git config --global --unset-all "url.$TEST_DIR/.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin PUSHES to pushalias:fork.git"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

@test "a pushInsteadOf rule in global config that origin's push url makes inert passes, and beside a failing note it is listed with the rerun line kept" {
    # Configured, so origin has a push url, to which git applies no pushInsteadOf rule: the rule on the
    # fork's url rewrites nothing and a push lands on the fork. Beside a note a rerun fixes, the rule is
    # listed and the rerun line stays, as set mode configures beside it.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global "url.$TEST_DIR/mirror.git.pushInsteadOf" "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"For information"* ]] || false
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
    git -C "$REPO" config --unset remote.pushDefault
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote.pushDefault is unset"* ]] || false
    rule_listed "url.$TEST_DIR/mirror.git.pushinsteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "the refusal of an origin that a rule in global config rewrites to the project lists the rule beside the commands" {
    git config --global "url.$UP.insteadOf" "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]] || false
    [[ "$output" == *"  origin = $UP$NL"* ]] || false
    [[ "$output" == *"$NL    git -C $QREPO config remote.origin.url <your-fork-url>$NL"* ]] || false
    rule_listed "url.$UP.insteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"
    git config --global --unset-all "url.$UP.insteadOf"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

# An includeIf "onbranch:" entry has git read the file it names only on a branch the entry matches, and
# a "hasconfig:remote.*.url:" entry only while a remote has a url it matches, so a branch switch or a
# remote write (set mode's own among them) can bring in what that file sets, which no other check saw.
# An entry whose file sets a remote.*, url.* or branch.*.pushRemote key, includes another file (which
# --check does not follow), or exists but cannot be read fails closed, in whatever config the entry
# lives: --check names the entry, where it lives, the file it names and what that file sets or git's
# error, and gives no rerun line, and set mode refuses, writing nothing. An entry whose file sets none
# of those passes. The two conditions share one reader, so the rows on onbranch entries pin both.

@test "an onbranch include in the clone's own config file, by a relative path, whose file sets a push url of origin's fails from another branch" {
    # Never configured, so --check also names what set mode sets; set mode refuses while the entry
    # stands, so there is no rerun line until it is gone. On main git reads none of the file; on a
    # branch named release a push to origin would also go to the other repository.
    bare "$TEST_DIR/mirror.git"
    printf '[remote "origin"]\n\tpushurl = %s\n' "$TEST_DIR/mirror.git" > "$REPO/.git/release.inc"
    git -C "$REPO" config "includeIf.onbranch:release.path" release.inc
    [ "$(git -C "$REPO" remote get-url --push --all origin)" = "$FORK" ]
    git -C "$REPO" checkout -q -b release
    [ "$(git -C "$REPO" remote get-url --push --all origin)" = "$TEST_DIR/mirror.git" ]
    git -C "$REPO" checkout -q main
    cond_include_refused "includeif.onbranch:release.path release.inc (in file:$PREPO/.git/config) names $PREPO/.git/release.inc, which sets remote.origin.pushurl"
    [[ "$output" == *"✗ these includeIf \"onbranch:\" and \"hasconfig:remote.*.url:\" entries name a file that sets a remote.*, url.* or branch.*.pushRemote key, or that --check cannot read in full. git reads it only while the entry's condition holds (a branch it matches is checked out, or a remote has a url it matches), which a branch switch or a remote write, set mode's own among them, can change; there a file that sets one of those keys can change where a push goes, and one git cannot read stops git. --check reads config only as it stands and cannot see that, and set mode cannot change it: remove each entry where it lives, or change its file so that it sets none of those keys and --check can read it in full, $AGAIN$NL    includeif.onbranch:release.path"* ]] || false
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "These includeIf \"onbranch:\" and \"hasconfig:remote.*.url:\" entries name a file that sets a remote.*, url.* or branch.*.pushRemote key, or that --check cannot read in full. git reads it only while the entry's condition holds (a branch it matches is checked out, or a remote has a url it matches), which a branch switch or a remote write, set mode's own among them, can change; there a file that sets one of those keys can change where a push goes, and one git cannot read stops git. Set mode can neither see that from here nor change it:$NL    includeif.onbranch:release.path release.inc"
    git -C "$REPO" config --unset "includeIf.onbranch:release.path"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an onbranch include in global config, by a path relative to that file, whose file sets a branch pushRemote and a url rule fails" {
    # Each key is named once, whatever the file sets beside it.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    local gdir="${GIT_CONFIG_GLOBAL%/*}"
    printf '[branch "release"]\n\tpushRemote = mirror\n\tpushRemote = mirror\n[url "%s/"]\n\tinsteadOf = rel:\n[user]\n\tname = x\n' "$TEST_DIR" > "$gdir/rel.inc"
    git config --global "includeIf.onbranch:rel*.path" rel.inc
    cond_include_refused "includeif.onbranch:rel*.path rel.inc (in file:$GIT_CONFIG_GLOBAL) names $gdir/rel.inc, which sets branch.release.pushremote, url.$TEST_DIR/.insteadof"
    [[ "$output" == *", url.$TEST_DIR/.insteadof$NL"* ]] || false
    no_commands_no_rerun
    git config --global --unset "includeIf.onbranch:rel*.path"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an onbranch include whose file exists but git cannot read, that includes another file, or whose path git expands by a user's name fails closed" {
    # git stops on an include whose file exists but that it cannot read (a parse error, permissions).
    # It skips one whose file is missing, as it skips 'b' here, so that one is not listed: the next row
    # pins that it passes alone.
    "$REPO/scripts/fork-remotes.sh"
    printf '[user]\n\tname = x\n' > "$TEST_DIR/locked.inc"
    chmod 000 "$TEST_DIR/locked.inc"
    printf '[[[\n' > "$TEST_DIR/bad.inc"
    printf '[include]\n\tpath = inner.inc\n' > "$TEST_DIR/outer.inc"
    printf '[includeIf "onbranch:x"]\n\tpath = inner.inc\n' > "$TEST_DIR/outer2.inc"
    git -C "$REPO" config "includeIf.onbranch:a.path" "$TEST_DIR/locked.inc"
    git -C "$REPO" config "includeIf.onbranch:b.path" "$TEST_DIR/missing.inc"
    git -C "$REPO" config "includeIf.onbranch:c.path" "$TEST_DIR/outer.inc"
    git -C "$REPO" config "includeIf.onbranch:d.path" "$TEST_DIR/outer2.inc"
    git -C "$REPO" config "includeIf.onbranch:e.path" "$TEST_DIR/bad.inc"
    git -C "$REPO" config "includeIf.onbranch:f.path" "~nobody/f.inc"
    git -C "$REPO" config "includeIf.onbranch:g.path" "%(prefix)/g.inc"
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
    git -C "$REPO" config "includeIf.onbranch:h.path" "~"
    cond_include_refused "includeif.onbranch:a.path $TEST_DIR/locked.inc (in file:$PREPO/.git/config) names $TEST_DIR/locked.inc, which git cannot read: "
    [[ "$output" == *"names $TEST_DIR/locked.inc, which git cannot read: "*"Permission denied"* ]] || false
    [[ "$output" != *"onbranch:b.path"* ]] || false
    [[ "$output" == *"$NL    includeif.onbranch:c.path $TEST_DIR/outer.inc (in file:$PREPO/.git/config) names $TEST_DIR/outer.inc, which sets include.path$NL"* ]] || false
    [[ "$output" == *"$NL    includeif.onbranch:d.path $TEST_DIR/outer2.inc (in file:$PREPO/.git/config) names $TEST_DIR/outer2.inc, which sets includeif.onbranch:x.path$NL"* ]] || false
    [[ "$output" == *"$NL    includeif.onbranch:e.path $TEST_DIR/bad.inc (in file:$PREPO/.git/config) names $TEST_DIR/bad.inc, which git cannot read: fatal: bad config line 1 in file $TEST_DIR/bad.inc$NL"* ]] || false
    [[ "$output" == *"$NL    includeif.onbranch:f.path ~nobody/f.inc (in file:$PREPO/.git/config) names its file by ~name/ or %(prefix)/, which git expands and --check does not, so --check cannot read it$NL"* ]] || false
    [[ "$output" == *"$NL    includeif.onbranch:g.path %(prefix)/g.inc (in file:$PREPO/.git/config) names its file by ~name/"* ]] || false
    [[ "$output" == *"$NL    includeif.onbranch:h.path ~ (in file:$PREPO/.git/config) names $TEST_DIR/home, which git cannot read: "* ]] || false
    no_commands_no_rerun
    chmod 600 "$TEST_DIR/locked.inc"
    git -C "$REPO" config --remove-section "includeIf.onbranch:a"
    git -C "$REPO" config --remove-section "includeIf.onbranch:c"
    git -C "$REPO" config --remove-section "includeIf.onbranch:d"
    git -C "$REPO" config --remove-section "includeIf.onbranch:e"
    git -C "$REPO" config --remove-section "includeIf.onbranch:f"
    git -C "$REPO" config --remove-section "includeIf.onbranch:g"
    git -C "$REPO" config --remove-section "includeIf.onbranch:h"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an onbranch include whose file sets none of those keys passes, wherever it lives, and set mode configures beside it" {
    # One in the clone's own config file by a relative path, one in global config by a path under the
    # home directory; the first file sets a branch key other than pushRemote. An includeIf on a gitdir:
    # condition is read as git reads it now, whatever its file sets: here it does not hold. A file that
    # does not exist sets nothing (git skips it on a matching branch, as the probe on the release branch
    # shows): a missing file, a path through a file, a missing file under ~/.
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
    printf '[user]\n\tname = x\n[branch "release"]\n\tmerge = refs/heads/release\n' > "$REPO/.git/plain.inc"
    printf '[core]\n\tabbrev = 12\n' > "$HOME/plain.inc"
    printf '[remote "other"]\n\turl = %s\n' "$TEST_DIR/elsewhere.git" > "$TEST_DIR/gitdir.inc"
    git -C "$REPO" config "includeIf.onbranch:release.path" plain.inc
    git config --global "includeIf.onbranch:release.path" "~/plain.inc"
    git -C "$REPO" config "includeIf.gitdir:$TEST_DIR/nowhere/.path" "$TEST_DIR/gitdir.inc"
    git -C "$REPO" config --add "includeIf.onbranch:release.path" "$TEST_DIR/missing.inc"
    git -C "$REPO" config --add "includeIf.onbranch:release.path" "$REPO/.git/plain.inc/sub.inc"
    git -C "$REPO" config --add "includeIf.onbranch:release.path" "~/missing.inc"
    git -C "$REPO" checkout -q -b release
    git -C "$REPO" config --list >/dev/null
    git -C "$REPO" checkout -q main
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "a hasconfig include matching the project's url, whose file sets a url rule, fails closed before set mode's write of upstream's url makes git read it" {
    # The entry's condition holds once a remote has the project's url, which set mode writes; the rule
    # in its file would then move every push to origin onto another repository after set mode printed
    # configured. --check names the entry, and set mode refuses, writing nothing.
    bare "$TEST_DIR/mirror.git"
    printf '[url "%s"]\n\tinsteadOf = %s\n' "$TEST_DIR/mirror.git" "$FORK" > "$TEST_DIR/hc.inc"
    git config --global "includeIf.hasconfig:remote.*.url:$UP.path" "$TEST_DIR/hc.inc"
    [ "$(git -C "$REPO" remote get-url origin)" = "$FORK" ]
    cond_include_refused "includeif.hasconfig:remote.*.url:$UP.path $TEST_DIR/hc.inc (in file:$GIT_CONFIG_GLOBAL) names $TEST_DIR/hc.inc, which sets url.$TEST_DIR/mirror.git.insteadof"
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    no_commands_no_rerun
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
    # git reads the file once a remote has the project's url
    git -C "$REPO" remote add probe "$UP"
    [ "$(git -C "$REPO" remote get-url origin)" = "$TEST_DIR/mirror.git" ]
    git -C "$REPO" remote remove probe
    git config --global --unset "includeIf.hasconfig:remote.*.url:$UP.path"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a hasconfig include matching the project's url whose file sets none of those keys passes, and so does one spelled in other case, which git never reads" {
    # git matches the condition's prefix, hasconfig:remote.*.url:, as spelled, so an entry spelled
    # hasConfig: or with .URL: is a condition git never takes as holding, whatever its file sets.
    bare "$TEST_DIR/mirror.git"
    printf '[core]\n\tabbrev = 12\n' > "$TEST_DIR/hc.inc"
    printf '[url "%s"]\n\tinsteadOf = %s\n' "$TEST_DIR/mirror.git" "$FORK" > "$TEST_DIR/never.inc"
    git config --global "includeIf.hasconfig:remote.*.url:$UP.path" "$TEST_DIR/hc.inc"
    git config --global "includeIf.hasConfig:remote.*.url:$UP.path" "$TEST_DIR/never.inc"
    git config --global "includeIf.hasconfig:remote.*.URL:$UP.path" "$TEST_DIR/never.inc"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    [ "$(git -C "$REPO" config --get core.abbrev)" = 12 ]
    [ "$(git -C "$REPO" remote get-url origin)" = "$FORK" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

# remote.pushDefault, a branch's pushRemote and gh-resolved decide where a bare push and a bare gh PR
# number go. A value held outside the clone's own config file that aims away from origin, and that set
# mode's write cannot override, would make a rerun line beside it loop, so it fails closed as origin's
# values do, and --check passes once it is removed where it lives: a pushRemote held anywhere outside
# that file (set mode writes none), gh-resolved on a remote other than origin held anywhere outside it,
# and a pushDefault or origin's gh-resolved held in an included file, config.worktree or the
# environment, which git reads after that file. One of the last two in global or system config gets
# the rerun line instead, as the rows after these show.

@test "a branch pushRemote in global config naming another remote fails closed, and a bare push lands on the fork once it is removed" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global branch.main.pushRemote mirror
    outside_refused "branch.main.pushremote mirror (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"branch.main.pushremote is 'mirror' (in file:$GIT_CONFIG_GLOBAL): a bare push from that branch would not go to your fork"* ]] || false
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
    [[ "$output" == *"remote.pushDefault is 'mirror' (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS): a bare 'git push' would not go to your fork"* ]] || false
    export GIT_CONFIG_COUNT=5
    unset GIT_CONFIG_KEY_5 GIT_CONFIG_VALUE_5
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "those settings held outside the clone's own config file pass when they aim at origin, and set mode configures beside them" {
    # remote.pushDefault and a branch's pushRemote naming origin, and gh-resolved = base on origin, aim
    # nowhere else, so none is listed, whether set mode's write overrides it (global config) or it is
    # the value git uses (the environment). Beside a failing note, none is listed as information either.
    git config --global remote.pushDefault origin
    git config --global branch.main.pushRemote origin
    git config --global remote.origin.gh-resolved base
    # the floor's five pairs stay exported, and this adds a sixth
    export GIT_CONFIG_COUNT=6 GIT_CONFIG_KEY_5=remote.origin.gh-resolved GIT_CONFIG_VALUE_5=base
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    git -C "$REPO" remote set-url --push upstream "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"upstream is PUSHABLE ($UP)"* ]] || false
    [[ "$output" != *"For information"* ]] || false
    [[ "$output" != *"remote.origin.gh-resolved is"* ]] || false
}

# git uses the last value of remote.pushDefault, of a branch's pushRemote and of origin's gh-resolved in
# the order it reads config, so --check decides on that value. One held outside the clone's own config
# file that a later value overrides decides nothing: it passes, and is listed as information beside a
# failing note. One in global or system config that git uses is overridden by set mode's own write of
# pushDefault or origin's gh-resolved, so a rerun fixes it; set mode writes no pushRemote, so one there
# fails closed. gh-resolved on any other remote fails closed wherever it is held outside the clone's own
# config file, the only place set mode removes it from, whatever value git reads after it.

@test "remote.pushDefault in global config that the clone's own overrides passes, and is listed as information beside a failing note" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global remote.pushDefault mirror
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"For information"* ]] || false
    git -C "$REPO" config --unset remote.origin.gh-resolved
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"gh has no default repository"* ]] || false
    [[ "$output" == *"$NL  For information: these settings, held outside the clone's own config file, aim a bare push or a bare gh PR number away from origin, but git uses a value it reads after each:$NL    remote.pushdefault mirror (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [[ "$output" != *"remote.pushDefault is"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a fresh clone with remote.pushDefault in global config and origin's gh-resolved in system config aimed away is configured, as set mode's own write overrides both" {
    unset GIT_CONFIG_NOSYSTEM
    export GIT_CONFIG_SYSTEM="$TEST_DIR/system.gitconfig"
    git config --system remote.origin.gh-resolved someone/other
    git config --global remote.pushDefault mirror
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote.pushDefault is 'mirror' (in file:$GIT_CONFIG_GLOBAL): a bare 'git push' would not go to your fork"* ]] || false
    [[ "$output" == *"remote.origin.gh-resolved is 'someone/other' (in file:$TEST_DIR/system.gitconfig), not 'base'"* ]] || false
    [[ "$output" != *"where set mode cannot change them"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$UP"
}

@test "remote.pushDefault in a file the clone's own config includes after its own value fails closed, as it wins after set mode writes" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    printf '[remote]\n\tpushDefault = mirror\n' > "$TEST_DIR/pd.inc"
    git -C "$REPO" config include.path "$TEST_DIR/pd.inc"
    outside_refused "remote.pushdefault mirror (in file:$TEST_DIR/pd.inc)"
    [[ "$output" == *"remote.pushDefault is 'mirror' (in file:$TEST_DIR/pd.inc): a bare 'git push' would not go to your fork"* ]] || false
    git config --file "$TEST_DIR/pd.inc" --unset-all remote.pushDefault
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "remote.pushDefault and origin's gh-resolved in config.worktree fail closed, as git reads that file after the clone's own" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config extensions.worktreeConfig true
    git -C "$REPO" config --worktree remote.pushDefault mirror
    outside_refused "remote.pushdefault mirror (in file:$PREPO/.git/config.worktree)"
    [[ "$output" == *"remote.pushDefault is 'mirror' (in file:$PREPO/.git/config.worktree): a bare 'git push' would not go to your fork"* ]] || false
    git -C "$REPO" config --worktree --unset-all remote.pushDefault
    git -C "$REPO" config --worktree remote.origin.gh-resolved someone/other
    outside_refused "remote.origin.gh-resolved someone/other (in file:$PREPO/.git/config.worktree)"
    [[ "$output" == *"remote.origin.gh-resolved is 'someone/other' (in file:$PREPO/.git/config.worktree), not 'base'"* ]] || false
    git -C "$REPO" config --worktree --unset-all remote.origin.gh-resolved
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a branch pushRemote in global config that the clone's own names origin over passes, and set mode leaves the clone's own in place" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global branch.main.pushRemote mirror
    git -C "$REPO" config branch.main.pushRemote origin
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" config --local --get branch.main.pushRemote)" = origin ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "a branch pushRemote in the clone's own config file over one in global config that also names another remote fails closed, as a rerun would only expose the global one" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global branch.main.pushRemote mirror
    git -C "$REPO" config branch.main.pushRemote mirror
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"branch.main.pushremote is 'mirror': a bare push from that branch would not go to your fork"* ]] || false
    [[ "$output" == *"where set mode cannot change them: remove each one where it lives, $AGAIN$NL    branch.main.pushremote mirror (in file:$GIT_CONFIG_GLOBAL), which git uses once set mode removes the clone's own value$NL"* ]] || false
    no_commands_no_rerun
    [[ "$output" != *"For information"* ]] || false
    set_mode_refuses "branch.main.pushremote mirror (in file:$GIT_CONFIG_GLOBAL), which git uses once set mode removes the clone's own value"
    # the value git falls back to is the last one held elsewhere: origin in global config, read after the
    # system config's mirror, which is then listed as information
    unset GIT_CONFIG_NOSYSTEM
    export GIT_CONFIG_SYSTEM="$TEST_DIR/system.gitconfig"
    git config --system branch.main.pushRemote mirror
    git config --global --replace-all branch.main.pushRemote origin
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"branch.main.pushremote is 'mirror': a bare push"* ]] || false
    [[ "$output" == *"For information: these settings"*"$NL    branch.main.pushremote mirror (in file:$TEST_DIR/system.gitconfig)$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "the pushRemote git falls back to is the last one held outside the clone's own config file, never another of its own: two there over one in global config naming another remote fail closed" {
    # Set mode removes every value of the key from the clone's own config file, so its first value here,
    # origin, is not what git falls back to; the global value is.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global branch.main.pushRemote mirror
    git -C "$REPO" config branch.main.pushRemote origin
    git -C "$REPO" config --add branch.main.pushRemote mirror
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"branch.main.pushremote is 'mirror': a bare push from that branch would not go to your fork"* ]] || false
    [[ "$output" == *"where set mode cannot change them: remove each one where it lives, $AGAIN$NL    branch.main.pushremote mirror (in file:$GIT_CONFIG_GLOBAL), which git uses once set mode removes the clone's own value$NL"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "branch.main.pushremote mirror (in file:$GIT_CONFIG_GLOBAL), which git uses once set mode removes the clone's own value"
    git config --global --unset-all branch.main.pushRemote
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    bare_push_lands_on_fork_only "$TEST_DIR/mirror.git" "$UP"
}

@test "origin's gh-resolved set to another repository by a GIT_CONFIG_COUNT pair fails closed, and one in global config that the clone's base overrides passes" {
    "$REPO/scripts/fork-remotes.sh"
    # the floor's five pairs stay exported, and this adds a sixth, which git reads after the clone's own
    # config file, so it overrides the base that configuring set
    export GIT_CONFIG_COUNT=6 GIT_CONFIG_KEY_5=remote.origin.gh-resolved GIT_CONFIG_VALUE_5=someone/other
    outside_refused "remote.origin.gh-resolved someone/other (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS)"
    [[ "$output" == *"remote.origin.gh-resolved is 'someone/other' (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS), not 'base'"* ]] || false
    export GIT_CONFIG_COUNT=5
    unset GIT_CONFIG_KEY_5 GIT_CONFIG_VALUE_5
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    git config --global remote.origin.gh-resolved someone/other
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" config --local --get remote.origin.gh-resolved)" = base ]
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
    [[ "$output" == *"git cannot read the urls of remote 'gmirror' ("*"No such remote"*"): git reads a remote this way when only global or system config, or the environment (GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS), defines it, and a push to it still works. --check cannot tell"* ]] || false
    [[ "$output" == *"set mode does not change remotes defined there: remove its url and push url values where each lives, $AGAIN$NL    remote.gmirror.url $FORK (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [[ "$output" != *"Its push urls could not be checked"* ]] || false      # said of upstream only
    [[ "$output" != *"fork-remotes.sh to fix."* ]] || false
    set_mode_refuses "git cannot read the urls of remote 'gmirror'"
    # a push url alone is a url git cannot read back too: a push to that remote goes there
    git config --global --unset-all remote.gmirror.url
    git config --global remote.gmirror.pushurl "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"git cannot read the urls of remote 'gmirror' ("*"$NL    remote.gmirror.pushurl $FORK (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    git config --global --unset-all remote.gmirror.pushurl
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
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

@test "a remote that global config gives only a fetch refspec names no repository: set mode configures a fresh clone beside one named upstream, and --check passes" {
    # git remote lists each and get-url refuses each, but no config gives either a url: git would use
    # its name as its url, a path that names no repository here. Neither is a remote git cannot read.
    git config --global remote.upstream.fetch '+refs/heads/*:refs/remotes/upstream/*'
    git config --global remote.gfetch.prune true
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    [[ "$output" != *"git cannot read the urls"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "a remote with no url is compared by its name read as a url, which can name the fork's repository" {
    # A remote named ../fork.git, with only a prune setting in global config: git uses the name as its
    # url, the fork's repository from the clone's top level, so a push to it lands on the fork.
    "$REPO/scripts/fork-remotes.sh"
    git config --global remote.../fork.git.prune true
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote '../fork.git' (fetch url ../fork.git)"* ]] || false
    [[ "$output" != *"git cannot read the urls"* ]] || false
    set_mode_refuses "remote '../fork.git'"
    git config --global --remove-section remote.../fork.git
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "a remote with no url named as the fork's repository lists the keys that define it with where each lives, and removing them clears the note" {
    # Defined only in global config, git remote remove refuses it (no such remote); defined in a file the
    # clone's own config includes, it cannot remove the section. So the note lists each key where it
    # lives, and does not say to remove the remote. With one key in the clone's own config file too, git
    # remote remove takes that one and the note lists the rest.
    "$REPO/scripts/fork-remotes.sh"
    git config --global remote.../fork.git.prune true
    git config --global remote.../fork.git.x.prune true
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" != *"remote.../fork.git.x.prune"* ]] || false
    [[ "$output" == *"✗ origin's fetch url $FORK is the same repository as remote '../fork.git' (fetch url ../fork.git): a fetch from origin and a bare gh PR number read that repository, and a push to origin goes to $FORK. If '../fork.git' is a second name for your fork, remove each key listed below where it lives: no config gives it a url, so git uses its name as its url, and git remote remove, which acts on the clone's own config file alone, cannot remove a remote that file does not define; if origin was set to that url by mistake, the commands below point it at your fork$NL    remote.../fork.git.prune true (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [[ "$output" != *"Remove '../fork.git'"* ]] || false
    set_mode_refuses "remote '../fork.git'"
    git config --global --unset-all remote.../fork.git.prune
    git config --global --unset-all remote.../fork.git.x.prune
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    printf '[remote "../fork.git"]\n\tprune = true\n' > "$TEST_DIR/n.inc"
    git -C "$REPO" config include.path "$TEST_DIR/n.inc"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"If '../fork.git' is a second name for your fork, remove each key listed below where it lives:"*"$NL    remote.../fork.git.prune true (in file:$TEST_DIR/n.inc)$NL"* ]] || false
    set_mode_refuses "remote '../fork.git'"
    git config --file "$TEST_DIR/n.inc" --unset-all remote.../fork.git.prune
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    git config --global remote.../fork.git.prune true
    git -C "$REPO" config remote.../fork.git.skipDefaultUpdate true
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"Remove '../fork.git' if it is a second name for your fork; no config gives it a url, so git uses its name as its url, and git remote remove does not reach the keys that define it outside the clone's own config file, listed below, so remove each where it lives; if origin was set to that url by mistake, the commands below point it at your fork$NL    remote.../fork.git.prune true (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [[ "$output" != *"skipdefaultupdate"* ]] || false
    git -C "$REPO" remote remove ../fork.git
    git config --global --unset-all remote.../fork.git.prune
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    # one whose name a rule held outside rewrites to the fork's url: the note lists the rule too
    git -C "$REPO" config remote.nm.fetch '+refs/heads/*:refs/remotes/nm/*'
    git config --global "url.$FORK.insteadOf" nm
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin's fetch url $FORK is the same repository as remote 'nm' (fetch url $FORK): "*"Remove 'nm' if it is a second name for your fork; git reads its url named above through the rules listed below, held outside the clone's own config file; if origin"*"$NL    url.$FORK.insteadof nm (in file:$GIT_CONFIG_GLOBAL)"* ]] || false
    git -C "$REPO" remote remove nm
    git config --global --unset-all "url.$FORK.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "a remote with no url whose name an insteadOf or a pushInsteadOf rule rewrites fails closed, with the rule listed" {
    # git uses the name as the url, and a global rule rewrites that name to the fork's repository. git
    # remote get-url refuses a remote defined outside the clone, and git ls-remote --get-url shows an
    # insteadOf rewrite of the name but not a pushInsteadOf one, which rewrites it for pushes alone.
    "$REPO/scripts/fork-remotes.sh"
    git config --global remote.xalias.fetch '+refs/heads/*:refs/remotes/xalias/*'
    git config --global "url.$FORK.insteadOf" "xalias"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"git cannot read the urls of remote 'xalias' ("*"): no config gives it a url or a push url and no legacy file names it, so git uses its name as its url, which these rules rewrite: a fetch from it or a push to it goes wherever they point. --check does not compare a name that a rule rewrites, since git ls-remote --get-url shows an insteadOf rewrite of it but not a pushInsteadOf one: remove each rule where it lives, or the remote where it is defined (git -C $QREPO config --show-origin --get-regexp '^remote\.' lists where, and calls the environment 'command line:'), $AGAIN$NL    url.$FORK.insteadof xalias (in file:$GIT_CONFIG_GLOBAL)"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "git cannot read the urls of remote 'xalias'"
    git config --global --unset-all "url.$FORK.insteadOf"
    git config --global "url.$FORK.pushInsteadOf" "xalias"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$NL    url.$FORK.pushinsteadof xalias (in file:$GIT_CONFIG_GLOBAL)"* ]] || false
    git config --global --unset-all "url.$FORK.pushInsteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an upstream that config defines, or whose name a rule rewrites, but whose urls git cannot read is reported as such, with its push urls unchecked, not as missing" {
    # upstream defined only in global config, then only by a GIT_CONFIG_COUNT pair: git remote lists it,
    # get-url refuses it, and a push to it still goes to its url. Then one with no url whose name a rule
    # rewrites.
    git config --global remote.upstream.url "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"git cannot read the urls of remote 'upstream' ("*"): git reads a remote this way when only global or system config, or the environment (GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS), defines it, and a push to it still works. Its push urls could not be checked either, so --check cannot say whether a push to upstream would fail. --check cannot tell"* ]] || false
    [[ "$output" == *"$NL    remote.upstream.url $UP (in file:$GIT_CONFIG_GLOBAL)"* ]] || false
    [[ "$output" != *"no 'upstream' remote"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "git cannot read the urls of remote 'upstream'"
    git config --global --unset-all remote.upstream.url
    # the floor's five pairs stay exported, and this adds a sixth
    export GIT_CONFIG_COUNT=6 GIT_CONFIG_KEY_5=remote.upstream.url GIT_CONFIG_VALUE_5="$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"Its push urls could not be checked either"* ]] || false
    [[ "$output" == *"$NL    remote.upstream.url $UP (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS)"* ]] || false
    [[ "$output" != *"no 'upstream' remote"* ]] || false
    export GIT_CONFIG_COUNT=5
    unset GIT_CONFIG_KEY_5 GIT_CONFIG_VALUE_5
    git config --global remote.upstream.fetch '+refs/heads/*:refs/remotes/upstream/*'
    git config --global "url.$UP.insteadOf" "upstream"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"git cannot read the urls of remote 'upstream' ("*"so git uses its name as its url, which these rules rewrite"* ]] || false
    [[ "$output" != *"no 'upstream' remote"* ]] || false
    git config --global --unset-all "url.$UP.insteadOf"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an upstream that only an unreadable legacy file names keeps the note that there is no upstream" {
    # git cannot read upstream there, and a push to it fails, so the note is true: the legacy file's
    # note names the file, and its push urls need no word of their own.
    mkdir -p "$REPO/.git/branches"
    printf '%s\n' "$UP" > "$REPO/.git/branches/upstream"
    chmod 000 "$REPO/.git/branches/upstream"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    [[ "$output" == *"git cannot read the urls of remote 'upstream' ("*"): the legacy file $PREPO/.git/branches/upstream defines it"* ]] || false
    [[ "$output" != *"Its push urls could not be checked"* ]] || false
    rm -f "$REPO/.git/branches/upstream"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
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

@test "--check and set mode run from a linked worktree, which reads the main clone's config file and legacy directories" {
    # The header asks for --check in every new worktree. There git config --local reads and writes the
    # main clone's .git/config, which --show-origin spells by its absolute path, and the legacy
    # .git/remotes and .git/branches directories are the main clone's, which git rev-parse --git-path
    # names; .git in the worktree is a file. git worktree add brings no untracked file, so the script is
    # copied in.
    local W="$TEST_DIR/wt"
    git -C "$REPO" worktree add -q -b wt "$W"
    mkdir -p "$W/scripts"
    cp "$REPO/scripts/fork-remotes.sh" "$W/scripts/"
    run "$W/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    run "$W/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    [ "$(git -C "$REPO" config --get remote.upstream.pushurl)" = "no-push://upstream-is-fetch-only" ]
    # legacy files in both of the main clone's directories, each naming the fork's repository
    mkdir -p "$REPO/.git/remotes" "$REPO/.git/branches"
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/lr"
    printf '%s\n' "$FORK" > "$REPO/.git/branches/lb"
    run "$W/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"is the same repository as remote 'lr' (fetch url $FORK)"*"remotes/lr, which defines it)"* ]] || false
    [[ "$output" == *"is the same repository as remote 'lb' (fetch url $FORK)"*"branches/lb, which defines it)"* ]] || false
    local before; before="$(cat "$REPO/.git/config")"
    run "$W/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"nothing was changed"* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
    rm "$REPO/.git/remotes/lr" "$REPO/.git/branches/lb"
    run "$W/scripts/fork-remotes.sh" --check
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

@test "an upstream whose only url is empty fails closed the same under every git, and once the command removes it the rerun line configures upstream" {
    # git 2.43 reads an empty url and git 2.55 reads none, taking the name upstream as its url, so the two
    # gave different notes; both now get this one, and set mode refuses. With the empty value removed,
    # upstream, which still has a push url, has no url on either git, which reads its name as one.
    other_clone
    git -C "$REPO" config remote.upstream.url ""
    git -C "$REPO" config remote.upstream.pushurl "$UP"
    empty_refused "remote.upstream.url, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.upstream.url
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from upstream, expected $UP$NL"* ]] || false
    [[ "$output" == *"✗ upstream is PUSHABLE ($UP): a stray push to upstream goes there instead of failing$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    run_from_other "$output" "Run " " to fix."
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    [ "$(git -C "$REPO" remote get-url --all upstream)" = "$UP" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    run git -C "$REPO" push upstream main
    [ "$status" -ne 0 ]
}

# upstream's url and push url are what set mode writes, in the clone's own config file alone, and
# --replace-all puts its one value where the last value it replaces stood. A url held outside that file
# and read ahead of the last one it holds, a url held outside it while it holds none (which set mode
# does not change, wherever its own write would land), and a push url held outside it other than the
# sentinel each keep set mode from fixing upstream: --check names it with where it lives and gives no
# rerun line, so it gives the same answer each time, and set mode refuses. --check compares upstream
# with the project's url as git resolves it, which is also what set mode's write of that url resolves to.

@test "an upstream url in an included file ahead of the remote section fails with where it lives, no rerun line and the same answer twice" {
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/elsewhere.git"
    printf '[remote "upstream"]\n\turl = %s\n' "$TEST_DIR/elsewhere.git" > "$TEST_DIR/up.inc"
    { printf '[include]\n\tpath = %s\n' "$TEST_DIR/up.inc"; cat "$REPO/.git/config"; } > "$TEST_DIR/config.new"
    mv "$TEST_DIR/config.new" "$REPO/.git/config"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/elsewhere.git, expected $UP. These urls of upstream's, held outside the clone's own config file, are read ahead of where set mode writes, so after a rerun git would fetch from the first of them: remove each one where it lives, $AGAIN$NL    remote.upstream.url $TEST_DIR/elsewhere.git (in file:$TEST_DIR/up.inc)$NL"* ]] || false
    no_commands_no_rerun
    local first="$output"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$output" = "$first" ]
    set_mode_refuses "upstream fetches from $TEST_DIR/elsewhere.git, not the project ($UP), and these urls of upstream's, held outside the clone's own config file, are read ahead of where set mode would write, so git would fetch from the first of them:$NL    remote.upstream.url $TEST_DIR/elsewhere.git (in file:$TEST_DIR/up.inc)"
    # with no url of upstream's in the clone's own config file, git fetches from the included one, which
    # set mode does not change, and the note says so rather than where set mode's write would go
    git -C "$REPO" config --unset-all remote.upstream.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/elsewhere.git, expected $UP. The clone's own config file, where set mode writes, holds no url of upstream's, and git fetches upstream from the first of these, held outside it, which set mode does not change: remove each one where it lives, $AGAIN$NL    remote.upstream.url $TEST_DIR/elsewhere.git (in file:$TEST_DIR/up.inc)$NL"* ]] || false
    [[ "$output" != *"read ahead of where set mode writes"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "upstream fetches from $TEST_DIR/elsewhere.git, not the project ($UP); the clone's own config file, where set mode writes, holds no url of upstream's, and git fetches upstream from the first of these, held outside it, which set mode does not change:$NL    remote.upstream.url $TEST_DIR/elsewhere.git (in file:$TEST_DIR/up.inc)"
    # the project's url held there instead: upstream fetches from the project, and set mode configures
    git config --file "$TEST_DIR/up.inc" --replace-all remote.upstream.url "$UP"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an upstream url in config.worktree, with none in the clone's own config file, is named with where it lives and no rerun line, and set mode refuses" {
    # git reads config.worktree after the clone's own config file, so the url set mode would write there
    # would come first. The note says what is so, that the clone's own file holds no url of upstream's
    # and git fetches from this one, and not that it is read ahead of where set mode writes.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/elsewhere.git"
    git -C "$REPO" config extensions.worktreeConfig true
    git -C "$REPO" config --unset-all remote.upstream.url
    git -C "$REPO" config --worktree remote.upstream.url "$TEST_DIR/elsewhere.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/elsewhere.git, expected $UP. The clone's own config file, where set mode writes, holds no url of upstream's, and git fetches upstream from the first of these, held outside it, which set mode does not change: remove each one where it lives, $AGAIN$NL    remote.upstream.url $TEST_DIR/elsewhere.git (in file:$PREPO/.git/config.worktree)$NL"* ]] || false
    [[ "$output" != *"read ahead of where set mode"* ]] || false
    no_commands_no_rerun
    local first="$output"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$output" = "$first" ]
    set_mode_refuses "upstream fetches from $TEST_DIR/elsewhere.git, not the project ($UP); the clone's own config file, where set mode writes, holds no url of upstream's, and git fetches upstream from the first of these, held outside it, which set mode does not change:$NL    remote.upstream.url $TEST_DIR/elsewhere.git (in file:$PREPO/.git/config.worktree)"
    git -C "$REPO" config --worktree --unset-all remote.upstream.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an upstream url in an included file read after the clone's own does not stop the rerun line, which fixes upstream" {
    # The included url is never the first: set mode's write replaces the clone's own url where it stood.
    git -C "$REPO" remote add upstream "$TEST_DIR/elsewhere.git"
    printf '[remote "upstream"]\n\turl = %s\n' "$TEST_DIR/other.git" > "$TEST_DIR/up.inc"
    git -C "$REPO" config include.path "$TEST_DIR/up.inc"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/elsewhere.git, expected $UP$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" remote get-url --all upstream)" = "$UP$NL$TEST_DIR/other.git" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an upstream url in an included file between two of the clone's own fails with where it lives and no rerun line" {
    # set mode's one url would go where the clone's second stood, after the included one, which git
    # would then fetch from.
    git -C "$REPO" remote add upstream "$TEST_DIR/elsewhere.git"
    printf '[remote "upstream"]\n\turl = %s\n' "$TEST_DIR/other.git" > "$TEST_DIR/up.inc"
    git -C "$REPO" config include.path "$TEST_DIR/up.inc"
    printf '[remote "upstream"]\n\turl = %s\n' "$TEST_DIR/elsewhere2.git" >> "$REPO/.git/config"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/elsewhere.git, expected $UP. These urls of upstream's, held outside"*"$NL    remote.upstream.url $TEST_DIR/other.git (in file:$TEST_DIR/up.inc)$NL"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "    remote.upstream.url $TEST_DIR/other.git (in file:$TEST_DIR/up.inc)"
    git config --file "$TEST_DIR/up.inc" --unset-all remote.upstream.url
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an upstream push url in an included file fails with where it lives and no rerun line, and the sentinel itself there passes" {
    # A push goes to every push url, and set mode's sentinel would join the included one, not replace
    # it: a rerun line here sent the reader round the same note every time.
    "$REPO/scripts/fork-remotes.sh"
    printf '[remote "upstream"]\n\tpushurl = %s\n' "$UP" > "$TEST_DIR/up.inc"
    git -C "$REPO" config include.path "$TEST_DIR/up.inc"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream is PUSHABLE ($UP): a stray push to upstream goes there instead of failing. These push urls of upstream's are held outside the clone's own config file, where set mode cannot remove them: remove each one where it lives, $AGAIN$NL    remote.upstream.pushurl $UP (in file:$TEST_DIR/up.inc)$NL"* ]] || false
    no_commands_no_rerun
    local first="$output"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$output" = "$first" ]
    set_mode_refuses "These push urls of upstream's are held outside the clone's own config file, where set mode cannot remove them, and the sentinel it writes would join them rather than replace them:$NL    remote.upstream.pushurl $UP (in file:$TEST_DIR/up.inc)"
    git config --file "$TEST_DIR/up.inc" --replace-all remote.upstream.pushurl "no-push://upstream-is-fetch-only"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    run git -C "$REPO" push upstream main
    [ "$status" -ne 0 ]
    [ "$(git -C "$UP" rev-list --count main)" = "1" ]
}

@test "an empty upstream push url, in global config or in the clone's own after the project's, fails closed the same under every git" {
    # git 2.55 reads an empty push url as clearing the push urls read before it: in global config that
    # leaves the clone's own sentinel, and in the clone's own after the project's url it leaves none, so
    # a push to upstream goes to its url, the project's. git 2.43 reads an empty push url in both places:
    # from global config a push fails, and after the project's url in the clone's own a push lands on the
    # project and then fails on the empty one. Both gits get this note, which stops --check before the
    # note on remote.pushDefault, and set mode refuses.
    "$REPO/scripts/fork-remotes.sh"
    git config --global remote.upstream.pushurl ""
    git -C "$REPO" config --unset remote.pushDefault
    empty_refused "remote.upstream.pushurl, an empty value (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" != *"remote.pushDefault is unset"* ]] || false
    no_empty_commands
    git config --global --unset-all remote.upstream.pushurl
    git -C "$REPO" config --replace-all remote.upstream.pushurl "$UP"
    git -C "$REPO" config --add remote.upstream.pushurl ""
    empty_refused "remote.upstream.pushurl, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.upstream.pushurl
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream is PUSHABLE ($UP): a stray push to upstream goes there instead of failing$NL"* ]] || false
    [[ "$output" == *"remote.pushDefault is unset"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    run git -C "$REPO" push upstream main
    [ "$status" -ne 0 ]
    [ "$(git -C "$UP" rev-list --count main)" = "1" ]
}

# An empty url or push url value names different urls to different gits: git 2.55 reads it as clearing
# the values read before it, as its documentation says, and git 2.43 reads it as an empty url. So can an
# insteadOf or pushInsteadOf rule whose base is empty, which rewrites a url it matches to an empty one.
# Whatever a check here read past either would be one git's reading, so on every git each fails closed
# first, on any remote and wherever it is held: --check lists each with where it lives and stops, set
# mode refuses and writes nothing, and the same rows pass under both gits.

@test "an empty url value of origin's after the fork's, or ahead of it, fails closed the same under every git, and the command clears it" {
    # git 2.55 reads the fork's url and then an empty one as no url, and uses the name origin; with the
    # empty one first, it reads the fork's url alone. git 2.43 reads an empty url in either place.
    git -C "$REPO" config --add remote.origin.url ""
    empty_refused "remote.origin.url, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.origin.url
    git -C "$REPO" config --unset-all remote.origin.url
    git -C "$REPO" config remote.origin.url ""
    git -C "$REPO" config --add remote.origin.url "$FORK"
    empty_refused "remote.origin.url, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.origin.url
    follow_steps
    [ "$(git -C "$REPO" config --get-all remote.origin.url)" = "$FORK" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" config --get-all remote.origin.pushurl)" = "$FORK" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

@test "origin with the project's url, an empty value and then the fork's fails closed, so set mode cannot copy the project's url onto the push url" {
    # git 2.55 reads the fork's url alone here, and set mode copied the first value as config holds it,
    # the project's, onto the push url; a push to origin then landed on the project. git 2.43 reads all
    # three. Both now stop on the empty value, and with it removed the project refusal stands.
    git -C "$REPO" config --replace-all remote.origin.url "$UP"
    git -C "$REPO" config --add remote.origin.url ""
    git -C "$REPO" config --add remote.origin.url "$FORK"
    empty_refused "remote.origin.url, an empty value (in file:$PREPO/.git/config)"
    run git -C "$REPO" config --get-all remote.origin.pushurl
    [ "$status" -ne 0 ]
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    empty_commands remote.origin.url
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin points at the upstream project, not at your fork.$NL  origin = $UP$NL"* ]] || false
}

@test "an empty upstream url in the clone's own config file over a global one fails closed the same under every git, and set mode leaves it in place" {
    # git 2.55 reads the clone's empty value as clearing the global url, so upstream fetches from the
    # project's url after it; git 2.43 fetches from the global url. Set mode's write of upstream's url
    # would remove the empty value and bring the global url back for git 2.55, so it refuses, and with
    # the empty value removed the global url is read ahead of the clone's own and fails closed.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git config --global remote.upstream.url "$TEST_DIR/mirror.git"
    git -C "$REPO" config --replace-all remote.upstream.url ""
    git -C "$REPO" config --add remote.upstream.url "$UP"
    empty_refused "remote.upstream.url, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.upstream.url
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/mirror.git, expected $UP. These urls of upstream's, held outside the clone's own config file, are read ahead of where set mode writes, so after a rerun git would fetch from the first of them: remove each one where it lives, $AGAIN$NL    remote.upstream.url $TEST_DIR/mirror.git (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    no_commands_no_rerun
    git config --global --unset-all remote.upstream.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "every empty value is listed with where it lives, in the order git reads them, and only the clone's own get a command" {
    # Two in the clone's own config file under one key, one in a file it includes after them, one in the
    # environment, which git reads last: one command removes the clone's own two, and each of the others
    # is removed where it lives.
    "$REPO/scripts/fork-remotes.sh"
    printf '[remote "upstream"]\n\turl = \n' > "$TEST_DIR/up.inc"
    git -C "$REPO" config include.path "$TEST_DIR/up.inc"
    git -C "$REPO" config --add remote.origin.pushurl ""
    git -C "$REPO" config --add remote.origin.pushurl ""
    # the floor's five pairs stay exported, and this adds a sixth
    export GIT_CONFIG_COUNT=6 GIT_CONFIG_KEY_5=remote.origin.url GIT_CONFIG_VALUE_5=
    empty_refused "remote.origin.pushurl, an empty value (in file:$PREPO/.git/config)" \
        "remote.origin.pushurl, an empty value (in file:$PREPO/.git/config)" \
        "remote.upstream.url, an empty value (in file:$TEST_DIR/up.inc)" \
        "remote.origin.url, an empty value (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS)"
    empty_commands remote.origin.pushurl
    follow_steps
    [ "$(git -C "$REPO" config --local --get-all remote.origin.pushurl)" = "$FORK" ]
    empty_refused "remote.upstream.url, an empty value (in file:$TEST_DIR/up.inc)" \
        "remote.origin.url, an empty value (set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS)"
    no_empty_commands
    export GIT_CONFIG_COUNT=5
    unset GIT_CONFIG_KEY_5 GIT_CONFIG_VALUE_5
    git config --file "$TEST_DIR/up.inc" --unset-all remote.upstream.url
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "a legacy file that defines origin or upstream with an empty url fails closed with where it lives, the same under every git, and is not read where config gives a url" {
    # git reads a legacy file only for a remote that config gives no url, and reads an empty url there as
    # it reads an empty config value: git 2.43 as an empty url, git 2.55 as clearing the urls read before
    # it. With the empty URL: line first, origin's first url was empty for git 2.43 and the script
    # stopped with status 2, while git 2.55 read the fork's url.
    git -C "$REPO" config --unset-all remote.origin.url
    mkdir -p "$REPO/.git/remotes" "$REPO/.git/branches"
    printf 'URL:  \nURL: %s\n' "$FORK" > "$REPO/.git/remotes/origin"
    printf '  #main\n' > "$REPO/.git/branches/upstream"
    empty_refused "a URL: line, an empty value (in the legacy file $PREPO/.git/remotes/origin)" \
        "the url on its first line, ahead of the '#', an empty value (in the legacy file $PREPO/.git/branches/upstream)"
    no_empty_commands
    # the empty URL: line last, with no newline after it, which git reads as a line too
    printf 'URL: %s\nURL:' "$FORK" > "$REPO/.git/remotes/origin"
    empty_refused "a URL: line, an empty value (in the legacy file $PREPO/.git/remotes/origin)" \
        "the url on its first line, ahead of the '#', an empty value (in the legacy file $PREPO/.git/branches/upstream)"
    # repaired, each is read as before: origin's url is in no config, and a blank line in a remotes
    # file is no URL: line; git ignores a branches file whose first line is blank, so there is no upstream
    printf 'URL: %s\n\nPull: refs/heads/main:refs/heads/origin\n' "$FORK" > "$REPO/.git/remotes/origin"
    printf '  \n' > "$REPO/.git/branches/upstream"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ]
    [[ "$output" != *"an empty value"* ]] || false
    [[ "$output" == *"origin's url is not in git config (the legacy file $PREPO/.git/remotes/origin defines it)"* ]] || false
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    # with origin's url in config, git reads no legacy file for it, and an empty URL: line there is no url
    git -C "$REPO" config remote.origin.url "$FORK"
    printf 'URL:\n' > "$REPO/.git/remotes/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" != *"an empty value"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
}

@test "an insteadOf or pushInsteadOf rule whose base is empty, in the clone's own config file, fails closed like an empty value, the same under every git, and its command clears it" {
    # A pushInsteadOf rule whose base is empty, on origin's second url while origin has no push url:
    # git 2.43 pushed to an empty url, so a push to origin failed while --check passed, and git 2.55 pushed
    # to both urls. Both gits now get the empty-value note, with the command that removes the rule.
    bare "$TEST_DIR/px.git"
    git -C "$REPO" config --add remote.origin.url "$TEST_DIR/px.git"
    git -C "$REPO" config url."".pushInsteadOf "$TEST_DIR/px.git"
    git -C "$REPO" remote add upstream "$UP"
    git -C "$REPO" config remote.upstream.pushurl no-push://upstream-is-fetch-only
    git -C "$REPO" config remote.pushDefault origin
    git -C "$REPO" config remote.origin.gh-resolved base
    empty_refused "url..pushinsteadof $TEST_DIR/px.git, a rule whose base is empty (in file:$PREPO/.git/config)"
    empty_commands url..pushinsteadof
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin PUSHES to $TEST_DIR/px.git, not the repository it fetches from ($FORK); a push to origin goes to $FORK, $TEST_DIR/px.git$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/px.git" "$UP"
    # An insteadOf rule whose base is empty, on origin's url, which every git rewrites to nothing.
    printf '[url ""]\n\tinsteadOf = %s\n' "$FORK" >> "$REPO/.git/config"
    [ -z "$(git -C "$REPO" remote get-url origin)" ]
    empty_refused "url..insteadof $FORK, a rule whose base is empty (in file:$PREPO/.git/config)"
    empty_commands url..insteadof
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an insteadOf rule whose base is empty, held outside the clone's own config file, fails closed with no command, on the url of a legacy file, a remote's name, or origin's name" {
    # git 2.55 rewrites a url that a legacy file gives, or a remote's name read as its url, as it reads
    # it, and reads the empty result as clearing; git 2.43 reads an empty url. They split: origin only a
    # legacy file defines stopped 2.43 with status 2 and gave 2.55 the legacy note, and an upstream with a
    # fetch refspec alone got a rerun line on 2.43 and the aliased note on 2.55. With origin's own name
    # rewritten, 2.43 read an empty url and 2.55 no remote: the rule now fails closed before git reads
    # origin's url, so both name it.
    git -C "$REPO" config --unset-all remote.origin.url
    mkdir -p "$REPO/.git/remotes"
    printf 'URL: %s\n' "$TEST_DIR/legacyx" > "$REPO/.git/remotes/origin"
    git config --global url."".insteadOf "$TEST_DIR/legacyx"
    empty_refused "url..insteadof $TEST_DIR/legacyx, a rule whose base is empty (in file:$GIT_CONFIG_GLOBAL)"
    no_empty_commands
    rm "$REPO/.git/remotes/origin"
    git config --global --unset-all url."".insteadOf
    git -C "$REPO" config remote.origin.url "$FORK"
    git -C "$REPO" config remote.upstream.fetch '+refs/heads/*:refs/remotes/upstream/*'
    git config --global url."".insteadOf upstream
    empty_refused "url..insteadof upstream, a rule whose base is empty (in file:$GIT_CONFIG_GLOBAL)"
    no_empty_commands
    git -C "$REPO" config --remove-section remote.upstream
    git -C "$REPO" config --unset-all remote.origin.url
    git config --global --replace-all url."".insteadOf origin
    empty_refused "url..insteadof origin, a rule whose base is empty (in file:$GIT_CONFIG_GLOBAL)"
    no_empty_commands
    git config --global --unset-all url."".insteadOf
    git -C "$REPO" config remote.origin.url "$FORK"
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "the note on empty values comes before git reads origin's url, so a clone with no origin gets it the same under every git" {
    # Both gits stop on a clone with no origin when they read its url; the empty value is named first.
    git -C "$REPO" config --remove-section remote.origin
    git -C "$REPO" config remote.upstream.url ""
    empty_refused "remote.upstream.url, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.upstream.url
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 2 ]
    [[ "$output" == "fork-remotes: git cannot read origin's url: "* ]] || false
}

@test "an empty url or push url value of any other remote fails closed the same under every git, and its command, quoted for a name that holds a space, clears it" {
    # A remote 'mirror' with the fork's url, an empty one and another repository's: git 2.43 read all
    # three and refused origin as sharing the fork's repository with it, and git 2.55 read the last alone
    # and passed. Both now stop on the empty value; with it removed, the shared-repository note stands.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/other.git"
    git -C "$REPO" remote add mirror "$FORK"
    git -C "$REPO" config --add remote.mirror.url ""
    git -C "$REPO" config --add remote.mirror.url "$TEST_DIR/other.git"
    empty_refused "remote.mirror.url, an empty value (in file:$PREPO/.git/config)"
    empty_commands remote.mirror.url
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin's fetch url $FORK is the same repository as remote 'mirror' (fetch url $FORK)"* ]] || false
    git -C "$REPO" remote remove mirror
    # an empty push url on a remote whose name holds a space
    git -C "$REPO" config "remote.my mirror.url" "$TEST_DIR/other.git"
    git -C "$REPO" config "remote.my mirror.pushurl" ""
    empty_refused "remote.my mirror.pushurl, an empty value (in file:$PREPO/.git/config)"
    empty_commands "remote.my mirror.pushurl"
    follow_steps
    run git -C "$REPO" config --get-all "remote.my mirror.pushurl"
    [ "$status" -ne 0 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    # an empty URL: line in a legacy file that alone defines another remote, whatever the remote's name
    # starts with
    mkdir -p "$REPO/.git/remotes"
    printf 'URL: %s\nURL:\n' "$FORK" > "$REPO/.git/remotes/mirror2"
    printf 'URL:\n' > "$REPO/.git/remotes/.mirror3"
    printf 'URL:\n' > "$REPO/.git/remotes/..mirror4"
    empty_refused "a URL: line, an empty value (in the legacy file $PREPO/.git/remotes/mirror2)" \
        "a URL: line, an empty value (in the legacy file $PREPO/.git/remotes/.mirror3)" \
        "a URL: line, an empty value (in the legacy file $PREPO/.git/remotes/..mirror4)"
    no_empty_commands
    rm "$REPO/.git/remotes/mirror2" "$REPO/.git/remotes/.mirror3" "$REPO/.git/remotes/..mirror4"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an insteadOf rule that rewrites the sentinel push url fails with the rule listed, and set mode refuses" {
    # git applies insteadOf to an explicit push url, so the sentinel set mode writes would push wherever
    # the rule points.
    "$REPO/scripts/fork-remotes.sh"
    git config --global "url.$TEST_DIR/.insteadOf" "no-push://"
    [ "$(git -C "$REPO" remote get-url --push upstream)" = "$TEST_DIR/upstream-is-fetch-only" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ set mode makes upstream fetch-only by writing no-push://upstream-is-fetch-only as its push url, and git rewrites that url by these rules, so a push to upstream would reach a repository instead of failing: remove each one where it lives, $AGAIN$NL    url.$TEST_DIR/.insteadof no-push:// (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [[ "$output" == *"upstream is PUSHABLE ($TEST_DIR/upstream-is-fetch-only)"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "These rules rewrite the sentinel push url set mode writes for upstream, no-push://upstream-is-fetch-only, so a push to upstream would not fail:$NL    url.$TEST_DIR/.insteadof no-push:// (in file:$GIT_CONFIG_GLOBAL)"
    git config --global --unset-all "url.$TEST_DIR/.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "upstream is compared with the project's url as git rewrites it, so a rule that rewrites that url passes after one run of set mode" {
    # The project's url is an alias that a global rule expands. Set mode writes the alias, which git
    # expands for upstream as it does for the project, so --check passes and a second run changes
    # nothing; compared with the url as written, --check asked for the same rerun every time. An upstream
    # genuinely elsewhere still fails.
    export ROMP_UPSTREAM_URL="proj:project.git"
    git config --global "url.$TEST_DIR/.insteadOf" "proj:"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"no 'upstream' remote"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    [ "$(git -C "$REPO" remote get-url upstream)" = "$UP" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    local config; config="$(cat "$REPO/.git/config")"
    "$REPO/scripts/fork-remotes.sh"
    [ "$(cat "$REPO/.git/config")" = "$config" ]
    git -C "$REPO" remote set-url upstream "$TEST_DIR/elsewhere.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/elsewhere.git, expected proj:project.git, which git rewrites to $UP$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
}

@test "a global insteadOf rule that moves origin's and the project's urls to another tree passes, and --check gives the same answer twice" {
    # The rule rewrites the fork's url and the project's url alike. --check reads both as git rewrites
    # them: upstream fetches from the project as git resolves it, and a push to origin goes where it
    # fetches from, so there is no note, and no rerun line to loop on.
    "$REPO/scripts/fork-remotes.sh"
    mkdir -p "$TEST_DIR/w"
    bare "$TEST_DIR/w/fork.git"
    git config --global "url.$TEST_DIR/w/.insteadOf" "$TEST_DIR/"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    local first="$output"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    [ "$output" = "$first" ]
    local old="$FORK"
    FORK="$TEST_DIR/w/fork.git"
    push_lands_on_fork_only "$old" "$UP"
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

@test "--check reads a local path holding a colon after a slash as a path, not the scp form" {
    # git takes a colon for the scp form only when no slash comes before it
    same_repository "$TEST_DIR/a:b.git" "file://$TEST_DIR/a:b.git"
}

@test "where a match passes, case counts: a push url or an upstream url that differs only in case, or ends in .GIT, is a note a rerun fixes" {
    # The push check and the upstream check compare ids exactly (see repo_id's comment), so a spelling
    # that may name another repository on a case-sensitive host is never taken for the expected one.
    # Their reading strips only a lowercase .git, as a forge does, so X.GIT keeps its suffix.
    export ROMP_UPSTREAM_URL="https://example.invalid/proj/romp.git"
    git -C "$REPO" remote set-url origin "https://example.invalid/someone/romp.git"
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" config --replace-all remote.origin.pushurl "https://example.invalid/Someone/romp.git"
    git -C "$REPO" config --replace-all remote.upstream.url "https://EXAMPLE.invalid/proj/romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin PUSHES to https://example.invalid/Someone/romp.git, not the repository it fetches from (https://example.invalid/someone/romp.git)"* ]] || false
    [[ "$output" == *"upstream fetches from https://EXAMPLE.invalid/proj/romp.git, expected https://example.invalid/proj/romp.git$NL"* ]] || false
    [[ "$output" != *"is the same repository as"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    git -C "$REPO" config --replace-all remote.origin.pushurl "https://example.invalid/someone/romp.GIT"
    git -C "$REPO" config --replace-all remote.upstream.url "https://example.invalid/proj/romp.GIT"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin PUSHES to https://example.invalid/someone/romp.GIT, not the repository it fetches from (https://example.invalid/someone/romp.git)"* ]] || false
    [[ "$output" == *"✗ upstream fetches from https://example.invalid/proj/romp.GIT, expected https://example.invalid/proj/romp.git$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "where a match passes, a local path with .git added is another repository and a url with a host loses one .git only, while where a match refuses they read as one" {
    # The push check and the upstream check read ids with repo_id's pass form (see its comment): a local
    # path keeps its suffix, as X and X.git are two directories, and a url with a host loses at most one
    # lowercase .git, as a forge strips one. So a push url at fork.git.git, a second bare repository
    # beside the fork, and an upstream at project beside project.git are notes a rerun fixes, and the
    # push lands on the fork alone. The shared check, where a match refuses, still reads fork.git.git as
    # the fork's repository.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/fork.git.git"
    bare "$TEST_DIR/project"
    git -C "$REPO" config --replace-all remote.origin.pushurl "$TEST_DIR/fork.git.git"
    git -C "$REPO" config --replace-all remote.upstream.url "$TEST_DIR/project"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin PUSHES to $TEST_DIR/fork.git.git, not the repository it fetches from ($FORK)"* ]] || false
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/project, expected $UP$NL"* ]] || false
    git -C "$REPO" config --replace-all remote.origin.pushurl "file://$TEST_DIR/fork.git.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ origin PUSHES to file://$TEST_DIR/fork.git.git, not the repository it fetches from ($FORK)"* ]] || false
    [[ "$output" == *"✗ upstream fetches from $TEST_DIR/project, expected $UP$NL"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$TEST_DIR/fork.git.git" "$TEST_DIR/project" "$UP"
    # a url with a host loses one .git, the one a forge strips, so the project's url without it passes,
    # and with .git twice it is a note; the same for a push url of origin's
    export ROMP_UPSTREAM_URL="https://example.invalid/proj/romp.git"
    git -C "$REPO" config --replace-all remote.upstream.url "https://example.invalid/proj/romp/"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    git -C "$REPO" config --replace-all remote.upstream.url "https://example.invalid/proj/romp.git.git"
    git -C "$REPO" remote set-url origin "https://example.invalid/someone/romp.git"
    git -C "$REPO" config --replace-all remote.origin.pushurl "https://example.invalid/someone/romp.git.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"✗ upstream fetches from https://example.invalid/proj/romp.git.git, expected https://example.invalid/proj/romp.git$NL"* ]] || false
    [[ "$output" == *"✗ origin PUSHES to https://example.invalid/someone/romp.git.git, not the repository it fetches from (https://example.invalid/someone/romp.git)"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    git -C "$REPO" config --replace-all remote.origin.pushurl "https://example.invalid/someone/romp"
    git -C "$REPO" config --replace-all remote.upstream.url "https://example.invalid/proj/romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    # where a match refuses, the suffix comes off to its fixpoint: a remote at fork.git.git is the fork's
    git -C "$REPO" remote set-url origin "$FORK"
    git -C "$REPO" config --replace-all remote.origin.pushurl "$FORK"
    git -C "$REPO" remote add mirror "$TEST_DIR/fork.git.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote 'mirror' (fetch url $TEST_DIR/fork.git.git)"* ]] || false
}

@test "--check counts spellings that differ in case as one repository where a match refuses, but X.GIT is not X" {
    # A host ignores case and a forge ignores it in owner and repository names, so Someone/Romp and
    # EXAMPLE.invalid are spellings of origin's repository (see repo_id's comment). A forge strips only a
    # lowercase .git suffix, and the fold comes after the strip, so romp.GIT names another repository.
    # Each spelling is compared on its own, so a match on one cannot hide the other.
    git -C "$REPO" remote set-url origin "https://example.invalid/someone/romp.git"
    git -C "$REPO" remote add mirror "https://example.invalid/someone/romp.GIT"
    run "$REPO/scripts/fork-remotes.sh" --check
    [[ "$output" == *"fork-remotes: checking"* ]] || false
    [[ "$output" != *"is the same repository as"* ]] || false
    git -C "$REPO" remote set-url mirror "https://example.invalid/Someone/Romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url https://example.invalid/someone/romp.git is the same repository as remote 'mirror' (fetch url https://example.invalid/Someone/Romp.git)"* ]] || false
    set_mode_refuses "remote 'mirror'"
    git -C "$REPO" remote set-url mirror "https://EXAMPLE.invalid/someone/romp"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url https://example.invalid/someone/romp.git is the same repository as remote 'mirror' (fetch url https://EXAMPLE.invalid/someone/romp)"* ]] || false
}

@test "the refusal counts an origin that spells the project's host, owner and name in other case as the project, but not one ending in .GIT" {
    export ROMP_UPSTREAM_URL="https://example.invalid/someone/romp.git"
    git -C "$REPO" remote set-url origin "https://EXAMPLE.invalid/Someone/Romp.git"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]] || false
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
    git -C "$REPO" remote set-url origin "https://example.invalid/someone/romp.GIT"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
}

@test "where a match refuses, local paths that differ only in case read as one repository: a second remote and the project spelled in other case are refused" {
    # A case-insensitive file system (macOS's default) reads two such spellings as one directory, so a
    # match refuses on them, at the cost of refusing two repositories a case-sensitive one keeps apart.
    # Neither spelling in other case exists here; nothing reads it.
    git -C "$REPO" remote add mirror "$TEST_DIR/Fork.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin's fetch url $FORK is the same repository as remote 'mirror' (fetch url $TEST_DIR/Fork.git)"* ]] || false
    set_mode_refuses "remote 'mirror'"
    git -C "$REPO" remote remove mirror
    export ROMP_UPSTREAM_URL="$TEST_DIR/PROJECT.git"
    git -C "$REPO" remote set-url origin "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"fork-remotes: origin points at the upstream project, not at your fork.$NL  origin = $UP$NL  project = $TEST_DIR/PROJECT.git$NL  origin's fetch url $UP is the project's repository$NL  origin's push url $UP is the project's repository$NL""Point origin at your fork first;"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"fork-remotes: origin points at the upstream project, not at your fork."* ]] || false
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
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
    [[ "$output" == *"remote 'mirror' (push url $FORK)"* ]] || false
    # the rule is in the clone's own config file, so it is not listed among rules held outside it
    [[ "$output" != *"$NL    url.$FORK.pushinsteadof"* ]]
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

@test "set mode replaces a doubled remote.pushDefault with one value, origin" {
    # git config --add by hand leaves two values, the last of which git uses; a plain set refuses a key
    # with two values, which stopped set mode part way through.
    "$REPO/scripts/fork-remotes.sh"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git -C "$REPO" config --add remote.pushDefault mirror
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"remote.pushDefault is 'mirror': a bare 'git push' would not go to your fork"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"fork-remotes: configured"* ]] || false
    [ "$(git -C "$REPO" config --get-all remote.pushDefault)" = origin ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    # another remote first and origin after it, both in the clone's own config file: git uses origin, and
    # the information beside a failing note lists only values held outside that file
    git -C "$REPO" config --replace-all remote.pushDefault mirror
    git -C "$REPO" config --add remote.pushDefault origin
    git -C "$REPO" config --unset remote.origin.gh-resolved
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"gh has no default repository"* ]] || false
    [[ "$output" != *"remote.pushDefault is"* ]] || false
    [[ "$output" != *"For information"* ]] || false
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

@test "the refusal reads every url of origin's: a second url naming the project is refused, with upstream missing or elsewhere" {
    # origin's first url is the fork and its second the project, and a push goes to both. Once set mode
    # had pointed upstream at the project, the next --check would find origin sharing its repository.
    # Both modes refuse before set mode writes, and with upstream at a third repository too.
    git -C "$REPO" config --add remote.origin.url "$UP"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin points at the upstream project, not at your fork.$NL  origin = $FORK$NL  project = $UP$NL  origin's extra url $UP is the project's repository$NL  origin's push url $UP is the project's repository$NL"* ]] || false
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
    bare "$TEST_DIR/elsewhere.git"
    git -C "$REPO" remote add upstream "$TEST_DIR/elsewhere.git"
    local before; before="$(cat "$REPO/.git/config")"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"  origin's extra url $UP is the project's repository$NL"* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"points at the upstream project"* ]] || false
    # with a push url of the fork's, git neither fetches from nor pushes to that second url, but set
    # mode's upstream write would still leave origin naming upstream's repository
    git -C "$REPO" config remote.origin.pushurl "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"  project = $UP$NL  origin's extra url $UP is the project's repository$NL"* ]] || false
    [[ "$output" != *"origin's push url $UP"* ]] || false
    follow_steps
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP" "$TEST_DIR/elsewhere.git"
}

@test "the refusal reads the project's url as git rewrites it, so an origin spelled as the alias a rule maps that url to is refused, with the rule listed" {
    # A global rule rewrites https urls on the project's host to an ssh Host alias, and origin was cloned
    # by that alias: repo_id cannot tell the alias from the host, but git rewrites the project's url to
    # the same alias. No url of origin's names the project as written, so the refusal names the rule,
    # with where it lives, and prints no commands; here origin is the project, and giving it the fork's
    # url, which the rule rewrites to the alias as well, clears the refusal. Nothing here contacts a
    # host.
    export ROMP_UPSTREAM_URL="https://example.invalid/someone/romp.git"
    git config --global "url.ex-alias:.insteadOf" "https://example.invalid/"
    git -C "$REPO" remote set-url origin "ex-alias:someone/romp.git"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"fork-remotes: origin is the project's repository as git reads the project's url, which a rule rewrites.$NL  origin = ex-alias:someone/romp.git$NL  project = https://example.invalid/someone/romp.git, which git rewrites to ex-alias:someone/romp.git$NL  origin's fetch url ex-alias:someone/romp.git is the project's repository$NL"* ]] || false
    [[ "$output" == *"git rewrites the project's url to that repository by these rules, each listed with where it lives:$NL    url.ex-alias:.insteadof https://example.invalid/ (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [[ "$output" == *"If origin is the project under a name these rules give it (an ssh alias, say), it is not your fork: give origin your fork's url and push url in the clone's own config file, $AGAIN."* ]] || false
    [[ "$output" != *"    git "* ]] || false
    run git -C "$REPO" remote get-url upstream
    [ "$status" -ne 0 ]
    git -C "$REPO" config --unset-all remote.origin.url
    git -C "$REPO" config remote.origin.url "https://example.invalid/me/romp.git"
    git -C "$REPO" config remote.origin.pushurl "https://example.invalid/me/romp.git"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 0 ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    # the same with the project's url itself spelled as an alias, which a rule in the clone's own config
    # file expands to origin's repository
    export ROMP_UPSTREAM_URL="alias:fork.git"
    git -C "$REPO" config "url.$TEST_DIR/.insteadOf" "alias:"
    git -C "$REPO" config --unset-all remote.upstream.url
    git -C "$REPO" config --unset-all remote.origin.pushurl
    git -C "$REPO" remote set-url origin "$FORK"
    local before; before="$(cat "$REPO/.git/config")"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"$NL  project = alias:fork.git, which git rewrites to $FORK$NL  origin's fetch url $FORK is the project's repository$NL"* ]] || false
    [[ "$output" == *"each listed with where it lives:$NL    url.$TEST_DIR/.insteadof alias: (in file:$PREPO/.git/config)$NL"* ]] || false
    [[ "$output" != *"    git "* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
}

@test "the refusal of an origin that is the fork, which a rule makes the project's url read as, names the rule and where it lives with no commands, and removing it there clears the refusal" {
    # A rule maps the project's url to the fork's, so git reads the project as origin's repository.
    # origin is the fork: commands that point origin at the fork changed nothing, and --check gave the
    # same refusal and the same commands again. The refusal names the rule and where it lives, in global
    # config and then in the clone's own config file; set mode refuses and writes nothing; once the rule
    # is removed where it lives, --check asks for the rerun, and then passes. origin has a push url, so a
    # pushInsteadOf rule on the fork's url rewrites nothing and is listed for information, and one on the
    # project's url is not among the rules that rewrite it.
    bare "$TEST_DIR/elsewhere.git"
    git -C "$REPO" config remote.origin.pushurl "$FORK"
    git config --global "url.$TEST_DIR/elsewhere.git.pushInsteadOf" "$FORK"
    git config --global --add "url.$TEST_DIR/elsewhere.git.pushInsteadOf" "$UP"
    git config --global "url.$FORK.insteadOf" "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" != *"pushinsteadof $UP ("* ]] || false
    rule_listed "url.$TEST_DIR/elsewhere.git.pushinsteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"
    [[ "$output" == *"fork-remotes: origin is the project's repository as git reads the project's url, which a rule rewrites.$NL  origin = $FORK$NL  project = $UP, which git rewrites to $FORK$NL  origin's fetch url $FORK is the project's repository$NL  origin's push url $FORK is the project's repository$NL"* ]] || false
    [[ "$output" == *"by these rules, each listed with where it lives:$NL    url.$FORK.insteadof $UP (in file:$GIT_CONFIG_GLOBAL)$NL""If origin is your fork"* ]] || false
    [[ "$output" == *"If origin is your fork, these rules make the project read as your fork, and pointing origin elsewhere cannot change that: remove each one where it lives, $AGAIN. If origin is the project"* ]] || false
    [[ "$output" != *"    git "* ]] || false
    [[ "$output" != *"points at the upstream project"* ]] || false
    local before; before="$(cat "$REPO/.git/config")"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"    url.$FORK.insteadof $UP (in file:$GIT_CONFIG_GLOBAL)$NL"* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
    git config --global --unset-all "url.$FORK.insteadOf"
    git -C "$REPO" config "url.$FORK.insteadOf" "$UP"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"by these rules, each listed with where it lives:$NL    url.$FORK.insteadof $UP (in file:$PREPO/.git/config)$NL"* ]] || false
    [[ "$output" != *"    git "* ]] || false
    git -C "$REPO" config --unset-all "url.$FORK.insteadOf"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP" "$TEST_DIR/elsewhere.git"
}

@test "the refusal also compares the project's url as written, where a rule rewrites it but not origin's spelling of it" {
    # A global rule rewrites the project's url, as written, to another directory; origin names the
    # project by a file:// url, which the rule does not match, so a push to origin lands on the project.
    mkdir -p "$TEST_DIR/w"
    git config --global "url.$TEST_DIR/w/.insteadOf" "$UP"
    git -C "$REPO" remote set-url origin "file://$UP"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"$NL  project = $UP, which git rewrites to $TEST_DIR/w/$NL  origin's fetch url file://$UP is the project's repository$NL"* ]] || false
}

@test "an origin whose own url or push url value names the project's repository gets the refusal with its commands, though a rule rewrites that value" {
    # A global rule rewrites the project's host to an ssh alias, so git reads origin's value and the
    # project's url alike as the alias. The value as configured is the project's url, so this is origin
    # set to the project, not a match only the rule makes: the refusal prints the commands, which clear
    # it while the rule stays. Then the same with the fork's url as origin's url and the project's url as
    # its push url value, and last a rule that rewrites origin's value but not the project's url.
    export ROMP_UPSTREAM_URL="https://example.invalid/someone/romp.git"
    git config --global "url.ex-alias:.insteadOf" "https://example.invalid/"
    git -C "$REPO" remote set-url origin "https://example.invalid/someone/romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"fork-remotes: origin points at the upstream project, not at your fork.$NL  origin = ex-alias:someone/romp.git$NL  project = https://example.invalid/someone/romp.git, which git rewrites to ex-alias:someone/romp.git$NL  origin's fetch url ex-alias:someone/romp.git is the project's repository$NL  origin's push url ex-alias:someone/romp.git is the project's repository$NL  origin's url value https://example.invalid/someone/romp.git, as git config holds it, names the project's repository$NL"* ]] || false
    [[ "$output" == *"then set your fork's url as its url and its push url:$NL    git -C $QREPO config --unset-all remote.origin.url$NL    git -C $QREPO config remote.origin.url <your-fork-url>$NL    git -C $QREPO config remote.origin.pushurl <your-fork-url>$NL"* ]] || false
    [[ "$output" != *"If origin is your fork"* ]] || false
    rule_listed "url.ex-alias:.insteadof https://example.invalid/ (in file:$GIT_CONFIG_GLOBAL)"
    local before; before="$(cat "$REPO/.git/config")"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin points at the upstream project, not at your fork."* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
    git -C "$REPO" config remote.origin.pushurl "https://example.invalid/someone/romp.git"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"fork-remotes: origin points at the upstream project, not at your fork.$NL  origin = $FORK$NL  project = https://example.invalid/someone/romp.git, which git rewrites to ex-alias:someone/romp.git$NL  origin's push url ex-alias:someone/romp.git is the project's repository$NL  origin's push url value https://example.invalid/someone/romp.git, as git config holds it, names the project's repository$NL"* ]] || false
    [[ "$output" == *"$NL    git -C $QREPO config --unset-all remote.origin.pushurl$NL"* ]] || false
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    # a rule that matches origin's spelling of the project's url, in other case, but not the project's
    # url as written: git reads origin as the alias and the project as itself, and only the value as
    # configured matches the project
    git config --global --unset-all "url.ex-alias:.insteadOf"
    git config --global "url.ex-alias:.insteadOf" "https://EXAMPLE.invalid/"
    git -C "$REPO" config remote.origin.pushurl "https://EXAMPLE.invalid/Someone/romp.git"
    [ "$(git -C "$REPO" remote get-url --push origin)" = "ex-alias:Someone/romp.git" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"fork-remotes: origin points at the upstream project, not at your fork.$NL  origin = $FORK$NL  project = https://example.invalid/someone/romp.git$NL  origin's push url value https://EXAMPLE.invalid/Someone/romp.git, as git config holds it, names the project's repository$NL"* ]] || false
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
}

@test "an origin that only a legacy file defines, with the project's url there, gets the refusal with its commands though a rule rewrites that url, and they clear it" {
    # A global rule rewrites the project's url, so git reads origin's url from its .git/remotes file and
    # the project's url alike as the rule's target. The url as the file holds it, trimmed as git trims
    # it, is the project's, so this is origin set to the project: the refusal prints the commands, which
    # set origin's url in the clone's own config file, where git then reads it in place of the file.
    git -C "$REPO" config --unset-all remote.origin.url
    mkdir -p "$REPO/.git/remotes" "$REPO/.git/branches"
    printf 'URL:  %s  \n' "$UP" > "$REPO/.git/remotes/origin"
    git config --global "url.$TEST_DIR/alias/project.git.insteadOf" "$UP"
    [ "$(git -C "$REPO" remote get-url origin)" = "$TEST_DIR/alias/project.git" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ]
    [[ "$output" == "fork-remotes: origin points at the upstream project, not at your fork.$NL  origin = $TEST_DIR/alias/project.git$NL  project = $UP, which git rewrites to $TEST_DIR/alias/project.git$NL  origin's fetch url $TEST_DIR/alias/project.git is the project's repository$NL  origin's push url $TEST_DIR/alias/project.git is the project's repository$NL  origin's url value $UP, as the legacy file $PREPO/.git/remotes/origin holds it, names the project's repository$NL""Point origin at your fork first; these commands remove every url and push url origin has in the clone's own config file, then set your fork's url as its url and its push url:$NL    git -C $QREPO config remote.origin.url <your-fork-url>$NL    git -C $QREPO config remote.origin.pushurl <your-fork-url>" ]] || false
    local before; before="$(cat "$REPO/.git/config")"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"origin points at the upstream project, not at your fork."* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
    # the same from a .git/branches file, whose first line git trims, and reads up to any '#'
    rm "$REPO/.git/remotes/origin"
    printf '  %s  \n' "$UP" > "$REPO/.git/branches/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ]
    [[ "$output" == *"$NL  origin's url value $UP, as the legacy file $PREPO/.git/branches/origin holds it, names the project's repository$NL""Point origin at your fork first;"* ]] || false
    # and beside a remotes file that gives no url, which git reads first
    printf '%s#main\n' "$UP" > "$REPO/.git/branches/origin"
    printf 'Pull: refs/heads/main:refs/heads/origin\n' > "$REPO/.git/remotes/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ]
    [[ "$output" == *"$NL  origin's url value $UP, as the legacy file $PREPO/.git/branches/origin holds it, names the project's repository$NL""Point origin at your fork first;"* ]] || false
    # git skips a legacy file it cannot read, and so does the comparison: with the remotes file unreadable
    # git reads the branches file, and with both unreadable it reads the name origin as origin's url
    chmod 000 "$REPO/.git/remotes/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ]
    [[ "$output" == *"$NL  origin's url value $UP, as the legacy file $PREPO/.git/branches/origin holds it, names the project's repository$NL""Point origin at your fork first;"* ]] || false
    chmod 000 "$REPO/.git/branches/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ]
    [[ "$output" != *"names the project's repository"* ]] || false
    [[ "$output" != *"Permission denied"* ]] || false
    chmod 644 "$REPO/.git/remotes/origin" "$REPO/.git/branches/origin"
    # git reads the branches file only where the remotes file gives no url, so the project's url there
    # is not origin's
    printf 'URL: %s\n' "$FORK" > "$REPO/.git/remotes/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 1 ]
    [[ "$output" == *"origin's url is not in git config (the legacy files $PREPO/.git/remotes/origin and $PREPO/.git/branches/origin define it)"* ]] || false
    [[ "$output" != *"the upstream project"* ]] || false
    [[ "$output" != *"names the project's repository"* ]] || false
    # the URL: line last, with no newline after it, which git reads as a line too
    rm "$REPO/.git/branches/origin"
    printf 'URL:  %s  ' "$UP" > "$REPO/.git/remotes/origin"
    run "$REPO/scripts/fork-remotes.sh" --check
    [[ "$output" == *"$NL  origin's url value $UP, as the legacy file $PREPO/.git/remotes/origin holds it, names the project's repository$NL"* ]] || false
    follow_steps
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"$RERUN"* ]] || false
    "$REPO/scripts/fork-remotes.sh"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
    push_lands_on_fork_only "$UP"
}

@test "a project url spelled as the name of a remote here stops the script, which would otherwise compare with that remote" {
    # git ls-remote --get-url reads a remote's name as that remote's url
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    export ROMP_UPSTREAM_URL=mirror
    local before; before="$(cat "$REPO/.git/config")"
    run "$REPO/scripts/fork-remotes.sh"
    [ "$status" -eq 2 ]
    [[ "$output" == *"fork-remotes: the project's url, mirror, is also the name of a remote in this clone, so git reads it as that remote's url; set ROMP_UPSTREAM_URL to the project's url itself"* ]] || false
    [ "$(cat "$REPO/.git/config")" = "$before" ]
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 2 ]
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
    [[ "$output" == *"These urls of origin's, or pushInsteadOf rules that match one while origin has no push url, are held outside the clone's own config file, where no command printed here can change them. Remove each one where it lives"* ]] || false
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

@test "the refusal of an origin whose pushes a pushInsteadOf rule in global config sends to the project gives the push url remedy, which clears it as printed" {
    # A fresh clone has no push url of origin's, so the rule sends every push to origin to the project.
    # The refusal lists the rule with where it lives and, as the note on values held outside the clone's
    # own config file does, says that a push url in that file makes the rule inert, with the command.
    git config --global "url.$UP.pushInsteadOf" "$FORK"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"origin points at the upstream project"* ]] || false
    [[ "$output" == *"$NL  origin's push url $UP is the project's repository$NL"* ]] || false
    [[ "$output" == *"Remove each one where it lives (or, for a pushInsteadOf rule listed here, give origin a push url in the clone's own config file with git -C $QREPO config remote.origin.pushurl <your-fork-url>: git applies no pushInsteadOf rule to a push url, so the rule then rewrites nothing), $AGAIN:$NL    url.$UP.pushinsteadof $FORK (in file:$GIT_CONFIG_GLOBAL)"* ]] || false
    [[ "$output" != *"    git "* ]] || false
    local cmd="${output#*with git -C }"; cmd="git -C ${cmd%%: git applies no*}"
    cmd="${cmd//<your-fork-url>/$FORK}"
    (cd "$TEST_DIR" && eval "$cmd")
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" != *"points at the upstream project"* ]] || false
    [[ "$output" == *"$RERUN"* ]] || false
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
    [[ "$output" == *"Fix what the notes above name, $AGAIN; set mode refuses to run while a remote's url or push url value is empty, an insteadOf or pushInsteadOf rule has an empty base, origin shares a repository with another remote, git cannot read a remote's urls, git config holds no url for origin, an includeIf \"onbranch:\" or \"hasconfig:remote.*.url:\" entry names a file that sets a remote.*, url.* or branch.*.pushRemote key or that --check cannot read in full, upstream does not fetch from the project while a url of upstream's held outside the clone's own config file is read ahead of the last one that file holds or that file holds none, upstream has a push url other than the sentinel held outside that file, a url rule rewrites the sentinel, or one of these is held anywhere but the clone's own config file, where it wins over anything set mode writes: a url of origin's, a pushInsteadOf rule that matches one while origin has no push url, or a setting that aims a bare push or a bare gh PR number away from origin."* ]] || false
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

@test "--check fails with git's own error on a remote url key, or a rule whose base is empty, written with no value" {
    # The empty-value check reads neither as an empty value: git stops on each when it reads origin's url.
    printf '[remote "mirror"]\n\turl\n' >> "$REPO/.git/config"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 2 ]
    [[ "$output" == *"fork-remotes: git cannot read origin's url: "*"remote.mirror.url"* ]] || false
    [[ "$output" != *"has no 'origin' remote"* ]] || false
    [[ "$output" != *"an empty value"* ]] || false
    git -C "$REPO" config --remove-section remote.mirror
    printf '[url ""]\n\tinsteadOf\n' >> "$REPO/.git/config"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 2 ]
    [[ "$output" == *"fork-remotes: git cannot read origin's url: "*"url..insteadof"* ]] || false
    [[ "$output" != *"a rule whose base is empty"* ]] || false
}

@test "a git without config --show-scope fails --check closed with a note naming its version, and set mode refuses" {
    # git 2.26 added --show-scope; a git from 2.8 to 2.25 reads --show-origin and refuses --show-scope.
    # A git on PATH ahead of the real one plays that git: it refuses the option as git does and names
    # itself 2.25.1. Discarding the refusal made a configured clone read as having no pushDefault and no
    # gh default, with a rerun line that never cleared, and set mode passed a branch pushRemote in global
    # config that aims away. Both modes now stop on it, and nothing else is reported.
    "$REPO/scripts/fork-remotes.sh"
    bare "$TEST_DIR/mirror.git"
    git -C "$REPO" remote add mirror "$TEST_DIR/mirror.git"
    git config --global branch.main.pushRemote mirror
    REAL_GIT="$(command -v git)"
    export REAL_GIT
    mkdir -p "$TEST_DIR/oldgit"
    cat > "$TEST_DIR/oldgit/git" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = --version ]; then echo "git version 2.25.1"; exit 0; fi
for a in "$@"; do
    if [ "$a" = --show-scope ]; then printf '%s\n' "error: unknown option \`show-scope'" "usage: git config [<options>]" >&2; exit 129; fi
done
exec "$REAL_GIT" "$@"
EOF
    chmod +x "$TEST_DIR/oldgit/git"
    local path="$PATH"
    PATH="$TEST_DIR/oldgit:$PATH"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"fork-remotes: checking$NL  ✗ git config --show-scope --show-origin, which these checks read to say where each value is held, failed (error: unknown option \`show-scope'). They need git 2.26 or later, and this is git version 2.25.1$NL"* ]] || false
    [[ "$output" != *"remote.pushDefault is unset"* ]] || false
    [[ "$output" != *"gh has no default repository"* ]] || false
    no_commands_no_rerun
    set_mode_refuses "They need git 2.26 or later, and this is git version 2.25.1"
    PATH="$path"
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -ne 0 ]
    [[ "$output" == *"branch.main.pushremote is 'mirror' (in file:$GIT_CONFIG_GLOBAL)"* ]] || false
    git config --global --unset-all branch.main.pushRemote
    run "$REPO/scripts/fork-remotes.sh" --check
    [ "$status" -eq 0 ]
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
