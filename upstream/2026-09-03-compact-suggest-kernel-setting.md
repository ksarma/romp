---
title: `setCompactSuggest` is absent from federation’s `KERNEL_SETTING` set — the maintainer read it as an omission in his #879 follow-ups
status: declined
where: design fact, not a change (the per-install, non-propagating settings idiom, 2026-09-01)
added: 2026-09-03
pr:
tier:
offered:
closed:
---
NOT a bug: `setCompactSuggest` and `thinkingSummaries` are per-install settings by design — each kernel keeps its own answer and the gear shows the local kernel’s value as authoritative, so broadcasting them to every remote host would be the defect; `gear.test.ts` pins the KERNEL_SETTING membership by source-parsing federation.ts, so adding it goes red there too. Explained on their #879 (2026-09-03). Any thinking-summaries offer must keep the same non-propagating shape.

Status detail (migrated from the table): **keep as-is — deliberate; explained to the maintainer**
