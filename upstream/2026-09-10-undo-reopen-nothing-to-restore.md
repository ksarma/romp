---
title: Undo clear: an undo-reopen with nothing to restore leaves the state as it stands in _fold_node, so a completed top comes back completed (not Working) after a stale pass save collapsed its re-clear or missed its clear
status: merged
where: kernel/judge.py (_fold_node's undo branch), docs/goal-state.md, tests/test_judge_guarded_node.py, tests/test_kernel_goal_compaction.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1242
closed: 2026-09-10
---
Pre-existing fold behaviour recorded in the review of their #1233 (our clear-undo-twin offer): the second undo-reopen of a clear the rebase collapsed, or the lone reopen of a clear that never replayed, fell through to open. The fold no-op covers every shape; a rebase dedup would not. Filed from #1233's head (now on main).
