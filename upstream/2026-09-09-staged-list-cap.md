---
title: Chat page: staged comments go as one message, and the strip shows a few and scrolls beyond
status: offered
where: ui/webview/staged-messages.ts (quoteReplyBody moved in, stagedBatchBody, stagedPosts with isSlashCommand), ui/webview/render.ts (flushStaged routes the posts, the strip .staged-list with its per-tab kept scroll, reveal-on-stage and fold caret), ui/webview/styles.css (the .staged-list cap, overflow-x and open-label wrap, caret rules), docs/guide.md (one new sentence on the list, and the Enter sentence says as one message); tests ui/webview/staged-messages.test.ts, ui/webview/staged-list-cap.test.ts, and the pins in composer-citation, send-scroll-preserve, rewind-edit, optimistic-send, composer-send (the two open-label rule pins)
added: 2026-09-09
pr:
tier: feature
offered: their PR #1193
closed:
---
The staged run above the composer goes out as ONE message (the user 2026-09-08, who wanted staged comments to land as one message, not a series): stagedPosts walks the stage in order and folds the items into one body, each as its quote block then its comment, with the typed message last (stagedBatchBody), so one post makes one bubble and one turn. Two kinds of item go on their own, at their place in stage order: a goal follow-up (the kernel wraps one goal per message, so it keeps its own askFollowUp) and a slash command, staged or typed (the kernel fires a command only at the head of its own text; folded in, a typed command was prose and a leading one took the comments after it as its argument). The strip itself shows about four items (.staged-list max-height 209px, its own scroll, the head with the count and Send now outside it), staging reveals the new item, the kept scroll offset is per tab, and a caret folds it to the head line for the page (the same user, whose twelve staged comments filled the page below the strip and pushed the transcript out of view).
