---
title: build_feed's per-session `live` (the backend-alive bit every card and placeholder wears) is clobbered inside the goal loop by the origin badge's local reuse of the same name — after one delegation-origin badge, every later card of that session (and the goal-less user-todo/blocked/awaiting placeholders after the loop) wears the badge's bool: a live session's cards dress .dead and route to revive; a dead session's offer Continue
status: merged
where: fold-review fix in `upfold0825`: the badge-local renamed `origin_live` in `kernel/kernel.py` build_feed; pinned red-first in `tests/test_feed_live_clobber.py` (both directions + the placeholder)
added: 2026-08-25
pr:
tier:
offered: their PR #734
closed: 2026-08-27
---
MERGED as-is (head is an ancestor of their main, verified same night). Branch retired. OFFERED 2026-08-27 (branch `feed-livebit`, `3eb2091b` off tip `14a4bd70`): the two-line rename + placeholder-ordering test; review clean, scaffold CI green (since-closed fork #117). Pre-existing in BOTH parents (verified against the merge), made routine by the tags era — origin badges persist for the card's life (their 2026-08-16 rule), so one absorbed badge poisons the session's whole card tail. Two-line fix, no fork-specific content; the test's placeholder leg needs the fork's user-todo store, so an offer would carry the two card-direction tests and re-home the placeholder pin.

Status detail (migrated from the table): ✅ **merged** — their PR #734, merged as-is 2026-08-27 (merge `5e76112e`)
