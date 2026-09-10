---
title: Tests: the live-order stability check feeds the second liveness read newest-first (so a reader that skipped the shared order fails it), and the session-order module docstring paraphrases the user
status: merged
where: tests/test_kernel.py (test_live_order_is_stable_under_activity), tests/test_kernel_order.py (module docstring)
added: 2026-09-10
pr:
tier: docs
offered: their PR #1265
closed: 2026-09-10
---
Two nits from the review of their #1240 (our ready no-strip follow-up). Tests only; filed directly from the upstream base.
