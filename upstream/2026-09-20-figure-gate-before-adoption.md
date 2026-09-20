---
title: The viewer's figure chain runs on the sanitizer's inert body before the nodes are adopted, so WebKit no longer fetches a gated figure while its placeholder stands
status: candidate
where: ui/webview/file-view.ts (mdBlock: resolveFigureRefs, rewriteFigureSrcs and gateRemoteFigures run on the sanitized body, then box.replaceChildren adopts it); ui/webview/file-view-figures-gate-adopt-browser.test.ts (new: three engines through an HTTP proxy the test runs, real servers' request logs); ui/webview/file-view-seam.test.ts (the order pin); plans/markdown-viewer.md (the Slice 4 record's item 9)
added: 2026-09-20
pr:
tier: fix
offered:
closed:
---
In WebKit the viewer fetched a gated figure while its placeholder said "Click to load", a pre-existing defect on main found by the review of fork PR 862 (finding extra8-3). mdBlock adopted the sanitized nodes into a live-document element before the figure chain ran, and WebKit starts an img's fetch synchronously when the element's node document becomes one with a render tree; Chromium and Firefox defer that fetch to a microtask, which ran after the chain had moved the attributes, so neither leaked. Reachable from the kernel-served dashboard under WebKit (Safari, the iOS web app); not from the VS Code panes, whose CSP names no remote img-src. What left: the reader's IP address, the time, the user agent and the figure's path, with no Referer, since the kernel sends Referrer-Policy same-origin. A figure of the file's folder was also requested against the page before rewriteFigureSrcs repointed it, then again through /file. The fix runs the whole chain over DOMPurify's RETURN_DOM body, a DOMParser document with no browsing context that never loads, and adopts afterwards. The leg is red in WebKit at 2d41e5c9b and green in all three engines after; the iOS statement rests on Playwright's WebKit build, not a device test. A privacy surface, so it lands on the owner's word.
