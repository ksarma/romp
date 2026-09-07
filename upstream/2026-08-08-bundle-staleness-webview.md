---
title: Bundle staleness check never watched `ui/webview`, so dashboard edits silently never shipped
status: resolved-upstream
where: PR #24
added: 2026-08-08
pr:
tier:
offered:
closed:
---
Upstream ships the same `_ensure_bundles` and the same bug: it scans only `vscode-extension/src`, while the browser UI is BUILT from `ui/webview` (render.ts, styles.css) — so an edit there leaves `dist/render.js` stale and the kernel serves the old dashboard with the source correct and pushed. It hides behind luck: any change that also brushes `src/` rebuilds everything. Found live (the user 2026-08-08) when a fast-mode badge stayed blue in the chat while the timeline's star went orange — the timeline pane is served verbatim from source, the chat from dist. Pure bug fix, no fork-specific content. RESOLVED upstream independently in v0.6.0 (`276571f8`, "the bundle watch sees its sources"); the fork kept its own `_bundle_inputs` in the merge as a superset — check the residual delta before ever offering it, likely not worth a PR.

Status detail (migrated from the table): resolved upstream
