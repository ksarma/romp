---
title: Kernel: every file-path import goes through load_source (kernel/loadsource.py, spec_from_file_location plus exec_module with load_module's sys.modules semantics), so the kernel loads clean under Python's load_module() deprecation; tests/romp_load.py twin; LOAD_CALLS gains load_source
status: offered
where: kernel/loadsource.py (new), tests/romp_load.py (new), tests/test_loadsource.py (new), kernel/kernel.py, kernel/judge.py, kernel/sdk_backend.py, kernel/codex_backend.py, tests/__init__.py, tests/conftest.py, tests/test_kernel_headless_ops.py, tests/test_api_health_hover.py, tests/test_state_isolation_order.py, kernel/README.md, tests/README.md, docs/judges.md
added: 2026-09-10
pr:
tier: fix
offered: their PR #1278
closed:
---
Divergence-audit row 2 PR 1: the loader half of fork PR 275 (free-threaded-readiness). The test-module sweep and the module-naming ratchet are PR 2, stacked on this branch.
