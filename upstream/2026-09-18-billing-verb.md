---
title: romp billing: a session's billing from the shell
status: candidate
where: bin/romp (`billing`), kernel/kernel.py (POST and GET /billing, _billing_request, _billing_read, _billing_default, _billing_far_answer, _park_reason, _drop_parked_auth, the drain's auth arm), kernel/sdk_backend.py (set_auth chip= and bounded= and its never-landed branch, set_auth_followers, follow_default_auth, _follow_default_unlanded, _follow_default's hand-back, _connect_landed's picked re-ask, _default_label, auth_apply_outlook, turn_open, billing_view, explicit_default_pick, _mirror_auth), cli/perf_public.py (HTTP_ROUTES, the fork-only shared copy of the register that tests/test_perf_export.py holds equal to the kernel's), docs/reference.md, tests/test_billing_route.py, tests/test_cli_billing_kernel.py, tests/test_headless_verbs_help.py (billing joins the census; the no-kernel misuse cases; fork-only), tests/test_sdk_backend.py (the request_reconnect caller pin gains _follow_default_unlanded), tests/fixtures/fake_claude.py
added: 2026-09-18
pr:
tier: feature
offered:
closed:
---
Until this only the dashboard could change which account a session bills. `romp billing <session> <pick>` posts the same setAuth op the Billing menu posts (a name, a sid or an attached host's session, forwarded as /end forwards), so the session reconnects at its next quiet moment; `--now` cuts the turn in flight after the pick is recorded, so the cut turn's settle arms the reconnect (no new arm path; a compaction is refused, not cut); `default` clears the session's own pick, a value the dashboard has no op for, through the follower walk's per-session move; `--all-following <pick>` writes a pick on every live follower of the machine default through that walk, with no /auth chip; the bare verb prints the launched side, the pick and the machine default, for a dormant session from its reg. The CLI and the kernel routes are upstream's code; the lab test runs the real bin/romp against a hermetic kernel with the fake CLI and skips without the SDK venv.
