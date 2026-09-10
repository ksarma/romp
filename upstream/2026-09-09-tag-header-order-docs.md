---
title: Guide: a tag group's header shows the tag's color and name, then the chevron and the count, the order the strip builds
status: merged
where: upstream branch tag-header-docs-offer: `docs/guide.md` (one sentence) and `ui/webview/tab-groups.test.ts` (an executing pin on the guide sentence plus a check that no CSS reorders the header)
added: 2026-09-09
pr:
tier: docs
offered: their PR #1225
closed: 2026-09-10
---
An upstream-native defect from their #1185, which reordered the tag group header to chip, caret, count and left the guide sentence listing the chevron first. Found by romp-maintainer-1's post-merge record; offered on the user's go of 2026-09-09.
