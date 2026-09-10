---
title: The mismatch remedy names the ROMP_PYTHON pin only for a recorded interpreter that still runs as the venv's python, and a creation refusal whose verdict raises is said on stderr
status: merged
where: docs/reference.md kernel/kernel.py kernel/sdk_backend.py tests/test_sdk_launch_error.py tests/test_sdk_venv_abi.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1299
closed: 2026-09-10
---
From the maintainer's post-merge record on their #1282 (items 1 and 3): the remedy's ROMP_PYTHON hint fires only when the recorded interpreter still runs as the venv's python; a creation refusal whose verdict raises is reported on stderr instead of passing silently.
