---
title: Tests: the raw-copytree guard reads each test module's call tree with ast (nested calls, aliased imports, a name-bound dist) over a text-prefiltered module set, and tests/README.md records the copy_dist rule
status: offered
where: tests/test_dist_copy_staging.py (raw_dist_copies, the guard, a twelve-snippet case), tests/README.md
added: 2026-09-10
pr:
tier: docs
offered: their PR #1266
closed:
---
Two nits from the review of their #1238 (our dist copy staging-race offer). Tests and README only; filed directly from the upstream base.
