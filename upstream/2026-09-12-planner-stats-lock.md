---
title: Planner gate: the skip counters are bumped under a lock (a lost update on free-threaded 3.14t)
status: candidate
where: kernel/judge.py: _PLANNER_STATS_LOCK, _planner_stat, planner_skip_stats; tests/test_planner_skip.py
added: 2026-09-12
pr:
tier: fix
offered:
closed:
---
run_plan bumps _PLANNER_STATS from every planner worker at once and d[k] += 1 is a read, an add and a write; with the GIL off two workers read the same value and one bump is lost, so a settled pass over three sessions reports (0, 2, 0). CI 3.14t cell, three sightings 2026-09-10 to -12; reproduced 1 in 150 runs on a free-threaded 3.14.6. Upstream kernel/judge.py carries the same three unlocked bumps.
