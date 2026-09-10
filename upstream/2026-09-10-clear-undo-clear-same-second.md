---
title: Override replay: a same-second re-clear or re-undo replays over a snapshot that already holds the earlier gesture (_newest_seal replaces the boolean twin check in the clear and unclear arms)
status: merged
where: kernel/judge.py (_replay_overrides: _newest_seal, the clear and unclear arms), tests/test_kernel_goal_compaction.py (ClearedLedgerIsAuthoritativeAcrossTheCompaction, four new tests on a private sid)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1233
closed: 2026-09-10
---
Defect in their #1190 and #1187 found while verifying them for the fold: the twin check read an earlier same-second sibling's surviving write as the row's own, so a clear, undo, clear inside one second lost the re-clear over a snapshot taken after the undo, and the mirror shape kept a released card flagged. Upstream-native; filed directly from the upstream base.
