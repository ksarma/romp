---
title: Show completed: an archived top cleared in cleared.jsonl whose only completion is a copied status leaves the list (_ledger_cleared_overlay drops the status-only cleared root and its subtree; a takeaway or an own verdict keeps the row)
status: merged
where: kernel/kernel.py (_ledger_cleared_overlay, _fleet_archived_tops docstring), tests/test_kernel_goal_compaction.py (two tests)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1243
closed: 2026-09-10
---
The residual their #1234 (our compaction re-seal offer) disclosed: archives written before it keep a copied completed status for a re-sealed cleared root, so the top stayed struck through under Show completed. Projection-side, no archive rewrite. Filed from #1234's head (now on main).
