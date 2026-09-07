---
title: Test fixtures leaked under /tmp: the suite’s `mkdtemp` state roots and per-test scratch were never removed (about 1.9 million directories accumulated on one dev box from repeated sweeps; a shell glob over them OOM-killed the kernel)
status: offered
where: fork PR #201 (`romp-tmpclean`, merged 2026-09-06); upstream’s `tests/conftest.py` leaks the same `mkdtemp`
added: 2026-09-06
pr: 201
tier: tests-only
offered: their PR #944
closed:
---
OFFERED 2026-09-06 (branch `tmpclean`, `e95ce457` off tip `2b9db2be`): cleanup ported onto upstream’s conftest and tests/__init__.py; proven by two suite runs under a private TMPDIR with no fixture growth; scaffold CI green (since-closed fork #207).

Status detail (migrated from the table): **offered** — their PR #944 (2026-09-06), label `tests-only`
