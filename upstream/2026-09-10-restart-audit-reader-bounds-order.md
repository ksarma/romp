---
title: Restart audit: a live quiet park survives an aged verdict or note, a stray SIGTERM does not consume it, and the manager's never-throws test runs its catch
status: offered
where: docs/reference.md kernel/kernel.py tests/manager-exit-attribution.test.js tests/test_restart_cuts.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1302
closed:
---
From the maintainer's post-merge record on their #1286 (items 1 to 3): the reader classifies verdicts and manager notes before its bounds so an aged row no longer hides a live quiet park; a stray SIGTERM with a quiet park on record does not stamp the park as consumed (quiet-park-auditt-stamp-on-stray-sigterm); the manager's never-throws test puts a regular file in the root's path so auditSigterm's catch runs (manager-exit-test-never-throws-path). The stderr-guard rider was dropped: the maintainer's review commit f36ddba8 carries it.
