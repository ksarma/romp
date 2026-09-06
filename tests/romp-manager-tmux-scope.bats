#!/usr/bin/env bats

# bin/romp-manager's startTmuxServer, through a REAL manager start. On Linux with the switch on it runs
# `tmux start-server` through `systemd-run --scope` in a romp-tmux-<ms> unit, so the server sits outside
# the service cgroup and outlives a service restart; when systemd-run fails it says so and starts the
# server bare, saying that too. tmuxStartArgv, the pure argv choice, has its node suite
# (tests/manager-tmux-scope.test.js); this file covers the call itself, the fallback, and the log lines,
# which nothing else did — the other manager-driving suites run with the switch floored off.
#
# A FAKE systemd-run first on PATH records its argv, then either execs the command after `--` (what
# --scope mode does for real) or, with FAKE_SYSTEMD_RUN_FAIL set, exits 1 with a bus error on stderr. A
# recording fake tmux answers the command either way. Nothing here reaches the real systemd-run or the
# user manager: the switch is turned on only behind the fake, and the floor tmux_private_socket_dir
# sets (ROMP_CLI_SCOPE=0) stays for the case that pins it.

load free-port
load tmux-private

setup() {
    TEST_DIR="$(mktemp -d)"
    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"
    BIN="$TEST_DIR/bin"; mkdir -p "$BIN"
    export FAKE_TMUX_CALLS="$TEST_DIR/tmux-calls" FAKE_SYSTEMD_RUN_CALLS="$TEST_DIR/systemd-run-calls"
    cat > "$BIN/tmux" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_TMUX_CALLS"
exit 0
FAKE
    cat > "$BIN/systemd-run" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_SYSTEMD_RUN_CALLS"
if [ -n "${FAKE_SYSTEMD_RUN_FAIL:-}" ]; then
    echo 'Failed to start transient scope unit: Failed to connect to bus: No such file or directory' >&2
    exit 1
fi
while [ "$#" -gt 0 ]; do a="$1"; shift; [ "$a" = "--" ] && break; done
exec "$@"
FAKE
    chmod +x "$BIN/tmux" "$BIN/systemd-run"
    export PATH="$BIN:$PATH"
    tmux_private_socket_dir "$TEST_DIR"   # private socket dir, and the ROMP_CLI_SCOPE=0 floor
    # The manager's registry root is private too: a real `up` writes there.
    export ROMP_STATE_DIR="$TEST_DIR/state"; mkdir -p "$ROMP_STATE_DIR"
    # Fake kernel launcher: stays alive without binding a real port.
    FAKE="$TEST_DIR/fake-serve"
    printf '#!/usr/bin/env bash\nexec sleep 30\n' > "$FAKE"
    chmod +x "$FAKE"
    LOG="$TEST_DIR/manager.log"
    free_port CPORT MPORT   # fresh per test, never a literal (tests/free-port.bash)
}

teardown() {
    curl -fsS -X POST "http://127.0.0.1:${CPORT:-0}/stop" >/dev/null 2>&1 || true
    [[ -n "${MGR_PID:-}" ]] && kill "$MGR_PID" 2>/dev/null || true
    # The kill before the rm (a server the real tmux started must not outlive the test), and last, so
    # its failure is teardown's status: bats swallows a failing command mid-teardown.
    tmux_private_kill && rm -rf "$TEST_DIR"
}

need_tools() {
    command -v node >/dev/null 2>&1 || skip "node not available"
    command -v curl >/dev/null 2>&1 || skip "curl not available"
}

# The real manager, its stderr (where log() writes) in $LOG, up to the control port answering. The tmux
# start runs before the port binds, so once /status answers the calls and the lines are on disk.
start_manager() {
    env ROMP_MANAGER_PORT=$CPORT ROMP_SERVE_PORT=$MPORT ROMP_SERVE_BIN="$FAKE" \
        node "$MGR" up >"$LOG" 2>&1 &
    MGR_PID=$!
    local i
    for i in $(seq 1 50); do
        curl -fsS "http://127.0.0.1:$CPORT/status" >/dev/null 2>&1 && return 0
        sleep 0.1
    done
    echo "the manager did not come up; its log:"; cat "$LOG"
    return 1
}

BARE='start-server ; set -g exit-empty off'

@test "switch on: the server starts through systemd-run --scope in a romp-tmux unit, and the log says so" {
    need_tools
    [ "$(uname -s)" = Linux ] || skip "the scoped path is Linux-only by construction (tmuxStartArgv)"
    export ROMP_CLI_SCOPE=1
    start_manager
    # one systemd-run call: a --user --scope --quiet --collect unit named romp-tmux-<ms>, the tmux argv after --
    [ "$(wc -l < "$FAKE_SYSTEMD_RUN_CALLS")" -eq 1 ]
    re='^--user --scope --quiet --collect --unit=romp-tmux-[0-9]+ -- tmux start-server ; set -g exit-empty off$'
    [[ "$(cat "$FAKE_SYSTEMD_RUN_CALLS")" =~ $re ]]
    # the fake exec'd the command after --, so tmux ran once, from inside the "scope", with the bare argv
    [ "$(cat "$FAKE_TMUX_CALLS")" = "$BARE" ]
    grep -q 'tmux server ensured in its own transient scope (romp-tmux-\*)' "$LOG"
    ! grep -q 'could not start the tmux server in a scope' "$LOG"
    ! grep -q 'ensured without a scope' "$LOG"
    ! grep -q 'launchd-rooted' "$LOG"
}

@test "switch on, systemd-run failing: the log names the failure, the server starts bare, and the log says it is unscoped" {
    need_tools
    [ "$(uname -s)" = Linux ] || skip "the scoped path is Linux-only by construction (tmuxStartArgv)"
    export ROMP_CLI_SCOPE=1 FAKE_SYSTEMD_RUN_FAIL=1
    start_manager
    [ "$(wc -l < "$FAKE_SYSTEMD_RUN_CALLS")" -eq 1 ]   # tried once...
    [ "$(cat "$FAKE_TMUX_CALLS")" = "$BARE" ]          # ...then the bare call, once
    grep -q 'systemd-run could not start the tmux server in a scope (' "$LOG"
    grep -q 'starting it the plain way instead' "$LOG"
    grep -q 'tmux server ensured without a scope' "$LOG"
    grep -q 'a service restart will take it down' "$LOG"
    ! grep -q 'in its own transient scope' "$LOG"
    ! grep -q 'launchd-rooted' "$LOG"
}

@test "the helper's floor holds under an inherited ROMP_SUPERVISED: no systemd-run call, the bare start, the plain line" {
    # What a tool shell under a self-hosted install carries. Every manager-driving suite relies on the
    # floor tmux_private_socket_dir set in setup() — this case sets nothing itself — and with the fake in
    # front of the real systemd-run a floor that failed would show as a recorded call, not as a scope.
    need_tools
    export ROMP_SUPERVISED=1
    [ "$ROMP_CLI_SCOPE" = 0 ]
    start_manager
    [ ! -e "$FAKE_SYSTEMD_RUN_CALLS" ]
    [ "$(cat "$FAKE_TMUX_CALLS")" = "$BARE" ]
    grep -q 'tmux server ensured (launchd-rooted)' "$LOG"
    ! grep -q 'transient scope' "$LOG"
    ! grep -q 'without a scope' "$LOG"
}
