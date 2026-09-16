---
title: The feed memo's forget walks the subagent-walk memo while a build inserts into it
status: candidate
where: kernel/kernel.py _feed_memo_forget
added: 2026-09-16
pr:
tier: fix
offered:
closed:
---
_feed_memo_forget drops a departed session's entry from _feed_memo under _feed_memo_lock, then drops its subagent-walk memo (_SUBAGENT_DIRS_MEMO) by walking that dict outside the lock, and the walk memo's writer, _subagent_dirs_ident, inserts under no lock from whichever thread is building (the pusher's build under _FEED_BUILD_LOCK and a request thread's own build, GET /feed.json or the clearAll op, run at once). A departed session's sweep meeting a peer build's insert raised RuntimeError, dictionary changed size during iteration, out of the build (reproduced on 3.12 and 3.14t by the fork's pull-in review of 2026-09-16). The fork snapshots the keys with list(_SUBAGENT_DIRS_MEMO) before the filter and pins it in tests/test_free_threaded_caches.py (FeedMemoForgetSweep: a stale key's hash inserts a fresh entry once during the forget; no raise, the departed entries gone, the live one and the insert standing). Upstream kernel/kernel.py at 14f1548a9 carries the same walk.
