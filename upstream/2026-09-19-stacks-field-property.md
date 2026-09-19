---
title: The stacks field test pins two entries keyed other, not the sampled frame
status: candidate
where: tests/test_perf_stats.py
added: 2026-09-19
pr: 834
tier: fix
offered:
closed:
---
tests/test_perf_stats.py StacksField test_two_threads_outside_the_register_are_two_entries_keyed_other asserted that a parked thread's innermost frame starts with wait; on the free-threaded 3.14 build the sampler catches the thread at the lock acquire inside Condition.wait (Condition.__enter__) about three module runs in ten. The test now asserts the property it is named for: two entries whose ident half is a planted thread's, each keyed by its own ident and other, each a stack sample (function (file:line) frames from the standard library or this repo, self false, no stage), no frame pinned. Not a retry count and not a second-frame pin, which are the same defect one step out. The three siblings that carried the same innermost-frame pin (StacksField.test_two_threads_sharing_a_name_are_two_entries, ServedSnapshotIsPasteSafe.test_a_thread_named_with_a_path_and_an_id_is_keyed_other_and_the_walk_stays_clean, PerfRoutes.test_get_perf_stacks_carries_one_frame_list_per_thread_with_its_stage_mark) pin their own properties and a shared _assert_stack_sample helper in a second commit. Based on main, not on PR 831.
