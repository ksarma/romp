---
title: API health indicator: history on hover. The rail cell's hover and click detail gain a History section read from GET /api-health at show time (the shell's cookie auth, no poll, the frame unchanged): overall.state with its since and why, one row per window (attempts, 429 and 5xx shares, give-ups, sessions retrying; an incomplete window says how long the kernel has been up), the newest six transitions with the state entered and how long it held, a kernel-restart row or divider where the tail crosses bootAt, and a loud line when the read fails; focus shows the hover and blur hides it
status: candidate
where: kernel/kernel.py (_LANDING_APIH_JS: load, histHTML, winRow, transRows; the tip stylesheet), docs/reference.md "The bottom bar's indicator", docs/guide.md; tests tests/test_api_health_hover.py, tests/test_api_health_hover_browser.py, ui/webview/api-health-hover.test.ts
added: 2026-09-08
pr:
tier: feature
offered:
closed:
---
Depends on the api-health-signal entry (approved) and the bottom-bar cell that offer carries. Reads the signal through the designed route, so it ports with them; nothing fork-specific beyond the salted labels the parent entry already flags.
