---
title: Chat build: a complete per-session signature replaces the judge-pass counter (round-4 P4)
status: candidate
where: kernel/kernel.py (_chat_build_sig, _CHAT_SIG_LABELS, _chat_build_deps, _chat_sig_deps, _chat_sig_shared, _names_rev, _claudemd_paths, build_session's dependency record, _read_task_output, _push, _PerfStats, _tmux_echo_rev, Sessions.live_rev), kernel/sdk_backend.py (_live_rev_bump, live_rev), docs/reference.md, tests/test_live_tail_rev.py, tests/test_chat_build_sig_inputs.py, tests/test_chat_fixed_cost_memos.py, tests/test_perf_stats.py, tests/romp-perf.bats, ui/webview/tab-snapshot.test.ts
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
The chat-build cache's signature no longer folds the global judge-pass counter, which rebuilt every background chat tab on every judge pass (about 360 of 410 background rebuilds per 120 s, byte-identical). It is a flat tuple with one labelled component per input build_session reads: files by identity, in-memory inputs by value, the live tail, the warm-anchor table and the names registry by revision, clock crossings as booleans, and three build-time dependencies (task-output tails, pending path tokens, postal cards) recorded on the cache entry and re-evaluated per cycle. A census test maps every read build_session makes to a component; a differential suite moves each input alone. Both backends count a per-session live-tail revision for it.
