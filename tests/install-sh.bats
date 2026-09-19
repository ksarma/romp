#!/usr/bin/env bats

# ./install.sh — "install romp normally, then everything (incl. federating this host from another
# dashboard) just works". Hermetic: HOME points at a temp dir; the login service, VS Code extension
# and SDK-venv steps are opted out (ROMP_NO_SERVICE / ROMP_NO_EXT / ROMP_NO_SDK) — they touch the
# real machine or the network. What's covered: hook symlinks, the idempotent settings.json merge,
# and the MCP/skills symlinks.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

load git-hermetic

setup() {
    git_hermetic
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
    # The state root, pinned to the path the default resolves to (round 1 of the install-rewrite review,
    # 2026-09-18): the running-manager case below runs the REAL bin/romp-service, whose rewrite journals itself
    # under the state root, and a kernel exports ROMP_STATE_DIR (a profile's) or XDG_STATE_HOME to its sessions,
    # so an unpinned run appended a row to a live restart-audit.jsonl. The default's own path rather than a
    # separate directory: the tokened-link case seeds its token at $HOME/.local/state/romp, where install.sh's
    # closing read looks, and a root elsewhere left that case red.
    export ROMP_STATE_DIR="$HOME/.local/state/romp"
    unset XDG_STATE_HOME
    export ROMP_NO_SERVICE=1 ROMP_NO_EXT=1 ROMP_NO_SDK=1
    # One try only: the closing dashboard-link block polls for the kernel's token
    # file, which never appears in this hermetic HOME — don't wait 10s for it.
    export ROMP_INSTALL_TOKEN_TRIES=1
    # Redirect the git pre-push hook symlink into a temp dir so install.sh never
    # writes into the REAL repo's .git/hooks while these tests run.
    export ROMP_GITHOOK_DIR="$TEST_DIR/githooks"
}

teardown() { rm -rf "$TEST_DIR"; }

count_cmd() {   # occurrences of a hook script in one event's rules
    python3 - "$HOME/.claude/settings.json" "$1" "$2" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
n = sum(1 for r in s.get("hooks", {}).get(sys.argv[2], []) for h in r.get("hooks", [])
        if h.get("command", "").endswith(sys.argv[3]))
print(n)
PY
}

@test "install.sh: wires hooks, settings.json, and the MCP config on a fresh machine" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -L "$HOME/.claude/hooks/romp-wake.sh" ]
    [[ "$(readlink "$HOME/.claude/hooks/romp-wake.sh")" == *"/hooks/romp-wake.sh" ]]
    [ "$(count_cmd Stop romp-wake.sh)" = "1" ]
    [ "$(count_cmd Stop romp-summarize.sh)" = "0" ]   # retired 2026-09-11, never registered again
    [ "$(count_cmd Stop tmux-status.sh)" = "0" ]      # retired the same day, never registered again
    [ "$(count_cmd Stop romp-postal-drain.sh)" = "1" ]
    [ "$(count_cmd SessionStart romp-postal-ensure.sh)" = "1" ]
    [ "$(count_cmd SessionStart romp-usertodo-context.sh)" = "1" ]
    [ -L "$HOME/.claude/hooks/romp-usertodo-context.sh" ]
    [ "$(count_cmd UserPromptSubmit romp-wake.sh)" = "1" ]
    # a compaction's END wakes the kernel too: the op parked behind a /compact delivers on this event
    [ "$(count_cmd PostCompact romp-wake.sh)" = "1" ]
    [ -L "$HOME/.claude/romp-postal.mcp.json" ]
    # romp's own Bash-side track guard (hooks/romp-track-bash-guard.mjs) is linked with the rest
    [ -L "$HOME/.claude/hooks/romp-track-bash-guard.mjs" ]
    [ "$(readlink "$HOME/.claude/hooks/romp-track-bash-guard.mjs")" = "$ROMP_DIR/hooks/romp-track-bash-guard.mjs" ]
}

@test "install.sh: registers no status hook — the SDK backend records a session's state itself" {
    # Until 2026-09-11 a status hook (hooks/tmux-status.sh) sat on seven events. It painted the tmux
    # status bar; the states/<sid>.jsonl rows of a Claude Code session were always the SDK backend's
    # own writes, so nothing replaced it. A fresh install links and registers nothing of that shape on
    # any event, and the three events only it sat on (PostToolUse, Notification, PreCompact) are not
    # created: an event with no hooks would be `[{"hooks": []}]` litter. On this fork PreToolUse is the
    # fifth event: it holds the two tracked-changes guards (the vendored track-guard.mjs and romp's own
    # Bash-side guard), registered by the same install.
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -z "$(find "$HOME/.claude/hooks" -name '*-status.sh')" ]
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
hooks = json.load(open(sys.argv[1]))["hooks"]
cmds = [(ev, h["command"]) for ev, groups in hooks.items() for g in groups for h in g.get("hooks", [])]
assert not [c for c in cmds if c[1].endswith("-status.sh")], cmds
assert sorted(hooks) == ["PostCompact", "PreToolUse", "SessionStart", "Stop", "UserPromptSubmit"], sorted(hooks)
PY
}

@test "install.sh: idempotent — a second run adds no duplicate hook entries" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"already registered"* ]]
    [ "$(count_cmd Stop romp-wake.sh)" = "1" ]
    [ "$(count_cmd UserPromptSubmit romp-summarize.sh)" = "0" ]
    # regression: a re-run used to FOLLOW the existing skill dir-symlink and drop a new link INSIDE
    # the repo (claude/skills/romp-postal/romp-postal → an absolute personal path). ln -sfn replaces
    # the link.
    [ ! -e "$ROMP_DIR/claude/skills/romp-postal/romp-postal" ]
    [ -L "$HOME/.claude/skills/romp-postal" ]
}

@test "install.sh: the retired bundled manager skill unlinks ONLY when it points into this repo" {
    # The manager skill moved to the user's dotfiles 2026-08-23 (romp ships primitives; workflows
    # live outside). The dotfiles successor claims the SAME ~/.claude/skills/manager name, so the
    # upgrade cleanup must remove a link into $ROMP_DIR and leave any other target alone — a plain
    # unlink here would delete the successor the moment a user reinstalls romp.
    mkdir -p "$HOME/.claude/skills"   # the hermetic HOME starts empty; ln needs the parent
    ln -s "$ROMP_DIR/claude/skills/manager" "$HOME/.claude/skills/manager"
    run bash "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ ! -e "$HOME/.claude/skills/manager" ] && [ ! -L "$HOME/.claude/skills/manager" ]
    mkdir -p "$HOME/dotfiles-skills/manager"
    ln -s "$HOME/dotfiles-skills/manager" "$HOME/.claude/skills/manager"
    run bash "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -L "$HOME/.claude/skills/manager" ]   # the dotfiles successor link survives the re-run
}

@test "install.sh: upgrading unlinks the retired romp skill, leaving no dangling link" {
    # An install from before 2026-07-27 has ~/.claude/skills/romp pointing at a directory this repo
    # no longer ships. Upgrading must clear it: a dangling symlink puts a broken skill in front of
    # every session.
    mkdir -p "$HOME/.claude/skills"
    ln -sfn "$ROMP_DIR/claude/skills/romp" "$HOME/.claude/skills/romp"
    [ -L "$HOME/.claude/skills/romp" ]

    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]

    [ ! -L "$HOME/.claude/skills/romp" ]
    [ ! -e "$HOME/.claude/skills/romp" ]
    [ -L "$HOME/.claude/skills/romp-postal" ]      # its neighbour is untouched
}

@test "install.sh: a real directory named romp survives — only a symlink is removed" {
    # Someone else's skill of that name is theirs, not ours to delete.
    mkdir -p "$HOME/.claude/skills/romp"
    echo "mine" > "$HOME/.claude/skills/romp/SKILL.md"

    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]

    [ -f "$HOME/.claude/skills/romp/SKILL.md" ]
}

@test "install.sh: upgrading de-registers the retired announcer hook and unlinks it, leaving other hooks alone" {
    # hooks/romp-summarize.sh (the live tmux phrase) was removed 2026-09-11 with the tmux backend's
    # dead leaves. An install from before still registers it on UserPromptSubmit and Stop and holds a
    # symlink to a file this repo no longer ships; upgrading must clear both, or Claude Code shells a
    # missing path on every prompt and every turn end. Other hooks, romp's and the user's, stay.
    mkdir -p "$HOME/.claude/hooks"
    ln -s "$ROMP_DIR/hooks/romp-summarize.sh" "$HOME/.claude/hooks/romp-summarize.sh"
    cat > "$HOME/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "UserPromptSubmit": [ { "hooks": [
      { "type": "command", "command": "~/.claude/hooks/romp-summarize.sh", "timeout": 10, "async": true } ] } ],
    "Stop": [ { "hooks": [
      { "type": "command", "command": "my-own-hook.sh" },
      { "type": "command", "command": "~/.claude/hooks/romp-summarize.sh", "timeout": 10, "async": true } ] } ],
    "SubagentStop": [ { "hooks": [
      { "type": "command", "command": "~/.claude/hooks/romp-summarize.sh", "timeout": 10, "async": true } ] } ]
  }
}
JSON
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp-summarize.sh"* ]]          # the upgrade says what it removed
    [ ! -L "$HOME/.claude/hooks/romp-summarize.sh" ]
    [ ! -e "$HOME/.claude/hooks/romp-summarize.sh" ]
    [ "$(count_cmd UserPromptSubmit romp-summarize.sh)" = "0" ]
    [ "$(count_cmd Stop romp-summarize.sh)" = "0" ]
    [ "$(count_cmd Stop my-own-hook.sh)" = "1" ]       # the user's own hook survives
    [ "$(count_cmd Stop romp-wake.sh)" = "1" ]         # the live hooks are registered as before
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
assert "SubagentStop" not in s["hooks"], list(s["hooks"])   # an event emptied by the removal is pruned, no litter
PY
}

@test "install.sh: a real file named like the retired announcer hook is left alone" {
    # Someone's own hook of that name is theirs; only the symlink install.sh once wrote is removed.
    mkdir -p "$HOME/.claude/hooks"
    echo "mine" > "$HOME/.claude/hooks/romp-summarize.sh"
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -f "$HOME/.claude/hooks/romp-summarize.sh" ]
    [ "$(cat "$HOME/.claude/hooks/romp-summarize.sh")" = "mine" ]
}

@test "install.sh: the retired-hook prune leaves a user's own empty and matcher-only groups alone" {
    # The prune drops only a group OUR removal emptied and an event it left with no groups. A user's
    # placeholder group (a matcher with no hooks yet, an empty group on an event romp never registers)
    # is theirs and must survive both a fresh install (which writes the file) and an upgrade re-run.
    # On this fork the user's Bash placeholder is also where romp's Bash-side track guard registers (the
    # merge keys PreToolUse groups by matcher, the coexist tests): the group keeps its matcher and gains
    # that one hook, and the vendored guard gets its own Write|Edit|MultiEdit group beside it.
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [ { "matcher": "Bash", "hooks": [] } ],
    "SubagentStart": [ { "hooks": [] } ],
    "Stop": [ { "hooks": [
      { "type": "command", "command": "~/.claude/hooks/romp-summarize.sh", "timeout": 10, "async": true } ] } ]
  }
}
JSON
    for _pass in fresh upgrade; do
        run "$ROMP_DIR/install.sh"
        [ "$status" -eq 0 ]
        python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))["hooks"]
assert [g.get("matcher") for g in s["PreToolUse"]] == ["Bash", "Write|Edit|MultiEdit"], s.get("PreToolUse")
assert [h["command"] for h in s["PreToolUse"][0]["hooks"]] == ["~/.claude/hooks/romp-track-bash-guard.mjs"], s["PreToolUse"][0]
assert s["SubagentStart"] == [{"hooks": []}], s.get("SubagentStart")
stop = [h["command"] for g in s["Stop"] for h in g["hooks"]]
assert not any(c.endswith("romp-summarize.sh") for c in stop), stop
assert any(c.endswith("romp-wake.sh") for c in stop), stop
PY
    done
}

@test "install.sh: a symlink to someone else's live script of the retired hook's name survives" {
    # Only a link install.sh could have written goes: one into this checkout, or a dangling one of that
    # shape (a checkout since moved). A user's own live script linked from their dotfiles is theirs.
    mkdir -p "$HOME/dotfiles/hooks" "$HOME/.claude/hooks"
    echo "mine" > "$HOME/dotfiles/hooks/romp-summarize.sh"
    ln -s "$HOME/dotfiles/hooks/romp-summarize.sh" "$HOME/.claude/hooks/romp-summarize.sh"
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -L "$HOME/.claude/hooks/romp-summarize.sh" ]
    [ "$(cat "$HOME/.claude/hooks/romp-summarize.sh")" = "mine" ]
    [[ "$output" != *"retired romp-summarize.sh"* ]]
    # ...while a DANGLING link of that shape (a romp checkout that has since moved) is still removed
    rm "$HOME/.claude/hooks/romp-summarize.sh"
    ln -s "$HOME/old-romp/hooks/romp-summarize.sh" "$HOME/.claude/hooks/romp-summarize.sh"
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ ! -L "$HOME/.claude/hooks/romp-summarize.sh" ]
    [ ! -e "$HOME/.claude/hooks/romp-summarize.sh" ]
}

@test "install.sh: upgrading de-registers the retired status hook on all seven events and unlinks it, wiring nothing in its place" {
    # hooks/tmux-status.sh, the hook that painted the tmux status bar, left 2026-09-11 with the tmux
    # backend; nothing replaces it, since the SDK backend records a Claude Code session's state
    # itself. An install from before registers it on seven events and holds a symlink to a path this
    # repo no longer ships: left in place, Claude Code would shell a missing path on every one of
    # those events in every session. Upgrading clears both, prunes the three events only it sat on
    # rather than leaving empty groups, and links nothing of that shape; the user's own hooks and
    # romp's other hooks stay.
    mkdir -p "$HOME/.claude/hooks"
    ln -s "$ROMP_DIR/hooks/tmux-status.sh" "$HOME/.claude/hooks/tmux-status.sh"
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
old = {"type": "command", "command": "~/.claude/hooks/tmux-status.sh", "timeout": 5, "async": False}
events = ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "Notification", "PreCompact", "PostCompact")
hooks = {ev: [{"hooks": [dict(old)]}] for ev in events}
hooks["Stop"][0]["hooks"].insert(0, {"type": "command", "command": "my-own-hook.sh"})
json.dump({"hooks": hooks}, open(sys.argv[1], "w"), indent=2)
PY
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"tmux-status.sh"* ]]              # the upgrade says what it removed
    [ ! -L "$HOME/.claude/hooks/tmux-status.sh" ]
    [ ! -e "$HOME/.claude/hooks/tmux-status.sh" ]
    [ -z "$(find "$HOME/.claude/hooks" -name '*-status.sh')" ]
    for ev in SessionStart UserPromptSubmit PostToolUse Stop Notification PreCompact PostCompact; do
        [ "$(count_cmd "$ev" -status.sh)" = "0" ]
    done
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
hooks = json.load(open(sys.argv[1]))["hooks"]
for ev in ("PostToolUse", "Notification", "PreCompact"):
    assert ev not in hooks, (ev, hooks[ev])       # emptied by the removal, so pruned: no litter
PY
    [ "$(count_cmd Stop my-own-hook.sh)" = "1" ]        # the user's own hook survives
    [ "$(count_cmd Stop romp-postal-drain.sh)" = "1" ]  # romp's other hooks are wired as on a fresh install
    [ "$(count_cmd Stop romp-wake.sh)" = "1" ]
}

@test "install.sh: a real file named like the status hook's old name is left alone" {
    mkdir -p "$HOME/.claude/hooks"
    echo "mine" > "$HOME/.claude/hooks/tmux-status.sh"
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -f "$HOME/.claude/hooks/tmux-status.sh" ]
    [ "$(cat "$HOME/.claude/hooks/tmux-status.sh")" = "mine" ]
    [ -L "$HOME/.claude/hooks/romp-wake.sh" ]           # romp's own hooks are wired regardless
}

@test "install.sh: preflight fails clearly when node is missing" {
    ROMP_NODE=romp-test-no-such-node run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Node.js not found"* ]]
    [[ "$output" == *"brew install node"* ]]
    # nothing was installed: the preflight runs before any mutation
    [ ! -e "$HOME/.claude/hooks/romp-wake.sh" ]
}

@test "install.sh: ROMP_SKIP_PREFLIGHT bypasses the checks" {
    ROMP_NODE=romp-test-no-such-node ROMP_SKIP_PREFLIGHT=1 run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -L "$HOME/.claude/hooks/romp-wake.sh" ]
}

# The login-service step (the user's rescue_me, 2026-07-21): a webview deploy must never bootout a
# HEALTHY romp-manager, and must FAIL LOUDLY (not `|| echo`-swallow) if an install it DID attempt fails —
# the swallowed failure is what left the dashboard dead on :29855. ROMP_SERVICE_BIN stubs romp-service.
_svc_stub() {   # write a fake romp-service to $1; behavior toggled by ROMP_SVC_RUNNING / ROMP_SVC_FAIL / ROMP_SVC_REWRITE_FAIL
                # (exit 1, a reload that failed) / ROMP_SVC_REWRITE_REFUSE (exit 5, the identity refusal, with romp-service's
                # own two lines) / ROMP_SVC_INSTALL_REFUSE (the same refusal on the install road, the marked update child's) /
                # ROMP_SVC_INSTALL_REFUSE_PATH (exit 5 on the install road for a manager path systemd refuses: no identity was read) /
                # ROMP_SVC_NOT_INSTALLED (status says not installed AND running; rewrite exits 3) /
                # ROMP_SVC_MINT_PORT (install writes that port into the state root's serve-port record beside a
                # serve-token, as the kernel the started service brings up does moments after it loads)
    cat > "$1" <<'SH'
#!/usr/bin/env bash
echo "$1" >> "$ROMP_SVC_LOG"
case "$1" in
  status) if [[ -n "${ROMP_SVC_NOT_INSTALLED:-}" ]]; then echo "not installed"; else echo "installed: /tmp/plist"; fi
          [[ -n "${ROMP_SVC_RUNNING:-}" ]] && echo "running"
          [[ -n "${ROMP_SVC_DYING:-}" ]] && echo "loaded but not running (last exit code: 134); launchd keeps respawning it — check /tmp/manager.log" ;;
  install) [[ -n "${ROMP_SVC_FAIL:-}" ]] && { echo "romp-service: bootstrap lost the drain-race" >&2; exit 1; }
           [[ -n "${ROMP_SVC_INSTALL_REFUSE:-}" ]] && { echo "romp-service: the login service unit on disk and this environment disagree; nothing was rewritten:" >&2
                                                       echo "  ROMP_STATE_DIR: the file carries /srv/second, this environment carries /srv/other" >&2; exit 5; }
           [[ -n "${ROMP_SVC_INSTALL_REFUSE_PATH:-}" ]] && { echo "romp-service: the manager's path (/srv/q\"uote/romp-manager) contains a quote, a backslash or a control character, which systemd refuses in an ExecStart= executable name (Executable name contains special characters: the unit would fail to load and never start); nothing was written." >&2
                                                            echo "  Move the clone to a path without those characters and run romp-service install from it." >&2; exit 5; }
           [[ -n "${ROMP_SVC_HELD:-}" ]] && { echo "romp-service: the agent's manager exited at once because a manager is ALREADY serving on :7432 outside the login service" >&2; exit 3; }
           [[ -n "${ROMP_SVC_MINT_PORT:-}" ]] && { mkdir -p "$ROMP_STATE_DIR"; printf '%s\n' "$ROMP_SVC_MINT_PORT" > "$ROMP_STATE_DIR/serve-port"; printf 'tok123\n' > "$ROMP_STATE_DIR/serve-token"; } ;;
  rewrite) [[ -n "${ROMP_SVC_REWRITE_FAIL:-}" ]] && { echo "romp-service: the unit was written but systemd did NOT reload it" >&2; exit 1; }
           [[ -n "${ROMP_SVC_REWRITE_REFUSE:-}" ]] && { echo "romp-service: the login unit on disk and this environment disagree; nothing was rewritten:" >&2
                                                       echo "  ROMP_KERNEL_PORT: the file carries 29866, this environment carries 31855" >&2; exit 5; }
           [[ -n "${ROMP_SVC_NOT_INSTALLED:-}" ]] && { echo "romp-service: no login service is installed (romp-service install writes and enables one)" >&2; exit 3; } ;;
esac
exit 0
SH
    chmod +x "$1"
}

@test "install.sh: a running romp-manager is never booted out: the unit goes through romp-service rewrite, and install never runs" {
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_RUNNING=1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    # it asked status, then rewrite (the unit, no restart; the test below drives the real romp-service), and NEVER
    # install (the bootout): the healthy manager was left up
    grep -qx status "$TEST_DIR/svc.log"
    grep -qx rewrite "$TEST_DIR/svc.log"
    [[ "$output" != *"Installing the romp login service"* ]]
    ! grep -qx install "$TEST_DIR/svc.log"
}

@test "install.sh: a FAILED unit rewrite under a running manager fails the run loudly, and install still never runs" {
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_RUNNING=1 ROMP_SVC_REWRITE_FAIL=1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp-service rewrite FAILED"* ]]
    [[ "$output" == *"still running"* ]]                    # the manager is up; the unit is what did not land
    [[ "$output" == *"Retry by hand:"* ]]                   # a reload that failed (exit 1) is retryable from this shell
    # the run stops there, as a failed install's does: no closing report (the ROMPHOME note, the dashboard link)
    # over a state that means the login service on disk is not this release's (round 1 of the review, 2026-09-18)
    [[ "$output" != *"ROMPHOME"* ]]
    [[ "$output" != *"http://127.0.0.1"* ]]
    [[ "$output" != *"romp url"* ]]
    run grep -x install "$TEST_DIR/svc.log"
    [ "$status" -ne 0 ]
}

@test "install.sh: a REFUSED unit rewrite (exit 5) fails the run, says the reason is printed above with romp-service's own lines reaching the operator, invents no retry command, and install never runs" {
    # Round 2 of the review (2026-09-18, departure d of round 1's body): romp-service exited 1 for the identity refusal
    # and for a failed reload alike, so the one retry line here sent the refusal back to the command that had just
    # refused it. The refusal has its own code now; install.sh points at the reason above and adds nothing.
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_RUNNING=1 ROMP_SVC_REWRITE_REFUSE=1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp-service rewrite refused"* ]]
    [[ "$output" == *"the reason is printed above"* ]]
    [[ "$output" == *"the login unit on disk and this environment disagree"* ]]    # romp-service's own text (tests-4)
    [[ "$output" == *"ROMP_KERNEL_PORT: the file carries 29866, this environment carries 31855"* ]]
    [[ "$output" == *"still running"* ]]
    [[ "$output" != *"Retry by hand"* ]]
    [[ "$output" != *"rewrite FAILED"* ]]
    [[ "$output" != *"ROMPHOME"* ]]
    [[ "$output" != *"romp url"* ]]
    run grep -x install "$TEST_DIR/svc.log"
    [ "$status" -ne 0 ]
}

@test "install.sh: a running manager with no unit at the path (status: not installed, then running) does not fail the deploy and does not fall through to install; the route is named, with the restart it costs" {
    # Round 2 of the review (correctness-3): a unit deleted while systemd still reports the service active gives this
    # status; the rewrite exits 3, and the filed version failed the whole deploy with a retry line that could never
    # succeed, where the base finished. Falling through to `install` is the bootout the gate exists to prevent, and
    # inside the kernel's update child it would restart every kernel on an otherwise untouched box.
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_RUNNING=1 ROMP_SVC_NOT_INSTALLED=1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"no login service unit is at the path romp-service writes"* ]]
    [[ "$output" == *"romp is serving"* ]]
    [[ "$output" == *"$TEST_DIR/romp-service install"* ]]
    [[ "$output" == *"restarts the manager"* ]]
    [[ "$output" != *"Retry by hand"* ]]
    [[ "$output" != *"rewrite FAILED"* ]]
    [[ "$output" == *"ROMPHOME"* ]]                          # the run goes on to the closing report
    grep -qx rewrite "$TEST_DIR/svc.log"
    run grep -x install "$TEST_DIR/svc.log"
    [ "$status" -ne 0 ]
}

# ── the unit under a running manager (the box admin's hazard review of the pull-in, 2026-09-16) ──
# Until 2026-09-18 the block above skipped the whole service step when the manager reported running, so a unit
# change a release carried (the MALLOC_ARENA_MAX=2 line the memory fix needs) never reached a box that installed
# while its manager ran, and the administrator added a drop-in by hand. Here the REAL bin/romp-service runs, with
# systemctl stubbed (ROMP_SYSTEMCTL; never the box's own): the unit on disk is this release's afterwards, systemd was
# asked to reload and nothing else, and the one line names the command that restarts the manager.
_systemctl_active_stub() {   # a systemctl whose is-active says the manager runs; every call's argv lands in systemctl-calls
    cat > "$TEST_DIR/systemctl" <<EOF
#!/bin/sh
echo "\$*" >> "$TEST_DIR/systemctl-calls"
case "\$2" in
  is-active) echo active ;;
  show) case "\$*" in
          *NeedDaemonReload*) echo no ;;                                  # the rewrite's read-back after its reload: loaded is current
          *FragmentPath*) echo "$TEST_DIR/systemd/romp-manager.service" ;;   # and loaded from the file just written
        esac ;;
  *) exit 0 ;;
esac
EOF
    chmod +x "$TEST_DIR/systemctl"
}

@test "install.sh: under a running manager the unit is rewritten and systemd reloaded; the manager is left as it is and the line names its restart" {
    unset ROMP_NO_SERVICE ROMP_SERVICE_NO_LOAD ROMP_SERVICE_BIN
    _systemctl_active_stub
    export ROMP_SYSTEMCTL="$TEST_DIR/systemctl" ROMP_OS_OVERRIDE=Linux
    export ROMP_SYSTEMD_DIR="$TEST_DIR/systemd" ROMP_MANAGER_BIN="$TEST_DIR/romp-manager"
    # the previous release's unit: the state of a box that installs while its manager runs. Its own PATH and ROMP_DIR
    # lines (round 2 of the review, 2026-09-18: the fixture had neither, so the end-to-end case asserted nothing about
    # PATH while the rewrite baked the caller's, and leaked the review worktree's ROMP_DIR in probes)
    mkdir -p "$ROMP_SYSTEMD_DIR" "$TEST_DIR/callerbin"
    printf '[Service]\nExecStart=%s up\nEnvironment=PATH=/unit/own/bin:/usr/bin\nEnvironment=ROMP_DIR=%s\nEnvironment=ROMP_SUPERVISED=1\n' \
        "$ROMP_MANAGER_BIN" "$ROMP_DIR" > "$ROMP_SYSTEMD_DIR/romp-manager.service"
    PATH="$TEST_DIR/callerbin:$PATH" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    # the release's unit reached the disk, whole (its allocator line is the review's example), and no scratch file stayed
    grep -q '^Environment=MALLOC_ARENA_MAX=2$' "$ROMP_SYSTEMD_DIR/romp-manager.service"
    grep -q "^ExecStart=$ROMP_MANAGER_BIN up$" "$ROMP_SYSTEMD_DIR/romp-manager.service"
    [ ! -e "$ROMP_SYSTEMD_DIR/romp-manager.service.tmp" ]
    # the unit's own PATH and ROMP_DIR, kept (round 2, tests-3, end to end through install.sh); the caller's PATH
    # reaching nothing is asserted last, since that `run` replaces $output
    grep -qx 'Environment=PATH=/unit/own/bin:/usr/bin' "$ROMP_SYSTEMD_DIR/romp-manager.service"
    grep -qxF "Environment=ROMP_DIR=$ROMP_DIR" "$ROMP_SYSTEMD_DIR/romp-manager.service"
    # the one line: the manager keeps its old unit, and the command that restarts it
    [[ "$output" == *"keeps its old unit until its next restart"* ]]
    [[ "$output" == *"systemctl --user restart romp-manager"* ]]
    [[ "$output" != *"already running"* ]]
    [[ "$output" != *"Installing the romp login service"* ]]
    [[ "$output" != *"kept an older definition"* ]]         # the read-back after the reload found the loaded unit current
    # the rewrite journaled itself under THIS run's state root (setup pins it; the row is the one the kernel's
    # restart-audit walk skips), never under a root the session's environment carried
    grep -q '"action": "service-rewrite"' "$ROMP_STATE_DIR/restart-audit.jsonl"
    # systemd was asked to reload and read back, and for nothing else: no enable, start, stop, restart or kill from
    # here. Last, and armed: `run` replaces $output, and a bare `!` mid-test asserts nothing in bats
    grep -qx -- '--user daemon-reload' "$TEST_DIR/systemctl-calls"
    run grep -E -- 'enable|start|stop|restart|kill' "$TEST_DIR/systemctl-calls"
    [ "$status" -ne 0 ]
    run grep -F "$TEST_DIR/callerbin" "$ROMP_SYSTEMD_DIR/romp-manager.service"
    [ "$status" -ne 0 ]
}

@test "install.sh: a loaded manager that keeps dying is reinstalled, not left up (the status line that is not running)" {
    # issue 1600, the status fix: romp-service says "loaded but not running (last exit code: N)" for a crash-looping
    # job; the shortcut keys on the bare line `running` (an exact whole-line grep), so this takes the reinstall branch
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_DYING=1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" != *"already running"* ]]
    grep -qx install "$TEST_DIR/svc.log"
}

@test "install.sh: installs the service when romp-manager is NOT running" {
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log"   # ROMP_SVC_RUNNING unset -> not running
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    grep -qx install "$TEST_DIR/svc.log"
}

@test "install.sh: a manager already serving outside the service is named as such, not as a dead dashboard (romp-service exit 3)" {
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_HELD=1
    ROMP_INSTALL_TOKEN_TRIES=1 ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]                                            # the service is still not the one running
    [[ "$output" == *"a manager already serving on the control port holds it"* ]]
    [[ "$output" == *"most likely a hand-run romp up outside the service"* ]]
    [[ "$output" != *"dashboard will be dead"* ]]
    [[ "$output" != *"dashboard is up"* ]]                          # the control port proves a manager, not the dashboard
    # round two: romp IS serving in this state, so the run goes on to the finish line (the link, or how to print it) and
    # the end-of-run banner, and exits non-zero at the END, not before them
    [[ "$output" == *"romp url"* ]]
    [[ "$output" == *"exiting non-zero"* ]]
    grep -qx install "$TEST_DIR/svc.log"
}

@test "install.sh: a FAILED service install fails the whole run loudly (never swallowed)" {
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_FAIL=1   # not running + install exits 1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp-service install FAILED"* ]]
    [[ "$output" == *"dashboard will be dead"* ]]
    grep -qx install "$TEST_DIR/svc.log"
}

@test "install.sh: a REFUSED service install (exit 5) ends the run saying nothing was written, with romp-service's own lines reaching the operator, no retry line and no dead-dashboard claim" {
    # Round 3 of the review (2026-09-19; correctness-2, tests-2, regression-1, kernel-2, extra5-1, extra8-1): round 2 taught
    # the install road to exit 5 (the marked update child keeps an installed unit's identity there) and branched the
    # REWRITE road on it, while this road folded the 5 into the generic failure class: a false end state (the dashboard is
    # not dead: nothing was attempted, and whatever manager is serving keeps serving) and a retry line naming the command
    # whose unmarked run re-bakes the unit from the retrying shell, the move the refusal had just prevented.
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_INSTALL_REFUSE=1   # not running + install exits 5
    mkdir -p "$HOME/.local/state/romp"
    printf 'tok123\n' > "$HOME/.local/state/romp/serve-token"            # a token on disk: another manager's, never printed here
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp-service install refused (the reason is printed above)"* ]]
    [[ "$output" != *"install refused to change the login service's identity"* ]]                 # round 4: the code is every no-write refusal, so the arm names none
    [[ "$output" == *"nothing was written or loaded"* ]]
    [[ "$output" == *"whatever manager is serving keeps serving"* ]]
    [[ "$output" == *"the login service unit on disk and this environment disagree"* ]]           # romp-service's own lines
    [[ "$output" == *"ROMP_STATE_DIR: the file carries /srv/second, this environment carries /srv/other"* ]]
    [[ "$output" != *"Retry by hand"* ]]
    [[ "$output" != *"will be dead"* ]]
    [[ "$output" != *"NOT running"* ]]
    [[ "$output" != *"install FAILED"* ]]
    # the run stops there, before the closing report and the tokened link (the convention the arms state)
    [[ "$output" != *"ROMPHOME"* ]]
    [[ "$output" != *"romp url"* ]]
    [[ "$output" != *"tok123"* ]]
    grep -qx install "$TEST_DIR/svc.log"
}

@test "install.sh: a service install refused over the manager's path (exit 5 with no identity read) ends the run the same way, pointing at romp-service's reason and claiming nothing about the identity" {
    # Round 4 of the review (2026-09-19; regression-3): exit 5 on the install road is every refusal that writes nothing, and since the
    # second pass over the round-3 addendum that includes a manager path systemd refuses as an executable name (and, under the marked
    # child, a form the reader does not read whole); the arm described every 5 as the identity refusal whose lines "name both values",
    # which this refusal never does. Worded as the rewrite road's arm is now.
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_INSTALL_REFUSE_PATH=1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp-service install refused (the reason is printed above)"* ]]
    [[ "$output" == *"nothing was written or loaded"* ]]
    [[ "$output" == *"contains a quote, a backslash or a control character"* ]]                     # romp-service's own reason reaches the operator
    [[ "$output" != *"identity"* ]]
    [[ "$output" != *"name both values"* ]]
    [[ "$output" != *"Retry by hand"* ]]
    [[ "$output" != *"will be dead"* ]]
    [[ "$output" != *"ROMPHOME"* ]]
    grep -qx install "$TEST_DIR/svc.log"
}

@test "install.sh: the closing dashboard link names the port of the state root's serve-port record, then ROMP_KERNEL_PORT, then the default" {
    # Round 3 of the review (2026-09-19, extra6-7): ROMP_KERNEL_PORT is in the kernel's update child's scrub list (the
    # rewrite compares it against the unit's line), and the closing link was its only reader here, so on a renumbered
    # install every self-update's log carried a link naming 29855, a port nothing served. The kernel's own serve-port
    # record beside the token is the authoritative answer for a caller with the state root and no shell variable.
    unset ROMP_NO_SERVICE ROMP_KERNEL_PORT
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_RUNNING=1
    mkdir -p "$ROMP_STATE_DIR"
    printf 'tok123\n' > "$ROMP_STATE_DIR/serve-token"
    printf '31855\n' > "$ROMP_STATE_DIR/serve-port"
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"http://127.0.0.1:31855/?token=tok123"* ]]
    [[ "$output" != *"29855"* ]]
    # the record outranks the environment's variable (the record is what the kernel serves on; the variable is what a
    # shell was told), and without the record the variable stands, then the default (the tokened-link case above).
    # Both port spellings are set, as the romp-service cases set them: the preflight's bin/romp-serve --print-python
    # refuses a shell whose ROMP_SERVE_PORT (a romp session's shell carries the live kernel's) disagrees with it.
    ROMP_KERNEL_PORT=31856 ROMP_SERVE_PORT=31856 ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"http://127.0.0.1:31855/?token=tok123"* ]]
    rm -f "$ROMP_STATE_DIR/serve-port"
    ROMP_KERNEL_PORT=31856 ROMP_SERVE_PORT=31856 ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"http://127.0.0.1:31856/?token=tok123"* ]]
    # a record that is not a port is skipped, never printed
    printf 'garbage\n' > "$ROMP_STATE_DIR/serve-port"
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [[ "$output" == *"http://127.0.0.1:29855/?token=tok123"* ]]
    # the ROMP_NO_SERVICE road's bare URL reads the same record
    printf '31857\n' > "$ROMP_STATE_DIR/serve-port"
    ROMP_NO_SERVICE=1 run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"http://127.0.0.1:31857/"* ]]
    [[ "$output" != *"token="* ]]
}

@test "install.sh: the closing link's port is read after the service step: a fresh install whose started kernel writes its serve-port record beside the token names that port" {
    # Mutation pass over round 3 (2026-09-19): the serve-port case above seeds the record before the run, which the
    # first read (before the service step) already sees, so the second read could go with the case green. A fresh
    # install has no record until the service it installs starts the kernel, which writes serve-port beside the token
    # it mints; the stub's install does what that kernel does, and the link must name the port it wrote.
    unset ROMP_NO_SERVICE ROMP_KERNEL_PORT
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_MINT_PORT=31855   # not running: the install road, whose install writes the record and the token
    [ ! -e "$ROMP_STATE_DIR/serve-port" ]
    [ ! -e "$ROMP_STATE_DIR/serve-token" ]
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    grep -qx install "$TEST_DIR/svc.log"
    [ "$(cat "$ROMP_STATE_DIR/serve-port")" = 31855 ]
    [[ "$output" == *"http://127.0.0.1:31855/?token=tok123"* ]]
    [[ "$output" != *"29855"* ]]
}

@test "install.sh: the failed-install line names the dashboard port the state root's record gives, not the default" {
    # Mutation pass over round 3 (2026-09-19): the FAILED case above runs with no record and no variable, where the
    # computed port and a literal 29855 read alike. A renumbered install's record names its own port.
    unset ROMP_NO_SERVICE ROMP_KERNEL_PORT
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_FAIL=1   # not running + install exits 1
    mkdir -p "$ROMP_STATE_DIR"
    printf '31855\n' > "$ROMP_STATE_DIR/serve-port"
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -ne 0 ]
    [[ "$output" == *"romp-service install FAILED"* ]]
    [[ "$output" == *"dashboard will be dead on :31855"* ]]
    [[ "$output" != *"29855"* ]]
}

# ── The closing dashboard link (the user 2026-07-25, who wanted installing alone to be
# enough to reach the dashboard) ── install.sh ends with the TOKENED link when the kernel
# has minted the token, and an honest pointer when it hasn't; it must never print a bare
# URL that bounces the first-time user to the paste-a-token login page.

@test "install.sh: the service road ends with the tokened dashboard link when the token exists" {
    # The road that found the service serving this dashboard: the token is the kernel's own, and the first click
    # signs the browser in. A guard beside the ROMP_NO_SERVICE test below, which prints no token.
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_RUNNING=1
    mkdir -p "$HOME/.local/state/romp"
    printf 'tok123\n' > "$HOME/.local/state/romp/serve-token"
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"http://127.0.0.1:29855/?token=tok123"* ]]
    [[ "$output" == *"romp url"* ]]
}

@test "install.sh: ROMP_NO_SERVICE prints no tokened link even with a token file on disk: the bare URL, and where the token comes from" {
    # The box admin's hazard review of the pull-in (2026-09-16): with ROMP_NO_SERVICE the install starts nothing, so
    # a serve-token here is another manager's (a previous install's, a hand-run romp up's), and the base printed its
    # URL, a credential into the terminal's scrollback and every scripted install's log for a dashboard this run is
    # not serving. The token is not read on this road at all.
    mkdir -p "$HOME/.local/state/romp"
    printf 'tok123\n' > "$HOME/.local/state/romp/serve-token"
    run "$ROMP_DIR/install.sh"     # setup sets ROMP_NO_SERVICE=1
    [ "$status" -eq 0 ]
    [[ "$output" != *"token="* ]]
    [[ "$output" != *"tok123"* ]]
    [[ "$output" == *"http://127.0.0.1:29855/"* ]]
    [[ "$output" == *"romp up"* ]]
    [[ "$output" == *"romp url"* ]]
    [[ "$output" == *"serve-token"* ]]
}

@test "install.sh: ROMP_NO_SERVICE with no token points at romp up, never a dead link" {
    run "$ROMP_DIR/install.sh"     # setup sets ROMP_NO_SERVICE=1; no serve-token exists
    [ "$status" -eq 0 ]
    grep -q "romp up" <<<"$output"
    grep -q "romp url" <<<"$output"
    ! grep -q "?token=" <<<"$output"
}

@test "install.sh: service up but token not minted yet, says how to get the link" {
    unset ROMP_NO_SERVICE
    _svc_stub "$TEST_DIR/romp-service"
    export ROMP_SVC_LOG="$TEST_DIR/svc.log" ROMP_SVC_RUNNING=1
    ROMP_SERVICE_BIN="$TEST_DIR/romp-service" run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    grep -q "still starting" <<<"$output"
    grep -q "romp url" <<<"$output"
    ! grep -q "?token=" <<<"$output"
}

@test "install.sh: merges into an existing settings.json without clobbering the user's own config" {
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/settings.json" <<'JSON'
{
  "model": "opus",
  "hooks": {
    "Stop": [ { "hooks": [ { "type": "command", "command": "my-own-hook.sh" } ] } ]
  }
}
JSON
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
assert s["model"] == "opus", "unrelated settings preserved"
stop = [h["command"] for r in s["hooks"]["Stop"] for h in r["hooks"]]
assert "my-own-hook.sh" in stop, stop
assert any(c.endswith("romp-wake.sh") for c in stop), stop
PY
}

# ── vscode-extension/install.sh: the build version is stamped, never committed ──
# The editor caches extension code BY VERSION, so each install must carry a strictly
# newer one; that number used to be written back into package.json and committed,
# which produced a version-churn commit per install and a package.json version that
# read like a romp release version without being one. The stamp now lives only in the
# packaged .vsix. These pin that: package.json comes back byte-identical, and the
# stamp it briefly held is strictly greater than the committed baseline.

ext_setup() {   # a throwaway copy so nothing here can touch the real extension dir
    EXT="$TEST_DIR/ext"
    mkdir -p "$EXT"
    cp "$ROMP_DIR/vscode-extension/install.sh" "$EXT/install.sh"
    printf '{\n  "name": "romp-chat-view",\n  "version": "0.4.0"\n}\n' > "$EXT/package.json"
    echo 'require("fs").writeFileSync("dist.marker","built")' > "$EXT/esbuild.js"
    # stub the toolchain the script shells out to; real node does the stamping
    mkdir -p "$TEST_DIR/stub"
    printf '#!/bin/sh\nexit 0\n' > "$TEST_DIR/stub/npm"
    printf '#!/bin/sh\ntouch romp-chat-view.vsix\nexit 0\n' > "$TEST_DIR/stub/npx"
    chmod +x "$TEST_DIR/stub/npm" "$TEST_DIR/stub/npx"
    export PATH="$TEST_DIR/stub:$PATH"
}

@test "vscode-extension/install.sh: restores package.json, leaving the committed version untouched" {
    ext_setup
    before="$(cat "$EXT/package.json")"
    ROMP_EXT_PACKAGE_ONLY=1 run "$EXT/install.sh"
    [ "$status" -eq 0 ]
    [ "$(cat "$EXT/package.json")" = "$before" ]   # byte-identical
    [ ! -f "$EXT/package.json.orig" ]              # no scratch file left behind
    [[ "$output" == *"build version -> 0.4."* ]]
    [[ "$output" == *"not committed"* ]]
}

@test "vscode-extension/install.sh: the stamped version is strictly newer than the committed baseline" {
    ext_setup
    ROMP_EXT_PACKAGE_ONLY=1 run "$EXT/install.sh"
    [ "$status" -eq 0 ]
    stamped="$(echo "$output" | sed -n 's/.*build version -> \([0-9.]*\).*/\1/p')"
    [ -n "$stamped" ]
    python3 - "$stamped" <<'PY'
import sys
base = (0, 4, 0)                       # the committed baseline in this fixture
got = tuple(int(x) for x in sys.argv[1].split("."))
assert got[:2] == base[:2], f"major.minor must not move (a lower one reads as a DOWNGRADE): {got}"
assert got > base, f"stamp must be strictly newer than the baseline: {got} !> {base}"
PY
}

@test "vscode-extension/install.sh: restores package.json even when packaging FAILS" {
    ext_setup
    printf '#!/bin/sh\nexit 3\n' > "$TEST_DIR/stub/npx"   # vsce package blows up mid-run
    chmod +x "$TEST_DIR/stub/npx"
    before="$(cat "$EXT/package.json")"
    ROMP_EXT_PACKAGE_ONLY=1 run "$EXT/install.sh"
    [ "$status" -ne 0 ]                            # the failure still surfaces
    [ "$(cat "$EXT/package.json")" = "$before" ]   # ...and the trap still restored
    [ ! -f "$EXT/package.json.orig" ]
}

# ── git pre-push identifier hook ──────────────────────────────────────
# install.sh symlinks .githooks/pre-push into the shared git hooks dir. The hook
# reads the banned strings from ~/.config/romp/private-strings.txt (so it arms
# EVERY worktree, not just the one holding an untracked scanner) and reads the
# PUSHED commits, not the working tree, which is not what gets published: each
# pushed ref's TIP tree must be clean, and each commit new to every fetched remote
# must ADD no banned line — so a leak in an intermediate commit is caught even when
# the tip is clean, while a tree that only inherits an older one is not refused.
# The same new commits' metadata is read too (their author and committer address
# domains, unless the clone is configured to use the address, and their messages;
# an annotated tag's own tagger and message likewise), which pre-push-identity.bats
# and pre-push-message.bats drive by hand. No strings file → a no-op, so a
# contributor's clone is unaffected.
# (ROMP_GITHOOK_DIR redirects install.sh's symlink target below; the behaviour
# tests copy the hook directly.)

@test "install.sh: symlinks the pre-push hook into the git hooks dir" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ -L "$ROMP_GITHOOK_DIR/pre-push" ]
    [[ "$(readlink "$ROMP_GITHOOK_DIR/pre-push")" == *"/.githooks/pre-push" ]]
}

@test "install.sh: ROMP_NO_GITHOOK skips the pre-push hook" {
    ROMP_NO_GITHOOK=1 run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ ! -e "$ROMP_GITHOOK_DIR/pre-push" ]
}

# Behaviour of the hook itself, exercised through a real `git push` to a bare
# remote, with a SYNTHETIC denylist (never a real identifier) via XDG_CONFIG_HOME.
setup_hook_repo() {
    export XDG_CONFIG_HOME="$TEST_DIR/cfg"
    # Pin the credential half OFF for the identifier tests: whether the machine
    # happens to have gitleaks on PATH must not change what they assert. The
    # gitleaks tests below turn it back on with a stub.
    export ROMP_NO_GITLEAKS=1
    mkdir -p "$XDG_CONFIG_HOME/romp"
    printf '# synthetic denylist\n\nZZBANNEDZZ\n' > "$XDG_CONFIG_HOME/romp/private-strings.txt"
    git init -q "$TEST_DIR/remote.git" --bare
    WORK="$TEST_DIR/work"
    git init -q "$WORK"
    git -C "$WORK" config user.email t@e.invalid
    git -C "$WORK" config user.name t
    cp "$ROMP_DIR/.githooks/pre-push" "$WORK/.git/hooks/pre-push"
    git -C "$WORK" remote add origin "$TEST_DIR/remote.git"
}

@test "pre-push hook: allows a push when every pushed tree is clean" {
    setup_hook_repo
    echo "clean" > "$WORK/ok.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm clean
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
}

@test "pre-push hook: blocks a push that would leak an identifier" {
    setup_hook_repo
    printf 'leak ZZBANNEDZZ here\n' > "$WORK/leak.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm leak
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"BLOCKED"* ]]
}

@test "pre-push hook: blocks a leak in an intermediate commit whose tip is clean" {
    # The regression that motivated the pushed-tree scan: a string introduced and
    # then removed mid-branch still ships in history even though the tip greps clean.
    setup_hook_repo
    printf 'leak ZZBANNEDZZ here\n' > "$WORK/leak.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm leak
    git -C "$WORK" rm -q leak.txt && git -C "$WORK" commit -qm remove
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"BLOCKED"* ]]
}

@test "pre-push hook: only commits NEW to the remote are scanned" {
    # A string that already escaped to the remote (before the denylist knew it)
    # must not block every future push — only what this push publishes counts.
    setup_hook_repo
    printf 'old ZZBANNEDZZ\n' > "$WORK/old.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm old
    git -C "$WORK" push --no-verify -q origin HEAD:main
    git -C "$WORK" rm -q old.txt && git -C "$WORK" commit -qm clean-tip
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
}

@test "pre-push hook: --no-verify bypasses the block" {
    setup_hook_repo
    printf 'leak ZZBANNEDZZ here\n' > "$WORK/leak.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm leak
    run git -C "$WORK" push --no-verify origin HEAD:main
    [ "$status" -eq 0 ]
}

@test "pre-push hook: no denylist file means the hook stays out of the way" {
    setup_hook_repo
    rm "$XDG_CONFIG_HOME/romp/private-strings.txt"
    printf 'would leak ZZBANNEDZZ\n' > "$WORK/leak.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm leak
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
}

@test "pre-push hook: a denylist of only comments and blanks bans nothing" {
    setup_hook_repo
    printf '# just a comment\n\n   \n' > "$XDG_CONFIG_HOME/romp/private-strings.txt"
    printf 'ZZBANNEDZZ\n' > "$WORK/leak.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm leak
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
}

# ── the credential half of the same hook (gitleaks) ───────────────────────
# A denylist can only catch strings you can enumerate, and nobody can enumerate
# a token before it leaks, so the hook also runs gitleaks over the pushed
# commits. These tests stub the scanner via ROMP_GITLEAKS: what is under test is
# the hook's wiring (which commits it hands over, what it does with the verdict),
# not gitleaks' own rules, and a stub keeps the suite deterministic on a machine
# that has never installed it. The rules and .gitleaks.toml are exercised for
# real in tests/gitleaks-config.bats and by CI's secret-scan job.

setup_gitleaks_stub() {   # <exit-code>: records its args, then exits that code
    # 0 is a clean scan; 2 is a finding (the hook asks gitleaks to report one so,
    # apart from its own failures); 1 is gitleaks failing.
    unset ROMP_NO_GITLEAKS
    GL_ARGS="$TEST_DIR/gitleaks.args"
    export ROMP_GITLEAKS="$TEST_DIR/gitleaks-stub"
    cat > "$ROMP_GITLEAKS" <<EOF
#!/usr/bin/env bash
echo "\$@" >> "$GL_ARGS"
echo "stub scanner ran" >&2
exit $1
EOF
    chmod +x "$ROMP_GITLEAKS"
}

@test "pre-push hook: a credential found in a pushed commit blocks the push" {
    setup_hook_repo
    setup_gitleaks_stub 2
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"BLOCKED"* ]]
    # The advice has to say rotate: a secret in a commit is already compromised,
    # and deleting it in a later commit does not un-publish it.
    [[ "$output" == *"ROTATE"* ]]
}

@test "pre-push hook: a scanner that fails refuses the push and says so, not that it found something" {
    # gitleaks exits 1 when it cannot run (an unreadable config, say) and 2, at
    # the hook's asking, on a finding. Publishing unscanned would be the silent
    # failure the scan exists to prevent, so a failure refuses too; but the
    # advice is to fix the scanner, not to rotate a credential nobody found.
    setup_hook_repo
    setup_gitleaks_stub 1
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"BLOCKED"* ]]
    [[ "$output" == *"could not scan"* ]]
    [[ "$output" != *"ROTATE"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
}

@test "pre-push hook: a credential is still refused on a clone with NO denylist" {
    # Any contributor's clone: no private-strings file. The identifier scan has
    # nothing to read there and stands down; the credential scan must run all
    # the same, so a hook that ends when the denylist is missing is wrong.
    setup_hook_repo
    rm "$XDG_CONFIG_HOME/romp/private-strings.txt"
    setup_gitleaks_stub 2
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [ -f "$GL_ARGS" ]      # the scanner really ran
}

@test "pre-push hook: a credential is still refused when the denylist bans nothing" {
    # The other way the identifier scan stands down: a file of comments and blanks.
    setup_hook_repo
    printf '# just a comment\n\n   \n' > "$XDG_CONFIG_HOME/romp/private-strings.txt"
    setup_gitleaks_stub 2
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"gitleaks found a credential"* ]]
}

@test "pre-push hook: a clean scan lets the push through" {
    setup_hook_repo
    setup_gitleaks_stub 0
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
    [ -f "$GL_ARGS" ]      # it really did run
    # --redact keeps the value out of the terminal, -v names the file, line and
    # rule (without it gitleaks prints a count). tests/gitleaks-config.bats
    # checks both against the real scanner; this pins the wiring.
    [[ "$(cat "$GL_ARGS")" == *"--redact -v"* ]]
    [[ "$(cat "$GL_ARGS")" != *"--config"* ]]   # no .gitleaks.toml in this repo: default rules
}

@test "pre-push hook: the repo's .gitleaks.toml is handed to the scanner by name" {
    # Explicit, not left to gitleaks' own lookup: with no --config it reads a
    # GITLEAKS_CONFIG from the environment before the source root, and a
    # developer's own config would replace the repo's rules.
    setup_hook_repo
    setup_gitleaks_stub 0
    printf '[extend]\nuseDefault = true\n' > "$WORK/.gitleaks.toml"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm rules
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
    root="$(git -C "$WORK" rev-parse --show-toplevel)"
    [[ "$(cat "$GL_ARGS")" == *"--config $root/.gitleaks.toml"* ]]
}

@test "pre-push hook: only the commits being pushed are handed to the scanner" {
    # The same rule the identifier scan follows: a secret that already escaped
    # must not block every later push, and the tip alone is not what ships.
    setup_hook_repo
    setup_gitleaks_stub 0
    echo "old" > "$WORK/old.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm old
    git -C "$WORK" push --no-verify -q origin HEAD:main
    old_sha="$(git -C "$WORK" rev-parse HEAD)"
    echo "new" > "$WORK/new.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm new
    new_sha="$(git -C "$WORK" rev-parse HEAD)"

    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
    # The hook hands gitleaks the range the identifier scan walks: the pushed
    # tip, minus every ref any fetched remote already has and the remote's old
    # tip (see rev_range in the hook).
    [[ "$(cat "$GL_ARGS")" == *"--log-opts=$new_sha --not --remotes $old_sha"* ]]
}

@test "pre-push hook: the scan asks git to show merge-commit diffs" {
    # `gitleaks git` runs `git log -p`, which shows NO diff for a merge commit by default, so a
    # secret introduced only in a conflict resolution would be handed to the scanner as empty. The
    # hook must pass --diff-merges=first-parent so merge content is actually scanned. Wiring only;
    # the real "the secret is caught" proof is in gitleaks-config.bats against real gitleaks.
    setup_hook_repo
    setup_gitleaks_stub 0
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
    [[ "$(cat "$GL_ARGS")" == *"--diff-merges=first-parent"* ]]
}

@test "pre-push hook: a brand-new branch is scanned from its first commit" {
    setup_hook_repo
    setup_gitleaks_stub 0
    echo "first" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm first
    sha="$(git -C "$WORK" rev-parse HEAD)"
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
    [[ "$(cat "$GL_ARGS")" == *"--log-opts=$sha --not --remotes"* ]]
}

@test "pre-push hook: a force-push over a remote tip this clone never fetched still scans" {
    # Another clone moves the branch; this one force-pushes without fetching,
    # so the remote's tip is a sha git cannot find here. gitleaks handed that
    # range logs git's error, scans no commits and exits 0, and a secret in the
    # push would go out unscanned. The hook falls back the way the identifier
    # scan does, to everything the pushed tip reaches: the unknown sha is not
    # in what the scanner is given.
    setup_hook_repo
    setup_gitleaks_stub 0
    echo "base" > "$WORK/base.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm base
    git -C "$WORK" push --no-verify -q origin HEAD:main
    git clone -q -b main "$TEST_DIR/remote.git" "$TEST_DIR/other"
    echo "other" > "$TEST_DIR/other/other.txt"
    git -C "$TEST_DIR/other" add -A && git -C "$TEST_DIR/other" commit -qm other
    git -C "$TEST_DIR/other" push -q origin HEAD:main
    other_sha="$(git -C "$TEST_DIR/other" rev-parse HEAD)"
    echo "mine" > "$WORK/mine.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm mine
    sha="$(git -C "$WORK" rev-parse HEAD)"
    run git -C "$WORK" push --force origin HEAD:main
    [ "$status" -eq 0 ]
    [[ "$(cat "$GL_ARGS")" == *"--log-opts=$sha --diff-merges=first-parent"* ]]
    [[ "$(cat "$GL_ARGS")" != *"$other_sha"* ]]
}

@test "pre-push hook: deleting a remote branch consults no scanner" {
    # A deletion pushes nothing (the local sha is all zeros); handing that to
    # gitleaks would only make it log a git error and scan nothing.
    setup_hook_repo
    setup_gitleaks_stub 0
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    git -C "$WORK" push --no-verify -q origin HEAD:feat
    run git -C "$WORK" push origin :feat
    [ "$status" -eq 0 ]
    [ ! -e "$GL_ARGS" ]
}

@test "pre-push hook: no gitleaks installed says so out loud and still pushes" {
    # Requiring an install to push would break every clone that never asked for
    # the scanner. Loud, not blocking.
    setup_hook_repo
    unset ROMP_NO_GITLEAKS
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    ROMP_GITLEAKS="$TEST_DIR/not-a-binary" run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
    [[ "$output" == *"gitleaks not installed"* ]]
    [[ "$output" == *"WITHOUT a secret scan"* ]]
}

@test "pre-push hook: ROMP_NO_GITLEAKS=1 silences the scan and its notice" {
    setup_hook_repo
    setup_gitleaks_stub 2                 # a scanner that WOULD refuse, if consulted
    export ROMP_NO_GITLEAKS=1             # the pin setup_hook_repo sets; the stub helper unset it
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -eq 0 ]
    [ ! -e "$GL_ARGS" ]                   # never consulted
    [[ "$output" != *"secret scan"* ]]    # and no notice about one
    [[ "$output" != *"romp pre-push"* ]]  # a clean push under the pin says nothing at all
}

@test "pre-push hook: --no-verify bypasses the credential block too" {
    setup_hook_repo
    setup_gitleaks_stub 2
    echo "whatever" > "$WORK/f.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm work
    run git -C "$WORK" push --no-verify origin HEAD:main
    [ "$status" -eq 0 ]
}

@test "pre-push hook: both scanners report before the push is refused" {
    # One push, two findings: the developer should learn about both in one go
    # rather than fixing the identifier, pushing again, and meeting the secret.
    setup_hook_repo
    setup_gitleaks_stub 2
    printf 'leak ZZBANNEDZZ here\n' > "$WORK/leak.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm leak
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"personal identifier"* ]]
    [[ "$output" == *"gitleaks found a credential"* ]]
    # One bypass line, after both verdicts.
    [ "$(grep -c -- 'git push --no-verify' <<<"$output")" -eq 1 ]
    [[ "${output##*personal identifier}" == *"git push --no-verify"* ]]
    [[ "${output##*gitleaks found a credential}" == *"git push --no-verify"* ]]
}

# ─── the tracked-changes tooling (vendor/track-changents) ─────────────

TC_LINKS="track-edit.mjs track-comment.mjs track-reply.mjs track-config.mjs track-guard.mjs"

guard_groups() {   # PreToolUse groups holding track-guard.mjs: "<count> <matcher> <timeout> <async>" per group
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
for g in s.get("hooks", {}).get("PreToolUse", []):
    hs = [h for h in g.get("hooks", []) if h.get("command", "").endswith("track-guard.mjs")]
    if hs:
        print(len(hs), g.get("matcher"), hs[0].get("timeout"), hs[0].get("async"))
PY
}

@test "install.sh: links the tracked-changes CLIs, guard and skill from the vendored copy" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Symlinked the tracked-changes tooling"* ]]
    for tc in track-edit track-comment track-reply track-config; do
        [ -L "$HOME/.claude/hooks/$tc.mjs" ]
        [ "$(readlink "$HOME/.claude/hooks/$tc.mjs")" = "$ROMP_DIR/vendor/track-changents/cli/$tc.mjs" ]
    done
    [ "$(readlink "$HOME/.claude/hooks/track-guard.mjs")" = "$ROMP_DIR/vendor/track-changents/hooks/track-guard.mjs" ]
    [ "$(readlink "$HOME/.claude/skills/tracked-changes")" = "$ROMP_DIR/vendor/track-changents/skill" ]
    [ -f "$HOME/.claude/skills/tracked-changes/SKILL.md" ]
    [[ "$output" != *"Replaced links"* ]]   # nothing was there to replace
}

@test "install.sh: registers the guard once, in a PreToolUse group whose matcher is exactly Write|Edit|MultiEdit, synchronous, timeout 10" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"PreToolUse:track-guard.mjs"* ]]
    [ "$(count_cmd PreToolUse track-guard.mjs)" = "1" ]
    [ "$(guard_groups)" = "1 Write|Edit|MultiEdit 10 False" ]
    # the command is the ~ form the uninstaller and the other romp entries use
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
groups = s["hooks"]["PreToolUse"]
# the vendored guard's group holds it alone; the Bash-side guard (the test below) has a group of its own
cmds = [h["command"] for g in groups if g.get("matcher") == "Write|Edit|MultiEdit" for h in g["hooks"]]
assert cmds == ["~/.claude/hooks/track-guard.mjs"], cmds
# romp's matcher-less hooks did not land in the guard's group, and no empty group was left behind
assert all(g.get("hooks") for e in s["hooks"].values() for g in e), s["hooks"]
PY
}

@test "install.sh: registers the Bash-side track guard once, in a PreToolUse group whose matcher is exactly Bash, synchronous, timeout 10" {
    # The vendored guard sees Write/Edit/MultiEdit only; a session in auto mode writes files through
    # Bash (cp, tee, heredocs, sed -i), which it never sees (plans/file-review.md, decision 47). romp's
    # own hook on the Bash tool closes that path, and it is registered by the same merge.
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"PreToolUse:romp-track-bash-guard.mjs"* ]]
    [ "$(count_cmd PreToolUse romp-track-bash-guard.mjs)" = "1" ]
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
groups = [g for g in s["hooks"]["PreToolUse"] if any(h["command"].endswith("romp-track-bash-guard.mjs") for h in g["hooks"])]
assert len(groups) == 1, groups
assert groups[0]["matcher"] == "Bash", groups[0]
assert groups[0]["hooks"] == [{"type": "command", "command": "~/.claude/hooks/romp-track-bash-guard.mjs", "timeout": 10, "async": False}], groups[0]
PY
    # a second run adds no second entry and no second group
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [ "$(count_cmd PreToolUse romp-track-bash-guard.mjs)" = "1" ]
    [ "$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(sum(1 for g in s["hooks"]["PreToolUse"] if g.get("matcher")=="Bash"))' "$HOME/.claude/settings.json")" = "1" ]
}

@test "install.sh: a second run adds no second guard entry, no second group, and reports no replacement" {
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"already registered"* ]]
    [[ "$output" != *"Replaced links"* ]]
    [ "$(count_cmd PreToolUse track-guard.mjs)" = "1" ]
    [ "$(guard_groups | wc -l)" = "1" ]
    for tc in $TC_LINKS; do
        [ -L "$HOME/.claude/hooks/$tc" ]
    done
    [ -L "$HOME/.claude/skills/tracked-changes" ]
    # the dir-symlink was replaced, not followed: no stray link INSIDE the vendored skill dir
    [ ! -e "$ROMP_DIR/vendor/track-changents/skill/tracked-changes" ]
}

@test "install.sh: a guard entry written by track-changents' own installer (expanded home path, no async key) counts as registered" {
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/settings.json" <<JSON
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit|MultiEdit",
        "hooks": [ { "type": "command", "command": "$HOME/.claude/hooks/track-guard.mjs", "timeout": 10 } ] }
    ]
  }
}
JSON
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" != *"PreToolUse:track-guard.mjs"* ]]
    [ "$(count_cmd PreToolUse track-guard.mjs)" = "1" ]
    [ "$(guard_groups | wc -l)" = "1" ]
    # the existing entry is left exactly as it was; the Bash-side guard's own group stands beside it
    python3 - "$HOME/.claude/settings.json" "$HOME" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
g = s["hooks"]["PreToolUse"]
assert [x.get("matcher") for x in g] == ["Write|Edit|MultiEdit", "Bash"], g
assert g[0]["hooks"] == [{"type": "command", "command": sys.argv[2] + "/.claude/hooks/track-guard.mjs", "timeout": 10}], g
assert [h["command"] for h in g[1]["hooks"]] == ["~/.claude/hooks/romp-track-bash-guard.mjs"], g
PY
}

@test "install.sh: the guard gets its own group beside a user's PreToolUse group with another matcher" {
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [ { "matcher": "Bash", "hooks": [ { "type": "command", "command": "my-bash-check.sh" } ] } ]
  }
}
JSON
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    python3 - "$HOME/.claude/settings.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
groups = s["hooks"]["PreToolUse"]
assert [g.get("matcher") for g in groups] == ["Bash", "Write|Edit|MultiEdit"], groups
# the merge keys groups by matcher: the user's Bash group keeps its hook and gains romp's Bash-side
# guard after it (hooks in a group run in parallel; nothing of the user's is moved or reordered)
assert groups[0]["hooks"][0] == {"type": "command", "command": "my-bash-check.sh"}, groups[0]
assert [h["command"] for h in groups[0]["hooks"]] == ["my-bash-check.sh", "~/.claude/hooks/romp-track-bash-guard.mjs"], groups[0]
assert [h["command"] for h in groups[1]["hooks"]] == ["~/.claude/hooks/track-guard.mjs"], groups[1]
PY
}

@test "install.sh: links into another track-changents checkout are re-pointed at the vendored copy, and the replacement is reported" {
    # The shape track-changents' own installer leaves behind: every link into a checkout of that project.
    other="$TEST_DIR/track-changents"
    mkdir -p "$other/cli" "$other/hooks" "$other/skill" "$HOME/.claude/hooks" "$HOME/.claude/skills"
    for tc in track-edit track-comment track-reply track-config; do
        echo "// old" > "$other/cli/$tc.mjs"
        ln -s "$other/cli/$tc.mjs" "$HOME/.claude/hooks/$tc.mjs"
    done
    echo "// old" > "$other/hooks/track-guard.mjs"
    ln -s "$other/hooks/track-guard.mjs" "$HOME/.claude/hooks/track-guard.mjs"
    echo "old skill" > "$other/skill/SKILL.md"
    ln -s "$other/skill" "$HOME/.claude/skills/tracked-changes"

    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Replaced links from another track-changents install"* ]]
    [[ "$output" == *"track-edit.mjs (was $other/cli/track-edit.mjs)"* ]]
    [[ "$output" == *"track-guard.mjs (was"* ]]
    [[ "$output" == *"tracked-changes (was"* ]]
    for tc in track-edit track-comment track-reply track-config; do
        [ "$(readlink "$HOME/.claude/hooks/$tc.mjs")" = "$ROMP_DIR/vendor/track-changents/cli/$tc.mjs" ]
    done
    [ "$(readlink "$HOME/.claude/hooks/track-guard.mjs")" = "$ROMP_DIR/vendor/track-changents/hooks/track-guard.mjs" ]
    [ "$(readlink "$HOME/.claude/skills/tracked-changes")" = "$ROMP_DIR/vendor/track-changents/skill" ]
    [ -f "$other/skill/SKILL.md" ]   # the checkout itself is untouched
    [ "$(cat "$other/cli/track-edit.mjs")" = "// old" ]

    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" != *"Replaced links"* ]]   # settled: nothing to report the second time
}

@test "install.sh: a real file named like a track-changents CLI is left alone, with a notice" {
    mkdir -p "$HOME/.claude/hooks"
    echo "mine" > "$HOME/.claude/hooks/track-edit.mjs"
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"track-edit.mjs is a real file, not a link"* ]]
    [ ! -L "$HOME/.claude/hooks/track-edit.mjs" ]
    [ "$(cat "$HOME/.claude/hooks/track-edit.mjs")" = "mine" ]
    [ -L "$HOME/.claude/hooks/track-comment.mjs" ]   # its neighbours are linked as usual
    [ -L "$HOME/.claude/hooks/track-guard.mjs" ]
}

@test "install.sh: the linked CLIs run through the symlink and resolve their imports from the vendored copy" {
    command -v node >/dev/null || skip "node not installed"
    run "$ROMP_DIR/install.sh"
    [ "$status" -eq 0 ]
    vault="$TEST_DIR/notes-api"
    mkdir -p "$vault/.git/hooks" "$vault/docs"
    echo "# Report" > "$vault/docs/report.md"
    # track-config's exit status IS its answer: 1 = off, 0 = on (see the skill)
    run node "$HOME/.claude/hooks/track-config.mjs" --file "$vault/docs/report.md"
    [ "$status" -eq 1 ]
    [ "$output" = "off" ]
    mkdir -p "$vault/.trackchanges"
    echo '{"v":2,"tracked":["docs/"]}' > "$vault/.trackchanges/config.json"
    run node "$HOME/.claude/hooks/track-config.mjs" --file "$vault/docs/report.md"
    [ "$status" -eq 0 ]
    [ "$output" = "on" ]
}
