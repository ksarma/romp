#!/usr/bin/env bats

# romp-uninstall and the guard's settings.json entry when the link under it is already GONE — not
# dangling, gone: nothing at ~/.claude/hooks/track-guard.mjs at all, because the link was removed by
# hand or ~/.claude/hooks/ was deleted before this ran. The uninstaller judges a guard entry by where
# the path it names resolves, and a path with nothing at it resolves to itself: not under this clone's
# vendor/track-changents/, not a dangling link into one. A resolve-only rule read install.sh's own
# entry as someone else's and kept it, with a notice that it "points outside this clone" — and from
# then on every Write/Edit in every Claude Code session ran a command that does not exist, the exact
# outcome the uninstaller exists to prevent. The rule here: with nothing at the path, the command
# string is the only evidence, and "~/.claude/hooks/track-guard.mjs" is the exact string install.sh
# writes and track-changents' own installer never does (it writes the expanded home path). That entry
# is romp's and goes. Any other form with nothing at its path is not romp's to drop and stays — with a
# notice that says what is wrong (the path does not exist), not that it points somewhere else.
# Hermetic: HOME is a temp dir; the login service, extension and SDK steps are opted out.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# Never the repo copy of the uninstaller: it tears down the login service and kills the manager of
# the clone it lives in, and that would be the developer's live romp (it was, 2026-07-27). A
# throwaway clone holds the real script, a stubbed romp-service, and a vendor/ that resolves to the
# real one (a symlink, never a copy: the uninstaller must not write under vendor/).
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

setup() {
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
    export ROMP_NO_SERVICE=1 ROMP_NO_EXT=1 ROMP_NO_SDK=1
    export ROMP_INSTALL_TOKEN_TRIES=1
    export ROMP_GITHOOK_DIR="$TEST_DIR/githooks"
    export ROMP_STATE_DIR="$TEST_DIR/state"
    mkdir -p "$ROMP_STATE_DIR"
    fake_clone
}

teardown() { rm -rf "$TEST_DIR"; }

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

hook_count() {   # how many romp hook commands are left registered across all events
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
try:
    s = json.load(open(sys.argv[1]))
except (IOError, OSError, ValueError):
    print(0); raise SystemExit
OURS = ("tmux-status.sh", "romp-summarize.sh", "romp-postal-drain.sh", "romp-postal-ensure.sh",
        "romp-postal-revive.sh", "romp-postal-context.sh", "romp-wake.sh")
n = sum(1 for rules in (s.get("hooks") or {}).values() for r in rules for h in r.get("hooks", [])
        if h.get("command", "").rsplit("/", 1)[-1] in OURS)
print(n)
PY
}

write_guard_settings() {   # a settings.json holding ONE guard entry, with the given command string
    mkdir -p "$HOME/.claude"
    python3 - "$HOME/.claude/settings.json" "$1" <<'PY'
import json, sys
p, cmd = sys.argv[1], sys.argv[2]
s = {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|MultiEdit",
                               "hooks": [{"type": "command", "command": cmd, "timeout": 10}]}]}}
json.dump(s, open(p, "w"), indent=2)
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
    write_guard_settings "$HOME/.claude/hooks/track-guard.mjs"
}

GONE_NOTICE="de-registered a track-guard.mjs entry with nothing at the path it names"
MISSING_NOTICE="left alone: a track-guard.mjs entry that names a path where nothing exists"

@test "romp-uninstall: install.sh's guard entry goes when its link was removed by hand before the uninstall" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -L "$HOME/.claude/hooks/track-guard.mjs" ]
    [ "$(guard_entries)" = "~/.claude/hooks/track-guard.mjs" ]

    # The premise: nothing at the path. Not a dangling link — no link at all.
    rm "$HOME/.claude/hooks/track-guard.mjs"
    [ ! -L "$HOME/.claude/hooks/track-guard.mjs" ]
    [ ! -e "$HOME/.claude/hooks/track-guard.mjs" ]

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [ -z "$(guard_entries)" ]
    [ "$(has_pretooluse)" = "False" ]
    [[ "$output" == *"$GONE_NOTICE"*"(~/.claude/hooks/track-guard.mjs)"* ]]
    [[ "$output" != *"left alone"* ]]
    [[ "$output" != *"points outside this clone"* ]]
    # The other five links were still there and still romp's.
    [[ "$output" == *"removed 5 links into vendor/track-changents/"* ]]
    for tc in track-edit track-comment track-reply track-config; do
        [ ! -L "$HOME/.claude/hooks/$tc.mjs" ]
    done
    [ ! -L "$HOME/.claude/skills/tracked-changes" ]
    # The vendored copy is untouched.
    [ -f "$ROMP_DIR/vendor/track-changents/hooks/track-guard.mjs" ]

    # Idempotent: a second run finds nothing and says so, with no notice about anything left.
    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"no romp hook entries registered"* ]]
    [[ "$output" != *"left alone"* ]]
    [[ "$output" != *"track-guard.mjs"* ]]
}

@test "romp-uninstall: install.sh's guard entry goes when ~/.claude/hooks/ was deleted wholesale" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ "$(hook_count)" -gt 0 ]
    [ "$(guard_entries)" = "~/.claude/hooks/track-guard.mjs" ]

    rm -rf "$HOME/.claude/hooks"
    [ ! -e "$HOME/.claude/hooks" ]

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [ -z "$(guard_entries)" ]
    [ "$(has_pretooluse)" = "False" ]
    [ "$(hook_count)" -eq 0 ]
    [[ "$output" == *"$GONE_NOTICE"* ]]
    [[ "$output" != *"left alone"* ]]
    # Nothing of the tooling is left to mention in settings.json.
    run grep -c 'track-guard\|track-changents\|PreToolUse' "$HOME/.claude/settings.json"
    [ "$output" = "0" ]
}

@test "romp-uninstall: an entry in the OTHER installer's form with nothing at its path stays, and the notice says the path does not exist" {
    # track-changents' own installer writes the expanded home path. With the link under it gone there
    # is no target to judge and the string is not install.sh's, so the entry is not romp's to drop —
    # but "points outside this clone" would describe a path that leads nowhere as a live install.
    foreign_install
    rm "$HOME/.claude/hooks/track-guard.mjs"

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [ "$(guard_entries)" = "$HOME/.claude/hooks/track-guard.mjs" ]
    [ "$(has_pretooluse)" = "True" ]
    [[ "$output" == *"$MISSING_NOTICE"*"($HOME/.claude/hooks/track-guard.mjs)"* ]]
    [[ "$output" != *"a track-guard.mjs entry that points outside this clone"* ]]
    [[ "$output" != *"$GONE_NOTICE"* ]]
    # The rest of that install is untouched: live links into its checkout, reported as before.
    for tc in track-edit track-comment track-reply track-config; do
        [ "$(readlink "$HOME/.claude/hooks/$tc.mjs")" = "$OTHER/cli/$tc.mjs" ]
    done
    [[ "$output" == *"left alone: ~/.claude/hooks/track-edit.mjs points outside this clone"* ]]
}

@test "romp-uninstall: a 'node <path>' entry naming a file that does not exist, outside any vendor/track-changents/, stays with the same notice" {
    write_guard_settings "node $TEST_DIR/elsewhere/hooks/track-guard.mjs"
    [ ! -e "$TEST_DIR/elsewhere" ]

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [ "$(guard_entries)" = "node $TEST_DIR/elsewhere/hooks/track-guard.mjs" ]
    [[ "$output" == *"$MISSING_NOTICE"*"(node $TEST_DIR/elsewhere/hooks/track-guard.mjs)"* ]]
    [[ "$output" != *"a track-guard.mjs entry that points outside this clone"* ]]
    [[ "$output" != *"$GONE_NOTICE"* ]]
}

@test "romp-uninstall: the tilde form with a link PRESENT into another checkout is still judged by the link, not the string" {
    # The string-only rule applies ONLY when nothing is at the path. With a link there, where it
    # points decides — a tilde-form entry over a link into a track-changents checkout stays.
    foreign_install
    write_guard_settings "~/.claude/hooks/track-guard.mjs"

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [ "$(guard_entries)" = "~/.claude/hooks/track-guard.mjs" ]
    [ "$(readlink "$HOME/.claude/hooks/track-guard.mjs")" = "$OTHER/hooks/track-guard.mjs" ]
    [[ "$output" == *"left alone: a track-guard.mjs entry that points outside this clone (~/.claude/hooks/track-guard.mjs)"* ]]
    [[ "$output" != *"$GONE_NOTICE"* ]]
    [[ "$output" != *"$MISSING_NOTICE"* ]]
}
