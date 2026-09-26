---
title: tests/romp-manager-origin.bats's teardown waits for the killed manager to exit before it removes the test directory, through a shared helper with its own pins
status: candidate
where: tests/stop-then-remove.bash (new: stop_then_remove, TERM then a bounded poll for the exit, KILL at the bound, then rm -rf), tests/stop-then-remove.bats (new: the stand-in pins and the teardown's source pin), tests/romp-manager-origin.bats (teardown), tests/README.md (the bats cleanup paragraph), upstream/2026-09-26-origin-bats-teardown-wait.md (this entry)
added: 2026-09-26
pr: 920
tier: docs
offered:
closed:
---
The project's copy of tests/romp-manager-origin.bats has the same teardown as the fork had: it kills the manager and removes the test directory on the next line. The manager's TERM handler appends restart-audit.jsonl under the state root inside that directory before it exits, so on a slow runner the teardown reds with rm's 'Directory not empty' after every assertion passed (fork PR 913's CI, 2026-09-25; the re-run passed), and a write that lands after the removal recreates the directory in the temp dir. The fix is tests only, so docs tier. The project's tests/romp-manager-ensure.bats and tests/romp.bats carry the same shape and are not changed here.
