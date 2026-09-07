---
title: The thread-wake notice rewrite keeps dict-shaped queue entries (a persisted user-todo answer) instead of erasing them
status: waiting
where: fork branch queuedicts (kernel/sdk_backend.py SdkBackend._ensure thread-wake notice prepend; tests/test_sdk_backend_queue.py or the module the fix's tests live in)
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
One strings-only filter survived the 2026-08-22 dict-aware queue sweep: the thread-wake notice rewrite dropped every non-string entry, so a persisted user-todo answer was lost when a dormant thread woke with a killed question or dead tasks. The fix decodes each entry with _queue_text for the junk and dedup tests and writes it back in its persisted shape. Upstream gets the same fix inside the usertodos-offer port (its commit a62502d9); status moves to landed when that PR merges.
