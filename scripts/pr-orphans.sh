#!/usr/bin/env bash
# scripts/pr-orphans.sh: report merged PRs whose merge commit is not an ancestor of main.
#
# The case it catches: a PR based on another PR's branch is merged into that branch AFTER the base
# has merged. GitHub marks it merged, the author moves on, and the content sits on a branch nobody
# has a PR for (2026-09-06: four such PRs in one afternoon; a person noticed). Every merged PR's
# merge commit must be reachable from main; one that is not is printed as `#N` (with its base and
# the commit) and the script exits 1. A clean set exits 0 and prints one line.
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
# out of the shell; a PR whose mergeCommit is null (none recorded) is reported the same way, since
# nothing shows its content reached main.
rows="$("$GH" pr list --state merged --limit "$LIMIT" --json number,mergeCommit,baseRefName \
        --jq '.[] | [.number, (.mergeCommit.oid // "none"), .baseRefName] | @tsv')"

orphans=0
checked=0
while IFS=$'\t' read -r n sha base; do
    [ -n "${n:-}" ] || continue
    checked=$((checked + 1))
    if [ "$sha" = "none" ] || ! git merge-base --is-ancestor "$sha" "$ref" 2>/dev/null; then
        echo "#$n"
        echo "  merged into '$base' at ${sha:0:10}: not an ancestor of $ref; its content is not on $MAIN" >&2
        orphans=$((orphans + 1))
    fi
done <<< "$rows"

if [ "$orphans" -ne 0 ]; then
    echo "pr-orphans: $orphans merged PR(s) whose content never reached $MAIN (of $checked checked). Open a PR from the branch to $MAIN." >&2
    exit 1
fi
echo "pr-orphans: clean ($checked merged PR(s) checked against $ref)"
