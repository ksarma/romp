---
title: Perf round 4 B: `_run_judging` finds each usage row's gloss by bisect on the sorted artifact-mark times and starts its horizon walk at bisect_left(t0 - 1) on the judge-usage rows when the reader's order fact holds; the reader verifies numeric, non-decreasing `t` and run end at most `t + 1` per appended row and hands the flag out with the snapshot
status: candidate
where: fork branch `perf4-judging-bisect` (PR pending): `kernel/kernel.py` (`_JudgeUsageSnapshot`, `_judge_usage_row_in_order`, `_judge_usage_rows_locked`, `_run_judging`); tests `tests/test_kernel_judging_bisect.py` (equivalence against a private copy of the pre-bisect function, the reader's flag, the horizon edges, growth between calls, the access-count proof that the walk starts at the horizon)
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
Upstream's `_run_judging` re-filters every same-(sid, judge) artifact mark per usage row and walks every retained row of the 31-day cache to keep the 48 h it plots; on the timeline profile the function was 15% of a bars build. Both lists are sorted by t, so both answers are prefix boundaries: bisect_right on the mark times for the gloss (ties included as the <= comparison included them), bisect_left at t0 - 1 on the row times for the first row that can pass the horizon filter, sound because the writer stamps t after recv so every row ends at or before t + 1. The reader checks the three facts the bisect needs once per appended row and returns the flag on the snapshot under the same lock as the rows; a file that breaks any of them walks every row as before, and a rotation or path change re-derives it. Output identical to the scans in the same order, no new persistent state, no memo. Measured on a 43,231-row log (4,413 rows inside 48 h, 32 alive sessions, 2,207 marks): `_run_judging` 48.7 to 12.2 ms median with an identical output digest; `build_timeline_bars` in tools/perf-bench.py 778 to 713 ms median.
