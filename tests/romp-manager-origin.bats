#!/usr/bin/env bats

# CSRF / drive-by guard for the manager control port (M2). A browser cross-site
# request carries an Origin the page cannot forge; the manager must reject any
# non-loopback Origin so a malicious tab can't POST /restart-all or /stop and
# kill the user's kernels. Server-side clients (the kernel's Restart proxy, the
# `romp on` CLI) send no Origin and must keep working.

load tmux-private

setup() {
    TEST_DIR="$(mktemp -d)"
    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"
    # A state root of the suite's own. The manager notes every SIGTERM it sends in
    # STATE_ROOT/restart-audit.jsonl (auditSigterm), and every test here stops a real manager in
    # teardown: with no root set, those rows landed in the LIVE ledger as requests on record for kills
    # nobody made (seven rows, 2026-09-06). ROMP_STATE_DIR outranks the XDG floor and a session of a
    # profiled kernel inherits it, so it is dropped, not shadowed. tests/bats-state-isolation.bats
    # checks that both lines stay.
    unset ROMP_STATE_DIR
    export XDG_STATE_HOME="$TEST_DIR/state"; mkdir -p "$XDG_STATE_HOME"
    # bin/romp-manager starts its tmux server in a transient systemd scope under ROMP_SUPERVISED (which a
    # romp session's tool shell inherits from the live service) — a test must never start a real scope
    # on the live user manager, so the switch is floored off (the kernel and manager both honour it).
    export ROMP_CLI_SCOPE=0
    # The manager under test is REAL, and startManager() runs `tmux start-server` before it binds the
    # control port: a call this file has no interest in, which must still never reach the machine's
    # tmux server (tests/tmux-private.bash has the 2026-09-06 incident). A no-op tmux on PATH absorbs
    # it; the private socket directory catches any call that reaches the real binary anyway.
    BIN="$TEST_DIR/bin"; mkdir -p "$BIN"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$BIN/tmux"
    chmod +x "$BIN/tmux"
    export PATH="$BIN:$PATH"
    tmux_private_socket_dir "$TEST_DIR"
    # Fake kernel launcher: stays alive without binding a real port.
    FAKE="$TEST_DIR/fake-serve"
    printf '#!/usr/bin/env bash\nexec sleep 30\n' > "$FAKE"
    chmod +x "$FAKE"
    CPORT=7571; MPORT=7572
}

teardown() {
    [[ -n "${MGR_PID:-}" ]] && kill "$MGR_PID" 2>/dev/null || true
    tmux_private_kill            # before the rm: a server the real tmux started must not outlive the test
    rm -rf "$TEST_DIR"
}

@test "manager rejects cross-site Origin, allows no-Origin clients" {
    command -v node >/dev/null 2>&1 || skip "node not available"
    command -v curl >/dev/null 2>&1 || skip "curl not available"

    env ROMP_MANAGER_PORT=$CPORT ROMP_SERVE_PORT=$MPORT ROMP_SERVE_BIN="$FAKE" \
        node "$MGR" up >/dev/null 2>&1 &
    MGR_PID=$!

    local i
    for i in $(seq 1 40); do
        curl -fsS "http://127.0.0.1:$CPORT/status" >/dev/null 2>&1 && break
        sleep 0.1
    done

    # No Origin (server-side client) → 200.
    run curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$CPORT/status"
    [ "$output" = "200" ]

    # Cross-site Origin on a read → 403.
    run curl -s -o /dev/null -w '%{http_code}' -H 'Origin: http://evil.example' \
        "http://127.0.0.1:$CPORT/status"
    [ "$output" = "403" ]

    # Cross-site state-changing POST (the real attack) → 403.
    run curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Origin: http://evil.example' \
        "http://127.0.0.1:$CPORT/restart-all"
    [ "$output" = "403" ]

    # A loopback Origin (the local web UI, if it ever calls directly) → allowed.
    run curl -s -o /dev/null -w '%{http_code}' -H "Origin: http://127.0.0.1:$CPORT" \
        "http://127.0.0.1:$CPORT/status"
    [ "$output" = "200" ]
}
