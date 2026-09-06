---
title: `tests/test_postal_relay_honesty.py::PresenceBlinkHonesty::test_disk_twin_carries_the_cache_across_a_bus_restart` depends on module order: red under xdist (`-n 8`) and when selected alone with `-k`, green with its module run in order — the one recurring full-sweep failure on every batch-12 port
status: candidate
where: upstream code (the fork carries the same module); surfaced by the batch-12 sweeps (2026-09-06); not yet built
added: 2026-09-06
pr:
tier:
offered:
closed:
---
`tests-only`: make the test seed its own state (or have the fixture reset it) so order stops mattering

Status detail (migrated from the table): candidate
