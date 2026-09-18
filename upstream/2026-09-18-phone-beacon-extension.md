---
title: Phone beacon extension: opt-in shared fields in the browser timing rows, a kill switch, the hide flush, and a kernel-side allowlist with row caps
status: candidate
where: ui/webview/perf-telemetry.ts (readSwitches, navInfo, foldResources, pageMarks, envInfo, the gap loop, the hide flush), ui/webview/settings.ts and gear.js (perfShare, perfMute under Debug > Diagnostics), kernel/kernel.py (the shim's __rompPerfMarks and diagMuted, the shell's diagMuted, CLIENT_DIAG_KEYS and _client_diag_admit/_client_diag_line in the clientDiag handler)
added: 2026-09-18
pr:
tier: feature
offered:
closed:
---
Two per-browser gear switches, both off by default. Share ON adds to the minute row, numbers and fixed-vocabulary identifiers only: nav, res, marks and env once per page (env again after a rotation), vis, wsBytes and rafGap every row. Mute ON stops every clientDiag row from the browser: the collector's, the pane shim's, the reload core's and the shell's. The collector flushes its minute on visibilitychange to hidden (iOS never fires pagehide on an app switch). The kernel's clientDiag handler admits an allowlist of top-level data keys per surface, cuts strings at 64 characters and stores a row over 8 KiB as a cap marker. Motivated by the phone freeze rows of 2026-09-18; the offer waits on the user's word under the standing no-new-upstreaming rule.
