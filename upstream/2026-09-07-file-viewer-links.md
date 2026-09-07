---
title: Links inside a file shown in the viewer: an http(s) URL in the text opens in a new tab; a file path opens that file in the viewer, resolved against the shown file's directory (absolute and `~/` paths as written, on the file's session), with a `:12` or `#L12` after it scrolling to the line; a Markdown link's target follows the same two rules; the grammar is the chat's path matcher under one extra gate (a slash and a letter-led extension, so import specifiers, routes and fractions stay text); the pass runs over the DOM the highlight built and changes no character, so comment highlights, change marks and selections keep working over a line with a link in it
status: candidate
where: fork branch `filelinks`: `ui/webview/file-view-links.ts` (new), `ui/webview/file-view.ts` (codeBlock, mdBlock, the body's link delegate, the `line` open option), `ui/webview/path-links.ts` (`PathLinkOptions`, `markPathLink`, `LINE_SUFFIX_RE`), `ui/webview/files.ts` (the pane's opener for a linked file), `ui/webview/styles.css` + `feed.css`, `docs/guide.md`; tests `ui/webview/file-view-links.test.ts`, `file-view-links-browser.test.ts`, `fileview-parity.test.ts`
added: 2026-09-07
pr:
tier: feature
offered:
closed:
---
Follows plans/file-review.md Slice 0 (the shared path matcher) and the viewer upstream already ships: the walk gains options rather than a second matcher, so the chat, the Waiting-on-you pane and the viewer link paths from one grammar. Self-contained (no kernel change: the kernel's `/file` route already resolves `~` and a relative path against the session's cwd). Not yet offered.
