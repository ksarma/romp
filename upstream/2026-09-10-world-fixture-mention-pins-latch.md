---
title: Tests: the chat signature's _World fixture resets the mention-pins latch per world, so a torn-down world's state root is never recreated
status: offered
where: tests/test_chat_build_sig_inputs.py (_World and RecordedDependencies setUp/tearDown, the sidecar test, a new Differential case)
added: 2026-09-10
pr:
tier: docs
offered: their PR #1303
closed:
---
From the maintainer's post-merge record on their #1296 (item 1): each test world latches its own mention-pins root, so a torn-down world's state directory is never recreated; the RecordedDependencies fixture mirrors it.
