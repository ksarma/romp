---
title: Chat page: a compact tabs-and-agents setting
status: candidate
where: ui/webview/settings.ts, ui/webview/dense-chrome.ts, ui/webview/render.ts, ui/webview/gear.js, ui/webview/styles.css, docs/guide.md, ui/webview/dense-chrome.test.ts, ui/webview/settings.test.ts
added: 2026-09-09
pr:
tier: feature
offered:
closed:
---
A new boolean setting, denseChrome (gear: Compact tabs and agents, off by default), applied as one body class by a pure applier beside the scheme and theme appliers, with a scoped block in styles.css: the tab strip's tabs and group headers get smaller padding, tighter gaps and (tabs) the 0.86em rung; the background-work box's rows get 11px text, a 1.3 line height, tighter padding, the trailing status word hidden where the dot already says it, and the list capped at about four rows with its inner scroll. Density only: no render path changes, and every default is byte-identical. The existing compact setting is the transcript fold, so a new key. Under the phone layout media rule the bar holds the session picker, so the strip rules reach only a viewport that shows the wrapping strip; the box rules reach every layout.
