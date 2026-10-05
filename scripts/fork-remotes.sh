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
# `git push upstream` dies with git's own error (no transport handles a
# no-push:// url) before it can contact anything. That is the loud failure we
# want, not a silent fallback that quietly does the wrong thing.
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
# what a test (or a paranoid moment) wants. Set mode refuses, and changes
# nothing, while a remote's url or push url value is empty, an insteadOf or
# pushInsteadOf rule has an empty base, origin shares a repository with another
# remote, git cannot read a remote's urls, git config holds no url for origin,
# an includeIf "onbranch:" or "hasconfig:remote.*.url:" entry names a file that
# sets a remote.*, url.* or branch.*.pushRemote key or that --check cannot read
# in full, upstream does not fetch from the project while a url of upstream's
# held outside the clone's own config file is read ahead of the last one that
# file holds or that file holds none, upstream has a push url other than the
# sentinel held outside that file, a url rule rewrites the sentinel, or one of
# these is held anywhere but the clone's own config file, where it wins over
# anything set mode writes: a url of origin's, a pushInsteadOf rule that matches
# one while origin has no push url, or a setting that aims a bare push or a bare
# gh PR number away from origin (see the checks below). It needs git 2.26 or
# later (git config --show-scope); with an older git, --check says so and set
# mode refuses.
#
# "The clone's own config file" means one file throughout: the one
# `git config --local` reads and writes (.git/config, or the main clone's in a
# linked worktree), not a file it includes and not config.worktree.
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
NL=$'\n'

check_only=0
case "${1:-}" in
    --check) check_only=1 ;;
    "") ;;
    *) echo "usage: scripts/fork-remotes.sh [--check]" >&2; exit 2 ;;
esac

# git's own error when it cannot read the clone at all: not a clone, or a config it cannot parse (a
# broken include, a bad GIT_CONFIG_COUNT entry).
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    _err="$(git rev-parse --git-dir 2>&1 >/dev/null || true)"
    echo "fork-remotes: git cannot read this clone: ${_err//$NL/ }" >&2
    exit 2
fi

# The clone's top level, as git sees it: physical, symlinks resolved. git runs a fetch or a push from
# there, so a relative local url is read against it. Every command this script prints names it with
# git -C, and every line that says to run this script names it by its path under the top level
# ($qscript), so each acts on this clone wherever the reader runs it.
toplevel="$(pwd -P)"
qtop="$(printf '%q' "$toplevel")"
qscript="$qtop/scripts/fork-remotes.sh"

# Where each config value is held: the checks below read git config --show-origin (git 2.8) for its
# file and --show-scope (git 2.26) for its scope, and each such read treats git's failure as no value.
# On a git that lacks either option, every one of those reads would fail, and the checks would pass
# values they never saw (a pushRemote aimed away, a url held in global config). So one read with both
# options comes first, and where it fails --check fails closed and set mode refuses, naming the git
# version and git's error. Past it, a read that fails is one where git found no such key (git exits 1),
# which the reads take as no value: every other git read here uses options git 2.26 has, and git stops
# on a config it cannot parse at the rev-parse above.
if ! _err="$(git config --show-scope --show-origin --list 2>&1 >/dev/null)"; then
    _why="git config --show-scope --show-origin, which these checks read to say where each value is held, failed (${_err%%"$NL"*}). They need git 2.26 or later, and this is $(git --version 2>&1 || true)"
    if [ $check_only -eq 1 ]; then
        echo "fork-remotes: checking"
        echo "  ✗ $_why"
        echo "Fix what the notes above name, then run $qscript --check again." >&2
    else
        {
            echo "fork-remotes: not configuring this clone; nothing was changed."
            echo "  $_why"
            echo "Run $qscript --check for what to change."
        } >&2
    fi
    exit 1
fi

# A local path with its empty, '.' and '..' segments resolved by spelling, into $_np.
norm_path() {
    local rest="$1/" seg
    _np=""
    while [ -n "$rest" ]; do
        seg="${rest%%/*}"; rest="${rest#*/}"
        case "$seg" in
            ""|.) ;;
            ..) _np="${_np%/*}" ;;
            *) _np="$_np/$seg" ;;
        esac
    done
    [ -n "$_np" ] || _np=/
}

# Compare repos by identity, not by string: https/ssh/.git-suffix spellings of
# the same repo must count as equal, or the "origin is not upstream" guard below
# would wave through an ssh-cloned upstream. The rule: each of git's documented
# url forms reduces to one id. A url with a scheme (ssh://, git://, https://,
# file://) drops the scheme, any user, and its scheme's default port (https 443,
# http 80, ssh 22, git 9418); the scp form [user@]host:path drops any user, the
# colon and a slash after it, so it reads as host/path; a local path, and a
# file:// url's path, is made absolute against the clone's top level, with its
# '.', '..' and empty segments resolved by spelling. repo_id keeps case.
# Which reading of a suffix or of case is safe depends on what a match does.
# Where a match refuses (origin is the project, origin shares a repository with
# another remote), two spellings that may name one repository must read as
# one: trailing slashes and lowercase .git suffixes come off until none is
# left, so 'X.git/', 'X/.git' and 'X.git.git' all read as 'X', and ids are
# compared folded (fold_id), so one repository spelled two ways is refused, at
# the cost of refusing two that a case-sensitive host, or a directory X beside
# a directory X.git, keeps apart. Where a match passes (a push to origin goes
# where it fetches from, upstream fetches from the project), two spellings that
# may name two repositories must not: repo_id <url> pass takes off a url with a
# host's trailing slashes and at most one lowercase .git, which is what a forge
# strips, and nothing from a local path or file:// url, where X and X.git are
# two directories, and ids are compared exactly, so such a difference is a note
# rather than a pass. A forge strips only a lowercase .git, so 'X.GIT' keeps
# its suffix either way and names another repository; the fold comes after the
# suffix is stripped. Case: a host ignores it, a forge ignores it in owner and
# repository names, and a case-insensitive file system (macOS's default) reads
# two spellings of a path as one directory.
# Dropping the scheme and the user merges what a plain ssh host keeps apart:
# https://host/x, ssh://host/x and host:x read as one, which a forge serves as
# one repository, but the scp form's path is relative to the login's home
# directory, so on a plain ssh host host:x and ssh://host/x name two paths, as
# do two users' host:x. Not normalized: host aliases, DNS names, ssh config Host
# entries, any port other than the default (ftp's and ftps's default ports
# among them), a ~ home-directory spelling (ssh://host/~/x names what host:x
# names), a doubled slash in a url with a host, a bracketed IPv6 host in the scp
# form, and symlinks in a local path.
repo_id() {  # <url> [pass]
    local u="$1" re='^([A-Za-z][A-Za-z0-9+.-]*)://([^/]*)(.*)$' scheme host path hosted=1
    if [[ $u =~ $re ]]; then
        scheme="${BASH_REMATCH[1]}"; host="${BASH_REMATCH[2]##*@}"; path="${BASH_REMATCH[3]}"
        case "$scheme:${host##*:}" in
            https:443|http:80|ssh:22|git+ssh:22|ssh+git:22|git:9418) host="${host%:*}" ;;
        esac
        if [ "$scheme" = file ]; then norm_path "$path"; u="$_np"; hosted=0; else u="$host$path"; fi
    elif [[ $u == *:* && ${u%%:*} != */* ]]; then
        # the scp form: a colon with no slash ahead of it, as git reads it
        host="${u%%:*}"; path="${u#*:}"
        u="${host##*@}/${path#/}"
    else
        case "$u" in /*) ;; *) u="$toplevel/$u" ;; esac
        norm_path "$u"; u="$_np"; hosted=0
    fi
    if [ "${2:-}" = pass ]; then
        if [ $hosted -eq 1 ]; then
            while [[ $u == */ ]]; do u="${u%/}"; done
            u="${u%.git}"
        fi
        printf '%s' "$u"
        return 0
    fi
    while :; do
        case "$u" in
            */) u="${u%/}" ;;
            *.git) u="${u%.git}" ;;
            *) break ;;
        esac
    done
    printf '%s' "$u"
}

# A repo_id with its case folded, ASCII only (tr, which works under bash 3.2, where ${x,,} needs
# bash 4).
fold_id() { printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]'; }

# One entry of `git config -z --get-regexp` (the key, a newline, the value) into $_pr_key and $_pr_val,
# neither trimmed; a key written with no value has none.
pr_split() {
    _pr_key="${1%%"$NL"*}"; _pr_val=""
    case "$1" in *"$NL"*) _pr_val="${1#*"$NL"}" ;; esac
}

# Every url remote $1 carries, as git resolves them: --all for a remote with several, and get-url
# applies insteadOf and pushInsteadOf rewrites, so each url reads the way a fetch or a push uses it.
# The fetch urls go into $r_fetch and the push urls into $r_push, one per line. get-url --push prints
# exactly the urls a push uses: the push urls, or for a remote with none its urls, except that when a
# pushInsteadOf rule rewrites any of them git pushes to the rewritten urls only. When git cannot read
# them, git's error goes into $r_err and it returns 1: get-url refuses a remote that only global or
# system config, or the environment (GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS), defines, which git
# remote lists, and a name that only an unreadable legacy file supplies. The -- keeps a remote whose
# name starts with a dash from being read as an option.
read_urls() {
    r_fetch=""; r_push=""; r_err=""
    if r_fetch="$(git remote get-url --all -- "$1" 2>/dev/null)" \
        && r_push="$(git remote get-url --push --all -- "$1" 2>/dev/null)"; then
        return 0
    fi
    r_err="$( { git remote get-url --all -- "$1" && git remote get-url --push --all -- "$1"; } 2>&1 >/dev/null || true)"
    r_err="${r_err//$NL/ }"
    r_fetch=""; r_push=""
    return 1
}

# Where a config value lives, from git config --show-origin: its file, or the environment, which
# --show-origin calls "command line:". git spells some files by a path relative to the top level, where
# this script runs (.git/config.worktree, an include with a relative path); those get the top level in
# front, so the path names the file from any directory.
where_from() {
    case "$1" in
        "command line:") printf '%s' "set in the environment by GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS" ;;
        file:/*) printf 'in %s' "$1" ;;
        file:*) printf 'in file:%s/%s' "$toplevel" "${1#file:}" ;;
        *) printf 'in %s' "$1" ;;
    esac
}

# The clone's own config file, as --show-origin spells it: the one --local reads (it reads no include).
local_cfg=""
IFS= read -r -d '' local_cfg < <(git config --local --show-origin -z --list 2>/dev/null) || true
# The legacy directories, where a .git/remotes or .git/branches file can define a remote.
remotes_dir="$(git rev-parse --git-path remotes)"; branches_dir="$(git rev-parse --git-path branches)"
case "$remotes_dir" in /*) ;; *) remotes_dir="$toplevel/$remotes_dir" ;; esac
case "$branches_dir" in /*) ;; *) branches_dir="$toplevel/$branches_dir" ;; esac

# Empty urls. git 2.55 reads an empty url value as clearing the values it read before it, as its
# documentation of remote.<name>.url says; git 2.43 reads it as a url, empty. An insteadOf or
# pushInsteadOf rule whose base is empty (git config spells its key url..insteadof or
# url..pushinsteadof) rewrites a url it matches to an empty one, and git 2.55 reads that as clearing
# too wherever it rewrites a url as it reads it (a pushInsteadOf rule's result, a legacy file's url, a
# remote's name read as its url), though not where it rewrites a url value of config, which it does
# once the values are read. So one config can name different urls to different gits: a value this
# script reads as config holds it may be one the running git no longer uses (set mode copies origin's
# first url value onto its push url), and what git resolves for origin, for upstream, or for any remote
# the shared-repository check compares with origin differs from one git to the next. So, on every git,
# each empty url or push url value of any remote's, and each rule whose base is empty, wherever it is
# held, fails closed before origin's url or anything after it is read: --check names it with where it
# lives, prints the commands that remove what the clone's own config file holds of it (a key's empty
# values, or every value of a rule's key), and stops there, with no rerun line; set mode refuses,
# writing nothing. A legacy file that defines a remote is read the same way, where git reads it
# (config gives that remote no url): a URL: line of a .git/remotes file with nothing after it, or a
# .git/branches file whose first line has nothing before its '#'. A key written with no value is left
# to git, which stops on it when it reads origin's url below, and a file that cannot be read to the
# checks below, which fail closed on it.
empty_out=""; empty_cmds=(); _seen="$NL"
# For a listed entry that the clone's own config file holds ($1 is where it lives, $2 its key): the
# command that removes what that file holds under the key, with the value pattern $3, once per key.
empty_cmd() {  # <where it lives> <key> <value pattern>
    [ "$1" = "$local_cfg" ] || return 0
    case "$_seen" in *"$NL$2$NL"*) return 0 ;; esac
    _seen="$_seen$2$NL"
    empty_cmds+=("git -C $qtop config --unset-all $(printf '%q' "$2")$3")
}
while IFS= read -r -d '' _src && IFS= read -r -d '' _ent; do
    pr_split "$_ent"
    [ "$_ent" = "$_pr_key$NL" ] || continue   # a value that is not empty, or a key written with none
    empty_out="$empty_out$NL    $_pr_key, an empty value ($(where_from "$_src"))"
    empty_cmd "$_src" "$_pr_key" " '^\$'"
done < <(git config -z --show-origin --get-regexp '^remote\..*\.(url|pushurl)$' 2>/dev/null || true)
for _d in "$remotes_dir" "$branches_dir"; do
    for _f in "$_d"/* "$_d"/.[!.]* "$_d"/..?*; do
        if [ ! -f "$_f" ] || [ ! -r "$_f" ]; then continue; fi
        if git config --get-all "remote.${_f##*/}.url" >/dev/null 2>&1; then continue; fi
        if [ "$_d" = "$remotes_dir" ]; then
            while IFS= read -r _line || [ -n "$_line" ]; do
                case "$_line" in URL:*) ;; *) continue ;; esac
                _v="${_line#URL:}"
                if [ -z "${_v//[[:space:]]/}" ]; then empty_out="$empty_out$NL    a URL: line, an empty value (in the legacy file $_f)"; fi
            done < "$_f"
        else
            _line=""; IFS= read -r _line < "$_f" || true
            _v="${_line%%#*}"
            if [ -n "${_line//[[:space:]]/}" ] && [ -z "${_v//[[:space:]]/}" ]; then
                empty_out="$empty_out$NL    the url on its first line, ahead of the '#', an empty value (in the legacy file $_f)"
            fi
        fi
    done
done
while IFS= read -r -d '' _src && IFS= read -r -d '' _ent; do
    pr_split "$_ent"
    case "$_ent" in *"$NL"*) ;; *) continue ;; esac   # a rule written with no value
    empty_out="$empty_out$NL    $_pr_key $_pr_val, a rule whose base is empty ($(where_from "$_src"))"
    empty_cmd "$_src" "$_pr_key" ""
done < <(git config -z --show-origin --get-regexp '^url\.\.(insteadof|pushinsteadof)$' 2>/dev/null || true)
empty_out="${empty_out#"$NL"}"
if [ -n "$empty_out" ]; then
    _what="an empty url or push url value, or an insteadOf or pushInsteadOf rule whose base is empty, which rewrites a url it matches to an empty one: a newer git (2.55, say) reads an empty url value, and some of the urls such a rule rewrites to nothing, as clearing the urls read before it, and an older one (2.43, say) reads each as an empty url"
    if [ $check_only -eq 1 ]; then
        echo "fork-remotes: checking"
        echo "  ✗ each of these is $_what, so such a config can name different urls to different gits, and --check reads nothing further while one stands. Remove each one where it lives, then run $qscript --check again$NL$empty_out"
        if [ ${#empty_cmds[@]} -gt 0 ]; then
            {
                echo "These commands, which act on this clone from any directory, remove each empty value and each rule above that the clone's own config file holds, there, and leave its other values:"
                for _c in "${empty_cmds[@]}"; do echo "    $_c"; done
            } >&2
        fi
        echo "Fix what the notes above name, then run $qscript --check again." >&2
    else
        {
            echo "fork-remotes: not configuring this clone; nothing was changed."
            echo "  Each of these is $_what, so set mode cannot tell which urls git uses:"
            printf '%s\n' "$empty_out"
            echo "Run $qscript --check for what to change."
        } >&2
    fi
    exit 1
fi

# origin's first url, as git resolves it, or git's own error (a url key written with no value, on any
# remote, is one).
if ! origin_url="$(git remote get-url origin 2>/dev/null)"; then
    _err="$(git remote get-url origin 2>&1 >/dev/null || true)"
    echo "fork-remotes: git cannot read origin's url: ${_err//$NL/ }" >&2
    exit 2
fi
# No url value is empty by here and no rule's base is, so origin's first url is not empty either; this
# stops the script on an empty one that comes some way this script does not know of.
[ -n "$origin_url" ] || { echo "fork-remotes: origin's first url is empty" >&2; exit 2; }

# origin's url and push url values as git config holds them, read exactly (-z), none of them empty (the
# check above stops on one), so every git reads them alike: origin_raw, its first url value, which set
# mode copies onto its push url; each url value (uv_val); how many of them the clone's own config file
# holds (n_local_url, n_local_push); each push url value and its source, in the order git reads them
# (pv_val and pv_src, which line up one for one with get-url --push --all when origin has push urls);
# and, in outside, one line per value held anywhere else (an included file, config.worktree, global or
# system config, the environment), each with where it lives. Nothing printed here can change those, and
# set mode cannot either, so they fail closed.
# A rule held anywhere else whose value starts one of origin's values goes by what it can do to a push
# to origin. A pushInsteadOf rule while origin has no push url decides where that push goes (git
# pushes to the urls it rewrites, and to those alone), so it joins outside and fails closed. An
# insteadOf rule rewrites a url for fetches and pushes alike: the urls --check compares are already
# the rewritten ones, and the raw url set mode copies onto the push url is rewritten as the fetch url
# is. A pushInsteadOf rule rewrites no push url, so while origin has one it rewrites nothing. Those
# two kinds go into outside_rules, listed beside a failing note as information, and fail nothing by
# themselves. outside_pi says whether outside holds such a pushInsteadOf rule.
origin_values() {
    local key src val ent v line vals=()
    origin_raw=""; n_local_url=0; n_local_push=0; outside=""; outside_rules=""; outside_pi=0
    uv_val=(); pv_src=(); pv_val=()
    for key in remote.origin.url remote.origin.pushurl; do
        while IFS= read -r -d '' src && IFS= read -r -d '' val; do
            vals+=("$val")
            if [ $key = remote.origin.url ]; then
                [ ${#vals[@]} -ne 1 ] || origin_raw="$val"
                uv_val+=("$val")
            else
                pv_src+=("$src"); pv_val+=("$val")
            fi
            if [ "$src" = "$local_cfg" ]; then
                if [ $key = remote.origin.url ]; then n_local_url=$((n_local_url + 1)); else n_local_push=$((n_local_push + 1)); fi
            else
                outside="$outside$NL$key $val ($(where_from "$src"))"
            fi
        done < <(git config -z --show-origin --get-all "$key" 2>/dev/null || true)
    done
    while IFS= read -r -d '' src && IFS= read -r -d '' ent; do
        [ "$src" != "$local_cfg" ] || continue
        pr_split "$ent"
        for v in ${vals[@]+"${vals[@]}"}; do
            case "$v" in "$_pr_val"*) ;; *) continue ;; esac
            line="$_pr_key $_pr_val ($(where_from "$src"))"
            if [[ $_pr_key == *.pushinsteadof ]] && [ ${#pv_src[@]} -eq 0 ]; then
                outside="$outside$NL$line"; outside_pi=1
            else
                outside_rules="$outside_rules$NL$line"
            fi
            break
        done
    done < <(git config -z --show-origin --get-regexp '^url\..*\.(insteadof|pushinsteadof)$' 2>/dev/null || true)
    outside="${outside#"$NL"}"; outside_rules="${outside_rules#"$NL"}"
}
origin_values

# The settings that decide where a bare push or a bare gh PR number goes: remote.pushDefault, each
# branch's pushRemote, and gh-resolved on each remote. git (and gh, for gh-resolved) uses the LAST value
# of a key in the order it reads config: system, global, the clone's own config file with the files it
# includes, config.worktree, the environment. So for pushDefault, a pushRemote and origin's gh-resolved,
# --check decides on that value, the one git uses. One that aims away from origin (another remote, or
# a value other than base on origin's gh-resolved) is a note, and where it lives says whether a rerun of
# set mode fixes it:
# - in the clone's own config file: set mode replaces it (pushDefault, origin's gh-resolved) or removes
#   it (a pushRemote). Removing a pushRemote leaves git the last value held anywhere else, so where that
#   one aims away too a rerun would only expose it, and it fails closed;
# - in global or system config: git reads the clone's own config file after those, so set mode's write
#   of pushDefault or origin's gh-resolved there overrides it; set mode writes no pushRemote, so a
#   pushRemote there fails closed;
# - anywhere else (a file the clone's own config includes, config.worktree, the environment): it can
#   still win after set mode writes, so it fails closed.
# A value held outside that aims away, but that a value git reads after it overrides, decides nothing
# and is listed beside a failing note as information. gh-resolved on any other remote fails closed
# wherever it is held outside the clone's own config file, the only place set mode removes it from.
# aim_out and aim_info get one line per value, with where it lives; pd_*, gh_* (origin's gh-resolved)
# and the pr_* arrays (each pushRemote that aims away) hold what --check and set mode act on.
aim_good() {  # <key> <value>: whether the value aims at origin
    if [ "$1" = remote.origin.gh-resolved ]; then [ "$2" = base ]; else [ "$2" = origin ]; fi
}
# The values of key $1 in git's read order, sorted as above: the one git uses into _ak_val (with _ak_set
# 0 when no config sets the key), " (where it lives)" into _ak_at when that is not the clone's own config
# file, and into _ak_fix whether a rerun of set mode fixes it (1) or it fails closed (0).
aim_key() {
    local key="$1" scope src val i e out=-1 fb=-1 sc=() sr=() va=() tail=""
    _ak_val=""; _ak_set=0; _ak_at=""; _ak_fix=1
    while IFS= read -r -d '' scope && IFS= read -r -d '' src && IFS= read -r -d '' val; do
        sc+=("$scope"); sr+=("$src"); va+=("$val")
    done < <(git config -z --show-scope --show-origin --get-all "$key" 2>/dev/null || true)
    [ ${#va[@]} -gt 0 ] || return 0
    e=$((${#va[@]} - 1))
    _ak_set=1; _ak_val="${va[$e]}"
    if [ "${sr[$e]}" != "$local_cfg" ]; then _ak_at=" ($(where_from "${sr[$e]}"))"; fi
    if ! aim_good "$key" "$_ak_val"; then
        if [ "${sr[$e]}" = "$local_cfg" ]; then
            if [[ $key == branch.*.pushremote ]]; then
                for ((i = e - 1; i >= 0; i--)); do
                    if [ "${sr[$i]}" != "$local_cfg" ]; then fb=$i; break; fi
                done
                if [ $fb -ge 0 ] && ! aim_good "$key" "${va[$fb]}"; then
                    out=$fb; tail=", which git uses once set mode removes the clone's own value"
                fi
            fi
        elif [[ $key == branch.*.pushremote ]] || { [ "${sc[$e]}" != global ] && [ "${sc[$e]}" != system ]; }; then
            out=$e
        fi
    fi
    if [ $out -ge 0 ]; then
        _ak_fix=0
        aim_out="$aim_out$NL$key ${va[$out]} ($(where_from "${sr[$out]}"))$tail"
    fi
    for ((i = 0; i < e; i++)); do
        if [ $i -ne $out ] && [ "${sr[$i]}" != "$local_cfg" ] && ! aim_good "$key" "${va[$i]}"; then
            aim_info="$aim_info$NL$key ${va[$i]} ($(where_from "${sr[$i]}"))"
        fi
    done
}
aim_values() {
    local key seen="$NL" src val
    aim_out=""; aim_info=""; pr_key=(); pr_val=(); pr_at=(); pr_fix=()
    aim_key remote.pushdefault
    pd_set=$_ak_set; pd_val="$_ak_val"; pd_at="$_ak_at"; pd_fix=$_ak_fix
    aim_key remote.origin.gh-resolved
    gh_set=$_ak_set; gh_val="$_ak_val"; gh_at="$_ak_at"; gh_fix=$_ak_fix
    while IFS= read -r -d '' key; do
        case "$seen" in *"$NL$key$NL"*) continue ;; esac
        seen="$seen$key$NL"
        case "$key" in
            remote.origin.gh-resolved) ;;
            branch.*.pushremote)
                aim_key "$key"
                if ! aim_good "$key" "$_ak_val"; then
                    pr_key+=("$key"); pr_val+=("$_ak_val"); pr_at+=("$_ak_at"); pr_fix+=("$_ak_fix")
                fi
                ;;
            *)
                while IFS= read -r -d '' src && IFS= read -r -d '' val; do
                    [ "$src" != "$local_cfg" ] || continue
                    aim_out="$aim_out$NL$key $val ($(where_from "$src"))"
                done < <(git config -z --show-origin --get-all "$key" 2>/dev/null || true)
                ;;
        esac
    done < <(git config -z --name-only --get-regexp '^(branch\..*\.pushremote|remote\..*\.gh-resolved)$' 2>/dev/null || true)
    aim_out="${aim_out#"$NL"}"; aim_info="${aim_info#"$NL"}"
}
aim_values

# includeIf entries, in any config git reads, whose condition a branch switch or a remote write can
# change: "onbranch:<pattern>", which holds while the branch checked out matches the pattern, and
# "hasconfig:remote.*.url:<pattern>", which holds while some remote has a url the pattern matches (set
# mode's own write of upstream's url can make one hold). git reads the file such an entry names only
# while its condition holds, so while it does not, no check here sees what that file sets, and while it
# does, a branch switch or a remote write can take it away. A file that sets a remote.* key
# (remote.pushDefault among them), a url.* key or a branch's pushRemote can then give origin another
# url or push url, rewrite one, add a remote that shares its repository, or aim a bare push at another
# remote. So can a file that includes another file, which git config -f does not follow, and nothing
# can say what a file git cannot read sets. Each such entry fails closed: condinc_out gets one line per
# entry, with where it lives, the file it names, and the keys that file sets or git's error. git reads
# a relative path against the directory of the file that holds the entry, and ~ or ~/ as the home
# directory; an entry set in the environment with a relative path is read here against the top level
# (git refuses it where its condition holds). A path git expands by a user's name (~name/) or its own
# prefix (%(prefix)/) is not expanded here, so nothing can say which file it names, and it fails closed
# too. An entry whose file sets none of those keys is left out, and so is one whose file does not exist
# (git skips an include whose file is missing, so it sets nothing); git stops on one whose file exists
# but cannot be read. An includeIf on any other condition is read as git reads it now, as any other
# config is: a gitdir: or gitdir/i: condition holds or not by where the repository is, which neither a
# branch switch nor a remote write changes, and git takes no other condition as holding. git matches
# both prefixes as spelled here, case and all.
condinc_values() {
    local src ent key path target dir err keys seen
    condinc_out=""
    while IFS= read -r -d '' src && IFS= read -r -d '' ent; do
        pr_split "$ent"; key="$_pr_key"; path="$_pr_val"; target="$path"
        case "$target" in
            /*) ;;
            \~|\~/*) target="${HOME:-}${target:1}" ;;
            \~*|"%(prefix)/"*)
                condinc_out="$condinc_out$NL$key $path ($(where_from "$src")) names its file by ~name/ or %(prefix)/, which git expands and --check does not, so --check cannot read it"
                continue
                ;;
            *)
                case "$src" in
                    file:*)
                        dir="${src#file:}"
                        case "$dir" in /*) ;; *) dir="$toplevel/$dir" ;; esac
                        target="${dir%/*}/$target"
                        ;;
                esac
                ;;
        esac
        # git's error read in the C locale, where it names a missing file as the C library does
        if ! err="$(LC_ALL=C git config -f "$target" --list 2>&1 >/dev/null)"; then
            case "$err" in *": No such file or directory"|*": Not a directory") continue ;; esac
            condinc_out="$condinc_out$NL$key $path ($(where_from "$src")) names $target, which git cannot read: ${err//$NL/ }"
            continue
        fi
        keys=""; seen="$NL"
        while IFS= read -r -d '' ent; do
            pr_split "$ent"
            case "$_pr_key" in
                remote.*|url.*|branch.*.pushremote|include.path|includeif.*.path) ;;
                *) continue ;;
            esac
            case "$seen" in *"$NL$_pr_key$NL"*) continue ;; esac
            seen="$seen$_pr_key$NL"; keys="${keys:+$keys, }$_pr_key"
        done < <(git config -f "$target" -z --list 2>/dev/null || true)
        if [ -n "$keys" ]; then
            condinc_out="$condinc_out$NL$key $path ($(where_from "$src")) names $target, which sets $keys"
        fi
    done < <(git config -z --show-origin --get-regexp '^includeif\.(onbranch|hasconfig:remote\.\*\.url):.*\.path$' 2>/dev/null || true)
    condinc_out="${condinc_out#"$NL"}"
}
condinc_values

# An origin whose url is in no config: a legacy .git/remotes or .git/branches file defines it (git reads
# one only for a remote that config gives no url), or, with neither, git reads the name origin as its
# url. legacy_origin says which, and is empty when config holds a url value of origin's.
legacy_origin=""
if [ ${#uv_val[@]} -eq 0 ]; then
    for _f in "$remotes_dir/origin" "$branches_dir/origin"; do
        if [ -f "$_f" ]; then legacy_origin="${legacy_origin:+$legacy_origin and }$_f"; fi
    done
    if [ -f "$remotes_dir/origin" ] && [ -f "$branches_dir/origin" ]; then
        legacy_origin="the legacy files $legacy_origin define it"
    elif [ -n "$legacy_origin" ]; then
        legacy_origin="the legacy file $legacy_origin defines it"
    else
        legacy_origin="no legacy file defines it either, so git reads the name origin as its url"
    fi
fi

# The commands that point origin at the fork. They depend on no configured value's spelling (an
# insteadOf alias, a url holding a regex metacharacter): they remove every url and push url origin has
# in the clone's own config file, then set the fork's url as its url and as its push url. git applies
# no pushInsteadOf rule to a push url, so a rule that rewrites the fork's url for pushes cannot move
# them; an insteadOf rule that matches the url typed rewrites both, as it rewrites any url. They are
# printed only when every value of origin's, and every pushInsteadOf rule that matches one while origin
# has no push url, is in that file, where they act; each names the clone with git -C. Any other rule
# held anywhere else that matches a value of origin's is listed beside them (rules_info).
print_steps() {
    if [ $n_local_url -gt 0 ]; then echo "    git -C $qtop config --unset-all remote.origin.url"; fi
    if [ $n_local_push -gt 0 ]; then echo "    git -C $qtop config --unset-all remote.origin.pushurl"; fi
    echo "    git -C $qtop config remote.origin.url <your-fork-url>"
    echo "    git -C $qtop config remote.origin.pushurl <your-fork-url>"
}
# The other way out for a pushInsteadOf rule held outside the clone's own config file that matches a
# url of origin's while origin has no push url, said wherever such a rule is listed: a push url in that
# file, to which git applies no pushInsteadOf rule.
pi_fix=""
[ $outside_pi -eq 0 ] || pi_fix=" (or, for a pushInsteadOf rule listed here, give origin a push url in the clone's own config file with git -C $qtop config remote.origin.pushurl <your-fork-url>: git applies no pushInsteadOf rule to a push url, so the rule then rewrites nothing)"
aim_list() { printf '%s\n' "$aim_out" | sed 's/^/    /'; }
outside_list() { printf '%s\n' "$outside" | sed 's/^/    /'; }
condinc_list() { printf '%s\n' "$condinc_out" | sed 's/^/    /'; }
# The rules held anywhere but the clone's own config file that fail nothing by themselves (see
# origin_values), listed as information beside a failing note, each with where it lives.
rules_info() {
    [ -n "$outside_rules" ] || return 0
    echo "  For information: these rules, held outside the clone's own config file, match a url of origin's, and neither set mode nor a command printed here can change them. An insteadOf rule rewrites the urls it matches for fetches and pushes alike, and --check reads urls as rewritten; a pushInsteadOf rule rewrites nothing while origin has a push url:"
    printf '%s\n' "$outside_rules" | sed 's/^/    /'
}
# The settings held outside the clone's own config file that aim away from origin but that a value git
# reads after each overrides (see aim_values), listed as information beside a failing note.
aim_info_list() {
    [ -n "$aim_info" ] || return 0
    echo "  For information: these settings, held outside the clone's own config file, aim a bare push or a bare gh PR number away from origin, but git uses a value it reads after each:"
    printf '%s\n' "$aim_info" | sed 's/^/    /'
}

# Every remote name: the names git remote lists, and the names a legacy .git/remotes or .git/branches
# file supplies, which git remote leaves out though a push and get-url use them.
names=(); n_cfg=(); n_files=()   # each name, whether git remote lists it, and the legacy files naming it
add_name() {  # <name> <listed by git remote: 0|1> [<legacy file>]
    local i
    for ((i = 0; i < ${#names[@]}; i++)); do
        if [ "${names[$i]}" = "$1" ]; then
            [ "$2" = 0 ] || n_cfg[i]=1
            [ -z "${3:-}" ] || n_files[i]="${n_files[$i]:+${n_files[$i]}$NL}$3"
            return 0
        fi
    done
    names+=("$1"); n_cfg+=("$2"); n_files+=("${3:-}")
}
while IFS= read -r _n; do
    [ -z "$_n" ] || add_name "$_n" 1
done < <(git remote)
for _d in "$remotes_dir" "$branches_dir"; do
    for _f in "$_d"/* "$_d"/.[!.]* "$_d"/..?*; do
        if [ -f "$_f" ]; then add_name "${_f##*/}" 0 "$_f"; fi
    done
done
# git reads no remote from a legacy branches file whose first line is blank, and a push to that name
# fails, so a name that only such files supply is no remote and is skipped. A file git cannot read is
# not skipped: nothing can say what it names.
legacy_blank() {  # <files, one per line>
    local f line
    while IFS= read -r f; do
        [ "${f%/*}" = "$branches_dir" ] && [ -r "$f" ] || return 1
        line=""; IFS= read -r line < "$f" || true
        [ -z "${line//[[:space:]]/}" ] || return 1
    done <<<"$1"
}
# Whether config, in any scope, gives remote $1 a url or a push url.
has_url() {
    git config --get-all "remote.$1.url" >/dev/null 2>&1 || git config --get-all "remote.$1.pushurl" >/dev/null 2>&1
}
# Each url and push url value of remote $1 held outside the clone's own config file, one line each with
# where it lives, indented as a listing.
remote_outside() {
    local key src val out=""
    for key in url pushurl; do
        while IFS= read -r -d '' src && IFS= read -r -d '' val; do
            [ "$src" != "$local_cfg" ] || continue
            out="$out$NL    remote.$1.$key $val ($(where_from "$src"))"
        done < <(git config -z --show-origin --get-all "remote.$1.$key" 2>/dev/null || true)
    done
    printf '%s' "${out#"$NL"}"
}
# Each rule whose key matches the regex $2, wherever it is held, whose value starts $1: the url rules git
# applies to $1 read as a url. One line each with where it lives, indented as a listing.
rules_on() {  # <url> <key regex>
    local src ent out=""
    while IFS= read -r -d '' src && IFS= read -r -d '' ent; do
        pr_split "$ent"
        case "$1" in "$_pr_val"*) out="$out$NL    $_pr_key $_pr_val ($(where_from "$src"))" ;; esac
    done < <(git config -z --show-origin --get-regexp "$2" 2>/dev/null || true)
    printf '%s' "${out#"$NL"}"
}
# The rules held outside the clone's own config file that rewrite a url or push url of remote $1 as git
# reads it: an insteadOf rule whose value starts a url or push url value of its, and a pushInsteadOf
# rule whose value starts a url value while it has no push url (git applies none to a push url). With
# byname as $2, the remote has no url and git uses its name as its url. One line each with where it
# lives, indented as a listing. A url a legacy file gives is not read here: the note names that file.
remote_rules() {  # <remote> [byname]
    local src ent val v urls=() pushes=() cands=() out=""
    while IFS= read -r -d '' val; do urls+=("$val"); done < <(git config -z --get-all "remote.$1.url" 2>/dev/null || true)
    while IFS= read -r -d '' val; do pushes+=("$val"); done < <(git config -z --get-all "remote.$1.pushurl" 2>/dev/null || true)
    if [ "${2:-}" = byname ]; then urls=("$1"); fi
    while IFS= read -r -d '' src && IFS= read -r -d '' ent; do
        [ "$src" != "$local_cfg" ] || continue
        pr_split "$ent"
        if [[ $_pr_key == *.pushinsteadof ]]; then
            [ ${#pushes[@]} -eq 0 ] || continue
            cands=(${urls[@]+"${urls[@]}"})
        else
            cands=(${urls[@]+"${urls[@]}"} ${pushes[@]+"${pushes[@]}"})
        fi
        for v in ${cands[@]+"${cands[@]}"}; do
            case "$v" in "$_pr_val"*) out="$out$NL    $_pr_key $_pr_val ($(where_from "$src"))"; break ;; esac
        done
    done < <(git config -z --show-origin --get-regexp '^url\..*\.(insteadof|pushinsteadof)$' 2>/dev/null || true)
    printf '%s' "${out#"$NL"}"
}
# The keys that define remote $1, wherever git reads them: each one held outside the clone's own config
# file, with its value and where it lives, indented as a listing, into _rk_out, and into _rk_local
# whether that file holds any of them. git remote remove acts on that file alone.
remote_keys() {
    local src ent var
    _rk_out=""; _rk_local=0
    while IFS= read -r -d '' src && IFS= read -r -d '' ent; do
        pr_split "$ent"
        case "$_pr_key" in "remote.$1."*) ;; *) continue ;; esac
        var="${_pr_key#"remote.$1."}"
        case "$var" in *.*) continue ;; esac
        if [ "$src" = "$local_cfg" ]; then
            _rk_local=1
        else
            _rk_out="$_rk_out$NL    $_pr_key $_pr_val ($(where_from "$src"))"
        fi
    done < <(git config -z --show-origin --get-regexp '^remote\.' 2>/dev/null || true)
    _rk_out="${_rk_out#"$NL"}"
}

# The project's url as git reads it. git ls-remote --get-url applies the insteadOf rules a fetch from
# that url would, and contacts nothing, so the project is compared as git resolves it, as every remote's
# urls are (an ssh alias that a rule maps the project's https url to, say). It also reads a remote's
# NAME as that remote's url, so a project url spelled as the name of a remote here stops the script
# rather than compare with that remote; and where git cannot resolve the url at all, the script stops
# with git's error. up_id, the resolved id, and the id of the url as written are what the refusal below
# compares; up_pid, the resolved id read where a match passes (see repo_id), is the one upstream must
# fetch from.
for _n in ${names[@]+"${names[@]}"}; do
    if [ "$_n" = "$UPSTREAM_URL" ]; then
        echo "fork-remotes: the project's url, $UPSTREAM_URL, is also the name of a remote in this clone, so git reads it as that remote's url; set ROMP_UPSTREAM_URL to the project's url itself" >&2
        exit 2
    fi
done
if ! up_resolved="$(git ls-remote --get-url -- "$UPSTREAM_URL" 2>/dev/null)" || [ -z "$up_resolved" ]; then
    _err="$(git ls-remote --get-url -- "$UPSTREAM_URL" 2>&1 >/dev/null || true)"
    echo "fork-remotes: git cannot resolve the project's url, $UPSTREAM_URL: ${_err//$NL/ }" >&2
    exit 2
fi
up_id="$(repo_id "$up_resolved")"; up_pid="$(repo_id "$up_resolved" pass)"
up_fid="$(fold_id "$up_id")"; up_raw_fid="$(fold_id "$(repo_id "$UPSTREAM_URL")")"
proj_txt="$UPSTREAM_URL"
[ "$up_resolved" = "$UPSTREAM_URL" ] || proj_txt="$UPSTREAM_URL, which git rewrites to $up_resolved"

# origin's urls, each with its kind, its repo_id read where a match passes (see repo_id), and its
# repo_id folded, in this order: its first url, the one git fetches from (fetch); any url after the
# first (extra), which git never fetches from, and pushes to when origin has no push url and no
# pushInsteadOf rule rewrites its urls; and the urls a push to origin uses (push). origin_pushes lists
# where a push to origin goes, read from git rather than assumed.
read_urls origin
o_kind=(); o_url=(); o_id=(); o_fid=()
_kind=fetch
while IFS= read -r _u; do
    [ -n "$_u" ] || continue
    o_kind+=("$_kind"); o_url+=("$_u"); o_id+=("$(repo_id "$_u" pass)"); o_fid+=("$(fold_id "$(repo_id "$_u")")"); _kind=extra
done <<<"$r_fetch"
origin_pushes=""; n_push=0
while IFS= read -r _u; do
    [ -n "$_u" ] || continue
    o_kind+=(push); o_url+=("$_u"); o_id+=("$(repo_id "$_u" pass)"); o_fid+=("$(fold_id "$(repo_id "$_u")")"); n_push=$((n_push + 1))
    origin_pushes="${origin_pushes:+$origin_pushes, }$_u"
done <<<"$r_push"
origin_id="$(repo_id "$origin_url" pass)"

# The one thing we cannot fix by ourselves. If origin IS the upstream project,
# this is not a fork clone (or someone re-pointed origin), and setting up
# fetch-only upstream would leave every push aimed at the project. Say so and
# stop rather than configure something misleading. Every url of origin's is
# compared, as git resolves it (the one it fetches from, any after it, which a
# push goes to when origin has no push url, and each one a push goes to), with
# the project's url both as written and as git resolves it, ids folded. This is
# also set mode's check against the state it leaves: once it had pointed
# upstream at the project, the shared-repository check below would find any
# such url on upstream. That check compares origin with the remotes as they
# stand before set mode writes.
# Where no url of origin's matches the project's url as written, only as git
# rewrites it, and no url or push url value of origin's, as git config or a
# legacy file holds it, names the project's repository, the rules that rewrite
# the project's url are why: origin may be your fork, which they make the
# project read as, and then no command that points origin at your fork can
# clear the refusal; or origin may be the project under a name they give it (an
# ssh alias, say). Nothing here can tell which, so the refusal lists those rules
# with where each lives, prints no commands, and says what to do in each case.
proj_hits=""; proj_raw=0
for ((_i = 0; _i < ${#o_url[@]}; _i++)); do
    [ "${o_url[$_i]}" != "$NOPUSH" ] || continue
    if [ "${o_fid[$_i]}" = "$up_fid" ] || [ "${o_fid[$_i]}" = "$up_raw_fid" ]; then
        proj_hits="$proj_hits$NL  origin's ${o_kind[$_i]} url ${o_url[$_i]} is the project's repository"
        if [ "${o_fid[$_i]}" = "$up_raw_fid" ]; then proj_raw=1; fi
    fi
done
# origin's own url and push url values, as git config holds them, are compared with the project's url
# as written too, ids folded, and so are its urls as a legacy file holds them where git reads one
# (config holds no url value of origin's): each URL: line of its .git/remotes file, trimmed as git
# trims it, or, where that file gives none, the first line of its .git/branches file, trimmed, up to
# any '#'. A value that names the project's repository is origin set to the project, whatever a rule
# makes git read it as: git reads the project's url through the same rules, so the urls above may match
# the project only as rewritten, or not at all where a rule matches origin's spelling of it alone. Such
# a value gets the refusal with the commands, and a line of its own where git rewrites it.
raw_hit() {  # <kind> <value> <what holds it>
    local u
    [ "$(fold_id "$(repo_id "$2")")" = "$up_raw_fid" ] || return 0
    proj_raw=1
    for u in ${o_url[@]+"${o_url[@]}"}; do [ "$u" != "$2" ] || return 0; done
    proj_hits="$proj_hits$NL  origin's $1 value $2, as $3 holds it, names the project's repository"
}
for _v in ${uv_val[@]+"${uv_val[@]}"}; do raw_hit url "$_v" "git config"; done
for _v in ${pv_val[@]+"${pv_val[@]}"}; do raw_hit "push url" "$_v" "git config"; done
if [ ${#uv_val[@]} -eq 0 ]; then
    _lg=0
    _f="$remotes_dir/origin"
    if [ -f "$_f" ] && [ -r "$_f" ]; then
        while IFS= read -r _line || [ -n "$_line" ]; do
            while [[ $_line == *[[:space:]] ]]; do _line="${_line%[[:space:]]}"; done
            case "$_line" in URL:*) ;; *) continue ;; esac
            _v="${_line#URL:}"
            while [[ $_v == [[:space:]]* ]]; do _v="${_v#[[:space:]]}"; done
            _lg=1
            raw_hit url "$_v" "the legacy file $_f"
        done < "$_f"
    fi
    _f="$branches_dir/origin"
    if [ $_lg -eq 0 ] && [ -f "$_f" ] && [ -r "$_f" ]; then
        _line=""; IFS= read -r _line < "$_f" || true
        while [[ $_line == *[[:space:]] ]]; do _line="${_line%[[:space:]]}"; done
        while [[ $_line == [[:space:]]* ]]; do _line="${_line#[[:space:]]}"; done
        if [ -n "$_line" ]; then raw_hit url "${_line%%#*}" "the legacy file $_f"; fi
    fi
fi
if [ -n "$proj_hits" ] && [ $proj_raw -eq 0 ]; then
    {
        echo "fork-remotes: origin is the project's repository as git reads the project's url, which a rule rewrites."
        echo "  origin = $origin_url"
        echo "  project = $proj_txt"
        printf '%s\n' "${proj_hits#"$NL"}"
        echo "git rewrites the project's url to that repository by these rules, each listed with where it lives:"
        rules_on "$UPSTREAM_URL" '^url\..*\.insteadof$'
        echo
        echo "If origin is your fork, these rules make the project read as your fork, and pointing origin elsewhere cannot change that: remove each one where it lives, then run $qscript --check again. If origin is the project under a name these rules give it (an ssh alias, say), it is not your fork: give origin your fork's url and push url in the clone's own config file, then run $qscript --check again."
        rules_info
    } >&2
    exit 1
fi
if [ -n "$proj_hits" ]; then
    {
        echo "fork-remotes: origin points at the upstream project, not at your fork."
        echo "  origin = $origin_url"
        echo "  project = $proj_txt"
        printf '%s\n' "${proj_hits#"$NL"}"
        if [ -n "$outside" ]; then
            echo "These urls of origin's, or pushInsteadOf rules that match one while origin has no push url, are held outside the clone's own config file, where no command printed here can change them. Remove each one where it lives$pi_fix, then run $qscript --check again:"
            outside_list
        else
            echo "Point origin at your fork first; these commands remove every url and push url origin has in the clone's own config file, then set your fork's url as its url and its push url:"
            print_steps
        fi
        rules_info
    } >&2
    exit 1
fi

# origin set by mistake to the url of another remote the clone carries (another fork kept as a second
# remote, say) passes every check that compares origin only with the project's url and with itself. A
# fetch from origin and a bare gh PR number would then read that other repository, and pushes may go
# there too. So each of origin's urls is compared by folded repo_id with each url of every other remote
# (a match refuses, so two spellings that may be one repository count as one). One finding per remote
# names both, with the first match, and lists the remote's url and push url values held outside the
# clone's own config file, which git remote remove does not reach, and the rules held there that rewrite
# a url of the remote's (remote_rules), so the url the note names can be traced to its config. The dead
# sentinel names no repository and is skipped on origin's side, which is enough (a match needs origin to
# carry it too): origin's push url set to it is the push check's finding. A remote whose urls git cannot
# read, where some config or legacy file gives it a url, is a finding too (unreadable): nothing can say
# it is not origin's repository. A remote that no config gives a url or a push url, and that no
# legacy file names (a fetch refspec alone in global config, say), has none of its own: git uses its
# name as its url, so that is what is compared, as git ls-remote --get-url reads it, and a finding on
# it lists every key that defines it held outside the clone's own config file, which git remote remove
# does not reach either (f_by says whether that file holds any of them). Where an insteadOf or
# pushInsteadOf rule rewrites the name of such a remote that git remote get-url refuses (one defined
# outside the clone), it is a finding (aliased). Set mode refuses on any finding, before it writes
# anything: it copies origin's first url onto its push url, which would send every push to the other
# remote's repository if origin was set to it by mistake.
f_kind=(); f_remote=(); f_text=(); f_files=(); f_list=()   # one entry per finding: origin's kind of url, unreadable or aliased
f_by=(); f_rules=()   # for a shared finding: local or outside where the remote's url is its name; the rules
up_unreadable=0   # upstream is a remote git cannot read, so --check cannot say there is none
for ((_x = 0; _x < ${#names[@]}; _x++)); do
    _r="${names[$_x]}"
    [ "$_r" != origin ] || continue
    # the legacy file(s) that define this remote, for the note to name: git reads them only for a
    # remote that config gives no url, whether or not git remote lists it, and ignores blank ones
    _files=""
    if [ -n "${n_files[$_x]}" ] && ! legacy_blank "${n_files[$_x]}" && ! git config --get-all "remote.$_r.url" >/dev/null 2>&1; then
        _files="${n_files[$_x]//$NL/ and }"
    fi
    if ! read_urls "$_r"; then
        if [ "${n_cfg[$_x]}" = 0 ] && legacy_blank "${n_files[$_x]}"; then continue; fi
        if has_url "$_r" || { [ -n "${n_files[$_x]}" ] && ! legacy_blank "${n_files[$_x]}"; }; then
            f_kind+=(unreadable); f_remote+=("$_r"); f_files+=("$_files"); f_list+=("$(remote_outside "$_r")")
            f_by+=(""); f_rules+=("")
            f_text+=("git cannot read the urls of remote '$_r' ($r_err)")
            if [ "$_r" = upstream ] && [ -z "$_files" ]; then up_unreadable=1; fi
            continue
        fi
        _rules="$(rules_on "$_r" '^url\..*\.(insteadof|pushinsteadof)$')"
        if [ -n "$_rules" ]; then
            f_kind+=(aliased); f_remote+=("$_r"); f_files+=(""); f_list+=("$_rules"); f_by+=(""); f_rules+=("")
            f_text+=("git cannot read the urls of remote '$_r' ($r_err)")
            if [ "$_r" = upstream ]; then up_unreadable=1; fi
            continue
        fi
        if ! r_fetch="$(git ls-remote --get-url -- "$_r" 2>/dev/null)"; then
            _err="$(git ls-remote --get-url -- "$_r" 2>&1 >/dev/null || true)"
            echo "fork-remotes: git cannot read remote '$_r' as a url: ${_err//$NL/ }" >&2
            exit 2
        fi
        r_push="$r_fetch"
    fi
    _rk=(); _ru=(); _rfid=()
    while IFS= read -r _u; do
        [ -n "$_u" ] || continue
        _rk+=(fetch); _ru+=("$_u"); _rfid+=("$(fold_id "$(repo_id "$_u")")")
    done <<<"$r_fetch"
    while IFS= read -r _u; do
        [ -n "$_u" ] || continue
        _rk+=(push); _ru+=("$_u"); _rfid+=("$(fold_id "$(repo_id "$_u")")")
    done <<<"$r_push"
    for ((_i = 0; _i < ${#o_url[@]}; _i++)); do
        [ "${o_url[$_i]}" != "$NOPUSH" ] || continue
        for ((_j = 0; _j < ${#_ru[@]}; _j++)); do
            if [ "${o_fid[$_i]}" = "${_rfid[$_j]}" ]; then
                if [ -z "$_files" ] && ! has_url "$_r"; then
                    remote_keys "$_r"
                    _by=local; [ $_rk_local -eq 1 ] || _by=outside
                    f_list+=("$_rk_out"); f_by+=("$_by"); f_rules+=("$(remote_rules "$_r" byname)")
                else
                    f_list+=("$(remote_outside "$_r")"); f_by+=(""); f_rules+=("$(remote_rules "$_r")")
                fi
                f_kind+=("${o_kind[$_i]}"); f_remote+=("$_r"); f_files+=("$_files")
                f_text+=("origin's ${o_kind[$_i]} url ${o_url[$_i]} is the same repository as remote '$_r' (${_rk[$_j]} url ${_ru[$_j]})")
                break 2
            fi
        done
    done
done

# What keeps set mode from fixing upstream. Set mode writes upstream's url and push url in the clone's
# own config file alone, and --replace-all puts its one value where the last value it replaces stood:
# - a url of upstream's held outside that file and read ahead of the last url the file holds: git
#   fetches from the first url, and set mode's write would not come first;
# - any url of upstream's held outside that file when the file holds none: git fetches from the first
#   of those, and set mode does not change them (whether its own write would come ahead of them depends
#   on where each is held, and is not worked out here);
# - a push url of upstream's held outside that file, other than the sentinel: a push goes to every push
#   url, and the sentinel set mode writes would join that one, not replace it;
# - an insteadOf rule, wherever it is held, that rewrites the sentinel itself: git applies insteadOf to
#   an explicit push url, so what set mode writes would push wherever the rule points.
# up_url_out and up_push_out list those values, and nopush_rules those rules, one line each with where
# it lives; up_has_local says whether the file holds a url of upstream's. up_exists says whether git
# reads an upstream at all (git remote get-url succeeds, the test git remote add makes: a key of
# upstream's in the repository's config, or a legacy file, even one whose url is empty). up_fetch is the
# url git fetches upstream from, and up_wrong says it is empty or not the project as git resolves it
# (ids read and compared where a match passes, see repo_id).
upstream_values() {
    local src val pend="" resolved
    up_url_out=""; up_push_out=""; nopush_rules=""; up_has_local=0
    while IFS= read -r -d '' src && IFS= read -r -d '' val; do
        if [ "$src" = "$local_cfg" ]; then
            up_has_local=1; up_url_out="$up_url_out$pend"; pend=""
        else
            pend="$pend$NL    remote.upstream.url $val ($(where_from "$src"))"
        fi
    done < <(git config -z --show-origin --get-all remote.upstream.url 2>/dev/null || true)
    if [ $up_has_local -eq 0 ]; then up_url_out="$pend"; fi
    while IFS= read -r -d '' src && IFS= read -r -d '' val; do
        if [ "$src" != "$local_cfg" ] && [ "$val" != "$NOPUSH" ]; then
            up_push_out="$up_push_out$NL    remote.upstream.pushurl $val ($(where_from "$src"))"
        fi
    done < <(git config -z --show-origin --get-all remote.upstream.pushurl 2>/dev/null || true)
    resolved="$(git ls-remote --get-url -- "$NOPUSH" 2>/dev/null || true)"
    if [ "$resolved" != "$NOPUSH" ]; then
        nopush_rules="$(rules_on "$NOPUSH" '^url\..*\.insteadof$')"
        [ -n "$nopush_rules" ] || nopush_rules="    $NOPUSH, which git reads as $resolved"
    fi
    up_url_out="${up_url_out#"$NL"}"; up_push_out="${up_push_out#"$NL"}"
}
upstream_values
up_exists=1
up_fetch="$(git remote get-url upstream 2>/dev/null)" || { up_exists=0; up_fetch=""; }
up_wrong=0
if [ $up_exists -eq 1 ] && { [ -z "$up_fetch" ] || [ "$(repo_id "$up_fetch" pass)" != "$up_pid" ]; }; then up_wrong=1; fi
up_said="upstream fetches from $up_fetch"
[ -n "$up_fetch" ] || up_said="upstream's first url is empty"
# what --check says of the urls of upstream's held outside the clone's own config file
if [ $up_has_local -eq 1 ]; then
    up_out_why="These urls of upstream's, held outside the clone's own config file, are read ahead of where set mode writes, so after a rerun git would fetch from the first of them"
else
    up_out_why="The clone's own config file, where set mode writes, holds no url of upstream's, and git fetches upstream from the first of these, held outside it, which set mode does not change"
fi

# Set mode refuses, writing nothing, on any finding above; on a url of origin's, or a pushInsteadOf rule
# that matches one while origin has no push url, held outside the clone's own config file; on a setting
# that aims a bare push or a bare gh PR number away from origin and that aim_values fails closed; on an
# includeIf entry that condinc_values lists; on an origin whose url is in no config; and on what keeps
# it from fixing upstream (see upstream_values). It has already refused on an empty value and on a rule
# whose base is empty.
if [ $check_only -eq 0 ] && { [ ${#f_kind[@]} -gt 0 ] || [ -n "$outside" ] || [ -n "$aim_out" ] || [ -n "$condinc_out" ] || [ -n "$legacy_origin" ] \
    || { [ $up_wrong -eq 1 ] && [ -n "$up_url_out" ]; } || [ -n "$up_push_out" ] || [ -n "$nopush_rules" ]; }; then
    {
        echo "fork-remotes: not configuring this clone; nothing was changed."
        for ((_i = 0; _i < ${#f_kind[@]}; _i++)); do echo "  ${f_text[$_i]}"; done
        if [ ${#f_kind[@]} -gt 0 ]; then
            echo "Set mode copies origin's first url onto its push url, which would send every push to another remote's repository if origin was set to it by mistake, and it cannot compare origin with a remote whose urls git cannot read."
        fi
        if [ -n "$outside" ]; then
            echo "These urls of origin's, or pushInsteadOf rules that match one while origin has no push url, are held outside the clone's own config file, where set mode cannot change them, so what it writes could not decide where a push to origin goes:"
            outside_list
        fi
        if [ -n "$aim_out" ]; then
            echo "These settings, which aim a bare push or a bare gh PR number away from origin, are held outside the clone's own config file, where set mode cannot change them:"
            aim_list
        fi
        if [ -n "$condinc_out" ]; then
            echo "These includeIf \"onbranch:\" and \"hasconfig:remote.*.url:\" entries name a file that sets a remote.*, url.* or branch.*.pushRemote key, or that --check cannot read in full. git reads it only while the entry's condition holds (a branch it matches is checked out, or a remote has a url it matches), which a branch switch or a remote write, set mode's own among them, can change; there a file that sets one of those keys can change where a push goes, and one git cannot read stops git. Set mode can neither see that from here nor change it:"
            condinc_list
        fi
        if [ -n "$legacy_origin" ]; then
            echo "origin's url is not in git config ($legacy_origin), so set mode has no url to copy onto its push url."
        fi
        if [ $up_wrong -eq 1 ] && [ -n "$up_url_out" ]; then
            if [ $up_has_local -eq 1 ]; then
                echo "$up_said, not the project ($proj_txt), and these urls of upstream's, held outside the clone's own config file, are read ahead of where set mode would write, so git would fetch from the first of them:"
            else
                echo "$up_said, not the project ($proj_txt); the clone's own config file, where set mode writes, holds no url of upstream's, and git fetches upstream from the first of these, held outside it, which set mode does not change:"
            fi
            printf '%s\n' "$up_url_out"
        fi
        if [ -n "$up_push_out" ]; then
            echo "These push urls of upstream's are held outside the clone's own config file, where set mode cannot remove them, and the sentinel it writes would join them rather than replace them:"
            printf '%s\n' "$up_push_out"
        fi
        if [ -n "$nopush_rules" ]; then
            echo "These rules rewrite the sentinel push url set mode writes for upstream, $NOPUSH, so a push to upstream would not fail:"
            printf '%s\n' "$nopush_rules"
        fi
        echo "Run $qscript --check for what to change."
    } >&2
    exit 1
fi

problems=0
rerun_fixes=0   # notes a rerun of set mode fixes
blocked=0       # notes on a state where set mode refuses, which withhold the rerun line
shared=0        # shared-repository notes, whose fix for origin is the commands printed after the notes
note() { problems=$((problems + 1)); echo "  ✗ $1"; }

if [ $check_only -eq 1 ]; then
    echo "fork-remotes: checking"
    # upstream fetches from the project, as git resolves both urls, and is fetch-only. A note a rerun of
    # set mode fixes asks for that rerun only where set mode's write would fix it; where something keeps
    # it from fixing upstream (see upstream_values), the note lists that, with where it lives, and set
    # mode refuses. An upstream that config defines, or whose name a rule rewrites, but whose urls git
    # cannot read has its own note below, which says so, and is not called missing; one that only an
    # unreadable legacy file names keeps the missing note, since git reads no url from that file and a
    # push to it fails. An upstream whose first url is empty, which nothing reaching here has (no value
    # is empty and no rule's base is), would still exist, and its note would say so.
    if [ $up_unreadable -eq 1 ]; then
        :
    elif [ $up_exists -eq 0 ]; then
        note "no 'upstream' remote (nothing to compare the fork against)"
        rerun_fixes=$((rerun_fixes + 1))
    elif [ $up_wrong -eq 1 ]; then
        if [ -n "$up_url_out" ]; then
            note "$up_said, expected $proj_txt. $up_out_why: remove each one where it lives, then run $qscript --check again$NL$up_url_out"
            blocked=$((blocked + 1))
        else
            note "$up_said, expected $proj_txt"
            rerun_fixes=$((rerun_fixes + 1))
        fi
    fi
    # every push url upstream carries: a push goes to each, so one besides the sentinel is enough (an
    # empty one names nowhere: a push to it fails). A push url held outside the clone's own config file,
    # other than the sentinel, makes set mode refuse whether or not git would push to it (see
    # upstream_values), so --check names each such value with where it lives, and no rerun line.
    if [ $up_exists -eq 1 ]; then
        up_pushable=""
        while IFS= read -r _u; do
            if [ -z "$_u" ] || [ "$_u" = "$NOPUSH" ]; then continue; fi
            up_pushable="${up_pushable:+$up_pushable, }$_u"
        done < <(git remote get-url --push --all upstream 2>/dev/null || true)
        if [ -n "$up_push_out" ]; then
            if [ -n "$up_pushable" ]; then
                _pp="upstream is PUSHABLE ($up_pushable): a stray push to upstream goes there instead of failing. These push urls of upstream's are held outside the clone's own config file, where set mode cannot remove them"
            else
                _pp="these push urls of upstream's are held outside the clone's own config file, where set mode cannot remove them, and the sentinel it writes would join them rather than replace them, so it refuses to run"
            fi
            note "$_pp: remove each one where it lives, then run $qscript --check again$NL$up_push_out"
            blocked=$((blocked + 1))
        elif [ -n "$up_pushable" ]; then
            note "upstream is PUSHABLE ($up_pushable): a stray push to upstream goes there instead of failing"
            rerun_fixes=$((rerun_fixes + 1))
        fi
    fi
    if [ -n "$nopush_rules" ]; then
        note "set mode makes upstream fetch-only by writing $NOPUSH as its push url, and git rewrites that url by these rules, so a push to upstream would reach a repository instead of failing: remove each one where it lives, then run $qscript --check again$NL$nopush_rules"
        blocked=$((blocked + 1))
    fi
    # Values of origin's, and pushInsteadOf rules that match one while origin has no push url, held
    # outside the clone's own config file: no rerun of set mode can change them, so --check names each
    # and where it lives, prints no step commands and no rerun line, and set mode refuses until they are
    # gone. Such a rule also stops applying once origin has a push url in the clone's own config file,
    # and the note says so, with the one command that sets it (pi_fix).
    if [ -n "$outside" ]; then
        note "these urls of origin's, or pushInsteadOf rules that match one while origin has no push url, are held outside the clone's own config file (the one git config --local writes), where neither set mode nor a command printed here can change them: remove each one where it lives$pi_fix, then run $qscript --check again$NL$(outside_list)"
        blocked=$((blocked + 1))
    fi
    if [ -n "$legacy_origin" ]; then
        if [ -z "$outside" ]; then
            _lfix="set origin's url in the clone's own config file with the commands below (git reads no legacy file for a remote whose url is in config)"
        else
            _lfix="once the values held outside the clone's own config file are gone, --check gives the commands that set origin's url there"
        fi
        note "origin's url is not in git config ($legacy_origin), and set mode, which copies origin's url onto its push url, refuses to run: $_lfix"
        blocked=$((blocked + 1))
    fi
    # origin's PUSH urls are separate from its fetch url. A push goes to every push url, so each is
    # compared with the repository origin fetches from (ids compared exactly: a match passes). Set mode
    # fixes this (it replaces every push url in the clone's own config file with origin's first url),
    # except for a push url held outside that file, which it cannot remove. Which offending url is held
    # where comes from lining origin's push url values up with the urls get-url prints, one for one: git
    # prints one url for each push url value, and none is empty here (the check above stops on an empty
    # value and on a rule whose base is empty, the one way git rewrites a url to nothing), so the counts
    # agree. They are compared all the same before a value is looked up, so that where they differ in a
    # way this script does not foresee no url is attributed, rather than the wrong place named. The note
    # names each offending url held outside with where it lives. With no push url values, set mode's
    # write replaces the urls a push goes to.
    _aligned=0
    if [ ${#pv_src[@]} -gt 0 ] && [ ${#pv_src[@]} -eq $n_push ]; then _aligned=1; fi
    _off=""; _off_out=""; _k=0
    for ((_i = 0; _i < ${#o_url[@]}; _i++)); do
        [ "${o_kind[$_i]}" = push ] || continue
        if [ "${o_id[$_i]}" != "$origin_id" ]; then
            _off="${_off:+$_off, }${o_url[$_i]}"
            if [ $_aligned -eq 1 ] && [ "${pv_src[$_k]}" != "$local_cfg" ]; then
                _off_out="${_off_out:+$_off_out, }${o_url[$_i]} ($(where_from "${pv_src[$_k]}"))"
            fi
        fi
        _k=$((_k + 1))
    done
    if [ -n "$_off" ]; then
        if [ -n "$_off_out" ]; then
            note "origin PUSHES to $_off, not the repository it fetches from ($origin_url); a push to origin goes to $origin_pushes. Set mode cannot remove $_off_out, held outside the clone's own config file"
        else
            note "origin PUSHES to $_off, not the repository it fetches from ($origin_url); a push to origin goes to $origin_pushes"
            rerun_fixes=$((rerun_fixes + 1))
        fi
    fi
    # The findings of the shared-repository check above. A rerun of set mode fixes none of them (set
    # mode refuses while one stands), so beside any of them the rerun line is withheld, and the reader
    # is told to fix origin, or the other remote, and run --check again. The fix for origin is the
    # commands printed after the notes, unless a value of origin's is held outside the clone's own
    # config file, which has its own note. The fix for the other remote names where its values live:
    # a legacy file, each url or push url held outside the clone's own config file, and, for a remote
    # whose url is its name, each key held there that defines it (git remote remove acts on that file
    # alone, and refuses a remote it does not define). The rules held there that rewrite a url of the
    # remote's are listed too, so the url the note names can be traced to its config.
    if [ -z "$outside" ]; then
        _fix="the commands below point it at your fork"
    else
        _fix="remove what the note on values held outside the clone's own config file lists, and --check then gives the commands that point it at your fork"
    fi
    for ((_i = 0; _i < ${#f_kind[@]}; _i++)); do
        _r="${f_remote[$_i]}"
        _rm="Remove '$_r' if it is a second name for your fork"
        [ -z "${f_files[$_i]}" ] || _rm="$_rm (delete ${f_files[$_i]}, which defines it)"
        case "${f_by[$_i]}" in
            outside)
                _rm="If '$_r' is a second name for your fork, remove each key listed below where it lives: no config gives it a url, so git uses its name as its url, and git remote remove, which acts on the clone's own config file alone, cannot remove a remote that file does not define"
                ;;
            local)
                [ -z "${f_list[$_i]}" ] || _rm="$_rm; no config gives it a url, so git uses its name as its url, and git remote remove does not reach the keys that define it outside the clone's own config file, listed below, so remove each where it lives"
                ;;
            *)
                [ -z "${f_list[$_i]}" ] || _rm="$_rm; git remote remove does not reach its url and push url values held outside the clone's own config file, listed below, so remove each where it lives"
                ;;
        esac
        [ -z "${f_rules[$_i]}" ] || _rm="$_rm; git reads its url named above through the rules listed below, held outside the clone's own config file"
        _lst=""
        [ -z "${f_list[$_i]}" ] || _lst="$NL${f_list[$_i]}"
        [ -z "${f_rules[$_i]}" ] || _lst="$_lst$NL${f_rules[$_i]}"
        case "${f_kind[$_i]}" in
            unreadable)
                if [ -n "${f_files[$_i]}" ]; then
                    note "${f_text[$_i]}: the legacy file ${f_files[$_i]} defines it, and git reads no url from that file. --check cannot tell whether it is origin's repository: delete or repair the file"
                else
                    _up=""
                    [ "$_r" != upstream ] || _up=" Its push urls could not be checked either, so --check cannot say whether a push to upstream would fail."
                    note "${f_text[$_i]}: git reads a remote this way when only global or system config, or the environment (GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS), defines it, and a push to it still works.$_up --check cannot tell whether it is origin's repository, and set mode does not change remotes defined there: remove its url and push url values where each lives, then run $qscript --check again$_lst"
                fi
                ;;
            aliased)
                note "${f_text[$_i]}: no config gives it a url or a push url and no legacy file names it, so git uses its name as its url, which these rules rewrite: a fetch from it or a push to it goes wherever they point. --check does not compare a name that a rule rewrites, since git ls-remote --get-url shows an insteadOf rewrite of it but not a pushInsteadOf one: remove each rule where it lives, or the remote where it is defined (git -C $qtop config --show-origin --get-regexp '^remote\\.' lists where, and calls the environment 'command line:'), then run $qscript --check again$_lst"
                ;;
            fetch)
                note "${f_text[$_i]}: a fetch from origin and a bare gh PR number read that repository, and a push to origin goes to $origin_pushes. $_rm; if origin was set to that url by mistake, $_fix$_lst"
                shared=$((shared + 1))
                ;;
            extra)
                note "${f_text[$_i]}: git fetches only from origin's first url, and a push to origin goes to $origin_pushes. $_rm; if the url was added to origin by mistake, $_fix$_lst"
                shared=$((shared + 1))
                ;;
            *)
                note "${f_text[$_i]}: a push to origin goes to $origin_pushes. $_rm; if origin was set to push there by mistake, $_fix$_lst"
                shared=$((shared + 1))
                ;;
        esac
        blocked=$((blocked + 1))
    done
    # a bare `git push` goes to remote.pushDefault, and without one to the branch's own remote, which
    # may be any remote; set mode sets it to origin. The value is the one git uses, read exactly, and
    # where it is held outside the clone's own config file the note says where (see aim_values, which
    # also says whether a rerun fixes it or it fails closed).
    if [ $pd_set -eq 0 ]; then
        note "remote.pushDefault is unset: a bare 'git push' from a branch that tracks another remote goes there, not to your fork"
        rerun_fixes=$((rerun_fixes + 1))
    elif [ "$pd_val" != "origin" ]; then
        note "remote.pushDefault is '$pd_val'$pd_at: a bare 'git push' would not go to your fork"
        [ $pd_fix -eq 0 ] || rerun_fixes=$((rerun_fixes + 1))
    fi
    # branch.<name>.pushRemote OVERRIDES remote.pushDefault, so checking only pushDefault above misses
    # a per-branch push aimed elsewhere: each branch's value git uses, when it is not 'origin', exactly
    # (a value such as ' origin' is another remote).
    for ((_i = 0; _i < ${#pr_key[@]}; _i++)); do
        note "${pr_key[$_i]} is '${pr_val[$_i]}'${pr_at[$_i]}: a bare push from that branch would not go to your fork"
        [ "${pr_fix[$_i]}" -eq 0 ] || rerun_fixes=$((rerun_fixes + 1))
    done
    # gh's default repository (see the header): origin must carry `gh-resolved = base` and no other
    # remote may carry the key at all (gh reads upstream's and github's before origin's, and a
    # default anywhere but origin is one too many). A value other than 'base' on origin names some
    # OWNER/REPO outright, which gh then uses instead of origin.
    if [ $gh_set -eq 0 ]; then
        note "gh has no default repository (remote.origin.gh-resolved is unset): a bare 'gh pr merge N' from a script would aim at the project, not your fork"
        rerun_fixes=$((rerun_fixes + 1))
    elif [ "$gh_val" != "base" ]; then
        note "remote.origin.gh-resolved is '$gh_val'$gh_at, not 'base': gh would resolve a bare PR number against that repo, not your fork"
        [ $gh_fix -eq 0 ] || rerun_fixes=$((rerun_fixes + 1))
    fi
    # every other remote carrying the key, once each, with how many values it holds: a doubled key (two
    # `git config --add` by hand) is what a plain --unset refused to clear, so the note names the remote
    # and the count, and a rerun of set mode (--unset-all) clears it. Keys and values are read with -z,
    # so a remote whose name holds a space is read whole.
    _gh_seen="$NL"
    while IFS= read -r -d '' _gh_key; do
        [ "$_gh_key" != "remote.origin.gh-resolved" ] || continue
        case "$_gh_seen" in *"$NL$_gh_key$NL"*) continue ;; esac
        _gh_seen="$_gh_seen$_gh_key$NL"
        _gh_remote="${_gh_key#remote.}"; _gh_remote="${_gh_remote%.gh-resolved}"
        _gh_n=0; _gh_vals=""
        while IFS= read -r -d '' _v; do
            _gh_n=$((_gh_n + 1)); _gh_vals="${_gh_vals:+$_gh_vals }$_v"
        done < <(git config -z --get-all "$_gh_key" 2>/dev/null || true)
        note "remote '$_gh_remote' carries gh's default-repository key ($_gh_key: $_gh_n value(s), '$_gh_vals'); only origin should, else gh may resolve a bare PR number there, not on your fork"
        rerun_fixes=$((rerun_fixes + 1))
    done < <(git config -z --name-only --get-regexp '^remote\..*\.gh-resolved$' 2>/dev/null || true)
    # Those settings, where one aims away from origin from somewhere set mode's write does not override
    # (see aim_values): set mode refuses while one stands.
    if [ -n "$aim_out" ]; then
        note "these settings, which aim a bare push or a bare gh PR number away from origin, are held outside the clone's own config file (the one git config --local writes), where set mode cannot change them: remove each one where it lives, then run $qscript --check again$NL$(aim_list)"
        blocked=$((blocked + 1))
    fi
    # includeIf entries whose file can change where a push goes once a branch switch or a remote write
    # makes their condition hold (see condinc_values): --check names each, set mode refuses while one
    # stands, so no rerun line.
    if [ -n "$condinc_out" ]; then
        note "these includeIf \"onbranch:\" and \"hasconfig:remote.*.url:\" entries name a file that sets a remote.*, url.* or branch.*.pushRemote key, or that --check cannot read in full. git reads it only while the entry's condition holds (a branch it matches is checked out, or a remote has a url it matches), which a branch switch or a remote write, set mode's own among them, can change; there a file that sets one of those keys can change where a push goes, and one git cannot read stops git. --check reads config only as it stands and cannot see that, and set mode cannot change it: remove each entry where it lives, or change its file so that it sets none of those keys and --check can read it in full, then run $qscript --check again$NL$(condinc_list)"
        blocked=$((blocked + 1))
    fi
    if [ $problems -eq 0 ]; then
        # what the checks above verified, and nothing more: none of them requires a third remote to be
        # fetch-only, so one that shares no repository with origin may push anywhere
        echo "  ✓ upstream fetches from the project, as git resolves both urls, and is fetch-only; origin's urls, and any pushInsteadOf rule that matches one while origin has no push url, are in the clone's own config file, no remote's url or push url value is empty and no insteadOf or pushInsteadOf rule has an empty base, and no includeIf \"onbranch:\" or \"hasconfig:remote.*.url:\" entry names a file that sets a remote.*, url.* or branch.*.pushRemote key or that --check cannot read in full; every push to origin goes to the repository it fetches from, and origin shares no repository with another remote; the remote.pushDefault git uses is origin, and no branch's pushRemote that git uses names another remote; origin is gh's only default repository"
        exit 0
    fi
    rules_info
    aim_info_list
    # The commands, where the notes ask for them and nothing outside the clone's own config file would
    # defeat them; then the rerun line only where nothing blocks set mode and a rerun fixes something.
    # Beside a note on a state where set mode refuses, the reader is told to fix what the notes name and
    # run --check again, which says when that is done.
    if [ $shared -gt 0 ] || [ -n "$legacy_origin" ]; then
        if [ -z "$outside" ]; then
            {
                echo "If origin was set to another remote's url by mistake, or git config holds no url for it, these commands, which act on this clone from any directory, remove every url and push url origin has in the clone's own config file, then set your fork's url as its url and its push url. git applies no pushInsteadOf rule to a push url; an insteadOf rule that matches the url you type rewrites both."
                print_steps
            } >&2
        fi
    fi
    if [ $blocked -gt 0 ]; then
        echo "Fix what the notes above name, then run $qscript --check again; set mode refuses to run while a remote's url or push url value is empty, an insteadOf or pushInsteadOf rule has an empty base, origin shares a repository with another remote, git cannot read a remote's urls, git config holds no url for origin, an includeIf \"onbranch:\" or \"hasconfig:remote.*.url:\" entry names a file that sets a remote.*, url.* or branch.*.pushRemote key or that --check cannot read in full, upstream does not fetch from the project while a url of upstream's held outside the clone's own config file is read ahead of the last one that file holds or that file holds none, upstream has a push url other than the sentinel held outside that file, a url rule rewrites the sentinel, or one of these is held anywhere but the clone's own config file, where it wins over anything set mode writes: a url of origin's, a pushInsteadOf rule that matches one while origin has no push url, or a setting that aims a bare push or a bare gh PR number away from origin." >&2
    elif [ $rerun_fixes -gt 0 ]; then
        echo "Run $qscript to fix." >&2
    else
        echo "Fix what the notes above name, then run $qscript --check again." >&2
    fi
    exit 1
fi

# --replace-all here and below: a key holding several values (an upstream with two urls, an upstream or
# origin with two push urls, or a doubled pushDefault) makes a plain set, or git remote set-url, refuse,
# which would stop set mode part way through. Whether upstream exists is up_exists, git remote get-url's
# exit status, which is the test git remote add makes before it refuses ("remote upstream already
# exists"): a key of upstream's in the repository's config, or a legacy file. Its output would not do as
# the test: it is an empty line for an upstream whose url is empty, which set mode has refused on above.
if [ $up_exists -eq 1 ]; then
    git config --replace-all remote.upstream.url "$UPSTREAM_URL"
else
    git remote add upstream "$UPSTREAM_URL"
fi
git config --replace-all remote.upstream.pushurl "$NOPUSH"
git config --replace-all remote.pushDefault origin
# Fix the two overrides --check now also inspects, so "run fork-remotes.sh to fix" is honest: a
# repointed origin push url, and any per-branch pushRemote aimed away from the fork (these override
# remote.pushDefault). origin's push url is set to its first url as git config holds it, not as git
# resolves it: git applies insteadOf to a push url as it does to a fetch url, so the raw value pushes
# where origin fetches, while a resolved value would be rewritten again by an insteadOf rule that
# matches it (chained rules) and push somewhere else. Every url of origin's is in the clone's own
# config file here and none is empty (set mode refuses otherwise), so the value copied is one this
# clone holds and the first url every git reads, whichever way it reads an empty value. Keys and values
# are read with -z, as --check reads them. Each pushRemote git uses that names another remote is held
# in the clone's own config file here (set mode refuses otherwise), and removing it there leaves git a
# value that aims at origin, or none (see aim_values); a pushRemote git uses that names origin is left
# alone, wherever a value overridden by it is held.
git config --replace-all remote.origin.pushurl "$origin_raw"
for ((_i = 0; _i < ${#pr_key[@]}; _i++)); do
    git config --unset-all "${pr_key[$_i]}" || true
done
# gh's default repository is origin, and origin alone: the same key on upstream or github is read
# before origin's (see the header), and on any remote it is a second default, so it goes too.
# --replace-all, because a hand `git config --add` can leave two values under origin's key and a
# plain set then refuses to overwrite them, which would stop set mode after the push guards; and
# --unset-all on the other remotes' keys for the same reason: a plain --unset refuses a doubled key,
# and the `|| true` swallowed that refusal, so the key survived a run that printed configured.
git config --replace-all remote.origin.gh-resolved base
while IFS= read -r -d '' _gh_key; do
    [ "$_gh_key" != "remote.origin.gh-resolved" ] || continue
    git config --unset-all "$_gh_key" || true
done < <(git config -z --name-only --get-regexp '^remote\..*\.gh-resolved$' 2>/dev/null || true)

echo "fork-remotes: configured"
echo "  origin   $origin_url  (fetch + push: your fork, and gh's default repository)"
echo "  upstream $UPSTREAM_URL  (fetch only; push disabled)"
echo "  a bare 'git push' goes to origin, and so does a bare 'gh pr <cmd> N'"
echo
echo "Check what the project has added since:  $qtop/scripts/upstream-check.sh"
