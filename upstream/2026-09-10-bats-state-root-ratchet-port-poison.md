---
title: Tests: the bats suites that start the real manager isolate their state root before their first test (a ratchet suite lists them), and the suite floors poison the kernel and serve ports beside the manager port
status: offered
where: tests/bats-state-isolation.bats (new), tests/romp-manager-ensure.bats, tests/romp-manager-origin.bats, tests/romp.bats, tests/conftest.py, tests/__init__.py, tests/test_state_isolation_order.py, tests/README.md
added: 2026-09-10
pr:
tier: docs
offered: their PR #1275
closed:
---
Divergence-audit row 11 (fork PRs 272 and 275's isolation half). The conftest poison lines are the simplify row's offer-with-the-twin part; the design question was settled by tightening the detector regex (four suites listed). The loader ratchet is a separate PR.
