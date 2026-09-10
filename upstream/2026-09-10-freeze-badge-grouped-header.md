---
title: Feed: the hover-freeze tells the hovered session header apart by column, not by session alone (a grouped header's data-fcol stamp; the freeze key includes the column)
status: merged
where: ui/webview/feed.ts (sessFreezeKey, the hovered compare, the data-fsid/data-fcol header stamps), ui/webview/feed-render-incremental.test.ts, ui/webview/feed-freeze.test.ts
added: 2026-09-10
pr:
tier: fix
offered: their PR #1232
closed: 2026-09-10
---
Defect 4 of the maintainer-side records on Henry's cleared-ledger PRs: a session header grouped under two columns froze the wrong one on hover because the freeze key named the session alone. Upstream-native; filed directly from the upstream base. Its full npm run carried main's two failures of 23:09Z to 23:50Z (fixed by their #1226), named in the body.
