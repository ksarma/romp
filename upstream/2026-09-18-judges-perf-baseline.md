---
title: Child-road perf test: the cpu_ms_sum baseline reads the snapshot it is compared against
status: candidate
where: tests/test_judges_process.py (plus one sentence each in kernel/kernel.py's _PerfStats docstring and docs/reference.md)
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
Tests-only. ChildRoad's one-pass test read its cpu_ms_sum baseline from the live _PERF_STATS.judge dict and its after value from snapshot(), which adds judge.py's module-global in-process pool total (jd.judge_worker_cpu_ms()) to its copy at read time; judge.py is one module object per test process, so pool work another module ran earlier in the same xdist worker landed in the delta (7.0465 for 7.0 in a full -n 12 run, 2026-09-18). The baseline now reads the snapshot; the comparison tolerates ulp rounding (two sums sharing a non-round addend round on different grids, so a literal equality flaked in half the draws); a new pin drives real pool work first and asserts both deltas and the read-time composition; the docstring and the reference say a delta comes from one source. Upstream's copy carries the same live-baseline line (upstream/main dacb28bdf, tests/test_judges_process.py:171). The counter's meaning is unchanged.
