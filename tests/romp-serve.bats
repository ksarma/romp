#!/usr/bin/env bats

# romp-serve maps the manager's spawn contract (--port / ROMP_SERVE_PORT) onto the
# Python kernel's env and execs it. The kernel binds loopback only; tailnet reach
# is `tailscale serve` proxying to loopback, so there is no persisted host opt-in
# (`romp --serve` removed 2026-07-19).

BIN="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)"
ROMP_SERVE="$BIN/romp-serve"
ROMP_SCRIPT="$BIN/romp"

setup() {
    # Running this suite INSIDE a romp session inherits the live kernel's port env, which would
    # turn every "unset" case below into an override (same trap tests/romp-service.bats documents).
    # ROMP_STATE_DIR too: a profiled kernel exports it to its sessions, and pick_python reads it before
    # XDG_STATE_HOME, so with it inherited the venv cases below would read a LIVE venv's pyvenv.cfg.
    unset ROMP_SERVE_PORT ROMP_KERNEL_PORT ROMP_STATE_DIR
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"
    export XDG_STATE_HOME="$HOME/.local/state"
    mkdir -p "$XDG_STATE_HOME/romp"
    # Stub kernel: print the env romp-serve hands it, then exit (no real server).
    export ROMP_KERNEL_BIN="$TEST_DIR/stub-kernel"
    cat > "$ROMP_KERNEL_BIN" << 'STUB'
#!/usr/bin/env bash
echo "PORT=${ROMP_KERNEL_PORT:-}"
echo "SERVEPORT=${ROMP_SERVE_PORT:-}"
echo "HOST=${ROMP_SERVE_HOST:-}"
echo "NOOPEN=${ROMP_KERNEL_NO_OPEN:-}"
echo "MGRPID=${ROMP_MANAGER_PID:-}"
STUB
    chmod +x "$ROMP_KERNEL_BIN"
    # romp-serve now execs the kernel VIA a picked python (`exec "$PY" "$KERNEL"`); the stub kernel is
    # bash, so hand it a "python" that just runs its argument as a shell script.
    export ROMP_PYTHON="$TEST_DIR/fake-python"
    cat > "$ROMP_PYTHON" << 'SHIM'
#!/usr/bin/env bash
exec bash "$@"
SHIM
    chmod +x "$ROMP_PYTHON"
}

teardown() { rm -rf "$TEST_DIR"; }

@test "romp-serve: maps --port to ROMP_KERNEL_PORT, sets no-open, execs the kernel" {
    run "$ROMP_SERVE" --port 9999
    [ "$status" -eq 0 ]
    [[ "$output" == *"PORT=9999"* ]]
    [[ "$output" == *"NOOPEN=1"* ]]
}

@test "romp-serve: host defaults to 127.0.0.1 with no opt-in" {
    run "$ROMP_SERVE" --port 9999
    [[ "$output" == *"HOST=127.0.0.1"* ]]
}

@test "romp-serve: a stale serve-host file can NOT rebind the kernel off loopback" {
    # The `romp --serve` opt-in is removed; a leftover state file must be ignored,
    # never silently expose the kernel on 0.0.0.0.
    printf '0.0.0.0\n' > "$XDG_STATE_HOME/romp/serve-host"
    run "$ROMP_SERVE" --port 9999
    [[ "$output" == *"HOST=127.0.0.1"* ]]
}

@test "romp-serve: explicit --host still wins (the manager's spawn seam)" {
    run "$ROMP_SERVE" --port 9999 --host 0.0.0.0
    [[ "$output" == *"HOST=0.0.0.0"* ]]
}

@test "romp-serve: ROMP_SERVE_PORT fallback + forwards ROMP_MANAGER_PID" {
    ROMP_MANAGER_PID=4242 ROMP_SERVE_PORT=29855 run "$ROMP_SERVE"
    [[ "$output" == *"PORT=29855"* ]]
    [[ "$output" == *"MGRPID=4242"* ]]
}

# ─── the two spellings of the listen port ───────────────────────────────────────────────────
# ROMP_SERVE_PORT (service-facing) and ROMP_KERNEL_PORT (process-facing) name ONE value, and
# this script is the seam where they meet. It used to read only the first and stamp it over the
# second, so renumbering a second kernel with the documented knob alone put the kernel on the
# primary's port while the CLI kept printing the configured one.

@test "romp-serve: ROMP_KERNEL_PORT alone (the documented knob) reaches the kernel" {
    ROMP_KERNEL_PORT=29856 run "$ROMP_SERVE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"PORT=29856"* ]]
}

@test "romp-serve: exports BOTH spellings from the one resolved port" {
    # Nothing downstream (the postal bus, the wake hook, a `romp` verb in a session) may read a
    # stale copy of the other name.
    ROMP_KERNEL_PORT=29856 run "$ROMP_SERVE"
    [[ "$output" == *"PORT=29856"* ]]
    [[ "$output" == *"SERVEPORT=29856"* ]]
    ROMP_SERVE_PORT=29857 run "$ROMP_SERVE"
    [[ "$output" == *"PORT=29857"* ]]
    [[ "$output" == *"SERVEPORT=29857"* ]]
}

@test "romp-serve: --port settles a disagreement and wins over both env spellings" {
    # The manager always passes --port; that is the kernel's own name for itself, so a stale
    # inherited env copy must never override it.
    ROMP_SERVE_PORT=29855 ROMP_KERNEL_PORT=29999 run "$ROMP_SERVE" --port 30001
    [ "$status" -eq 0 ]
    [[ "$output" == *"PORT=30001"* ]]
    [[ "$output" == *"SERVEPORT=30001"* ]]
}

@test "romp-serve: conflicting spellings with no --port REFUSE to start" {
    # A silent pick here is the collision that reports success. Fail loudly instead.
    ROMP_SERVE_PORT=29855 ROMP_KERNEL_PORT=29856 run "$ROMP_SERVE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"29855"* ]]
    [[ "$output" == *"29856"* ]]
    ! printf '%s\n' "$output" | grep -q '^PORT='     # the stub kernel never ran
}

@test "romp-serve: matching spellings are not a conflict" {
    ROMP_SERVE_PORT=29856 ROMP_KERNEL_PORT=29856 run "$ROMP_SERVE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"PORT=29856"* ]]
}

@test "romp-serve: neither set and no --port leaves both unset (the kernel's own default)" {
    run "$ROMP_SERVE"
    [ "$status" -eq 0 ]
    [ "$(printf '%s\n' "$output" | grep '^PORT=')" = "PORT=" ]
    [ "$(printf '%s\n' "$output" | grep '^SERVEPORT=')" = "SERVEPORT=" ]
}

@test "romp --serve: removed — rejected as unknown, writes no state" {
    run "$ROMP_SCRIPT" --serve on
    [ "$status" -ne 0 ]
    [[ "$output" == *"unknown option"* ]]
    [ ! -f "$XDG_STATE_HOME/romp/serve-host" ]
}

# ─── pick_python: the kernel runs on the best python available (Agent SDK needs >= 3.10) ────────
# Unit tests over the extracted function. It runs only candidates the tests lay down as fakes, so a
# bare fake PATH is enough; that PATH has no `timeout`, which is the no-coreutils path, and one test
# below adds the real one back. The e2e wiring (exec "$PY" "$KERNEL") is covered by every test above
# via the ROMP_PYTHON shim in setup().

extract_pick() { sed -n '/^pick_python()/,/^}/p' "$1"; }

@test "pick_python: ROMP_PYTHON override wins verbatim" {
    mkdir -p "$TEST_DIR/custom"
    printf '#!/bin/sh\n' > "$TEST_DIR/custom/python"; chmod +x "$TEST_DIR/custom/python"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON="$TEST_DIR/custom/python" run pick_python
    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_DIR/custom/python" ]
}

@test "pick_python: newest python3.1x on PATH beats plain python3" {
    fakebin="$TEST_DIR/fakebin"; mkdir -p "$fakebin"
    printf '#!/bin/sh\n' > "$fakebin/python3.12"; chmod +x "$fakebin/python3.12"
    printf '#!/bin/sh\n' > "$fakebin/python3";    chmod +x "$fakebin/python3"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON= PATH="$fakebin" run pick_python
    [ "$output" = "$fakebin/python3.12" ]
}

@test "pick_python: probes ~/.local/bin explicitly (non-login ssh shells lack it on PATH)" {
    mkdir -p "$HOME/.local/bin"
    printf '#!/bin/sh\n' > "$HOME/.local/bin/python3.11"; chmod +x "$HOME/.local/bin/python3.11"
    fakebin="$TEST_DIR/fakebin2"; mkdir -p "$fakebin"
    printf '#!/bin/sh\n' > "$fakebin/python3"; chmod +x "$fakebin/python3"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON= PATH="$fakebin" run pick_python
    [ "$output" = "$HOME/.local/bin/python3.11" ]
}

@test "pick_python: falls back to plain python3 when no 3.1x exists anywhere" {
    fakebin="$TEST_DIR/fakebin3"; mkdir -p "$fakebin"
    printf '#!/bin/sh\n' > "$fakebin/python3"; chmod +x "$fakebin/python3"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON= PATH="$fakebin" run pick_python
    [ "$output" = "$fakebin/python3" ]
}

# ─── pick_python: the SDK venv names the interpreter; the newest install is only the fallback ────
# A stray `uv python install 3.14` put a python3.14 into ~/.local/bin, and the next kernel respawn
# ran on it while the venv's compiled extensions were still 3.12's: every SDK session died at
# import with a message blaming a missing install (2026-09-06). The venv's pyvenv.cfg records the
# interpreter it was built with, so a box with a venv runs THAT; newest-first is for boxes without one.

write_venv_cfg() {   # $1 = state root, then the pyvenv.cfg lines
    local root="$1"; shift
    mkdir -p "$root/sdkvenv"
    printf '%s\n' "$@" > "$root/sdkvenv/pyvenv.cfg"
}

@test "pick_python: a venv's recorded interpreter (executable key) beats a newer python on PATH" {
    fakebin="$TEST_DIR/fakebin-venv"; mkdir -p "$fakebin" "$TEST_DIR/venvpy"
    printf '#!/bin/sh\n' > "$fakebin/python3.14"; chmod +x "$fakebin/python3.14"
    printf '#!/bin/sh\n' > "$TEST_DIR/venvpy/python3.12"; chmod +x "$TEST_DIR/venvpy/python3.12"
    write_venv_cfg "$XDG_STATE_HOME/romp" "home = $TEST_DIR/venvpy" "version = 3.12.3" \
        "executable = $TEST_DIR/venvpy/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON= PATH="$fakebin" run pick_python
    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_DIR/venvpy/python3.12" ]
}

@test "pick_python: an older venv with only home + version still names its interpreter" {
    # python < 3.11 wrote no `executable =` line; home + version reach the same binary.
    fakebin="$TEST_DIR/fakebin-venv2"; mkdir -p "$fakebin" "$TEST_DIR/venvpy2"
    printf '#!/bin/sh\n' > "$fakebin/python3.14"; chmod +x "$fakebin/python3.14"
    printf '#!/bin/sh\n' > "$TEST_DIR/venvpy2/python3.10"; chmod +x "$TEST_DIR/venvpy2/python3.10"
    write_venv_cfg "$XDG_STATE_HOME/romp" "home = $TEST_DIR/venvpy2" "include-system-site-packages = false" \
        "version = 3.10.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON= PATH="$fakebin" run pick_python
    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_DIR/venvpy2/python3.10" ]
}

@test "pick_python: ROMP_STATE_DIR is where the venv is looked for" {
    fakebin="$TEST_DIR/fakebin-venv3"; mkdir -p "$fakebin" "$TEST_DIR/venvpy3"
    printf '#!/bin/sh\n' > "$fakebin/python3.14"; chmod +x "$fakebin/python3.14"
    printf '#!/bin/sh\n' > "$TEST_DIR/venvpy3/python3.12"; chmod +x "$TEST_DIR/venvpy3/python3.12"
    write_venv_cfg "$TEST_DIR/altstate" "home = $TEST_DIR/venvpy3" "version = 3.12.3" \
        "executable = $TEST_DIR/venvpy3/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON= ROMP_STATE_DIR="$TEST_DIR/altstate" PATH="$fakebin" run pick_python
    [ "$output" = "$TEST_DIR/venvpy3/python3.12" ]
}

@test "pick_python: a venv whose interpreter is gone falls back to newest-first and SAYS so" {
    fakebin="$TEST_DIR/fakebin-gone"; mkdir -p "$fakebin"
    printf '#!/bin/sh\n' > "$fakebin/python3.13"; chmod +x "$fakebin/python3.13"
    write_venv_cfg "$XDG_STATE_HOME/romp" "home = $TEST_DIR/no-such-dir" "version = 3.12.3" \
        "executable = $TEST_DIR/no-such-dir/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    # stderr to a file rather than `run --separate-stderr`: that flag needs mktemp, and PATH is bare here.
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    err="$(cat "$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.13" ]
    [[ "$err" == *"$TEST_DIR/no-such-dir/python3.12"* ]]    # names the interpreter it could not run
    [[ "$err" == *"romp-sdk-setup"* ]]                       # and the way to make the venv match again
}

@test "pick_python: a venv with a broken interpreter (present, will not run) also falls back" {
    fakebin="$TEST_DIR/fakebin-broken"; mkdir -p "$fakebin" "$TEST_DIR/brokenpy"
    printf '#!/bin/sh\n' > "$fakebin/python3.13"; chmod +x "$fakebin/python3.13"
    printf '#!/bin/sh\nexit 127\n' > "$TEST_DIR/brokenpy/python3.12"; chmod +x "$TEST_DIR/brokenpy/python3.12"
    write_venv_cfg "$XDG_STATE_HOME/romp" "executable = $TEST_DIR/brokenpy/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    err="$(cat "$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.13" ]
    [[ "$err" == *"$TEST_DIR/brokenpy/python3.12"* ]]
}

@test "pick_python: no venv means newest-first, silently (a fresh box before romp-sdk-setup)" {
    fakebin="$TEST_DIR/fakebin-fresh"; mkdir -p "$fakebin"
    printf '#!/bin/sh\n' > "$fakebin/python3.13"; chmod +x "$fakebin/python3.13"
    printf '#!/bin/sh\n' > "$fakebin/python3.12"; chmod +x "$fakebin/python3.12"
    [ ! -e "$XDG_STATE_HOME/romp/sdkvenv" ]
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.13" ]
    [ ! -s "$TEST_DIR/stderr" ]
}

@test "pick_python: ROMP_PYTHON wins over the venv's recorded interpreter too" {
    mkdir -p "$TEST_DIR/venvpy4" "$TEST_DIR/custom"
    printf '#!/bin/sh\n' > "$TEST_DIR/venvpy4/python3.12"; chmod +x "$TEST_DIR/venvpy4/python3.12"
    printf '#!/bin/sh\n' > "$TEST_DIR/custom/python";       chmod +x "$TEST_DIR/custom/python"
    write_venv_cfg "$XDG_STATE_HOME/romp" "executable = $TEST_DIR/venvpy4/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON="$TEST_DIR/custom/python" run pick_python
    [ "$output" = "$TEST_DIR/custom/python" ]
}

@test "pick_python: romp-serve and romp-sdk-setup carry the SAME picker (venv must match the kernel)" {
    diff <(sed -n '/^pick_python()/,/^}/p' "$ROMP_SERVE") \
         <(sed -n '/^pick_python()/,/^}/p' "$BIN/romp-sdk-setup")
}

# ─── pick_python: the pin is checked, and the candidates are checked (review of the 2026-09-06 fix) ──
# A fake interpreter that claims one X.Y: exits 0 for the version check naming it, 1 for any other
# version check, 0 for `-c pass`. The bare `printf '#!/bin/sh\n'` fakes above answer every check with 0.
fake_python() {   # $1 path, $2 the X.Y it claims
    mkdir -p "$(dirname "$1")"
    printf '#!/bin/sh\ncase "$*" in *"(%s, %s)"*) exit 0 ;; *version_info*) exit 1 ;; esac\nexit 0\n' \
        "${2%%.*}" "${2#*.}" > "$1"
    chmod +x "$1"
}

@test "pick_python: ROMP_PYTHON naming a missing path is refused with the pin named, not bash's own error" {
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON="$TEST_DIR/no-such/python3.12" run pick_python
    [ "$status" -eq 1 ]
    [[ "$output" == *"ROMP_PYTHON=$TEST_DIR/no-such/python3.12"* ]]
    [[ "$output" == *"not an executable interpreter"* ]]
    [[ "$output" == *"service.env"* ]]                        # where a pin usually lives
}

@test "pick_python: ROMP_PYTHON naming a file that is not executable is refused the same way" {
    mkdir -p "$TEST_DIR/pin"; printf '#!/bin/sh\n' > "$TEST_DIR/pin/python3.12"     # no chmod +x
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON="$TEST_DIR/pin/python3.12" run pick_python
    [ "$status" -eq 1 ]
    [[ "$output" == *"not an executable interpreter"* ]]
    ROMP_PYTHON="$TEST_DIR/pin" run pick_python                # a directory is not one either
    [ "$status" -eq 1 ]
}

@test "pick_python: ROMP_PYTHON as a bare command name resolves on PATH and is echoed as given" {
    fakebin="$TEST_DIR/fakebin-pin"; mkdir -p "$fakebin"
    printf '#!/bin/sh\n' > "$fakebin/python3.12"; chmod +x "$fakebin/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    ROMP_PYTHON=python3.12 PATH="$fakebin" run pick_python
    [ "$status" -eq 0 ]
    [ "$output" = "python3.12" ]
    ROMP_PYTHON=python3.99 PATH="$fakebin" run pick_python
    [ "$status" -eq 1 ]
    [[ "$output" == *"ROMP_PYTHON=python3.99"* ]]
}

@test "romp-serve: a bad ROMP_PYTHON stops the launch with one romp line, and the kernel never starts" {
    # End to end. Before the check romp-serve died at its exec with bash's "No such file or directory"
    # (exit 127, no mention of the pin), and the manager respawned it every few seconds.
    ROMP_PYTHON="$TEST_DIR/no-such/python3.12" run "$ROMP_SERVE" --port 9999
    [ "$status" -eq 1 ]
    [[ "$output" == *"ROMP_PYTHON=$TEST_DIR/no-such/python3.12"* ]]
    [[ "$output" != *"No such file or directory"* ]]
    [[ "$output" != *"PORT="* ]]                              # the stub kernel never ran
}

@test "pick_python: a home/python3 that is no longer the recorded X.Y is NOT taken silently" {
    # Stdlib venvs on Debian/Ubuntu record `home = /usr/bin` and a version, no executable. A distro
    # upgrade removes python3.12 and repoints /usr/bin/python3 at 3.14: that path is present and runs,
    # and taking it put the kernel on the wrong minor with no line saying so.
    fakebin="$TEST_DIR/fakebin-upg"; mkdir -p "$fakebin"
    fake_python "$fakebin/python3.14" 3.14
    fake_python "$TEST_DIR/upg/python3" 3.14                  # home/python3, another minor now
    write_venv_cfg "$XDG_STATE_HOME/romp" "home = $TEST_DIR/upg" "version = 3.12.3"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    err="$(cat "$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.14" ]                        # newest-first, since no 3.12 is left anywhere
    [[ "$err" == *"$TEST_DIR/upg/python3.12"* ]]              # names what the venv was built with
    [[ "$err" == *"romp-sdk-setup"* ]]                        # and that the venv must be rebuilt for the pick
}

@test "pick_python: a home/python3 that IS the recorded X.Y is taken, silently (the check rejects only a mismatch)" {
    fakebin="$TEST_DIR/fakebin-same"; mkdir -p "$fakebin"
    fake_python "$fakebin/python3.14" 3.14
    fake_python "$TEST_DIR/same/python3" 3.12
    write_venv_cfg "$XDG_STATE_HOME/romp" "home = $TEST_DIR/same" "version = 3.12.3"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    [ "$out" = "$TEST_DIR/same/python3" ]
    [ ! -s "$TEST_DIR/stderr" ]
}

@test "pick_python: the recorded binary itself is checked against the recorded X.Y" {
    fakebin="$TEST_DIR/fakebin-exe"; mkdir -p "$fakebin"
    fake_python "$fakebin/python3.14" 3.14
    fake_python "$TEST_DIR/exe/python3" 3.14                  # `executable` kept its path, changed its minor
    write_venv_cfg "$XDG_STATE_HOME/romp" "version = 3.12.3" "executable = $TEST_DIR/exe/python3"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.14" ]
    [ -s "$TEST_DIR/stderr" ]
}

@test "pick_python: when the recorded interpreter is gone, another python of the SAME minor beats newest-first" {
    # `executable` is a realpath into a patch-versioned install root, which a patch upgrade removes
    # while python3.12 on PATH still runs. The venv's site-packages are valid for it, so nothing needs
    # rebuilding, and the kernel must not move to 3.14 for want of looking.
    fakebin="$TEST_DIR/fakebin-minor"; mkdir -p "$fakebin"
    fake_python "$fakebin/python3.14" 3.14
    fake_python "$fakebin/python3.12" 3.12
    write_venv_cfg "$XDG_STATE_HOME/romp" "version = 3.12.4" "executable = $TEST_DIR/gone/3.12.4/bin/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    err="$(cat "$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.12" ]
    [[ "$err" == *"$TEST_DIR/gone/3.12.4/bin/python3.12"* ]]  # what it could not run
    [[ "$err" == *"using $fakebin/python3.12"* ]]             # and what it used instead
    [[ "$err" != *"romp-sdk-setup"* ]]                        # no rebuild is needed
}

@test "pick_python: the same-minor fallback also looks in ~/.local/bin" {
    fakebin="$TEST_DIR/fakebin-minor2"; mkdir -p "$fakebin"
    fake_python "$fakebin/python3.14" 3.14
    fake_python "$HOME/.local/bin/python3.12" 3.12
    write_venv_cfg "$XDG_STATE_HOME/romp" "version = 3.12.4" "executable = $TEST_DIR/gone/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    [ "$out" = "$HOME/.local/bin/python3.12" ]
}

@test "pick_python: a python3.12 on PATH that is not actually 3.12 is skipped by the same-minor fallback" {
    fakebin="$TEST_DIR/fakebin-liar"; mkdir -p "$fakebin"
    fake_python "$fakebin/python3.14" 3.14
    fake_python "$fakebin/python3.12" 3.14                    # a shim named for one minor, running another
    write_venv_cfg "$XDG_STATE_HOME/romp" "version = 3.12.4" "executable = $TEST_DIR/gone/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    err="$(cat "$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.14" ]
    [[ "$err" == *"romp-sdk-setup"* ]]
}

@test "pick_python: a cfg with a home but no version line offers no home candidate (a bare python is python2 on many boxes)" {
    fakebin="$TEST_DIR/fakebin-py2"; mkdir -p "$fakebin" "$TEST_DIR/py2home"
    fake_python "$fakebin/python3.14" 3.14
    printf '#!/bin/sh\n' > "$TEST_DIR/py2home/python"; chmod +x "$TEST_DIR/py2home/python"   # runs, answers 0
    write_venv_cfg "$XDG_STATE_HOME/romp" "home = $TEST_DIR/py2home" "include-system-site-packages = false"
    eval "$(extract_pick "$ROMP_SERVE")"
    out="$(ROMP_PYTHON= PATH="$fakebin" pick_python 2>"$TEST_DIR/stderr")"
    [ "$out" = "$fakebin/python3.14" ]
    [ -s "$TEST_DIR/stderr" ]                                 # and it is not silent about the venv
}

@test "pick_python: a recorded interpreter that hangs counts as not runnable (bounded by timeout where coreutils has it)" {
    command -v timeout >/dev/null 2>&1 || skip "no coreutils timeout on this box"
    fakebin="$TEST_DIR/fakebin-hang"; mkdir -p "$fakebin" "$TEST_DIR/tbin" "$TEST_DIR/hang"
    ln -s "$(command -v timeout)" "$TEST_DIR/tbin/timeout"    # the one real tool the picker may use
    fake_python "$fakebin/python3.14" 3.14
    printf '#!/bin/sh\nexec /bin/sleep 30\n' > "$TEST_DIR/hang/python3.12"; chmod +x "$TEST_DIR/hang/python3.12"
    write_venv_cfg "$XDG_STATE_HOME/romp" "version = 3.12.4" "executable = $TEST_DIR/hang/python3.12"
    eval "$(extract_pick "$ROMP_SERVE")"
    local t0=$SECONDS
    out="$(ROMP_PYTHON= PATH="$fakebin:$TEST_DIR/tbin" pick_python 2>"$TEST_DIR/stderr")"
    err="$(cat "$TEST_DIR/stderr")"
    [ $((SECONDS - t0)) -lt 20 ]                              # bounded: the fake would have slept 30 s
    [ "$out" = "$fakebin/python3.14" ]
    [[ "$err" == *"$TEST_DIR/hang/python3.12"* ]]
}
