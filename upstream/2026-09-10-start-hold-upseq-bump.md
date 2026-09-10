---
title: Tunnel rows: the recovery counter (upSeq) bumps once per Start, not once per answered poll under the Start hold (_note_recovery returns without bumping or spending the miss marks while booting)
status: merged
where: kernel/kernel.py (_note_recovery), tests/test_kernel_tunnel_truth.py (RecoveryCounter, four tests)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1239
closed: 2026-09-10
---
Contract defect in their #1209 found while verifying it for the fold: every answered pass under a Start hold bumped the counter (1, 2, 3, then 4 when the hold cleared); the dashboard was immune because the row reads starting. Upstream-native; filed directly from the upstream base.
