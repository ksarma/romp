---
title: Sessions & tags dialog: one-line tag rows with a colour popover, folded pane filters, room for the sessions
status: candidate
where: ui/romp-timeline-view.js (the dialog: one colour dot per tag row and _openTagColorPop/_closeTagColorPop, the pane-filters fold with lensSummary and the page-lifetime paneFiltersOpen, the tag table capped at 35vh and scrolling within itself), ui/timeline-tags-scale.test.ts (executed over the fake DOM), ui/timeline-tags-scale-browser.test.ts (the measured layout at 1300px with thirty tags and forty sessions), ui/timeline-views-panel.test.ts (four pins re-aimed), ui/CLAUDE.md (the many-tags rule)
added: 2026-09-09
pr:
tier: feature
offered:
closed:
---
With ten tags the dialog filled the page: twelve inline swatches per tag row and a five-pane matrix of every tag left two session rows under the fold. Each tag row is now one line with one colour dot that opens the palette as a popover (the same recolor write); pane filters fold to one summary line per pane, opened by the caption caret and remembered for the page; the tag table caps its height and scrolls within itself so the sessions table keeps the space.
