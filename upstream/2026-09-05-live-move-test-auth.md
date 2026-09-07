---
title: The live session-move test's hermetic auth borrows the user's own `apiKeyHelper` command (from `$CLAUDE_CONFIG_DIR/settings.json`, default `~/.claude/settings.json`) instead of reading a key from a `~/.config` cache file; `_user_api_key_helper(config_dir=None)` with its own non-live tests; the skip reason names both accepted auth sources
status: merged
where: fork branch `livetest-auth` (PR #190): `tests/test_session_move_live.py`
added: 2026-09-05
pr:
tier: tests-only
offered: their PR #946
closed: 2026-09-06
---
Upstream carries the cache-reading fallback via their #888 (the sessmove fold): a machine-specific path no other box has, and one that now violates the no-key-on-disk rule here. The helper borrow copies a COMMAND, never a key, and works wherever Claude Code itself is configured. Live run verified on our box 2026-09-05 (17 s).

Status detail (migrated from the table): **offered** — their PR #946 (2026-09-06), label `tests-only`; re-verified at tip: upstream has no cache-file fallback (the row's premise), so the offer is the borrow plus a slug assertion fix

MERGED 2026-09-06T19:49Z as their PR #946 (merge `a50831b1`), as offered. Two test tightenings from the review ride the tests-only follow-ups bundle (`batch12-review-tests-only-followups`).
