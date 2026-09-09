---
title: Tab strip, inline layout: a group header or the trail divider whose first tab wrapped to the next row moves down to open that row with it, and the divider counts as a row member for the per-row hairlines again
status: candidate
where: ui/webview/render.ts (paintTabRowLines counts the inline divider; keepGroupsWithTabs places a .tab-keep-break ahead of a header or divider whose first tab wrapped, on the strip rebuild, the strip's width observer and the document's fonts finishing a load, never while a tab is dragged, and not for a pair no row can hold; ensureTabRowObserver observes a zero-height width sentinel instead of #tabs, so the pass's own row changes raise no ResizeObserver loop notice; the tab drag's slot before the inline divider behind a keep break is the previous row's end), ui/webview/styles.css (the .tab-row-sentinel rule; comments), docs/guide.md; tests ui/webview/tab-row-keep.test.ts (the painter, the pass and the observer executed over a flex-wrap model), ui/webview/tab-row-keep-browser.test.ts (the same code in Chromium through a live observer: the loop notice, the drag freeze), ui/webview/tab-groups.test.ts, tests/test_tab_groups_rows.py (served, at a width where the pass fires, then narrowed through the live observer)
added: 2026-09-09
pr: 434
tier: fix
offered:
closed:
---
Follows the strip-inline offer (their PR #1168): under one group per row, upstream default, every header already opens its row and neither defect shows; the fix matters wherever the inline flow is on. Two defects from the fork PRs 401 to 404: T264 excluded .tab-group-sep from the hairline rows for the breaks, which dropped the visible inline divider too; and a header that fit at the end of a row while its first tab wrapped read as a caption over the tabs it stood above.
