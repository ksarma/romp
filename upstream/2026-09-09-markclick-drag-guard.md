---
title: Comments panel: a drag-selection inside a change mark ends in the Comment float, not the change card
status: candidate
where: ui/webview/file-comments.ts (dragClick; the fcchange and fcopen handlers), ui/webview/file-comments-markclick.test.ts, ui/webview/file-comments-markclick-browser.test.ts, plans/file-review.md (Slice 2, decision 41, Tests), docs/guide.md
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
A change mark and a comment highlight are controls, so a drag begun and ended inside one fired a click on it, the card opened, and its scroll hid the Comment float: a comment inside a tracked change could be left only by replying to the change. The guard reads the click's own state (a non-collapsed selection with both ends in the viewer's body is a drag's) and leaves the keyboard (detail 0) alone. Client-only; a stand-in unit module and a two-engine browser leg with a real mouse drag.
