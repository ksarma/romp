---
title: Tests: test_comment_create_idempotent's setUp clears the three create memos (_recent_creates, _inflight_creates, _parked_creates) under _create_lock beside _thread_msgs_cache
status: merged
where: tests/test_comment_create_idempotent.py
added: 2026-09-10
pr:
tier: docs
offered: their PR #1257
closed: 2026-09-10
---
Review follow-up on their #1236 (our comment create identity offer): isolation, not a behaviour fix; the module was order-independent by chance. Filed from #1236's head (now on main).
