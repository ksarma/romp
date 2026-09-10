#!/usr/bin/env bash
# scripts/fork-remotes.sh — make this clone's remotes safe for a fork.
#
# In a fork there are two repos in play and only ONE of them is ours to write
# to. The failure this prevents is a push that lands on the project we forked
# FROM: a stray `git push upstream`, or a `git push` that a stale
# `remote.pushDefault` aims at the wrong place. Both are easy to type and neither
# is easy to take back, so the guard is configuration rather than care:
#
#   origin    = your fork      fetch + push        (everything goes here;
#                                                   gh's default repository)
#   upstream  = the project    fetch ONLY          (push URL set to a dead
#                                                   sentinel, so a push fails
#                                                   loudly instead of landing)
#
# Git has no "read-only remote" flag, so the sentinel push URL is the mechanism:
# `git push upstream` dies with "does not appear to be a git repository" before
# it can contact anything. That is the loud failure we want — not a silent
# fallback that quietly does the wrong thing.
#
# gh is the other door. `gh pr view N` or `gh pr merge N` without -R resolves N
# against a default repository gh reads from git config: the remote carrying
# `gh-resolved = base` (what `gh repo set-default` writes). gh consults the
# remotes in its own order, upstream before origin, and with no key and no
# terminal to ask on it takes the first: on a fresh clone with both remotes a
# bare PR number is the PROJECT's PR N (verified 2026-09-09 with gh 2.97 — a
# fork PR read as merged because the project's PR of that number was, and a
# merge by number would have aimed at the project). So the guard also sets
# `remote.origin.gh-resolved = base`, with plain git config (no gh call: it
# works offline and in tests), and clears the key from every other remote: gh
# ranks upstream and github above origin, so a key on either shadows origin's,
# and origin should be the only default in any case. --check reads it the way
# it reads pushDefault.
#
# Idempotent: run it whenever, including on a fresh clone. `--check` verifies
# without changing anything and exits non-zero if the clone is unsafe, which is
# what a test (or a paranoid moment) wants.
#
# The upstream URL defaults to the project romp was forked from; override with
# ROMP_UPSTREAM_URL for a differently-rooted fork. `origin` is never rewritten —
# whatever your fork's URL is stays as it is.
set -euo pipefail

# Configure the clone this script lives in, whatever directory it was called
# from. A guard that silently configured whichever repo the shell happened to be
# sitting in would be worse than no guard: you would read "configured" and trust
# the wrong clone.
cd "$(cd "$(dirname "$0")/.." && pwd)"

UPSTREAM_URL="${ROMP_UPSTREAM_URL:-https://github.com/romp-on/romp.git}"
NOPUSH="no-push://upstream-is-fetch-only"   # not a URL git can resolve, on purpose

check_only=0
case "${1:-}" in
    --check) check_only=1 ;;
    "") ;;
    *) echo "usage: scripts/fork-remotes.sh [--check]" >&2; exit 2 ;;
esac

git rev-parse --git-dir >/dev/null 2>&1 || { echo "fork-remotes: not a git clone" >&2; exit 2; }

# Compare repos by identity, not by string: https/ssh/.git-suffix spellings of
# the same repo must count as equal, or the "origin is not upstream" guard below
# would wave through an ssh-cloned upstream.
repo_id() {
    printf '%s' "$1" \
        | sed -e 's#^git@\([^:]*\):#\1/#' -e 's#^[a-z+]*://##' -e 's#^[^@/]*@##' \
              -e 's#\.git$##' -e 's#/*$##' \
        | tr '[:upper:]' '[:lower:]'
}

url_of() { git remote get-url "$1" 2>/dev/null || true; }

origin_url="$(url_of origin)"
[ -n "$origin_url" ] || { echo "fork-remotes: this clone has no 'origin' remote" >&2; exit 2; }

# The one thing we cannot fix by ourselves. If origin IS the upstream project,
# this is not a fork clone (or someone re-pointed origin), and setting up
# fetch-only upstream would leave every push aimed at the project. Say so and
# stop rather than configure something misleading.
if [ "$(repo_id "$origin_url")" = "$(repo_id "$UPSTREAM_URL")" ]; then
    cat >&2 <<EOF
fork-remotes: origin points at the upstream project, not at your fork.
  origin = $origin_url
Point origin at your fork first:
  git remote set-url origin <your-fork-url>
EOF
    exit 1
fi

problems=0
note() { problems=$((problems + 1)); echo "  ✗ $1"; }

if [ $check_only -eq 1 ]; then
    echo "fork-remotes: checking"
    up_fetch="$(url_of upstream)"
    if [ -z "$up_fetch" ]; then
        note "no 'upstream' remote (nothing to compare the fork against)"
    elif [ "$(repo_id "$up_fetch")" != "$(repo_id "$UPSTREAM_URL")" ]; then
        note "upstream fetches from $up_fetch, expected $UPSTREAM_URL"
    fi
    up_push="$(git remote get-url --push upstream 2>/dev/null || true)"
    if [ -n "$up_fetch" ] && [ "$up_push" != "$NOPUSH" ]; then
        note "upstream is PUSHABLE ($up_push) — a stray push would land on the project"
    fi
    # origin's PUSH url is separate from its fetch url; the repo_id check at the top read only fetch.
    # A push url repointed at the project sends a bare push there while everything else looks fine.
    origin_push="$(git remote get-url --push origin 2>/dev/null || true)"
    if [ -n "$origin_push" ] && [ "$(repo_id "$origin_push")" != "$(repo_id "$origin_url")" ]; then
        note "origin PUSHES to $origin_push, not your fork — a bare push would not land on the fork"
    fi
    pd="$(git config --get remote.pushDefault || true)"
    if [ -n "$pd" ] && [ "$pd" != "origin" ]; then
        note "remote.pushDefault is '$pd' — a bare 'git push' would not go to your fork"
    fi
    # branch.<name>.pushRemote OVERRIDES remote.pushDefault, so checking only pushDefault above misses
    # a per-branch push aimed elsewhere. Anything but 'origin' is a bare push that skips the fork.
    while read -r _pr_key _pr_val; do
        [ -z "$_pr_key" ] && continue
        [ "$_pr_val" = "origin" ] && continue
        note "$_pr_key is '$_pr_val' — a bare push from that branch would not go to your fork"
    done < <(git config --get-regexp '^branch\..*\.pushRemote$' 2>/dev/null || true)
    # gh's default repository (see the header): origin must carry `gh-resolved = base` and no other
    # remote may carry the key at all (gh reads upstream's and github's before origin's, and a
    # default anywhere but origin is one too many). A value other than 'base' on origin names some
    # OWNER/REPO outright, which gh then uses instead of origin.
    gh_origin="$(git config --get remote.origin.gh-resolved || true)"
    if [ -z "$gh_origin" ]; then
        note "gh has no default repository (remote.origin.gh-resolved is unset) — a bare 'gh pr merge N' from a script would aim at the project, not your fork"
    elif [ "$gh_origin" != "base" ]; then
        note "remote.origin.gh-resolved is '$gh_origin', not 'base' — gh would resolve a bare PR number against that repo, not your fork"
    fi
    while read -r _gh_key _gh_val; do
        [ -z "$_gh_key" ] && continue
        [ "$_gh_key" = "remote.origin.gh-resolved" ] && continue
        note "$_gh_key is '$_gh_val' — only origin should carry gh's default-repository key; gh may resolve a bare PR number there, not on your fork"
    done < <(git config --get-regexp '^remote\..*\.gh-resolved$' 2>/dev/null || true)
    if [ $problems -eq 0 ]; then
        echo "  ✓ origin (your fork) is the only pushable remote and gh's default repository"
        exit 0
    fi
    echo "Run scripts/fork-remotes.sh to fix." >&2
    exit 1
fi

if [ -n "$(url_of upstream)" ]; then
    git remote set-url upstream "$UPSTREAM_URL"
else
    git remote add upstream "$UPSTREAM_URL"
fi
git remote set-url --push upstream "$NOPUSH"
git config remote.pushDefault origin
# Fix the two overrides --check now also inspects, so "run fork-remotes.sh to fix" is honest: a
# repointed origin push url, and any per-branch pushRemote aimed away from the fork (these override
# remote.pushDefault). origin's push url is reset to its own fetch url; a pushRemote pointing AT
# origin is already safe and left alone.
git remote set-url --push origin "$origin_url"
while read -r _pr_key _pr_val; do
    [ -z "$_pr_key" ] && continue
    [ "$_pr_val" = "origin" ] && continue
    git config --unset "$_pr_key" || true
done < <(git config --get-regexp '^branch\..*\.pushRemote$' 2>/dev/null || true)
# gh's default repository is origin, and origin alone: the same key on upstream or github is read
# before origin's (see the header), and on any remote it is a second default, so it goes too.
# --replace-all, because a hand `git config --add` can leave two values under origin's key and a
# plain set then refuses to overwrite them, which would stop set mode after the push guards.
git config --replace-all remote.origin.gh-resolved base
while read -r _gh_key _gh_val; do
    [ -z "$_gh_key" ] && continue
    [ "$_gh_key" = "remote.origin.gh-resolved" ] && continue
    git config --unset "$_gh_key" || true
done < <(git config --get-regexp '^remote\..*\.gh-resolved$' 2>/dev/null || true)

echo "fork-remotes: configured"
echo "  origin   $origin_url  (fetch + push — your fork; gh's default repository)"
echo "  upstream $UPSTREAM_URL  (fetch only; push disabled)"
echo "  a bare 'git push' goes to origin, and so does a bare 'gh pr <cmd> N'"
echo
echo "Check what the project has added since:  scripts/upstream-check.sh"
