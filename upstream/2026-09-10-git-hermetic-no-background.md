---
title: Tests: the bats git floor forbids background maintenance in fixture repos and their bare remotes, so a teardown's rm -rf never races a detached git child
status: offered
where: tests/README.md tests/git-hermetic.bash tests/git-hermetic.bats tests/pre-push-hook.bats
added: 2026-09-10
pr:
tier: docs
offered: their PR #1329
closed:
---
Residual of the maintainer's #1312 record after the owner's #1314/#1315 moved the python fixtures onto tests/git_fixture.py: the bats floor's git_hermetic exports the five no-background keys as GIT_CONFIG_COUNT pairs, pre-push-hook.bats joins the floor, git-hermetic.bats pins the keys and a traced commit, README names the pairs.
