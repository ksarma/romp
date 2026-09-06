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
    unset ROMP_SERVE_PORT ROMP_KERNEL_PORT ROMP_POSTAL_PORT ROMP_MANAGER_PORT ROMP_STATE_DIR CLAUDE_CONFIG_DIR ROMP_TMUX_SOCKET
    # The env-file path is baked (and, when non-default, exported) into the unit too; a developer shell
    # that carries any of these must not leak it into the default-install assertions below.
    unset ROMP_SERVICE_ENV_FILE ROMP_SERVICE_ENV XDG_CONFIG_HOME
}

teardown() { rm -rf "$TEST_DIR"; }

@test "install (macOS): launchd plist runs 'romp-manager up' at login, kept alive" {
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    local plist="$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
    [ -f "$plist" ]
    grep -q "<string>$ROMP_MANAGER_BIN</string>" "$plist"
    grep -q "<string>up</string>" "$plist"
    grep -q "RunAtLoad" "$plist"
    grep -q "KeepAlive" "$plist"
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
    # After bootstrap the NEW job answers print (the post-install running check sees it).
    grep -q bootstrap "$calls" && exit 0
    [ "\$(grep -c print "$calls")" -ge 4 ] && exit 5   # the old job finally drains away
    exit 0                                             # still tearing down
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

@test "install bakes the rest of the profile: state root, Claude config dir, tmux socket" {
    # The same set romp-manager's specEnv hands an aux kernel — a profile that is only half
    # carried is the silent-divergence bug, not a smaller version of it.
    export ROMP_STATE_DIR="$TEST_DIR/alt-state" CLAUDE_CONFIG_DIR="$TEST_DIR/alt-claude" ROMP_TMUX_SOCKET=romp-alt
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    grep -q "^Environment=ROMP_STATE_DIR=$TEST_DIR/alt-state$"      "$unit"
    grep -q "^Environment=CLAUDE_CONFIG_DIR=$TEST_DIR/alt-claude$"  "$unit"
    grep -q "^Environment=ROMP_TMUX_SOCKET=romp-alt$"               "$unit"
}

@test "a default install writes NO instance env — unchanged for everyone not doing this" {
    # setup() cleared the set, so this is the single-user machine's install.
    ROMP_OS_OVERRIDE=Linux run "$SVC" install
    [ "$status" -eq 0 ]
    local unit="$ROMP_SYSTEMD_DIR/romp-manager.service"
    run grep -q "ROMP_SERVE_PORT\|ROMP_KERNEL_PORT\|ROMP_POSTAL_PORT\|ROMP_MANAGER_PORT\|ROMP_STATE_DIR\|CLAUDE_CONFIG_DIR\|ROMP_TMUX_SOCKET" "$unit"
    [ "$status" -ne 0 ]
    # ...and the file is still well-formed around the seam: the always-present
    # (optional, dash-prefixed) EnvironmentFile line, a blank line, then [Install].
    grep -q "^Environment=ROMP_SUPERVISED=1$" "$unit"
    grep -q "^EnvironmentFile=-" "$unit"
    grep -q "^\[Install\]$" "$unit"
    [ -z "$(sed -n '/^EnvironmentFile=-/{n;p;}' "$unit")" ]
    ROMP_OS_OVERRIDE=Darwin run "$SVC" install
    [ "$status" -eq 0 ]
    run grep -q "ROMP_SERVE_PORT\|ROMP_STATE_DIR\|ROMP_TMUX_SOCKET" "$ROMP_LAUNCHD_DIR/com.romp.manager.plist"
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
    # kernel/keysource.py resolves the env file from the SERVICE's environment, which never sees the
    # installing shell's ROMP_SERVICE_ENV_FILE — so a non-default path baked into EnvironmentFile= alone
    # was read by systemd and not by the kernel's live key read (romp keyswap rewrote a file the kernel
    # never looked at). The resolved path now rides the unit and the plist whenever it is not the default.
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
    # kernel/keysource.py resolves the env file from ROMP_SERVICE_ENV_FILE, else its alias ROMP_SERVICE_ENV, so
    # `romp keyswap` in a shell that set only the alias reads that file and, on a MISMATCH, sends the operator
    # to `romp-service install` from this shell. The installer read the primary alone: that install wrote no
    # override line and the kernel kept the default path with the remedy done (review find, 2026-09-06). Both
    # names now resolve here as they do there, and the line written is always the primary, which
    # bin/romp-node-launch and the kernel read.
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
    # both set: the primary wins, the order kernel/keysource.py reads them in
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

# ─── status: the key source and the unit's shape (2026-09-05) ────────────────────────
# `status` reads the same non-secret configuration the kernel reads (kernel/envsource.py: this
# environment, then service.env) and says which key source is in force, whether ExecStart runs the
# manager through a shell, and which credential-shaped NAMES a unit, drop-in, plist or service.env
# carries. Values are assembled at run time and the assertions check none of them is printed.

@test "status (Linux): key source is file by default, command with its selector when the command is configured" {
    ROMP_OS_OVERRIDE=Linux "$SVC" install >/dev/null
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"key source: file"* ]]
    [[ "$output" == *"ExecStart: runs the manager directly"* ]]
    [[ "$output" != *"credential-shaped"* ]]
    # the command in this environment; the selector in its default file under XDG_CONFIG_HOME
    export XDG_CONFIG_HOME="$TEST_DIR/cfg"
    mkdir -p "$XDG_CONFIG_HOME/romp"
    ROMP_CREDENTIAL_COMMAND="$TEST_DIR/cred.sh \"\$1\"" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"key source: command (no selector)"* ]]
    [[ "$output" != *"cred.sh"* ]]                            # which source, never the setting's text
    printf 'hp\n' > "$XDG_CONFIG_HOME/romp/credential-selector"
    # the token is shown by name only when ROMP_CREDENTIAL_NAMES declares it; undeclared, by length
    ROMP_CREDENTIAL_COMMAND="$TEST_DIR/cred.sh \"\$1\"" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"key source: command (selector undeclared, 2 chars)"* ]]
    [[ "$output" != *"selector hp"* ]]
    ROMP_CREDENTIAL_COMMAND="$TEST_DIR/cred.sh \"\$1\"" ROMP_CREDENTIAL_NAMES="hp, lp" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"key source: command (selector hp)"* ]]
    ROMP_CREDENTIAL_COMMAND="$TEST_DIR/cred.sh \"\$1\"" ROMP_CREDENTIAL_NAMES="lp" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"key source: command (selector undeclared, 2 chars)"* ]]
    # a selector file holding something that is not a name is said, not shown
    local junk="romp-test-fixture-$RANDOM $RANDOM"
    printf '%s\n' "$junk" > "$XDG_CONFIG_HOME/romp/credential-selector"
    ROMP_CREDENTIAL_COMMAND="$TEST_DIR/cred.sh \"\$1\"" ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"key source: command (selector file holds something that is not a name)"* ]]
    [[ "$output" != *"fixture"* ]]
}

@test "status: the same lines in service.env are read the way the kernel reads them (last wins, one layer of quotes)" {
    export ROMP_SERVICE_ENV_FILE="$TEST_DIR/service.env"
    printf 'lp\n' > "$TEST_DIR/sel"
    printf 'ROMP_EXPECTED_AUTH=key\nROMP_CREDENTIAL_COMMAND=first\nROMP_CREDENTIAL_COMMAND="%s"\n  ROMP_CREDENTIAL_SELECTOR_FILE = %s\nROMP_CREDENTIAL_NAMES=hp,lp\n' \
        "$TEST_DIR/cred.sh \"\$1\"" "$TEST_DIR/sel" > "$ROMP_SERVICE_ENV_FILE"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"not installed"* ]]
    [[ "$output" == *"key source: command (selector lp)"* ]]
    [[ "$output" != *"ExecStart"* ]]                          # no unit: nothing to say about its shape
    [[ "$output" != *"cred.sh"* ]]
    # an empty assignment last is "unset": file mode
    printf 'ROMP_CREDENTIAL_COMMAND=x\nROMP_CREDENTIAL_COMMAND=\n' > "$ROMP_SERVICE_ENV_FILE"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"key source: file"* ]]
}

@test "status (Linux): names credential-shaped lines a unit or drop-in carries — names only — and a shell-wrapped ExecStart" {
    ROMP_OS_OVERRIDE=Linux "$SVC" install >/dev/null
    local v="romp-test-fixture-$RANDOM$RANDOM$RANDOM"
    mkdir -p "$ROMP_SYSTEMD_DIR/romp-manager.service.d"
    {
        printf '[Service]\n'
        printf 'Environment=ANTHROPIC_API_KEY=%s "OTHER_TOKEN=%s x" EMPTY_TOKEN= NOT_A_SECRET=1\n' "$v" "$v"
        printf 'Environment="SECOND_API_KEY=%s"\n' "$v"
        printf 'ExecStart=\n'
        printf "ExecStart=/usr/bin/zsh -lc 'exec %s up'\n" "$ROMP_MANAGER_BIN"
    } > "$ROMP_SYSTEMD_DIR/romp-manager.service.d/shell.conf"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"unit carries credential-shaped lines: ANTHROPIC_API_KEY, OTHER_TOKEN, SECOND_API_KEY"* ]]
    [[ "$output" != *"EMPTY_TOKEN"* ]]                        # set to nothing: not a credential
    [[ "$output" != *"NOT_A_SECRET"* ]]
    [[ "$output" != *"$v"* ]]                                 # never a value
    [[ "$output" == *"ExecStart: runs the manager through a shell (its variables freeze until a manager restart)"* ]]
    # `env` in front of the shell is still the shell; a drop-in that resets to the direct form reads direct
    printf '[Service]\nExecStart=\nExecStart=/usr/bin/env FOO=1 bash -c "exec %s up"\n' "$ROMP_MANAGER_BIN" \
        > "$ROMP_SYSTEMD_DIR/romp-manager.service.d/shell.conf"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"through a shell"* ]]
    printf '[Service]\nExecStart=\nExecStart=%s up\n' "$ROMP_MANAGER_BIN" > "$ROMP_SYSTEMD_DIR/romp-manager.service.d/shell.conf"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [[ "$output" == *"ExecStart: runs the manager directly"* ]]
    [[ "$output" != *"credential-shaped"* ]]
}

@test "status (Linux): Environment= bodies split like systemd — a quoted assignment with spaces is ONE assignment" {
    ROMP_OS_OVERRIDE=Linux "$SVC" install >/dev/null
    local v="romp-test-fixture-$RANDOM$RANDOM$RANDOM"
    mkdir -p "$ROMP_SYSTEMD_DIR/romp-manager.service.d"
    {
        printf '[Service]\n'
        # A_TOKEN's value has a space; B_TOKEN=b sits INSIDE NOT's quoted value (a value, not a name);
        # C_TOKEN quotes only its value; D_TOKEN's quoted value is a space and a letter (non-empty);
        # E_TOKEN's quoted value is empty
        printf 'Environment="A_TOKEN=%s x" "NOT=a B_TOKEN=%s" C_TOKEN="p q" "D_TOKEN= z" E_TOKEN=""\n' "$v" "$v"
    } > "$ROMP_SYSTEMD_DIR/romp-manager.service.d/env.conf"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"unit carries credential-shaped lines: A_TOKEN, C_TOKEN, D_TOKEN"* ]]
    [[ "$output" != *"B_TOKEN"* ]]                            # part of NOT's value, never a variable the unit sets
    [[ "$output" != *"E_TOKEN"* ]]                            # set to nothing
    [[ "$output" != *"$v"* ]]
}

# _split_env_words called directly: the function's text is taken from the script (running the script
# would dispatch a subcommand) and defined in this shell, which has no `body` variable of its own.
_load_split_env_words() { eval "$(sed -n '/^_split_env_words() {/,/^}/p' "$SVC")"; }

@test "_split_env_words: splits its ARGUMENT from a caller with no body variable" {
    # `local body="$1" ... n=${#body}` expanded ${#body} before local assigned body, so n was the
    # length of the CALLER's body (0 here): nothing was printed. The one caller in the script happens
    # to hold the same string in a variable of that name, which is why status never showed it.
    _load_split_env_words
    unset body
    run _split_env_words 'A_TOKEN=x "B_TOKEN=y z" C=1'
    [ "$status" -eq 0 ]
    [ "$output" = $'A_TOKEN=x\nB_TOKEN=y z\nC=1' ]
    body="short"                                              # a caller's shorter body: still the argument
    run _split_env_words 'LONGER_TOKEN=a-value-longer-than-the-word-short D=2'
    [ "$status" -eq 0 ]
    [ "$output" = $'LONGER_TOKEN=a-value-longer-than-the-word-short\nD=2' ]
}

@test "_split_env_words: a backslash escapes the next character inside and outside quotes; an unterminated quote keeps the words before it" {
    _load_split_env_words
    unset body
    run _split_env_words 'A_TOKEN=a\ b "B_TOKEN=c\"d e" C_TOKEN=\"f D=\\x'
    [ "$status" -eq 0 ]
    [ "$output" = $'A_TOKEN=a b\nB_TOKEN=c"d e\nC_TOKEN="f\nD=\\x' ]
    run _split_env_words "'S_TOKEN=it\\'s' T=1"
    [ "$status" -eq 0 ]
    [ "$output" = $'S_TOKEN=it\'s\nT=1' ]
    run _split_env_words 'A_TOKEN=trail\'
    [ "$status" -eq 0 ]
    [ "$output" = 'A_TOKEN=trail' ]
    run _split_env_words 'X=1 "A_TOKEN=open B_TOKEN=b'
    [ "$status" -eq 1 ]
    [ "$output" = 'X=1' ]                                     # the words before the quote, as systemd keeps them; nothing from the quote on
    run _split_env_words '"A_TOKEN=open B_TOKEN=b'
    [ "$status" -eq 1 ]
    [ -z "$output" ]                                          # the quote opened the first word: no word stands
    run _split_env_words ""
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "status (Linux): an escaped quote in an Environment= value is a value, and an unterminated line names the words before its quote" {
    ROMP_OS_OVERRIDE=Linux "$SVC" install >/dev/null
    local v="romp-test-fixture-$RANDOM$RANDOM$RANDOM"
    mkdir -p "$ROMP_SYSTEMD_DIR/romp-manager.service.d"
    {
        printf '[Service]\n'
        # A_TOKEN's value carries an escaped quote followed by what looks like a second assignment: one word
        printf 'Environment="A_TOKEN=%s\\" B_TOKEN=%s"\n' "$v" "$v"
        # an unterminated quote: systemd ignores the assignment it opens, and so does this (C_TOKEN is not named)
        printf 'Environment="C_TOKEN=%s\n' "$v"
        printf 'Environment=D_TOKEN=%s\n' "$v"
        # a word completed before an unterminated quote is kept, by systemd and here (E_TOKEN named, F_TOKEN not)
        printf 'Environment=E_TOKEN=%s "F_TOKEN=%s\n' "$v" "$v"
    } > "$ROMP_SYSTEMD_DIR/romp-manager.service.d/env.conf"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"unit carries credential-shaped lines: A_TOKEN, D_TOKEN, E_TOKEN"* ]]
    [[ "$output" != *"B_TOKEN"* ]]
    [[ "$output" != *"C_TOKEN"* ]]
    [[ "$output" != *"F_TOKEN"* ]]
    [[ "$output" != *"$v"* ]]
}

@test "status: a credential-shaped line in service.env is named, never shown" {
    export ROMP_SERVICE_ENV_FILE="$TEST_DIR/service.env"
    local v="romp-test-fixture-$RANDOM$RANDOM$RANDOM"
    printf 'ROMP_EXPECTED_AUTH=key\nANTHROPIC_API_KEY=%s\nMY_TOKEN=""\n# A_TOKEN=%s\nROMP_TOKEN_COUNT=3\n' "$v" "$v" > "$ROMP_SERVICE_ENV_FILE"
    ROMP_OS_OVERRIDE=Linux run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"service.env carries credential-shaped lines: ANTHROPIC_API_KEY"* ]]
    [[ "$output" != *"MY_TOKEN"* ]]                           # empty after the quotes: no credential
    [[ "$output" != *"A_TOKEN"* ]]                            # a comment
    [[ "$output" != *"$v"* ]]
}

@test "status (macOS): the plist's pairs and program are read the same way" {
    ROMP_OS_OVERRIDE=Darwin "$SVC" install >/dev/null
    ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"key source: file"* ]]
    [[ "$output" == *"ExecStart: runs the manager directly"* ]]   # romp-node-launch is the program, not a shell
    [[ "$output" != *"credential-shaped"* ]]
    local v="romp-test-fixture-$RANDOM$RANDOM$RANDOM"
    cat > "$ROMP_LAUNCHD_DIR/com.romp.manager.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
  <key>Label</key><string>com.romp.manager</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>exec $ROMP_MANAGER_BIN up</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/usr/bin</string>
    <key>A_TOKEN</key><string>$v</string>
    <key>EMPTY_API_KEY</key><string></string>
  </dict>
</dict>
</plist>
EOF
    ROMP_OS_OVERRIDE=Darwin run "$SVC" status
    [ "$status" -eq 0 ]
    [[ "$output" == *"unit carries credential-shaped lines: A_TOKEN"* ]]
    [[ "$output" != *"EMPTY_API_KEY"* ]]
    [[ "$output" != *"$v"* ]]
    [[ "$output" == *"ExecStart: runs the manager through a shell"* ]]
}
