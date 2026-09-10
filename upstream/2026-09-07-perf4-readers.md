---
title: Stat-keyed memos for the per-lane readers every timeline build re-read (captions with message and segment indexes, states-overlay fold, SDK registry), and exact memory gauges on the /perf snapshot with two romp perf lines
status: candidate
where: fork branch `perf4-readers` (kernel/kernel.py `_captions` / `_Caps` / `_seg_caption` / `_seg_work_caption` / `_states_awaiting_overlay` / `_thread_reg` / `_process_stats` / `_cache_gauges` / `_PerfStats.snapshot`; kernel/event_model.py `fold_records(on=)` and `cache_gauges`; kernel/judge.py `cache_gauges`; bin/romp `perf`; tools/perf-bench.py; tests/test_kernel_captions_memo.py, tests/test_kernel_msgcaption.py, tests/test_perf_stats.py, tests/test_perf_bench.py, tests/romp-perf.bats; docs/reference.md)
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
Perf round 4, PR 6 (item C items 1-4 and M1-lite). Offline bench on the sealed state copy, 31 live sessions, medians of 5: build_timeline bars 937 -> 467 ms, skeleton 103 -> 43 ms, build_feed 680 -> 623 ms (100%-hit ceilings, not the acceptance number). Every memo keys on (inode, mtime_ns, size) taken before the read, or folds through the shared append-incremental reader, and reports hit/miss counters and its occupancy under /perf memos. The gauges are exact occupancy only (no sampler, no estimator); two live snapshots an hour apart decide between an allocator fix, an object-graph sampler and a departure sweep.

The C3 slice (the states-overlay fold with its intrMarks/statesOverlay memos reporting under /perf) is offered separately as their PR #1228 (entry interrupt-tick-tail-memos, 2026-09-09); the captions, SDK-registry and memory-gauge slices stay in this entry.
