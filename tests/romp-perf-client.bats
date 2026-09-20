#!/usr/bin/env bats

# `romp perf client [--minutes <n>] [--json]` — the browser side of `romp perf`: folds the surface "perf"
# rows the pane bundles post (ui/webview/perf-telemetry.ts: one "minute" row per pane per minute, a
# "slowframe" row per frame at or over 100 ms, five a minute at most) out of $STATE/client-diag.jsonl and
# its rotated predecessor client-diag.jsonl.1, per dashboard id (the first eight characters of the wid) and
# pane app, over the last <n> minutes, and prints one screen.
#
# Nothing here touches a kernel: the verb reads the files directly, and a curl on PATH that fails proves
# it never tried. The fixture is synthetic (placeholder wids, the pane apps the kernel names, invented
# numbers), written relative to the wall clock so the window arithmetic is exercised for real; one minute
# row is a half minute (a pagehide flush), so a rate that divided by the row count would be caught. Every
# refusal is loud and specific: an absent file, an empty file, a file with no perf rows, perf rows all
# older than the window, an unknown flag or a zero window.

ROMP_SCRIPT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp"

setup() {
    # bin/romp resolves the state directory as ${ROMP_STATE_DIR:-$XDG_STATE_HOME/romp} and the token as
    # ${ROMP_SERVE_TOKEN:-<state>/serve-token}: a live kernel's exports outrank the redirection below
    unset ROMP_STATE_DIR ROMP_SERVE_TOKEN
    TEST_DIR="$(mktemp -d)"
    export XDG_STATE_HOME="$TEST_DIR/state"
    mkdir -p "$XDG_STATE_HOME/romp"
    export DIAG="$XDG_STATE_HOME/romp/client-diag.jsonl"
    MOCK="$TEST_DIR/mock"; mkdir -p "$MOCK"
    export CURL_LOG="$TEST_DIR/curl.log"
    printf '#!/usr/bin/env bash\necho "$*" >> "$CURL_LOG"; exit 7\n' > "$MOCK/curl"; chmod +x "$MOCK/curl"
    export PATH="$MOCK:$PATH"
    # Dashboard 11111111: a feed pane with three minute rows, the last a half minute (2.5 min in all): 36 feed
    # frames (14.4/min) costing 900 ms (360 ms/min), whose summed histogram puts the window p50 under 4 ms,
    # the p90 under 32 and the p99 under 128, 9 of them over 16.7 ms (25%) and 2 at or over 100 ms (6%);
    # the federation layer's own share as fed:feed (40 ms); 9 long frames with 1230 ms of blocking; the
    # attribution feed.js:render@1200 (1200 + 900 ms) and the shim's inline callback page:(anonymous)@31245;
    # one slow frame row with its attribution and a minute in which 45 more slow frames went unsent past the
    # pane's cap. The second minute (400 ms of handler time) is the worst. A chat pane the shell has hidden
    # (a zero viewport) in a browser that reports no long frames. Dashboard 22222222: a phone's feed pane,
    # with a stale row an hour old that the default window must exclude. Two lines that are not perf rows
    # (a shim breadcrumb; a malformed line) are skipped.
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1, W2 = "11111111-2222-3333-4444-555555555555", "22222222-3333-4444-5555-666666666666"
def row(t, wid, what, data): return json.dumps({"t": t, "wid": wid, "surface": "perf", "what": what, "data": data})
def H(**at):
    h = [0] * 14
    for k, v in at.items(): h[int(k[1:])] = v
    return h
def st(n, ms_sum, ms_max, n16, n100, hist): return {"n": n, "ms_sum": ms_sum, "ms_max": ms_max, "n16": n16, "n100": n100, "hist": hist}
NOSLOW = {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}
feed_a = {"app": "feed", "since": (now - 210) * 1000, "span_ms": 60000,
          "frames": {"feed": st(10, 300, 120, 3, 1, H(b1=2, b2=3, b3=2, b4=1, b5=1, b7=1)),
                     "fed:feed": st(10, 40, 8, 0, 0, H(b0=2, b1=3, b2=3, b3=2)),
                     "chatTail": st(1, 2, 2, 0, 0, H(b2=1))},
          "free": {"n": 5, "p50": 20, "p90": 61, "max": 80},
          "loaf": {"n": 3, "blocking_ms": 410, "worst_ms": 320, "top": [{"k": "feed.js:render@1200", "ms": 1200, "n": 3, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "slow": NOSLOW, "heap_mb": 140.0, "dom": 8000, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
feed_b = {"app": "feed", "since": (now - 150) * 1000, "span_ms": 60000,
          "frames": {"feed": st(14, 400, 130, 4, 1, H(b1=3, b2=4, b3=3, b4=2, b5=1, b7=1))},
          "free": {"n": 7, "p50": 15, "p90": 50, "max": 70},
          "loaf": {"n": 6, "blocking_ms": 820, "worst_ms": 300, "top": [{"k": "feed.js:render@1200", "ms": 900, "n": 5, "inv": "WebSocket.onmessage"}, {"k": "page:(anonymous)@31245", "ms": 300, "n": 6, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "slow": {"sent": 1, "suppressed": 45, "suppressed_worst_ms": 380},
          "heap_mb": 141.0, "dom": 8200, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
feed_c = {"app": "feed", "since": (now - 60) * 1000, "span_ms": 30000,
          "frames": {"feed": st(12, 200, 90, 2, 0, H(b1=4, b2=4, b3=2, b4=1, b6=1))},
          "free": None,
          "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "loaf"},
          "slow": NOSLOW, "heap_mb": 142.5, "dom": 8412, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
slow = {"app": "feed", "type": "feed", "ms": 130, "dom": 8400,
        "loaf": {"ms": 140, "blocking_ms": 90, "top": [{"k": "feed.js:render@1200", "ms": 110, "inv": "WebSocket.onmessage"}]}}
chat = {"app": "chat", "since": (now - 100) * 1000, "span_ms": 60000,
        "frames": {"chatTail": st(30, 60, 5, 0, 0, H(b0=10, b1=10, b2=8, b3=2))},
        "free": {"n": 3, "p50": 8, "p90": 12, "max": 20},
        "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
        "slow": NOSLOW, "heap_mb": 90.0, "dom": 3000, "visible": True, "hidden_pane": True, "ua": "chrome-desktop"}
phone = {"app": "feed", "since": (now - 80) * 1000, "span_ms": 60000,
         "frames": {"feed": st(2, 50, 30, 2, 0, H(b5=2))},       # 20 and 30 ms: both in the 16-32 bucket, both over 16.7
         "free": {"n": 2, "p50": 40, "p90": 45, "max": 45},
         "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
         "slow": NOSLOW, "dom": 5000, "visible": True, "hidden_pane": False, "ua": "safari-ios"}
stale = dict(phone, frames={"feed": st(999, 5, 5, 0, 0, H(b0=999))}, since=(now - 3660) * 1000)
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
    [[ "$output" == *"2 dashboards, 3 panes, 5 minute rows, 1 slow frame row"* ]]
    # the feed pane of dashboard 11111111: 2.5 min of rows, the last sample's heap and DOM
    [[ "$output" == *"dashboard 11111111 · feed   chrome-desktop   2.5 min reported   heap 142.5 MB   dom 8412   visible"* ]]
    # the pane's total, then each type by its share: rate, ms/min, window percentiles from the summed histogram, max, shares
    [[ "$output" == *"handler      377 ms/min total"* ]]
    [[ "$output" == *"feed           14.4/min    360 ms/min   p50 <4   p90 <32   p99 <128 ms   max 130   >16.7 ms 25%   >=100 ms 6%"* ]]
    [[ "$output" == *"fed:feed        4.0/min     16 ms/min   p50 <2   p90 <8   p99 <8 ms   max 8   >16.7 ms 0%   >=100 ms 0%"* ]]
    [[ "$output" == *"chatTail        0.4/min      1 ms/min"* ]]
    # feed before fed:feed before chatTail: sorted by handler time, not by count. Panes print in (dashboard,
    # app) order, so the chat pane and its own chatTail line come first; the check is within the feed pane's block.
    feed_block="$(echo "$output" | sed -n '/^dashboard 11111111 · feed/,/^dashboard 22222222/p')"
    feed_line="$(echo "$feed_block" | grep -n '^    feed ' | head -1 | cut -d: -f1)"
    fed_line="$(echo "$feed_block" | grep -n '^    fed:feed ' | head -1 | cut -d: -f1)"
    chat_line="$(echo "$feed_block" | grep -n '^    chatTail ' | head -1 | cut -d: -f1)"
    [ -n "$feed_line" ] && [ -n "$fed_line" ] && [ -n "$chat_line" ]
    [ "$feed_line" -lt "$fed_line" ] && [ "$fed_line" -lt "$chat_line" ]
    [[ "$output" == *"free after a frame, worst minute's p90 61 ms"* ]]
    [[ "$output" == *"long frames 3.6/min   blocking 492 ms/min   worst 320 ms"* ]]
    [[ "$output" == *"feed.js:render@1200 2100 ms (WebSocket.onmessage)   page:(anonymous)@31245 300 ms (WebSocket.onmessage)"* ]]
    # the worst minute is the second one: its span (the browser's minute start to the kernel's receipt), its own
    # counts and percentiles, its long frames
    [[ "$output" =~ 'worst minute '[0-9][0-9]:[0-9][0-9]:[0-9][0-9]-[0-9][0-9]:[0-9][0-9]:[0-9][0-9]'   400 ms handler' ]]
    [[ "$output" == *"400 ms handler   feed 14 (p90 <32 ms, max 130)   long frames 6, blocking 820 ms"* ]]
    # the slow frame row, then the ones the pane did not send
    [[ "$output" == *"feed 130 ms (dom 8400)  feed.js:render@1200 110 ms"* ]]
    [[ "$output" == *"and 45 more (45 not sent by the pane past its per-minute cap; worst 380 ms)"* ]]
    # the hidden chat pane, in a browser without long-frame reports
    [[ "$output" == *"dashboard 11111111 · chat   chrome-desktop   1 min reported   heap 90.0 MB   dom 3000   hidden (no viewport)"* ]]
    [[ "$output" == *"chatTail       30.0/min     60 ms/min   p50 <2   p90 <4   p99 <8 ms   max 5"* ]]
    [[ "$output" == *"long frames: not reported by this browser"* ]]
    # the phone: its hour-old row is outside the window, and a row without heap says so
    [[ "$output" == *"dashboard 22222222 · feed   safari-ios   1 min reported   heap n/a   dom 5000   visible"* ]]
    [[ "$output" == *"feed            2.0/min     50 ms/min   p50 <32   p90 <32   p99 <32 ms   max 30   >16.7 ms 100%   >=100 ms 0%"* ]]
    [[ "$output" != *"999"* ]]
    [[ "$output" == *"slow frames  none"* ]]
    [ ! -f "$CURL_LOG" ]                                 # no kernel round trip
}

@test "romp perf client: the shell's row (long frames only, no frame types) renders as a pane of its dashboard without special handling" {
    # The dashboard shell (the top-level window, ui/webview/shell-perf.ts) runs the panes' collector with no
    # brackets at all: Chromium reports a long animation frame to the top-level document, never to the iframe
    # whose script ran it, so the shell's row is where a pane script that blocked the page is named. The row
    # has the minute row's shape with an empty frames map and no free sample, so the verb renders it like any pane's.
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1 = "11111111-2222-3333-4444-555555555555"
def row(t, wid, what, data): return json.dumps({"t": t, "wid": wid, "surface": "perf", "what": what, "data": data})
shell = {"app": "shell", "since": (now - 70) * 1000, "span_ms": 60000,
         "frames": {}, "free": None,
         "loaf": {"n": 1, "blocking_ms": 19950, "worst_ms": 20000,
                  "top": [{"k": "chat.js:paintAll@9000", "ms": 19500, "n": 1, "inv": "Window.requestAnimationFrame"},
                          {"k": "page:onMove@120", "ms": 150, "n": 1, "inv": "DIV.onpointermove"}], "src": "loaf"},
         "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}, "heap_mb": 60.0, "dom": 900, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
with open(sys.argv[1], "a") as f:
    f.write(row(now - 10, W1, "minute", shell) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 dashboards, 4 panes, 6 minute rows, 1 slow frame row"* ]]
    # the shell: one more pane of dashboard 11111111, no frame types, the long frame it alone saw with the pane script the browser named
    [[ "$output" == *"dashboard 11111111 · shell   chrome-desktop   1 min reported   heap 60.0 MB   dom 900   visible"* ]]
    shell_block="$(echo "$output" | sed -n '/^dashboard 11111111 · shell/,/^dashboard 22222222/p')"
    [[ "$shell_block" == *"handler      no frames"* ]]
    [[ "$shell_block" == *"main thread  free after a frame p90 n/a   long frames 1.0/min   blocking 19950 ms/min   worst 20000 ms"* ]]
    [[ "$shell_block" == *"attribution  chat.js:paintAll@9000 19500 ms (Window.requestAnimationFrame)   page:onMove@120 150 ms (DIV.onpointermove)"* ]]
    [[ "$shell_block" == *"0 ms handler   no frames   long frames 1, blocking 19950 ms"* ]]
    [[ "$shell_block" == *"slow frames  none"* ]]
    # the feed pane's own screen is unchanged by the extra pane
    [[ "$output" == *"feed           14.4/min    360 ms/min   p50 <4   p90 <32   p99 <128 ms   max 130   >16.7 ms 25%   >=100 ms 6%"* ]]
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
panes = {(p["wid"], p["app"]): p for p in d["panes"]}
assert set(panes) == {("11111111", "feed"), ("11111111", "chat"), ("11111111", "shell"), ("22222222", "feed")}, set(panes)
s = panes[("11111111", "shell")]
assert s["frames"] == {} and s["total_ms_per_min"] == 0 and s["free_p90"] is None and s["minutes"] == 1, s
assert s["loaf"] == {"per_min": 1.0, "blocking_ms_per_min": 19950.0, "worst_ms": 20000, "src": "loaf"}, s["loaf"]
assert s["top"] == [{"k": "chat.js:paintAll@9000", "ms": 19500, "inv": "Window.requestAnimationFrame"}, {"k": "page:onMove@120", "ms": 150, "inv": "DIV.onpointermove"}], s["top"]
assert s["worst_minute"]["total_ms"] == 0 and s["worst_minute"]["loaf_n"] == 1 and s["worst_minute"]["blocking_ms"] == 19950, s["worst_minute"]
assert s["slow"] == [] and s["heap_mb"] == 60.0 and s["dom"] == 900
'
}

@test "romp perf client: a Files pane row (the viewer's fileview:paint and fileview:reflow passes, no frames pushed to it) renders as a pane of its dashboard without special handling" {
    # The Files pane receives no frames; its collector times the viewer's own passes (perf-telemetry.ts,
    # file-view.ts perfTimed): fileview:paint (a text body painted) and fileview:reflow (the comments panel's
    # re-place of its cards over reflowed text). A 20 s divider drag over a large reviewed document was invisible
    # to this verb until the pane had a collector; its row has the minute row's shape, so the verb folds it like any pane's.
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1 = "11111111-2222-3333-4444-555555555555"
def row(t, wid, what, data): return json.dumps({"t": t, "wid": wid, "surface": "perf", "what": what, "data": data})
def H(**at):
    h = [0] * 14
    for k, v in at.items(): h[int(k[1:])] = v
    return h
def st(n, ms_sum, ms_max, n16, n100, hist): return {"n": n, "ms_sum": ms_sum, "ms_max": ms_max, "n16": n16, "n100": n100, "hist": hist}
files = {"app": "files", "since": (now - 70) * 1000, "span_ms": 60000,
         "frames": {"fileview:paint": st(1, 180, 180, 1, 1, H(b8=1)), "fileview:reflow": st(12, 720, 90, 12, 0, H(b6=12))},
         "free": {"n": 13, "p50": 40, "p90": 95, "max": 120},
         "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "loaf"},
         "slow": {"sent": 1, "suppressed": 0, "suppressed_worst_ms": 0}, "heap_mb": 210.0, "dom": 40000, "visible": True, "hidden_pane": False, "ua": "chrome-desktop"}
slow = {"app": "files", "type": "fileview:paint", "ms": 180, "dom": 40000}
with open(sys.argv[1], "a") as f:
    f.write(row(now - 12, W1, "minute", files) + "\n" + row(now - 11, W1, "slowframe", slow) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"2 dashboards, 4 panes, 6 minute rows, 2 slow frame rows"* ]]
    # the Files pane: the viewer's two pass types, the reflow's twelve passes first by handler time
    [[ "$output" == *"dashboard 11111111 · files   chrome-desktop   1 min reported   heap 210.0 MB   dom 40000   visible"* ]]
    files_block="$(echo "$output" | sed -n '/^dashboard 11111111 · files/,/^dashboard 22222222/p')"
    [[ "$files_block" == *"handler      900 ms/min total"* ]]
    [[ "$files_block" == *"fileview:reflow   12.0/min    720 ms/min   p50 <64   p90 <64   p99 <64 ms   max 90   >16.7 ms 100%   >=100 ms 0%"* ]]
    [[ "$files_block" == *"fileview:paint    1.0/min    180 ms/min   p50 <256   p90 <256   p99 <256 ms   max 180   >16.7 ms 100%   >=100 ms 100%"* ]]
    reflow_line="$(echo "$files_block" | grep -n '^    fileview:reflow ' | head -1 | cut -d: -f1)"
    paint_line="$(echo "$files_block" | grep -n '^    fileview:paint ' | head -1 | cut -d: -f1)"
    [ -n "$reflow_line" ] && [ -n "$paint_line" ] && [ "$reflow_line" -lt "$paint_line" ]
    [[ "$files_block" == *"main thread  free after a frame, worst minute's p90 95 ms   long frames 0.0/min   blocking 0 ms/min   worst 0 ms"* ]]
    [[ "$files_block" == *"900 ms handler   fileview:reflow 12 (p90 <64 ms, max 90)   fileview:paint 1 (p90 <256 ms, max 180)   long frames 0, blocking 0 ms"* ]]
    [[ "$files_block" == *"fileview:paint 180 ms (dom 40000)"* ]]
    # the feed pane's own screen is unchanged by the extra pane
    [[ "$output" == *"feed           14.4/min    360 ms/min   p50 <4   p90 <32   p99 <128 ms   max 130   >16.7 ms 25%   >=100 ms 6%"* ]]
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
panes = {(p["wid"], p["app"]): p for p in d["panes"]}
assert set(panes) == {("11111111", "feed"), ("11111111", "chat"), ("11111111", "files"), ("22222222", "feed")}, set(panes)
f = panes[("11111111", "files")]
assert set(f["frames"]) == {"fileview:paint", "fileview:reflow"} and f["frames"]["fileview:reflow"]["n"] == 12 and f["frames"]["fileview:paint"]["n"] == 1, f["frames"]
assert f["free_p90"] == 95 and f["total_ms_per_min"] == 900 and f["minutes"] == 1, f
assert f["slow"] == [{"t": f["slow"][0]["t"], "type": "fileview:paint", "ms": 180, "dom": 40000, "loaf": []}], f["slow"]
assert f["loaf"] == {"per_min": 0.0, "blocking_ms_per_min": 0.0, "worst_ms": 0, "src": "loaf"} and f["top"] == [], (f["loaf"], f["top"])
'
}

@test "romp perf client: the kernel's capped rows are counted in the header and --json, a whole-row marker is skipped, and no phantom pane appears" {
    # Since 2026-09-18 the kernel bounds a client-diag row at 24 KiB (kernel.py _client_diag_line) in two shapes: a
    # perf minute row over the bound sheds its uncapped wsBytesByHost map whole, then its per-minute figures (frames
    # first), and names them under its capped key,
    # keeping its span, heap and DOM; any other row over the bound becomes a marker, data {"capped": true, "bytes": N}
    # plus the pane's app when the row had one. The reader used to fold a marker as a pane with one zero-ms minute,
    # and a marker without app landed under a pane named "?"; a shed row read as an empty minute with nothing said.
    # Now the markers are skipped and both kinds are counted, in the header and in --json, so the loss is visible.
    # The header counts the shed rows by WHAT they dropped (capped.dropped; shed_keys in --json): since the round-1
    # ladder sheds the map first, a row can lose wsBytesByHost alone with its frames intact and folded, and the old
    # wording, "shed frames", called that row's frames lost when they were not (review round 1, 2026-09-20). The
    # third loss shape (the maintainer's round 4, kernel-1): a row a VALUE of which the kernel stored short (a string
    # cut at 64 characters, nesting nulled past 8 levels) is kept whole otherwise and carries `cut`, the admitted keys
    # it happened under; the reader counts those rows and names the keys (cut_rows, cut_keys), beside the shed count
    # when the row also shed keys, so a stored value can be told from a whole one here too.
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" != *"capped whole"* ]]                  # nothing lost: the clause is absent, not zeroed
    [[ "$output" != *"with a value cut"* ]]
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["shed_minute_rows"] == 0 and d["capped_rows"] == 0, (d["shed_minute_rows"], d["capped_rows"])
assert d["cut_rows"] == 0 and d["cut_keys"] == {}, (d["cut_rows"], d["cut_keys"])
'
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1 = "11111111-2222-3333-4444-555555555555"
def row(t, wid, what, data): return json.dumps({"t": t, "wid": wid, "surface": "perf", "what": what, "data": data})
# a chat minute row the kernel stored without its frames (its once-per-page nav survived the shed, as intended)
shed = {"app": "chat", "since": (now - 75) * 1000, "span_ms": 60000,
        "free": {"n": 4, "p50": 9, "p90": 14, "max": 22},
        "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
        "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}, "heap_mb": 90.0, "dom": 3000, "visible": True, "hidden_pane": True, "ua": "chrome-desktop",
        "nav": {"ttfb": 120}, "capped": {"bytes": 30000, "dropped": ["frames"]}}
# a timeline minute row the kernel shed the wsBytesByHost map from, the ladder's first step: its frames stayed and fold
mapshed = {"app": "timeline", "since": (now - 70) * 1000, "span_ms": 60000,
           "frames": {"tlBars": {"n": 6, "ms_sum": 60, "ms_max": 20, "n16": 1, "n100": 0, "hist": [0, 0, 0, 4, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0]}},
           "free": {"n": 6, "p50": 10, "p90": 20, "max": 30},
           "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
           "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}, "heap_mb": 60.0, "dom": 1500, "visible": True, "hidden_pane": False, "ua": "chrome-desktop",
           "capped": {"bytes": 25000, "dropped": ["wsBytesByHost"]}, "cut": ["loaf"]}   # and a long-frame attribution string in it was cut: the row is a shed row AND a cut row
# the shell's minute row (no frame types) with a long-frame attribution string the kernel cut at 64 characters: kept whole
# otherwise, it folds as the shell's pane and carries `cut` naming the key the cut fell under (kernel.py _client_diag_admit)
cutrow = {"app": "shell", "since": (now - 65) * 1000, "span_ms": 60000,
          "free": {"n": 3, "p50": 8, "p90": 12, "max": 15},
          "loaf": {"n": 1, "blocking_ms": 80, "worst_ms": 120, "top": [{"k": "feed.js:render@1200", "ms": 100, "n": 1, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}, "heap_mb": 30.0, "dom": 200, "visible": True, "hidden_pane": False, "ua": "chrome-desktop",
          "cut": ["loaf"]}
with open(sys.argv[1], "a") as f:
    f.write(row(now - 15, W1, "minute", shed) + "\n"
            + row(now - 8, W1, "minute", {"capped": True, "bytes": 40000, "app": "chat"}) + "\n"
            + row(now - 5, W1, "slowframe", {"capped": True, "bytes": 30000}) + "\n"
            + row(now - 9, W1, "minute", mapshed) + "\n"
            + row(now - 12, W1, "minute", cutrow) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" != *"· ?"* ]]                           # the marker without app makes no phantom pane
    # the two shed rows and the cut shell row count as minute rows, the two markers count as capped, and neither marker counts as a
    # row of either kind; the header says what each shed row dropped: the chat row its frames, the timeline row the wsBytesByHost
    # map alone; and it counts the rows with a cut value by the key the cut fell under: the shell row and the timeline row (a shed
    # row too, counted under both shapes), loaf on both
    [[ "$output" == *"2 dashboards, 5 panes, 8 minute rows, 1 slow frame row; 2 minute rows shed keys (frames on 1, wsBytesByHost on 1), 2 rows capped whole, 2 rows with a value cut (loaf on 2)"* ]]
    # the shell's cut row folded as its own pane: the cut is named in the header, never a reason to drop the row
    [[ "$output" == *"dashboard 11111111 · shell   chrome-desktop   1 min reported   heap 30.0 MB   dom 200   visible"* ]]
    [[ "$output" != *"rows shed frames"* && "$output" != *"row shed frames"* ]]   # the old sentence, which called the map-shed row's frames lost
    # the timeline pane's frames folded: the map-shed row kept them
    [[ "$output" == *"dashboard 11111111 · timeline   chrome-desktop   1 min reported   heap 60.0 MB   dom 1500   visible"* ]]
    [[ "$output" == *"tlBars          6.0/min     60 ms/min   p50 <8   p90 <16   p99 <16 ms   max 20   >16.7 ms 17%   >=100 ms 0%"* ]]
    # the chat pane folds the shed row by its span: one minute became two, with the last sample's heap and DOM unchanged
    [[ "$output" == *"dashboard 11111111 · chat   chrome-desktop   2 min reported   heap 90.0 MB   dom 3000   hidden (no viewport)"* ]]
    [[ "$output" == *"chatTail       15.0/min     30 ms/min"* ]]   # 30 frames and 60 ms over two minutes now
    # the feed pane's own screen is unchanged
    [[ "$output" == *"feed           14.4/min    360 ms/min   p50 <4   p90 <32   p99 <128 ms   max 130   >16.7 ms 25%   >=100 ms 6%"* ]]
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["shed_minute_rows"] == 2 and d["capped_rows"] == 2, (d["shed_minute_rows"], d["capped_rows"])
assert d["shed_keys"] == {"frames": 1, "wsBytesByHost": 1}, d["shed_keys"]   # per key, the rows that dropped it
assert d["cut_rows"] == 2 and d["cut_keys"] == {"loaf": 2}, (d["cut_rows"], d["cut_keys"])   # the third shape: per key, the rows a cut fell under
panes = {(p["wid"], p["app"]): p for p in d["panes"]}
assert set(panes) == {("11111111", "feed"), ("11111111", "chat"), ("11111111", "timeline"), ("11111111", "shell"), ("22222222", "feed")}, set(panes)
tl = panes[("11111111", "timeline")]
assert tl["rows"] == 1 and tl["frames"]["tlBars"]["n"] == 6 and tl["total_ms_per_min"] == 60, tl   # the frames of the row that shed the map fold
assert not any(p["app"] == "?" for p in d["panes"]), [p["app"] for p in d["panes"]]
c = panes[("11111111", "chat")]
assert c["minutes"] == 2 and c["rows"] == 2 and c["frames"]["chatTail"]["n"] == 30 and c["heap_mb"] == 90.0 and c["dom"] == 3000, c
assert [m["total_ms"] for m in c["minutes_detail"]] == [60, 0], c["minutes_detail"]
'
    # a window whose one loss is a cut value shows the clause too (the loss visible on its own, the other two shapes at zero, their
    # key lists not rendered at zero). The two cut keys are BUILT FROM THE ALLOWLIST (the maintainer's round 5, correctness-5: the
    # fixture had posted `why`, a key the perf surface does not admit, so the leg pinned the rendering of a row no writer can emit,
    # since the kernel builds the cut list from the admitted keys alone): two admitted perf keys whose values a poster can fill
    # (loaf, a nested object with strings; env, likewise), read off kernel.py's CLIENT_DIAG_KEYS['perf'] and asserted admitted; the
    # header renders the keys in sorted order (bin/romp sorts cut_keys), so the assertion is built in that order too. The kernel
    # admits by key and never checks the poster, so the second key stands in for any admitted key a poster fills.
    CUTKEYS="$(python3 - "$ROMP_SCRIPT" <<'PY'
import re, sys, os
src = open(os.path.join(os.path.dirname(os.path.realpath(sys.argv[1])), "..", "kernel", "kernel.py"), encoding="utf-8").read()
m = re.search(r'"perf": frozenset\(\((.*?)\)\),', src, re.S)
assert m, "kernel.py: CLIENT_DIAG_KEYS['perf'] not found"
admitted = set(re.findall(r'"([A-Za-z_]+)"', m.group(1)))
for k in ("loaf", "env"):
    assert k in admitted, ("not an admitted perf key", k)
print(" ".join(sorted(["loaf", "env"])))
PY
)"
    read -r CUT1 CUT2 <<< "$CUTKEYS"
    [ -n "$CUT1" ] && [ -n "$CUT2" ]
    python3 - "$DIAG" "$CUT1" "$CUT2" <<'PY'
import json, sys, time
now = int(time.time())
W1 = "11111111-2222-3333-4444-555555555555"
open(sys.argv[1], "w").write(json.dumps({"t": now - 10, "wid": W1, "surface": "perf", "what": "minute", "data": {
    "app": "shell", "since": (now - 70) * 1000, "span_ms": 60000, "free": {"n": 3, "p50": 8, "p90": 12, "max": 15},
    "loaf": {"n": 1, "blocking_ms": 80, "worst_ms": 120, "top": [{"k": "feed.js:render@1200", "ms": 100, "n": 1, "inv": "WebSocket.onmessage"}], "src": "loaf"},
    "env": {"dv": 1, "entryTypes": ["longtask"]},
    "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}, "heap_mb": 30.0, "dom": 200, "visible": True, "hidden_pane": False, "ua": "chrome-desktop",
    "cut": [sys.argv[2], sys.argv[3]]}}) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 dashboard, 1 pane, 1 minute row, 0 slow frame rows; 0 minute rows shed keys, 0 rows capped whole, 1 row with a value cut ($CUT1 on 1, $CUT2 on 1)"* ]]
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["cut_rows"] == 1 and d["cut_keys"] == {sys.argv[1]: 1, sys.argv[2]: 1} and d["shed_minute_rows"] == 0 and d["capped_rows"] == 0, d
' "$CUT1" "$CUT2"
    # a loss and NO cut (the maintainer's round 5, regression-5, extra10-1, kernel-1): a window with a shed row and a cap marker and no
    # cut value renders the shed and capped counts and no cut term at all (the clause had printed "0 rows with a value cut (no key
    # named)" here); the shed row drops loaf, a key of the ladder the header used to leave unnamed (kernel-2: the shed clause is
    # worded from shed_keys, so every key the ladder sheds is named)
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1 = "11111111-2222-3333-4444-555555555555"
shed = {"app": "feed", "since": (now - 70) * 1000, "span_ms": 60000,
        "frames": {"feed": {"n": 2, "ms_sum": 20, "ms_max": 12, "n16": 0, "n100": 0, "hist": [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}},
        "free": {"n": 3, "p50": 8, "p90": 12, "max": 15}, "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0},
        "heap_mb": 30.0, "dom": 200, "visible": True, "hidden_pane": False, "ua": "chrome-desktop",
        "capped": {"bytes": 26000, "dropped": ["wsBytesByHost", "loaf"]}}
open(sys.argv[1], "w").write(json.dumps({"t": now - 10, "wid": W1, "surface": "perf", "what": "minute", "data": shed}) + "\n"
                              + json.dumps({"t": now - 8, "wid": W1, "surface": "perf", "what": "minute", "data": {"capped": True, "bytes": 40000, "app": "chat"}}) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 dashboard, 1 pane, 1 minute row, 0 slow frame rows; 1 minute row shed keys (loaf on 1, wsBytesByHost on 1), 1 row capped whole"* ]]
    [[ "$output" != *"with a value cut"* ]]
    [[ "$output" != *"no key named"* ]]
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["shed_minute_rows"] == 1 and d["shed_keys"] == {"loaf": 1, "wsBytesByHost": 1} and d["capped_rows"] == 1 and d["cut_rows"] == 0 and d["cut_keys"] == {}, d
'
    # the fallback covered (round 5, kernel-1): a row whose cut list names no string key (an empty list) counts as a cut row and the
    # parenthetical says so, since the count is above zero and the key map is empty
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1 = "11111111-2222-3333-4444-555555555555"
open(sys.argv[1], "w").write(json.dumps({"t": now - 10, "wid": W1, "surface": "perf", "what": "minute", "data": {
    "app": "shell", "since": (now - 70) * 1000, "span_ms": 60000, "free": {"n": 3, "p50": 8, "p90": 12, "max": 15},
    "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
    "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}, "heap_mb": 30.0, "dom": 200, "visible": True, "hidden_pane": False, "ua": "chrome-desktop",
    "cut": []}}) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"0 minute rows shed keys, 0 rows capped whole, 1 row with a value cut (no key named)"* ]]
    # a window holding cap markers alone is a loss to report, not an idle dashboard: the refusal names them
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
W1 = "11111111-2222-3333-4444-555555555555"
open(sys.argv[1], "w").write(json.dumps({"t": now - 10, "wid": W1, "surface": "perf", "what": "minute", "data": {"capped": True, "bytes": 40000, "app": "chat"}}) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 1 ]
    [[ "$output" == *"no browser telemetry in the last 10 min (the newest perf row is 0 min old) (1 row in the window was capped whole by the kernel and holds no figures)"* ]]

}

@test "romp perf client --minutes: narrows the window, and a half-minute row is rated by its span" {
    run "$ROMP_SCRIPT" perf client --minutes 1
    [ "$status" -eq 0 ]
    [[ "$output" == *"from the last 1 min"* ]]
    [[ "$output" == *"2 dashboards, 3 panes, 3 minute rows, 0 slow frame rows"* ]]
    [[ "$output" == *"0.5 min reported"* ]]              # only the newest feed minute is inside, and it is half a minute
    [[ "$output" == *"feed           24.0/min    400 ms/min   p50 <4   p90 <16   p99 <64 ms   max 90"* ]]   # 12 frames: rank 11 of [0,4,4,2,1,0,1] is the 8-16 bucket
    [[ "$output" != *"feed.js:render"* ]]
    [[ "$output" == *"slow frames  none"* ]]
    run "$ROMP_SCRIPT" perf client --minutes=2
    [ "$status" -eq 0 ]
    [[ "$output" == *"4 minute rows, 1 slow frame row"* ]]   # the 150 s old minute is outside; the 100 s old slow frame is inside
    [[ "$output" == *"feed.js:render@1200 900 ms (WebSocket.onmessage)   page:(anonymous)@31245 300 ms (WebSocket.onmessage)"* ]]
}

@test "romp perf client --json: the folded panes as JSON, with the per-minute array" {
    run "$ROMP_SCRIPT" perf client --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["window_min"] == 10
panes = {(p["wid"], p["app"]): p for p in d["panes"]}
assert set(panes) == {("11111111", "feed"), ("11111111", "chat"), ("22222222", "feed")}, set(panes)
f = panes[("11111111", "feed")]
ff = f["frames"]["feed"]
assert ff["n"] == 36 and ff["ms_sum"] == 900 and abs(ff["per_min"] - 14.4) < 1e-9 and abs(ff["ms_per_min"] - 360) < 1e-9
assert ff["p50_lt"] == 4 and ff["p90_lt"] == 32 and ff["p99_lt"] == 128 and ff["max"] == 130 and ff["n16"] == 9 and ff["n100"] == 2
assert ff["hist"] == [0, 9, 11, 7, 4, 2, 1, 2, 0, 0, 0, 0, 0, 0], ff["hist"]
assert abs(f["total_ms_per_min"] - 376.8) < 1e-9 and f["minutes"] == 2.5
assert f["free_p90"] == 61 and f["heap_mb"] == 142.5 and f["dom"] == 8412
assert abs(f["loaf"]["per_min"] - 3.6) < 1e-9 and abs(f["loaf"]["blocking_ms_per_min"] - 492) < 1e-9 and f["loaf"]["worst_ms"] == 320
assert f["top"][0] == {"k": "feed.js:render@1200", "ms": 2100, "inv": "WebSocket.onmessage"}
assert [m["total_ms"] for m in f["minutes_detail"]] == [342, 400, 200], f["minutes_detail"]
assert f["worst_minute"]["total_ms"] == 400 and f["worst_minute"]["loaf_n"] == 6 and f["worst_minute"]["blocking_ms"] == 820
assert f["worst_minute"]["t"] - f["worst_minute"]["since"] // 1000 == 60, f["worst_minute"]   # the minute began 60 s before its row arrived
assert f["slow_suppressed"] == 45 and f["slow_suppressed_worst_ms"] == 380
assert len(f["slow"]) == 1 and f["slow"][0]["ms"] == 130 and f["slow"][0]["loaf"] == [{"k": "feed.js:render@1200", "ms": 110}]
c = panes[("11111111", "chat")]
assert c["hidden_pane"] is True and c["loaf"]["src"] == "none"
p = panes[("22222222", "feed")]
assert p["frames"]["feed"]["n"] == 2 and p["heap_mb"] is None and p["ua"] == "safari-ios"
'
}

@test "romp perf client: reads the rotated .1 file before the current one and says so" {
    mv "$DIAG" "$DIAG.1"
    python3 - "$DIAG" <<'PY'
import json, sys, time
now = int(time.time())
h = [0] * 14; h[3] = 4
open(sys.argv[1], "w").write(json.dumps({"t": now - 10, "wid": "22222222-3333-4444-5555-666666666666", "surface": "perf", "what": "minute",
    "data": {"app": "chat", "since": (now - 70) * 1000, "span_ms": 60000,
             "frames": {"chatTail": {"n": 4, "ms_sum": 20, "ms_max": 7, "n16": 0, "n100": 0, "hist": h}},
             "free": None, "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
             "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0}, "dom": 900, "visible": True, "hidden_pane": False, "ua": "safari-ios"}}) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 0 ]
    [[ "$output" == *"($DIAG and .1)"* ]]
    [[ "$output" == *"2 dashboards, 4 panes, 6 minute rows, 1 slow frame row"* ]]
    [[ "$output" == *"dashboard 22222222 · chat"* ]]
    [[ "$output" == *"dashboard 11111111 · feed"* ]]
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

@test "romp perf client: an empty file, or one with breadcrumbs but no perf rows, says the same, naming the rows" {
    : > "$DIAG"
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 1 ]
    [[ "$output" == *"no browser telemetry yet: rebuild the bundles and reload the dashboard"* ]]
    [[ "$output" == *'no surface "perf" rows'* ]]
    printf '{"t": %d, "wid": "11111111-2222-3333-4444-555555555555", "surface": "pane-shim", "what": "wsclose", "data": {"app": "feed"}}\n' "$(date +%s)" > "$DIAG"
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 1 ]
    [[ "$output" == *'no surface "perf" rows'* ]]
}

@test "romp perf client: perf rows all older than the window are said with their age, not shown as an empty screen" {
    python3 - "$DIAG" <<'PY'
import json, sys, time
t = int(time.time()) - 3600
h = [0] * 14; h[1] = 1
open(sys.argv[1], "w").write(json.dumps({"t": t, "wid": "22222222-3333-4444-5555-666666666666", "surface": "perf", "what": "minute",
                                        "data": {"app": "feed", "span_ms": 60000, "frames": {"feed": {"n": 1, "ms_sum": 1, "ms_max": 1, "n16": 0, "n100": 0, "hist": h}},
                                                 "free": None, "loaf": {"n": 0, "blocking_ms": 0, "worst_ms": 0, "top": [], "src": "none"},
                                                 "slow": {"sent": 0, "suppressed": 0, "suppressed_worst_ms": 0},
                                                 "dom": 1, "visible": True, "hidden_pane": False, "ua": "other"}}) + "\n")
PY
    run "$ROMP_SCRIPT" perf client
    [ "$status" -eq 1 ]
    [[ "$output" == *"no browser telemetry in the last 10 min (the newest perf row is 60 min old)"* ]]
    [[ "$output" == *"--minutes to widen the window"* ]]
    run "$ROMP_SCRIPT" perf client --minutes 120
    [ "$status" -eq 0 ]
    [[ "$output" == *"1 dashboard, 1 pane, 1 minute row, 0 slow frame rows"* ]]
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
    [[ "$output" == *"usage: romp perf [--interval <s>] [--json] | romp perf log on|off | romp perf stacks [--json] | romp perf client"* ]]   # the stacks verb sits in the line (T401)
    run "$ROMP_SCRIPT" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"romp perf client"* ]]
}
