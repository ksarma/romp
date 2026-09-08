---
title: Hide single sessions inside a tab-strip group, apart from the group fold: the section snapshot lists every member with a Hide or Show button and a Hidden (N) fold that keeps hidden sessions one click away, with a needs-you count on its head; a hidden member has no tab while its group is open, folding and opening the group leave the hidden set as it was, the header keeps the pip and todo flag over hidden members (the pip red for a feed-judged needs-you too) and its count says how many are hidden, and on an open group the count, pip and flag show the section in the pane without folding it; a pick of a hidden session shows its transcript with the header as stand-in without opening the fold; the flag is a per-(tab, section) entry beside the Show-when-folded pins in the per-browser romp:tabgroups store (same shape, same rename follow, same prune; an older store reads as nothing hidden, and a key a newer build adds rides an older build's writes), and the hide wins where a member is both pinned and hidden
status: candidate
where: fork PR #380 (`tabhide`): ui/webview/tab-groups.ts (TabGroupsState.hidden and rest, isHidden / setHidden / toggleHidden, planStrip hides, headWords, StripHead), ui/webview/tab-snapshot.ts (SnapRow.hidden, onYou, standInPip, hiddenNeeds, hiddenFoldWords, actWords, snapshotHeading), ui/webview/tab-state.ts (SHOW_GROUP_CLICK, sectionDoorTitle, sectionTodoTitle door), ui/webview/tab-snapshot-view.ts (repeatedClick), ui/webview/render.ts (the non-folding door show-group, writeTabGroupsPruned, the snapshot host acts hide / show / toggle-hidden, syncHiddenFold, setRowHidden, hiddenTabIds), ui/webview/styles.css, docs/guide.md, docs/reference.md; tests ui/webview/tab-hide.test.ts, ui/webview/tab-hide-browser.test.ts
added: 2026-09-08
pr: 380
tier: feature
offered:
closed:
---
Rides the tab-groups, tab-strip-todo-flag and tabsnapshot entries (the snapshot pane is the surface). No kernel change: the store is per browser, as the folds and pins are.
