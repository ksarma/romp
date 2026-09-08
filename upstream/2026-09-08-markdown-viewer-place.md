---
title: The markdown viewer keeps the reader's place across a reload, a view switch, a pane resize and a text-size step; a sized picture keeps its ratio; the notice bar sits above the body row and survives scroll and swaps; the Comment float hides on body scroll; the row's redundant container-type goes (plans/markdown-viewer.md Slice 2)
status: candidate
where: fork branch mdviewer-s2 (ui/webview/reader-place.ts new; ui/webview/file-view.ts renderBody, the ResizeObserver repaint, setTextSize, noteBar, enterEdit, exitEdit, openUrlView; ui/webview/anchor-map.ts renderedBlockSpan, renderedBlockAt, rawRowSpan; ui/webview/file-comments.ts hideFloatOnScroll; ui/webview/styles.css and feed.css; the legs file-view-place-browser, file-view-notebar-browser, file-comments-float-scroll-browser, file-view-fold-browser over ui/webview/real-viewer-leg.ts, file-view-place.test.ts, md-sanitize-wide-media-browser.test.ts; the moved pins; docs/guide.md; plans/markdown-viewer.md)
added: 2026-09-08
pr:
tier: fix
offered:
closed:
---
