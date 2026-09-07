# tests/tmux-private.bash: a tmux socket directory private to one bats test.
#
# Use from a bats file: `load tmux-private` at the top, `tmux_private_socket_dir "$TEST_DIR"` in
# setup(), and `tmux_private_kill && rm -rf "$TEST_DIR"` as the LAST line of teardown(). The kill must
# run before the rm (see tmux_private_kill), and its failure must be teardown's own status: bats runs
# teardown with errexit and the ERR trap off, so a failing command in the middle of it is swallowed
# and the test passes; only teardown's return status can fail it.
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
#
# The same call floors ROMP_CLI_SCOPE=0 (2026-09-06). Under ROMP_SUPERVISED — what bin/romp-service's
# unit sets, and what a tool shell under a self-hosted install inherits from it — bin/romp-manager
# starts its tmux server through `systemd-run --scope`, and the kernel spawns each session's CLI the
# same way (cli_scope_supported), so a suite that starts the real manager would leave a transient
# scope on the developer's user manager. Every suite that isolates tmux inherits the floor here rather
# than repeating it in setup(); pytest's is tests/conftest.py. A suite that means to exercise the scoped
# path exports ROMP_CLI_SCOPE=1 AFTER this call, with a fake systemd-run first on PATH
# (tests/romp-manager-tmux-scope.bats).

tmux_private_socket_dir() {   # $1 = the test's temp dir, removed in teardown
    TMUX_PRIVATE_TEST_DIR="$1"
    TMUX_PRIVATE_DIR="$1/tmux"
    mkdir -p "$TMUX_PRIVATE_DIR"
    export TMUX_TMPDIR="$TMUX_PRIVATE_DIR"
    export ROMP_CLI_SCOPE=0
}

# The machine's tmux: the first `tmux` on PATH that is NOT under the test directory, where every suite
# here keeps its mocks. A mock on PATH answers `kill-server` with exit 0 and kills nothing (the first
# run of the isolation leaked a server that way), so the kill below never goes through PATH.
# Prints the path. Exit 1 when there is none (a box without tmux started no server either); exit 2,
# with a message, when tmux_private_socket_dir was never called: with TMUX_PRIVATE_TEST_DIR unset the
# exclusion pattern would read `/*` and skip EVERY absolute PATH entry, so the search would report "no
# tmux" on a box that has one, and a caller would take that for a box with nothing to kill.
tmux_private_real_tmux() {
    local dir dirs
    if [ -z "${TMUX_PRIVATE_TEST_DIR:-}" ]; then
        echo "tmux-private: TMUX_PRIVATE_TEST_DIR is unset (tmux_private_socket_dir not called); refusing to pick a tmux" >&2
        return 2
    fi
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
#
# Exit 0 when tmux_private_socket_dir was never called (nothing was armed, so nothing can have leaked;
# a teardown that runs after a setup failed early must not add a second error). Exit 1, with a message,
# when it WAS called and the directory is already gone: the sockets went with it, so any server started
# under it is now unreachable by -S and has leaked. That is the teardown ordering bug this guards
# (an `rm -rf "$TEST_DIR"` before the kill), and a silent exit 0 there would hide it.
tmux_private_kill() {
    local sock tmux rc
    [ -n "${TMUX_PRIVATE_DIR:-}" ] || return 0
    if [ ! -d "$TMUX_PRIVATE_DIR" ]; then
        echo "tmux-private: $TMUX_PRIVATE_DIR is gone before tmux_private_kill ran; a server started under it has leaked (call tmux_private_kill before the rm -rf)" >&2
        return 1
    fi
    tmux="$(tmux_private_real_tmux)" && rc=0 || rc=$?
    case "$rc" in
        0) ;;
        1) return 0 ;;    # no tmux on the box: no server was started
        *) return 1 ;;    # refused (message already printed)
    esac
    for sock in "$TMUX_PRIVATE_DIR"/tmux-*/*; do
        [ -S "$sock" ] || continue
        "$tmux" -S "$sock" kill-server 2>/dev/null || true
    done
    return 0
}
