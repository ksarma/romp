---
title: settings.ts showBranch comment carries two contradictory defaults
status: approved
where: ui/webview/settings.ts (the showBranch field comment, near line 21)
added: 2026-09-16
pr:
tier: docs
offered:
closed:
---
Upstream's tip 14f1548a9 states two defaults in the showBranch field comment of ui/webview/settings.ts: T409's sentence (romp-on/romp#1613, commit c041acd97, merged 2026-09-14: the key is the MIRROR of the status line's branch widget, which defaults on since 2026-09-13), then the older sentence saying OFF by default (2026-08-10, the statusline trimmed for narrow panes; an explicit stored true keeps showing it), while DEFAULT_SETTINGS sets showBranch true and status-widgets.ts registers the branch widget defaultOn true. The OFF sentence is upstream's own: commit 22467281e of 2026-08-10 (subject: Show git branch defaults OFF) was written on an upstream branch and landed through upstream's PR romp-on/romp#276, and it reached the fork at the v0.7.0 fold (fork PR 50); no fork commit ever carried it, so the merge drops upstream's earlier sentence, superseded by T409's default, and the correction is offerable as a one-sentence deletion on upstream's file. T409 rewrote the sentence in front of it and left it standing. The fork's stage 1 pull-in of 14f1548a9 (the webview area's review round 1, item 4; commit b65ca1bc3) keeps T409's sentence and drops the OFF one, so the comment states the one default the code has; no code or pin changed, and the pull-in PR body's Semantic shifts records that the fork's pre-merge OFF default (its DEFAULT_SETTINGS since the same fold) is reversed by the merge.

2026-09-18: approved for offer by the user (batch 5 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
