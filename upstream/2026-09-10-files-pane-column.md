---
title: Files pane: the file viewer as a dashboard column of its own, off by default, with a File links open in setting
status: merged
where: The pane itself from fork PR #187 (the remainder the 2026-09-03 files-pane entry left home), the shell's pane-set broadcast and the phone tab rule from fork PR #188, the relay hold and the tab-tap rule from the review; kernel/kernel.py (_files_page, /files, _shim no_stale, _PANE_ORDER, the landing scripts), ui/webview/files.ts, files-recent.ts, file-route.ts, files-pane.css, render.ts, file-view.ts, settings.ts, gear.js, palette-main.ts, esbuild.js, docs/guide.md, ui/README.md; tests/test_files_pane.py, tests/test_pane_state_broadcast.py and the re-pinned kernel and webview tests
added: 2026-09-10
pr: 187
tier: feature
offered: their PR #1305 + their PR #1310 (browser route)
closed: 2026-09-10
---
Features plan row 32, PR 1 of 2 (the user's 2026-09-09 ruling: file it, stacked; the folder route into the pane follows as PR 2 on this branch). Off by default behind the File links open in setting; request/response viewer, no VS Code mirror; defining __rompMobileTab turns the tip's dangling call live.
