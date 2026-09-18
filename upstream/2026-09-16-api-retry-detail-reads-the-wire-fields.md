---
title: api_retry detail reads the wire's attempt and error string
status: approved
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
and no category. Fixer round 9 of the pull-in found five SDK-gated cases in tests/test_sdk_backend.py red whenever
the SDK was importable; one was red for this defect (ApiRetryState's detail case). The other four were test-side, by
round 9's own account: two stale pins from before the code they read moved (OptionsAssembly's ultracode seed and
FastModeReportedState's refused ask, the latter a fork-only class), a fake whose init streamed at connect
(ReconnectReconcilesInflight) and a class with no current event loop for the settle to schedule on (ApiRetryState's
bare-payload case). The fix reads the wire's fields with a fails-before test on the installed CLI's frame; the
re-pinned tests pass on upstream's code too. Found during the fork's 2026-09-16 pull-in review (PR 755 on the fork).

2026-09-18: approved for offer by the user (batch 1 of the 2026-09-18 plan).
