---
title: T223's dormant-thread boot skip (`_boot_reconcile`: `if r.get("threadOf") and not queued: continue`) runs BEFORE the arm that reports and clears a dead life's `pendingAsk` / `bgTasks`, and an explicit thread wake (`_ensure` → `SdkSession`) never reads or clears either flag — so a dormant thread whose CLI died holding an ask or background tasks carries the stale flags across every boot and wake until a later boot finds it WITH a queue, and then prepends both old-life notices (`ASK_DIED_NOTICE`, `task_death_notice`) ahead of the user's freshly typed reply
status: merged
where: inherited verbatim from upstream `b878b1ad` (`kernel/sdk_backend.py` `_boot_reconcile`: the T223 guard above the T214 ask/bg-task arm); not fixed on the fork
added: 2026-09-02
pr:
tier:
offered: their PR #878
closed: 2026-09-02
---
MERGED as-is. Branch retired. OFFERED 2026-09-02 combined with the boot-regs-reread row into ONE two-commit PR (branch `boot-reconcile`, `03ffc92b` off tip `70a36077`) — both edit the same _boot_reconcile pass; review clean, scaffold CI green (since-closed fork #155). Found by the fold's adversarial review; not a fork regression — the fork's `_queue_texts` composition only decides what `queued` is, the ordering is upstream's. Fix shape: for a skipped thread, report-or-clear the two flags the way the pending-flag heal already runs above the skip, or clear them at the explicit wake. Red-first test before offering.

Status detail (migrated from the table): ✅ **merged** — their PR #878 (commit B), merged as-is 2026-09-02 — ✅ came home in upfold0905 (2026-09-05)
