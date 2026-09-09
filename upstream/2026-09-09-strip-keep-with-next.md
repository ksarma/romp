---
title: Tab strip, inline layout: a group header or the trail divider whose first tab wrapped to the next row moves down to open that row with it, and the divider counts as a row member for the per-row hairlines again
status: candidate
where: ui/webview/render.ts (paintTabRowLines counts the inline divider; keepGroupsWithTabs places a .tab-keep-break ahead of a header or divider whose first tab wrapped, on the strip rebuild and the ResizeObserver that already paint the hairlines), ui/webview/styles.css (comments), docs/guide.md; tests ui/webview/tab-row-keep.test.ts (the painter executed over a flex-wrap model), ui/webview/tab-groups.test.ts, tests/test_tab_groups_rows.py
added: 2026-09-09
pr: 434
tier: fix
offered:
closed:
---
Follows the strip-inline offer (their PR #1168): under one group per row, upstream default, every header already opens its row and neither defect shows; the fix matters wherever the inline flow is on. Two defects from the fork PRs 401 to 404: T264 excluded .tab-group-sep from the hairline rows for the breaks, which dropped the visible inline divider too; and a header that fit at the end of a row while its first tab wrapped read as a caption over the tabs it stood above.
