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
# bare PR number is the PROJECT's PR N (verified 2026-09-09 with gh 2.97: a
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
# would wave through an ssh-cloned upstream. Trailing slashes are stripped before
# and after the .git suffix, so 'X.git/' and 'X/.git' both read as 'X'. Limits:
# an ssh port, a user other than git in user@host:, and a doubled slash each make
# one repository read as two; and every url is lowercased, so two local paths
# that differ only in case read as one.
repo_id() {
    printf '%s' "$1" \
        | sed -e 's#^git@\([^:]*\):#\1/#' -e 's#^[a-z+]*://##' -e 's#^[^@/]*@##' \
              -e 's#/*$##' -e 's#\.git$##' -e 's#/*$##' \
        | tr '[:upper:]' '[:lower:]'
}

url_of() { git remote get-url "$1" 2>/dev/null || true; }

# Every url a remote carries, one "<fetch|push> <url>" line each, as git resolves them: --all for a
# remote with several, and get-url applies insteadOf and pushInsteadOf rewrites, so a url is read the
# way a fetch or a push would use it. A remote with no push url prints its fetch urls under push.
# The -- keeps a remote whose name starts with a dash from being read as an option.
urls_of() {
    git remote get-url --all -- "$1" 2>/dev/null | sed 's/^/fetch /' || true
    git remote get-url --push --all -- "$1" 2>/dev/null | sed 's/^/push /' || true
}

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
shared=0   # of those, the shared-repository notes, which name their own fix (the fetch note's ends with a rerun)
rerun_moves_pushes=0   # 1 once a fetch note fires while a push to origin goes somewhere its fetch url is not, which withholds the rerun line
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
    # origin set by mistake to the url of another remote the clone carries (another fork kept as a
    # second remote, say) passes every check above: they compare origin only with the project's url
    # and with itself. A fetch from origin and a bare gh PR number would then read that other
    # repository, and pushes may go there too. So each of origin's urls is compared by repo_id with
    # each url of every other remote, and one note per remote names both, with the first match.
    # origin's urls come in three kinds, read in this order: its first url, the one git fetches from
    # (fetch); any url after the first (extra), which git never fetches from but pushes to when origin
    # has no push url; and its push urls (push). The dead sentinel names no repository and is skipped
    # on origin's side, which is enough (a match needs origin to carry it too): origin's push url set
    # to it is the push check's finding above, which a rerun fixes.
    origin_urls="$(urls_of origin | awk '$1 == "fetch" && seen++ { sub(/^fetch/, "extra") } { print }')"
    # where a push to origin goes, read from git rather than assumed: every push url, or every url
    # when origin has no push url
    origin_pushes="$(printf '%s\n' "$origin_urls" | awk '$1 == "push" { sub(/^push /, ""); printf "%s%s", (n++ ? ", " : ""), $0 }')"
    while IFS= read -r _dup_r; do
        case "$_dup_r" in ""|origin) continue ;; esac
        _dup_hit=""
        while read -r _dup_okind _dup_ourl; do
            case "$_dup_ourl" in ""|"$NOPUSH") continue ;; esac
            while read -r _dup_rkind _dup_rurl; do
                [ -n "$_dup_rurl" ] || continue
                if [ "$(repo_id "$_dup_ourl")" = "$(repo_id "$_dup_rurl")" ]; then
                    _dup_hit="origin's $_dup_okind url $_dup_ourl is the same repository as remote '$_dup_r' ($_dup_rkind url $_dup_rurl)"
                    break 2
                fi
            done <<<"$(urls_of "$_dup_r")"
        done <<<"$origin_urls"
        [ -n "$_dup_hit" ] || continue
        # Each note names its own fix and does not count toward the rerun advice. A rerun never
        # rewrites origin's fetch url or removes an extra url, and resets origin's push url to its
        # fetch url unless origin carries several push urls (its set-url refuses those). So:
        # - fetch: a rerun copies origin's fetch url, the one the note names, onto its push url. Where a
        #   push to origin already goes only to that repository, that moves no push, and the rerun line
        #   stays for the other notes (upstream given the fork's url, say, which a rerun fixes). Where a
        #   push goes anywhere else, the rerun would move it onto the repository the note names, so the
        #   standalone line is withheld whatever else fired. The note's steps cannot move a push onto
        #   that repository as long as each succeeds: the fetch url first, the push url next, the rerun
        #   last. On an origin with several urls the first step names the url to replace, the form git
        #   accepts there (a plain set-url origin refuses a remote with several).
        # - extra: a rerun cannot remove it, so the note names the git command that does.
        # - push: a match on origin's one push url is also the push check's finding above (it cannot
        #   match the fetch url, or the fetch note would have fired), which brings the rerun line
        #   back; a match on a second push url the rerun cannot clear.
        shared=$((shared + 1))
        case "$_dup_okind" in
            fetch)
                while read -r _dup_pkind _dup_purl; do
                    if [ "$_dup_pkind" = push ] && [ "$(repo_id "$_dup_purl")" != "$(repo_id "$origin_url")" ]; then
                        rerun_moves_pushes=1
                    fi
                done <<<"$origin_urls"
                _dup_set="git remote set-url origin <your-fork-url>"
                case "$origin_urls" in
                    *$'\n'"extra "*) _dup_set="git remote set-url origin <your-fork-url> <that-url>, which replaces only that one of origin's urls" ;;
                esac
                note "$_dup_hit: if origin was set to that url by mistake, a fetch from origin and a bare gh PR number read that repository, not your fork, and a push to origin goes to $origin_pushes. Point origin's fetch and push urls at your fork ($_dup_set, then git remote set-url --push origin <your-fork-url>), then run scripts/fork-remotes.sh; or remove '$_dup_r' if it is a second name for your fork"
                ;;
            extra)
                note "$_dup_hit: git fetches only from origin's first url, and a push to origin goes to $origin_pushes. Remove that url (git remote set-url --delete origin <that-url>), or remove '$_dup_r' if it is a second name for your fork"
                ;;
            *)
                note "$_dup_hit: a push to origin lands there. Remove that push url (git remote set-url --delete --push origin <that-url>), or remove '$_dup_r' if it is a second name for your fork"
                ;;
        esac
    done < <(git remote)
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
        note "gh has no default repository (remote.origin.gh-resolved is unset): a bare 'gh pr merge N' from a script would aim at the project, not your fork"
    elif [ "$gh_origin" != "base" ]; then
        note "remote.origin.gh-resolved is '$gh_origin', not 'base': gh would resolve a bare PR number against that repo, not your fork"
    fi
    # every other remote carrying the key, once each, with how many values it holds: a doubled key (two
    # `git config --add` by hand) is what a plain --unset refused to clear, so the note names the remote
    # and the count, and a rerun of set mode (--unset-all) clears it
    while read -r _gh_key; do
        [ -z "$_gh_key" ] && continue
        [ "$_gh_key" = "remote.origin.gh-resolved" ] && continue
        _gh_remote="${_gh_key#remote.}"; _gh_remote="${_gh_remote%.gh-resolved}"
        _gh_n="$(git config --get-all "$_gh_key" | wc -l | tr -d ' ')"
        _gh_vals="$(git config --get-all "$_gh_key" | tr '\n' ' ' | sed 's/ $//')"
        note "remote '$_gh_remote' carries gh's default-repository key ($_gh_key: $_gh_n value(s), '$_gh_vals'); only origin should, else gh may resolve a bare PR number there, not on your fork"
    done < <(git config --get-regexp '^remote\..*\.gh-resolved$' 2>/dev/null | awk '{print $1}' | sort -u || true)
    if [ $problems -eq 0 ]; then
        # what the checks above verified, and nothing more: none of them reads where a bare push goes
        # while remote.pushDefault is unset, or what a third remote pushes to
        echo "  ✓ upstream fetches from the project and is fetch-only; origin pushes to the repository it fetches from, shares no repository with another remote, and is gh's only default repository; no pushDefault or pushRemote is set to anything but origin"
        exit 0
    fi
    # The rerun advice only where a rerun fixes something and moves no push: the shared-repository notes
    # name their own fix, and beside a fetch note whose rerun would move pushes (see the fetch case
    # above) the standalone line is withheld.
    if [ $rerun_moves_pushes -eq 0 ] && [ $problems -gt $shared ]; then
        echo "Run scripts/fork-remotes.sh to fix." >&2
    fi
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
    git config --unset-all "$_pr_key" || true
done < <(git config --get-regexp '^branch\..*\.pushRemote$' 2>/dev/null || true)
# gh's default repository is origin, and origin alone: the same key on upstream or github is read
# before origin's (see the header), and on any remote it is a second default, so it goes too.
# --replace-all, because a hand `git config --add` can leave two values under origin's key and a
# plain set then refuses to overwrite them, which would stop set mode after the push guards; and
# --unset-all on the other remotes' keys for the same reason: a plain --unset refuses a doubled key,
# and the `|| true` swallowed that refusal, so the key survived a run that printed configured.
git config --replace-all remote.origin.gh-resolved base
while read -r _gh_key _gh_val; do
    [ -z "$_gh_key" ] && continue
    [ "$_gh_key" = "remote.origin.gh-resolved" ] && continue
    git config --unset-all "$_gh_key" || true
done < <(git config --get-regexp '^remote\..*\.gh-resolved$' 2>/dev/null || true)

echo "fork-remotes: configured"
echo "  origin   $origin_url  (fetch + push: your fork, and gh's default repository)"
echo "  upstream $UPSTREAM_URL  (fetch only; push disabled)"
echo "  a bare 'git push' goes to origin, and so does a bare 'gh pr <cmd> N'"
echo
echo "Check what the project has added since:  scripts/upstream-check.sh"
