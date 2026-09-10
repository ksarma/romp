---
title: Pane shim: declare a redial only once the kernel's caps frame has answered the bundle's ready
status: merged
where: docs/read-side.md kernel/kernel.py tests/test_chat_skeleton_reconnect.py tests/test_pane_shim_return.py ui/webview/skeleton-tabs.ts
added: 2026-09-10
pr:
tier: fix
offered: their PR #1352
closed: 2026-09-10
---
From the maintainer's review record on their #1325: commit 1 is the shim-ready-while-connecting-pin (tests only); commit 2 latches readyAcked on the kernel's caps frame as a fourth conjunct of the dial term, so a ready the kernel never answered dials as a fresh page for the page's life; docs and the exact-string pins follow.
