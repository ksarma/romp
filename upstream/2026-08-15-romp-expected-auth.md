---
title: ROMP_EXPECTED_AUTH: a box declares its intended auth side, so apiKeyHelper boxes stop ringing the per-init "launched for the login" false alarm (the never-silent mismatch check inverts to flag the CONTRADICTING landing), and the all-keyed telemetry silence becomes honest surfaces (once-per-episode refresh_usage line, telemetryUnavailable + rail hover, authLive Billing row, persisted apiKeyAuth)
status: merged
where: fork branch `apikeyauth` (feature `b5669326` + review fixes)
added: 2026-08-15
pr:
tier:
offered: their PR #577
closed: 2026-08-23
---
MERGED as-is (head is an ancestor of their main, verified same day). Branch retired. OFFERED 2026-08-23 (branch `expected-auth`, `87fca5a4` off tip `147678b1`): Status-interface line inserted surgically without fork churn; the #563 usage-poll interaction explained in the body; review clean, scaffold CI green (since-closed fork #107). Upstream ships the same `_note_auth_source` comparison and the same `api_key_auth` gates, so the permanent false alarm and the silent all-keyed dead-end exist there verbatim. Undeclared behavior is byte-identical; validated on the fork first.

Status detail (migrated from the table): ✅ **merged** — their PR #577, merged as-is 2026-08-23 (merge `22343b2d`)
