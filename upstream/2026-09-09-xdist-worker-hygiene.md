---
title: Tests: restore the shared judge roots and the sessions-file seam after every test, and fail the test that does not
status: offered
where: upstream-only tests change on fork branch `xdist-hygiene-offer` (commit `ba878a98` on their main `ab144390`): `tests/conftest.py` autouse guard `_shared_state_restored` plus `restore_env`; save/restore of `jd.STATE`/`jd.PROJECTS` in test_episode_boundary, test_kernel_goal_compaction, test_session_retry_suppress, test_subagent_transcripts, test_chat_delta_resync, test_clear_chat_view; seam restores in seven postal modules and test_judge_rate_limit_gate; a KeylessKeyBilledCalls fixture fix. The fork has its own victim-side fix in #438 (tag_edit_ack private roots), verified compatible with the guard; the fold reconciles
added: 2026-09-09
pr:
tier: docs
offered: their PR #1176
closed:
---
Root cause: kernel.py loads the judge with SourceFileLoader("romp_judge").load_module(), which re-executes into the one module object in sys.modules, so every kernel-loading test shares jd.STATE; a test that rebinds it to a temp dir and removes the dir without restoring breaks every later jd.STATE user on that xdist worker. Reproduced on upstream 3e4398a3: three default -n 8 runs clean, loadfile and loadscope red in about half the runs, every victim green alone; attributions confirmed by a two-module deterministic run each. The known-test-flakes memory listed these as flakes since 2026-09-07; they were deterministic ordering dependencies.
