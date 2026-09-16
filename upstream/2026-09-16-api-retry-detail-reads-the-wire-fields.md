---
title: api_retry detail reads the wire's attempt and error string
status: candidate
where: kernel/sdk_backend.py: the api_retry branch of _on_message; tests/test_sdk_backend.py ApiRetryState
added: 2026-09-16
pr:
tier: fix
offered:
closed:
---

The installed CLI's SDKAPIRetryMessage carries attempt, max_retries, retry_delay_ms, error_status (null for a
connection error) and error as a category string (overloaded, rate_limit, authentication_failed, server_error,
unknown). Upstream's api_retry branch read neither attempt nor the string error, so the detail showed a local tally
and no category; five of its own SDK-gated tests were red whenever the SDK was importable. The fix reads the wire's
fields with a fails-before test; the re-pinned tests pass on upstream's code too. Found during the fork's
2026-09-16 pull-in review (PR 755 on the fork).
