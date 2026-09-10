---
title: Docs: architecture.md states the kernel's Python and the SDK venv's three rebuild cases (the clause shared with fork PR 630), bin/README.md lists romp-codex-setup, and bats covers a uv-built venv's pyvenv.cfg (version_info, no executable) in romp-serve.bats and install-optional-deps.bats
status: offered
where: docs/architecture.md, bin/README.md, tests/romp-serve.bats, tests/install-optional-deps.bats
added: 2026-09-10
pr:
tier: docs
offered: their PR #1295
closed:
---
From the maintainer's post-merge record on their #1282 (items 2, 4 and 5); two commits (docs; bats). The architecture sentence is byte-identical to fork PR 630's so the fold stays clean.
