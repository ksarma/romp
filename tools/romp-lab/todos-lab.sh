#!/usr/bin/env bash
# todos-lab.sh: the user-todos phase of romp-lab (README.md), a sibling of lab.sh rather than a mode
# in it. The phase needs more than a --todos-only flag: the user-todos switch turned ON in the lab
# state before the kernel boots, a synthetic project with files the session can name, a postal bus on
# its own port (the switch is read by both), video and asset directories for the GIF cuts, and a
# stricter environment scrub than the other phases run under. Folding those into lab.sh would change
# the preamble every other phase runs; the shared part is copied instead and kept in step by hand.
#
# HERMETICITY FIRST, as in lab.sh: the state root moves to a temp dir BEFORE any romp code runs; the
# kernel gets its own token, its own kernel port and its own postal port; nothing here may touch live
# state, the live postal bus, the live manager, a systemd unit, or any visible display.
#
#   tools/romp-lab/todos-lab.sh --keep --out=DIR
#
# LAB_ROOT (default $TMPDIR, else /tmp) holds the temp root, so a box whose /tmp is crowded can point
# it elsewhere; LAB_MODEL picks the reply model as lab.sh documents (default: the cheapest Haiku the
# menu offers). --out=DIR copies the finished assets (PNG, GIF, the context-block text, marks.json,
# the record) outside the repo. --keep keeps the temp root (kernel.log, shots/, video/, assets/); a
# failing run keeps it regardless.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEEP=0
OUT=""
for a in "$@"; do case "$a" in
  --keep) KEEP=1 ;;
  --out=*) OUT="${a#--out=}" ;;
  --todos-only) ;;      # the only phase this script runs; accepted for symmetry with lab.sh
esac; done

LAB_ROOT="${LAB_ROOT:-${TMPDIR:-/tmp}}"
mkdir -p "$LAB_ROOT"
LAB="$(mktemp -d "$LAB_ROOT/romp-lab-XXXXXX")"
mkdir -p "$LAB/state" "$LAB/shots" "$LAB/video" "$LAB/assets" "$LAB/notes-api/routes"
# a synthetic project whose basename the statusline shows: notes-api
cat > "$LAB/notes-api/README.md" <<'EOF'
# notes-api

A small HTTP API for personal notes. A synthetic scratch project for a demo; nothing here is real.
EOF
cat > "$LAB/notes-api/routes/notes.py" <<'EOF'
"""Unauthenticated note routes: list, get, create. Login is not wired yet."""

NOTES = {}


def list_notes():
    return list(NOTES.values())


def get_note(note_id):
    return NOTES.get(note_id)


def create_note(body):
    note_id = str(len(NOTES) + 1)
    NOTES[note_id] = {"id": note_id, "body": body}
    return NOTES[note_id]
EOF

export XDG_STATE_HOME="$LAB/state"
unset ROMP_STATE_DIR || true
# never the machine's real manager: poisoned to a dead port, not unset (absent maps to the live port)
export ROMP_MANAGER_PORT=1
# never watch, name or address the live deployment: a lab started from a shell inside a running
# session inherits the live manager's pid (the kernel exits when it dies), the session's own identity,
# and the CLI's own environment (a messaging socket, a session id) that a lab CLI must not join
unset ROMP_MANAGER_PID ROMP_SID ROMP_SESSION_NAME || true
for v in $(env | grep -o '^CLAUDE[A-Z_]*' | sort -u); do unset "$v" || true; done
# no transient systemd scopes for the lab's CLIs: the lab starts no systemd unit
export ROMP_CLI_SCOPE=0
# the SDK venv is PACKAGES, not state: a symlink shares bytes only, nothing here writes into it
REAL_VENV="${HOME}/.local/state/romp/sdkvenv"
if [ -d "$REAL_VENV" ]; then
  mkdir -p "$LAB/state/romp"
  ln -s "$REAL_VENV" "$LAB/state/romp/sdkvenv"
fi
export ROMP_KERNEL_NO_OPEN=1
export ROMP_SERVE_TOKEN="labtok-$(head -c8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
freeport() { python3 - <<'PY'
import socket
s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()
PY
}
PORT=$(freeport)
POSTAL_PORT=$(freeport)
while [ "$POSTAL_PORT" = "$PORT" ]; do POSTAL_PORT=$(freeport); done
export ROMP_KERNEL_PORT="$PORT"
export ROMP_SERVE_PORT="$PORT"          # the hooks resolve ROMP_SERVE_PORT first: they must ask THIS kernel
export ROMP_POSTAL_PORT="$POSTAL_PORT"  # the lab kernel spawns its own bus; the live bus is never adopted

# the per-install switch, ON in the lab state before the kernel starts (kernel USER_TODOS_SWITCH_FILE,
# read by the postal bus under the same name), and a cheaper triage judge for the segment placement
mkdir -p "$LAB/state/romp"
printf '{"enabled": true, "gt": %s}\n' "$(date +%s)000" > "$LAB/state/romp/user-todos-enabled.json"
printf 'haiku\n' > "$LAB/state/romp/judge-model"

# serve the FRESH build of THIS tree, and a copy of it (ROMP_DIST_DIR), as lab.sh does
( cd "$ROOT/vscode-extension" && node esbuild.js >/dev/null 2>&1 )
mkdir -p "$LAB/dist"
cp "$ROOT/vscode-extension/dist/"*.js "$LAB/dist/" 2>/dev/null || true
cp "$ROOT/vscode-extension/dist/"*.css "$LAB/dist/" 2>/dev/null || true
if [ -d "$ROOT/vscode-extension/dist/fonts" ]; then cp -r "$ROOT/vscode-extension/dist/fonts" "$LAB/dist/fonts"; fi
export ROMP_DIST_DIR="$LAB/dist"
export ROMP_WS_KEEPALIVE=2

KERNEL_BIN="$ROOT/bin/romp-kernel"
"$KERNEL_BIN" > "$LAB/kernel.log" 2>&1 &
KPID=$!
cleanup() {
  # the restart phase relaunches the kernel and records the new pid
  [ -f "$LAB/kernel.pid" ] && KPID="$(cat "$LAB/kernel.pid")"
  kill "$KPID" 2>/dev/null || true
  wait "$KPID" 2>/dev/null || true
  # the lab's own postal bus outlives the kernel (start_new_session): stop it by its pidfile
  if [ -f "$LAB/state/romp/postal/server.pid" ]; then
    kill "$(cat "$LAB/state/romp/postal/server.pid")" 2>/dev/null || true
  fi
  if [ "$KEEP" = 1 ]; then echo "kept: $LAB (kernel.log, shots/, video/, assets/)"; else rm -rf "$LAB"; fi
}
trap cleanup EXIT

for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then break; fi
  sleep 0.5
  kill -0 "$KPID" 2>/dev/null || { echo "kernel died at boot: $LAB/kernel.log:"; tail -20 "$LAB/kernel.log"; exit 1; }
done
curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null || { echo "kernel never became healthy"; exit 1; }
echo "lab kernel up on :$PORT (postal :$POSTAL_PORT, state: $LAB/state, project: $LAB/notes-api)"

RC=0
LAB_DIR="$LAB" PORT="$PORT" TOKEN="$ROMP_SERVE_TOKEN" PROJECT_DIR="$LAB/notes-api" KPID="$KPID" \
  KERNEL_BIN="$KERNEL_BIN" OUT_DIR="$OUT" HOOK="$ROOT/hooks/romp-usertodo-context.sh" \
  node "$ROOT/tools/romp-lab/todos-loop.mjs" || RC=$?
echo "todos loop exit: $RC (shots: $LAB/shots, assets: $LAB/assets)"
[ -f "$LAB/kernel.pid" ] && KPID="$(cat "$LAB/kernel.pid")"
[ "$RC" = 0 ] || KEEP=1
exit "$RC"
