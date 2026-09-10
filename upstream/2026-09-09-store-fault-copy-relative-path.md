---
title: A refused clear, drop or undo names goals/<sid>.json in its dialog, not the absolute state path
status: merged
where: upstream branch store-fault-copy-offer, re-derived from fork commit 3115179b (fold PR #392): `kernel/kernel.py` `_store_fault_copy` and the four `skipped[sid]` sites in `_mark_nodes_cleared` and `_restore_goal_archive`; tests `tests/test_goal_store_fault_boundary.py` GestureRefusal (six dispatcher cases plus the helper's own)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1210
closed: 2026-09-09
---
Audit row 14. The err dialog answering a refused clear, sub-goal drop or undo quoted the goals file's absolute path under the home directory; the helper strips the state root from every path the fault names, keeping the errno text and goals/<sid>.json, so the user still learns which store refused. The judge-errors row keeps the whole path.
