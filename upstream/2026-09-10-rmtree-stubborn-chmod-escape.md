---
title: Test-root sweep: the chmod retry re-modes only directories inside the tombstone, never its parent or a symlink's target
status: offered
where: kernel/sdk_backend.py (_rmtree_stubborn onexc handler), tests/test_test_root_sweep.py (four DeadOwnerSweep tests), tests/README.md (hermetic-temp paragraph)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1356
closed:
---
