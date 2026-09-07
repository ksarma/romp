---
title: The dashboard as an installable home-screen app + Web Push for the bell events (manifest/icons/Apple metas, iOS-standalone safe-area, `/sw.js` + `/push/*` + VAPID on stdlib+`cryptography`, tap-to-open aimed by wid, `setAppBadge` needs-you count)
status: landed
where: PRs #9, #15, #20, #21; `plans/ios-app.md`
added: 2026-08-08
pr:
tier:
offered:
closed:
---
All kernel-side code upstream ships too; live-verified end to end on an iPhone 2026-08-08 (install, lock-screen push, tap lands on the firing session, badge). Self-contained: no new hard dependency (`cryptography` is a soft dep behind a loud 500) and no bundle changes. Includes the raw-run test-state hardening (#20) and the SW `skipWaiting` lesson (#21). LANDED upstream 2026-08-08 as `b8b127e3` (the squashed offer), and they built on it (Android cookie persistence `7cfd44f6`, one-device subscription relay `fb1c8972`) — all back on the fork via the v0.6.0 merge (PR #35).

Status detail (migrated from the table): landed
