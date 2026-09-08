---
title: Perf B4: `save_goals`' no-op check memoizes the disk side by file identity (inode, mtime_ns, size, by fstat on the descriptor that is read) to a hash of the store's canonical content and hashes the in-memory store once per publish; the compare-and-swap that guards concurrent writers reads the file's revision fresh on every real publish and never consults the memo
status: merged
where: fork PR #228 (`perf-b4`, merged 2026-09-06): `kernel/judge.py` (`save_goals`; `goal_io_stats` gains `disk_hits`, `disk_misses`, `disk_seeds`), `kernel/kernel.py` (the compaction sweep evicts absent paths; `_rebind_state` clears), `bin/romp`, `docs/reference.md`; tests `tests/test_judge_store_noop_publish.py::DiskMemo` (26), `tests/test_kernel_goal_compaction.py`, `tests/test_perf_stats.py`, `tests/romp-perf.bats`
added: 2026-09-07
pr: 228
tier: fix
offered: their PR #1059
closed: 2026-09-08
---
Upstream's `save_goals` asks on every call whether the store on disk already holds the bytes it is about to write, by re-reading and parsing the disk store and serializing the in-memory one; judge threads save on every pass, mostly with nothing new, so the check was about 3% of the kernel's interpreter time in the 2026-09-06 profile. A byte-identical republish is still a no-op and a changed file is never mistaken for the memoized one. Because the CAS stays exact, an identity collision (a recycled inode within one mtime tick) can only skip a publish whose content the file already held, never let a writer pass the CAS on a stale revision; the first review reproduced that hazard in a memo-served form of the CAS, which is why it stays exact. After a publish the memo is seeded from the temp file's identity before the rename, only when no rebase ran; an absent or unreadable store drops its entry. Measured on a 1 MB store: no-op save 20.7 to 8.6 ms; real write 42.0 to 22.7 ms (the exact CAS read costs one parse per real publish, about 5 ms at this size); first no-op after a publish 28.8 to 8.1 ms.

Depends on `romp-perf` (fork #199) for the three counters only. The test class covers the K/B/C identity-collision interleaving in which a later writer must still rebase and keep the intervening event, a foreign atomic replace, same-size in-place and same-tick rewrites told apart by inode or size, and a replace racing the read.

OFFERED 2026-09-08: offered upstream inside bundle PR #1059 (Identity memos on the judge's goal-store loads, saves and scans, and a shared read-only cache for the pusher; label fix; branch store-memos-offer; head b168928b; a draft while the branch is rebased onto the moved upstream tip) with `judge-failure-scan-memo`, `chain-membership-memo`, `goals-pass-snapshot-memo`, `propagate-load-once`, `shared-goal-store-cache` and the journal half of `awaiting-lift-identity-gate`'s `_unread` mark. Reworked at the rebase onto upstream's #1019: both descriptor readers raise on a read fault or on bytes that are not a store object (`_disk_parse`) and drop the entry.

MERGED 2026-09-08: merged upstream as their PR #1059 (merge 9c9a926a, 2026-09-08T18:41:39Z) after the maintainer's own review commit; the bundle's counters land later through GET /perf's memos key, which the review commit added.
