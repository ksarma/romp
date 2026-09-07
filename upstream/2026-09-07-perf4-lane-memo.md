---
title: A per-lane segment memo in build_timeline keyed on the parse, store and captions objects, with _derive_judging split into a clock-free derivation and the horizon assembly
status: candidate
where: fork branch `perf4-lanes` (kernel/kernel.py `_lane_segments` / `_lane_memo` / `_lanes_forget` / `_lanes_memo_report` / `_derive_judging_marks` / `_judging_assemble` / `build_timeline` / `_PerfStats.snapshot`; tests/test_timeline_lane_memo.py, tests/test_timeline_bars_resilience.py, tests/test_kernel_goal_cache_wiring.py, tests/test_perf_stats.py, ui/timeline-lineage.test.ts; docs/reference.md)
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
Perf round 4, PR 9 (item A, amended form). Offline bench on the sealed state copy, 31 live sessions, medians of 5, two before/after pairs: build_timeline bars 476.7 -> 93.4 ms and 477.6 -> 94.5 ms (100%-hit ceilings, not the acceptance number); a 30-build replay at a 2 s cadence served 99.3% of lanes and 99.5% of segments after the first build. Every input is in the key by object identity or by value, the horizon and the caption cap are applied at assembly, a live tail or a private store derives without holding, and the memo reports one outcome per lane per full build under /perf memos.lanes.
