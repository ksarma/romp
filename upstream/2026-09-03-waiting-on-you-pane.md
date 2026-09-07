---
title: The "Waiting on you" pane: every session's open user todos across attached machines in one dashboard column, oldest first, with Reply / Dismiss / open-session per row: build_feed ships `userTodoRows` + `userTodosOn` beside the count map (same read, same gates, byte-stable), federation prefixes + merges the rows, app=`waiting` rides the feed frame with the feed pane's caps, `ui/webview/waiting.ts` reuses `userTodoAnswer` / `userTodoDismiss` unchanged and never reads `asks`
status: waiting
where: fork branch `waitingpane` (stacked on the todoswitch / todofix PRs #183 / #184)
added: 2026-09-03
pr:
tier:
offered:
closed:
---
BROWSER SHELL ONLY: the VS Code extension's panel mirror (the `KernelPipe` app union, `openPaneByKey` / `updateStrips`, a panel + HTML builder, `page-skeleton.ts`, `view-routing.ts`, the `package.json` command, `romp-menu.ts`) is a deliberate FOLLOW-UP, not in this branch (the esbuild entry ships, so the extension builds unchanged). Pure feature, no fork-specific content.

Status detail (migrated from the table): **waiting**: gated on the user-todos slices above (and the switch + log PRs) being offered first; the pane has no meaning upstream without them
