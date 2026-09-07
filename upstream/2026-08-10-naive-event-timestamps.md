---
title: Kernel-built event timestamps are naive box-local — every rail stamp renders at the KERNEL's wall time on any viewer in a different timezone
status: merged
where: `tzstamp` branch PR
added: 2026-08-10
pr:
tier:
offered: their PR #331
closed:
---
Upstream ships the identical `iso()`: `datetime.fromtimestamp(t).strftime(...)` with no offset suffix, shipped in chat-event payloads and recovered client-side with `Date.parse`, which reads an offset-less string in the BROWSER's timezone. Net effect: the rail shows the kernel box's wall-clock digits on every viewer — invisible while box and viewer share a timezone, wrong by the full UTC offset the moment they don't (found reading a UTC devbox's dashboard from a Mac, 2026-08-10). The CLI's own transcript records were never affected (they carry '…Z' and both ends honor it); only kernel-BUILT events (orphan replies, retry notes, effort notes, clear boundaries, atom stamps) took the naive path. One-line fix: `fromtimestamp(t, timezone.utc)` + a 'Z' suffix — the same wire form the transcript already wears. Test round-trips under non-UTC process timezones. Pure fix, no fork-specific content.

Status detail (migrated from the table): **MERGED — upstream PR #331**
