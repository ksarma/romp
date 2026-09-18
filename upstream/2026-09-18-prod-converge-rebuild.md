---
title: The in-place converge rebuild builds the production profile
status: approved
where: kernel/kernel.py _rebuild_dist; tests/test_bundle_build_mode.py
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
A bare node esbuild.js in _rebuild_dist served unminified bundles with sourcemaps after every fast-forward, and _ensure_bundles never re-minified them (mtime staleness, not profile). Same --production and ROMP_EXT_DEV_BUILD knob as the two other builders; test fails before.

2026-09-18: approved for offer by the user (batch 2 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded). Filed stacked on new-route-effort-refusal-echo (shared file kernel/kernel.py); bar-wire-comment-fix's one line rides in this PR.
