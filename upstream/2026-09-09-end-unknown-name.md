---
title: POST /end, /interrupt and /send refuse a name no session answers to with a 404 instead of minting a phantom sid
status: candidate
where: `kernel/kernel.py` `_unknown_session_refusal(sid, who)` after `_sid_of`, asked by the /send route and by the /interrupt and /end route after their remote forward; `bin/romp` send/interrupt/end block reads the HTTP status off the response (no more curl -f) and prints the refusal reason, plus per-verb -h/--help; `tests/test_kernel_headless_ops.py` UnknownSessionRefused (new class; the existing route tests register their sids), `tests/romp-headless.bats` (status-aware fake kernel, two new tests), `tests/test_post_push_coalescing.py` (its probe session is registered)
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
`_sid_of` hands back its input unchanged when nothing matches, so a typo reached the backends as a phantom sid: /end killed it and `_confirmed_ended`, finding nothing listed, certified the death, so `romp end <typo>` printed a bare ok while the real session ran on; /send handed the phantom to the tmux backend and folded its refusal into ok:true. A peer handoff flow that trusted the ok had to re-check the roster. The gate is the fork-comment door's (registered or live), asked after the remote forward; the CLI used to swallow every 4xx into "kernel not reachable", and `romp end --help` POSTed a session named --help.
