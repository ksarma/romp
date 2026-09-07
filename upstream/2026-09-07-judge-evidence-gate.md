---
title: Judge: an evidence gate for the planner and closer, with the parse key pinned under the pass frame
status: candidate
where: fork PR #301 (`judge-gate`): `kernel/judge.py` (`_frame_parse_key`, `parsed_session`, `tasks_for`; `_STAGE_STAMP`, `_stage_sig`, `_gate_check`, `_gated`, `run_plan`, `run_close`, `_settle_not_before`; `_close_session`'s lazy `seg_by_id`; `save_goals`' `noop_hash_ms`), `kernel/event_model.py` (`_bg_expiry_t`, `task_store_dir`, `task_store_fp`), `kernel/kernel.py` (`_PerfStats` judge wakes and tiers, `_CountedEvent(on_set)`, `_producer_wake`), `bin/romp` (perf: cpu/pass, wakes, tiers, no-op hash); tests `tests/test_judge_stage_gate.py`, `tests/test_judge_pass_frame.py`
added: 2026-09-07
pr: 301
tier: feature
offered:
closed:
---
Upstream's planner and closer run every discovered session in full every pass, with about two of thirty sessions holding anything new; the two tiers are a third of an idle pass's CPU and nearly all of its saves. The gate skips a (tier, session) run only when every input the tier reads is identical by identity to what it last judged to completion, with the parse key pinned under the pass frame before anything is read so a stamp has something exact to stand for, a completeness bit so a deferred or failed run never stamps, and a background launch's deadline as the one clock input. Measured on a 31-session state copy: cpu/pass 1.30 s to 0.49 s for the two tiers, 56 of 62 saves per pass gone, the closer skipping 99-100% of sessions. Depends on the pass frame (upstream has it) and on P9's shared store counters only for the perf lines; P2 (the store-only tiers on the same gate) follows in the fork.
