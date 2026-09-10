---
title: A pane hidden after the user has looked at it no longer raises the stale banner: each pane publishes its hidden word, and every consumer reads the union of its probe and that word
status: merged
where: upstream branch pane-hidden-word-offer, re-derived from fork PR #392's review commits 3115179b and cd4cfe81: `ui/webview/paint-gate.ts` publishPaneHidden, new `ui/webview/chat-visibility.ts`, publishers in `feed.ts`, `fleet.ts` and `ui/romp-timeline-view.js`, the union read in `kernel/kernel.py`'s shim, `perf-telemetry.ts` and render.ts's prefetch gate, `docs/reference.md`; tests: kernel-lane node runs in `tests/test_kernel_disconnect_banner.py`, browser legs `tests/test_pane_hidden_word_browser.py` (Chromium and Firefox), webview executing tests and pins
added: 2026-09-09
pr:
tier: fix
offered: their PR #1216
closed: 2026-09-10
---
Audit row 6, a generalisation: the shim's paneHidden had one witness, the zero-viewport probe, which in Chromium keeps a display:none iframe at its last shown size, so a pane hidden after being shown could raise the stale banner over a working dashboard; every consumer of the probe now reads the union of the probe and the pane's own hidden word. The waiting.ts publisher stays fork-only until user todos land.
