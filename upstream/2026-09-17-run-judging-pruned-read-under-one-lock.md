---
title: The judging band reads the reader's prune count, checks its boundary and slices the live rows in three unlocked steps, so a prune landing between the check and the slice drops rows from one frame
status: candidate
where: kernel/kernel.py (_judge_usage_cursor, the pruned read, the boundary check and the slice under one _JUDGE_USAGE_LOCK hold; _run_judging's read; _judge_usage_rows_snapshot for the /analytics roll-up); tests/test_free_threaded_caches.py::JudgeUsageWalkers
added: 2026-09-17
pr:
tier: fix
offered:
closed:
---
_run_judging (the judging band memo, romp-on/romp pull 1798) reads _JUDGE_USAGE_CACHE's pruned count, verifies the boundary object at the shifted cursor and takes rows[skip:] as three steps with no lock held, while the reader's left prune runs under the lock on whichever thread reads the log (an analytics request, a cold connect push) and shifts every index in place. A prune landing between the boundary check and the slice starts the slice that many rows past the verified boundary, so one bars frame loses the rows in between (healed by the next build's reset). Unreachable on a GIL build in practice (no eval breaker between the check and the slice on CPython 3.12) and reproduced deterministically on a free-threaded interpreter, which the fork's CI runs as a cell upstream lacks. The fix takes the count, the check and the slice under one hold of the reader's lock (a small cursor helper); the same review found the /analytics roll-up walking the live list unlocked once the reader stopped copying it, so the roll-up walks a snapshot copied under the lock. Pinned by two interleaving tests: the roll-up counts the rows present at its walk's start while a second thread appends and prunes through the reader, and the band's frame carries every horizon row present at its read while a second thread that itself takes the lock prunes between the check and the slice. Found by the 2026-09-17 catch-up fold's kernel review (items 5 and 6).
