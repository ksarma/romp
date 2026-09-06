#!/usr/bin/env bash
# scripts/land.sh N [M]: merge one or two PRs alone, each with a merge commit.
#
# The batch (scripts/batch.py) is how PRs normally land; this is the path for an urgent fix or a
# one-file ledger PR that conflicts with nothing. Per PR it runs
#   gh pr merge N --merge --delete-branch --match-head-commit <head> [--auto]
# and afterward scripts/pr-orphans.sh, so a merge that strands a dependent is reported at once.
#
# Refusals, each the plain statement of a rule the repository already has:
#   * --squash / --rebase (or -s / -r) anywhere on the command line: merge commits only. A squash
#     or rebase rewrites SHAs, so a PR stacked on this one is never marked merged and its content
#     never reaches main by itself.
#   * a base branch that belongs to an already-merged PR: merging into it lands nothing on main
#     (2026-09-06: four PRs merged into already-merged bases). Retarget first:
#     gh pr edit N --base main.
#   * a PR that is not open, or is a draft.
#   * a repository whose settings do not allow merge commits.
#
# --auto is passed only when a ruleset exists on main (detected through the rulesets API, never
# assumed): without required checks, auto-merge merges at once and protects nothing. Whether the
# ruleset page accepts the fork's check names is to verify when one is created; this script only
# asks whether any ruleset exists.
#
# Env: ROMP_GH names the gh binary (tests stub it); ROMP_ORPHANS_LIMIT passes through to
# pr-orphans.sh. Exit 2 on a refusal or usage error, 1 when gh fails.
set -euo pipefail

cd "$(cd "$(dirname "$0")/.." && pwd)"
GH="${ROMP_GH:-gh}"
MAIN="${ROMP_MAIN_BRANCH:-main}"

usage() { echo "usage: scripts/land.sh N [M]   (PR numbers; merge commits only)" >&2; exit 2; }

prs=()
for arg in "$@"; do
    case "$arg" in
        --squash|-s|--rebase|-r)
            echo "land: refused: $arg. Merge commits only: a squash or rebase leaves a stacked PR open and its content off $MAIN." >&2
            exit 2 ;;
        --*) usage ;;
        *) [[ "$arg" =~ ^[0-9]+$ ]] || usage; prs+=("$arg") ;;
    esac
done
[ "${#prs[@]}" -ge 1 ] && [ "${#prs[@]}" -le 2 ] || usage

# Repository settings: merge commits must be allowed, and the other two methods being off is what
# makes the wrong click impossible (a warning here, not a refusal: the settings are the maintainer's).
settings="$("$GH" repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed 2>/dev/null || echo '{}')"
if printf '%s' "$settings" | grep -q '"mergeCommitAllowed": *false'; then
    echo "land: refused: the repository does not allow merge commits (gh repo edit --enable-merge-commit)" >&2
    exit 2
fi
if printf '%s' "$settings" | grep -Eq '"(squashMergeAllowed|rebaseMergeAllowed)": *true'; then
    echo "land: warning: squash or rebase merges are still enabled in the repository settings" >&2
fi

auto=()
if [ "$("$GH" api 'repos/{owner}/{repo}/rulesets' --jq 'length' 2>/dev/null || echo 0)" != "0" ]; then
    auto=(--auto)
    echo "land: a ruleset exists on $MAIN; merging with --auto (lands when the required checks pass)"
fi

for n in "${prs[@]}"; do
    view="$("$GH" pr view "$n" --json state,isDraft,baseRefName,headRefName,headRefOid)"
    state="$(printf '%s' "$view" | sed -n 's/.*"state": *"\([A-Z]*\)".*/\1/p')"
    draft="$(printf '%s' "$view" | sed -n 's/.*"isDraft": *\(true\|false\).*/\1/p')"
    base="$(printf '%s' "$view" | sed -n 's/.*"baseRefName": *"\([^"]*\)".*/\1/p')"
    head_sha="$(printf '%s' "$view" | sed -n 's/.*"headRefOid": *"\([0-9a-f]*\)".*/\1/p')"
    if [ "$state" != "OPEN" ]; then
        echo "land: refused: #$n is $state, not open" >&2; exit 2
    fi
    if [ "$draft" = "true" ]; then
        echo "land: refused: #$n is a draft" >&2; exit 2
    fi
    if [ "$base" != "$MAIN" ]; then
        merged_base="$("$GH" pr list --state merged --head "$base" --json number --jq '.[0].number' 2>/dev/null || true)"
        if [ -n "$merged_base" ] && [ "$merged_base" != "null" ]; then
            echo "land: refused: #$n is based on '$base', the branch of merged PR #$merged_base; merging there lands nothing on $MAIN." >&2
            echo "  Retarget it first:  gh pr edit $n --base $MAIN" >&2
            exit 2
        fi
        echo "land: note: #$n is based on '$base', not $MAIN (the base is not a merged PR's branch)"
    fi
    echo "land: merging #$n ($head_sha) with a merge commit"
    "$GH" pr merge "$n" --merge --delete-branch --match-head-commit "$head_sha" "${auto[@]}"
done

exec "$(dirname "$0")/pr-orphans.sh"
