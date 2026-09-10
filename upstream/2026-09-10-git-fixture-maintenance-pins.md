---
title: Tests: the trace pins match git's maintenance spawn line, not a bare substring; a missing key is named; the bare clones are pinned
status: offered
where: tests/git_fixture.py tests/test_git_fixture.py tests/test_github_repo.py tests/test_restart_classifier.py
added: 2026-09-10
pr:
tier: docs
offered: their PR #1327
closed:
---
From the maintainer's post-merge records on the owner's #1314 and #1315: the bare-substring maintenance pins become the spawn-line form, the restart-classifier config read takes --default so a missing key is named, the two bare clones in test_github_repo get a pin, and forbid_background's docstring says a linked worktree shares its main repository's config.
