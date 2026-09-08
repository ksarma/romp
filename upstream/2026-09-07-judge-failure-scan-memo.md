---
title: Perf B9: `judge_failure_scan` memoizes each store's failed count on the identity of the file it was counted from (inode, mtime_ns, size, taken by fstat on the descriptor that is read), so a call stats every store and parses only the ones whose key changed
status: merged
where: fork PR #213 (`perf-b9`, merged 2026-09-06): `kernel/judge.py` (`judge_failure_scan`; `goal_io_stats` gains `scans`, `scan_hits`, `scan_parses`), `bin/romp` and `docs/reference.md` (the counters); tests `tests/test_judge.py::JudgeFailureScanMemo` (6), pins in `tests/test_perf_stats.py` and `tests/romp-perf.bats`
added: 2026-09-07
pr: 213
tier: fix
offered: their PR #1059
closed: 2026-09-08
---
Upstream ships the same scan (`judge_failure_scan` in `kernel/judge.py`, called from `kernel/kernel.py`) on every timeline build and every dashboard connect push, and every call parses every goal store again (about 13 MB on a 30-session board; 1.8% of interpreter time in the 2026-09-06 profile). The memo is rebuilt from each call's glob and swapped in with one assignment: deleted stores drop out, concurrent callers never share a mutable dict, a store that fails to parse is retried on the next call, and the give-up cause is recomputed only when a store's key changed. The commit message records why the key is sound (mtime_ns strictly increases across tmp+rename publishes on Linux 6.13+; the inode alone distinguishes one publish only) and the residual one-tick window on coarse-timestamp kernels, which is narrower than the existing one-second gate in front of the scan. Measured on 40 synthetic stores (1.13 MB): 7.8 ms per call before; 8.0 ms cold, 0.24 ms steady, 0.60 ms after one store is republished.

Depends on the kernel counters entry (`romp-perf`, fork #199) only for the three counters and their pins; the memo ports without it.

OFFERED 2026-09-08: offered upstream inside bundle PR #1059 (Identity memos on the judge's goal-store loads, saves and scans, and a shared read-only cache for the pusher; label fix; branch store-memos-offer; head b168928b; a draft while the branch is rebased onto the moved upstream tip) with `chain-membership-memo`, `goals-pass-snapshot-memo`, `save-goals-noop-disk-memo`, `propagate-load-once`, `shared-goal-store-cache` and the journal half of `awaiting-lift-identity-gate`'s `_unread` mark.

MERGED 2026-09-08: merged upstream as their PR #1059 (merge 9c9a926a, 2026-09-08T18:41:39Z) after the maintainer's own review commit; the bundle's counters land later through GET /perf's memos key, which the review commit added.
