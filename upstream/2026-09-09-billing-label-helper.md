---
title: Reference: the Billing row's four readings, as render.ts renders them, pinned (the kernel, judge and UI parts of fork PR #410 are superseded by their #1128 and #1147)
status: merged
where: kernel/kernel.py (Sessions.live merge, build_session Billing fields, _bills_login, _auth_key_present, _unpicked_default, _auth_avail, the judge's _UNPICKED_AUTH_FN wire), kernel/sdk_backend.py (read_sdk_defaults cache, unpicked_auth, seeded_auth, new_session_auth, spawn's seed, effective_auth, default_auth, snapshot, _live_row, _note_auth_source), kernel/judge.py (_judge_auth, _unpicked_auth), ui/webview/billing-label.ts (new; pickerBillingRow), ui/webview/render.ts (Billing row, tab-menu Billing item, picker Billing row, Status.authPicked), docs/reference.md; tests: tests/test_expected_auth.py, tests/test_judge_auth_billing.py, tests/test_retry_pause_autoresume.py, tests/test_session_auth.py, tests/test_reference_billing_label.py (new), ui/webview/billing-label.test.ts (new), ui/webview/auth-selector.test.ts
added: 2026-09-09
pr:
tier: docs
offered: their PR #1182
closed: 2026-09-09
---
The tab hover Billing row said Login for every session on a box whose sessions authenticate through Claude Code apiKeyHelper. Three causes: the kernel live merge never forwarded authLive from the SDK row, so every kernel reader of the CLI report saw ""; the unpicked default read the key romp holds, which a helper box never does; and the row worded a seeded default the CLI disagreed with as a pick. Fix: the merge forwards authLive and authPicked; the unpicked default falls to ROMP_EXPECTED_AUTH when it speaks; the row shows the CLI reported side plainly and warns only for an explicit pick the CLI contradicted; the first init report persists so a restart never blanks it.

Verified 2026-09-09 against upstream tip 67773fb2: all three causes are fixed or superseded there. Their #1147 merges authLive into Sessions.live() and adds the unavailable and fell arms; their #1128 retires romp's own key providers, so an unpicked reader on a helper box already says key; the persist-first-report change inverts a test upstream pins on purpose, and _bills_login is fork-only. The fork's kernel, judge and UI changes are therefore not ported. What survived was one stale sentence in docs/reference.md that misdescribed the Billing row against upstream's own render.ts, offered as a docs PR with a test that reads the reference and pins the rendered forms.
