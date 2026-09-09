---
title: Perf B16: `_send_slot_delta` records the parts object a client's state was derived from and short-circuits when the builder hands the same object again inside the repost window, and the delta frame goes through `_client_send` so a drop names its slot and a failed send does not advance the revision
status: merged
where: fork PR #224 (`perf-b16`, merged 2026-09-06): `kernel/kernel.py` (`_send_slot_delta`; the delta send through `_client_send`); tests `tests/test_view_deltas.py::BarsDeltas`, `tests/test_perf_stats.py`, `tests/test_kernel_timeline_split.py` (end to end through the real `_push`: an unchanged timeline sends no bars, a rebuilt one sends a slotted delta)
added: 2026-09-07
pr: 224
tier: fix
offered: their PR #1060
closed: 2026-09-08
---
Upstream's view-delta path (`?delta=1` clients; the timeline bars and the feed slots) compares every collection entry per client per cycle even when the builder handed exactly the same parts object as the previous cycle, and sends the delta frame outside the slot bookkeeping, so a drop is logged without a slot. The parts object is recorded on the keyed full, after a sent delta, and on an unchanged compare; the same object arriving again costs a deduped count and no per-entry work; a rebuilt payload (a new object) is compared as before, once, then adopted. With the send through `_client_send`, `curSlot` is set, a drop names its slot and marks the client dead, and the revision does not advance on a failed send. Measured on a synthetic 7.1 MB bars payload with 26,612 entries: an unchanged same-object cycle 14.7 ms to 0 per timeline client.

The `deduped` counter pins rest on `romp-perf` (fork #199); the short-circuit itself needs nothing else. The PR also updated the frame labeller's docstring in `tools/perf-bench.py`, which is fork tooling (entry `perf-bench-tool`) and not part of this offer.

OFFERED 2026-09-08: offered upstream inside bundle PR #1060 (Pusher: one build, one encode and one compare per change; the timeline's live tick translates the plot; label fix; branch pusher-timeline-offer; head 7da31ce9; a draft while the branch is rebased onto the moved upstream tip) with `timeline-skeleton-from-cache`, `tool-result-scan-no-dumps`, `one-encode-per-payload-per-build-on-the-pusher-thread-plan`, `tick-jobs-wake-memos-discover-once` and the timeline's live tick (P5) of `browser-round2-cuts`.

MERGED 2026-09-08: merged upstream as their PR #1060 (merge dd310bb9, 2026-09-08T15:37:14Z) after the maintainer's own review commit.
