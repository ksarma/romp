---
title: The todo Reply sheet holds three rows with the phone keyboard up; the long detail scrolls within a cap
status: candidate
where: ui/webview/styles.css (#ut-reply-prompt .ut-reply-input, #ut-reply-prompt .ut-detail.open, #ut-reply-prompt.kb-tight), ui/webview/waiting.ts showReply, ui/webview/render.ts showUserTodoReply
added: 2026-09-19
pr:
tier: fix
offered:
closed:
---
On a phone with the keyboard up a todo's long detail filled the Reply sheet and the answer box was one squeezed line above Cancel and Send (2026-09-19, screenshot). The sheet is a column flex box capped at the window with overflow hidden; a wrapped text block's automatic minimum refuses to shrink and a textarea's resolves to zero, so the box took the whole deficit and the cap clipped. Three rules scoped to the dialog (the answer box a fixed item with a three-row floor; the detail the item that gives way, a scroll container capped and scrolling within itself, min-height 0 beside it as belt and braces; the short-window frame on the overlay's own selector) and, in both twin builders, the picker's kb-tight fold on the window's own resize plus a grow handler on the composer's growComposer pattern. Fake-DOM legs execute the fold and the grow out of each builder's source; rule pins; browser legs in Chromium, Firefox and WebKit at 390x508 and 390x420 against the served /waiting page and the chat's sheet.
