---
title: Declaration-gated env-file credential warning: a boot rings on a credential-shaped `service.env` line that contradicts the declared auth (`=login` arm sure, `=key` arm a design point)
status: approved
where: fork PR #229 (`keyfree`, merge `988d010f`) and fold commits `78a05f07` / `0c621352` (the warning, runtime strings): the boot `key_source_verdict`'s declaration-gated warning on credential-shaped `service.env` lines (`_warn_credential_lines_in_env_file` speaks in file mode; see the keyswap divergence entry); carve from the key-free branch without the file-mode refusal or the no-keys docs stance
added: 2026-09-07
pr: 229
tier: feature
offered:
closed:
---
The tier-2 piece of the API-key management bucket (`api-key-management`) that is offerable without the maintainer conversation: when the installation declares how it authenticates (`ROMP_EXPECTED_AUTH`), a boot rings on a credential-shaped line in `service.env` that contradicts the declaration. The `=login` arm (a key line present while login is declared) is the sure part; the `=key` arm is a body design point, since upstream's model keeps the key in that file.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier feature). Carve out of #229 without the file-mode refusal or the no-keys docs stance (neither is offerable); upstream's open #932 (CONFLICTING as of 2026-09-07) also edits the credential-read paths.
