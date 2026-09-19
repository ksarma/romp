---
title: Compact mode streams its tail by unit, and the head gap's per-turn estimate is the median over complete turns, measured off the unit observer
status: candidate
where: ui/webview/render.ts (syncViewInner's compact seam, patchWorkedFooters, renderWindowItems, sizeSpacers, measureUnits/applyMeasure, the unit ResizeObserver), ui/webview/chat-compact-tail.ts, ui/webview/turn-estimate.ts, ui/webview/chat-regions.ts (MAX_TURN_PX)
added: 2026-09-19
pr: 861
tier: fix
offered:
closed:
---
Two defects the user sees on both platforms, visible on the phone: typing and streaming stutter (in compact mode, the default, every streamed frame that changed or appended an event rebuilt the whole rendered window, at least 80 units, once per animation frame) and the head spacer jumping 24k to 1.43M px in one second (the per-turn estimate was the window's whole height over its user-row count, measured once for the view's life, so a tail window with one user row read about 7,150 px per turn). Fix 1: the compact tail trims by data-unit from the first unit the plan names (chat-compact-tail.ts) and re-appends with appendItem; the rebuild stays for a stale view, a change above the window, a gap past the start or a bottom spacer; the folded-reply footer is patched by position instead of marking the view stale. Fix 2: the median over the turns the window holds whole, at least two, re-measured on every window build, capped at 20 default turns under every reader. Fix 3: no layout read in the render task: heights come from the unit ResizeObserver's border-box map at frame end, the figures reach the DOM inside the next paint, and the spacer diag row reads the scroller a frame later.
