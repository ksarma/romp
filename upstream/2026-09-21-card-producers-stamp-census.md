---
title: The card boards test censuses the producers: every card-shaped literal stamps board and category
status: candidate
where: tests/test_card_boards.py _card_literals and the census case; kernel/kernel.py _user_todo_placeholder (fork-only)
added: 2026-09-21
pr:
tier: docs
offered:
closed:
---
Upstream's pin in tests/test_card_boards.py (from PR 1837) counted the compliant stamps, `KSRC.count('"board": "feed"') == 7`, beside a roster of seven families copied from the source, so it could not see a missing family: this fork has an eighth card producer, `_user_todo_placeholder`, whose dict carried `column` and no `board` or `category` (the only card in the kernel shipping without a board, so ui/webview/feed.ts's stated contract was false here), the pin read green with the gap in the tree and turned red on the fix (8 != 7). The fork's census, `_card_literals`, walks kernel.py's AST for every dict literal carrying both an `itemId` key and a `column` key (the producers; the snapshot entries with `column` and no `itemId`, and the app messages and log rows with `itemId` and no `column`, are not cards) and asserts that each carries `board` and `category`, failing by function and line, and that the producers' names equal the roster's keys, one literal each, so any producer is seen whether or not the roster names it, with two self-checks of the shape (the todo placeholder's stamp removed in a copy of the source names `_user_todo_placeholder`; a board stamped on a snapshot entry adds no producer) and an executed case that builds the two goal-less placeholders and reads board, category, column and itemId. Upstream's own seven producers already satisfy the census, so the offer is the test alone; the fork's eighth, `_user_todo_placeholder`, stamps `"board": "feed", "category": "needs_input"` beside its column now, which is fork-only code and no part of the offer.
