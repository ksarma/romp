---
title: The /perf reference names the feed memo's failed and failing counters
status: candidate
where: docs/reference.md, the /perf builds.feed.memo paragraph (one sentence after the miss_by clause); tests/test_perf_stats.py, the memo block pin reads the paragraph
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
GET /perf builds.feed.memo gained failed (per-session card builds that raised, cumulative since boot) and failing (sessions whose last build raised, a standing count) with the card-build containment, and the paragraph in docs/reference.md that lists the memo's counters still named only the eight older ones; upstream shares the gap, since its PR 1812 changed no docs. The fork carries the fix now: one sentence in that paragraph describing both counters, what a failing session's board shows and how the fault is reported, and a pin in tests/test_perf_stats.py that the paragraph names every counter the block serves. The offer waits on the user's word; the ledger is the queue.
