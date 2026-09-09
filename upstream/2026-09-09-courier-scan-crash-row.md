---
title: Courier: a raise in one session's scan is that session's pass-crash row, not the tier's
status: offered
where: upstream branch courier-scan-offer, re-derived from the courier-evidence-gate entry's residual (fork PR #355): `kernel/judge.py` `run_courier` (the settle, the episode floor and the segment walk under the per-session try that already caught the parse and store reads; the half-walked session's queued rows dropped; the session left out of `_COURIER_SEEN`); tests `tests/test_courier_skip.py` `CourierScanCrash` (five cases)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1184
closed:
---
The residual of the courier-evidence-gate entry after their #1158, #1161 and #1170 built upstream's own change gate: a raise in one session's settle, episode floor or segment walk escaped `run_courier`, so no session's delegate was placed that pass, the four tiers after the courier did not run, and no judge-errors row was filed. The scan now runs under the same per-session boundary as the parse and the store read: one pass-crash row for that session, its unfinished walk's rows dropped, the session scanned again next pass, the loop moving on. The gate itself is resolved upstream in its own shape; the fork's `_gated` shape is not offered.
