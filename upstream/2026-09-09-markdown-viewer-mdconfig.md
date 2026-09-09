---
title: Markdown viewer Slice 4: one marked configuration for every bundle (md-config.ts), Obsidian constructs (front matter, footnotes in place, callouts, ==mark==, wikilinks and embeds), KaTeX in the files and feed bundles, rewriteFigureSrcs over every fetching attribute, and a click-to-load gate for figures on hosts outside a gear list
status: candidate
where: fork branch `mdviewer-s4`: ui/webview/md-config.ts (new), figure-gate.ts (new), render.ts, file-view.ts, file-view-links.ts, chat-md.ts, anchor-map.ts, file-comments.ts, settings.ts, gear.js, styles.css, feed.css, tools/file-comments-host.mjs; tests md-config.test.ts, md-config-obsidian-browser.test.ts, anchor-map-obsidian.test.ts (fixture anchor-map-fixtures/obsidian.md), figure-gate.test.ts, file-view-figures-gate-browser.test.ts, gear-figure-hosts.test.ts, math-bundles.test.ts, plus the re-pinned anchor-map, chat-md, render-math, md-url-view, file-view-figures-absolute, md-sanitize-viewer-math-browser and md-strikethrough tests; docs/guide.md, docs/reference.md, plans/markdown-viewer.md
added: 2026-09-09
pr:
tier: feature
offered:
closed:
---
Upstream ships the same viewer and the same chat renderer, so every piece applies there: a note with Obsidian syntax renders as Obsidian renders it, math renders on every surface instead of the chat page alone, and a remote picture in a viewed file no longer fires a request on open (a tracking pixel) unless its host is on the list or the person clicks. One consequence to weigh with it: the chat replies take the same grammar (wikilinks there are an unclickable styled span, a reply that opens with YAML folds), recorded in the plan as an open ruling. Built as Slice 4 of plans/markdown-viewer.md, stacked on Slices 1 to 3.
