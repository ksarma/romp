---
title: Perf: the judge pool workers' CPU lands in the kernel's live counters at write time, so a live read and a snapshot agree
status: candidate
where: kernel/judge.py (set_worker_cpu_sink, _judge_cpu_add), kernel/kernel.py (_PerfStats.judge_worker_cpu, the snapshot, the arming after _PERF_STATS), tests/test_perf_stats.py, tests/test_judges_process.py, tests/test_judge_serve.py, docs/reference.md
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
`_PerfStats.snapshot()` added judge.py's module-global pool counter (`jd.judge_worker_cpu_ms()`, fed by `_TimedPool`) to its COPY of `judge.cpu_ms_sum` at every read while the live dict never carried it, so a live read and a snapshot read of one counter disagreed by the whole total and a delta taken from one of each was wrong (the child-road test paid, then read both from the snapshot). The workers' CPU now lands in the live dict as each pool future ends: judge.py exposes `set_worker_cpu_sink(fn)` (a callable it holds, in the direction the module already takes for `set_sdk_owner_provider` and `run_pass(before_tier=...)`), the kernel arms it with `_PerfStats.judge_worker_cpu` right after building the collector, and the snapshot copies `cpu_ms_sum` and `cpu_ms_workers` without adding. The module counter and `judge_worker_cpu_ms()` stay for the serve child, which runs judge.py with no kernel in its process and reports `workerCpuMs` from it; the child road's fold in `judge_child_done` is unchanged. Upstream carries the read-time fold (upstream/main db73909e6, kernel/kernel.py `snapshot()` `judge["cpu_ms_sum"] += workers`). Tests: a live read and a snapshot agree after pool work (red before), the child's report lands once with `cpu_ms_workers` flat, the sink is optional (a judge module no kernel loaded keeps its counter), and a child process shows the kernel arms the sink at load.
