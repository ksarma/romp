---
title: `tests/romp.bats` leaks 6 temp dirs per run: `bin/romp`'s detached picker-check on the resume path double-forks the REAL postal service, which mints a `serve-token` under the fixture home after teardown's `rm -rf`; the suite's curl mock also flakes on SIGPIPE
status: approved
where: leak fix: fork PR #233 (branch `tmpleak`, merged 2026-09-06 as `54bd3106`), commit `e98c8c79` (the detached call honours `ROMP_POSTAL_BIN` like the mail and refresh paths, and romp.bats stands in for the service). Their #944's exit-time sweep cannot catch it (the write happens in a detached process after cleanup). SIGPIPE flake: the curl mock's stdin drain, fork main `3190e9d6` (2026-09-04, the `romp new --in` commit; not `835a0a4a`, the Codex-spawn `--env` refusal, which only reuses `_stub_curl`); upstream's romp.bats has no drain
added: 2026-09-06
pr: 233
tier: tests-only
offered:
closed:
---
`tests-only`; its own port now that fork PR #233 has landed — not a fold into their #944

Status detail (migrated from the table): candidate

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier tests-only — offered with the child-process hygiene entry (`tmp-hygiene-child-processes`). Pointer fixes today: fork PR #233 merged 2026-09-06 (`54bd3106`); the SIGPIPE drain came in `3190e9d6`, not `835a0a4a`).
