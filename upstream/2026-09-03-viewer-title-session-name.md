---
title: The web file viewer's title bar names the session a file was opened from — an identity-coloured chip (the waiting pane's .wt-sess idiom), "host:" quiet for a remote session; the viewer carried the sid for federation routing but never showed whose file was up
status: candidate
where: fork commit `dfaf23e8` (ui/webview/file-view.ts resolver export + chip; resolvers registered beside initFileView in render.ts and feed.ts; both sheets + fileview-parity.test.ts; pins and an executed ladder replica in ui/webview/file-view.test.ts)
added: 2026-09-03
pr:
tier:
offered:
closed:
---
UI-only, no kernel change. Upstream ships the same shared viewer with the same sid-in/no-label-out, and its shell-relay and Reload openers know only the sid too, so the resolve-from-sid shape carries over unchanged. Leaves the file browser's own bar unlabeled (optional follow-up on the same resolver).

Status detail (migrated from the table): candidate
