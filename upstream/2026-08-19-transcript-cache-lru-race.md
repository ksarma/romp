---
title: The transcript-cache LRU races its cross-thread callers: hits MUTATE (pop + reinsert) and eviction is `pop(next(iter()))`, so with more distinct files than slots one thread's eviction pops the entry another just matched (KeyError from the unconditional pop; RuntimeError from `next(iter())` over a resizing dict) — and callers catch-and-degrade, so the raise surfaces as wrong behavior, not a crash
status: merged
where: `kernel/event_model.py` `_read_jsonl_incremental`; fixed in the v0.12.0 fold (`upfold0819`)
added: 2026-08-19
pr:
tier:
offered: their PR #538
closed: 2026-08-22
---
MERGED as-is 2026-08-22 (head is an ancestor of their main, verified in the fold). Branch retired; the fork had carried the fix since `upfold0819`, so the fold converges the two copies. OFFERED 2026-08-20 (branch `lru-race`, `51b18028` off tip `f3ec1297`): two-file hunks re-derived with upstream-true rationale (fork-only vocabulary dropped); hammer test red within ~1s on unfixed code; review clean, scaffold CI green (since-closed fork #90); the port survived a mid-run process restart via the workflow cache. Upstream ships the same mutate-on-hit LRU with the same cross-thread callers (their judge tiers + pusher share the cache), so the race exists there verbatim. Fix is diff-minimal against their shape: a module-level lock held for the cheap dict ops only (lookup+move, insert, evict — the parse stays outside it) plus guarded pops, so a lost race degrades to a re-parse, never a raise. Pinned red-first by a multi-thread hammer in `tests/test_kernel_jsonl_cache.py` (unfixed, it raises within ~1s).

Status detail (migrated from the table): ✅ **merged** — their PR #538, merged as-is 2026-08-22 (merge `6aea062a`); came home in the 2026-08-22 tip fold (`upfold0823`)
