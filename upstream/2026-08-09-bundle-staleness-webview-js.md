---
title: Bundle staleness scan misses `ui/webview` *.js — a `gear.js`-only edit never rebuilds the chat bundle
status: merged
where: PR #42 (`efcea880`); offer branch `bundle-js` (`87595102`, single commit off upstream `d0f7c423`)
added: 2026-08-09
pr:
tier:
offered: their PR #384
closed: 2026-08-14
---
Offer branch cleaned up post-merge; CAME HOME in the 2026-08-15 tip fold (`upfold0815`) — the keep-the-helper conflict resolved as predicted (fork keeps `_bundle_inputs`, widened with `src/*.js` for parity; their test's inline-form pin re-aimed at the helper). Upstream's inline scan still misses `ui/romp-timeline-view.js`, flagged unanswered in the PR body. The `romp-timeline-view.js` adjacent gap stays flagged in the PR body, unanswered so far. The third incarnation of the staleness seam, found live 2026-08-09: the scan globs `*.ts`/`*.css` under `ui/webview`, but `gear.js` is a plain-JS module `feed.ts` `require()`s into the chat bundle — a gear-only change ships dark through kernel restarts (`/version` reports the new field while the served bundle predates it). Upstream's bundle-watch fix (`276571f8`, in v0.7.0) has the identical hole. Re-verified and offered 2026-08-14: the fix was HAND-RE-DERIVED against upstream's inline scan (their `_ensure_bundles` never grew the fork's `_bundle_inputs` helper), widening `*.js` over both watch roots (safe: `vscode-extension/src` has no `.js`, dist sits outside both); the test was re-expressed in their `tests/test_bundle_build_mode.py`'s source-level style, deriving the watched-module set from `require()` scans with `gear.js` as a sentinel (the fork's `test_kernel_bundle_staleness.py` imports a fork-only helper and cannot port). The offer's PR body also flags — but does not fix — a SECOND unwatched module the re-verify found: `timeline-main.ts` requires `../romp-timeline-view.js`, which sits OUTSIDE both watch roots (a candidate follow-up if the maintainer wants it; the fork's own `_bundle_inputs` already watches it explicitly). Fork CI green via a since-closed scaffold PR (#63; push CI is main-only).

Status detail (migrated from the table): **merged** — their PR #384, merged as-is 2026-08-14 (merge `1f292bdf`; our head `87595102` is an ancestor of their main, verified 2026-08-15)
