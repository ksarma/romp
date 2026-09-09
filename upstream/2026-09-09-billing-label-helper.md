---
title: Billing label: a helper-authenticated session reads API key, not login
status: candidate
where: kernel/kernel.py (Sessions.live merge, build_session Billing fields, _bills_login, _auth_key_present, _declared_default_auth, _auth_avail), kernel/sdk_backend.py (unpicked_auth, effective_auth, default_auth, declared_auth, snapshot, _live_row, _note_auth_source), ui/webview/billing-label.ts (new), ui/webview/render.ts (Billing row, tab-menu Billing item, picker written-out choice, Status.authPicked), docs/reference.md; tests: tests/test_expected_auth.py, tests/test_retry_pause_autoresume.py, ui/webview/billing-label.test.ts (new), ui/webview/auth-selector.test.ts
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
The tab hover Billing row said Login for every session on a box whose sessions authenticate through Claude Code apiKeyHelper. Three causes: the kernel live merge never forwarded authLive from the SDK row, so every kernel reader of the CLI report saw ""; the unpicked default read the key romp holds, which a helper box never does; and the row worded a seeded default the CLI disagreed with as a pick. Fix: the merge forwards authLive and authPicked; the unpicked default falls to ROMP_EXPECTED_AUTH when it speaks; the row shows the CLI reported side plainly and warns only for an explicit pick the CLI contradicted; the first init report persists so a restart never blanks it.
