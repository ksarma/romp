---
title: Timeline dead-lane memo: the stat key carries st_ctime_ns (a chmod or rename moves it) and the dead-lane key carries the host downtime spans (a suspension recorded after a dead lane was cached re-derives it); a failed dead parse is cached as the empty lane until the stat moves
status: offered
where: kernel/kernel.py _stat_key, _dead_lane_key, the dead-lane populate in build_timeline (the failed field), _lanes_stats dead_serve/dead_miss/dead_failed_serve and _lanes_memo_report; tests/test_timeline_lane_memo.py DeadLanes; tests/test_perf_stats.py
added: 2026-09-09
pr:
tier: fix
offered: their PR #1175 (fork branch `dead-lane-key-offer`, commit `e1ed5a7f` on their main `ab144390`; `_stat_key` gains `st_ctime_ns`, `_dead_lane_key` ends in `tuple(_downtime)`; the cleared-set memo test pin moves to 5)
closed:
---
Upstream #1131 derives a dead lane once and serves it while its keyed inputs stand, but two inputs the lane reads are missing from its key. A chmod or a rename moves neither mtime nor size, so st_ctime_ns joins _stat_key; a host suspension recorded after the lane was cached (the spans _awake_spans excises from every bar) left the un-excised bar served until a keyed file moved, which a dead transcript never does, so tuple(_downtime) joins _dead_lane_key. With ctime in the key a failed dead parse is cached as the empty lane (a dead file has no writer, so re-parsing every cycle yields nothing, and a corrupt large file was otherwise re-read every ~6 s for the 48 h window); a permission fix moves the stat and re-attempts it. dead_serve, dead_miss and dead_failed_serve keep the memo's hit share readable, live-only from this fold. Landed in the 2026-09-09 fold (slice 1), conditions 2 and 3 of the lane memo ruling; upstream #1131 lacks these.
