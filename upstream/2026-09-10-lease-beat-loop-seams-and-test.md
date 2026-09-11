---
title: Lease heartbeat: the beat loop is stepped by a test through sleep and clock seams; a refused heartbeat thread leaves the session unleased instead of crashing its connect
status: offered
where: kernel/sdk_backend.py (_lease_beat_loop seams, _lease_open thread-start guard), tests/test_sdk_lifecycle_hardening.py (LeaseRules, two tests)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1375
closed:
---
