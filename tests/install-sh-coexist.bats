#!/usr/bin/env bats

# install.sh alongside what is ALREADY on the machine: hook entries another tool or the user
# registered, and a track-changents install from that project's own checkout. Two rules are pinned
# here, both about the settings.json registrar's presence check and the tooling links:
#   - romp's own hooks are judged by the exact "~/.claude/hooks/<name>" string install.sh writes
#     (the string bin/romp-uninstall drops). A same-named script registered from some other path,
#     or named as an ARGUMENT of a user's wrapper, is someone else's and never stands in for ours:
#     taking it for ours would leave romp's hook silently unregistered. Only the tracked-changes
#     guard, which track-changents' own installer also registers (expanded home path), is judged by
#     basename, and there every whitespace token of the command counts.
#   - taking over another track-changents install's links is reported together with what
#     romp-uninstall will later do with them and how to get that install back, because the links
#     now resolve into this clone and the uninstaller removes them as romp's own.
# Hermetic like tests/install-sh.bats: HOME is a temp dir; the service, extension and SDK steps
# are opted out.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
    export ROMP_NO_SERVICE=1 ROMP_NO_EXT=1 ROMP_NO_SDK=1
    export ROMP_INSTALL_TOKEN_TRIES=1
    export ROMP_GITHOOK_DIR="$TEST_DIR/githooks"
    export ROMP_STATE_DIR="$TEST_DIR/state"
    mkdir -p "$ROMP_STATE_DIR"
}

teardown() { rm -rf "$TEST_DIR"; }

event_cmds() {   # every command registered under one event, one per line, in order
    python3 - "$HOME/.claude/settings.json" "$1" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
for g in s.get("hooks", {}).get(sys.argv[2], []):
    for h in g.get("hooks", []):
        print(h.get("command", ""))
PY
}

count_exact() {   # occurrences of one exact command string under one event
    event_cmds "$1" | grep -cxF -- "$2" || true
}

@test "install.sh: a same-named hook registered from another path does not stand in for romp's own" {
    # A Stop hook that happens to share romp-wake.sh's name, and a user wrapper whose ARGUMENT is
    # named like romp-summarize.sh. Neither is romp's hook; both must be left alone and both of
    # romp's must still be registered.
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "Stop": [ { "hooks": [ { "type": "command", "command": "/opt/tools/romp-wake.sh" } ] } ],
    "UserPromptSubmit": [ { "hooks": [ { "type": "command", "command": "my-wrapper.sh romp-summarize.sh" } ] } ]
  }
}
JSON
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Stop:romp-wake.sh"* ]]
    [[ "$output" == *"UserPromptSubmit:romp-summarize.sh"* ]]
    [ "$(count_exact Stop /opt/tools/romp-wake.sh)" = "1" ]
    [ "$(count_exact Stop '~/.claude/hooks/romp-wake.sh')" = "1" ]
    [ "$(count_exact UserPromptSubmit 'my-wrapper.sh romp-summarize.sh')" = "1" ]
    [ "$(count_exact UserPromptSubmit '~/.claude/hooks/romp-summarize.sh')" = "1" ]

    # The exact string is now present, so a re-run adds nothing and leaves the user's entries as found.
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"already registered"* ]]
    [ "$(count_exact Stop /opt/tools/romp-wake.sh)" = "1" ]
    [ "$(count_exact Stop '~/.claude/hooks/romp-wake.sh')" = "1" ]
    [ "$(count_exact UserPromptSubmit 'my-wrapper.sh romp-summarize.sh')" = "1" ]
    [ "$(count_exact UserPromptSubmit '~/.claude/hooks/romp-summarize.sh')" = "1" ]
}

@test "install.sh: a guard entry in the 'node <path>' form counts as registered, and is left as it was" {
    # The basename rule for the guard reads every whitespace token, the way bin/romp-uninstall's
    # guard_verdict does, so an entry that runs the guard through node is not doubled.
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/settings.json" <<JSON
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit|MultiEdit",
        "hooks": [ { "type": "command", "command": "node $HOME/.claude/hooks/track-guard.mjs", "timeout": 10 } ] }
    ]
  }
}
JSON
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" != *"PreToolUse:track-guard.mjs"* ]]
    [ "$(event_cmds PreToolUse)" = "node $HOME/.claude/hooks/track-guard.mjs" ]
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
assert len(s["hooks"]["PreToolUse"]) == 1, s["hooks"]["PreToolUse"]
PY
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

@test "install.sh: taking over another track-changents install's links says what romp-uninstall will do with them and how to get that install back" {
    foreign_install
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Replaced links from another track-changents install"* ]]
    [[ "$output" == *"romp-uninstall will remove those links and the guard's settings.json entry"* ]]
    [[ "$output" == *"re-run its install.sh"* ]]

    # Nothing was replaced on a second run, so neither line appears.
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" != *"Replaced links"* ]]
    [[ "$output" != *"romp-uninstall will remove"* ]]
}

@test "install.sh: a fresh machine gets no takeover notice" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" != *"Replaced links"* ]]
    [[ "$output" != *"romp-uninstall will remove"* ]]
}

# The uninstaller is never run from the real clone (it tears down the login service and kills the
# manager of the clone it lives in; tests/romp-uninstall.bats explains). A throwaway clone carries
# the real script, a stubbed romp-service, and a vendor/ that resolves to the real one, so install
# and uninstall agree on where the links lead, as they do when both run from one clone.
fake_clone() {
    CLONE="$TEST_DIR/clone"
    mkdir -p "$CLONE/bin" "$CLONE/vscode-extension"
    cp "$ROMP_DIR/bin/romp-uninstall" "$CLONE/bin/romp-uninstall"
    chmod +x "$CLONE/bin/romp-uninstall"
    ln -s "$ROMP_DIR/vendor" "$CLONE/vendor"
    cat > "$CLONE/bin/romp-service" <<EOF
#!/usr/bin/env bash
echo "romp-service \$* (stub)" >> "$TEST_DIR/service.log"
EOF
    chmod +x "$CLONE/bin/romp-service"
}

@test "install.sh then romp-uninstall: the notice holds, the taken-over links and the guard entry go and the checkout stays" {
    foreign_install
    fake_clone
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp-uninstall will remove those links"* ]]

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    for tc in track-edit track-comment track-reply track-config track-guard; do
        [ ! -e "$HOME/.claude/hooks/$tc.mjs" ]
        [ ! -L "$HOME/.claude/hooks/$tc.mjs" ]
    done
    [ ! -e "$HOME/.claude/skills/tracked-changes" ]
    [ ! -L "$HOME/.claude/skills/tracked-changes" ]
    [ -z "$(event_cmds PreToolUse)" ]
    # The checkout the notice points the user back to is intact, byte for byte.
    [ "$(cat "$OTHER/cli/track-edit.mjs")" = "// theirs" ]
    [ "$(cat "$OTHER/hooks/track-guard.mjs")" = "// theirs" ]
    [ "$(cat "$OTHER/skill/SKILL.md")" = "# theirs" ]
}
