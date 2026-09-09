---
title: Reload core: a pane hold (upload, held-send, the shim's sends) older than 60 s releases the reload as a backstop, with a console line naming the hold and a note in the replayed toasts; gesture words have no deadline
status: candidate
where: kernel/kernel.py _RELOAD_CORE_JS (clock, unclock, what, released, the GESTURE set, busy()'s gesture-first walk); ui/webview/reload-hold.ts releasedNotices; ui/webview/render.ts persistNoticesForReload; tests/test_dashboard_auto_reload.py UploadHoldExecuted; ui/webview/reload-hold.test.ts
added: 2026-09-09
pr:
tier: feature
offered:
closed:
---
Upstream's pane hold (#1104, #1123) has one exit, the pane's own ending event, so a wedged upload that never acks or nacks pins the page on an old build indefinitely; the fork adds a 60 s backstop. The clock starts when the pane's word first blocks an owed reload and resets when the word ends or changes (a hold released and re-raised gets its own 60 s); at 60 s the reload fires anyway, one console line names the word and the seconds, and the fresh page's replayed toasts carry a note saying which hold had not finished. The five gesture words (pointer, pan, drag, selection, typing) are never clocked, so a reload still never lands mid-gesture, and busy() reports a gesture anywhere ahead of a pane word. Landed in the 2026-09-09 fold (slice 1) on the reviewer's ruling; upstream at bcc7e215 has none of it.
