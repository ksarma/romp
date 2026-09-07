---
title: Spend tokens fold from the result's `modelUsage` (cumulative per CLI process, subagent-inclusive, summed across models per field) instead of the per-turn, main-loop-only `usage` dict, which under-counted a 2.6M-token turn as 6,346 tokens on Claude Code 2.1.261 (the CLI's own schema text says to prefer `modelUsage` for accounting); `usage` stays the fallback where `modelUsage` is missing, recorded per turn (never diffed as cumulative) and announced as a problem naming the cause: once per kernel life for an SDK without `model_usage` shadowing the venv's (a host-level cause, so the line names no session and lives on the backend's flag), once per session for a CLI omitting `modelUsage`
status: candidate
where: `kernel/sdk_backend.py` (`_MODEL_USAGE_KEYS`, `model_usage_totals`, `result_token_totals`, the token fold in the ResultMessage settle branch); tests in `tests/test_sdk_backend.py` (`SpendRecord`, the modelUsage tests)
added: 2026-09-06
pr:
tier:
offered:
closed:
---
Fork `41b2303c` (2026-09-05); the SDK cause's once flag moved to the backend on 2026-09-06 (per session it was one card per live session plus one per dormant revive). Upstream's settle diffs `usage` the same way; the dollars were already right there (the per-turn delta fold).

Status detail (migrated from the table): candidate
