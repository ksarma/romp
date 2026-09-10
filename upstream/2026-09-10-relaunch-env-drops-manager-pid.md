---
title: Tests: the relaunch stanza a served lab writes drops the run's own ROMP_TESTS_ names, and an executing test pins that a live session's identity (manager pid, sid, name, bin) never reaches a relaunched lab kernel
status: offered
where: tests/test_ship_reship.py (relaunch_env, RELAUNCH_ENV_EXCLUDED_PREFIXES, RelaunchEnv), tests/README.md
added: 2026-09-10
pr:
tier: docs
offered: their PR #1274
closed:
---
Follow-up their #1235 and #1237's review records asked for, filed after their #1262 (kernel_env as a list of names) merged; with the list, the identity names cannot reach a lab kernel, so the change is the ROMP_TESTS_ exclusion plus the pins and the README convention.
