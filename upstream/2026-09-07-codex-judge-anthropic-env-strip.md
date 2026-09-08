---
title: Codex judge children get every `ANTHROPIC_*` variable stripped, not only `ANTHROPIC_API_KEY`
status: offered
where: fork PR #229 (`keyfree`, merge `988d010f`), introduced by its commit `74d5d68e` (2026-09-05): `kernel/judge.py`, the Codex child's env build drops every key starting `ANTHROPIC_` where upstream drops only `ANTHROPIC_API_KEY`; carve from the key-free branch (`78a05f07` / `0c621352` are the keyswap-refusal commits, not this strip)
added: 2026-09-07
pr: 229
tier: fix
offered: their PR #966
closed:
---
The tier-1 piece of the API-key management bucket (`api-key-management`) that is offerable without the maintainer conversation: a Codex-engine judge child is launched with every `ANTHROPIC_*` variable removed, so an Anthropic key in the kernel's environment or `service.env` (and any `ANTHROPIC_BASE_URL` / auth token beside it) never reaches another vendor's process. Upstream strips the one key. If the `ANTHROPIC_LP_API_KEY` catalog rung ever travels it must carry this strip.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). Upstream's open #932 (CONFLICTING as of 2026-09-07) adds a Codex bypass on nearby hunks of `kernel/judge.py`.

OFFERED 2026-09-07: offered upstream as their PR #966 (2026-09-07, label fix, head f094e3fd).
