---
title: The thread-wake notice rewrite keeps dict-shaped queue entries (a persisted user-todo answer) instead of erasing them
status: candidate
where: fork PR #323 (`queuedicts`, merged 2026-09-07): kernel/sdk_backend.py SdkBackend._ensure thread-wake notice prepend; tests/test_sdk_boot_stagger.py ThreadWakeHearsItsDeadLife and tests/test_sdk_lifecycle_hardening.py TodoIdsRideTheQueue
added: 2026-09-07
pr: 323
tier: fix
offered: their PR #994
closed: 2026-09-20
---
One strings-only filter survived the 2026-08-22 dict-aware queue sweep: the thread-wake notice rewrite dropped every non-string entry, so a persisted user-todo answer was lost when a dormant thread woke with a killed question or dead tasks. The fix decodes each entry with _queue_text for the junk and dedup tests and writes it back in its persisted shape. Upstream gets the same fix inside the usertodos-offer port (its commit a62502d9); status moves to landed when that PR merges.

2026-09-18: the sha a62502d9 above is a commit of the usertodos-offer branch from before https://github.com/romp-on/romp/pull/994 was rebuilt on 2026-09-10 (force-pushed away; its rewritten counterpart, same message, is a033e0586), still reachable on GitHub but not among the PR's 44 commits. The PR's current head cb5b6c2a9 and upstream/main both keep the strings-only filter in the thread-wake notice rewrite and define no _queue_text, because the port changed shape: reg['queue'] stays bare strings and a todo answer's id rides the reg['queueMeta'] sidecar (the project's own T252c design, https://github.com/romp-on/romp/pull/1076, merged 2026-09-08), block-aligned by queue_meta_from_reg across a notice prepend and re-attached by the seed. The case this entry fixes is pinned by the port's own test, TodoIdsRideTheQueue.test_thread_wake_notice_keeps_the_id_on_its_entry (a killed-question wake puts the notice first and the seed still reads the id on the answer). Nothing separate is left to offer: the entry rides that PR as its user-todos siblings do. The fork PR was #323.

**Their PR #994 closed unmerged on 2026-09-20; back to `candidate` because this one is separately
offerable.** #994 was closed as a direction call on the user-todos feature, not on this fix. This entry
is tier `fix` and its subject stands on its own: a thread-wake notice rewrite that erases dict-shaped
queue entries loses a persisted answer whoever asked for it. The user authorised offering the stranded
fixes as their own pull request (2026-09-21), so this is a candidate for that offer rather than dead
work. Whoever cuts it should re-derive the claim against the project's main first, since their
replacement design merged after this entry was written.
