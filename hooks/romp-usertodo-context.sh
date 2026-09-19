#!/usr/bin/env bash
# romp-usertodo-context.sh: SessionStart hook (sources: resume, compact, clear). Hands a romp session its
# OPEN requests to the person it works for back as PASSIVE context: the agent's own outstanding notes with
# their ids and one instruction (withdraw what is met or moot), so an agent whose working memory was wiped
# remembers what it asked for (plans/user-todos.md, segment C). A compaction drops everything the session
# knew about its open requests, and the CLI re-fires SessionStart with source=compact for exactly this; a
# resume (a kernel restart, a revival) is the same loss; a /clear keeps the stable sid the request store is
# keyed on while the agent forgets its rows, and the agent is the only actor that can withdraw them (the
# person's alternative is Dismiss by hand, one row at a time). additionalContext costs no turn, and a session
# with nothing open gets nothing at all.
#
# The KERNEL renders the words (POST /usertodo/context, a read-only route on the store's owner), never this
# hook, so tests/test_injected_voice.py scans the exact text a session receives.
#
# Five gates in cost order, then one round trip, then one render. Every exit is 0 and silent: a SessionStart
# hook must never fail the turn, and the requests stay on the person's own surfaces regardless.
#   1. ROMP_SUMMARIZING: the judge's nested claude has no requests of its own (the postal hooks' gate).
#   2. ROMP_SID, and its shape: a romp session is one launched with ROMP_SID in its environment (the kernel
#      sets it on every CLI it spawns). The sid is interpolated into a JSON body below, so a mangled or
#      crafted value dies here, not on the wire.
#   3. THE SWITCH STAT: requests from sessions are off by default and per install (the kernel's
#      user-todos-enabled.json under the state root). No file is the shipped default, off, and it costs
#      nothing here: the stat runs before the payload is read and before anything that costs a process. The
#      hook reads no CONTENT. The kernel is the one authority on the file's value (false, malformed and
#      unreadable all read off there, said once), and its answer's `enabled` field silences this hook, so a
#      hand-edited file can never make the hook and the kernel disagree. A present file saying false costs
#      one bounded round trip per resume, compaction or clear: the price of one reader.
#   4. The source: resume, compact or clear. startup stays silent (a fresh sid has no rows; a kernel-restart
#      resume arrives as resume) and so does fork (a born fork has a new sid with no rows).
#   5. THE IDENTITY GATE, the postal hooks' (romp-postal-context.sh, romp-postal-ensure.sh): THIS CLI must be
#      the session ROMP_SID names, not a process that inherited the variable. Everything a session's Bash
#      tool runs carries its ROMP_SID, so a `claude -p` a session spawned would otherwise pass gates 1 to 4
#      on its mid-run compaction and take the PARENT's requests into its own context: a leak across
#      conversations and a prompt to withdraw rows it does not own. The CLI names itself in the payload's
#      session_id (CLAUDE_CODE_SESSION_ID stands in for a payload without one); the check reads the SDK
#      registry's row for the sid (sdk/<ROMP_SID>.json under the state root), whose lastSid is the
#      conversation the kernel last saw the CLI on. By source: a clear passes on the reg's existence (a
#      /clear rotates the CLI onto a new id, and the reg learns it only after this hook has run; nothing a
#      session runs from its Bash tool fires a clear); resume and compact need the id to be the sid or the
#      reg's lastSid. One difference from the siblings, on purpose: their empty-lastSid allowance is for a
#      first startup, ahead of the kernel's init-time write, and startup is excluded at gate 4, so an empty
#      lastSid passes nothing here. No id, no reg, or an unreadable reg: nothing to check against, silence.
set -uo pipefail

[[ -n "${ROMP_SUMMARIZING:-}" ]] && exit 0
[[ -n "${ROMP_SID:-}" ]] || exit 0
[[ "$ROMP_SID" =~ ^[0-9a-zA-Z][0-9a-zA-Z-]*$ ]] || exit 0
state="${ROMP_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/romp}"
[[ -e "$state/user-todos-enabled.json" ]] || exit 0       # the kernel's USER_TODOS_SWITCH_FILE; existence only

input="$(cat)"
[[ "$input" =~ \"source\":[[:space:]]*\"([^\"]+)\" ]] && start_kind="${BASH_REMATCH[1]}" || start_kind=""
case "$start_kind" in resume|compact|clear) ;; *) exit 0 ;; esac

if [[ "$input" =~ \"session_id\":[[:space:]]*\"([^\"]+)\" ]]; then cli_id="${BASH_REMATCH[1]}"
else cli_id="${CLAUDE_CODE_SESSION_ID:-}"; fi
[[ -n "$cli_id" ]] || exit 0
if [[ "$cli_id" != "$ROMP_SID" ]]; then
    reg="$state/sdk/$ROMP_SID.json"
    last_sid="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1])).get("lastSid") or "")' "$reg" 2>/dev/null)" || exit 0
    if [[ "$start_kind" == "clear" ]]; then :                     # the reg exists; its lastSid is still the previous id
    else [[ -n "$last_sid" && "$last_sid" == "$cli_id" ]] || exit 0; fi
fi

# Either spelling of the kernel's listen port (bin/romp-serve exports both); ROMP_SERVE_PORT first, so a
# session under an aux kernel asks ITS kernel. The token as the kernel resolves it: env override, else the
# 0600 state file. It travels on STDIN as a curl config, never in argv (/proc/<pid>/cmdline is world-readable),
# escaped for curl's quoted config syntax, the romp-wake.sh way. Any failure (no kernel, a 403, a timeout)
# is silence.
port="${ROMP_SERVE_PORT:-${ROMP_KERNEL_PORT:-29855}}"
tok="${ROMP_SERVE_TOKEN:-}"
[[ -n "$tok" ]] || tok="$(cat "$state/serve-token" 2>/dev/null || true)"
esc="${tok//\\/\\\\}"; esc="${esc//\"/\\\"}"
resp="$(printf 'header = "X-Romp-Token: %s"\n' "$esc" \
    | curl -sf -m 3 --config - -X POST "http://127.0.0.1:${port}/usertodo/context" \
           -H "Content-Type: application/json" --data "{\"id\":\"$ROMP_SID\"}" 2>/dev/null)" || exit 0
[[ -n "$resp" ]] || exit 0

# The render. `enabled` false means nothing, whatever block rides along (the kernel's word on the switch); a
# missing `enabled` reads as on (an older kernel answering first in a mixed upgrade: the block alone decides);
# an empty or whitespace block means nothing (no noise for a session with nothing open); else one JSON line.
python3 - "$resp" <<'PY'
import json, sys
try:
    d = json.loads(sys.argv[1])
    block = "" if not isinstance(d, dict) or d.get("enabled") is False else str(d.get("block") or "").strip()
except Exception:
    block = ""
if block:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": block}}))
PY
exit 0
