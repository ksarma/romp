---
title: GET /models names why the Codex model list is empty; the backend caches only a non-empty catalog
status: merged
where: upstream-only follow-up on fork branch `codex-models-error-offer` (commit `ab07bd64` on their main `3e4398a3`): `kernel/codex_backend.py` `model_catalog()` caches only a non-empty list, records and logs each empty reason once, `model_catalog_error()`; `kernel/kernel.py` GET /models codex section carries an always-present `error` string (gate unchanged); `tests/test_codex_backend.py`; `tests/test_codex_models_route.py` new. The fork carries the same idea from #406 with a different route shape; the fold reconciles
added: 2026-09-09
pr:
tier: fix
offered: their PR #1167
closed: 2026-09-09
---
Third of the four pieces fork #406 owed upstream: a Codex model picker that opens blank with no reason because the backend cached an empty first page for the process and the route swallowed every failure. The `error` field is the value the later picker reason row (piece 4, feature) will read; the models frame on the first Codex session (piece 3, fix) stays separate.
