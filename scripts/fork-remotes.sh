#!/usr/bin/env bash
# scripts/fork-remotes.sh — make this clone's remotes safe for a fork.
#
# In a fork there are two repos in play and only ONE of them is ours to write
# to. The failure this prevents is a push that lands on the project we forked
# FROM: a stray `git push upstream`, or a `git push` that a stale
# `remote.pushDefault` aims at the wrong place. Both are easy to type and neither
# is easy to take back, so the guard is configuration rather than care:
#
#   origin    = your fork      fetch + push        (everything goes here)
#   upstream  = the project    fetch ONLY          (push URL set to a dead
#                                                   sentinel, so a push fails
#                                                   loudly instead of landing)
#
# Git has no "read-only remote" flag, so the sentinel push URL is the mechanism:
# `git push upstream` dies with "does not appear to be a git repository" before
# it can contact anything. That is the loud failure we want — not a silent
# fallback that quietly does the wrong thing.
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
    if [ $problems -eq 0 ]; then
        echo "  ✓ origin (your fork) is the only pushable remote"
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

echo "fork-remotes: configured"
echo "  origin   $origin_url  (fetch + push — your fork)"
echo "  upstream $UPSTREAM_URL  (fetch only; push disabled)"
echo "  a bare 'git push' goes to origin"
echo
echo "Check what the project has added since:  scripts/upstream-check.sh"
