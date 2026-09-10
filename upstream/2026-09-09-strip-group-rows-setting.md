---
title: Tab strip: one tag group per row becomes a setting (default per project)
status: merged
where: ui/webview/settings.ts (stripGroupRows, default off), ui/webview/gear.js (the Chat checkbox "One tag group per row in the tab strip"), ui/webview/render.ts (the T264 row breaks gated on the setting, makeTrailSep for the inline trail divider, the strip signature, the drop walk edge), ui/webview/styles.css (the divider rule scoped off the break), docs/guide.md (one sentence); tests ui/webview/tab-groups.test.ts, ui/webview/tab-drag-live.test.ts, ui/webview/settings.test.ts, tests/test_tab_groups_rows.py, ui/webview/tab-hide-browser.test.ts (the harness's settings stub at the fork default)
added: 2026-09-09
pr: 401
tier: feature
offered: their PR #1168 (feature; upstream keeps one group per row as the default and gains the gear setting; fork branch `strip-rows-offer`, commit `e0a64ffe` on their main `3e4398a3`)
closed: 2026-09-09
---
The fork flows the grouped tab strip inline by default (the user 2026-09-08, whose strip of eleven tag groups became eleven rows under T264, romp-on/romp#1087) and keeps the one-group-per-row layout as a per-device gear setting. Upstream keeps its per-row default; the offer is the setting, so a strip with many tag groups can flow.
