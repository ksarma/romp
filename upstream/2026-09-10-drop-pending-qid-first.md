---
title: Chat: a pending bubble's ✕ drops the entry that owns its id, never the first same-text entry pressed in the same millisecond (dropPending resolves the id first); _wire_qid uses fullmatch; the _client_qid refusal branch has a test; read-side.md's tmux sentence corrected
status: offered
where: ui/webview/send-pending.ts, ui/webview/send-pending.test.ts, kernel/kernel.py (_wire_qid, _CLIENT_QID_RE comment), tests/test_queued_copy_identity.py, docs/read-side.md
added: 2026-09-10
pr:
tier: fix
offered: their PR #1260
closed:
---
The follow-up the post-merge record on their #1224 (our press-qid offer) filed, confirmed by three verifiers: two same-text sends in one millisecond dropped the wrong client entry while the kernel cancelled the right copy. The ✎ edit path is left to the edit-by-id follow-up. Filed directly from the upstream base.
