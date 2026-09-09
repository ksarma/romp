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

FOLDED 2026-09-09 (slice 3 of the inbound fold): the fork converged on the landed per-landing _models_changed() and retired its own gate-flip counter (has_live, gate_closings, the two door reads) with the 22 tests that pinned it; tests/test_codex_models_route.py's OneFrameOnRevive class pins that a revive sends exactly one models frame per app, in two executed tests, test_reviving_a_dead_codex_session_sends_exactly_one_frame_per_picker_app (a fake backend) and test_the_real_backends_revive_sends_exactly_one_frame_per_picker_app (the real clientless CodexBackend through the real door); upstream's tests/test_codex_models_frame.py pins the set of apps per landing.
