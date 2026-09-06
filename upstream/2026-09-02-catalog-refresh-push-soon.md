---
title: `_refresh_model_catalog` called `_push_soon()` after a fetch added version ids, its comment claiming the pickers re-read `/models` on the next frame — but no client re-read the choice lists after page load: `render.ts` filled `MODEL_CHOICES` / `EFFORT_CHOICES` from one page-load fetch, `gear.js` wrote its options exactly once per page (`choicesP`), and the timeline's lane list loaded once — so an open dashboard kept the page-load list until a reload, and the push was a no-op for the thing it named
status: merged
where: FIXED on the fork in the `upfold0902` reconciliation (2026-09-02): the fetch that adds ids emits the models frame (`_models_changed` — the `{type:"models", rev}` frame fork PR #140 gave every picker a listener for: chat/comment `loadModelChoices`, the timeline lanes' `refreshModels`, the gear's `adoptChoices`/`paintChoices`), so every open picker re-reads `/models` on the event; the comment names the real mechanism. Pinned in `tests/test_model_catalog.py` (`FetchAndFallback::test_a_fetch_that_adds_ids_tells_every_open_picker_to_re_read_models`, silent when a fetch adds nothing)
added: 2026-09-02
pr: 140
tier:
offered: their PR #882
closed: 2026-09-02
---
MERGED as-is inside their PR #882 (the model-alias offer's third commit; merge `ab176ed7`, 2026-09-02) and in HEAD after upfold0905. What merged: `_refresh_model_catalog` calls `_models_changed()` when a fetch adds version ids, and `_models_changed` sends the `{type:"models", rev}` frame to the chat, timeline and feed clients whenever the pick memory moves or the catalog grows (both in `kernel/kernel.py`; the comment names this mechanism). Every open picker re-reads `/models` on the frame, highest rev wins: the chat and comment pickers' `loadModelChoices` (`ui/webview/render.ts`), the timeline lanes' `refreshModels` (`ui/webview/timeline-boot.ts`), the gear's `adoptChoices`/`paintChoices` (`ui/webview/gear.js`). Pinned by `tests/test_model_catalog.py` (`FetchAndFallback::test_a_fetch_that_adds_ids_tells_every_open_picker_to_re_read_models`; silent when a fetch adds nothing). It was offered inside the alias PR rather than alone because on upstream's tree without #140 the frame had no listener. Branch retired.

Status detail (migrated from the table): ✅ **merged** — their PR #882 (commit 3, the models frame), merged 2026-09-02 (merge `ab176ed7`); the code is in HEAD — ✅ came home in upfold0905 (2026-09-05)
