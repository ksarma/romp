---
title: docs/reference.md documents the feed memo's coldLive and coldFlip counters
status: candidate
where: docs/reference.md (section Kernel performance counters, the builds bullet's memo paragraph, the per-session card memo inside build_feed: the coldLive and coldFlip sentence after the failed and failing sentence); upstream/2026-09-20-perf-cold-counters-docs.md (this entry)
added: 2026-09-20
pr:
tier: docs
offered:
closed:
---
Upstream PR 1820 added two counters to the /perf builds.feed.memo block, coldLive (the living sessions whose cache-only parse read missed, per session per build; a session no client and no judge has parsed rides it every build, so a standing count is those cold-by-design sessions, not a fault) and coldFlip (the sessions the memo held under a warm key and re-read in place through the parser instead of deriving cold, one kernel parse each, counted under parses too), and ships them undocumented in docs/reference.md, whose memo paragraph names every other key of the block. The fork's docs/reference.md carries one sentence documenting both, added in the fold that took 1820 because the fork's tests/test_perf_stats.py pin requires every key of the block to be named in that paragraph. The offer waits on the offers pipeline; docs only.
