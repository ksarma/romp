---
title: Perf P18: the pause and hold callers read a limits-only usage reading (`_usage_limits`), and `_usage` parses spend.json once per call
status: candidate
where: fork branch `perf4-usage-split` (PR not yet opened): `kernel/kernel.py` (`_usage_doc`, `_usage_limits`, `_spend_doc`, `_usage`; the `doc` argument of `_spend_windows` and `_spend_series`; `_account_limited`, `_retry_resume_at`, `_limit_hold`); tests `tests/test_usage_limits_split.py`, `tests/test_kernel_usage_limit.py`, `tests/test_retry_pause_autoresume.py`, `tests/test_kernel_rail_usage.py`, `tests/test_usage_per_account.py`, `tests/test_kernel_limit_queue.py`, `ui/webview/rail-spend.test.ts`
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
`_account_limited` (both edges of the limit pause), `_retry_resume_at` (the API-error card's countdown) and `_limit_hold` (the queue's account gate) read `limited` and the windows' resetsAt, which derive from usage.json, the acct stamp and the clock; they went through `_usage()`, which parsed spend.json twice per call (once in `_spend_windows`, once in `_spend_series`; 200 KB, about 6 ms) to attach spend figures they never read, and on a host in the spend arm the pause paid that once per pusher cycle for a `limited` key the arm does not produce. `_usage_limits()` is the rate-window half on its own and the three callers read it; `_usage()` builds on it and parses the ledger once, handing the document to both spend readers through an optional `doc` argument (None keeps each reader's own read, so the analytics build and every standalone caller are unchanged). No memo: every call reads the files as they are. Measured on a 211 KB ledger in the spend arm: `_auto_pause_on_limit` 6.11 ms to 0.047 ms median per call with zero ledger parses; `_usage` 6.22 ms to 4.07 ms with one parse instead of two. The exactness and value refuters of the round-4 design pass prescribed this form over a parsed-document memo.
