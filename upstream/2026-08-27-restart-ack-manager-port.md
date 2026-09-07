---
title: `/restart` acks before resolving the manager port — the deterministic kernel-side fix: resolve the port BEFORE sending the ack, closing the race for every caller, guarded conftest or not
status: merged
where: not yet built (design from the 2026-08-27 forensics); pairs with the conftest-floor row
added: 2026-08-27
pr:
tier:
offered: their PR #737
closed: 2026-08-27
---
MERGED as-is (head is an ancestor of their main, verified same night). Branch retired. OFFERED 2026-08-27 (branch `restart-race`, `a133665b` off tip `14a4bd70`): handlers resolve pre-ack and thread the value down (/restart local+remote branches, /update daemon); non-HTTP callers keep env-at-use via a sentinel default. Deterministic ordering test (restore rides the ack itself — no sleeps) red on base; three source-pin test files updated in-commit with the justification in the body; ServeSecurity needed NO change and is now deterministic. Review clean, scaffold CI green. The conftest floor protects test runs; this closes the underlying race in the kernel itself. Small, and the incident narrative (a test suite restarting a production deployment through an env-restore race) makes the case for both halves.

Status detail (migrated from the table): ✅ **merged** — their PR #737 (commit 1 of the pair), merged as-is 2026-08-27 (merge `b264635b`)
