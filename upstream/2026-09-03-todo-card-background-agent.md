---
title: To-do card false alarm: `_fold_tasks` folded a BACKGROUND-AGENT `TaskCreate` (the Task tool's `{agent_hint, prompt}` shape, no `subject`, result is an agent id not "Task #N") into the checklist as a phantom pending task, so a session that only launched background agents tripped the card's "can't read the task store" error whenever the store was unresolvable
status: offered
where: branch `todofix`: `kernel/kernel.py` (`_fold_tasks` guard), `tests/test_kernel.py`
added: 2026-09-03
pr:
tier: fix
offered: their PR #942
closed:
---
OFFERED 2026-09-06 (branch `todofix-offer`, `764089c8` off tip `2b9db2be`): the review caught a REAL recorded background-task id in the test fixture and this row/kernel comment named another project’s session — both redacted here and in the offer (the strings are now in the private-strings scanner); the card-level assertion was made non-vacuous. Scaffold CI green (since-closed fork #205). Upstream ships the same `_fold_tasks` and the same error card, so the same false alarm. One guard: a create with no `subject` and a `prompt`/`agent_hint` is a background task, not a to-do — it does not fold. Repro: a background-agent-only session (another project)'s overnight pipeline (the user 2026-09-03). ~3 lines + a test; ports as-is.

Status detail (migrated from the table): **offered** — their PR #942 (2026-09-06), label `fix`
