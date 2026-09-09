---
title: Codex: a session going live sends the models frame, so an open dashboard learns the model list without a reload
status: merged
where: upstream-only follow-up on fork branch `codex-frame-doors-offer` (commit `dd1f0aab` on their main `dc1b4554`): `kernel/kernel.py` `_create_codex_session_inner` and `_revive_session_inner` call `_models_changed()` once the backend landed the row (every landing, not the exact closed-to-open flip; no gate counter); `tests/test_codex_models_frame.py` new (eight tests over the real doors). The fork carries a counter-based version from #406; the fold reconciles
added: 2026-09-09
pr:
tier: fix
offered: their PR #1169
closed: 2026-09-09
---
Fourth Codex piece owed upstream after #406: a dashboard loaded before the first Codex session never learned the model list until reload because neither door sent the models frame. The per-landing rule is argued in the body against the exact flip (a door cannot see the flip without the backend counting closings). Remaining piece: the picker reason row (feature).
