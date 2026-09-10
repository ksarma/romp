---
title: The kernel runs the interpreter its SDK venv was built for (venv-first pick_python in the three scripts, a checked ROMP_PYTHON pin, the same-tag fallback and a bounded probe), and a venv built for another python is named as such on every surface, not as a missing install
status: offered
where: bin/romp-serve, bin/romp-sdk-setup, bin/romp-codex-setup, kernel/kernel.py, kernel/sdk_backend.py, kernel/codex_backend.py, tests/romp-serve.bats, tests/install-optional-deps.bats, tests/test_sdk_venv_abi.py, tests/test_sdk_launch_error.py, tests/test_codex_backend.py, docs/reference.md, docs/install.md, bin/README.md
added: 2026-09-10
pr: 272
tier: fix
offered: their PR #1282
closed:
---
Divergence-audit row 27 PR 1a (with docs row 45 riding), the 2026-09-06 outage's cause. PR 1b (unrequested-sigterm-audit) and PR 2 (romp-down, stacked on 1b) follow. Fork follow-up: docs/install.md's fork copy is stale (pre-#272 order).
