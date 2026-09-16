---
title: settings.ts showBranch comment carries two contradictory defaults
status: candidate
where: ui/webview/settings.ts (the showBranch field comment, near line 21)
added: 2026-09-16
pr:
tier: docs
offered:
closed:
---
Upstream's tip 14f1548a9 states two defaults in the showBranch field comment of ui/webview/settings.ts: T409's sentence (romp-on/romp#1613, commit c041acd97, merged 2026-09-14: the key is the MIRROR of the status line's branch widget, which defaults on since 2026-09-13), then the older sentence saying OFF by default (2026-08-10, the statusline trimmed for narrow panes; an explicit stored true keeps showing it), while DEFAULT_SETTINGS sets showBranch true and status-widgets.ts registers the branch widget defaultOn true. The OFF sentence entered upstream through upstream's PR romp-on/romp#276 on 2026-08-10 (commit 22467281e, subject: Show git branch defaults OFF, offered from this fork) and reached the fork in a fold; the commit is an ancestor of both trees, and the correction is offerable either way. T409 rewrote the sentence in front of it and left it standing. The fork's stage 1 pull-in of 14f1548a9 (the webview area's review round 1, item 4; commit b65ca1bc3) keeps T409's sentence and drops the OFF one, so the comment states the one default the code has; no code or pin changed, and the pull-in PR body's Semantic shifts records that the fork's pre-merge OFF default is reversed by the merge. The offer is the same one-sentence deletion on upstream's file.
