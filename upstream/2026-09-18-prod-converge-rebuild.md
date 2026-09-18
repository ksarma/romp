---
title: The in-place converge rebuild builds the production profile
status: candidate
where: kernel/kernel.py _rebuild_dist; tests/test_bundle_build_mode.py
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
A bare node esbuild.js in _rebuild_dist served unminified bundles with sourcemaps after every fast-forward, and _ensure_bundles never re-minified them (mtime staleness, not profile). Same --production and ROMP_EXT_DEV_BUILD knob as the two other builders; test fails before.
