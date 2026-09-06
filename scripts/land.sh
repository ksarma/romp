#!/usr/bin/env bash
# scripts/land.sh [--auto] [--into-open-pr] N [M]: merge one or two PRs alone, each with a merge
# commit. `scripts/land.sh --help` prints the usage and the table of refusals; that table lives in
# help() below and nowhere else, so this header does not repeat it.
#
# The batch (scripts/batch.py) is how PRs normally land; this is the path for an urgent fix or a
# one-file ledger PR that conflicts with nothing. Per PR it runs
#   gh pr merge N --merge --match-head-commit <head> [--auto]
# and afterward scripts/pr-orphans.sh, so a merge that strands a dependent is reported at once.
#
# Every PR is read and checked (state, draft, base, mergeability, checks) before any is merged, so a
# refusal never follows a merge. Right before its own merge each PR is read again: a head that
# moved, or anything the first check would have refused, stops the run (nothing more merges; the
# orphan check still runs), and a PR the first merge marked merged is skipped. A pair whose one
# member is based on the other's branch merges the lower PR first, whichever order was given: the
# lower branch is deleted on merge (the repository setting, or the API call below), GitHub retargets
# the upper PR to main, and its head has not moved. Given top-down, the upper merge advances the
# lower branch and the second merge, pinned to the old head, fails with the content stranded
# (2026-09-06 review).
#
# Branches: never --delete-branch. gh's flag also deletes the LOCAL branch of that name, and in
# this repo every PR branch is checked out in a sibling worktree, so the local delete fails after
# the remote merge has already happened and the script would stop there (a second PR unmerged, the
# orphan check skipped). The remote branch is GitHub's to delete when the repository deletes
# branches on merge (it does here); when that setting is off, the remote ref is deleted through the
# API once the PR reads MERGED. Local branches and worktrees are the owning session's.
#
# gh's JSON is reduced by gh's own --jq to one word per line, or one row of fields joined on US
# (\x1f, a byte neither a branch name nor a check name can hold; git refuses control characters in
# a ref name); the shell parses no JSON and none of gh's prose. A sed pattern that once read the
# fields ended a value at the first ',' or '}', both legal in a branch name (2026-09-06 review). The
# one thing read from a gh error line is the status gh appends to every API error, `(HTTP 404)`,
# which tells "no branch protection" from a read that failed.
#
# Env: ROMP_GH names the gh binary (tests stub it); ROMP_ORPHANS_LIMIT passes through to
# pr-orphans.sh. Exit 2 on a refusal, a stop or a usage error, 1 when gh fails; otherwise
# pr-orphans.sh's exit (0 clean, 1 when a merged PR's content is not on main).
set -euo pipefail

ORPHANS="$(cd "$(dirname "$0")" && pwd)/pr-orphans.sh"
cd "$(cd "$(dirname "$0")/.." && pwd)"
GH="${ROMP_GH:-gh}"
MAIN="${ROMP_MAIN_BRANCH:-main}"

help() {
    cat <<EOF
usage: scripts/land.sh [--auto] [--into-open-pr] N [M]
       scripts/land.sh --help

Merges one or two PRs (numbers), each with a merge commit:
  gh pr merge N --merge --match-head-commit <head> [--auto]
then runs scripts/pr-orphans.sh, which reports a merged PR whose content is not on $MAIN. The batch
(scripts/batch.py) is how PRs normally land; this is for an urgent fix or a one-file PR that
conflicts with nothing.

Refusals (exit 2). Every PR is read and checked before any is merged, so a refusal never follows a
merge; the second PR of a pair is checked before the first one lands.
  --squash / --rebase (-s / -r)  Merge commits only. A squash or rebase rewrites SHAs, so a PR
                                 stacked on this one is never marked merged and its content never
                                 reaches $MAIN by itself.
  not open, or a draft           The PR's state and draft flag as GitHub reports them.
  merge commits not allowed      The repository setting (gh repo edit --enable-merge-commit).
  conflicting                    mergeable: CONFLICTING against its base. Resolve on the branch.
  mergeability not computed      mergeable: UNKNOWN. GitHub computes it after a push; re-run in a
                                 moment.
  checks failing                 A check run or commit status at the head that is not SUCCESS,
                                 NEUTRAL or SKIPPED, with or without --auto.
  checks pending                 Without --auto. Wait for them, or pass --auto to land when they
                                 pass. No checks at all is noted, not refused.
  blocked                        mergeStateStatus: BLOCKED, a rule on $MAIN is not met. Without
                                 --auto; with it the merge is armed and lands when the rule is met.
  behind                         mergeStateStatus: BEHIND, $MAIN moved and the rule wants the branch
                                 up to date: gh pr update-branch N, then re-run.
  a base other than $MAIN         Three cases, checked in this order because branch names are reused
                                 here (an open PR's head first, so a name a merged PR once used is
                                 not mistaken for it):
                                 - the head of an OPEN PR: merging there puts the content on that
                                   branch only, where it reaches $MAIN if and when that PR merges,
                                   and pr-orphans.sh reports it until then. --into-open-pr overrides
                                   this one case, to merge the upper PR into the lower one's branch
                                   on purpose. When that PR is the other member of the pair no flag
                                   is needed:
                                   the lower PR merges first and the upper one lands on $MAIN once
                                   GitHub retargets it.
                                 - the head of a MERGED PR: the branch is gone or stale and the
                                   merge lands nothing on $MAIN. Retarget: gh pr edit N --base $MAIN.
                                 - a branch no PR has as its head: the same retarget.
  --auto without its two preconditions, each read, never assumed:
    "Allow auto-merge"           The repository setting (REST allow_auto_merge; off on this fork at
                                 writing). Turning it on is the maintainer's call:
                                 gh repo edit --enable-auto-merge.
    a rule on $MAIN that gates    A ruleset rule of type required_status_checks, pull_request,
    a merge                      required_deployments, merge_queue or code_scanning, or classic
                                 branch protection with required status checks or required reviews.
                                 A rule that only blocks force pushes or deletion does not count:
                                 with nothing to wait for, --auto merges at once and protects
                                 nothing. A rules or protection read that fails for any reason but
                                 a 404 is refused as unreadable, with gh's error.

Stops (exit 2), after a merge. Each PR is read again right before its own merge, and the run stops
when that read would have been refused (state, base, mergeability, checks), or when the PR's
head moved since it was checked (someone pushed); nothing more is merged and the orphan check
still runs. A PR the first merge already marked merged (its commits were in the first PR's branch)
is skipped, not failed.

Branches: never --delete-branch (gh's flag also deletes the local branch, which is checked out in a
session's worktree here). The remote branch is deleted by the repository setting, or through the
API when that setting is off; local branches are never touched.

Env: ROMP_GH names the gh binary; ROMP_ORPHANS_LIMIT passes through to pr-orphans.sh.
Exit 2 on a refusal, a stop or a usage error, 1 when gh fails; otherwise pr-orphans.sh's exit.
EOF
}

usage() { echo "usage: scripts/land.sh [--auto] [--into-open-pr] N [M]   (PR numbers; merge commits only; --help for the refusals)" >&2; exit 2; }

# row_of <keys...>: a --jq expression giving the named top-level fields as one US-joined row, null
# as empty, booleans and numbers as words. Read back with `IFS="$US" read -r`. The separator is
# spelled as jq's escape, passed as an argument: printf would turn it into the byte in a format.
row_of() {
    local keys="" k
    for k in "$@"; do keys="${keys:+$keys, }.$k"; done
    printf '[%s] | map(if . == null then "" else tostring end) | join("%s")' "$keys" '\u001f'
}
US=$'\x1f'

list() {  # list "<words>": the words ", "-joined, with a leading space, for a message
    local out="" w
    for w in $1; do out="${out:+$out,} $w"; done
    printf '%s' "$out"
}

prs=()
auto=0
into_open=0
for arg in "$@"; do
    case "$arg" in
        --help|-h) help; exit 0 ;;
        --squash|-s|--rebase|-r)
            echo "land: refused: $arg. Merge commits only: a squash or rebase leaves a stacked PR open and its content off $MAIN." >&2
            exit 2 ;;
        --auto) auto=1 ;;
        --into-open-pr) into_open=1 ;;
        --*) usage ;;
        *) [[ "$arg" =~ ^[0-9]+$ ]] || usage; prs+=("$arg") ;;
    esac
done
if [ "${#prs[@]}" -lt 1 ] || [ "${#prs[@]}" -gt 2 ]; then usage; fi

# Repository settings: merge commits must be allowed, and the other two methods being off is what
# makes the wrong click impossible (a warning here, not a refusal: the settings are the maintainer's).
settings="$("$GH" repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,deleteBranchOnMerge \
    --jq "$(row_of mergeCommitAllowed squashMergeAllowed rebaseMergeAllowed deleteBranchOnMerge)" 2>/dev/null || true)"
IFS="$US" read -r merge_commit_allowed squash_allowed rebase_allowed deletes_on_merge <<< "$settings"
if [ "$merge_commit_allowed" = "false" ]; then
    echo "land: refused: the repository does not allow merge commits (gh repo edit --enable-merge-commit)" >&2
    exit 2
fi
if [ "$squash_allowed" = "true" ] || [ "$rebase_allowed" = "true" ]; then
    echo "land: warning: squash or rebase merges are still enabled in the repository settings" >&2
fi

auto_flag=()
if [ "$auto" = 1 ]; then
    allow_auto="$("$GH" api 'repos/{owner}/{repo}' --jq '.allow_auto_merge' 2>/dev/null || echo unknown)"
    if [ "$allow_auto" != "true" ]; then
        echo "land: refused: --auto needs the repository's \"Allow auto-merge\" setting, which is off (allow_auto_merge: $allow_auto)." >&2
        echo "  Turning it on is the maintainer's call: gh repo edit --enable-auto-merge. Merge without --auto instead." >&2
        exit 2
    fi
    # A rule on main that gates a merge. The rules endpoint lists every rule that applies to the
    # branch, the protective ones included (non_fast_forward, deletion, ...), so the types are read,
    # not counted. It answers [] for a branch with no rules, so a failure is a failed read, not "none".
    if ! rule_types="$("$GH" api "repos/{owner}/{repo}/rules/branches/$MAIN" --jq '.[].type' 2>&1)"; then
        echo "land: refused: --auto, and could not read the rules on $MAIN: $rule_types" >&2
        exit 2
    fi
    gating=""; other=""
    for t in $rule_types; do
        case "$t" in
            required_status_checks|pull_request|required_deployments|merge_queue|code_scanning) gating="$gating $t" ;;
            *) other="$other $t" ;;
        esac
    done
    # Classic branch protection: the endpoint 404s for an unprotected branch, its documented answer
    # for "none"; any other failure is a failed read. The keys with a value are what is set.
    protected=0; prot_keys=""; prot_gating=""
    if prot_out="$("$GH" api "repos/{owner}/{repo}/branches/$MAIN/protection" --jq 'to_entries[] | select(.value != null) | .key' 2>&1)"; then
        protected=1
        prot_keys="$prot_out"
        for k in $prot_keys; do
            case "$k" in required_status_checks|required_pull_request_reviews) prot_gating="$prot_gating $k" ;; esac
        done
    elif ! printf '%s' "$prot_out" | grep -q 'HTTP 404'; then
        echo "land: refused: --auto, and could not read $MAIN's branch protection: $prot_out" >&2
        exit 2
    fi
    if [ -z "$gating" ] && [ -z "$prot_gating" ]; then
        what=""
        [ -z "$other" ] || what="ruleset rules$(list "$other"), which protect the branch and gate no merge"
        if [ "$protected" = 1 ]; then
            what="${what:+$what; }branch protection on $MAIN requires no checks and no reviews (set:$(list "$prot_keys"))"
        fi
        if [ -n "$what" ]; then
            echo "land: refused: --auto: no rule on $MAIN gates a merge ($what), so it would merge at once and protect nothing; merge without --auto." >&2
        else
            echo "land: refused: --auto with nothing required on $MAIN (no ruleset rule, no branch protection) merges at once and protects nothing; merge without --auto." >&2
        fi
        exit 2
    fi
    auto_flag=(--auto)
    echo "land: merging with --auto (auto-merge is allowed and $MAIN has required rules that gate a merge:$(list "$gating$prot_gating"); a PR whose checks are pending lands when they pass)"
fi

# read_pr <n>: the fields the checks use, into pr_* variables. Two reads: the flat fields, then the
# check rollup reduced by gh's --jq to one row per check, kind/name/status/conclusion/state (a
# CheckRun has status and conclusion, a commit StatusContext has state). The fields are joined on
# US (\x1f), a byte no check name holds; a '|' shifted the fields of a check named 'build | linux',
# and a tab is IFS whitespace to `read`, which folds the empty fields together.
read_pr() {
    local row
    row="$("$GH" pr view "$1" --json state,isDraft,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus \
        --jq "$(row_of state isDraft baseRefName headRefName headRefOid mergeable mergeStateStatus)")"
    IFS="$US" read -r pr_state pr_draft pr_base pr_head_ref pr_head_sha pr_mergeable pr_mss <<< "$row"
    pr_rollup="$("$GH" pr view "$1" --json statusCheckRollup \
        --jq '(.statusCheckRollup // [])[] | [.__typename, (.name // .context), .status, .conclusion, .state] | map(. // "") | join("\u001f")')"
}

# stash_pr <i> / load_pr <i>: the pr_* variables of prs[i], kept from the first pass.
stash_pr() {
    states[$1]="$pr_state"; drafts[$1]="$pr_draft"; bases[$1]="$pr_base"; head_refs[$1]="$pr_head_ref"
    head_shas[$1]="$pr_head_sha"; mergeables[$1]="$pr_mergeable"; msss[$1]="$pr_mss"; rollups[$1]="$pr_rollup"
}
load_pr() {
    pr_state="${states[$1]}"; pr_draft="${drafts[$1]}"; pr_base="${bases[$1]}"; pr_head_ref="${head_refs[$1]}"
    pr_head_sha="${head_shas[$1]}"; pr_mergeable="${mergeables[$1]}"; pr_mss="${msss[$1]}"; pr_rollup="${rollups[$1]}"
}

# classify_checks <rollup rows>: checks_failing and checks_pending as ", "-joined names, checks_n.
# A run that is not COMPLETED is pending; SUCCESS, NEUTRAL and SKIPPED are green; the rest is red.
classify_checks() {
    local kind name status conclusion cstate word
    checks_failing=""; checks_pending=""; checks_n=0
    while IFS="$US" read -r kind name status conclusion cstate; do
        [ -n "$kind$name$status$conclusion$cstate" ] || continue
        checks_n=$((checks_n + 1))
        if [ "$kind" = StatusContext ]; then word="$cstate"
        elif [ "$status" != COMPLETED ]; then word=PENDING
        else word="$conclusion"; fi
        case "$word" in
            SUCCESS|NEUTRAL|SKIPPED) ;;
            PENDING|QUEUED|IN_PROGRESS|WAITING|REQUESTED|EXPECTED|"") checks_pending="${checks_pending:+$checks_pending, }$name" ;;
            *) checks_failing="${checks_failing:+$checks_failing, }$name ($word)" ;;
        esac
    done <<< "$1"
}

merged_list=""
fail() {  # fail <verb> <message>: a refusal before any merge, or a stop after one; exit 2
    echo "land: $1: $2" >&2
    if [ "$1" = stopped ]; then
        echo "  ${merged_list# } merged before the stop; nothing more is merged. The orphan check runs next." >&2
        "$ORPHANS" || true
    fi
    exit 2
}

notes=1
note() { if [ "$notes" = 1 ]; then echo "land: $*"; fi; }  # printed in the first pass only

# check_pr <i> <verb>: the rules, against the pr_* variables loaded for prs[i]. <verb> is "refused"
# before any merge and "stopped" after one. Order: state, draft, base, mergeability, checks, then
# the merge state, so the message names the first thing the maintainer can act on.
check_pr() {
    local i="$1" verb="$2" n="${prs[$1]}" j other open_base merged_base
    if [ "$pr_state" != "OPEN" ]; then
        fail "$verb" "#$n is $pr_state, not open"
    fi
    if [ "$pr_draft" = "true" ]; then
        fail "$verb" "#$n is a draft"
    fi
    if [ "$pr_base" != "$MAIN" ]; then
        other=""
        for j in "${!prs[@]}"; do
            [ "$j" != "$i" ] && [ "${head_refs[$j]}" = "$pr_base" ] && other="$j"
        done
        if [ -n "$other" ]; then
            if [ "${merged_in_run[$other]}" = 1 ]; then
                fail "$verb" "#$n is still based on '$pr_base', the branch of #${prs[$other]}, which merged in this run; GitHub did not retarget it (the branch was not deleted). Retarget it (gh pr edit $n --base $MAIN) and re-run"
            fi
            note "note: #$n is based on '$pr_base', the branch of #${prs[$other]}, the other PR of this pair: #${prs[$other]} merges first, then #$n lands on $MAIN once GitHub retargets it (the branch is deleted on merge)"
        else
            open_base="$("$GH" pr list --state open --head "$pr_base" --json number --jq '.[0].number' 2>/dev/null || true)"
            if [ -n "$open_base" ] && [ "$open_base" != "null" ]; then
                if [ "$into_open" != 1 ]; then
                    fail "$verb" "$(printf '%s\n  %s' \
                        "#$n is based on '$pr_base', the branch of open PR #$open_base. Merging there puts #$n's content on that branch only; it reaches $MAIN only if #$open_base merges, and pr-orphans.sh reports it until then." \
                        "Retarget it (gh pr edit $n --base $MAIN), leave the pair to the batch, land both here (scripts/land.sh $open_base $n), or pass --into-open-pr to merge into #$open_base's branch anyway.")"
                fi
                note "note: #$n merges into '$pr_base' (open PR #$open_base), not $MAIN, as --into-open-pr asked; its content reaches $MAIN only when #$open_base merges, and pr-orphans.sh will report it until then"
            else
                merged_base="$("$GH" pr list --state merged --head "$pr_base" --json number --jq '.[0].number' 2>/dev/null || true)"
                if [ -n "$merged_base" ] && [ "$merged_base" != "null" ]; then
                    fail "$verb" "$(printf '%s\n  %s' "#$n is based on '$pr_base', the branch of merged PR #$merged_base; merging there lands nothing on $MAIN." \
                        "Retarget it first:  gh pr edit $n --base $MAIN")"
                fi
                fail "$verb" "$(printf '%s\n  %s' "#$n is based on '$pr_base', not $MAIN, and no PR has that branch as its head; merging there lands nothing on $MAIN." \
                    "Retarget it first:  gh pr edit $n --base $MAIN")"
            fi
        fi
    fi
    case "$pr_mergeable" in
        MERGEABLE) ;;
        CONFLICTING) fail "$verb" "#$n conflicts with $pr_base (mergeable: CONFLICTING); resolve on the branch and push, then re-run" ;;
        *) fail "$verb" "#$n's mergeability is not computed yet (mergeable: $pr_mergeable); GitHub computes it after a push, so re-run in a moment" ;;
    esac
    classify_checks "$pr_rollup"
    if [ -n "$checks_failing" ]; then
        fail "$verb" "#$n's checks are failing: $checks_failing"
    fi
    case "$pr_mss" in
        BLOCKED)
            if [ "$auto" != 1 ]; then
                fail "$verb" "#$n is blocked by a rule on $MAIN (mergeStateStatus: BLOCKED); wait for the rule to be met, or pass --auto to land when it is"
            fi
            [ -n "$checks_pending" ] || note "#$n is blocked by a rule on $MAIN (mergeStateStatus: BLOCKED); --auto lands it when the rule is met" ;;
        BEHIND) fail "$verb" "#$n is behind $MAIN (mergeStateStatus: BEHIND): the rule wants the branch up to date; gh pr update-branch $n, then re-run" ;;
    esac
    if [ -n "$checks_pending" ]; then
        if [ "$auto" = 1 ]; then
            note "#$n's checks are pending ($checks_pending); --auto lands it when they pass"
        else
            fail "$verb" "#$n's checks are pending: $checks_pending. Wait for them, or pass --auto to land when they pass"
        fi
    elif [ "$checks_n" = 0 ]; then
        note "note: #$n has no checks reported at its head"
    fi
}

# Pass 1: read every PR, then check every PR, so a refusal never follows a merge.
states=(); drafts=(); bases=(); head_refs=(); head_shas=(); mergeables=(); msss=(); rollups=()
merged_in_run=()
for i in "${!prs[@]}"; do
    read_pr "${prs[$i]}"
    stash_pr "$i"
    merged_in_run[i]=0
done
for i in "${!prs[@]}"; do
    load_pr "$i"
    check_pr "$i" refused
done

# The order: a PR based on the other's branch merges after it, whichever order was given.
order=("${!prs[@]}")
if [ "${#prs[@]}" = 2 ] && [ "${bases[0]}" = "${head_refs[1]}" ]; then
    order=(1 0)
    echo "land: merging #${prs[1]} before #${prs[0]}: #${prs[0]} is based on its branch"
fi

# Pass 2: each PR is read again right before its own merge, and the same rules are applied to what
# was read; a difference after a merge is a stop, not a refusal.
notes=0
verb=refused
for i in "${order[@]}"; do
    n="${prs[$i]}"
    read_pr "$n"
    if [ "$pr_state" = "MERGED" ]; then
        echo "land: #$n was marked merged by an earlier merge of this run; nothing to do for it"
        merged_in_run[i]=1
        continue
    fi
    if [ "$pr_head_sha" != "${head_shas[$i]}" ]; then
        fail "$verb" "#$n's head moved since it was checked (${head_shas[$i]:0:10}, now ${pr_head_sha:0:10}); someone pushed. Re-run to check the new head"
    fi
    check_pr "$i" "$verb"
    echo "land: merging #$n ($pr_head_sha) with a merge commit"
    if ! "$GH" pr merge "$n" --merge --match-head-commit "$pr_head_sha" "${auto_flag[@]}"; then
        echo "land: gh could not merge #$n; stopping.${merged_list:+ Merged in this run:$merged_list.} The orphan check runs next." >&2
        "$ORPHANS" || true
        exit 1
    fi
    verb=stopped
    after="$("$GH" pr view "$n" --json state --jq .state)"
    if [ "$after" != "MERGED" ]; then
        echo "land: #$n reads $after after the merge call (auto-merge armed: it lands when the required checks pass); nothing more to do for it now"
        continue
    fi
    merged_in_run[i]=1
    merged_list="$merged_list #$n"
    if [ "$deletes_on_merge" = "true" ]; then
        echo "land: #$n merged; the repository deletes '$pr_head_ref' on merge (local branches are untouched)"
    else
        echo "land: #$n merged; deleting remote branch '$pr_head_ref' (the repository does not delete branches on merge; local branches are untouched)"
        "$GH" api -X DELETE "repos/{owner}/{repo}/git/refs/heads/$pr_head_ref" >/dev/null \
            || echo "land: warning: could not delete remote branch '$pr_head_ref'; delete it by hand so a PR based on it is retargeted" >&2
    fi
done

exec "$ORPHANS"
