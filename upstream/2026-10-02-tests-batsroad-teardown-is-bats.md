---
title: BatsRoad's timeout test asserts the bound, TERM then KILL to the group and no process left; the poll's teardown under the group TERM is a race inside bats and is no longer asserted
status: candidate
where: tests/test_bats_bare_negation.py (BatsRoad timeout test, renamed; _end_group docstring; BatsRoad.POLL comment), upstream/2026-10-02-tests-batsroad-teardown-is-bats.md (this entry)
added: 2026-10-02
pr: 946
tier: docs
offered:
closed:
---
BatsRoad's timeout test, now test_a_run_past_the_bound_is_timed_out_its_group_sent_term_then_kill_and_no_process_of_it_left (before: test_a_run_past_the_bound_is_timed_out_with_its_teardown_run_and_no_process_of_it_left), no longer asserts the poll test's teardown marker. bats does not promise that teardown under the group TERM: bats-exec-test appends the teardown's output to a file under BATS_RUN_TMPDIR, and the bats leader's EXIT trap removes that directory under the same TERM, so whichever process runs first decides it (bats 1.10.0 and 1.11.1). The marker assertion went red in 49 of 50 runs pinned to one CPU, 8 of 150 unpinned local runs and 1 of 320 CI shell jobs. The test now asserts what romp controls: the run is timed out near its 2 s bound, its process group is sent TERM and then KILL (read off the test thread's os.killpg calls with the group each one names: both must name one group, which with no process of the run left is the run's, so TERM before KILL to the run's group stays pinned: a KILL-only or a TERM-only _end_group turns it red, and so does one that sends the TERM to another group), no process of the run is left, and decide calls the run undecided. _end_group's docstring, the POLL comment and the note above the test say the same. Tests only. The test exists only in the fork's rewrite of the module (entry 2026-09-20-bats-bare-negation-oracle, a candidate, fork PR 871); the project's tree has the older module with no BatsRoad, so this change can be offered only together with that rewrite.
