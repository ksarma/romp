---
title: The feed's foreign cleared-id list skips ids that name no session (parked:, quarantine:, provisional:, awaiting:, blocked:), so one Clear-all no longer floods clearedForeign
status: merged
where: kernel/kernel.py (_cleared_foreign, _CLEARED_NO_SESSION), tests/test_kernel_goal_compaction.py
added: 2026-09-09
pr:
tier: fix
offered: their PR #1229
closed: 2026-09-10
---
Defect in their #1190 found while verifying it for the fold: _cleared_foreign classifies by the text before the last colon, so every prefixed id the feed writes rides every frame as a remote clear. Upstream-native, no fork port; filed directly from the upstream base.
