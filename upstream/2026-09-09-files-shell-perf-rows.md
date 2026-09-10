---
title: Files pane and shell rows for romp perf client: the viewer times its paint pass, the shell observes long frames
status: merged
where: ui/webview/federation.ts (perfCollectorFor installs on every page), ui/webview/file-view.ts (perfTimed: fileview:paint, fileview:reflow), ui/webview/shell-perf.ts (new dist entry, app "shell", held rows), ui/webview/perf-telemetry.ts (header), vscode-extension/esbuild.js, kernel/kernel.py (_landing loads /dist/shell-perf.js), bin/romp (comment), docs/reference.md; tests ui/webview/shell-perf.test.ts, ui/webview/perf-telemetry.test.ts, ui/webview/file-view-seam.test.ts, tests/romp-perf-client.bats, tests/test_kernel.py
added: 2026-09-09
pr: 427
tier: feature
offered: their PR #1281 (shell half); their PR #1290 (viewer half)
closed: 2026-09-10
---
A divider drag with a large reviewed note open in the Files pane blocked the main thread for about 20 s and no pane recorded a long animation frame: the Files pane had no collector (nothing is pushed to it) and Chromium reports an iframe's long frames to the top-level window, where nothing listened. The Files pane now runs the page collector and the viewer brackets its own paint pass as fileview:paint and fileview:reflow; the shell page runs the same collector under app shell with no brackets, posting the long frames it observes through its own socket. Both rows have the minute row shape, so romp perf client shows them unchanged. Rows carry numbers and code identifiers only, as before.
