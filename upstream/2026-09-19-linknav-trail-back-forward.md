---
title: The file viewer keeps a trail of the files reached through its links, with Back and Forward
status: candidate
where: ui/webview/file-trail.ts (trailRoot, trailPush, trailBack, trailForward, trailSetView, trailEnd, navTitle, navChord, liveTrail); ui/webview/file-view.ts (openFromViewer, moveTrail, the bar's fileview-nav group, onNavKey; closeFileView and openUrlView end the trail); ui/webview/icons.ts (ICON_BACK, ICON_FORWARD)
added: 2026-09-19
pr:
tier: feature
offered:
closed:
---
A link followed inside a shown file replaces the card; before this there was no way back but the Files pane's Recent list. The viewer now keeps a trail of the files reached through its own links (a module-level state with pure functions, file-trail.ts) and shows Back and Forward as two glyph buttons at the left of its bar, with Alt+Left and Alt+Right (Cmd+[ and Cmd+] on a Mac) as chords while no text field holds the keyboard. Back re-opens the previous file with no target, so the remembered place re-seats it, in the view it was left in, without touching the saved preference. An open from outside the viewer starts the trail over; closing the viewer ends it. Browser history is not integrated (recorded as a follow-on with the trade-off). No kernel change, no new route. Records in plans/markdown-viewer.md, Follow-on: Link navigation.
