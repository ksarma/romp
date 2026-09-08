---
title: The file viewer renders a note in a document type scale: GitHub heading sizes with rules under h1 and h2, a centred 80ch column at 1.15 times the page size in a sans face in both themes, task boxes without bullets, table header fill, striping and column alignment, kbd, tab-size 4, per-line rows and a Copy button on every fence, six more grammars (rust, go, c, java, sql, toml), a readable code-comment colour, a pane-wide table under the centred column through a body-sized container, an anchor map that paints across wrapped code rows, and an @media print block that prints a note black on white across pages
status: candidate
where: ui/webview/styles.css, ui/webview/feed.css, ui/webview/files-pane.css, ui/webview/file-view.ts (mdBlock), ui/webview/code-block.ts (new), ui/webview/viewer-grammars.ts (new), ui/webview/highlight-cache.ts, ui/webview/render.ts, ui/webview/anchor-map.ts, ui/webview/reader-place.ts, docs/guide.md; tests ui/webview/file-view-typescale-browser.test.ts, file-view-print-browser.test.ts, anchor-map-wrapped-code.test.ts, anchor-map-wrapped-code-browser.test.ts, code-block.test.ts
added: 2026-09-08
pr:
tier: feature
offered:
closed:
---
Slice 3 of plans/markdown-viewer.md (decisions 3, 4 and 5 ruled 2026-09-07); the build note under the slice records where the code departs from the plan text. Fork-only pieces: none; the whole slice is viewer code upstream ships too. Depends on Slices 1 and 2 (fork PRs #390 and the mdviewer-s2 branch).
