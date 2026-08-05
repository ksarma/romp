#!/usr/bin/env bash
# scripts/upstream-check.sh — what has the project we forked from added since we
# diverged, and would any of it collide with our own changes?
#
# Read-only apart from the fetch: it never merges, rebases, or checks anything
# out. Deciding what to take is the point of looking, so this reports and stops,
# and prints the command it would have run.
#
# The collision section is the part worth reading: it intersects the files the
# new upstream commits touch with the files OUR fork-only commits touch. That is
# where a merge will actually cost attention; everything else fast-forwards past
# us without comment.
#
#   scripts/upstream-check.sh            # fetch, then report
#   scripts/upstream-check.sh --quiet    # print nothing when there is nothing new
#   scripts/upstream-check.sh --no-fetch # report against what we already fetched
#
# Branch names: ROMP_FORK_BRANCH (default main) is ours, ROMP_UPSTREAM_BRANCH
# (default main) is theirs.
set -euo pipefail

cd "$(cd "$(dirname "$0")/.." && pwd)"   # report on this script's clone, not the shell's cwd

MINE="${ROMP_FORK_BRANCH:-main}"
THEIRS="upstream/${ROMP_UPSTREAM_BRANCH:-main}"
LIST_MAX="${ROMP_UPSTREAM_LIST_MAX:-25}"

do_fetch=1
quiet=0
for arg in "$@"; do
    case "$arg" in
        --no-fetch) do_fetch=0 ;;
        --quiet) quiet=1 ;;
        *) echo "usage: scripts/upstream-check.sh [--quiet] [--no-fetch]" >&2; exit 2 ;;
    esac
done

git remote get-url upstream >/dev/null 2>&1 || {
    echo "upstream-check: no 'upstream' remote — run scripts/fork-remotes.sh first" >&2
    exit 2
}
git rev-parse --verify --quiet "$MINE" >/dev/null || {
    echo "upstream-check: no local branch '$MINE' (set ROMP_FORK_BRANCH)" >&2
    exit 2
}

if [ $do_fetch -eq 1 ]; then
    # --prune keeps deleted upstream branches from lingering as phantom refs.
    git fetch --quiet --prune upstream || {
        echo "upstream-check: fetch from upstream failed" >&2
        exit 1
    }
fi
git rev-parse --verify --quiet "$THEIRS" >/dev/null || {
    echo "upstream-check: '$THEIRS' not found after fetch (set ROMP_UPSTREAM_BRANCH)" >&2
    exit 2
}

behind="$(git rev-list --count "$MINE..$THEIRS")"
ahead="$(git rev-list --count "$THEIRS..$MINE")"

if [ "$behind" = "0" ]; then
    [ $quiet -eq 1 ] && exit 0
    echo "upstream-check: $MINE is up to date with $THEIRS"
    [ "$ahead" != "0" ] && echo "  ($ahead commit(s) of your own on top)"
    exit 0
fi

echo "upstream-check: $behind new commit(s) on $THEIRS, $ahead of your own on $MINE"
echo
echo "New upstream (newest first, merges folded away):"
git log --no-merges --oneline --max-count="$LIST_MAX" "$MINE..$THEIRS" | sed 's/^/  /'
more="$(git rev-list --no-merges --count "$MINE..$THEIRS")"
[ "$more" -gt "$LIST_MAX" ] && echo "  … and $((more - LIST_MAX)) more"

if [ "$ahead" != "0" ]; then
    theirs_files="$(git diff --name-only "$MINE...$THEIRS")"
    mine_files="$(git diff --name-only "$THEIRS...$MINE")"
    overlap="$(printf '%s\n' "$theirs_files" | grep -Fxf <(printf '%s\n' "$mine_files") || true)"
    echo
    if [ -n "$overlap" ]; then
        echo "Files you have changed that upstream also changed — the merge lands here:"
        printf '%s\n' "$overlap" | sed 's/^/  /'
    else
        echo "None of your changed files were touched upstream; the merge should be clean."
    fi
fi

echo
echo "To take it (on a branch, never on your shared checkout):"
echo "  git checkout -b upstream-merge $MINE && git merge $THEIRS"
