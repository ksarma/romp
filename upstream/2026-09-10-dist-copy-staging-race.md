---
title: Tests: the served-page classes copy dist/ through one helper (tests/dist_copy.py copy_dist) that skips a concurrent build's staging files, and esbuild.js's failure line survives an empty errors list; the 300-character cut is pinned against the kernel's tail
status: offered
where: tests/dist_copy.py (new), 17 served-page test modules' setUpClass copies, vscode-extension/esbuild.js (failureSummary, main().catch), vscode-extension/src/esbuild-build.test.ts, tests/test_dist_copy_staging.py, tests/test_bundle_build_mode.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1238
closed:
---
Follow-up to our merged #1213 and the finding its post-merge record filed: under a parallel local pytest a served-page class could error in setUpClass on a hidden .tmp staging file a sibling worker's rebuild removed mid-copy. Filed directly from the upstream base.
