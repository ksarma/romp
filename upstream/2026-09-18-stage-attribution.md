---
title: GET /perf credits a jobs.<job> stage to its writer: the flat stages_ms row is the jobs thread's, the pusher's nine cycle jobs are counted under pusher.cycleJobsMs, and a write from a thread owning neither loop counts under stagesForeign
status: candidate
where: kernel/kernel.py (_PerfStats.stage, the snapshot), docs/reference.md, tests/test_perf_stats.py, tests/test_jobs_thread_split.py
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Meaning change, 2026-09-18: `stages_ms.jobs.<job>` narrowed from every thread's time under the name to the jobs thread's own; those rows keep their names and their values, since the housekeeping jobs already ran on the jobs thread alone. The pusher thread's nine cycle jobs (beginCheckpointCycle, sessionsListing, applyPendingOps, turnNotify, persistCheckpoints, convergeCheckpoints, bootRowBackstop, kernelSample, apiHealth), in those rows until then, left `stages_ms` that day and are counted from then on under `pusher.cycleJobsMs.<job>`, seeded at zero so the block is always whole; a `jobs.<job>` write from a thread owning neither loop goes to `stagesForeign`, counted rather than merged into a row that names another thread. No call site, stage mark, split row, boot row or CLI line changes; JOBS stays the census as CYCLE_JOBS + PASS_JOBS. Nothing had been exported before the change; the nine keys are not comparable across it.
