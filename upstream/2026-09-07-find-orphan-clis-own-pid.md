---
title: `find_orphan_clis` treats the current kernel's own children as live by pid, not only by the parent's command line
status: approved
where: not built; from the maintainer's review comment on their PR #941 (2026-09-06): `kernel/sdk_backend.py` `find_orphan_clis(ps_lines, lastsids)`; the caller already passes `os.getpid()` to `find_session_cli`
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
After #941 the kernel's own children are protected only when `_is_kernel_cmd` recognises the parent's launch spelling; the old `ppid != 1` test protected them unconditionally. Pass `os.getpid()` and treat `ppid == own pid` as live, with a test.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). #941's head `509c3f11` is not on fork main; build off upstream/main. Fork side, open PRs #272, #275 and #258 touch `kernel/sdk_backend.py`.
