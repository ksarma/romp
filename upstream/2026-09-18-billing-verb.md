---
title: romp billing: a session's billing from the shell
status: candidate
where: bin/romp (`billing`), kernel/kernel.py (POST and GET /billing, _billing_request, _billing_read), kernel/sdk_backend.py (set_auth chip=, set_auth_followers, follow_default_auth, _reconnect_follower, auth_apply_outlook, billing_view), docs/reference.md, tests/test_billing_route.py, tests/test_cli_billing_kernel.py, tests/fixtures/fake_claude.py
added: 2026-09-18
pr:
tier: feature
offered:
closed:
---
Until this only the dashboard could change which account a session bills. `romp billing <session> <pick>` posts the same setAuth op the Billing menu posts (a name, a sid or an attached host's session, forwarded as /end forwards), so the session reconnects at its next quiet moment; `--now` cuts the turn in flight after the pick is recorded, so the cut turn's settle arms the reconnect (no new arm path; a compaction is refused, not cut); `default` clears the session's own pick, a value the dashboard has no op for, through the follower walk's per-session move; `--all-following <pick>` writes a pick on every live follower of the machine default through that walk, with no /auth chip; the bare verb prints the launched side, the pick and the machine default, for a dormant session from its reg. The CLI and the kernel routes are upstream's code; the lab test runs the real bin/romp against a hermetic kernel with the fake CLI and skips without the SDK venv.
