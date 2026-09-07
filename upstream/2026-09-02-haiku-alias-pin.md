---
title: Bare `haiku` alias pinned to 4.5 in `_ALIAS_HEAD` with no drift signal if the catalog moves it; and `test_index_tier_with_no_model_resolves_the_tier_pick` passes against main too, so it does not bind what its name says
status: merged
where: maintainer’s no-gate notes on their #880 (2026-09-02); not yet built anywhere
added: 2026-09-02
pr:
tier: fix
offered: their PR #948
closed: 2026-09-06
---
Two small follow-ups the maintainer named while merging the judge thinking lever. A drift pin for the alias head, and a test that actually binds the tier-pick resolution.

Status detail (migrated from the table): **offered** — their PR #948 (2026-09-06), label `fix`

MERGED 2026-09-06T19:50Z as their PR #948 (merge `1bc4d823`; head `e6edcab8`), as offered. The once-per-process line for an envelope without `modelUsage` is its own entry (`note-served-model-no-modelusage`).
