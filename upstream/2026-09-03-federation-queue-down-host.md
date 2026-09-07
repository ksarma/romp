---
title: Federation queue edges: a setting queued for a DOWN host is silent at queue time (no client-diag breadcrumb); `flushPending` clears the map only after the whole loop, so a send that throws mid-flush replays delivered entries on the next open; N kernels refusing one stale flush yield N identical toasts naming no host
status: offered
where: maintainer’s follow-ups on their #879 (2026-09-03); not yet built
added: 2026-09-03
pr:
tier: fix
offered: their PR #945
closed:
---
Three small hardening items on the merged queue-aware sender: queue-time breadcrumb, per-entry clear during flush, host-attributed dedup of stale toasts.

Status detail (migrated from the table): **offered** — their PR #945 (2026-09-06), label `fix`; combined with the other #879 follow-up row into one PR
