---
title: Merged board: applyViewerClears drops a remote archived top whose only completion is a copied status (cleared, derived done, blank summary) with its subtree, mirroring the owning kernel's overlay rule from their #1243
status: offered
where: ui/webview/federation.ts (applyViewerClears), ui/webview/federation-cleared-overlay.test.ts
added: 2026-09-10
pr:
tier: fix
offered: their PR #1269
closed:
---
Parity break between their #1243 (our archived cleared-root offer) and the viewer's cleared overlay, recorded as an unverified nit in #1243's review and verified at the tip. Filed directly from the upstream base.
