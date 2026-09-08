---
title: Hide single sessions inside a tab-strip group, apart from the group fold: the section snapshot lists every member with a Hide or Show button and a Hidden (N) fold that keeps hidden sessions one click away, with a needs-you count on its head; a hidden member has no tab while its group is open, folding and opening the group leave the hidden set as it was, the header keeps the pip and todo flag over hidden members and its count says how many are hidden, a pick of a hidden session shows its transcript with the header as stand-in without opening the fold; the flag is a per-(tab, section) entry beside the Show-when-folded pins in the per-browser romp:tabgroups store (same shape, same rename follow, same prune; an older store reads as nothing hidden), and the hide wins where a member is both pinned and hidden
status: candidate
where: fork branch tabhide: ui/webview/tab-groups.ts (TabGroupsState.hidden, isHidden / setHidden / toggleHidden, planStrip hides, headWords, StripHead), ui/webview/tab-snapshot.ts (SnapRow.hidden, hiddenNeeds, hiddenFoldWords, actWords, snapshotHeading), ui/webview/render.ts (writeTabGroupsPruned, the snapshot host acts hide / show / toggle-hidden, syncHiddenFold, setRowHidden, hiddenTabIds), ui/webview/styles.css, docs/guide.md, docs/reference.md; tests ui/webview/tab-hide.test.ts
added: 2026-09-08
pr:
tier: feature
offered:
closed:
---
Rides the tab-groups, tab-strip-todo-flag and tabsnapshot entries (the snapshot pane is the surface). No kernel change: the store is per browser, as the folds and pins are.
