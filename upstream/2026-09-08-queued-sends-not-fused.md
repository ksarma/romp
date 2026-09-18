---
title: Queued sends are delivered one message each, never fused; sends carry a client id
status: approved
where: kernel/sdk_backend.py (inputs() hold + _untaken_taken), tests/test_queued_sends_not_fused.py (the feeder-hold cases)
added: 2026-09-08
pr:
tier: fix
offered:
closed:
---
A fix in the SDK feeder, which upstream ships in the same shape: `inputs()` forwards every queued text to the CLI as soon as it is queued and the CLI drains its whole queue into one user record, so two messages sent during one turn reach the agent as one; only the rename ping's own pre-turn feed was held. The feeder now holds the next text until a turn frame proves the CLI took the last one, and each composer send carries a client-minted id through the queue entry, echo, queued chip and landed record, so the chat reconciles and cancels by id rather than by text. The sdk_backend.py hold and the send-pending.ts client port as they are; the kernel.py plumbing needs re-slotting, since the send id rides the parked op behind the fork's user-todo slot and upstream's `_send_or_park` takes `(be, sid, text, echo)`.

2026-09-15: the stage 1 pull-in of upstream 02bc8acb4 retired the client and kernel halves of this entry (the fork's `_QueueText.send_id` and unqueue by id, the send id through `_send_or_park`, `_backend_send` and the cancel arms, `_note_send_landings` and the chat `sendIds`, and the id-matched reconcile and cancel in `send-pending.ts` and `render.ts`) in favour of upstream's qid identity (romp-on/romp#1224, #1260 and #1273; the pull-in's Q1). What remains fork-only, and what an offer carries, is the sdk_backend.py feeder hold (`inputs()` holds the next text until a turn frame proves the CLI took the last one, with `_untaken_taken`) and its cases in `tests/test_queued_sends_not_fused.py`.

2026-09-18: the kernel.py re-slotting note in the first paragraph is obsolete: the 2026-09-15 pull-in adopted the project's qid identity (the note above), so an offer carries the feeder hold and its cases alone.

2026-09-18: approved for offer by the user (batch 2 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
