---
title: Chat: a late stamp reads a user event that names the send (its uuid, qid or qids) as this send's whatever its stamp, so a client clock ahead of the kernel no longer doubles the bubble or leaves it unretired
status: merged
where: ui/webview/send-pending.ts (namesSend, stampBase), ui/webview/send-pending.test.ts (section 16)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1273
closed: 2026-09-10
---
Fork-derived: the fork carries the rule on its own sendId model; re-derived onto the project's qid shape after their #1224 and #1260. Filed directly from the upstream base.
