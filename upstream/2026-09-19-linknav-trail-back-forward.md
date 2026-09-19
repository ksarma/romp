---
title: The file viewer keeps a trail of the files reached through its links, with Back and Forward, and an Open the picture control on every figure
status: candidate
where: ui/webview/file-trail.ts (trailRoot, trailPush, trailBack, trailForward, trailSetView, trailEnd, navTitle, navChord, liveTrail); ui/webview/file-view.ts (openFromViewer, moveTrail, the bar's fileview-nav group, onNavKey; closeFileView and openUrlView end the trail; ensureFigureControl, figureTarget, armFigureControls and the body's figure click listener); ui/webview/icons.ts (ICON_BACK, ICON_FORWARD, ICON_EXPAND); ui/webview/anchor-map.ts and ui/webview/reader-place.ts (CONTROL_CLASSES); ui/webview/styles.css and ui/webview/feed.css (.fileview-md .fv-figopen)
added: 2026-09-19
pr:
tier: feature
offered:
closed:
---
A link followed inside a shown file replaces the card; before this there was no way back but the Files pane's Recent list. The viewer now keeps a trail of the files reached through its own links (a module-level state with pure functions, file-trail.ts) and shows Back and Forward as two glyph buttons at the left of its bar, with Alt+Left and Alt+Right (Cmd+[ and Cmd+] on a Mac) as chords while no text field holds the keyboard. Back re-opens the previous file with no target, so the remembered place re-seats it, in the view it was left in, without touching the saved preference. An open from outside the viewer starts the trail over; closing the viewer ends it. Every picture a rendered file embeds wears an "Open the picture" glyph button after it (a sibling, never a wrapper), revealed by the pointer or a keyboard focus, that opens the picture in the viewer through the same trail push, so Back returns to the file at the figure's place; a plain click on the picture does the same while the Comments panel is closed, a Cmd/Ctrl-click opens the /file URL in a tab, a remote picture opens in a tab, and a gated placeholder gets its control once loaded. Browser history is not integrated (recorded as a follow-on with the trade-off). No kernel change, no new route. Records in plans/markdown-viewer.md, Follow-on: Link navigation.
