---
title: Auto-reload notices: the four state refusals (a picker waiting, an edit in progress, attachments staged, a branch jump off this dashboard) are raised through ephemeralWarnToast so they do not replay after the reload
status: merged
where: ui/webview/render.ts (stageComposer, the branchjump handler), ui/webview/reload-notices.test.ts
added: 2026-09-09
pr:
tier: fix
offered: their PR #1227
closed: 2026-09-10
---
Follow-up to their #1217 (our reload-notices offer), which marked one state refusal and undercounted: three staging refusals and the branch-jump refusal also report a state, and the edit refusal replays as a false report on a page with no edit in progress. Filed directly from the upstream base; lands on the fork by the next fold.
