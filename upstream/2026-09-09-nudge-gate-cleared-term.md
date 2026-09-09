---
title: Nudge placement gate: STATE/cleared.jsonl is a term of the memo key, so a clear re-derives the gate instead of serving a stale answer
status: candidate
where: kernel/kernel.py _nudge_placement_gate (clr = _stat_key(jd.STATE / "cleared.jsonl") beside epi, held in the memo tuple and compared on the hit path); tests/test_nudge_walk_gate.py TheGateReEvaluatesOnItsInputsOnly.test_a_cleared_row_recomputes
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
Upstream #1141 (b544ee8e) keys the gate on the parse, the shared goal-store view and the episodes log; the fork adds STATE/cleared.jsonl, the cards cleared off the board (not the episodes log, which upstream calls the clears log), because plan_units reads that file live (judge.py _live_anchor_gone -> _cleared_under -> _view_cleared), so a key that omitted it served a stale answer silently after a clear. Landed in the 2026-09-09 fold (slice 3) on the reviewer ruling (A, condition 1); an offer candidate, the twin of the planner skip key terms (2026-09-09-planner-key-blind-terms).
