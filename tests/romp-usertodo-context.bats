#!/usr/bin/env bats

# romp-usertodo-context.sh is a SessionStart hook (plans/user-todos.md, segment C): on the resume,
# compact and clear sources it asks the kernel (POST /usertodo/context) for the session's open
# requests and emits the rendered block as additionalContext, the agent's own outstanding notes to
# the person it works for, so it can withdraw the ones that are met or moot after its working memory
# was wiped. Five gates in cost order, then one round trip, then one render; every exit is 0 and
# silent: the summarizer's nested CLI, no ROMP_SID (or a mangled one), no switch file under the state
# root (a stat, before the payload is read: off costs nothing), a source that is not resume, compact
# or clear, and the postal hooks' identity gate (the CLI's id must be the sid or the SDK registry's
# lastSid for it, a clear passing on the reg's existence), so a `claude -p` a session runs from its
# Bash tool never takes its parent's requests. It must never fail the turn, kernel down included.

setup() {
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"; mkdir -p "$HOME"
    MOCK="$TEST_DIR/mock"; mkdir -p "$MOCK"
    export CURL_LOG="$TEST_DIR/curl.log"
    export CURL_STDIN="$TEST_DIR/curl.stdin"
    # Mock curl: capture the stdin config (the token travels there, never argv), log argv, answer with
    # $CURL_RESPONSE, exit with $CURL_EXIT. This hook READS curl's stdout, so the mock answers synchronously.
    cat > "$MOCK/curl" <<'MOCK'
#!/usr/bin/env bash
cat > "$CURL_STDIN" 2>/dev/null
echo "curl $*" >> "$CURL_LOG"
printf '%s' "${CURL_RESPONSE:-}"
exit "${CURL_EXIT:-0}"
MOCK
    chmod +x "$MOCK/curl"
    export PATH="$MOCK:$PATH"
    # Clear the inherited romp env: running this suite from inside a romp session carries ROMP_SID and
    # ROMP_SERVE_PORT (the "outside a romp session" and default-port cases would flip), ROMP_STATE_DIR
    # outranks XDG_STATE_HOME for the switch file and the reg, and CLAUDE_CODE_SESSION_ID stands in for
    # a payload without a session_id and would leak a developer's own id into the no-id cases.
    unset ROMP_STATE_DIR ROMP_SID ROMP_SERVE_PORT ROMP_KERNEL_PORT ROMP_SERVE_TOKEN ROMP_SUMMARIZING
    unset CLAUDE_CODE_SESSION_ID
    export XDG_STATE_HOME="$TEST_DIR/state"
    mkdir -p "$XDG_STATE_HOME/romp"
    switch_on
    export CURL_RESPONSE='{"ok": true, "enabled": true, "block": "Notes you still have open with the person you work for"}'
    SID="11111111-2222-3333-4444-555555555555"     # the romp sid: ROMP_SID, and a fresh spawn's CLI id
    FSID="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"    # the conversation the reg's lastSid names (a resume)
    OTHER="99999999-8888-7777-6666-555555555555"   # an id in neither place: a child the session ran
    CLEARED="cccccccc-dddd-4eee-8fff-000000000000"  # the id a /clear rotated the CLI onto; the reg learns it only after the clear SessionStart
    HOOK="$(cd "$(dirname "$BATS_TEST_FILENAME")/../hooks" && pwd)/romp-usertodo-context.sh"
}

teardown() { rm -rf "$TEST_DIR"; }

# the per-install switch file under the state root; the hook stats it and never reads its content
switch_on() { printf '{"enabled": true, "gt": 1}' > "${1:-$XDG_STATE_HOME/romp}/user-todos-enabled.json"; }
# the SDK registry row for a sid with the given lastSid: write_reg <lastSid> [<sid>] [<state root>]
write_reg() {
    local root="${3:-$XDG_STATE_HOME/romp}"
    mkdir -p "$root/sdk"
    printf '{"sid": "%s", "name": "web", "cwd": "/tmp/notes-api", "mode": "acceptEdits", "lastSid": "%s", "alive": true}' \
        "${2:-$SID}" "$1" > "$root/sdk/${2:-$SID}.json"
}
# $1 the CLI's session_id, $2 the start's source (startup | resume | clear | compact | fork)
payload() { printf '{"session_id":"%s","transcript_path":"/tmp/notes-api/t.jsonl","hook_event_name":"SessionStart","source":"%s"}' "$1" "$2"; }
# a payload with a source and no session_id (CLAUDE_CODE_SESSION_ID stands in)
payload_noid() { printf '{"transcript_path":"/tmp/notes-api/t.jsonl","hook_event_name":"SessionStart","source":"%s"}' "$1"; }
# $1 the SessionStart payload on the hook's stdin
run_hook() { run bash -c 'printf "%s" "$1" | "$2"' _ "$1" "$HOOK"; }
# every file under the state root with its checksum: the hook must leave the tree byte-identical
snap_state() { (cd "$XDG_STATE_HOME" && find . -type f | LC_ALL=C sort | while IFS= read -r f; do printf '%s ' "$f"; cksum < "$f"; done); }

@test "on resume it emits the kernel's block as additionalContext" {
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"hookEventName": "SessionStart"'* ]]
    [[ "$output" == *'"additionalContext"'* ]]
    [[ "$output" == *'Notes you still have open with the person you work for'* ]]
}

@test "on compact it asks /usertodo/context and emits: the post-compaction re-surface" {
    ROMP_SID="$SID" run_hook "$(payload "$SID" compact)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    grep -q '/usertodo/context' "$CURL_LOG"
}

@test "on clear it asks and emits: a cleared session's rows stand and only its agent can withdraw them" {
    ROMP_SID="$SID" run_hook "$(payload "$SID" clear)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    grep -q '/usertodo/context' "$CURL_LOG"
}

@test "startup and fork are silent: no query at all" {
    for src in startup fork; do
        ROMP_SID="$SID" run_hook "$(payload "$SID" "$src")"
        [ "$status" -eq 0 ]
        [ -z "$output" ]
    done
    [ ! -e "$CURL_LOG" ]
}

@test "a payload with no source at all is silent, no query" {
    ROMP_SID="$SID" run_hook '{"session_id":"'"$SID"'"}'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "the body carries ROMP_SID, the store's key, not the payload's session_id" {
    # the payload's id is the CLI's conversation, which a resume moves off the stable sid; the reg for
    # ROMP_SID names that conversation as its lastSid, so the identity gate passes and the sid is asked for
    write_reg "$FSID" "$OTHER"
    ROMP_SID="$OTHER" run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    grep -q "$OTHER" "$CURL_LOG"
    run grep -q "$FSID" "$CURL_LOG"
    [ "$status" -ne 0 ]
}

@test "the request is a JSON POST of {id} with the content type set" {
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    grep -q -- '-X POST' "$CURL_LOG"
    grep -q 'Content-Type: application/json' "$CURL_LOG"
    grep -q -- "--data {\"id\":\"$SID\"}" "$CURL_LOG"
}

@test "an empty block means no output at all: a session with nothing open gets nothing" {
    export CURL_RESPONSE='{"ok": true, "enabled": true, "block": ""}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "a whitespace-only or missing block is nothing to say too" {
    export CURL_RESPONSE='{"ok": true, "enabled": true, "block": " \n "}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    export CURL_RESPONSE='{"ok": true, "enabled": true}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" compact)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "the kernel saying the feature is off means no output, whatever block rides along; it did ask" {
    export CURL_RESPONSE='{"ok": true, "enabled": false, "block": "Notes you still have open with the person you work for"}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    grep -q '/usertodo/context' "$CURL_LOG"
}

@test "enabled true emits the block; a missing enabled field is read as on (an older kernel)" {
    export CURL_RESPONSE='{"ok": true, "enabled": true, "block": "Notes you still have open with the person you work for"}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    export CURL_RESPONSE='{"ok": true, "block": "Notes you still have open with the person you work for"}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
}

@test "a kernel answer that is not JSON emits nothing and never fails the turn" {
    export CURL_RESPONSE='<html>502 Bad Gateway</html>'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "outside a romp session (no ROMP_SID, or an empty one) it is silent and never queries" {
    run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    ROMP_SID="" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "the summarizer's nested CLI is silent, no query" {
    ROMP_SID="$SID" ROMP_SUMMARIZING=1 run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "a mangled ROMP_SID never reaches the wire and creates no file" {
    # the sid is interpolated into a JSON body: the shape gate keeps a crafted value out of the request
    ROMP_SID='11111111"</dev/null;touch pwned;' run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
    [ ! -e "$TEST_DIR/pwned" ] && [ ! -e "pwned" ] && [ ! -e "$HOME/pwned" ]
}

@test "the shape gate stands alone: a mangled sid the identity gate would pass still never reaches the wire" {
    # the case above exits at the identity gate as well (the payload's id is not the mangled sid, and the reg
    # for it does not exist), so it cannot tell the two gates apart. Here the identity gate passes: first by its
    # shortcut (the payload's id IS the sid), then by a reg planted where a sid with a path in it would point
    # (sdk/<sid>.json resolved against the state root), so only the shape gate stands between the value and
    # the request body, and the reg path it bounds
    ROMP_SID='11111111;touch pwned' run_hook "$(payload '11111111;touch pwned' resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
    [ ! -e "$TEST_DIR/pwned" ] && [ ! -e "pwned" ] && [ ! -e "$HOME/pwned" ]
    write_reg "$FSID" "../outside"       # lands at romp/outside.json: the path a sid of ../outside would read
    [ -f "$XDG_STATE_HOME/romp/outside.json" ]
    ROMP_SID='../outside' run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "a failed or refused query never fails the turn and emits nothing" {
    export CURL_EXIT=22 CURL_RESPONSE=""
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "the kernel being unreachable (real curl, dead port) never fails the turn" {
    rm "$MOCK/curl"
    ROMP_SID="$SID" ROMP_SERVE_PORT=1 run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "it asks /usertodo/context on the configured kernel port" {
    ROMP_SID="$SID" ROMP_SERVE_PORT=7777 run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    grep -q 'http://127.0.0.1:7777/usertodo/context' "$CURL_LOG"
}

@test "it defaults to port 29855 and honours ROMP_KERNEL_PORT, the other spelling" {
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    grep -q 'http://127.0.0.1:29855/usertodo/context' "$CURL_LOG"
    : > "$CURL_LOG"
    ROMP_SID="$SID" ROMP_KERNEL_PORT=7778 run_hook "$(payload "$SID" resume)"
    grep -q 'http://127.0.0.1:7778/usertodo/context' "$CURL_LOG"
}

@test "the serve token rides stdin as a curl config, never argv" {
    # /proc/<pid>/cmdline is world-readable (the romp-wake.sh rule)
    ROMP_SID="$SID" ROMP_SERVE_TOKEN="TESTTOKENDONOTUSE" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    run grep -q "TESTTOKENDONOTUSE" "$CURL_LOG"
    [ "$status" -ne 0 ]
    grep -q -- "--config" "$CURL_LOG"
    grep -q "X-Romp-Token: TESTTOKENDONOTUSE" "$CURL_STDIN"
}

@test "a token with curl-config metacharacters arrives escaped, the romp-wake.sh way" {
    ROMP_SID="$SID" ROMP_SERVE_TOKEN='ab"c\d' run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    run cat "$CURL_STDIN"
    [ "$output" = 'header = "X-Romp-Token: ab\"c\\d"' ]
}

@test "the serve token falls back to the state root's serve-token file" {
    printf 'tok-from-file\n' > "$XDG_STATE_HOME/romp/serve-token"
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    grep -q 'X-Romp-Token: tok-from-file' "$CURL_STDIN"
}

@test "a multi-line block round-trips into valid hook JSON" {
    export CURL_RESPONSE='{"ok": true, "enabled": true, "block": "Notes you still have open:\n- Need the auth-scheme decision (ut-11111111, opened 2026-08-20)\n\nIf one is met or moot now, withdraw it (withdraw_user_todo); otherwise leave it standing."}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    # the emitted line is JSON Claude Code parses: prove it round-trips with the block intact
    python3 - "$output" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
ctx = d["hookSpecificOutput"]["additionalContext"]
assert d["hookSpecificOutput"]["hookEventName"] == "SessionStart"
assert "withdraw_user_todo" in ctx and "\n\n" in ctx, ctx
PY
}

# ── the switch stat ──────────────────────────────────────────────────────────────────────────────

@test "no switch file: silent and no query on resume, compact and clear (off costs nothing)" {
    rm "$XDG_STATE_HOME/romp/user-todos-enabled.json"
    for src in resume compact clear; do
        ROMP_SID="$SID" run_hook "$(payload "$SID" "$src")"
        [ "$status" -eq 0 ]
        [ -z "$output" ]
    done
    [ ! -e "$CURL_LOG" ]
}

@test "a switch file saying false: the hook reads no content, so it asks, and the kernel's answer silences it" {
    printf '{"enabled": false, "gt": 1}' > "$XDG_STATE_HOME/romp/user-todos-enabled.json"
    export CURL_RESPONSE='{"ok": true, "enabled": false, "block": ""}'
    ROMP_SID="$SID" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    grep -q '/usertodo/context' "$CURL_LOG"
}

@test "ROMP_STATE_DIR outranks XDG_STATE_HOME for the switch file and the reg" {
    # the switch file sits only under XDG_STATE_HOME: with ROMP_STATE_DIR set the stat misses, silence
    ROOT2="$TEST_DIR/root2"; mkdir -p "$ROOT2"
    ROMP_SID="$SID" ROMP_STATE_DIR="$ROOT2" run_hook "$(payload "$SID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
    # the switch file under ROMP_STATE_DIR, and the reg the identity gate reads under it too: emits
    switch_on "$ROOT2"
    write_reg "$FSID" "$SID" "$ROOT2"
    ROMP_SID="$SID" ROMP_STATE_DIR="$ROOT2" run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    # the same reg only under XDG_STATE_HOME: the gate reads ROMP_STATE_DIR, finds no reg, silence
    rm "$ROOT2/sdk/$SID.json"
    write_reg "$FSID"
    ROMP_SID="$SID" ROMP_STATE_DIR="$ROOT2" run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ── the identity gate (the postal hooks' three rules, less the startup allowance) ────────────────

@test "a CLI the session itself ran (an id in neither place) gets nothing on resume or compact" {
    # a `claude -p` from the session's Bash tool inherits ROMP_SID; its own session_id is a fresh uuid, and
    # its mid-run auto-compaction comes back as a compact start under that id
    write_reg "$FSID"
    ROMP_SID="$SID" run_hook "$(payload "$OTHER" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    ROMP_SID="$SID" run_hook "$(payload "$OTHER" compact)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "the reg's lastSid passes on resume and on compact: the conversation the CLI continued or kept" {
    write_reg "$FSID"
    ROMP_SID="$SID" run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    ROMP_SID="$SID" run_hook "$(payload "$FSID" compact)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
}

@test "a /clear start with a new id and an existing reg passes: the reg learns the id only after this hook" {
    write_reg "$FSID"
    ROMP_SID="$SID" run_hook "$(payload "$CLEARED" clear)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
}

@test "a /clear start with no reg for the sid gets nothing, and the hook does not fail" {
    ROMP_SID="$SID" run_hook "$(payload "$CLEARED" clear)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "an unreadable reg is the same silence on resume and on clear, never a failed turn" {
    mkdir -p "$XDG_STATE_HOME/romp/sdk"; printf 'not json' > "$XDG_STATE_HOME/romp/sdk/$SID.json"
    ROMP_SID="$SID" run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    ROMP_SID="$SID" run_hook "$(payload "$CLEARED" clear)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "a payload without session_id: CLAUDE_CODE_SESSION_ID stands in, and with neither the hook is silent" {
    write_reg "$FSID"
    ROMP_SID="$SID" CLAUDE_CODE_SESSION_ID="$FSID" run_hook "$(payload_noid resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    rm -f "$CURL_LOG"
    ROMP_SID="$SID" run_hook "$(payload_noid resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    # on clear the reg's existence alone passes the gate, so an empty id must be refused BEFORE the gate: with no
    # id there is nothing to check, and the reg being there says nothing about which CLI this is
    ROMP_SID="$SID" run_hook "$(payload_noid clear)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "a payload with spaces after its colons is read the same: the regexes tolerate whitespace" {
    # the CLI writes compact JSON today; the read must not depend on it, the postal hooks' regex
    ROMP_SID="$SID" run_hook '{"session_id": "'"$SID"'", "hook_event_name": "SessionStart", "source": "resume"}'
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    grep -q -- "--data {\"id\":\"$SID\"}" "$CURL_LOG"
}

@test "an empty lastSid passes nothing here: startup is excluded before the gate, so its allowance has no case" {
    # the postal hooks let an empty lastSid through at startup only (the reg as spawn mints it, ahead of the
    # kernel's init-time write); this hook never fires at startup, so by resume or compact the field must hold the id
    write_reg ""
    ROMP_SID="$SID" run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    ROMP_SID="$SID" run_hook "$(payload "$FSID" compact)"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$CURL_LOG" ]
}

@test "the hook never writes under the state root" {
    write_reg "$FSID"
    printf 'tok-from-file\n' > "$XDG_STATE_HOME/romp/serve-token"
    before="$(snap_state)"
    ROMP_SID="$SID" run_hook "$(payload "$FSID" resume)"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"additionalContext"'* ]]
    [ "$(snap_state)" = "$before" ]
}
