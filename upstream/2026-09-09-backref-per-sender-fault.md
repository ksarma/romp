---
title: Courier link repair: an unreadable sender store is skipped for that sender, not for every recipient
status: merged
where: upstream-only fix on fork branch `backref-fault-offer` (commit `6bcde04c` on their main `50e824f3`): `kernel/judge.py` `_handoff_backref` reads each sender through `load_goals_shared_or_fault`, withholds the memo slot on a fault and files one store-unreadable row per sender; `tests/test_backref_memo.py` gains four tests and one contract change (raise to skip). Fork main has not folded their #1170 yet; the fold brings both
added: 2026-09-09
pr:
tier: fix
offered: their PR #1177
closed: 2026-09-09
---
From the maintainer-side review record on their #1170: the sender-board walk behind the courier link repair read every discovered store through the read-only view, whose raise on one unreadable store failed the lookup for every message id and recipient and filed a pass-crash row per pass. Per-sender containment is the rule every other reader follows.
