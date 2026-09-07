---
title: `save_goals`' pid-keyed tmp name is thread-unsafe — two threads saving one sid collide (`FileNotFoundError` at their `judge.py` save path; observed once live on a post-merge boot)
status: merged
where: not yet built; thread-key the tmp at all three call sites
added: 2026-08-27
pr:
tier:
offered: their PR #738
closed: 2026-08-27
---
MERGED as-is (head is an ancestor of their main, verified same night). Branch retired. OFFERED 2026-08-27 (branch `savegoals-tmp`, `3948f561` off tip `14a4bd70`): thread-keyed tmp at all mint sites + the two-thread hammer (red within ~1s on base). Review clean, scaffold CI green (since-closed fork #122). Co-found in the 2026-08-27 forensics, unrelated to the restart race. Synthetic reproduction needed (two-thread hammer on one sid).

Status detail (migrated from the table): ✅ **merged** — their PR #738, merged as-is 2026-08-27 (merge `ae09d878`)
