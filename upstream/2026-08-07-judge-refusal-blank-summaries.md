---
title: Judge scratch-refusal blanking card summaries (`""` counted as a model failure)
status: resolved-upstream
where: PR #4 (`a0e95cd7`)
added: 2026-08-07
pr:
tier:
offered:
closed:
---
CLOSED 2026-08-23 without an offer: re-verification found the fix ALREADY at their tip byte-identical (the paused-flag "SKIPPED, not failed" block + give-up counters + the pinning test in their test_judge_scratch_private.py, zero diff vs the fork) — it travelled inside the scratch-dirs security chain. User-visible bug upstream too, independent of the security work.

Status detail (migrated from the table): ✅ **resolved upstream** — rode the fork’s security PR #379
