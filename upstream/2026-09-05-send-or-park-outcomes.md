---
title: `_send_or_park` returns three outcomes — `"parked"`, else the backend send's own result (truthy sent; a tmux send returns its nonce), falsy refused — and `_tmux_send`'s inner `paste()` returns False on every abort and True after the Enter (`go()` assigns `delivered = paste()`, fires `on_refused` / `on_delivered` in a `finally`, and returns None). Upstream's `_send_or_park` is True/False (`ae98b1dc`, POST /send's `queued = bool(...)`)
status: divergence
where: `kernel/kernel.py` (`_send_or_park`, `_tmux_send`; POST /send computes `queued = (_send_or_park(...) == "parked")`); fork `ac8340da`; pinned by `tests/test_kernel_parked_ops_liveness.py` (`== "parked"` / `!= "parked"`) and `tests/test_user_todos.py` (the delivery stamp keyed on the outcome; `_tmux_send`'s `on_refused` / `on_delivered`)
added: 2026-09-05
pr:
tier:
offered:
closed:
---
The user-todo delivery stamp (`on_refused` / `on_delivered`, the slice-1 row) keys on sent-vs-refused-vs-parked, which upstream's bool cannot express. Kept at upfold0905 (2026-09-05); upstream's one consumer repointed to `== "parked"` and its one test adjusted (`assertFalse` → `assertNotEqual(..., "parked")`). Every fold will touch this until one side converges; an offer of the three-outcome contract would ride the user-todos slices.

Status detail (migrated from the table): divergence
