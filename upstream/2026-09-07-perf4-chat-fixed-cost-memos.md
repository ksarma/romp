---
title: Chat build: attribution counters and exact memos for the per-build fixed costs (round-4 P3)
status: merged
where: kernel/kernel.py (build_session, _chat_build_sig labels, _merge_live_atoms, _fold_tasks, _hydrate_postal, _msg_summaries, _node_anchor_uuids, _PerfStats), bin/romp, docs/reference.md, tests/test_chat_fixed_cost_memos.py, tests/test_chat_fold.py, tests/test_postal_hydrate_scope.py, tests/test_perf_stats.py, tests/romp-perf.bats
added: 2026-09-07
pr:
tier: fix
offered: their PR #1251
closed: 2026-09-10
---
builds.chat gains active/background counts and a per-component miss attribution; the live merge, the fold gate postal cards, the goal-tree walk and the task fold are memoized on every input they read (identity-held objects, stat-before-read keys); the fold commit hydrates only raw postal events new since the seal; _msg_summaries is re-keyed on the captions file and the goal store. The ledger and task-fold memos are labelled interim pending P4.
