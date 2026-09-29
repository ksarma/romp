---
title: board-def.test.ts and test_card_boards.py: the needs-you count pins accept either spelling of the pair
status: candidate
where: ui/webview/board-def.test.ts (the sort, grouping and notification-set test, which reads the kernel's feed table: the either-spelling needs-you pin); tests/test_card_boards.py (BellAndBadgeReadTheBoard: the _needs_you_count either-spelling pin and the _feed_notifications_diff needs_you literal pin); upstream/2026-09-20-board-def-needs-you-pin-widened.md (this entry)
added: 2026-09-20
pr:
tier: docs
offered:
closed:
---
Upstream pins kernel.py's needs-you count by the byte string of the project's spelling, the category read (the column as the fallback for an older card) compared with == against _board_needs_you(a.get("board")) inline, in ui/webview/board-def.test.ts at line 64 and tests/test_card_boards.py at line 156, and test_card_boards.py at line 170 asserts that no col == "needs_input" literal survives in _feed_notifications_diff (all three from PR 1837; the line numbers are upstream's at the fold's pin 9290cd007, where each resolves, not this fork's, whose pins the where: line locates by test), so a kernel that spells the same test another way, or keeps that literal for another purpose, reads red. This fork's user-todo count binds the helper to _ny first and spells the skip with !=, and its todo-floor latch in the diff keeps the literal, so the fork carries the two count pins widened to accept either spelling of the same property (the pair matched with the closing paren of the a.get expressions kept, so no unrelated per-sid check satisfies it) and the literal pin (upstream's line 170) re-aimed at the exact line 1837 replaced, needs_you = col == "needs_input"; the kernel's != stays. The offer, the widened and re-aimed pins and nothing else, waits on the offers pipeline.
