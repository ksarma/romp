---
title: The chat's empty Codex effort menu states a final answer instead of waiting
status: approved
where: ui/webview/render.ts toggleMetaMenu's empty Codex arm: with a per-model catalog held, the effort kind writes the timeline lane menu's sentence and no dots, at open and in the loaded callback; ui/webview/codex-meta-choices.test.ts pins and executes it
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The chat's empty Codex effort menu wears the loader dots and says it is asking for the list, then that there is no effort list yet, for a model whose catalog entry lists no levels and for a model the catalog does not know: a wait-shaped row for a final answer, since the kernel serves the catalog from a once-per-process cache and the open's re-read cannot change it, while the timeline's lane menu already states the same case final. The fork carries the fix now: with a catalog held, the effort kind's row reads the timeline's sentence, no effort levels from Codex for this model, with no dots, at open and when the re-read lands, and the wait copy stays for a menu with no catalog yet. The offer waits on the user's word; the ledger is the queue.

2026-09-18: approved for offer by the user (batch 5 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
