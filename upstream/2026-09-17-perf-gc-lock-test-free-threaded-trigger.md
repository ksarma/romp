---
title: tests/test_perf_gc_block.py's gc-under-lock case collects explicitly inside the locked region: the free-threaded collector starts no automatic collection on a burst of 2 x threshold + 100 objects
status: approved
where: tests/test_perf_gc_block.py: the module docstring's item (c), the LockFree class docstring (143-146) and test_a_collection_triggered_under_the_stats_lock_finishes (159-164 at the 2026-09-17 catch-up fold's merge 2def2572f)
added: 2026-09-17
pr:
tier: docs
offered:
closed:
---
The case pins the review's deadlock (a gc.callbacks hook that took the stats lock waited on its own thread forever): it allocates 2 x gc.get_threshold()[0] + 100 lists on a helper thread under the lock and expects the collector to run there. That is the GIL build's scheduling. The free-threaded collector (CPython 3.14t, Python/gc_free_threading.c gc_should_collect) also requires the young count to reach a quarter of the live objects and the process's memory to have grown by a tenth since the last collection, which the test's own gc.collect() has just reset, so the burst starts no collection and the witness list stays empty (the fork's 3.14t CI cell, 2026-09-17; upstream's matrix stops at 3.13). The fix adds gc.collect() inside the locked region: the same callback path on the same thread with the lock held, on every build; a probe with the first draft's lock-taking callback still deadlocks there (red on 3.12 and 3.14t). Test-only.

2026-09-18: approved for offer by the user (batch 7 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
