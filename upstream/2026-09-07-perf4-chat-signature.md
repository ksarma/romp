---
title: Chat build: a complete per-session signature replaces the judge-pass counter (round-4 P4)
status: offered
where: kernel/kernel.py (_chat_build_sig, _CHAT_SIG_LABELS, _chat_build_deps, _chat_sig_deps, _chat_sig_shared, _names_digest, _claudemd_paths, build_session's dependency record, _read_task_output, _subagent_meta_map, _agent_steps, _push, _PerfStats, _tmux_echo_rev, Sessions.live_rev), kernel/sdk_backend.py (_touch_live, live_rev), docs/reference.md, tests/test_live_tail_rev.py, tests/test_chat_build_sig_inputs.py, tests/test_chat_fixed_cost_memos.py, tests/test_perf_stats.py, tests/test_stage0_log_readers.py, tests/romp-perf.bats, ui/webview/tab-snapshot.test.ts
added: 2026-09-07
pr:
tier: fix
offered: their PR #1277
closed:
---
The chat-build cache's signature no longer folds the global judge-pass counter, which rebuilt every background chat tab on every judge pass (about 360 of 410 background rebuilds per 120 s, byte-identical). It is a flat tuple with one labelled component per input build_session reads: files by identity, in-memory inputs by value, the live tail and the warm-anchor table by revision, the names registry by digest, clock crossings as booleans, and three build-time dependencies (task-output tails and the agent files the Agent cards read, pending path tokens, postal cards) recorded on the cache entry and re-evaluated per cycle. Every tab is served on this one key, the watched one included (upstream's separate active-tab key, _active_chat_sig, and its _views_dirty watermark for the chat are retired: each stamp they covered is a component, and the post-build re-signature covers an input that moves while the build runs). A census test maps every read build_session makes to a component; a differential suite moves each input alone. Both backends count a per-session live-tail revision for it (the SDK backend's upstream _touch_live, with one bump per changed call).

Re-derived onto the project's chat build after their #1251 (the fixed-cost memos) merged: three commits (the live-tail revision, the one signature, docs and the two webview comments); the live= handoff took the allowed alternative (_serve_live scope inside the signature). Filed 2026-09-10.
