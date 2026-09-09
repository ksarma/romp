---
title: esbuild.js: a failed rebuild leaves dist/ as it was, each bundle lands by rename, and the last stderr line names the cause
status: offered
where: upstream branch esbuild-atomic-offer, re-derived from fork commits cd96affe, 75cf78d5, 3c41c49a: `vscode-extension/esbuild.js` (buildAll with write: false, staging plus rename, stale-staging removal, failureSummary fitted to the kernel's 300-character tail, the require.main gate and exports); tests `vscode-extension/src/esbuild-build.test.ts`, `esbuild-failure-cap.test.ts`, `esbuild-write-rename.test.ts` (15 executing cases)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1213
closed:
---
Audit row 9. A webview failure after the extension bundle built left dist/ half new (the kernel's cache token jumped and every dashboard reloaded into stale bundles), each in-place write could serve a truncated bundle mid-write, and the stderr tail showed esbuild's transport stack. Fork PR #440's lab-copy race is a separate docs-tier follow-up.
