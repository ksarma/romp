---
title: A timeline connect push lends its liveness map to the lane builds it runs, over a stale cache and on a cold live-first connect, so the builds' nested readers stop reading liveness again for every lane
status: candidate
where: kernel/kernel.py (_push: the connect push's stale-cache lane build and the cold live-first connect's two live-only builds run inside _serve_live); tests/test_kernel_pusher_snapshot.py (TimelineConnectReadsLivenessOnce, _HeldClock, SID3: new); tests/test_lab_dist.py (_TREE_COPIERS: the module copies its own synthetic world, never dist); upstream/2026-10-06-timeline-connect-live-once.md (this entry)
added: 2026-10-06
pr: 993
tier: fix
offered:
closed:
---
A timeline connect push runs on the WebSocket handler's thread, where no cycle scope serves a liveness snapshot, and it builds there on two paths. Over a stale cache it builds the lanes fresh with build_timeline(now, live_map, with_bars=False). On a cold live-first connect (no full timeline build cached yet) it builds the live lanes and then their bars, both with live_only=True. Under each of those builds, every live lane's nested readers (the row lookup in _session_awaiting, which build_timeline calls without live=, and the one in _bg_live_norm under it) called Sessions.live() again. The push now lends its map to each of those builds with _serve_live, the helper the chat builds and _awaiting_items_payload already use. Each lend covers its build alone, so no frame is sent under it. The helper leaves an active cycle scope alone, so the pusher's timeline stage does not change.

The cold live-first path runs for any fresh page load whose timeline connect arrives before a pusher cycle with a ready timeline client has finished a full build, because only such a cycle fills the full timeline cache. When a kernel's first timeline client is a fresh page load, that load takes the path however long after the start it comes. A dashboard left open across a restart redials as ready, so the pusher serves it and fills the cache; fresh loads that arrive after that build take the other paths.

Tests: a connect push over a stale cache with three live lanes reads liveness once (seven before the fix), its lanes equal an unlent build's, and no frame is sent with a scope on the handler thread. A cold live-first connect push over the same lanes reads liveness once (16 before the fix), and its two frames equal, byte for byte, those of an unlent push over a fresh copy of the same world. A pusher cycle with a timeline client still reads liveness once. upstream/main has the same two connect paths and the same _serve_live.

## Bench

tools/perf-bench.py with local A/B helpers over a 30-session state copy, the timeline client only, the state copied fresh for each run.

- Stale-cache connect, two runs per head interleaved. The bench hands the push its liveness map, so the reads it counts are the nested ones: 87 per connect push before the fix, 0 after (the kernel's own connect push makes the one read it hands down). Median 972 ms (796 to 1296 ms, n=14) before, 87 ms (73 to 106 ms, n=14) after. With a CPU thread at 50% duty beside the push: median 2355 ms (1731 to 2792 ms, n=8) before, 162 ms (149 to 194 ms, n=8) after.
- Cold live-first connect, the kernel's own connect push, four runs interleaved (two per tree): 176 reads and a median 2051 ms (1741 to 2465 ms, n=14) without the two lends, 1 read and a median 327 ms (266 to 368 ms, n=14) with them. The bench's parse caches were warm. On a real first page load the bars build may also parse cold transcripts, and the lends do not change that cost.
