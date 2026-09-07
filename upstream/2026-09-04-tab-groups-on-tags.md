---
title: Tab groups on tags: a spawned session inherits its parent's tag memberships (a fork, a promoted comment thread, and `romp new` run inside a session, which sends `ROMP_SID` as `parent` marked `parentAuto`, and inside a comment thread resolves to the thread's session; POST /new and the WS createSession op take `parent` + `tags` and refuse an unknown explicit parent — an unknown AUTO parent creates the session untagged with `parentIgnored` echoed; /new echoes `tags` plus the positional `tagsRequested`/`tagsApplied` pair so the CLI tells a normalized name from a refused one; the two doors differ on a name that already runs: `/new` re-asserts an explicit `--in`, the picker's op warns instead, since its Tags row is a prefill), `romp new --in <tag>` / `--no-inherit`, and the chat tab strip sectioned by home tag on the desktop layout only (headers in `tagOrder`, per-browser fold state with `archived` folded by default, header drag reorders `tagOrder` through the views path the timeline's pill drag writes, one-click "Move to <tag>" rows in the Tags flyout, the picker's prefilled Tags row for SDK sessions, a "Group tabs by tag" switch in the tag-lens menu); every views-blob writer under `_views_lock`
status: approved
where: fork PR #189 (branch `tabgroups`, merged 2026-09-05): `kernel/kernel.py` (`_inherit_tag_membership`, `_tag_ack` / `_tag_new_session`, `_resolve_parent_sid` / `_parent_from_request`, the `/new` + `createSession` params, the locked `setTimelineViews` write), `bin/romp`, `ui/webview/tab-groups.ts` + `render.ts` / `tag-menu.ts` / `styles.css`, `docs/guide.md` / `reference.md` / `read-side.md`; tests in `tests/test_timeline_views.py` (TagInheritance), `test_new_route_prefs.py` (NewRouteTags), `test_new_session_dir.py` (CreateSessionTags), `test_kernel_fork.py`, `test_comment_threads.py`, `tests/romp.bats`, `ui/webview/tab-groups.test.ts`
added: 2026-09-04
pr: 189
tier: feature
offered:
closed:
---
Upstream ships the same tag store, `_heal_timeline_views`, `romp new`, and Tags flyout, so both halves port as-is. Two offerable units: the kernel + CLI inheritance (one commit each), and the sectioned strip. No fork-only infrastructure involved. Known v1 gaps to state in any offer: inheritance is local-tags-only (a remote-homed parent tag is not copied), a tab dropped into another section does not change membership (Move to is the path), and the phone page has no strip to section.

Status detail (migrated from the table): candidate

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier feature — two offerable units (inheritance; the sectioned strip); the folded-tab-strip entry and the Codex-arm tagging divergence ride on it; state the v1 gaps (local-tags-only inheritance, a drop does not change membership, the phone strip is unsectioned)).
