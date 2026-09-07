---
title: The durable bg-task scan doesn't know the Monitor tool — a monitor-held session reads idle to the lift/nudge/awaiting machinery
status: merged
where: `monscan` branch PR
added: 2026-08-10
pr:
tier:
offered: their PR #335
closed:
---
Upstream ships the identical two-shape `_scan_bg_tasks` (backgrounded Bash + async Agent): a session idle behind a Monitor watch scans as "nothing dispatched", so its awaiting stamp can lift only by the 6h backstop and every consumer of the pairing is blind to the wait. Their live SDK lifecycle path handles monitors fine (probe-verified here — same stream contract), so the gap is transcript-durability only, but that is the path the judge's settled gate and the stamp lift ride. Fix registers the Monitor launch (persistent ones excluded — a session-length subscription is furniture, not awaited work), guards the parser's missing-status→"completed" default so a wrapped monitor EVENT can never end a live watch, fails phantom launches whose ack errored, and emits the launch-recorded lifetime ceiling (`timeout_ms`) as a deadline consumers expire on — which also closes the dead-CLI staleness hole bash tasks can't close (they record no bound). Shapes corpus-derived from 44 real monitor lifecycles; tests rebuild them synthetically. Pure fix, no fork-specific content.

Status detail (migrated from the table): **MERGED — upstream PR #335**
