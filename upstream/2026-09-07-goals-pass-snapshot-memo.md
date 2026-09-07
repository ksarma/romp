---
title: Perf B5: `_begin_goals_pass` keeps the judge pass's goal-store snapshot in a memo keyed on each store file's stat identity (inode, mtime_ns, size), re-decoding only stores whose identity changed, and `_feed_goals` copies an entry before replaying a user gesture onto it (copy-on-punch)
status: candidate
where: fork PR #220 (`perf-b5`, merged 2026-09-06): `kernel/kernel.py` (`_begin_goals_pass`, `_feed_goals`, `/perf memos.goals_snap`: hit, miss, fail, evict, punch, entries, bytes), `docs/reference.md`; tests `tests/test_kernel.py::ViewBuilder` (a second pass decodes only changed stores; a punch copies and never mutates the memoized store; an undecodable store is served live and retried only when it changes; a vanished store is forgotten; one test per key component, each shown red under the matching mutation), `tests/test_perf_stats.py`
added: 2026-09-07
pr: 220
tier: fix
offered:
closed:
---
At the start of every judge pass upstream's producer thread parses every goal store on disk (72 files, up to 1.3 MB each) to give the feed a pass-consistent snapshot; passes run on every session's turn end, so on a busy board this is the producer thread's main cost (3% of interpreter time, a quarter of a second of parsing per pass). The snapshot is shared across passes, so nothing downstream may mutate a served store (audited; the punch copies). A store that does not decode is remembered under its file version, reported once, retried when the file changes, and that session is served live meanwhile. The commit records what the key rests on: mtime_ns moving between publishes (guaranteed on Linux 6.13+ because the pass's own stat marks the prior inode queried), with the same-tick equal-size blind spot on coarse-timestamp kernels that the shared read-only cache's byte compare closes. Measured on 60 synthetic stores of 0.5 to 1 MB: a steady pass with nothing changed 250 ms to 0.6 ms; one changed store 4.4 ms; five changed 33 ms; the cold first pass 213 ms against 290 to 500 ms before.

Depends on `romp-perf` (fork #199) for the `memos.goals_snap` block only. The fork's P9 shared read-only cache (`shared-goal-store-cache`, #267) leaves this memo in place for `_feed_goals`, so the two can be offered in either order.
