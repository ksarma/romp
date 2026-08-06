#!/usr/bin/env bats

# romp-uninstall must leave the machine looking un-installed, so a from-scratch reinstall really is
# from scratch — and must do it WITHOUT collateral damage to the user's own Claude Code config.
# Hermetic: HOME is a temp dir; the login service and network steps are opted out.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# The uninstaller is NEVER run from the real clone here. It tears down the login service and kills
# the manager, and its ROMP_DIR comes from its own $0 — so running the repo copy would take down the
# developer's live romp mid-test-suite (it did, 2026-07-27). Instead each test gets a THROWAWAY clone:
# the real script, a stubbed romp-service, and disposable build artifacts. Everything the uninstaller
# does to $HOME is still exercised for real, because HOME is a temp dir too.
fake_clone() {
    CLONE="$TEST_DIR/clone"
    mkdir -p "$CLONE/bin" "$CLONE/vscode-extension"
    cp "$ROMP_DIR/bin/romp-uninstall" "$CLONE/bin/romp-uninstall"
    chmod +x "$CLONE/bin/romp-uninstall"
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

# Claude Code's project-dir encoding, as kernel/judge.py's _proj_dir implements it: every
# non-alphanumeric character replaced, over the realpath. Tests must build the expected directory
# with THIS, never with a shell ${p//\//-} — that only replaces slashes, and a test using it
# agrees with a buggy implementation instead of with Claude Code.
_proj_slug() {
    python3 - "$1" <<'PYEOF'
import os, re, sys
print(re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(sys.argv[1])))
PYEOF
}

teardown() { rm -rf "$TEST_DIR"; }

hook_count() {   # how many romp hook commands are left registered across all events
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys, os
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

@test "romp-uninstall: removes the hook symlinks, skills and MCP config that install.sh created" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -L "$HOME/.claude/hooks/tmux-status.sh" ]
    [ -L "$HOME/.claude/romp-postal.mcp.json" ]
    [ "$(hook_count)" -gt 0 ]

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]

    [ ! -e "$HOME/.claude/hooks/tmux-status.sh" ]
    [ ! -e "$HOME/.claude/hooks/romp-summarize.sh" ]
    [ ! -e "$HOME/.claude/hooks/romp-postal-drain.sh" ]
    [ ! -e "$HOME/.claude/skills/romp" ]
    [ ! -e "$HOME/.claude/skills/romp-postal" ]
    [ ! -e "$HOME/.claude/romp-postal.mcp.json" ]
    [ "$(hook_count)" -eq 0 ]
}

@test "romp-uninstall: leaves the user's OWN hooks in settings.json untouched" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]

    # A hook of the user's own, in an event romp also writes to.
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
p = sys.argv[1]
s = json.load(open(p))
s["hooks"].setdefault("Stop", []).append(
    {"hooks": [{"type": "command", "command": "~/.claude/hooks/my-own-notify.sh", "timeout": 5}]})
s["permissions"] = {"allow": ["Bash(ls:*)"]}      # a non-hook setting, must also survive
json.dump(s, open(p, "w"), indent=2)
PY

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]

    run python3 -c "
import json; s = json.load(open('$HOME/.claude/settings.json'))
cmds = [h['command'] for rules in (s.get('hooks') or {}).values() for r in rules for h in r.get('hooks', [])]
assert '~/.claude/hooks/my-own-notify.sh' in cmds, cmds
assert s['permissions'] == {'allow': ['Bash(ls:*)']}, s.get('permissions')
print('preserved')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"preserved"* ]]
}

@test "romp-uninstall: keeps recorded state by default, deletes it only with --purge" {
    echo '{"synthetic": "record"}' > "$ROMP_STATE_DIR/serve-token"
    mkdir -p "$ROMP_STATE_DIR/sdkvenv/bin"

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [ -f "$ROMP_STATE_DIR/serve-token" ]          # records survive a plain uninstall...
    [ ! -d "$ROMP_STATE_DIR/sdkvenv" ]            # ...but the venv is an install artifact, so it goes
    [[ "$output" == *"state dir kept"* ]]

    run "$CLONE/bin/romp-uninstall" --yes --purge
    [ "$status" -eq 0 ]
    [ ! -d "$ROMP_STATE_DIR" ]
}

@test "romp-uninstall: strips the PATH line bootstrap.sh added, and nothing else" {
    cat > "$HOME/.bashrc" <<EOF
export EDITOR=vim

# romp
export PATH="\$PATH:$CLONE/bin"
alias ll='ls -la'
EOF

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]

    ! grep -qF "$CLONE/bin" "$HOME/.bashrc"
    ! grep -q '^# romp$' "$HOME/.bashrc"
    grep -q 'EDITOR=vim' "$HOME/.bashrc"          # the user's own lines are untouched
    grep -q "alias ll=" "$HOME/.bashrc"
}

@test "romp-uninstall: removes the build artifacts a reinstall must rebuild" {
    # Stand-ins for what vscode-extension/install.sh produces, in the throwaway clone — never the
    # real one, whose dist/ is what the running kernel is serving to the browser right now.
    mkdir -p "$CLONE/vscode-extension/node_modules" "$CLONE/vscode-extension/dist"
    touch "$CLONE/vscode-extension/dist/render.js" "$CLONE/vscode-extension/romp-chat-view.vsix"

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]

    [ ! -d "$CLONE/vscode-extension/node_modules" ]
    [ ! -d "$CLONE/vscode-extension/dist" ]
    [ ! -f "$CLONE/vscode-extension/romp-chat-view.vsix" ]
}

@test "romp-uninstall: never touches a DIFFERENT clone's install (kills only its own manager)" {
    # Two clones coexist on a dev machine (worktrees are the norm here). Uninstalling one must
    # leave the other's build artifacts — and, by the same path-scoped match, its manager — alone.
    other="$TEST_DIR/other-clone"
    mkdir -p "$other/vscode-extension/dist"
    touch "$other/vscode-extension/dist/render.js"

    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]

    [ -f "$other/vscode-extension/dist/render.js" ]
    # The pkill pattern must be this clone's absolute path, not a bare 'bin/romp-manager'.
    grep -q 'pkill -f "\$ROMP_DIR/bin/romp-manager"' "$CLONE/bin/romp-uninstall"
}

@test "romp-uninstall: is idempotent — a second run on a clean machine still exits 0" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
}

@test "romp uninstall: reachable as a verb and listed in help" {
    run "$ROMP_DIR/bin/romp" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp uninstall"* ]]
}

# ── the invisible consequence of --purge ─────────────────────────────────────
# The dashboard is token-gated and the first visit stores a year-long cookie, so an open tab
# keeps working until the state dir goes and the next kernel mints a NEW token. Then that tab
# drops to the token page, which reads as "the dashboard never loaded" rather than "signed out"
# — which is exactly how it landed on a real reinstall. The teardown step that causes it must
# say so, so the cycle is self-explanatory without anyone diagnosing it.

@test "romp-uninstall: --purge warns the browser session is invalidated, and how to get back in" {
    run "$CLONE/bin/romp-uninstall" --yes --purge
    [ "$status" -eq 0 ]
    [[ "$output" == *"signed out"* || "$output" == *"token page"* ]]
    [[ "$output" == *"romp url"* ]]                 # the exact command that fixes it
    [[ "$output" == *"not a failed install"* ]]     # names the misreading it prevents
}

@test "romp-uninstall: says nothing about tokens when state is kept (no new token is minted)" {
    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [[ "$output" != *"signed out"* ]]
    [[ "$output" != *"token page"* ]]
}

# ── the judge scratch's Claude Code project dir, which lives OUTSIDE the state dir ───────────
# romp runs judges as `claude` rooted at JUDGE_SCRATCH, so Claude Code writes their transcripts to
# a project dir keyed on that path — outside $STATE, so --purge missed them and a reinstalled romp
# kept showing judge records from the PREVIOUS install. They are romp's own droppings, never a
# session anyone started, so the teardown owns them.
#
# The scratch itself moved from /tmp/romp-judge into "$STATE/judge-scratch" on 2026-08-05, so
# --purge now takes the directory as part of the state root; the DERIVED project dir is still keyed
# on the path, which is what the default below has to track.

@test "romp-uninstall: the judge scratch default follows the state root, not /tmp" {
    # A stale default would leave the derived project dir behind — the 2026-07-27 incomplete-teardown
    # symptom, returning under a new name. ROMP_JUDGE_SCRATCH is deliberately NOT set here.
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    scratch="$ROMP_STATE_DIR/judge-scratch"
    mkdir -p "$scratch"
    # Build the expected directory the way CLAUDE CODE does — kernel/judge.py's _proj_dir rule,
    # every non-alphanumeric replaced over the realpath — NOT with the shell substitution the
    # script under test uses. Deriving it the same way the code does is how this test passed while
    # --purge swept a directory that never existed: it asserted the implementation against itself.
    proj="$CLAUDE_CONFIG_DIR/projects/$(_proj_slug "$scratch")"
    mkdir -p "$proj"
    echo '{"synthetic":"judge call"}' > "$proj/11111111-2222-3333-4444-555555555555.jsonl"

    run "$CLONE/bin/romp-uninstall" --yes --purge
    [ "$status" -eq 0 ]
    [ ! -d "$proj" ]
}

@test "romp-uninstall: removes romp's judge scratch and its transcripts" {
    export ROMP_JUDGE_SCRATCH="$TEST_DIR/romp-judge"
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    mkdir -p "$ROMP_JUDGE_SCRATCH"
    proj="$CLAUDE_CONFIG_DIR/projects/$(_proj_slug "$ROMP_JUDGE_SCRATCH")"
    mkdir -p "$proj"
    echo '{"synthetic":"judge call"}' > "$proj/11111111-2222-3333-4444-555555555555.jsonl"

    run "$CLONE/bin/romp-uninstall" --yes --purge
    [ "$status" -eq 0 ]

    [ ! -d "$ROMP_JUDGE_SCRATCH" ]
    [ ! -d "$proj" ]
}

@test "romp-uninstall: never touches YOUR sessions under ~/.claude/projects" {
    export ROMP_JUDGE_SCRATCH="$TEST_DIR/romp-judge"
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    mkdir -p "$ROMP_JUDGE_SCRATCH"
    mkdir -p "$CLAUDE_CONFIG_DIR/projects/$(_proj_slug "$ROMP_JUDGE_SCRATCH")"
    # A real project dir of the user's, which must survive untouched — deleting it would
    # destroy their own Claude Code history, which is not romp's to remove.
    mine="$CLAUDE_CONFIG_DIR/projects/-home-someone-notes-api"
    mkdir -p "$mine"
    echo '{"synthetic":"my session"}' > "$mine/99999999-8888-7777-6666-555555555555.jsonl"

    run "$CLONE/bin/romp-uninstall" --yes --purge
    [ "$status" -eq 0 ]

    [ -f "$mine/99999999-8888-7777-6666-555555555555.jsonl" ]
    [ -d "$CLAUDE_CONFIG_DIR/projects" ]
}

@test "romp-uninstall: a SYMLINKED judge scratch is refused, never followed to someone's own sessions" {
    # The guards read the raw $JUDGE_SCRATCH string while the project-dir slug is derived from its
    # REALPATH, so a symlink there made the validated string and the deleted target two different
    # paths. Reproduced before the fix: with the scratch symlinked at a checkout, a plain
    # `romp-uninstall --yes` — this section is NOT gated on --purge — deleted that checkout's own
    # Claude Code transcripts. kernel/judge.py refuses a symlinked scratch for the same reason.
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    mkdir -p "$TEST_DIR/someone-elses-project"
    mine="$CLAUDE_CONFIG_DIR/projects/$(_proj_slug "$TEST_DIR/someone-elses-project")"
    mkdir -p "$mine"
    echo '{"synthetic":"my own session"}' > "$mine/11111111-2222-3333-4444-555555555555.jsonl"

    ln -s "$TEST_DIR/someone-elses-project" "$ROMP_STATE_DIR/judge-scratch"
    run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]                              # skipped loudly, never aborted
    [[ "$output" == *"skipped"* ]]
    [ -f "$mine/11111111-2222-3333-4444-555555555555.jsonl" ]
}

@test "romp-uninstall: a relocated state dir (symlinked ANCESTOR) is still cleaned" {
    # Only the final component is checked. A symlinked $STATE is a legitimate setup — it is where
    # judge.py writes too — so refusing that would be an over-correction.
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    mkdir -p "$TEST_DIR/elsewhere/romp"
    rm -rf "$ROMP_STATE_DIR"
    ln -s "$TEST_DIR/elsewhere/romp" "$ROMP_STATE_DIR"
    scratch="$ROMP_STATE_DIR/judge-scratch"
    mkdir -p "$scratch"
    proj="$CLAUDE_CONFIG_DIR/projects/$(_proj_slug "$scratch")"
    mkdir -p "$proj"
    echo '{"synthetic":"judge call"}' > "$proj/11111111-2222-3333-4444-555555555555.jsonl"

    run "$CLONE/bin/romp-uninstall" --yes --purge
    [ "$status" -eq 0 ]
    [ ! -d "$proj" ]
}

@test "romp-uninstall: a mangled judge scratch can never resolve to the projects dir itself" {
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    mine="$CLAUDE_CONFIG_DIR/projects/-home-someone-notes-api"
    mkdir -p "$mine"
    echo '{"synthetic":"my session"}' > "$mine/99999999-8888-7777-6666-555555555555.jsonl"

    # Each of these would expand to a catastrophic `rm -rf` if taken at face value.
    for bad in "/" "" "$HOME" "/tmp" "/tmp/romp-judge/.."; do
        ROMP_JUDGE_SCRATCH="$bad" run "$CLONE/bin/romp-uninstall" --yes --purge
        [ "$status" -eq 0 ]                       # skipped, not aborted
        [ -d "$CLAUDE_CONFIG_DIR/projects" ]
        [ -f "$mine/99999999-8888-7777-6666-555555555555.jsonl" ]
        [ -d "$HOME" ]
    done
    [ -d "/tmp" ]
}

# ── the guards compare strings, and one directory has many spellings ─────────────────────────
# "$HOME/" and "$HOME" name the same directory but are different strings, so every raw string
# equality guard above the rm is defeated by a trailing slash — and by a trailing "/.", the same
# trick spelt with a dot. The slash ALSO switches off the symlink refusal: `[[ -L "$p/" ]]` is
# false for a symlink to a directory, because the trailing slash makes the test resolve the link
# instead of lstat'ing it. So the string must be normalised before ANY guard reads it.

@test "romp-uninstall: a trailing slash or /. cannot smuggle \$HOME past the guards" {
    # The hole needs a home path that passes the *romp* name check — real ones exist
    # (a user named after the project, a home under /srv/romp). Everything in it is at stake.
    export HOME="$TEST_DIR/romp-home"
    mkdir -p "$HOME"
    echo "irreplaceable" > "$HOME/precious.txt"
    for bad in "$HOME/" "$HOME//" "$HOME/." "$HOME/./"; do
        ROMP_JUDGE_SCRATCH="$bad" run "$CLONE/bin/romp-uninstall" --yes
        [ "$status" -eq 0 ]                       # skipped loudly, never aborted
        [[ "$output" == *"skipped"* ]]
        [ -f "$HOME/precious.txt" ]
    done
}

@test "romp-uninstall: a scratch aimed at the state dir itself is refused — records survive a plain uninstall" {
    # "$STATE" contains "romp" for every default install, so it passes the name check — and a
    # plain, no---purge uninstall then deletes the very records it promises to keep. The state
    # dir is only ever removed by --purge, behind its own confirmation; the scratch guard must
    # never become a second, unconfirmed path to it.
    export ROMP_STATE_DIR="$TEST_DIR/state-romp"
    mkdir -p "$ROMP_STATE_DIR"
    echo '{"synthetic":"record"}' > "$ROMP_STATE_DIR/serve-token"
    for bad in "$ROMP_STATE_DIR" "$ROMP_STATE_DIR/" "$ROMP_STATE_DIR/."; do
        ROMP_JUDGE_SCRATCH="$bad" run "$CLONE/bin/romp-uninstall" --yes
        [ "$status" -eq 0 ]
        [[ "$output" == *"skipped"* ]]
        [ -f "$ROMP_STATE_DIR/serve-token" ]
    done
}

@test "romp-uninstall: a trailing slash does not defeat the symlink refusal" {
    # Same setup as the symlink test above, plus one character. Before normalisation the slash
    # made `[[ -L ]]` resolve the link, so the refusal never fired and the rm followed it.
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    mkdir -p "$TEST_DIR/someone-elses-project"
    echo "not romp's" > "$TEST_DIR/someone-elses-project/keep.txt"
    mine="$CLAUDE_CONFIG_DIR/projects/$(_proj_slug "$TEST_DIR/someone-elses-project")"
    mkdir -p "$mine"
    echo '{"synthetic":"my own session"}' > "$mine/11111111-2222-3333-4444-555555555555.jsonl"

    ln -s "$TEST_DIR/someone-elses-project" "$ROMP_STATE_DIR/judge-scratch"
    ROMP_JUDGE_SCRATCH="$ROMP_STATE_DIR/judge-scratch/" run "$CLONE/bin/romp-uninstall" --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"skipped"* ]]
    [ -f "$TEST_DIR/someone-elses-project/keep.txt" ]
    [ -f "$mine/11111111-2222-3333-4444-555555555555.jsonl" ]
}

# ── every spelling of $HOME/$STATE, not just the two the suffix-trimmer knew ──────────────────
# A suffix-trimmer only strips what is at the END of the string. It is defeated by (a) a trailing
# newline — $(...) strips the newline AFTER the trimmer has already given up, so the trailing slash
# it left behind survives; and (b) an INTERNAL alternate spelling ($STATE//romp, $HOME/./x) it never
# looks at. Both name the same directory the equality guards are meant to protect. These enumerate
# the classes as INPUTS and assert the protected dir survives — the property, not the two spellings.

@test "romp-uninstall: a mangled spelling of \$HOME never reaches rm -rf (newline, //, /./)" {
    export HOME="$TEST_DIR/romp-home"
    mkdir -p "$HOME/keep"
    echo "irreplaceable" > "$HOME/keep/precious.txt"
    # A literal trailing newline, an internal double slash, an internal /./ — each names $HOME.
    for bad in "$HOME/"$'\n' "$TEST_DIR//romp-home" "$TEST_DIR/./romp-home" "$TEST_DIR/romp-home/."$'\n'; do
        ROMP_JUDGE_SCRATCH="$bad" run "$CLONE/bin/romp-uninstall" --yes
        [ "$status" -eq 0 ]                       # skipped loudly, never a partial rm
        [[ "$output" == *"skipped"* ]]
        [ -f "$HOME/keep/precious.txt" ]
    done
}

@test "romp-uninstall: a mangled spelling of the state dir never reaches rm -rf (newline, //, /./)" {
    export ROMP_STATE_DIR="$TEST_DIR/state-romp"
    mkdir -p "$ROMP_STATE_DIR"
    echo '{"synthetic":"record"}' > "$ROMP_STATE_DIR/serve-token"
    for bad in "$ROMP_STATE_DIR/"$'\n' "$TEST_DIR//state-romp" "$TEST_DIR/./state-romp" "$ROMP_STATE_DIR/."$'\n'; do
        ROMP_JUDGE_SCRATCH="$bad" run "$CLONE/bin/romp-uninstall" --yes
        [ "$status" -eq 0 ]
        [[ "$output" == *"skipped"* ]]
        [ -f "$ROMP_STATE_DIR/serve-token" ]      # a plain --yes must keep every record
    done
}

@test "romp-uninstall: the real scratch is still cleaned when spelt with // or a trailing slash" {
    # The normalisation must not become a reason to SKIP a legitimate scratch: $STATE//judge-scratch
    # and $STATE/judge-scratch/ both name romp's own dir and must still be torn down.
    export CLAUDE_CONFIG_DIR="$HOME/.claude"
    for spell in "$ROMP_STATE_DIR//judge-scratch" "$ROMP_STATE_DIR/judge-scratch/"; do
        rm -rf "$ROMP_STATE_DIR/judge-scratch"
        scratch="$ROMP_STATE_DIR/judge-scratch"
        mkdir -p "$scratch"
        proj="$CLAUDE_CONFIG_DIR/projects/$(_proj_slug "$scratch")"
        mkdir -p "$proj"
        echo '{"synthetic":"judge call"}' > "$proj/11111111-2222-3333-4444-555555555555.jsonl"
        ROMP_JUDGE_SCRATCH="$spell" run "$CLONE/bin/romp-uninstall" --yes --purge
        [ "$status" -eq 0 ]
        [[ "$output" != *"skipped: '$spell'"* ]]  # NOT skipped — it is romp's own
        [ ! -d "$scratch" ]
        [ ! -d "$proj" ]
    done
}
