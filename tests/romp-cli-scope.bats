#!/usr/bin/env bats

# bin/romp-cli-scope — the exec-in-place wrapper the kernel spawns a session's `claude` CLI through
# on Linux under systemd, so the CLI (and everything it later starts: tool shells, setsid children,
# tmux servers) runs in a transient scope of its own instead of the manager service's cgroup, which
# systemd's default KillMode=control-group empties on every service restart.
#
# A FAKE systemd-run first on PATH records its argv (FAKE_LOG holds the LAST call's argv, one element
# per line; FAKE_CALLS appends one line per call) and then execs the command after `--`, so the tests
# see exactly what the wrapper asked for and the fake "real CLI" still runs. The wrapper calls it
# twice per launch: a pre-flight `-- true`, then the scoped CLI. Nothing here touches the real
# systemd-run.

setup() {
    TEST_DIR="$(mktemp -d)"
    WRAPPER="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-cli-scope"
    BIN="$TEST_DIR/bin"
    mkdir -p "$BIN"
    export FAKE_LOG="$TEST_DIR/systemd-run.argv"
    export FAKE_CALLS="$TEST_DIR/systemd-run.calls"
    cat > "$BIN/systemd-run" <<'SH'
#!/bin/sh
# one argv element per line, then exec the command after `--` (what --scope mode does for real)
printf '%s\n' "$@" > "$FAKE_LOG"
echo "$*" >> "$FAKE_CALLS"
while [ "$#" -gt 0 ]; do a="$1"; shift; [ "$a" = "--" ] && break; done
exec "$@"
SH
    chmod +x "$BIN/systemd-run"
    # the fake "real CLI": its pid, its parent's pid, and its argv one element per line
    REAL="$TEST_DIR/claude"
    cat > "$REAL" <<'SH'
#!/bin/sh
echo "REAL pid=$$ ppid=$PPID"
printf 'ARG:%s\n' "$@"
SH
    chmod +x "$REAL"
    export PATH="$BIN:$PATH"
    export ROMP_CLI_REAL="$REAL"
    export ROMP_SID="11111111-2222-3333-4444-555555555555"
    unset ROMP_CLI_SCOPE
}

teardown() { rm -rf "$TEST_DIR"; }

@test "runs the real CLI through systemd-run with the arguments passed verbatim" {
    run "$WRAPPER" --input-format stream-json "two words" --resume "$ROMP_SID" ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"REAL pid="* ]]
    # every argument, in order, including the one with a space, the ones starting with --,
    # and the empty one
    expected="$(printf 'ARG:%s\n' --input-format stream-json "two words" --resume "$ROMP_SID" "")"
    [ "$(printf '%s\n' "$output" | grep '^ARG:')" = "$expected" ]
    [ -s "$FAKE_LOG" ]
}

@test "asks systemd-run for a --user --scope --quiet --collect unit and hands it the real CLI after --" {
    run "$WRAPPER" a b
    [ "$status" -eq 0 ]
    grep -qx -- '--user' "$FAKE_LOG"
    grep -qx -- '--scope' "$FAKE_LOG"
    grep -qx -- '--quiet' "$FAKE_LOG"
    grep -qx -- '--collect' "$FAKE_LOG"
    grep -qx -- "--description=romp session $ROMP_SID" "$FAKE_LOG"
    # after `--`: the real CLI, then the args verbatim
    tail_after_dash="$(sed -n '/^--$/,$p' "$FAKE_LOG" | sed 1d)"
    [ "$tail_after_dash" = "$(printf '%s\n' "$REAL" a b)" ]
}

@test "the unit is romp-session-<first 8 of the sid>-<pid>-<start time>, and differs between two runs" {
    run "$WRAPPER"
    [ "$status" -eq 0 ]
    unit1="$(grep '^--unit=' "$FAKE_LOG")"
    # <pid> is the pid the CLI ran as (exec-in-place: wrapper pid == CLI pid); the time component is
    # what keeps the name unique once pids wrap while an earlier CLI's scope is still loaded (a tmux
    # server it started keeps the scope alive) — systemd refuses a duplicate name as "already loaded"
    pid1="$(printf '%s\n' "$output" | sed -n 's/^REAL pid=\([0-9]*\) .*/\1/p')"
    [ -n "$pid1" ]
    [[ "$unit1" =~ ^--unit=romp-session-11111111-${pid1}-[0-9]+$ ]]
    run "$WRAPPER"
    [ "$status" -eq 0 ]
    unit2="$(grep '^--unit=' "$FAKE_LOG")"
    [[ "$unit2" =~ ^--unit=romp-session-11111111-[0-9]+-[0-9]+$ ]]
    [ "$unit1" != "$unit2" ]
}

# No session identity, no scope (2026-09-05): the SDK's per-connect version check runs `<cli_path> -v`
# with the KERNEL's environment — ROMP_CLI_REAL (the kernel exports it) but no ROMP_SID — and a probe
# must run the CLI directly rather than mint a romp-session-unknown-* scope per connect.
@test "an empty ROMP_SID runs the real CLI directly — a probe, not a session; systemd-run is not invoked" {
    ROMP_SID= run "$WRAPPER" -v
    [ "$status" -eq 0 ]
    [ ! -e "$FAKE_LOG" ]
    [ ! -e "$FAKE_CALLS" ]
    [ "$(printf '%s\n' "$output" | grep '^ARG:')" = "ARG:-v" ]
}

@test "an unset ROMP_SID runs the real CLI directly the same way" {
    unset ROMP_SID
    run "$WRAPPER" -v
    [ "$status" -eq 0 ]
    [ ! -e "$FAKE_CALLS" ]
    [[ "$output" == *"REAL pid="* ]]
}

@test "a pre-flight scope (-- true) runs before the CLI's own scope" {
    run "$WRAPPER" a
    [ "$status" -eq 0 ]
    [ "$(wc -l < "$FAKE_CALLS")" -eq 2 ]
    first="$(sed -n 1p "$FAKE_CALLS")"
    [[ "$first" == *"--user --scope --quiet --collect -- true" ]]
    [[ "$first" != *"--unit="* ]]
    second="$(sed -n 2p "$FAKE_CALLS")"
    [[ "$second" == *"--unit=romp-session-11111111-"* ]]
    [[ "$second" == *"-- $REAL a" ]]
}

@test "a failing pre-flight falls back to the real CLI directly, with one stderr line naming the reason" {
    # systemd-run that cannot start a scope (the user bus gone): the CLI must still launch, in
    # the caller's cgroup, and the reason must reach stderr (the kernel captures the CLI's stderr)
    cat > "$BIN/systemd-run" <<'SH'
#!/bin/sh
echo "$*" >> "$FAKE_CALLS"
echo "Failed to connect to bus: No such file or directory" >&2
echo "a second stderr line that must not be quoted" >&2
exit 1
SH
    chmod +x "$BIN/systemd-run"
    ERR="$TEST_DIR/stderr"
    run sh -c '"$0" --input-format stream-json "two words" 2>"$1"' "$WRAPPER" "$ERR"
    [ "$status" -eq 0 ]
    # the real CLI ran, directly, with its arguments intact
    [[ "$output" == *"REAL pid="* ]]
    [ "$(printf '%s\n' "$output" | grep '^ARG:')" = "$(printf 'ARG:%s\n' --input-format stream-json "two words")" ]
    # systemd-run was tried exactly once (the pre-flight), never for the CLI itself
    [ "$(wc -l < "$FAKE_CALLS")" -eq 1 ]
    [[ "$(cat "$FAKE_CALLS")" == *"-- true" ]]
    # one stderr line: names the wrapper, the reason's first line, and the direct run
    [ "$(wc -l < "$ERR")" -eq 1 ]
    grep -q '^romp-cli-scope: ' "$ERR"
    grep -q 'Failed to connect to bus' "$ERR"
    grep -q 'directly' "$ERR"
    # armed absence check (a bare mid-test `! grep` is exempt from bats' errexit and asserts nothing)
    run grep -q 'second stderr line' "$ERR"
    [ "$status" -ne 0 ]
}

@test "exec in place: the CLI keeps the wrapper's pid and its parent is the launching shell" {
    # Launch from a shell whose pid we know; the wrapper execs systemd-run, which execs the CLI —
    # so the CLI's pid must be that shell's pid and its ppid the shell's parent (this bats
    # process), with no extra parent between them.
    run sh -c 'echo "SH pid=$$ ppid=$PPID"; exec "$0"' "$WRAPPER"
    [ "$status" -eq 0 ]
    sh_pid="$(printf '%s\n' "$output" | sed -n 's/^SH pid=\([0-9]*\) .*/\1/p')"
    sh_ppid="$(printf '%s\n' "$output" | sed -n 's/^SH pid=[0-9]* ppid=\([0-9]*\)$/\1/p')"
    real_pid="$(printf '%s\n' "$output" | sed -n 's/^REAL pid=\([0-9]*\) .*/\1/p')"
    real_ppid="$(printf '%s\n' "$output" | sed -n 's/^REAL pid=[0-9]* ppid=\([0-9]*\)$/\1/p')"
    [ -n "$sh_pid" ] && [ -n "$real_pid" ]
    [ "$real_pid" = "$sh_pid" ]
    [ "$real_ppid" = "$sh_ppid" ]
}

@test "ROMP_CLI_SCOPE=0 runs the real CLI directly — systemd-run is not invoked" {
    ROMP_CLI_SCOPE=0 run "$WRAPPER" x "y z"
    [ "$status" -eq 0 ]
    [ ! -e "$FAKE_LOG" ]
    [ "$(printf '%s\n' "$output" | grep '^ARG:')" = "$(printf 'ARG:%s\n' x "y z")" ]
}

@test "no systemd-run on PATH: the real CLI runs directly" {
    rm "$BIN/systemd-run"
    PATH="$BIN" run "$WRAPPER" --input-format stream-json
    [ "$status" -eq 0 ]
    [ ! -e "$FAKE_LOG" ]
    [[ "$output" == *"ARG:--input-format"* ]]
}

# The refusal tests run the wrapper under an inner sh that reports the exit code on stdout: bats's
# `run` warns on a bare 127 (it reads it as command-not-found), and 127 is exactly the code wanted.
@test "an empty ROMP_CLI_REAL is refused: exit 127 and a stderr line naming the variable" {
    ERR="$TEST_DIR/stderr"
    ROMP_CLI_REAL= run sh -c '"$0" a 2>"$1"; echo "exit=$?"' "$WRAPPER" "$ERR"
    [ "$status" -eq 0 ]
    [ "$output" = "exit=127" ]
    grep -q 'ROMP_CLI_REAL' "$ERR"
    [ ! -e "$FAKE_LOG" ]
}

@test "an unset ROMP_CLI_REAL is refused the same way" {
    unset ROMP_CLI_REAL
    ERR="$TEST_DIR/stderr"
    run sh -c '"$0" 2>"$1"; echo "exit=$?"' "$WRAPPER" "$ERR"
    [ "$status" -eq 0 ]
    [ "$output" = "exit=127" ]
    grep -q 'ROMP_CLI_REAL' "$ERR"
}
