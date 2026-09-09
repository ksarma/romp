---
title: Judge read memos: the eviction at the cap runs under a lock
status: offered
where: upstream-only fix on fork branch `memo-evict-offer` (commit `f33cf8b7` on their main `50e824f3`): `kernel/judge.py` `_FILE_MEMO_LOCK` around `_memo_put`, block comment and `load_goal_archive` docstring corrected; `tests/test_file_read_memos.py` gains a MemoEviction class with two two-thread tests over a hooked dict. Fork main has not folded their #1171 yet; the fold brings both
added: 2026-09-09
pr:
tier: fix
offered: their PR #1178
closed:
---
From the maintainer-side review record on their #1171: _memo_put evicted with memo.pop(next(iter(memo))) and inserted with no lock while the archive memo is filled from every load_goals thread and the captions memo from the index tier and planner workers; at the 256 cap two fills for new sids could raise KeyError or RuntimeError past the OSError-only _or_fault boundary. The lock is a leaf (acquired under _GOAL_ARCH_LOCK on the undo-restore path, never the reverse); reads and counters stay unlocked.
