---
title: Tab strip: an open group's count over hidden members reads 6+2, not "2 hidden"
status: candidate
where: fork PR #402 (merged 2026-09-09, the count fix to tab-hide-sessions): ui/webview/tab-state.ts (compactCount, stripAndHidden; headWords and sectionDoorTitle call them), ui/webview/tab-groups.ts, ui/webview/render.ts (two comment lines beside the count's paint), docs/guide.md; tests ui/webview/tab-hide.test.ts, ui/webview/tab-hide-browser.test.ts; upstream/2026-09-08-tab-hide-sessions.md (its title follows the form)
added: 2026-09-18
pr: 402
tier: fix
offered:
closed:
---
Belongs with tab-hide-sessions (fork PR #380) and rides in its offer: the head count over hidden members on an open group read as the words "2 hidden", which took too much room on a strip with a dozen groups; it now reads <shown>+<hidden> (6+2), as narrow as a plain count, with its first number still matching the tabs on the strip. One source for the form in tab-state.ts; the tooltip spells it out.
