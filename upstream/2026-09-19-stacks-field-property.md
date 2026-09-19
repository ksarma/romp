---
title: The stacks field test pins two entries keyed other, not the sampled frame
status: candidate
where: tests/test_perf_stats.py
added: 2026-09-19
pr:
tier: fix
offered:
closed:
---
tests/test_perf_stats.py StacksField test_two_threads_outside_the_register_are_two_entries_keyed_other asserted that a parked thread's innermost frame starts with wait; on the free-threaded 3.14 build the sampler catches the thread at the lock acquire inside Condition.wait (Condition.__enter__) about three module runs in ten. The test now asserts the property it is named for: two entries whose ident half is a planted thread's, each keyed by its own ident and other, each a stack sample (function (file:line) frames from the standard library or this repo, self false, no stage), no frame pinned. Not a retry count and not a second-frame pin, which are the same defect one step out. Based on main, not on PR 831.
