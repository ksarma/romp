---
title: Pinned notes: a session pins short notes above its own transcript for the person it works for (postal pin_note / unpin_note; a sid-keyed kernel store with POST /pinnote and /unpinnote plus the unpinNote drive op; the #pinned-notes strip between the tab bar and the transcript, one code path with the user-todo row for path and PR links)
status: candidate
where: fork branch `pinnotes` (kernel/kernel.py the pinned-notes store, `_chat_build_sig` fold, `build_session` field, `_send_chat` tail, the two routes, the `unpinNote` drive op and `_chat_body`; postal/postal_service.py the two tools and `_pinned_notes_words`; ui/webview/pinned-notes.ts, render.ts, styles.css; vscode-extension/src/page-skeleton.ts; tests/test_pinned_notes.py, tests/test_postal_pinned_notes.py, tests/test_injected_voice.py, ui/webview/pinned-notes.test.ts; docs/reference.md, docs/guide.md)
added: 2026-09-08
pr:
tier: feature
offered:
closed:
---
A feature on top of the transcript pane, independent of the user-todos switch. The strip repaints only on the frame that carries a changed list (a pin, an unpin), the notes are bounded at eight per session with the oldest dropped first, and a remote session's pin or unpin is forwarded to the kernel that owns it the way /usertodo/withdraw is. The VS Code chat webview shares render.ts and the skeleton, so it gets the strip too.
