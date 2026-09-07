---
title: A safeguards refusal classifies as transient — the auto-retry re-sends the refused prompt forever (one refused prompt drew 12 injected retries in ~6 minutes)
status: merged
where: `refusalretry` branch
added: 2026-08-15
pr:
tier:
offered: their PR #540
closed: 2026-08-22
---
MERGED as-is 2026-08-22 (head is an ancestor of their main, verified in the fold). Branch retired. OFFERED 2026-08-20 (branch `refusal-retry`, two commits `f460dfe5`+`b8679d2b` off tip `f3ec1297`: kernel class + separately-droppable dashboard mirror): red-first 18 pytest + 16 node failures on the unfixed base, full suites green after; review clean, scaffold CI green (since-closed fork #94). Upstream ships the same `_api_error` / `_fire_api_retry` / `_auto_retry_tick`, so the same storm: a classifier refusal writes an assistant error record (`invalid_request`, "safeguards flagged…") that falls through as transient, and each refusal's NEW record uuid mints a new retry episode — the once-per-episode gate cannot terminate a deterministic error, and in fallback configurations each retry manufactures another model downgrade. Fix adds a fifth on-you class. Detection is event-based with the CLI's wording as a CO-EQUAL signature, both required by the evidence: the system `model_refusal_no_fallback`/`_fallback` record links to its episode by parentUuid (both it and the error carry the refused user message's uuid; `refusedUserMessageUuid` observed diverging from the episode's parent in 2 of 13 records, so it is NOT the link), and the CLI omits the record for some refusal errors (observed in the same storm that produced linked ones), so the text signature is not a legacy fallback. Never auto-retried (manual Retry keeps the override contract); the card floors to needs-you; every retry/countdown surface skips it and names the real fix (rewrite the prompt or drop the thread). Pure fix, no fork-specific content; fixtures synthetic.

Status detail (migrated from the table): ✅ **merged** — their PR #540, merged as-is 2026-08-22 (merge `c0c82f1f`); came home in the 2026-08-22 tip fold (`upfold0823`)
