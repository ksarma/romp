---
title: Three fork-only behaviours kept through upfold0905 where upstream's evolved code sits beside them: fast judging (`_judge_fast`, `_FAST_MODELS`, the `--settings` fast opt-in in `_judge_cmd`, the gear's `setJudgeFast` toggle, `/version.judgeFast`); the user-todo delivery seam (`SdkBackend.send(sid, text, user_todo=None)`, `enqueue(todo=)`, the dict-aware `_queue_texts` / `_queue_wire`, `_mark_dropped_echoes` carrying the todo, `todo_lost=` on the backend); and parent/tags carried into upstream's new Codex arm in both doors — `_create_codex_session(parent=, tags=)` applies them through `_tag_ack` before its push and returns `(sid, echo)` like the SDK create; POST /new's Codex arm echoes `tags` / `tagsRequested` / `tagsApplied` / `parentIgnored` and refuses `env` loudly (the backend has no `set_env`); the WS op's Codex arm warns a `tagError`; the tmux refusal stays after it — so a create asked into a tag group is never spawned untagged (round 2, 2026-09-05)
status: divergence
where: `kernel/judge.py`, `kernel/sdk_backend.py`, `kernel/kernel.py` (`_dispatch_ws`'s create arms); fork `4c3b62bf` (fast judging), `d554c2f9` (the seam), the `tabgroups` branch
added: 2026-09-05
pr:
tier:
offered:
closed:
---
Fast judging was never offered (a per-install cost toggle). The seam rides the user-todos slices (candidate rows above). The Codex tagging follows from the tab-groups row and would ride that offer. None of the three changes upstream's behaviour while the fork-only feature is off.

Status detail (migrated from the table): divergence
