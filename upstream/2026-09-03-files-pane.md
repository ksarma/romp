---
title: A "Files" pane: the file viewer as its own dashboard column (`/files`, `app=files`, `ui/webview/files.ts` + `files-pane.css`, sixth in `_PANE_ORDER`, off by default), a third value of the fork's `fileLinkPane` setting ("pane") routing a chat file-link click into it with the session's identity for the chip, a recent-files empty state, and the viewer's quote-to-composer seed forwarded through the shell from any pane without a composer
status: approved
where: fork PR #187 (branch `filespane`, merged 2026-09-03; stacked on `dfaf23e8`). Approved part: the fourth commit `3ac26e30` only (`ui/webview/file-view.ts` `composerWindow` plus the shell's `editorSelection` forward in `kernel/kernel.py`); commits 5-12 stay home. The whole branch: `kernel/kernel.py` (`_files_page`, `/files`, every landing pane list, the relay's `pane` branch, the `editorSelection` forward, the shim's `NO_STALE_CAP` — a page with no kernel-pushed view opts out of the stale-banner arm), `ui/webview/files.ts`, `files-recent.ts`, `files-pane.css`, `file-view.ts` (`composerWindow`, `initFileView` `onRelay`, the editor-chunk derivation naming `files.js`), `render.ts` `openPath`, `settings.ts`, `gear.js`; tests in `tests/test_files_pane.py`, `ui/webview/files.test.ts` and the pane pins
added: 2026-09-03
pr: 187
tier: feature
offered:
closed:
---
Stacks on FORK-ONLY infrastructure: upstream removed the `viewFile` shell relay and has no `fileLinkPane` setting, so the routing half does not port as-is, and the pane itself needs upstream to want a sixth column. Portable on its own: the cross-document quote seed (`composerWindow` + the shell's `editorSelection` forward, the branch's first commit), which also fixes the feed-hosted viewer's dead quote gesture that upstream ships. Browser shell only; the VS Code extension mirror is deferred like the waiting pane's.

Status detail (migrated from the table): candidate (partial)

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier feature — PARTIAL: only the cross-document quote-to-composer seed (commit `3ac26e30`), which fixes the feed-hosted viewer's dead quote gesture upstream ships; it depends on the viewer-title entry (`viewer-title-session-name`, `dfaf23e8`). The pane itself (`_files_page`, `/files`, `files.ts`, `fileLinkPane`) needs a maintainer conversation of its own and stays home; the VS Code mirror is deferred).
