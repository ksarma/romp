---
title: `_patch_rows` raises TypeError on a structuredPatch hunk whose lines array carries a non-string (`ln[:1]` on int/None), and the chat-build consumer has no guard — the escape reaches the pusher's outer try and aborts EVERY push cycle permanently, since the bad record is permanent; every other odd shape already degrades to no rows
status: merged
where: fold-review fix in `upfold0825`: a non-string line entry degrades its hunk inside `_patch_rows`' existing bad-shape idiom; pinned red-first in `tests/test_kernel_patch_rows.py`
added: 2026-08-25
pr:
tier:
offered: their PR #736
closed: 2026-08-27
---
MERGED as-is (head is an ancestor of their main, verified same night). Branch retired. OFFERED 2026-08-27 (branch `patchrows-guard`, `dd9d4383` off tip `14a4bd70`): all three raise sites guarded, transplanted clean of the mixed fork commit’s other concerns; review clean, scaffold CI green (since-closed fork #115). Upstream ships `_patch_rows` and the guardless consumer verbatim (the structuredPatch chain their #576 wired live). Three-line fix, no fork-specific content.

Status detail (migrated from the table): ✅ **merged** — their PR #736, merged as-is 2026-08-27 (merge `ae718e50`)
