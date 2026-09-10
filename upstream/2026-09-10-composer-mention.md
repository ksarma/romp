---
title: Composer: "@" plus letters lists the live sessions by name, and Enter, Tab or a click inserts the plain @name
status: offered
where: docs/guide.md ui/webview/ask-draft-predates.test.ts ui/webview/composer-mention-pane.test.ts ui/webview/composer-mention.test.ts ui/webview/composer-mention.ts ui/webview/composer-resize.test.ts ui/webview/mcp-panel.test.ts ui/webview/reload-notices.test.ts ui/webview/render.ts ui/webview/scroll-movers.test.ts ui/webview/slash-cmd-chip.test.ts ui/webview/styles.css ui/webview/tab-close-clicksafe.test.ts ui/webview/tab-strip-skip-exec.test.ts
added: 2026-09-10
pr: 321
tier: feature
offered: their PR #1300
closed:
---
Features plan row: the composer's @-mention card and the @name chip; the pure module composer-mention.ts, render.ts owns the card, the composer wiring and the chip; every composer clear goes through clearBox(); an IME's commit Enter is left to the composition.
