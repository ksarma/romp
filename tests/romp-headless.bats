#!/usr/bin/env bats

# `romp send|interrupt|end <session> [text]` — headless session control through the kernel
# HTTP API (2026-07-05: interrupt/end existed only as browser WS ops, so a runaway session had no
# headless stop). Bare words since round 3 (2026-07-25); the dashed spellings stay as SILENT
# aliases because agent-facing text delivered before then names them. A tiny one-shot python
# server stands in for the kernel; failures must be LOUD (non-zero exit + a message), never a
# silent curl swallow.

ROMP_SCRIPT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp"

setup() {
    TEST_DIR="$(mktemp -d)"
}

teardown() {
    [ -n "${SERVER_PID:-}" ] && kill "$SERVER_PID" 2>/dev/null
    rm -rf "$TEST_DIR"
}

# Start a one-shot fake kernel; writes its port to $TEST_DIR/port and its request to $TEST_DIR/req.
# $2 (optional): the HTTP status the fake answers (default 200): a 4xx or 5xx with a JSON or text body drives the
# CLI's reason relay (fork PR 433; the refusal cases below). $3 (optional): seconds to hold the answer AFTER reading
# the request (default 0): a kernel that took the message but answers late (the boot-storm shape the exit-code test
# below drives, upstream 2026-09-12).
start_fake_kernel() {   # $1 = response body, $2 = HTTP status (default 200), $3 = answer delay in seconds (default 0)
    python3 - "$1" "$TEST_DIR" "${2:-200}" "${3:-0}" <<'PY' &
import http.server, json, sys, time
body, tdir, status, delay = sys.argv[1].encode(), sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        with open(tdir + "/req", "w") as f:
            f.write(self.path + "\n" + self.rfile.read(n).decode())
        if delay:
            time.sleep(delay)
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass
class _Bound(http.server.HTTPServer):   # no reverse lookup of the bind address: HTTPServer.server_bind runs socket.getfqdn(host), about 36 s on GitHub's macOS images
    def server_bind(self):
        import socketserver
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]
s = _Bound(("127.0.0.1", 0), H)
with open(tdir + "/port", "w") as f:
    f.write(str(s.server_address[1]))
s.handle_request()
PY
    SERVER_PID=$!
    until [ -s "$TEST_DIR/port" ]; do sleep 0.05; done
    export ROMP_KERNEL_PORT="$(cat "$TEST_DIR/port")"
}

@test "romp interrupt <name> POSTs /interrupt and exits 0 on ok" {
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" interrupt runaway
    [ "$status" -eq 0 ]
    [[ "$output" == *"ok (runaway)"* ]]
    grep -q "^/interrupt$" <(head -1 "$TEST_DIR/req")
    grep -q '"name": "runaway"' "$TEST_DIR/req"
}

@test "romp end stops a session through /end" {
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" end done-with-it
    [ "$status" -eq 0 ]
    grep -q "^/end$" <(head -1 "$TEST_DIR/req")
}

@test "romp end self resolves through ROMP_SID and defers to idle by default" {
    # a session closing ITSELF after its work (the user 2026-08-15): self = the spawn-frozen sid,
    # and the kernel kills at the turn's settle so the goodbye lands first
    start_fake_kernel '{"ok": true}'
    ROMP_SID="11111111-2222-3333-4444-555555555555" run "$ROMP_SCRIPT" end self
    [ "$status" -eq 0 ]
    grep -q "^/end$" <(head -1 "$TEST_DIR/req")
    grep -q '"id": "11111111-2222-3333-4444-555555555555"' "$TEST_DIR/req"
    grep -q '"when": "idle"' "$TEST_DIR/req"
}

@test "romp end self --now skips the deferral; self outside a session fails loudly" {
    start_fake_kernel '{"ok": true}'
    ROMP_SID="11111111-2222-3333-4444-555555555555" run "$ROMP_SCRIPT" end self --now
    [ "$status" -eq 0 ]
    run grep -q '"when"' "$TEST_DIR/req"
    [ "$status" -ne 0 ]
    ROMP_SID="" run "$ROMP_SCRIPT" end self
    [ "$status" -eq 2 ]
    [[ "$output" == *"only works from inside a romp SDK session"* ]]
}

@test "romp end --when-idle says deferred when the kernel deferred, ok when it killed at once" {
    # the kernel's when:idle arm answers {"ok": true, "deferred": true} and a far kernel's deferral is
    # relayed as is; the CLI printed the same bare "ok (web)" for that and for an immediate kill, so a
    # caller could not tell a session gone from one still finishing its turn (review round 4, 2026-09-09)
    start_fake_kernel '{"ok": true, "deferred": true}'
    run "$ROMP_SCRIPT" end web --when-idle
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp end: deferred (web), ends when idle"* ]]
    [[ "$output" != *"romp end: ok"* ]]
    grep -q '"when": "idle"' "$TEST_DIR/req"
    rm -f "$TEST_DIR/port" "$TEST_DIR/req"          # the fake is one-shot: a second one needs a fresh port file
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" end web --when-idle
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp end: ok (web)"* ]]
    [[ "$output" != *"deferred"* ]]
}

@test "the dashed spellings are silent aliases: --send works and says nothing about it" {
    # Agent-facing text delivered before 2026-07-25 (postal reply footers, skill
    # docs in old transcripts) names the dashed forms; they must keep working
    # with no retirement noise.
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" --send helper "hello"
    [ "$status" -eq 0 ]
    [[ "$output" != *"retired"* ]]
    grep -q "^/send$" <(head -1 "$TEST_DIR/req")
    grep -q '"name": "helper"' "$TEST_DIR/req"
}

@test "romp send ships JSON-safe text" {
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" send helper 'fix the "thing" \ and this'
    [ "$status" -eq 0 ]
    grep -q "^/send$" <(head -1 "$TEST_DIR/req")
    python3 - "$TEST_DIR/req" <<'PY'
import json, sys
body = open(sys.argv[1]).read().split("\n", 1)[1]
assert json.loads(body) == {"name": "helper", "text": 'fix the "thing" \\ and this'}, body
PY
}

@test "romp send --tag appends the render-hint marker; bad labels and missing text exit 2" {
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" send helper --tag kickoff 'boot brief for the run'
    [ "$status" -eq 0 ]
    python3 - "$TEST_DIR/req" <<'PY'
import json, sys
body = open(sys.argv[1]).read().split("\n", 1)[1]
d = json.loads(body)
assert d["name"] == "helper", d
assert d["text"] == "boot brief for the run\n\n<!-- romp-tag: kickoff -->", d
PY
    run "$ROMP_SCRIPT" send helper --tag 'two words' 'text'
    [ "$status" -eq 2 ]
    [[ "$output" == *"--tag must be one word"* ]]
    run "$ROMP_SCRIPT" send helper --tag kickoff
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp send"* ]]
}

@test "romp send reports queued when the kernel parked it" {
    # a sender inside the target's own open turn (an agent sending itself a slash command) must learn
    # the command has not run yet (2026-09-03: a parked /clear read 'ok' and never fired)
    start_fake_kernel '{"ok": true, "queued": true}'
    run "$ROMP_SCRIPT" send busy1 "/frobnicate now"
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp send: queued (busy1)"* ]]
    [[ "$output" == *"delivers when the session is quiet"* ]]
}

@test "romp send still says ok on queued:false and on a bare ok reply" {
    start_fake_kernel '{"ok": true, "queued": false}'
    run "$ROMP_SCRIPT" send web "hello"
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp send: ok (web)"* ]]
}

@test "a kernel refusal is loud: non-zero exit + the kernel's answer" {
    start_fake_kernel '{"ok": false, "error": "id or name required"}'
    run "$ROMP_SCRIPT" interrupt ghost
    [ "$status" -eq 1 ]
    [[ "$output" == *"refused"* ]]
    [[ "$output" == *"id or name required"* ]]   # the kernel's own words, not the raw body
}

@test "an unreachable kernel is loud, not a silent curl swallow" {
    ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" interrupt anyone
    [ "$status" -eq 1 ]
    [[ "$output" == *"kernel not reachable"* ]]
}

@test "usage errors exit 2: missing session name, send without text" {
    run "$ROMP_SCRIPT" interrupt
    [ "$status" -eq 2 ]
    run "$ROMP_SCRIPT" send lonely
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp send"* ]]
}

@test "an unknown session is a 404 the CLI surfaces by its reason, exit 1" {
    # the kernel used to mint a phantom sid for a typo and answer ok:true; it now refuses with a 404
    # whose error names the name. curl -f swallowed every 4xx body into "kernel not reachable", so the
    # status is read off the response instead and the reason is printed
    start_fake_kernel '{"ok": false, "error": "no live session named '"'"'typo'"'"'"}' 404
    run "$ROMP_SCRIPT" end typo
    [ "$status" -eq 1 ]
    [[ "$output" == *"no live session named 'typo'"* ]]
    [[ "$output" != *"kernel not reachable"* ]]
    grep -q '"name": "typo"' "$TEST_DIR/req"
}

@test "a non-JSON refusal body is quoted with its status, and the printf fallback says the same when the parser dies" {
    # the kernel's own refusals carry {ok:false, error}; a proxy's plain-text 502, or a JSON body with no
    # error field, has no reason to lift, so the status and the raw answer are printed instead
    start_fake_kernel 'gateway down' 502
    run "$ROMP_SCRIPT" interrupt web
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp interrupt: the kernel answered HTTP 502: gateway down"* ]]
    [[ "$output" != *"kernel not reachable"* ]]
    rm -f "$TEST_DIR/port" "$TEST_DIR/req"          # the fake is one-shot: a second one needs a fresh port file
    start_fake_kernel '{"ok": false}' 500
    run "$ROMP_SCRIPT" end web
    [ "$status" -eq 1 ]
    [[ "$output" == *'romp end: the kernel answered HTTP 500: {"ok": false}'* ]]
    # the parser itself failing (a python3 that dies on the reason script, and on nothing else: the
    # payload build in the same block needs the real one) falls to the printf line with the same words
    _real="$(command -v python3)"
    mkdir -p "$TEST_DIR/shim"
    cat > "$TEST_DIR/shim/python3" <<SHIM
#!/usr/bin/env bash
[[ "\$*" == *"the kernel answered HTTP"* ]] && exit 1
exec "$_real" "\$@"
SHIM
    chmod +x "$TEST_DIR/shim/python3"
    rm -f "$TEST_DIR/port" "$TEST_DIR/req"
    start_fake_kernel 'gateway down' 503
    PATH="$TEST_DIR/shim:$PATH" run "$ROMP_SCRIPT" interrupt web
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp interrupt: the kernel answered HTTP 503: gateway down"* ]]
}

@test "a verb's own flag in the session slot is usage and exit 2, never a session named --now" {
    # `romp end --now web` used to POST {"name": "--now"} (and, since the gate, come back "no live session
    # named '--now'"); the compact verb answers its own misplaced flags with usage, so these do too. Every
    # other dash-leading word is still a session name
    ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" end --now web
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp end <session>|self [--now|--when-idle]"* ]]
    [[ "$output" != *"kernel not reachable"* ]]
    ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" end --when-idle web
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp end"* ]]
    # `romp send --tag <label> <session> <text>` is the documented leading form since upstream's 2026-09-12
    # change (bin/romp pre-parses the tag ahead of the session slot), so it is neither usage nor a session
    # named --tag: the label is taken and the POST goes out, here to a port nothing answers on
    ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" send --tag kick web hello there
    [ "$status" -eq 1 ]
    [[ "$output" == *"romp send: kernel not reachable on :1"* ]]
    [[ "$output" != *"usage: romp send"* ]]
    # --tag is end's session name and --now is send's: neither verb owns the other's flag
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" end --tag
    [ "$status" -eq 0 ]
    grep -q '"name": "--tag"' "$TEST_DIR/req"
    rm -f "$TEST_DIR/port" "$TEST_DIR/req"
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" send -oddname hello
    [ "$status" -eq 0 ]
    grep -q '"name": "-oddname"' "$TEST_DIR/req"
}

@test "the bare verb prints the usage line --help prints, exit 2, without a kernel" {
    # `romp end` with no session printed a bare `usage: romp end <session> ` (a trailing space from an
    # empty substitution) while --help spelled the full form; one usage string per verb now (review round 2)
    for verb in send interrupt end; do
        ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" "$verb" --help
        [ "$status" -eq 0 ]
        _first="${lines[0]}"
        [[ "$_first" == "usage: romp $verb "* ]]
        ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" "$verb"
        [ "$status" -eq 2 ]
        [ "$output" == "$_first" ]
    done
}

@test "romp send, interrupt and end each answer --help without a kernel" {
    # `romp end --help` used to POST a session named --help (the phantom-sid bug from the other side)
    for verb in send interrupt end; do
        ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" "$verb" --help
        [ "$status" -eq 0 ]
        [[ "$output" == *"usage: romp $verb <session>"* ]]
        [[ "$output" != *"kernel not reachable"* ]]
        ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" "$verb" -h
        [ "$status" -eq 0 ]
        [[ "$output" == *"usage: romp $verb <session>"* ]]
    done
    run "$ROMP_SCRIPT" send --help
    [[ "$output" == *"--tag <label>"* ]]
    run "$ROMP_SCRIPT" end --help
    [[ "$output" == *"--now"* ]]
    [[ "$output" == *"self"* ]]
}

# ── romp compact (2026-08-30, the user via the dashboard team) ──
# First-class in-place compaction: POSTs /compact, tells the caller which arm ran (now vs queued),
# refuses honestly. The one-shot fake kernel captures the request like the send/interrupt tests.

@test "romp compact <name> POSTs /compact and says compacting now" {
    start_fake_kernel '{"ok": true, "queued": false}'
    run "$ROMP_SCRIPT" compact bigctx
    [ "$status" -eq 0 ]
    [[ "$output" == *"compacting bigctx now"* ]]
    grep -q "^/compact$" <(head -1 "$TEST_DIR/req")
    grep -q '"name": "bigctx"' "$TEST_DIR/req"
}

@test "romp compact reports queued when a turn is open" {
    start_fake_kernel '{"ok": true, "queued": true}'
    run "$ROMP_SCRIPT" compact busy1
    [ "$status" -eq 0 ]
    [[ "$output" == *"queued for busy1"* ]]
    [[ "$output" == *"fires the moment the current turn ends"* ]]
}

@test "romp compact refusals are loud: dead session, unreachable kernel, usage" {
    start_fake_kernel '{"ok": false, "error": "no live session named '"'"'ghost'"'"' — a dead session has no context to compact; revive it first"}'
    run "$ROMP_SCRIPT" compact ghost
    [ "$status" -eq 1 ]
    [[ "$output" == *"revive it first"* ]]
    ROMP_KERNEL_PORT=1 run "$ROMP_SCRIPT" compact anyone
    [ "$status" -eq 1 ]
    [[ "$output" == *"kernel not reachable"* ]]
    run "$ROMP_SCRIPT" compact
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp compact"* ]]
    run "$ROMP_SCRIPT" compact who --timeout notanumber
    [ "$status" -eq 2 ]
}

@test "romp help lists compact beside the other session verbs" {
    run "$ROMP_SCRIPT" help
    [[ "$output" == *"romp compact <session>"* ]]
}

# The queued+--wait path died before its first poll (set -e killed the arming assignment — review
# find, 2026-08-30) and the --wait fake below is MULTI-request: POST answers queued, then GET
# /sessions walks quiet → compacting → quiet, the armed-only-after-quiet sequence. A leading-zero
# --timeout was octal to (( )) and the timeout never fired; a remote response refuses --wait
# honestly (the local /sessions never lists remote rows).

start_wait_kernel() {   # $1 = POST response body; GETs serve quiet,compacting,compacting,quiet…
    python3 - "$1" "$TEST_DIR" <<'PY' &
import http.server, json, sys
body, tdir = sys.argv[1].encode(), sys.argv[2]
hits = {"n": 0}
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); self.rfile.read(n)
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        hits["n"] += 1
        rows = [{"id": "11111111-2222-3333-4444-555555555555", "name": "busy1",
                 "compacting": hits["n"] in (2, 3)}]
        b = json.dumps(rows).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def log_message(self, *a):
        pass
class _Bound(http.server.HTTPServer):   # no reverse lookup of the bind address: HTTPServer.server_bind runs socket.getfqdn(host), about 36 s on GitHub's macOS images
    def server_bind(self):
        import socketserver
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]
s = _Bound(("127.0.0.1", 0), H)
with open(tdir + "/port", "w") as f:
    f.write(str(s.server_address[1]))
for _ in range(12):
    s.handle_request()
PY
    SERVER_PID=$!
    until [ -s "$TEST_DIR/port" ]; do sleep 0.05; done
    export ROMP_KERNEL_PORT="$(cat "$TEST_DIR/port")"
}

@test "romp compact --wait on a QUEUED compaction survives set -e, arms after quiet, and completes" {
    start_wait_kernel '{"ok": true, "queued": true}'
    run "$ROMP_SCRIPT" compact busy1 --wait --timeout 30
    [ "$status" -eq 0 ]
    [[ "$output" == *"queued for busy1"* ]]
    [[ "$output" == *"done — busy1 compacted"* ]]
}

@test "romp compact --wait refuses a leading-zero timeout (octal to the poll arithmetic)" {
    run "$ROMP_SCRIPT" compact who --timeout 08
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp compact"* ]]
}

@test "romp compact --wait on a remote session refuses honestly instead of reporting it dead" {
    start_fake_kernel '{"ok": true, "queued": false, "remote": "TESTHOST-B"}'
    run "$ROMP_SCRIPT" compact farswitch --wait --timeout 10
    [ "$status" -eq 1 ]
    [[ "$output" == *"compacting farswitch now"* ]]
    [[ "$output" == *"can't follow a remote session from here (it lives on TESTHOST-B)"* ]]
    [[ "$output" == *"still requested"* ]]
}

@test "a dash-leading session name reaches the kernel like send does; the verb's own flags still get usage" {
    start_fake_kernel '{"ok": true, "queued": false}'
    run "$ROMP_SCRIPT" compact -oddname
    [ "$status" -eq 0 ]
    grep -q '"name": "-oddname"' "$TEST_DIR/req"
    run "$ROMP_SCRIPT" compact --wait
    [ "$status" -eq 2 ]
}

@test "romp send: a kernel that took the request but answers late exits 3 and says the message may be delivered" {
    # 2026-09-12: this shape wore "kernel not reachable" and exit 1, so a retry-on-exit caller re-sent a delivered
    # message on every try (nine copies of one wake, twenty seconds apart, after a restart). The request must be
    # on the fake kernel's disk (it was taken), the exit distinct from a refusal, and the words honest.
    start_fake_kernel '{"ok": true}' 200 3
    ROMP_KERNEL_HTTP_TIMEOUT_S=1 run "$ROMP_SCRIPT" send helper 'a wake the kernel took slowly'
    [ "$status" -eq 3 ]
    [[ "$output" == *"took the request but did not answer within 1s"* ]]
    [[ "$output" == *"may already have delivered the message"* ]]
    [[ "$output" == *"do not retry blindly"* ]]
    [[ "$output" != *"not reachable"* ]]
    grep -q "^/send$" <(head -1 "$TEST_DIR/req")
}

@test "romp billing: a kernel that took the pick but answers late exits 3 and says it may already have acted" {
    # round 1 of the billing verb's review (2026-09-19; its tests-6): the verb copies the send and end verbs' exit-3 arm
    # (bin/romp _bl_posted) and the reference states the contract, but no leg reached it; a mutation from 3 to 1 there left
    # the suite green. The serve token rides the environment (the verb reads it before the POST and refuses an empty one
    # with exit 1, so without it this leg would assert 3 and get 1); the fake holds its answer past the 1 s cap
    start_fake_kernel '{"ok": true, "session": "web", "pick": "login", "reconnect": "now", "cut": false, "queued": false}' 200 3
    ROMP_SERVE_TOKEN=t ROMP_KERNEL_HTTP_TIMEOUT_S=1 run "$ROMP_SCRIPT" billing web login
    [ "$status" -eq 3 ]
    [[ "$output" == *"took the request but did not answer within 1s"* ]]
    [[ "$output" == *"it may already have acted on it"* ]]
    [[ "$output" == *"do not retry blindly"* ]]
    [[ "$output" != *"not reachable"* ]]
    grep -q "^/billing$" <(head -1 "$TEST_DIR/req")
}

@test "romp billing: a kernel nobody is listening on is 'not reachable', exit 1, and no pick was made" {
    # the second arm of the same contract (tests-6): the request never left, so the exit is a refusal's and the curl code is named
    export ROMP_KERNEL_PORT=1
    ROMP_SERVE_TOKEN=t run "$ROMP_SCRIPT" billing web login
    [ "$status" -eq 1 ]
    [[ "$output" == *"kernel not reachable"* ]]
    [[ "$output" == *"[curl exit"* ]]
}

@test "romp send: a kernel nobody is listening on is 'not reachable', exit 1, and nothing was sent" {
    # a port with no listener: the request never left, so the old message and code stand, and the curl code is named
    export ROMP_KERNEL_PORT=1
    run "$ROMP_SCRIPT" send helper 'a message nobody took'
    [ "$status" -eq 1 ]
    [[ "$output" == *"kernel not reachable"* ]]
    [[ "$output" == *"[curl exit"* ]]
}

@test "romp send --tag ahead of the session name tags the send instead of addressing a session called --tag" {
    # 2026-09-12: a timer's `romp send --tag <label> <session> <text>` read `--tag` AS the session name four
    # times in one night and the kernel refused a paste to a target that does not exist, while the timer read
    # "sent". A verb's own flag is never a session name; the leading form tags and addresses like the trailing one.
    start_fake_kernel '{"ok": true}'
    run "$ROMP_SCRIPT" send --tag wake helper 'the ten-minute pulse'
    [ "$status" -eq 0 ]
    python3 - "$TEST_DIR/req" <<'PY'
import json, sys
body = open(sys.argv[1]).read().split("\n", 1)[1]
d = json.loads(body)
assert d["name"] == "helper", d
assert d["text"] == "the ten-minute pulse\n\n<!-- romp-tag: wake -->", d
PY
    run "$ROMP_SCRIPT" send --tag
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp send"* ]]
    run "$ROMP_SCRIPT" send --tag wake
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp send"* ]]
}
