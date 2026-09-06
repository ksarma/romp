#!/usr/bin/env bats

# tests/tmux-private.bash gives a bats file a tmux socket directory private to the test. These cases
# pin the helper's own contract, above all where it must FAIL rather than fall through: every silent
# return here is a server that could outlive a test on the machine's tmux. Nothing below runs tmux.

load tmux-private

setup() {
    TEST_DIR="$(mktemp -d)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "tmux_private_socket_dir creates the directory and exports TMUX_TMPDIR under the test dir" {
    tmux_private_socket_dir "$TEST_DIR"
    [ "$TMUX_TMPDIR" = "$TEST_DIR/tmux" ]
    [ -d "$TMUX_TMPDIR" ]
    [ "$TMUX_PRIVATE_DIR" = "$TEST_DIR/tmux" ]
    [ "$TMUX_PRIVATE_TEST_DIR" = "$TEST_DIR" ]
}

@test "tmux_private_kill fails loudly when the private directory is already gone" {
    # The teardown ordering bug: an `rm -rf "$TEST_DIR"` before the kill takes the sockets with it, so a
    # server started under the directory can no longer be reached by -S. Exit 0 there would hide a leak.
    tmux_private_socket_dir "$TEST_DIR"
    rm -rf "$TMUX_PRIVATE_DIR"
    run tmux_private_kill
    [ "$status" -eq 1 ]
    [[ "$output" == *"tmux-private:"* ]]
    [[ "$output" == *"$TMUX_PRIVATE_DIR"* ]]
    [[ "$output" == *"leaked"* ]]
}

@test "tmux_private_kill is a silent no-op when nothing was armed" {
    # A teardown after a setup that failed before tmux_private_socket_dir ran: nothing could have leaked,
    # and a second error would only bury the first.
    unset TMUX_PRIVATE_DIR TMUX_PRIVATE_TEST_DIR
    run tmux_private_kill
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "tmux_private_real_tmux refuses when the test dir variable is unset" {
    # With TMUX_PRIVATE_TEST_DIR unset the exclusion pattern reads `/*`, which skips every absolute PATH
    # entry: the search would report "no tmux" on a box that has one, and tmux_private_kill would take
    # that for a box with nothing to kill.
    unset TMUX_PRIVATE_TEST_DIR
    run tmux_private_real_tmux
    [ "$status" -eq 2 ]
    [[ "$output" == *"tmux-private:"* ]]
    [[ "$output" == *"TMUX_PRIVATE_TEST_DIR"* ]]
}

@test "tmux_private_real_tmux skips a tmux under the test dir and finds one outside it" {
    # The kill must reach the machine's tmux, never a suite's PATH mock (a mock answered kill-server with
    # exit 0 and the first run of the isolation leaked a server). Both binaries here are stand-ins: the
    # one outside the test dir lives in its own temp dir, so the case holds on a box without tmux.
    tmux_private_socket_dir "$TEST_DIR"
    local mock="$TEST_DIR/bin" real; mkdir -p "$mock"
    real="$(mktemp -d)"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$mock/tmux"; chmod +x "$mock/tmux"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$real/tmux"; chmod +x "$real/tmux"
    PATH="$mock:$real:$PATH" run tmux_private_real_tmux
    rm -rf "$real"
    [ "$status" -eq 0 ]
    [ "$output" = "$real/tmux" ]
}
