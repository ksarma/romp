---
title: The viewer's GitHub link: a lazy sid-routed fileGitLink op (git on the owning machine answers toplevel/tracked/origin), an anchor that appears only on a real URL
status: merged
where: fork PR (fbgh branch)
added: 2026-08-15
pr:
tier:
offered: their PR #543
closed: 2026-08-22
---
MERGED 2026-08-22: rebased onto the just-landed file browser (landing as `a04be8aa`), plus the maintainer’s follow-on commit (`fbc0a1b5`) generalizing the anchor into a viewer ACTION REGISTRY (the GitHub link is its first entry), which the fold adopted as the shared shape. Branch retired. OFFERED 2026-08-20 (branch `git-link`, `d4129996` off tip `f3ec1297`): anchor re-derived between Wrap and Download (upstream never took raw edits) with self-contained WS poster plumbing; the body offers to rebase around the sibling file-browser PR; review clean, scaffold CI green (since-closed fork #93). Follows the file-links/viewer offer like the rest of the viewer family; pure feature, no fork-specific content. Its gate cleared 2026-08-18 (#385 merged upstream). Like the browser row: re-derive against the v0.12.0 viewer (the fold placed the anchor in the acts bar between Edit/Save and Download), don't cherry-pick fork history.

Status detail (migrated from the table): ✅ **merged** — their PR #543, 2026-08-22 (merge `01ee7f5d`); came home in the 2026-08-22 tip fold (`upfold0823`)
