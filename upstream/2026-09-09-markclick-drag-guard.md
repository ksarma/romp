---
title: Comments panel: a drag-selection inside a change mark ends in the Comment float, not the change card
status: candidate
where: ui/webview/file-comments.ts (dragClick, endInside; the fcchange and fcopen handlers), ui/webview/actions.ts (the stand-down comment), plans/file-review.md (Slice 2, decision 41, Tests), docs/guide.md; tests ui/webview/file-comments-markclick.test.ts, file-comments-markclick-controls.test.ts, file-comments-markclick-browser.test.ts, file-comments-markclick-controls-browser.test.ts, actions.test.ts, tools/file-review-plan-markclick.test.mjs
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
A change mark and a comment highlight are controls, so a drag begun and ended inside one fired a click on it, the card opened, and its scroll hid the Comment float: a comment inside a tracked change could be left only by replying to the change. The guard reads the click's own state against the clicked mark (a non-collapsed selection whose ends both lie inside that mark, or at its edges as an engine may report a drag's end, is a drag's; one standing elsewhere in the body leaves the click a click, since a press on a deletion's label, a region rectangle or a mark inside a link collapses no standing selection), takes the press pulse back on the click it stands down, and leaves the keyboard (detail 0) alone. Client-only; two stand-in unit modules and two Chromium-and-Firefox browser legs with a real mouse.
