---
title: Chat: a Codex model or effort menu with no list says why and asks for the list again instead of opening blank
status: merged
where: upstream-only follow-up on fork branch `codex-picker-row-offer` (commit `0234412c` on their main `1566f7ae`): `ui/webview/render.ts` meta menu (reason row reading the codex section `error`, re-read on open, re-resolved anchor, dismissed-tab close, HTTP status in the picker error), `ui/webview/styles.css`, `ui/webview/codex-meta-choices.test.ts`, `ui/webview/models-rev.test.ts`, `docs/codex.md`. The fork carries the same idea from #406 against its own render.ts; the fold reconciles
added: 2026-09-09
pr: 406
tier: feature
offered: their PR #1172
closed: 2026-09-09
---
Fourth Codex piece owed upstream after #406. Labelled feature (a new UI state with copy, a CSS class, a re-read policy and two placement rules); the body says fix is defensible if the maintainer prefers. Reads the error field their #1167 added. A member feature PR merges on the owner approval on the current head: rebase only when CONFLICTING.
