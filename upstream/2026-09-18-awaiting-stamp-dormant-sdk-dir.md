---
title: Tests: two in-process kernel cases create the SDK registry directory their premise assumes (the awaiting-stamp dormant case, the opening chip live merge)
status: offered
where: `tests/test_kernel_awaiting_stamp.py` `AwaitingWake.test_dormant_session_is_not_woken_but_converts_to_the_dead_wait_block`: FIXED on the fork since 7fa1814da (2026-09-16, pull-in fixer round 4), lines 667 to 672, a comment and `km.jd.SDKDIR.mkdir(parents=True, exist_ok=True)` beside the names-entry write. `tests/test_kernel_opening_chip.py` `OpeningChipDecidingEvent.setUp`: FIXED on the fork by branch opening-chip-sdkdir (2026-09-18), SDKDIR rebound to the private root and created for both judge module objects. The project has neither; only the offer is outstanding.
added: 2026-09-18
pr:
tier: docs
offered: their PR #1888
closed:
---
Each case writes a names entry for its synthetic sid and never creates `jd.SDKDIR`, and `_sdk_records_blind` reads a missing registry directory beside a names entry as blindness (the 2026-09-11 tmux-removal rule): the dormant case's `_dead_wait_corroborated` stands down (stderr: the SDK registry directory cannot be read) and never converts, and the live-merge case's `Sessions.live()` serves its previous rows (stderr: the registry directory is missing or cannot be read) and the backend's row is None. Each passes only when an earlier test in the same pytest process created `sdk/` at the import-bound state root: deterministic red alone, scheduling luck under xdist (each test is distributed on its own). Diagnosed 2026-09-18 by instrumenting the registry stat through a pytest plugin; pre-creating the directory makes both pass. The kernel's boot pass creates `sdk/`, so a running kernel is never affected; the fix is the tests'. The class was measured by an executed census the same day: 287 tests reach the two functions in a full run, 284 pass alone, and these two are the whole class (a separate same-module memo dependence in tests/test_kernel_pusher_snapshot.py is not part of it).

2026-09-19: offered as their PR #1888 at 08:43Z (docs tier, its own branch on the project's tip ba9321388, not stacked; the re-derived change creates the registry directory in both fixtures and adds a fixture self-check, +41/-1 over the two test modules).
