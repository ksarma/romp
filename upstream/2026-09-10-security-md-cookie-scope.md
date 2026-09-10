---
title: SECURITY.md: the token cookie is accepted only from an allowed Origin because cookies are scoped by host, not by port (RFC 6265 section 8.5); why the drain arm takes only an explicit token; one executing pin for the own-loopback clause
status: offered
where: SECURITY.md (the trust-model paragraph above 'What is already hardened'), tests/test_kernel_auth_hardening.py (CookieDoesNotBypassOrigin, one test)
added: 2026-09-10
pr: 1
tier: docs
offered: their PR #1280
closed:
---
Divergence-audit row 46 (fork commit da467ecb via fork PR 1), re-derived against the project's _origin_ok/_authorize/_write_token_ok at the tip; adds the no-Origin clause the fork text lacked.
