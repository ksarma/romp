---
title: Judge: the store-only tiers (unblocker, grouper, consolidator, distiller) on the evidence gate, with three identity memos
status: candidate
where: fork PR #317 (`judge-gate-p2`, based on #301): `kernel/judge.py` (`PARSE_TIERS`, `_sig_inputs`, `_stage_sig`, `_gated`, `run_unblock`, `run_group`, `run_consolidate`, `run_distill`, `_mark_unread`, `_read_failed` and the stage-site completeness marks; `_kids_map` and `_distill_due_t`, `_live_prompt_since`, `_view_cleared`, `stalled_facts`); tests `tests/test_judge_stage_gate.py`, `tests/test_judge_identity_memos.py`, `tests/romp-perf.bats`
added: 2026-09-07
pr: 317
tier: feature
offered:
closed:
---
Upstream's four store-only judge tiers load and walk every discovered session's store every pass (132 of 455 loads per pass on the live kernel) to decide, almost always, that nothing is owed. They now run through the same evidence gate as the planner and closer, each keyed on what its decision path reads: the unblocker on the pinned parse pair and the store trio; the grouper and consolidator on the store trio and cleared.jsonl; the distiller on the store trio, the states file and its own stall records. Every no-write deferral marks the run incomplete, and a store that loads as a fallback (an unparseable file, an unreadable journal) marks it too, so the per-pass judge-errors row and the retry survive the gate. Three identity memos come first: one children map per store for `_distill_due_t`, and `_live_prompt_since` and `_view_cleared` memoized on their append-only files' identity. Measured on the 31-session state copy with the judge paused: the four tiers' idle pass 0.59 s to 0.17 s CPU and 124 to 20 store loads (the memos alone 0.59 to 0.44 s), the whole triage sequence 1.37 s to 1.13 s and 199 to 96 loads per pass; the grouper skips 90% of sessions, the consolidator 97%, the distiller 100%, the unblocker 48% on the paused bench (16 sessions hold blocks a paused model cannot examine; live, each examines once and stamps). Depends on PR #301 (the gate) and, like it, on the pass frame.
