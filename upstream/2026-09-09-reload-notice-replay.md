---
title: Auto-reload: the notice raised as the last pending ship retires is shown again by the page that follows the reload
status: offered
where: upstream branch reload-notices-offer, re-derived from fork PR #398 (b1ebc498, c3130d8f) and its siblings: new `ui/webview/reload-notices.ts` (liveNotices, keepReloadNotices, takeReloadNotices, sessionStorage key romp:reloadNotices), `ui/webview/render.ts` (warnToast returns its element, the ephemeral mark on the cannot-send-yet toast, persistNoticesForReload as the reload hook, the load-time replay); tests `ui/webview/reload-notices.test.ts`, `reload-restore.test.ts`, `tests/test_ship_reship.py` (a served Chromium leg against a relaunched kernel)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1217
closed:
---
Audit row 4, PR A only: the nack and dismiss toasts raised as the last pending ship retires were appended one macrotask before the owed reload fired and were lost; they now ride sessionStorage and replay once on the page after the reload, with the state-reporting toast marked ephemeral. PR B (the 60 s reload deadline backstop) stays unfiled; the reload-deadline-backstop entry remains at waiting.
