---
title: The timeline's `_viewsKey` drifted from its webview twin: upstream's 2026-08-25 lens fix taught `viewsKey` (session-views.ts) to compare per-surface `actives` and drop the retired `hidden`, but the timeline's hand-copy (romp-timeline-view.js — it can't import TS) was left behind, so a lens-only edit's optimistic pending copy is cleared by the first stale views-bearing frame and the tag filter visibly flaps (revert-then-jump-back)
status: merged
where: fold-review fix in `upfold0825`: `_viewsKey` brought to the twin's exact shape; a source-parity pin in `ui/timeline-views-panel.test.ts` compares the two serializations so the copies cannot drift again
added: 2026-08-25
pr:
tier:
offered: their PR #735
closed: 2026-08-27
---
MERGED as-is (head is an ancestor of their main, verified same night). Branch retired. OFFERED 2026-08-27 (branch `viewskey-drift`, `b2e7d652` off tip `14a4bd70`): mirrors the current twin + a self-checking parity pin in their house style; review clean, scaffold CI green (since-closed fork #116). Upstream ships the same hand-copy in the same file and fixed only the twin, so their timeline flaps identically. Pure bug fix + a drift pin in their own house style (regex/source pins over the .js); no fork-specific content.

Status detail (migrated from the table): ✅ **merged** — their PR #735, merged as-is 2026-08-27 (merge `dd844a6d`)
