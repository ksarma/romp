---
title: Planner skip key: cleared.jsonl, the session death marker and the stall slice are terms of the key, so a clear, a death or a stall re-runs the planner instead of serving a skipped pass
status: candidate
where: kernel/judge.py _plan_key (three trailing terms, _stall_term); tests/test_planner_key_terms.py
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
Upstream #1173 keys the planner skip on the goal store, the episodes file and the task store; the fork adds the cleared set, the GONEDIR death marker and the stall slice, without which a clear, a death or a stall serves a skipped pass. Landed in the 2026-09-09 fold (slice 3) on the reviewer ruling; an offer candidate, the twin of the nudge gate cleared-set term.
