---
title: `_send_or_park` returns three outcomes — `"parked"`, else the backend send's own result (truthy sent; a tmux send returns its nonce), falsy refused — and `_tmux_send`'s inner `paste()` returns False on every abort and True after the Enter (`go()` assigns `delivered = paste()`, fires `on_refused` / `on_delivered` in a `finally`, and returns None). Upstream's `_send_or_park` is True/False (`ae98b1dc`, POST /send's `queued = bool(...)`)
status: candidate
where: `kernel/kernel.py` (`_send_or_park`, `_tmux_send`; POST /send computes `queued = (_send_or_park(...) == "parked")`); fork `ac8340da`; pinned by `tests/test_kernel_parked_ops_liveness.py` (`== "parked"` / `!= "parked"`) and `tests/test_user_todos.py` (the delivery stamp keyed on the outcome; `_tmux_send`'s `on_refused` / `on_delivered`)
added: 2026-09-05
pr:
tier: major-feature
offered: their PR #994 (commit b40df67a, slice 1)
closed: 2026-09-20
---
The user-todo delivery stamp (`on_refused` / `on_delivered`, the slice-1 row) keys on sent-vs-refused-vs-parked, which upstream's bool cannot express. Kept at upfold0905 (2026-09-05); upstream's one consumer repointed to `== "parked"` and its one test adjusted (`assertFalse` → `assertNotEqual(..., "parked")`). Every fold will touch this until one side converges; an offer of the three-outcome contract would ride the user-todos slices.

Status detail (migrated from the table): divergence

2026-09-09: rides inside the user-todos RFC https://github.com/romp-on/romp/pull/994 as its first slice (commit b40df67a), not a PR of its own: a standalone PR would be inert upstream and collide with that PR's rebases. The port rewrites lczh's None arm (145139a6, their #1033) to the backend's False, with _pr_watch_deliver testing `is not False` and test_pr_watch.py asserting False.

**Their PR #994 closed unmerged on 2026-09-20; back to `candidate` and NOT yet decided.** #994 was
closed as a direction call on the user-todos feature. This entry is tier `major-feature` and is NOT one
of the stranded fixes the user authorised offering separately on 2026-09-21, so do not cut an offer from
it on that word. It is recorded as a candidate rather than `keep-private` because nobody has tested
whether the project would take the piece with the second store removed, and there is precedent for a
partial take. That question waits on the user's own conversation with the maintainer about the
direction; leave the status alone until he reports it.
