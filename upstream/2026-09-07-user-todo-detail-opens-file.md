---
title: A user todo's detail path opens the file from the Waiting-on-you pane: a file path in a todo's detail is a link that opens the file in the Files pane, the Reply modal shows the same link, and a relative path resolves against the todo's session on the kernel
status: candidate
where: fork PR #239 (`filereview-s0`, merged 2026-09-06): `ui/webview/path-links.ts` (new: the path-token matcher moved out of `render.ts`, emitting `.file-uri-link` spans with `data-act="openpath"`), `ui/webview/waiting.ts`, `ui/webview/render.ts`, `ui/webview/files.ts`, `ui/webview/file-view.ts`, `kernel/kernel.py`, `docs/guide.md`; tests `ui/webview/path-links*.test.ts`, `ui/webview/waiting-detail-link.test.ts`, `ui/webview/waiting-link-focus.test.ts`, `ui/webview/waiting-pane-browser.test.ts`, `ui/webview/user-todo-links*.test.ts`, `tests/test_path_links.py`, `tests/test_kernel_path_token_pointer.py`, `tests/test_guide_waiting_on_you_hidden_todos.py`
added: 2026-09-07
pr: 239
tier: feature
offered:
closed:
---
Slice 0 of plans/file-review.md, which its Upstream section names as a candidate on its own: a session's `add_user_todo` detail that names a file left the person a path to copy into the Files pane; now the path is the link. Self-contained (no sidecar, no host script), and the shared path-link module is what the chat's own path links use too. Not yet offered.
