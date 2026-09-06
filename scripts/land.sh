#!/usr/bin/env bash
# scripts/land.sh [--auto] [--into-open-pr] N [M]: merge one or two PRs alone, each with a merge
# commit.
#
# The batch (scripts/batch.py) is how PRs normally land; this is the path for an urgent fix or a
# one-file ledger PR that conflicts with nothing. Per PR it runs
#   gh pr merge N --merge --match-head-commit <head> [--auto]
# and afterward scripts/pr-orphans.sh, so a merge that strands a dependent is reported at once.
#
# Refusals (exit 2), each the plain statement of a rule the repository already has. Every PR is
# checked before any is merged, so a refusal never follows a merge:
#   * --squash / --rebase (or -s / -r) anywhere on the command line: merge commits only. A squash
#     or rebase rewrites SHAs, so a PR stacked on this one is never marked merged and its content
#     never reaches main by itself.
#   * a PR that is not open, or is a draft.
#   * a repository whose settings do not allow merge commits.
#   * a base branch other than main. Three cases, checked in this order because branch names are
#     reused here (an open PR's head first, so a name a merged PR once used is not mistaken for it):
#       - the head of an OPEN PR: merging there puts the content on that branch only, where it
#         reaches main if and when that PR merges, and pr-orphans.sh reports it until then.
#         --into-open-pr overrides this one case, for a chain the maintainer wants merged by hand
#         from the bottom up; the batch orders such a pair on its own.
#       - the head of a MERGED PR: the branch is gone or stale and the merge lands nothing on main
#         (2026-09-06: four PRs merged into already-merged bases). Retarget first:
#         gh pr edit N --base main.
#       - a branch no PR has as its head: the same retarget.
#   * --auto when the repository's "Allow auto-merge" setting is off (GitHub: auto-merge must be
#     enabled for the repository before a PR can use it; REST allow_auto_merge, off on this fork at
#     writing), or when nothing is required on main (no ruleset rule, no branch protection): with
#     nothing to wait for, --auto merges at once and protects nothing. Both are read, never
#     assumed; turning the setting on is the maintainer's call (gh repo edit --enable-auto-merge).
#
# Branches: never --delete-branch. gh's flag also deletes the LOCAL branch of that name, and in
# this repo every PR branch is checked out in a sibling worktree, so the local delete fails after
# the remote merge has already happened and the script would stop there (a second PR unmerged, the
# orphan check skipped). The remote branch is GitHub's to delete when the repository deletes
# branches on merge (it does here); when that setting is off, the remote ref is deleted through the
# API once the PR reads MERGED. Local branches and worktrees are the owning session's.
#
# Env: ROMP_GH names the gh binary (tests stub it); ROMP_ORPHANS_LIMIT passes through to
# pr-orphans.sh. Exit 2 on a refusal or usage error, 1 when gh fails.
set -euo pipefail

cd "$(cd "$(dirname "$0")/.." && pwd)"
GH="${ROMP_GH:-gh}"
MAIN="${ROMP_MAIN_BRANCH:-main}"

usage() { echo "usage: scripts/land.sh [--auto] [--into-open-pr] N [M]   (PR numbers; merge commits only)" >&2; exit 2; }

json_field() {  # json_field <json> <key>: the string, boolean or number value of a top-level key
    printf '%s' "$1" | sed -n 's/.*"'"$2"'": *"\{0,1\}\([^",}]*\)"\{0,1\}.*/\1/p' | head -n1
}

prs=()
auto=0
into_open=0
for arg in "$@"; do
    case "$arg" in
        --squash|-s|--rebase|-r)
            echo "land: refused: $arg. Merge commits only: a squash or rebase leaves a stacked PR open and its content off $MAIN." >&2
            exit 2 ;;
        --auto) auto=1 ;;
        --into-open-pr) into_open=1 ;;
        --*) usage ;;
        *) [[ "$arg" =~ ^[0-9]+$ ]] || usage; prs+=("$arg") ;;
    esac
done
[ "${#prs[@]}" -ge 1 ] && [ "${#prs[@]}" -le 2 ] || usage

# Repository settings: merge commits must be allowed, and the other two methods being off is what
# makes the wrong click impossible (a warning here, not a refusal: the settings are the maintainer's).
settings="$("$GH" repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,deleteBranchOnMerge 2>/dev/null || echo '{}')"
if [ "$(json_field "$settings" mergeCommitAllowed)" = "false" ]; then
    echo "land: refused: the repository does not allow merge commits (gh repo edit --enable-merge-commit)" >&2
    exit 2
fi
if printf '%s' "$settings" | grep -Eq '"(squashMergeAllowed|rebaseMergeAllowed)": *true'; then
    echo "land: warning: squash or rebase merges are still enabled in the repository settings" >&2
fi
deletes_on_merge="$(json_field "$settings" deleteBranchOnMerge)"

auto_flag=()
if [ "$auto" = 1 ]; then
    allow_auto="$("$GH" api 'repos/{owner}/{repo}' --jq '.allow_auto_merge' 2>/dev/null || echo unknown)"
    if [ "$allow_auto" != "true" ]; then
        echo "land: refused: --auto needs the repository's \"Allow auto-merge\" setting, which is off (allow_auto_merge: $allow_auto)." >&2
        echo "  Turning it on is the maintainer's call: gh repo edit --enable-auto-merge. Merge without --auto instead." >&2
        exit 2
    fi
    rules="$("$GH" api "repos/{owner}/{repo}/rules/branches/$MAIN" --jq 'length' 2>/dev/null || echo 0)"
    if [ "$rules" = "0" ] && ! "$GH" api "repos/{owner}/{repo}/branches/$MAIN/protection" >/dev/null 2>&1; then
        echo "land: refused: --auto with nothing required on $MAIN (no ruleset rule, no branch protection) merges at once and protects nothing; merge without --auto." >&2
        exit 2
    fi
    auto_flag=(--auto)
    echo "land: merging with --auto (auto-merge is allowed and $MAIN has required rules; a PR whose checks are pending lands when they pass)"
fi

# Every PR is read and checked before any is merged, so a refusal never follows a merge (the second
# PR of a pair is checked before the first one lands).
head_shas=()
head_refs=()
for n in "${prs[@]}"; do
    view="$("$GH" pr view "$n" --json state,isDraft,baseRefName,headRefName,headRefOid)"
    state="$(json_field "$view" state)"
    draft="$(json_field "$view" isDraft)"
    base="$(json_field "$view" baseRefName)"
    if [ "$state" != "OPEN" ]; then
        echo "land: refused: #$n is $state, not open" >&2; exit 2
    fi
    if [ "$draft" = "true" ]; then
        echo "land: refused: #$n is a draft" >&2; exit 2
    fi
    if [ "$base" != "$MAIN" ]; then
        open_base="$("$GH" pr list --state open --head "$base" --json number --jq '.[0].number' 2>/dev/null || true)"
        if [ -n "$open_base" ] && [ "$open_base" != "null" ]; then
            if [ "$into_open" != 1 ]; then
                echo "land: refused: #$n is based on '$base', the branch of open PR #$open_base. Merging there puts #$n's content on that branch only; it reaches $MAIN only if #$open_base merges, and pr-orphans.sh reports it until then." >&2
                echo "  Retarget it (gh pr edit $n --base $MAIN), leave the pair to the batch, or pass --into-open-pr to merge into #$open_base's branch anyway." >&2
                exit 2
            fi
            echo "land: note: #$n merges into '$base' (open PR #$open_base), not $MAIN, as --into-open-pr asked; its content reaches $MAIN only when #$open_base merges, and pr-orphans.sh will report it until then"
        else
            merged_base="$("$GH" pr list --state merged --head "$base" --json number --jq '.[0].number' 2>/dev/null || true)"
            if [ -n "$merged_base" ] && [ "$merged_base" != "null" ]; then
                echo "land: refused: #$n is based on '$base', the branch of merged PR #$merged_base; merging there lands nothing on $MAIN." >&2
            else
                echo "land: refused: #$n is based on '$base', not $MAIN, and no PR has that branch as its head; merging there lands nothing on $MAIN." >&2
            fi
            echo "  Retarget it first:  gh pr edit $n --base $MAIN" >&2
            exit 2
        fi
    fi
    head_shas+=("$(json_field "$view" headRefOid)")
    head_refs+=("$(json_field "$view" headRefName)")
done

for i in "${!prs[@]}"; do
    n="${prs[$i]}"
    head_sha="${head_shas[$i]}"
    head_ref="${head_refs[$i]}"
    echo "land: merging #$n ($head_sha) with a merge commit"
    "$GH" pr merge "$n" --merge --match-head-commit "$head_sha" "${auto_flag[@]}"
    after="$(json_field "$("$GH" pr view "$n" --json state)" state)"
    if [ "$after" != "MERGED" ]; then
        echo "land: #$n reads $after after the merge call (auto-merge armed: it lands when the required checks pass); nothing more to do for it now"
        continue
    fi
    if [ "$deletes_on_merge" = "true" ]; then
        echo "land: #$n merged; the repository deletes '$head_ref' on merge (local branches are untouched)"
    else
        echo "land: #$n merged; deleting remote branch '$head_ref' (the repository does not delete branches on merge; local branches are untouched)"
        "$GH" api -X DELETE "repos/{owner}/{repo}/git/refs/heads/$head_ref" >/dev/null \
            || echo "land: warning: could not delete remote branch '$head_ref'; delete it by hand so a PR based on it is retargeted" >&2
    fi
done

exec "$(dirname "$0")/pr-orphans.sh"
