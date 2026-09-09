---
title: Codex backend: several queued sends land one text block each, and each retire takes back one echo per send
status: merged
where: upstream-only follow-up to the Codex parity fix, on fork branch `codex-echo-blocks-offer` (commit `bda83b1e` on their main `557a2430`): `kernel/codex_events.py` `_user_input_texts` writes one block per input; `kernel/codex_backend.py` `_rec_texts`/`_append` retire one echo per landed block and `send()` takes back only its own echo on the dead path; `plans/codex-backend.md`; tests in test_codex_events_golden, test_codex_backend, test_codex_echo_merge. The fork carries the same change from #406; the fold reconciles
added: 2026-09-09
pr:
tier: fix
offered: their PR #1166
closed: 2026-09-09
---
The second of the four pieces fork #406 owed upstream after the parity fix: a turn started from several queued sends produced one joined user record, so no echo retired. Red-first: seven tests. Remaining pieces: the /models empty-list reason (fix), the models frame on the first Codex session (fix), the picker reason row (feature).
