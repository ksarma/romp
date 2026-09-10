---
title: Held input echoes: a slash or skill command's echo retires on the transcript's command wrapper record (session_backend.command_text_key, a second key rule applied by the kernel prune, the thread's held count, the backend's boot scan and the fed-copy pairing)
status: merged
where: kernel/session_backend.py (command_text_key), kernel/kernel.py (_landed, _merge_live_atoms prune, qids_for_landing), kernel/sdk_backend.py (_text_landed, _command_invocation), docs/read-side.md, tests/test_kernel_slash_echo_retire.py and three sibling modules
added: 2026-09-10
pr:
tier: fix
offered: their PR #1261
closed: 2026-09-10
---
Live defect the user hit on his own dashboard (2026-09-10 00:15Z): a slash send's echo never matched the wrapper record the CLI writes, so the sending bubble stayed forever and a restart ran the command twice. Upstream-native; filed directly from the upstream base.
