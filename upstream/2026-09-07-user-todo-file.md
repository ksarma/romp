---
title: A user todo names the file it is about: `add_user_todo(text, detail?, file?)` stores the resolved absolute path on the record, the Waiting-on-you row and its Reply modal show the file as a chip that opens it, the SessionStart listing shows the path after the text, and a Send from the file's Comments panel offers to answer the open todos naming the file however the file was opened (one is a checkbox, several a radio group)
status: candidate
where: the todo-file follow-on (plans/file-review.md, the Getting into it bullet and the note beside the Slice 2 build note): `kernel/kernel.py` (`_user_todo_file`, `_add_user_todo`'s `file`, POST /usertodo's `file` and `warning`, `_user_todos_naming_file` and the `todos` list on every successful `fileCommentsResult`, the context block's file line, the lifecycle log's `file`), `postal/postal_service.py` (the tool's `file` argument and the relayed warning), `hooks/romp-usertodo-context.sh`, `claude/romp-session-prompt.md`, `ui/webview/waiting.ts` and `waiting-pane.css` (the chip), `ui/webview/file-comments.ts` and `file-comments-model.ts` (`todoChoices`, the checkbox or radio group), `docs/guide.md`, `docs/reference.md`; tests `tests/test_user_todos.py`, `tests/test_file_comments.py`, `tests/test_file_comments_e2e.py` (the loop from the real postal tool over a loopback socket through the real handler), `tests/test_postal_user_todos.py`, `tests/test_session_prompt.py`, `tests/test_injected_voice.py`, `tests/romp-usertodo-context.bats`, `ui/webview/waiting-file-chip.test.ts`, `ui/webview/file-comments-todo-choices.test.ts`, `tests/test_guide_todo_file_chip.py`
added: 2026-09-07
pr:
tier: feature
offered:
closed:
---
Depends on the user-todos slices and the file-comments candidate landing first: the record, the tool and the panel it extends are theirs. Before it, the link between a todo and its file was a path in the todo's free-text detail (the Slice 0 candidate, user-todo-detail-opens-file), and only a Send from a viewer opened through that link answered the todo; now the association is a field, the kernel resolves it once, and any Send on the file offers the todo. Not yet offered: awaits the user's walk.
