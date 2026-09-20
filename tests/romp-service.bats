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
    # no restart, stop or kill on the install road: enable --now starts an inactive unit and leaves a running one as it is, which is what four
    # surfaces tell the operator (install.sh's exit-3 route message, bin/romp-service's shared refusal tail and its ExecStart-path refusal,
    # docs/reference.md); this line holds the behaviour those sentences assert (round 6 of fork PR #778, tests-3: a restart added to the
    # install arm left both bats files green)
    run grep -E -- 'restart|stop|kill' "$calls"
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
    _svc_line "$unit" 'Environment=ADMIN_LOCAL_KNOB=1'
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
    # the quoted form (in [Service], where systemd reads it: appended after [Install] it is a line systemd ignores, which the
    # addendum to round 3 refuses for a kept variable)
    _svc_line "$unit" 'Environment="PATH=/quoted/bin:/usr/bin"'
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
_plutil_stub() {   # a stand-in for macOS plutil at $TEST_DIR/plutil-bin/plutil, the two forms romp-service calls: -extract <keypath> raw [-n] [-expect T] -o - <file>
                   # and -extract <keypath> xml1 -o - <file> (the type teller, round 8 of fork PR #778: a plist document whose root element is
                   # the value, as plutil(1) says of -extract, "a new plist of type fmt"; written here by plistlib). A container extracted raw
                   # renders as plutil(1) and the open-source implementation say: an array as its element count, a dictionary as its keys one
                   # per line, alpha-sorted; $3 (count, the default; refuse: exit 1 with the open-source implementation's message form, the
                   # behaviour no evidenced plutil has and which the reader must not read as absence).
                   # $1 is what it writes after the raw value (nl, the default: one line end, plutil(1)'s documented behaviour; nonl: none, the
                   # line-end calibration's other branch, since round 4's mutation pass (2026-09-19) found the stand-in always wrote one, so that
                   # branch had never run; lacking: one only when the value LACKS one, round 7 of fork PR #778's correctness-1, the behaviour the
                   # one-value calibration could not tell from nl's, under which it took a value's own trailing newline off; two: two line ends;
                   # strip: the value's own trailing newline stripped, none written; strip_nl: stripped, then one written; crlf: CR LF after the
                   # value; crlf_all: every newline in the value as CR LF and CR LF after it; nested_nonl, array_nonl, top_nonl, key_label_nonl:
                   # none for a dotted key path, for an array index, for a top-level key, for the Label alone, one otherwise, the key-shape
                   # behaviours the four probes span; file_nonl and file_lacking: nl on the reader's own scratch plist (a file under a directory
                   # named romp-service-plutil.) and nonl or lacking on any other file, the behaviours no scratch can span, which the round-7
                   # addendum's file-side checks refuse; interior_nonl, nonascii_nonl, key_ccd_nonl, index_nonl: none for a value with a newline
                   # inside it, for one with a non-ASCII character, for the key path ending in .CLAUDE_CONFIG_DIR, for an array index above 0,
                   # one otherwise, the classes keyed on the value's bytes, the key's name and the array index that the four probes do not
                   # carry and the round-8 echo of each file value through the scratch does). No evidenced plutil behaves as any but the first;
                   # the reader refuses the others rather than assuming. $2 is what -n does (honour, the default: plutil(1)'s no line end after
                   # the raw value; ignore: accepted and a line end written anyway; reject: an unrecognised switch, exit 2 and nothing on
                   # stdout; half: honoured for a top-level key and ignored for a dotted one).
    local mode="${1:-nl}" nmode="${2:-honour}" cmode="${3:-count}"
    mkdir -p "$TEST_DIR/plutil-bin"
    printf '#!/usr/bin/env python3\nMODE = "%s"    # what follows the raw value (the _plutil_stub comment in tests/romp-service.bats)\nNMODE = "%s"   # what -n does\nCMODE = "%s"   # a container extracted raw: count (plutil(1)) or refuse\n' "$mode" "$nmode" "$cmode" > "$TEST_DIR/plutil-bin/plutil"
    cat >> "$TEST_DIR/plutil-bin/plutil" <<'PY'
import base64, datetime, plistlib, sys
a = sys.argv[1:]
if len(a) < 4 or a[0] != "-extract":
    sys.exit(2)
kp, fmt, path, i, nflag = a[1], a[2], None, 3, False
if fmt not in ("raw", "xml1"):
    sys.stderr.write("plutil: Unknown format specifier: %s\n" % fmt); sys.exit(1)
while i < len(a):
    if a[i] in ("-o", "-expect"):
        i += 2
    elif a[i] == "-n":
        if NMODE == "reject":
            sys.stderr.write("plutil: unrecognized option -n\n"); sys.exit(2)
        nflag = True; i += 1
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
if fmt == "xml1":
    sys.stdout.buffer.write(plistlib.dumps(cur)); sys.exit(0)
if isinstance(cur, (list, dict)) and CMODE == "refuse":
    print("%s: Value at %s is a %s type and cannot be extracted in raw format" % (path, kp, "array" if isinstance(cur, list) else "dictionary")); sys.exit(1)
if isinstance(cur, list):
    text = str(len(cur))
elif isinstance(cur, dict):
    text = "\n".join(sorted(cur))
elif isinstance(cur, bool):
    text = "true" if cur else "false"
elif isinstance(cur, datetime.datetime):
    text = cur.strftime("%Y-%m-%dT%H:%M:%SZ")
elif isinstance(cur, bytes):
    text = base64.b64encode(cur).decode()
else:
    text = str(cur)
scratch = "romp-service-plutil." in path      # the reader's own scratch plist
dotted = "." in kp
array = kp.rsplit(".", 1)[-1].isdigit()
end = "\n"
if MODE == "nonl": end = ""
elif MODE == "lacking": end = "" if text.endswith("\n") else "\n"
elif MODE == "two": end = "\n\n"
elif MODE == "strip": text = text.rstrip("\n"); end = ""
elif MODE == "strip_nl": text = text.rstrip("\n"); end = "\n"
elif MODE == "crlf": end = "\r\n"
elif MODE == "crlf_all": text = text.replace("\n", "\r\n"); end = "\r\n"
elif MODE == "nested_nonl": end = "" if dotted else "\n"
elif MODE == "array_nonl": end = "" if array else "\n"
elif MODE == "top_nonl": end = "\n" if dotted else ""
elif MODE == "key_label_nonl": end = "" if kp == "Label" else "\n"
elif MODE == "file_nonl": end = "\n" if scratch else ""
elif MODE == "file_lacking": end = "\n" if scratch else ("" if text.endswith("\n") else "\n")
elif MODE == "interior_nonl": end = "" if "\n" in text[:-1] else "\n"
elif MODE == "nonascii_nonl": end = "" if any(ord(c) > 127 for c in text) else "\n"
elif MODE == "key_ccd_nonl": end = "" if kp.endswith(".CLAUDE_CONFIG_DIR") else "\n"
elif MODE == "index_nonl": end = "" if array and int(kp.rsplit(".", 1)[-1]) >= 1 else "\n"
if nflag and (NMODE == "honour" or (NMODE == "half" and not dotted)):
    end = ""
sys.stdout.write(text + end)
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
_svc_line() {   # $1 the unit, $@ lines: inserted into [Service], before [Install] (a line appended after [Install], which the tests here
                # once did, is one systemd does not read: the read-write lens's harness had the same fault, 2026-09-19)
    local unit="$1" l; shift
    for l in "$@"; do printf '%s\n' "$l"; done > "$unit.ins"
    awk -v ins="$unit.ins" 'BEGIN { while ((getline line < ins) > 0) buf = buf line "\n" } /^\[Install\]/ && !done { printf "%s", buf; done = 1 } { print }' "$unit" > "$unit.new"
    mv -f "$unit.new" "$unit"; rm -f "$unit.ins"
}
_sd() {   # the oracle: a python that reads a unit the way systemd v255 does, written once under $TEST_DIR; prints its path. What it
          # models, how that was checked and where it refuses to guess are in its own header. `has NAME` tells a variable set to the
          # empty string from one not set, which `env NAME` cannot; every mode answers `ERROR: <why>` for a file systemd loads nothing
          # from or refuses to start (a bad section header, a line that is not UTF-8, no ExecStart, two of them, a command systemd
          # refuses), since what systemd hands the manager is then nothing, and a case that expects a value there is wrong.
    local py="$TEST_DIR/sd.py"
    [ -f "$py" ] || cat > "$py" <<'PY'
# The oracle models systemd 255 (255.4-1ubuntu8.17, the box this was written on, 2026-09-19), and that build alone: a claim checked
# against 255.4 says nothing about 256, which may move any rule below. How that was checked: every rule was run against
# `systemd-analyze --user verify` on that box over the boundary cases its comment names (the round-4 probe set: line endings,
# continuations, comments, headers, escapes, names, ExecStart shapes, EnvironmentFile shapes), the case the rule refuses and the case
# it accepts, before the rule was written here; and the whole model is run against systemd by tests/romp-service-differential.py (the
# fold of 2026-09-19, after the oracle lens of round 4 found eleven classes of disagreement), whose fixture set, expected counts and
# systemd version are recorded in that file and in tests/README.md. The function names are systemd v255's (conf-parser.c, fileio.c
# read_line, extract-word.c extract_first_word, escape.c cunescape_one, specifier.c specifier_printf, utf8.c utf8_is_valid,
# path-util.c path_simplify / path_is_valid / filename_is_valid, load-fragment.c config_parse_environ / config_parse_exec /
# config_parse_unit_env_file, service.c service_verify). It models the forms these tests feed it and RAISES on anything outside that
# set (a specifier other than %% and %h, the deprecated %c %r %R included, an ExecStop or SuccessAction that would rescue a unit
# with no ExecStart), so a case leaning on the oracle where it is not modelled
# fails loudly rather than validating against a guess (round 4, extra6-6: the specifier table and the escape set were wrong, and an
# ExecStart path came out as the literal string None). Text is handled as latin-1 so every byte of the file survives; a value is
# written out as bytes. Of service_verify it models the ExecStart count and, since round 6 of fork PR #778 (extra5-2), Restart= beside
# Type=oneshot; the Exec* keys other than ExecStart (ExecStartPre, ExecStop's own command) are not read, a latent gap no case or fixture
# feeds, said here rather than modelled.
import json, os, re, sys
WS = " \t\n\r"          # WHITESPACE: strstrip, the comment test's skip and extract_first_word's separators (not \f or \v: verified,
                        # a form-feed-indented line is an unknown key and a form feed inside a value does not split it)
KNOWN = set("aAbBCdEfgGHiIjJlLmMnNopPqsStTuUvVwWyY")   # systemd.unit(5)'s table on 255, %h and %% apart
KNOWN |= set("crR")     # undocumented and deprecated, and still resolved on 255 (the unit's cgroup path, the slice's, the root's, with a
                        # deprecation warning): the fold, class B, where they were read as letters outside the table and the item dropped
ALNUM = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")   # POSSIBLE_SPECIFIERS less %: ASCII letters and digits
SECTIONS = {"Unit", "Service", "Install"}
RESTARTS = ("no", "on-success", "on-failure", "on-abnormal", "on-watchdog", "on-abort", "always")   # config_parse_service_restart's table
NAME_MAX, PATH_MAX = 255, 4096
class Fatal(Exception): pass
class WordError(Exception): pass    # extract_first_word's -EINVAL, its text saying which form (an unbalanced quote, a trailing backslash,
                                    # an escape cunescape_one refuses)

def read_lines(data):
    # read_line: a line ends at \n, \r or a NUL; after one of them each further terminator of a kind not yet seen in that ending is
    # taken with it, so \r\n and \n\r are one ending and \r\r or \n\n two (verified: a continuation joins across CRLF and LFCR, not
    # across CRCRLF; a bare CR and a NUL split a line)
    lines, cur, i, n = [], bytearray(), 0, len(data)
    while i < n:
        c = data[i]
        if c in (0x0a, 0x0d, 0x00):
            seen = {c}; i += 1
            while i < n and data[i] in (0x0a, 0x0d, 0x00) and data[i] not in seen:
                seen.add(data[i]); i += 1
            lines.append(bytes(cur)); cur = bytearray(); continue
        cur.append(c); i += 1
    if cur: lines.append(bytes(cur))
    return lines

def unichar_is_valid(cp):
    # unichar_is_valid: below the end of the code space, not a surrogate, not a noncharacter (U+FDD0 to U+FDEF, and the last two code
    # points of every plane); cunescape_one applies it to a \U escape and utf8_is_valid to every decoded character
    return cp < 0x110000 and not 0xD800 <= cp <= 0xDFFF and not 0xFDD0 <= cp <= 0xFDEF and (cp & 0xFFFE) != 0xFFFE

def utf8_ok(s):
    # utf8_is_valid: the encoding, then unichar_is_valid on each character (the fold, class C: python's decoder passes a noncharacter,
    # systemd drops an assignment carrying one and refuses the whole file on a line carrying one raw; verified on 255.4)
    try: t = s.encode("latin-1").decode("utf-8")
    except UnicodeError: return False
    return all(unichar_is_valid(ord(c)) for c in t)

ESC = {"\\": "\\", '"': '"', "'": "'", "s": " ", "n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v"}
def cunescape_one(s, i):
    # (text, consumed), or None for an escape systemd refuses: \x needs two hex digits and not 00, an octal three digits below 400 and
    # not 000, \u four hex digits and not 0 (a surrogate or a noncharacter is encoded as bytes, which the assignment check then drops:
    # verified, \ud800 gives three bytes that are not UTF-8), \U eight hex digits and a code point unichar_is_valid accepts (the fold,
    # class D: \U0000D800 and \U0000FFFE are refused by cunescape_one itself, where the oracle refused only 0 and above 10FFFF); an
    # eight-bit byte comes back raw (a latin-1 char), a code point as its UTF-8 bytes
    c = s[i]
    if c in ESC: return ESC[c], 1
    if c == "x":
        h = s[i + 1:i + 3]
        if not re.fullmatch(r"[0-9A-Fa-f]{2}", h): return None
        b = int(h, 16)
        return (chr(b), 3) if b else None
    if c in "01234567":
        o = s[i:i + 3]
        if not re.fullmatch(r"[0-7]{3}", o): return None
        b = int(o, 8)
        return (chr(b), 3) if 0 < b <= 255 else None
    if c in "uU":
        k = 4 if c == "u" else 8
        h = s[i + 1:i + 1 + k]
        if not re.fullmatch(r"[0-9A-Fa-f]{%d}" % k, h): return None
        cp = int(h, 16)
        if cp == 0 or cp > 0x10FFFF: return None
        if c == "U" and not unichar_is_valid(cp): return None
        return chr(cp).encode("utf-8", "surrogatepass").decode("latin-1"), 1 + k
    return None

def extract_first_word(s, i, relax=False):
    # extract_first_word with EXTRACT_UNQUOTE|EXTRACT_CUNESCAPE (and EXTRACT_UNESCAPE_RELAX when relax) from position i: (word, next i)
    # past the separators that follow, or None at the end; WordError for -EINVAL. Inside quotes an end of text is an unbalanced quote
    # (a backslash there too, since the relaxed retry does not save it, which is why systemd reports it as Unbalanced quoting); unquoted,
    # a backslash at the end is kept verbatim under relax and refused otherwise, and an escape cunescape_one refuses is kept as the
    # backslash and the character under relax and refused otherwise
    n = len(s)
    while i < n and s[i] in WS: i += 1
    if i >= n: return None
    w, q = "", None
    while i < n:
        c = s[i]
        if c == "\\":
            i += 1
            if i >= n:
                if q is None and relax: w += "\\"; break
                raise WordError("unbalanced quote" if q is not None else "trailing backslash")
            r = cunescape_one(s, i)
            if r is None:
                if relax: w += "\\" + s[i]; i += 1; continue
                raise WordError("unknown escape")
            w += r[0]; i += r[1]; continue
        if q is not None:
            if c == q: q = None
            else: w += c
            i += 1; continue
        if c in WS: break
        if c in "\"'": q = c; i += 1; continue
        w += c; i += 1
    if q is not None: raise WordError("unbalanced quote")
    while i < n and s[i] in WS: i += 1
    return w, i

def extract_first_word_and_warn(s, i):
    # extract_first_word_and_warn: the strict read, then, on -EINVAL, one retry under EXTRACT_UNESCAPE_RELAX (Ignoring unknown escape
    # sequences); what still fails is reported as Unbalanced quoting
    try: return extract_first_word(s, i)
    except WordError:
        try: return extract_first_word(s, i, relax=True)
        except WordError: raise WordError("unbalanced quote")

def specifiers(w):
    # unit_env_printf / unit_path_printf / unit_full_printf, all specifier_printf: %% is %, a trailing % a %, %h the home (HOME here,
    # which is what the tests mean by it; systemd reads the passwd entry); every other letter of the table (the deprecated %c %r %R
    # with it) expands to a host-, user-, cgroup- or unit-path-dependent value no test feeds, raised; a letter or a digit outside the
    # table fails to resolve (Invalid slot), None, and the caller says what systemd does with the item; a % before any other character
    # is copied with the character (POSSIBLE_SPECIFIERS is alphanumerical: the fold, class A, where a%/b failed to resolve here)
    out, i, n = "", 0, len(w)
    while i < n:
        c = w[i]
        if c == "%":
            if i + 1 >= n: out += "%"; i += 1; continue
            d = w[i + 1]
            if d == "%": out += "%"
            elif d == "h": out += os.environ.get("HOME", "")
            elif d in KNOWN: raise NotImplementedError("the specifier %%%s is not modelled (its value is the host's, the cgroup's or the unit path's)" % d)
            elif d in ALNUM: return None
            else: out += "%" + d
            i += 2; continue
        out += c; i += 1
    return out

def env_name_ok(k):   # env_name_is_valid (verified: A-B, A.B, 1A, an empty name and a non-ASCII letter refused; _A accepted)
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) is not None

def unsafe(p):        # string_is_safe's complement: a quote, a backslash, DEL or a control character
    return any(c in "\"'\\\x7f" or ord(c) < 32 for c in p)

def filename_is_valid(p):   # not empty, not . or .., no slash, at most NAME_MAX bytes
    return p not in ("", ".", "..") and "/" not in p and len(p.encode("latin-1")) <= NAME_MAX

def path_is_valid(p):       # not empty, below PATH_MAX, every component at most NAME_MAX bytes (verified: a 256-byte component fails)
    return p != "" and len(p.encode("latin-1")) < PATH_MAX and all(len(c.encode("latin-1")) <= NAME_MAX for c in p.split("/"))

def path_simplify(p):       # duplicate slashes and . components dropped, .. kept, the leading slash kept (exec->path, not argv[0]: the fold,
                            # class J, where the oracle's path was the written form)
    parts = [c for c in p.split("/") if c not in ("", ".")]
    return ("/" if p.startswith("/") else "") + "/".join(parts) if parts else ("/" if p.startswith("/") else p)

def parse_exec(rv, cmds):
    # config_parse_exec over one rvalue, appending to cmds ({path, argv, ignore}); returns None, or the text of a fatal error. Word by word
    # as systemd reads it: the first word through extract_first_word_and_warn (a failure there yields nothing more from the line, the
    # commands before it standing); a first word that is exactly ; (unquoted or quoted) separates; the prefix characters each once, `!!`
    # the one pair, + and ! exclusive, a repeated or conflicting one left in the path (the fold, class G); the path through the
    # specifiers, then Empty path, string_is_safe, a trailing slash, path_is_valid or filename_is_valid (the fold, class I); argv[0] is
    # the written path unless @ separates it (the fold, class F), and exec->path the simplified one; the arguments through the raw-text
    # checks for an unquoted ; and a \; before each word (the fold, class H); with the - prefix every error after the first word drops
    # that command and the rest of the line with a warning (the fold, class K), without it the unit fails
    p, n = 0, len(rv)
    while True:
        try: r = extract_first_word_and_warn(rv, p)
        except WordError: return None                                  # Unbalanced quoting, ignoring: nothing more from the line
        if r is None: return None
        first, p = r
        if first == ";": continue                                       # a lone ; is a separator (verified: `;` first, quoted too)
        flags, sep0, f = set(), False, 0
        while f < len(first):
            ch = first[f]
            if ch == "-" and "ignore" not in flags: flags.add("ignore")
            elif ch == "@" and not sep0: sep0 = True
            elif ch == ":" and "noenv" not in flags: flags.add("noenv")
            elif ch == "+" and not flags & {"priv", "nosetuid", "ambient"}: flags.add("priv")
            elif ch == "!" and not flags & {"priv", "nosetuid", "ambient"}: flags.add("nosetuid")
            elif ch == "!" and not flags & {"priv", "ambient"}: flags.discard("nosetuid"); flags.add("ambient")
            else: break
            f += 1
        ignore = "ignore" in flags
        def fail(msg):
            return None if ignore else msg
        path = specifiers(first[f:])
        if path is None: return fail("Failed to resolve unit specifiers in the ExecStart command: the unit will not be started")
        if path == "": return fail("Empty path in command line: the unit will not be started")
        if unsafe(path): return fail("Executable name contains special characters: " + path)
        if path.endswith("/"): return fail("Executable path specifies a directory: " + path)
        if not (path_is_valid(path) if path.startswith("/") else filename_is_valid(path)):
            return fail("Neither a valid executable name nor an absolute path: " + path)
        argv = [] if sep0 else [path]
        path = path_simplify(path)
        semicolon = False
        while p < n:
            if rv[p] == ";" and (p + 1 >= n or rv[p + 1] in WS):
                p += 1
                while p < n and rv[p] in WS: p += 1
                semicolon = True; break
            if rv[p] == "\\" and rv[p + 1:p + 2] == ";" and (p + 2 >= n or rv[p + 2] in WS):
                argv.append(";"); p += 2
                while p < n and rv[p] in WS: p += 1
                continue
            try: r = extract_first_word_and_warn(rv, p)
            except WordError: return fail("Unbalanced quoting in an ExecStart argument: the unit will not be started")
            if r is None: break
            word, p = r
            a = specifiers(word)
            if a is None: return fail("Failed to resolve unit specifiers in an ExecStart argument: the unit will not be started")
            argv.append(a)
        if not argv: return fail("Empty executable name or zeroeth argument: the unit will not be started")
        cmds.append({"path": path, "argv": argv, "ignore": ignore})
        if not semicolon: return None

def parse(path):
    data = open(path, "rb").read()
    st = {"sec": None, "env": {}, "execs": [], "envfiles": [], "etype": "simple", "rescue": False, "restart": "no"}
    def line(p, ln):
        s = p.strip(WS)
        if not s: return
        if not utf8_ok(s): raise Fatal("String is not UTF-8 clean (line %d): the unit fails to load" % ln)
        if s[0] == "[":
            # the name is what lies between [ and the LAST character, which must be ]; a bad header is fatal for the whole file
            # (verified: [Instal, [Service]x, [Install]   # comment, [Ser"vice], a control character; [Ser vice], [], [Ser.vice] and
            # [Service]] are only unknown sections, ignored with a warning, and an X- section silently)
            if s[-1] != "]": raise Fatal("Invalid section header %s (line %d): the unit fails to load" % (s, ln))
            name = s[1:-1]
            if unsafe(name): raise Fatal("Bad characters in section header %s (line %d): the unit fails to load" % (s, ln))
            st["sec"] = name if name in SECTIONS else None
            return
        if "=" not in s: return                                            # Missing '=', ignoring line (verified)
        lv, rv = s.split("=", 1); lv, rv = lv.strip(WS), rv.strip(WS)
        if st["sec"] != "Service": return                                  # outside a section or in another one: ignored
        if lv == "Type": st["etype"] = rv; return
        if lv == "Restart":
            if rv in RESTARTS: st["restart"] = rv                          # a value outside the table, the empty one included, is Failed to parse
            return                                                         # service restart specifier, ignoring: the earlier value stands (verified)
        if lv in ("ExecStop", "SuccessAction"): st["rescue"] = True; return
        if lv == "Environment":
            if rv == "": st["env"] = {}; return
            # config_parse_environ commits each item as it goes (verified: `1A=1 B=\q` warns on 1A first, then Invalid syntax), so the
            # items before a failing one stand and the failing one and the rest of the line are dropped
            i = 0
            while True:
                try: r = extract_first_word(rv, i)
                except WordError: return                                   # Invalid syntax, ignoring: the rest of the line
                if r is None: return
                w, i = r
                res = specifiers(w)
                if res is None: continue                                   # Failed to resolve specifiers, ignoring (the item)
                k, sep, v = res.partition("=")
                if sep and env_name_ok(k) and utf8_ok(v): st["env"][k] = v  # env_assignment_is_valid (verified: \xff in a value drops it)
            return
        if lv == "ExecStart":
            if rv == "": st["execs"] = []; return
            err = parse_exec(rv, st["execs"])
            if err is not None: raise Fatal(err)
            return
        if lv == "EnvironmentFile":
            if rv == "": st["envfiles"] = []; return
            r = specifiers(rv)
            if r is None: return                                           # Failed to resolve unit specifiers, ignoring
            pfx, fp = ("-", r[1:]) if r.startswith("-") else ("", r)
            if not fp.startswith("/"): return                              # EnvironmentFile= path is not absolute, ignoring (a quoted path too)
            fp = path_simplify(fp)                                         # path_simplify_and_warn: -/x//y/env is -/x/y/env, /x/./env and /x/env/ are
                                                                           # /x/env (the round-5 preface of fork PR #778, verified on 255.4; the
                                                                           # differential's fold batch carries the forms)
            if ".." in fp.split("/"): return                               # EnvironmentFile= path is not normalized, ignoring (verified: /x/../env reads no file)
            st["envfiles"].append((pfx, fp))
    cont = None
    bom = False
    ln = 0
    for ln, raw in enumerate(read_lines(data), 1):
        l = raw.decode("latin-1")
        if l.lstrip(WS)[:1] in ("#", ";"): continue                       # a comment, skipped before the mark strip and before a continuation joins (verified)
        if not bom and l.startswith("\xef\xbb\xbf"): l = l[3:]; bom = True   # the FIRST UTF-8 byte order mark at the raw start of a line, anywhere
                                                                           # in the file, and no other: config_parse's one latch (round 6 of fork PR
                                                                           # #778, correctness-1 and extra5-1; verified on 255.4: a marked comment
                                                                           # is no comment and spends the latch, a second mark and a mark after a
                                                                           # blank are text; line 1 alone had it here, the reader's own rule)
        p = (cont + l) if cont is not None else l
        esc = False
        for ch in p:
            if esc: esc = False
            elif ch == "\\": esc = True
        if esc: cont = p[:-1] + " "; continue                              # the trailing backslash becomes a blank, the next line joins
        cont = None
        line(p, ln)
    if cont is not None: line(cont, ln + 1)                                # config_parse parses a continuation still pending at the end of
                                                                           # the file (the fold, class E: it was never parsed here)
    # service_verify (verified: no ExecStart refused for Type=simple and Type=oneshot alike; two refused unless Type=oneshot)
    if not st["execs"]:
        if st["rescue"]: raise NotImplementedError("a unit with no ExecStart and an ExecStop or SuccessAction is not modelled")
        raise Fatal("Service has no ExecStart=, ExecStop=, or SuccessAction=: Refusing")
    if len(st["execs"]) > 1 and st["etype"] != "oneshot": raise Fatal("Service has more than one ExecStart= setting, which is only allowed for Type=oneshot services: Refusing")
    # service_verify's next rule (round 6 of fork PR #778, extra5-2: romp's unit carries Restart=always, so a case planting Type=oneshot into it
    # read a command list from a file systemd loads nothing from; verified on 255.4: always and on-success refuse, on-failure loads)
    if st["etype"] == "oneshot" and st["restart"] in ("always", "on-success"): raise Fatal("Service has Restart= set to either always or on-success, which isn't allowed for Type=oneshot services: Refusing")
    return st["env"], st["execs"], st["envfiles"]

what = sys.argv[2]
try:
    env, execs, envfiles = parse(sys.argv[1])
except Fatal as e:
    out = "ERROR: %s" % e
else:
    if what == "env": out = env.get(sys.argv[3], "")
    elif what == "has": out = "yes" if sys.argv[3] in env else "no"
    elif what == "exec0": out = execs[0]["path"]                           # exec->path, the simplified one systemd runs and verifies
    elif what == "execn": out = str(len(execs[0]["argv"]))                 # systemd's argv: the path is in it unless @ separated it
    elif what == "arg": out = execs[0]["argv"][int(sys.argv[3])]           # one argument's text (the fold's addendum: the count alone let a
                                                                           # \; kept as two characters pass as the argument ;)
    elif what == "execs": out = str(len(execs))
    elif what == "envfile": out = envfiles[0][1] if envfiles else ""
    elif what == "dump": out = json.dumps({"env": env, "execs": execs, "envfiles": [{"prefix": a, "path": b} for a, b in envfiles]}, ensure_ascii=False)
    else: raise SystemExit("unknown mode %r" % what)
sys.stdout.buffer.write(out.encode("latin-1") + b"\n")
PY
    printf '%s' "$py"
}
_sd_read() {   # $1 the unit, $2 env NAME | has NAME | exec0 | execn | arg N | execs | envfile: what systemd reads, through the oracle
    python3 "$(_sd)" "$@"
}
_unit_env_value() {   # $1 the unit, $2 a name: the value systemd reads for it (the oracle above; the shlex of round 3 was not systemd's reading)
    _sd_read "$1" env "$2"
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

@test "rewrite (Linux): a hand-quoted instance line with whitespace goes back in the writer's form, the same bytes, and reads back whole; an install writes a value with whitespace, a % or a backslash in the quoted form systemd reads whole, a plain one unquoted as before" {
    # Round 3 (extra6-2): round 2 taught the reader to MATCH a quoted Environment= line for every key, and only PATH was
    # written back verbatim; an instance value read out of a quoted line was re-emitted unquoted, and systemd cuts an
    # unquoted item at whitespace (systemd.exec(5) Environment=, systemd.syntax(7) Quoting). The written line is parsed
    # here the way systemd parses it (_unit_env_value, the oracle). The addendum to round 3 (2026-09-19) writes the value
    # back through the one writer instead of replaying the line; for these lines that is the same bytes.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" cc="$TEST_DIR/claude cfg dir" st="$TEST_DIR/pct%dir"
    _old_unit "$unit"
    _svc_line "$unit" 'Environment="CLAUDE_CONFIG_DIR='"$cc"'"' 'Environment="ROMP_STATE_DIR='"$TEST_DIR"'/pct%%dir"'   # hand-quoted, the doubled % systemd wants
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite                      # the clean shell
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR='"$cc"'"' "$unit"                           # the writer's form: quoted, the same bytes
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

# ─── the mutation pass over round 3 (2026-09-19): the pins the reviewer's mutation lens found missing ───────────
# Each case reds under one mutation of bin/romp-service that the round-3 cases left green: the plutil reader's branch
# for a Label that does not extract returning 0, _xml_unescape decoding a reference twice, and the ROMP_PLUTIL knob
# ignored (this host has no plutil, so the knob and the default resolved the same reader in every round-3 case). The
# pass's fourth case, an unquoted %h specifier replayed as written, is retired by the addendum to round 3 below, which
# refuses a specifier as a form the reader does not read whole.

@test "rewrite (macOS): through plutil, a plist from which no Label extracts (no Label entry, or not a plist at all) is refused, exit 5 and byte for byte, nothing read out of it, on rewrite, rewrite --check and the marked child's install" {
    # Mutation pass (2026-09-19): the round-3 cases drove the plutil reader with a Label present (romp's, or another
    # label), so the branch for a Label that does not extract could return 0 with every case green; the stand-in then
    # read the values out of the file, and a plist with no Label was rewritten at exit 0.
    unset ROMP_SERVICE_NO_LOAD
    _plutil_stub
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$plist" "$plist.romp"
    # every entry romp writes except Label (re-saved, so the stand-in parses it and finds no Label)
    python3 - "$plist" <<'PY'
import plistlib, sys
with open(sys.argv[1], "rb") as f:
    d = plistlib.load(f)
del d["Label"]
with open(sys.argv[1], "wb") as f:
    plistlib.dump(d, f)
PY
    cp "$plist" "$plist.nolabel"
    printf 'not a property list\n' > "$plist.text"                     # not a plist at all: the parser refuses it
    local shape
    for shape in nolabel text; do
        cp "$plist.$shape" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"plutil could not extract its Label entry"* ]]
        [[ "$output" == *"not a plist launchd would load, or one with no Label"* ]]
        [[ "$output" == *"nothing was rewritten"* ]]
        [[ "$output" == *"romp-service install from the shell and clone that should own the service"* ]]
        [[ "$output" != *"Rewrote"* ]]
        cmp -s "$plist" "$plist.$shape"
        [ ! -e "$plist.tmp" ]
        run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
        [ "$status" -ne 0 ]                                              # nothing journaled
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"plutil could not extract its Label entry"* ]]
        [[ "$output" != *"agree"* ]]
        cmp -s "$plist" "$plist.$shape"
        run env -i HOME="$HOME" PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
            ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"plutil could not extract its Label entry"* ]]
        cmp -s "$plist" "$plist.$shape"                                  # the marked child wrote nothing either
    done
    # the control: romp's own plist, through the same stand-in, reads and rewrites
    cp "$plist.romp" "$plist"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
}

@test "rewrite (macOS): ROMP_PLUTIL names the reader: a plutil named by path reads a re-saved plist with none on PATH, and a path that does not exist runs the one-line fallback past a plutil that is on PATH" {
    # Mutation pass (2026-09-19): this host has no plutil, so with the knob ignored (PLUTIL=plutil) every round-3 case
    # still resolved the reader it asked for: the stand-in was on PATH under that name where the knob named it, and the
    # knob's path that does not exist found nothing where the default found nothing either. Told apart both ways here.
    unset ROMP_SERVICE_NO_LOAD
    _plutil_stub
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$plist" "$plist.romp"
    # the knob by path, the stand-in NOT on PATH under any name: a binary plist reads through it
    _resave "$plist" binary
    ROMP_PLUTIL="$TEST_DIR/plutil-bin/plutil" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
    grep -q '<key>Label</key><string>com.romp.manager</string>' "$plist"
    # the knob at a path that does not exist, the stand-in ON PATH as plutil: the fallback runs and refuses the re-saved form
    cp "$plist.romp" "$plist"
    _resave "$plist" xml
    cp "$plist" "$plist.saved"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_PLUTIL="$TEST_DIR/no-plutil-here" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"no plutil is available"* ]]
    cmp -s "$plist" "$plist.saved"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_PLUTIL="$TEST_DIR/no-plutil-here" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    cmp -s "$plist" "$plist.saved"
    # the control: the same PATH with the knob unset reads it
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '<key>ROMP_KERNEL_PORT</key><string>29866</string>' "$plist"
}

@test "rewrite (macOS): the one-line reader undoes &amp; last: a value whose text is an entity (&lt;, &gt;) reads back as written, agrees with the owning shell and is unchanged by a clean-shell rewrite" {
    # Mutation pass (2026-09-19): the round-3 escaping cases carried &, <, > and a quote, which decode the same in any
    # order; a value whose TEXT is an entity (a directory named with &lt;) is written as &amp;lt; and, undone in the
    # wrong order, decodes twice to <, so the owning shell was refused over a path it never changed and a clean-shell
    # rewrite wrote the doubly decoded value back. The fallback reader alone: plutil decodes itself.
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here"
    local envf="$TEST_DIR/lit &lt;x dir/service.env" cc="$TEST_DIR/cc &gt; dir"
    mkdir -p "$cc"
    ROMP_PLUTIL="$none" ROMP_SERVICE_ENV_FILE="$envf" CLAUDE_CONFIG_DIR="$cc" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qF '<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/lit &amp;lt;x dir/service.env</string>' "$plist"   # escaped once: the & of the text
    grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>'"$TEST_DIR"'/cc &amp;gt; dir</string>' "$plist"
    [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_SERVICE_ENV_FILE)" = "$envf" ]
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR)" = "$cc" ]
    cp "$plist" "$plist.once"
    ROMP_PLUTIL="$none" ROMP_SERVICE_ENV_FILE="$envf" CLAUDE_CONFIG_DIR="$cc" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite   # the owning shell agrees
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.once"
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite                                                            # the clean shell changes nothing
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.once"
    [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_SERVICE_ENV_FILE)" = "$envf" ]
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR)" = "$cc" ]
    # a shell carrying the doubly decoded text is a DIFFERENT value, refused naming the file's as written
    ROMP_PLUTIL="$none" ROMP_SERVICE_ENV="$TEST_DIR/lit <x dir/service.env" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"the file reads $envf, this environment names $TEST_DIR/lit <x dir/service.env"* ]]
    cmp -s "$plist" "$plist.once"
}

# ─── the addendum to round 3 (2026-09-19): the readers refuse what they cannot read whole, every written value reads back ───
# Two pre-run lenses over the round-3 head. The plist-road lens: a one-line plist with ONE entry split across two lines passed
# the two-marker form check and read that entry as absent (its medium); the fallback's ExecStart read took the line before
# <string>up</string> whatever it was (its low). The read-write trace, D1 to D8: ROMP_DIR and ExecStart written bare, the
# single quote unquoted, a specifier taken literally, `Key = Value` read as absent, a continuation replayed, the compare
# decoding unlike systemd, a numeric character reference kept as text. The rule the cases below pin, stated in
# bin/romp-service's header and docs/reference.md: a reader that cannot read a form WHOLE refuses it (exit 5, nothing
# written, the form and the remedy named); a value the reader accepts is written back in a form systemd or launchd reads
# IDENTICALLY, which these cases verify by parsing the written file the way the daemon does (_sd_read, _plist_get).

@test "rewrite (macOS): without plutil, romp's own plist with ONE entry split across two lines by hand (PATH, StandardOutPath, an instance entry) is refused, exit 5 and byte for byte with no audit row, on rewrite, rewrite --check and the marked child's install; through the plutil stand-in the split entry reads exactly" {
    # the plist-road lens's medium: round 3's assertion was two markers (Label, ROMP_SUPERVISED), so an editor's split of any
    # OTHER entry passed it and that entry read as absent: PATH dropped, the log paths moved to the caller's HOME at exit 0 with
    # the success line, --check blessing it first. The reader now asserts every entry it reads is on one line with its <string>.
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here" k
    mkdir -p "$TEST_DIR/pathbin" "$TEST_DIR/xdg"
    PATH="$TEST_DIR/pathbin:$PATH" XDG_STATE_HOME="$TEST_DIR/xdg" ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$plist" "$plist.romp"
    local path_v; path_v="$(_plist_get "$plist" EnvironmentVariables.PATH)"
    [ "$(_plist_get "$plist" StandardOutPath)" = "$TEST_DIR/xdg/romp/manager.log" ]     # not the caller's HOME default
    for k in PATH StandardOutPath ROMP_KERNEL_PORT; do
        awk -v k="$k" '{ t = "<key>" k "</key>"; if (index($0, t "<string>") > 0) { i = index($0, t) + length(t); print substr($0, 1, i - 1); print "    " substr($0, i) } else print }' "$plist.romp" > "$plist"
        grep -qx "  *<key>$k</key>" "$plist"                                            # the hand form: key alone on its line
        [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_KERNEL_PORT)" = 29866 ]     # launchd still reads every entry
        cp "$plist" "$plist.split"
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"its $k entry is split across lines"* ]]
        [[ "$output" == *"reads an entry whole or not at all"* ]]
        [[ "$output" == *"nothing was rewritten"* ]]
        [[ "$output" != *"Rewrote"* ]]
        cmp -s "$plist" "$plist.split"
        [ ! -e "$plist.tmp" ]
        run grep -c '"action": "service-rewrite"' "$TEST_DIR/xdg/romp/restart-audit.jsonl" "$XDG_STATE_HOME/romp/restart-audit.jsonl"
        [ "$status" -ne 0 ]                                                             # nothing journaled, under either root
        [ ! -e "$XDG_STATE_HOME/romp/manager.log" ]                                     # and the log paths never moved here
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"its $k entry is split across lines"* ]]
        cmp -s "$plist" "$plist.split"
        run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
            ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"its $k entry is split across lines"* ]]
        cmp -s "$plist" "$plist.split"
        # through plutil the split entry is an entry: read exactly, kept, the log paths where they were
        _plutil_stub
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 0 ]
        [ "$(_plist_get "$plist" EnvironmentVariables.PATH)" = "$path_v" ]
        [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_KERNEL_PORT)" = 29866 ]
        [ "$(_plist_get "$plist" StandardOutPath)" = "$TEST_DIR/xdg/romp/manager.log" ]
        grep -qF "<key>$k</key><string>" "$plist"                                       # written back in romp's one-line form
    done
}

@test "rewrite (macOS): without plutil, a ProgramArguments array collapsed onto one line is refused as a form not read whole, exit 5 and byte for byte on all three roads, never as another clone; through the plutil stand-in the manager's path reads exactly" {
    # the plist-road lens's low: the fallback's ExecStart read printed the line before <string>up</string> whatever it was, so
    # the collapsed array yielded `<key>ProgramArguments</key>` as the manager's path and the OWNING clone was refused as
    # another clone, the operator sent to re-run from the clone they were in. Safe (nothing written) and wrong on both counts.
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here"
    ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    awk 'BEGIN { a = 0 } /^[[:space:]]*<array>/ { a = 1; buf = $0; next } a == 1 { sub(/^[[:space:]]*/, ""); buf = buf $0; if ($0 ~ /<\/array>/) { print buf; a = 0 }; next } { print }' "$plist" > "$plist.new"
    mv -f "$plist.new" "$plist"
    grep -qE '^ *<array><string>.*<string>up</string></array>$' "$plist"                 # the hand form, one line
    [ "$(_plist_get "$plist" ProgramArguments.1)" = "$ROMP_MANAGER_BIN" ]               # which launchd reads whole
    cp "$plist" "$plist.array"
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"its ProgramArguments array is not one <string> a line ending in <string>up</string>"* ]]
    [[ "$output" == *"reads the array whole or not at all"* ]]
    [[ "$output" != *"this clone would write"* ]]                                       # not a false other-clone diagnosis
    [[ "$output" != *"ProgramArguments</key>, this clone"* ]]
    cmp -s "$plist" "$plist.array"
    run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
    [ "$status" -ne 0 ]
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ProgramArguments array is not one <string> a line"* ]]
    cmp -s "$plist" "$plist.array"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
        ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ProgramArguments array is not one <string> a line"* ]]
    cmp -s "$plist" "$plist.array"
    # a plist with no <string>up</string> line at all is the same refusal, never an absent ExecStart re-pointed at this clone
    sed 's|<string>up</string>|<string>start</string>|' "$plist.array" > "$plist"
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ProgramArguments array is not one <string> a line"* ]]
    # through plutil the collapsed array reads: the owning clone is accepted and the path written back one string a line
    cp "$plist.array" "$plist"
    _plutil_stub
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_plist_get "$plist" ProgramArguments.1)" = "$ROMP_MANAGER_BIN" ]
    grep -qx "    <string>$ROMP_MANAGER_BIN</string>" "$plist"
    ROMP_MANAGER_BIN="$TEST_DIR/other/romp-manager" PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $TEST_DIR/romp-manager, this clone would write $TEST_DIR/other/romp-manager"* ]]
}

@test "unit: every value systemd word-splits is written in the form it reads back as that value, on the install road and the rewrite road: a space, a double quote, a single quote, a backslash, a percent and a leading dash in ROMP_DIR, an instance variable and the service.env path, a space, a percent and a leading dash in ExecStart; a hand-quoted ROMP_DIR line and ExecStart are accepted and written in the writer's form; a manager path with a quote, a backslash or a control character (a tab), which systemd refuses as an executable name, is refused on install and rewrite with nothing written" {
    # the read-write lens, D1, D2 and D7: ROMP_DIR was written bare on both roads (a hand-quoted line that systemd read whole was
    # decoded, agreed, and written back bare, which systemd cut at the space, %-expanded or dropped), the install road's quoting
    # class missed the single quote (systemd dropped the whole line as unbalanced), and ExecStart's path went bare on every road.
    # One writer now, _unit_word; the oracle (_sd_read) parses the written file as systemd does.
    # The second pass over the addendum (N07): systemd v255 refuses ANY ExecStart command path with a quote, a backslash or a
    # control character (string_is_safe: "Executable name contains special characters", the unit fails to load, verified with
    # systemd-analyze --user verify), so no written form of such a path reads back; this case had installed the manager at one
    # and asserted the oracle read it back. ExecStart's round-trip leg keeps the characters that do round-trip (a space, a
    # percent, a leading dash), the quote and the backslash are a refusal leg on both roads, and the oracle models the check.
    unset ROMP_SERVICE_NO_LOAD
    local odd="$TEST_DIR/o sp\"q 'a' b\\s 100% -d" unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mdir="$TEST_DIR/m sp 100% -d/mgr"
    local svc2="$odd/bin/romp-service" mgr="$mdir/romp-manager" cc="$odd/claude" envf="$odd/service.env" bad
    mkdir -p "$odd/bin" "$odd/mgr" "$mdir" "$cc"
    cp "$SVC" "$svc2"                                                                     # ROMP_DIR is the clone the script runs from
    # the refusal legs first, no unit on disk: a double quote, a backslash, a control character (a tab: round 4, tests-4, the arm
    # had no case) and the path with all three; exit 5, no unit written, nothing journaled, the reason and the remedy named
    for bad in "$TEST_DIR/q\"uote/romp-manager" "$TEST_DIR/b\\slash/romp-manager" "$TEST_DIR/t	ab/romp-manager" "$odd/mgr/romp-manager"; do
        ROMP_MANAGER_BIN="$bad" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 run "$svc2" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"the manager's path ($bad) contains a quote, a backslash or a control character"* ]]
        [[ "$output" == *"Executable name contains special characters"* ]]
        [[ "$output" == *"nothing was written"* ]]
        [[ "$output" == *"Move the clone to a path without those characters"* ]]
        [ ! -e "$unit" ]
        [ ! -e "$unit.tmp" ]
        [ ! -e "$XDG_STATE_HOME/romp/restart-audit.jsonl" ]
    done
    ROMP_MANAGER_BIN="$mgr" CLAUDE_CONFIG_DIR="$cc" ROMP_SERVICE_ENV_FILE="$envf" ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$svc2" install >/dev/null
    [ "$(_sd_read "$unit" env ROMP_DIR)" = "$odd" ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$cc" ]
    [ "$(_sd_read "$unit" env ROMP_SERVICE_ENV_FILE)" = "$envf" ]
    [ "$(_sd_read "$unit" envfile)" = "$envf" ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    [ "$(_sd_read "$unit" execn)" = 2 ]                                                   # the path and `up`, nothing split off
    [ "$(_sd_read "$unit" env ROMP_KERNEL_PORT)" = 29866 ]
    grep -qxF 'Environment=ROMP_KERNEL_PORT=29866' "$unit"                                # a plain value stays bare, as before
    grep -qxF 'Environment=ROMP_SUPERVISED=1' "$unit"
    grep -q '^ExecStart="' "$unit"                                                        # the quoted form where it is needed
    grep -q '^Environment="ROMP_DIR=' "$unit"
    cp "$unit" "$unit.installed"
    # the rewrite road from a clean shell: the same values read back, the file byte for byte the install's
    local stub; stub="$(_systemctl_stub active)"
    ROMP_MANAGER_BIN="$mgr" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite
    [ "$status" -eq 0 ]
    cmp -s "$unit" "$unit.installed"
    ROMP_MANAGER_BIN="$mgr" CLAUDE_CONFIG_DIR="$cc" ROMP_SERVICE_ENV_FILE="$envf" ROMP_KERNEL_PORT=29866 ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite
    [ "$status" -eq 0 ]                                                                   # the owning shell agrees
    # the marked update child's install road over the file: the same bytes
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_MANAGER_BIN="$mgr" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 \
        ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" XDG_STATE_HOME="$XDG_STATE_HOME" "$svc2" install
    [ "$status" -eq 0 ]
    cmp -s "$unit" "$unit.installed"
    # a hand-quoted ROMP_DIR line and ExecStart in systemd's other form (single quotes, \' and \\ escapes, %%), which systemd
    # reads whole: accepted as the owning clone, written back in the writer's form, and read back as the same value
    local hq="${odd//\\/\\\\}"; hq="${hq//\'/\\\'}"; hq="${hq//%/%%}"
    local hm="${mgr//\\/\\\\}"; hm="${hm//\'/\\\'}"; hm="${hm//%/%%}"
    grep -v -e '^Environment="ROMP_DIR=' -e '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" "Environment='ROMP_DIR=$hq'" "ExecStart='$hm' up"
    [ "$(_sd_read "$unit" env ROMP_DIR)" = "$odd" ]                                       # the hand form reads whole to systemd
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    ROMP_MANAGER_BIN="$mgr" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" != *"this clone would write"* ]]
    cmp -s "$unit" "$unit.installed"                                                      # the writer's form again
    [ "$(_sd_read "$unit" env ROMP_DIR)" = "$odd" ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    # a hand ExecStart whose quoted path carries a double quote, a single quote and a backslash: systemd reads the word whole and
    # then refuses it as an executable name (the oracle reads the ERROR marker, where it read the path back before), so the line
    # is a form not read whole: refused, exit 5, the file untouched, on rewrite, rewrite --check and the marked child's install
    local hb="$odd/mgr/romp-manager"; hb="${hb//\\/\\\\}"; hb="${hb//\"/\\\"}"; hb="${hb//%/%%}"
    grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" "ExecStart=\"$hb\" up"
    [ "$(_sd_read "$unit" exec0)" = "ERROR: Executable name contains special characters: $odd/mgr/romp-manager" ]
    cp "$unit" "$unit.hand"
    ROMP_MANAGER_BIN="$odd/mgr/romp-manager" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"is in a form this rewrite does not read whole"* ]]
    [[ "$output" == *"ExecStart's command path contains a quote, a backslash or a control character"* ]]
    [[ "$output" == *"Move the clone to a path without those characters"* ]]
    [[ "$output" != *"Rewrote"* ]]
    cmp -s "$unit" "$unit.hand"
    [ ! -e "$unit.tmp" ]
    ROMP_MANAGER_BIN="$odd/mgr/romp-manager" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite --check
    [ "$status" -eq 5 ]
    cmp -s "$unit" "$unit.hand"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_MANAGER_BIN="$odd/mgr/romp-manager" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 \
        ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" XDG_STATE_HOME="$XDG_STATE_HOME" "$svc2" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart's command path contains a quote, a backslash or a control character"* ]]
    cmp -s "$unit" "$unit.hand"
    # a unit with no ExecStart line, rewritten from a clone at such a path: the path this clone WOULD write is the refusal, on
    # --check too, so the kernel's preflight ends such a deploy before the tree moves
    grep -v '^ExecStart=' "$unit.installed" > "$unit"
    cp "$unit" "$unit.noexec"
    ROMP_MANAGER_BIN="$odd/mgr/romp-manager" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"the manager's path ($odd/mgr/romp-manager) contains a quote, a backslash or a control character"* ]]
    [[ "$output" != *"agree"* ]]
    ROMP_MANAGER_BIN="$odd/mgr/romp-manager" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite
    [ "$status" -eq 5 ]
    cmp -s "$unit" "$unit.noexec"
    [ "$(grep -c -- '--user daemon-reload' "$TEST_DIR/systemctl-calls")" -eq 3 ]          # the three accepted rewrites above reloaded; no refused one did
    # the control: the same characters in ROMP_DIR, the instance variable and the service.env path stayed accepted above (systemd
    # puts the rule on the executable name alone), and the accepted ExecStart path round-trips with its space, percent and dash
    ROMP_MANAGER_BIN="$mgr" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$svc2" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
}

@test "rewrite (Linux): systemd's blank-padded form, Environment = X=y and ExecStart = /p up, is read as systemd reads it: an ExecStart naming another clone is refused and never re-pointed, and the owning clone's padded lines are accepted with the port kept" {
    # the read-write lens, D4: `Key = Value` read as absent to round 3's anchored regexes, so the port line was dropped and an
    # ExecStart naming another clone was silently re-pointed at this one, past the identity guard.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" road
    _old_unit "$unit"
    sed "s|^ExecStart=\(.*\)\$|ExecStart = \1|" "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" "Environment = ROMP_KERNEL_PORT=31855"
    [ "$(_sd_read "$unit" env ROMP_KERNEL_PORT)" = 31855 ]                                # systemd's reading of the padded form
    [ "$(_sd_read "$unit" exec0)" = "$ROMP_MANAGER_BIN" ]
    local stub; stub="$(_systemctl_stub active)"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_KERNEL_PORT=29866 ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]                                                                   # the padded line's value is compared
    [[ "$output" == *"ROMP_KERNEL_PORT: the file carries 31855, this environment carries 29866"* ]]
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env ROMP_KERNEL_PORT)" = 31855 ]                                # kept, in the writer's form
    grep -qxF 'Environment=ROMP_KERNEL_PORT=31855' "$unit"
    grep -qxF "ExecStart=$ROMP_MANAGER_BIN up" "$unit"
    # another clone's ExecStart, padded: refused on every road, the file untouched
    mkdir -p "$TEST_DIR/other"
    sed "s|^ExecStart=.*\$|ExecStart = $TEST_DIR/other/romp-manager up|" "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    [ "$(_sd_read "$unit" exec0)" = "$TEST_DIR/other/romp-manager" ]
    cp "$unit" "$unit.other"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $TEST_DIR/other/romp-manager, this clone would write $ROMP_MANAGER_BIN"* ]]
    cmp -s "$unit" "$unit.other"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    cmp -s "$unit" "$unit.other"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
        ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $TEST_DIR/other/romp-manager"* ]]
    cmp -s "$unit" "$unit.other"
}

@test "rewrite (Linux): a specifier written by hand (%h in an instance line, in ExecStart, in EnvironmentFile) is a form the reader does not read whole: refused, exit 5, the line and the specifier named, nothing written or journaled, on rewrite, rewrite --check and the marked child's install; %% is a literal % and reads" {
    # the read-write lens, D3: systemd expands %h before the manager sees the value, and round 3's reader took the text literally
    # (a state root under a relative %h/ in the caller's working directory, an EnvironmentFile re-doubled into a path that is
    # not absolute, the shell carrying the expanded value refused). The mutation pass had pinned the opposite for an instance
    # line, replaying it as written; a replay keeps the text and not the reading, so the form is refused under the rule.
    unset ROMP_SERVICE_NO_LOAD
    cd "$TEST_DIR"                                                                        # where a literal %h/ would have been created
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" form stub rows; stub="$(_systemctl_stub active)"
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    rows="$(grep -c '"action": "service-install"' "$XDG_STATE_HOME/romp/restart-audit.jsonl")"   # _old_unit's own install journaled one
    for form in 'Environment=ROMP_STATE_DIR=%h/.local/state/romp' 'Environment="CLAUDE_CONFIG_DIR=%h/.claude-romp"' 'EnvironmentFile=-%h/.config/romp/service.env' 'ExecStart=%h/bin/romp-manager up'; do
        cp "$unit.clean" "$unit"
        case "$form" in EnvironmentFile=*|ExecStart=*) grep -v "^${form%%=*}=" "$unit" > "$unit.new" && mv -f "$unit.new" "$unit" ;; esac
        _svc_line "$unit" "$form"
        cp "$unit" "$unit.hand"
        ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"is in a form this rewrite does not read whole"* ]]
        [[ "$output" == *"specifier %h"* ]]
        [[ "$output" == *"nothing was rewritten"* ]]
        [[ "$output" == *"Write the absolute path in its place"* ]]
        [[ "$output" != *"this clone would write"* ]]
        cmp -s "$unit" "$unit.hand"
        [ ! -e "$unit.tmp" ]
        [ ! -e "$TEST_DIR/%h" ]
        run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
        [ "$status" -ne 0 ]
        ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"specifier %h"* ]]
        cmp -s "$unit" "$unit.hand"
        run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
            ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"specifier %h"* ]]
        cmp -s "$unit" "$unit.hand"
        [ "$(grep -c '"action": "service-install"' "$XDG_STATE_HOME/romp/restart-audit.jsonl")" = "$rows" ]   # the refused install journaled nothing
    done
    # %% is a literal % to systemd and to the reader: read, and written back doubled in the quoted form
    cp "$unit.clean" "$unit"
    _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/pct%%dir'
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/pct%dir" ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR=/x/pct%%dir"' "$unit"
    CLAUDE_CONFIG_DIR=/x/pct%dir ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]                                                                   # the shell carrying the decoded value agrees
}

@test "rewrite (Linux): a continuation line (a trailing backslash), two assignments on one Environment= line, and a kept line under [Install] are forms the reader does not read whole: refused, the line and the form named, nothing written, on all three roads" {
    # the read-write lens, D5: the reader took the physical line, so the trailing backslash was replayed and joined to the
    # next WRITTEN line, which it swallowed (ROMP_MANAGER_PORT dropped, ROMP_STATE_DIR turned into a variable named
    # Environment). The other two are the same class: a second assignment on the line the writer writes one item to, and a
    # line under [Install], which systemd does not read Environment= in and round 3 replayed under [Service].
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" stub; stub="$(_systemctl_stub active)"
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    # A: the continuation, which systemd reads whole (the oracle: both ports), and which a replay would not preserve
    _svc_line "$unit" 'Environment=ROMP_KERNEL_PORT=31855 \' '    ROMP_MANAGER_PORT=7433' "Environment=ROMP_STATE_DIR=$TEST_DIR/st"
    [ "$(_sd_read "$unit" env ROMP_KERNEL_PORT)" = 31855 ]
    [ "$(_sd_read "$unit" env ROMP_MANAGER_PORT)" = 7433 ]
    cp "$unit" "$unit.A"
    # B: two assignments on one line
    cp "$unit.clean" "$unit.B"; _svc_line "$unit.B" 'Environment=ROMP_KERNEL_PORT=31855 ROMP_MANAGER_PORT=7433'
    # C: a PATH line under [Install]
    cp "$unit.clean" "$unit.C"; printf 'Environment=PATH=/hand/bin:/usr/bin\n' >> "$unit.C"
    local f expect
    for f in A B C; do
        cp "$unit.$f" "$unit"
        case "$f" in
            A) expect="ends in a backslash, a continuation" ;;
            B) expect="ROMP_KERNEL_PORT is assigned beside another assignment on one line" ;;
            C) expect="Environment under [Install], a section systemd does not read it in" ;;
        esac
        ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"is in a form this rewrite does not read whole (line "* ]]
        [[ "$output" == *"$expect"* ]]
        [[ "$output" == *"nothing was rewritten"* ]]
        cmp -s "$unit" "$unit.$f"
        [ ! -e "$unit.tmp" ]
        run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
        [ "$status" -ne 0 ]
        ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"$expect"* ]]
        cmp -s "$unit" "$unit.$f"
        run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
            ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"$expect"* ]]
        cmp -s "$unit" "$unit.$f"
    done
    # the control: one assignment a line, each in [Service], reads and rewrites, both ports kept
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=ROMP_KERNEL_PORT=31855' 'Environment=ROMP_MANAGER_PORT=7433'
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env ROMP_KERNEL_PORT)" = 31855 ]
    [ "$(_sd_read "$unit" env ROMP_MANAGER_PORT)" = 7433 ]
    # and a hand key under [Install], which systemd ignores and this rewrite keeps nothing of, is no refusal
    cp "$unit.clean" "$unit"; printf 'Environment=ADMIN_LOCAL_KNOB=1\n' >> "$unit"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
}

@test "rewrite (Linux): the compare decodes as systemd does: blanks after a closing quote are stripped, and a bare value with whitespace is its first word, so the shell carrying what systemd handed the manager is not refused; the written line reads the same to systemd" {
    # the read-write lens, D6 (U13, U16): the decoded value kept the closing quote and the trailing blanks (systemd strips the
    # rvalue first), and a bare value with a space decoded as the whole tail where systemd reads the first word and drops the
    # rest as an invalid assignment; both refused the update child's own environment, exit 5.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" stub; stub="$(_systemctl_stub active)"
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    mkdir -p "$TEST_DIR/cc dir" "$TEST_DIR/a"
    # U13: trailing blanks after the closing quote
    _svc_line "$unit" 'Environment="CLAUDE_CONFIG_DIR='"$TEST_DIR"'/cc dir"  '
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$TEST_DIR/cc dir" ]
    CLAUDE_CONFIG_DIR="$TEST_DIR/cc dir" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR="$TEST_DIR/cc dir" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$TEST_DIR/cc dir" ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR='"$TEST_DIR"'/cc dir"' "$unit"                # the writer's form, the blanks gone
    # U16: a bare value with whitespace, the form an install before round 3 wrote
    cp "$unit.clean" "$unit"
    _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=$TEST_DIR/a b"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$TEST_DIR/a" ]                       # what systemd hands the manager
    CLAUDE_CONFIG_DIR="$TEST_DIR/a" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR="$TEST_DIR/a b" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]                                                                   # the whole tail is not what systemd reads
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries $TEST_DIR/a, this environment carries $TEST_DIR/a b"* ]]
    CLAUDE_CONFIG_DIR="$TEST_DIR/a" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$TEST_DIR/a" ]                       # the same reading after the rewrite
    grep -qxF "Environment=CLAUDE_CONFIG_DIR=$TEST_DIR/a" "$unit"
}

@test "rewrite (macOS): the one-line reader decodes a numeric character reference (&#38; decimal, &#x26; hexadecimal) as launchd does: the owning shell agrees, the value is written back as the named entity, and plistlib reads the same value before and after" {
    # the read-write lens, D8: round 3's reader decoded the five named entities only, so a numeric reference was kept as text and
    # re-escaped to &amp;#38;, launchd then reading the literal &#38; and the owning shell refused (the fallback reader alone;
    # plutil decodes it). One left-to-right pass now decodes each reference once.
    unset ROMP_SERVICE_NO_LOAD
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here"
    local cc="$TEST_DIR/amp & dir" envf="$TEST_DIR/hex & dir/service.env"
    mkdir -p "$cc" "$TEST_DIR/hex & dir"
    ROMP_PLUTIL="$none" CLAUDE_CONFIG_DIR="$cc" ROMP_SERVICE_ENV_FILE="$envf" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$plist" "$plist.named"
    sed -e '/<key>CLAUDE_CONFIG_DIR<\/key>/ s|&amp;|\&#38;|' -e '/<key>ROMP_SERVICE_ENV_FILE<\/key>/ s|&amp;|\&#x26;|' "$plist.named" > "$plist"
    grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>'"$TEST_DIR"'/amp &#38; dir</string>' "$plist"
    grep -qF '<key>ROMP_SERVICE_ENV_FILE</key><string>'"$TEST_DIR"'/hex &#x26; dir/service.env</string>' "$plist"
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR)" = "$cc" ]          # launchd's reading of the hand form
    [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_SERVICE_ENV_FILE)" = "$envf" ]
    ROMP_PLUTIL="$none" CLAUDE_CONFIG_DIR="$cc" ROMP_SERVICE_ENV_FILE="$envf" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]                                                                   # the owning shell agrees
    ROMP_PLUTIL="$none" CLAUDE_CONFIG_DIR="$cc" ROMP_SERVICE_ENV_FILE="$envf" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -F '&#' "$plist"
    [ "$status" -ne 0 ]                                                                   # written back named
    cmp -s "$plist" "$plist.named"
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR)" = "$cc" ]
    [ "$(_plist_get "$plist" EnvironmentVariables.ROMP_SERVICE_ENV_FILE)" = "$envf" ]
    # a differing shell is refused naming the decoded value
    ROMP_PLUTIL="$none" CLAUDE_CONFIG_DIR="$TEST_DIR/other" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries $cc, this environment carries $TEST_DIR/other"* ]]
    # a & that opens no reference, and a reference to a non-ASCII character, both read as launchd reads them
    sed -e '/<key>CLAUDE_CONFIG_DIR<\/key>/ s|&amp;|\&amp;#38;|' "$plist.named" > "$plist"    # the literal text &#38;, escaped as launchd wants it
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR)" = "$TEST_DIR/amp &#38; dir" ]
    ROMP_PLUTIL="$none" CLAUDE_CONFIG_DIR="$TEST_DIR/amp &#38; dir" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    sed -e '/<key>CLAUDE_CONFIG_DIR<\/key>/ s|&amp;|\&#x00e9;|' "$plist.named" > "$plist"    # é, two UTF-8 bytes
    ROMP_PLUTIL="$none" CLAUDE_CONFIG_DIR="$TEST_DIR/amp é dir" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
}

# ─── the second pass over the addendum (2026-09-19): an empty assignment is a value, and the reads outside the form checks ──
# The second read-to-write trace left three items. An EMPTY assignment (Environment=PATH=, an empty <string></string>) read as
# absence under both readers, since _file_value's empty string was a missing line and an empty value alike and every caller
# tested -n: dropped at exit 0, --check blessing it, a shell carrying a value not refused. Presence is carried apart from the
# value now (_file_present, _unit_item's set mode, _KEEP_INSTANCE_SET). The ExecStart oracle gap and the sweep of the reads
# left outside _unit_scan and _plist_readable have their cases above (the word-splitting case) and below.

@test "rewrite (Linux): an empty assignment (Environment=PATH=, Environment=CLAUDE_CONFIG_DIR=) is a value systemd reads, the variable set to the empty string: kept as written on rewrite, rewrite --check and the marked child's install, never dropped and never the caller's PATH, and a shell carrying a value for the variable is refused naming it and the empty value; an empty ROMP_DIR= is a differing clone; an empty ROMP_STATE_DIR= is kept and the audit row goes under the default root" {
    # the second pass over the addendum (N02i, N06): the drop changed systemd's reading from the empty string to unset, and for
    # PATH gave the service systemd's default PATH in place of an empty one, at exit 0 with the success line.
    unset ROMP_SERVICE_NO_LOAD
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" stub rows; stub="$(_systemctl_stub active)"
    _old_unit "$unit"
    grep -v '^Environment=PATH=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" 'Environment=PATH=' 'Environment=CLAUDE_CONFIG_DIR='
    [ "$(_sd_read "$unit" has PATH)" = yes ]                                              # systemd: set, to the empty string
    run _sd_read "$unit" env PATH                                                         # the run form (the round-6 addendum of fork PR #778,
    [ "$status" -eq 0 ]                                                                   # tests-5: an empty answer is a status 0 and no text)
    [ "$output" = "" ]
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = yes ]
    mkdir -p "$TEST_DIR/markerbin" "$TEST_DIR/cc"
    PATH="$TEST_DIR/markerbin:$PATH" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    PATH="$TEST_DIR/markerbin:$PATH" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment=PATH=' "$unit"                                                  # kept, byte for byte the line
    grep -qxF 'Environment=CLAUDE_CONFIG_DIR=' "$unit"
    [ "$(grep -cE '^Environment="?PATH=' "$unit")" -eq 1 ]
    [ "$(grep -cE '^Environment="?CLAUDE_CONFIG_DIR=' "$unit")" -eq 1 ]
    run grep -F "$TEST_DIR/markerbin" "$unit"
    [ "$status" -ne 0 ]                                                                   # never the caller's PATH
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"                                     # the release's line landed
    [ "$(_sd_read "$unit" has PATH)" = yes ]                                              # systemd's reading, unchanged
    run _sd_read "$unit" env PATH
    [ "$status" -eq 0 ]
    [ "$output" = "" ]
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = yes ]
    cp "$unit" "$unit.kept"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    cmp -s "$unit" "$unit.kept"                                                           # a second rewrite: the same bytes
    run env -i HOME="$HOME" PATH="$TEST_DIR/markerbin:$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
        ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 0 ]
    cmp -s "$unit" "$unit.kept"                                                           # the marked child's install: the same bytes
    # a shell carrying a value for the empty variable is a differing shell: refused naming the variable and the empty value,
    # on rewrite, --check and the child's install, the file untouched
    CLAUDE_CONFIG_DIR="$TEST_DIR/cc" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries an empty value, this environment carries $TEST_DIR/cc"* ]]
    [[ "$output" == *"retry from a shell that does not set it"* ]]
    cmp -s "$unit" "$unit.kept"
    CLAUDE_CONFIG_DIR="$TEST_DIR/cc" ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    run env -i HOME="$HOME" PATH="$PATH" CLAUDE_CONFIG_DIR="$TEST_DIR/cc" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 \
        ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries an empty value"* ]]
    cmp -s "$unit" "$unit.kept"
    # an empty ROMP_DIR= names no clone: a differing clone, refused, the file untouched
    grep -v '^Environment=ROMP_DIR=' "$unit.kept" > "$unit"; _svc_line "$unit" 'Environment=ROMP_DIR='
    cp "$unit" "$unit.nodir"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_DIR: the file names an empty value, this clone is "* ]]
    [[ "$output" == *"not the installed one"* ]]
    cmp -s "$unit" "$unit.nodir"
    # an empty ROMP_STATE_DIR= is what the manager reads as unset (its default root): the line is kept, empty, and the audit row
    # goes under the default from HOME as for no line
    cp "$unit.kept" "$unit"; _svc_line "$unit" 'Environment=ROMP_STATE_DIR='
    rows="$(grep -c '"action": "service-rewrite"' "$HOME/.local/state/romp/restart-audit.jsonl")"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment=ROMP_STATE_DIR=' "$unit"
    [ "$(_sd_read "$unit" has ROMP_STATE_DIR)" = yes ]
    [ "$(grep -c '"action": "service-rewrite"' "$HOME/.local/state/romp/restart-audit.jsonl")" -eq $((rows + 1)) ]
}

@test "rewrite (macOS): an empty entry (<key>PATH</key><string></string>, an instance entry, ROMP_SERVICE_ENV_FILE, StandardOutPath) is a value launchd reads, the variable set to the empty string: kept as written on rewrite, rewrite --check and the marked child's install under both readers, plistlib reading the empty string before and after, and a shell carrying a value is refused naming it; a self-closing <string/> is refused by the fallback and read by plutil; an empty program string before up is a differing clone" {
    # the second pass over the addendum (N06b): the empty entry read as no entry under both readers and was dropped at exit 0,
    # --check blessing it first; launchd had read the variable set to the empty string.
    unset ROMP_SERVICE_NO_LOAD
    _plutil_stub
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here" reader pl k kp val
    mkdir -p "$TEST_DIR/pathbin" "$TEST_DIR/xdg"
    PATH="$TEST_DIR/pathbin:$PATH" XDG_STATE_HOME="$TEST_DIR/xdg" ROMP_KERNEL_PORT=29866 ROMP_SERVICE_ENV_FILE="$TEST_DIR/custom/service.env" \
        ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$plist" "$plist.romp"
    for reader in fallback plutil; do
        pl="$none"; [ "$reader" = plutil ] && pl="$TEST_DIR/plutil-bin/plutil"
        for k in PATH ROMP_KERNEL_PORT ROMP_SERVICE_ENV_FILE StandardOutPath; do
            sed "s|<key>$k</key><string>[^<]*</string>|<key>$k</key><string></string>|" "$plist.romp" > "$plist"
            grep -qF "<key>$k</key><string></string>" "$plist"
            kp="EnvironmentVariables.$k"; [ "$k" = StandardOutPath ] && kp="$k"
            [ "$(_plist_get "$plist" "$kp")" = "" ]                                        # launchd: the entry, set to the empty string
            ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
            [ "$status" -eq 0 ]
            ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
            [ "$status" -eq 0 ]
            grep -qF "<key>$k</key><string></string>" "$plist"                             # kept, empty, as written
            [ "$(grep -cF "<key>$k</key>" "$plist")" -eq 1 ]
            [ "$(_plist_get "$plist" "$kp")" = "" ]                                        # launchd's reading, unchanged
            run grep -F "$TEST_DIR/pathbin" "$plist"
            [ "$k" != PATH ] || [ "$status" -ne 0 ]                                       # never the caller's PATH
            cp "$plist" "$plist.kept"
            ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
            [ "$status" -eq 0 ]
            cmp -s "$plist" "$plist.kept"                                                 # a second rewrite: the same bytes
            run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
                ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
            [ "$status" -eq 0 ]
            cmp -s "$plist" "$plist.kept"                                                 # the marked child's install: the same bytes
        done
        # a shell carrying a value for the empty entry is a differing shell: refused naming the variable and the empty value
        for k in ROMP_KERNEL_PORT ROMP_SERVICE_ENV_FILE; do
            sed "s|<key>$k</key><string>[^<]*</string>|<key>$k</key><string></string>|" "$plist.romp" > "$plist"; cp "$plist" "$plist.empty"
            val=31855; [ "$k" = ROMP_SERVICE_ENV_FILE ] && val="$TEST_DIR/other/service.env"
            run env "$k=$val" ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite
            [ "$status" -eq 5 ]
            [[ "$output" == *"$k: the file "*"an empty value, this environment "*"$val"* ]]
            [[ "$output" != *"Rewrote"* ]]
            cmp -s "$plist" "$plist.empty"
            run env "$k=$val" ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite --check
            [ "$status" -eq 5 ]
            cmp -s "$plist" "$plist.empty"
        done
        # the self-closing <string/>, which launchd reads as the empty string too: not a form the one-line reader reads (refused
        # naming the entry, the file untouched); plutil reads it and the writer puts the value back as <string></string>
        sed "s|<key>PATH</key><string>[^<]*</string>|<key>PATH</key><string/>|" "$plist.romp" > "$plist"; cp "$plist" "$plist.selfclose"
        [ "$(_plist_get "$plist" EnvironmentVariables.PATH)" = "" ]
        ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        if [ "$reader" = fallback ]; then
            [ "$status" -eq 5 ]
            [[ "$output" == *"its PATH entry is split across lines, or is not <key>PATH</key><string>...</string> on one line"* ]]
            cmp -s "$plist" "$plist.selfclose"
        else
            [ "$status" -eq 0 ]
            grep -qF '<key>PATH</key><string></string>' "$plist"
            [ "$(_plist_get "$plist" EnvironmentVariables.PATH)" = "" ]
        fi
        # an empty program string before up is a value launchd reads (a program it cannot run), never an absent ExecStart to be
        # re-pointed at this clone: a differing clone, exit 5, the file untouched
        sed "s|<string>$ROMP_MANAGER_BIN</string>|<string></string>|" "$plist.romp" > "$plist"; cp "$plist" "$plist.noprog"
        grep -qx '    <string></string>' "$plist"
        [ "$(_plist_get "$plist" ProgramArguments.1)" = "" ]
        ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"ExecStart: the file runs an empty value, this clone would write $ROMP_MANAGER_BIN"* ]]
        cmp -s "$plist" "$plist.noprog"
    done
}

@test "rewrite (macOS): the reads the sweep found outside the form check go through it: a read key on two lines and a second or trailing up string are refused by the fallback as forms not read whole, byte for byte on all three roads; through plutil an array with no up, with up first, with two or with arguments after it is refused, never read as an absent ExecStart and re-pointed at this clone, and a key on two lines reads as the parser reads it" {
    # the second pass over the addendum (the anchored-regex sweep): _file_value's -m1 grep read the FIRST of two lines carrying a
    # key where the parser keeps one; its awk took the line before the FIRST <string>up</string>; the plutil read took the argument
    # before the first up, and read an array with none as no ExecStart, which the rewrite re-pointed at the deploying clone at
    # exit 0. Both readers now read the array in _plist_readable and require up once and last after the manager's path.
    unset ROMP_SERVICE_NO_LOAD
    _plutil_stub
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here" pl="$TEST_DIR/plutil-bin/plutil" shape expect
    mkdir -p "$TEST_DIR/pathbin"
    PATH="$TEST_DIR/pathbin:$PATH" ROMP_KERNEL_PORT=29866 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    cp "$plist" "$plist.romp"
    # A: PATH on two lines, both in the one-line form (the parser keeps the second)
    awk '{ print } /^    <key>PATH<\/key><string>/ { print "    <key>PATH</key><string>/second/bin</string>" }' "$plist.romp" > "$plist.A"
    [ "$(_plist_get "$plist.A" EnvironmentVariables.PATH)" = /second/bin ]
    # B: up twice; C: an argument after up; D: no up at all; E: up alone
    awk '{ print } /^    <string>up<\/string>$/ { print "    <string>up</string>" }' "$plist.romp" > "$plist.B"
    awk '{ print } /^    <string>up<\/string>$/ { print "    <string>--flag</string>" }' "$plist.romp" > "$plist.C"
    sed 's|<string>up</string>|<string>start</string>|' "$plist.romp" > "$plist.D"
    awk '/<array>/ { a = 1 } /<\/array>/ { a = 0 } a && /<string>/ && !/<string>up<\/string>/ { next } { print }' "$plist.romp" > "$plist.E"
    [ "$(_plist_get "$plist.B" ProgramArguments.3)" = up ]
    [ "$(_plist_get "$plist.C" ProgramArguments.3)" = --flag ]
    [ "$(_plist_get "$plist.E" ProgramArguments.0)" = up ]
    for shape in A B C D E; do
        cp "$plist.$shape" "$plist"
        case "$shape" in
            A) expect="its PATH entry is on 2 lines, and this reader reads one" ;;
            *) expect="its ProgramArguments array is not one <string> a line ending in <string>up</string>, with up once and last" ;;
        esac
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"$expect"* ]]
        [[ "$output" == *"nothing was rewritten"* ]]
        [[ "$output" != *"this clone would write"* ]]
        cmp -s "$plist" "$plist.$shape"
        [ ! -e "$plist.tmp" ]
        run grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl"
        [ "$status" -ne 0 ]
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"$expect"* ]]
        cmp -s "$plist" "$plist.$shape"
        run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
            ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"$expect"* ]]
        cmp -s "$plist" "$plist.$shape"
    done
    # through plutil: the array shapes are refused by the same rule, naming the count, never as another clone
    for shape in B C D E; do
        cp "$plist.$shape" "$plist"
        case "$shape" in B|C) expect="as 4 arguments" ;; D) expect="as 3 arguments" ;; E) expect="as 1 arguments" ;; esac
        ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"reads its ProgramArguments $expect where romp writes the launcher, the manager's path and up (up once, last, after the manager's path)"* ]]
        [[ "$output" != *"this clone would write"* ]]
        cmp -s "$plist" "$plist.$shape"
        ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        cmp -s "$plist" "$plist.$shape"
        run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_NO_NODE_COPY=1 \
            ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" "$SVC" install
        [ "$status" -eq 5 ]
        cmp -s "$plist" "$plist.$shape"
    done
    # and the key on two lines reads through plutil as the parser reads it: one entry written back, with the parser's value
    cp "$plist.A" "$plist"
    ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(grep -cF '<key>PATH</key>' "$plist")" -eq 1 ]
    grep -qxF '    <key>PATH</key><string>/second/bin</string>' "$plist"
    [ "$(_plist_get "$plist" EnvironmentVariables.PATH)" = /second/bin ]
    # the control: romp's own plist reads and rewrites under both readers, the array kept as the launcher, the manager and up
    cp "$plist.romp" "$plist"
    ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_plist_get "$plist" ProgramArguments.1)" = "$ROMP_MANAGER_BIN" ]
    [ "$(_plist_get "$plist" ProgramArguments.2)" = up ]
    ROMP_PLUTIL="$pl" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_plist_get "$plist" ProgramArguments.1)" = "$ROMP_MANAGER_BIN" ]
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

# Round 4 of the review (2026-09-19): the line ending, the comment, the header, systemd's blanks, the escapes, the untested refusals, the
# resets, the drop-ins, the newline-ending values. Every guard below is run against BOTH of its boundary cases, the form it must refuse
# and the form it must accept, with the oracle read first so what a refusal says about systemd is pinned as well; the oracle itself was
# checked against systemd-analyze --user verify (its header says how).
_svc_bytes() {   # $1 the unit, $@ python-escaped strings (\r, \n, \x0c, \x00, \xNN decoded to bytes): inserted before [Install] byte for byte,
                 # where _svc_line's awk would not carry a NUL or a bare CR as such
    python3 - "$@" <<'PY'
import sys
p = sys.argv[1]; data = open(p, "rb").read()
ins = b"".join(a.encode("utf-8").decode("unicode_escape").encode("latin-1") for a in sys.argv[2:])
i = data.index(b"[Install]"); open(p, "wb").write(data[:i] + ins + data[i:])
PY
}
_line_endings() {   # $1 the unit, $2 crlf | cr: every LF rewritten as that ending
    python3 - "$1" "$2" <<'PY'
import sys
p, kind = sys.argv[1], sys.argv[2]; d = open(p, "rb").read()
open(p, "wb").write(d.replace(b"\n", b"\r\n" if kind == "crlf" else b"\r"))
PY
}
_three_roads_refuse() {   # $1 the unit, $2 a phrase the refusal carries, $@ phrases it must not: exit 5, the form named, the file byte for byte, no
                          # rewrite audit row, on rewrite, rewrite --check and the marked child's install (the shape of the continuation case)
    local unit="$1" expect="$2" stub absent rows; shift 2; stub="$(_systemctl_stub active)"
    cp "$unit" "$unit.before"
    rows="$(grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl" 2>/dev/null || true)"   # a case may have rewritten before
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"is in a form this rewrite does not read whole (line "* ]]
    [[ "$output" == *"$expect"* ]]
    [[ "$output" == *"nothing was rewritten"* ]]
    for absent in "$@"; do [[ "$output" != *"$absent"* ]]; done
    cmp -s "$unit" "$unit.before"
    [ ! -e "$unit.tmp" ]
    [ "$(grep -c '"action": "service-rewrite"' "$XDG_STATE_HOME/romp/restart-audit.jsonl" 2>/dev/null || true)" = "${rows:-0}" ]   # the refused rewrite journaled nothing
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"$expect"* ]]
    for absent in "$@"; do [[ "$output" != *"$absent"* ]]; done
    cmp -s "$unit" "$unit.before"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
        ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"$expect"* ]]
    for absent in "$@"; do [[ "$output" != *"$absent"* ]]; done
    cmp -s "$unit" "$unit.before"
}
_marked_install() {   # the marked child's install over the unit on disk; $status and $output are its. CLAUDE_CONFIG_DIR is forwarded when the
                      # caller's shell carries it and stays unset otherwise (round 6 of fork PR #778, tests-4: four legs prefixed a value onto
                      # _marked_install_ok, whose env -i dropped it, so the marked child ran with the variable unset and the legs could not see
                      # a disagreement; the addendum split the run from the exit-0 assertion so a leg can expect the refusal a disagreeing
                      # value earns, which is what pins the forward: without it the child keeps the file's line at exit 0)
    local ccd=(); [[ -z "${CLAUDE_CONFIG_DIR+x}" ]] || ccd=(CLAUDE_CONFIG_DIR="$CLAUDE_CONFIG_DIR")
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
        ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "${ccd[@]}" "$SVC" install
}
_marked_install_ok() {   # the marked child's install over the unit on disk, expected to keep it and exit 0; $output is its output
    _marked_install
    [ "$status" -eq 0 ]
}
# The byte-order-mark shapes case's two helpers, at file scope (round 7 of fork PR #778, tests-1 and regression-1: defined inside the
# @test body, their indented closing braces ended tests/test_bats_bare_negation.py's block early, so 211 lines of that case were
# outside the bare-negation scan; the scanner's block-end is a column-zero brace now, and the helpers live here beside the others).
# They read the caller's $unit and $mgr by bash's dynamic scope, as _three_roads_refuse reads $status and $output.
_kept() {   # the file at $unit (the caller's local, read by dynamic scope, as $mgr is), built by the function $2, carries a marked kept
            # CLAUDE_CONFIG_DIR line systemd reads as $1: kept and compared on the three roads, the rewrite writing it without the mark
            # and with LF endings (the marked child's install rewrites the file, so it is rebuilt between the roads)
    local want="$1" build="$2"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$want" ]
    CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries $want, this environment carries /x/other"* ]]
    CLAUDE_CONFIG_DIR="$want" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR="$want" _marked_install_ok
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$want" ]
    "$build"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run env LC_ALL=C grep -c $'\xef\xbb\xbf' "$unit"
    [ "$status" -ne 0 ]
    run grep -c $'\r' "$unit"
    [ "$status" -ne 0 ]
    [ "$(grep -cE '^Environment="?CLAUDE_CONFIG_DIR=' "$unit")" -eq 1 ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$want" ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
}
_whole() {   # the file at $unit (the caller's local, as above), built by the function $1, reads whole (the oracle: the manager, ROMP_DIR set) and passes the three roads,
             # the rewrite writing no mark and no CR
    "$1"
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    [ "$(_sd_read "$unit" has ROMP_DIR)" = yes ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"agree"* ]]
    _marked_install_ok
    "$1"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run env LC_ALL=C grep -c $'\xef\xbb\xbf' "$unit"
    [ "$status" -ne 0 ]
    run grep -c $'\r' "$unit"
    [ "$status" -ne 0 ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
}
_bom_before() {   # $1 a unit, $2 where to write it, $3 a needle: the file with $4 (text, default none) and then $5 (default the UTF-8 byte order
                  # mark; '' for none) inserted before the needle's first occurrence, byte for byte otherwise
    python3 - "$@" <<'PY'
import sys
src, dst, needle = sys.argv[1], sys.argv[2], sys.argv[3].encode("utf-8", "surrogateescape")
before = sys.argv[4].encode("utf-8", "surrogateescape") if len(sys.argv) > 4 else b""
mark = sys.argv[5].encode("utf-8", "surrogateescape") if len(sys.argv) > 5 else b"\xef\xbb\xbf"
d = open(src, "rb").read()
assert needle in d, needle
open(dst, "wb").write(d.replace(needle, before + mark + needle, 1))
PY
}
_utf8_locale() {   # a UTF-8 locale a fresh bash really runs under (C.UTF-8 or en_US.UTF-8 as locale -a lists it), or exit 1 with the remedy: a
                   # locale listed but not generated makes bash fall back to C, and a leg that must run under UTF-8 would then prove nothing
    local utf8loc; utf8loc="$(locale -a 2>/dev/null | grep -iE '^(C|en_US)\.utf-?8$' | head -1)"
    if [[ -z "$utf8loc" ]] || ! LC_ALL="$utf8loc" bash -c '[[ "$1" == [[:alnum:]] ]]' _ $'\xc3\xa9'; then
        echo "romp-service.bats: no UTF-8 locale a fresh bash runs under (locale -a lists ${utf8loc:-neither C.UTF-8 nor en_US.UTF-8}; a listed one must match a non-ASCII letter with [[:alnum:]] under LC_ALL=<it>, else bash fell back to C). Remedy: generate one (Debian and Ubuntu: locale-gen C.UTF-8 or en_US.UTF-8, or dpkg-reconfigure locales), then run the case again." >&2
        return 1
    fi
    printf '%s' "$utf8loc"
}
_nodec_bin() {   # a PATH directory carrying every command of /usr/bin and /bin but iconv and python3 (and python), so a child finds no UTF-8
                 # decoder and everything else; prints its path
    local d="$TEST_DIR/nodec-bin" f b
    mkdir -p "$d"
    for f in /usr/bin/* /bin/*; do
        b="${f##*/}"
        case "$b" in iconv|python|python3|python3.*) continue ;; esac
        [ -e "$d/$b" ] || ln -s "$f" "$d/$b" 2>/dev/null || true
    done
    printf '%s' "$d"
}

@test "rewrite (Linux): the line ending is read as systemd reads it: a CRLF unit is accepted whole and written back with LF, a CRLF continuation is refused as the continuation it is, and a bare-CR unit, two CRs before the LF and a NUL byte are refused naming the byte, on all three roads" {
    # round 4 (extra5-1, tests-1, the round's headline): the continuation count ran on the raw line, so on a CRLF unit the backslash was
    # followed by the CR and the count saw none; systemd strips that one CR first and joins, so the swallowed line was read as live and
    # written as real (D5 through a line ending). And systemd's read_line ends a line at a bare CR too, where bash's read does not, so a
    # CR-only unit read as ONE line, dropped PATH and ROMP_STATE_DIR and re-pointed ExecStart at exit 0 (D4 through a line ending).
    # Verified against systemd-analyze --user verify (255.4): one CR joins, two do not, a bare CR and a NUL split a line.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mgr="$ROMP_MANAGER_BIN"
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    # a CRLF unit with no continuation: read whole (the oracle agrees) and written back as an LF unit, the replayed PATH line's CR off
    _line_endings "$unit" crlf
    grep -q $'\r' "$unit"
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    _marked_install_ok
    _line_endings "$unit" crlf
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -c $'\r' "$unit"
    [ "$status" -ne 0 ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    grep -q '^Environment=PATH=' "$unit"
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    # the CRLF continuation: systemd joins `RestartSec=2 \` to the next line, so ROMP_STATE_DIR is never an assignment (the oracle says so);
    # refused as the continuation it is, and the swallowed root never becomes the audit row's
    cp "$unit.clean" "$unit"; _line_endings "$unit" crlf; _svc_bytes "$unit" 'RestartSec=2 \\\r\n' "Environment=ROMP_STATE_DIR=$TEST_DIR/st\r\n"
    [ "$(_sd_read "$unit" has ROMP_STATE_DIR)" = no ]
    _three_roads_refuse "$unit" "ends in a backslash, a continuation" "carriage return"
    [ ! -e "$TEST_DIR/st/restart-audit.jsonl" ]
    # a CR-only unit: one line to bash's read, every line to systemd (the oracle reads it whole); refused naming the carriage return,
    # never read as a unit with no ExecStart and re-pointed
    cp "$unit.clean" "$unit"; _line_endings "$unit" cr
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    [ "$(_sd_read "$unit" has ROMP_DIR)" = yes ]
    _three_roads_refuse "$unit" "carries a carriage return before its end" "this clone would write" "ends in a backslash"
    # two CRs before the LF: to systemd the line and an empty one, so the backslash joins nothing; the count strips ONE CR, not every
    # trailing blank, so it does not fire, and the second CR is a line end this reader does not read, which is what is refused
    cp "$unit.clean" "$unit"; _svc_bytes "$unit" 'Restart=always\\\r\r\n'
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    _three_roads_refuse "$unit" "carries a carriage return before its end" "ends in a backslash"
    # a NUL byte: a line end to systemd, dropped by bash's read
    cp "$unit.clean" "$unit"; _svc_bytes "$unit" 'Environment=A=1\x00Environment=CLAUDE_CONFIG_DIR=/x/nul\n'
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = yes ]
    _three_roads_refuse "$unit" "carries a NUL byte"
    # the shared tail every refusal but the own-line ones print (bin/romp-service _unit_refuse), pinned once where it renders, on the marked
    # child's install the helper ran last and on the rewrite road: the whole second line from the remedy on, and the old clause absent
    # (round 6 of fork PR #778, tests-1 and extra7-1: the round-5 preface corrected the clause, which said the install restarts the manager,
    # with no pin, so restoring it left this suite at 132 ok)
    [[ "$output" == *"  Remove the NUL byte, then systemctl --user daemon-reload and run the deploy again; or run romp-service install from the shell and clone that should own the service (the header says what it bakes), which writes the unit afresh, reloads systemd and runs enable --now, which starts an inactive unit and leaves a running one as it is; a running manager keeps its old unit until its next restart:  systemctl --user restart romp-manager"* ]]
    [[ "$output" != *"restarts the manager"* ]]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"  Remove the NUL byte, then systemctl --user daemon-reload and run the deploy again; or run romp-service install from the shell and clone that should own the service (the header says what it bakes), which writes the unit afresh, reloads systemd and runs enable --now, which starts an inactive unit and leaves a running one as it is; a running manager keeps its old unit until its next restart:  systemctl --user restart romp-manager"* ]]
    [[ "$output" != *"restarts the manager"* ]]
}

@test "rewrite (Linux): a comment ending in a backslash joins nothing and is accepted on all three roads, the rewrite matching a comment-free one byte for byte; a blank after a backslash is no continuation, so a hand key with one is accepted and an Environment= item with one is refused as the trailing backslash systemd refuses, never as a continuation; a comment inside an open continuation leaves the continuation refused" {
    # round 4 (correctness-1, tests-1, extra6-3, extra7-1): the count ran BEFORE the comment skip, so an operator commenting out a wrapped
    # ExecStart (a # on each line, the backslashes kept) stopped every deploy on the box with exit 5 over a file systemd reads perfectly;
    # systemd skips a comment before its continuation test, inside an open continuation too. The count stays on the line as read, not
    # the blank-stripped one: systemd does not join when a blank follows the backslash (verified), and that form has its own true text.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" form
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    ROMP_OS_OVERRIDE=Linux "$SVC" rewrite >/dev/null; cp "$unit" "$unit.plain"            # the comment-free rewrite, for the byte comparison
    for form in '# a wrapped comment \' ';another comment style \' '  # indented, ending in a backslash \' '# ExecStart=/x/old/romp-manager \' '#    --old-flag \'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "$form"
        [ "$(_sd_read "$unit" exec0)" = "$ROMP_MANAGER_BIN" ]                             # systemd reads the unit whole
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        _marked_install_ok
        cp "$unit.clean" "$unit"; _svc_line "$unit" "$form"
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        cmp -s "$unit" "$unit.plain"
    done
    # a blank after the backslash is no continuation to systemd: on a key this rewrite keeps nothing of, accepted; on an Environment= item,
    # refused as what it is to systemd (a trailing backslash, at which it drops the item, the items before it standing: the oracle reads
    # the first one), never as a continuation
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Restart=always\ '
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc \ '
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
    _three_roads_refuse "$unit" "a trailing backslash, at which systemd drops the item and the rest of the line" "a continuation systemd joins" "whole line"
    # a comment inside an open continuation is skipped by systemd, and the continuation joins the line after it: the continuation is
    # the refusal, before the comment is reached
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=ROMP_KERNEL_PORT=31855 \' '# a comment inside the continuation' '    ROMP_MANAGER_PORT=7433'
    [ "$(_sd_read "$unit" env ROMP_MANAGER_PORT)" = 7433 ]
    _three_roads_refuse "$unit" "ends in a backslash, a continuation"
}

@test "rewrite (Linux): a section header systemd refuses the whole file on (not ending in ]: [Instal, [Service]x, a trailing comment; a quote, a backslash or a control character in the name) is refused on all three roads naming the header, never read past, and every oracle read of the file says nothing loads; a well-formed header systemd only ignores ([Ser vice], [], [Ser.vice], [X-Hand], [Service]]) is accepted" {
    # round 4 (extra6-1, high): the reader kept the previous section over a malformed header, so a kept value under `[Instal` read as
    # live and the rewrite replayed it under [Service], where it took effect for the first time, and `[Service]x` had the refusal name
    # [Unit], a section the file did not carry; systemd loads nothing from such a file (Invalid section header, Bad characters in
    # section header: verified on 255.4). A syntactically valid unknown header is only ignored by systemd, so refusing it would be a
    # false refusal; the refuters narrowed the predicate to exactly systemd's.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" hdr
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    for hdr in '[Instal' '[Service]x' '[Install]   # auto-start at login' '[Ser"vice]' "[Ser'vice]" '[Ser\vice]' '['; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "$hdr" 'Environment=CLAUDE_CONFIG_DIR=/x/hand/cc'
        [[ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" == "ERROR: "*"section header"* ]]
        [[ "$(_sd_read "$unit" exec0)" == "ERROR: "* ]]
        _three_roads_refuse "$unit" "section header" "under [Unit]" "this clone would write"
        [ "$(grep -c 'CLAUDE_CONFIG_DIR' "$unit")" -eq 1 ]                                # the hand line, where it was: never laundered
    done
    for hdr in '[Ser\x01vice]\n' '[Ser\x7fvice]\n'; do
        cp "$unit.clean" "$unit"; _svc_bytes "$unit" "$hdr" 'Environment=CLAUDE_CONFIG_DIR=/x/hand/cc\n'
        [[ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" == "ERROR: Bad characters in section header"* ]]
        _three_roads_refuse "$unit" "a quote, a backslash or a control character, which systemd refuses whole (Bad characters in section header)"
    done
    # another clone's ExecStart under the bad header: the header is the refusal, not the clone (the operator was sent to the wrong remedy)
    cp "$unit.clean" "$unit"; grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" '[Instal' "ExecStart=$TEST_DIR/other/romp-manager up"
    _three_roads_refuse "$unit" "Invalid section header" "this clone would write" "not the installed one"
    # accepted: headers systemd ignores with a warning, with a line under each that this rewrite keeps nothing of
    for hdr in '[Ser vice]' '[]' '[Ser.vice]' '[X-Hand]' '[Service]]' '[[Service]'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "$hdr" 'Restart=always'
        [ "$(_sd_read "$unit" exec0)" = "$ROMP_MANAGER_BIN" ]
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
    done
}

@test "rewrite (Linux): blanks are systemd's set: a form-feed-indented Environment= line is an unknown key to systemd and is not read, where it was read and written back live; a form feed inside a value does not split it, and the shell carrying the whole value agrees" {
    # round 4 (extra6-5, in the refuters' form): bash's [[:space:]] adds \f and \v to systemd's " \t\n\r", so the line strip accepted a
    # line systemd ignores, and the word split cut a value at a form feed systemd keeps whole. The fix first offered (space and tab
    # alone) refused a CRLF unit both read fine, so the set is systemd's, CR included (the line-ending case pins the CRLF unit).
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" ff=$'\f'
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    _svc_bytes "$unit" '\x0cEnvironment=CLAUDE_CONFIG_DIR=/x/ff\n'
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]                                  # an unknown key to systemd
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -c 'CLAUDE_CONFIG_DIR' "$unit"
    [ "$status" -ne 0 ]                                                                   # not read, so not written: systemd's reading is unchanged
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    cp "$unit.clean" "$unit"; _svc_bytes "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/a\x0cb\n'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/a${ff}b" ]                        # one word to systemd
    CLAUDE_CONFIG_DIR="/x/a${ff}b" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/a${ff}b" ]                        # the writer's form, the same reading
}

@test "rewrite (Linux): every escape systemd decodes is decoded as systemd decodes it, agreeing with the oracle and with the shell carrying the value; an escape systemd refuses is refused saying systemd drops the item and the rest of the line, the items before it standing; an eight-bit or surrogate escape is refused saying systemd reads it and this reader does not model that; ExecStart's escapes are read the way config_parse_exec reads them" {
    # round 4 (correctness-4, extra5-4, extra6-4): the reader refused \a \b \f \v \xNN \NNN \u \U with a text saying systemd drops the
    # line as invalid syntax, which is false: systemd's cunescape decodes them all, and what it does refuse (\q, \x with fewer than two
    # digits, \x00, an octal above \377, \u0000, a code point above U+10FFFF) drops the item and the rest of the line, the items before
    # it standing (config_parse_environ commits each as it goes), not the whole line (verified on 255.4). An eight-bit byte and a
    # surrogate systemd decodes into raw bytes it then judges as UTF-8, a reading this reader does not model: refused saying so, the
    # safe side of the rule. config_parse_exec keeps an escape it does not know as the backslash and the character and then refuses the
    # executable name for the backslash, so the unit never starts.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" exp form
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    exp=$'/x/AA\xc3\xa9\xc3\xa9\a\b\f\v \t\\"\'q'
    form='Environment="CLAUDE_CONFIG_DIR=/x/\x41\101\u00e9\U000000e9\a\b\f\v\s\t\\\"\'"'"'q"'
    _svc_line "$unit" "$form"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$exp" ]
    CLAUDE_CONFIG_DIR="$exp" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '^Environment="CLAUDE_CONFIG_DIR=' "$unit"                                     # the writer's quoted form
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$exp" ]                              # reads as the same value
    CLAUDE_CONFIG_DIR="$exp" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    # refused as systemd refuses them; the oracle: the item is dropped, the one before it (a port) stands
    for form in 'Environment=ROMP_KERNEL_PORT=31855 CLAUDE_CONFIG_DIR=/x/\q|an escape systemd does not decode (\q)' \
                'Environment=ROMP_KERNEL_PORT=31855 CLAUDE_CONFIG_DIR=/x/\x4|the escape \x4, which is not \x and two hexadecimal digits' \
                'Environment=ROMP_KERNEL_PORT=31855 CLAUDE_CONFIG_DIR=/x/\x00|the escape \x00, a NUL byte' \
                'Environment=ROMP_KERNEL_PORT=31855 CLAUDE_CONFIG_DIR=/x/\400|the escape \400, above \377' \
                'Environment=ROMP_KERNEL_PORT=31855 CLAUDE_CONFIG_DIR=/x/\u0000|the escape \u0000, U+0000' \
                'Environment=ROMP_KERNEL_PORT=31855 CLAUDE_CONFIG_DIR=/x/\U00110000|the escape \U00110000, above U+10FFFF'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "${form%%|*}"
        [ "$(_sd_read "$unit" env ROMP_KERNEL_PORT)" = 31855 ]
        [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
        _three_roads_refuse "$unit" "${form#*|}" "whole line" "this reader does not decode"
        [[ "$output" == *"drops the item and the rest of the line as invalid syntax (the items before it on the line stand)"* ]]
    done
    # decoded by systemd into bytes this reader does not model: a valid pair reads to systemd, a lone byte or a surrogate drops the assignment
    for form in 'Environment=CLAUDE_CONFIG_DIR=/x/\xc3\xa9|the escape \xc3, a byte at or above 0x80' \
                'Environment=CLAUDE_CONFIG_DIR=/x/\xff|the escape \xff, a byte at or above 0x80' \
                'Environment=CLAUDE_CONFIG_DIR=/x/\377|the escape \377, a byte at or above 0x80' \
                'Environment=CLAUDE_CONFIG_DIR=/x/\ud800|the escape \ud800, a surrogate'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "${form%%|*}"
        _three_roads_refuse "$unit" "${form#*|}" "drops the item" "systemd does not decode"
        [[ "$output" == *"this reader does not model that reading"* ]]
    done
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]                                  # the surrogate: bytes that are not UTF-8, dropped
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/\xc3\xa9'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = $'/x/\xc3\xa9' ]                       # the pair: systemd reads it
    # ExecStart: an escape systemd does not know stays a backslash in the path, which string_is_safe then refuses (the oracle's error);
    # one it decodes reads as the same path
    cp "$unit.clean" "$unit"; grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" "ExecStart=$TEST_DIR/r\\qomp-manager up"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Executable name contains special characters: "* ]]
    _three_roads_refuse "$unit" "ExecStart's command has an escape systemd does not decode (\q)" "drops the item"
    [[ "$output" == *"keeps the backslash and refuses the executable name"* ]]
    cp "$unit.clean" "$unit"; grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" "ExecStart=${ROMP_MANAGER_BIN%romp-manager}\\x72omp-manager up"     # \x72 is r: the same path to systemd and here
    [ "$(_sd_read "$unit" exec0)" = "$ROMP_MANAGER_BIN" ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
}

@test "rewrite (Linux): the refusals that shipped untested, each run against the input it must refuse and read through the oracle first: ExecStart arguments that are not up alone (extra ones, none, a second command), a second ExecStart= line, a second EnvironmentFile= line, a prefix character (named alone, never with the path), an unbalanced quote in ExecStart and in an Environment= item" {
    # round 4 (tests-2, extra7-2): both refuters mutated each of these to accept-and-continue and the suite stayed green; executed, the
    # not-up-alone mutant silently dropped a --foreground argument on rewrite and the second-EnvironmentFile mutant switched which env
    # file the manager loads. The ExecStart forms replace the unit's own line first (kept, the second-line refusal fires instead); the
    # two second-line forms keep it. The prefix message names the character alone (round 4: it printed the command word, a path).
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mgr="$ROMP_MANAGER_BIN" form
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=$mgr up --foreground"
    [ "$(_sd_read "$unit" execn)" = 3 ]                                                   # systemd runs it with the extra argument
    _three_roads_refuse "$unit" "ExecStart's arguments are not up alone"
    grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=$mgr"
    [ "$(_sd_read "$unit" execn)" = 1 ]
    _three_roads_refuse "$unit" "ExecStart's arguments are not up alone"
    grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=$mgr up ; /bin/true"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Service has more than one ExecStart"* ]]    # a second command on the line: systemd refuses the unit
    _three_roads_refuse "$unit" "ExecStart's arguments are not up alone"
    cp "$unit.clean" "$unit"; _svc_line "$unit" "ExecStart=$mgr up"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Service has more than one ExecStart"* ]]
    _three_roads_refuse "$unit" "a second ExecStart= line, which systemd refuses in a service of this type"
    cp "$unit.clean" "$unit"; _svc_line "$unit" "EnvironmentFile=-$TEST_DIR/second.env"
    [ "$(_sd_read "$unit" envfile)" = "$HOME/.config/romp/service.env" ]                  # systemd loads both; the unit's own is first
    _three_roads_refuse "$unit" "a second EnvironmentFile= line"
    for form in "-$mgr" "@$mgr" ":$mgr" "+$mgr" "!$mgr" "!!$mgr"; do
        grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=$form up"
        [ "$(_sd_read "$unit" exec0)" = "$mgr" ]                                          # systemd strips the prefix and runs the manager
        _three_roads_refuse "$unit" "begins with a prefix character (${form:0:1})" "prefix character ($form"
    done
    grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=\"$mgr up"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Service has no ExecStart"* ]]               # Unbalanced quoting: the line yields no command
    _three_roads_refuse "$unit" "ExecStart's command has an unbalanced quote"
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=ROMP_KERNEL_PORT=31855 "CLAUDE_CONFIG_DIR=/x/cc'
    [ "$(_sd_read "$unit" env ROMP_KERNEL_PORT)" = 31855 ]                                # the item before the bad one stands
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    _three_roads_refuse "$unit" "an Environment= item with an unbalanced quote, at which systemd drops the item and the rest of the line" "whole line"
}

@test "rewrite (Linux): an empty rvalue resets what was read, as systemd resets it, each reset pinned by its own mutation: Environment= drops the kept assignments before it (another value in the shell is then no disagreement and no line is written); ExecStart= drops the command (the file is one systemd refuses to load, and the rewrite writes this clone's, as for a unit with no line); EnvironmentFile= drops the file (the default stands, so a shell naming the unit's former file is refused), as a path that is not absolute does" {
    # round 4 (tests-3): the three reset legs were untested (removing all three left the suite green, and an instrument on them never
    # fired). Agreement reads in opposite directions per key, the refuters noted, so each leg has its own shape, and the reading AFTER
    # the rewrite is asserted through the oracle, since the rewrite that follows a reset changes what systemd loads: the release's own
    # lines (ROMP_SUPERVISED, MALLOC_ARENA_MAX) are written fresh whatever a reset cleared, that being the rewrite's purpose, and a
    # file left with no ExecStart, which systemd refuses to load, gets this clone's command, round 2's rule for a file with no line.
    # The relative EnvironmentFile path is round 4's: systemd ignores it with a warning, and the reader had read it as a path.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/svc.env" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -v '^Environment=MALLOC_ARENA_MAX=' "$unit" > "$unit.old" && mv -f "$unit.old" "$unit"; cp "$unit" "$unit.clean"
    # Environment=: the kept assignment before the reset is gone to systemd, and so is the release's own line before it
    _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc' 'Environment='
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    [ "$(_sd_read "$unit" has ROMP_SUPERVISED)" = no ]
    CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]                                                                   # absence is no disagreement, whatever the shell carries
    CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -c 'CLAUDE_CONFIG_DIR' "$unit"
    [ "$status" -ne 0 ]                                                                   # no line: neither the file's former value nor the shell's
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    [ "$(_sd_read "$unit" env ROMP_SUPERVISED)" = 1 ]                                     # the release's line, written fresh
    # ExecStart=: no command after it, a unit systemd refuses to load; read as no command, and this clone's is written
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'ExecStart='
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Service has no ExecStart"* ]]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"second ExecStart"* ]]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" exec0)" = "$ROMP_MANAGER_BIN" ]
    [ "$(grep -c '^ExecStart=' "$unit")" -eq 1 ]
    # a reset and then another clone's command: the reset counts, the later line is the one read, and it names another clone
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'ExecStart=' "ExecStart=$TEST_DIR/other/romp-manager up"
    [ "$(_sd_read "$unit" exec0)" = "$TEST_DIR/other/romp-manager" ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $TEST_DIR/other/romp-manager"* ]]
    # EnvironmentFile=: no file after the reset, so the default path stands and the shell naming the unit's former file differs
    cp "$unit.clean" "$unit"; grep -q "^EnvironmentFile=-$TEST_DIR/svc.env\$" "$unit"; _svc_line "$unit" 'EnvironmentFile='
    run _sd_read "$unit" envfile                                                          # the run form: an oracle that raised is a nonzero status,
    [ "$status" -eq 0 ]                                                                   # not an empty answer (round 6 of fork PR #778, tests-5)
    [ "$output" = "" ]
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/svc.env" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_SERVICE_ENV_FILE: the file reads $HOME/.config/romp/service.env, this environment names $TEST_DIR/svc.env"* ]]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=-$HOME/.config/romp/service.env" "$unit"                  # the default, as a unit with no line gets
    [ "$(_sd_read "$unit" envfile)" = "$HOME/.config/romp/service.env" ]
    run grep -c 'ROMP_SERVICE_ENV_FILE' "$unit"
    [ "$status" -ne 0 ]                                                                   # the override line went with the file it named
    # a path that is not absolute: ignored by systemd with a warning, so no file, the same reading and the same rewrite
    cp "$unit.clean" "$unit"; grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; _svc_line "$unit" 'EnvironmentFile=-rel/service.env'
    run _sd_read "$unit" envfile                                                          # the run form: an oracle that raised is a nonzero status,
    [ "$status" -eq 0 ]                                                                   # not an empty answer (round 6 of fork PR #778, tests-5)
    [ "$output" = "" ]
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/svc.env" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=-$HOME/.config/romp/service.env" "$unit"
    run grep -F 'rel/service.env' "$unit"
    [ "$status" -ne 0 ]
}

@test "rewrite (Linux): a hand ExecStart whose quoted path carries a control character (a tab) is refused as an executable name systemd refuses, the refusal's second line naming the move and the install with no daemon-reload step; the install road refuses the same path" {
    # round 4 (tests-4, extra7-4): _exec_path_unsafe's control-character arm had no case on either road, and the unit-scan site's remedy
    # named the install route itself, so the shared tail then added "then systemctl --user daemon-reload", a step the install already
    # performs; the site has its own second line now, the shape of _exec_path_refuse's.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" tab=$'\t'
    _old_unit "$unit"; grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    mkdir -p "$TEST_DIR/t${tab}ab"
    _svc_line "$unit" "ExecStart=\"$TEST_DIR/t${tab}ab/romp-manager\" up"
    [ "$(_sd_read "$unit" exec0)" = "ERROR: Executable name contains special characters: $TEST_DIR/t${tab}ab/romp-manager" ]
    _three_roads_refuse "$unit" "a quote, a backslash or a control character, which systemd refuses in an executable name" "then systemctl --user daemon-reload"
    # the round-5 preface's third commit (fork PR #778, 2026-09-19): the remedy said the install restarts the manager, which a plain Linux
    # install does not (daemon-reload, enable --now, which leaves an active unit as it is; no road of the reader calls restart), so it now
    # says what the install does and names the restart the user runs; the pin holds the whole corrected line and the old clause absent
    [[ "$output" == *"  Move the clone to a path without those characters (the same characters are fine in ROMP_DIR and the service.env path; ExecStart's command path is the one systemd checks) and run romp-service install from it, which writes the unit afresh, reloads systemd and runs enable --now, which starts an inactive unit and leaves a running one as it is; a running manager keeps its old unit until its next restart:  systemctl --user restart romp-manager"* ]]
    [[ "$output" != *"restarts the manager"* ]]
    ROMP_MANAGER_BIN="$TEST_DIR/t${tab}ab/romp-manager" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"contains a quote, a backslash or a control character"* ]]
    [[ "$output" == *"nothing was written"* ]]
}

@test "rewrite (Linux): a hand value ending in one bare percent is a literal percent to systemd and to the reader: accepted, read back whole by the oracle, written back with the percent doubled" {
    # round 4 (tests-5, narrowed by the refuter to this arm): dropping the trailing-percent case in _unit_specifiers turned this form
    # into a false refusal on rewrite and --check, and no case fed it (a value the writer emits is doubled before the reader sees a tail)
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/pct%'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = '/x/pct%' ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"disagree"* ]]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR=/x/pct%%"' "$unit"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = '/x/pct%' ]
    CLAUDE_CONFIG_DIR='/x/pct%' ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
}

@test "rewrite (macOS): without plutil, romp's own one-line layout carrying another job's Label, no Label entry, or a Label split across two lines is refused by the fallback's gate as not romp's one-line form, exit 5 and byte for byte, on rewrite, rewrite --check and the marked child's install" {
    # round 4 (extra7-3): the gate at the head of the fallback reader was unpinned (an `if false` left the suite green), and the one input
    # it alone refuses, romp's layout with a foreign Label, had no case; the refuter found it also guards an absent Label and a split one.
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here" form
    ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null; cp "$plist" "$plist.clean"
    for form in foreign absent split; do
        case "$form" in
            foreign) sed 's|<key>Label</key><string>com.romp.manager</string>|<key>Label</key><string>com.other.job</string>|' "$plist.clean" > "$plist" ;;
            absent)  grep -v '<key>Label</key>' "$plist.clean" > "$plist" ;;
            split)   python3 - "$plist.clean" "$plist" <<'PY'
import sys
s = open(sys.argv[1]).read().replace("<key>Label</key><string>com.romp.manager</string>", "<key>Label</key>\n  <string>com.romp.manager</string>")
open(sys.argv[2], "w").write(s)
PY
                     ;;
        esac
        cp "$plist" "$plist.before"
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"its Label entry is not <key>Label</key><string>com.romp.manager</string> on one line"* ]]
        [[ "$output" == *"no plutil is available"* ]]
        [[ "$output" != *"is not romp's"* ]]                                              # the plutil road's wording, not this road's
        cmp -s "$plist" "$plist.before"
        ROMP_PLUTIL="$none" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        cmp -s "$plist" "$plist.before"
        run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" \
            ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" ROMP_NODE_SRC="$ROMP_NODE_SRC" ROMP_PLUTIL="$none" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
        [ "$status" -eq 5 ]
        cmp -s "$plist" "$plist.before"
    done
}

@test "rewrite (Linux): a hand PATH line carrying %h goes back byte for byte and is no refusal, since the PATH line is replayed as written and systemd expands the text, as a specifier in a variable the rewrite drops is none; a specifier in a value the writer re-encodes is still refused" {
    # round 4 (extra5-2): the specifier refusal fired on PATH's value, which the rewrite road never uses (the line is replayed), so an
    # ordinary `Environment=PATH=%h/bin:...` stopped every deploy over a line that round-trips; the refuter found live user units in
    # this form. The decode is not skipped, only the refusal: %% is still undone in the value the reader holds.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"; grep -v '^Environment=PATH=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" 'Environment=PATH=%h/.local/bin:/usr/bin:/bin'
    [ "$(_sd_read "$unit" env PATH)" = "$HOME/.local/bin:/usr/bin:/bin" ]                # systemd's reading, %h expanded
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    _marked_install_ok
    grep -qxF 'Environment=PATH=%h/.local/bin:/usr/bin:/bin' "$unit"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment=PATH=%h/.local/bin:/usr/bin:/bin' "$unit"                     # the line, byte for byte
    [ "$(grep -cE '^Environment="?PATH=' "$unit")" -eq 1 ]
    [ "$(_sd_read "$unit" env PATH)" = "$HOME/.local/bin:/usr/bin:/bin" ]
    cp "$unit" "$unit.kept"; _svc_line "$unit" 'Environment=ADMIN_KNOB=%t/romp'
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    cmp -s "$unit" "$unit.kept"                                                           # a dropped variable's specifier: no refusal, the line gone as every hand line is
    _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=%h/.claude-romp'
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"the specifier %h in CLAUDE_CONFIG_DIR"* ]]
}

@test "rewrite (Linux): the EnvironmentFile= line's prefix is the unit's own: a mandatory line (no dash) goes back mandatory, a tolerant one (the dash) tolerant, and a unit with no line gets the tolerant default" {
    # round 4 (extra5-3): the reader stripped the leading dash and the writer always wrote one, so a hand-written mandatory line came
    # back tolerant, a form systemd reads differently (a missing file is an error under one and nothing under the other). Asserted on
    # the raw line: the oracle strips the dash on read and would pass either way.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    _old_unit "$unit"; grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" "EnvironmentFile=$TEST_DIR/mandatory.env"
    [ "$(_sd_read "$unit" envfile)" = "$TEST_DIR/mandatory.env" ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=$TEST_DIR/mandatory.env" "$unit"
    run grep -F "EnvironmentFile=-" "$unit"
    [ "$status" -ne 0 ]
    [ "$(_sd_read "$unit" envfile)" = "$TEST_DIR/mandatory.env" ]
    grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; _svc_line "$unit" "EnvironmentFile=-$TEST_DIR/tolerant.env"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=-$TEST_DIR/tolerant.env" "$unit"
    grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=-$HOME/.config/romp/service.env" "$unit"                  # no line: the tolerant default (round 2's rule)
}

@test "rewrite and install (Linux): a kept value ending in a newline is refused on all three roads and on install, since every read of a value loses a trailing newline through a command substitution; a newline inside a value round-trips through the writer's escape and agrees with the shell carrying it" {
    # round 4 (correctness-2, in the refuter's scope): systemd decodes a trailing \n inside quotes into a real newline, and _file_value,
    # _same_path's basename and pwd -P and the plist road all read through $(), which strips it, so the compare compared another value
    # and the writer wrote one; a newline inside the value already round-tripped, so only a value ENDING in one is refused. The install
    # refuses the same value from the environment, since the file it would write is one every later rewrite refuses.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" nl=$'\n'
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    _svc_line "$unit" 'Environment="CLAUDE_CONFIG_DIR=/x/a\n"'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \n \n" ]   # systemd: the newline is in the value
    _three_roads_refuse "$unit" "the value of CLAUDE_CONFIG_DIR ends in a newline, which this reader loses on the read"
    cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=\"ROMP_STATE_DIR=$TEST_DIR/st\\n\""
    _three_roads_refuse "$unit" "the value of ROMP_STATE_DIR ends in a newline"
    [ ! -e "$TEST_DIR/st/restart-audit.jsonl" ]
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment="CLAUDE_CONFIG_DIR=/x/a\nb"'
    CLAUDE_CONFIG_DIR="/x/a${nl}b" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR=/x/a\nb"' "$unit"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \n b \n" ]
    rm -f "$unit"
    CLAUDE_CONFIG_DIR="/x/a${nl}" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR in this environment ends in a newline"* ]]
    [[ "$output" == *"nothing was written"* ]]
    [ ! -e "$unit" ]
    ROMP_STATE_DIR="$TEST_DIR/st${nl}" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_STATE_DIR in this environment ends in a newline"* ]]
    [ ! -e "$unit" ]
    CLAUDE_CONFIG_DIR="/x/a${nl}b" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR=/x/a\nb"' "$unit"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
}

@test "rewrite and install (macOS): a plist value ending in a newline (&#10; last) is refused by the fallback reader and through plutil, byte for byte on all three roads; a newline inside a value is decoded (&#10; in the middle), agrees with the shell, and is written back as &#10; on one line so the entry stays readable; an install with such a value writes it that way, and refuses one ending in a newline" {
    # round 4 (correctness-3): _xml_unescape's newline case was dead (its result went through a $()), and the writer put a raw newline into
    # the entry, splitting it across lines for the next read to refuse. The decoder writes into a variable now and the writer escapes
    # the newline and the carriage return as numeric references; a value ENDING in a newline is refused, as the unit's is.
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" none="$TEST_DIR/no-plutil-here" nl=$'\n' reader
    _plutil_stub
    CLAUDE_CONFIG_DIR="/x/a${nl}b" ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>/x/a&#10;b</string>' "$plist"          # one line, the reference
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \n b \n" ]
    cp "$plist" "$plist.mid"
    for reader in "PATH=$TEST_DIR/plutil-bin:$PATH" "ROMP_PLUTIL=$none"; do
        cp "$plist.mid" "$plist"
        run env "$reader" CLAUDE_CONFIG_DIR="/x/a${nl}b" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        run env "$reader" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite
        [ "$status" -eq 0 ]
        grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>/x/a&#10;b</string>' "$plist"
        [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \n b \n" ]
        sed 's|<string>/x/a&#10;b</string>|<string>/x/a\&#10;</string>|' "$plist.mid" > "$plist"; cp "$plist" "$plist.before"
        [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \n \n" ]
        run env "$reader" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"has a CLAUDE_CONFIG_DIR entry whose value ends in a newline"* ]]
        [[ "$output" == *"nothing was rewritten"* ]]
        cmp -s "$plist" "$plist.before"
        run env "$reader" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        cmp -s "$plist" "$plist.before"
        run env -i HOME="$HOME" PATH="$PATH" "$reader" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Darwin ROMP_SERVICE_NO_LOAD=1 ROMP_LAUNCHD_DIR="$ROMP_LAUNCHD_DIR" \
            ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" ROMP_NODE_SRC="$ROMP_NODE_SRC" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
        [ "$status" -eq 5 ]
        cmp -s "$plist" "$plist.before"
    done
    rm -f "$plist"
    CLAUDE_CONFIG_DIR="/x/a${nl}" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR in this environment ends in a newline"* ]]
    [ ! -e "$plist" ]
}

@test "rewrite (Linux): drop-ins beside the unit are not read, and the rewrite says so at exit 0 on rewrite, --check and the marked child's install, naming the directory and the files; a drop-in that resets ExecStart through a shell wrapper (the live shape) is no refusal and is left byte for byte; with no drop-in nothing is said" {
    # round 4 (extra6-2, in the refuters' form): the reader reads the fragment alone while systemd composes the service with every
    # <unit>.d/*.conf, so the identity check speaks for the file; both fixes first offered (reading drop-ins into the scan, refusing on a
    # drop-in ExecStart) were shown to refuse a live deploy whose drop-in resets ExecStart through `zsh -c 'exec ... up'`, a form the
    # reader's own rule refuses, so the notice is advisory. The residual (a fragment with no ExecStart beside a non-resetting drop-in
    # that supplies one, after which systemd refuses the merged unit as having two) is recorded at _dropin_advisory.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" d="$ROMP_SYSTEMD_DIR/romp-manager.service.d"
    _old_unit "$unit"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" != *"drop-ins"* ]]
    mkdir -p "$d"
    printf '[Service]\nExecStart=\nExecStart=/usr/bin/zsh -c '"'"'exec %s up'"'"'\n' "$ROMP_MANAGER_BIN" > "$d/10-shell-env.conf"
    printf '[Service]\nMemorySwapMax=0\n' > "$d/20-noswap.conf"
    cp "$d/10-shell-env.conf" "$TEST_DIR/10.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"drop-ins also define this service and were not read: 10-shell-env.conf, 20-noswap.conf (under $d"* ]]
    [[ "$output" == *"login service unit on disk and this environment agree"* ]]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"drop-ins also define this service and were not read"* ]]
    cmp -s "$d/10-shell-env.conf" "$TEST_DIR/10.before"
    grep -qxF "ExecStart=$ROMP_MANAGER_BIN up" "$unit"                                    # the file keeps its own command; the drop-in is systemd's
    _marked_install_ok
    [[ "$output" == *"drop-ins also define this service and were not read"* ]]
}

@test "rewrite (Linux): a line that is not valid UTF-8 is refused on all three roads, since systemd refuses the whole file on it and loads nothing; a valid non-ASCII value reads whole, agrees with the shell and round-trips" {
    # round 4, found while running the header rule against systemd: "String is not UTF-8 clean" is fatal to the load on 255.4, not a
    # skipped line, so a reader that read on replayed a value systemd never applied, the class of the malformed header
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" e=$'\xc3\xa9'
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    _svc_bytes "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/\xff\n'
    [[ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" == "ERROR: String is not UTF-8 clean"* ]]
    _three_roads_refuse "$unit" "it is not valid UTF-8, on which systemd refuses the whole file"
    cp "$unit.clean" "$unit"; _svc_bytes "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/caf\xc3\xa9\n'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/caf$e" ]
    CLAUDE_CONFIG_DIR="/x/caf$e" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/caf$e" ]
}

# Round 4's mutation pass (2026-09-19): the lens ran the suite under one mutation per claim below and it stayed green, so each got
# its case here, red under exactly that mutation and green with the code restored, the refused form and the accepted neighbour in
# the same test. The two oracle cases pin the oracle itself: its refusal to guess at a specifier it does not model, and its name rule.

@test "rewrite (Linux): a UTF-8 byte order mark is read as systemd reads it: the first mark at the raw start of any line comes off and no other does, so a unit beginning with the mark, or with the mark before [Service] on a later line, reads whole on all three roads and is written back without it; a mark before an ExecStart line naming another clone is refused as that clone's, a mark before a kept CLAUDE_CONFIG_DIR line keeps the line and compares it; a second mark, a mark after a tab and a mark behind a marked comment are text, and a marked comment ending in a backslash is the continuation it is to systemd, refused" {
    # round 4 stripped the mark on line 1 alone (the mutation pass: every unit the suite fed the reader began with [Unit], so the strip changed
    # no verdict); round 6 of fork PR #778 (correctness-1, extra5-1; each shape below run against systemd-analyze --user verify on 255.4)
    # found systemd's rule is one latch per FILE: the first mark at the raw start of any line comes off, after the comment test, and never
    # another. So a mark before a kept line made this reader read the line as absent, and the rewrite wrote this clone's value at exit 0 on
    # all three roads (ExecStart re-pointed at the deploying clone, the D4 class on the success path; a CLAUDE_CONFIG_DIR line dropped), and
    # the mark before [Service], which this case asserted as no header, is a header systemd reads: the unit loads whole.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mgr="$ROMP_MANAGER_BIN" bom=$'\xef\xbb\xbf' other="$TEST_DIR/other/romp-manager" shape
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    # the mark before line 1, [Service] first: whole on three roads, written back without it
    sed -n '/^\[Service\]/,$p' "$unit.clean" > "$unit.svc"
    { printf '%s' "$bom"; cat "$unit.svc"; } > "$unit"
    [ "$(head -c 3 "$unit" | od -An -tx1 | tr -d ' \n')" = efbbbf ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    [ "$(_sd_read "$unit" has ROMP_DIR)" = yes ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"agree"* ]]
    _marked_install_ok
    { printf '%s' "$bom"; cat "$unit.svc"; } > "$unit"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(head -c 3 "$unit" | od -An -tx1 | tr -d ' \n')" != efbbbf ]
    [ "$(head -1 "$unit")" = '[Unit]' ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    # the mark before [Service] on a later line: the header systemd reads and the unit whole (the oracle agrees), written back without the mark
    _bom_before "$unit.clean" "$unit" '[Service]'
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    [ "$(_sd_read "$unit" has ROMP_DIR)" = yes ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    _marked_install_ok
    _bom_before "$unit.clean" "$unit" '[Service]'
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run env LC_ALL=C grep -c $'\xef\xbb\xbf' "$unit"
    [ "$status" -ne 0 ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    # the mark before an ExecStart line naming another clone: systemd runs that clone's manager, and so the identity guard refuses on all
    # three roads, the file byte for byte (the round's HIGH: at exit 0 the rewrite re-pointed it at this clone)
    mkdir -p "$TEST_DIR/other"
    grep -v '^ExecStart=' "$unit.clean" > "$unit.o"; _svc_line "$unit.o" "ExecStart=$other up"
    _bom_before "$unit.o" "$unit" 'ExecStart='
    [ "$(_sd_read "$unit" exec0)" = "$other" ]
    cp "$unit" "$unit.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $other, this clone would write $mgr"* ]]
    [[ "$output" == *"disagree; nothing was rewritten"* ]]
    cmp -s "$unit" "$unit.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $other"* ]]
    cmp -s "$unit" "$unit.before"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
        ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $other"* ]]
    cmp -s "$unit" "$unit.before"
    # the mark before a kept CLAUDE_CONFIG_DIR line: systemd sets it, so the reader keeps the line through a rewrite from a shell without the
    # variable and compares it against a shell carrying another value (the line was dropped at exit 0)
    cp "$unit.clean" "$unit.o"; _svc_line "$unit.o" 'Environment=CLAUDE_CONFIG_DIR=/x/cc'
    _bom_before "$unit.o" "$unit" 'Environment=CLAUDE_CONFIG_DIR='
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
    CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries /x/cc, this environment carries /x/other"* ]]
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR=/x/cc _marked_install_ok
    _bom_before "$unit.o" "$unit" 'Environment=CLAUDE_CONFIG_DIR='
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment=CLAUDE_CONFIG_DIR=/x/cc' "$unit"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
    # the mark as TEXT: a second mark (line 1 carries the first), a mark after a tab, and a mark behind a marked comment line (no comment to
    # systemd, and it spends the latch): the line is an unknown key name to systemd, so the variable is not set, the oracle says no, and the
    # reader keeps nothing of it (a shell carrying another value is not compared, since the file assigns nothing)
    for shape in second tab comment; do
        cp "$unit.clean" "$unit.o"; _svc_line "$unit.o" 'Environment=CLAUDE_CONFIG_DIR=/x/cc'
        case "$shape" in
            second) _bom_before "$unit.o" "$unit.t" 'Environment=CLAUDE_CONFIG_DIR='; _bom_before "$unit.t" "$unit" '[Unit]' ;;
            tab) _bom_before "$unit.o" "$unit" 'Environment=CLAUDE_CONFIG_DIR=' $'\t' ;;
            comment) _bom_before "$unit.o" "$unit" 'Environment=CLAUDE_CONFIG_DIR=' "$bom"$'# c\n' ;;
        esac
        [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
        CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        run grep -c '/x/cc' "$unit"
        [ "$status" -ne 0 ]
    done
    # a marked comment ending in a backslash: no comment to systemd, whose backslash joins the next line, so the kept line after it is
    # swallowed; the reader refuses the continuation on all three roads (a reader that stripped the mark before its comment test would read
    # the marked line as a comment and take the swallowed line as live: the dangerous direction)
    cp "$unit.clean" "$unit.o"; _svc_line "$unit.o" 'Environment=CLAUDE_CONFIG_DIR=/x/cc'
    _bom_before "$unit.o" "$unit" 'Environment=CLAUDE_CONFIG_DIR=' "$bom"'# c\'$'\n' ''
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    _three_roads_refuse "$unit" "ends in a backslash, a continuation"
}

@test "rewrite (Linux): the byte order mark's remaining shapes read as systemd reads them on all three roads: the mark beside a CRLF line ending (before line 1, before a kept line, alone on the line that closes a continuation, before [Service]); before the PATH line, the EnvironmentFile line and a ROMP_DIR line (another clone's refused as that clone's, this clone's kept); before an indented, a quoted and a trailing-blank kept line; a marked empty Environment= reset; a marked whitespace-only line; two marks on one line, a marked second ExecStart with the latch spent and a marked ExecStart= reset; a mark inside a value, before a name, before the ExecStart path and inside the section name; and a continuation closed by a line holding only a second mark, which systemd joins and this reader refuses as the continuation it is; the marked child's install runs with the shell's CLAUDE_CONFIG_DIR, so a disagreeing value is refused on that road too" {
    # the round-6 addendum of fork PR #778: the lens over the round-6 commit ran these shapes by hand against systemd-analyze --user verify on
    # 255.4 and against the reader, found them agreeing, and named them unpinned; each is a fixture of the differential's fold batch too
    # (fold-bom-*). At f7525fe16 the first leg is red: a mark before a kept line under CRLF read the line as absent, the D4 class on the
    # success path, and the marked child's install then wrote the file without it at exit 0.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mgr="$ROMP_MANAGER_BIN" bom=$'\xef\xbb\xbf' pathval form v repo
    repo="$(cd "$(dirname "$SVC")/.." && pwd)"
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    pathval="$(_sd_read "$unit.clean" env PATH)"; [ -n "$pathval" ]
    # CRLF: the mark before a kept line (the red leg at f7525fe16)
    cp "$unit.clean" "$unit.o"; _svc_line "$unit.o" 'Environment=CLAUDE_CONFIG_DIR=/x/cc'
    _b_crlf_kept() { _bom_before "$unit.o" "$unit" 'Environment=CLAUDE_CONFIG_DIR='; _line_endings "$unit" crlf; }
    _b_crlf_kept; grep -q $'\r' "$unit"
    _kept /x/cc _b_crlf_kept
    grep -qxF 'Environment=CLAUDE_CONFIG_DIR=/x/cc' "$unit"
    # tests-4's pin: the marked child's install from a shell carrying another value is refused, the file byte for byte (_marked_install
    # forwards the variable; a helper that dropped it ran the child with the variable unset, which keeps the file's line at exit 0)
    _b_crlf_kept; cp "$unit" "$unit.before"
    CLAUDE_CONFIG_DIR=/x/other _marked_install
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries /x/cc, this environment carries /x/other"* ]]
    [[ "$output" == *"disagree; nothing was rewritten"* ]]
    cmp -s "$unit" "$unit.before"
    # CRLF: the mark before line 1 and before [Service], whole on the three roads, written back without the mark and with LF
    sed -n '/^\[Service\]/,$p' "$unit.clean" > "$unit.svc"
    _b_crlf_first() { { printf '%s' "$bom"; cat "$unit.svc"; } > "$unit"; _line_endings "$unit" crlf; }
    _b_crlf_service() { _bom_before "$unit.clean" "$unit" '[Service]'; _line_endings "$unit" crlf; }
    _whole _b_crlf_first
    _whole _b_crlf_service
    # a mark alone on the line that closes an open continuation, under LF and under CRLF: a blank to systemd (the latch free), so the pending
    # line stands as its own; the reader reads it the same on the three roads and writes it without the backslash
    for form in lf crlf; do
        _b_cont() { cp "$unit.clean" "$unit"; _svc_bytes "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc\\\n\xef\xbb\xbf\nEnvironment=ADMIN_KNOB=1\n'; [[ "$form" != crlf ]] || _line_endings "$unit" crlf; }
        _b_cont
        [ "$(_sd_read "$unit" env ADMIN_KNOB)" = 1 ]
        _kept /x/cc _b_cont
        run grep -c '\\$' "$unit"
        [ "$status" -ne 0 ]
    done
    # the mark before the PATH line, which the rewrite replays as written: the written line is the one without the mark and systemd reads
    # the same PATH (at f7525fe16 the line read as absent and the rewrite omitted PATH)
    _b_path() { _bom_before "$unit.clean" "$unit" 'Environment=PATH='; }
    _b_path
    [ "$(_sd_read "$unit" env PATH)" = "$pathval" ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    _marked_install_ok
    [ "$(_sd_read "$unit" env PATH)" = "$pathval" ]
    _b_path
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF "Environment=PATH=$pathval" "$unit"
    [ "$(grep -cE '^Environment="?PATH=' "$unit")" -eq 1 ]
    run env LC_ALL=C grep -c $'\xef\xbb\xbf' "$unit"
    [ "$status" -ne 0 ]
    [ "$(_sd_read "$unit" env PATH)" = "$pathval" ]
    # the mark before a non-default EnvironmentFile line: the file's path is kept and compared (at f7525fe16 the line read as absent, the
    # default path was written in its place and a shell naming the file's own path was refused)
    grep -v '^EnvironmentFile=' "$unit.clean" > "$unit.o"; _svc_line "$unit.o" "EnvironmentFile=-$TEST_DIR/svc.env"
    _b_envf() { _bom_before "$unit.o" "$unit" 'EnvironmentFile='; }
    _b_envf
    [ "$(_sd_read "$unit" envfile)" = "$TEST_DIR/svc.env" ]
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/svc.env" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/other.env" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_SERVICE_ENV_FILE: the file reads $TEST_DIR/svc.env, this environment names $TEST_DIR/other.env"* ]]
    _marked_install_ok
    grep -qxF "EnvironmentFile=-$TEST_DIR/svc.env" "$unit"
    _b_envf
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=-$TEST_DIR/svc.env" "$unit"
    [ "$(_sd_read "$unit" envfile)" = "$TEST_DIR/svc.env" ]
    # the mark before a ROMP_DIR line: another clone's is refused on the three roads as that clone's, the file byte for byte (at f7525fe16 the
    # line read as absent and the rewrite wrote this clone's ROMP_DIR at exit 0, the D4 re-point on a value the identity guard exists for);
    # this clone's is kept
    grep -q "^Environment=ROMP_DIR=$repo\$" "$unit.clean"
    sed "s|^Environment=ROMP_DIR=.*|Environment=ROMP_DIR=$TEST_DIR/otherclone|" "$unit.clean" > "$unit.o"
    _bom_before "$unit.o" "$unit" 'Environment=ROMP_DIR='
    [ "$(_sd_read "$unit" env ROMP_DIR)" = "$TEST_DIR/otherclone" ]
    cp "$unit" "$unit.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_DIR: the file names $TEST_DIR/otherclone, this clone is $repo"* ]]
    [[ "$output" == *"disagree; nothing was rewritten"* ]]
    cmp -s "$unit" "$unit.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_DIR: the file names $TEST_DIR/otherclone"* ]]
    cmp -s "$unit" "$unit.before"
    _marked_install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ROMP_DIR: the file names $TEST_DIR/otherclone"* ]]
    cmp -s "$unit" "$unit.before"
    _b_rompdir() { _bom_before "$unit.clean" "$unit" 'Environment=ROMP_DIR='; }
    _whole _b_rompdir
    grep -qxF "Environment=ROMP_DIR=$repo" "$unit"
    # an indented kept line, a quoted one and one with trailing blanks behind the mark: systemd strips the mark, then the blanks, and unquotes
    # the word; kept and compared as the value it reads
    for form in "  Environment=CLAUDE_CONFIG_DIR=/x/cc|/x/cc" 'Environment="CLAUDE_CONFIG_DIR=/x/c c"|/x/c c' "Environment=CLAUDE_CONFIG_DIR=/x/cc  "$'\t'"|/x/cc"; do
        v="${form#*|}"
        _b_form() { cp "$unit.clean" "$unit"; _svc_line "$unit" "$bom${form%%|*}"; }
        _b_form
        _kept "$v" _b_form
    done
    # a marked empty Environment= reset after the kept lines: systemd forgets PATH, ROMP_DIR and the kept line before it, and the reader
    # follows (PATH omitted from the written unit, ROMP_DIR written as this clone's, the documented absence behaviour; a shell carrying
    # another CLAUDE_CONFIG_DIR is not compared, since the file assigns nothing at its end). At f7525fe16 the reset read as absent and PATH
    # was written back where systemd had reset it
    _b_reset() { cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc' "${bom}Environment="; }
    _b_reset
    [ "$(_sd_read "$unit" has PATH)" = no ]
    [ "$(_sd_read "$unit" has ROMP_DIR)" = no ]
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    _marked_install_ok
    [ "$(_sd_read "$unit" has PATH)" = no ]
    _b_reset
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -cE '^Environment="?PATH=' "$unit"
    [ "$status" -ne 0 ]
    [ "$(_sd_read "$unit" has PATH)" = no ]
    grep -qxF "Environment=ROMP_DIR=$repo" "$unit"
    run grep -c '/x/cc' "$unit"
    [ "$status" -ne 0 ]
    # a marked whitespace-only line spends the strip and is a blank; the kept line after it is read
    _b_ws() { cp "$unit.clean" "$unit"; _svc_line "$unit" "$bom  "$'\t' 'Environment=CLAUDE_CONFIG_DIR=/x/cc'; }
    _b_ws
    _kept /x/cc _b_ws
    # two marks on one line: the second is text, so the line is an unknown key to systemd and the variable is not set; the reader keeps
    # nothing of it
    cp "$unit.clean" "$unit"; _svc_line "$unit" "$bom${bom}Environment=CLAUDE_CONFIG_DIR=/x/cc"
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -c '/x/cc' "$unit"
    [ "$status" -ne 0 ]
    # a marked second ExecStart line with the latch spent on line 1: text to systemd, which runs the first; no second-ExecStart refusal here,
    # and the rewrite drops the line. A marked empty ExecStart= reset before the real line: a reset to systemd, and the real line stands
    mkdir -p "$TEST_DIR/other"
    _b_second_exec() { cp "$unit.clean" "$unit.o"; _svc_line "$unit.o" "${bom}ExecStart=$TEST_DIR/other/romp-manager up"; { printf '%s' "$bom"; cat "$unit.o"; } > "$unit"; }
    _whole _b_second_exec
    run grep -c "$TEST_DIR/other/romp-manager" "$unit"
    [ "$status" -ne 0 ]
    _b_exec_reset() { _bom_before "$unit.clean" "$unit" 'ExecStart=' '' "$bom"$'ExecStart=\n'; }
    _whole _b_exec_reset
    [ "$(grep -c '^ExecStart=' "$unit")" -eq 1 ]
    # a mark in the middle of a line: inside a kept value it is bytes of the value, carried and compared; before the name it is no assignment
    # to systemd (Invalid environment assignment, ignoring), so the variable is not set and the reader keeps nothing; before the ExecStart
    # path the command is not absolute, which systemd refuses whole, and the reader refuses the identity (the file runs the marked path);
    # inside the section name the section is one systemd does not know, so the kept lines under it are refusal 7
    _b_mid_value() { cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/c${bom}c"; }
    _b_mid_value
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/c${bom}c" ]
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries /x/c${bom}c, this environment carries /x/cc"* ]]
    CLAUDE_CONFIG_DIR="/x/c${bom}c" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR="/x/c${bom}c" _marked_install_ok
    _b_mid_value
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/c${bom}c" ]
    cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=${bom}CLAUDE_CONFIG_DIR=/x/cc"
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
    CLAUDE_CONFIG_DIR=/x/other ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    run grep -c '/x/cc' "$unit"
    [ "$status" -ne 0 ]
    grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=${bom}$mgr up"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Neither a valid executable name nor an absolute path"* ]]
    cp "$unit" "$unit.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs ${bom}$mgr, this clone would write $mgr"* ]]
    cmp -s "$unit" "$unit.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    cmp -s "$unit" "$unit.before"
    _marked_install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs ${bom}$mgr"* ]]
    cmp -s "$unit" "$unit.before"
    sed "s/^\[Service\]/[Ser${bom}vice]/" "$unit.clean" > "$unit"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Service has no ExecStart"* ]]
    _three_roads_refuse "$unit" "ExecStart under [Ser${bom}vice], a section systemd does not read it in"
    # a continuation closed by a line holding only a second mark, the latch spent by a marked line 1: systemd joins the two (the mark a word it
    # drops: Invalid environment assignment, ignoring) and reads the kept value; the reader refuses the join as the continuation it is, on the
    # three roads, the safe direction (the header's refusal 3 names the shape)
    cp "$unit.clean" "$unit.o"; _svc_bytes "$unit.o" 'Environment=CLAUDE_CONFIG_DIR=/x/cc\\\n\xef\xbb\xbf\n'
    { printf '%s' "$bom"; cat "$unit.o"; } > "$unit"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
    _three_roads_refuse "$unit" "ends in a backslash, a continuation systemd joins to the next line"
}

@test "rewrite (Linux): a shell value ending in a newline names no place the file names: CLAUDE_CONFIG_DIR and ROMP_MANAGER_BIN carrying the file's own path plus a newline are refused on rewrite, rewrite --check and the marked child's install as differing values, never compared equal through basename and pwd -P, which lose the newline; the same values without it agree" {
    # the mutation pass (2026-09-19): the guard in _same_path had no case of its own, since the file side cannot carry a trailing
    # newline past the scan; the environment side can, and without the guard the place compare ran through two command
    # substitutions that strip it, so a shell value with the newline compared equal to the file's and a differing value went unsaid
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mgr="$ROMP_MANAGER_BIN" nl=$'\n'
    _old_unit "$unit"; mkdir -p "$TEST_DIR/cc"
    _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=$TEST_DIR/cc"
    cp "$unit" "$unit.before"
    CLAUDE_CONFIG_DIR="$TEST_DIR/cc" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR="$TEST_DIR/cc$nl" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries $TEST_DIR/cc, this environment carries $TEST_DIR/cc"* ]]
    [[ "$output" == *"disagree; nothing was rewritten"* ]]
    CLAUDE_CONFIG_DIR="$TEST_DIR/cc$nl" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    cmp -s "$unit" "$unit.before"
    run env -i HOME="$HOME" PATH="$PATH" CLAUDE_CONFIG_DIR="$TEST_DIR/cc$nl" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 \
        ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"CLAUDE_CONFIG_DIR: the file carries $TEST_DIR/cc"* ]]
    cmp -s "$unit" "$unit.before"
    # the manager's path: the file's ExecStart against a ROMP_MANAGER_BIN ending in a newline is another clone, never the same file
    ROMP_MANAGER_BIN="$mgr$nl" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $mgr, this clone would write $mgr"* ]]
    [[ "$output" == *"ran from a clone that is not the installed one"* ]]
    ROMP_MANAGER_BIN="$mgr$nl" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    cmp -s "$unit" "$unit.before"
    run env -i HOME="$HOME" PATH="$PATH" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 \
        ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$mgr$nl" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"ExecStart: the file runs $mgr"* ]]
    cmp -s "$unit" "$unit.before"
    ROMP_MANAGER_BIN="$mgr" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
}

@test "rewrite (Linux): on a rewrite that reloads systemd, the drop-in advisory also lists the loaded unit's DropInPaths as systemctl reports them: one beside the unit is named once, by its file name, one elsewhere is added by its path, and one systemctl alone knows is said with no directory beside the unit; rewrite --check and the marked child's install ask systemctl nothing and list the directory alone; nothing reported and no directory: nothing said" {
    # the mutation pass (2026-09-19): the suite's setup exports ROMP_SERVICE_NO_LOAD for every case, so the branch that asks systemctl
    # never ran and the suite stayed green with it unreachable; here the rewrite loads, through a stub that answers DropInPaths
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" d="$ROMP_SYSTEMD_DIR/romp-manager.service.d" far="$TEST_DIR/elsewhere/romp-manager.service.d/50-site.conf"
    local stub="$TEST_DIR/systemctl-stub" calls="$TEST_DIR/systemctl-calls" answer="$TEST_DIR/dropinpaths"
    unset ROMP_SERVICE_NO_LOAD
    _old_unit "$unit"
    cat > "$stub" <<EOF
#!/bin/sh
echo "\$*" >> "$calls"
case "\$2" in
  is-active) echo active ;;
  show) case "\$*" in
          *NeedDaemonReload*) echo no ;;
          *FragmentPath*) echo "$unit" ;;
          *DropInPaths*) cat "$answer" ;;
        esac ;;
  *) exit 0 ;;
esac
EOF
    chmod +x "$stub"
    printf '%s\n' "$far" > "$answer"                                                     # a drop-in at another search-path level, no directory beside the unit
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"drop-ins also define this service and were not read: $far (under $d, and systemd's other search paths)"* ]]
    [[ "$output" == *"Rewrote the login service unit"* ]]
    grep -qx -- '--user show -p DropInPaths --value romp-manager.service' "$calls"
    mkdir -p "$d"; printf '[Service]\nMemorySwapMax=0\n' > "$d/10-local.conf"
    printf '%s %s\n' "$d/10-local.conf" "$far" > "$answer"                               # systemctl names the directory's own too: once, by file name
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"were not read: 10-local.conf, $far (under $d"* ]]
    [[ "$output" != *"$d/10-local.conf"* ]]
    rm -f "$calls"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check              # --check calls systemctl not at all: the directory alone
    [ "$status" -eq 0 ]
    [[ "$output" == *"were not read: 10-local.conf (under $d"* ]]
    [[ "$output" != *"50-site"* ]]
    [ ! -e "$calls" ]
    _marked_install_ok
    [[ "$output" == *"were not read: 10-local.conf (under $d"* ]]
    [[ "$output" != *"50-site"* ]]
    [ ! -e "$calls" ]
    printf '%s\n' "$d/10-local.conf" > "$answer"                                          # systemctl adds nothing the directory did not say
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"were not read: 10-local.conf (under $d, and systemd's other search paths)"* ]]
    rm -rf "$d"; : > "$answer"
    ROMP_SYSTEMCTL="$stub" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    [[ "$output" != *"drop-ins"* ]]
}

@test "install and rewrite (macOS and Linux): a carriage return inside a value is written as &#13; in the plist and as \\r in the unit, so launchd and systemd read the return the shell carries (a raw return in XML character data reads as a line feed): the value agrees with the shell under both plist readers and with the oracle, goes back the same way on rewrite, and a value ending in a return is kept whole, not refused" {
    # the mutation pass (2026-09-19): the newline case had its test and the return case none, so the plist writer's &#13; could go
    # and every case stayed green; a raw return in an XML string is normalised to a line feed by the parser, plistlib's here,
    # launchd's on a mac, so the manager would have read another value than the one installed
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" unit="$ROMP_SYSTEMD_DIR/romp-manager.service" none="$TEST_DIR/no-plutil-here" cr=$'\r' reader
    _plutil_stub
    CLAUDE_CONFIG_DIR="/x/a${cr}b" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>/x/a&#13;b</string>' "$plist"
    run grep -c $'\r' "$plist"
    [ "$status" -ne 0 ]                                                                  # no raw return anywhere in the file
    [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \r b \n" ]
    cp "$plist" "$plist.mid"
    for reader in "PATH=$TEST_DIR/plutil-bin:$PATH" "ROMP_PLUTIL=$none"; do
        cp "$plist.mid" "$plist"
        run env "$reader" CLAUDE_CONFIG_DIR="/x/a${cr}b" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        run env "$reader" CLAUDE_CONFIG_DIR="/x/a${cr}c" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite --check
        [ "$status" -eq 5 ]                                                              # the return is read as itself: what follows it is compared
        run env "$reader" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite
        [ "$status" -eq 0 ]
        grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>/x/a&#13;b</string>' "$plist"
        [ "$(_plist_get "$plist" EnvironmentVariables.CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \r b \n" ]
    done
    rm -f "$plist"
    CLAUDE_CONFIG_DIR="/x/a${cr}" ROMP_OS_OVERRIDE=Darwin run "$SVC" install              # ending in a return: a command substitution keeps it, so no refusal
    [ "$status" -eq 0 ]
    grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>/x/a&#13;</string>' "$plist"
    for reader in "PATH=$TEST_DIR/plutil-bin:$PATH" "ROMP_PLUTIL=$none"; do
        run env "$reader" CLAUDE_CONFIG_DIR="/x/a${cr}" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        run env "$reader" CLAUDE_CONFIG_DIR="/x/a" ROMP_OS_OVERRIDE=Darwin "$SVC" rewrite --check
        [ "$status" -eq 5 ]
    done
    # the unit: the writer's \r escape, which systemd decodes to the return (a raw return in the file would be a line end to it)
    CLAUDE_CONFIG_DIR="/x/a${cr}b" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR=/x/a\rb"' "$unit"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR | od -c | head -1 | tr -s ' ')" = "0000000 / x / a \r b \n" ]
    CLAUDE_CONFIG_DIR="/x/a${cr}b" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    CLAUDE_CONFIG_DIR="/x/a${cr}c" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR=/x/a\rb"' "$unit"
}

@test "rewrite (macOS): the plutil line-end calibration's other branch: a plutil that writes no line end after a raw extract has nothing taken off, so the plist's values read whole through it and a value ending in a newline is still refused; a plutil that writes one has exactly that taken off, on the same two plists" {
    # the mutation pass (2026-09-19): the stand-in plutil always printed a trailing newline, so the branch for one that does not was
    # never run, and setting the flag unconditionally left every case green; with such a plutil the flag set wrongly takes a value's
    # own trailing newline off, and the one refusal that newline exists for is skipped, the value silently shortened
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" stubpath="$TEST_DIR/plutil-bin/plutil" nl=$'\n'
    _plutil_stub nonl
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    [ "$("$stubpath" -extract Label raw -o - "$plist"; printf x)" = "com.romp.managerx" ]   # this plutil writes no line end
    cp "$plist" "$plist.before"
    PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/c ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 5 ]                                                                  # nothing taken off the value: one character short disagrees
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.before"                                                      # a clean-shell rewrite through it leaves the plist byte for byte
    sed 's|<string>/x/cc</string>|<string>/x/cc\&#10;</string>|' "$plist.before" > "$plist"; cp "$plist" "$plist.nl"
    [ "$("$stubpath" -extract EnvironmentVariables.CLAUDE_CONFIG_DIR raw -o - "$plist"; printf x)" = "/x/cc${nl}x" ]   # the value's own newline, no line end after it
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"has a CLAUDE_CONFIG_DIR entry whose value ends in a newline"* ]]
    cmp -s "$plist" "$plist.nl"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    cmp -s "$plist" "$plist.nl"
    _plutil_stub                                                                          # the first branch: a plutil that writes a line end
    [ "$("$stubpath" -extract Label raw -o - "$plist"; printf x)" = "com.romp.manager${nl}x" ]
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"has a CLAUDE_CONFIG_DIR entry whose value ends in a newline"* ]]
    cmp -s "$plist" "$plist.nl"
    cp "$plist.before" "$plist"
    PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.before"
}

@test "rewrite and install (Linux): the control-character arm of the ExecStart-path and section-header refusals is systemd's byte set under any locale: under a UTF-8 locale a manager path holding U+0085 (a C1 control) installs and rewrites and a header naming a section with it is the unknown section it is to systemd, where U+0001 in either is refused under both locales" {
    # round 6 of fork PR #778 (extra8-1): _exec_path_unsafe spelled its arm as bash's [[:cntrl:]], the locale's class, which under a UTF-8
    # locale takes in the C1 controls and U+2028 and U+2029; systemd's string_is_safe is a byte test (below a space, or DEL), so the same
    # path was refused from a UTF-8 shell (C.UTF-8 among them) and written from a C one. Verified on 255.4: a path or a header with U+0085
    # loads (Unknown section, ignored, for the header), U+0001 is Executable name contains special characters and Bad characters in section
    # header. The set is spelled out now, as _ALNUM spells its letters; this case runs the same legs under both locales.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" utf8loc nel=$'\xc2\x85' soh=$'\x01' loc
    utf8loc="$(_utf8_locale)"
    mkdir -p "$TEST_DIR/a${nel}b" "$TEST_DIR/a${soh}b"
    for loc in C "$utf8loc"; do
        rm -f "$unit"
        LC_ALL="$loc" ROMP_MANAGER_BIN="$TEST_DIR/a${nel}b/romp-manager" ROMP_OS_OVERRIDE=Linux run "$SVC" install
        [ "$status" -eq 0 ]
        [ "$(grep -c "a${nel}b/romp-manager up" "$unit")" = 1 ]
        [ "$(_sd_read "$unit" exec0)" = "$TEST_DIR/a${nel}b/romp-manager" ]                  # systemd runs it
        LC_ALL="$loc" ROMP_MANAGER_BIN="$TEST_DIR/a${nel}b/romp-manager" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        LC_ALL="$loc" ROMP_MANAGER_BIN="$TEST_DIR/a${nel}b/romp-manager" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        # a header with the same character: an unknown section to systemd, ignored, and the unit loads; the reader reads past it too
        _svc_line "$unit" "[X${nel}Y]"
        [ "$(_sd_read "$unit" exec0)" = "$TEST_DIR/a${nel}b/romp-manager" ]
        LC_ALL="$loc" ROMP_MANAGER_BIN="$TEST_DIR/a${nel}b/romp-manager" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        # the neighbour systemd refuses, under both locales: U+0001 in the path on install and on a hand line, and in a header
        LC_ALL="$loc" ROMP_MANAGER_BIN="$TEST_DIR/a${soh}b/romp-manager" ROMP_OS_OVERRIDE=Linux run "$SVC" install
        [ "$status" -eq 5 ]
        [[ "$output" == *"contains a quote, a backslash or a control character"* ]]
        rm -f "$unit"; ROMP_OS_OVERRIDE=Linux "$SVC" install >/dev/null; cp "$unit" "$unit.clean"
        grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=$TEST_DIR/a${soh}b/romp-manager up"
        [ "$(_sd_read "$unit" exec0)" = "ERROR: Executable name contains special characters: $TEST_DIR/a${soh}b/romp-manager" ]
        LC_ALL="$loc" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"ExecStart's command path contains a quote, a backslash or a control character"* ]]
        cp "$unit.clean" "$unit"; _svc_line "$unit" "[X${soh}Y]"
        [[ "$(_sd_read "$unit" exec0)" == "ERROR: Bad characters in section header"* ]]
        LC_ALL="$loc" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"Bad characters in section header"* ]]
    done
}

@test "rewrite (Linux): a reader that cannot check does not report a failed check: with neither iconv nor python3 on PATH a plain ASCII unit reads whole on all three roads (an ASCII line is UTF-8 by definition), a unit with a non-ASCII line is refused as one this reader cannot check, naming what to put on PATH and never saying the line is not UTF-8, the file byte for byte; the same unit with a decoder agrees, and a line that is not UTF-8 is refused as such only when a decoder read it" {
    # round 6 of fork PR #778 (correctness-3): _unit_utf8 mapped a missing python3's exit 127 onto a genuine rejection, so a box with neither
    # decoder on PATH (install.sh's own preflight supports a machine with no python3 on PATH; busybox has no iconv applet) refused a plain
    # ASCII unit at exit 5 saying line 1 is not valid UTF-8, a fact false of the file, with a remedy (write the line in UTF-8) that could not
    # clear it, and install.sh failed the deploy. A checker that cannot check says so; an ASCII line needs no decoder to be decided.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" nodec e=$'\xc3\xa9'
    nodec="$(_nodec_bin)"
    run env PATH="$nodec" bash -c 'command -v iconv || command -v python3'
    [ "$status" -ne 0 ]                                                                   # the premise: neither decoder is found
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    run env LC_ALL=C grep -c $'[\x80-\xff]' "$unit"
    [ "$status" -ne 0 ]                                                                   # the unit is plain ASCII
    PATH="$nodec" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"agree"* ]]
    [[ "$output" != *"not valid UTF-8"* ]]
    run env -i HOME="$HOME" PATH="$nodec" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" \
        ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 0 ]
    PATH="$nodec" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$unit"
    # a non-ASCII kept value: with no decoder the reader cannot check the line and says so, on all three roads; with one it agrees
    cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/caf$e"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/caf$e" ]
    cp "$unit" "$unit.before"
    PATH="$nodec" CLAUDE_CONFIG_DIR="/x/caf$e" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"has a line that is not plain ASCII (the first is line "* ]]
    [[ "$output" == *"this reader cannot check that it is UTF-8 as systemd checks it: neither iconv nor python3 is on PATH; nothing was rewritten"* ]]
    [[ "$output" == *"  Put iconv or python3 on PATH and run the deploy again"* ]]
    [[ "$output" != *"not valid UTF-8"* ]]
    [[ "$output" != *"is in a form this rewrite does not read whole"* ]]
    cmp -s "$unit" "$unit.before"
    PATH="$nodec" CLAUDE_CONFIG_DIR="/x/caf$e" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"neither iconv nor python3 is on PATH"* ]]
    cmp -s "$unit" "$unit.before"
    run env -i HOME="$HOME" PATH="$nodec" CLAUDE_CONFIG_DIR="/x/caf$e" ROMP_UPDATE_CHILD=1 ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 \
        ROMP_SYSTEMD_DIR="$ROMP_SYSTEMD_DIR" ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN" XDG_STATE_HOME="$XDG_STATE_HOME" "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"neither iconv nor python3 is on PATH"* ]]
    cmp -s "$unit" "$unit.before"
    CLAUDE_CONFIG_DIR="/x/caf$e" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check                # the neighbour: a decoder on PATH
    [ "$status" -eq 0 ]
    # a line that is not UTF-8: refused as such when a decoder read it, as one this reader cannot check when none did
    cp "$unit.clean" "$unit"; _svc_bytes "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/a\xffb\n'
    cp "$unit" "$unit.before"
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"it is not valid UTF-8"* ]]
    PATH="$nodec" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"neither iconv nor python3 is on PATH"* ]]
    [[ "$output" != *"not valid UTF-8"* ]]
    cmp -s "$unit" "$unit.before"
}

@test "rewrite (macOS): the plutil line-end calibration reads a scratch plist this reader writes, never the file's Label: a Label ending in a newline is not romp's Label under a plutil that writes no line end and under one that does, refused at exit 5 on rewrite and rewrite --check with the plist byte for byte, alone and beside a value ending in a newline; the clean plist rewrites byte for byte under both; a scratch directory that cannot be made is refused, never read around" {
    # round 6 of fork PR #778 (regression-1): the calibration read the file's own Label and took its value to have no line end, so under a
    # plutil writing none a Label ending in a newline read as the line end: the flag set wrongly, one newline came off every value the reader
    # read, the not-romp's gate passed a Label launchd reads with the newline, _plist_values_whole never fired and the rewrite wrote every
    # value a newline short at exit 0 (the silent value change correctness-2 and correctness-3 closed in round 4, reopened here). One class
    # with the unit reader's byte order mark: the reader reading a value other than the one launchd or systemd reads, then writing.
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" stub nl=$'\n'
    _plutil_stub nonl
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    cp "$plist" "$plist.before"
    sed 's|<string>com.romp.manager</string>|<string>com.romp.manager\&#10;</string>|' "$plist.before" > "$plist.lnl"
    sed 's|<string>/x/cc</string>|<string>/x/cc\&#10;</string>|' "$plist.lnl" > "$plist.both"
    run cmp -s "$plist.lnl" "$plist.before"; [ "$status" -ne 0 ]
    run cmp -s "$plist.both" "$plist.lnl"; [ "$status" -ne 0 ]
    for stub in nonl nl; do
        [ "$stub" = nonl ] || _plutil_stub                                                # the second pass: a plutil that writes a line end
        cp "$plist.lnl" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 5 ]
        [[ "$output" == *"is not romp's: plutil reads its Label as com.romp.manager\\n, not com.romp.manager"* ]]
        [[ "$output" != *"agree"* ]]
        cmp -s "$plist" "$plist.lnl"
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"is not romp's"* ]]
        cmp -s "$plist" "$plist.lnl"
        cp "$plist.both" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        cmp -s "$plist" "$plist.both"
        cp "$plist.before" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 0 ]
        cmp -s "$plist" "$plist.before"
    done
    # the scratch cannot be made: refused, the reason named, nothing read around it
    cp "$plist.before" "$plist"
    TMPDIR="$TEST_DIR/no-such-dir" PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"no scratch directory could be made under $TEST_DIR/no-such-dir"* ]]
    [[ "$output" != *"agree"* ]]
    # round 8 (correctness-3's refuters): the scratch arms are the box's state, not the tool's, so they name a writable TMPDIR or the
    # install as the way out, and not another plutil, which would fail the same way; red before (no remedy line at all)
    [[ "$output" == *"Set TMPDIR to a directory this user can write, or write the plist afresh"* ]]
    [[ "$output" != *"Name another plutil in ROMP_PLUTIL"* ]]
    [[ "$output" != *"This refuses every plist read through this plutil"* ]]
    cmp -s "$plist" "$plist.before"
    # round 7 of fork PR #778 (tests-2): the third arm, a plutil whose Label read-back is neither the value alone nor the value and one line
    # end (two line ends here), refused with the bytes it read, nothing read around; the arm the round-7 calibration makes load-bearing
    _plutil_stub two
    [ "$("$TEST_DIR/plutil-bin/plutil" -extract Label raw -o - "$plist.before"; printf x)" = "com.romp.manager${nl}${nl}x" ]
    cp "$plist.before" "$plist"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 5 ]
    [[ "$output" == *"did not read this reader's scratch plist's Label (romp.calibrate) back as the value alone or as the value and one line end of its own (it read romp.calibrate\\n\\n; a line end is rendered as \\n)"* ]]
    [[ "$output" != *"agree"* ]]
    cmp -s "$plist" "$plist.before"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 5 ]
    [[ "$output" == *"it read romp.calibrate\\n\\n"* ]]
    # round 8 of fork PR #778 (correctness-3): this arm refuses every plist for the tool's life and said neither so nor how to proceed,
    # where its two sibling arms said both; red before on both sentences
    [[ "$output" == *"This refuses every plist read through this plutil, this one included, not this file alone"* ]]
    [[ "$output" == *"Name another plutil in ROMP_PLUTIL, or write the plist afresh"* ]]
    cmp -s "$plist" "$plist.before"
    # the second arm (the refuter's rider): the scratch directory is made but cannot be written to, driven by a mktemp on the stub's PATH that
    # names a regular file, so the write into it fails for any user (a read-only directory would not refuse root); refused with the reason,
    # under both stand-ins and on both verbs, and the arm's STOP is pinned by the success line's absence (the round-7 mutation lens: with the
    # arm printing its reason and returning 0 this leg still saw exit 5 under the default stand-in, from the not-romp gate misreading the
    # clean Label with an uncalibrated flag, while under the no-line-end stand-in the clean plist rewrote at exit 0 with the refusal line
    # printed above the success line)
    printf 'not a directory\n' > "$TEST_DIR/notadir"
    printf '#!/bin/sh\nprintf "%%s\\n" "%s"\n' "$TEST_DIR/notadir" > "$TEST_DIR/plutil-bin/mktemp"; chmod +x "$TEST_DIR/plutil-bin/mktemp"
    for stub in nl nonl; do
        _plutil_stub "$stub"
        for verb in "rewrite --check" rewrite; do
            cp "$plist.before" "$plist"
            PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
            [ "$status" -eq 5 ]
            [[ "$output" == *"the scratch could not be written under ${TMPDIR:-/tmp}; nothing was rewritten"* ]]   # the reader's own spelling of the directory
            [[ "$output" != *"Not a directory"* ]]                                            # the arm's reason, not the shell's
            [[ "$output" == *"Set TMPDIR to a directory this user can write, or write the plist afresh"* ]]   # round 8: the arm's own way out
            [[ "$output" != *"Name another plutil in ROMP_PLUTIL"* ]]
            [[ "$output" != *"agree"* ]]
            [[ "$output" != *"Rewrote"* ]]
            cmp -s "$plist" "$plist.before"
        done
    done
    rm -f "$TEST_DIR/plutil-bin/mktemp"
}

@test "rewrite (macOS): the plutil line-end calibration measures a value with no line end of its own and three that end in one (a top-level string, a nested entry, an array element), so a plutil that writes a line end always or never is told, and one that writes a line end only when the value lacks one, one that writes two, or one that strips the value's own is refused as a tool this reader cannot read through, the probe and the bytes named: under each, a Label, a CLAUDE_CONFIG_DIR or a manager path ending in a newline is refused at exit 5 with the plist byte for byte on rewrite and rewrite --check (read whole and refused as not romp's or as ending in a newline under the two real behaviours; refused before any read under the other three), the clean plist rewrites byte for byte under the two real behaviours and is refused with the tool named under the other three, and nothing is written a newline short at exit 0" {
    # round 7 of fork PR #778 (correctness-1, regression-2, extra5-1, one defect): round 6 calibrated on ONE scratch value with no line end of
    # its own, the one class of value where the flag changes nothing, and applied the answer to values that end in one, where it decides
    # everything. A plutil that writes a line end only when the value lacks one read that scratch exactly as one that always writes it, the
    # flag was set as for the latter, and the file's Label ending in a newline then read a newline short: the not-romp gate opened, the
    # value check never fired, and the rewrite wrote the Label, CLAUDE_CONFIG_DIR and the manager's path a newline short at exit 0 with the
    # success line (round 5's regression-1 again, on the round-6 reader). At c4c8803c3 the lacking and strip legs are red: exit 0, the
    # plist changed. The evidence that no plutil behaves either way, as read (round 8, extra5-1): plutil(1) documents -n as suppressing
    # the terminating newline of a raw extract and says nothing else about the terminator; swift-corelibs-foundation's PLUContext.swift
    # writes it (line 1035) on the flag and the output format alone, never on the value; Apple's plutil is closed source and no plutil
    # binary ran here. So: not seen in what was read, untested on a mac. The reader refuses rather than assumes, and the refusal is the
    # tool's, every plist included.
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" stubpath="$TEST_DIR/plutil-bin/plutil" stub f nl=$'\n' mgr="$ROMP_MANAGER_BIN"
    _plutil_stub nonl
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    cp "$plist" "$plist.before"
    grep -qF "<string>$mgr</string>" "$plist.before"
    sed 's|<string>com.romp.manager</string>|<string>com.romp.manager\&#10;</string>|' "$plist.before" > "$plist.lnl"     # the Label ends in a newline
    sed 's|<string>/x/cc</string>|<string>/x/cc\&#10;</string>|' "$plist.before" > "$plist.vnl"                            # CLAUDE_CONFIG_DIR does
    sed 's|<string>/x/cc</string>|<string>/x/cc\&#10;</string>|' "$plist.lnl" > "$plist.both"                              # both
    sed "s|<string>$mgr</string>|<string>$mgr\&#10;</string>|" "$plist.before" > "$plist.exec"                              # the manager's path does
    for f in lnl vnl both exec; do run cmp -s "$plist.$f" "$plist.before"; [ "$status" -ne 0 ]; done
    for stub in nonl nl lacking two strip; do
        case "$stub" in
          nonl)    _plutil_stub nonl ;;                                                        # never writes a line end
          nl)      _plutil_stub ;;                                                             # always writes one
          lacking) _plutil_stub lacking ;;                                                     # writes one only when the value lacks one
          two)     _plutil_stub two ;;                                                         # writes two
          strip)   _plutil_stub strip ;;                                                       # strips the value's own, writes none
        esac
        # what each stub hands the reader for a Label with a newline of its own (read as the reader reads, with a sentinel); the lacking
        # stub hands the SAME bytes for the Label with one and the Label without, which is the ambiguity the calibration must refuse
        case "$stub" in
          nonl)    [ "$("$stubpath" -extract Label raw -o - "$plist.lnl"; printf x)" = "com.romp.manager${nl}x" ] ;;
          nl)      [ "$("$stubpath" -extract Label raw -o - "$plist.lnl"; printf x)" = "com.romp.manager${nl}${nl}x" ] ;;
          lacking) [ "$("$stubpath" -extract Label raw -o - "$plist.lnl"; printf x)" = "com.romp.manager${nl}x" ]
                   [ "$("$stubpath" -extract Label raw -o - "$plist.before"; printf x)" = "com.romp.manager${nl}x" ] ;;
          two)     [ "$("$stubpath" -extract Label raw -o - "$plist.before"; printf x)" = "com.romp.manager${nl}${nl}x" ] ;;
          strip)   [ "$("$stubpath" -extract Label raw -o - "$plist.lnl"; printf x)" = "com.romp.managerx" ] ;;
        esac
        for f in lnl vnl both exec; do
            cp "$plist.$f" "$plist"
            PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
            [ "$status" -eq 5 ]
            [[ "$output" != *"agree"* ]]
            [[ "$output" == *"nothing was rewritten"* ]]
            cmp -s "$plist" "$plist.$f"
            PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
            [ "$status" -eq 5 ]
            [[ "$output" == *"nothing was rewritten"* ]]
            cmp -s "$plist" "$plist.$f"
            case "$stub:$f" in
              nonl:lnl|nl:lnl|nonl:both|nl:both) [[ "$output" == *"is not romp's: plutil reads its Label as com.romp.manager\\n, not com.romp.manager"* ]] ;;
              nonl:vnl|nl:vnl)                   [[ "$output" == *"has a CLAUDE_CONFIG_DIR entry whose value ends in a newline"* ]] ;;
              nonl:exec|nl:exec)                 [[ "$output" == *"names a program whose path ends in a newline"* ]] ;;
              lacking:*|strip:*)
                  [[ "$output" == *"ends a raw extract one way for a value with no line end of its own and another way for a value that ends in one, so a value's own trailing line end cannot be told from the tool's"* ]]
                  [[ "$output" == *"its StandardOutPath (romp.calibrate\\n) back as romp.calibrate"* ]]
                  [[ "$output" == *"This refuses every plist read through this plutil, this one included, not this file alone"* ]]
                  [[ "$output" == *"Name another plutil in ROMP_PLUTIL, or write the plist afresh"* ]]
                  [[ "$output" != *"is not romp's"* ]] ;;
              two:*)                             [[ "$output" == *"(it read romp.calibrate\\n\\n; a line end is rendered as \\n)"* ]] ;;
            esac
        done
        case "$stub" in
          lacking) [[ "$output" == *"back as romp.calibrate\\n and its StandardOutPath (romp.calibrate\\n) back as romp.calibrate\\n, where romp.calibrate\\n\\n would say the tool's line end is one it always writes"* ]] ;;
          strip)   [[ "$output" == *"back as romp.calibrate and its StandardOutPath (romp.calibrate\\n) back as romp.calibrate, where romp.calibrate\\n would say the tool's line end is one it never writes"* ]] ;;
        esac
        # the clean plist: rewritten byte for byte under the two real behaviours, refused with the tool named under the other three (the
        # refusal is the tool's, not the file's: a total block, said in the text with the two ways out)
        cp "$plist.before" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        case "$stub" in
          nonl|nl) [ "$status" -eq 0 ]; [[ "$output" == *"agree"* ]] ;;
          *)       [ "$status" -eq 5 ]; [[ "$output" != *"agree"* ]]; [[ "$output" == *"plutil"* ]] ;;
        esac
        cmp -s "$plist" "$plist.before"
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        case "$stub" in
          nonl|nl) [ "$status" -eq 0 ] ;;
          *)       [ "$status" -eq 5 ]; [[ "$output" == *"nothing was rewritten"* ]] ;;
        esac
        cmp -s "$plist" "$plist.before"
    done
    # the other shapes the four probes span, each refused whole before any read of the file (the round-7 calibration lens ran them and
    # found them refused, with no case of their own): the value's own newline stripped and one written (the pair arm, as lacking), CR LF
    # after the value and CR LF throughout (the Label arm, the bytes named, the CR raw), and a line end that depends on the key shape
    # (none for a dotted path, for an array index, for a top-level key, for the Label alone: the pair arm, naming the probe that
    # disagreed). The last four are what pin the nested and array probes by execution (the mutation lens: with either probe gone the
    # calibration cases stayed green): with a probe gone its stand-in is still refused, later and on the file, under another text.
    for stub in strip_nl crlf crlf_all nested_nonl array_nonl top_nonl key_label_nonl; do
        _plutil_stub "$stub"
        for f in before lnl; do
            cp "$plist.$f" "$plist"
            for verb in "rewrite --check" rewrite; do
                PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
                [ "$status" -eq 5 ]
                [[ "$output" != *"agree"* ]]
                [[ "$output" != *"Rewrote"* ]]
                [[ "$output" != *"is not romp's"* ]]
                [[ "$output" == *"nothing was rewritten"* ]]
                case "$stub" in
                  strip_nl)       [[ "$output" == *"back as romp.calibrate\\n and its StandardOutPath (romp.calibrate\\n) back as romp.calibrate\\n, where romp.calibrate\\n\\n would say the tool's line end is one it always writes"* ]] ;;
                  crlf|crlf_all)  [[ "$output" == *"did not read this reader's scratch plist's Label (romp.calibrate) back as the value alone or as the value and one line end of its own (it read romp.calibrate"$'\r'"\\n; a line end is rendered as \\n)"* ]] ;;
                  nested_nonl)    [[ "$output" == *"back as romp.calibrate\\n and its EnvironmentVariables.PATH (romp.calibrate\\n) back as romp.calibrate\\n, where romp.calibrate\\n\\n would say the tool's line end is one it always writes"* ]] ;;
                  array_nonl)     [[ "$output" == *"back as romp.calibrate\\n and its ProgramArguments.0 (romp.calibrate\\n) back as romp.calibrate\\n, where romp.calibrate\\n\\n would say the tool's line end is one it always writes"* ]] ;;
                  top_nonl)       [[ "$output" == *"back as romp.calibrate and its EnvironmentVariables.PATH (romp.calibrate\\n) back as romp.calibrate\\n\\n, where romp.calibrate\\n would say the tool's line end is one it never writes"* ]] ;;
                  key_label_nonl) [[ "$output" == *"back as romp.calibrate and its StandardOutPath (romp.calibrate\\n) back as romp.calibrate\\n\\n, where romp.calibrate\\n would say the tool's line end is one it never writes"* ]] ;;
                esac
                # every arm of the calibration says the refusal is the tool's and names the two ways out (round 8, correctness-3: the crlf
                # stubs, the Label arm, were exempted here because that arm said neither; red before on them)
                [[ "$output" == *"This refuses every plist read through this plutil, this one included, not this file alone"* ]]
                [[ "$output" == *"Name another plutil in ROMP_PLUTIL, or write the plist afresh"* ]]
                cmp -s "$plist" "$plist.$f"
            done
        done
    done
}

@test "rewrite (macOS): the plutil line-end calibration's transfer from the scratch to the file is checked on the file: under a plutil that writes a line end on the scratch and none on the file, or one only when the file's value lacks one, the clean plist or a Label, a CLAUDE_CONFIG_DIR or a manager path ending in a newline is refused at exit 5 with the plist byte for byte on rewrite and rewrite --check, the key and the bytes named, where round 7 wrote the value a newline short at exit 0; a plutil that honours -n for one probe and not another is refused whole; a plutil that ignores or rejects -n is read one way and refuses nothing over the switch; and the scratch is removed on every road out" {
    # the round-7 addendum of fork PR #778, after the calibration lens: the four probes span the value's own line end and the key shape and
    # by construction nothing else (a scratch is not the file), and fourteen stand-ins keyed on what they do not span (the file's place or
    # size, the key's name, an array index above 0, the value's bytes, the input format) each read a Label, a CLAUDE_CONFIG_DIR or a
    # manager path ending in a newline a newline short at exit 0 with the success line. The file-side checks in _plutil_raw: a tool writing
    # no line end on the file shows on a value without one of its own, the Label or the launcher's path here, and is refused there (a
    # withholding class confined to values that end in a line end does not show there); a tool writing one only when the file's value lacks
    # one is told on the file itself where the tool honours -n, since the extract with and without the switch then differ by nothing where
    # they should differ by the tool's line end; and every value read is echoed through the scratch (round 8), so a line end keyed on the
    # value's bytes, the key's name or the array index is told on the file's own values (the round-8 case below). The RULE, not a list of
    # the classes closed (round 8 of fork PR #778, correctness-2, after two file-keyed stand-ins outside the list written short at exit 0):
    # these reads tell the tool's line end from the value's own only for a tool that REPORTS the value's bytes and treats the scratch as it
    # treats the file. The residual, said and not pinned (a pin here would assert a silent value change), at its width: a tool that ALTERS
    # the value's bytes on the file (strips its own newline, then writes one or none) reads identically on both roads and cannot be told
    # through itself, -n honoured or not; and a tool keyed on what no scratch shares with the file (its place, size, name or format) that
    # also ignores or lacks -n (file_lacking ignore) reads a value ending in a newline a newline short and rewrites at exit 0. Both are
    # untested by construction, not tested and absent. The evidence that no plutil does either, as read: plutil(1) documents -n and says
    # nothing else of the terminator; the open-source implementation writes it on the flag and format alone (PLUContext.swift line 1035);
    # Apple's plutil is closed source and no plutil binary ran here.
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" stubpath="$TEST_DIR/plutil-bin/plutil" stub f verb nmode nl=$'\n' mgr="$ROMP_MANAGER_BIN" left
    _plutil_stub
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    cp "$plist" "$plist.before"
    grep -qF "<string>$mgr</string>" "$plist.before"
    sed 's|<string>com.romp.manager</string>|<string>com.romp.manager\&#10;</string>|' "$plist.before" > "$plist.lnl"     # the Label ends in a newline
    sed 's|<string>/x/cc</string>|<string>/x/cc\&#10;</string>|' "$plist.before" > "$plist.vnl"                            # CLAUDE_CONFIG_DIR does
    sed "s|<string>$mgr</string>|<string>$mgr\&#10;</string>|" "$plist.before" > "$plist.exec"                              # the manager's path does
    for f in lnl vnl exec; do run cmp -s "$plist.$f" "$plist.before"; [ "$status" -ne 0 ]; done
    # 1. a line end only when the FILE's value lacks one (the scratch read as always): the clean plist through, each newline fixture refused
    #    on the file at the key that carries it, the two read-backs named and equal where they should differ by one line end
    _plutil_stub file_lacking
    [ "$("$stubpath" -extract Label raw -o - "$plist.lnl"; printf x)" = "com.romp.manager${nl}x" ]          # on the file: the value's own newline, none written
    [ "$("$stubpath" -extract Label raw -n -o - "$plist.lnl"; printf x)" = "com.romp.manager${nl}x" ]       # and the same under -n
    [ "$("$stubpath" -extract Label raw -o - "$plist.before"; printf x)" = "com.romp.manager${nl}x" ]       # a value without one: the tool's line end written
    [ "$("$stubpath" -extract Label raw -n -o - "$plist.before"; printf x)" = "com.romp.managerx" ]         # and withheld under -n
    for f in lnl vnl exec; do
        cp "$plist.$f" "$plist"
        for verb in "rewrite --check" rewrite; do
            PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
            [ "$status" -eq 5 ]
            [[ "$output" != *"agree"* ]]
            [[ "$output" != *"Rewrote"* ]]
            [[ "$output" != *"is not romp's"* ]]
            [[ "$output" == *"nothing was rewritten"* ]]
            [[ "$output" == *"Name another plutil in ROMP_PLUTIL, or write the plist afresh"* ]]
            case "$f" in
              lnl)  [[ "$output" == *"plutil reads this plist's Label as com.romp.manager\\n and, asked for no line end of its own (-n), as com.romp.manager\\n, where the two would differ by exactly one line end"* ]] ;;
              vnl)  [[ "$output" == *"plutil reads this plist's EnvironmentVariables.CLAUDE_CONFIG_DIR as /x/cc\\n and, asked for no line end of its own (-n), as /x/cc\\n, where the two would differ by exactly one line end"* ]] ;;
              exec) [[ "$output" == *"plutil reads this plist's ProgramArguments.1 as $mgr\\n and, asked for no line end of its own (-n), as $mgr\\n, where the two would differ by exactly one line end"* ]] ;;
            esac
            cmp -s "$plist" "$plist.$f"
        done
    done
    cp "$plist.before" "$plist"
    PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"agree"* ]]
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.before"
    # 2. no line end on the FILE (the scratch read as always), -n honoured and ignored: every plist refused, the clean one and the two whose
    #    Label has no newline of its own on the Label (read back without the line end the scratch showed), the Label ending in a newline on
    #    the two-way read where -n is honoured and on the launcher's path where it is not (the strict arm alone, nothing armed)
    for nmode in honour ignore; do
        _plutil_stub file_nonl "$nmode"
        for f in before lnl vnl exec; do
            cp "$plist.$f" "$plist"
            for verb in "rewrite --check" rewrite; do
                PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
                [ "$status" -eq 5 ]
                [[ "$output" != *"agree"* ]]
                [[ "$output" != *"Rewrote"* ]]
                [[ "$output" != *"is not romp's"* ]]
                [[ "$output" == *"nothing was rewritten"* ]]
                [[ "$output" == *"Name another plutil in ROMP_PLUTIL, or write the plist afresh"* ]]
                case "$nmode:$f" in
                  *:before|*:vnl|*:exec) [[ "$output" == *"plutil ended every raw extract of this reader's scratch plist with a line end of its own and ended its extract of this plist's Label (com.romp.manager) with none, so the line end it writes depends on the file or on the value"* ]] ;;
                  honour:lnl)            [[ "$output" == *"plutil reads this plist's Label as com.romp.manager\\n and, asked for no line end of its own (-n), as com.romp.manager\\n, where the two would differ by exactly one line end"* ]] ;;
                  ignore:lnl)            [[ "$output" == *"ended its extract of this plist's ProgramArguments.0 ($(_plist_get "$plist.before" ProgramArguments.0)) with none"* ]] ;;
                esac
                cmp -s "$plist" "$plist.$f"
            done
        done
    done
    # 3. a plutil that writes a line end and ignores -n, or rejects it: nothing armed and nothing refused over the switch; round 7's reader,
    #    the clean plist byte for byte and the Label ending in a newline not romp's
    for nmode in ignore reject; do
        _plutil_stub nl "$nmode"
        cp "$plist.before" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        [[ "$output" == *"agree"* ]]
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 0 ]
        cmp -s "$plist" "$plist.before"
        cp "$plist.lnl" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        [[ "$output" == *"is not romp's: plutil reads its Label as com.romp.manager\\n, not com.romp.manager"* ]]
        cmp -s "$plist" "$plist.lnl"
    done
    # 4. -n honoured for a top-level key and ignored for a dotted one: refused whole, the probe and the bytes named
    _plutil_stub nl half
    for f in before lnl; do
        cp "$plist.$f" "$plist"
        for verb in "rewrite --check" rewrite; do
            PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
            [ "$status" -eq 5 ]
            [[ "$output" != *"agree"* ]]
            [[ "$output" != *"Rewrote"* ]]
            [[ "$output" != *"is not romp's"* ]]
            [[ "$output" == *"asked for no line end of its own (-n), plutil read this reader's scratch plist's Label (romp.calibrate) back as romp.calibrate and its EnvironmentVariables.PATH (romp.calibrate\\n) back as romp.calibrate\\n\\n, where romp.calibrate\\n would say the switch holds for every value"* ]]
            [[ "$output" == *"This refuses every plist read through this plutil, this one included, not this file alone"* ]]
            [[ "$output" == *"Name another plutil in ROMP_PLUTIL, or write the plist afresh"* ]]
            cmp -s "$plist" "$plist.$f"
        done
    done
    # 5. the scratch is removed on every road out (the mutation lens: with both rm -rf gone one romp-service-plutil.* directory was left per
    #    read and no case noticed): a fresh TMPDIR holds none after a rewrite through the default stand-in, after a refusal on the pair arm
    #    (lacking), on the Label arm (two), on the -n arm (half) and on the file-side arms (file_lacking on the Label fixture)
    mkdir -p "$TEST_DIR/scratch-tmp"
    for stub in nl lacking two "nl half" file_lacking; do
        _plutil_stub $stub
        case "$stub" in file_lacking) cp "$plist.lnl" "$plist" ;; *) cp "$plist.before" "$plist" ;; esac
        TMPDIR="$TEST_DIR/scratch-tmp" PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        case "$stub" in nl) [ "$status" -eq 0 ] ;; *) [ "$status" -eq 5 ] ;; esac
        left=("$TEST_DIR/scratch-tmp"/romp-service-plutil.*)
        [ ! -e "${left[0]}" ]
    done
}

@test "rewrite (macOS): through plutil an entry of another type than string (an array, a dictionary, an integer, a boolean, a date) at the Label, at CLAUDE_CONFIG_DIR or at PATH is refused at exit 5 with the plist byte for byte on rewrite and rewrite --check, the key and the type named, under a plutil that writes a line end and one that does not; a plutil that renders no container raw is refused the same way and never read as an absent entry; the one-line fallback refuses the same plists" {
    # round 8 of fork PR #778 (extra4-2): the plutil road asserted no value TYPE where the one-line fallback does, so an entry of another
    # type was read as plutil's raw rendering (an array as its element count, a dictionary as its keys, an integer as its digits, a
    # boolean as true or false, a date as its RFC 3339 text) and the rewrite wrote it back as a <string> at exit 0 with the success line
    # on every key it keeps without a compare (PATH, the log paths, ROMP_STATE_DIR, an instance variable the shell does not set), rewrite
    # --check blessing the file first. The reader now reads each entry twice, as an xml1 plist whose root element names the type and raw,
    # and refuses a root that is not <string>; an entry that extracts one way and not the other (a plutil refusing to render a container
    # raw, the refuter's stand-in) is refused too, where the one read's failure had read as no such key and the entry was dropped.
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" stub k t verb kp
    _plutil_stub
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    cp "$plist" "$plist.before"
    grep -qF '<key>CLAUDE_CONFIG_DIR</key><string>/x/cc</string>' "$plist.before"
    declare -A REP=([array]='<array><string>a</string><string>b</string></array>' [dict]='<dict><key>k</key><string>v</string></dict>'
                    [integer]='<integer>5</integer>' [true]='<true/>' [date]='<date>2026-01-01T00:00:00Z</date>')
    for k in Label CLAUDE_CONFIG_DIR PATH; do
        for t in array dict integer true date; do
            sed -E "s|<key>$k</key><string>[^<]*</string>|<key>$k</key>${REP[$t]}|" "$plist.before" > "$plist.$k.$t"
            run cmp -s "$plist.$k.$t" "$plist.before"; [ "$status" -ne 0 ]
            grep -qF "<key>$k</key>${REP[$t]}" "$plist.$k.$t"
        done
    done
    # what the stand-in hands the reader for a container extracted raw, as plutil(1) says: the count, the keys
    [ "$("$TEST_DIR/plutil-bin/plutil" -extract EnvironmentVariables.PATH raw -o - "$plist.PATH.array"; printf x)" = $'2\nx' ]
    [ "$("$TEST_DIR/plutil-bin/plutil" -extract Label raw -o - "$plist.Label.dict"; printf x)" = $'k\nx' ]
    [[ "$("$TEST_DIR/plutil-bin/plutil" -extract Label xml1 -o - "$plist.Label.array")" == *"<plist version=\"1.0\">"*"<array>"* ]]
    for stub in nl nonl; do
        _plutil_stub "$stub"
        for k in Label CLAUDE_CONFIG_DIR PATH; do
            case "$k" in Label) kp=Label ;; *) kp="EnvironmentVariables.$k" ;; esac
            for t in array dict integer true date; do
                cp "$plist.$k.$t" "$plist"
                for verb in "rewrite --check" rewrite; do
                    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
                    [ "$status" -eq 5 ]
                    [[ "$output" != *"agree"* ]]
                    [[ "$output" != *"Rewrote"* ]]
                    [[ "$output" == *"nothing was rewritten"* ]]
                    [[ "$output" == *"plutil reads its $kp entry as <$t>, not as a <string>, and this reader reads string values alone"* ]]
                    [[ "$output" == *"To write it afresh in romp's form, run romp-service install"* ]]
                    cmp -s "$plist" "$plist.$k.$t"
                done
            done
        done
        # the clean plist still rewrites byte for byte: the type read refuses nothing on a plist of strings
        cp "$plist.before" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        [[ "$output" == *"agree"* ]]
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 0 ]
        cmp -s "$plist" "$plist.before"
    done
    # a plutil that refuses to render a container raw: the entry extracts as a plist and not raw, refused as read one way only, never as
    # absent (at the round-7 head the PATH entry was dropped at exit 0 with the success line under such a tool, round 3's defect in reverse)
    _plutil_stub nl honour refuse
    run "$TEST_DIR/plutil-bin/plutil" -extract EnvironmentVariables.PATH raw -o - "$plist.PATH.array"
    [ "$status" -eq 1 ]
    [[ "$output" == *"is a array type and cannot be extracted in raw format"* ]]
    for k in Label CLAUDE_CONFIG_DIR PATH; do
        case "$k" in Label) kp=Label ;; *) kp="EnvironmentVariables.$k" ;; esac
        for t in array dict; do
            cp "$plist.$k.$t" "$plist"
            for verb in "rewrite --check" rewrite; do
                PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
                [ "$status" -eq 5 ]
                [[ "$output" != *"agree"* ]]
                [[ "$output" != *"Rewrote"* ]]
                [[ "$output" == *"plutil extracts its $kp entry as a plist (xml1) and not as a raw value, so what the entry holds cannot be told"* ]]
                [[ "$output" == *"never as absent; nothing was rewritten"* ]]
                cmp -s "$plist" "$plist.$k.$t"
            done
        done
    done
    # the one-line fallback (ROMP_PLUTIL at a path that does not exist) refuses every one of the fifteen as a form it does not read whole
    for k in Label CLAUDE_CONFIG_DIR PATH; do
        for t in array dict integer true date; do
            cp "$plist.$k.$t" "$plist"
            ROMP_PLUTIL="$TEST_DIR/no-such-plutil" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
            [ "$status" -eq 5 ]
            [[ "$output" == *"is not in the one-line form romp writes"* ]]
            cmp -s "$plist" "$plist.$k.$t"
        done
    done
}

@test "rewrite (macOS): every value read through plutil is echoed through the reader's scratch plist under its own key: a plutil whose line end depends on the value's bytes (a newline inside it, a non-ASCII character), on the key's name (CLAUDE_CONFIG_DIR) or on the array index (the manager's path at 1), the classes the four probes do not carry, is refused at exit 5 with the plist byte for byte on rewrite and rewrite --check, the key and both read-backs named, where -n is ignored or rejected, and by the two-way read where it is honoured; the honest plutil rewrites the clean plist byte for byte and refuses the same values as ending in a newline" {
    # round 8 of fork PR #778 (extra4-1, with correctness-2): the file-side check could tell the tool's line end from the value's own only
    # for a value that does not already end in one, so a plutil withholding its line end for a class confined to newline-ending values
    # (a newline inside the value, a non-ASCII character: the refuters' stand-ins) read such a value a newline short and rewrote it at
    # exit 0 wherever -n was not honoured, while the reader's comment said such a class showed on the file's constants. Every value read
    # is now written into the scratch at the same key path shape, key name and array index and read back, which must give the file's raw
    # read again; the value's own bytes and the key are then the file's, and the scratch differs from the file only in its place, size,
    # name and format, which is the residual the reader states. At the round-7 head: interior_nonl reject on the PATH fixture, exit 0,
    # 'Rewrote the login agent', PATH /a\nb\n written back as /a\nb (the drive in the PR body).
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" stubpath="$TEST_DIR/plutil-bin/plutil" pair mode f nmode verb nl=$'\n' mgr="$ROMP_MANAGER_BIN"
    _plutil_stub
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    cp "$plist" "$plist.before"
    grep -qF "<string>$mgr</string>" "$plist.before"
    sed -E 's|<key>PATH</key><string>[^<]*</string>|<key>PATH</key><string>/a\&#10;b\&#10;</string>|' "$plist.before" > "$plist.interior"   # PATH: a newline inside, one at the end
    sed 's|<string>/x/cc</string>|<string>/caf\&#233;\&#10;</string>|' "$plist.before" > "$plist.nonascii"                             # CLAUDE_CONFIG_DIR: non-ASCII, ends in a newline
    sed 's|<string>/x/cc</string>|<string>/x/cc\&#10;</string>|' "$plist.before" > "$plist.key"                                          # CLAUDE_CONFIG_DIR ends in a newline
    sed "s|<string>$mgr</string>|<string>$mgr\&#10;</string>|" "$plist.before" > "$plist.index"                                            # the manager's path, ProgramArguments.1, does
    for f in interior nonascii key index; do run cmp -s "$plist.$f" "$plist.before"; [ "$status" -ne 0 ]; done
    [ "$(_plist_get "$plist.nonascii" EnvironmentVariables.CLAUDE_CONFIG_DIR; printf x)" = "/café${nl}${nl}x" ]   # python's print adds one
    for pair in interior_nonl:interior:EnvironmentVariables.PATH nonascii_nonl:nonascii:EnvironmentVariables.CLAUDE_CONFIG_DIR key_ccd_nonl:key:EnvironmentVariables.CLAUDE_CONFIG_DIR index_nonl:index:ProgramArguments.1; do
        mode="${pair%%:*}"; f="${pair#*:}"; f="${f%%:*}"; kp="${pair##*:}"
        for nmode in ignore reject honour; do
            _plutil_stub "$mode" "$nmode"
            # the stand-in on the fixture's value: the value's own newline, none of the tool's (the class withholds), and the same under -n
            [[ "$("$stubpath" -extract "$kp" raw -o - "$plist.$f"; printf x)" == *"${nl}x" ]]
            [[ "$("$stubpath" -extract "$kp" raw -o - "$plist.$f"; printf x)" != *"${nl}${nl}x" ]]
            [ "$("$stubpath" -extract Label raw -o - "$plist.$f"; printf x)" = "com.romp.manager${nl}x" ]   # outside the class: the tool's line end
            cp "$plist.$f" "$plist"
            for verb in "rewrite --check" rewrite; do
                PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" $verb
                [ "$status" -eq 5 ]
                [[ "$output" != *"agree"* ]]
                [[ "$output" != *"Rewrote"* ]]
                [[ "$output" != *"is not romp's"* ]]
                [[ "$output" == *"nothing was rewritten"* ]]
                [[ "$output" == *"Name another plutil in ROMP_PLUTIL, or write the plist afresh"* ]]
                case "$nmode" in
                  honour) [[ "$output" == *"plutil reads this plist's $kp as "*" and, asked for no line end of its own (-n), as "*", where the two would differ by exactly one line end"* ]] ;;
                  *)      [[ "$output" == *"plutil reads this plist's $kp as "*" and, given that value written into this reader's scratch plist under the same key, reads it back as "*", where the two would be the same bytes"* ]]
                          [[ "$output" == *"the value's own bytes, the key's name, its place in the array"* ]] ;;
                esac
                cmp -s "$plist" "$plist.$f"
            done
        done
        # the clean plist under the same class, -n rejected: through byte for byte where the class has no member in it (a newline inside,
        # non-ASCII), refused on the file's own constant where it has one (CLAUDE_CONFIG_DIR /x/cc, the manager's path: read back with no
        # line end where the scratch showed one, the round-7 check)
        _plutil_stub "$mode" reject
        cp "$plist.before" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite --check
        case "$mode" in
          interior_nonl|nonascii_nonl) [ "$status" -eq 0 ]; [[ "$output" == *"agree"* ]] ;;
          key_ccd_nonl)  [ "$status" -eq 5 ]; [[ "$output" == *"ended its extract of this plist's EnvironmentVariables.CLAUDE_CONFIG_DIR (/x/cc) with none"* ]] ;;
          index_nonl)    [ "$status" -eq 5 ]; [[ "$output" == *"ended its extract of this plist's ProgramArguments.1 ($mgr) with none"* ]] ;;
        esac
        cmp -s "$plist" "$plist.before"
    done
    # the honest stand-in on the four fixtures: the echo agrees and the value is refused as ending in a newline, byte for byte; the clean
    # plist rewrites byte for byte (the echo of every value refuses nothing on a plist the tool reports faithfully)
    _plutil_stub
    for f in interior nonascii key index; do
        cp "$plist.$f" "$plist"
        PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
        [ "$status" -eq 5 ]
        case "$f" in
          interior)     [[ "$output" == *"has a PATH entry whose value ends in a newline"* ]] ;;
          nonascii|key) [[ "$output" == *"has a CLAUDE_CONFIG_DIR entry whose value ends in a newline"* ]] ;;
          index)        [[ "$output" == *"names a program whose path ends in a newline"* ]] ;;
        esac
        cmp -s "$plist" "$plist.$f"
    done
    cp "$plist.before" "$plist"
    PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    cmp -s "$plist" "$plist.before"
    # and no scratch is left behind by the echoes (the round-7 addendum's removal check, on the road that now keeps the scratch through
    # the read)
    mkdir -p "$TEST_DIR/scratch-tmp2"
    TMPDIR="$TEST_DIR/scratch-tmp2" PATH="$TEST_DIR/plutil-bin:$PATH" ROMP_OS_OVERRIDE=Darwin run "$SVC" rewrite
    [ "$status" -eq 0 ]
    local left=("$TEST_DIR/scratch-tmp2"/romp-service-plutil.*)
    [ ! -e "${left[0]}" ]
}

@test "install (Linux and macOS): a PATH, a service.env path or a manager path ending in a newline is refused before anything is written, the value named, no audit row; the same values without it install, and a PATH with a newline inside is written escaped and read back whole" {
    # the mutation pass (2026-09-19): the instance-variable leg had its case and the three fixed values none, so each of those legs
    # could go and the suite stayed green; on Linux a manager path with a newline is a control character systemd refuses in an
    # executable name and that refusal fires first, so the leg's own text is the mac's to show
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist" nl=$'\n'
    run env PATH="$PATH:/x$nl" ROMP_OS_OVERRIDE=Linux "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"PATH in this environment ends in a newline"* ]]
    [[ "$output" == *"nothing was written"* ]]
    [ ! -e "$unit" ]
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/svc.env$nl" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"the service.env path in this environment ends in a newline"* ]]
    [ ! -e "$unit" ]
    ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN$nl" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"the manager's path"* ]]
    [[ "$output" == *"nothing was written"* ]]
    [ ! -e "$unit" ]
    ROMP_MANAGER_BIN="$ROMP_MANAGER_BIN$nl" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"the manager's path (ROMP_MANAGER_BIN) in this environment ends in a newline"* ]]
    [ ! -e "$plist" ]
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/svc.env$nl" ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 5 ]
    [[ "$output" == *"the service.env path in this environment ends in a newline"* ]]
    [ ! -e "$plist" ]
    [ ! -e "$XDG_STATE_HOME/romp/restart-audit.jsonl" ]                                   # a refused install journals nothing
    ROMP_SERVICE_ENV_FILE="$TEST_DIR/svc.env" ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    grep -qxF "EnvironmentFile=-$TEST_DIR/svc.env" "$unit"
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    [ -f "$plist" ]
    rm -f "$unit"
    run env PATH="/usr/bin$nl:$PATH" ROMP_OS_OVERRIDE=Linux "$SVC" install                # a newline inside: the writer's escape, systemd's decode
    [ "$status" -eq 0 ]
    grep -qF 'Environment="PATH=/usr/bin\n:' "$unit"
    [ "$(_sd_read "$unit" env PATH | head -c 10 | od -c | head -1 | tr -s ' ')" = "0000000 / u s r / b i n \n :" ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
}

@test "rewrite (Linux): the oracle refuses to guess and drops what systemd drops: a specifier from systemd's table it does not model (%t) raises rather than expanding, while %h expands, %% is a percent and a letter outside the table drops the item; an assignment whose name systemd refuses (A-B, 1A, A.B) is no assignment to the oracle or to the reader, so a kept variable beside it is not beside another assignment, while a valid name (_A) beside it is" {
    # the mutation pass (2026-09-19): no case fed the oracle a specifier from the table or an invalid name, so it could expand the one
    # to a placeholder and accept the other and every case stayed green; a case leaning on the oracle where it is not modelled must
    # fail loudly, and the reader's name rule needs its accept case (the invalid word is dropped, not counted) beside its refuse case
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" n
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=%t/romp'
    run _sd_read "$unit" env CLAUDE_CONFIG_DIR
    [ "$status" -ne 0 ]
    [[ "$output" == *"NotImplementedError"* && "$output" == *"the specifier %t is not modelled"* ]]
    _three_roads_refuse "$unit" "the specifier %t in CLAUDE_CONFIG_DIR"
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=%h/.cc'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$HOME/.cc" ]
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/100%%'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/100%" ]
    CLAUDE_CONFIG_DIR=/x/100% ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment="CLAUDE_CONFIG_DIR=/x/100%%"' "$unit"
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "/x/100%" ]
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=%z/cc'
    [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]                                  # a letter outside the table: the item fails to resolve and is dropped
    _three_roads_refuse "$unit" "the specifier %z in CLAUDE_CONFIG_DIR"
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=A-B=/x/bad 1A=1 A.B=2 CLAUDE_CONFIG_DIR=/x/cc'
    for n in A-B 1A A.B; do [ "$(_sd_read "$unit" has "$n")" = no ]; done
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
    CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    _marked_install_ok
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=A-B=/x/bad 1A=1 A.B=2 CLAUDE_CONFIG_DIR=/x/cc'
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'Environment=CLAUDE_CONFIG_DIR=/x/cc' "$unit"
    run grep -F 'A-B' "$unit"
    [ "$status" -ne 0 ]                                                                  # dropped, as every hand word is
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=_A=1 CLAUDE_CONFIG_DIR=/x/cc'
    [ "$(_sd_read "$unit" has _A)" = yes ]
    _three_roads_refuse "$unit" "CLAUDE_CONFIG_DIR is assigned beside another assignment on one line"
}

@test "rewrite (Linux): the fold of the oracle lens, the reader's classes, each with its accepted neighbour: a % before a non-alphanumerical character is a % to systemd and reads as one in a kept value, in ExecStart and in EnvironmentFile (A), where a letter or a digit after it is still the refused specifier; a \\u noncharacter, a \\U surrogate or noncharacter and a raw noncharacter are refused as systemd drops or refuses them (C, D), where U+FDF0 and U+1FFFD read whole; a continuation backslash on the file's last line is read as systemd parses it and goes back without it (E), where one before another line is still the refused continuation" {
    # the fold (2026-09-19) after round 4's oracle lens: 125 disagreements between the oracle and systemd 255.4 in 11 classes; these four
    # were the READER's as well (classified by running bin/romp-service on each class beside systemd-analyze --user verify). A: the
    # specifier pass refused a%/b, which systemd keeps as written (specifier_printf resolves letters and digits alone), so a working unit
    # was refused. C, D: a \uFFFE was carried and written back raw, a line systemd loads NOTHING from (String is not UTF-8 clean), where
    # systemd drops the escaped assignment alone; a \U0000FFFE was carried where cunescape_one refuses it (Invalid syntax, the item and
    # the rest of the line dropped); a \U0000D800 was refused with the \u form's explanation. E: the last line's backslash was refused as a
    # join to a next line that does not exist, where config_parse parses the pending continuation at the end of the file.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" form v raw
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    # A, a kept value: accepted, written in the writer's form (%% doubled), and read back as the same value by the oracle. The last form
    # has a non-ASCII letter after the % (systemd's POSSIBLE_SPECIFIERS is ASCII, so it copies both characters), and the reader runs under
    # a UTF-8 locale, where a test asking the locale's alphabet instead of the listed one takes the letter for a specifier (the fold's
    # addendum: the reader's [[:alnum:]] and the oracle's isalnum both would, and no case had a letter outside ASCII). The leg needs that
    # locale installed and usable: under the C locale bash's [[:alnum:]] never matches the letter's bytes, so the [[:alnum:]] mutation
    # stays green and the leg proves nothing, and a name that is not installed is the C locale by another name (a fresh bash falls back
    # to it). So no UTF-8 locale, or one bash cannot use, FAILS here with the remedy; the leg never passes vacuously and never skips (the
    # round-5 preface of fork PR #778; the fallback to C.UTF-8 by name, which stood here, was that vacuous pass on a runner without one)
    local utf8loc; utf8loc="$(locale -a 2>/dev/null | grep -iE '^(C|en_US)\.utf-?8$' | head -1)"
    if [[ -z "$utf8loc" ]]; then
        echo "romp-service.bats: no UTF-8 locale is installed (locale -a lists neither C.UTF-8 nor en_US.UTF-8), and the non-ASCII leg of class A needs one to prove anything. Remedy: install one (Debian and Ubuntu: apt-get install locales, then locale-gen en_US.UTF-8, or dpkg-reconfigure locales; C.UTF-8 comes with libc-bin on Ubuntu) or select an installed UTF-8 locale by name in this case, then run the case again." >&2
        false
    fi
    if ! LC_ALL="$utf8loc" bash -c '[[ "$1" == [[:alnum:]] ]]' _ $'\xc3\xa9'; then
        echo "romp-service.bats: the UTF-8 locale $utf8loc is listed by locale -a, but a fresh bash under LC_ALL=$utf8loc does not match a non-ASCII letter with [[:alnum:]] (it fell back to the C locale), so the non-ASCII leg of class A would prove nothing. Remedy: generate the locale (Debian and Ubuntu: locale-gen $utf8loc, or dpkg-reconfigure locales) or select another installed UTF-8 locale by name in this case, then run the case again." >&2
        false
    fi
    for form in '/x/a%/b' '/x/a%-b' '/x/a%.b' '/x/a%~b' '/x/a%:b' '/x/a%'$'\xc3\xa9''b'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=$form"
        [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$form" ]                     # systemd keeps % and the character
        LC_ALL="$utf8loc" CLAUDE_CONFIG_DIR="$form" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        CLAUDE_CONFIG_DIR="$form" _marked_install_ok
        LC_ALL="$utf8loc" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        grep -qxF "Environment=\"CLAUDE_CONFIG_DIR=${form//%/%%}\"" "$unit"
        [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$form" ]
    done
    # A, the neighbour: a letter or a digit after the % is a specifier systemd resolves or fails, refused as before
    for form in '/x/a%1b' '/x/a%zb'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=$form"
        [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]                          # Invalid slot: the item is dropped
        _three_roads_refuse "$unit" "the specifier %${form:5:1} in CLAUDE_CONFIG_DIR"
    done
    # A, ExecStart's path and EnvironmentFile's path
    ROMP_MANAGER_BIN="$TEST_DIR/pct%-dir/romp-manager" ROMP_OS_OVERRIDE=Linux ROMP_SERVICE_NO_LOAD=1 "$SVC" install >/dev/null
    grep -qxF "ExecStart=\"$TEST_DIR/pct%%-dir/romp-manager\" up" "$unit"            # the writer doubles it
    grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; _svc_line "$unit" "ExecStart=$TEST_DIR/pct%-dir/romp-manager up"
    [ "$(_sd_read "$unit" exec0)" = "$TEST_DIR/pct%-dir/romp-manager" ]
    ROMP_MANAGER_BIN="$TEST_DIR/pct%-dir/romp-manager" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    cp "$unit.clean" "$unit"; grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; _svc_line "$unit" 'EnvironmentFile=-/nx/%-/env'
    [ "$(_sd_read "$unit" envfile)" = '/nx/%-/env' ]
    ROMP_SERVICE_ENV_FILE='/nx/%-/env' ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    ROMP_SERVICE_ENV_FILE='/nx/%-/env' ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
    [ "$status" -eq 0 ]
    grep -qxF 'EnvironmentFile=-/nx/%%-/env' "$unit"
    [ "$(_sd_read "$unit" envfile)" = '/nx/%-/env' ]
    # C: a \u noncharacter, which systemd decodes and then drops the assignment for (the item alone: a later item stands)
    for form in '\uFFFE' '\uFFFF' '\uFDD0' '\uFDEF'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/$form ADMIN_KNOB=1"
        [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
        [ "$(_sd_read "$unit" env ADMIN_KNOB)" = 1 ]                                    # the rest of the line stands
        _three_roads_refuse "$unit" "the escape $form, a noncharacter, which systemd decodes into bytes that are not UTF-8 by its rule" "systemd does not decode" \
            "drops the item and the rest of the line" "Write the character itself"
        [[ "$output" == *"this reader does not model that reading"* ]]
        # the kind's remedy (the fold's addendum): the escape goes, since the character written raw is the whole-file refusal below
        [[ "$output" == *"Remove the escape from the value (written as the character itself, the line is not UTF-8 to systemd, which then loads nothing from the file)"* ]]
    done
    # D: a \U surrogate or noncharacter, which cunescape_one refuses: the item and the rest of the line are dropped as invalid syntax
    for form in '\U0000D800|a surrogate' '\U0000DFFF|a surrogate' '\U0000FFFE|a noncharacter' '\U0000FDD0|a noncharacter' '\U0001FFFE|a noncharacter' '\U0010FFFE|a noncharacter'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/${form%%|*} ADMIN_KNOB=1"
        [ "$(_sd_read "$unit" has CLAUDE_CONFIG_DIR)" = no ]
        [ "$(_sd_read "$unit" has ADMIN_KNOB)" = no ]                                    # the rest of the line is dropped too
        _three_roads_refuse "$unit" "the escape ${form%%|*}, ${form#*|}, which systemd refuses in the \\U form" "does not model that reading"
        [[ "$output" == *"drops the item and the rest of the line as invalid syntax (the items before it on the line stand)"* ]]
    done
    # D in ExecStart's path: the relaxed retry keeps the backslash and string_is_safe refuses the executable name; the unit never starts
    cp "$unit.clean" "$unit"; grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
    _svc_line "$unit" "ExecStart=$TEST_DIR/a\\U0000FFFEb/romp-manager up"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Executable name contains special characters: "* ]]
    ROMP_MANAGER_BIN="$TEST_DIR/a"$'\xef\xbf\xbe'"b/romp-manager" _three_roads_refuse "$unit" "ExecStart's command has the escape \\U0000FFFE, a noncharacter, which systemd refuses in the \\U form"
    # C raw: a noncharacter written as its bytes is a line systemd refuses the whole file on, where iconv and python pass it: U+FFFE, U+FDD0,
    # U+1FFFE, and beyond plane 1 U+BFFFF and U+10FFFE (the last two code points of every plane; the fold's addendum, where the check
    # narrowed to plane 1 passed)
    for raw in $'\xef\xbf\xbe' $'\xef\xb7\x90' $'\xf0\x9f\xbf\xbe' $'\xf2\xaf\xbf\xbf' $'\xf4\x8f\xbf\xbe'; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/$raw"
        [[ "$(_sd_read "$unit" exec0)" == "ERROR: String is not UTF-8 clean"* ]]
        CLAUDE_CONFIG_DIR="/x/$raw" _three_roads_refuse "$unit" "it is not valid UTF-8, on which systemd refuses the whole file"
    done
    # C and D, the neighbours: the code points beside the refused ranges, on both sides (U+FDCF and U+FDF0 around the noncharacter block,
    # U+D7FF and U+E000 around the surrogates, U+1FFFD below plane 1's last two), read whole, agree with the shell and round-trip
    for form in '\uFDF0|'$'\xef\xb7\xb0' '\uFDCF|'$'\xef\xb7\x8f' '\U0001FFFD|'$'\xf0\x9f\xbf\xbd' '\uE000|'$'\xee\x80\x80' '\uD7FF|'$'\xed\x9f\xbf'; do
        v="/x/${form#*|}"
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/${form%%|*}"
        [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$v" ]
        CLAUDE_CONFIG_DIR="$v" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = "$v" ]
        CLAUDE_CONFIG_DIR="$v" _marked_install_ok
    done
    # E: the [Service] section moved to the end of the file, so its hand line is the file's LAST line and ends in a backslash: systemd parses
    # the pending continuation without it, and so does the reader on all three roads; the rewrite writes the line without the backslash
    # (the PATH form: its line is replayed as stored, so the stored line must be the one without the backslash: the fold's addendum)
    for form in 'Environment=CLAUDE_CONFIG_DIR=/x/cc|env CLAUDE_CONFIG_DIR|/x/cc' "ExecStart=$ROMP_MANAGER_BIN up|exec0|$ROMP_MANAGER_BIN" 'Environment=PATH=/x/bin:/usr/bin|env PATH|/x/bin:/usr/bin'; do
        { sed -n '/^\[Install\]/,$p' "$unit.clean"; echo; sed '/^\[Install\]/,$d' "$unit.clean"; } > "$unit"
        [[ "$form" != ExecStart=* ]] || { grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; }
        printf '%s\\' "${form%%|*}" >> "$unit"                                          # no newline after the backslash: the file's end
        v="${form#*|}"; [ "$(_sd_read "$unit" ${v%|*})" = "${v#*|}" ]
        CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        CLAUDE_CONFIG_DIR=/x/cc _marked_install_ok
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        run grep -c '\\$' "$unit"
        [ "$status" -ne 0 ]                                                             # no line ends in a backslash any more
        [ "$(_sd_read "$unit" ${v%|*})" = "${v#*|}" ]
    done
    # E, the neighbour: the same line followed by a text line is the continuation systemd joins, refused as before (the oracle reads the
    # join: the next line's text is a second item); a comment or a blank line after it is the addendum's case below
    { sed -n '/^\[Install\]/,$p' "$unit.clean"; echo; sed '/^\[Install\]/,$d' "$unit.clean"; } > "$unit"
    printf 'Environment=CLAUDE_CONFIG_DIR=/x/cc\\\nEnvironment=ADMIN_KNOB=1\n' >> "$unit"
    [ "$(_sd_read "$unit" env Environment)" = ADMIN_KNOB=1 ]
    _three_roads_refuse "$unit" "it ends in a backslash, a continuation systemd joins to the next line"
}

@test "rewrite (Linux): the fold's addendum, class E as systemd applies it: a continuation backslash that only comment lines separate from a blank line or the file's end stands as its own line (a comment then the end, with and without a final newline; a blank line then [Install]; a whitespace-only line then a text line; a comment, a blank line, a text line), read the same on all three roads and written back without the backslash, where one a text line follows past any comments is still the refused join, the header directly after it too, and the oracle reads the join systemd makes" {
    # the mutation pass on the fold (2026-09-19): the fold read the file's LAST line as systemd parses a pending continuation, and the
    # fold case's neighbour asserted a refusal on a comment line following the backslash, a shape systemd reads exactly as the end
    # (config_parse skips a comment line inside an open continuation, and a blank line, whitespace alone included, closes it: the
    # pending line is parsed then); the realistic shape, a trailing backslash typed on the block's last line above the blank line before
    # [Install], was refused. Each shape here was run against systemd-analyze --user verify on 255.4, and the differential's fold batch
    # (tests/romp-service-differential.py) carries them.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mgr="$ROMP_MANAGER_BIN"
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    _end() { { sed -n '/^\[Install\]/,$p' "$unit.clean"; echo; sed '/^\[Install\]/,$d' "$unit.clean"; } > "$unit"; printf "$1" >> "$unit"; }
    _ok() {   # the file at $unit: the oracle reads /x/cc, the three roads accept, the rewrite writes no line ending in a backslash and the
              # oracle still reads /x/cc from what it wrote
        [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
        CLAUDE_CONFIG_DIR=/x/cc ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        CLAUDE_CONFIG_DIR=/x/cc _marked_install_ok
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        run grep -c '\\$' "$unit"
        [ "$status" -ne 0 ]
        [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
        [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    }
    # accepted: comment lines (# and ;) then the end of the file, with and without a final newline
    _end 'Environment=CLAUDE_CONFIG_DIR=/x/cc\\\n# a comment after it\n; and another\n'; _ok
    _end 'Environment=CLAUDE_CONFIG_DIR=/x/cc\\\n# a comment after it'; _ok
    # accepted: a blank line then [Install], the standard layout with the backslash typed on the block's last line; the header stays one
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc\' ''; _ok
    grep -qx '\[Install\]' "$unit"
    # accepted: a whitespace-only line closes it too, and the text line after that is its own line
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc\' $'  \t ' 'Environment=ADMIN_KNOB=1'
    [ "$(_sd_read "$unit" env ADMIN_KNOB)" = 1 ]; _ok
    # accepted: a comment, then a blank line, then a text line
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc\' '# c' '' 'Environment=ADMIN_KNOB=1'
    [ "$(_sd_read "$unit" env ADMIN_KNOB)" = 1 ]; _ok
    # refused: a text line past the comment is the join systemd makes (the oracle reads the second line as the item Environment=ADMIN_KNOB=1,
    # a variable named Environment), and the header directly after the backslash is joined the same way (then no header)
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc\' '# c' 'Environment=ADMIN_KNOB=1'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
    [ "$(_sd_read "$unit" has ADMIN_KNOB)" = no ]
    [ "$(_sd_read "$unit" env Environment)" = ADMIN_KNOB=1 ]
    _three_roads_refuse "$unit" "it ends in a backslash, a continuation systemd joins to the next line (past any comment lines), which this reader reads as a line of its own"
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/cc\'
    [ "$(_sd_read "$unit" env CLAUDE_CONFIG_DIR)" = /x/cc ]
    _three_roads_refuse "$unit" "it ends in a backslash, a continuation systemd joins to the next line"
}

@test "unit oracle: the fold's oracle-only classes, where the reader's answer stood and the oracle's moved to systemd's: %c %r %R raise as not modelled rather than dropping the item (B); the @ prefix's argv leaves the path out and @path alone is refused (F); a repeated or conflicting prefix stays in the path (G); a quoted or escaped ; is an argument (H); . and .. are no executable names (I); exec0 is the simplified path (J); the - prefix drops a failing command and the rest of the line, the others standing (K)" {
    # the fold (2026-09-19): these seven classes were the ORACLE's alone, since the reader refuses every prefix character and every
    # argument shape but `up` alone and compares an ExecStart path as a place; each oracle reading here was run against systemd-analyze
    # --user verify on 255.4 by tests/romp-service-differential.py, which carries the whole fixture set
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" mgr="$ROMP_MANAGER_BIN" c
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    for c in c r R; do                                                                   # B: deprecated, undocumented, still resolved on 255
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/a%${c}b"
        run _sd_read "$unit" has CLAUDE_CONFIG_DIR
        [ "$status" -ne 0 ]
        [[ "$output" == *"NotImplementedError"* && "$output" == *"the specifier %$c is not modelled"* ]]
        _three_roads_refuse "$unit" "the specifier %$c in CLAUDE_CONFIG_DIR"             # the reader's standing answer to a resolving specifier
    done
    _x() { grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "$@"; }
    _x "ExecStart=@$mgr up"                                                              # F: argv[0] is the word after the path
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    [ "$(_sd_read "$unit" execn)" = 1 ]
    _x "ExecStart=@$mgr"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Empty executable name or zeroeth argument"* ]]
    _x "ExecStart=!!$mgr up"                                                             # G: !! is the one accepted pair
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    for c in "!!!" "--" "@@" "+!" "!+" "::" "++"; do
        _x "ExecStart=$c$mgr up"
        [[ "$(_sd_read "$unit" exec0)" == "ERROR: "* ]]                                  # the extra character stays in the path, which is no name
    done
    _x "ExecStart=--$mgr up"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Service has no ExecStart"* ]]              # under -, the failing command is dropped, nothing is left
    _x "ExecStart=!!!$mgr up"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Neither a valid executable name nor an absolute path: !"* ]]
    _x "ExecStart=$mgr up \";\" x"                                                       # H: a quoted ; is an argument, not a separator
    [ "$(_sd_read "$unit" execs)" = 1 ]
    [ "$(_sd_read "$unit" execn)" = 4 ]
    [ "$(_sd_read "$unit" arg 2)" = ';' ]
    _x "ExecStart=$mgr up \; x"                                                         # \; is the argument ; (its text, not its count alone:
    [ "$(_sd_read "$unit" execs)" = 1 ]                                                  # the fold's addendum, where a \; kept as two
    [ "$(_sd_read "$unit" execn)" = 4 ]                                                  # characters counted the same)
    [ "$(_sd_read "$unit" arg 2)" = ';' ]
    _x "ExecStart=$mgr up ; $mgr down" "Type=oneshot"                                    # the unquoted ; separates, as before; the unit's own
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Service has Restart= set to either always or on-success"* ]]   # Restart=always beside Type=oneshot
    _x "ExecStart=$mgr up ; $mgr down" "Type=oneshot" "Restart=on-failure"               # is a file systemd loads nothing from (round 6 of fork
    [ "$(_sd_read "$unit" execs)" = 2 ]                                                  # PR #778, extra5-2), so each plant carries a Restart it loads
    _x "ExecStart=."                                                                     # I: . and .. are no executable names; .x is one
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Neither a valid executable name nor an absolute path: ."* ]]
    _x "ExecStart=.."
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Neither a valid executable name nor an absolute path: .."* ]]
    _x "ExecStart=.x"
    [ "$(_sd_read "$unit" exec0)" = ".x" ]
    local long; long="$(printf 'a%.0s' $(seq 1 255))"                                  # filename_is_valid and path_is_valid: a name or a component of
    _x "ExecStart=$long"                                                                 # 255 bytes is the most (the fold's addendum: NAME_MAX was
    [ "$(_sd_read "$unit" exec0)" = "$long" ]                                            # pinned by the recipe alone, and from the refused side)
    _x "ExecStart=/nx/$long/x"
    [ "$(_sd_read "$unit" exec0)" = "/nx/$long/x" ]
    _x "ExecStart=${long}a"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Neither a valid executable name nor an absolute path: "* ]]
    _x "ExecStart=/nx/${long}a/x"
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Neither a valid executable name nor an absolute path: "* ]]
    _x "ExecStart=${mgr%/romp-manager}//romp-manager up"                                 # J: exec0 is exec->path, simplified; the reader agrees as a place
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
    [ "$status" -eq 0 ]
    _x "ExecStart=${mgr%/romp-manager}/./romp-manager up"
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    _x "ExecStart=-/nx/%1/x" "ExecStart=$mgr up" "Type=oneshot" "Restart=on-failure"     # K: - drops the failing command, the next line stands
    [ "$(_sd_read "$unit" execs)" = 1 ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
    _x "ExecStart=/nx/%1/x" "ExecStart=$mgr up" "Type=oneshot" "Restart=on-failure"      # without -, the unit fails
    [[ "$(_sd_read "$unit" exec0)" == "ERROR: Failed to resolve unit specifiers in the ExecStart command"* ]]
    _x "ExecStart=$mgr up ; -/nx/a\\\\b ; /nx/bin/c" "Type=oneshot" "Restart=on-failure" # the commands before the failing one stand, the rest of the line goes
    [ "$(_sd_read "$unit" execs)" = 1 ]
    [ "$(_sd_read "$unit" exec0)" = "$mgr" ]
}

@test "rewrite (Linux): D3 over its four letters in one pin: %c, %r and %R in a kept Environment value are refused as %h is, on rewrite, rewrite --check and the marked child's install (exit 5, the specifier named in the variable as one systemd expands and this reader would take literally, the absolute path as the remedy, the file byte for byte), and %r in ExecStart's path is refused the same way, %c %R %h beside it; a narrowing that exempts the deprecated letters, or %h alone, turns this red" {
    # round 5 preface (2026-09-19; the ruling on the fold, class B accepted as left): systemd 255 still resolves the deprecated %c %r %R
    # (with a deprecation warning), so D3, a specifier the reader would take literally is refused with the absolute path as the remedy,
    # covers four letters, and nothing held the three deprecated ones by the whole refusal text or the remedy (the oracle-only case
    # above asserts the short phrase). Green at the head it was written on, since the reader already refuses: the red here is a future
    # narrowing's, _unit_specifiers exempting c, r and R (the documented table alone) or h alone.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" c
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    for c in c r R h; do
        cp "$unit.clean" "$unit"; _svc_line "$unit" "Environment=CLAUDE_CONFIG_DIR=/x/a%${c}b"
        _three_roads_refuse "$unit" "the specifier %$c in CLAUDE_CONFIG_DIR, which systemd expands and this reader would take literally"
        _three_roads_refuse "$unit" "Write the absolute path in its place (a literal % is written %%)"
        grep -v '^ExecStart=' "$unit.clean" > "$unit"; _svc_line "$unit" "ExecStart=/x/%${c}/romp-manager up"
        _three_roads_refuse "$unit" "ExecStart carries the specifier %$c, which systemd expands and this reader would take literally"
        _three_roads_refuse "$unit" "Write the absolute path in its place (a literal % is written %%)"
    done
}

@test "rewrite (Linux): a \\u escape naming a surrogate or a noncharacter in ExecStart's path is refused on rewrite, rewrite --check and the marked child's install (exit 5, the file byte for byte) with this surface's own form, that systemd decodes the escape and runs the unit where a rewrite would write the decoded bytes raw and systemd then refuses the line whole, and refusal 13's remedy, to move the clone; the Environment= twin's consequence and its remove-the-escape remedy are absent, and the oracle reads the decoded path systemd runs" {
    # the round-5 preface (fork PR #778, 2026-09-19; verified on 255.4 by hand and by the differential's esc-P-bsuFFFE and esc-P-bsud800):
    # systemd's cunescape_one decodes a \u surrogate or noncharacter into bytes and config_parse_exec keeps the path, so the unit loads and
    # runs; the same bytes written raw are a line systemd refuses whole (String is not UTF-8 clean), so the escape is the only written form
    # that reads back to the same bytes, and the writer, which writes a path raw, has none. The refusal is right; its text rendered the
    # Environment= twin's parenthetical (an assignment carrying them is dropped, that surface's consequence) and its remedy said to remove
    # the escape, which cannot be followed: a rewrite proceeds only when the path is this clone's, so the escape stands for a byte of the
    # executable's real path. Red under the old remedy restored (the _W_EXEC_ERR and _W_EXEC_FIX assignments dropped from _unit_unichar).
    # The addendum to that commit (the lens on it): the remedy's clause that the install restarts the manager was false (a plain install
    # runs daemon-reload and enable --now, which leaves an active unit as it is, and nothing in the reader calls restart: a logged stub
    # counts 0 restart calls), so the remedy now says the running manager keeps its old unit until its next restart, with the command, as
    # the rewrite's own line does, and the old clause is asserted absent; red under that clause restored.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" form esc rest what raw
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    for form in '\uFFFE|a noncharacter|'$'\xef\xbf\xbe' '\uD800|a surrogate|'$'\xed\xa0\x80' '\uFDD0|a noncharacter|'$'\xef\xb7\x90' '\uDFFF|a surrogate|'$'\xed\xbf\xbf'; do
        esc="${form%%|*}"; rest="${form#*|}"; what="${rest%%|*}"; raw="${rest#*|}"
        cp "$unit.clean" "$unit"; grep -v '^ExecStart=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"
        _svc_line "$unit" "ExecStart=$TEST_DIR/a${esc}b/romp-manager up"
        [ "$(_sd_read "$unit" exec0)" = "$TEST_DIR/a${raw}b/romp-manager" ]           # systemd loads the unit and runs the decoded path
        ROMP_MANAGER_BIN="$TEST_DIR/a${raw}b/romp-manager" _three_roads_refuse "$unit" \
            "ExecStart's command has the escape $esc, $what, which systemd decodes into bytes that are not UTF-8 by its rule and runs this unit with; a rewrite would have to write the decoded bytes raw, which systemd then refuses whole (String is not UTF-8 clean), so this reader does not carry the escape" \
            "an Environment= assignment carrying them is dropped" "Remove the escape from" "this reader does not model that reading" "then systemctl --user daemon-reload"
        ROMP_MANAGER_BIN="$TEST_DIR/a${raw}b/romp-manager" _three_roads_refuse "$unit" \
            "Move the clone to a path without such characters (the escape stands for a byte of the executable's real path, so the line without it names another place) and run romp-service install from it, which writes the unit afresh; the running manager keeps its old unit until its next restart:  systemctl --user restart romp-manager" \
            "restarts the manager"
    done
    # the Environment= twin keeps its own consequence and remedy (the fold case above holds them; here the one phrase that tells the two apart)
    cp "$unit.clean" "$unit"; _svc_line "$unit" 'Environment=CLAUDE_CONFIG_DIR=/x/\uFFFE'
    _three_roads_refuse "$unit" "an Environment= assignment carrying them is dropped" "runs this unit with" "Move the clone"
}

@test "rewrite (Linux): an EnvironmentFile path with a doubled slash, a . component or a trailing slash is read as written and written back byte for byte on rewrite, rewrite --check and the marked child's install, its - prefix kept, where systemd and the oracle read the simplified path from the same line before and after; a shell naming the same spelling agrees, one naming the simplified spelling agrees when the place exists and is refused, exit 5 and nothing written, when it does not" {
    # the round-5 preface (fork PR #778, 2026-09-19), by execution on 255.4: systemd's config_parse_unit_env_file runs path_simplify_and_warn
    # on the path (-/x//y/env loads as -/x/y/env; /x/./env and /x/env/ as /x/env; a .. component left after simplifying is ignored as not
    # normalized), and the reader neither simplifies nor refuses: the line goes back as written, its - prefix kept, so the file systemd reads
    # is the same before and after a rewrite. The compare against ROMP_SERVICE_ENV_FILE is by place (_same_path): the same spelling agrees,
    # and so does the simplified one for a place that exists; two spellings of a place that does not exist are refused (exit 5, nothing
    # written), a false refusal on the safe side, stated here as it is. The oracle raised on these forms as not modelled until this commit.
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service" form simp
    _old_unit "$unit"; cp "$unit" "$unit.clean"
    mkdir -p "$TEST_DIR/ef/y"
    for form in "-/x//y/env|/x/y/env" "/x/./env|/x/env" "/x/env/|/x/env" "-$TEST_DIR/ef//y/env|$TEST_DIR/ef/y/env" "$TEST_DIR/ef/./env|$TEST_DIR/ef/env" "$TEST_DIR/ef/env/|$TEST_DIR/ef/env"; do
        simp="${form#*|}"; form="${form%%|*}"
        cp "$unit.clean" "$unit"; grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; _svc_line "$unit" "EnvironmentFile=$form"
        [ "$(_sd_read "$unit" envfile)" = "$simp" ]                                        # systemd's reading: the simplified path
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check
        [ "$status" -eq 0 ]
        _marked_install_ok
        grep -qxF "EnvironmentFile=$form" "$unit"                                           # written back as written, the prefix kept
        cp "$unit.clean" "$unit"; grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; _svc_line "$unit" "EnvironmentFile=$form"
        ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
        [ "$status" -eq 0 ]
        grep -qxF "EnvironmentFile=$form" "$unit"
        [ "$(_sd_read "$unit" envfile)" = "$simp" ]                                        # and systemd reads the same file from the written line
        ROMP_SERVICE_ENV_FILE="${form#-}" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check    # the same spelling agrees
        [ "$status" -eq 0 ]
        cp "$unit" "$unit.before"
        ROMP_SERVICE_ENV_FILE="$simp" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite --check         # the simplified spelling: by place
        if [[ "$form" == *"$TEST_DIR"* ]]; then
            [ "$status" -eq 0 ]
        else
            [ "$status" -eq 5 ]
            [[ "$output" == *"ROMP_SERVICE_ENV_FILE: the file reads ${form#-}, this environment names $simp"* ]]
            [[ "$output" == *"nothing was rewritten"* ]]
            ROMP_SERVICE_ENV_FILE="$simp" ROMP_OS_OVERRIDE=Linux run "$SVC" rewrite
            [ "$status" -eq 5 ]
            cmp -s "$unit" "$unit.before"
        fi
    done
    # the neighbour systemd ignores: a .. component left after simplifying reads no file to systemd and to the oracle, and the reader keeps
    # the line as it keeps a path that is not absolute
    cp "$unit.clean" "$unit"; grep -v '^EnvironmentFile=' "$unit" > "$unit.new" && mv -f "$unit.new" "$unit"; _svc_line "$unit" 'EnvironmentFile=-/x/y/../env'
    run _sd_read "$unit" envfile                                                          # the run form: an oracle that raised is a nonzero status,
    [ "$status" -eq 0 ]                                                                   # not an empty answer (round 6 of fork PR #778, tests-5)
    [ "$output" = "" ]
}

@test "unit reader: the header's numbered list of refusals is one item per _unit_refuse call site in _unit_scan, 1 to N with no gap, every call site in the file inside that function, and N is 21" {
    # the mutation pass (2026-09-19): the header states the list's definition (the call sites) and its count, and nothing held either;
    # a refusal added without its item, or an item without its call site, turns this red until the header is brought level
    # a call site is the name followed by a blank on a line that is not a comment (the fold's addendum: the count read the name and a
    # quote, and a call whose first argument was unquoted, `_unit_refuse 0 ...`, escaped it; the definition has ( after the name)
    local n_sites n_file items
    n_sites="$(awk '/^_unit_scan\(\) \{/ { f = 1 } f && !/^[[:space:]]*#/ && /_unit_refuse / { c++ } f && /^\}/ { print c + 0; exit }' "$SVC")"
    n_file="$(grep -vE '^[[:space:]]*#' "$SVC" | grep -c '_unit_refuse ')"
    [ -n "$n_sites" ]
    [ "$n_sites" = "$n_file" ]
    items="$(sed -n '/Refused, one item per _unit_refuse call site/,/^# A line systemd ignores that carries nothing/p' "$SVC" \
        | grep -oE '(^|[^0-9.])[0-9]+\. [a-z]' | sed -E 's/^[^0-9]*//; s/\. .*//' | sort -n | uniq | tr '\n' ' ')"
    [ "$items" = "$(seq 1 "$n_sites" | tr '\n' ' ')" ]
    [ "$n_sites" -eq 21 ]
}

@test "unit reader tests: an oracle answer expected to be empty is read through run and its status, never through a command substitution compared to the empty string, so a raising oracle is a red case and not an empty answer (a census of this file)" {
    # round 6 of fork PR #778 (tests-5): bats applies no errexit inside a test command's substitution, so a nonzero exit of the oracle read as
    # the empty answer the assertion expected, and the same delta had given the oracle a raising path. The three sites were rewritten to the
    # run form (a status 0 and no text), the two PATH reads beside them with the addendum, and the shape is held here over the file, since no
    # checked-in unit those sites read makes the oracle raise (the pin the revert reds is this census, not a case)
    local sub='\[ "\$\(_sd_read [^)]*\)" = "" \]' n_run
    run grep -cE -- "$sub" "$BATS_TEST_FILENAME"
    [ "$status" -ne 0 ]
    [ "$output" = 0 ]
    run grep -cE -- "${sub%\"\" \\]}'' \\]" "$BATS_TEST_FILENAME"
    [ "$status" -ne 0 ]
    [ "$output" = 0 ]
    n_run="$(grep -cE 'run _sd_read "\$unit" (envfile|env PATH)( +#.*)?$' "$BATS_TEST_FILENAME")"
    [ "$n_run" -ge 5 ]                                                                    # the run form stands at the five sites
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
