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
A fix in the SDK feeder, which upstream ships in the same shape: `inputs()` forwards every queued text to the CLI as soon as it is queued and the CLI drains its whole queue into one user record, so two messages sent during one turn reach the agent as one; only the rename ping's own pre-turn feed was held. The feeder now holds the next text until a turn frame proves the CLI took the last one, and each composer send carries a client-minted id through the queue entry, echo, queued chip and landed record, so the chat reconciles and cancels by id rather than by text. The sdk_backend.py hold and the send-pending.ts client port as they are; the kernel.py plumbing needs re-slotting, since the send id rides the parked op behind the fork's user-todo slot and upstream's `_send_or_park` takes `(be, sid, text, echo)`.
