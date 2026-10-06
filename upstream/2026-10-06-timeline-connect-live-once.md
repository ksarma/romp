---
title: A timeline connect push over a stale cache lends its liveness map to the lane build, so the build's nested readers stop reading liveness again for every lane
status: candidate
where: kernel/kernel.py (_push: the connect push's stale-cache lane build runs inside _serve_live); tests/test_kernel_pusher_snapshot.py (TimelineConnectReadsLivenessOnce, _HeldClock, SID3: new); upstream/2026-10-06-timeline-connect-live-once.md (this entry)
added: 2026-10-06
pr:
tier: fix
offered:
closed:
---
A timeline connect push runs on the WebSocket handler's thread, where no cycle scope serves a liveness snapshot. Over a stale cache it builds the lanes fresh with build_timeline(now, live_map, with_bars=False), and every live lane's nested readers under that build (the row lookup in _session_awaiting, which build_timeline calls without live=, and the one in _bg_live_norm under it) called Sessions.live() again. The push now lends its map to that build with _serve_live, the helper the chat builds and _awaiting_items_payload already use. The helper leaves an active cycle scope alone, so the pusher's timeline stage does not change. A new test counts one Sessions.live() read for a connect push over three live lanes (seven before the fix) and checks that the lanes equal an unlent build's; a second pins one read for a pusher cycle with a timeline client. On a 30-session state copy a connect push took 87 reads and a median 972 ms (796 to 1296 ms, n=14) before the fix, and 87 ms (73 to 106 ms, n=14) after. upstream/main has the same stale-cache build and the same _serve_live.

## Bench

tools/perf-bench.py with a local A/B helper over a 30-session state copy: the timeline client only, two runs per head interleaved, the state copied fresh for each run. The bench hands the push its liveness map, so the reads it counts are the nested ones: 87 per connect push before the fix, 0 after (the kernel's own connect push makes the one read it hands down). With a CPU thread at 50% duty beside the push: median 2355 ms (1731 to 2792 ms, n=8) before, 162 ms (149 to 194 ms, n=8) after.

## Recorded, not fixed

kernel/kernel.py, _push: the cold live-first connect (no full timeline build cached since the kernel started) calls build_timeline twice with live_only=True, also outside any scope. On the new test's three live lanes that connect push reads liveness 16 times. It runs only for connects that arrive before the pusher's first full timeline build after the kernel starts, and is left for a separate change.
