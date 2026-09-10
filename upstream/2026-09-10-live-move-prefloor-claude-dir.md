---
title: Tests: the live session-move test's apiKeyHelper borrow works under pytest again (conftest saves the operator's Claude settings dir as ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR before the CLAUDE_CONFIG_DIR floor replaces it; the test reads the saved location first)
status: offered
where: tests/conftest.py (the setdefault before the floor, the _ENV_VALUE_PATH_NAMES entry), tests/test_session_move_live.py (_user_api_key_helper read order), tests/test_claude_config_floor.py, tests/test_env_value_redaction.py
added: 2026-09-10
pr:
tier: docs
offered: their PR #1237
closed:
---
Conftest audit row: their #1065 floors CLAUDE_CONFIG_DIR for every test while the opt-in live session-move test (their #946) still reads it, so the apiKeyHelper borrow was a dead route under pytest. Tests only. The fork's systemd and launchd dir floors are deleted fork-side instead (the user's decision, 2026-09-09), not offered.
