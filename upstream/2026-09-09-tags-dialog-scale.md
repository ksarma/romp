---
title: Sessions & tags dialog: one-line tag rows with a colour popover, folded pane filters, room for the sessions
status: merged
where: ui/romp-timeline-view.js (the dialog: one colour dot per tag row and _openTagColorPop/_closeTagColorPop/_placeTagColorPop, _menuHost taking the anchor element, the pane-filters fold with lensSummary and the page-lifetime paneFiltersOpen, the height budget: the tag table capped at 30vh and scrolling within itself, the floors measured off the rendered rows (three tag rows, min(live, 4) session rows), the open matrix's own cell, the card scrolling past the floors, the New tag row under the table, the reorder drag's whole-row rule with the mid-drag re-rank), ui/timeline-tags-scale.test.ts (executed over the fake DOM), ui/timeline-tags-scale-browser.test.ts (the measured layout at 1300px, 800px, 700px, 420px and a phone held sideways with thirty tags and forty sessions, the floors with one and three tags and none to forty live sessions, a real pointer drag past the table's edge and a wheel mid-drag; the popover in an offset iframe and in the 200px bottom band), ui/timeline-views-panel.test.ts (pins re-aimed), ui/timeline-menu-place.test.ts (menuTop's above branch), ui/timeline-kernel-post.test.ts (opens the folded pane filters before clicking a chip), ui/timeline-tagorder-drag.test.ts (its cells seated inside the table's box), ui/webview/menu-echo.test.ts (the menu count follows the popover), ui/webview/tab-color-picker.test.ts (the swatch split read from the popover), ui/CLAUDE.md (the many-tags rule)
added: 2026-09-09
pr:
tier: feature
offered: their PR #1198
closed: 2026-09-09
---
With ten tags the dialog filled the page: twelve inline swatches per tag row and a five-pane matrix of every tag left two session rows under the fold. Each tag row is now one line with one colour dot that opens the palette as a popover (the same recolor write); pane filters fold to one summary line per pane, opened by the caption caret and remembered for the page; the tag table caps its height and scrolls within itself so the sessions table keeps the space.
