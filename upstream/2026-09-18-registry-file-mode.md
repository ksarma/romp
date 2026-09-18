---
title: The session registry and the parked-ops mirror are created owner-only, with no readable window
status: candidate
where: kernel/sdk_backend.py (write_reg: the temp is opened O_EXCL at 0600), kernel/kernel.py (_atomic_write: a mode is the temp's creation mode, not a chmod after the write; _save_pending_ops and the alias migration's reg rewrite pass mode=0o600)
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Upstream has the same writers byte for byte: write_reg publishes sdk/<sid>.json through a write_text temp at the umask mode (0644, or 0664 under umask 002) and _save_pending_ops mirrors a parked ("env", {...}) op through _atomic_write with no mode, so a per-session env value under a token-shaped name sits in both files at that mode, while the sibling writer of the same values (flag_settings_path) is 0600. The temp is now created at 0600 and os.replace carries the mode, so an older file tightens on its next write; _atomic_write creates a mode-bearing temp at the mode instead of chmod-ing it after the write. Every reader is the same uid. A mitigation behind the 0700 state root, not a fix for the value living in a file. Found in PR 776's review round (kernel-1, extra5-2) and deferred to its own fix.
