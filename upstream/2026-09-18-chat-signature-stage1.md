---
title: Chat signature pass: memos.chatSig counters, stages_cpu_ms and the static and deps sub-seams
status: candidate
where: kernel/kernel.py (`_CHAT_SIG_STATS`, `_chat_sig_scope`, `_chat_sig_note_pre`, `_chat_sig_seam_close`, `_thread_cpu`, `_PerfStats.CPU_STAGES`, `STAGES`, `CONTAINERS`, `stage`, `_chat_build_sig`, `_push`, `_pusher_cycle_jobs`, `_jobs_pass`); kernel/sdk_backend.py (`reg_reads_on_thread`); docs/reference.md; tests in `tests/test_perf_stats.py` and `tests/test_kernel_delta_send.py`
added: 2026-09-18
pr:
tier: feature
offered:
closed:
---
Upstream ships the same pusher and the same chat signature pass, which pays about 4 ms of wall per tab per cycle with a dashboard attached and had no counter for what it does. Stage 1 of the chat-signature design is measurement with zero behaviour change: GET /perf memos.chatSig counts the signatures taken (pre, post, thread, nosig, waited), the cache compare (compares, compareIdentity), the stats and the names, switch and registry reads inside a signature, and a warm-tab census (warmEligible, warmBlockedByOutline, heldBody); stages_cpu_ms carries each chat seam and container thread CPU (user, sys) from getrusage(RUSAGE_THREAD) beside the wall, empty where the platform lacks the clock, and keeps the CPU for the flat rows alone (a mark whose wall the stage-attribution fix routes to pusher.cycleJobsMs, pusher.connectPush.stagesMs or stagesForeign records no CPU row); and push.chat.sig becomes a container of push.chat.sig.static and push.chat.sig.deps under the nested-sum rule of PR 759. Every frame is byte-identical with the counting sites as no-ops, proved by the six-cycle wire test. Filed 2026-09-18 by the fork performance session.
