---
title: Judge: save_goals refuses to publish a store that loaded as a fallback for a goals file that exists and did not read
status: candidate
where: fork PR #322 (`unread-store-save`, stacked on #317): `kernel/judge.py` (`UnreadStoreError`, `save_goals`, `_disk_rev`, `_mark_unread`, `_fallback_store`, `load_goals`, `load_goals_shared`, `load_goal_archive`, `save_goal_archive`, `unreadable_store_sids`, `goal_io_stats`, `fast_forward_placements`, the six stages' and the courier's stand-down, `run_propagate`); `kernel/kernel.py` (`_undo_clear`, `_restore_goal_archive`, `_compact_goal_stores`, `_unreadable_store_warns`, the `undoClear` handler); `bin/romp` (the perf goals line); `ui/webview/feed.ts` (`undoClearResult`); `docs/reference.md`; tests `tests/test_unread_store_save.py`, `tests/test_judge_stage_gate.py`, `tests/test_judge_store_cas.py`, `tests/test_courier_kind_demote_only.py`, `tests/test_perf_stats.py`, `tests/romp-perf.bats`, `ui/webview/feed-undo-result.test.ts`
added: 2026-09-07
pr: 322
tier: fix
offered:
closed:
---
load_goals answers an empty store when the goals file exists and cannot be read or parsed, and save_goals took that fallback for a create: its base revision 0 matched the 0 that _disk_rev answered for the unparseable file, so the grouper and consolidator (their signature write), the planner and closer (their unconditional pass-end save) and the kernel's undo-clear restore each replaced the file with the empty fallback, after which it read again, empty. save_goals now refuses a store marked as a store fallback and refuses when the CAS cannot read the file at publish time (_disk_rev None), leaving the file and the holder's base as they were, with one judge-errors row; the mark carries its reason, and a store whose journal did not read still publishes (its content is the file's; the journal replays on every load). load_goals logs one store-unreadable row per failure episode, and the six judge stages and the courier stand down on a fallback store at the load, so a corrupt file costs no model calls. Found by the P2 gate's build (fork PR #317) and confirmed pre-existing by three independent refuters.
