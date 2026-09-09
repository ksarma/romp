---
title: File viewer: the edit-mode notice sits above the body, not inside it
status: offered
where: upstream branch notice-bar-offer, re-derived from fork PR #396 (mdviewer-s2): `ui/webview/file-view.ts` (`noteBar`, the fallback-editor and refused-save mounts, `exitEdit`'s removal by reference), `ui/webview/styles.css` and `feed.css` (`.fileview > .fileview-err { flex: 0 0 auto; }`); tests `ui/webview/file-view-notice.test.ts` (new), `file-edit.test.ts`, `fileview-parity.test.ts`
added: 2026-09-09
pr:
tier: fix
offered: their PR #1183
closed:
---
One piece of the markdown-viewer-place entry (fork PR #396, Slice 2) offered on its own: both edit-mode notices were prepended into `.fileview-body`, whose editor is 100% tall, so the notice cut the editor off by its own height and scrolled away with it. The notice is now a child of the card between the title bar and the body, held by reference so a replaced viewer's leaked Escape handler cannot strip the live card's notice; the rest of Slice 2 (the reader's place across paints) stays a candidate.
