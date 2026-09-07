#!/usr/bin/env bats

# romp-uninstall and the tracked-changes tooling when the clone install.sh ran from has MOVED or is
# GONE. install.sh links ~/.claude/hooks/track-*.mjs and ~/.claude/skills/tracked-changes into the
# clone's vendor/track-changents/ and registers the guard as a PreToolUse hook; the uninstaller judges
# each by where it resolves. After `mv romp-a romp-b` every link dangles, and a dangling link resolves
# to its OLD target — never into the new clone's copy — so a resolve-only rule reads romp's own
# leftovers as someone else's install and keeps them, guard entry included: from then on every
# Write/Edit in every Claude Code session runs a hook whose file is gone. The rule here: a link or
# entry that leads to a path which no longer exists, under some vendor/track-changents/, is romp's
# (only romp links into such a directory, and a dangling link is nobody's live install). A dangling
# link into anything ELSE is still left alone.
# Hermetic: HOME is a temp dir; the login service, extension and SDK steps are opted out.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# A throwaway clone the REAL install.sh can run from, at $1: install.sh reads the clone it lives in,
# so a copy of it there, next to a bin/romp it can see, installs THAT clone — and the links it writes
# name that clone's vendor/track-changents/. vendor/ is a symlink to the real one (never a copy: the
# uninstaller must not write under vendor/, and this would show it). Never the repo copy of either
# script: romp-uninstall tears down the login service and kills the manager of the clone it lives
# in, and that would be the developer's live romp (it was, 2026-07-27).
throwaway_clone() {
    local clone="$1"
    mkdir -p "$clone/bin" "$clone/vscode-extension"
    cp "$ROMP_DIR/install.sh" "$clone/install.sh"
    cp "$ROMP_DIR/bin/romp-uninstall" "$clone/bin/romp-uninstall"
    chmod +x "$clone/install.sh" "$clone/bin/romp-uninstall"
    ln -s "$ROMP_DIR/bin/romp" "$clone/bin/romp"
    ln -s "$ROMP_DIR/vendor" "$clone/vendor"
    cat > "$clone/bin/romp-service" <<EOF
#!/usr/bin/env bash
echo "romp-service \$* (stub)" >> "$TEST_DIR/service.log"
EOF
    chmod +x "$clone/bin/romp-service"
}

setup() {
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
    export ROMP_NO_SERVICE=1 ROMP_NO_EXT=1 ROMP_NO_SDK=1
    export ROMP_INSTALL_TOKEN_TRIES=1
    export ROMP_GITHOOK_DIR="$TEST_DIR/githooks"
    export ROMP_STATE_DIR="$TEST_DIR/state"
    mkdir -p "$ROMP_STATE_DIR"
    # The clone install.sh runs from, and a second one that stays put.
    A="$TEST_DIR/romp-a"
    throwaway_clone "$A"
    CLONE="$TEST_DIR/clone"
    throwaway_clone "$CLONE"
}

teardown() { rm -rf "$TEST_DIR"; }

TC_LINKS="track-edit.mjs track-comment.mjs track-reply.mjs track-config.mjs track-guard.mjs"

guard_entries() {   # the command of every track-guard.mjs entry, across all events
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
try:
    s = json.load(open(sys.argv[1]))
except (IOError, OSError, ValueError):
    raise SystemExit
for rules in (s.get("hooks") or {}).values():
    for r in rules:
        for h in r.get("hooks", []):
            if h.get("command", "").endswith("track-guard.mjs"):
                print(h["command"])
PY
}

has_pretooluse() {
    python3 -c 'import json, sys; print("PreToolUse" in (json.load(open(sys.argv[1])).get("hooks") or {}))' \
        "$HOME/.claude/settings.json"
}

set_guard_command() {   # rewrite the one guard entry's command string
    python3 - "$HOME/.claude/settings.json" "$1" <<'PY'
import json, sys
p, cmd = sys.argv[1], sys.argv[2]
s = json.load(open(p))
for rules in s["hooks"].values():
    for r in rules:
        for h in r.get("hooks", []):
            if h.get("command", "").endswith("track-guard.mjs"):
                h["command"] = cmd
json.dump(s, open(p, "w"), indent=2)
PY
}

assert_dangling() {   # a symlink whose target is gone
    [ -L "$1" ]
    [ ! -e "$1" ]
}

foreign_install() {   # the shape track-changents' own installer leaves behind, in $TEST_DIR/track-changents
    OTHER="$TEST_DIR/track-changents"
    mkdir -p "$OTHER/cli" "$OTHER/hooks" "$OTHER/skill" "$HOME/.claude/hooks" "$HOME/.claude/skills"
    for tc in track-edit track-comment track-reply track-config; do
        echo "// theirs" > "$OTHER/cli/$tc.mjs"
        ln -s "$OTHER/cli/$tc.mjs" "$HOME/.claude/hooks/$tc.mjs"
    done
    echo "// theirs" > "$OTHER/hooks/track-guard.mjs"
    ln -s "$OTHER/hooks/track-guard.mjs" "$HOME/.claude/hooks/track-guard.mjs"
    echo "# theirs" > "$OTHER/skill/SKILL.md"
    ln -s "$OTHER/skill" "$HOME/.claude/skills/tracked-changes"
    cat > "$HOME/.claude/settings.json" <<JSON
{ "hooks": { "PreToolUse": [ { "matcher": "Write|Edit|MultiEdit",
    "hooks": [ { "type": "command", "command": "$HOME/.claude/hooks/track-guard.mjs", "timeout": 10 } ] } ] } }
JSON
}

@test "romp-uninstall: a clone MOVED since install still removes its tracked-changes links and guard entry" {
    run "$A/install.sh"
    [ "$status" -eq 0 ]
    [ "$(readlink "$HOME/.claude/hooks/track-guard.mjs")" = "$A/vendor/track-changents/hooks/track-guard.mjs" ]
    [ "$(guard_entries)" = "~/.claude/hooks/track-guard.mjs" ]

    B="$TEST_DIR/romp-b"
    mv "$A" "$B"
    # The premise: every link now dangles, and resolves to the OLD clone's path.
    for tc in $TC_LINKS; do assert_dangling "$HOME/.claude/hooks/$tc"; done
    assert_dangling "$HOME/.claude/skills/tracked-changes"

    run "$B/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"removed 6 links into vendor/track-changents/"* ]]
    [[ "$output" == *"6 of them led into a vendor/track-changents/ which no longer exists"* ]]
    [[ "$output" == *"de-registered a track-guard.mjs entry that led into a vendor/track-changents/ which no longer exists"* ]]
    [[ "$output" != *"left alone"* ]]
    for tc in $TC_LINKS; do
        [ ! -e "$HOME/.claude/hooks/$tc" ]
        [ ! -L "$HOME/.claude/hooks/$tc" ]
    done
    [ ! -e "$HOME/.claude/skills/tracked-changes" ]
    [ ! -L "$HOME/.claude/skills/tracked-changes" ]
    [ -z "$(guard_entries)" ]
    [ "$(has_pretooluse)" = "False" ]
    # The vendored copy the links once resolved to is untouched.
    [ -f "$ROMP_DIR/vendor/track-changents/hooks/track-guard.mjs" ]
    [ -f "$ROMP_DIR/vendor/track-changents/skill/SKILL.md" ]
}

@test "romp-uninstall: a clone DELETED since install is cleaned up by another clone's uninstall, expanded-path entry included" {
    run "$A/install.sh"
    [ "$status" -eq 0 ]
    # The entry as track-changents' own installer writes it (install.sh keeps such an entry rather than
    # doubling it): the expanded home path, judged by where the link under it leads.
    set_guard_command "$HOME/.claude/hooks/track-guard.mjs"
    rm -rf "$A"
    for tc in $TC_LINKS; do assert_dangling "$HOME/.claude/hooks/$tc"; done

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"6 of them led into a vendor/track-changents/ which no longer exists"* ]]
    [[ "$output" == *"de-registered a track-guard.mjs entry that led into a vendor/track-changents/ which no longer exists — a romp clone moved or deleted since install ($HOME/.claude/hooks/track-guard.mjs)"* ]]
    [[ "$output" != *"left alone"* ]]
    for tc in $TC_LINKS; do [ ! -L "$HOME/.claude/hooks/$tc" ]; done
    [ ! -L "$HOME/.claude/skills/tracked-changes" ]
    [ -z "$(guard_entries)" ]
    [ "$(has_pretooluse)" = "False" ]
}

@test "romp-uninstall: a 'node <path>' guard entry naming a deleted clone's vendored file directly goes too" {
    run "$A/install.sh"
    [ "$status" -eq 0 ]
    # No link in between: the entry names the vendored file itself, the form install.sh's presence
    # check also honours. Only the resolved path is there to judge.
    set_guard_command "node $A/vendor/track-changents/hooks/track-guard.mjs"
    rm -rf "$A"

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [ -z "$(guard_entries)" ]
    [ "$(has_pretooluse)" = "False" ]
    [[ "$output" == *"de-registered a track-guard.mjs entry that led into a vendor/track-changents/ which no longer exists"* ]]
}

@test "romp-uninstall: a dangling link into a DELETED track-changents checkout is not romp's and stays, with a notice" {
    # The other installer's shape, its checkout gone: the links dangle, but nowhere near a
    # vendor/track-changents/, so the moved-clone rule must not claim them.
    foreign_install
    rm -rf "$OTHER"
    for tc in $TC_LINKS; do assert_dangling "$HOME/.claude/hooks/$tc"; done

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"no links into this clone's vendor/track-changents/"* ]]
    [[ "$output" != *"no longer exists"* ]]
    [[ "$output" == *"left alone: ~/.claude/hooks/track-guard.mjs points outside this clone ($OTHER/hooks/track-guard.mjs)"* ]]
    [[ "$output" == *"left alone: ~/.claude/skills/tracked-changes points outside this clone ($OTHER/skill)"* ]]
    [[ "$output" == *"left alone: a track-guard.mjs entry that points outside this clone ($HOME/.claude/hooks/track-guard.mjs)"* ]]
    for tc in $TC_LINKS; do [ -L "$HOME/.claude/hooks/$tc" ]; done
    [ -L "$HOME/.claude/skills/tracked-changes" ]
    [ "$(guard_entries)" = "$HOME/.claude/hooks/track-guard.mjs" ]
}

@test "romp-uninstall: a LIVE install from another clone is still left alone (the moved-clone rule needs a missing target)" {
    # Two clones, both present; install.sh ran from the other one. Its links resolve to a real file
    # that is not under THIS clone's vendor/ (a real copy, not a link to the shared one), so they are
    # a live install of another clone and stay — the rule fires only when the target is gone.
    rm "$A/vendor"
    mkdir -p "$A/vendor"
    cp -R "$ROMP_DIR/vendor/track-changents" "$A/vendor/track-changents"
    run "$A/install.sh"
    [ "$status" -eq 0 ]
    for tc in $TC_LINKS; do [ -e "$HOME/.claude/hooks/$tc" ]; done

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"no links into this clone's vendor/track-changents/"* ]]
    [[ "$output" == *"left alone: ~/.claude/hooks/track-guard.mjs points outside this clone ($A/vendor/track-changents/hooks/track-guard.mjs)"* ]]
    [[ "$output" == *"left alone: a track-guard.mjs entry that points outside this clone (~/.claude/hooks/track-guard.mjs)"* ]]
    for tc in $TC_LINKS; do [ -L "$HOME/.claude/hooks/$tc" ]; done
    [ "$(guard_entries)" = "~/.claude/hooks/track-guard.mjs" ]
}
