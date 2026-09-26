#!/usr/bin/env bats

# tests/stop-then-remove.bash stops a test's background process and removes the test's directory only
# once that process has exited. These cases run it against a stand-in that keeps writing under the
# directory after its TERM, the way bin/romp-manager's shutdown writes its restart audit there: nothing
# may be left behind, the call returns at the stand-in's exit and not after a fixed time, a process that
# ignores TERM is KILLed, and a directory that cannot be removed still fails the call. The last case
# checks that tests/romp-manager-origin.bats's teardown goes through the helper. Nothing below starts a
# manager.
#
# Among the parts of the helper no case pins (changing each leaves every case green): the branch for a
# pid still running five seconds after its KILL, which no case reaches, since a KILL cannot be caught or
# ignored; the `wait` that reaps a pid that is this shell's child, which case 1 runs, though no case
# reads a status that `wait` could change; when the KILL comes, and which stream its message goes to
# (case 3 reads the message in run's merged output); the default bound's value (a default of 4 s leaves
# every case green); and a pid whose TERM fails, one already gone at the call or one that kill -0 is
# refused on, which no case passes: the helper swallows the failure, the poll ends at once and the
# directory is removed, and a helper that returned at the failed TERM instead, leaving the directory,
# keeps every case green.

load stop-then-remove

# The wall clock in microseconds, for the bounds on when a call returns: bash 5's EPOCHREALTIME where it
# is set, else perl's Time::HiRes, since the macOS cell's bash is 3.2 and has no EPOCHREALTIME. The
# stand-in carries a copy (setup writes it in), so both sides read the same clock.
_now_us() {
    local t="${EPOCHREALTIME:-}"
    [ -n "$t" ] || t="$(perl -MTime::HiRes=time -e 'printf "%.6f", time')"
    printf '%s\n' "${t//[!0-9]/}"
}

setup() {
    TEST_DIR="$(mktemp -d)"
    # The stand-in. $1 the directory to write under, $2 a file it creates once its TERM disposition is
    # set, $3 what a TERM does, $4 how many rows a burst writes (20 by default): `burst` writes a row
    # every 0.05 s, so 20 rows take about a second (recreating the directory with mkdir -p, as the
    # manager's mkdirSync does), then writes the clock's reading into $2.burst-done and exits; `ignore`
    # ignores TERM and writes until it is KILLed, with builtins only, so no child of its own can write
    # after the KILL, and marks $2.wrote-after-removal if a write finds the directory gone.
    STANDIN="$TEST_DIR/standin"
    { echo '#!/usr/bin/env bash'; declare -f _now_us; cat <<'EOF'; } > "$STANDIN"
dir="$1"; ready="$2"; mode="$3"; rows="${4:-20}"
burst() {
    local i
    for i in $(seq 1 "$rows"); do
        mkdir -p "$dir/state/romp" 2>/dev/null
        printf 'row\n' 2>/dev/null >> "$dir/state/romp/restart-audit.jsonl"
        sleep 0.05
    done
    _now_us > "$ready.burst-done"
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

_returned_at_the_exit() {   # $1 and $2 the call's start and end (microseconds), after a burst stand-in has exited
    # The call returned after the stand-in's last write, and less than a second after it. On its own this
    # passes a fixed wait a little longer than cases 1 and 2's one-second burst; case 5's three-second
    # stand-in is what rules out a fixed wait in place of the poll.
    local done_us
    done_us="$(cat "$TEST_DIR/ready.burst-done")"
    echo "the call started at $1, the stand-in's last write was at $done_us, the call returned at $2 (microseconds)"
    [ "$2" -ge "$done_us" ]
    [ $(( $2 - done_us )) -lt 1000000 ]
}

@test "the directory is removed only once a process still writing after its TERM has exited" {
    "$STANDIN" "$TEST_DIR/target" "$TEST_DIR/ready" burst &
    STANDIN_PID=$!
    _await_ready
    local start end
    start="$(_now_us)"
    stop_then_remove "$STANDIN_PID" "$TEST_DIR/target" 2>"$TEST_DIR/stderr"   # in this shell, as teardown() calls it
    end="$(_now_us)"
    # A writer the helper did not wait for is still writing here; let it finish, so every write it
    # makes lands before the check below.
    wait "$STANDIN_PID" 2>/dev/null || true
    [ -e "$TEST_DIR/ready.burst-done" ]   # the premise: the stand-in wrote for its whole second after the TERM
    [ ! -e "$TEST_DIR/target" ]           # and no write of that second outlived the removal
    [[ "$(cat "$TEST_DIR/stderr")" != *KILL* ]]   # the TERM ended it; no KILL was sent
    _returned_at_the_exit "$start" "$end"
}

@test "the same holds when the process is not this shell's child (the call under run)" {
    # run is a subshell, and the stand-in is a child of the test's shell, not of that subshell: bash's
    # wait cannot reach it there, so the poll alone must see it exit.
    "$STANDIN" "$TEST_DIR/target" "$TEST_DIR/ready" burst &
    STANDIN_PID=$!
    _await_ready
    local start end
    start="$(_now_us)"
    run stop_then_remove "$STANDIN_PID" "$TEST_DIR/target"
    end="$(_now_us)"
    [ "$status" -eq 0 ]
    [[ "$output" != *KILL* ]]             # the TERM ended it; no KILL was sent
    wait "$STANDIN_PID" 2>/dev/null || true
    [ -e "$TEST_DIR/ready.burst-done" ]
    [ ! -e "$TEST_DIR/target" ]
    _returned_at_the_exit "$start" "$end"
}

@test "a process that ignores TERM is KILLed, the KILL is said in the call's output, and the directory is removed" {
    "$STANDIN" "$TEST_DIR/target" "$TEST_DIR/ready" ignore &
    STANDIN_PID=$!
    _await_ready
    run stop_then_remove "$STANDIN_PID" "$TEST_DIR/target" 1
    [ "$status" -eq 0 ]
    [[ "$output" == *"stop-then-remove: pid $STANDIN_PID still running 1s after TERM; sending KILL"* ]]
    [[ "$output" != *"after KILL"* ]]     # the poll after the KILL saw it exit
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
    # The child exits only on a flag raised once its parent has become the sleep: a child that exits
    # before the exec can be reaped by bash first, and then no zombie is left (seen in CI). Its loop also
    # ends once that parent is gone ($$ in it is the pid that becomes the sleep, which teardown KILLs and
    # reaps), and the command runs with fd 3 closed. A child that polled on after a failed premise below
    # held bats' fd 3 open, and the bats run did not exit after reporting the failure.
    bash -c 'while [ ! -e "$2" ] && kill -0 $$ 2>/dev/null; do sleep 0.02; done & printf "%s\n" "$!" > "$1"; exec sleep 30' \
        _ "$TEST_DIR/zombie.pid" "$TEST_DIR/zombie.go" 3>&- &
    STANDIN_PID=$!   # the sleep, which teardown KILLs; the zombie goes with it
    local zpid="" comm="" st="" i
    for ((i = 0; i < 100; i++)); do
        comm="$(ps -o comm= -p "$STANDIN_PID" 2>/dev/null | tr -d ' ')"
        zpid="$(cat "$TEST_DIR/zombie.pid" 2>/dev/null || true)"
        [[ "$comm" == sleep && -n "$zpid" ]] && break
        sleep 0.05
    done
    [[ "$comm" == sleep && -n "$zpid" ]]  # the parent has exec'd into the sleep, and the child's pid is known
    : > "$TEST_DIR/zombie.go"
    for ((i = 0; i < 100; i++)); do
        st="$(ps -o stat= -p "$zpid" 2>/dev/null | tr -d ' ')"
        [[ "$st" == Z* ]] && break
        sleep 0.05
    done
    [[ "$st" == Z* ]]                     # the premise: the pid handed over is a zombie
    SECONDS=0
    run stop_then_remove "$zpid" "$TEST_DIR/target" 2
    [ "$status" -eq 0 ]
    [ "$SECONDS" -lt 2 ]
    [[ "$output" != *"sending KILL"* ]]
    [ ! -e "$TEST_DIR/target" ]
}

@test "a process that writes for three seconds after its TERM is waited for, not cut off after a fixed time" {
    # 60 rows, three seconds or more: longer than a fixed time a helper might wait in place of the exit.
    # A fixed wait shorter than this burst KILLs the stand-in before it has finished; one longer than it
    # makes cases 1 and 2 return more than a second after their one-second burst has ended.
    "$STANDIN" "$TEST_DIR/target" "$TEST_DIR/ready" burst 60 &
    STANDIN_PID=$!
    _await_ready
    local start end
    start="$(_now_us)"
    run stop_then_remove "$STANDIN_PID" "$TEST_DIR/target"
    end="$(_now_us)"
    [ "$status" -eq 0 ]
    [[ "$output" != *KILL* ]]             # the TERM ended it; no KILL was sent
    wait "$STANDIN_PID" 2>/dev/null || true
    [ -e "$TEST_DIR/ready.burst-done" ]   # the premise: it wrote all 60 rows after its TERM
    [ $(( $(cat "$TEST_DIR/ready.burst-done") - start )) -ge 3000000 ]   # which took three seconds or more
    [ ! -e "$TEST_DIR/target" ]
    _returned_at_the_exit "$start" "$end"
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
