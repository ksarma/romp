#!/usr/bin/env bats

# bin/romp-cli-scope — the exec-in-place wrapper the kernel spawns a session's `claude` CLI through
# on Linux under systemd, so the CLI (and everything it later starts: tool shells, setsid children,
# tmux servers) runs in a transient scope of its own instead of the manager service's cgroup, which
# KillMode=control-group empties on every service restart.
#
# A FAKE systemd-run first on PATH records its argv and then execs the command after `--`, so the
# tests see exactly what the wrapper asked for and the fake "real CLI" still runs. Nothing here
# touches the real systemd-run.

setup() {
    TEST_DIR="$(mktemp -d)"
    WRAPPER="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-cli-scope"
    BIN="$TEST_DIR/bin"
    mkdir -p "$BIN"
    export FAKE_LOG="$TEST_DIR/systemd-run.argv"
    cat > "$BIN/systemd-run" <<'SH'
#!/bin/sh
# one argv element per line, then exec the command after `--` (what --scope mode does for real)
printf '%s\n' "$@" > "$FAKE_LOG"
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

@test "the unit is romp-session-<first 8 of the sid>-<pid>, and differs between two runs" {
    run "$WRAPPER"
    [ "$status" -eq 0 ]
    unit1="$(grep '^--unit=' "$FAKE_LOG")"
    [[ "$unit1" == --unit=romp-session-11111111-* ]]
    # the suffix is the pid the CLI ran as (exec-in-place: wrapper pid == CLI pid)
    pid1="$(printf '%s\n' "$output" | sed -n 's/^REAL pid=\([0-9]*\) .*/\1/p')"
    [ "$unit1" = "--unit=romp-session-11111111-$pid1" ]
    run "$WRAPPER"
    [ "$status" -eq 0 ]
    unit2="$(grep '^--unit=' "$FAKE_LOG")"
    [ "$unit1" != "$unit2" ]
}

@test "an empty ROMP_SID still names the unit, without a sid" {
    ROMP_SID= run "$WRAPPER"
    [ "$status" -eq 0 ]
    grep -q '^--unit=romp-session-unknown-[0-9][0-9]*$' "$FAKE_LOG"
    grep -qx -- '--description=romp session unknown' "$FAKE_LOG"
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
