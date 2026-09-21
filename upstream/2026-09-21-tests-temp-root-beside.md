---
title: Test temp roots beside, not inside: under pytest-xdist a worker's private `romp-tests-*` root is minted in the recorded system temp dir (`ROMP_TESTS_SYSTEM_TMPDIR`) beside the controller's rather than inside it, so the harness spends one 20-byte root level on every path whatever the worker count; a nested process lists its pid and root in `<parent root>/romp-tests-children` and the parent removes a dead child's root at run end, so a killed worker leaks nothing. Before, the deepest hosts-on lab's AF_UNIX socket path (`tests/test_session_host_restart.py`, `host-served-XXXXXXXX/xdg/romp/hosts/<sid8>.sock`) was TMPDIR + 90 bytes under `-n` and TMPDIR + 70 alone: 107 = `SOCK_PATH_MAX` exactly at a 17-byte TMPDIR, and at 18 every session-host test failed under xdist and passed alone (76 sweep logs read it as a flake). A derived pin (`tests/test_tempdir_hygiene.py` HarnessSocketBudget) measures the roots the harness makes by execution, scans the tests' own hosts-on lab shapes by AST and asserts the total against the kernel's `SOCK_PATH_MAX` with the margin in its message, and reds on a planted extra level or a longer prefix.
status: candidate
where: tests/__init__.py, tests/conftest.py, tests/test_tempdir_hygiene.py, tests/README.md; docstrings in kernel/session_host.py, kernel/sdk_backend.py, tests/test_session_host.py, tests/test_host_transport.py, tests/test_lab_dist.py
added: 2026-09-21
pr:
tier: tests-only
offered:
closed:
---
Upstream's tests/__init__.py and tests/conftest.py carry the same root, redirect and marker (their PR #999 took the hygiene), so their xdist runs nest the same way and any hosts-on lab there is 20 bytes closer to the budget than it need be; tests-only.
