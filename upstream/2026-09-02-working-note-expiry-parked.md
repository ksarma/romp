---
title: Working-note expiry keeps the note of a session parked on the user: `_clear_done_working_notes` keys on a new `_open_top_goal` (rolled-up status `working` OR `blocked`) instead of `_working_top_goal`, so only a session whose top goals are all done or cleared has its `set_working` claim lifted
status: merged
where: branch `notekeep`: `kernel/kernel.py` (`_open_top_goal`, `_clear_done_working_notes`), `tests/test_kernel.py`
added: 2026-09-02
pr:
tier:
offered: their PR #893
closed: 2026-09-03
---
MERGED as-is (head is an ancestor). The fold flag above (fork main still carries the two-helper shape) stands. Branch retired. OFFERED 2026-09-02 (branch `notekeep-offer` — `origin/notekeep` is the fork’s own merged branch — `bdfa6136` off tip `31d8731b`): review caught a FALSE call-graph claim (Auto Nudge dropped its `_working_top_goal` call in c48dd598; the expiry was the sole caller), so the offer renames/widens the helper IN PLACE to `_open_top_goal` — no second helper, no dead code; the expiry test now drives the real predicate and asserts the lift on completion. ⚠ FOLD FLAG: fork main (af6d5676) carries the OLD two-helper shape — take upstream’s rename-in-place at the next fold. Scaffold CI green (since-closed fork #166). Upstream ships the same expiry and the same postal contract ("a peer with no note holds nothing"), so the same defect: a blocked-on-you session is idle without being done, its worktree/branch/files are still its own, and lifting its note told peers the surface was free (a 2026-09-02 census across this box's sessions found parked sessions whose claims had vanished from `list_agents` while they still held them). Reverses the first cut's deliberate "blocked-on-you also lifts" choice; the reason is recorded in the docstring. Two lines of code plus two tests; ports as-is.

Status detail (migrated from the table): ✅ **merged** — their PR #893, merged as-is 2026-09-03 — ✅ came home in upfold0905 (2026-09-05)
