---
title: The bats venv-python stub's cat reads /dev/null so the romp-codex-setup cases cannot hang on an inherited open stdin; the uv pyvenv.cfg fixture comments name both version_info shapes (X.Y for a uv-managed interpreter, X.Y.Z for a system python)
status: merged
where: tests/install-optional-deps.bats (write_stub_py, the romp-sdk-setup uv case comment), tests/romp-serve.bats (the pick_python uv case comment)
added: 2026-09-10
pr:
tier: docs
offered: their PR #1298
closed: 2026-09-10
---
From the maintainer's post-merge record on their #1295 (two items: the stub's stdin, and the version_info comment; the second is the pyvenv-version-info-comment candidate, carried as commit 2 of the same PR). Two other romp-sdk-setup-only stubs keep the bare cat: they are reached only through a heredoc and do not block.
