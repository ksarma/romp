---
title: The `setAutoNudge` WS branch re-ticks `_auto_nudge_tick(..., run_dead_wait=False)` on a real apply, so turning the nudge on acts now instead of waiting for the pusher's next tick
status: offered
where: `kernel/kernel.py` (the `setAutoNudge` arm of `_dispatch_ws`); fork `5be9181f`, kept through `643a16cb` and upfold0905; pinned by `tests/test_setting_gesture_order.py` (WiringPins) and `tests/test_dead_wait_block.py`
added: 2026-09-05
pr:
tier: fix
offered: their PR #943
closed:
---
OFFERED 2026-09-06 (branch `autonudge-retick`, `ba56632f` off tip `2b9db2be`); scaffold CI green (since-closed fork #206). Fork-only, never offered: v0.15.0's branch was a bare `_set_auto_nudge(...)`, and upstream's tip only tells a stale gesture — its turn-on tick sits under `setCompactSuggest` (T208). Kept at the fold (2026-09-05); `_compact_suggest_tick`'s comment counts three concurrent entry points for that reason. A small offer: one call plus the two pins.

Status detail (migrated from the table): **offered** — their PR #943 (2026-09-06), label `fix`
