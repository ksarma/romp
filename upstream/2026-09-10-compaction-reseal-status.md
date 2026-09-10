---
title: Compaction: a re-sealed cleared top leaves Show completed (the move loop pops from the status dict rollup_status replaced, not the one bound before the re-seal)
status: merged
where: kernel/kernel.py (_compact_goal_store, one rebind after jd.rollup_status), tests/test_kernel_goal_compaction.py (the ledger-stamps test amended with three assertions)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1234
closed: 2026-09-10
---
Defect in their #1187 found while verifying it for the fold: the compaction re-seal rolled the status up into a fresh dict but the move loop popped from the earlier one, so the archive kept completed, the live store saved a dangling entry, and the re-sealed top stayed struck through under Show completed. Upstream-native; filed directly from the upstream base.
