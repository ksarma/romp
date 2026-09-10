---
title: Markdown images: the served-URL probe budget follows the URL (mdImgProbe, mdImgProbing beside mdImgFailed), so a turn re-rendered while it streams keeps its three attempts, and the reconnect heal probes every remembered URL
status: offered
where: ui/webview/preview.ts (retryMdImgProbes, the capture listener, probeMdImgUrl.onload, healMdImgs), ui/webview/md-img-park.test.ts
added: 2026-09-10
pr:
tier: fix
offered: their PR #1245
closed:
---
Defect in their #1222 (markdown images parked) recorded by the review of that PR: the three-attempt budget was a closure over the img element a streaming turn replaces on every push, so a served URL that 404s while its turn streams got one probe and stayed parked; the heal read connected imgs only. Upstream-native; filed directly from the upstream base.
