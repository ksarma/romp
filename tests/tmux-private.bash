# tests/tmux-private.bash: a tmux socket directory private to one bats test.
#
# Use from a bats file: `load tmux-private` at the top, `tmux_private_socket_dir "$TEST_DIR"` in
# setup(), and `tmux_private_kill` in teardown() BEFORE `rm -rf "$TEST_DIR"`.
#
# Why (2026-09-06): a bats sweep ran tests/romp-manager-ensure.bats ninety seconds after a stray
# `tmux kill-server` elsewhere had removed the machine's default tmux server. That file starts a REAL
# detached bin/romp-manager, whose startManager() runs `tmux start-server` on the DEFAULT socket, at
# the one moment no server existed there. The machine's tmux server was then the test's: it carried
# the sweep's environment (BATS_*, the sweep session's ROMP_SID, a fake-serve path under a temp dir
# already deleted) and sat in the service's cgroup. A tmux mock on PATH covers only the tests that
# install one; TMUX_TMPDIR covers every tmux the subject reaches, mock or real.
#
# The directory MUST exist before tmux runs. tmux 3.4 falls back to the default socket directory
# silently when TMUX_TMPDIR names a missing one (verified: with TMUX_TMPDIR set to a missing path,
# `#{socket_path}` reads /tmp/tmux-<uid>/default), so an export without the mkdir isolates nothing.
# tmux puts its socket at $TMUX_TMPDIR/tmux-<uid>/default, creating the tmux-<uid> level itself.

tmux_private_socket_dir() {   # $1 = the test's temp dir, removed in teardown
    TMUX_PRIVATE_TEST_DIR="$1"
    TMUX_PRIVATE_DIR="$1/tmux"
    mkdir -p "$TMUX_PRIVATE_DIR"
    export TMUX_TMPDIR="$TMUX_PRIVATE_DIR"
}

# The machine's tmux: the first `tmux` on PATH that is NOT under the test directory, where every suite
# here keeps its mocks. A mock on PATH answers `kill-server` with exit 0 and kills nothing (the first
# run of the isolation leaked a server that way), so the kill below never goes through PATH.
# Prints the path; fails when there is none (a box without tmux started no server either).
tmux_private_real_tmux() {
    local dir dirs
    IFS=: read -ra dirs <<< "$PATH"
    for dir in "${dirs[@]}"; do
        [ -n "$dir" ] || continue
        case "$dir" in "$TMUX_PRIVATE_TEST_DIR"|"$TMUX_PRIVATE_TEST_DIR"/*) continue ;; esac
        [ -x "$dir/tmux" ] && { printf '%s\n' "$dir/tmux"; return 0; }
    done
    return 1
}

# Kill every tmux server whose socket sits under the private directory: a `start-server` outlives its
# client, and the manager that ran it, so without this a server (kept alive by the manager's
# `exit-empty off`) would leak past the test. -S names the socket outright (no TMUX_TMPDIR lookup, so
# this can never resolve to the machine's server), and it runs before the directory is removed:
# afterwards a bare `tmux kill-server` WOULD fall back to the machine's (the silent fallback above).
# kill-server never starts a server, so a stale socket is inert.
tmux_private_kill() {
    local sock tmux
    [[ -n "${TMUX_PRIVATE_DIR:-}" && -d "$TMUX_PRIVATE_DIR" ]] || return 0
    tmux="$(tmux_private_real_tmux)" || return 0
    for sock in "$TMUX_PRIVATE_DIR"/tmux-*/*; do
        [ -S "$sock" ] || continue
        "$tmux" -S "$sock" kill-server 2>/dev/null || true
    done
    return 0
}
