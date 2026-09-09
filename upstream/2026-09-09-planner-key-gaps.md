---
title: Planner gate: the key carries the leaf task store, the captions file and each running launch deadline crossing
status: merged
where: upstream-only fix on fork branch `planner-key-offer` (commit `b98d7a7c` on their main `50e824f3`): `kernel/judge.py` `_plan_key` (leaf task-store term in place, captions and expiry terms appended, `_bg_expiry_key` helper, the pass clock threaded through `_bg_unresolved`/`_awaiting_bg_hold`/`_session_settled` with the same lines as our open #1062); `tests/test_planner_skip.py` seven new tests; `tests/test_bg_scan_monitor.py` pin rewritten; `docs/reference.md` plannerSkip passage. Fork main has not folded their #1173 yet; the fold brings both, and #1062 rebases cleanly over it
added: 2026-09-09
pr:
tier: fix
offered: their PR #1179
closed: 2026-09-09
---
From the maintainer-side review record on their #1173: the skip key stats tasks/<sid>/ while the sync reads tasks/<leafFsid>/ (a to-do change alone never re-plans after a /clear, masked today by the SDK hook registry rewrite); the floor-title heal reads captions/<fsid>.jsonl, not in the key; the settled gate applies the wall clock to every running launch, so a recorded session holding an expired launch never re-plans until another input moves (masked at the default by the closer). The expiry is keyed as the boolean it resolves to, the shape kernel.py _lift_spent_awaiting uses.
