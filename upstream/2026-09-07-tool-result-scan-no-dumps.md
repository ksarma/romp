---
title: Perf P4: `_seg_mids` and `_fold_tasks` stop encoding every list-shaped tool_result with `json.dumps` to search it for a string; `_encoded_mids` walks the result and visits the strings the encoding would write, encoding only a string that contains the marker literal, and `_fold_tasks` encodes at the one read (TaskCreate) that needs the text
status: merged
where: fork PR #263 (`perf2-segmids`, merged 2026-09-07 in batch #277): `kernel/kernel.py` (`_seg_mids`, `_encoded_mids`, `_fold_tasks`); tests `tests/test_kernel_tool_result_scan.py` (15 tests, 24 subtests; a verbatim copy of the old `_seg_mids` is the oracle), `tests/test_kernel.py` (the seg_mids test asserts list equality, not set equality)
added: 2026-09-07
pr: 263
tier: fix
offered: their PR #1060
closed: 2026-09-08
---
Upstream has both functions in this shape. `_seg_mids` runs once per segment on every timeline build, and the results it encodes are mostly base64 image blocks and tool_reference blocks that never carry a marker: in the 2026-09-06 pusher profile `json.dumps` under `_seg_mids` was 2.3% of the thread and under `_fold_tasks` another 0.3%. The ids come back unchanged and in the same order: a match cannot cross the encoder's `, ` and `: ` separators because the id admits no space, and every non-string value encodes to digits, `true`/`false`/`null` or brackets, none of which can hold a marker. Two cases that raised before now yield no ids: a result value `json.dumps` refuses, and a text block whose `text` is null. The oracle test covers every content shape the SDK passes through (a plain string, text blocks beside image and tool_reference blocks, bare strings in a list, nested dicts and dict keys, None) and the shapes it does not, plus order, duplicates and the escaped marker shapes no emitter writes. Micro-benchmark over 200 synthetic segments: 42.7 ms to 14.2 ms (medians). The chat's displayed check_inbox output still encodes its result, deliberately: that string is displayed, not only searched.

Based on main; no dependency on the rest of the round-2 stack or on `/perf`.

OFFERED 2026-09-08: offered upstream inside bundle PR #1060 (Pusher: one build, one encode and one compare per change; the timeline's live tick translates the plot; label fix; branch pusher-timeline-offer; head 7da31ce9; a draft while the branch is rebased onto the moved upstream tip) with `view-delta-identity-short-circuit`, `timeline-skeleton-from-cache`, `one-encode-per-payload-per-build-on-the-pusher-thread-plan`, `tick-jobs-wake-memos-discover-once` and the timeline's live tick (P5) of `browser-round2-cuts`.

MERGED 2026-09-08: merged upstream as their PR #1060 (merge dd310bb9, 2026-09-08T15:37:14Z) after the maintainer's own review commit.
