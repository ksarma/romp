---
title: Their edit trace (`_edit_trace_body`, #542's consent-gate commit) embeds the request-supplied file PATH with no marker hygiene — a marker-shaped filename becomes a live `romp-msg-id`/`romp-tag`/`romp-injected` match in the injected body
status: merged
where: fold-review fix in `upfold0823`: the path runs through `_neutralize_romp_markers`, like every untrusted half of an injected body
added: 2026-08-23
pr:
tier:
offered: their PR #575
closed: 2026-08-23
---
MERGED as-is (head is an ancestor of their main, verified 2026-08-24). Branch retired. OFFERED 2026-08-23 (branch `edit-trace-markers`, `dbd6a44a` off tip `147678b1`): carved to ONLY the neutralizer + _edit_trace_body application, tests re-homed off test_user_todos.py (user-todos stays unoffered; its future offer must REUSE the upstream helper); review clean, scaffold CI green (since-closed fork #106). NOTE for the next fold: helper placement diverges (fork keeps it in the todos neighborhood) — dedup deliberately. The neutralizer is fork-side (the user-todos answer-body work) and would travel with an offer. Pinned in tests/test_user_todos.py's MarkerNeutralizerVariants against the verbatim downstream regexes.

Status detail (migrated from the table): ✅ **merged** — their PR #575, merged as-is 2026-08-23 (merge `7ab7941f`)
