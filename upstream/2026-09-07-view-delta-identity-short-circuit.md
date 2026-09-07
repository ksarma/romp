---
title: Perf B16: `_send_slot_delta` records the parts object a client's state was derived from and short-circuits when the builder hands the same object again inside the repost window, and the delta frame goes through `_client_send` so a drop names its slot and a failed send does not advance the revision
status: candidate
where: fork PR #224 (`perf-b16`, merged 2026-09-06): `kernel/kernel.py` (`_send_slot_delta`; the delta send through `_client_send`); tests `tests/test_view_deltas.py::BarsDeltas`, `tests/test_perf_stats.py`, `tests/test_kernel_timeline_split.py` (end to end through the real `_push`: an unchanged timeline sends no bars, a rebuilt one sends a slotted delta)
added: 2026-09-07
pr: 224
tier: fix
offered:
closed:
---
Upstream's view-delta path (`?delta=1` clients; the timeline bars and the feed slots) compares every collection entry per client per cycle even when the builder handed exactly the same parts object as the previous cycle, and sends the delta frame outside the slot bookkeeping, so a drop is logged without a slot. The parts object is recorded on the keyed full, after a sent delta, and on an unchanged compare; the same object arriving again costs a deduped count and no per-entry work; a rebuilt payload (a new object) is compared as before, once, then adopted. With the send through `_client_send`, `curSlot` is set, a drop names its slot and marks the client dead, and the revision does not advance on a failed send. Measured on a synthetic 7.1 MB bars payload with 26,612 entries: an unchanged same-object cycle 14.7 ms to 0 per timeline client.

The `deduped` counter pins rest on `romp-perf` (fork #199); the short-circuit itself needs nothing else. The PR also updated the frame labeller's docstring in `tools/perf-bench.py`, which is fork tooling (entry `perf-bench-tool`) and not part of this offer.
