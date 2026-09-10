---
title: Comments: a create is remembered by the id its send gesture minted (createId in the frame; _create_key keys on (parent sid, createId)), so a second comment in the same words on the same passage is a second thread, not a second ack
status: merged
where: kernel/kernel.py (_create_key, _parked_key, the WS door, the reservation, the park-once check, the pusher's retry), ui/webview/comments.ts (CommentCreate, mintCreateId, newCommentCreate, commentCreateFrame), ui/webview/render.ts, tests/test_comment_create_idempotent.py, ui/webview/comments.test.ts, ui/webview/comment-remote-routing.test.ts
added: 2026-09-10
pr:
tier: fix
offered: their PR #1236
closed: 2026-09-10
---
Data-loss defect in their #1208: the create memo keyed on the words swallowed a deliberate second comment in the same words on the same passage (two acks, the second name nowhere on disk). Upstream-native; filed directly from the upstream base.
