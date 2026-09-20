---
title: The pusher memo tests state their jobs pass, and the empty-window case counts its reads instead of a threshold
status: merged
where: tests/test_kernel_pusher_snapshot.py: _CycleFixture.setUp (the pass-counter pin), OneDiscoverPerCycle._cycle (the read count) and test_an_empty_window_is_still_one_sweep_per_cycle; fork branch pusher-memo-order, landed on the fork 2026-09-18 as a tests-only change
added: 2026-09-18
pr:
tier: docs
offered: their PR #1887
closed: 2026-09-19
---
test_an_empty_window_is_still_one_sweep_per_cycle failed alone (4 memo hits against the 5 it asserted) and passed after a sibling that had run a _jobs_cycle in the same process; pytest-xdist schedules every test on its own, so it could fail in any full run whose worker had not run a sibling first. The fifth reader was _spend_guard_tick, which _jobs_pass skips on the process first pass (_PERF_STATS.jobs["passes"] >= 1, the T401 follow-up) and which also returns before its read when the spend ceiling is 0; the counter is module state the fixture never set, and with an empty window the _path_of reads under _compacting_now that carry the two-session siblings past the threshold are gone, so the guard decided the count. The kernel is right and the pin (one miss per key with an empty result memoized) is right. The fixture now pins the pass counter to at least one for every cycle test (mock.patch.dict, the shape tests/test_spend_tree_memo.py uses), and the empty-window case asserts hit + miss == the reads the pass made and at least one hit, so it holds on a cold pass, with the guard off, and after any sibling; a mutant that reads an empty memo value as a miss still fails it. The fix is the fork branch pusher-memo-order. The project has the same case and the same first-pass gate (unchanged on its main through e7e68f0c9, 2026-09-18; the census ran it on 2301f38af, 3 of 3 red alone).

2026-09-19: offered as their PR #1887 at 08:18Z (docs tier, its own branch on the project's tip ba9321388, not stacked; the re-derived change counts the pass's reads and pins the jobs pass, +33/-6 on the one test module).

2026-09-19: merged upstream at 09:23Z (207336c1b) by the project's maintainer; the scaffold and branch pair are closed and deleted.
