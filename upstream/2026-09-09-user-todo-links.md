---
title: User todos: URLs in the text are links, and a todo can carry its own link
status: candidate
where: fork branch `todo-links` (ui/webview/url-links.ts and ui/webview/link-opener.ts new; ui/webview/render.ts, ui/webview/waiting.ts, ui/webview/file-view-links.ts, ui/webview/pr-links.ts, ui/webview/styles.css, ui/webview/waiting-pane.css; kernel/kernel.py `_user_todo_link`, `_register_user_todo`, `_open_user_todos`, the lifecycle log and its fold, `_user_todo_context_block`, the /usertodo route; postal/postal_service.py the `link` argument, `_todo_link_error` and the tool descriptions; docs/reference.md, docs/guide.md, CONTEXT.md, claude/romp-session-prompt.md; tests/test_user_todos.py, tests/test_postal_user_todos.py, tests/test_postal_user_todo_link.py, tests/test_reference_todo_file.py, tests/test_injected_voice.py, ui/webview/url-links.test.ts, ui/webview/render-todo-file-chip.test.ts, ui/webview/waiting-file-chip.test.ts and the re-aimed ui/webview/user-todos-card.test.ts, user-todo-title-links.test.ts, user-todo-links.test.ts, file-uri-link.test.ts, file-view-links.test.ts)
added: 2026-09-09
pr:
tier: feature
offered:
closed:
---
A fix and a feature on the user-todo surfaces (the user 2026-09-08, whose todo titles carried pull-request URLs that stayed plain text). The fix: an http(s) URL in a todo text or detail is a link on every surface that renders it (the chat card, its Reply modal, the Waiting-on-you pane, pinned notes), through the file viewer URL grammar moved into url-links.ts and run before the path walk; punctuation after the URL and a closing bracket it did not open stay outside the link. The feature: an optional `link` argument on add_user_todo, http or https only, refused otherwise before any post (the kernel route answers 400 for other clients), stored beside `file`, carried on the wire and in the lifecycle log the same way, and shown as a second chip in the file chip dress. The pane opener the PR links use is lifted into link-opener.ts and shared.
