#!/usr/bin/env bats

# tests/stop-then-remove.bash stops a test's background process and removes the test's directory only
# once that process has exited. These cases run it against a stand-in that keeps writing under the
# directory after its TERM, the way bin/romp-manager's shutdown writes its restart audit there: nothing
# may be left behind, a process that ignores TERM is KILLed at the bound, and a directory that cannot be
# removed still fails the call. The last case checks that tests/romp-manager-origin.bats's teardown goes
# through the helper. Nothing below starts a manager.

load stop-then-remove

setup() {
    TEST_DIR="$(mktemp -d)"
    # The stand-in. $1 the directory to write under, $2 a file it creates once its TERM disposition is
    # set, $3 what a TERM does: `burst` writes a row every 0.05 s for about a second (recreating the
    # directory with mkdir -p, as the manager's mkdirSync does), then creates $2.burst-done and exits;
    # `ignore` ignores TERM and writes until it is KILLed, with builtins only, so no child of its own can
    # write after the KILL, and marks $2.wrote-after-removal if a write finds the directory gone.
    STANDIN="$TEST_DIR/standin"
    cat > "$STANDIN" <<'EOF'
#!/usr/bin/env bash
dir="$1"; ready="$2"; mode="$3"
burst() {
    local i
    for i in $(seq 1 20); do
        mkdir -p "$dir/state/romp" 2>/dev/null
        printf 'row\n' 2>/dev/null >> "$dir/state/romp/restart-audit.jsonl"
        sleep 0.05
    done
    : > "$ready.burst-done"
    exit 0
}
case "$mode" in
    burst) trap burst TERM ;;
    ignore) trap '' TERM ;;
esac
: > "$ready"
while :; do
    if [ "$mode" = ignore ]; then
        { printf 'row\n' >> "$dir/state/romp/restart-audit.jsonl"; } 2>/dev/null || : > "$ready.wrote-after-removal"
    fi
    sleep 0.05
done
EOF
    chmod +x "$STANDIN"
    mkdir -p "$TEST_DIR/target/state/romp"
    : > "$TEST_DIR/target/state/romp/serve-token"
}

teardown() {
    # A stand-in a failed case left running: KILL runs no trap, so it writes nothing more.
    [ -n "${STANDIN_PID:-}" ] && kill -9 "$STANDIN_PID" 2>/dev/null || true
    [ -n "${STANDIN_PID:-}" ] && wait "$STANDIN_PID" 2>/dev/null || true
    rm -rf "$TEST_DIR"
}

_await_ready() {   # the stand-in has set its TERM disposition, so the TERM below meets it
    local i
    for ((i = 0; i < 50; i++)); do
        [ -e "$TEST_DIR/ready" ] && return 0
        sleep 0.1
    done
    echo "the stand-in never became ready" >&2
    return 1
}

@test "the directory is removed only once a process still writing after its TERM has exited" {
    "$STANDIN" "$TEST_DIR/target" "$TEST_DIR/ready" burst &
    STANDIN_PID=$!
    _await_ready
    stop_then_remove "$STANDIN_PID" "$TEST_DIR/target"   # in this shell, as teardown() calls it
    # A writer the helper did not wait for is still writing here; let it finish, so every write it
    # makes lands before the check below.
    wait "$STANDIN_PID" 2>/dev/null || true
    [ -e "$TEST_DIR/ready.burst-done" ]   # the premise: the stand-in wrote for its whole second after the TERM
    [ ! -e "$TEST_DIR/target" ]           # and no write of that second outlived the removal
}

@test "the same holds when the process is not this shell's child (the call under run)" {
    # run is a subshell, and the stand-in is a child of the test's shell, not of that subshell: bash's
    # wait cannot reach it there, so the poll alone must see it exit.
    "$STANDIN" "$TEST_DIR/target" "$TEST_DIR/ready" burst &
    STANDIN_PID=$!
    _await_ready
    run stop_then_remove "$STANDIN_PID" "$TEST_DIR/target"
    [ "$status" -eq 0 ]
    wait "$STANDIN_PID" 2>/dev/null || true
    [ -e "$TEST_DIR/ready.burst-done" ]
    [ ! -e "$TEST_DIR/target" ]
}

@test "a process that ignores TERM is KILLed at the bound, the KILL is said on stderr, and the directory is removed" {
    "$STANDIN" "$TEST_DIR/target" "$TEST_DIR/ready" ignore &
    STANDIN_PID=$!
    _await_ready
    run stop_then_remove "$STANDIN_PID" "$TEST_DIR/target" 1
    [ "$status" -eq 0 ]
    [[ "$output" == *"stop-then-remove: pid $STANDIN_PID still running 1s after TERM; sending KILL"* ]]
    [ ! -e "$TEST_DIR/target" ]
    local st rc=0
    st="$(ps -o stat= -p "$STANDIN_PID" 2>/dev/null | tr -d ' ')"
    [[ -z "$st" || "$st" == Z* ]]         # gone, or a zombie awaiting its reap, when the call returned
    wait "$STANDIN_PID" || rc=$?
    [ "$rc" -eq 137 ]                     # killed by the KILL (128 + 9); the TERM did nothing
    [ ! -e "$TEST_DIR/ready.wrote-after-removal" ]   # it wrote every 0.05 s until then, never into a removed directory
}

@test "a zombie counts as exited: the call neither waits out the bound nor sends a KILL" {
    # A zombie still answers kill -0, and a parent that never reaps (here a sleep that bash exec'd into
    # after starting the child) keeps it one. It can write nothing, so the poll must stop at it.
    bash -c 'true & printf "%s\n" "$!" > "$1"; exec sleep 30' _ "$TEST_DIR/zombie.pid" &
    STANDIN_PID=$!   # the sleep, which teardown KILLs; the zombie goes with it
    local zpid="" st="" i
    for ((i = 0; i < 50; i++)); do
        zpid="$(cat "$TEST_DIR/zombie.pid" 2>/dev/null || true)"
        [ -n "$zpid" ] && st="$(ps -o stat= -p "$zpid" 2>/dev/null | tr -d ' ')"
        [[ "$st" == Z* ]] && break
        sleep 0.1
    done
    [[ "$st" == Z* ]]                     # the premise: the pid handed over is a zombie
    SECONDS=0
    run stop_then_remove "$zpid" "$TEST_DIR/target" 2
    [ "$status" -eq 0 ]
    [ "$SECONDS" -lt 2 ]
    [[ "$output" != *"sending KILL"* ]]
    [ ! -e "$TEST_DIR/target" ]
}

@test "an empty pid skips the stop and still removes the directory" {
    stop_then_remove "" "$TEST_DIR/target"
    [ ! -e "$TEST_DIR/target" ]
}

@test "the call fails when the directory cannot be removed, so the teardown still goes red" {
    [ "$(id -u)" -ne 0 ] || skip "root removes the entries of a read-only directory"
    mkdir "$TEST_DIR/target/locked"
    : > "$TEST_DIR/target/locked/f"
    chmod 500 "$TEST_DIR/target/locked"
    run stop_then_remove "" "$TEST_DIR/target"
    chmod 700 "$TEST_DIR/target/locked"
    [ "$status" -ne 0 ]
    [[ "$output" == *"rm:"* ]]
}

@test "tests/romp-manager-origin.bats's teardown ends in stop_then_remove on its manager's pid and test directory" {
    # A source pin. It guards that the suite's teardown still reaches the helper; the cases above are what
    # prove the helper waits. A teardown put back to a kill and an rm -rf of its own would keep them green.
    local body code
    body="$(sed -n '/^teardown() {$/,/^}$/p' "$BATS_TEST_DIRNAME/romp-manager-origin.bats")"
    [ -n "$body" ]
    code="$(printf '%s\n' "$body" | sed 's/^[[:space:]]*//' | grep -Ev '^(#|$|teardown\(\) \{$|\}$)')"
    [ -n "$code" ]
    [ "$(printf '%s\n' "$code" | tail -n 1)" = 'stop_then_remove "${MGR_PID:-}" "$TEST_DIR"' ]
    [ -z "$(printf '%s\n' "$code" | grep -E '(^|[;&|[:space:]])(rm|kill)([[:space:]]|$)' || true)" ]
}
