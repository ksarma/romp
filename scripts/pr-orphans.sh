#!/usr/bin/env bash
# scripts/pr-orphans.sh: report merged PRs whose content is not on main.
#
# The case it catches: a PR based on another PR's branch is merged into that branch AFTER the base
# has merged. GitHub marks it merged, the author moves on, and the content sits on a branch nobody
# has a PR for (2026-09-06: four such PRs in one afternoon; a person noticed). Every merged PR's
# merge commit must be reachable from main; one that is not is printed as `#N` (with its base and
# the commit) and the script exits 1. A clean set exits 0 and prints one line.
#
# A merged PR with NO merge commit recorded is a separate case. GitHub documents merge_commit_sha
# for merge, squash and rebase merges; what it records for a PR marked merged indirectly (every
# member of a batch) is undocumented and nothing observed yet says. The question the script answers,
# "did the content reach main", does not need the field: the PR's head commit is either reachable
# from main or not. So a null merge commit falls back to the head: reachable is clean (noted, not
# reported); unreachable is printed as `#N` with distinct wording, "unknown: check by hand", and
# exits 1 like a stranded PR, since a clone that never fetched the head reads the same way.
#
# Runs locally (scripts/land.sh and `batch.py finish` call it) and as a small job on every push to
# main (.github/workflows/pr-orphans.yml), so the class is reported within minutes.
#
# The check is against main as this clone knows it: origin/main when the remote-tracking ref
# exists (a clone, or CI's full-depth checkout), else the local main. A merge commit this clone has
# never fetched is not an ancestor of anything here and is reported; fetch and re-run before
# treating that as a stranded PR.
#
# Env: ROMP_GH names the gh binary (tests stub it); ROMP_ORPHANS_LIMIT caps how many merged PRs are
# read, newest first (default 200; the window a stranded PR is found in).
set -euo pipefail

cd "$(cd "$(dirname "$0")/.." && pwd)"
GH="${ROMP_GH:-gh}"
MAIN="${ROMP_MAIN_BRANCH:-main}"
LIMIT="${ROMP_ORPHANS_LIMIT:-200}"

# Check against the remote's main, not a stale local copy: land.sh runs this right after a merge
# the clone has not seen yet, and a clone that never fetched would report every recent merge.
# ROMP_ORPHANS_NO_FETCH=1 skips the fetch (CI's fresh checkout does not need one).
if [ -z "${ROMP_ORPHANS_NO_FETCH:-}" ] && git remote get-url origin >/dev/null 2>&1; then
    git fetch --quiet --prune origin 2>/dev/null || echo "pr-orphans: fetch from origin failed; checking what the clone has" >&2
fi

if git rev-parse --verify --quiet "refs/remotes/origin/$MAIN" >/dev/null; then
    ref="origin/$MAIN"
elif git rev-parse --verify --quiet "refs/heads/$MAIN" >/dev/null; then
    ref="$MAIN"
else
    echo "pr-orphans: no $MAIN branch in this clone" >&2
    exit 2
fi

# One line per merged PR: number <tab> merge commit <tab> base branch. gh's --jq keeps the parsing
# out of the shell; a PR whose mergeCommit is null (none recorded) arrives as "none" and is checked
# by its head commit instead (one extra read per such PR; they are rare).
rows="$("$GH" pr list --state merged --limit "$LIMIT" --json number,mergeCommit,baseRefName \
        --jq '.[] | [.number, (.mergeCommit.oid // "none"), .baseRefName] | @tsv')"

head_of() {  # head_of <pr>: the PR's head commit as GitHub records it, or nothing
    "$GH" pr view "$1" --json headRefOid </dev/null 2>/dev/null \
        | sed -n 's/.*"headRefOid": *"\([0-9a-f]*\)".*/\1/p' | head -n1
}

orphans=0
unknown=0
unrecorded=0
checked=0
while IFS=$'\t' read -r n sha base; do
    [ -n "${n:-}" ] || continue
    checked=$((checked + 1))
    if [ "$sha" != "none" ]; then
        if ! git merge-base --is-ancestor "$sha" "$ref" 2>/dev/null; then
            echo "#$n"
            echo "  merged into '$base' at ${sha:0:10}: not an ancestor of $ref; its content is not on $MAIN" >&2
            orphans=$((orphans + 1))
        fi
        continue
    fi
    head="$(head_of "$n")"
    if [ -n "$head" ] && git merge-base --is-ancestor "$head" "$ref" 2>/dev/null; then
        echo "pr-orphans: #$n has no merge commit recorded; its head ${head:0:10} is on $ref, so its content reached $MAIN"
        unrecorded=$((unrecorded + 1))
    else
        echo "#$n"
        echo "  merged into '$base' with no merge commit recorded, and its head ${head:-(unknown)} is not an ancestor of $ref: unknown, check by hand (fetch first; then compare the PR's commits with $MAIN)" >&2
        unknown=$((unknown + 1))
    fi
done <<< "$rows"

if [ "$orphans" -ne 0 ]; then
    echo "pr-orphans: $orphans merged PR(s) whose content never reached $MAIN (of $checked checked). Open a PR from the branch to $MAIN." >&2
fi
if [ "$unknown" -ne 0 ]; then
    echo "pr-orphans: $unknown merged PR(s) with no merge commit recorded and a head not on $MAIN (of $checked checked): unknown, check by hand." >&2
fi
[ "$orphans" -eq 0 ] && [ "$unknown" -eq 0 ] || exit 1
extra=""
[ "$unrecorded" -eq 0 ] || extra="; $unrecorded with no merge commit recorded, reached $MAIN by head"
echo "pr-orphans: clean ($checked merged PR(s) checked against $ref$extra)"
