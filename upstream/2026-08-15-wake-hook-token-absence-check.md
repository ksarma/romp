---
title: The #380 token-absence check in `tests/romp-wake-hook.bats` sits MID-test as a bare `! grep` — inert under bats' errexit, so the serve-token-never-in-argv property it guards is unasserted upstream
status: resolved-upstream
where: the fold kept the fork's armed `run`+status form (fork commit `b393aaa8`; resolution in `upfold0815`)
added: 2026-08-15
pr:
tier:
offered: their PR #403
closed: 2026-08-15
---
Found resolving the 2026-08-15 tip fold: upstream's merged #380 carried the check in the exact class #383 armed (a `!` pipeline is exempt from errexit unless it is the test's final command; this one had two commands after it). Routed to the security session same day; they confirmed, fixed it upstream as #403, and swept every upstream .bats for the pattern — that line was the ONLY remaining instance (expected: #383 had armed the rest). Audit lesson from their repro, for any future absence-check re-audit: an inert check is MASKED whenever the probe's leak also breaks something adjacent (their first probe dropped `--config` with `-H`, so a LATER armed line failed and the test went red anyway) — prove inertness with a leak that keeps everything else well-formed, or the audit passes checks that assert nothing.

Status detail (migrated from the table): ✅ **resolved upstream — their #403** (2026-08-15, the security session's follow-up)
