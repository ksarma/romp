---
title: API health cell in the dashboard's bottom bar: one dot and one word beside the spend cell (ok; rate limited, overloaded, offline or errors with the count of sessions waiting; paused with the reason), built from a latched per-session API-error read, the live retrying state and the retry-pause file, pushed as one apiHealth frame on change
status: candidate
where: fork branch apihealth (kernel/kernel.py: _api_last_failed, _api_error_scan(user_clears), _apih_class, _api_health_frame, _api_health_push, _apih_resend, _LANDING_APIH_JS, the #rail-api cell and its CSS in _landing; tests/test_api_health_rail.py, tests/test_api_error_tail.py ApiLastFailedLatch, tests/test_kernel_pane_rail.py ApiHealthCell; docs/guide.md, docs/reference.md)
added: 2026-09-07
pr:
tier: feature
offered:
closed:
---
Pure feature in code upstream ships too (the kernel's shell page, the retry-pause file, the api_retry storm state); no fork-specific content. Every field of the frame moves on one named event (a retry frame, an isApiErrorMessage record, fresh assistant output, a pause set or lifted, a session leaving the roster) and never on a clock; two computes over the same world at different times serialize identically and send once. One behavior change outside the cell: _auto_pause_on_limit records reason limit at the pause event. Deferred: the VS Code strip twin and the phone's Usage-modal section.
