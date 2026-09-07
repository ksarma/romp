---
title: Perf B1: `_rewound_away` and `reconcile_rewound_goals` route through `_chain_membership`, a per-session memo of the transcript's chain graph keyed on every input the graph reads (transcript paths and their stat identity, the states log, the resume-fork lineage closure, the pending cut), and `_select_eclipsed_chains` builds its children map and text witness over the eclipse set only
status: candidate
where: fork PR #217 (`perf-b1`, merged 2026-09-06): `kernel/judge.py` (`_chain_membership`, `_CHAIN_MEMO`, `_rewound_away`, `reconcile_rewound_goals`), `kernel/event_model.py` (`_select_eclipsed_chains`), `kernel/kernel.py`, `bin/romp`, `docs/reference.md` (`judge.chain_memo` hits, misses, populates, bypasses); tests `tests/test_judge_rewind_cleanup.py::ChainMemo` (15), `tests/test_event_model_golden.py::EclipsedChainSelection`, and `jd._CHAIN_MEMO.clear()` beside every `_PARSE_CACHE.clear()` in 32 test files
added: 2026-09-07
pr: 217
tier: fix
offered:
closed:
---
Upstream has the same guard: before minting or retiring a goal the planner asks whether a uuid provably sits on a rewound-away branch right now (the writer whose evidence predates the diary stands down), and each call rebuilds the transcript's chain graph from disk, twice when a rollback is pending. In the 2026-09-06 profile that was 11.5% of the kernel's interpreter time, the largest single item. The key is computed before the build, never after; a build that raised or a key that could not be taken is never memoized; least-recently-used eviction at 256 entries; cleared on state rebind. Same inputs, same verdict. The narrowed eclipse selection's verdict identity is pinned against the whole-graph result on four sibling-fork fixtures. Measured on a synthetic 6.3 MB transcript with an eclipsed fork and a rewound branch: `_rewound_away` 409 ms cold, 148 ms on a memo miss with records cached, 0.026 ms on a hit; the narrowing alone took `chain_membership` from 186 to 112 ms.

Depends on `romp-perf` (fork #199) for the counters only. The three tests the adversarial review asked for (the states-file stat alone invalidating in the first-hop resume-fork geometry, the key taken before the build reads, a vanished from-file invalidating through the closure) were each shown red under the matching mutation. The 32-file `_CHAIN_MEMO.clear()` sweep is mechanical; regenerate it against upstream's test tree rather than cherry-pick it.
