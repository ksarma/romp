---
title: Chat page: staged comments go as one message, and the strip shows a few and scrolls beyond
status: candidate
where: ui/webview/staged-messages.ts (quoteReplyBody moved in, stagedBatchBody), ui/webview/render.ts (flushStaged folds the run and the typed message, the strip .staged-list and fold caret), ui/webview/styles.css (the .staged-list cap and caret rules), docs/guide.md (one sentence); tests ui/webview/staged-messages.test.ts, ui/webview/staged-list-cap.test.ts, and the pins in composer-citation, send-scroll-preserve, rewind-edit
added: 2026-09-09
pr:
tier: feature
offered:
closed:
---
The staged run above the composer goes out as ONE message (the user 2026-09-08, who wanted staged comments to land as one message, not a series): stagedBatchBody folds every staged item in stage order, each as its quote block then its comment, and the typed message last, into one body, so one post makes one bubble and one turn; a staged goal follow-up keeps its own askFollowUp because the kernel wraps one goal per message. The strip itself shows about four items (.staged-list max-height 209px, its own scroll, the head with the count and Send now outside it) and a caret folds it to the head line for the page (the same user, whose twelve staged comments filled the page below the strip and pushed the transcript out of view).
