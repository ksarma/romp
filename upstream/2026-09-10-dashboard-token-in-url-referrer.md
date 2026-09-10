---
title: The dashboard drops ?token= from its address once the cookie is set (the head script's replaceState), and every page the kernel serves carries Referrer-Policy: same-origin, so SECURITY.md's claim that a cross-site page cannot obtain the token holds by construction
status: offered
where: kernel/kernel.py (_landing head script, _send), SECURITY.md, tests/test_kernel_auth_hardening.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1297
closed:
---
From the maintainer's post-merge record on their #1280 (item 2); same-origin rather than no-referrer because their open #1219 reads the Referer on same-origin requests.
