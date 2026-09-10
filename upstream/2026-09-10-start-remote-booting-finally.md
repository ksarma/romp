---
title: Tunnel rows: a Start whose step raises releases the row's hold through _fail and re-raises (except BaseException around _start_remote's body), so the row is not frozen at starting, with its recovery counter, until a kernel restart
status: merged
where: kernel/kernel.py (_start_remote), tests/test_kernel_remote_start.py (StartRemote, five tests)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1268
closed: 2026-09-10
---
Pre-existing gap recorded in the review of their #1239 (our Start-hold counter offer), verified at the tip. Filed directly from the upstream base.
