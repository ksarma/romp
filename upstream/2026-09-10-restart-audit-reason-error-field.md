---
title: Kernel exit path: a dead stderr no longer skips the drain or the exit, and the cut row names the reason helper's fault (reasonError)
status: merged
where: docs/reference.md kernel/kernel.py tests/test_restart_cuts.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1304
closed: 2026-09-10
---
From the maintainer's post-merge record on their #1286's review-fix commit f36ddba8 (items 1 to 3): the cut row carries reasonError when the reason helper fails; a direct-call pin of the helper's stderr guard (restart-audit-stderr-guard-pin); the exit path's stderr writes go through one guarded helper so a dead stderr never skips the drain or the exit (restart-audit-drain-announce-guard). Stacked on their #1302 (restart-audit-followups).
