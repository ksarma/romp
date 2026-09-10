---
title: A SIGTERM nobody asked for leaves a row and a cut reason (signal, manager-sigterm and parent-gone audit rows; _drain_and_exit shared with _parent_watch; the reader bounds at the kernel's start), and the manager notes every kill it sends
status: merged
where: kernel/kernel.py, bin/romp-manager, tests/test_restart_cuts.py, tests/manager-exit-attribution.test.js, docs/reference.md, bin/README.md
added: 2026-09-10
pr: 272
tier: fix
offered: their PR #1286
closed: 2026-09-10
---
Divergence-audit row 27 PR 1b (exit attribution), the second defect the 2026-09-06 outage exposed. romp-down (PR 2) stacks on this branch.
