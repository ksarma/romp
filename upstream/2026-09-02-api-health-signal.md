---
title: The API-health signal: `GET /api-health` (authed). Per-(auth label, model family) attempt / response / give-up counts over 60/300/900 s windows; `ok`s deduped (one per `AssistantMessage.message_id`); main thread only, with the exclusion declared in the payload; `rate429` named as an ATTEMPT share beside distinct sessions/turns retrying; give-ups counted ungated from `ResultMessage.api_error_status` (paired with the error-stamped assistant frame that precedes it); a thrash/degraded/recovering/unknown state derived AT READ TIME from the ring and the last persisted `(state, stateSince)` (no tick; hysteresis = enter/exit thresholds plus a 120 s hold on two windows, backtested against the 2026-09-01 shape; every bucket comes back `unknown` at a restart) with the per-bucket state and the transitions tail persisted atomically in a bounded `STATE/api-health.json`; `romp api-health`; two one-shot log diagnostics (the first `api_retry` frame's keys, the first sighting of each unhandled `SystemMessage` subtype)
status: candidate
where: branch `apihealth`: `kernel/sdk_backend.py` (`ApiHealth`, `api_health_state`, `api_health_counts`, `api_health_auth_label`, the `_ah_note_*` hooks in `_on_message`), `kernel/kernel.py` (`/api-health` after the gate, boot identity from `/version`'s globals), `bin/romp` `api-health`; tests `tests/test_api_health.py`, `tests/test_kernel_auth_hardening.py::ApiHealthRouteGate`, `tests/romp-api-health.bats`; `docs/reference.md` "The API-health signal"
added: 2026-09-02
pr:
tier:
offered:
closed:
---
Every symbol it hooks exists upstream (`SdkSession._on_message`'s api_retry / Assistant / Result branches, `_note_auth_source`, `work_api_key`, `acct_digest`, `_authorize`, `_BOOT_ID`/`_STARTED`), so the change ports as-is; no in-kernel consumer, no UI. Fork-specific, to flag in the body: the auth label is a per-install SALTED digest (`STATE/api-health-salt`; an empty file means unsalted). Upstream may prefer plain digests like its account digest, and the salt file is the one switch. Vocabulary: the JSON's top-level roll-up is `overall`, not the design note's `fleet`, to honour the fork's word rule. The note's `derivedAt`/`tickS`/`retryPause`/`tokens` fields are deliberately not shipped (state is read-time, the retry-pause consumer is a follow-up, token sums were not in the reviewed scope). Thresholds come from one incident on one box; re-check against the next before trusting them.

Status detail (migrated from the table): candidate
