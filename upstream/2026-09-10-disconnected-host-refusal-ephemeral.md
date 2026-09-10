---
title: Auto-reload: the plain send's refusal on a disconnected host is marked ephemeral, so the page that follows a restart's reload does not replay it
status: merged
where: ui/webview/render.ts (sendComposer's deliver, the hostIsDown branch; the census above ephemeralWarnToast), ui/webview/reload-notices.test.ts
added: 2026-09-10
pr:
tier: fix
offered: their PR #1270
closed: 2026-09-10
---
Follow-up to their #1227 and #1246, whose bodies left this refusal unmarked; the argument is ours (the fresh page's disconnected set is empty at replay time, the redial is not re-posted, the draft carries the message). Filed directly from the upstream base.
