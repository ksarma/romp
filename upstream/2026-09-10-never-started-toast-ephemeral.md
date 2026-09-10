---
title: Auto-reload: the never-started send refusal on a failed provisional tab and the queued edit's send refusal (host down or provisional tab) are raised through ephemeralWarnToast, so neither comes back on the page that follows a reload
status: offered
where: ui/webview/render.ts (sendComposer's deliver, the queued-edit refusal, the census comment), ui/webview/reload-notices.test.ts (three lifted cases, pin 10), ui/webview/provisional.test.ts (one pin)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1246
closed:
---
Follow-up the delta review of their #1227 (our reload state toasts offer) filed: two more state refusals in sendComposer still rode the reload. Filed directly from the upstream base.
