# tests/stop-then-remove.bash: the last step of a teardown whose test started a background process that
# writes under the test's directory. It stops the process, waits until the process has exited, and only
# then removes the directory.
#
# Use from a bats file: `load stop-then-remove` at the top, then `stop_then_remove "${PID:-}" "$TEST_DIR"`
# as the last line of teardown(). An empty PID skips the stop (a test that skipped before it started its
# process). The call's status is rm's, so a directory that cannot be removed still fails the test. An
# optional third argument is the bound in whole seconds (default 10).
#
# Why (fork PR 913's CI, 2026-09-25): tests/romp-manager-origin.bats killed its manager and removed the
# test directory on the next line. The manager's TERM handler writes restart-audit.jsonl under the state
# root inside that directory before it exits (shutdownAll and auditSigterm in bin/romp-manager), and on a
# slow runner the write landed while rm was walking the tree: `rm: cannot remove '.../state/romp':
# Directory not empty`, a red teardown after every assertion of the test had passed. A write that lands
# after rm has finished fails nothing and is as wrong: the writer's mkdir recreates the directory, and it
# is left behind in the temp dir.
#
# The wait is a poll, not bash's `wait`, which reaches only this shell's own children (a call under `run`
# is a subshell, whose parent's children it cannot wait on) and has no bound. The poll works for any pid
# this shell may signal. A pid that `kill -0` is refused on (another user's process, for example) is
# treated as gone, and the directory is removed at once. After the bound it sends KILL, says so on stderr, and polls for up to five more seconds. The default
# bound is above the manager's own shutdown grace for its kernels (8 s, then it exits), so a manager is
# not cut off in the middle of its shutdown. A zombie counts as exited, since it can write nothing more.
# Once the poll ends, `wait` reaps the process when it is this shell's child.
#
# It stops one process. Children of that process that also write under the directory are the caller's
# to stop, unless the process stops them itself before it exits, as the manager does its kernels.

stop_then_remove() {   # stop_then_remove PID DIR [BOUND]: TERM PID, wait for it to exit (KILL at BOUND s), then rm -rf DIR
    local pid="$1" dir="$2" bound="${3:-10}" i
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null || true
        for ((i = 0; i < bound * 10; i++)); do
            _stop_then_remove_running "$pid" || break
            sleep 0.1
        done
        if _stop_then_remove_running "$pid"; then
            echo "stop-then-remove: pid $pid still running ${bound}s after TERM; sending KILL" >&2
            kill -9 "$pid" 2>/dev/null || true
            for ((i = 0; i < 50; i++)); do
                _stop_then_remove_running "$pid" || break
                sleep 0.1
            done
        fi
        if _stop_then_remove_running "$pid"; then
            echo "stop-then-remove: pid $pid still running 5s after KILL; removing $dir anyway" >&2
        else
            wait "$pid" 2>/dev/null || true
        fi
    fi
    rm -rf "$dir"
}

_stop_then_remove_running() {   # $1 pid: true while it runs; false once it is gone or a zombie
    local st
    kill -0 "$1" 2>/dev/null || return 1
    st="$(ps -o stat= -p "$1" 2>/dev/null | tr -d ' ')"
    case "$st" in Z*) return 1 ;; esac
    return 0
}
