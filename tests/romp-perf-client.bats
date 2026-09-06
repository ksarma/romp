#!/usr/bin/env bats

# `romp perf client [--minutes <n>] [--json]` — the browser side of `romp perf`: folds the surface "perf"
# rows the pane bundles post (ui/webview/perf-telemetry.ts: one "minute" row per pane per minute, a
# "slowframe" row per handler at or over 100 ms) out of $STATE/client-diag.jsonl, per dashboard id (the
# first eight characters of the wid) and pane app, over the last <n> minutes, and prints one screen.
#
# Nothing here touches a kernel: the verb reads the file directly, and a curl on PATH that fails proves
# it never tried. The fixture is synthetic (placeholder wids, the pane apps the kernel names, invented
# numbers), written relative to the wall clock so the window arithmetic is exercised for real. Every
# refusal is loud and specific: an absent file, a file with no perf rows, perf rows all older than the
# window, an unknown flag or a zero window.

ROMP_SCRIPT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp"

setup() {
    TEST_DIR="$(mktemp -d)"
    export XDG_STATE_HOME="$TEST_DIR/state"
    mkdir -p "$XDG_STATE_HOME/romp"
    export DIAG="$XDG_STATE_HOME/romp/client-diag.jsonl"
    MOCK="$TEST_DIR/mock"; mkdir -p "$MOCK"
    export CURL_LOG="$TEST_DIR/curl.log"
    printf '#!/usr/bin/env bash\necho "$*" >> "$CURL_LOG"; exit 7\n' > "$MOCK/curl"; chmod +x "$MOCK/curl"
    export PATH="$MOCK:$PATH"
    # Dashboard 11111111: a feed pane with three minutes (36 feed frames, so 12.0/min; the worst minute's
    # p90 is 48 and its max 130; 9 long frames carrying 1230 ms of blocking over 3 min, so 3.0/min and 410
    # ms/min; feed.js:render attributed 1200 + 900 ms) plus one slow frame with its attribution, and a chat
    # pane the shell has hidden (a zero viewport) in a browser that reports no long frames. Dashboard
    # 22222222: a phone's feed pane, with a stale row an hour old that the default window must exclude.
    # Two lines that are not perf rows (a shim breadcrumb; a malformed line) are skipped.
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1, W2 = "11111111-2222-3333-4444-555555555555", "22222222-3333-4444-5555-666666666666"
def row(t, wid, what, data): return json.dumps({"t": t, "wid": wid, "surface": "perf", "what": what, "data": data})
feed_a = {"app": "feed", "since": (now - 210) * 1000, "span_ms": 60000,
          "frames": {"feed": {"n": 10, "ms_sum": 300, "ms_max": 120, "p90": 48}, "chatTail": {"n": 1, "ms_sum": 2, "ms_max": 2, "p90": 2}},
          "free": {"n": 5, "p50": 20, "p90": 61, "max": 80},
          "loaf": {"n": 3, "blocking_ms": 410, "worst_ms": 320, "top": [{"k": "feed.js:render", "ms": 1200, "n": 3, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "heap_mb": 140.0, "dom": 8000, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
feed_b = {"app": "feed", "since": (now - 150) * 1000, "span_ms": 60000,
          "frames": {"feed": {"n": 14, "ms_sum": 400, "ms_max": 130, "p90": 40}},
          "free": {"n": 7, "p50": 15, "p90": 50, "max": 70},
          "loaf": {"n": 6, "blocking_ms": 820, "worst_ms": 300, "top": [{"k": "feed.js:render", "ms": 900, "n": 5, "inv": "WebSocket.onmessage"}, {"k": "feed.js:applyFeedPayload", "ms": 300, "n": 2, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "heap_mb": 141.0, "dom": 8200, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
feed_c = {"app": "feed", "since": (now - 90) * 1000, "span_ms": 60000,
          "frames": {"feed": {"n": 12, "ms_sum": 200, "ms_max": 90, "p90": 30}},
          "free": None,
          "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "loaf"},
          "heap_mb": 142.5, "dom": 8412, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
slow = {"app": "feed", "type": "feed", "ms": 130, "dom": 8400,
        "loaf": {"ms": 140, "blocking_ms": 90, "top": [{"k": "feed.js:render", "ms": 110, "inv": "WebSocket.onmessage"}]}}
chat = {"app": "chat", "since": (now - 100) * 1000, "span_ms": 60000,
        "frames": {"chatTail": {"n": 30, "ms_sum": 60, "ms_max": 5, "p90": 3}},
        "free": {"n": 3, "p50": 8, "p90": 12, "max": 20},
        "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
        "heap_mb": 90.0, "dom": 3000, "visible": True, "hidden_pane": True, "ua": "chrome-desktop"}
phone = {"app": "feed", "since": (now - 80) * 1000, "span_ms": 60000,
         "frames": {"feed": {"n": 2, "ms_sum": 50, "ms_max": 30, "p90": 30}},
         "free": {"n": 2, "p50": 40, "p90": 45, "max": 45},
         "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
         "dom": 5000, "visible": True, "hidden_pane": False, "ua": "safari-ios"}
stale = dict(phone, frames={"feed": {"n": 999, "ms_sum": 5, "ms_max": 5, "p90": 5}}, since=(now - 3660) * 1000)
lines = [
    row(now - 3600, W2, "minute", stale),
    json.dumps({"t": now - 200, "wid": W1, "surface": "pane-shim", "what": "wsclose", "data": {"app": "feed", "code": 1006}}),
    row(now - 150, W1, "minute", feed_a),
    "this line is not json",
    row(now - 100, W1, "slowframe", slow),
    row(now - 90, W1, "minute", feed_b),
    row(now - 40, W1, "minute", chat),
    row(now - 30, W1, "minute", feed_c),
    row(now - 20, W2, "minute", phone),
]
open(sys.argv[1], "w").write("\n".join(lines) + "\n")
PY
}

teardown() { rm -rf "$TEST_DIR"; }

@test "romp perf client: one screen per dashboard and pane, folded over the window" {
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"browser telemetry from the last 10 min"* ]]
    [[ "$output" == *"2 dashboards, 3 panes, 5 minute rows, 1 slow frame"* ]]
    # the feed pane of dashboard 11111111: rates over its three minutes, the worst minute's p90/max, the last sample's heap and DOM
    [[ "$output" == *"dashboard 11111111 · feed   chrome-desktop   3 min reported   heap 142.5 MB   dom 8412   visible"* ]]
    [[ "$output" == *"feed 12.0 (p90 48 ms, max 130)"* ]]
    [[ "$output" == *"chatTail 0.3 (p90 2 ms, max 2)"* ]]
    [[ "$output" == *"free after a frame p90 61 ms"* ]]
    [[ "$output" == *"long frames 3.0/min   blocking 410 ms/min   worst 320 ms"* ]]
    [[ "$output" == *"feed.js:render 2100 ms   feed.js:applyFeedPayload 300 ms"* ]]
    [[ "$output" == *"feed 130 ms (dom 8400)  feed.js:render 110 ms"* ]]
    # the hidden chat pane, in a browser without long-frame reports
    [[ "$output" == *"dashboard 11111111 · chat   chrome-desktop   1 min reported   heap 90.0 MB   dom 3000   hidden (no viewport)"* ]]
    [[ "$output" == *"chatTail 30.0 (p90 3 ms, max 5)"* ]]
    [[ "$output" == *"long frames: not reported by this browser"* ]]
    # the phone: its hour-old row is outside the window, and a row without heap says so
    [[ "$output" == *"dashboard 22222222 · feed   safari-ios   1 min reported   heap n/a   dom 5000   visible"* ]]
    [[ "$output" == *"feed 2.0 (p90 30 ms, max 30)"* ]]
    [[ "$output" != *"999"* ]]
    [[ "$output" == *"slow frames  none"* ]]
    [ ! -f "$CURL_LOG" ]                                 # no kernel round trip
}

@test "romp perf client --minutes: narrows the window; --minutes=<n> too" {
    run "$ROMP_SCRIPT" perf client --minutes 1
    [ "$status" -eq 0 ]
    [[ "$output" == *"from the last 1 min"* ]]
    [[ "$output" == *"2 dashboards, 3 panes, 3 minute rows, 0 slow frames"* ]]
    [[ "$output" == *"feed 12.0 (p90 30 ms, max 90)"* ]]   # only the newest feed minute is inside
    [[ "$output" != *"feed.js:applyFeedPayload"* ]]
    run "$ROMP_SCRIPT" perf client --minutes=2
    [ "$status" -eq 0 ]
    [[ "$output" == *"4 minute rows, 1 slow frame"* ]]   # the 150 s old minute is outside; the 100 s old slow frame is inside
    [[ "$output" == *"feed.js:render 900 ms   feed.js:applyFeedPayload 300 ms"* ]]
}

@test "romp perf client --json: the folded panes as JSON" {
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["window_min"] == 10
panes = {(p["wid"], p["app"]): p for p in d["panes"]}
assert set(panes) == {("11111111", "feed"), ("11111111", "chat"), ("22222222", "feed")}, set(panes)
f = panes[("11111111", "feed")]
assert f["frames"]["feed"]["n"] == 36 and abs(f["frames"]["feed"]["per_min"] - 12.0) < 1e-9
assert f["frames"]["feed"]["p90"] == 48 and f["frames"]["feed"]["max"] == 130
assert f["free_p90"] == 61 and f["heap_mb"] == 142.5 and f["dom"] == 8412
assert abs(f["loaf"]["per_min"] - 3.0) < 1e-9 and abs(f["loaf"]["blocking_ms_per_min"] - 410) < 1e-9 and f["loaf"]["worst_ms"] == 320
assert f["top"][0] == {"k": "feed.js:render", "ms": 2100}
assert len(f["slow"]) == 1 and f["slow"][0]["ms"] == 130 and f["slow"][0]["loaf"] == [{"k": "feed.js:render", "ms": 110}]
c = panes[("11111111", "chat")]
assert c["hidden_pane"] is True and c["loaf"]["src"] == "none"
p = panes[("22222222", "feed")]
assert p["frames"]["feed"]["n"] == 2 and p["heap_mb"] is None and p["ua"] == "safari-ios"
'
}

@test "romp perf client: reads the file under ROMP_STATE_DIR when it is set" {
    mkdir -p "$TEST_DIR/other"
    mv "$DIAG" "$TEST_DIR/other/client-diag.jsonl"
    ROMP_STATE_DIR="$TEST_DIR/other" run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"($TEST_DIR/other/client-diag.jsonl)"* ]]
    [[ "$output" == *"3 panes"* ]]
}

@test "romp perf client: an absent file says the bundles need rebuilding and the dashboard reloading" {
    rm "$DIAG"
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 1 ]
    [[ "$output" == *"no browser telemetry yet: rebuild the bundles and reload the dashboard"* ]]
    [[ "$output" == *"does not exist"* ]]
}

@test "romp perf client: a file with breadcrumbs but no perf rows says the same, naming the rows" {
    printf '{"t": %d, "wid": "11111111-2222-3333-4444-555555555555", "surface": "pane-shim", "what": "wsclose", "data": {"app": "feed"}}\n' "$(date +%s)" > "$DIAG"
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 1 ]
    [[ "$output" == *"no browser telemetry yet: rebuild the bundles and reload the dashboard"* ]]
    [[ "$output" == *'no surface "perf" rows'* ]]
}

@test "romp perf client: perf rows all older than the window are said with their age, not shown as an empty screen" {
    python3 - "$DIAG" <<'PY'
import json, sys, time
t = int(time.time()) - 3600
open(sys.argv[1], "w").write(json.dumps({"t": t, "wid": "22222222-3333-4444-5555-666666666666", "surface": "perf", "what": "minute",
                                        "data": {"app": "feed", "span_ms": 60000, "frames": {"feed": {"n": 1, "ms_sum": 1, "ms_max": 1, "p90": 1}},
                                                 "free": None, "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
                                                 "dom": 1, "visible": True, "hidden_pane": False, "ua": "other"}}) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 1 ]
    [[ "$output" == *"no browser telemetry in the last 10 min (the newest perf row is 60 min old)"* ]]
    [[ "$output" == *"--minutes to widen the window"* ]]
    run "$ROMP_SCRIPT" perf client --minutes 120
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 dashboard, 1 pane, 1 minute row, 0 slow frames"* ]]
}

@test "romp perf client: an unknown flag, a zero window or a non-numeric window is refused" {
    run "$ROMP_SCRIPT" perf client --nope
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp perf client"* ]]
    run "$ROMP_SCRIPT" perf client --minutes 0
    [ "$status" -eq 2 ]
    run "$ROMP_SCRIPT" perf client --minutes soon
    [ "$status" -eq 2 ]
    run "$ROMP_SCRIPT" perf client --minutes
    [ "$status" -eq 2 ]
}

@test "romp perf: the two-snapshot verb is untouched — its usage now names client, and help lists the sub-verb" {
    run "$ROMP_SCRIPT" perf --nope
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage: romp perf [--interval <s>] [--json] | romp perf log on|off | romp perf client"* ]]
    run "$ROMP_SCRIPT" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp perf client"* ]]
}
