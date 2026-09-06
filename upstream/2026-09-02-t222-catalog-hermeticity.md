---
title: A hermeticity floor for the T222 model-catalog refresh: constructing the SDK backend fires `_refresh_model_catalog("boot")` at every build — an async GET to the Models API on any credential the process carries (the manager-env key `work_api_key` claimed, else a bare `ANTHROPIC_API_KEY`, else an `ANTHROPIC_AUTH_TOKEN` bearer) — and upstream floors only its two kernel-SPAWNING tests inline (`test_gear_select_matrix.py`, `test_ship_reship.py`). In a shell carrying none of those the refresh finds no credential and stops, so no test in either suite reaches the network today (checked, not assumed); but every in-process backend construction (thread rows, user todos, judge billing, any future test) is one exported key away from a real request no test asserts on, on a key the test never chose
status: merged
where: the fold merge (`upfold0902`): a suite-wide `ROMP_MODEL_CATALOG=off` floor in `tests/conftest.py` — import-time set plus a per-test autouse re-assert, so the catalog suite's own setUp/tearDown pops cannot erase it for the tests that follow (the manager-port poison's reasoning) — pinned by `tests/test_model_catalog_floor.py` (a test pops the switch; the next proves it is back and the refresh is inert)
added: 2026-09-02
pr:
tier:
offered: their PR #877
closed: 2026-09-02
---
MERGED as-is (head is an ancestor). Branch retired. OFFERED 2026-09-02 (branch `catalog-floor`, `612b80b4` off tip `70a36077`, test-only): review caught an inaccurate pytest-internals claim in the comment/body — corrected to the verified fixture-fill-before-TestCase.run mechanism before posting; scaffold CI green (since-closed fork #152). Defensive and test-only, no fork-specific content; the catalog suite's fake-server tests keep working because they pop the var in setUp (the fixture runs first). Cut clean off their tip: the conftest block + the pin test.

Status detail (migrated from the table): ✅ **merged** — their PR #877, merged as-is 2026-09-02 — ✅ came home in upfold0905 (2026-09-05)
