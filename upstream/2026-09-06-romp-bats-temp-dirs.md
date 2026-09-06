---
title: `tests/romp.bats` leaks 6 temp dirs per run: `bin/romp`'s detached picker-check on the resume path double-forks the REAL postal service, which mints a `serve-token` under the fixture home after teardown's `rm -rf`; the suite's curl mock also flakes on SIGPIPE
status: candidate
where: leak fix: fork branch `tmpleak`, commit `e98c8c79` (the detached call honours `ROMP_POSTAL_BIN` like the mail and refresh paths, and romp.bats stands in for the service; fork PR pending, 2026-09-06). Their #944's exit-time sweep cannot catch it (the write happens in a detached process after cleanup). SIGPIPE flake: fork main `835a0a4a` (2026-09-04); still open upstream
added: 2026-09-06
pr:
tier:
offered:
closed:
---
`tests-only`; its own port once the fork PR lands — not a fold into #944

Status detail (migrated from the table): candidate
