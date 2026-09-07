---
title: Report redaction in the test suite: a failing test's report cannot print an environment value, extracted against upstream's conftest
status: approved
where: fork PR #229 (`keyfree`, merge `988d010f`): `tests/test_env_value_redaction.py` (on fork main, absent upstream) and the conftest hook (`ENV_VALUE_REDACTED`, `env_values_to_redact`, `redact_env_values` in the fork's 533-line `tests/conftest.py`); extract against upstream's 142-line `tests/conftest.py` (at `d0e3dddf`, after their #944: the `XDG_STATE_HOME` mkdtemp at :13, `pytest_sessionfinish` at :17, no redaction code) and compose with #944's sessionfinish sweep hook
added: 2026-09-07
pr: 229
tier: tests-only
offered:
closed:
---
The tier-0 piece of the API-key management bucket (`api-key-management`) that is offerable without the maintainer conversation: the suite's report output redacts process-environment values so a failing test cannot print a credential. Test-only.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier tests-only). Carve it cleanly out of #229's key-free code and compose with (not replace) upstream's #944 `pytest_sessionfinish`; fork side, open fork PR #275 touches `tests/conftest.py`.
