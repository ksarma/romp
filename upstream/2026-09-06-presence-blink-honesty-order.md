---
title: `tests/test_postal_relay_honesty.py::PresenceBlinkHonesty::test_disk_twin_carries_the_cache_across_a_bus_restart` depends on module order: red under xdist (`-n 8`) and when selected alone with `-k`, green with its module run in order — the one recurring full-sweep failure on every batch-12 port
status: offered
where: upstream code (the fork carries the same module); surfaced by the batch-12 sweeps (2026-09-06); not yet built
added: 2026-09-06
pr:
tier: tests-only
offered: their PR #965
closed:
---
`tests-only`: make the test seed its own state (or have the fixture reset it) so order stops mattering

Status detail (migrated from the table): candidate

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier tests-only — the #953 CI note recorded five xdist-ordering failures in two untouched files that pass alone but named neither, so the second file may want the same treatment).

OFFERED 2026-09-07: offered upstream as their PR #965 (2026-09-07, label tests-only, head 7ae11680), together with the batch-12 tests-only follow-ups bundle (`batch12-review-tests-only-followups`), which rode in the same PR.
