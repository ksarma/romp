---
title: An answered wake files its diary row from its own writer load of the goal store (regression from their #1141)
status: merged
where: upstream-only fix on fork branch `wake-answer-offer` (commit `07ff2b3e` on their main `28ecee8c`): `kernel/kernel.py` `_file_wake_answer(sid, gid, now)` loads its own writer copy at the write moment, both callers changed; `tests/test_wake_answer_files_under_shared_view.py` new; `tests/test_nudge_gate_memo.py` drops its source-text pin. Not on fork main until a fold carries their #1141 and this fix together
added: 2026-09-09
pr:
tier: fix
offered: their PR #1160
closed: 2026-09-09
---
Their #1141 (merged 2026-09-09 06:08Z) made the nudge walk read the goal store through the shared read-only view and hand that view to the answered leg, whose writer raised FrozenStoreError inside its own except: the first answered wake per kernel process filed no row, never retried, and switched the shared cache off until restart. Found and recorded on #1141 by the maintainer-side review; fixed here the same day.
