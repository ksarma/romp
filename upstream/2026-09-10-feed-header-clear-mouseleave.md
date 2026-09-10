---
title: Feed: a session header's Clear all dispatches the synthetic mouseleave the card path dispatches, so the hover-freeze gate the header row holds is released by the click
status: merged
where: ui/webview/feed.ts (clearSessionCards), ui/webview/feed-render-incremental.test.ts, ui/webview/feed-sess-clear.test.ts
added: 2026-09-10
pr:
tier: fix
offered: their PR #1254
closed: 2026-09-10
---
Pre-existing asymmetry recorded in the review of their #1232 (our freeze-badge offer): the card path has dispatched a synthetic mouseleave at Clear since 2026-07; the header path handed the row to its ghost with the gate still held. Filed directly from the upstream base.
