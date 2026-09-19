#!/usr/bin/env bats

# romp-service generates the right login-agent unit per platform (launchd plist on
# macOS, systemd --user on Linux). ROMP_SERVICE_NO_LOAD asserts unit content without
# touching launchctl/systemctl; ROMP_OS_OVERRIDE exercises both platforms on one host.

setup() {
    TEST_DIR="$(mktemp -d)"
    SVC="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-service"
    export HOME="$TEST_DIR/home"
    export XDG_STATE_HOME="$HOME/.local/state"
    export ROMP_LAUNCHD_DIR="$TEST_DIR/LaunchAgents"
    export ROMP_SYSTEMD_DIR="$TEST_DIR/systemd"
    export ROMP_SERVICE_NO_LOAD=1                      # write the unit, don't load it
    export ROMP_MANAGER_BIN="$TEST_DIR/romp-manager"   # stable path to assert in the unit
    mkdir -p "$HOME"
    # A stand-in "node" so the macOS install's romp-node copy is hermetic + fast
    # (a byte-copy of THIS, asserted by content) rather than the real multi-MB node.
    printf '#!/bin/sh\necho fake-node "$@"\n' > "$TEST_DIR/fake-node"
    chmod +x "$TEST_DIR/fake-node"
    export ROMP_NODE_SRC="$TEST_DIR/fake-node"
    # Running this suite INSIDE a romp session inherits the live kernel's ROMP_SERVE_PORT /
    # ROMP_MANAGER_PORT, which the unit now bakes — so a default-vs-override test would be
    # reading the developer's machine instead of the code. Clear the whole instance set; the
    # tests that want them set them explicitly.
    unset ROMP_SERVE_PORT ROMP_KERNEL_PORT ROMP_POSTAL_PORT ROMP_MANAGER_PORT ROMP_STATE_DIR CLAUDE_CONFIG_DIR
    # The env-file path is baked (and, when non-default, exported) into the unit too; a developer shell
    # that carries any of these must not leak it into the default-install assertions below.
    unset ROMP_SERVICE_ENV_FILE ROMP_SERVICE_ENV XDG_CONFIG_HOME
    # The macOS install's verification probes the control port when the agent's manager is not running (a manager
    # already serving there, a hand-run one, is named as such). A developer's machine, and a romp session's, has a
    # live manager on the default port, so every test here answers that probe with a stand-in that says nothing
    # serves; the tests about that state set their own.
    printf '#!/bin/sh\nexit 1\n' > "$TEST_DIR/probe-nothing"
    chmod +x "$TEST_DIR/probe-nothing"
    export ROMP_MANAGER_PROBE="$TEST_DIR/probe-nothing"
}

teardown() {
    # the hang shapes record their pids: whatever a failing case left alive dies here, never in the suite's wake
    local p; for p in node sleeper; do [ -s "$TEST_DIR/$p.pid" ] && kill -KILL "$(cat "$TEST_DIR/$p.pid")" 2>/dev/null; done
    rm -rf "$TEST_DIR"
}

@test "install (macOS): launchd plist runs 'romp-manager up' at login, kept alive" {
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    [ -f "$plist" ]
    grep -q "<string>$ROMP_MANAGER_BIN</string>" "$plist"
    grep -q "<string>up</string>" "$plist"
    grep -q "RunAtLoad" "$plist"
    grep -q "KeepAlive" "$plist"
    # issue 1600: KeepAlive with launchd's default ten-second throttle respawned a manager that died at once
    # six times a minute forever; the interval bounds that loop to once a minute (a manager that ran longer
    # than it before exiting is respawned at once, since the throttle counts from the job's last start)
    grep -q "<key>ThrottleInterval</key><integer>60</integer>" "$plist"
}

@test "install (macOS): login agent runs the manager under the romp-node copy (FDA identity)" {
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    local launcher; launcher="$(dirname "$SVC")/romp-node-launch"
    # ProgramArguments must be: <launcher> <manager> up — the launcher FIRST, so
    # macOS keys the Full Disk Access grant to romp-node, not the shared "node".
    grep -Fq "<string>$launcher</string>" "$plist"
    grep -Fq "<string>$ROMP_MANAGER_BIN</string>" "$plist"
    grep -q "<string>up</string>" "$plist"
    local lline mline
    lline="$(grep -Fn "$launcher" "$plist" | head -1 | cut -d: -f1)"
    mline="$(grep -Fn "$ROMP_MANAGER_BIN" "$plist" | head -1 | cut -d: -f1)"
    [ "$lline" -lt "$mline" ]
    # The romp-node copy was created as a byte-for-byte copy of the source node.
    local rn="$XDG_STATE_HOME/romp/romp-node"
    [ -x "$rn" ]
    cmp -s "$ROMP_NODE_SRC" "$rn"
    # install tells the user the exact path to grant Full Disk Access to.
    [[ "$output" == *"$rn"* ]]
    [[ "$output" == *"Full Disk Access"* ]]
}

@test "install (macOS): a node copy that cannot run from the state dir is removed, and the install says the manager runs on the system node" {
    # issue 1600: the copy is probed once made (an empty program, stdin closed, a bound); a node whose shared
    # library is referenced relative to its install dies from the copy, so the copy goes and the message
    # names the consequence for Full Disk Access. The launcher probes too, so this is the install's half.
    local src="$TEST_DIR/bound-node"
    cat > "$src" <<EOF
#!/bin/sh
case "\$0" in
  "$src") exit 0 ;;
  *) echo "dyld[4242]: Library not loaded: @rpath/libnode.dylib" >&2; exit 134 ;;
esac
EOF
    chmod +x "$src"
    ROMP_NODE_SRC="$src" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local rn="$XDG_STATE_HOME/romp/romp-node"
    [ ! -e "$rn" ]                                            # the unusable copy is gone
    [[ "$output" == *"cannot run from $rn"* ]]
    [[ "$output" == *"runs on the system node"* ]]
    [[ "$output" == *"ROMP_NO_NODE_COPY=1"* ]]
    [[ "$output" != *"grant it to romp's OWN node copy"* ]]   # no grant advice for a copy that is not there
}

@test "install (macOS): ROMP_NO_NODE_COPY=1 in service.env, the route the message names, makes no copy and removes a stale one" {
    # round two of issue 1600: the install never parsed service.env (it bakes the path into the unit and the plist), so
    # the line the messages name did nothing for the install's own copy. The environment is UNSET here; the file is
    # the default one under this test's HOME (the setup clears XDG_CONFIG_HOME and ROMP_SERVICE_ENV_FILE).
    ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null        # a copy from a normal install
    local rn="$XDG_STATE_HOME/romp/romp-node"
    [ -x "$rn" ]
    unset ROMP_NO_NODE_COPY
    mkdir -p "$HOME/.config/romp"
    printf '# knobs\nROMP_NO_NODE_COPY="1"\n' > "$HOME/.config/romp/service.env"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ ! -e "$rn" ]
    [[ "$output" != *"grant it to romp's OWN node copy"* ]]   # no grant advice for a copy that is not there
    # …and the line read from a non-default path, the one the plist and unit are told about
    printf 'ROMP_NO_NODE_COPY=\n' > "$HOME/.config/romp/service.env"   # an empty value is OFF
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ -x "$rn" ]
    export ROMP_SERVICE_ENV_FILE="$TEST_DIR/elsewhere/service.env"
    mkdir -p "$TEST_DIR/elsewhere"; printf 'ROMP_NO_NODE_COPY=yes\n' > "$ROMP_SERVICE_ENV_FILE"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ ! -e "$rn" ]
}

@test "install (macOS): a node copy that HANGS from the state dir is killed at the bound and removed, and no node is leaked" {
    command -v setsid >/dev/null 2>&1 || skip "needs setsid to scope the process-group check (Linux)"
    local src="$TEST_DIR/hang-node"
    cat > "$src" <<EOF
#!/bin/sh
case "\$0" in
  "$src") exit 0 ;;
  *) exec sleep 600 ;;
esac
EOF
    chmod +x "$src"
    local bare="$TEST_DIR/bare"; mkdir -p "$bare"
    local t
    for t in bash sh cmp cp chmod mv mkdir rm sleep ps setsid id date cut head tr printf sed cat grep dirname readlink; do p="$(command -v "$t" 2>/dev/null || true)"; [ -n "$p" ] && ln -s "$p" "$bare/$t"; done
    local tmo; tmo="$(command -v timeout || true)"
    [ -n "$tmo" ] || skip "needs coreutils timeout to bound the run"
    PATH="$bare" ROMP_NODE_SRC="$src" ROMP_OS_OVERRIDE=Darwin run "$tmo" 60 setsid -w bash -c 'printf "%s\n" "$$" > "$1"; exec "$2" install' _ "$TEST_DIR/pgid" "$SVC"
    [ "$status" -eq 0 ]
    [ ! -e "$XDG_STATE_HOME/romp/romp-node" ]
    [[ "$output" == *"cannot run from"* ]]
    local pgid; pgid="$(cat "$TEST_DIR/pgid")"
    run bash -c 'ps -eo pgid=,args= | awk -v g="$1" "\$1==g"' _ "$pgid"
    [[ "$output" != *"sleep 600"* ]]
    [ -z "$output" ]
}

# These cases need setsid and coreutils timeout for their outer bound, so on a mac, the platform that takes the watchdog
# path, they SKIP: the watchdog code is the same on both platforms and is exercised here through the bare PATH, but a mac
# run of the suite proves nothing about it (the tidy of the fresh-install set names this; a mac-shaped bound is future work).
# The hang shapes on both probe paths, the install's twin of the launcher's matrix (round four of issue 1600): exec (the
# copy is the hung process), fork (a version manager's shim runs node instead of exec'ing it: the hung process is a child
# of the pid the wrapper holds, which leaked on the watchdog path) and deaf (TERM ignored: only KILL ends it, and a timeout
# without -k held the install for good). The stand-in runs from its source path and hangs from the copy's; the bound is
# two seconds here (ROMP_NODE_PROBE_BOUND); the hung pids go to files, so the leak check names them.
_hang_src() {   # $1 shape: exec | fork | deaf
    local body
    case "$1" in
      exec) body='exec sleep 60' ;;
      fork) body='sleep 60 & echo $! > "'"$TEST_DIR"'/sleeper.pid"; wait' ;;
      deaf) body='trap "" TERM; exec sleep 60' ;;
    esac
    cat > "$TEST_DIR/hang-node" <<EOF
#!/bin/sh
case "\$0" in
  "$TEST_DIR/hang-node") exit 0 ;;
  *) echo \$\$ > "$TEST_DIR/node.pid"; $body ;;
esac
EOF
    chmod +x "$TEST_DIR/hang-node"
}
_dead() {   # $1 pid: gone, or a zombie awaiting its reap
    local st; st="$(ps -o stat= -p "$1" 2>/dev/null | tr -d ' ')"
    [ -z "$st" ] || [ "${st#Z}" != "$st" ]
}
_run_install_hang() {   # $1 shape, $2 path: bare (the watchdog) | timeout; the install in its own session under a 20 s outer bound
    command -v setsid >/dev/null 2>&1 || skip "needs setsid to scope the process-group check (Linux)"
    local tmo; tmo="$(command -v timeout || true)"
    [ -n "$tmo" ] || skip "needs coreutils timeout to bound the run"
    _hang_src "$1"
    local bare="$TEST_DIR/bare"; rm -rf "$bare"; mkdir -p "$bare"
    local t p
    for t in bash sh cmp cp chmod mv mkdir rm sleep ps pgrep setsid id date cut head tr printf sed cat grep dirname readlink; do p="$(command -v "$t" 2>/dev/null || true)"; [ -n "$p" ] && ln -s "$p" "$bare/$t"; done
    if [ "$2" = timeout ]; then ln -s "$tmo" "$bare/timeout"; fi
    rm -f "$TEST_DIR/node.pid" "$TEST_DIR/sleeper.pid" "$TEST_DIR/pgid"
    PATH="$bare" ROMP_NODE_PROBE_BOUND=2 ROMP_NODE_SRC="$TEST_DIR/hang-node" ROMP_OS_OVERRIDE=Darwin run "$tmo" 20 setsid -w bash -c 'printf "%s\n" "$$" > "$1"; exec "$2" install' _ "$TEST_DIR/pgid" "$SVC"
}
_install_hang_asserts() {   # the copy is removed with the reason said, and nothing of the probe survives: not the node, not its child, nothing in the session
    [ "$status" -eq 0 ]
    [ ! -e "$XDG_STATE_HOME/romp/romp-node" ]
    [[ "$output" == *"cannot run from"* ]]
    [ -s "$TEST_DIR/node.pid" ]
    _dead "$(cat "$TEST_DIR/node.pid")"
    [ ! -s "$TEST_DIR/sleeper.pid" ] || _dead "$(cat "$TEST_DIR/sleeper.pid")"
    local pgid; pgid="$(cat "$TEST_DIR/pgid")"
    run bash -c 'ps -eo pgid=,args= | awk -v g="$1" "\$1==g"' _ "$pgid"
    [ -z "$output" ]
}
@test "install (macOS), the watchdog path: a shim that FORKS the hung node leaks nothing: the tree under the wrapper's pid is killed" { _run_install_hang fork bare; _install_hang_asserts; }
@test "install (macOS), the watchdog path: a node that IGNORES TERM is killed a second later and the copy removed" { _run_install_hang deaf bare; _install_hang_asserts; }
@test "install (macOS), the timeout path: a hung copy is killed at the bound (control: so it was before this round)" { _run_install_hang exec timeout; _install_hang_asserts; }
@test "install (macOS), the timeout path: a shim that FORKS the hung node leaks nothing (control: timeout signals the whole group)" { _run_install_hang fork timeout; _install_hang_asserts; }
@test "install (macOS), the timeout path: a node that IGNORES TERM is killed by -k a second after the bound instead of holding the install for good" { _run_install_hang deaf timeout; _install_hang_asserts; }

@test "install (macOS): ROMP_NODE_PROBE_BOUND=0 is clamped to one second, so a good copy is kept instead of failed at once" {
    # on the watchdog path (a bare PATH without timeout, a stock mac's): the base's sleep 0 killed the probe before a copy that
    # takes half a second answered (the setup's instant stand-in beat that kill, so the copy here sleeps first)
    printf '#!/bin/sh\nsleep 0.5\necho fake-node "$@"\n' > "$TEST_DIR/slow-node"; chmod +x "$TEST_DIR/slow-node"
    local bare="$TEST_DIR/bare"; rm -rf "$bare"; mkdir -p "$bare"
    local t p
    for t in bash sh cmp cp chmod mv mkdir rm sleep ps pgrep id date cut head tr printf sed cat grep dirname readlink; do p="$(command -v "$t" 2>/dev/null || true)"; [ -n "$p" ] && ln -s "$p" "$bare/$t"; done
    PATH="$bare" ROMP_NODE_SRC="$TEST_DIR/slow-node" ROMP_NODE_PROBE_BOUND=0 ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ -x "$XDG_STATE_HOME/romp/romp-node" ]
    [[ "$output" != *"cannot run from"* ]]
    # and a value with a leading zero is a decimal bound, not an octal error on stderr (round two of the tidy)
    ROMP_NODE_PROBE_BOUND=08 ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ -x "$XDG_STATE_HOME/romp/romp-node" ]
    [[ "$output" != *"value too great"* ]]
    [[ "$output" != *"octal"* ]]
    # and a huge value is the hour cap, not an integer diagnostic and a one-second clamp (the second tidy)
    ROMP_NODE_PROBE_BOUND=99999999999999999999 ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ -x "$XDG_STATE_HOME/romp/romp-node" ]
    [[ "$output" != *"integer expression expected"* ]]
}

@test "install (macOS): a ROMP_NODE_PROBE_BOUND with leading zeros is its number, not an hour: 0000001 bounds a hung copy at one second" {
    local tmo; tmo="$(command -v timeout || true)"
    [ -n "$tmo" ] || skip "needs coreutils timeout to bound the run"
    _hang_src exec
    rm -f "$TEST_DIR/node.pid"
    ROMP_NODE_PROBE_BOUND=0000001 ROMP_NODE_SRC="$TEST_DIR/hang-node" ROMP_OS_OVERRIDE=Darwin run "$tmo" 20 "$SVC" install
    [ "$status" -eq 0 ]                                        # not the outer bound: an hour would have hit it
    [ ! -e "$XDG_STATE_HOME/romp/romp-node" ]
    [[ "$output" == *"cannot run from"* ]]
}

@test "install (macOS), the watchdog path: a sleep on PATH that FORKS its sleep leaves no child behind: the sleep's tree is ended" {
    command -v setsid >/dev/null 2>&1 || skip "needs setsid to scope the process-group check (Linux)"
    local bare="$TEST_DIR/bare-fork"; mkdir -p "$bare"
    local t p
    for t in bash sh cmp cp chmod mv mkdir rm ps pgrep setsid id date cut head tr printf sed cat grep dirname readlink; do p="$(command -v "$t" 2>/dev/null || true)"; [ -n "$p" ] && ln -s "$p" "$bare/$t"; done
    local real; real="$(command -v sleep)"
    printf '#!/bin/sh\n"%s" "$@" &\nwait\n' "$real" > "$bare/sleep"; chmod +x "$bare/sleep"
    printf '#!/bin/sh\n"%s" 0.3\necho fake-node "$@"\n' "$real" > "$TEST_DIR/slow-node"; chmod +x "$TEST_DIR/slow-node"
    PATH="$bare" ROMP_NODE_SRC="$TEST_DIR/slow-node" ROMP_OS_OVERRIDE=Darwin run setsid -w bash -c 'printf "%s\n" "$$" > "$1"; exec "$2" install' _ "$TEST_DIR/pgid" "$SVC"
    [ "$status" -eq 0 ]
    [ -x "$XDG_STATE_HOME/romp/romp-node" ]
    local pgid; pgid="$(cat "$TEST_DIR/pgid")"
    run bash -c 'ps -eo pgid=,args= | awk -v g="$1" "\$1==g"' _ "$pgid"
    [ -z "$output" ]
}

@test "install (macOS), the watchdog path: a sleep on PATH that ignores TERM is KILLed after a bounded check, so a fast probe does not wait out the bound" {
    command -v setsid >/dev/null 2>&1 || skip "needs setsid to scope the process-group check (Linux)"
    local tmo; tmo="$(command -v timeout || true)"
    [ -n "$tmo" ] || skip "needs coreutils timeout to bound the run"
    local bare="$TEST_DIR/bare-deaf"; mkdir -p "$bare"
    local t p
    for t in bash sh cmp cp chmod mv mkdir rm ps pgrep setsid id date cut head tr printf sed cat grep dirname readlink; do p="$(command -v "$t" 2>/dev/null || true)"; [ -n "$p" ] && ln -s "$p" "$bare/$t"; done
    local real; real="$(command -v sleep)"
    printf '#!/bin/sh\ntrap "" TERM\nexec "%s" "$@"\n' "$real" > "$bare/sleep"; chmod +x "$bare/sleep"
    local t0=$SECONDS
    PATH="$bare" ROMP_NODE_PROBE_BOUND=8 ROMP_OS_OVERRIDE=Darwin run "$tmo" 30 setsid -w bash -c 'printf "%s\n" "$$" > "$1"; exec "$2" install' _ "$TEST_DIR/pgid" "$SVC"
    [ "$status" -eq 0 ]
    [ -x "$XDG_STATE_HOME/romp/romp-node" ]
    [ $((SECONDS - t0)) -lt 5 ]
    local pgid; pgid="$(cat "$TEST_DIR/pgid")"
    run bash -c 'ps -eo pgid=,args= | awk -v g="$1" "\$1==g"' _ "$pgid"
    [ -z "$output" ]
}

@test "install (macOS): the hatch reads 0, false, no and off as off, and the file's last assignment wins" {
    mkdir -p "$HOME/.config/romp"
    local rn="$XDG_STATE_HOME/romp/romp-node"
    unset ROMP_NO_NODE_COPY
    for v in 0 false No off OFF; do
        rm -f "$rn"
        printf 'ROMP_NO_NODE_COPY=%s\n' "$v" > "$HOME/.config/romp/service.env"
        ROMP_OS_OVERRIDE=Darwin run "$SVC" install
        [ "$status" -eq 0 ]
        [ -x "$rn" ]
    done
    for v in disabled none; do                                 # any other non-empty value is on: the docs say so
        rm -f "$rn"
        printf 'ROMP_NO_NODE_COPY=%s\n' "$v" > "$HOME/.config/romp/service.env"
        ROMP_OS_OVERRIDE=Darwin run "$SVC" install
        [ "$status" -eq 0 ]
        [ ! -e "$rn" ]
    done
    printf 'ROMP_NO_NODE_COPY=1\nROMP_NO_NODE_COPY=\n' > "$HOME/.config/romp/service.env"   # set, then cleared below: the copy is made
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ -x "$rn" ]
    printf 'ROMP_NO_NODE_COPY=\nROMP_NO_NODE_COPY=1\n' > "$HOME/.config/romp/service.env"   # cleared, then set: skipped and removed
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ ! -e "$rn" ]
    printf 'ROMP_NO_NODE_COPY=0\n' > "$HOME/.config/romp/service.env"                            # the file's last word wins over the environment: it says off here
    ROMP_NO_NODE_COPY=0 ROMP_OS_OVERRIDE=Darwin run "$SVC" install                              # 0 in the environment is off too
    [ "$status" -eq 0 ]
    [ -x "$rn" ]
}

@test "install (macOS): ROMP_NO_NODE_COPY=1 in the environment makes no copy either (the second route)" {
    ROMP_NO_NODE_COPY=1 ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ ! -e "$XDG_STATE_HOME/romp/romp-node" ]
}

@test "install (macOS): a node copy that dies by SIGNAL from the state dir leaves no job-status line in the output" {
    local src="$TEST_DIR/abort-node"
    cat > "$src" <<EOF
#!/bin/sh
case "\$0" in
  "$src") exit 0 ;;
  *) kill -ABRT \$\$ ;;
esac
EOF
    chmod +x "$src"
    ROMP_NODE_SRC="$src" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ ! -e "$XDG_STATE_HOME/romp/romp-node" ]
    [[ "$output" == *"cannot run from"* ]]
    [[ "$output" != *"Aborted"* ]]
    [[ "$output" != *"core dumped"* ]]
}

@test "install (Linux): systemd unit is unchanged — no romp-node launcher (no TCC there)" {
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    grep -q "ExecStart=$ROMP_MANAGER_BIN up" "$unit"
    # `run` + status, NOT a bare `! grep`: `!` is exempt from set -e, so mid-test it asserts nothing.
    run grep -q "romp-node-launch" "$unit"
    [ "$status" -ne 0 ]
    [ ! -e "$XDG_STATE_HOME/romp/romp-node" ]
}

@test "install (Linux): systemd --user service runs 'romp-manager up', restart=always" {
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    [ -f "$unit" ]
    grep -q "ExecStart=$ROMP_MANAGER_BIN up" "$unit"
    grep -q "Restart=always" "$unit"
    grep -q "WantedBy=default.target" "$unit"
}

@test "status reflects install; uninstall removes the unit (macOS)" {
    ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [[ "$output" == *"not installed"* ]]
    ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [[ "$output" == *"installed:"* ]]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" uninstall
    [ "$status" -eq 0 ]
    [ ! -f "$ROMP_LAUNCHD_DIR/com.romp.manager.plist" ]
}

# The install's bootstrap races the preceding bootout (launchd rejects with
# "Input/output error" while the old job drains). ROMP_LAUNCHCTL stubs launchctl
# to exercise that path: install must RETRY until launchd accepts, and fail
# loudly — never silently — if it never does (a swallowed failure leaves no
# agent loaded and a dead kernel with nothing saying why).

@test "install (macOS): bootstrap retries through the bootout drain race" {
    unset ROMP_SERVICE_NO_LOAD
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$1" >> "$calls"
[ "\$1" = bootout ] && exit 0
# once loaded, print names the live process (the post-install check reads the pid line, not print's exit)
[ "\$1" = print ] && [ "\$(grep -c bootstrap "$calls")" -ge 3 ] && { echo "	pid = 4242"; exit 0; }
[ "\$(grep -c bootstrap "$calls")" -ge 3 ] && exit 0
echo "Bootstrap failed: 5: Input/output error" >&2
exit 5
EOF
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    grep -q bootout "$calls"
    [ "$(grep -c bootstrap "$calls")" -eq 3 ]
    [[ "$output" == *"Installed launchd agent"* ]]
}

@test "install (macOS): no bootstrap while the old job is still draining" {
    # bootout only STARTS the teardown; a manager draining live SDK sessions outlives any
    # blind retry window (2026-07-20, twice: every bootstrap rejected mid-drain -> no agent
    # loaded, dead dashboard). Install must WAIT for the job to actually leave launchd
    # (print stops answering) and only then bootstrap.
    unset ROMP_SERVICE_NO_LOAD
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$1" >> "$calls"
if [ "\$1" = print ]; then
    # After bootstrap the NEW job answers print with its live pid (the post-install running check reads it).
    grep -q bootstrap "$calls" && { echo "	pid = 4242"; exit 0; }
    [ "\$(grep -c print "$calls")" -ge 4 ] && exit 5   # the old job finally drains away
    exit 0                                             # still tearing down (loaded, no process named)
fi
exit 0
EOF
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ "$(grep -c print "$calls")" -ge 4 ]              # waited through the drain
    [ "$(grep -c bootstrap "$calls")" -eq 1 ]          # then loaded cleanly, first try
    # the drain-wait prints stop BEFORE the bootstrap; only the running-check prints follow it
    grep -B1000 bootstrap "$calls" | grep -q print     # waited, then bootstrapped
}

@test "install (macOS): a bootstrap that never lands fails LOUDLY, not silently" {
    unset ROMP_SERVICE_NO_LOAD
    local stub="$TEST_DIR/launchctl-stub"
    cat > "$stub" <<'EOF'
#!/bin/sh
[ "$1" = bootout ] && exit 0
echo "Bootstrap failed: 5: Input/output error" >&2
exit 5
EOF
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 1 ]
    [[ "$output" == *"FAILED to load the login agent"* ]]
    [[ "$output" == *"Input/output error"* ]]
    [[ "$output" == *"Retry by hand"* ]]
}

@test "unsupported OS fails cleanly" {
    ROMP_OS_OVERRIDE=Plan9 run "$SVC" install
    [ "$status" -eq 1 ]
    [[ "$output" == *"unsupported OS"* ]]
}

@test "install appends an attribution line to the restart audit" {
    # Four unload-without-reload outages in one day were untraceable: the loud failure went to the
    # CALLER's stderr and nothing recorded WHO ran the install. Every install now journals itself.
    export XDG_STATE_HOME="$TEST_DIR/state"
    export CLAUDE_CODE_SESSION_ID="11111111-2222-3333-4444-555555555555"
    mkdir -p "$TEST_DIR/state/romp/names"
    printf 'testsess\t/tmp\n' > "$TEST_DIR/state/romp/names/11111111-2222-3333-4444-555555555555"
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 run "$SVC" install
    [ "$status" -eq 0 ]
    local aud="$TEST_DIR/state/romp/restart-audit.jsonl"
    [ -f "$aud" ]
    grep -q '"action": "service-install"' "$aud"
    grep -q '"name": "testsess"' "$aud"
}

@test "install (macOS): a bootstrap that is accepted but never runs fails loudly" {
    # bootstrap ACCEPTED != job RUNNING: launchd can take the definition and still fail the spawn.
    # Exit 0 must require the service to actually report itself.
    unset ROMP_SERVICE_NO_LOAD
    export XDG_STATE_HOME="$TEST_DIR/state"
    local stub="$TEST_DIR/launchctl-stub"
    cat > "$stub" <<'EOF2'
#!/bin/sh
[ "$1" = bootout ] && exit 0
[ "$1" = bootstrap ] && exit 0    # accepted...
exit 5                            # ...but print never finds it running
EOF2
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 1 ]
    [[ "$output" == *"NOT running"* ]]
}

# ── loaded is not running (issue 1600) ─────────────────────────────────────────────────────
# launchctl print succeeds for any LOADED job, a crash-looping one included: the manager's copied node
# aborted at exec, KeepAlive respawned it every throttle interval, `status` said running and install.sh
# trusted that. The job's record names its process (a `pid = N` line) only while one runs, and keeps the
# previous run's exit code; both are read now.
_dying_record() {   # the record of a loaded job that keeps dying: no pid, last exit 134
    printf 'gui/501/com.romp.manager = {\n\tactive count = 0\n\tstate = not running\n\tlast exit code = 134\n\truns = 17\n}\n'
}
_crashloop_loaded_stub() {   # for status: a launchctl whose job is loaded from the start and keeps dying
    cat > "$1" <<'EOF'
#!/bin/sh
[ "$1" = bootout ] && exit 0
[ "$1" = bootstrap ] && exit 0
if [ "$1" = print ]; then
    printf 'gui/501/com.romp.manager = {\n\tactive count = 0\n\tstate = not running\n\tlast exit code = 134\n\truns = 17\n}\n'
    exit 0
fi
exit 0
EOF
    chmod +x "$1"
}
_crashloop_stub() {   # for install: print fails until bootstrap (the drain wait ends at once); the FIRST post-bootstrap print
    # names a pid, the aborting manager alive for its first split second, and every later print says not running, exit 134.
    # Round two of issue 1600: the base declared success on that first pid; the install must re-read a second later and
    # see the SAME pid before it says installed.
    local stub="$1" calls="$2"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$1" >> "$calls"
[ "\$1" = bootout ] && exit 0
[ "\$1" = bootstrap ] && exit 0
if [ "\$1" = print ]; then
    grep -q bootstrap "$calls" || exit 5                                  # not loaded until bootstrapped
    if [ "\$(sed -n '/bootstrap/,\$p' "$calls" | grep -c print)" -eq 1 ]; then      # the first print AFTER the bootstrap: alive
        printf 'gui/501/com.romp.manager = {\n\tactive count = 1\n\tstate = running\n\tpid = 4242\n\tlast exit code = (never exited)\n}\n'
        exit 0
    fi
    printf 'gui/501/com.romp.manager = {\n\tactive count = 0\n\tstate = not running\n\tlast exit code = 134\n\truns = 2\n}\n'
    exit 0
fi
exit 0
EOF
    chmod +x "$stub"
}
_running_stub() {   # a launchctl whose job runs: print names the pid, the same one every time
    cat > "$1" <<'EOF'
#!/bin/sh
[ "$1" = print ] && { printf 'gui/501/com.romp.manager = {\n\tactive count = 1\n\tstate = running\n\tpid = 4242\n\tlast exit code = (never exited)\n}\n'; exit 0; }
exit 0
EOF
    chmod +x "$1"
}

@test "status (macOS): a loaded job that keeps dying is NOT running, and the last exit code is named" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null   # the plist alone
    local stub="$TEST_DIR/launchctl-stub"; _crashloop_loaded_stub "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"installed:"* ]]
    [[ "$output" == *"loaded but not running"* ]]
    [[ "$output" == *"last exit code: 134"* ]]
    # never the bare line install.sh keys its skip-the-reinstall shortcut on
    run grep -qx running <<< "$output"
    [ "$status" -ne 0 ]
}

@test "status (macOS): a job whose record names a live pid is running (a CONTROL: green at the base too, where print's exit alone said running)" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/launchctl-stub"; _running_stub "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [ "$status" -eq 0 ]
    run grep -qx running <<< "$output"
    [ "$status" -eq 0 ]
}

@test "status (macOS): the record's readers survive a print of thousands of lines and capture the exit value whole" {
    # round two, lows 1 and 2: `sed | head -1` under set -e plus pipefail died of SIGPIPE once sed's output passed the pipe
    # buffer (exit 141, no status line), and the value stopped at its first space, so "(signal: 6)" read as "(signal:"
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/launchctl-stub"
    cat > "$stub" <<'EOF'
#!/bin/sh
if [ "$1" = print ]; then
    printf 'gui/501/com.romp.manager = {\n\tstate = not running\n'
    i=0; while [ "$i" -lt 3000 ]; do printf '\tlast exit code = (signal: 6)\n'; i=$((i+1)); done   # loop-ok: a fixed-count stub
    printf '}\n'; exit 0
fi
exit 0
EOF
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"last exit code: (signal: 6)"* ]]
    # …and a record of thousands of pid lines reads as running, not as a broken pipe
    cat > "$stub" <<'EOF'
#!/bin/sh
if [ "$1" = print ]; then
    printf 'gui/501/com.romp.manager = {\n\tstate = running\n'
    i=0; while [ "$i" -lt 3000 ]; do printf '\tpid = 4242\n'; i=$((i+1)); done   # loop-ok: a fixed-count stub
    printf '}\n'; exit 0
fi
exit 0
EOF
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [ "$status" -eq 0 ]
    run grep -qx running <<< "$output"
    [ "$status" -eq 0 ]
}

@test "install (macOS): a job that loads, lives for a moment and then keeps dying fails loudly, naming the last exit code" {
    # round two, medium 1: the first post-bootstrap read saw the aborting manager alive; a second later the pid is gone.
    # The stub's print fails until the bootstrap, so the drain wait before it ends at once (low 3).
    unset ROMP_SERVICE_NO_LOAD
    export XDG_STATE_HOME="$TEST_DIR/state"
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    _crashloop_stub "$stub" "$calls"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 1 ]
    [[ "$output" == *"NOT running"* ]]
    [[ "$output" == *"last exit code: 134"* ]]
    [[ "$output" != *"Installed launchd agent"* ]]
    [ "$(grep -c print "$calls")" -ge 3 ]                     # the drain wait's print, the first live read, the re-read
}

# ── a manager already serving outside the service ─────────────────────────────────────────
# bin/romp-manager refuses to start a second manager on a held control port (exit 1 at once), the throttle keeps the
# respawn out of the verification window, and the install ended saying the dashboard would be dead while the hand-run
# manager was serving it. The verification probes the control port and names that state with its own code.
_dying_loaded_stub() {   # for install: print fails until bootstrap, then a loaded job with no pid and last exit $3 (1 by default)
    local stub="$1" calls="$2" code="${3:-1}"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$1" >> "$calls"
[ "\$1" = bootout ] && exit 0
[ "\$1" = bootstrap ] && exit 0
if [ "\$1" = print ]; then
    grep -q bootstrap "$calls" || exit 5
    printf 'gui/501/com.romp.manager = {\n\tactive count = 0\n\tstate = not running\n\tlast exit code = $code\n\truns = 2\n}\n'
    exit 0
fi
exit 0
EOF
    chmod +x "$stub"
}

@test "install (macOS): a manager already serving on the control port is named when the agent's code is the manager's refusal (1), with the log pointer" {
    unset ROMP_SERVICE_NO_LOAD
    export XDG_STATE_HOME="$TEST_DIR/state"
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    _dying_loaded_stub "$stub" "$calls" 1
    printf '#!/bin/sh\necho "probed :$1" >> "%s"\nexit 0\n' "$TEST_DIR/probe-calls" > "$TEST_DIR/probe-up"; chmod +x "$TEST_DIR/probe-up"
    ROMP_MANAGER_PORT=7499 ROMP_MANAGER_PROBE="$TEST_DIR/probe-up" ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 3 ]
    [[ "$output" == *"ALREADY serving on :7499"* ]]
    [[ "$output" == *"code 1"* ]]
    [[ "$output" == *"most likely outside the login service"* ]]     # the probe cannot tell whose manager answers
    [[ "$output" == *"check $XDG_STATE_HOME/romp/manager.log"* ]]     # the log pointer stays in every branch (round two)
    [[ "$output" != *"dashboard"* ]]                                   # the control port proves a manager, not the dashboard
    grep -q "probed :7499" "$TEST_DIR/probe-calls"                     # the port the manager would use, not a default
    # …and with nothing answering the port, the plain NOT running verdict and exit 1 as before
    printf '#!/bin/sh\nexit 1\n' > "$TEST_DIR/probe-down"; chmod +x "$TEST_DIR/probe-down"
    rm -f "$calls"
    ROMP_MANAGER_PROBE="$TEST_DIR/probe-down" ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 1 ]
    [[ "$output" == *"NOT running"* ]]
    [[ "$output" != *"ALREADY serving"* ]]
}

@test "install (macOS): an agent that died of its own cause (134) beside a manager answering is reported as both facts, not as the held port" {
    # round two of the install-wording fix: the branch was gated on the probe alone, so issue 1600's own shape (the node copy
    # aborting at exec) read as a held port once the user had worked around it with a hand-run romp up
    unset ROMP_SERVICE_NO_LOAD
    export XDG_STATE_HOME="$TEST_DIR/state"
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    _dying_loaded_stub "$stub" "$calls" 134
    printf '#!/bin/sh\nexit 0\n' > "$TEST_DIR/probe-up"; chmod +x "$TEST_DIR/probe-up"
    ROMP_MANAGER_PORT=7499 ROMP_MANAGER_PROBE="$TEST_DIR/probe-up" ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 1 ]
    [[ "$output" == *"NOT running (last exit code: 134)"* ]]
    [[ "$output" == *"check $XDG_STATE_HOME/romp/manager.log"* ]]
    [[ "$output" == *"A manager is also serving on :7499"* ]]
    [[ "$output" == *"not why it died"* ]]
    [[ "$output" != *"ALREADY serving"* ]]
}

@test "install (macOS): the probe asks the port service.env gives the agent's manager (last assignment, quotes off), not the environment's default" {
    unset ROMP_SERVICE_NO_LOAD ROMP_MANAGER_PORT
    export XDG_STATE_HOME="$TEST_DIR/state"
    mkdir -p "$HOME/.config/romp"
    printf 'ROMP_MANAGER_PORT=7601\nROMP_MANAGER_PORT="7602"\n' > "$HOME/.config/romp/service.env"
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    _dying_loaded_stub "$stub" "$calls" 1
    printf '#!/bin/sh\necho "probed :$1" >> "%s"\nexit 0\n' "$TEST_DIR/probe-calls" > "$TEST_DIR/probe-up"; chmod +x "$TEST_DIR/probe-up"
    ROMP_MANAGER_PROBE="$TEST_DIR/probe-up" ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 3 ]
    [[ "$output" == *"ALREADY serving on :7602"* ]]
    grep -q "probed :7602" "$TEST_DIR/probe-calls"
    ! grep -q "probed :7432" "$TEST_DIR/probe-calls"
}

@test "both units bake ROMP_SUPERVISED=1 — the manager's stale-self refresh needs a respawning supervisor" {
    # The manager may EXIT on a refresh when its own binary changed (the fresh supervisor respawn IS
    # the refresh) — but only when something WILL respawn it. KeepAlive/Restart=always is that
    # something; this env var is how the manager knows it's running under one (2026-07-24).
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    grep -q "<key>ROMP_SUPERVISED</key><string>1</string>" "$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    grep -q "^Environment=ROMP_SUPERVISED=1$" "$ROMP_SYSTEMD_DIR/romp-manager.service"
}

# ── the instance env: which romp does this service supervise? ──────────────────────────────
# A second OS user on one machine (a kernel handed to another person) shares the PORT space,
# so their manager/kernel/bus must be renumbered. The installing shell had the overrides; the
# unit did not, so the supervised manager came up on the defaults, its control port collided
# with the primary user's, and the service died at login while every foreground `romp` command
# still reported the configured port.

@test "install bakes the renumbered ports into the unit (Linux) and the plist (macOS)" {
    export ROMP_SERVE_PORT=29856 ROMP_POSTAL_PORT=25303 ROMP_MANAGER_PORT=7433
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    grep -q "^Environment=ROMP_SERVE_PORT=29856$"   "$unit"
    grep -q "^Environment=ROMP_POSTAL_PORT=25303$"  "$unit"
    grep -q "^Environment=ROMP_MANAGER_PORT=7433$"  "$unit"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    grep -q "<key>ROMP_SERVE_PORT</key><string>29856</string>"  "$plist"
    grep -q "<key>ROMP_POSTAL_PORT</key><string>25303</string>" "$plist"
    grep -q "<key>ROMP_MANAGER_PORT</key><string>7433</string>" "$plist"
}

@test "install bakes ROMP_KERNEL_PORT — the spelling the docs tell people to set" {
    # docs/reference.md names ROMP_KERNEL_PORT and not ROMP_SERVE_PORT, so someone renumbering a
    # second instance by the book sets only this one. It used to reach no unit at all: the
    # supervised manager came up on the default and the new kernel bound the primary's port.
    export ROMP_KERNEL_PORT=29856
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    grep -q "^Environment=ROMP_KERNEL_PORT=29856$" "$ROMP_SYSTEMD_DIR/romp-manager.service"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    grep -q "<key>ROMP_KERNEL_PORT</key><string>29856</string>" "$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
}

@test "install bakes the rest of the profile: state root, Claude config dir" {
    # The same set romp-manager's specEnv hands an aux kernel — a profile that is only half
    # carried is the silent-divergence bug, not a smaller version of it.
    export ROMP_STATE_DIR="$TEST_DIR/alt-state" CLAUDE_CONFIG_DIR="$TEST_DIR/alt-claude"
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    grep -q "^Environment=ROMP_STATE_DIR=$TEST_DIR/alt-state$"      "$unit"
    grep -q "^Environment=CLAUDE_CONFIG_DIR=$TEST_DIR/alt-claude$"  "$unit"
}

@test "a default install writes NO instance env — unchanged for everyone not doing this" {
    # setup() cleared the set, so this is the single-user machine's install.
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    run grep -q "ROMP_SERVE_PORT\|ROMP_KERNEL_PORT\|ROMP_POSTAL_PORT\|ROMP_MANAGER_PORT\|ROMP_STATE_DIR\|CLAUDE_CONFIG_DIR" "$unit"
    [ "$status" -ne 0 ]
    # ...and the file is still well-formed around the seam: the always-present
    # (optional, dash-prefixed) EnvironmentFile line, a blank line, then [Install].
    grep -q "^Environment=ROMP_SUPERVISED=1$" "$unit"
    grep -q "^EnvironmentFile=-" "$unit"
    grep -q "^\[Install\]$" "$unit"
    [ -z "$(sed -n '/^EnvironmentFile=-/{n;p;}' "$unit")" ]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    run grep -q "ROMP_SERVE_PORT\|ROMP_STATE_DIR\|CLAUDE_CONFIG_DIR" "$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    [ "$status" -ne 0 ]        # (a bare `! cmd` that is not the test's last statement can never fail it)
}

@test "the rendered unit and plist stay well-formed with the instance env present" {
    export ROMP_SERVE_PORT=29856 ROMP_MANAGER_PORT=7433
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    # every Environment= line sits in [Service], i.e. before [Install]
    local envlast instline
    envlast="$(grep -n '^Environment=' "$unit" | tail -1 | cut -d: -f1)"
    instline="$(grep -n '^\[Install\]$' "$unit" | cut -d: -f1)"
    [ "$envlast" -lt "$instline" ]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    # the pairs land INSIDE EnvironmentVariables, and the plist still parses
    if command -v plutil >/dev/null 2>&1; then plutil -lint "$plist" >/dev/null; fi
    local dictline portline closeline
    dictline="$(grep -n '<key>EnvironmentVariables</key>' "$plist" | cut -d: -f1)"
    portline="$(grep -n '<key>ROMP_SERVE_PORT</key>' "$plist" | cut -d: -f1)"
    closeline="$(grep -n '<key>RunAtLoad</key>' "$plist" | cut -d: -f1)"
    [ "$dictline" -lt "$portline" ]
    [ "$portline" -lt "$closeline" ]
}

@test "install (Linux): unit loads optional extra service env (service.env)" {
    # EnvironmentFile=- (leading dash): missing file is a no-op, so a default
    # install behaves exactly as before anyone creates service.env.
    XDG_CONFIG_HOME="$HOME/.config" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    grep -Fq "EnvironmentFile=-$HOME/.config/romp/service.env" "$ROMP_SYSTEMD_DIR/romp-manager.service"
}

@test "install carries a non-default env-file path into the unit (quoted) and the plist (escaped); a default install does not" {
    # kernel/credentials.py resolves the env file from the SERVICE's environment, which never sees the
    # installing shell's ROMP_SERVICE_ENV_FILE, so a non-default path baked into EnvironmentFile= alone
    # was read by systemd and not by the kernel's own read of the same file (its boot check today). The
    # resolved path rides the unit and the plist whenever it is not the default.
    # every character class systemd or XML would mangle: a space (word-split), a double quote and a
    # backslash (quoting), a percent sign (specifier expansion), an ampersand (XML)
    local odd='alt "q" \b %z & dir'
    export ROMP_SERVICE_ENV_FILE="$TEST_DIR/$odd/service.env"
    mkdir -p "$TEST_DIR/$odd"
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    local exp_env='Environment="ROMP_SERVICE_ENV_FILE='"$TEST_DIR"'/alt \"q\" \\b %%z & dir/service.env"'   # quoted, escaped, % doubled
    grep -Fq "$exp_env" "$unit"
    local exp_file='EnvironmentFile=-'"$TEST_DIR"'/alt "q" \b %%z & dir/service.env'                         # % doubled here too
    grep -Fq "$exp_file" "$unit"
    [ -z "$(sed -n '/^EnvironmentFile=-/{n;p;}' "$unit")" ]                                     # the seam is unchanged
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    local exp_plist='<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/alt &quot;q&quot; \b %z &amp; dir/service.env</string>'
    grep -Fq "$exp_plist" "$plist"
    command -v python3 >/dev/null 2>&1 && python3 -c "import plistlib,sys; plistlib.load(open(sys.argv[1],'rb'))" "$plist"
    unset ROMP_SERVICE_ENV_FILE
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    run grep -q "ROMP_SERVICE_ENV_FILE" "$unit"
    [ "$status" -ne 0 ]        # (a bare `! cmd` that is not the test's last statement can never fail it)
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    run grep -q "ROMP_SERVICE_ENV_FILE" "$plist"
    [ "$status" -ne 0 ]
}

@test "install from a shell that set only the alias ROMP_SERVICE_ENV carries the path as ROMP_SERVICE_ENV_FILE; the primary wins when both are set" {
    # kernel/credentials.py resolves the env file from ROMP_SERVICE_ENV_FILE, else its alias ROMP_SERVICE_ENV
    # (service_env_path), so a shell that set only the alias and the kernel read the same file. The installer
    # read the primary alone: that install wrote no override line and the kernel kept the default path (review
    # find, 2026-09-06). Both names now resolve here as they do there, and the line written is always the
    # primary, which bin/romp-node-launch and the kernel read.
    export ROMP_SERVICE_ENV="$TEST_DIR/alias dir/service.env"
    mkdir -p "$TEST_DIR/alias dir"
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    grep -Fq 'Environment="ROMP_SERVICE_ENV_FILE='"$TEST_DIR"'/alias dir/service.env"' "$unit"
    grep -Fq 'EnvironmentFile=-'"$TEST_DIR"'/alias dir/service.env' "$unit"
    run grep -q 'ROMP_SERVICE_ENV=' "$unit"
    [ "$status" -ne 0 ]                     # the primary name is written, never the alias
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    grep -Fq '<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/alias dir/service.env</string>' "$plist"
    run grep -q 'ROMP_SERVICE_ENV<' "$plist"
    [ "$status" -ne 0 ]
    # both set: the primary wins, the order kernel/credentials.py reads them in
    export ROMP_SERVICE_ENV_FILE="$TEST_DIR/primary/service.env"
    mkdir -p "$TEST_DIR/primary"
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    grep -Fq 'Environment="ROMP_SERVICE_ENV_FILE='"$TEST_DIR"'/primary/service.env"' "$unit"
    run grep -Fq "alias dir" "$unit"
    [ "$status" -ne 0 ]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    grep -Fq '<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/primary/service.env</string>' "$plist"
    run grep -Fq "alias dir" "$plist"
    [ "$status" -ne 0 ]
}

# ─── the clean-shell install: `env -i HOME=... PATH=... romp-service install` ──────────────────
# write_unit bakes every set instance variable and PATH, so a re-install that must not carry a session's ROMP_* ports
# into the unit runs from a clean shell, and a clean shell has no XDG_RUNTIME_DIR or DBUS_SESSION_BUS_ADDRESS, which
# systemctl --user needs to find the user manager: the install wrote the unit and died at daemon-reload ("Failed to
# connect to bus: No medium found"), systemd kept the loaded definition, and the manager's next respawn ran without
# the new Environment line while the file on disk read as installed (review find, 2026-09-16). The install now derives
# both from the uid when absent, reports a reload that fails in its own words, and shows the LOADED unit's Environment.
# The fake systemctl sits on PATH, the only road a clean shell has to it, and records each call's argv with the two
# variables as it saw them; a fake loginctl beside it keeps the best-effort enable-linger off the box's own logind.
# NEVER the real systemctl here: the recipe would act on the box's own manager.
_clean_shell_bin() {   # $1 what `show -p Environment` prints; $2 non-empty: daemon-reload fails as it does without a bus;
                       # $3 what `show -p NeedDaemonReload --value` prints (default no). `show` answers per PROPERTY (round 2 of
                       # the review, 2026-09-18): the install arm reads systemd's flag and the loaded fragment after its reload,
                       # as the rewrite arm does, so a stub answering every show alike would feed the Environment string to both
    local dir="$TEST_DIR/fakebin" calls="$TEST_DIR/systemctl-calls" reload='exit 0' need="${3:-no}"
    [ -z "${2:-}" ] || reload='echo "Failed to connect to bus: No medium found" >&2; exit 1'
    mkdir -p "$dir"
    cat > "$dir/systemctl" <<EOF
#!/bin/sh
echo "\$* | XDG_RUNTIME_DIR=\${XDG_RUNTIME_DIR-unset} DBUS_SESSION_BUS_ADDRESS=\${DBUS_SESSION_BUS_ADDRESS-unset}" >> "$calls"
case "\$2" in
  daemon-reload) $reload ;;
  show) case "\$*" in
          *NeedDaemonReload*) echo "$need" ;;
          *FragmentPath*) echo "$HOME/.config/systemd/user/romp-manager.service" ;;
          *) echo "$1" ;;
        esac ;;
  *) exit 0 ;;
esac
EOF
    printf '#!/bin/sh\necho "loginctl $*" >> "%s"\nexit 0\n' "$calls" > "$dir/loginctl"
    chmod +x "$dir/systemctl" "$dir/loginctl"
    printf '%s' "$dir"
}

@test "install (Linux) from a clean shell (env -i HOME PATH): the bus variables are derived from the uid, daemon-reload precedes the start, the loaded Environment is shown" {
    local fakebin; fakebin="$(_clean_shell_bin 'Environment=PATH=/usr/bin:/bin ROMP_DIR=/opt/romp ROMP_SUPERVISED=1 MALLOC_ARENA_MAX=2')"
    # the recipe as the deploy note gives it, HOME and PATH only (nothing of this suite's environment: no
    # ROMP_SERVICE_NO_LOAD, no ROMP_SYSTEMD_DIR, no ROMP_MANAGER_BIN), but for the platform override and the fake bin
    # first on PATH
    run env -i HOME="$HOME" PATH="$fakebin:$PATH" ROMP_OS_OVERRIDE=Linux "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$HOME/.config/systemd/user/romp-manager.service" calls="$TEST_DIR/systemctl-calls"
    [[ "$output" == *"Installed systemd --user service: $unit"* ]]
    # the LOADED unit's Environment is shown, for the deploy to read against the file
    [[ "$output" == *"Loaded unit (systemctl --user show -p Environment): Environment=PATH=/usr/bin:/bin ROMP_DIR=/opt/romp ROMP_SUPERVISED=1 MALLOC_ARENA_MAX=2"* ]]
    [[ "$output" != *"does not carry"* ]]
    [ -f "$unit" ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    # both variables reached systemctl on every call, derived from the uid at the paths systemd places them
    local uid; uid="$(id -u)"
    grep -qxF -- "--user daemon-reload | XDG_RUNTIME_DIR=/run/user/$uid DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus" "$calls"
    grep -qxF -- "--user enable --now romp-manager.service | XDG_RUNTIME_DIR=/run/user/$uid DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus" "$calls"
    grep -qxF -- "--user show -p Environment romp-manager.service | XDG_RUNTIME_DIR=/run/user/$uid DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus" "$calls"
    # the reload precedes the start: a start under an unreloaded definition is the old unit
    local rl st
    rl="$(grep -n -- '^--user daemon-reload ' "$calls" | head -1 | cut -d: -f1)"
    st="$(grep -n -- '^--user enable --now romp-manager.service ' "$calls" | head -1 | cut -d: -f1)"
    [ -n "$rl" ]
    [ -n "$st" ]
    [ "$rl" -lt "$st" ]
    # the enable-linger went to the fake loginctl, never the box's logind
    grep -q '^loginctl enable-linger ' "$calls"
    # neither variable is baked into the unit, and no instance variable is: the clean shell's purpose is kept
    run grep -q 'XDG_RUNTIME_DIR\|DBUS_SESSION_BUS_ADDRESS\|ROMP_MANAGER_PORT\|ROMP_SERVE_PORT' "$unit"
    [ "$status" -ne 0 ]
    run grep -q 'unset' "$calls"
    [ "$status" -ne 0 ]
}

@test "install (Linux): a shell that has the bus variables keeps its own values; only an absent one is derived" {
    local fakebin; fakebin="$(_clean_shell_bin 'Environment=MALLOC_ARENA_MAX=2')"
    run env -i HOME="$HOME" PATH="$fakebin:$PATH" XDG_RUNTIME_DIR=/nonexistent/rt ROMP_OS_OVERRIDE=Linux "$SVC" install
    [ "$status" -eq 0 ]
    grep -qxF -- '--user daemon-reload | XDG_RUNTIME_DIR=/nonexistent/rt DBUS_SESSION_BUS_ADDRESS=unix:path=/nonexistent/rt/bus' "$TEST_DIR/systemctl-calls"
    rm -f "$TEST_DIR/systemctl-calls"
    run env -i HOME="$HOME" PATH="$fakebin:$PATH" DBUS_SESSION_BUS_ADDRESS=unix:path=/nonexistent/bus ROMP_OS_OVERRIDE=Linux "$SVC" install
    [ "$status" -eq 0 ]
    grep -qxF -- "--user daemon-reload | XDG_RUNTIME_DIR=/run/user/$(id -u) DBUS_SESSION_BUS_ADDRESS=unix:path=/nonexistent/bus" "$TEST_DIR/systemctl-calls"
}

@test "install (Linux): a daemon-reload that fails is loud in the install's own words, and nothing is started" {
    # before this, set -e ended the install on systemctl's line alone: no romp-service line said the unit on disk was
    # not the loaded one, and the file diff the deploy checks read as installed
    local fakebin; fakebin="$(_clean_shell_bin 'Environment=PATH=/usr/bin' reload-fails)"
    run env -i HOME="$HOME" PATH="$fakebin:$PATH" ROMP_OS_OVERRIDE=Linux "$SVC" install
    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to connect to bus: No medium found"* ]]     # systemctl's own reason stays visible
    [[ "$output" == *"systemd did NOT reload it"* ]]
    [[ "$output" == *"next respawn runs under it"* ]]
    [[ "$output" != *"Installed systemd --user service"* ]]
    [ -f "$HOME/.config/systemd/user/romp-manager.service" ]              # the file is written; the message says so
    run grep -q -- 'enable --now' "$TEST_DIR/systemctl-calls"
    [ "$status" -ne 0 ]
}

@test "install (Linux): after the reload the install arm reads systemd's flag and the loaded fragment, as the rewrite arm does; an older definition is named from the flag, never from the merged Environment" {
    # Round 2 of the review (2026-09-18): the install arm grepped the loaded Environment for the allocator line, which a
    # drop-in supplying that line satisfies over an entirely stale fragment (false green on a box with such a drop-in),
    # while the rewrite arm read NeedDaemonReload; one file now gives one answer to "did systemd pick this up". The
    # loaded Environment is still shown; the verdict comes from the flag.
    local fakebin; fakebin="$(_clean_shell_bin 'Environment=PATH=/usr/bin:/bin ROMP_DIR=/opt/romp ROMP_SUPERVISED=1 MALLOC_ARENA_MAX=2' '' yes)"
    run env -i HOME="$HOME" PATH="$fakebin:$PATH" ROMP_OS_OVERRIDE=Linux "$SVC" install
    [ "$status" -eq 0 ]
    [[ "$output" == *"Loaded unit (systemctl --user show -p Environment): Environment=PATH=/usr/bin:/bin ROMP_DIR=/opt/romp ROMP_SUPERVISED=1 MALLOC_ARENA_MAX=2"* ]]
    [[ "$output" == *"NeedDaemonReload=yes"* ]]                      # the allocator line is in the merged Environment; the flag says stale
    [[ "$output" == *"kept an older definition"* ]]
    [[ "$output" != *"does not carry"* ]]
    grep -q -- '--user show -p NeedDaemonReload --value romp-manager.service |' "$TEST_DIR/systemctl-calls"
    grep -q -- '--user show -p FragmentPath --value romp-manager.service |' "$TEST_DIR/systemctl-calls"
    # a loaded Environment WITHOUT the allocator line and a clean flag is not named stale: the flag is the authority
    rm -f "$TEST_DIR/systemctl-calls"
    fakebin="$(_clean_shell_bin 'Environment=PATH=/usr/bin:/bin ROMP_DIR=/opt/romp ROMP_SUPERVISED=1')"
    run env -i HOME="$HOME" PATH="$fakebin:$PATH" ROMP_OS_OVERRIDE=Linux "$SVC" install
    [ "$status" -eq 0 ]
    [[ "$output" != *"kept an older definition"* ]]
    [[ "$output" != *"does not carry"* ]]
}

# ─── rewrite: the unit or the plist, its own identity kept, and no restart ──────────────────
# The box admin's hazard review of the pull-in (2026-09-16): install.sh runs this while the manager is up, where an
# `install` would boot the manager out (macOS) and where skipping the step, as install.sh did until 2026-09-18, left
# the unit on disk at the previous release's. Linux writes and reloads, macOS writes; neither starts, stops, enables
# or loads anything, and the file lands by rename (no scratch file stays, no truncated unit at a reload). Round 1 of
# the review (2026-09-18): the rewrite runs on every deploy from whatever ran it (the kernel's detached update, a
# session's shell), so it keeps the file's own identity, ExecStart, ROMP_DIR, PATH and the instance Environment
# block, refreshes the release's lines, and refuses when a value this environment carries differs from the file's.
# The previous release's file, for the cases below, is the current install's with the allocator line removed and a
# marker line added, so the old bytes can be told from the new ones through a hard link.
_old_unit() {   # $1 the unit path: install the current unit, then age it into the previous release's
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -v '^Environment=MALLOC_ARENA_MAX=' "$1" > "$1.old" && mv -f "$1.old" "$1"
    printf '# previous release\n' >> "$1"
}

@test "rewrite (Linux): writes the release's unit by rename and asks systemd to reload, nothing else; the one line names the manager's restart" {
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"
    ln "$unit" "$unit.pre"                                              # the old bytes, under a second name
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    local out="$output"
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    grep -q "^ExecStart=$ROMP_MANAGER_BIN up$" "$unit"
    [ ! -e "$unit.tmp" ]
    # landed by RENAME: the hard link still holds the previous release's bytes (a truncating write would have
    # rewritten them in place), and the unit is the new file
    grep -qx '# previous release' "$unit.pre"
    run grep -x '# previous release' "$unit"
    [ "$status" -ne 0 ]
    # systemd was asked to reload and read back, and for nothing else: no enable, start, stop, restart or kill
    grep -qx -- '--user daemon-reload' "$TEST_DIR/systemctl-calls"
    run grep -E -- 'enable|start|stop|restart|kill' "$TEST_DIR/systemctl-calls"
    [ "$status" -ne 0 ]
    [[ "$out" == *"keeps its old unit until its next restart:  systemctl --user restart romp-manager"* ]]
    [ "$(printf '%s\n' "$out" | grep -c 'systemctl --user restart romp-manager')" -eq 1 ]   # the instruction once
    [[ "$out" != *"kept an older definition"* ]]                                            # the read-back was clean
    # the rewrite journals itself (who ran the deploy) under this state root, the row the kernel's walk skips
    grep -q '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
}

@test "rewrite (Linux): a daemon-reload that fails is loud and exit 1; the unit is on disk and the message says so" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/systemctl-stub"
    printf '#!/bin/sh\necho "Failed to connect to bus: No medium found" >&2\nexit 1\n' > "$stub"
    chmod +x "$stub"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 1 ]
    [[ "$output" == *"Failed to connect to bus: No medium found"* ]]     # systemctl's own reason stays visible
    [[ "$output" == *"systemd did NOT reload it"* ]]
    [[ "$output" == *"next respawn runs under it"* ]]
    [[ "$output" != *"Rewrote the login service unit"* ]]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$ROMP_SYSTEMD_DIR/romp-manager.service"
}

@test "rewrite (Linux): after the reload the authoritative flag is read; NeedDaemonReload=yes is said on stderr at exit 0, an unreadable flag too" {
    # Round 1 of the review (2026-09-18): the install arm reads the loaded Environment back and greps it for the
    # allocator line, which a drop-in supplying that line satisfies over an entirely stale fragment (the drop-in boxes
    # are the population this road exists for). The rewrite arm reads systemd's own answer instead: NeedDaemonReload
    # is yes when the file on disk is newer than the loaded definition, the state a reload that returned 0 and kept
    # the old definition leaves. An advisory, exit 0, as the install arm's: install.sh gates on the exit code, and a
    # box whose probe alone is unreadable must still deploy.
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/systemctl-stub"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$*" >> "$TEST_DIR/systemctl-calls"
case "\$*" in *NeedDaemonReload*) echo yes ;; esac
exit 0
EOF
    chmod +x "$stub"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"Rewrote the login service unit"* ]]
    [[ "$output" == *"NeedDaemonReload=yes"* ]]
    [[ "$output" == *"kept an older definition"* ]]
    grep -qx -- '--user show -p NeedDaemonReload --value romp-manager.service' "$TEST_DIR/systemctl-calls"
    # a probe that prints nothing is said too, never read as clean
    printf '#!/bin/sh\nexit 0\n' > "$stub"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"NeedDaemonReload could not be read"* ]]
}

@test "rewrite with no service installed exits 3 and writes nothing, not even its audit row: a unit nothing enabled would read as installed" {
    unset ROMP_SERVICE_NO_LOAD
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 3 ]
    [[ "$output" == *"no login service is installed"* ]]
    [ ! -e "$ROMP_SYSTEMD_DIR/romp-manager.service" ]
    [ ! -e "$TEST_DIR/systemctl-calls" ]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 3 ]
    [[ "$output" == *"no login agent is installed"* ]]
    [ ! -e "$ROMP_LAUNCHD_DIR/com.romp.manager.plist" ]
    # round 1 of the review (2026-09-18): the audit row is written after the installed check, so a run that wrote
    # nothing journals nothing
    [ ! -e "$XDG_STATE_HOME/romp/restart-audit.jsonl" ]
}

@test "rewrite (Linux): keeps the unit's own PATH and instance lines: the caller's environment adds none and drops none" {
    # Round 1 of the review (2026-09-18). The rewrite runs from whatever ran install.sh: the kernel's detached update
    # carries the manager's ports for every kernel and a profile's state root and Claude config dir, a session's
    # shell carries the kernel's; the base's install-time contract (bake what the installing shell sets) would have
    # written those into the shared login unit on every deploy. A value the unit does not carry is not added; a line
    # the unit carries is kept when the environment says nothing about it.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"
    local pathline; pathline="$(grep '^Environment=PATH=' "$unit")"
    mkdir -p "$TEST_DIR/otherbin"
    local stub; stub="$(_systemctl_stub active)"
    PATH="$TEST_DIR/otherbin:$PATH" ROMP_SERVE_PORT=31855 ROMP_KERNEL_PORT=31855 ROMP_POSTAL_PORT=31900 \
        ROMP_MANAGER_PORT=31856 ROMP_STATE_DIR="$TEST_DIR/aux" CLAUDE_CONFIG_DIR="$TEST_DIR/aux-claude" \
        ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"                  # the release's line landed
    grep -qxF -- "$pathline" "$unit"                                    # the unit's PATH, not the caller's
    run grep -E '^Environment=(ROMP_SERVE_PORT|ROMP_KERNEL_PORT|ROMP_POSTAL_PORT|ROMP_MANAGER_PORT|ROMP_STATE_DIR|CLAUDE_CONFIG_DIR)=' "$unit"
    [ "$status" -ne 0 ]
    run grep -F "$TEST_DIR/otherbin" "$unit"
    [ "$status" -ne 0 ]
    # the other direction: a renumbered install's lines survive a rewrite from a shell without the exports
    ROMP_SERVE_PORT=29866 ROMP_KERNEL_PORT=29866 ROMP_MANAGER_PORT=7433 ROMP_STATE_DIR="$TEST_DIR/second" \
        ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -q '^Environment=ROMP_KERNEL_PORT=29866$' "$unit"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '^Environment=ROMP_SERVE_PORT=29866$' "$unit"
    grep -q '^Environment=ROMP_KERNEL_PORT=29866$' "$unit"
    grep -q '^Environment=ROMP_MANAGER_PORT=7433$' "$unit"
    grep -qF "Environment=ROMP_STATE_DIR=$TEST_DIR/second" "$unit"
}

@test "rewrite (Linux): refuses, exit 5 and nothing written or reloaded, when a value this environment carries differs from the unit's line" {
    # Round 1 of the review (2026-09-18): an EFFECTIVE mismatch, a line the unit carries and a different value in the
    # environment, is the one state that is refused, naming both values and the deliberate way through; raw absence
    # (every kernel's environment sets the ports, most units carry none) is not, or nearly every deploy would fail.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    ROMP_SERVE_PORT=29866 ROMP_KERNEL_PORT=29866 ROMP_MANAGER_PORT=7433 \
        ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$unit" "$unit.copy"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SERVE_PORT=29866 ROMP_KERNEL_PORT=31855 ROMP_MANAGER_PORT=7433 \
        ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]                                                  # its own code (round 2): not a failed reload's 1
    [[ "$output" == *"ROMP_KERNEL_PORT"* ]]
    [[ "$output" == *"29866"* ]]
    [[ "$output" == *"31855"* ]]
    [[ "$output" == *"romp-service install"* ]]
    # the class is said: a value THIS ENVIRONMENT carries is fixed by a shell without it, not by another clone
    [[ "$output" == *"retry from a shell that does not set it"* ]]
    [[ "$output" != *"not the installed one"* ]]
    [[ "$output" != *"ROMP_SERVE_PORT"* ]]                              # only the differing value is named
    [[ "$output" != *"Rewrote"* ]]
    cmp -s "$unit" "$unit.copy"                                          # untouched
    [ ! -e "$unit.tmp" ]
    [ ! -e "$TEST_DIR/systemctl-calls" ]                                 # no reload of a unit that did not change
    run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
    [ "$status" -ne 0 ]                                                  # nothing rewritten, nothing journaled
}

@test "rewrite (Linux): refuses when the unit's ExecStart names another clone, naming both and the install that relocates" {
    # Round 1 of the review (2026-09-18): a deploy run from a clone that is not the installed one (a review worktree,
    # a second checkout) must not re-point the login service at itself, nor refresh another clone's unit from its own
    # template; the relocation is `romp-service install` from the clone that should own the service.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    mkdir -p "$TEST_DIR/other/bin"
    ROMP_MANAGER_BIN="$TEST_DIR/other/bin/romp-manager" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$unit" "$unit.copy"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite   # ROMP_MANAGER_BIN is the suite's, another path
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart"* ]]
    [[ "$output" == *"$TEST_DIR/other/bin/romp-manager"* ]]
    [[ "$output" == *"$ROMP_MANAGER_BIN"* ]]
    [[ "$output" == *"romp-service install"* ]]
    # the class is said: the CLONE is not the installed one; no retry from another shell is offered for it
    [[ "$output" == *"not the installed one"* ]]
    [[ "$output" != *"retry from a shell"* ]]
    cmp -s "$unit" "$unit.copy"
    [ ! -e "$TEST_DIR/systemctl-calls" ]
    # the same clone reached through a symlinked directory is the same clone, not a refusal
    ln -s "$TEST_DIR/other" "$TEST_DIR/other-link"
    ROMP_MANAGER_BIN="$TEST_DIR/other-link/bin/romp-manager" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q "^ExecStart=$TEST_DIR/other/bin/romp-manager up$" "$unit"   # the unit's own path, kept
}

@test "rewrite (Linux): a line added to the unit by hand is dropped, and a drop-in is left byte for byte" {
    # The documented contract (a line of your own belongs in service.env or a drop-in), pinned on the rewrite road
    # since it runs on every deploy (round 1 of the review, 2026-09-18); the base's install road carries the same.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"
    printf 'Environment=ADMIN_LOCAL_KNOB=1\n' >> "$unit"
    mkdir -p "$unit.d"
    printf '[Service]\nEnvironment=FROM_DROPIN=1\n' > "$unit.d/local.conf"
    cp "$unit.d/local.conf" "$TEST_DIR/local.conf.copy"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    run grep ADMIN_LOCAL_KNOB "$unit"
    [ "$status" -ne 0 ]
    cmp -s "$unit.d/local.conf" "$TEST_DIR/local.conf.copy"
}

@test "rewrite (Linux): a unit reached through a symlink becomes a regular file at that path, and the line says so" {
    # Round 1 of the review (2026-09-18): the rename replaces the link, not the file behind it (writing through the
    # link would put romp's generated unit into the administrator's own checkout, the base's behaviour); the line
    # names the link that was replaced, so later edits of the target being invisible to systemd is not a mystery.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"
    mkdir -p "$TEST_DIR/dotfiles"
    mv "$unit" "$TEST_DIR/dotfiles/romp-manager.service"
    ln -s "$TEST_DIR/dotfiles/romp-manager.service" "$unit"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ ! -L "$unit" ]
    [ -f "$unit" ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    grep -qx '# previous release' "$TEST_DIR/dotfiles/romp-manager.service"    # the target is not written through
    [[ "$output" == *"was a symlink"* ]]
    [[ "$output" == *"$TEST_DIR/dotfiles/romp-manager.service"* ]]
}

@test "rewrite (macOS): writes the plist by rename and calls launchctl not at all; the node copy is refreshed; the line says when launchd reads it" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    # the previous release's plist: a hand-added entry in the dict and a marker after the document element
    awk '/<key>ROMP_SUPERVISED<\/key>/{print; print "    <key>ADMIN_LOCAL_KNOB</key><string>1</string>"; next}1' "$plist" > "$plist.old"
    mv -f "$plist.old" "$plist"
    printf '<!-- previous release -->\n' >> "$plist"
    ln "$plist" "$plist.pre"
    rm -f "$XDG_STATE_HOME/romp/romp-node"
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    printf '#!/bin/sh\necho "$1" >> "%s"\nexit 0\n' "$calls" > "$stub"
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q "<string>$ROMP_MANAGER_BIN</string>" "$plist"
    grep -q '<key>KeepAlive</key><true/>' "$plist"
    [ ! -e "$plist.tmp" ]
    [ ! -e "$calls" ]                                                    # no bootout, bootstrap, kickstart or print
    [[ "$output" == *"until launchd next loads the agent:  romp-service install (or the next login)"* ]]
    grep -qx -- '<!-- previous release -->' "$plist.pre"                 # landed by rename: the link holds the old bytes
    run grep -c 'previous release' "$plist"
    [ "$status" -ne 0 ]
    run grep -c ADMIN_LOCAL_KNOB "$plist"                                # a hand-added entry is dropped, as documented
    [ "$status" -ne 0 ]
    [ -x "$XDG_STATE_HOME/romp/romp-node" ]                              # the launcher's node copy is refreshed
}

@test "rewrite (macOS): keeps the plist's own instance entries, refuses on a differing value, and names a replaced symlink" {
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite                            # no export in this shell: the entry is kept
    [ "$status" -eq 0 ]
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
    ROMP_SERVE_PORT=31855 ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite      # a port the plist does not carry: not added
    [ "$status" -eq 0 ]
    run grep -c ROMP_SERVE_PORT "$plist"
    [ "$status" -ne 0 ]
    cp "$plist" "$plist.copy"
    ROMP_KERNEL_PORT=31855 ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite     # a differing value: refused
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_KERNEL_PORT"* ]]
    [[ "$output" == *"29866"* ]]
    [[ "$output" == *"31855"* ]]
    cmp -s "$plist" "$plist.copy"
    mkdir -p "$TEST_DIR/dotfiles"
    mv "$plist" "$TEST_DIR/dotfiles/com.romp.manager.plist"
    ln -s "$TEST_DIR/dotfiles/com.romp.manager.plist" "$plist"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ ! -L "$plist" ]
    [[ "$output" == *"was a symlink"* ]]
    cmp -s "$TEST_DIR/dotfiles/com.romp.manager.plist" "$plist.copy"     # the target is not written through
}

# ─── round 2 of the review (2026-09-18): what absence means, the check mode, the state root, the child on the install road ──

@test "rewrite --check (Linux): the identity checks alone; exit 0 with nothing written, reloaded or journaled, exit 5 on a disagreement, exit 3 with none installed, exit 2 on an unknown flag" {
    # The kernel's update runs this BEFORE it fetches the release and moves the checkout: a deploy the rewrite would
    # refuse then moves nothing first (the round's high: the refusal sat after the fast-forward)
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 3 ]
    [[ "$output" == *"no login service is installed"* ]]
    _old_unit "$unit"
    cp "$unit" "$unit.copy"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"agree"* ]]
    [[ "$output" == *"--check"* ]]
    # the file's noun is the road's (round 3, extra7-5): the refusal and the --check line name the same thing
    [[ "$output" == *"The login service unit on disk and this environment agree"* ]]
    cmp -s "$unit" "$unit.copy"                                          # the previous release's bytes, untouched
    [ ! -e "$unit.tmp" ]
    [ ! -e "$TEST_DIR/systemctl-calls" ]                                 # no reload
    run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
    [ "$status" -ne 0 ]                                                  # no row (the install's own row is there)
    ROMP_KERNEL_PORT=31855 ROMP_SERVE_PORT=31855 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    ROMP_KERNEL_PORT=29866 ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_KERNEL_PORT"* ]]
    [[ "$output" == *"nothing was rewritten"* ]]
    [[ "$output" == *"the login service unit on disk and this environment disagree"* ]]
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --bogus
    [ "$status" -eq 2 ]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check                   # the plist road: exit 3 with none, 0 with one
    [ "$status" -eq 3 ]
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    cp "$plist" "$plist.copy"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"The login agent on disk and this environment agree"* ]]
    [[ "$output" != *"login service"* ]]
    cmp -s "$plist" "$plist.copy"
    ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]                                                  # absent in the plist: not a disagreement
    ROMP_SERVICE_ENV="$TEST_DIR/elsewhere/service.env" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"the login agent on disk and this environment disagree"* ]]
    cmp -s "$plist" "$plist.copy"
}

@test "rewrite (Linux): a unit installed with the service.env path set (the alias) keeps its EnvironmentFile line and the override on a rewrite from a shell setting neither name; an explicitly set differing value refuses, naming both" {
    # Round 2 (departure c of round 1's body, ruled: the refusal on absence was wrong). Round 1 compared the unit's line
    # against the DEFAULT the resolver computes in the rewriting shell, so a renumbered install (a non-default
    # service.env path) refused every deploy from a plain shell, install.sh's and the kernel's update child's alike
    # (ROMP_SERVICE_ENV_FILE is not in the child's scrub list, so a pre-override-era unit refused from it too). The
    # compare fires only on a value this environment SET; otherwise the unit's own path is kept, override line included.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    ROMP_SERVICE_ENV="$TEST_DIR/custom/service.env" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qF "EnvironmentFile=-$TEST_DIR/custom/service.env" "$unit"
    grep -qF 'Environment="ROMP_SERVICE_ENV_FILE='"$TEST_DIR"'/custom/service.env"' "$unit"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite   # setup unset both names: the plain shell
    [ "$status" -eq 0 ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    grep -qF "EnvironmentFile=-$TEST_DIR/custom/service.env" "$unit"                            # kept
    grep -qF 'Environment="ROMP_SERVICE_ENV_FILE='"$TEST_DIR"'/custom/service.env"' "$unit"   # and the override with it
    run grep -F "$HOME/.config/romp/service.env" "$unit"
    [ "$status" -ne 0 ]                                                                         # the default did not creep in
    # the same path set explicitly agrees; a DIFFERING explicit value refuses and names both paths and the variable
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/custom/service.env" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    cp "$unit" "$unit.copy"
    ROMP_SERVICE_ENV="$TEST_DIR/elsewhere/service.env" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_SERVICE_ENV"* ]]
    [[ "$output" == *"$TEST_DIR/custom/service.env"* ]]
    [[ "$output" == *"$TEST_DIR/elsewhere/service.env"* ]]
    [[ "$output" == *"retry from a shell that does not set it"* ]]
    cmp -s "$unit" "$unit.copy"
}

@test "rewrite (macOS): the plist's own ROMP_SERVICE_ENV_FILE entry is kept from a shell setting neither name, and an explicitly set differing value refuses" {
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/custom/service.env" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qF '<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/custom/service.env</string>' "$plist"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qF '<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/custom/service.env</string>' "$plist"
    cp "$plist" "$plist.copy"
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/elsewhere/service.env" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_SERVICE_ENV_FILE"* ]]
    [[ "$output" == *"$TEST_DIR/custom/service.env"* ]]
    [[ "$output" == *"$TEST_DIR/elsewhere/service.env"* ]]
    cmp -s "$plist" "$plist.copy"
}

@test "rewrite: a file with no service.env line reads the kernel's default, never this shell's XDG_CONFIG_HOME resolution; a set value that differs from the default refuses" {
    # Round 2 (correctness-1's reachable half): a unit from before the EnvironmentFile line, and every default plist,
    # carry no path; round 1 resolved that absence in the rewriting shell (XDG_CONFIG_HOME, or the exported name), so a
    # deploy from a profile's or session's shell wrote its own resolution into the primary's file. The kernel with no
    # line reads $HOME/.config/romp/service.env, so that is what absence means here.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"
    grep -v '^EnvironmentFile=' "$unit" > "$unit.old" && mv -f "$unit.old" "$unit"   # the pre-EnvironmentFile unit
    local stub; stub="$(_systemctl_stub active)"
    XDG_CONFIG_HOME="$TEST_DIR/xdg" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite   # ROMP_SYSTEMD_DIR is pinned, so the unit is found
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=-$HOME/.config/romp/service.env" "$unit"   # the release's line, at the kernel's default
    run grep -F "$TEST_DIR/xdg" "$unit"
    [ "$status" -ne 0 ]
    run grep ROMP_SERVICE_ENV_FILE "$unit"
    [ "$status" -ne 0 ]                                                    # and no override line for a default path
    # macOS: a default plist writes no key; a rewrite from a shell with XDG_CONFIG_HOME adds none, and a set value that
    # differs from the default is a disagreement with what the agent reads
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    run grep ROMP_SERVICE_ENV_FILE "$plist"
    [ "$status" -ne 0 ]
    XDG_CONFIG_HOME="$TEST_DIR/xdg" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -F 'ROMP_SERVICE_ENV_FILE' "$plist"
    [ "$status" -ne 0 ]
    run grep -F "$TEST_DIR/xdg" "$plist"
    [ "$status" -ne 0 ]
    cp "$plist" "$plist.copy"
    ROMP_SERVICE_ENV="$TEST_DIR/xdg/romp/service.env" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"$HOME/.config/romp/service.env"* ]]
    [[ "$output" == *"$TEST_DIR/xdg/romp/service.env"* ]]
    cmp -s "$plist" "$plist.copy"
}

@test "rewrite (Linux): the EnvironmentFile line's doubled % is undone before the compare, so a path with a % agrees with the exported name" {
    # Round 2 (tests-2): the %% unescape had no pin; deleting it left the suite green
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    mkdir -p "$TEST_DIR/pct%dir"
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/pct%dir/service.env" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qF "EnvironmentFile=-$TEST_DIR/pct%%dir/service.env" "$unit"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/pct%dir/service.env" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qF "EnvironmentFile=-$TEST_DIR/pct%%dir/service.env" "$unit"
    grep -qF 'Environment="ROMP_SERVICE_ENV_FILE='"$TEST_DIR"'/pct%%dir/service.env"' "$unit"
}

@test "rewrite (Linux): the ROMP_DIR arm alone: a copy of the script in another clone, with ExecStart agreeing, is refused on ROMP_DIR" {
    # Round 2 (tests-2): the arm had no pin of its own; the clone-mismatch case above differs on ExecStart too. Here
    # ROMP_MANAGER_BIN names the unit's own ExecStart, so only ROMP_DIR (the script's own clone) differs.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local repo; repo="$(cd "$(dirname "$SVC")/.." && pwd)"
    grep -qxF "Environment=ROMP_DIR=$repo" "$unit"
    mkdir -p "$TEST_DIR/otherclone/bin"
    cp "$SVC" "$TEST_DIR/otherclone/bin/romp-service"
    cp "$unit" "$unit.copy"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$TEST_DIR/otherclone/bin/romp-service" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_DIR"* ]]
    [[ "$output" == *"$repo"* ]]
    [[ "$output" == *"$TEST_DIR/otherclone"* ]]
    [[ "$output" == *"not the installed one"* ]]
    [[ "$output" != *"ExecStart"* ]]                                    # that arm agreed; only ROMP_DIR is named
    cmp -s "$unit" "$unit.copy"
    [ ! -e "$TEST_DIR/systemctl-calls" ]
}

@test "rewrite (Linux): a unit with no PATH line gets none, never this caller's; a hand-quoted PATH line is a PATH line and goes back as written" {
    # Round 2 (tests-3, correctness-1): a PATH-less unit took the whole caller PATH (a session's), and a quoted
    # Environment="PATH=..." read as absent and was dropped. The rewrite writes the line the unit had, or none.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"
    grep -v '^Environment=PATH=' "$unit" > "$unit.old" && mv -f "$unit.old" "$unit"
    mkdir -p "$TEST_DIR/markerbin"
    local stub; stub="$(_systemctl_stub active)"
    PATH="$TEST_DIR/markerbin:$PATH" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    run grep -E '^Environment="?PATH=' "$unit"
    [ "$status" -ne 0 ]                                                  # no PATH line appeared
    run grep -F "$TEST_DIR/markerbin" "$unit"
    [ "$status" -ne 0 ]
    grep -q '^Environment=ROMP_DIR=' "$unit"                             # the rest of the block is intact
    # the quoted form
    printf 'Environment="PATH=/quoted/bin:/usr/bin"\n' >> "$unit"
    PATH="$TEST_DIR/markerbin:$PATH" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="PATH=/quoted/bin:/usr/bin"' "$unit"          # kept, quotes and all
    [ "$(grep -cE '^Environment="?PATH=' "$unit")" -eq 1 ]
    run grep -F "$TEST_DIR/markerbin" "$unit"
    [ "$status" -ne 0 ]
    # macOS: a plist with no PATH key gets none
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -v '<key>PATH</key>' "$plist" > "$plist.old" && mv -f "$plist.old" "$plist"
    PATH="$TEST_DIR/markerbin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -F '<key>PATH</key>' "$plist"
    [ "$status" -ne 0 ]
    run grep -F "$TEST_DIR/markerbin" "$plist"
    [ "$status" -ne 0 ]
}

@test "rewrite (Linux): after the reload the loaded fragment is read; a unit systemd loads from elsewhere, or a fragment that cannot be read, is said at exit 0, and the unit's own path is silent" {
    # Round 2 (correctness-8): NeedDaemonReload answers `no` for a unit systemd has never heard of, so a unit written
    # outside systemd's search path read as loaded and current. FragmentPath is the file systemd loads FROM, compared
    # as a place; one property per call, since systemd orders a multi-property answer by its own rules.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"
    local stub="$TEST_DIR/systemctl-stub"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$*" >> "$TEST_DIR/systemctl-calls"
case "\$*" in
  *NeedDaemonReload*) echo no ;;
  *FragmentPath*) echo "$TEST_DIR/elsewhere/romp-manager.service" ;;
esac
exit 0
EOF
    chmod +x "$stub"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"Rewrote the login service unit"* ]]
    [[ "$output" == *"loads romp-manager.service from $TEST_DIR/elsewhere/romp-manager.service"* ]]
    [[ "$output" == *"not from the file just written ($unit)"* ]]
    grep -qx -- '--user show -p FragmentPath --value romp-manager.service' "$TEST_DIR/systemctl-calls"
    grep -qx -- '--user show -p NeedDaemonReload --value romp-manager.service' "$TEST_DIR/systemctl-calls"
    # the unit's own path, reached through a symlinked directory: the same place, silent
    ln -s "$ROMP_SYSTEMD_DIR" "$TEST_DIR/systemd-link"
    sed -i.bak "s|$TEST_DIR/elsewhere/romp-manager.service|$TEST_DIR/systemd-link/romp-manager.service|" "$stub"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" != *"loads romp-manager.service from"* ]]
    [[ "$output" != *"FragmentPath could not be read"* ]]
    # a fragment that prints nothing is said, never read as clean
    printf '#!/bin/sh\ncase "$*" in *NeedDaemonReload*) echo no ;; esac\nexit 0\n' > "$stub"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"FragmentPath could not be read"* ]]
}

@test "rewrite (macOS): the state root is the plist's, not this shell's: a ROMP_STATE_DIR shell leaves a default plist's log paths, node copy and audit row where they are" {
    # Round 2 (correctness-2, regression-4; departure a of round 1's body, fixed): every \$STATE-derived value came from
    # the deploying environment. A profile's update child or a session's shell rewriting the primary's plist moved
    # StandardOutPath, made a node copy under the aux root and journaled the deploy there.
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" def="$XDG_STATE_HOME/romp"
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qF "<key>StandardOutPath</key><string>$def/manager.log</string>" "$plist"
    rm -f "$def/romp-node" "$def/restart-audit.jsonl"
    ROMP_STATE_DIR="$TEST_DIR/aux" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qF "<key>StandardOutPath</key><string>$def/manager.log</string>" "$plist"
    grep -qF "<key>StandardErrorPath</key><string>$def/manager.log</string>" "$plist"
    run grep -F "$TEST_DIR/aux" "$plist"
    [ "$status" -ne 0 ]
    [ -x "$def/romp-node" ]                                              # refreshed under the plist's root
    [ ! -e "$TEST_DIR/aux/romp-node" ]
    grep -q '"action": "service-rewrite"' "$def/restart-audit.jsonl"    # journaled under the plist's root
    [ ! -e "$TEST_DIR/aux/restart-audit.jsonl" ]
}

@test "rewrite (macOS): a plist carrying ROMP_STATE_DIR keeps its log paths on a rewrite from a clean shell, and the node copy under ITS root is the one refreshed" {
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" second="$TEST_DIR/second" def="$XDG_STATE_HOME/romp"
    ROMP_STATE_DIR="$second" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qF "<key>ROMP_STATE_DIR</key><string>$second</string>" "$plist"
    grep -qF "<key>StandardOutPath</key><string>$second/manager.log</string>" "$plist"
    cmp -s "$ROMP_NODE_SRC" "$second/romp-node"
    printf '#!/bin/sh\necho fake-node-v2 "$@"\n' > "$TEST_DIR/fake-node-v2"      # the node changed since the install
    chmod +x "$TEST_DIR/fake-node-v2"
    ROMP_NODE_SRC="$TEST_DIR/fake-node-v2" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite   # setup unset ROMP_STATE_DIR: the clean shell
    [ "$status" -eq 0 ]
    grep -qF "<key>ROMP_STATE_DIR</key><string>$second</string>" "$plist"
    grep -qF "<key>StandardOutPath</key><string>$second/manager.log</string>" "$plist"      # not moved to the default
    run grep -F "$def/manager.log" "$plist"
    [ "$status" -ne 0 ]
    cmp -s "$TEST_DIR/fake-node-v2" "$second/romp-node"                 # the copy under the plist's root followed the source
    [ ! -e "$def/romp-node" ]                                            # no copy under the caller's root
    grep -q '"action": "service-rewrite"' "$second/restart-audit.jsonl"
    [ ! -e "$def/restart-audit.jsonl" ]
}

@test "rewrite (macOS): an XDG_STATE_HOME install's log path is kept as it is, though no entry names the root" {
    # the refinement the round asked for: resolving absence to the default as the rewriting shell computes it still
    # loses an XDG_STATE_HOME install's path, since neither writer bakes XDG_STATE_HOME into the file
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" xdg="$TEST_DIR/xdgstate"
    XDG_STATE_HOME="$xdg" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qF "<key>StandardOutPath</key><string>$xdg/romp/manager.log</string>" "$plist"
    run grep ROMP_STATE_DIR "$plist"
    [ "$status" -ne 0 ]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite                            # setup's XDG_STATE_HOME: another root
    [ "$status" -eq 0 ]
    grep -qF "<key>StandardOutPath</key><string>$xdg/romp/manager.log</string>" "$plist"
    grep -q '"action": "service-rewrite"' "$xdg/romp/restart-audit.jsonl"
    [ ! -e "$XDG_STATE_HOME/romp/restart-audit.jsonl" ]
}

@test "rewrite (Linux): the attribution row is journaled under the unit's state root in both directions, never the caller's" {
    # Round 2 (regression-4). The unit never bakes XDG_STATE_HOME, so a unit with no ROMP_STATE_DIR line resolves to the
    # default from \$HOME here; a unit carrying the line resolves to that line, whatever the caller exports.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" def="$HOME/.local/state/romp"
    _old_unit "$unit"
    rm -f "$def/restart-audit.jsonl"
    local stub; stub="$(_systemctl_stub active)"
    ROMP_STATE_DIR="$TEST_DIR/aux" XDG_STATE_HOME="$TEST_DIR/aux-xdg" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '"action": "service-rewrite"' "$def/restart-audit.jsonl"
    [ ! -e "$TEST_DIR/aux/restart-audit.jsonl" ]
    [ ! -e "$TEST_DIR/aux-xdg/romp/restart-audit.jsonl" ]
    run grep -F "$TEST_DIR/aux" "$unit"
    [ "$status" -ne 0 ]
    # the other direction
    ROMP_STATE_DIR="$TEST_DIR/second" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    rm -f "$def/restart-audit.jsonl" "$TEST_DIR/second/restart-audit.jsonl"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite   # the plain shell
    [ "$status" -eq 0 ]
    grep -q '"action": "service-rewrite"' "$TEST_DIR/second/restart-audit.jsonl"
    [ ! -e "$def/restart-audit.jsonl" ]
}

@test "install: the kernel's marked update child keeps an installed unit's instance lines and identity; an unmarked minimal install bakes what it has (the documented contract); with no unit the marked child installs one" {
    # Round 2 (kernel-1). install.sh takes the install road when the manager is not running under the service (`romp up
    # --foreground`, a hand-run install), and the update child's scrubbed environment then rewrote the unit from itself:
    # the four ports and the Claude config dir gone, the state root re-baked from the caller, exit 0 and nothing said.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    ROMP_SERVE_PORT=29866 ROMP_KERNEL_PORT=29866 ROMP_POSTAL_PORT=29900 ROMP_MANAGER_PORT=7433 \
        ROMP_STATE_DIR="$TEST_DIR/second" CLAUDE_CONFIG_DIR="$TEST_DIR/second-claude" \
        ROMP_OS_OVERRIDE=Linux "$SVC" install >/dev/null
    local v; for v in ROMP_SERVE_PORT=29866 ROMP_KERNEL_PORT=29866 ROMP_POSTAL_PORT=29900 ROMP_MANAGER_PORT=7433 "ROMP_STATE_DIR=$TEST_DIR/second" "CLAUDE_CONFIG_DIR=$TEST_DIR/second-claude"; do
        grep -qxF "Environment=$v" "$unit"
    done
    local pathline; pathline="$(grep '^Environment=PATH=' "$unit")"
    mkdir -p "$TEST_DIR/childbin"
    run env -i HOME="$HOME" PATH="$TEST_DIR/childbin:$PATH" ROMP_UPDATE_CHILD=1 ROMP_STATE_DIR="$TEST_DIR/second" \
        ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
    [ "$status" -eq 0 ]
    for v in ROMP_SERVE_PORT=29866 ROMP_KERNEL_PORT=29866 ROMP_POSTAL_PORT=29900 ROMP_MANAGER_PORT=7433 "ROMP_STATE_DIR=$TEST_DIR/second" "CLAUDE_CONFIG_DIR=$TEST_DIR/second-claude"; do
        grep -qxF "Environment=$v" "$unit"                               # all six survive the child
    done
    grep -qxF -- "$pathline" "$unit"                                     # and the unit's PATH, not the child's
    run grep -F "$TEST_DIR/childbin" "$unit"
    [ "$status" -ne 0 ]
    grep -q '"action": "service-install"' "$TEST_DIR/second/restart-audit.jsonl"   # journaled under the unit's root
    # the marked child with a DIFFERING value is refused on this road too, exit 5, the unit untouched
    cp "$unit" "$unit.copy"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_STATE_DIR="$TEST_DIR/other" \
        ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_STATE_DIR"* ]]
    cmp -s "$unit" "$unit.copy"
    # the control: a person's minimal install, unmarked, bakes what that shell sets and nothing else (the header's contract)
    run env -i HOME="$HOME" PATH="$PATH" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
    [ "$status" -eq 0 ]
    run grep -E '^Environment=(ROMP_SERVE_PORT|ROMP_KERNEL_PORT|ROMP_POSTAL_PORT|ROMP_MANAGER_PORT|ROMP_STATE_DIR|CLAUDE_CONFIG_DIR)=' "$unit"
    [ "$status" -ne 0 ]
    # no unit at all: the marked child installs one from its environment, as a fresh box wants
    rm -f "$unit"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_STATE_DIR="$TEST_DIR/fresh" \
        ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
    [ "$status" -eq 0 ]
    grep -qxF "Environment=ROMP_STATE_DIR=$TEST_DIR/fresh" "$unit"
}

@test "install (macOS): the marked update child keeps an installed plist's instance entries" {
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_KERNEL_PORT=29866 ROMP_MANAGER_PORT=7433 CLAUDE_CONFIG_DIR="$TEST_DIR/second-claude" ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
        ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
    [ "$status" -eq 0 ]
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
    grep -q '<key>ROMP_MANAGER_PORT</key><string>7433</string>' "$plist"
    grep -qF "<key>CLAUDE_CONFIG_DIR</key><string>$TEST_DIR/second-claude</string>" "$plist"
}

@test "install (Linux): a unit path that is a symlink becomes a regular file, the link's target is byte for byte unchanged, and the line says so" {
    # Round 2 (fresh-2): the shared writer's rename replaced the link on the install road too, a change from the base
    # (which wrote through the link into the administrator's own file); the rewrite road had the pin, this road none
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    mkdir -p "$ROMP_SYSTEMD_DIR" "$TEST_DIR/dotfiles"
    printf '[Service]\nExecStart=/dotfiles/own up\n# the administrator'"'"'s own file\n' > "$TEST_DIR/dotfiles/romp-manager.service"
    cp "$TEST_DIR/dotfiles/romp-manager.service" "$TEST_DIR/dotfiles.copy"
    ln -s "$TEST_DIR/dotfiles/romp-manager.service" "$unit"
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    [ ! -L "$unit" ]
    [ -f "$unit" ]
    grep -q "^ExecStart=$ROMP_MANAGER_BIN up$" "$unit"
    cmp -s "$TEST_DIR/dotfiles/romp-manager.service" "$TEST_DIR/dotfiles.copy"
    [[ "$output" == *"was a symlink"* ]]
    [[ "$output" == *"$TEST_DIR/dotfiles/romp-manager.service"* ]]
}

# ─── round 3 of the review (2026-09-19): the plist's form, one escape per direction, systemd's quoting, the log-path rung ──
# A reader that cannot parse a file must not report its values as absent: the one-line grep read a plist any macOS tool
# had re-saved (canonical XML: key and string on separate lines; binary: no tags at all) as a plist with no entries, and
# the rewrite dropped PATH, the instance block and the service.env path, moved the log paths and, on a binary plist from
# a second clone, re-pointed the agent at the deploying clone, exit 0, and `rewrite --check` blessed both. macOS has
# plutil; this Linux host has a stand-in (below) or none, and both readers are exercised.
_plutil_stub() {   # a stand-in for macOS plutil at $TEST_DIR/plutil-bin/plutil, the one form romp-service calls: -extract <keypath> raw [-expect T] -o - <file>
    mkdir -p "$TEST_DIR/plutil-bin"
    cat > "$TEST_DIR/plutil-bin/plutil" <<'PY'
#!/usr/bin/env python3
import plistlib, sys
a = sys.argv[1:]
if len(a) < 4 or a[0] != "-extract":
    sys.exit(2)
kp, path, i = a[1], None, 3
while i < len(a):
    if a[i] in ("-o", "-expect"):
        i += 2
    else:
        path = a[i]; i += 1
try:
    with open(path, "rb") as f:
        cur = plistlib.load(f)
except Exception as e:
    print("%s: Property List error: %s" % (path, e)); sys.exit(1)
for part in kp.split("."):
    if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
        cur = cur[int(part)]
    elif isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print("%s: Could not extract value, error: No value at that key path or invalid key path: %s" % (path, kp)); sys.exit(1)
if isinstance(cur, (list, dict)):
    print(len(cur))
elif isinstance(cur, bool):
    print("true" if cur else "false")
else:
    print(cur)
PY
    chmod +x "$TEST_DIR/plutil-bin/plutil"
}
_resave() {   # $1 the plist, $2 xml | binary: re-save it as plutil -convert, PlistBuddy, defaults and Xcode do (canonical XML, key and string on separate lines, sorted; or bplist00)
    python3 - "$1" "$2" <<'PY'
import plistlib, sys
p, fmt = sys.argv[1], sys.argv[2]
with open(p, "rb") as f:
    d = plistlib.load(f)
with open(p, "wb") as f:
    plistlib.dump(d, f, fmt=plistlib.FMT_BINARY if fmt == "binary" else plistlib.FMT_XML)
PY
}
_plist_get() {   # $1 the plist, $2 a dotted key path: the decoded value, as launchd reads it
    python3 - "$1" "$2" <<'PY'
import plistlib, sys
with open(sys.argv[1], "rb") as f:
    d = plistlib.load(f)
for part in sys.argv[2].split("."):
    d = d[int(part)] if isinstance(d, list) else d[part]
print(d)
PY
}
_unit_env_value() {   # $1 the unit, $2 a name: the value systemd reads for it from the unit's Environment= lines (systemd.syntax(7) quoting: quotes off, \\ and \" undone; the specifier's %% undone)
    python3 - "$1" "$2" <<'PY'
import shlex, sys
name = sys.argv[2]
for line in open(sys.argv[1]):
    if line.startswith("Environment="):
        for item in shlex.split(line[len("Environment="):]):
            k, _, v = item.partition("=")
            if k == name:
                print(v.replace("%%", "%"))
PY
}

@test "rewrite (macOS): a plist re-saved in canonical XML or as binary is read through plutil when one is on PATH: its identity, PATH, instance entries, service.env path and log paths survive, and another clone or a differing value is still refused" {
    unset ROMP_SERVICE_NO_LOAD
    _plutil_stub
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" xdg="$TEST_DIR/xdgstate" repo; repo="$(cd "$(dirname "$SVC")/.." && pwd)"
    mkdir -p "$TEST_DIR/pathbin" "$TEST_DIR/other/bin"
    PATH="$TEST_DIR/pathbin:$PATH" XDG_STATE_HOME="$xdg" ROMP_KERNEL_PORT=29866 ROMP_MANAGER_PORT=7433 CLAUDE_CONFIG_DIR="$TEST_DIR/second-claude" \
        ROMP_SERVICE_ENV_FILE="$TEST_DIR/custom/service.env" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local pathval; pathval="$(_plist_get "$plist" EnvironmentVariables.PATH)"
    [[ "$pathval" == "$TEST_DIR/pathbin:"* ]]
    local fmt
    for fmt in xml binary; do
        _resave "$plist" "$fmt"
        run grep -aqF '<key>Label</key><string>' "$plist"
        [ "$status" -ne 0 ]                                              # the one-line form is gone
        cp "$plist" "$plist.saved"
        # another clone: refused on ExecStart, read out of the re-saved file, the file byte for byte
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_MANAGER_BIN="$TEST_DIR/other/bin/romp-manager" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"ExecStart: the file runs $ROMP_MANAGER_BIN, this clone would write $TEST_DIR/other/bin/romp-manager"* ]]
        cmp -s "$plist" "$plist.saved"
        # a differing instance value: refused, --check too
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_KERNEL_PORT=31855 ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"ROMP_KERNEL_PORT: the file carries 29866, this environment carries 31855"* ]]
        cmp -s "$plist" "$plist.saved"
        # the clean shell: exit 0, the plist back in romp's form with every entry it carried, the log paths where they were
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 0 ]
        grep -qF "<key>PATH</key><string>$pathval</string>" "$plist"
        run grep -F "plutil-bin" "$plist"
        [ "$status" -ne 0 ]                                              # the file's PATH, not this shell's
        grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
        grep -q '<key>ROMP_MANAGER_PORT</key><string>7433</string>' "$plist"
        grep -qF "<key>CLAUDE_CONFIG_DIR</key><string>$TEST_DIR/second-claude</string>" "$plist"
        grep -qF "<key>ROMP_SERVICE_ENV_FILE</key><string>$TEST_DIR/custom/service.env</string>" "$plist"
        grep -qF "<key>StandardOutPath</key><string>$xdg/romp/manager.log</string>" "$plist"
        grep -qF "<string>$ROMP_MANAGER_BIN</string>" "$plist"
        grep -qF "<key>ROMP_DIR</key><string>$repo</string>" "$plist"
        run grep -F "$XDG_STATE_HOME/romp" "$plist"
        [ "$status" -ne 0 ]                                              # not moved to this shell's root
        grep -q '"action": "service-rewrite"' "$xdg/romp/restart-audit.jsonl"
    done
}

@test "rewrite (macOS): without plutil a plist not in romp's one-line form is refused, exit 5 and byte for byte, on rewrite, rewrite --check and the marked child's install; the refusal names the form and the route; romp's own form still reads" {
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here"   # ROMP_PLUTIL at a path that does not exist: the fallback, on a mac too
    ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$plist" "$plist.romp"
    local fmt
    for fmt in xml binary; do
        cp "$plist.romp" "$plist"
        _resave "$plist" "$fmt"
        cp "$plist" "$plist.saved"
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"not in the one-line form romp writes"* ]]
        [[ "$output" == *"no plutil is available"* ]]
        [[ "$output" == *"nothing was rewritten"* ]]
        [[ "$output" == *"romp-service install from the shell and clone that should own the service"* ]]
        [[ "$output" != *"Rewrote"* ]]
        cmp -s "$plist" "$plist.saved"
        [ ! -e "$plist.tmp" ]
        run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
        [ "$status" -ne 0 ]                                              # nothing journaled
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"not in the one-line form romp writes"* ]]
        cmp -s "$plist" "$plist.saved"
        run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
            ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"not in the one-line form romp writes"* ]]
        cmp -s "$plist" "$plist.saved"                                   # the marked child wrote nothing either
    done
    # the second marker: Label on one line, ROMP_SUPERVISED split across two, is the re-saved form too
    awk '{ if ($0 ~ /<key>ROMP_SUPERVISED<\/key><string>1<\/string>/) { print "    <key>ROMP_SUPERVISED</key>"; print "    <string>1</string>" } else print }' "$plist.romp" > "$plist"
    cp "$plist" "$plist.split"
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_SUPERVISED entry is split across lines"* ]]
    cmp -s "$plist" "$plist.split"
    # a plist from before ROMP_SUPERVISED existed reads: Label alone is the marker, so an older box is not refused
    grep -v ROMP_SUPERVISED "$plist.romp" > "$plist"
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
    grep -q '<key>ROMP_SUPERVISED</key><string>1</string>' "$plist"
    # the control: romp's own form with a hand-added one-line entry reads and rewrites as before (the entry dropped, as documented)
    awk '/<key>ROMP_SUPERVISED<\/key>/{print; print "    <key>ADMIN_LOCAL_KNOB</key><string>1</string>"; next}1' "$plist.romp" > "$plist"
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
    run grep ADMIN_LOCAL_KNOB "$plist"
    [ "$status" -ne 0 ]
    # a plist that is not romp's at all (a Label of something else), through the stand-in plutil: refused, naming the Label
    _plutil_stub
    sed "s|<string>com.romp.manager</string>|<string>com.example.other</string>|" "$plist.romp" > "$plist"
    cp "$plist" "$plist.other"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"reads its Label as com.example.other, not com.romp.manager"* ]]
    cmp -s "$plist" "$plist.other"
}

@test "rewrite (macOS): a service.env path with &, <, > and a double quote is escaped once on write and decoded on read, with plutil and without: the owning shell is not refused, and two clean-shell rewrites leave the plist byte for byte" {
    # Round 3 (regression-3, extra6-3, extra7-1): the writer escaped the path and the reader returned the escaped text, so
    # the shell that installed it was refused over a path it never changed, and every clean-shell rewrite added a layer
    unset ROMP_SERVICE_NO_LOAD
    _plutil_stub
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" envf="$TEST_DIR/alt <x> & \"q\" dir/service.env" reader
    for reader in "PATH=$TEST_DIR/plutil-bin:$PATH" "ROMP_PLUTIL=$TEST_DIR/no-plutil-here"; do
        rm -f "$plist"
        env "$reader" ROMP_SERVICE_ENV_FILE="$envf" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
        grep -qF '<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/alt &lt;x&gt; &amp; &quot;q&quot; dir/service.env</string>' "$plist"
        [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_SERVICE_ENV_FILE)" = "$envf" ]
        run env "$reader" ROMP_SERVICE_ENV_FILE="$envf" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite        # the owning shell: agrees
        [ "$status" -eq 0 ]
        [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_SERVICE_ENV_FILE)" = "$envf" ]
        cp "$plist" "$plist.once"
        run env "$reader" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite                                       # the clean shell, twice
        [ "$status" -eq 0 ]
        run env "$reader" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite
        [ "$status" -eq 0 ]
        cmp -s "$plist" "$plist.once"                                                                  # no layer per rewrite
        [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_SERVICE_ENV_FILE)" = "$envf" ]
        run env "$reader" ROMP_SERVICE_ENV="$TEST_DIR/elsewhere/service.env" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite   # a differing path still refuses, decoded
        [ "$status" -eq 5 ]
        [[ "$output" == *"the file reads $envf, this environment names $TEST_DIR/elsewhere/service.env"* ]]
        cmp -s "$plist" "$plist.once"
    done
}

@test "install and rewrite (macOS): every plist value is XML-escaped once: an instance entry and a state root with & parse, survive a rewrite and agree with the owning shell" {
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" cc="$TEST_DIR/cc & <dir>" st="$TEST_DIR/state & root"
    CLAUDE_CONFIG_DIR="$cc" ROMP_STATE_DIR="$st" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR)" = "$cc" ]          # plistlib parses it: the & went in as &amp;
    [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_STATE_DIR)" = "$st" ]
    [ "$(_plist_get "$plist" StandardOutPath)" = "$st/manager.log" ]
    [ "$(_plist_get "$plist" StandardErrorPath)" = "$st/manager.log" ]
    grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>'"$TEST_DIR"'/cc &amp; &lt;dir&gt;</string>' "$plist"
    cp "$plist" "$plist.once"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite                                            # the clean shell (setup unset both)
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.once"
    grep -q '"action": "service-rewrite"' "$st/restart-audit.jsonl"                      # the root, read back decoded, is the one journaled under
    CLAUDE_CONFIG_DIR="$cc" ROMP_STATE_DIR="$st" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite   # the owning shell agrees
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.once"
}

@test "rewrite (macOS): a plist whose StandardOutPath is not <root>/manager.log keeps that path, and the attribution row and the node copy land under its directory" {
    # Round 3 (extra7-3, the pin the round asked for over the middle rung of round 2's chain: the file's ROMP_STATE_DIR line,
    # else the directory of the plist's own log path, else the default from $HOME)
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" logs="$TEST_DIR/logs"
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    mkdir -p "$logs"
    sed -i.bak "s|<string>$XDG_STATE_HOME/romp/manager.log</string>|<string>$logs/agent.out</string>|g" "$plist"   # a hand-redirected log, both keys
    grep -qF "<key>StandardOutPath</key><string>$logs/agent.out</string>" "$plist"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qF "<key>StandardOutPath</key><string>$logs/agent.out</string>" "$plist"
    grep -qF "<key>StandardErrorPath</key><string>$logs/agent.out</string>" "$plist"
    run grep -F "manager.log" "$plist"
    [ "$status" -ne 0 ]
    grep -q '"action": "service-rewrite"' "$logs/restart-audit.jsonl"
    [ -x "$logs/romp-node" ]
    run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
    [ "$status" -ne 0 ]                                                                    # not under this shell's root
}

@test "rewrite (Linux): a hand-quoted instance line with whitespace goes back as written and reads back whole; an install writes a value with whitespace, a % or a backslash in the quoted form systemd reads whole, a plain one unquoted as before" {
    # Round 3 (extra6-2): round 2 taught the reader to MATCH a quoted Environment= line for every key, and only PATH was
    # written back verbatim; an instance value read out of a quoted line was re-emitted unquoted, and systemd cuts an
    # unquoted item at whitespace (systemd.exec(5) Environment=, systemd.syntax(7) Quoting). The written line is parsed
    # here the way systemd parses it (_unit_env_value).
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" cc="$TEST_DIR/claude cfg dir" st="$TEST_DIR/pct%dir"
    _old_unit "$unit"
    printf 'Environment="CLAUDE_CONFIG_DIR=%s"\n' "$cc" >> "$unit"
    printf 'Environment="ROMP_STATE_DIR=%s"\n' "$TEST_DIR/pct%%dir" >> "$unit"          # hand-quoted, with the doubled % systemd wants
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite                      # the clean shell
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR='"$cc"'"' "$unit"                           # as written, quotes and all
    grep -qxF 'Environment="ROMP_STATE_DIR='"$TEST_DIR"'/pct%%dir"' "$unit"
    [ "$(grep -cE '^Environment="?CLAUDE_CONFIG_DIR=' "$unit")" -eq 1 ]
    [ "$(_unit_env_value "$unit" CLAUDE_CONFIG_DIR)" = "$cc" ]                             # what systemd reads: the whole value
    [ "$(_unit_env_value "$unit" ROMP_STATE_DIR)" = "$st" ]
    grep -q '"action": "service-rewrite"' "$st/restart-audit.jsonl"                       # the decoded root is the one journaled under
    # the compare reads the decoded value: the owning shell agrees, a differing one refuses naming the decoded value
    CLAUDE_CONFIG_DIR="$cc" ROMP_STATE_DIR="$st" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR="$TEST_DIR/other" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries $cc, this environment carries $TEST_DIR/other"* ]]
    # the install road: a value that needs quoting gets it, escaped; a plain one stays unquoted, byte for byte as before
    local bs="$TEST_DIR/back\\slash \"q\""
    mkdir -p "$bs"
    CLAUDE_CONFIG_DIR="$bs" ROMP_STATE_DIR="$st" ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qxF 'Environment=ROMP_KERNEL_PORT=29866' "$unit"
    grep -qxF 'Environment="ROMP_STATE_DIR='"$TEST_DIR"'/pct%%dir"' "$unit"
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR='"$TEST_DIR"'/back\\slash \"q\""' "$unit"
    [ "$(_unit_env_value "$unit" CLAUDE_CONFIG_DIR)" = "$bs" ]
    [ "$(_unit_env_value "$unit" ROMP_STATE_DIR)" = "$st" ]
    [ "$(_unit_env_value "$unit" ROMP_KERNEL_PORT)" = 29866 ]
    # and a rewrite replays them as written, agreeing with the shell that installed them
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR='"$TEST_DIR"'/back\\slash \"q\""' "$unit"
    CLAUDE_CONFIG_DIR="$bs" ROMP_STATE_DIR="$st" ROMP_KERNEL_PORT=29866 ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
}

# ─── stop / start: the supervisor halves of `romp down` / `romp up` ──────────────────────────
# A stop has to go THROUGH the supervisor: the manager exiting on its own is a crash to
# Restart=always / KeepAlive and it respawns within seconds. ROMP_SYSTEMCTL stubs systemctl the
# way ROMP_LAUNCHCTL stubs launchctl; both record their argv so the tests assert the exact call.

_systemctl_stub() {
    # $1 = what `is-active` answers (active|inactive|failed); every call's argv lands in systemctl-calls
    local stub="$TEST_DIR/systemctl-stub" calls="$TEST_DIR/systemctl-calls"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$*" >> "$calls"
case "\$2" in
  is-active) echo "$1"; [ "$1" = active ] ;;
  show) case "\$*" in
          *NeedDaemonReload*) echo no ;;                                 # the read-back after the reload: loaded is current
          *FragmentPath*) echo "\${ROMP_SYSTEMD_DIR}/romp-manager.service" ;;   # and loaded from the file just written
        esac ;;
  *) exit 0 ;;
esac
EOF
    chmod +x "$stub"
    printf '%s' "$stub"
}

@test "stop (Linux): stops the unit through systemctl and says it stays stopped" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" stop
    [ "$status" -eq 0 ]
    grep -qx -- '--user stop romp-manager.service' "$TEST_DIR/systemctl-calls"
    [[ "$output" == *"stays stopped until"* ]]
    # never a disable: the unit stays enabled so the next boot (linger) brings it back
    run grep -q 'disable' "$TEST_DIR/systemctl-calls"
    [ "$status" -ne 0 ]
}

@test "start (Linux): starts the unit through systemctl" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub; stub="$(_systemctl_stub inactive)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" start
    [ "$status" -eq 0 ]
    grep -qx -- '--user start romp-manager.service' "$TEST_DIR/systemctl-calls"
    [[ "$output" == *"Started the login service"* ]]
}

@test "stop / start with no unit installed exit 3 and touch nothing: the caller falls back" {
    unset ROMP_SERVICE_NO_LOAD
    local stub; stub="$(_systemctl_stub inactive)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" stop
    [ "$status" -eq 3 ]
    [[ "$output" == *"no login service is installed"* ]]
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" start
    [ "$status" -eq 3 ]
    [ ! -e "$TEST_DIR/systemctl-calls" ]
    # macOS: the same contract against the plist
    ROMP_OS_OVERRIDE=Darwin run "$SVC" stop
    [ "$status" -eq 3 ]
    [[ "$output" == *"no login agent is installed"* ]]
}

@test "stop (Linux): a failing systemctl stop is loud and exit 1" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/systemctl-stub"
    printf '#!/bin/sh\ncase "$2" in is-active) echo active; exit 0 ;; esac\necho "Failed to stop" >&2\nexit 1\n' > "$stub"
    chmod +x "$stub"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" stop
    [ "$status" -eq 1 ]
    [[ "$output" == *"stop romp-manager.service failed"* ]]
}

@test "stop (macOS): boots the job out and waits for it to leave launchd" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    # loaded until the bootout lands; `print` fails once bootout has been called
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$1" >> "$calls"
case "\$1" in
  print) grep -q bootout "$calls" && exit 1; exit 0 ;;
  *) exit 0 ;;
esac
EOF
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" stop
    [ "$status" -eq 0 ]
    grep -q bootout "$calls"
    [[ "$output" == *"Stopped the login agent"* ]]
}

@test "start (macOS): a booted-out job is bootstrapped again; a loaded one is kickstarted" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    # not loaded: print fails, so bootstrap
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$1" >> "$calls"
[ "\$1" = print ] && exit 1
exit 0
EOF
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" start
    [ "$status" -eq 0 ]
    grep -q bootstrap "$calls"
    run grep -q kickstart "$calls"
    [ "$status" -ne 0 ]
    # loaded: print succeeds, so kickstart, no bootstrap
    : > "$calls"
    printf '#!/bin/sh\necho "$1" >> "%s"\nexit 0\n' "$calls" > "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" start
    [ "$status" -eq 0 ]
    grep -q kickstart "$calls"
    run grep -q bootstrap "$calls"
    [ "$status" -ne 0 ]
}

@test "status names a deliberate stop: the romp down marker's time, and how to start again" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub; stub="$(_systemctl_stub inactive)"
    mkdir -p "$XDG_STATE_HOME/romp"
    printf '{"t": %s, "cmd": "romp down"}\n' "$(date +%s)" > "$XDG_STATE_HOME/romp/down-by-romp"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"stopped by romp down at "* ]]
    [[ "$output" == *"(romp up to start)"* ]]
    run grep -qx running <<< "$output"
    [ "$status" -ne 0 ]
    # a running service outranks a stale marker: no "stopped" line while it answers active
    stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"running"* ]]
    run grep -q 'stopped by romp down' <<< "$output"
    [ "$status" -ne 0 ]
    # no marker, not running: nothing about a deliberate stop
    rm "$XDG_STATE_HOME/romp/down-by-romp"
    stub="$(_systemctl_stub inactive)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    run grep -q 'romp down' <<< "$output"
    [ "$status" -ne 0 ]
}

@test "status renders an old marker with its date, not a bare clock time" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub; stub="$(_systemctl_stub inactive)"
    mkdir -p "$XDG_STATE_HOME/romp"
    printf '{"t": %s, "cmd": "romp down"}\n' "$(( $(date +%s) - 3 * 86400 ))" > "$XDG_STATE_HOME/romp/down-by-romp"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" =~ stopped\ by\ romp\ down\ at\ [0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2} ]]
}

@test "stop (Linux): an installed unit that is not running is exit 4, says so, and is not stopped again" {
    # `systemctl --user stop` on an inactive unit exits 0, which would read as a stop while a manager
    # started outside the service kept running; the caller stops that one itself on a 4
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub; stub="$(_systemctl_stub inactive)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" stop
    [ "$status" -eq 4 ]
    [[ "$output" == *"installed but not running"* ]]
    run grep -q -- '--user stop' "$TEST_DIR/systemctl-calls"
    [ "$status" -ne 0 ]
    run grep -q 'Stopped the login service' <<< "$output"
    [ "$status" -ne 0 ]
    # a failed unit is not running either
    stub="$(_systemctl_stub failed)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" stop
    [ "$status" -eq 4 ]
}

@test "stop (macOS): an installed agent that is not loaded is exit 4, says so, and no bootout" {
    unset ROMP_SERVICE_NO_LOAD
    ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    local stub="$TEST_DIR/launchctl-stub" calls="$TEST_DIR/launchctl-calls"
    printf '#!/bin/sh\necho "$1" >> "%s"\n[ "$1" = print ] && exit 1\nexit 0\n' "$calls" > "$stub"
    chmod +x "$stub"
    ROMP_LAUNCHCTL="$stub" ROMP_OS_OVERRIDE=Darwin run "$SVC" stop
    [ "$status" -eq 4 ]
    [[ "$output" == *"installed but not running"* ]]
    run grep -q bootout "$calls"
    [ "$status" -ne 0 ]
    run grep -q 'Stopped the login agent' <<< "$output"
    [ "$status" -ne 0 ]
}
