---
title: The section view's rows open the tab's context menu
status: candidate
where: ui/webview/render.ts: snapshotHost (one contextmenu listener on the view's host, calling showTabMenu with the section as the copy), rowHasTabMenu, startTabRename's row editor, renderSnapshot's rename hold; ui/webview/tab-snapshot-view.ts menuAnchor; styles.css; docs/guide.md, docs/reference.md; ui/webview/tab-snapshot-menu.test.ts
added: 2026-09-18
pr:
tier: feature
offered:
closed:
---
A right-click, a long-press or the keyboard's menu key on a row of a tag's at-a-glance view opens the tab's context menu for that row's session, built by showTabMenu itself with the section as the copy, so a hidden session (no tab on the strip) reaches every per-session setting from the one place it has a row; its Hide tab row reads Show tab. Rename edits the name on the row while the view shows it, under the strip's rename hold, since it resolved a tab node before and did nothing for a hidden session. The view and the menu are upstream's code (the T264b, T322 and tabhide work); the fork adds the door. An offer waits on the user's word.
