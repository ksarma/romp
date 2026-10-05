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
# nothing, while origin shares a repository with another remote, git cannot read
# a remote's urls, git config holds no url for origin, or one of these is held
# anywhere but the clone's own config file: a url of origin's, a rule that
# rewrites one, or a setting that aims a bare push or a bare gh PR number away
# from origin (see the checks below).
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
# '.', '..' and empty segments resolved by spelling. Then trailing slashes and
# .git suffixes come off until none is left, so 'X.git/', 'X/.git' and
# 'X.git.git' all read as 'X'. Nothing is lowercased: a difference in case
# anywhere but the scheme reads as a different repository, so 'X.GIT' is not
# 'X'; a forge ignores case in owner and repository names, so there two
# spellings of one repository read as two (origin spelled Romp-On/romp is not
# taken for the project, and an upstream spelled that way fails the upstream
# check).
# Dropping the scheme and the user merges what a plain ssh host keeps apart:
# https://host/x, ssh://host/x and host:x read as one, which a forge serves as
# one repository, but the scp form's path is relative to the login's home
# directory, so on a plain ssh host host:x and ssh://host/x name two paths, as
# do two users' host:x. Not normalized: host aliases, DNS names, ssh config Host
# entries, any port other than the default (ftp's and ftps's default ports
# among them), a ~ home-directory spelling (ssh://host/~/x names what host:x
# names), a doubled slash in a url with a host, a bracketed IPv6 host in the scp
# form, and symlinks in a local path.
repo_id() {
    local u="$1" re='^([A-Za-z][A-Za-z0-9+.-]*)://([^/]*)(.*)$' scheme host path
    if [[ $u =~ $re ]]; then
        scheme="${BASH_REMATCH[1]}"; host="${BASH_REMATCH[2]##*@}"; path="${BASH_REMATCH[3]}"
        case "$scheme:${host##*:}" in
            https:443|http:80|ssh:22|git+ssh:22|ssh+git:22|git:9418) host="${host%:*}" ;;
        esac
        if [ "$scheme" = file ]; then norm_path "$path"; u="$_np"; else u="$host$path"; fi
    elif [[ $u == *:* && ${u%%:*} != */* ]]; then
        # the scp form: a colon with no slash ahead of it, as git reads it
        host="${u%%:*}"; path="${u#*:}"
        u="${host##*@}/${path#/}"
    else
        case "$u" in /*) ;; *) u="$toplevel/$u" ;; esac
        norm_path "$u"; u="$_np"
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
# remote lists and a push still uses, and a name that only an unreadable legacy file supplies. The --
# keeps a remote whose name starts with a dash from being read as an option.
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

# origin's first url, as git resolves it, or git's own error.
if ! origin_url="$(git remote get-url origin 2>/dev/null)"; then
    _err="$(git remote get-url origin 2>&1 >/dev/null || true)"
    echo "fork-remotes: git cannot read origin's url: ${_err//$NL/ }" >&2
    exit 2
fi
[ -n "$origin_url" ] || { echo "fork-remotes: origin's first url is empty" >&2; exit 2; }

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

# origin's url and push url values as git config holds them, read exactly (-z): origin_raw, its first
# url value, which set mode copies onto its push url; how many of them the clone's own config file
# holds (n_local_url, n_local_push); the source of each push url value in the order git reads them
# (pv_src, which lines up one for one with get-url --push --all when origin has push urls); and, in
# outside, one line per value held anywhere else (an included file, config.worktree, global or system
# config, the environment), and per insteadOf or pushInsteadOf rule held anywhere else whose value
# starts one of origin's values, each with where it lives. Nothing printed here can change those, and
# set mode cannot either, so they fail closed. The clone's own config file is the one --local reads
# (it reads no include), as --show-origin spells it.
origin_values() {
    local key src val ent v vals=()
    origin_raw=""; n_local_url=0; n_local_push=0; outside=""; pv_src=(); pv_empty=0; local_cfg=""
    IFS= read -r -d '' local_cfg < <(git config --local --show-origin -z --list 2>/dev/null) || true
    for key in remote.origin.url remote.origin.pushurl; do
        while IFS= read -r -d '' src && IFS= read -r -d '' val; do
            vals+=("$val")
            if [ $key = remote.origin.url ]; then
                [ ${#vals[@]} -ne 1 ] || origin_raw="$val"
            else
                pv_src+=("$src")
                [ -n "$val" ] || pv_empty=1
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
            case "$v" in "$_pr_val"*) outside="$outside$NL$_pr_key $_pr_val ($(where_from "$src"))"; break ;; esac
        done
    done < <(git config -z --show-origin --get-regexp '^url\..*\.(insteadof|pushinsteadof)$' 2>/dev/null || true)
    outside="${outside#"$NL"}"
}
origin_values

# The settings that decide where a bare push or a bare gh PR number goes, held anywhere but the clone's
# own config file, when they aim it away from origin: remote.pushDefault or a branch's pushRemote naming
# another remote, gh-resolved on another remote, and gh-resolved on origin with a value other than
# base. Set mode writes only the clone's own config file, so a rerun cannot change one, and like
# origin's values held outside they fail closed: aim_out gets one line per value, with where it lives.
# A value that names origin (base, on origin's gh-resolved) aims nowhere else and is left out.
aim_values() {
    local src ent
    aim_out=""
    while IFS= read -r -d '' src && IFS= read -r -d '' ent; do
        [ "$src" != "$local_cfg" ] || continue
        pr_split "$ent"
        case "$_pr_key" in
            remote.pushdefault|branch.*.pushremote) [ "$_pr_val" != origin ] || continue ;;
            remote.origin.gh-resolved) [ "$_pr_val" != base ] || continue ;;
        esac
        aim_out="$aim_out$NL$_pr_key $_pr_val ($(where_from "$src"))"
    done < <(git config -z --show-origin --get-regexp '^(remote\.pushdefault|branch\..*\.pushremote|remote\..*\.gh-resolved)$' 2>/dev/null || true)
    aim_out="${aim_out#"$NL"}"
}
aim_values

# An origin whose url is in no config: a legacy .git/remotes or .git/branches file defines it (git reads
# one only for a remote that config gives no url), or, with neither, git reads the name origin as its
# url. legacy_origin says which, and is empty when config holds origin's url.
remotes_dir="$(git rev-parse --git-path remotes)"; branches_dir="$(git rev-parse --git-path branches)"
case "$remotes_dir" in /*) ;; *) remotes_dir="$toplevel/$remotes_dir" ;; esac
case "$branches_dir" in /*) ;; *) branches_dir="$toplevel/$branches_dir" ;; esac
legacy_origin=""
if [ -z "$origin_raw" ]; then
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
# printed only when every value of origin's, and every rule that rewrites one, is in that file, where
# they act; each names the clone with git -C.
print_steps() {
    if [ $n_local_url -gt 0 ]; then echo "    git -C $qtop config --unset-all remote.origin.url"; fi
    if [ $n_local_push -gt 0 ]; then echo "    git -C $qtop config --unset-all remote.origin.pushurl"; fi
    echo "    git -C $qtop config remote.origin.url <your-fork-url>"
    echo "    git -C $qtop config remote.origin.pushurl <your-fork-url>"
}
aim_list() { printf '%s\n' "$aim_out" | sed 's/^/    /'; }
outside_list() { printf '%s\n' "$outside" | sed 's/^/    /'; }

# The one thing we cannot fix by ourselves. If origin IS the upstream project,
# this is not a fork clone (or someone re-pointed origin), and setting up
# fetch-only upstream would leave every push aimed at the project. Say so and
# stop rather than configure something misleading.
if [ "$(repo_id "$origin_url")" = "$(repo_id "$UPSTREAM_URL")" ]; then
    {
        echo "fork-remotes: origin points at the upstream project, not at your fork."
        echo "  origin = $origin_url"
        if [ -n "$outside" ]; then
            echo "These urls of origin's, or rules that rewrite them, are held outside the clone's own config file, where no command printed here can change them. Remove each one where it lives, then run $qscript --check again:"
            outside_list
        else
            echo "Point origin at your fork first; these commands remove every url and push url origin has in the clone's own config file, then set your fork's url as its url and its push url:"
            print_steps
        fi
    } >&2
    exit 1
fi

# origin's urls, each with its kind and repo_id, in this order: its first url, the one git fetches
# from (fetch); any url after the first (extra), which git never fetches from, and pushes to when
# origin has no push url and no pushInsteadOf rule rewrites its urls; and the urls a push to origin
# uses (push). origin_pushes lists where a push to origin goes, read from git rather than assumed.
read_urls origin
o_kind=(); o_url=(); o_id=()
_kind=fetch
while IFS= read -r _u; do
    [ -n "$_u" ] || continue
    o_kind+=("$_kind"); o_url+=("$_u"); o_id+=("$(repo_id "$_u")"); _kind=extra
done <<<"$r_fetch"
origin_pushes=""; n_push=0
while IFS= read -r _u; do
    [ -n "$_u" ] || continue
    o_kind+=(push); o_url+=("$_u"); o_id+=("$(repo_id "$_u")"); n_push=$((n_push + 1))
    origin_pushes="${origin_pushes:+$origin_pushes, }$_u"
done <<<"$r_push"
origin_id="$(repo_id "$origin_url")"

# origin set by mistake to the url of another remote the clone carries (another fork kept as a second
# remote, say) passes every check that compares origin only with the project's url and with itself. A
# fetch from origin and a bare gh PR number would then read that other repository, and pushes may go
# there too. So each of origin's urls is compared by repo_id with each url of every other remote: the
# names git remote lists, and the names a legacy .git/remotes or .git/branches file supplies, which git
# remote leaves out though a push and get-url use them. One finding per remote names both, with the
# first match. The dead sentinel names no repository and is skipped on origin's side, which is enough
# (a match needs origin to carry it too): origin's push url set to it is the push check's finding. A
# remote whose urls git cannot read is a finding too: nothing can say it is not origin's repository.
# Set mode refuses on any finding, before it writes anything: it copies origin's first url onto its
# push url, which would send every push to the other remote's repository if origin was set to it by
# mistake.
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
f_kind=(); f_remote=(); f_text=(); f_files=()   # one entry per finding: origin's kind of url, or unreadable
for ((_x = 0; _x < ${#names[@]}; _x++)); do
    _r="${names[$_x]}"
    [ "$_r" != origin ] || continue
    # the legacy file(s) that define this remote, for the note to name: git reads them only for a
    # remote that config gives no url, whether or not git remote lists it
    _files=""
    if [ -n "${n_files[$_x]}" ] && ! git config --get-all "remote.$_r.url" >/dev/null 2>&1; then
        _files="${n_files[$_x]//$NL/ and }"
    fi
    if ! read_urls "$_r"; then
        if [ "${n_cfg[$_x]}" = 0 ] && legacy_blank "${n_files[$_x]}"; then continue; fi
        f_kind+=(unreadable); f_remote+=("$_r"); f_files+=("$_files")
        f_text+=("git cannot read the urls of remote '$_r' ($r_err)")
        continue
    fi
    _rk=(); _ru=(); _rid=()
    while IFS= read -r _u; do
        [ -n "$_u" ] || continue
        _rk+=(fetch); _ru+=("$_u"); _rid+=("$(repo_id "$_u")")
    done <<<"$r_fetch"
    while IFS= read -r _u; do
        [ -n "$_u" ] || continue
        _rk+=(push); _ru+=("$_u"); _rid+=("$(repo_id "$_u")")
    done <<<"$r_push"
    for ((_i = 0; _i < ${#o_url[@]}; _i++)); do
        [ "${o_url[$_i]}" != "$NOPUSH" ] || continue
        for ((_j = 0; _j < ${#_ru[@]}; _j++)); do
            if [ "${o_id[$_i]}" = "${_rid[$_j]}" ]; then
                f_kind+=("${o_kind[$_i]}"); f_remote+=("$_r"); f_files+=("$_files")
                f_text+=("origin's ${o_kind[$_i]} url ${o_url[$_i]} is the same repository as remote '$_r' (${_rk[$_j]} url ${_ru[$_j]})")
                break 2
            fi
        done
    done
done

# Set mode refuses, writing nothing, on any finding above, on a url of origin's or a rule that rewrites
# one held outside the clone's own config file, on a setting held there that aims a bare push or a bare
# gh PR number away from origin, and on an origin whose url is in no config.
if [ $check_only -eq 0 ] && { [ ${#f_kind[@]} -gt 0 ] || [ -n "$outside" ] || [ -n "$aim_out" ] || [ -n "$legacy_origin" ]; }; then
    {
        echo "fork-remotes: not configuring this clone; nothing was changed."
        for ((_i = 0; _i < ${#f_kind[@]}; _i++)); do echo "  ${f_text[$_i]}"; done
        if [ ${#f_kind[@]} -gt 0 ]; then
            echo "Set mode copies origin's first url onto its push url, which would send every push to another remote's repository if origin was set to it by mistake, and it cannot compare origin with a remote whose urls git cannot read."
        fi
        if [ -n "$outside" ]; then
            echo "These urls of origin's, or rules that rewrite them, are held outside the clone's own config file, where set mode cannot change them, so what it writes could not decide where a push to origin goes:"
            outside_list
        fi
        if [ -n "$aim_out" ]; then
            echo "These settings, which aim a bare push or a bare gh PR number away from origin, are held outside the clone's own config file, where set mode cannot change them:"
            aim_list
        fi
        if [ -n "$legacy_origin" ]; then
            echo "origin's url is not in git config ($legacy_origin), so set mode has no url to copy onto its push url."
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
    up_fetch="$(git remote get-url upstream 2>/dev/null || true)"
    if [ -z "$up_fetch" ]; then
        note "no 'upstream' remote (nothing to compare the fork against)"
        rerun_fixes=$((rerun_fixes + 1))
    elif [ "$(repo_id "$up_fetch")" != "$(repo_id "$UPSTREAM_URL")" ]; then
        note "upstream fetches from $up_fetch, expected $UPSTREAM_URL"
        rerun_fixes=$((rerun_fixes + 1))
    fi
    # every push url upstream carries: a push goes to each, so one besides the sentinel is enough
    if [ -n "$up_fetch" ]; then
        up_pushable=""
        while IFS= read -r _u; do
            [ "$_u" = "$NOPUSH" ] || up_pushable="${up_pushable:+$up_pushable, }$_u"
        done < <(git remote get-url --push --all upstream 2>/dev/null || true)
        if [ -n "$up_pushable" ]; then
            note "upstream is PUSHABLE ($up_pushable): a stray push to upstream goes there instead of failing"
            rerun_fixes=$((rerun_fixes + 1))
        fi
    fi
    # Values of origin's, and rules that rewrite them, held outside the clone's own config file: no
    # printed command and no rerun of set mode can change them, so --check names each and where it
    # lives, prints no commands and no rerun line, and set mode refuses until they are gone.
    if [ -n "$outside" ]; then
        note "these urls of origin's, or rules that rewrite them, are held outside the clone's own config file (the one git config --local writes), where neither set mode nor a command printed here can change them: remove each one where it lives, then run $qscript --check again$NL$(outside_list)"
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
    # origin's PUSH urls are separate from its fetch url; the repo_id check at the top read only fetch.
    # A push goes to every push url, so each is compared with the repository origin fetches from. Set
    # mode fixes this (it replaces every push url in the clone's own config file with origin's first
    # url), except for a push url held outside that file, which it cannot remove. Which offending url
    # is held where comes from lining origin's push url values up with the urls get-url prints, one
    # for one; where they do not line up (no push url values, whose push urls set mode's write
    # replaces, or an empty value), an offending url counts as held outside when any push value is.
    _aligned=0
    if [ ${#pv_src[@]} -gt 0 ] && [ $pv_empty -eq 0 ] && [ ${#pv_src[@]} -eq $n_push ]; then _aligned=1; fi
    _pv_out_any=0
    for _s in ${pv_src[@]+"${pv_src[@]}"}; do [ "$_s" = "$local_cfg" ] || _pv_out_any=1; done
    _off=""; _off_out=""; _k=0
    for ((_i = 0; _i < ${#o_url[@]}; _i++)); do
        [ "${o_kind[$_i]}" = push ] || continue
        if [ "${o_id[$_i]}" != "$origin_id" ]; then
            _off="${_off:+$_off, }${o_url[$_i]}"
            if { [ $_aligned -eq 1 ] && [ "${pv_src[$_k]}" != "$local_cfg" ]; } \
                || { [ $_aligned -eq 0 ] && [ ${#pv_src[@]} -gt 0 ] && [ $_pv_out_any -eq 1 ]; }; then
                _off_out="${_off_out:+$_off_out, }${o_url[$_i]}"
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
    # config file, which has its own note.
    if [ -z "$outside" ]; then
        _fix="the commands below point it at your fork"
    else
        _fix="remove what the note on values held outside the clone's own config file lists, and --check then gives the commands that point it at your fork"
    fi
    for ((_i = 0; _i < ${#f_kind[@]}; _i++)); do
        _r="${f_remote[$_i]}"
        _rm="Remove '$_r' if it is a second name for your fork"
        [ -z "${f_files[$_i]}" ] || _rm="$_rm (delete ${f_files[$_i]}, which defines it)"
        case "${f_kind[$_i]}" in
            unreadable)
                if [ -n "${f_files[$_i]}" ]; then
                    note "${f_text[$_i]}: the legacy file ${f_files[$_i]} defines it, and git reads no url from that file. --check cannot tell whether it is origin's repository: delete or repair the file"
                else
                    note "${f_text[$_i]}: a remote that only global or system config, or the environment (GIT_CONFIG_COUNT or GIT_CONFIG_PARAMETERS), defines reads this way, and a push to it still works. --check cannot tell whether it is origin's repository, and set mode does not change remotes defined there: remove it where it is defined (git -C $qtop config --show-origin --get-regexp '^remote\\.' lists where, and calls the environment 'command line:')"
                fi
                ;;
            fetch)
                note "${f_text[$_i]}: a fetch from origin and a bare gh PR number read that repository, and a push to origin goes to $origin_pushes. $_rm; if origin was set to that url by mistake, $_fix"
                shared=$((shared + 1))
                ;;
            extra)
                note "${f_text[$_i]}: git fetches only from origin's first url, and a push to origin goes to $origin_pushes. $_rm; if the url was added to origin by mistake, $_fix"
                shared=$((shared + 1))
                ;;
            *)
                note "${f_text[$_i]}: a push to origin goes to $origin_pushes. $_rm; if origin was set to push there by mistake, $_fix"
                shared=$((shared + 1))
                ;;
        esac
        blocked=$((blocked + 1))
    done
    # a bare `git push` goes to remote.pushDefault, and without one to the branch's own remote, which
    # may be any remote; set mode sets it to origin. Read with -z, so a value is compared exactly.
    pd=""
    IFS= read -r -d '' pd < <(git config -z --get remote.pushDefault 2>/dev/null) || true
    if [ -z "$pd" ]; then
        note "remote.pushDefault is unset: a bare 'git push' from a branch that tracks another remote goes there, not to your fork"
        rerun_fixes=$((rerun_fixes + 1))
    elif [ "$pd" != "origin" ]; then
        note "remote.pushDefault is '$pd': a bare 'git push' would not go to your fork"
        rerun_fixes=$((rerun_fixes + 1))
    fi
    # branch.<name>.pushRemote OVERRIDES remote.pushDefault, so checking only pushDefault above misses
    # a per-branch push aimed elsewhere. Anything but 'origin' is a bare push that skips the fork. Read
    # with -z (key, a newline, the value, a NUL), so a value such as ' origin' is not trimmed to origin.
    while IFS= read -r -d '' _pr_entry; do
        pr_split "$_pr_entry"
        [ "$_pr_val" != "origin" ] || continue
        note "$_pr_key is '$_pr_val': a bare push from that branch would not go to your fork"
        rerun_fixes=$((rerun_fixes + 1))
    done < <(git config -z --get-regexp '^branch\..*\.pushRemote$' 2>/dev/null || true)
    # gh's default repository (see the header): origin must carry `gh-resolved = base` and no other
    # remote may carry the key at all (gh reads upstream's and github's before origin's, and a
    # default anywhere but origin is one too many). A value other than 'base' on origin names some
    # OWNER/REPO outright, which gh then uses instead of origin.
    gh_origin=""
    IFS= read -r -d '' gh_origin < <(git config -z --get remote.origin.gh-resolved 2>/dev/null) || true
    if [ -z "$gh_origin" ]; then
        note "gh has no default repository (remote.origin.gh-resolved is unset): a bare 'gh pr merge N' from a script would aim at the project, not your fork"
        rerun_fixes=$((rerun_fixes + 1))
    elif [ "$gh_origin" != "base" ]; then
        note "remote.origin.gh-resolved is '$gh_origin', not 'base': gh would resolve a bare PR number against that repo, not your fork"
        rerun_fixes=$((rerun_fixes + 1))
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
    # Those settings, where one held outside the clone's own config file aims away from origin: set mode
    # writes only that file, so it cannot change one, and refuses while one stands (see aim_values).
    if [ -n "$aim_out" ]; then
        note "these settings, which aim a bare push or a bare gh PR number away from origin, are held outside the clone's own config file (the one git config --local writes), where set mode cannot change them: remove each one where it lives, then run $qscript --check again$NL$(aim_list)"
        blocked=$((blocked + 1))
    fi
    if [ $problems -eq 0 ]; then
        # what the checks above verified, and nothing more: none of them requires a third remote to be
        # fetch-only, so one that shares no repository with origin may push anywhere
        echo "  ✓ upstream fetches from the project and is fetch-only; origin's urls, and any rule that rewrites them, are in the clone's own config file; every push to origin goes to the repository it fetches from, and origin shares no repository with another remote; remote.pushDefault is origin and no branch's pushRemote names another remote; origin is gh's only default repository"
        exit 0
    fi
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
        echo "Fix what the notes above name, then run $qscript --check again; set mode refuses to run while origin shares a repository with another remote, git cannot read a remote's urls, git config holds no url for origin, or one of these is held anywhere but the clone's own config file: a url of origin's, a rule that rewrites one, or a setting that aims a bare push or a bare gh PR number away from origin." >&2
    elif [ $rerun_fixes -gt 0 ]; then
        echo "Run $qscript to fix." >&2
    else
        echo "Fix what the notes above name, then run $qscript --check again." >&2
    fi
    exit 1
fi

# --replace-all here and below: a key holding several values (an upstream with two urls, an upstream or
# origin with two push urls, or a doubled pushDefault) makes a plain set, or git remote set-url, refuse,
# which would stop set mode part way through.
if [ -n "$(git remote get-url upstream 2>/dev/null || true)" ]; then
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
# config file here (set mode refuses otherwise), so the value copied is one this clone holds. A
# pushRemote pointing AT origin is already safe and left alone; keys and values are read with -z, as
# --check reads them.
git config --replace-all remote.origin.pushurl "$origin_raw"
while IFS= read -r -d '' _pr_entry; do
    pr_split "$_pr_entry"
    [ "$_pr_val" != "origin" ] || continue
    git config --unset-all "$_pr_key" || true
done < <(git config -z --get-regexp '^branch\..*\.pushRemote$' 2>/dev/null || true)
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
echo "Check what the project has added since:  scripts/upstream-check.sh"
