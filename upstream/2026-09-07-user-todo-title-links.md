---
title: A file path in a user todo's one-line text is a link, as a path in its detail already is: the same matcher and span (path-links.ts), applied by each host's todo linker to the row's text and the Reply modal's quoted line, in the Waiting-on-you pane and on the chat's todo card; the postal tool schema says so
status: candidate
where: fork PR #346 (`todolinks`): `ui/webview/pr-links.ts` (the reference boundary judged over the rendered text: prRefSegments takes the preceding character, the walk carries it across inline elements and resets at a line or block edge), `ui/webview/waiting.ts` (linkTodoPaths on the row and the Reply modal's quoted line, one delegate on the modal's box, showReply's PR-ref pass), `ui/webview/render.ts` (openLinkedPath, called by the transcript's bindPathLink and the body delegate's openpath; linkTodoLinePaths marks the line without the figure pass, linkTodoDetailPaths is linkifyFileUris with delegated binding), `postal/postal_service.py` (add_user_todo's text/detail descriptions), `docs/guide.md`, `docs/reference.md`; tests `ui/webview/user-todo-title-links.test.ts` (new), `ui/webview/pr-links.test.ts`, `ui/webview/user-todo-links.test.ts`, `ui/webview/waiting-detail-link.test.ts`, pins in `file-uri-link`, `chat-pin-history`, `chat-space-paths`, `user-img-dedup`
added: 2026-09-07
pr: 346
tier: feature
offered:
closed:
---
Rides with the user-todos slices (upstream/2026-08-22-user-todos-slice-*.md, approved as an RFC) and the detail's file links (upstream/2026-09-07-user-todo-detail-opens-file.md): it adds no system those do not already ship, and the kernel is untouched (shape-only linking, the detail's grammar; a :line suffix stays text). The user 2026-09-07: sessions often put the path in the line itself, which left no way to open it.
