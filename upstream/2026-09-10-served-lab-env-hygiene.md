---
title: Tests: a served lab's cfg.json carries only the environment the relaunched kernel needs (relaunch_env: ROMP_*, XDG_*, CLAUDE_CONFIG_DIR, PATH, HOME, TMPDIR, TMUX_TMPDIR), never the runner's whole environment
status: offered
where: tests/test_ship_reship.py (relaunch_env, kernel_env, _relaunch, RelaunchEnv test, probe checks in the served legs), tests/test_dashboard_reload_served.py
added: 2026-09-10
pr:
tier: docs
offered: their PR #1235
closed:
---
Secrets hygiene found while verifying their #1217 for the fold: both served labs wrote a copy of os.environ into the lab's cfg.json for the driver's relaunch, so a runner whose shells carry API keys left them in a temp file for the run. Tests only; upstream-native; filed directly from the upstream base. The fixture whitelist follow-up (served-fixture-env-whitelist) stacks on it.
