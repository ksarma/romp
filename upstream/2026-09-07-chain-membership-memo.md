---
title: Perf B1: `_rewound_away` and `reconcile_rewound_goals` route through `_chain_membership`, a per-session memo of the transcript's chain graph keyed on every input the graph reads (transcript paths and their stat identity, the states log, the resume-fork lineage closure, the pending cut), and `_select_eclipsed_chains` builds its children map and text witness over the eclipse set only
status: merged
where: fork PR #217 (`perf-b1`, merged 2026-09-06): `kernel/judge.py` (`_chain_membership`, `_CHAIN_MEMO`, `_rewound_away`, `reconcile_rewound_goals`), `kernel/event_model.py` (`_select_eclipsed_chains`), `kernel/kernel.py`, `bin/romp`, `docs/reference.md` (`judge.chain_memo` hits, misses, populates, bypasses); tests `tests/test_judge_rewind_cleanup.py::ChainMemo` (15), `tests/test_event_model_golden.py::EclipsedChainSelection`, and `jd._CHAIN_MEMO.clear()` beside every `_PARSE_CACHE.clear()` in 32 test files
added: 2026-09-07
pr: 217
tier: fix
offered: their PR #1059
closed: 2026-09-08
---
Upstream has the same guard: before minting or retiring a goal the planner asks whether a uuid provably sits on a rewound-away branch right now (the writer whose evidence predates the diary stands down), and each call rebuilds the transcript's chain graph from disk, twice when a rollback is pending. In the 2026-09-06 profile that was 11.5% of the kernel's interpreter time, the largest single item. The key is computed before the build, never after; a build that raised or a key that could not be taken is never memoized; least-recently-used eviction at 256 entries; cleared on state rebind. Same inputs, same verdict. The narrowed eclipse selection's verdict identity is pinned against the whole-graph result on four sibling-fork fixtures. Measured on a synthetic 6.3 MB transcript with an eclipsed fork and a rewound branch: `_rewound_away` 409 ms cold, 148 ms on a memo miss with records cached, 0.026 ms on a hit; the narrowing alone took `chain_membership` from 186 to 112 ms.

Depends on `romp-perf` (fork #199) for the counters only. The three tests the adversarial review asked for (the states-file stat alone invalidating in the first-hop resume-fork geometry, the key taken before the build reads, a vanished from-file invalidating through the closure) were each shown red under the matching mutation. The 32-file `_CHAIN_MEMO.clear()` sweep is mechanical; regenerate it against upstream's test tree rather than cherry-pick it.

OFFERED 2026-09-08: offered upstream inside bundle PR #1059 (Identity memos on the judge's goal-store loads, saves and scans, and a shared read-only cache for the pusher; label fix; branch store-memos-offer; head b168928b; a draft while the branch is rebased onto the moved upstream tip) with `judge-failure-scan-memo`, `goals-pass-snapshot-memo`, `save-goals-noop-disk-memo`, `propagate-load-once`, `shared-goal-store-cache` and the journal half of `awaiting-lift-identity-gate`'s `_unread` mark.

MERGED 2026-09-08: merged upstream as their PR #1059 (merge 9c9a926a, 2026-09-08T18:41:39Z) after the maintainer's own review commit; the bundle's counters land later through GET /perf's memos key, which the review commit added.
