---
title: `tools/ui-bench.mjs`: a headless-Chromium bench for the dashboard panes that records a pane's frame stream from a live kernel and replays it into the real pane page served through the kernel's own `Handler`, measuring per frame type the handler and settle time, long animation frames with attribution, heap after a forced GC, DOM and layout counters and console errors, with `--cpu-profile` V8 profiles ranked by function and aligned to frame windows
status: merged
where: fork PR #227 (`romp-ui-bench`, merged 2026-09-06): `tools/ui-bench.mjs`, `docs/reference.md`, `CONTRIBUTING.md`, `.github/workflows/ci.yml`; tests `tests/ui-bench.test.mjs` (34 tests under 5 s, including two real headless replays of the feed and timeline pages)
added: 2026-09-07
pr: 227
tier: feature
offered: their PR #1057
closed: 2026-09-10
---
Upstream's kernel counters and its verification of UI changes stop at the WebSocket, so freezes in desktop Chrome had no reproducible measurement. `--record <app>` connects to the live kernel's WebSocket as the browser does (token cookie and Origin, the pane's caps, the ready handshake, nothing else) and saves frames as JSONL under the system temp directory only, mode 0600, refusing paths inside a checkout. `--replay <app> --frames FILE` runs the kernel `Handler` in an isolated subprocess (private state and tmux dirs, a per-run minted token, the manager and API env removed, the key file, model catalog and CLI floored the way the test suite floors them, the postal bus disabled, a stdin watchdog so the child dies with the tool) with a Node front server owning the WebSocket; `--synthesize` for tests, `--compare A B` for deltas; live runs use a per-user root with dead-run sweeping, and `ROMP_UI_BENCH_REQUIRE=1` makes CI fail loudly without a browser. Its first finding drove the feed pane change (entry `feed-pane-incremental-render`): on the recorded feed stream the first 6.6 MB frame cost 870 ms in the handler and a 542 KB delta 775 ms, with 98% of `render()`'s self time on one `scrollTop` write that forced a whole-tree layout.

Standalone tooling; no kernel or pane change. Re-cut the `.github/workflows/ci.yml` and `CONTRIBUTING.md` hunks against upstream's versions of those files.

OFFERED 2026-09-08: offered upstream inside bundle PR #1057 (Tools: offline performance benches for the kernel's payload builders and the dashboard panes; label feature; branch dev-bench-offer; head 6db5b129) with `perf-bench-tool`. Reworked at the rebase for upstream's #1016 (the pane shim hands frames to the bundle through a MessageChannel flush): the instrument wraps the handler, bundle and settle seams, counts coalesced frames, and aligns its CPU-profile windows on the deliveries.
