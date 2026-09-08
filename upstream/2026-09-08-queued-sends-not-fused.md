---
title: Queued sends are delivered one message each, never fused; sends carry a client id
status: candidate
where: kernel/sdk_backend.py (inputs() hold + _untaken_taken, _QueueText.send_id, unqueue by id), kernel/kernel.py (send id through _send_or_park/_backend_send/cancel arms, _note_send_landings, chat sendIds), ui/webview/send-pending.ts + render.ts (id-matched reconcile and ✕), docs/guide.md, tests/test_queued_sends_not_fused.py
added: 2026-09-08
pr:
tier: fix
offered:
closed:
---
